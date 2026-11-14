#!/usr/bin/env python3
"""Turn the per-jet table of nano_to_table.py + features_qgl.py into labelled quark/gluon tables.

    make_jet_table.py raw.parquet --out table.parquet [--out-q15 table_q15.parquet] --json composition.json

Selection: obs_genjet_matched == 1. Label: quark (1) = |partonFlavour| in {1,2,3}, gluon (0) = 21;
other jets dropped (counted). --out-q15 also writes the cross-check table with quark = {1..5}.
The truth columns obs_parton_flavour and obs_genjet_matched are dropped from the outputs.
Composition (raw counts and weighted fractions, before the label cut) goes to --json.

Stdout KEY=VALUE: N_RAW N_UNMATCHED N_UDS N_C N_B N_G N_UNDEF N_OTHER N_QUARK N_GLUON
N_QUARK_Q15 OUTPUT. Exit 0 ok, 1 fewer than --min-per-class jets of a class, 2 bad input.
"""
import argparse
import json
import sys

import numpy as np


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("raw")
    p.add_argument("--out", required=True)
    p.add_argument("--out-q15")
    p.add_argument("--json", required=True)
    p.add_argument("--min-per-class", type=int, default=0)
    a = p.parse_args()
    try:
        import pandas as pd

        t = pd.read_parquet(a.raw)
        fl = np.abs(t["obs_parton_flavour"].to_numpy()).astype(int)
        matched = t["obs_genjet_matched"].to_numpy() > 0.5
        w = t["weight"].to_numpy()
    except Exception as e:  # noqa: BLE001
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    groups = {"uds": np.isin(fl, [1, 2, 3]), "c": fl == 4, "b": fl == 5, "g": fl == 21, "undef": fl == 0}
    groups["other"] = ~np.any(list(groups.values()), axis=0)
    comp = {"n_raw": int(len(t)), "n_unmatched": int((~matched).sum()),
            "unmatched_weighted_frac": float(w[~matched].sum() / w.sum()), "matched": {}}
    wm = w[matched].sum()
    for k, m in groups.items():
        mm = m & matched
        comp["matched"][k] = {"n": int(mm.sum()), "weighted_frac": float(w[mm].sum() / wm)}
    # per-sample composition
    comp["per_sample"] = {}
    for s, g in t.groupby("sample"):
        f2 = np.abs(g["obs_parton_flavour"].to_numpy()).astype(int)
        m2 = g["obs_genjet_matched"].to_numpy() > 0.5
        comp["per_sample"][s] = {k: int((m2 & np.isin(f2, v)).sum()) for k, v in
                                 (("uds", [1, 2, 3]), ("c", [4]), ("b", [5]), ("g", [21]), ("undef", [0]))}
        comp["per_sample"][s]["unmatched"] = int((~m2).sum())
    drop = ["obs_parton_flavour", "obs_genjet_matched"]
    out = {}
    for path, qset, key in ((a.out, [1, 2, 3], "N_QUARK"), (a.out_q15, [1, 2, 3, 4, 5], "N_QUARK_Q15")):
        if not path:
            continue
        q, g = matched & np.isin(fl, qset), matched & (fl == 21)
        tt = t[q | g].drop(columns=drop).copy()
        tt["label"] = q[q | g].astype(np.int8)
        tt = tt.reset_index(drop=True)
        tt.to_parquet(path, index=False)
        out[key] = int(q.sum())
        if key == "N_QUARK":
            out["N_GLUON"] = int(g.sum())
    comp["label_definition"] = {"quark": "|partonFlavour| in {1,2,3}", "gluon": "partonFlavour == 21",
                                "quark_q15": "|partonFlavour| in {1..5}", "selection": "genJetIdx >= 0"}
    comp.update(out)
    with open(a.json, "w") as f:
        json.dump(comp, f, indent=1)
    res = {"N_RAW": len(t), "N_UNMATCHED": comp["n_unmatched"],
           **{f"N_{k.upper()}": v["n"] for k, v in comp["matched"].items()}, **out, "OUTPUT": a.out}
    print("\n".join(f"{k}={v}" for k, v in res.items()))
    return 1 if min(out.get("N_QUARK", 0), out.get("N_GLUON", 0)) < a.min_per_class else 0


if __name__ == "__main__":
    sys.exit(main())
