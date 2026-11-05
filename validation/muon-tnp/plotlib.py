"""Plots for the muon tag-and-probe validation (CMS Open Data style). Units GeV."""
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplhep as hep
import numpy as np

plt.style.use(hep.style.CMS)
TITLE = {"tightid": "Tight ID (den: tracker muons)", "tightiso": "Tight PF iso (den: tight ID + IP)",
         "isomu24": "IsoMu24 or IsoTkMu24 (den: tight ID + iso)"}
PT_TOP = 300.0  # display upper edge of the open last pT bin (drawn to 300 GeV)


def label(ax, lumi, loc=0, fs=None):
    hep.cms.label("Open Data", data=True, lumi=f"{lumi:.1f}", com=13, ax=ax, loc=loc, fontsize=fs)


def save(fig, outdir, name):
    os.makedirs(outdir, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(outdir, f"{name}.{ext}"), bbox_inches="tight")
    plt.close(fig)


def _xy(rows):
    lo = np.array([r["pt"][0] for r in rows]); hi = np.array([r["pt"][1] if r["pt"][1] else PT_TOP for r in rows])
    return 0.5 * (lo + hi), 0.5 * (hi - lo), lo, hi


def eff_plot(wp, S, lumi, outdir):
    rows = S["wp"][wp]["bins"]
    etas = sorted({tuple(r["aeta"]) for r in rows})
    fig, ax = plt.subplots(2, len(etas), figsize=(6.0 * len(etas), 9), sharex="col", gridspec_kw=dict(height_ratios=[3, 1.6], hspace=0.05))
    for i, e in enumerate(etas):
        rr = [r for r in rows if tuple(r["aeta"]) == e]
        x, dx, lo, hi = _xy(rr)
        a, b = ax[0, i], ax[1, i]
        a.errorbar(x, [r["eff_data"] for r in rr], xerr=dx, yerr=[r["eff_data_err"] for r in rr], fmt="o", color="k", label="Data (pass/fail fit)")
        a.errorbar(x, [r["eff_mc"] for r in rr], xerr=dx, yerr=[r["eff_mc_err"] for r in rr], fmt="s", color="tab:red", mfc="none", label="DY MC (counting)")
        a.text(0.04, 0.05, rf"$|\eta|$ {e[0]:g}-{e[1]:g}", transform=a.transAxes, fontsize=18)
        lowest = min(min(r["eff_data"], r["eff_mc"]) for r in rr)
        a.set_ylim(max(0.0, lowest - 0.08), 1.02)
        if i == 0:
            a.set_ylabel("Efficiency"); a.legend(fontsize=14, loc="lower right")
        sf = np.array([r["sf"] for r in rr]); tot = np.array([r["sf_total_err"] for r in rr]); st = np.array([r["sf_stat"] for r in rr])
        pg = np.array([r["pog_sf"] for r in rr]); pu = np.array([r["pog_unc"] for r in rr])
        for j in range(len(rr)):
            b.fill_between([lo[j], hi[j]], pg[j] - pu[j], pg[j] + pu[j], color="tab:blue", alpha=0.3, lw=0, label="POG SF $\\pm$ (systup$-$nom)" if j == 0 else None)
            b.plot([lo[j], hi[j]], [pg[j]] * 2, color="tab:blue", lw=1.5)
        b.errorbar(x, sf, xerr=dx, yerr=tot, fmt="o", color="k", capsize=0, label="SF ours (stat+syst)")
        b.errorbar(x, sf, yerr=st, fmt="none", color="tab:orange", capsize=3, label="stat only")
        b.set_xscale("log"); b.set_xlim(14, 330); b.set_xlabel(r"Probe $p_{T}$ [GeV]")
        b.set_xticks([20, 30, 50, 100, 200]); b.set_xticklabels(["20", "30", "50", "100", "200"])
        b.minorticks_off()
        if i == 0:
            b.set_ylabel("Data / MC SF"); hd, lb = b.get_legend_handles_labels()
        ymin = min((sf - tot).min(), (pg - pu).min()); ymax = max((sf + tot).max(), (pg + pu).max())
        b.set_ylim(max(0.9, ymin - 0.01), min(1.1, ymax + 0.01))
    fig.legend(hd, lb, loc="lower center", ncol=3, fontsize=14, bbox_to_anchor=(0.5, -0.04))
    fig.text(0.99, -0.03, "last pT bin is open: drawn to 300 GeV", ha="right", fontsize=12)
    label(ax[0, 0], lumi, fs=16)
    fig.suptitle(TITLE[wp], y=0.99, fontsize=20)
    save(fig, outdir, f"eff_{wp}")


