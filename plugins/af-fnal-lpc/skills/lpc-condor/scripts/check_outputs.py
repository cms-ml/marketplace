#!/usr/bin/env python3
"""Check which condor jobs produced their output on EOS and write a resubmit list.

Usage:
  check_outputs.py --jobs jobs.txt --outdir root://cmseos.fnal.gov//store/user/<you>/<area> \
                   --pattern 'output_{jobid}.root' [--min-bytes 1000] [--resubmit jobs_resubmit.txt]

jobs.txt lines are "<index> <inputs>" (make_filelist.py). For every index the
expected file is --pattern with {jobid} replaced. A job is OK if the file exists
and is at least --min-bytes. Missing or small jobs are written, unchanged, to the
resubmit file; submit it with the same JDL, pointing `queue ... from` at it.
When all jobs are OK, a stale resubmit file from an earlier check is removed.

Stdout: JSON summary {"total", "ok", "missing", "too_small", "resubmit"}.
Exit 0 if all OK, 2 if some jobs need resubmission, 1 on errors (e.g. listing failed).
Standard library only; needs `xrdfs`.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys


def list_dir(url: str) -> dict[str, int]:
    host, _, path = url[len("root://"):].partition("/")
    res = subprocess.run(["xrdfs", f"root://{host}", "ls", "-l", "/" + path.lstrip("/")],
                         capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"error: listing {url} failed: {res.stderr.strip()[:300]}")
    # `xrdfs ls -l` lines: <perms> <owner> <group> <size> <date> <time> <path>
    sizes = {}
    for line in res.stdout.splitlines():
        parts = line.split()
        if len(parts) >= 7 and parts[3].isdigit():
            sizes[parts[-1].rsplit("/", 1)[-1]] = int(parts[3])
    return sizes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--jobs", required=True)
    ap.add_argument("--outdir", required=True)
    ap.add_argument("--pattern", default="output_{jobid}.root")
    ap.add_argument("--min-bytes", type=int, default=1)
    ap.add_argument("--resubmit", default="jobs_resubmit.txt")
    args = ap.parse_args()
    if not args.outdir.startswith("root://"):
        sys.exit("error: --outdir must be a root:// URL, e.g. root://cmseos.fnal.gov//store/user/<you>/<area>")

    jobs = [l.rstrip("\n") for l in open(args.jobs) if l.strip()]
    sizes = list_dir(args.outdir)
    missing, small, redo = [], [], []
    for line in jobs:
        jobid = line.split(maxsplit=1)[0]
        name = args.pattern.format(jobid=jobid)
        if name not in sizes:
            missing.append(jobid); redo.append(line)
        elif sizes[name] < args.min_bytes:
            small.append(jobid); redo.append(line)
    if redo:
        with open(args.resubmit, "w") as fh:
            fh.write("\n".join(redo) + "\n")
    elif os.path.exists(args.resubmit):
        os.remove(args.resubmit)                 # stale list from an earlier failed check
    print(json.dumps({"total": len(jobs), "ok": len(jobs) - len(redo), "missing": missing,
                      "too_small": small, "resubmit": args.resubmit if redo else None}))
    return 2 if redo else 0


if __name__ == "__main__":
    sys.exit(main())
