#!/usr/bin/env python3
"""Turn NanoAOD (or any flat/jagged ROOT tree) samples into one flat Parquet training table.

    nano_to_table.py --features <skill>/assets/features_dijet.py --lumi 16400 \
        --sample zp2000:1:1.0:root://.../a.root --sample qcd1000:0:1117:root://.../b.root,root://.../c.root \
        --max-events 20000 -o table.parquet

--sample NAME:LABEL:XSEC_PB:FILE[,FILE...]  LABEL 1 = signal, 0 = background. XSEC_PB "data"
makes a data sample (label -1, weight 1). File URLs may contain ':' (root://). Repeat per sample,
or give --samples samples.json: [{"name":..,"label":..,"xsec_pb":..,"files":[..]}, ...].

Columns written: the features and obs_* observers from the feature module, plus
  label, sample, event, gen_weight, fold (= event % --n-folds: the ONLY allowed split key) and
  weight = xsec_pb * lumi * genWeight / sum(genWeight over all events read of that sample),
  which keeps the sign of genWeight. With --max-events the sum runs over the events read, so
  the normalisation stays correct for partial files.
Also writes <output>.meta.json (features, observers, per-sample counts and sum of weights,
package versions, the command).

Stdout KEY=VALUE: N_ROWS N_SIG N_BKG N_DATA N_FEATURES NEG_WEIGHT_FRAC OUTPUT [DRY_RUN].
Diagnostics on stderr. Exit codes: 0 ok, 1 a sample has no selected events, 2 bad arguments
or unreadable input. --dry-run reads the first 1000 events per file and writes nothing.
"""
from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys


def log(m):
    print(m, file=sys.stderr, flush=True)


def parse_sample(s):
    parts = s.split(":", 3)
    if len(parts) != 4:
        raise ValueError(f"--sample needs NAME:LABEL:XSEC_PB:FILES, got {s!r}")
    name, label, xsec, files = parts
    data = xsec == "data"
    return {"name": name, "label": -1 if data else int(label), "xsec_pb": None if data else float(xsec),
            "files": [f for f in files.split(",") if f]}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--sample", action="append", default=[], help="NAME:LABEL:XSEC_PB:FILE[,FILE...] (repeatable)")
    p.add_argument("--samples", help="JSON file with the sample list instead of --sample")
    p.add_argument("--features", required=True, help="feature module (.py) with BRANCHES and build(ev)")
    p.add_argument("--tree", default="Events")
    p.add_argument("--event-branch", default="event", help="event-number branch (default: %(default)s)")
    p.add_argument("--weight-branch", default="genWeight", help="generator weight branch; '' for none")
    p.add_argument("--lumi", type=float, default=1.0, help="integrated luminosity in pb^-1 (default: 1)")
    p.add_argument("--max-events", type=int, default=None, help="events to read per file (default: all)")
    p.add_argument("--n-folds", type=int, default=5, help="fold = event %% n (default: %(default)s)")
    p.add_argument("--step", default="200 MB", help="uproot chunk size (default: %(default)s)")
    p.add_argument("-o", "--output", required=True, help="output .parquet")
    p.add_argument("--force", action="store_true", help="overwrite the output")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()

    try:
        samples = json.load(open(a.samples)) if a.samples else [parse_sample(s) for s in a.sample]
        for s in samples:
            s.setdefault("label", -1 if s.get("xsec_pb") is None else None)
        if not samples or any(not s["files"] for s in samples):
            raise ValueError("no samples or a sample without files")
        spec = importlib.util.spec_from_file_location("features", a.features)
        fm = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(fm)
    except Exception as e:  # noqa: BLE001
        log(f"error: {type(e).__name__}: {e}")
        return 2
    if os.path.exists(a.output) and not (a.force or a.dry_run):
        log(f"error: {a.output} exists (use --force)")
        return 2

    import awkward as ak
    import numpy as np
    import pandas as pd
    import uproot

    stop = 1000 if a.dry_run else a.max_events
    frames, meta = [], []
    for s in samples:
        is_data = s.get("xsec_pb") is None
        branches = list(fm.BRANCHES) + [a.event_branch]
        if a.weight_branch and not is_data:
            branches.append(a.weight_branch)
        cols, sumw, nread = [], 0.0, 0
        for path in s["files"]:
            try:
                tree = uproot.open(path, timeout=300)[a.tree]
                for ev in tree.iterate(branches, entry_stop=stop, step_size=a.step):
                    gw = np.ones(len(ev)) if (is_data or not a.weight_branch) else ak.to_numpy(ev[a.weight_branch])
                    sumw += float(gw.sum())
                    nread += len(ev)
                    d = fm.build(ev)
                    m = d.pop("_mask")
                    d["event"] = ak.to_numpy(ev[a.event_branch])[m].astype(np.uint64)
                    d["gen_weight"] = gw[m].astype(np.float32)
                    cols.append(pd.DataFrame(d))
            except Exception as e:  # noqa: BLE001
                log(f"error: {path}: {type(e).__name__}: {e}")
                return 2
        df = pd.concat(cols, ignore_index=True)
        if len(df) == 0:
            log(f"error: sample {s['name']}: no event passes the selection ({nread} read)")
            return 1
        df["weight"] = 1.0 if is_data else df["gen_weight"].astype(np.float64) * s["xsec_pb"] * a.lumi / sumw
        df["label"] = np.int8(s["label"])
        df["sample"] = s["name"]
        frames.append(df)
        meta.append({"name": s["name"], "label": s["label"], "xsec_pb": s.get("xsec_pb"), "files": s["files"],
                     "n_read": nread, "sum_gen_weight": sumw, "n_selected": len(df),
                     "sum_weight": float(df["weight"].sum())})
        log(f"# {s['name']}: read {nread}, selected {len(df)}, sum(weight) {df['weight'].sum():.4g}")

    t = pd.concat(frames, ignore_index=True)
    t["fold"] = (t["event"] % np.uint64(a.n_folds)).astype(np.int8)
    reserved = {"label", "sample", "event", "gen_weight", "weight", "fold"}
    feats = [c for c in t.columns if c not in reserved and not c.startswith("obs_")]
    mc = t[t.label >= 0]
    neg = float((mc.weight < 0).mean()) if len(mc) else 0.0
    out = {"N_ROWS": len(t), "N_SIG": int((t.label == 1).sum()), "N_BKG": int((t.label == 0).sum()),
           "N_DATA": int((t.label == -1).sum()), "N_FEATURES": len(feats), "NEG_WEIGHT_FRAC": round(neg, 4),
           "OUTPUT": a.output}
    if a.dry_run:
        out["DRY_RUN"] = 1
    else:
        os.makedirs(os.path.dirname(os.path.abspath(a.output)), exist_ok=True)
        t.to_parquet(a.output, index=False)
        with open(a.output + ".meta.json", "w") as f:
            json.dump({"features": feats, "observers": [c for c in t.columns if c.startswith("obs_")],
                       "n_folds": a.n_folds, "lumi_pb": a.lumi, "samples": meta,
                       "versions": {"uproot": uproot.__version__, "awkward": ak.__version__,
                                    "numpy": np.__version__, "pandas": pd.__version__},
                       "command": " ".join(sys.argv)}, f, indent=1)
    print("\n".join(f"{k}={v}" for k, v in out.items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
