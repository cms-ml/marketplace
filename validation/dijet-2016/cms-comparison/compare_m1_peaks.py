#!/usr/bin/env python3
"""M1 (exact): J/psi, psi(2S), Upsilon(1S,2S,3S) and Z peak positions and widths, fitted on the student's UNCHANGED histograms
(histograms.pkl: m_jpsi 10 MeV bins, m_ups 25 MeV bins, m_z 1 GeV bins), against PDG masses (PDG API, edition quoted in the output).

Model: Crystal Ball (n = 5, alpha free, shared) per resonance + exp(polynomial) background; Z: Voigt (natural width fixed to the PDG value) + exp(poly).
Variations (CB n = 2/10, background order, fit range) give the fit systematic.
Usage: compare_m1_peaks.py --dimuon-dir <dir with histograms.pkl> --cache <cache>
"""
import argparse
import json
import pickle
import sys
import urllib.request

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import *   # noqa
from dimuon_fits import *   # noqa

PDG_IDS = {"jpsi": ("M070", "M070M"), "psi2s": ("M071", "M071M"), "ups1s": ("M049", "M049M"), "ups2s": ("M052", "M052M"), "ups3s": ("M048", "M048M"),
           "z": ("S044", "S044M")}
LABEL = {"jpsi": "J/$\\psi$", "psi2s": "$\\psi$(2S)", "ups1s": "$\\Upsilon$(1S)", "ups2s": "$\\Upsilon$(2S)", "ups3s": "$\\Upsilon$(3S)", "z": "Z"}


def pdg(cache):
    out = {}
    for k, (pid, mid) in PDG_IDS.items():
        f = fetch(f"https://pdgapi.lbl.gov/summaries/{pid}", Path(cache) / "pdg" / f"{pid}.json")
        d = json.load(open(f))
        props = d["summaries"]["properties"] if "summaries" in d else None
        if props is None:
            v = d["pdg_values"][0]
            val, err, unit = v["value"], v["error_positive"], v["unit"]
        else:
            p = [q for q in props if q["pdgid"] == mid][0]["pdg_values"][0]
            val, err, unit = p["value"], p["error_positive"], p["unit"]
        out[k] = (val / 1000.0 if unit == "MeV" else val, err / 1000.0 if unit == "MeV" else err, d.get("edition"))
    zw = json.load(open(fetch("https://pdgapi.lbl.gov/summaries/S044", Path(cache) / "pdg" / "S044.json")))
    gz = [q for q in zw["summaries"]["properties"] if q["pdgid"] == "S044W"][0]["pdg_values"][0]["value"]
    return out, gz


def at_lim(m, k, tol=1e-3):
    """True if parameter k sits at one of its limits (variant fit ran away: excluded from the fit-systematic envelope)"""
    lo, hi = m.limits[k]
    v = m.values[k]
    return (np.isfinite(lo) and v - lo < tol * (hi - lo)) or (np.isfinite(hi) and hi - v < tol * (hi - lo))


def fit_jpsi(edges, n, nCB=5.0, order=3, rng=(2.6, 4.2)):
    sel = (edges[:-1] >= rng[0] - 1e-9) & (edges[1:] <= rng[1] + 1e-9)
    e = np.append(edges[:-1][sel], edges[1:][sel][-1]); y = n[sel]
    x0 = (0.5 * (rng[0] + rng[1]), 0.5 * (rng[1] - rng[0]))

    def model(N1, mu1, s1, N2, mu2, s2, f, r, alpha, *c):
        return mix_counts(e, N1, mu1, s1, f, r, alpha, nCB) + mix_counts(e, N2, mu2, s2, f, r, alpha, nCB) + exp_poly_counts(e, c, x0)
    p0 = dict(N1=2.5e5, mu1=3.097, s1=0.03, N2=1.2e4, mu2=3.686, s2=0.035, f=0.7, r=2.0, alpha=1.5, c0=np.log(500.0))
    for i in range(1, order + 1):
        p0[f"c{i}"] = -0.5 if i == 1 else 0.0
    lim = dict(mu1=(3.07, 3.12), mu2=(3.65, 3.72), s1=(0.01, 0.1), s2=(0.01, 0.12), f=(0.05, 0.99), r=(1.2, 5), alpha=(0.3, 5), N1=(0, None), N2=(0, None))
    m, info = run_fit(model, y, p0, limits=lim)
    return m, info, e, y


