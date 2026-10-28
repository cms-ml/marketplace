#!/usr/bin/env python3
"""Build condor job input lists: one line per job, "<index> <url1,url2,...>".

Sources (pick one):
  --xrootd-dir root://HOST//path   recurse an XRootD directory (Open Data, EOS) with xrdfs
  --das /Primary/Processed/TIER    files of a DAS dataset via dasgoclient (needs a grid proxy)
  --from-file list.txt             existing list, one URL or LFN per line

Usage examples:
  make_filelist.py --xrootd-dir root://eospublic.cern.ch//eos/opendata/cms/Run2016H/JetHT/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1 \
                   --files-per-job 5 -o jobs.txt
  make_filelist.py --das /JetHT/Run2016H-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD --redirector root://cmsxrootd.fnal.gov/ -o jobs.txt
  make_filelist.py ... --max-files 10        # small test: the first 10 files in sorted path order

Output: jobs.txt for `queue jobid,inputs from jobs.txt` in the JDL. The fixed index
lets resubmitted jobs keep their number (see check_outputs.py).
Stdout: a one-line JSON summary. Diagnostics on stderr. Exit 1 if no files found.
Standard library only; needs `xrdfs` or `dasgoclient` on PATH for those sources.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys


def run(cmd: list[str]) -> list[str]:
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        sys.exit(f"error: {' '.join(cmd)} failed: {res.stderr.strip()[:300]}")
    return [l.strip() for l in res.stdout.splitlines() if l.strip()]


def split_url(url: str) -> tuple[str, str]:
    """root://host//path -> ('root://host', '/path')."""
    if not url.startswith("root://"):
        sys.exit(f"error: --xrootd-dir must start with root://, got {url}")
    rest = url[len("root://"):]
    host, _, path = rest.partition("/")
    return f"root://{host}", "/" + path.lstrip("/")


def list_xrootd(url: str, max_files: int | None) -> list[str]:
    host, top = split_url(url)
    files, stack = [], [top]
    while stack:
        d = stack.pop()
        for entry in sorted(run(["xrdfs", host, "ls", d]), reverse=True):
            if entry.endswith(".root"):
                files.append(f"{host}/{entry}")
            elif "." not in entry.rsplit("/", 1)[-1]:   # directory (no extension)
                stack.append(entry)
    return sorted(files)


def list_das(dataset: str, redirector: str) -> list[str]:
    lfns = run(["dasgoclient", "-query", f"file dataset={dataset}"])
    return [redirector.rstrip("/") + "/" + l if l.startswith("/store") else l for l in lfns]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--xrootd-dir")
    src.add_argument("--das")
    src.add_argument("--from-file")
    ap.add_argument("--redirector", default="root://cmsxrootd.fnal.gov/",
                    help="prefix for /store LFNs (default: US redirector)")
    ap.add_argument("--files-per-job", type=int, default=1)
    ap.add_argument("--max-files", type=int, help="stop after N files (for test runs)")
    ap.add_argument("-o", "--output", default="jobs.txt")
    args = ap.parse_args()

    if args.xrootd_dir:
        files = list_xrootd(args.xrootd_dir, args.max_files)
    elif args.das:
        files = list_das(args.das, args.redirector)
    else:
        files = [l.strip() for l in open(args.from_file) if l.strip() and not l.startswith("#")]
        files = [args.redirector.rstrip("/") + "/" + f if f.startswith("/store") else f for f in files]
    if args.max_files:
        files = files[: args.max_files]
    if not files:
        print("error: no ROOT files found", file=sys.stderr)
        return 1

    n = max(1, args.files_per_job)
    jobs = [f"{k} " + ",".join(files[i:i + n]) for k, i in enumerate(range(0, len(files), n))]
    with open(args.output, "w") as fh:
        fh.write("\n".join(jobs) + "\n")
    print(json.dumps({"files": len(files), "jobs": len(jobs), "files_per_job": n, "output": args.output}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
