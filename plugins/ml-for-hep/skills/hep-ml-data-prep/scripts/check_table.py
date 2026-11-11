#!/usr/bin/env python3
"""Pre-training checks on a feature table (Parquet): leakage, bad values, weights, folds.

    check_table.py table.parquet [--features a,b,c] [--mass obs_mjj] [--json checks.json]

Checks (FAIL = exit 1):
  bad_values       NaN/inf in a feature
  constant         a feature with a single value
  forbidden_name   feature names that look like truth or bookkeeping
                   (gen, truth, label, flavour, weight, xsec, event, run, lumi, fold, sample)
  leakage          weighted single-feature AUC > --max-single-auc (default 0.98): one input
                   that separates the classes almost perfectly is nearly always a label proxy
  fold_class       a fold without signal or without background
Warnings (reported, exit stays 0): effective sample size of a class below --min-neff,
|Pearson r| between a feature and --mass in background above --max-mass-corr (sculpting risk),
negative-weight fraction above 0.3.

Features default to every column that is not reserved (label, sample, event, gen_weight,
weight, fold) and does not start with obs_. Rows with label < 0 (data) are ignored.

Stdout KEY=VALUE: N_FEATURES N_FAIL N_WARN FAILED=<names> WARNED=<names> NEFF_SIG NEFF_BKG
NEG_WEIGHT_FRAC TOP_SINGLE_AUC=<feature>:<auc> STATUS=PASS|FAIL. Details per feature go to
--json. Exit codes: 0 pass, 1 a check failed, 2 bad input. Read-only (writes only --json).
"""
from __future__ import annotations

import argparse
import json
import re
import sys

import numpy as np

RESERVED = {"label", "sample", "event", "gen_weight", "weight", "fold"}
FORBIDDEN = re.compile(r"(^|_)(gen|truth|label|hadronflavour|partonflavour|flavour|weight|xsec|event|run|lumi|fold|sample)", re.I)


def wauc(y, s, w):
    """Weighted ROC AUC; valid for signed weights (integral of TPR dFPR)."""
    o = np.argsort(-s, kind="stable")
    y, s, w = y[o], s[o], w[o]
    tp, fp = np.cumsum(w * y), np.cumsum(w * (1 - y))
    last = np.r_[s[1:] != s[:-1], True]
    tpr, fpr = np.r_[0, tp[last] / tp[-1]], np.r_[0, fp[last] / fp[-1]]
    return float(np.sum(0.5 * (tpr[1:] + tpr[:-1]) * np.diff(fpr)))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("table")
    p.add_argument("--features", help="comma-separated feature columns (default: by naming convention)")
    p.add_argument("--label", default="label")
    p.add_argument("--weight", default="weight")
    p.add_argument("--fold", default="fold")
    p.add_argument("--mass", help="observer column for the mass-correlation warning")
    p.add_argument("--max-single-auc", type=float, default=0.98)
    p.add_argument("--max-mass-corr", type=float, default=0.5)
    p.add_argument("--min-neff", type=float, default=1000)
    p.add_argument("--json", help="write per-feature details here")
    a = p.parse_args()
    try:
        import pandas as pd

        t = pd.read_parquet(a.table)
        t = t[t[a.label] >= 0]
        feats = a.features.split(",") if a.features else [
            c for c in t.columns if c not in RESERVED | {a.label, a.weight, a.fold} and not c.startswith("obs_")]
        y = t[a.label].to_numpy().astype(float)
        w = t[a.weight].to_numpy().astype(float) if a.weight in t else np.ones(len(t))
        if not feats or y.min() == y.max():
            raise ValueError("no features, or only one class in the table")
        t[feats]
    except Exception as e:  # noqa: BLE001
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2

    fail, warn, det = {}, {}, {}
    for f in feats:
        x = t[f].to_numpy().astype(float)
        d = {}
        nbad = int((~np.isfinite(x)).sum())
        if nbad:
            fail.setdefault("bad_values", []).append(f)
            d["n_bad"] = nbad
            x = np.where(np.isfinite(x), x, 0.0)
        if np.ptp(x) == 0:
            fail.setdefault("constant", []).append(f)
        else:
            auc = wauc(y, x, w)
            d["single_auc"] = round(max(auc, 1 - auc), 4)
            if d["single_auc"] > a.max_single_auc:
                fail.setdefault("leakage", []).append(f)
            if a.mass:
                b = y == 0
                d["mass_corr_bkg"] = round(float(np.corrcoef(x[b], t[a.mass].to_numpy()[b])[0, 1]), 3)
                if abs(d["mass_corr_bkg"]) > a.max_mass_corr:
                    warn.setdefault("mass_corr", []).append(f)
        if FORBIDDEN.search(f):
            fail.setdefault("forbidden_name", []).append(f)
        det[f] = d
    neff = {}
    for name, lab in (("SIG", 1), ("BKG", 0)):
        ww = w[y == lab]
        neff[name] = float(ww.sum() ** 2 / (ww**2).sum())
        if neff[name] < a.min_neff:
            warn.setdefault("low_neff", []).append(name.lower())
    if a.fold in t:
        for k, g in t.groupby(a.fold):
            if g[a.label].nunique() < 2:
                fail.setdefault("fold_class", []).append(f"fold{k}")
    negf = float((w < 0).mean())
    if negf > 0.3:
        warn.setdefault("neg_weights", []).append(f"{negf:.2f}")
    top = max(((f, d.get("single_auc", 0)) for f, d in det.items()), key=lambda z: z[1])
    res = {"N_FEATURES": len(feats), "N_FAIL": sum(map(len, fail.values())), "N_WARN": sum(map(len, warn.values())),
           "FAILED": ";".join(f"{k}:{','.join(v)}" for k, v in fail.items()) or "none",
           "WARNED": ";".join(f"{k}:{','.join(v)}" for k, v in warn.items()) or "none",
           "NEFF_SIG": round(neff["SIG"], 1), "NEFF_BKG": round(neff["BKG"], 1), "NEG_WEIGHT_FRAC": round(negf, 4),
           "TOP_SINGLE_AUC": f"{top[0]}:{top[1]}", "STATUS": "FAIL" if fail else "PASS"}
    if a.json:
        with open(a.json, "w") as f:
            json.dump({"summary": res, "fail": fail, "warn": warn, "features": det}, f, indent=1)
    print("\n".join(f"{k}={v}" for k, v in res.items()))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
