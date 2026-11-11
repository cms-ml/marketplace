#!/usr/bin/env python3
"""Train a gradient-boosted classifier on a flat feature table and run the standard checks.

    train_bdt.py table.parquet --out-dir runs/bdt0 [--backend xgboost|hgb|lightgbm] [--onnx]

Input: Parquet with feature columns, label (1 signal, 0 background; rows with label < 0 are
scored but never trained on), weight (signed physics weight), fold (event % n) and optional
obs_* observers (see the hep-ml-data-prep skill). Features default to every column that is
not reserved and does not start with obs_.

What it does
  split     by fold: --train-folds (default 0,1,2), --val-folds (3; early stopping only),
            --test-folds (4; never seen in training or model selection)
  weights   training weight = |w| (--neg-weights abs, default), max(w,0) (zero) or rows with
            w<0 dropped (drop), then each class scaled to the same sum (--no-balance to skip)
            and the mean set to 1. All metrics use the original signed weights.
  train     early stopping on the validation logloss (--early-stopping rounds)
  checks    weighted AUC train/val/test; weighted KS test of the score, train vs test, for
            signal and background; gain importance and mean |SHAP| (xgboost/lightgbm built-in
            TreeSHAP, no shap package needed)
  export    xgboost: model.json (+ model.onnx with --onnx, needs onnxmltools);
            lightgbm: model.txt; hgb: model.pkl (+ model.onnx with --onnx, needs skl2onnx).
            ONNX outputs are compared with the native scores on the test rows.

Outputs in --out-dir: model.*, scores.parquet (score, split, label, weight, fold, event,
sample, obs_*: every row), metrics.json (everything below plus params, features, importance,
versions, seed), and one line appended to <out-dir>/../runs.jsonl (the offline run log).
--params-json '{"max_depth": 3, ...}' overrides the hyperparameter flags (used by the
hyperparam-scan skill). --progress-every N prints "PROGRESS step=<iter> value=<val AUC>"
lines (xgboost) so a scan can prune the run.

Stdout KEY=VALUE: BACKEND N_TRAIN N_VAL N_TEST N_FEATURES BEST_ITER AUC_TRAIN AUC_VAL AUC_TEST
AUC_GAP KS_P_SIG KS_P_BKG OVERTRAINED TOP_FEATURES [ONNX_MAX_ABS_DIFF ONNX_FRAC_DIFF] SECONDS OUT_DIR STATUS.
OVERTRAINED=1 when AUC_TRAIN - AUC_TEST > --max-auc-gap (0.02) or (min KS p < --min-ks-p
(0.01) and the gap > half of that limit). STATUS=FAIL when OVERTRAINED, AUC_TEST < --min-auc
(0.6), or more than 0.5% of the ONNX scores differ from the native ones by > 1e-4
(ONNX_FRAC_DIFF; ONNX stores float32 split thresholds, so a few lightgbm/HGB rows that sit on
a threshold can move by O(0.01): ONNX_MAX_ABS_DIFF reports the largest).
Exit codes: 0 ok, 1 STATUS=FAIL (outputs are still written), 2 bad input or missing package.
--dry-run prints the split sizes and features and writes nothing. --skip-existing returns the
stored result when <out-dir>/metrics.json was made with the same arguments.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

import numpy as np

RESERVED = {"label", "sample", "event", "gen_weight", "weight", "fold"}
DEFAULTS = {"n_estimators": 1000, "learning_rate": 0.1, "max_depth": 4, "min_child_weight": 1.0,
            "subsample": 0.8, "colsample_bytree": 0.8, "reg_lambda": 1.0, "gamma": 0.0}


def log(m):
    print(m, file=sys.stderr, flush=True)


def wauc(y, s, w):
    """Weighted ROC AUC; valid for signed weights."""
    o = np.argsort(-s, kind="stable")
    y, s, w = y[o], s[o], w[o]
    tp, fp = np.cumsum(w * y), np.cumsum(w * (1 - y))
    last = np.r_[s[1:] != s[:-1], True]
    tpr, fpr = np.r_[0, tp[last] / tp[-1]], np.r_[0, fp[last] / fp[-1]]
    return float(np.sum(0.5 * (tpr[1:] + tpr[:-1]) * np.diff(fpr)))


def wks(x1, w1, x2, w2):
    """Weighted two-sample KS: (D, p) with p from the asymptotic law and effective sample sizes."""
    from scipy.stats import kstwobign

    if len(x1) == 0 or len(x2) == 0:
        return float("nan"), float("nan")
    grid = np.sort(np.concatenate([x1, x2]))

    def cdf(x, w):
        o = np.argsort(x)
        c = np.cumsum(w[o]) / w.sum()
        i = np.searchsorted(x[o], grid, side="right")
        return np.where(i > 0, c[np.maximum(i - 1, 0)], 0.0)

    d = float(np.max(np.abs(cdf(x1, w1) - cdf(x2, w2))))
    n1, n2 = w1.sum() ** 2 / (w1**2).sum(), w2.sum() ** 2 / (w2**2).sum()
    return d, float(kstwobign.sf(d * np.sqrt(n1 * n2 / (n1 + n2))))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("table")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--backend", choices=["xgboost", "hgb", "lightgbm"], default="xgboost")
    p.add_argument("--features", help="comma-separated columns (default: by naming convention)")
    p.add_argument("--label", default="label")
    p.add_argument("--weight", default="weight")
    p.add_argument("--fold", default="fold")
    p.add_argument("--train-folds", default="0,1,2")
    p.add_argument("--val-folds", default="3")
    p.add_argument("--test-folds", default="4")
    p.add_argument("--neg-weights", choices=["abs", "zero", "drop"], default="abs")
    p.add_argument("--no-balance", action="store_true", help="do not equalise the class weight sums")
    for k, v in DEFAULTS.items():
        p.add_argument("--" + k.replace("_", "-"), type=type(v), default=v, help="(default: %(default)s)")
    p.add_argument("--params-json", help="JSON dict overriding the hyperparameter flags")
    p.add_argument("--early-stopping", type=int, default=30, help="rounds without val improvement")
    p.add_argument("--progress-every", type=int, default=0, help="print PROGRESS lines every N iterations")
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--threads", type=int, default=4)
    p.add_argument("--min-auc", type=float, default=0.6)
    p.add_argument("--max-auc-gap", type=float, default=0.02)
    p.add_argument("--min-ks-p", type=float, default=0.01)
    p.add_argument("--onnx", action="store_true")
    p.add_argument("--skip-existing", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    t0 = time.time()
    os.environ.setdefault("OMP_NUM_THREADS", str(a.threads))  # also limits sklearn HGB
    hp = {k: getattr(a, k) for k in DEFAULTS}
    try:
        if a.params_json:
            extra = json.loads(a.params_json)
            unknown = set(extra) - set(DEFAULTS)
            if unknown:
                raise ValueError(f"unknown hyperparameters {sorted(unknown)}; allowed: {sorted(DEFAULTS)}")
            hp.update({k: type(DEFAULTS[k])(v) for k, v in extra.items()})
        import pandas as pd

        t = pd.read_parquet(a.table)
        feats = a.features.split(",") if a.features else [
            c for c in t.columns if c not in RESERVED | {a.label, a.weight, a.fold} and not c.startswith("obs_")]
        folds = {k: [int(x) for x in getattr(a, k + "_folds").split(",")] for k in ("train", "val", "test")}
        if set(folds["train"]) & set(folds["val"]) or (set(folds["train"]) | set(folds["val"])) & set(folds["test"]):
            raise ValueError("train, val and test folds must not overlap")
        X = t[feats].to_numpy(dtype=np.float32)
        y = t[a.label].to_numpy()
        w = t[a.weight].to_numpy(dtype=np.float64) if a.weight in t else np.ones(len(t))
        fold = t[a.fold].to_numpy()
    except Exception as e:  # noqa: BLE001
        log(f"error: {type(e).__name__}: {e}")
        return 2
    cfg = {"table": os.path.abspath(a.table), "backend": a.backend, "features": feats, "folds": folds, "hp": hp,
           "neg_weights": a.neg_weights, "balance": not a.no_balance, "early_stopping": a.early_stopping,
           "seed": a.seed}
    cfg_hash = hashlib.sha1(json.dumps(cfg, sort_keys=True).encode()).hexdigest()[:12]
    mpath = os.path.join(a.out_dir, "metrics.json")
    if a.skip_existing and os.path.exists(mpath):
        old = json.load(open(mpath))
        if old.get("config_hash") == cfg_hash:
            log("# identical run found, returning stored metrics")
            print("\n".join(f"{k}={v}" for k, v in old["summary"].items()))
            return 0 if old["summary"]["STATUS"] == "PASS" else 1

    mc = y >= 0
    sel = {k: mc & np.isin(fold, v) for k, v in folds.items()}
    for k, m in sel.items():
        if len(np.unique(y[m])) < 2:
            log(f"error: the {k} split has {int(m.sum())} rows and not both classes")
            return 2
    if a.dry_run:
        print("\n".join(f"N_{k.upper()}={int(m.sum())}" for k, m in sel.items()))
        print(f"N_FEATURES={len(feats)}\nFEATURES={','.join(feats)}\nDRY_RUN=1")
        return 0

    def train_weight(m):
        ww = np.abs(w[m]) if a.neg_weights == "abs" else np.clip(w[m], 0, None)
        if not a.no_balance:
            for c in (0, 1):
                ww[y[m] == c] /= ww[y[m] == c].sum()
        return ww / ww.mean()

    if a.neg_weights == "drop":
        sel["train"] &= w > 0
        sel["val"] &= w > 0
    wtr, wva = train_weight(sel["train"]), train_weight(sel["val"])
    Xtr, ytr, Xva, yva = X[sel["train"]], y[sel["train"]], X[sel["val"]], y[sel["val"]]
    os.makedirs(a.out_dir, exist_ok=True)
    importance, shap_abs, versions = {}, {}, {"numpy": np.__version__}

    try:
        if a.backend == "xgboost":
            import xgboost as xgb

            versions["xgboost"] = xgb.__version__

            class Progress(xgb.callback.TrainingCallback):
                def after_iteration(self, model, epoch, evals_log):
                    if a.progress_every and (epoch + 1) % a.progress_every == 0:
                        s = model.predict(xgb.DMatrix(Xva), iteration_range=(0, epoch + 1))
                        print(f"PROGRESS step={epoch + 1} value={wauc(yva, s, w[sel['val']]):.5f}", flush=True)
                    return False

            model = xgb.XGBClassifier(
                tree_method="hist", objective="binary:logistic", eval_metric="logloss", random_state=a.seed,
                n_jobs=a.threads, early_stopping_rounds=a.early_stopping, callbacks=[Progress()], **hp)
            model.fit(Xtr, ytr, sample_weight=wtr, eval_set=[(Xva, yva)], sample_weight_eval_set=[wva], verbose=False)
            best_iter = int(model.best_iteration) + 1
            score = model.predict_proba(X)[:, 1]
            bst = model.get_booster()[:best_iter]  # keep only the trees up to the best iteration
            bst.feature_names = feats
            bst.save_model(os.path.join(a.out_dir, "model.json"))
            importance = {k: float(v) for k, v in bst.get_score(importance_type="total_gain").items()}
            idx = np.flatnonzero(sel["test"])[:5000]
            contrib = bst.predict(xgb.DMatrix(X[idx], feature_names=feats), pred_contribs=True)
            shap_abs = dict(zip(feats, np.abs(contrib[:, :-1]).mean(axis=0).tolist()))
        elif a.backend == "lightgbm":
            import lightgbm as lgb

            versions["lightgbm"] = lgb.__version__
            model = lgb.LGBMClassifier(
                n_estimators=hp["n_estimators"], learning_rate=hp["learning_rate"], max_depth=hp["max_depth"],
                num_leaves=2 ** hp["max_depth"] - 1, min_sum_hessian_in_leaf=hp["min_child_weight"],
                subsample=hp["subsample"], subsample_freq=1, colsample_bytree=hp["colsample_bytree"],
                reg_lambda=hp["reg_lambda"], min_split_gain=hp["gamma"], random_state=a.seed, n_jobs=a.threads,
                verbose=-1)
            model.fit(Xtr, ytr, sample_weight=wtr, eval_set=[(Xva, yva)], eval_sample_weight=[wva],
                      callbacks=[lgb.early_stopping(a.early_stopping, verbose=False)])
            best_iter = int(model.best_iteration_)
            model.booster_.save_model(os.path.join(a.out_dir, "model.txt"), num_iteration=best_iter)
            bst = lgb.Booster(model_file=os.path.join(a.out_dir, "model.txt"))  # trees up to the best iteration
            score = bst.predict(X)
            importance = dict(zip(feats, bst.feature_importance("gain").tolist()))
            idx = np.flatnonzero(sel["test"])[:5000]
            contrib = bst.predict(X[idx], pred_contrib=True)
            shap_abs = dict(zip(feats, np.abs(contrib[:, :-1]).mean(axis=0).tolist()))
        else:
            import joblib
            import sklearn
            from sklearn.ensemble import HistGradientBoostingClassifier

            versions["sklearn"] = sklearn.__version__
            # HGB early-stops on its own random validation split, so give it train only and
            # use the val folds for the reported AUC_VAL (subsample/colsample/gamma do not apply)
            model = HistGradientBoostingClassifier(
                max_iter=hp["n_estimators"], learning_rate=hp["learning_rate"], max_depth=hp["max_depth"],
                l2_regularization=hp["reg_lambda"], early_stopping=True, validation_fraction=0.2,
                n_iter_no_change=a.early_stopping, random_state=a.seed)
            model.fit(Xtr, ytr, sample_weight=wtr)
            best_iter = int(model.n_iter_)
            score = model.predict_proba(X)[:, 1]
            joblib.dump({"model": model, "features": feats, "sklearn": sklearn.__version__},
                        os.path.join(a.out_dir, "model.pkl"))
    except ImportError as e:
        log(f"error: {e}. Install it in a venv (see the skill) or choose another --backend")
        return 2

    auc = {k: wauc(y[m].astype(float), score[m], w[m]) for k, m in sel.items()}
    ks = {}
    for name, c in (("SIG", 1), ("BKG", 0)):
        m1, m2 = sel["train"] & (y == c), sel["test"] & (y == c)
        ks[name] = wks(score[m1], np.abs(w[m1]), score[m2], np.abs(w[m2]))
    gap = auc["train"] - auc["test"]
    min_p = min(ks["SIG"][1], ks["BKG"][1])
    over = gap > a.max_auc_gap or (min_p < a.min_ks_p and gap > a.max_auc_gap / 2)

    onnx_diff = None
    if a.onnx:
        try:
            import onnxruntime as ort

            n = int(min(sel["test"].sum(), 5000))
            xt = X[sel["test"]][:n]
            path = os.path.join(a.out_dir, "model.onnx")
            if a.backend == "hgb":
                from skl2onnx import to_onnx

                onx = to_onnx(model, xt[:1], options={"zipmap": False}, target_opset=17)
            else:
                import onnxmltools
                from onnxmltools.convert.common.data_types import FloatTensorType

                it = [("input", FloatTensorType([None, len(feats)]))]
                if a.backend == "xgboost":
                    bst.feature_names = None  # the converter needs f0, f1, ... names
                    onx = onnxmltools.convert_xgboost(bst, initial_types=it, target_opset=15)
                else:
                    onx = onnxmltools.convert_lightgbm(bst, initial_types=it, target_opset=15, zipmap=False)
            with open(path, "wb") as f:
                f.write(onx.SerializeToString())
            sess = ort.InferenceSession(path)
            out = sess.run(None, {sess.get_inputs()[0].name: xt})
            prob = next(o for o in out if getattr(o, "ndim", 0) == 2)[:, -1]
            dd = np.abs(prob - score[sel["test"]][:n])
            onnx_diff, onnx_frac = float(dd.max()), float((dd > 1e-4).mean())
        except Exception as e:  # noqa: BLE001
            log(f"error: ONNX export/check failed: {type(e).__name__}: {e}")
            onnx_diff, onnx_frac = float("inf"), 1.0

    split = np.full(len(t), "unused", dtype=object)
    for k, m in sel.items():
        split[m] = k
    split[~mc] = "data"
    keep = [c for c in t.columns if c in RESERVED | {a.label, a.weight, a.fold} or c.startswith("obs_")]
    out = t[keep].copy()
    out["score"], out["split"] = score.astype(np.float32), split
    out.to_parquet(os.path.join(a.out_dir, "scores.parquet"), index=False)

    rank = sorted(shap_abs or importance, key=(shap_abs or importance).get, reverse=True)
    status = "FAIL" if (over or auc["test"] < a.min_auc or (onnx_diff is not None and onnx_frac > 0.005)) else "PASS"
    res = {"BACKEND": a.backend, "N_TRAIN": int(sel["train"].sum()), "N_VAL": int(sel["val"].sum()),
           "N_TEST": int(sel["test"].sum()), "N_FEATURES": len(feats), "BEST_ITER": best_iter,
           "AUC_TRAIN": round(auc["train"], 5), "AUC_VAL": round(auc["val"], 5), "AUC_TEST": round(auc["test"], 5),
           "AUC_GAP": round(gap, 5), "KS_P_SIG": float(f"{ks['SIG'][1]:.3g}"), "KS_P_BKG": float(f"{ks['BKG'][1]:.3g}"),
           "OVERTRAINED": int(over), "TOP_FEATURES": ",".join(rank[:5]) or "n/a"}
    if onnx_diff is not None:
        res["ONNX_MAX_ABS_DIFF"] = float(f"{onnx_diff:.2e}")
        res["ONNX_FRAC_DIFF"] = round(onnx_frac, 5)
    res.update({"SECONDS": round(time.time() - t0, 1), "OUT_DIR": a.out_dir, "STATUS": status})
    full = {"summary": res, "config": cfg, "config_hash": cfg_hash, "ks_D": {k: v[0] for k, v in ks.items()},
            "importance_total_gain": importance, "mean_abs_shap": shap_abs, "versions": versions,
            "command": " ".join(sys.argv)}
    with open(mpath, "w") as f:
        json.dump(full, f, indent=1)
    with open(os.path.join(os.path.dirname(os.path.abspath(a.out_dir)), "runs.jsonl"), "a") as f:
        f.write(json.dumps({"time": time.strftime("%Y-%m-%dT%H:%M:%S"), "hash": cfg_hash, "hp": hp, **res}) + "\n")
    print("\n".join(f"{k}={v}" for k, v in res.items()))
    return 0 if status == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
