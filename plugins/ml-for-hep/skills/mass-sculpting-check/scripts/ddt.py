#!/usr/bin/env python3
"""Decorrelate a score from the mass after training: a DDT-style quantile map.

    ddt.py scores.parquet --mass obs_mjj --bkg-eff 0.1 -o scores_ddt.parquet
        [--fit-split train] [--bins 20] [--score score] [--label label] [--weight weight]

In --bins quantile bins of the mass, find the score threshold that keeps --bkg-eff of the
background, interpolate it linearly in the mass (constant outside the range), and write
score_ddt = score - threshold(mass). The cut score_ddt > 0 then has background efficiency
--bkg-eff at every mass. The map is fitted on background rows of --fit-split (default
"train": never fit it on the rows you test the sculpting on) and applied to every row.
A map is valid for ONE working point; make one per working point (-o and --column).
Writes the Parquet with the new column and <output>.map.json (mass points, thresholds).

Stdout KEY=VALUE: N_FIT BKG_EFF COLUMN THR_MIN THR_MAX OUTPUT. Exit codes: 0 ok, 1 fewer
than 50 background fit events per mass bin, 2 bad input. --dry-run fits and writes nothing.
"""
from __future__ import annotations

import argparse
import json
import sys

import numpy as np


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("scores")
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--mass", required=True)
    p.add_argument("--bkg-eff", type=float, required=True)
    p.add_argument("--bins", type=int, default=20)
    p.add_argument("--score", default="score")
    p.add_argument("--column", default="score_ddt", help="name of the new column")
    p.add_argument("--label", default="label")
    p.add_argument("--weight", default="weight")
    p.add_argument("--split", default="split")
    p.add_argument("--fit-split", default="train")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    try:
        import pandas as pd

        t = pd.read_parquet(a.scores)
        fit = t[(t[a.label] == 0) & ((t[a.split] == a.fit_split) if a.split in t else True)]
        s, m = fit[a.score].to_numpy(float), fit[a.mass].to_numpy(float)
        w = np.abs(fit[a.weight].to_numpy(float)) if a.weight in fit else np.ones(len(fit))
        if not 0 < a.bkg_eff < 1 or len(fit) == 0:
            raise ValueError("need 0 < --bkg-eff < 1 and background rows in the fit split")
    except Exception as e:  # noqa: BLE001
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    if len(fit) < 50 * a.bins:
        print(f"error: {len(fit)} fit events for {a.bins} bins (< 50 per bin); lower --bins", file=sys.stderr)
        return 1
    edges = np.quantile(m, np.linspace(0, 1, a.bins + 1))
    xs, thr = [], []
    for lo, hi in zip(edges[:-1], edges[1:]):
        k = (m >= lo) & (m <= hi)
        o = np.argsort(-s[k])
        c = np.cumsum(w[k][o]) / w[k].sum()
        thr.append(float(s[k][o][min(int(np.searchsorted(c, a.bkg_eff)), k.sum() - 1)]))
        xs.append(float(np.average(m[k], weights=w[k])))
    res = {"N_FIT": len(fit), "BKG_EFF": a.bkg_eff, "COLUMN": a.column, "THR_MIN": round(min(thr), 5),
           "THR_MAX": round(max(thr), 5), "OUTPUT": a.output}
    if a.dry_run:
        res["DRY_RUN"] = 1
    else:
        t[a.column] = (t[a.score].to_numpy(float) - np.interp(t[a.mass].to_numpy(float), xs, thr)).astype(np.float32)
        t.to_parquet(a.output, index=False)
        with open(a.output + ".map.json", "w") as f:
            json.dump({"mass": xs, "threshold": thr, "bkg_eff": a.bkg_eff, "score": a.score, "mass_column": a.mass,
                       "fit_split": a.fit_split}, f, indent=1)
    print("\n".join(f"{k}={v}" for k, v in res.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
