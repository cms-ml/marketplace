#!/usr/bin/env python3
"""Our data/MC scale factors against the official CMS Muon POG ones (2016postVFP UL,
muon_Z.json.gz), read from summary.json. Writes plots/sf_vs_cms_<wp> and
plots/sf_vs_cms_overview (PNG + PDF). Also redraws the SF/POG maps. Units GeV.

    python3 plot_cms_comparison.py [summary.json] [plots/]
"""
import json
import os
import sys

import numpy as np

import plotlib
from plotlib import PT_TOP, TITLE, label, plt, save, _xy

CMS = "CMS Muon POG, 2016postVFP UL"


def sf_vs_cms(wp, S, lumi, outdir, rows=None, name=None, title=None, err_label="stat+syst"):
    rows = rows if rows is not None else S["wp"][wp]["bins"]
    etas = sorted({tuple(r["aeta"]) for r in rows})
    fig, ax = plt.subplots(2, len(etas), figsize=(6.0 * len(etas), 9), sharex="col",
                           gridspec_kw=dict(height_ratios=[3, 1.6], hspace=0.05))
    for i, e in enumerate(etas):
        rr = sorted((r for r in rows if tuple(r["aeta"]) == e), key=lambda r: r["pt"][0])
        x, dx, lo, hi = _xy(rr)
        sf = np.array([r["sf"] for r in rr]); err = np.array([r["sf_total_err"] for r in rr])
        pg = np.array([r["pog_sf"] for r in rr]); pu = np.array([r["pog_unc"] for r in rr])
        a, b = ax[0, i], ax[1, i]
        a.errorbar(x, pg, yerr=pu, xerr=[x - lo, hi - x], fmt="s", color="tab:red", mfc="none", ms=8, label=CMS)
        a.errorbar(x, sf, yerr=err, xerr=[x - lo, hi - x], fmt="o", color="black", ms=6,
                   label=f"This work, 3.6 fb$^{{-1}}$ Open Data ({err_label})")
        r = sf / pg
        for l_, h_, u_ in zip(lo, hi, pu / pg):
            b.fill_between([l_, h_], 1 - u_, 1 + u_, color="tab:red", alpha=0.25, lw=0)
        b.errorbar(x, r, yerr=err / pg, xerr=[x - lo, hi - x], fmt="o", color="black", ms=5)
        b.axhline(1, color="tab:red", lw=1)
        a.set_xscale("log"); a.text(0.96, 0.05, f"|$\\eta$| {e[0]:g}-{e[1]:g}", transform=a.transAxes, fontsize=16, ha="right")
        b.set_xticks([20, 30, 50, 100, 200]); b.set_xticklabels(["20", "30", "50", "100", "200"])
        b.xaxis.set_minor_formatter(plt.NullFormatter()); b.set_xlim(lo[0] * 0.9, PT_TOP)
        lo_y = min((sf - err).min(), (pg - pu).min()); hi_y = max((sf + err).max(), (pg + pu).max())
        a.set_ylim(max(0.85, lo_y - 0.01), min(1.12, hi_y + 0.02))
        lim = max(0.02, min(0.08, np.nanmax(np.abs(r - 1) + err / pg) * 1.15))
        b.set_ylim(1 - lim, 1 + lim)
        b.set_xlabel(r"Probe $p_{T}$ [GeV]")
        if i == 0:
            a.set_ylabel("Data / MC scale factor"); b.set_ylabel("Ours / CMS")
    ax[0, 0].legend(loc="upper left", fontsize=13)
    label(ax[0, 0], lumi, fs=16)
    fig.suptitle(title or f"{TITLE[wp]}: scale factor vs CMS", y=0.99, fontsize=20)
    save(fig, outdir, name or f"sf_vs_cms_{wp}")


