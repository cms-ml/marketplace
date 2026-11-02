#!/usr/bin/env python3
"""Build jobs.txt (9 jobs: 6 data, 2 QCD, 1 signal) from per-sample file lists.

Usage: make_jobs.py <listdir> <data_all_files.txt> -o jobs.txt
<listdir> holds sig_<M>.txt and qcd_<bin>.txt written by lpc-condor make_filelist.py
(lines "<idx> <url>", one file per line). Data files are split in 6 contiguous chunks,
QCD files are dealt round-robin into 2 jobs (balances events), all signal files go in 1 job.
"""
import argparse, glob, os
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument("listdir"); ap.add_argument("datafiles"); ap.add_argument("-o", default="jobs.txt")
ap.add_argument("--ndata", type=int, default=6); ap.add_argument("--nqcd", type=int, default=2)
a = ap.parse_args()
urls = lambda pat: [l.split()[1] for p in sorted(glob.glob(os.path.join(a.listdir, pat))) for l in open(p) if l.strip()]
data = [l.strip() for l in open(a.datafiles) if l.strip()]
qcd = urls("qcd_*.txt"); qcd = [u for u in qcd if "HT500to700" not in u]   # HT500to700 skipped (spec)
sig = urls("sig_*.txt")
jobs = []
n = len(data)
for i in range(a.ndata):
    jobs.append((f"d{i}", data[i * n // a.ndata:(i + 1) * n // a.ndata]))
for i in range(a.nqcd):
    jobs.append((f"q{i}", qcd[i::a.nqcd]))
jobs.append(("s0", sig))
with open(a.o, "w") as f:
    for j, u in jobs:
        f.write(f"{j} {','.join(u)}\n")
        print(j, len(u), "files")
