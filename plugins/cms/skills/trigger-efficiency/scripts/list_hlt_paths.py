#!/usr/bin/env python3
"""List the HLT paths stored in NanoAOD files, with how often each one fired.

Use it before choosing signal and reference triggers: path names and
thresholds change between menus (even within one year), and a path can be
present as a branch but never fire in part of the data.

Usage examples:
  list_hlt_paths.py root://eospublic.cern.ch//eos/opendata/cms/Run2016H/JetHT/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/130000/0290F73B-A51C-A441-AEC1-8429F9CC8AA8.root
  list_hlt_paths.py f1.root f2.root --match 'PFJet|PFHT' --entries 200000
  list_hlt_paths.py f.root --match AK8 --json

Stdout: a "# files=<n> events=<n> match=<regex>" header, then one line per path,
"<fraction> <n_fired> <path>", sorted by name, where the fraction is over the
events of the files that HAVE the path; paths absent from some files get
"(absent in k/n files)" appended. With --json: one JSON object instead.
Diagnostics on stderr.
Exit codes: 0 ok, 1 no HLT branch matched, 2 a file could not be opened.
Needs uproot and numpy (e.g. the LCG view or a CMSSW python3).
"""
from __future__ import annotations

import argparse
import json
import re
import sys

import numpy as np
import uproot


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="NanoAOD files (local paths or root:// URLs)")
    ap.add_argument("--match", default="", help="regex on the path name, e.g. 'PFJet|PFHT'")
    ap.add_argument("--entries", type=int, default=100_000, help="events read per file (default 100000; 0 = all)")
    ap.add_argument("--json", action="store_true", help="print one JSON object instead of text lines")
    a = ap.parse_args()

    pat = re.compile(a.match)
    fired: dict[str, int] = {}
    seen: dict[str, int] = {}       # events in the files that have the path
    nfiles: dict[str, int] = {}
    total = 0
    nread = 0
    for f in a.files:
        try:
            tree = uproot.open(f)["Events"]
        except Exception as e:  # noqa: BLE001 - report any open failure the same way
            print(f"error: cannot open {f}: {e}", file=sys.stderr)
            return 2
        names = [k for k in tree.keys() if k.startswith("HLT_") and pat.search(k[4:])]
        nread += 1
        if not names:
            continue
        stop = None if a.entries == 0 else a.entries
        arrays = tree.arrays(names, entry_stop=stop, library="np")
        n = len(arrays[names[0]])
        total += n
        for k in names:
            fired[k] = fired.get(k, 0) + int(np.count_nonzero(arrays[k]))
            seen[k] = seen.get(k, 0) + n
            nfiles[k] = nfiles.get(k, 0) + 1
        print(f"{f}: {n} events, {len(names)} paths", file=sys.stderr)

    if not fired:
        print("error: no HLT_ branch matched", file=sys.stderr)
        return 1
    if a.json:
        print(json.dumps({"files": nread, "events": total,
                          "paths": {k: {"fired": fired[k], "events": seen[k], "files": nfiles[k]}
                                    for k in sorted(fired)}}))
    else:
        print(f"# files={nread} events={total} match={a.match!r}")
        for k in sorted(fired):
            note = f"  (absent in {nread - nfiles[k]}/{nread} files)" if nfiles[k] < nread else ""
            print(f"{fired[k] / seen[k]:.5f} {fired[k]:>8d} {k}{note}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