def overview(S, lumi, outdir, ptlo=30.0, pthi=60.0):
    """SF/CMS per |eta| bin, uncertainty-weighted over ptlo-pthi GeV, for the three working points."""
    fig, ax = plt.subplots(figsize=(11, 6.5))
    style = {"tightid": ("o", "black"), "tightiso": ("s", "tab:blue"), "isomu24": ("^", "tab:red")}
    for k, wp in enumerate(S["wp"]):
        rows = [r for r in S["wp"][wp]["bins"] if r["pt"][0] >= ptlo and r["pt"][1] and r["pt"][1] <= pthi]
        etas = sorted({tuple(r["aeta"]) for r in rows})
        xs, ys, es = [], [], []
        for j, e in enumerate(etas):
            rr = [r for r in rows if tuple(r["aeta"]) == e]
            q = np.array([r["sf"] / r["pog_sf"] for r in rr])
            s = np.array([np.hypot(r["sf_total_err"], r["pog_unc"]) / r["pog_sf"] for r in rr])
            w = 1 / s ** 2
            xs.append(j + 0.15 * (k - 1)); ys.append(np.sum(w * q) / np.sum(w)); es.append(1 / np.sqrt(np.sum(w)))
        m, c = style.get(wp, ("o", None))
        ax.errorbar(xs, ys, yerr=es, fmt=m, color=c, ms=9, label=TITLE[wp].split(" (")[0])
    if "filter_bits" in S:   # IsoMu24 with bit-2 matching for tag and probe (definition b), stat uncertainty only
        bb = [r for r in S["filter_bits"]["measurement"]["b"]["bins"] if r["pt"][0] >= ptlo and r["pt"][1] and r["pt"][1] <= pthi]
        xs, ys, es = [], [], []
        for j, e in enumerate(etas):
            rr = [r for r in bb if r["aeta_lo"] == e[0]]
            q = np.array([r["sf_over_pog"] for r in rr]); s_ = np.array([np.hypot(r["sf_stat"], r["pog_unc"]) / r["pog_sf"] for r in rr]); w = 1 / s_ ** 2
            xs.append(j + 0.15 * 2); ys.append(np.sum(w * q) / np.sum(w)); es.append(1 / np.sqrt(np.sum(w)))
        ax.errorbar(xs, ys, yerr=es, fmt="D", color="tab:green", mfc="none", ms=9, label="IsoMu24, tag and probe bit 2 only (stat)")
    ax.axhline(1, color="gray", ls="--")
    ax.set_xticks(range(len(etas))); ax.set_xticklabels([f"{e[0]:g}-{e[1]:g}" for e in etas])
    ax.set_xlabel(r"Probe $|\eta|$"); ax.set_ylabel(f"SF ours / SF CMS ({ptlo:g}-{pthi:g} GeV)")
    ax.set_ylim(0.97, 1.04)
    ax.legend(loc="upper left", fontsize=15, title=f"vs {CMS}", title_fontsize=13)
    label(ax, lumi, fs=16)
    save(fig, outdir, "sf_vs_cms_overview")


def bit2_plot(S, lumi, outdir):
    """IsoMu24 with tag and probe matched to the bit-2 (Iso) object only: the definition the skill uses."""
    m = S.get("filter_bits", {}).get("measurement", {}).get("b")
    if not m:
        return
    edges = sorted({tuple(r["aeta"]) for r in S["wp"]["isomu24"]["bins"]})
    lo2e = {e[0]: e for e in edges}
    rows = [dict(r, aeta=list(lo2e[r["aeta_lo"]]), sf_total_err=r["sf_stat"]) for r in m["bins"]]
    sf_vs_cms("isomu24", S, lumi, outdir, rows=rows, name="sf_vs_cms_isomu24_bit2", err_label="stat",
              title="IsoMu24 or IsoTkMu24, tag and probe matched to bit 2 (Iso) only: scale factor vs CMS")


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "summary.json"
    outdir = sys.argv[2] if len(sys.argv) > 2 else "plots"
    S = json.load(open(path))
    lumi = S["luminosity"]["recorded_fb"]
    for wp in S["wp"]:
        sf_vs_cms(wp, S, lumi, outdir)
        plotlib.map_plot(wp, S, lumi, outdir)
    overview(S, lumi, outdir)
    bit2_plot(S, lumi, outdir)
    print("OUT=" + outdir)


if __name__ == "__main__":
    main()
