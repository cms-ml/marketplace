#!/usr/bin/env python3
"""Build jobs.txt (+ input_files.json) from make_filelist.py listings (lines '<idx> <url>').

Data: every STEP-th file (sorted path order) of the Run2016G and Run2016H listings, in NG and NH jobs of
contiguous files (G and H stay in separate jobs). MC: all files, dealt round-robin into NM jobs.
Usage: make_jobs.py data_G.txt data_H.txt mc_all.txt [--step 5] -o jobs.txt
"""
import argparse
import json

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument("g"); ap.add_argument("h"); ap.add_argument("mc")
ap.add_argument("--step", type=int, default=5); ap.add_argument("--ng", type=int, default=2)
ap.add_argument("--nh", type=int, default=2); ap.add_argument("--nm", type=int, default=2)
ap.add_argument("-o", default="jobs.txt"); ap.add_argument("--files-json", default="input_files.json")
a = ap.parse_args()
urls = lambda p: [l.split()[1] for l in open(p) if l.strip()]
G, H, M = urls(a.g), urls(a.h), urls(a.mc)
sel = {"G": G[::a.step], "H": H[::a.step], "mc": M}
jobs = []
for era, n in (("G", a.ng), ("H", a.nh)):
    f = sel[era]
    for i in range(n):
        jobs.append((f"{era}{i}", f[i * len(f) // n:(i + 1) * len(f) // n]))
for i in range(a.nm):
    jobs.append((f"mc{i}", M[i::a.nm]))
with open(a.o, "w") as fo:
    for j, u in jobs:
        fo.write(f"{j} {','.join(u)}\n")
        print(j, len(u), "files")
json.dump({"step": a.step, "n_listed": {"G": len(G), "H": len(H), "mc": len(M)},
           "selected": {k: [u.split("/eos/opendata/cms/")[1] for u in v] for k, v in sel.items()}},
          open(a.files_json, "w"), indent=0)
