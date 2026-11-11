#!/usr/bin/env python3
"""Closure tests for ML-based and data-driven background estimates.

    closure.py abcd  table.parquet --x score --x-cut 0.9 --y obs_n_btag --y-cut 1 [--query "label == 0"]
                     [--bin-col obs_mjj --bin-edges 1200,1600,2200,4000] --out-dir closure
    closure.py hist  table.parquet --var obs_mjj --edges 1200,1400,...  --pred-query "..." --obs-query "..."
                     [--pred-weight w_pred] [--normalise] --out-dir closure
    closure.py hist  --json pred_obs.json --out-dir closure      # {"edges":[], "pred":[], "pred_err":[], "obs":[], "obs_err":[]}
    closure.py kfold scores_f0.parquet scores_f1.parquet ... --bkg-eff 0.1 --out-dir closure

abcd   Regions from two cuts: A = x pass & y pass (signal-like), B = x pass & y fail,
       C = x fail & y pass, D = x fail & y fail. Prediction A_pred = B * C / D, compared with
       the observed A where the truth is known (simulation, or a validation region in data).
       Reports the pull and the non-closure A_obs/A_pred - 1, inclusively and per --bin-col
       bin, plus the Pearson correlation of x and y (ABCD needs them independent in the
       background). Weighted sums with sum-of-w^2 errors.
hist   Predicted vs observed histogram of --var: rows of --pred-query (weight --pred-weight,
       e.g. a transfer factor or reweighting column) against rows of --obs-query. --normalise
       compares shapes only. Or give both histograms as JSON.
kfold  K models, each scored on its own held-out fold: with one common score threshold (set
       for --bkg-eff on all folds together) the background pass fraction and the AUC must
       agree across folds. Disagreement means the folds are not equivalent (leakage through the
       split key, a fold-dependent selection) or the model is unstable.

Common results: pulls per bin, chi2/ndf and its p-value, mean and RMS of the pulls, the
inclusive non-closure and NONCLOSURE_SYST = max(|non-closure|, its statistical uncertainty),
the number to carry as a systematic if the test passes.
STATUS=FAIL when the chi2 p-value < --min-p (0.01), |inclusive pull| > --max-pull (3), or (abcd)
a region has fewer than --min-events (10) effective events (the test has no power: LOW_STAT).
Writes <out-dir>/closure.json and closure.png.

Stdout KEY=VALUE: TEST N_BINS CHI2_NDF P_VALUE PULL_INCL PULL_MEAN PULL_RMS MAX_ABS_PULL
NONCLOSURE NONCLOSURE_ERR NONCLOSURE_SYST [CORR_XY N_A N_B N_C N_D A_PRED A_OBS] FAILED STATUS.
Exit codes: 0 pass, 1 STATUS=FAIL, 2 bad input. --dry-run prints the region or bin counts only.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np


def finish(a, test, pred, perr, obs, oerr, labels, extra, failed, incl=None):
    """Pulls, chi2 and non-closure for binned predicted vs observed; writes outputs."""
    from scipy.stats import chi2 as chi2dist

    pred, perr, obs, oerr = (np.asarray(v, float) for v in (pred, perr, obs, oerr))
    err = np.sqrt(perr**2 + oerr**2)
    ok = err > 0
    pulls = np.where(ok, (obs - pred) / np.where(ok, err, 1), 0.0)
    ndf = int(ok.sum()) - (1 if getattr(a, "normalise", False) else 0)
    chi2 = float(np.sum(pulls[ok] ** 2))
    pval = float(chi2dist.sf(chi2, ndf)) if ndf > 0 else float("nan")
    P, O, PE, OE = incl if incl else (pred.sum(), obs.sum(), np.sqrt((perr**2).sum()), np.sqrt((oerr**2).sum()))
    nc = O / P - 1 if P > 0 else float("nan")
    nce = abs(O / P) * np.sqrt((OE / O) ** 2 + (PE / P) ** 2) if P > 0 and O > 0 else float("nan")
    pull_incl = (O - P) / np.sqrt(PE**2 + OE**2) if PE + OE > 0 else float("nan")
    if ndf > 0 and pval < a.min_p:
        failed.append("chi2")
    if not getattr(a, "normalise", False) and abs(pull_incl) > a.max_pull:
        failed.append("inclusive_pull")
    res = {"TEST": test, "N_BINS": int(ok.sum()), "CHI2_NDF": round(chi2 / max(ndf, 1), 3), "P_VALUE": float(f"{pval:.3g}"),
           "PULL_INCL": round(float(pull_incl), 3), "PULL_MEAN": round(float(pulls[ok].mean()), 3) if ok.any() else "nan",
           "PULL_RMS": round(float(pulls[ok].std()), 3) if ok.any() else "nan",
           "MAX_ABS_PULL": round(float(np.abs(pulls).max()), 3), "NONCLOSURE": round(float(nc), 4),
           "NONCLOSURE_ERR": round(float(nce), 4), "NONCLOSURE_SYST": round(float(np.nanmax([abs(nc), nce])), 4)}
    res.update(extra)
    res.update({"FAILED": ",".join(failed) or "none", "STATUS": "FAIL" if failed else "PASS"})
    os.makedirs(a.out_dir, exist_ok=True)
    with open(os.path.join(a.out_dir, "closure.json"), "w") as f:
        json.dump({"summary": res, "bins": labels, "pred": pred.tolist(), "pred_err": perr.tolist(), "obs": obs.tolist(),
                   "obs_err": oerr.tolist(), "pulls": pulls.tolist(), "command": " ".join(sys.argv)}, f, indent=1)
    if not a.no_plots:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        x = np.arange(len(pred))
        fig, (ax, rx) = plt.subplots(2, 1, figsize=(5.5, 5), sharex=True, gridspec_kw={"height_ratios": [3, 1.2]})
        ax.errorbar(x - 0.08, pred, perr, fmt="s", color="C0", label="predicted")
        ax.errorbar(x + 0.08, obs, oerr, fmt="o", color="k", label="observed")
        if (pred > 0).all() and (obs > 0).all():
            ax.set_yscale("log")
        ax.set_title(f"{test} closure: chi2/ndf = {res['CHI2_NDF']}, p = {res['P_VALUE']}", fontsize=9)
        ax.legend()
        rx.bar(x, pulls, color="C0")
        rx.axhline(0, color="k", lw=0.5)
        rx.set(ylabel="pull", ylim=(-4, 4), xticks=x)
        rx.set_xticklabels(labels, rotation=45, ha="right", fontsize=6)
        fig.savefig(os.path.join(a.out_dir, "closure.png"), dpi=120, bbox_inches="tight")
    print("\n".join(f"{k}={v}" for k, v in res.items()))
    return 1 if failed else 0


def sums(w):
    return float(w.sum()), float(np.sqrt((w**2).sum()))


def cmd_abcd(a, pd):
    t = pd.read_parquet(a.table)
    if a.query:
        t = t.query(a.query)
    x, y = t[a.x].to_numpy(float), t[a.y].to_numpy(float)
    w = t[a.weight].to_numpy(float) if a.weight in t else np.ones(len(t))
    xp, yp = x > a.x_cut, y > a.y_cut
    reg = {"A": xp & yp, "B": xp & ~yp, "C": ~xp & yp, "D": ~xp & ~yp}
    if a.bin_col:
        edges = [float(e) for e in a.bin_edges.split(",")]
        v = t[a.bin_col].to_numpy(float)
        bins = [((v >= lo) & (v < hi), f"{lo:g}-{hi:g}") for lo, hi in zip(edges[:-1], edges[1:])]
    else:
        bins = [(np.ones(len(t), bool), "inclusive")]

    def predict(m):
        n = {k: sums(w[r & m]) for k, r in reg.items()}
        (A, eA), (B, eB), (C, eC), (D, eD) = (n[k] for k in "ABCD")
        if min(B, C, D) <= 0:
            return 0.0, 0.0, A, eA, n
        pr = B * C / D
        return pr, pr * np.sqrt((eB / B) ** 2 + (eC / C) ** 2 + (eD / D) ** 2), A, eA, n

    allm = np.ones(len(t), bool)
    P, PE, O, OE, n = predict(allm)
    neff = {k: (v[0] / v[1]) ** 2 if v[1] > 0 else 0.0 for k, v in n.items()}
    extra = {"CORR_XY": round(float(np.corrcoef(x, y)[0, 1]), 4)}
    extra.update({f"N_{k}": round(neff[k], 1) for k in "ABCD"})
    extra.update({"A_PRED": float(f"{P:.5g}"), "A_OBS": float(f"{O:.5g}")})
    if a.dry_run:
        print("\n".join(f"{k}={v}" for k, v in extra.items()) + "\nDRY_RUN=1")
        return 0
    failed = ["low_stat"] if min(neff.values()) < a.min_events else []
    rows = [predict(m) for m, _ in bins]
    return finish(a, "abcd", [r[0] for r in rows], [r[1] for r in rows], [r[2] for r in rows], [r[3] for r in rows],
                  [b[1] for b in bins], extra, failed, incl=(P, O, PE, OE))


def cmd_hist(a, pd):
    if a.json:
        d = json.load(open(a.json))
        edges, pred, perr, obs, oerr = (np.asarray(d[k], float) for k in ("edges", "pred", "pred_err", "obs", "obs_err"))
    else:
        t = pd.read_parquet(a.table)
        edges = np.array([float(e) for e in a.edges.split(",")])
        out = []
        for q, wc in ((a.pred_query, a.pred_weight), (a.obs_query, a.obs_weight)):
            s = t.query(q)
            w = s[wc].to_numpy(float) if wc in s else np.ones(len(s))
            out += [np.histogram(s[a.var], edges, weights=w)[0], np.sqrt(np.histogram(s[a.var], edges, weights=w**2)[0])]
        pred, perr, obs, oerr = out
    if a.normalise:
        k = obs.sum() / pred.sum()
        pred, perr = pred * k, perr * k
    if a.dry_run:
        print(f"N_BINS={len(pred)}\nSUM_PRED={pred.sum():.5g}\nSUM_OBS={obs.sum():.5g}\nDRY_RUN=1")
        return 0
    return finish(a, "hist", pred, perr, obs, oerr, [f"{lo:g}-{hi:g}" for lo, hi in zip(edges[:-1], edges[1:])], {}, [])


def cmd_kfold(a, pd):
    parts = []
    for f in a.scores:
        t = pd.read_parquet(f)
        if a.split in t:
            t = t[t[a.split] == a.test_split]
        t = t[t[a.label] >= 0]
        w = t[a.weight].to_numpy(float) if a.weight in t else np.ones(len(t))
        parts.append((t[a.score].to_numpy(float), t[a.label].to_numpy(), w))
    if len(parts) < 2:
        raise ValueError("kfold needs at least two score files")
    sb = np.concatenate([s[y == 0] for s, y, w in parts])
    wb = np.concatenate([w[y == 0] for s, y, w in parts])
    o = np.argsort(-sb)
    thr = sb[o][min(int(np.searchsorted(np.cumsum(wb[o]) / wb.sum(), a.bkg_eff)), len(sb) - 1)]
    eff, err, aucs = [], [], []
    for s, y, w in parts:
        b = y == 0
        e = w[b & (s > thr)].sum() / w[b].sum()
        neff = w[b].sum() ** 2 / (w[b] ** 2).sum()
        eff.append(e)
        err.append(np.sqrt(max(e * (1 - e), 1e-12) / neff))
        oo = np.argsort(-s)
        tp, fp = np.cumsum((w * (y == 1))[oo]), np.cumsum((w * b)[oo])
        aucs.append(float(np.sum(0.5 * (np.r_[0, tp[:-1]] + tp) * np.diff(np.r_[0, fp])) / (tp[-1] * fp[-1])))
    if a.dry_run:
        print(f"N_FOLDS={len(parts)}\nTHRESHOLD={thr:.5g}\nDRY_RUN=1")
        return 0
    extra = {"THRESHOLD": round(float(thr), 5), "AUC_MEAN": round(float(np.mean(aucs)), 5),
             "AUC_STD": round(float(np.std(aucs, ddof=1)), 5), "AUC_MIN": round(min(aucs), 5), "AUC_MAX": round(max(aucs), 5)}
    n = len(parts)
    return finish(a, "kfold", [a.bkg_eff] * n, [0.0] * n, eff, err, [os.path.basename(os.path.dirname(os.path.abspath(f))) for f in a.scores], extra, [])


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--out-dir", required=True)
    common.add_argument("--weight", default="weight")
    common.add_argument("--min-p", type=float, default=0.01)
    common.add_argument("--max-pull", type=float, default=3.0)
    common.add_argument("--no-plots", action="store_true")
    common.add_argument("--dry-run", action="store_true")
    sub = p.add_subparsers(dest="sub", required=True)
    s = sub.add_parser("abcd", parents=[common])
    s.add_argument("table")
    s.add_argument("--x", required=True)
    s.add_argument("--x-cut", type=float, required=True)
    s.add_argument("--y", required=True)
    s.add_argument("--y-cut", type=float, required=True)
    s.add_argument("--query", help="pandas query selecting the rows (e.g. \"label == 0 and split == 'test'\")")
    s.add_argument("--bin-col")
    s.add_argument("--bin-edges")
    s.add_argument("--min-events", type=float, default=10)
    s.set_defaults(fn=cmd_abcd)
    s = sub.add_parser("hist", parents=[common])
    s.add_argument("table", nargs="?")
    s.add_argument("--json")
    s.add_argument("--var")
    s.add_argument("--edges")
    s.add_argument("--pred-query")
    s.add_argument("--obs-query")
    s.add_argument("--pred-weight", default="weight")
    s.add_argument("--obs-weight", default="weight")
    s.add_argument("--normalise", action="store_true")
    s.set_defaults(fn=cmd_hist)
    s = sub.add_parser("kfold", parents=[common])
    s.add_argument("scores", nargs="+")
    s.add_argument("--bkg-eff", type=float, default=0.1)
    s.add_argument("--score", default="score")
    s.add_argument("--label", default="label")
    s.add_argument("--split", default="split")
    s.add_argument("--test-split", default="test")
    s.set_defaults(fn=cmd_kfold)
    a = p.parse_args()
    try:
        import pandas as pd

        return a.fn(a, pd)
    except (OSError, KeyError, ValueError, TypeError, SyntaxError) as e:
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