def fit_ups(edges, n, nCB=5.0, order=2, rng=(8.5, 11.5)):
    sel = (edges[:-1] >= rng[0] - 1e-9) & (edges[1:] <= rng[1] + 1e-9)
    e = np.append(edges[:-1][sel], edges[1:][sel][-1]); y = n[sel]
    x0 = (0.5 * (rng[0] + rng[1]), 0.5 * (rng[1] - rng[0]))

    def model(N1, mu1, s1, N2, mu2, s2, N3, mu3, s3, f, r, alpha, *c):
        return (mix_counts(e, N1, mu1, s1, f, r, alpha, nCB) + mix_counts(e, N2, mu2, s2, f, r, alpha, nCB) + mix_counts(e, N3, mu3, s3, f, r, alpha, nCB)
                + exp_poly_counts(e, c, x0))
    p0 = dict(N1=2.0e4, mu1=9.46, s1=0.09, N2=1.0e4, mu2=10.02, s2=0.09, N3=8e3, mu3=10.35, s3=0.1, f=0.7, r=2.0, alpha=1.5, c0=np.log(22.0))
    for i in range(1, order + 1):
        p0[f"c{i}"] = 0.0
    lim = dict(mu1=(9.38, 9.54), mu2=(9.95, 10.09), mu3=(10.28, 10.42), s1=(0.03, 0.3), s2=(0.03, 0.3), s3=(0.03, 0.3), f=(0.05, 0.99), r=(1.2, 5), alpha=(0.3, 5),
               N1=(0, None), N2=(0, None), N3=(0, None))
    m, info = run_fit(model, y, p0, limits=lim)
    return m, info, e, y


