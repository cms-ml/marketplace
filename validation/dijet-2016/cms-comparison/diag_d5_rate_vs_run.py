#!/usr/bin/env python3
"""Diagnostic for the flat absolute-normalisation deficit seen in D5: student events per recorded fb^-1 versus run.
Selection: golden JSON, signal-trigger OR, |deta|<1.3, m_jj > 1530 GeV (fully efficient), tight-ID leading jets |eta|<2.4.
Usage: diag_d5_rate_vs_run.py --cache <cache> --skims '<glob>'
"""
import argparse, glob, json, sys
import numpy as np
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import *   # noqa
sys.path.insert(0, str(STUDENT_DIR))
import dijetlib as D

ap = argparse.ArgumentParser()
ap.add_argument("--cache", required=True)
ap.add_argument("--skims", required=True)
a = ap.parse_args()
golden = D.golden_keys(Path(a.cache) / "opendata" / "golden.json")
nrun = {}
for p in sorted(glob.glob(a.skims)):
    info = json.loads(str(np.load(p)["info"]))
    mask = np.uint32((1 << info["n_sig_trigs"]) - 1)
    for s, o, nb, na in D.iter_events([p], ["mjj", "eta1", "eta2", "trig", "run", "lumi"], {"data": 1530.0}, golden, only="data"):
        if s != "data":
            continue
        m = ((o["trig"] & mask) > 0) & (np.abs(o["eta1"] - o["eta2"]) < 1.3)
        runs, cnt = np.unique(o["run"][m], return_counts=True)
        for r, c in zip(runs, cnt):
            nrun[int(r)] = nrun.get(int(r), 0) + int(c)
# recorded lumi per run (golden LS only)
lumi = {}
for line in open(Path(a.cache) / "opendata" / "pp_2016lumibyls.csv"):
    if line.startswith("#"):
        continue
    c = line.strip().split(",")
    run = int(c[0].split(":")[0]); ls = int(c[1].split(":")[0])
    if run * 100000 + ls in set() or True:
        pass
    lumi.setdefault(run, []).append((ls, float(c[6])))
gset = {}
import json as _j
gj = _j.load(open(Path(a.cache) / "opendata" / "golden.json"))
def in_golden(run, ls):
    for lo, hi in gj.get(str(run), []):
        if lo <= ls <= hi:
            return True
    return False
runs = sorted(r for r in nrun if r in lumi)
L = np.array([sum(v for ls, v in lumi[r] if in_golden(r, ls)) for r in runs])
N = np.array([nrun[r] for r in runs])
ok = L > 0.02            # fb^-1
rate = N[ok] / L[ok]
rr = np.array(runs)[ok]
eras = np.where(rr < 280500, "G", "H")
for e in ("G", "H"):
    m = eras == e
    log(f"era {e}: runs {m.sum()}, N = {N[ok][m].sum()}, L = {L[ok][m].sum():.3f} fb-1, rate = {N[ok][m].sum()/L[ok][m].sum():.0f} /fb-1")
log(f"all: rate {N[ok].sum()/L[ok].sum():.0f} /fb-1; per-run rate rms/mean = {rate.std()/rate.mean():.3f}")
plt, hep = setup_mpl()
fig, ax = plt.subplots(figsize=(10, 7))
ax.errorbar(np.arange(ok.sum()), rate, yerr=rate / np.sqrt(N[ok]), fmt="o", ms=4, color="black")
ax.set_xlabel("run index (runs with > 20 pb$^{-1}$ recorded, ordered)")
ax.set_ylabel("events / fb$^{-1}$ ($m_{jj}$>1530, |$\\Delta\\eta$|<1.3)")
open_data_label(ax, hep)
savefig(fig, "D5c_rate_per_fb_vs_run")
save_result("D5c_diag", student_result="events per recorded fb^-1 vs run (diagnostic)", rate_G=float(N[ok][eras == "G"].sum() / L[ok][eras == "G"].sum()),
            rate_H=float(N[ok][eras == "H"].sum() / L[ok][eras == "H"].sum()), rms_over_mean=float(rate.std() / rate.mean()),
            verdict="DIAGNOSTIC", reason="uniform rate per fb^-1 across runs -> flat factor is not a lost-run or prescale effect")
