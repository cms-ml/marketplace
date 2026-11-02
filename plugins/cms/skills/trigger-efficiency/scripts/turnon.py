#!/usr/bin/env python3
"""Trigger turn-on helpers: Clopper-Pearson efficiency, plateau threshold, plot.

Import it (copy next to your analysis, or add this directory to sys.path):

    from turnon import efficiency, find_threshold, plateau, plot_turnon
    eff = efficiency(num, den)                 # dict: num, den, eff, lo, hi (68% CP)
    thr, i = find_threshold(eff, edges)        # lowest edge where the curve stays on the plateau
    p = plateau(eff, i)                        # pooled efficiency above the threshold, with CP interval

or run the self-contained demo, which measures the 2016 dijet turn-on
(signal OR vs HLT_PFJet260, tight-ID jets |eta| < 2.4, |deta| < 1.1)
directly from JetHT NanoAOD:

    turnon.py --demo FILE [FILE ...] [--out turnon_demo.png]

Stdout (demo): KEY=VALUE lines (THRESHOLD_GEV, PLATEAU, PLATEAU_LO, PLATEAU_HI,
N_REF_ABOVE). Diagnostics on stderr. Exit codes: 0 ok, 1 no plateau found
(too few events: add files), 2 bad input. Units: GeV.
Needs numpy, scipy, uproot, awkward, matplotlib, mplhep (the LCG view has all).
"""
from __future__ import annotations

import argparse
import sys

import numpy as np
from scipy import stats

# CMS dijet binning (resolution-motivated variable bins, GeV), as used in the
# CMS dijet searches; use it for m_jj turn-ons so they line up with the fit bins.
# Slice it for the turn-on range, e.g. DIJET_EDGES[(DIJET_EDGES >= 649) & (DIJET_EDGES <= 3019)].
DIJET_EDGES = np.array([
    1, 3, 6, 10, 16, 23, 31, 40, 50, 61, 74, 88, 103, 119, 137, 156, 176, 197, 220, 244, 270, 296, 325,
    354, 386, 419, 453, 489, 526, 565, 606, 649, 693, 740, 788, 838, 890, 944, 1000, 1058, 1118, 1181,
    1246, 1313, 1383, 1455, 1530, 1607, 1687, 1770, 1856, 1945, 2037, 2132, 2231, 2332, 2438, 2546, 2659,
    2775, 2895, 3019, 3147, 3279, 3416, 3558, 3704, 3854, 4010, 4171, 4337, 4509, 4686, 4869, 5058, 5253,
    5455, 5663, 5877, 6099, 6328, 6564, 6808, 7060, 7320, 7589, 7866, 8152, 8447, 8752, 9067, 9391, 9726,
    10072, 10430, 10798, 11179, 11571, 11977, 12395, 12827, 13272, 13732, 14000], dtype=float)
DEMO_EDGES = DIJET_EDGES[(DIJET_EDGES >= 649) & (DIJET_EDGES <= 3019)]


def clopper_pearson(k, n, cl=0.6827):
    """Exact binomial interval. Returns (eff, lo, hi); eff is NaN where n == 0."""
    k = np.asarray(k, float)
    n = np.asarray(n, float)
    a = (1 - cl) / 2
    with np.errstate(invalid="ignore", divide="ignore"):
        lo = np.where(k > 0, stats.beta.ppf(a, k, n - k + 1), 0.0)
        hi = np.where(k < n, stats.beta.ppf(1 - a, k + 1, n - k), 1.0)
        eff = np.where(n > 0, k / n, np.nan)
    return eff, lo, hi


def efficiency(num, den, cl=0.6827):
    """Per-bin efficiency with CP interval. num/den are counts (passing ref AND signal / passing ref)."""
    num = np.asarray(num, float)
    den = np.asarray(den, float)
    if np.any(num > den):
        raise ValueError("num > den in some bin: the numerator must be a subset of the denominator")
    eff, lo, hi = clopper_pearson(num, den, cl)
    return {"num": num, "den": den, "eff": eff, "lo": lo, "hi": hi}


def find_threshold(e, edges, target=0.99, min_events=100):
    """Lowest bin edge E such that (1) every populated bin above E has its CP upper bound >= target,
    (2) the pooled efficiency above E is >= target, and (3) the reference sample above E has at
    least min_events events (otherwise the "compatible with 1" test is meaningless).
    Returns (E, bin_index) or (nan, -1)."""
    for i in range(len(edges) - 1):
        den = e["den"][i:]
        if den.sum() < min_events:
            break
        bins_ok = np.all((e["hi"][i:] >= target) | (den == 0))
        if bins_ok and e["num"][i:].sum() / den.sum() >= target:
            return float(edges[i]), i
    return float("nan"), -1


def plateau(e, i):
    """Pooled efficiency above bin i, with its CP interval: (eff, lo, hi, n_ref)."""
    k, n = e["num"][i:].sum(), e["den"][i:].sum()
    eff, lo, hi = clopper_pearson(k, n)
    return float(eff), float(lo), float(hi), int(n)


