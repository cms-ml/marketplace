#!/usr/bin/env python3
"""Sum MC normalisation bookkeeping from the NanoAOD Runs tree over many files
(original NanoAOD or skims made with skim.py, which copy Runs unchanged).

Prints genEventCount, genEventSumw, genEventSumw2 and the sum-of-weights for
each LHE scale / PDF variation. In NanoAOD the Runs LHEScaleSumw and
LHEPdfSumw are stored *divided by genEventSumw* of that file, so they are
combined here as sum_i(genEventSumw_i * LHE*Sumw_i) / sum_i(genEventSumw_i).
With --xsec (pb) and --lumi (/pb) it also prints the per-event weight factor
XSEC*LUMI/SUMW to multiply genWeight by.

stdout: KEY=VALUE. stderr: progress. Exit: 0 ok, 1 error, 2 no Runs info (data?).

Example:
  sumw.py -i @dy_files.txt --xsec 6077.22 --lumi 36310
"""
import argparse
import sys

import numpy as np
import uproot


def expand(items):
    out = []
    for it in items:
        if it.startswith("@"):
            out += [l.strip() for l in open(it[1:]) if l.strip() and not l.startswith("#")]
        else:
            out.append(it)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-i", "--input", nargs="+", required=True, help="files; @list.txt reads a list")
    p.add_argument("--xsec", type=float, help="cross section in pb")
    p.add_argument("--lumi", type=float, help="integrated luminosity in /pb")
    a = p.parse_args()

    tot = {"genEventCount": 0.0, "genEventSumw": 0.0, "genEventSumw2": 0.0}
    lhe = {}
    for fn in expand(a.input):
        with uproot.open(fn) as f:
            if "Runs" not in f:
                print(f"ERROR: {fn}: no Runs tree (skim made without copying it?)", file=sys.stderr)
                return 2
            r = f["Runs"].arrays(library="np")
        # NanoAOD v7 and older used a trailing underscore (genEventSumw_)
        get = lambda k: r[k] if k in r else r.get(k + "_")
        if get("genEventSumw") is None:
            print(f"ERROR: {fn}: Runs has no genEventSumw (data file?)", file=sys.stderr)
            return 2
        sw = get("genEventSumw").astype(float)
        for k in tot:
            tot[k] += float(np.sum(get(k)))
        for k in ("LHEScaleSumw", "LHEPdfSumw"):
            v = get(k)
            if v is None:
                continue
            for w, arr in zip(sw, v):
                acc = lhe.setdefault(k, np.zeros(len(arr)))
                if len(acc) != len(arr):
                    print(f"ERROR: {fn}: {k} length {len(arr)} != {len(acc)} (mixed samples?)", file=sys.stderr)
                    return 1
                acc += w * np.asarray(arr, float)
        print(f"  {fn.rsplit('/', 1)[-1]}: sumw={float(np.sum(sw)):.6g}", file=sys.stderr)

    print(f"N_FILES={len(expand(a.input))}")
    print(f"GEN_EVENT_COUNT={int(tot['genEventCount'])}")
    print(f"SUMW={tot['genEventSumw']:.10g}\nSUMW2={tot['genEventSumw2']:.10g}")
    if tot["genEventSumw2"] > 0:
        print(f"N_EFF={tot['genEventSumw'] ** 2 / tot['genEventSumw2']:.6g}")
    for k, acc in lhe.items():
        print(f"{k.upper()}_SUMW={','.join(f'{x:.10g}' for x in acc)}")
    if a.xsec is not None and a.lumi is not None:
        print(f"WEIGHT_FACTOR={a.xsec * a.lumi / tot['genEventSumw']:.6g}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
