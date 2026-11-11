#!/usr/bin/env python3
"""Evaluate a binary classifier from its per-event scores: ROC, working points, overtraining,
calibration, per-category performance, data/MC agreement. Model-agnostic (BDT, DNN, GNN).

    evaluate.py scores.parquet --out-dir eval [--train scores_train.parquet]
        [--category obs_j1_pt:0,1000,1500,1e9] [--data-mc] [--compare obs_mjj,j1_btag]

Input: Parquet with a score column, a label column (1 signal, 0 background, <0 data) and
optionally weight (signed) and split ("train"/"val"/"test"). The test sample is the rows with
split == --test-split when the split column exists, otherwise the whole file; the training
sample is split == "train" or the --train file. Column names are options (--score, --label,
--weight, --split), e.g. --label is_signal for the particlenet-training outputs.

Results
  AUC_TEST, AUC_TRAIN, AUC_GAP, AUC_ERR (bootstrap, 50 resamples)
  working points: for each --bkg-effs (default 0.1,0.01,0.001) the threshold, signal
    efficiency and the number of test background events passing (N_BKG_PASS < 10 marks the
    point "low_stat": the threshold is not measured, lower the target or get more events)
  overtraining: weighted KS of train vs test scores, per class
  calibration: reliability of the score as P(signal) with the classes weighted equally
    (ECE; only meaningful if the model was trained class-balanced and the score is used as a
    probability, so it is reported, never a failure)
  per category (--category COLUMN:edge,edge,...): AUC and signal efficiency at the first
    working point, per bin; AUC_CAT_MIN is the worst bin
  data/MC (--data-mc): shape chi2/ndf between data (label < 0) and the weighted MC sum for
    the score and every --compare column, in --bins bins of equal expected MC yield. Run it in a
    control region where the signal is negligible.

Writes <out-dir>/evaluation.json and roc.png, scores.png, calibration.png (--no-plots to skip).
Stdout KEY=VALUE: N_TEST_SIG N_TEST_BKG AUC_TEST AUC_ERR [AUC_TRAIN AUC_GAP KS_P_SIG KS_P_BKG
OVERTRAINED] SIG_EFF_AT_BKG_<eff> THR_AT_BKG_<eff> ECE [AUC_CAT_MIN] [DATA_MC_CHI2_NDF_MAX
DATA_MC_WORST] FAILED STATUS.
STATUS=FAIL when AUC_TEST < --min-auc (0.6), OVERTRAINED (same rule as train_bdt.py), a
category AUC < --min-auc, or a data/MC chi2/ndf > --max-chi2-ndf (3).
Exit codes: 0 pass, 1 STATUS=FAIL (outputs written), 2 bad input. --dry-run prints the sample
sizes and writes nothing.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np


def wauc(y, s, w):
    o = np.argsort(-s, kind="stable")
    y, s, w = y[o], s[o], w[o]
    tp, fp = np.cumsum(w * y), np.cumsum(w * (1 - y))
    if tp[-1] <= 0 or fp[-1] <= 0:
        return float("nan")
    last = np.r_[s[1:] != s[:-1], True]
    tpr, fpr = np.r_[0, tp[last] / tp[-1]], np.r_[0, fp[last] / fp[-1]]
    return float(np.sum(0.5 * (tpr[1:] + tpr[:-1]) * np.diff(fpr)))


def wks(x1, w1, x2, w2):
    from scipy.stats import kstwobign

    grid = np.sort(np.concatenate([x1, x2]))

    def cdf(x, w):
        o = np.argsort(x)
        c = np.cumsum(w[o]) / w.sum()
        i = np.searchsorted(x[o], grid, side="right")
        return np.where(i > 0, c[np.maximum(i - 1, 0)], 0.0)

    d = float(np.max(np.abs(cdf(x1, w1) - cdf(x2, w2))))
    n1, n2 = w1.sum() ** 2 / (w1**2).sum(), w2.sum() ** 2 / (w2**2).sum()
    return d, float(kstwobign.sf(d * np.sqrt(n1 * n2 / (n1 + n2))))


def wquantile(x, w, q):
    """Threshold t such that the weighted fraction with x > t is q."""
    o = np.argsort(-x)
    c = np.cumsum(w[o]) / w.sum()
    i = min(int(np.searchsorted(c, q)), len(x) - 1)
    return float(x[o][i])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("scores")
    p.add_argument("--train", help="separate Parquet with the training-sample scores")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--score", default="score")
    p.add_argument("--label", default="label")
    p.add_argument("--weight", default="weight")
    p.add_argument("--split", default="split")
    p.add_argument("--test-split", default="test")
    p.add_argument("--bkg-effs", default="0.1,0.01,0.001")
    p.add_argument("--category", help="COLUMN:edge,edge,... for per-bin performance")
    p.add_argument("--data-mc", action="store_true", help="compare data (label<0) with MC shapes")
    p.add_argument("--compare", default="", help="extra columns for the data/MC comparison")
    p.add_argument("--bins", type=int, default=20)
    p.add_argument("--min-auc", type=float, default=0.6)
    p.add_argument("--max-auc-gap", type=float, default=0.02)
    p.add_argument("--min-ks-p", type=float, default=0.01)
    p.add_argument("--max-chi2-ndf", type=float, default=3.0)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--no-plots", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    try:
        import pandas as pd

        t = pd.read_parquet(a.scores)

        def cols(df):
            w = df[a.weight].to_numpy(float) if a.weight in df else np.ones(len(df))
            return df[a.score].to_numpy(float), df[a.label].to_numpy(float), w

        has_split = a.split in t
        te = t[t[a.split] == a.test_split] if has_split else t
        te = te[te[a.label] >= 0]
        tr = pd.read_parquet(a.train) if a.train else (t[t[a.split] == "train"] if has_split else None)
        s, y, w = cols(te)
        effs = [float(x) for x in a.bkg_effs.split(",")]
        if len(te) == 0 or y.min() == y.max():
            raise ValueError("the test sample is empty or has one class")
        cmp_cols = [a.score] + [c for c in a.compare.split(",") if c]
        if a.data_mc:
            t[cmp_cols]
        if a.category:
            ccol, cedges = a.category.split(":")
            cedges = [float(x) for x in cedges.split(",")]
            te[ccol]
    except Exception as e:  # noqa: BLE001
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    res = {"N_TEST_SIG": int((y == 1).sum()), "N_TEST_BKG": int((y == 0).sum())}
    if a.dry_run:
        res["N_TRAIN"] = 0 if tr is None else len(tr)
        res["DRY_RUN"] = 1
        print("\n".join(f"{k}={v}" for k, v in res.items()))
        return 0
    failed, det = [], {}
    rng = np.random.default_rng(a.seed)
    auc = wauc(y, s, w)
    boot = []
    for _ in range(50):
        i = rng.integers(0, len(y), len(y))
        boot.append(wauc(y[i], s[i], w[i]))
    res["AUC_TEST"], res["AUC_ERR"] = round(auc, 5), round(float(np.nanstd(boot)), 5)
    if not auc >= a.min_auc:
        failed.append("auc")
    if tr is not None and len(tr):
        s2, y2, w2 = cols(tr)
        auc2 = wauc(y2, s2, w2)
        gap = auc2 - auc
        ks = {n: wks(s2[y2 == c], np.abs(w2[y2 == c]), s[y == c], np.abs(w[y == c])) for n, c in (("SIG", 1), ("BKG", 0))}
        over = gap > a.max_auc_gap or (min(ks["SIG"][1], ks["BKG"][1]) < a.min_ks_p and gap > a.max_auc_gap / 2)
        res.update({"AUC_TRAIN": round(auc2, 5), "AUC_GAP": round(gap, 5), "KS_P_SIG": float(f"{ks['SIG'][1]:.3g}"),
                    "KS_P_BKG": float(f"{ks['BKG'][1]:.3g}"), "OVERTRAINED": int(over)})
        if over:
            failed.append("overtrained")
    sb, wb, ss, ws = s[y == 0], w[y == 0], s[y == 1], w[y == 1]
    wps = []
    for e in effs:
        thr = wquantile(sb, wb, e)
        npass = int((sb > thr).sum())
        es = float(ws[ss > thr].sum() / ws.sum())
        neff = ws.sum() ** 2 / (ws**2).sum()
        wps.append({"bkg_eff": e, "threshold": thr, "sig_eff": es, "sig_eff_err": float(np.sqrt(max(es * (1 - es), 0) / neff)),
                    "n_bkg_pass": npass, "low_stat": npass < 10})
        res[f"SIG_EFF_AT_BKG_{e:g}"] = round(es, 4)
        res[f"THR_AT_BKG_{e:g}"] = round(thr, 5)
    det["working_points"] = wps
    # calibration with equal class weight
    wn = np.abs(w).copy()
    for c in (0, 1):
        wn[y == c] /= wn[y == c].sum()
    edges = np.linspace(0, 1, 11)
    ib = np.clip(np.digitize(s, edges) - 1, 0, 9)
    tot = np.bincount(ib, wn, 10)
    pred = np.divide(np.bincount(ib, wn * s, 10), tot, out=np.zeros(10), where=tot > 0)
    obs = np.divide(np.bincount(ib, wn * y, 10), tot, out=np.zeros(10), where=tot > 0)
    res["ECE"] = round(float(np.sum(tot / tot.sum() * np.abs(pred - obs))), 4)
    det["calibration"] = {"mean_score": pred.tolist(), "signal_fraction": obs.tolist(), "bin_weight": tot.tolist()}
    if a.category:
        x = te[ccol].to_numpy(float)
        cats = []
        for lo, hi in zip(cedges[:-1], cedges[1:]):
            m = (x >= lo) & (x < hi)
            ok = m.sum() > 0 and len(np.unique(y[m])) == 2
            ca = wauc(y[m], s[m], w[m]) if ok else float("nan")
            ms = m & (y == 1)
            ce = float(w[ms & (s > wps[0]["threshold"])].sum() / w[ms].sum()) if ms.sum() else float("nan")
            cats.append({"lo": lo, "hi": hi, "n": int(m.sum()), "auc": ca, "sig_eff_wp0": ce})
        det["categories"] = {"column": ccol, "bins": cats}
        vals = [c["auc"] for c in cats if c["auc"] == c["auc"]]
        if vals:
            res["AUC_CAT_MIN"] = round(min(vals), 5)
            if min(vals) < a.min_auc:
                failed.append("category_auc")
    if a.data_mc:
        d, mc = t[t[a.label] < 0], t[t[a.label] >= 0]
        if len(d) == 0:
            print("error: --data-mc needs rows with label < 0", file=sys.stderr)
            return 2
        wm = mc[a.weight].to_numpy(float) if a.weight in mc else np.ones(len(mc))
        out = {}
        for c in cmp_cols:
            xm, xd = mc[c].to_numpy(float), d[c].to_numpy(float)
            o = np.argsort(xm)  # bins with equal expected (weighted) MC yield
            cw = np.cumsum(np.abs(wm[o])) / np.abs(wm).sum()
            ed = np.unique(xm[o][np.minimum(np.searchsorted(cw, np.linspace(0, 1, a.bins + 1)), len(xm) - 1)])
            ed[0], ed[-1] = -np.inf, np.inf
            hm, hm2, hd = np.histogram(xm, ed, weights=wm)[0], np.histogram(xm, ed, weights=wm**2)[0], np.histogram(xd, ed)[0]
            k = hd.sum() / hm.sum()
            var = np.clip(k * hm, 0, None) + k * k * hm2  # expected Poisson variance + MC statistics
            ok = var > 0
            out[c] = {"chi2": float(np.sum((hd[ok] - k * hm[ok]) ** 2 / var[ok])), "ndf": int(ok.sum() - 1)}
            out[c]["chi2_ndf"] = out[c]["chi2"] / max(out[c]["ndf"], 1)
        det["data_mc"] = out
        worst = max(out, key=lambda c: out[c]["chi2_ndf"])
        res["DATA_MC_CHI2_NDF_MAX"], res["DATA_MC_WORST"] = round(out[worst]["chi2_ndf"], 2), worst
        if out[worst]["chi2_ndf"] > a.max_chi2_ndf:
            failed.append("data_mc")
    res["FAILED"] = ",".join(failed) or "none"
    res["STATUS"] = "FAIL" if failed else "PASS"
    os.makedirs(a.out_dir, exist_ok=True)
    with open(os.path.join(a.out_dir, "evaluation.json"), "w") as f:
        json.dump({"summary": res, **det, "command": " ".join(sys.argv)}, f, indent=1)
    if not a.no_plots:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        o = np.argsort(-s)
        fig, ax = plt.subplots(figsize=(5, 4))
        ax.plot(np.cumsum((w * y)[o]) / ws.sum(), np.clip(np.cumsum((w * (1 - y))[o]) / wb.sum(), 1e-6, 1))
        ax.set(yscale="log", xlabel="Signal efficiency", ylabel="Background efficiency", title=f"AUC = {auc:.4f}")
        fig.savefig(os.path.join(a.out_dir, "roc.png"), dpi=120, bbox_inches="tight")
        fig, ax = plt.subplots(figsize=(5, 4))
        b = np.linspace(min(s.min(), 0), max(s.max(), 1), 41)
        for c, name, col in ((1, "signal", "C3"), (0, "background", "C0")):
            ax.hist(s[y == c], b, weights=w[y == c], density=True, histtype="step", color=col, label=f"{name} (test)")
            if tr is not None and len(tr):
                h = np.histogram(s2[y2 == c], b, weights=w2[y2 == c], density=True)[0]
                ax.plot(0.5 * (b[1:] + b[:-1]), h, ".", color=col, label=f"{name} (train)")
        ax.set(yscale="log", xlabel="Classifier score", ylabel="Normalised")
        ax.legend(fontsize=7)
        fig.savefig(os.path.join(a.out_dir, "scores.png"), dpi=120, bbox_inches="tight")
        fig, ax = plt.subplots(figsize=(4, 4))
        ax.plot([0, 1], [0, 1], "k:")
        ax.plot(pred[tot > 0], obs[tot > 0], "o-")
        ax.set(xlabel="Mean score", ylabel="Signal fraction (balanced classes)", title=f"ECE = {res['ECE']}")
        fig.savefig(os.path.join(a.out_dir, "calibration.png"), dpi=120, bbox_inches="tight")
    print("\n".join(f"{k}={v}" for k, v in res.items()))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