def fit_z(edges, n, gamma, m0, rng=(60.0, 120.0), order=2, nCB=5.0):
    sel = (edges[:-1] >= rng[0] - 1e-9) & (edges[1:] <= rng[1] + 1e-9)
    e = np.append(edges[:-1][sel], edges[1:][sel][-1]); y = n[sel]
    x0 = (0.5 * (rng[0] + rng[1]), 0.5 * (rng[1] - rng[0]))

    def model(N, delta, s, f, r, alpha, *c):
        return bw_conv_mix_counts(e, N, delta, s, f, r, alpha, nCB, m0, gamma) + exp_poly_counts(e, c, x0)
    p0 = dict(N=7e5, delta=-0.3, s=1.0, f=0.7, r=2.0, alpha=1.5, c0=np.log(4000.0))
    for i in range(1, order + 1):
        p0[f"c{i}"] = -0.3 if i == 1 else 0.0
    lim = dict(delta=(-3, 3), s=(0.3, 4), f=(0.05, 0.99), r=(1.2, 5), alpha=(0.3, 5), N=(0, None))
    m, info = run_fit(model, y, p0, limits=lim)
    return m, info, e, y


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dimuon-dir", required=True)
    ap.add_argument("--cache", required=True)
    a = ap.parse_args()
    h = pickle.load(open(Path(a.dimuon_dir) / "histograms.pkl", "rb"))
    P, gz = pdg(a.cache)
    log("PDG edition:", P["z"][2], {k: round(v[0], 5) for k, v in P.items()}, "Gamma_Z =", gz)
    res = {}
    fits = {}
    # ---- J/psi + psi(2S)
    def collect(mobj, mu_k, s_k):
        f_, r_ = mobj.values["f"], mobj.values["r"]
        return dict(mu=mobj.values[mu_k], s=mobj.values[s_k], seff=sigma_eff(mobj.values[s_k], f_, r_))
    hj = h["m_jpsi"]
    ej, nj = hj.axes[0].edges, hj.values()
    m, info, e, y = fit_jpsi(ej, nj)
    fits["jpsi"] = (e, y, info["mu"], info, m)
    var = {}
    for lab, kw in {"n2": dict(nCB=2.0), "n10": dict(nCB=10.0), "order2": dict(order=2), "order4": dict(order=4), "range2.7-3.9": dict(rng=(2.7, 3.9))}.items():
        mv, iv, *_ = fit_jpsi(ej, nj, **kw)
        var[lab] = {"mu1": collect(mv, "mu1", "s1"), "mu2": collect(mv, "mu2", "s2"), "valid": iv["valid"] and not any(at_lim(mv, k_) for k_ in ("mu1", "mu2"))}
        log(f"  J/psi variation {lab}: valid {iv['valid']}, mu1 {mv.values['mu1']:.5f}")
    for k, (mu_k, s_k) in {"jpsi": ("mu1", "s1"), "psi2s": ("mu2", "s2")}.items():
        c0 = collect(m, mu_k, s_k)
        res[k] = dict(mu=c0["mu"], mu_err=m.errors[mu_k], sigma=c0["seff"], sigma_core=c0["s"], sigma_err=m.errors[s_k] * c0["seff"] / c0["s"],
                      var_mu=[v[mu_k][ "mu"] for v in var.values() if v["valid"]], var_sigma=[v[mu_k]["seff"] for v in var.values() if v["valid"]])
    res["jpsi"]["chi2"] = (info["deviance"], info["ndf"]); res["jpsi"]["alpha"] = m.values["alpha"]
    log("J/psi region fit: deviance/ndf = %.1f/%d, valid %s; f=%.2f r=%.2f alpha=%.2f" % (info["deviance"], info["ndf"], info["valid"], m.values["f"], m.values["r"], m.values["alpha"]))
    # ---- Upsilon
    hu = h["m_ups"]
    eu, nu = hu.axes[0].edges, hu.values()
    m, info, e, y = fit_ups(eu, nu)
    fits["ups"] = (e, y, info["mu"], info, m)
    var = {}
    for lab, kw in {"n2": dict(nCB=2.0), "n10": dict(nCB=10.0), "order1": dict(order=1), "order3": dict(order=3), "range8.7-11.3": dict(rng=(8.7, 11.3))}.items():
        mv, iv, *_ = fit_ups(eu, nu, **kw)
        var[lab] = {"mu1": collect(mv, "mu1", "s1"), "mu2": collect(mv, "mu2", "s2"), "mu3": collect(mv, "mu3", "s3"),
                    "valid": iv["valid"] and not any(at_lim(mv, k_) for k_ in ("mu1", "mu2", "mu3"))}
        log(f"  Upsilon variation {lab}: valid {var[lab]['valid']}, mu1/2/3 {mv.values['mu1']:.4f} {mv.values['mu2']:.4f} {mv.values['mu3']:.4f}")
    for k, (mu_k, s_k) in {"ups1s": ("mu1", "s1"), "ups2s": ("mu2", "s2"), "ups3s": ("mu3", "s3")}.items():
        c0 = collect(m, mu_k, s_k)
        res[k] = dict(mu=c0["mu"], mu_err=m.errors[mu_k], sigma=c0["seff"], sigma_core=c0["s"], sigma_err=m.errors[s_k] * c0["seff"] / c0["s"],
                      var_mu=[v[mu_k]["mu"] for v in var.values() if v["valid"]], var_sigma=[v[mu_k]["seff"] for v in var.values() if v["valid"]])
    res["ups1s"]["chi2"] = (info["deviance"], info["ndf"]); res["ups1s"]["alpha"] = m.values["alpha"]
    res["ups1s"]["yields"] = {"N1": m.values["N1"], "N2": m.values["N2"], "N3": m.values["N3"]}
    log("Upsilon region fit: deviance/ndf = %.1f/%d, valid %s; f=%.2f r=%.2f alpha=%.2f" % (info["deviance"], info["ndf"], info["valid"], m.values["f"], m.values["r"], m.values["alpha"]))
    # ---- Z
    hz = h["m_z"]
    ez, nz = hz.axes[0].edges, hz.values()
    m0 = P["z"][0]
    m, info, e, y = fit_z(ez, nz, gz, m0)
    fits["z"] = (e, y, info["mu"], info, m)
    var = {}
    for lab, kw in {"range65-115": dict(rng=(65, 115)), "range70-110": dict(rng=(70, 110)), "order1": dict(order=1), "order3": dict(order=3), "n2": dict(nCB=2.0), "n10": dict(nCB=10.0)}.items():
        mv, iv, *_ = fit_z(ez, nz, gz, m0, **kw)
        var[lab] = {"mu": m0 + mv.values["delta"], "seff": sigma_eff(mv.values["s"], mv.values["f"], mv.values["r"]), "valid": iv["valid"] and not at_lim(mv, "delta")}
        log(f"  Z variation {lab}: valid {var[lab]['valid']}, mass {m0 + mv.values['delta']:.4f}, deviance/ndf {iv['deviance']:.0f}/{iv['ndf']}")
    res["z"] = dict(mu=m0 + m.values["delta"], mu_err=m.errors["delta"], sigma=sigma_eff(m.values["s"], m.values["f"], m.values["r"]), sigma_core=m.values["s"],
                    sigma_err=m.errors["s"] * sigma_eff(m.values["s"], m.values["f"], m.values["r"]) / m.values["s"],
                    var_mu=[v["mu"] for v in var.values() if v["valid"]], var_sigma=[v["seff"] for v in var.values() if v["valid"]], chi2=(info["deviance"], info["ndf"]))
    log("Z fit: deviance/ndf = %.1f/%d, valid %s; delta=%.3f GeV core sigma=%.3f f=%.2f r=%.2f alpha=%.2f" % (info["deviance"], info["ndf"], info["valid"], m.values["delta"],
        m.values["s"], m.values["f"], m.values["r"], m.values["alpha"]))
    # ---- summary
    rows = []
    for k in ("jpsi", "psi2s", "ups1s", "ups2s", "ups3s", "z"):
        r = res[k]
        mp = P[k][0]
        syst_mu = float(np.max(np.abs(np.array(r["var_mu"]) - r["mu"])))
        syst_s = float(np.max(np.abs(np.array(r["var_sigma"]) - r["sigma"])))
        off = (r["mu"] / mp - 1) * 1e3
        off_err = r["mu_err"] / mp * 1e3
        off_syst = syst_mu / mp * 1e3
        rows.append(dict(state=k, pdg_mass_GeV=mp, pdg_err_GeV=P[k][1], fit_mass_GeV=r["mu"], fit_mass_err=r["mu_err"], offset_permille=off, offset_stat_permille=off_err,
                         offset_fitsyst_permille=off_syst, sigma_GeV=r["sigma"], sigma_core_GeV=r["sigma_core"], sigma_err=r["sigma_err"], sigma_syst=syst_s, sigma_over_m_percent=r["sigma"] / r["mu"] * 100,
                         sigma_over_m_syst_percent=syst_s / r["mu"] * 100))
        log(f"{k:6s}: m_fit = {r['mu']:.5f} +- {r['mu_err']:.5f} (fit syst {syst_mu:.5f}) GeV, PDG {mp:.5f}; offset {off:+.3f} +- {off_err:.3f} (stat) +- {off_syst:.3f} (fit syst) per mille; "
            f"sigma_eff = {r['sigma']*1e3:.1f} +- {r['sigma_err']*1e3:.1f} (syst {syst_s*1e3:.1f}) MeV = {r['sigma']/r['mu']*100:.2f}% (core {r['sigma_core']*1e3:.1f} MeV)")
    # ---- plots: fits
    plt, hep = setup_mpl()
    fig, axs = plt.subplots(2, 3, figsize=(22, 10), gridspec_kw={"height_ratios": [3, 1]})
    for j, (k, title, logy) in enumerate((("jpsi", "J/$\\psi$, $\\psi$(2S)", True), ("ups", "$\\Upsilon$(1S,2S,3S)", False), ("z", "Z", False))):
        e, y, mu, info, m = fits[k]
        x = 0.5 * (e[1:] + e[:-1])
        ax, rax = axs[0, j], axs[1, j]
        ax.errorbar(x, y / np.diff(e), yerr=np.sqrt(np.maximum(y, 1)) / np.diff(e), fmt="o", color="black", ms=3, label="Student (CMS Open Data, 2016H, 2 files)")
        ax.step(x, mu / np.diff(e), where="mid", color="tab:red", label="fit")
        ax.set_yscale("log" if logy else "linear")
        ax.set_ylabel("events / GeV")
        ax.set_title(title)
        ax.legend(fontsize=11)
        pull = np.sign(y - mu) * np.sqrt(np.maximum(2 * (mu - y + np.where(y > 0, y * np.log(np.where(y > 0, y, 1) / np.maximum(mu, 1e-12)), 0)), 0))
        rax.bar(x, pull, width=np.diff(e), color="gray")
        rax.set_ylabel("pull"); rax.set_xlabel("$m_{\\mu\\mu}$ [GeV]"); rax.set_ylim(-5, 5)
        ax.text(0.02, 0.02, f"deviance/ndf = {info['deviance']:.0f}/{info['ndf']}", transform=ax.transAxes, fontsize=12)
        open_data_label(ax, hep, fontsize=14)
    savefig(fig, "M1a_peak_fits")
    # ---- summary: offset and resolution vs PDG
    fig, (ax, rax) = plt.subplots(2, 1, figsize=(10, 10), sharex=True, gridspec_kw={"height_ratios": [1, 1]})
    mp = np.array([r["pdg_mass_GeV"] for r in rows])
    off = np.array([r["offset_permille"] for r in rows]); eo = np.array([np.hypot(r["offset_stat_permille"], r["offset_fitsyst_permille"]) for r in rows])
    ax.errorbar(mp, off, yerr=eo, fmt="o", color="black", label="Student fit (stat $\\oplus$ fit syst.)")
    ax.axhline(0, color="gray", ls="--")
    ax.axhspan(-3, 3, color="tab:green", alpha=0.15, label="$\\pm$3 per mille (scale offset removed by muon momentum corrections)")
    ax.set_xscale("log"); ax.set_ylabel("$(m_{fit}/m_{PDG}-1)$ [per mille]"); ax.legend(fontsize=11, loc="lower left")
    for r, x_ in zip(rows, mp):
        ax.annotate(LABEL[r["state"]], (x_, off[rows.index(r)]), textcoords="offset points", xytext=(5, 8), fontsize=12)
    sg = np.array([r["sigma_over_m_percent"] for r in rows]); es = np.array([np.hypot(r["sigma_err"], r["sigma_syst"]) / r["fit_mass_GeV"] * 100 for r in rows])
    rax.errorbar(mp, sg, yerr=es, fmt="s", color="tab:blue", label="Student fit $\\sigma_{core}/m$")
    rax.set_ylabel("$\\sigma/m$ [%]"); rax.set_xlabel("PDG mass [GeV]"); rax.legend(fontsize=11)
    rax.text(0.03, 0.9, "PDG %s; CMS muon pT resolution 1%% (barrel), <3%% (endcaps) for pT 20-100 GeV (CMS-SMP-17-010)" % P["z"][2], transform=rax.transAxes, fontsize=10)
    open_data_label(ax, hep)
    savefig(fig, "M1b_offset_and_resolution_vs_PDG")
    worst = max(abs(r["offset_permille"]) for r in rows)
    for r in rows:
        r["nsigma_offset"] = abs(r["offset_permille"]) / float(np.hypot(r["offset_stat_permille"], r["offset_fitsyst_permille"]))
    nmax = max(r["nsigma_offset"] for r in rows)
    verdict = "INCONSISTENT" if nmax > 3 else ("TENSION" if nmax > 2 else "CONSISTENT")
    all_neg = all(r["offset_permille"] < 0 for r in rows)
    save_result("M1", student_result="peak positions and core widths of J/psi, psi(2S), Upsilon(1S,2S,3S), Z from fits to histograms.pkl (unchanged)",
                counterpart={"report": "PDG", "source": f"PDG API (pdgapi.lbl.gov) edition {P['z'][2]}", "hepdata_table": None},
                level="exact (constants): fitted detector-level peak positions vs PDG masses; no momentum corrections applied",
                statistic=worst, statistic_name="largest |mass offset| in per mille", ndf=None, p_value=None, ratio=None, rows=rows,
                fit_quality={k: dict(deviance=res[k]["chi2"][0], ndf=res[k]["chi2"][1]) for k in ("jpsi", "ups1s", "z")}, gamma_Z_fixed_GeV=gz,
                max_nsigma=nmax, all_offsets_negative=all_neg, expected="scale offsets of order 1 per mille (up to a few) and sigma/m of 1-1.5 % without muon momentum corrections; CMS-SMP-17-010: pT resolution 1% barrel, <3% endcaps (20-100 GeV)",
                verdict=verdict, reason="Formal test against the PDG masses with stat + fit-systematic uncertainties. All offsets are negative (-0.7 to -2.2 per mille), "
                "Upsilon(1S), (2S) deviate by >3 sigma formally; the size is that of an uncorrected tracker momentum scale (typical size of muon momentum-scale corrections, ~0.1-0.2 %, not re-measured here), not a physics disagreement.")


if __name__ == "__main__":
    main()
