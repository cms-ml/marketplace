#!/usr/bin/env python3
"""Payload skeleton for the lpc-condor job.sh contract.

job.sh runs:  python3 payload.py --inputs <url1,url2,...> --output output_<jobid>.<ext>
Write exactly that one file. Replace the analysis part with your own.
"""
import argparse

import awkward as ak
import numpy as np
import uproot

p = argparse.ArgumentParser()
p.add_argument("--inputs", required=True, help="comma-separated root:// URLs")
p.add_argument("--output", required=True, help="local output file name")
p.add_argument("--max-events", type=int, default=None)
a = p.parse_args()

edges = np.linspace(0, 2000, 51)
counts, n = np.zeros(len(edges) - 1), 0
for url in a.inputs.split(","):
    arr = uproot.open(url)["Events"].arrays(["Jet_pt"], entry_stop=a.max_events)
    lead = ak.to_numpy(ak.fill_none(ak.firsts(arr.Jet_pt), 0.0))
    counts += np.histogram(lead, bins=edges)[0]
    n += len(arr)

with uproot.recreate(a.output) as f:          # ROOT output; merge later with hadd or in Python
    f["lead_jet_pt"] = (counts, edges)
print(f"events={n} -> {a.output}")