def map_plot(wp, S, lumi, outdir):
    rows = S["wp"][wp]["bins"]
    etas = sorted({tuple(r["aeta"]) for r in rows}); pts = sorted({tuple(r["pt"]) for r in rows}, key=lambda p: p[0])
    M = np.full((len(etas), len(pts)), np.nan); P = M.copy()
    for r in rows:
        i, j = etas.index(tuple(r["aeta"])), pts.index(tuple(r["pt"]))
        M[i, j] = r["sf_over_pog"]; P[i, j] = r["pull"]
    fig, ax = plt.subplots(figsize=(13, 5.5))
    im = ax.pcolormesh(np.arange(len(pts) + 1), np.arange(len(etas) + 1), M, cmap="RdBu_r", vmin=0.95, vmax=1.05)
    for i in range(len(etas)):
        for j in range(len(pts)):
            if np.isfinite(M[i, j]):
                ax.text(j + 0.5, i + 0.5, f"{M[i, j]:.3f}\n({P[i, j]:+.1f}$\\sigma$)", ha="center", va="center", fontsize=12)
    ax.set_xticks(np.arange(len(pts)) + 0.5); ax.set_xticklabels([f"{p[0]:g}-{p[1]:g}" if p[1] else f"{p[0]:g}+" for p in pts], fontsize=13)
    ax.set_yticks(np.arange(len(etas)) + 0.5); ax.set_yticklabels([f"{e[0]:g}-{e[1]:g}" for e in etas])
    ax.set_xlabel(r"Probe $p_{T}$ [GeV]"); ax.set_ylabel(r"Probe $|\eta|$")
    ax.set_title(f"SF ours / SF POG (pull) : {TITLE[wp]}", fontsize=16, y=1.12)
    fig.colorbar(im, ax=ax, label="SF ours / SF POG (colour range 0.95-1.05, numbers exact)")
    label(ax, lumi, fs=14)
    save(fig, outdir, f"sf_ratio_map_{wp}")


def pull_plot(S, lumi, outdir):
    wps = list(S["wp"])
    lo, hi = -8.0, 24.0
    fig, ax = plt.subplots(1, len(wps), figsize=(6.5 * len(wps), 6.5), sharey=True)
    ax = np.atleast_1d(ax)
    edges = np.arange(lo, hi + 1e-9, 1.0)
    for a, wp in zip(ax, wps):
        p = np.array([r["pull"] for r in S["wp"][wp]["bins"]])
        n_under, n_over = int((p < lo).sum()), int((p > hi).sum())
        a.hist(np.clip(p, lo + 1e-6, hi - 1e-6), bins=edges, color="tab:blue", alpha=0.7)
        a.set_xlabel("Pull (SF $-$ POG) / $\\sigma$")
        a.text(0.97, 0.95, f"{wp}\nmean {S['wp'][wp]['mean_pull']:+.2f}, RMS {S['wp'][wp]['rms_pull']:.2f}\nmax pull {p.max():+.1f}\n(under/overflow: {n_under}/{n_over})",
               transform=a.transAxes, ha="right", va="top", fontsize=15)
        a.set_xlim(lo, hi)
    ax[0].set_ylabel("Bins")
    label(ax[0], lumi, fs=14)
    save(fig, outdir, "pulls")


def fit_plot(wp, key, nom, row, S_lumi, outdir, tag):
    h = nom[key]["hists"]; par = h["par"]
    lo, hi = 70.0, 115.0
    nb = len(h["hp"]); edges = np.linspace(lo, hi, nb + 1); c = 0.5 * (edges[1:] + edges[:-1]); x = c - 90
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.5))
    for a, passing in zip(axs, (True, False)):
        d = h["hp"] if passing else h["hf"]
        t = np.clip(h["tp"] if passing else h["tf"], 0, None); t = t / t.sum()
        e = par["eff"] if passing else 1 - par["eff"]
        bk = par["bp"] if passing else par["bf"]; sl = par["ap"] if passing else par["af"]
        ee = np.exp(sl * x); bkg = bk * ee / ee.sum()
        a.errorbar(c, d, yerr=np.sqrt(d), fmt="ko", ms=4, label="Data")
        a.stairs(par["nsig"] * e * t + bkg, edges, color="tab:blue", lw=2, label="Signal + bkg fit")
        a.stairs(bkg, edges, color="tab:red", ls="--", lw=2, label="Exponential bkg")
        a.set_xlabel(r"$m_{\mu\mu}$ [GeV]"); a.set_ylabel("Pairs / GeV (log)")
        a.set_title(f"{'Pass' if passing else 'Fail'}: {row['label'].replace('_', ', ')} GeV", fontsize=14, y=1.1)
        a.set_yscale("log"); a.set_ylim(0.5, 5 * max(d.max(), 1))
        a.legend(fontsize=12)
    axs[0].text(0.03, 0.8, f"$\\epsilon$ = {row['eff_data']:.4f} $\\pm$ {row['eff_data_err']:.4f}\nfit ok: {row['fit_ok']}", transform=axs[0].transAxes, fontsize=13)
    label(axs[0], S_lumi, fs=13)
    save(fig, outdir, f"fit_{wp}_{row['label']}_{tag}")


