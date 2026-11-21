#!/usr/bin/env python3
"""Skim and slim CMS NanoAOD with uproot: keep selected branches, apply an
event preselection and (for data) a golden-JSON lumi mask, and copy the Runs
and LuminosityBlocks trees so normalisation and luminosity stay recoverable.

Output: one ROOT file with Events (kept branches, NanoAOD naming, n<Coll>
counters), Runs (unchanged, all entries), LuminosityBlocks (lumi sections
that were read, golden-JSON filtered for data) and Cutflow (always written,
one entry per input file, so hadd keeps it like Runs):
  n_all, n_lumimask          events read; after the golden JSON (= n_all for MC)
  n_<step>                   events passing the lumi mask and every step up to <step>
  nm1_<step>                 N-1: events passing the lumi mask and every step except <step>
  w_* , wm1_<step>           the same as sums of genWeight (MC only)
  w2_*, w2m1_<step>          sums of genWeight**2, for the MC statistical uncertainty (MC only)
Steps are the --step NAME=EXPR cuts in the order given (--cut EXPR is one step
named "cut"). Sum the tree over skims with cutflow.py.

The output is written as <output>.part and renamed when the job succeeds.

stdout: KEY=VALUE summary. stderr: progress. Exit codes: 0 ok, 1 runtime
error, 2 bad arguments (unknown branch in --cut). --keep patterns that match
nothing are listed in MISSING_PATTERNS (expected for MC-only branches on data).

Examples:
  skim.py -i in.root -o out.root --keep 'Muon_*' 'HLT_IsoMu24' 'MET_*' \
      --cut 'ak.sum((Muon_pt > 26) & Muon_tightId, axis=1) >= 1' \
      --lumi-json Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt
  skim.py -i @files.txt -o out.root --keep-file keep.txt --cut 'nMuon >= 2'
  skim.py -i in.root -o out.root --keep 'Muon_*' \
      --step 'trigger=HLT_IsoMu24 | HLT_IsoTkMu24' --step 'two_muons=ak.sum(Muon_pt > 20, axis=1) >= 2'
"""
import argparse
import fnmatch
import json
import os
import re
import sys
import time

import awkward as ak
import numpy as np
import uproot

ALWAYS_KEEP = ["run", "luminosityBlock", "event"]
MC_KEEP = ["genWeight"]


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def expand_inputs(items):
    out = []
    for it in items:
        if it.startswith("@"):
            with open(it[1:]) as f:
                out += [l.strip() for l in f if l.strip() and not l.startswith("#")]
        else:
            out.append(it)
    return out


def read_patterns(pats, files):
    out = list(pats or [])
    for fn in files or []:
        with open(fn) as f:
            out += [l.split("#")[0].strip() for l in f]
    return [p for p in out if p]


def select_branches(all_names, keep, drop):
    sel = [b for b in all_names if any(fnmatch.fnmatchcase(b, p) for p in keep)]
    sel = [b for b in sel if not any(fnmatch.fnmatchcase(b, p) for p in drop)]
    return sel


class LumiMask:
    """Golden JSON {"run": [[lo, hi], ...]} -> vectorised (run, lumi) mask."""

    def __init__(self, path):
        with open(path) as f:
            js = json.load(f)
        rng = sorted((int(r), lo, hi) for r, rs in js.items() for lo, hi in rs)
        self.lo = np.array([(r << 20) | lo for r, lo, _ in rng], dtype=np.int64)
        self.hi = np.array([(r << 20) | hi for r, _, hi in rng], dtype=np.int64)

    def __call__(self, run, lumi):
        key = (np.asarray(run, np.int64) << 20) | np.asarray(lumi, np.int64)
        idx = np.searchsorted(self.lo, key, side="right") - 1
        ok = idx >= 0
        ok[ok] = key[ok] <= self.hi[idx[ok]]
        return ok


