#!/usr/bin/env python3
"""Does a cut on the classifier score change the background mass shape? Quantify it.

    sculpting.py scores.parquet --mass obs_mjj --mass-range 1200,4000 --out-dir sculpt
        [--score score] [--label label] [--weight weight] [--bkg-effs 0.5,0.1,0.01] [--log-bins]

Uses background rows only (label == 0) of the test split (rows with split == --test-split when a
split column exists, otherwise all rows). For every working point (score cut keeping a
fraction --bkg-effs of the background):
  chi2/ndf and p-value between the PASS and FAIL mass histograms (independent samples,
    shape-normalised, weighted errors; bins with fewer than --min-bin-neff effective events in
    either histogram are merged into their neighbour)
  JSD (base 2) between the two normalised histograms, and the same for a random split of the
    same size (JSD_FLOOR: what statistics alone give)
  largest |pass/expected - 1| over bins, weighted KS p-value on the unbinned mass
Global: Pearson r and distance correlation (on --dcor-n events drawn with probability |w|)
between score and mass, and with signal rows present R50 (1 / background efficiency at 50%
signal efficiency) and INV_JSD_50 (1 / JSD at that cut), the usual decorrelation benchmark.

A working point is SCULPTED when its chi2 p-value < --min-p (0.01) and JSD > 2 x JSD_FLOOR;
it is LOW_STAT (not judged) when fewer than --min-pass (200) effective events pass.
STATUS=FAIL if any working point is SCULPTED; with every point LOW_STAT the status is FAIL
too (nothing was verified). Writes <out-dir>/sculpting.json and sculpting.png.

Stdout KEY=VALUE: N_BKG PEARSON_R DCOR [R50 INV_JSD_50] and per working point
CHI2_NDF_<eff> P_<eff> JSD_<eff> JSD_FLOOR_<eff> MAX_DEV_<eff> VERDICT_<eff>, then
N_SCULPTED N_LOW_STAT STATUS.
Exit codes: 0 pass, 1 STATUS=FAIL, 2 bad input. --dry-run prints N_BKG and the bin edges only.
Mass in GeV.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

import numpy as np


def jsd(p, q):
    p, q = p / p.sum(), q / q.sum()
    m = 0.5 * (p + q)

    def kl(a, b):
        ok = a > 0
        return float(np.sum(a[ok] * np.log2(a[ok] / b[ok])))

    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def dcor(x, y):
    """Distance correlation (Szekely et al. 2007), O(n^2) memory."""
    def centred(v):
        d = np.abs(v[:, None] - v[None, :])
        return d - d.mean(0)[None, :] - d.mean(1)[:, None] + d.mean()

    a, b = centred(x.astype(float)), centred(y.astype(float))
    return float(np.sqrt(max((a * b).mean(), 0) / np.sqrt((a * a).mean() * (b * b).mean())))


def wquantile(x, w, q):
    o = np.argsort(-x)
    c = np.cumsum(w[o]) / w.sum()
    return float(x[o][min(int(np.searchsorted(c, q)), len(x) - 1)])


def compare(m, w, passed, edges, min_neff):
    """chi2 between pass and fail mass shapes after merging low-statistics bins."""
    h = [np.histogram(m[s], edges, weights=w[s])[0] for s in (passed, ~passed)]
    v = [np.histogram(m[s], edges, weights=w[s] ** 2)[0] for s in (passed, ~passed)]
    groups, cur = [], []
    for i in range(len(edges) - 1):
        cur.append(i)
        if all(hh[cur].sum() ** 2 / max(vv[cur].sum(), 1e-300) >= min_neff for hh, vv in zip(h, v)):
            groups.append(cur)
            cur = []
    if cur:
        groups[-1:] = [(groups[-1] if groups else []) + cur]
    hp, hf = (np.array([hh[g].sum() for g in groups]) for hh in h)
    vp, vf = (np.array([vv[g].sum() for g in groups]) for vv in v)
    k = hp.sum() / hf.sum()
    chi2 = float(np.sum((hp - k * hf) ** 2 / (vp + k * k * vf)))
    ndf = len(groups) - 1
    exp = (hp + hf) * hp.sum() / (hp + hf).sum()
    return chi2, ndf, float(np.max(np.abs(hp / exp - 1))) if ndf > 0 else float("nan"), jsd(np.clip(hp, 0, None), np.clip(hf, 0, None))


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("scores")
    p.add_argument("--out-dir", required=True)
    p.add_argument("--mass", required=True, help="mass column")
    p.add_argument("--mass-range", required=True, help="lo,hi in GeV")
    p.add_argument("--bins", type=int, default=30)
    p.add_argument("--log-bins", action="store_true")
    p.add_argument("--score", default="score")
    p.add_argument("--label", default="label")
    p.add_argument("--weight", default="weight")
    p.add_argument("--split", default="split")
    p.add_argument("--test-split", default="test")
    p.add_argument("--bkg-effs", default="0.5,0.1,0.01")
    p.add_argument("--min-p", type=float, default=0.01)
    p.add_argument("--min-pass", type=float, default=200)
    p.add_argument("--min-bin-neff", type=float, default=10)
    p.add_argument("--dcor-n", type=int, default=3000)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--no-plots", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    try:
        import pandas as pd
        from scipy.stats import chi2 as chi2dist

        t = pd.read_parquet(a.scores)
        if a.split in t:
            t = t[t[a.split] == a.test_split]
        lo, hi = (float(x) for x in a.mass_range.split(","))
        t = t[(t[a.mass] >= lo) & (t[a.mass] < hi) & (t[a.label] >= 0)]
        y = t[a.label].to_numpy()
        s, m = t[a.score].to_numpy(float), t[a.mass].to_numpy(float)
        w = t[a.weight].to_numpy(float) if a.weight in t else np.ones(len(t))
        b = y == 0
        effs = [float(x) for x in a.bkg_effs.split(",")]
        if b.sum() < 100:
            raise ValueError(f"only {int(b.sum())} background rows in the mass range")
    except Exception as e:  # noqa: BLE001
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    edges = np.geomspace(lo, hi, a.bins + 1) if a.log_bins else np.linspace(lo, hi, a.bins + 1)
    res = {"N_BKG": int(b.sum())}
    if a.dry_run:
        print(f"N_BKG={res['N_BKG']}\nEDGES={','.join(f'{e:.4g}' for e in edges)}\nDRY_RUN=1")
        return 0
    rng = np.random.default_rng(a.seed)
    sb, mb, wb = s[b], m[b], w[b]
    res["PEARSON_R"] = round(float(np.corrcoef(sb, mb)[0, 1]), 4)
    i = rng.choice(len(sb), min(a.dcor_n, len(sb)), replace=False, p=np.abs(wb) / np.abs(wb).sum())
    res["DCOR"] = round(dcor(sb[i], mb[i]), 4)
    if (y == 1).sum() > 0:
        thr50 = wquantile(s[y == 1], w[y == 1], 0.5)
        pas = sb > thr50
        eb = wb[pas].sum() / wb.sum()
        if 0 < eb < 1:
            res["R50"] = round(float(1 / eb), 2)
            j = compare(mb, wb, pas, edges, 0)[3]
            res["INV_JSD_50"] = round(1 / j, 1) if j > 0 else float("inf")
    wps, nsc, nlow = [], 0, 0
    for e in effs:
        thr = wquantile(sb, wb, e)
        pas = sb > thr
        neff = wb[pas].sum() ** 2 / max((wb[pas] ** 2).sum(), 1e-300)
        chi2, ndf, dev, j = compare(mb, wb, pas, edges, a.min_bin_neff)
        floor = float(np.mean([compare(mb, wb, rng.permutation(pas), edges, a.min_bin_neff)[3] for _ in range(20)]))
        pval = float(chi2dist.sf(chi2, ndf)) if ndf > 0 else float("nan")
        if neff < a.min_pass or ndf < 1:
            verdict = "LOW_STAT"
            nlow += 1
        elif pval < a.min_p and j > 2 * floor:
            verdict = "SCULPTED"
            nsc += 1
        else:
            verdict = "OK"
        wps.append({"bkg_eff": e, "threshold": thr, "neff_pass": float(neff), "chi2": chi2, "ndf": ndf, "p": pval,
                    "jsd": j, "jsd_floor": floor, "max_dev": dev, "verdict": verdict})
        res.update({f"CHI2_NDF_{e:g}": round(chi2 / max(ndf, 1), 2), f"P_{e:g}": float(f"{pval:.3g}"),
                    f"JSD_{e:g}": float(f"{j:.3g}"), f"JSD_FLOOR_{e:g}": float(f"{floor:.3g}"),
                    f"MAX_DEV_{e:g}": round(dev, 3), f"VERDICT_{e:g}": verdict})
    fail = nsc > 0 or nlow == len(effs)
    res.update({"N_SCULPTED": nsc, "N_LOW_STAT": nlow, "STATUS": "FAIL" if fail else "PASS"})
    os.makedirs(a.out_dir, exist_ok=True)
    with open(os.path.join(a.out_dir, "sculpting.json"), "w") as f:
        json.dump({"summary": res, "working_points": wps, "edges": edges.tolist(), "score": a.score, "mass": a.mass,
                   "command": " ".join(sys.argv)}, f, indent=1)
    if not a.no_plots:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        fig, (ax, rx) = plt.subplots(2, 1, figsize=(5.5, 5.5), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
        c = 0.5 * (edges[1:] + edges[:-1])
        h0 = np.histogram(mb, edges, weights=wb)[0]
        ax.stairs(h0 / h0.sum(), edges, color="k", label="all background")
        for k, wp in enumerate(wps):
            pas = sb > wp["threshold"]
            h = np.histogram(mb[pas], edges, weights=wb[pas])[0]
            v = np.histogram(mb[pas], edges, weights=wb[pas] ** 2)[0]
            ok = (h > 0) & (h0 > 0)
            ax.stairs(h / h.sum(), edges, color=f"C{k}", label=f"bkg eff {wp['bkg_eff']:g}: {wp['verdict']}")
            rx.errorbar(c[ok], (h / h.sum() / (h0 / h0.sum()))[ok], (np.sqrt(v) / h)[ok], fmt=".", color=f"C{k}", ms=3)
        ax.set(yscale="log", ylabel="Normalised background")
        ax.legend(fontsize=7)
        rx.axhline(1, color="k", lw=0.5)
        rx.set(xlabel=f"{a.mass} [GeV]", ylabel="pass / all", ylim=(0, 2))
        fig.savefig(os.path.join(a.out_dir, "sculpting.png"), dpi=120, bbox_inches="tight")
    print("\n".join(f"{k}={v}" for k, v in res.items()))
    return 1 if fail else 0


if __name__ == "__main__":
    sys.exit(main())
