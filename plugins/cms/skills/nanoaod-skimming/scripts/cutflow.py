#!/usr/bin/env python3
"""Sum the Cutflow tree written by skim.py over skims and print the cutflow.

The Cutflow tree has one entry per input NanoAOD file (hadd concatenates the
entries, like Runs), so summing over per-job skims or over merged skims gives
the same numbers. Every file must have the same steps.

Columns per step:
  N         events passing the lumi mask and every step up to this one
  eff       N / N of the previous row (relative efficiency)
  cum       N / n_all (cumulative efficiency)
  N-1       events passing every step except this one
  final/N-1 fraction of the N-1 events this step keeps (its efficiency with all other cuts applied)
For MC the same columns are given in sum of genWeight (W, W-1), with the
statistical uncertainty sqrt(sum genWeight**2) of W (W err) when the skim has w2_*.

stdout: the table, then KEY=VALUE: N_FILES (skim files read), N_INPUT_FILES (Cutflow
entries = original NanoAOD files they were made from), STEPS, N_ALL, N_LUMIMASK,
CUTFLOW_<step>, NMINUS1_<step>, and for MC W_ALL, CUTFLOW_W_<step>, NMINUS1_W_<step>
(and CUTFLOW_WERR_<step>, NMINUS1_WERR_<step> with w2_*).
--json writes the same numbers to a file.
Exit codes: 0 ok, 2 a file has no Cutflow tree or different steps.

Examples:
  cutflow.py -i skim_SingleMuon_2016G_*.root
  cutflow.py -i @skims.txt --json cutflow.json
"""
import argparse
import json
import sys

import numpy as np
import uproot


def expand_inputs(items):
    out = []
    for it in items:
        if it.startswith("@"):
            with open(it[1:]) as f:
                out += [l.strip() for l in f if l.strip() and not l.startswith("#")]
        else:
            out.append(it)
    return out


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-i", "--input", nargs="+", required=True, help="skim files (local or root://); @list.txt reads a list")
    p.add_argument("--json", help="also write the summed cutflow to this JSON file")
    a = p.parse_args()

    files = expand_inputs(a.input)
    keys, tot, n_entries = None, None, 0
    for fn in files:
        with uproot.open(fn) as f:
            if "Cutflow" not in f:
                print(f"ERROR: {fn} has no Cutflow tree (made with an older skim.py, or not by skim.py)", file=sys.stderr)
                return 2
            t = f["Cutflow"]
            k = list(t.keys())
            if keys is None:
                keys, tot = k, {b: 0.0 for b in k}
            elif k != keys:
                print(f"ERROR: {fn} has Cutflow branches {k}, {files[0]} has {keys}: skims made with different steps",
                      file=sys.stderr)
                return 2
            arr = t.arrays(library="np")
            for b in keys:
                tot[b] += float(np.sum(arr[b], dtype=np.float64))
            n_entries += t.num_entries

    is_mc = "w_all" in keys
    has_w2 = "w2_all" in keys  # skims from cms <= 0.6.0 have no w2_*
    steps = [b[2:] for b in keys if b.startswith("n_") and b not in ("n_all", "n_lumimask")]
    final_n = tot[f"n_{steps[-1]}"] if steps else tot["n_lumimask"]

    def frac(x, y):
        return x / y if y else float("nan")

    hdr = f"{'step':<24}{'N':>14}{'eff':>9}{'cum':>9}{'N-1':>14}{'final/N-1':>11}"
    if is_mc:
        hdr += f"{'W':>16}" + (f"{'W err':>12}" if has_w2 else "") + f"{'W-1':>16}"
    print(hdr)
    rows = [("all", tot["n_all"], None, "w_all"), ("lumimask", tot["n_lumimask"], None, "w_lumimask")]
    rows += [(s, tot[f"n_{s}"], tot[f"nm1_{s}"], f"w_{s}") for s in steps]
    prev = None
    for name, n, nm1, wk in rows:
        eff = frac(n, prev) if prev is not None else float("nan")
        line = f"{name:<24}{n:>14.0f}{eff:>9.4f}{frac(n, tot['n_all']):>9.4f}"
        line += f"{nm1:>14.0f}{frac(final_n, nm1):>11.4f}" if nm1 is not None else f"{'':>14}{'':>11}"
        if is_mc:
            line += f"{tot[wk]:>16.6g}"
            if has_w2:
                line += f"{tot['w2' + wk[1:]] ** 0.5:>12.4g}"
            line += f"{tot['wm1_' + name]:>16.6g}" if nm1 is not None else f"{'':>16}"
        print(line)
        prev = n

    print(f"N_FILES={len(files)}\nN_INPUT_FILES={n_entries}\nSTEPS={','.join(steps)}")
    print(f"N_ALL={tot['n_all']:.0f}\nN_LUMIMASK={tot['n_lumimask']:.0f}")
    for s in steps:
        print(f"CUTFLOW_{s}={tot['n_' + s]:.0f}\nNMINUS1_{s}={tot['nm1_' + s]:.0f}")
    if is_mc:
        print(f"W_ALL={tot['w_all']:.10g}")
        for s in steps:
            print(f"CUTFLOW_W_{s}={tot['w_' + s]:.10g}\nNMINUS1_W_{s}={tot['wm1_' + s]:.10g}")
            if has_w2:
                print(f"CUTFLOW_WERR_{s}={tot['w2_' + s] ** 0.5:.6g}\nNMINUS1_WERR_{s}={tot['w2m1_' + s] ** 0.5:.6g}")

    if a.json:
        out = {"n_files": len(files), "n_input_files": n_entries, "is_mc": is_mc, "steps": steps,
               "n_all": tot["n_all"], "n_lumimask": tot["n_lumimask"],
               "cutflow": {s: tot["n_" + s] for s in steps}, "nminus1": {s: tot["nm1_" + s] for s in steps}}
        if is_mc:
            out.update(w_all=tot["w_all"], w_lumimask=tot["w_lumimask"],
                       cutflow_w={s: tot["w_" + s] for s in steps}, nminus1_w={s: tot["wm1_" + s] for s in steps})
            if has_w2:
                out.update(w2_all=tot["w2_all"], cutflow_w2={s: tot["w2_" + s] for s in steps},
                           nminus1_w2={s: tot["w2m1_" + s] for s in steps})
        with open(a.json, "w") as f:
            json.dump(out, f, indent=2)
            f.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
