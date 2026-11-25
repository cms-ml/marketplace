#!/usr/bin/env python3
"""Integrated luminosity of the lumi sections in NanoAOD/skim files.

Reads (run, luminosityBlock) from each file's LuminosityBlocks tree (skim.py
already applied the golden JSON there), removes duplicates (the same lumi
section split across files), and sums the recorded luminosity from a
brilcalc --byls CSV: run:fill,ls,time,beamstatus,E,delivered,recorded,...
Open Data ships one per year, e.g.
root://eospublic.cern.ch//eos/opendata/cms/luminosity/2016/pp_2016lumibyls.csv
On lxplus make it with brilcalc lumi --byls --normtag ... --output-style csv.

--golden instead takes a golden JSON and integrates all of it (full-year lumi).
stdout: KEY=VALUE (LUMI_PB, LUMI_FB, N_LS, N_LS_MISSING). Exit: 0 ok, 1 error,
3 some lumi sections absent from the CSV (outside the normtag / not certified).
"""
import argparse
import csv
import io
import json
import subprocess
import sys

import numpy as np
import uproot


def open_text(path):
    if path.startswith("root://"):
        return io.StringIO(subprocess.run(["xrdcp", "-s", path, "-"], check=True, capture_output=True, text=True).stdout)
    return open(path)


def read_byls(path):
    unit = None
    lumi = {}
    for row in csv.reader(open_text(path)):
        if not row:
            continue
        if row[0].startswith("#"):
            hdr = ",".join(row)
            if "recorded(" in hdr:
                unit = hdr.split("recorded(")[1].split(")")[0]
            continue
        run = int(row[0].split(":")[0])
        ls = int(row[1].split(":")[0])
        lumi[(run, ls)] = float(row[6])
    scale = {"/fb": 1000.0, "/pb": 1.0, "/nb": 1e-3, "/ub": 1e-6}.get(unit)
    if scale is None:
        raise SystemExit(f"cannot parse recorded unit from CSV header (got {unit!r})")
    return lumi, scale


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("-i", "--input", nargs="+", help="NanoAOD/skim files; @list.txt reads a list")
    src.add_argument("--golden", help="golden JSON: integrate every certified lumi section")
    p.add_argument("--byls", required=True, help="brilcalc --byls CSV (local or root://)")
    a = p.parse_args()

    pairs = set()
    if a.golden:
        for r, rngs in json.load(open(a.golden)).items():
            for lo, hi in rngs:
                pairs.update((int(r), ls) for ls in range(lo, hi + 1))
    else:
        files = []
        for it in a.input:
            files += [l.strip() for l in open(it[1:]) if l.strip()] if it.startswith("@") else [it]
        for fn in files:
            with uproot.open(fn) as f:
                if "LuminosityBlocks" not in f:
                    print(f"ERROR: {fn}: no LuminosityBlocks tree", file=sys.stderr)
                    return 1
                t = f["LuminosityBlocks"].arrays(["run", "luminosityBlock"], library="np")
            pairs.update(zip(t["run"].tolist(), t["luminosityBlock"].tolist()))

    table, scale = read_byls(a.byls)
    got = [table[k] for k in pairs if k in table]
    missing = len(pairs) - len(got)
    pb = float(np.sum(got)) * scale
    print(f"N_LS={len(pairs)}\nN_LS_MISSING={missing}\nLUMI_PB={pb:.6g}\nLUMI_FB={pb / 1000:.6g}")
    if missing:
        print(f"WARNING: {missing} lumi sections not in {a.byls}", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    sys.exit(main())
