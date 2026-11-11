#!/usr/bin/env python3
"""Copy the first N jets (selected branches only) of a jet ntuple into a small local ROOT file.

weaver expands its --data-train/--data-test arguments with glob.glob, so it
cannot read root:// URLs; and the Open Data Hbb ntuples are 1.2 GB per file.
This writes a local, branch-reduced subset that weaver (or anything else) can read:

    make_jet_subset.py root://eospublic.cern.ch//eos/opendata/cms/datascience/HiggsToBBNtupleProducerTool/\
HiggsToBBNTuple_HiggsToBB_QCD_RunII_13TeV_MC/train/ntuple_merged_10.root \
        -o <scratch>/train_10.root --entries 50000

By default it keeps the fj_* jet variables used for labels/observers, event_no
and every pfcand_* and sv_* branch. Jagged branches are written as
variable-length branches with uproot (counter branch n<name>).

Stdout: KEY=VALUE (N_JETS, N_BRANCHES, OUTPUT, SIZE_MB). Diagnostics on stderr.
Exit codes: 0 ok, 1 no branch matched, 2 bad input (cannot open, output exists
without --force). --dry-run prints what would be written and writes nothing.
Needs uproot >= 5, awkward >= 2 (the LCG_109 view has both).
"""
from __future__ import annotations

import argparse
import fnmatch
import os
import sys

DEFAULT_BRANCHES = [
    "event_no", "fj_pt", "fj_eta", "fj_phi", "fj_sdmass", "fj_isH", "fj_isQCD",
    "label_H_bb", "sample_isQCD", "n_pfcands", "pfcand_*", "n_sv", "sv_*",
]


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    p.add_argument("input", help="input ROOT file (local path or root:// URL)")
    p.add_argument("-o", "--output", required=True, help="output ROOT file (local)")
    p.add_argument("--tree", default="deepntuplizer/tree", help="input tree path (default: %(default)s)")
    p.add_argument("--out-tree", default=None, help="output tree name (default: same as --tree)")
    p.add_argument("--entries", type=int, default=50000, help="number of jets to copy (default: %(default)s)")
    p.add_argument("--start", type=int, default=0, help="first entry (default: 0)")
    p.add_argument("--branches", nargs="+", default=DEFAULT_BRANCHES,
                   help="branch names or glob patterns (default: labels, observers, pfcand_*, sv_*)")
    p.add_argument("--force", action="store_true", help="overwrite the output")
    p.add_argument("--dry-run", action="store_true", help="list the branches and exit")
    a = p.parse_args()

    import uproot

    try:
        tree = uproot.open(a.input)[a.tree]
    except Exception as e:  # noqa: BLE001 - report any open error as bad input
        print(f"error: cannot open {a.input}:{a.tree}: {e}", file=sys.stderr)
        return 2
    keys = tree.keys()
    names = [k for k in keys if any(fnmatch.fnmatchcase(k, pat) for pat in a.branches)]
    if not names:
        print(f"error: no branch matches {a.branches}", file=sys.stderr)
        return 1
    stop = min(a.start + a.entries, tree.num_entries)
    print(f"# {len(names)} branches, entries [{a.start}, {stop}) of {tree.num_entries}", file=sys.stderr)
    if a.dry_run:
        print("\n".join(names), file=sys.stderr)
        print(f"N_JETS={stop - a.start}\nN_BRANCHES={len(names)}\nOUTPUT={a.output}\nDRY_RUN=1")
        return 0
    if os.path.exists(a.output) and not a.force:
        print(f"error: {a.output} exists (use --force)", file=sys.stderr)
        return 2

    arrays = tree.arrays(names, entry_start=a.start, entry_stop=stop)
    out_tree = a.out_tree or a.tree
    with uproot.recreate(a.output) as f:
        # a dict of top-level arrays: uproot writes jagged ones with a counter branch
        f[out_tree] = {n: arrays[n] for n in names}
    size = os.path.getsize(a.output) / 1e6
    print(f"N_JETS={len(arrays)}\nN_BRANCHES={len(names)}\nOUTPUT={a.output}\nSIZE_MB={size:.1f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