def gh_plot(wp, S, lumi, outdir):
    rows = S["run_dependence"]["wp"][wp]["bins"]
    etas = sorted({tuple(r["aeta"]) for r in rows})
    fig, ax = plt.subplots(1, len(etas), figsize=(6 * len(etas), 5.5), sharey=True)
    for i, e in enumerate(etas):
        rr = [r for r in rows if tuple(r["aeta"]) == e]
        x, dx, lo, hi = _xy(rr)
        a = ax[i]
        a.errorbar(x * 0.97, [r["sf_G"] for r in rr], yerr=[r["sf_G_stat"] for r in rr], fmt="o", color="tab:green", label="Run2016G")
        a.errorbar(x * 1.03, [r["sf_H"] for r in rr], yerr=[r["sf_H_stat"] for r in rr], fmt="s", color="tab:purple", label="Run2016H")
        for j, r in enumerate(rr):
            a.plot([lo[j], hi[j]], [r["pog_sf"]] * 2, color="tab:blue", lw=2, label="POG (F late+G+H)" if j == 0 else None)
        a.set_xscale("log"); a.set_xticks([20, 30, 50, 100, 200]); a.set_xticklabels(["20", "30", "50", "100", "200"]); a.minorticks_off()
        a.set_xlabel(r"Probe $p_{T}$ [GeV]"); a.text(0.04, 0.05, rf"$|\eta|$ {e[0]:g}-{e[1]:g}", transform=a.transAxes, fontsize=16)
        a.set_ylim(0.9, 1.1)
    ax[0].set_ylabel("Data / MC SF"); ax[0].legend(fontsize=12)
    fig.suptitle(f"{TITLE[wp]}: Run2016G vs Run2016H", y=1.04, fontsize=18)
    label(ax[0], lumi, fs=13)
    save(fig, outdir, f"run_dependence_{wp}")


def filterbit_plot(S, lumi, outdir):
    d = S["filter_bits"]["measurement"]
    fig, ax = plt.subplots(1, 2, figsize=(14, 5.5))
    names = {"S": "skill (event fired + bit + pT)", "A": "bit + pT only", "C": "path-specific"}
    cols = {"S": "k", "A": "tab:red", "C": "tab:green"}
    for t in "SAC":
        bb = [b for b in d[t]["bins"] if b["pt_lo"] == 40.0]
        xs = np.arange(len(bb)) + {"S": -0.15, "A": 0.0, "C": 0.15}[t]
        ax[0].errorbar(xs, [b["sf"] for b in bb], yerr=[b["sf_stat"] for b in bb], fmt="o", color=cols[t], label=names[t])
    ax[0].plot(np.arange(len(bb)), [b["pog_sf"] for b in bb], "_", color="tab:blue", ms=40, mew=2, label="POG")
    ax[0].set_xticks(np.arange(len(bb))); ax[0].set_xticklabels([f"{b['aeta_lo']:g}-" for b in bb])
    ax[0].set_xlabel(r"Probe $|\eta|$ bin (lower edge), $p_T$ 40-50 GeV"); ax[0].set_ylabel("IsoMu24 SF"); ax[0].legend(fontsize=12)
    for nm, c in (("data", "k"), ("mc", "tab:red")):
        f = S["filter_bits"][nm]
        ax[1].bar(nm, 100 * f["fraction_matched_probes_in_event_fired_neither"], color=c)
    ax[1].set_ylabel("Matched probes in events with neither path fired [%]")
    label(ax[0], lumi, fs=13)
    save(fig, outdir, "filter_bits")


def make_all(S, pd, dd, dm, outdir, lumi):
    os.makedirs(outdir, exist_ok=True)
    for wp in S["wp"]:
        eff_plot(wp, S, lumi, outdir)
        map_plot(wp, S, lumi, outdir)
        rows = pd[wp]["rows"]; nom = pd[wp]["nom"]
        keys = sorted(nom)
        lab = {r["label"]: k for r, k in zip(rows, keys)}
        # representative bins: barrel 40-50, endcap 1.2-2.1 at 40-50, lowest pT barrel; worst pull; worst |SF/POG-1|
        reps = []
        for r in rows:
            if (r["aeta"][0] == 0.0 and r["pt"][0] == 40.0) or (r["aeta"][0] == 1.2 and r["pt"][0] == 40.0) or (r["aeta"][0] == 2.1 and r["pt"][0] == 30.0):
                reps.append((r, "rep"))
        worst = sorted(rows, key=lambda r: -abs(r["pull"]))[:2]
        reps += [(r, "worst") for r in worst]
        for r, tag in reps:
            fit_plot(wp, lab[r["label"]], nom, r, lumi, outdir, tag)
    pull_plot(S, lumi, outdir)
    for wp in S["run_dependence"]["wp"]:
        gh_plot(wp, S, lumi, outdir)
    if "filter_bits" in S:
        filterbit_plot(S, lumi, outdir)