def plot_turnon(ax, e, edges, label, dx=0.0, xerr=True, **kw):
    """Draw efficiency points with asymmetric CP errors, skipping empty bins (NaN breaks errorbar).
    dx shifts the markers (GeV) so several references can share one plot; xerr=False drops the
    bin-width bars (useful for cross-check overlays). Extra kwargs go to ax.errorbar."""
    c = 0.5 * (edges[1:] + edges[:-1]) + dx
    w = 0.5 * np.diff(edges)
    ok = e["den"] > 0
    ax.errorbar(c[ok], e["eff"][ok], xerr=w[ok] if xerr else None,
                yerr=[e["eff"][ok] - e["lo"][ok], e["hi"][ok] - e["eff"][ok]],
                fmt=kw.pop("fmt", "o"), label=label, **kw)


# ----------------------------------------------------------------------------- demo

SIGNAL_2016 = ["HLT_PFHT900", "HLT_PFHT800", "HLT_PFJet450", "HLT_PFJet500",
               "HLT_CaloJet500_NoJetID", "HLT_AK8PFJet450", "HLT_AK8PFJet500"]
REFERENCE = "HLT_PFJet260"


def demo_counts(files, edges):
    import awkward as ak
    import uproot

    num = np.zeros(len(edges) - 1)
    den = np.zeros(len(edges) - 1)
    for f in files:
        tree = uproot.open(f)["Events"]
        keys = set(tree.keys())
        sig = [t for t in SIGNAL_2016 if t in keys]          # menus differ: HLT_PFHT800 is absent in 2016H
        if REFERENCE not in keys or not sig:
            raise SystemExit(f"error: {f} lacks {REFERENCE} or all signal paths")
        missing = sorted(set(SIGNAL_2016) - set(sig))
        print(f"{f}: signal paths missing in this file: {missing or 'none'}", file=sys.stderr)
        cols = ["Jet_pt", "Jet_eta", "Jet_phi", "Jet_mass", "Jet_jetId", REFERENCE] + sig
        for a in tree.iterate(cols, step_size="200 MB"):
            good = (a.Jet_pt > 30) & ((a.Jet_jetId & 2) > 0)    # tight ID (bit 2) in 2016 UL NanoAOD
            j = a[["Jet_pt", "Jet_eta", "Jet_phi", "Jet_mass"]][good][:, :2]
            two = ak.num(j.Jet_pt) == 2
            a, j = a[two], j[two]
            pt, eta, phi, m = (ak.to_numpy(j[c]) for c in ("Jet_pt", "Jet_eta", "Jet_phi", "Jet_mass"))
            px, py, pz = pt * np.cos(phi), pt * np.sin(phi), pt * np.sinh(eta)
            en = np.sqrt(px**2 + py**2 + pz**2 + m**2)
            mjj = np.sqrt(np.maximum(en.sum(1)**2 - px.sum(1)**2 - py.sum(1)**2 - pz.sum(1)**2, 0))
            sel = (np.abs(eta) < 2.4).all(1) & (np.abs(eta[:, 0] - eta[:, 1]) < 1.1)
            ref = sel & ak.to_numpy(a[REFERENCE])
            fired = np.zeros(len(a), bool)
            for t in sig:
                fired |= ak.to_numpy(a[t])
            den += np.histogram(mjj[ref], edges)[0]
            num += np.histogram(mjj[ref & fired], edges)[0]
    return num, den


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--demo", nargs="+", metavar="FILE", required=True, help="2016 JetHT NanoAOD files")
    ap.add_argument("--out", default="turnon_demo.png", help="plot file (default turnon_demo.png)")
    ap.add_argument("--target", type=float, default=0.99, help="plateau target efficiency (default 0.99)")
    a = ap.parse_args()

    num, den = demo_counts(a.demo, DEMO_EDGES)
    e = efficiency(num, den)
    thr, i = find_threshold(e, DEMO_EDGES, target=a.target)
    if i < 0:
        print("error: no plateau found; add files (the reference trigger is prescaled)", file=sys.stderr)
        return 1
    eff, lo, hi, n = plateau(e, i)

    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import mplhep as hep
    hep.style.use("CMS")
    fig, ax = plt.subplots()
    plot_turnon(ax, e, DEMO_EDGES, f"ref. {REFERENCE}", color="k")
    ax.axvline(thr, ls="--", color="tab:green", label=f"$m_{{jj}}$ > {thr:.0f} GeV")
    ax.set(xlabel=r"$m_{jj}$ [GeV]", ylabel="Trigger efficiency", ylim=(0, 1.15))
    ax.legend(loc="lower right")
    hep.cms.label("Open Data", data=True, com=13, ax=ax)
    fig.savefig(a.out)

    print(f"THRESHOLD_GEV={thr:.0f}")
    print(f"PLATEAU={eff:.5f}")
    print(f"PLATEAU_LO={lo:.5f}")
    print(f"PLATEAU_HI={hi:.5f}")
    print(f"N_REF_ABOVE={n}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
