#!/usr/bin/env python3
"""D5 (shape) + extra: inclusive m_jj spectrum of the student (rebuilt from the condor skims) vs CMS-EXO-16-056
(JHEP 08 (2018) 130, INSPIRE 1676214, HEPData table 'Differential dijet spectrum (High-mass analysis)').

Usage: compare_d5_inclusive.py --cache <scratch cache dir> --skims '<glob of output_d*.npz>'
Step 1 streams the data skims one file at a time (about 2-3 GB RSS at most) and caches the per-category m_jj histograms
in <cache>/d5_student_hist.npz.  The same pass re-derives the student's 1b / 2b spectra: they must equal the student's
HEPData record (closure check of the rebuilt selection).
"""
import argparse
import glob
import json
import sys
import time

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import *   # noqa

sys.path.insert(0, str(STUDENT_DIR))
import dijetlib as D   # student's helper module (read only)

GOLDEN_URL = "https://opendata.cern.ch/record/14220/files/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"


def build(cache, skims):
    out = Path(cache) / "d5_student_hist.npz"
    if out.exists():
        return dict(np.load(out))
    summ = json.load(open(STUDENT_DIR / "summary.json"))
    thr = summ["trigger"]["threshold_mjj_GeV"]
    wp_m = summ["btag_wp_deepjet_2016postVFP_UL"]["M"]
    golden = D.golden_keys(fetch(GOLDEN_URL, Path(cache) / "opendata" / "golden.json"))
    edges = D.DIJET_EDGES[(D.DIJET_EDGES >= thr) & (D.DIJET_EDGES <= 14000)]
    h = {c: np.zeros(len(edges) - 1) for c in ("incl", "1b", "2b", "incl_deta13")}
    paths = sorted(glob.glob(skims))
    t0 = time.time()
    nsig_mask = None
    for p in paths:
        info = json.loads(str(np.load(p)["info"]))
        mask = np.uint32((1 << info["n_sig_trigs"]) - 1)
        # student's own streaming loader: golden JSON applied to data, m_jj > threshold
        for s, o, nb, na in D.iter_events([p], ["mjj", "eta1", "eta2", "btag1", "btag2", "trig", "run", "lumi"],
                                          {"data": thr}, golden, only="data"):
            if s != "data":
                continue
            base = ((o["trig"] & mask) > 0) & (o["mjj"] > thr)
            deta = np.abs(o["eta1"] - o["eta2"])
            h["incl_deta13"] += np.histogram(o["mjj"][base & (deta < 1.3)], edges)[0]   # diagnostic only (CMS cut)
            m = base & (deta < 1.1)
            nb_ = (o["btag1"][m] > wp_m).astype(int) + (o["btag2"][m] > wp_m).astype(int)
            mj = o["mjj"][m]
            h["incl"] += np.histogram(mj, edges)[0]
            h["1b"] += np.histogram(mj[nb_ >= 1], edges)[0]
            h["2b"] += np.histogram(mj[nb_ >= 2], edges)[0]
        log(f"{Path(p).name}: cumulative incl events {h['incl'].sum():.0f} ({time.time()-t0:.0f} s)")
    np.savez(out, edges=edges, **h)
    return dict(np.load(out))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--skims", required=True)
    ap.add_argument("--min-counts", type=float, default=20.0, help="min counts per merged bin in both spectra")
    a = ap.parse_args()
    H = build(a.cache, a.skims)
    edges = H["edges"]
    # ---- closure against the student's published HEPData record
    import yaml
    clo = {}
    for cat in ("1b", "2b"):
        d = yaml.safe_load(open(STUDENT_DIR / "hepdata" / f"mjj_spectrum_{cat}.yaml"))
        v = np.array([x["value"] for x in d["dependent_variables"][0]["values"]])
        clo[cat] = {"max_abs_diff": float(np.max(np.abs(v - H[cat][: len(v)]))), "n_bins": len(v),
                    "total_student_hepdata": float(v.sum()), "total_rebuilt": float(H[cat][: len(v)].sum())}
    log("closure vs student HEPData:", clo)
    summ = json.load(open(STUDENT_DIR / "summary.json"))
    lumi_fb = summ["luminosity"]["recorded_fb"]

    # ---- CMS-EXO-16-056
    rec = hepdata_dir(a.cache, 1676214)
    t = read_table(rec, "Differential dijet spectrum (High-mass analysis)")
    iv = t["indep"][0]
    c_lo, c_hi = iv["low"], iv["high"]
    c_n = t["dep"][0]["value"]                       # event yield
    c_xs = t["dep"][1]["value"]                     # pb/TeV
    ok = c_n > 0
    L_cms = np.median(c_n[ok] / (c_xs[ok] * (c_hi - c_lo)[ok] / 1e3))     # pb^-1
    log(f"implied CMS luminosity from the table: {L_cms/1e3:.2f} fb-1")
    # same binning: map CMS bins onto student's edges
    s_n = H["incl"]
    idx = [int(np.where(np.isclose(edges[:-1], lo))[0][0]) for lo in c_lo]
    assert all(np.isclose(edges[i + 1], hi) for i, hi in zip(idx, c_hi))
    s_n_c = s_n[idx]
    # common range: lowest CMS edge 1246 GeV; high-mass bins merged until >= min-counts in both
    ed, (ns, nc) = merge_high_bins(c_lo.tolist() + [c_hi[-1]], [s_n_c, c_n], a.min_counts, [s_n_c, c_n])
    chi2, ndf = two_sample_chi2(ns, nc)
    p = pvalue(chi2, ndf)
    Ns, Nc = ns.sum(), nc.sum()
    xc = np.sqrt(ed[1:] * ed[:-1])
    ps, pc = ns / Ns, nc / Nc
    r = ps / pc
    rerr = r * np.sqrt(1 / ns + 1 / nc)
    sl = ratio_slope(xc / 1e3, r, rerr)
    log(f"D5 shape: chi2/ndf = {chi2:.1f}/{ndf}, p = {p:.2e}; ratio slope = {sl['b']:.4f} +- {sl['b_err']:.4f} per TeV; "
        f"range {ed[0]:.0f}-{ed[-1]:.0f}, {len(ns)} bins, N_student={Ns:.0f}, N_CMS={Nc:.0f}")

    # ---- diagnostic: mass-scale factor s (student spectrum = CMS template at m/s), Poisson likelihood
    from iminuit import Minuit
    fit_c = D.fit_background(np.array(ed), nc, 4)          # CMS template, 4-parameter dijet function, merged bins
    par = fit_c["par"]

    def mu_s(A, s):
        return A * D.bin_integral(np.array(ed) / s, *par)

    def nll(A, s):
        mu = np.maximum(mu_s(A, s), 1e-12)
        return float(np.sum(mu - ns * np.log(mu)))
    m = Minuit(nll, A=Ns / max(D.bin_integral(np.array(ed), *par).sum(), 1e-9), s=1.0)
    m.errordef = Minuit.LIKELIHOOD
    m.limits["s"] = (0.8, 1.25)
    m.migrad()
    s_fit, s_err = float(m.values["s"]), float(m.errors["s"])
    dev1 = D.deviance(ns, mu_s(m.values["A"], s_fit))
    m1 = Minuit(nll, A=m.values["A"], s=1.0)
    m1.errordef = Minuit.LIKELIHOOD
    m1.fixed["s"] = True
    m1.migrad()
    dev0 = D.deviance(ns, mu_s(m1.values["A"], 1.0))
    log(f"mass-scale diagnostic: s = {s_fit:.4f} +- {s_err:.4f}; deviance {dev0:.1f} (s=1) -> {dev1:.1f} (s free), ndf {ndf}/{ndf-1}")

    # ---- absolute ratio (not a test: Delta eta cut and wide jets differ), student dsigma/dm vs CMS in common bins
    ds = ns / (lumi_fb * 1e3 * np.diff(ed)) * 1e3             # pb/TeV
    dc = nc / (L_cms * np.diff(ed)) * 1e3
    absr = float(np.sum(ns) / (lumi_fb * 1e3) / (np.sum(nc) / L_cms))
    log(f"absolute: sum(student)/L_s over sum(CMS)/L_cms = {absr:.3f}")

    # ---- supplementary diagnostic: the student's own events with the CMS cut |deta| < 1.3 (selection of the CMS paper)
    allcms_e = np.array(c_lo.tolist() + [c_hi[-1]])
    pos = [int(np.where(np.isclose(allcms_e, e))[0][0]) for e in ed[:-1]]
    ns13 = np.add.reduceat(H["incl_deta13"][idx], pos)
    chi13, ndf13 = two_sample_chi2(ns13, nc)
    p13 = pvalue(chi13, ndf13)
    r13 = (ns13 / ns13.sum()) / pc
    sl13 = ratio_slope(xc / 1e3, r13, r13 * np.sqrt(1 / ns13 + 1 / nc))
    f_deta = float(ns.sum() / ns13.sum())          # fraction of |deta|<1.3 events that have |deta|<1.1 (student data)
    abs13 = float(ns13.sum() / (lumi_fb * 1e3) / (np.sum(nc) / L_cms))
    log(f"supplementary |deta|<1.3: chi2/ndf = {chi13:.1f}/{ndf13}, p = {p13:.2e}, slope {sl13['b']:+.4f} +- {sl13['b_err']:.4f}/TeV; "
        f"N(<1.1)/N(<1.3) = {f_deta:.3f}; absolute ratio with the same deta cut = {abs13:.3f}")

    # ---- diagnostic: mass-scale s needed to reproduce the ABSOLUTE yield (CMS m_W = s * student m), with the measured
    #      |deta| acceptance factor and the luminosity ratio, no free normalisation
    def mu_abs(s_):
        return (lumi_fb * 1e3 / L_cms) * f_deta * D.bin_integral(np.array(ed) * s_, *par) / 1.0

    def nll_abs(s_):
        mu = np.maximum(mu_abs(s_), 1e-12)
        return float(np.sum(mu - ns * np.log(mu)))
    ma = Minuit(nll_abs, s_=1.0)
    ma.errordef = Minuit.LIKELIHOOD
    ma.limits["s_"] = (0.8, 1.3)
    ma.migrad()
    s_abs, s_abs_err = float(ma.values["s_"]), float(ma.errors["s_"])
    # mass-scale-only fit has the Jacobian: student dm = dm_W / s  -> already inside bin_integral(edges*s)
    dev_abs1 = D.deviance(ns, mu_abs(1.0))
    dev_abs = D.deviance(ns, mu_abs(s_abs))
    log(f"absolute mass-scale diagnostic: s = {s_abs:.4f} +- {s_abs_err:.4f}; deviance {dev_abs1:.0f} (s=1) -> {dev_abs:.0f}")

    # ---- plot
    plt, hep = setup_mpl()
    fig, (ax, rax) = plt.subplots(2, 1, figsize=(10, 10), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    w = np.diff(ed)
    ax.errorbar(xc, ps / w * 1e3, yerr=np.sqrt(ns) / Ns / w * 1e3, fmt="o", color="black", ms=4,
                label="Student: JetHT 2016G+H, AK4 CHS, |$\\Delta\\eta$|<1.1")
    ax.errorbar(xc, pc / w * 1e3, yerr=np.sqrt(nc) / Nc / w * 1e3, fmt="s", color="tab:red", ms=4, mfc="none",
                label="CMS-EXO-16-056, wide jets, |$\\Delta\\eta$|<1.3, 36 fb$^{-1}$")
    ax.set_yscale("log")
    ax.set_ylabel("Normalised $(1/N)\\,dN/dm_{jj}$ [1/TeV]")
    ax.legend(fontsize=14, loc="upper right")
    ax.text(0.04, 0.05, f"$\\chi^2$/ndf = {chi2:.0f}/{ndf} (stat. only), common range {ed[0]:.0f}-{ed[-1]:.0f} GeV\n"
            f"ratio slope = {sl['b']:+.3f} $\\pm$ {sl['b_err']:.3f} / TeV", transform=ax.transAxes, fontsize=13)
    rax.errorbar(xc, r, yerr=rerr, fmt="o", color="black", ms=4)
    rax.axhline(1, color="gray", ls="--")
    xx = np.linspace(xc.min(), xc.max(), 50)
    rax.plot(xx, sl["a"] + sl["b"] * (xx / 1e3 - sl["xmean"]), color="tab:blue", lw=1.5, label="linear fit")
    rax.set_ylabel("Student / CMS")
    rax.set_xlabel("$m_{jj}$ [GeV]")
    rax.set_ylim(0.6, 1.4)
    rax.legend(fontsize=12)
    open_data_label(ax, hep, lumi=round(lumi_fb, 1))
    savefig(fig, "D5_inclusive_mjj_vs_EXO16056")

    # ---- absolute ratio per bin (supplementary plot)
    rabs11 = (ns / lumi_fb) / (nc / (L_cms / 1e3))
    rabs13 = (ns13 / lumi_fb) / (nc / (L_cms / 1e3))
    e11 = rabs11 * np.sqrt(1 / ns + 1 / nc)
    e13 = rabs13 * np.sqrt(1 / ns13 + 1 / nc)
    sl_abs = ratio_slope(xc / 1e3, rabs13, e13)
    log("absolute ratio per merged bin (|deta|<1.3):", np.round(rabs13, 3).tolist())
    log(f"absolute ratio |deta|<1.3: weighted mean {sl_abs['c0']:.3f}, slope {sl_abs['b']:+.4f} +- {sl_abs['b_err']:.4f} per TeV")
    fig, ax = plt.subplots(figsize=(10, 7))
    ax.errorbar(xc, rabs11, yerr=e11, fmt="o", color="black", ms=4, label="|$\\Delta\\eta$|<1.1 (student selection)")
    ax.errorbar(xc, rabs13, yerr=e13, fmt="s", color="tab:blue", ms=4, mfc="none", label="|$\\Delta\\eta$|<1.3 (CMS cut, student events)")
    ax.axhline(1, color="gray", ls="--")
    ax.set_xlabel("$m_{jj}$ [GeV]")
    ax.set_ylabel("Student $d\\sigma/dm$ / CMS-EXO-16-056")
    ax.set_ylim(0.2, 1.2)
    ax.legend(fontsize=14, loc="lower right")
    ax.text(0.04, 0.95, "absolute, $L_{student}$=%.1f fb$^{-1}$, $L_{CMS}$=%.1f fb$^{-1}$" % (lumi_fb, L_cms / 1e3), transform=ax.transAxes, fontsize=13, va="top")
    open_data_label(ax, hep, lumi=round(lumi_fb, 1))
    savefig(fig, "D5b_inclusive_absolute_ratio_vs_EXO16056")

    verdict = "INCONSISTENT" if nsigma(p) > 3 else ("TENSION" if nsigma(p) > 2 else "CONSISTENT")
    save_result(
        "D5", student_result="inclusive m_jj spectrum, 2016G+H JetHT, AK4 CHS, |deta|<1.1, rebuilt from skims (incl. golden JSON, trigger OR)",
        counterpart={"report": "CMS-EXO-16-056", "inspire": 1676214, "hepdata_record": "ins1676214",
                     "hepdata_table": "Differential dijet spectrum (High-mass analysis)", "paper": "JHEP 08 (2018) 130, arXiv:1806.00843"},
        level="shape: detector-level counts (student) vs CMS observed event yields (detector level, wide jets); both normalised in the common range",
        statistic=chi2, statistic_name="two-sample Pearson chi2 (stat. errors only)", ndf=ndf, p_value=p, nsigma=nsigma(p),
        ratio=None, ratio_slope_per_TeV=sl["b"], ratio_slope_err=sl["b_err"], range_GeV=[float(ed[0]), float(ed[-1])],
        n_bins=len(ns), mass_scale_fit={"s": s_fit, "s_err": s_err, "deviance_s1": dev0, "deviance_sfree": dev1},
        absolute_ratio_student_over_cms=absr, supplementary_deta13={"chi2": chi13, "ndf": ndf13, "p_value": p13, "slope_per_TeV": sl13["b"],
        "slope_err": sl13["b_err"], "frac_deta11_over_deta13": f_deta, "absolute_ratio_same_deta_cut": abs13,
        "abs_ratio_deta13_mean": sl_abs["c0"], "abs_ratio_deta13_slope_per_TeV": sl_abs["b"], "abs_ratio_deta13_slope_err": sl_abs["b_err"],
        "abs_mass_scale_fit": {"s": s_abs, "s_err": s_abs_err, "deviance_s1": dev_abs1, "deviance_sfit": dev_abs}}, cms_implied_lumi_fb=L_cms / 1e3, student_lumi_fb=lumi_fb, closure=clo,
        verdict=verdict,
        reason="Shape differs by a mass-dependent slope; CMS uses wide jets (FSR recombination, mjj shifted up), |deta|<1.3 vs 1.1, |eta|<2.5 vs 2.4; "
               "a mass-scale factor s absorbs the slope (see mass_scale_fit). Statistical errors only.")
    save_result(
        "D5b", student_result="inclusive dsigma/dm = N/(L dm), same data and selection as D5 (|deta|<1.1), L = %.2f fb^-1" % lumi_fb,
        counterpart={"report": "CMS-EXO-16-056", "inspire": 1676214, "hepdata_record": "ins1676214",
                     "hepdata_table": "Differential dijet spectrum (High-mass analysis)", "paper": "JHEP 08 (2018) 130, arXiv:1806.00843"},
        level="absolute: student detector-level N/(L dm) vs CMS cross section (pb/TeV, L = 35.9 fb^-1 recovered from the table); CMS uses |deta|<1.3 and wide jets",
        statistic=None, statistic_name="n.a. (ratio far outside any plausible systematic envelope)", ndf=None, p_value=None, ratio=absr,
        ratio_same_deta_cut=abs13, frac_deta11_over_deta13=f_deta, ratio_slope_deta13_per_TeV=sl_abs["b"], ratio_slope_err=sl_abs["b_err"],
        mass_scale_needed_for_absolute=s_abs, mass_scale_residual_deviance=dev_abs, rate_per_run_diagnostic="see D5c_diag",
        verdict="INCONSISTENT",
        reason="Ratio %.3f (|deta|<1.1 vs 1.3); %.3f after correcting the |deta| acceptance with the student's own data; flat in m_jj (slope %.4f +- %.4f /TeV) and uniform in run, so not a "
               "mass-scale/wide-jet effect (a pure mass-scale fit needs s = %.3f and then leaves deviance %.0f for %d bins). Cause not identified." % (absr, abs13, sl_abs["b"], sl_abs["b_err"], s_abs, dev_abs, len(ns)))


if __name__ == "__main__":
    main()
