#!/usr/bin/env python3
"""How often HLT_IsoMu22 is active in the data files, and where bit-2 objects at 22-24 GeV come from.

Usage: isomu22_check.py -o out.json <tag>=<file> ...   (tags starting with "mc" are simulation)
Per file: P(IsoMu22 | IsoMu24), P(IsoMu22 | IsoMu24 or IsoTkMu24), P(IsoMu22_eta2p1 | IsoMu24); per lumi
section (data, LS with >= 5 IsoMu24 events) the fraction of LS where IsoMu22 fired in > 95%, < 5% or in between
(between = a real random prescale, the extremes = the path switched on or off per LS); and for events with a
muon TrigObj with filter bit 2 at 22 <= pT < 24 GeV and none at >= 24 GeV, the fraction that fired IsoMu22.
"""
from __future__ import annotations

import argparse
import json

import awkward as ak
import numpy as np
import uproot

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("files", nargs="+")
ap.add_argument("-o", "--out", required=True)
a = ap.parse_args()

res = {}
for spec in a.files:
    tag, path = spec.split("=", 1)
    is_mc = tag.startswith("mc")
    br = ["HLT_IsoMu24", "HLT_IsoTkMu24", "HLT_IsoMu22", "HLT_IsoMu22_eta2p1", "TrigObj_id", "TrigObj_pt", "TrigObj_filterBits"]
    if not is_mc:
        br += ["run", "luminosityBlock"]
    ev = uproot.open(f"{path}:Events").arrays(br)
    m24 = ak.to_numpy(ev.HLT_IsoMu24)
    m22 = ak.to_numpy(ev.HLT_IsoMu22)
    either = m24 | ak.to_numpy(ev.HLT_IsoTkMu24)
    r = dict(n_events=len(ev), p_isomu22_given_isomu24=float(m22[m24].mean()),
             p_isomu22_given_isomu24_or_isotkmu24=float(m22[either].mean()),
             p_isomu22eta2p1_given_isomu24=float(ak.to_numpy(ev.HLT_IsoMu22_eta2p1)[m24].mean()))
    mu2 = (ev.TrigObj_id == 13) & ((ev.TrigObj_filterBits & 2) != 0)
    low = ak.to_numpy(ak.any(mu2 & (ev.TrigObj_pt >= 22) & (ev.TrigObj_pt < 24), axis=1))
    high = ak.to_numpy(ak.any(mu2 & (ev.TrigObj_pt >= 24), axis=1))
    only_low = low & ~high
    r["n_events_bit2_22to24_only"] = int(only_low.sum())
    r["p_isomu22_given_bit2_22to24_only"] = float(m22[only_low].mean()) if only_low.any() else None
    if not is_mc:
        run, ls = ak.to_numpy(ev.run), ak.to_numpy(ev.luminosityBlock)
        key = run.astype(np.int64) * 100000 + ls
        k24 = key[m24]
        uniq, inv, cnt = np.unique(k24, return_inverse=True, return_counts=True)
        frac = np.bincount(inv, weights=m22[m24].astype(float)) / cnt
        use = cnt >= 5
        r.update(n_lumisections=int(use.sum()), frac_ls_on=float((frac[use] > 0.95).mean()),
                 frac_ls_off=float((frac[use] < 0.05).mean()),
                 frac_ls_between=float(((frac[use] >= 0.05) & (frac[use] <= 0.95)).mean()),
                 runs=sorted(int(x) for x in np.unique(run)))
    res[tag] = r
    print(tag, json.dumps({k: (round(v, 4) if isinstance(v, float) else v) for k, v in r.items() if k != "runs"}))
with open(a.out, "w") as f:
    json.dump(res, f, indent=1)