def to_writable(arrays, names, counters):
    """Group NanoAOD branches into records so uproot writes n<Coll> counters."""
    out, groups = {}, {}
    jagged = {b for b in names if arrays[b].ndim > 1}
    # uproot writes the n<Coll> counter itself: writing the input one too would clash
    regenerated = {"n" + b for b in jagged} | {"n" + b.split("_", 1)[0] for b in jagged}
    for b in names:
        if b in counters and b in regenerated:
            continue
        coll = b.split("_", 1)[0]
        if "_" in b and ("n" + coll) in counters and arrays[b].ndim > 1:
            groups.setdefault(coll, {})[b.split("_", 1)[1]] = arrays[b]
        else:
            out[b] = arrays[b]
    for coll, fields in groups.items():
        if coll in out:  # e.g. LHEPdfWeight plus LHEPdfWeight_x: keep flat names
            for k, v in fields.items():
                out[f"{coll}_{k}"] = v
        else:
            out[coll] = ak.zip(fields)
    return out


def write_chunk(fout, name, data):
    if name in fout:
        fout[name].extend(data)
    else:
        fout[name] = data


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("-i", "--input", nargs="+", required=True, help="files or root:// URLs; @list.txt reads a file list")
    p.add_argument("-o", "--output", required=True, help="output ROOT file (local path; copy to EOS afterwards)")
    p.add_argument("--keep", nargs="*", default=[], help="branch glob patterns to keep (default: all)")
    p.add_argument("--keep-file", nargs="*", help="files with one glob pattern per line (# comments)")
    p.add_argument("--drop", nargs="*", default=[], help="branch glob patterns to drop after --keep")
    p.add_argument("--cut", help="event selection: Python expression over branch names, ak and np (one step named 'cut')")
    p.add_argument("--step", action="append", default=[], metavar="NAME=EXPR",
                   help="named selection step, repeatable, applied in order; all steps (and --cut) are ANDed "
                        "and recorded in the Cutflow tree with sequential and N-1 counts")
    p.add_argument("--lumi-json", help="golden JSON; applied only to data (files without genWeight)")
    p.add_argument("--step-size", default="100 MB", help="uproot iterate step size (default 100 MB)")
    p.add_argument("--max-events", type=int, help="stop after this many input events per file (tests only)")
    p.add_argument("--dry-run", action="store_true", help="list kept branches and cut inputs, write nothing")
    a = p.parse_args()

    files = expand_inputs(a.input)
    keep = read_patterns(a.keep, a.keep_file) or ["*"]

    with uproot.open(files[0]) as f0:
        names = f0["Events"].keys()
    is_mc = "genWeight" in names
    counters = {b for b in names if b.startswith("n")}
    kept = select_branches(names, keep, a.drop)
    for b in ALWAYS_KEEP + (MC_KEEP if is_mc else []):
        if b not in kept:
            kept.append(b)
    missing = [pt for pt in keep if not any(fnmatch.fnmatchcase(b, pt) for b in names)]
    if missing:  # normal for MC-only branches in a list shared with data; fatal for typos
        log(f"WARNING: --keep patterns match no branch: {missing}")
    steps = []  # [(name, expr)] in cutflow order
    for st in a.step:
        name, sep, expr = st.partition("=")
        name = name.strip()
        if not sep or not expr.strip() or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name):
            log(f"ERROR: --step must be NAME=EXPR with NAME a plain identifier, got {st!r}")
            return 2
        steps.append((name, expr))
    if a.cut:
        steps.append(("cut", a.cut))
    step_names = [n for n, _ in steps]
    if len(set(step_names)) != len(step_names) or {"all", "lumimask"} & set(step_names):
        log(f"ERROR: step names must be unique and not 'all' or 'lumimask': {step_names}")
        return 2
    cut_inputs = []
    if steps:
        text = " ".join(e for _, e in steps)
        idents = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text)) - {"ak", "np", "axis", "True", "False", "None"}
        cut_inputs = sorted(i for i in idents if i in names)
        unknown = sorted(i for i in idents if i not in names and not hasattr(ak, i) and not hasattr(np, i))
        if unknown:
            log(f"ERROR: names in --cut/--step are not branches: {unknown}")
            return 2
    to_read = sorted(set(kept) | set(cut_inputs))

    log(f"files={len(files)} is_mc={is_mc} kept_branches={len(kept)} of {len(names)} cut_inputs={cut_inputs}")
    if a.dry_run:
        print("\n".join(f"KEEP={b}" for b in kept))
        print(f"IS_MC={int(is_mc)}\nN_KEPT={len(kept)}\nN_BRANCHES={len(names)}")
        print(f"STEPS={','.join(step_names)}")
        print(f"MISSING_PATTERNS={','.join(missing)}")
        return 0

    mask_fn = LumiMask(a.lumi_json) if (a.lumi_json and not is_mc) else None
    if a.lumi_json and is_mc:
        log("note: --lumi-json ignored for MC")

    n_in = n_lumi = n_out = 0
    sumw_read = sumw_out = 0.0
    k = len(steps)
    tot_n = np.zeros(2 + 2 * k, np.int64)  # all, lumimask, n_<step>..., nm1_<step>...
    tot_w = np.zeros(2 + 2 * k, np.float64)
    tot_w2 = np.zeros(2 + 2 * k, np.float64)
    t0 = time.time()
    tmp = a.output + ".part"  # renamed only on success, so a failed job leaves no <output>
    any_partial = False
    with uproot.recreate(tmp) as fout:
        for fn in files:
            with uproot.open(fn) as fin:
                ev = fin["Events"]
                absent = sorted(set(to_read) - set(ev.keys()))
                if absent:
                    log(f"ERROR: {fn} lacks branches {absent} that {files[0]} has; skim files of one "
                        "campaign/era together, or drop these from --keep")
                    os.remove(tmp)
                    return 1
                stop = min(a.max_events, ev.num_entries) if a.max_events else None
                partial = stop is not None and stop < ev.num_entries
                any_partial |= partial
                seen = set()
                cf_n = np.zeros(2 + 2 * k, np.int64)  # this input file's Cutflow entry
                cf_w = np.zeros(2 + 2 * k, np.float64)
                cf_w2 = np.zeros(2 + 2 * k, np.float64)
                for arr in ev.iterate(to_read, step_size=a.step_size, entry_stop=stop, library="ak"):
                    n = len(arr)
                    n_in += n
                    sel = np.ones(n, bool)
                    if is_mc:
                        sumw_read += float(np.sum(ak.to_numpy(arr["genWeight"]), dtype=np.float64))
                    if mask_fn is not None:
                        sel &= mask_fn(arr["run"], arr["luminosityBlock"])
                    n_lumi += int(sel.sum())
                    if partial:
                        seen.update(np.unique((ak.to_numpy(arr["run"]).astype(np.int64) << 20) | ak.to_numpy(arr["luminosityBlock"])).tolist())
                    gw = ak.to_numpy(arr["genWeight"]).astype(np.float64) if is_mc else np.ones(n)
                    rows = [np.ones(n, bool), sel.copy()]
                    if steps:
                        ns = {b: arr[b] for b in cut_inputs}
                        ns.update(ak=ak, np=np)
                        passes = []
                        for _, expr in steps:
                            c = np.asarray(ak.fill_none(eval(expr, {"__builtins__": {}}, ns), False), bool)
                            passes.append(np.broadcast_to(c, (n,)))
                        nfail = np.sum([~q for q in passes], axis=0)
                        cum = sel.copy()
                        for q in passes:
                            cum &= q
                            rows.append(cum.copy())
                        for q in passes:  # N-1: every other step passes; this one may fail
                            rows.append(sel & ((nfail == 0) | ((nfail == 1) & ~q)))
                        sel = cum
                    for j, r in enumerate(rows):
                        cf_n[j] += int(r.sum())
                        cf_w[j] += float(gw[r].sum())
                        cf_w2[j] += float((gw[r] ** 2).sum())
                    out = arr[sel]
                    n_out += len(out)
                    if is_mc:
                        sumw_out += float(np.sum(ak.to_numpy(out["genWeight"]), dtype=np.float64))
                    if len(out):
                        write_chunk(fout, "Events", to_writable(out, kept, counters))
                    log(f"  {fn.rsplit('/', 1)[-1]}: read {n_in} pass {n_out} ({time.time() - t0:.0f}s)")
                cf = {"n_all": cf_n[:1], "n_lumimask": cf_n[1:2]}
                cf.update({f"n_{s}": cf_n[2 + j:3 + j] for j, s in enumerate(step_names)})
                cf.update({f"nm1_{s}": cf_n[2 + k + j:3 + k + j] for j, s in enumerate(step_names)})
                if is_mc:
                    cf.update({"w_all": cf_w[:1], "w_lumimask": cf_w[1:2]})
                    cf.update({f"w_{s}": cf_w[2 + j:3 + j] for j, s in enumerate(step_names)})
                    cf.update({f"wm1_{s}": cf_w[2 + k + j:3 + k + j] for j, s in enumerate(step_names)})
                    cf.update({"w2_all": cf_w2[:1], "w2_lumimask": cf_w2[1:2]})
                    cf.update({f"w2_{s}": cf_w2[2 + j:3 + j] for j, s in enumerate(step_names)})
                    cf.update({f"w2m1_{s}": cf_w2[2 + k + j:3 + k + j] for j, s in enumerate(step_names)})
                write_chunk(fout, "Cutflow", cf)
                tot_n += cf_n
                tot_w += cf_w
                tot_w2 += cf_w2
                runs = fin["Runs"].arrays(library="ak")
                rnames = [b for b in runs.fields if not (b.startswith("n") and b[1:] in runs.fields)]
                write_chunk(fout, "Runs", {b: runs[b] for b in rnames})
                lb = fin["LuminosityBlocks"].arrays(["run", "luminosityBlock"], library="ak")
                if mask_fn is not None:
                    lb = lb[mask_fn(lb["run"], lb["luminosityBlock"])]
                if partial:  # only lumi sections whose events were read (last one may be incomplete)
                    key = (ak.to_numpy(lb["run"]).astype(np.int64) << 20) | ak.to_numpy(lb["luminosityBlock"])
                    lb = lb[np.isin(key, np.fromiter(seen, np.int64))]
                if len(lb):
                    write_chunk(fout, "LuminosityBlocks", {b: lb[b] for b in lb.fields})
        if "Events" not in fout:
            log("WARNING: no event passed; Events tree not written")

    os.replace(tmp, a.output)
    print(f"OUTPUT={a.output}\nIS_MC={int(is_mc)}\nN_FILES={len(files)}")
    print(f"EVENTS_IN={n_in}\nEVENTS_AFTER_LUMIMASK={n_lumi}\nEVENTS_OUT={n_out}")
    print(f"N_KEPT_BRANCHES={len(kept)}\nPARTIAL_FILES={int(any_partial)}")
    print(f"MISSING_PATTERNS={','.join(missing)}")
    if is_mc:
        print(f"SUMW_READ={sumw_read:.10g}\nSUMW_OUT={sumw_out:.10g}")
    print(f"STEPS={','.join(step_names)}")
    for j, s in enumerate(step_names):
        print(f"CUTFLOW_{s}={tot_n[2 + j]}\nNMINUS1_{s}={tot_n[2 + k + j]}")
        if is_mc:
            print(f"CUTFLOW_W_{s}={tot_w[2 + j]:.10g}\nNMINUS1_W_{s}={tot_w[2 + k + j]:.10g}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        sys.exit(1)
    except Exception as e:  # e.g. XRootD timeout: report it, leave only <output>.part behind
        log(f"ERROR: {type(e).__name__}: {e}")
        sys.exit(1)
