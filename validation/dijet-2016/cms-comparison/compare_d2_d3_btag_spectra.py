#!/usr/bin/env python3
"""D2 (shape) and D3 (absolute): the student's 2 b-tag and >=1 b-tag m_jj spectra vs the 2016 spectra of CMS-EXO-20-008
(INSPIRE paper 2676943, PRD 108 (2023) 012009; HEPData ins1920627 is attached to the PAS CMS-PAS-EXO-20-008).

CMS tables (HEPData record ins1920627), 2016 column of Figure 3: dsigma/dm [fb/GeV] vs bin centre, Poisson errors:
  'Figure 3 first row first column'   double b
  'Figure 3 second row first column'  single b (exactly one b-tagged jet)
  'Figure 3 fourth row first column'  inclusive single b ('b*' category)
Bin edges are not in the record: they are recovered from the bin centres with the standard CMS dijet binning.
Event counts are recovered as N = (value/error)^2 (Poisson errors), and the luminosity actually used as N/(value * width).

Usage: compare_d2_d3_btag_spectra.py --cache <cache dir>
"""
import argparse
import json
import sys

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import *   # noqa

sys.path.insert(0, str(STUDENT_DIR))
import dijetlib as D

REC = 1920627
T_2B = "Figure 3 first row first column"
T_1B = "Figure 3 second row first column"
T_INCL = "Figure 3 fourth row first column"
T_MU = "Figure 3 third row first column"


def cms_table(rec, name):
    t = read_table(rec, name)
    xc = t["indep"][0]["value"]
    dv = t["dep"][0]
    v = dv["value"]
    err = next(iter(dv["errors"].values()))
    # standard dijet binning -> edges
    E = D.DIJET_EDGES
    lo = np.empty(len(xc)); hi = np.empty(len(xc))
    for i, c in enumerate(xc):
        j = np.where(np.isclose(0.5 * (E[:-1] + E[1:]), c, atol=0.01))[0]
        assert len(j) == 1, (name, c)
        lo[i], hi[i] = E[j[0]], E[j[0] + 1]
    w = hi - lo
    ok = (v > 1e-6) & (err > 1e-6)
    n = np.where(ok, (v / np.where(ok, err, 1)) ** 2, 0.0)
    lumi_impl = np.where(ok, n / (np.where(ok, v, 1) * w), np.nan)      # fb^-1
    return dict(lo=lo, hi=hi, w=w, xs=v, err=err, n=n, ok=ok, lumi=lumi_impl, units=dv["units"], qual=dv["qualifiers"],
                header=dv["name"], desc=t["meta"]["description"])


def student_spectra():
    s = json.load(open(STUDENT_DIR / "summary.json"))
    edges = np.array(s["fit"]["1b"]["fit_edges_GeV"])
    n1 = np.array(s["fit"]["1b"]["data_counts"]); n2 = np.array(s["fit"]["2b"]["data_counts"])
    # cross-check against the student's HEPData record (rounded to 5 significant digits there)
    import yaml
    chk = {}
    for cat, n in (("1b", n1), ("2b", n2)):
        d = yaml.safe_load(open(STUDENT_DIR / "hepdata" / f"mjj_spectrum_{cat}.yaml"))
        v = np.array([x["value"] for x in d["dependent_variables"][0]["values"]])
        chk[cat] = float(np.max(np.abs(v - n)))
    return edges, n1, n2, s["luminosity"]["recorded_fb"], chk


def shape_test(name, edges_s, n_s, cms, min_counts, tag, extra=None):
    """normalised shape comparison on the common range; returns dict + plot"""
    lo_c = cms["lo"]
    first = lo_c[cms["ok"]][0]
    sel = np.where(np.isclose(edges_s[:-1][:, None], lo_c[None, :]).any(1))[0]
    s_lo = edges_s[:-1][sel]
    ci = {float(l): i for i, l in enumerate(lo_c)}
    idx = [ci[float(l)] for l in s_lo]
    ns = n_s[sel]
    nc = cms["n"][idx]
    e = np.append(s_lo, edges_s[sel[-1] + 1])
    ed, (ms, mc) = merge_high_bins(e, [ns, nc], min_counts, [ns, nc])
    chi2, ndf = two_sample_chi2(ms, mc)
    p = pvalue(chi2, ndf)
    xc = np.sqrt(ed[1:] * ed[:-1])
    ps, pc = ms / ms.sum(), mc / mc.sum()
    r = ps / pc
    rerr = r * np.sqrt(1 / ms + 1 / mc)
    sl = ratio_slope(xc / 1e3, r, rerr)
    return dict(edges=ed, ns=ms, nc=mc, chi2=chi2, ndf=ndf, p=p, xc=xc, ps=ps, pc=pc, r=r, rerr=rerr, slope=sl,
                range=(float(ed[0]), float(ed[-1])), Ns=float(ms.sum()), Nc=float(mc.sum()), first_cms_edge=float(first))


def plot_shape(res, tag, student_label, cms_label, cms_ref, lumi_fb, ylabel="Normalised  $(1/N)\\,dN/dm_{jj}$ [1/TeV]"):
    plt, hep = setup_mpl()
    fig, (ax, rax) = plt.subplots(2, 1, figsize=(10, 10), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    w = np.diff(res["edges"])
    ax.errorbar(res["xc"], res["ps"] / w * 1e3, yerr=res["ps"] / np.sqrt(res["ns"]) / w * 1e3, fmt="o", color="black", ms=4, label=student_label)
    ax.errorbar(res["xc"], res["pc"] / w * 1e3, yerr=res["pc"] / np.sqrt(res["nc"]) / w * 1e3, fmt="s", color="tab:red", ms=4, mfc="none", label=cms_label)
    ax.set_yscale("log")
    ax.set_ylabel(ylabel)
    ax.legend(fontsize=13, loc="upper right")
    sl = res["slope"]
    ax.text(0.04, 0.05, f"$\\chi^2$/ndf = {res['chi2']:.1f}/{res['ndf']} (p = {res['p']:.1e}, stat. only)\nrange {res['range'][0]:.0f}-{res['range'][1]:.0f} GeV; "
            f"slope = {sl['b']:+.3f} $\\pm$ {sl['b_err']:.3f} / TeV\n{cms_ref}", transform=ax.transAxes, fontsize=12)
    rax.errorbar(res["xc"], res["r"], yerr=res["rerr"], fmt="o", color="black", ms=4)
    rax.axhline(1, color="gray", ls="--")
    xx = np.linspace(res["xc"].min(), res["xc"].max(), 50)
    rax.plot(xx, sl["a"] + sl["b"] * (xx / 1e3 - sl["xmean"]), color="tab:blue", lw=1.5)
    rax.set_ylabel("Student / CMS")
    rax.set_xlabel("$m_{jj}$ [GeV]")
    rax.set_ylim(0.5, 1.5)
    open_data_label(ax, hep, lumi=round(lumi_fb, 1))
    return fig


def verdict_from(p, slope=None, slope_err=None):
    """INCONSISTENT: p-value above 3 sigma; TENSION: 2-3 sigma, or a ratio slope more than 3 sigma from zero (clear trend)."""
    n = nsigma(p)
    trend = slope is not None and abs(slope) / slope_err > 3
    return "INCONSISTENT" if n > 3 else ("TENSION" if (n > 2 or trend) else "CONSISTENT")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    ap.add_argument("--min-counts", type=float, default=20.0)
    a = ap.parse_args()
    rec = hepdata_dir(a.cache, REC)
    edges_s, n1, n2, lumi_fb, chk = student_spectra()
    log("student HEPData vs summary.json counts, max |diff|:", chk)
    tabs = {k: cms_table(rec, k) for k in (T_2B, T_1B, T_INCL, T_MU)}
    # ---- what is the normalisation of the 2016 tables? ('LUMINOSITY: 138' qualifier)
    lum = {k: (float(np.nanmedian(t["lumi"])), float(np.nanstd(t["lumi"]) / np.nanmean(t["lumi"]))) for k, t in tabs.items()}
    log("implied luminosity N/(sigma*width) per table [fb-1] (median, rel. spread):", lum)
    log("qualifiers of the 2016 tables:", tabs[T_2B]["qual"])
    # integer-ness of the recovered counts (rounding of value/error to 5 digits)
    nn = tabs[T_2B]["n"][tabs[T_2B]["ok"]]
    log("recovered counts, deviation from nearest integer / sqrt(N): max", float(np.max(np.abs(nn - np.round(nn)) / np.sqrt(nn))))
    L_cms = lum[T_2B][0]
    # does the inclusive table equal 1b+2b ?
    sum12 = tabs[T_1B]["xs"] + tabs[T_2B]["xs"]
    r41 = tabs[T_INCL]["xs"] / sum12
    okm = tabs[T_INCL]["ok"] & tabs[T_2B]["ok"] & tabs[T_1B]["ok"]
    log("CMS inclusive-single-b / (single-b + double-b), first 6 bins:", np.round(r41[okm][:6], 3).tolist(), " last of well populated:", np.round(r41[okm][-3:], 3).tolist())

    # ======================================================================= D2: shapes
    plt, hep = setup_mpl()
    out = {}
    # (a) 2b vs double b
    cm2 = tabs[T_2B]
    r2 = shape_test("2b", edges_s, n2, cm2, a.min_counts, "2b")
    # (b) >=1b vs inclusive single b (name-matched) and vs 1b+2b (definition-matched)
    cm4 = tabs[T_INCL]
    r4 = shape_test(">=1b vs incl", edges_s, n1, cm4, a.min_counts, "1b")
    cm12 = dict(cm4)
    cm12["n"] = tabs[T_1B]["n"] + tabs[T_2B]["n"]
    cm12["xs"] = sum12
    cm12["ok"] = tabs[T_1B]["ok"] & tabs[T_2B]["ok"]
    r12 = shape_test(">=1b vs 1b+2b", edges_s, n1, cm12, a.min_counts, "1b12")
    # (c) exclusive 1b = student(>=1b) - student(2b) vs single b
    r1x = shape_test("excl 1b", edges_s, n1 - n2, tabs[T_1B], a.min_counts, "1bx")
    labS2 = "Student: 2 b tags (DeepJet M), AK4 CHS, 2016G+H"
    labS1 = "Student: $\\geq$1 b tag (DeepJet M), AK4 CHS, 2016G+H"
    refC = "CMS-EXO-20-008 (PRD 108 (2023) 012009), 2016, wide jets"
    fig = plot_shape(r2, "2b", labS2, "CMS-EXO-20-008, double b, 2016 (36.3 fb$^{-1}$)", refC, lumi_fb)
    savefig(fig, "D2a_2b_shape_vs_EXO20008")
    fig = plot_shape(r4, "1b", labS1, "CMS-EXO-20-008, inclusive single b, 2016", refC, lumi_fb)
    savefig(fig, "D2b_ge1b_shape_vs_EXO20008")
    fig = plot_shape(r12, "1b12", labS1, "CMS-EXO-20-008, single b + double b, 2016", refC, lumi_fb)
    savefig(fig, "D2b2_ge1b_shape_vs_EXO20008_1bplus2b")
    fig = plot_shape(r1x, "1bx", "Student: exactly 1 b tag (=$\\geq$1b minus 2b)", "CMS-EXO-20-008, single b, 2016", refC, lumi_fb)
    savefig(fig, "D2c_excl1b_shape_vs_EXO20008")

    def pack(r):
        return dict(chi2=r["chi2"], ndf=r["ndf"], p_value=r["p"], nsigma=nsigma(r["p"]), range_GeV=r["range"], n_bins=len(r["ns"]),
                    slope_per_TeV=r["slope"]["b"], slope_err=r["slope"]["b_err"], ratio_mean=r["slope"]["c0"], ratio_mean_err=r["slope"]["c0_err"],
                    ratio_first_bin=float(r["r"][0]), ratio_last_bin=float(r["r"][-1]), N_student=r["Ns"], N_cms=r["Nc"])
    for k, r in (("2b", r2), ("ge1b_vs_incl", r4), ("ge1b_vs_1bplus2b", r12), ("excl1b", r1x)):
        out[k] = pack(r)
        log(f"D2 {k}: chi2/ndf = {r['chi2']:.1f}/{r['ndf']}, p = {r['p']:.2e}, slope = {r['slope']['b']:+.3f} +- {r['slope']['b_err']:.3f} /TeV, "
            f"ratio(first/last) = {r['r'][0]:.3f}/{r['r'][-1]:.3f}, range {r['range']}")

    cparts = lambda tab: {"report": "CMS-EXO-20-008", "inspire_paper": 2676943, "paper": "PRD 108 (2023) 012009, arXiv:2205.01835",
                          "hepdata_record": "ins1920627 (attached to PAS CMS-PAS-EXO-20-008)", "hepdata_table": tab}
    common_reason = ("Statistics only (student N and CMS N from Poisson errors). CMS: wide jets (R=1.1 FSR recombination), |eta|<2.5, DeepJet with data/MC scale factors, "
                     "JEC of the 2016 legacy reprocessing, all of 2016 (eras B-H); student: AK4 CHS, |eta|<2.4, DeepJet medium, UL JEC, G+H only. ")
    save_result("D2a", student_result="m_jj spectrum, 2 b tags (both leading AK4 jets DeepJet medium), 2016G+H, |deta|<1.1, mjj>1058 GeV",
                counterpart=cparts(T_2B), level="shape: detector-level event counts vs CMS dsigma/dm (fb/GeV, detector level, not unfolded), both normalised on the common range",
                statistic=r2["chi2"], statistic_name="two-sample Pearson chi2 (stat. only)", ndf=r2["ndf"], p_value=r2["p"], ratio=None,
                details=out["2b"], verdict=verdict_from(r2["p"], r2["slope"]["b"], r2["slope"]["b_err"]), reason=common_reason)
    save_result("D2b", student_result="m_jj spectrum, >=1 b tag (inclusive of 2b), 2016G+H, |deta|<1.1",
                counterpart=cparts(T_INCL), level="shape (normalised, detector level)", statistic=r4["chi2"], statistic_name="two-sample Pearson chi2 (stat. only)",
                ndf=r4["ndf"], p_value=r4["p"], ratio=None, details=out["ge1b_vs_incl"], alt_definition_match=out["ge1b_vs_1bplus2b"],
                verdict=verdict_from(r4["p"], r4["slope"]["b"], r4["slope"]["b_err"]),
                reason=common_reason + "The CMS 'inclusive single b' table is NOT the sum of the single-b and double-b tables (ratio 1.11-1.17, mass dependent, see details); "
                       "the alternative counterpart 1b+2b is given in alt_definition_match.")
    save_result("D2b_alt", student_result="m_jj spectrum, >=1 b tag, 2016G+H, |deta|<1.1 (definition-matched counterpart: single b + double b)",
                counterpart=cparts("Figure 3 first row + second row first column (sum of N)"), level="shape (normalised, detector level)", statistic=r12["chi2"],
                statistic_name="two-sample Pearson chi2 (stat. only)", ndf=r12["ndf"], p_value=r12["p"], ratio=None, details=out["ge1b_vs_1bplus2b"],
                verdict=verdict_from(r12["p"], r12["slope"]["b"], r12["slope"]["b_err"]), reason=common_reason)
    save_result("D2c", student_result="m_jj spectrum, exactly 1 b tag (>=1b minus 2b), 2016G+H, |deta|<1.1",
                counterpart=cparts(T_1B), level="shape (normalised, detector level)", statistic=r1x["chi2"], statistic_name="two-sample Pearson chi2 (stat. only)",
                ndf=r1x["ndf"], p_value=r1x["p"], ratio=None, details=out["excl1b"], verdict=verdict_from(r1x["p"], r1x["slope"]["b"], r1x["slope"]["b_err"]), reason=common_reason)

    # ======================================================================= D3: absolute dsigma/dm
    plt, hep = setup_mpl()
    res3 = {}
    cm_1b2b = cm12
    comps = [("2b", n2, cm2, "D3a", T_2B, "2 b tags", "double b (row 1)", "black", "o"),
             ("ge1b", n1, cm4, "D3b", T_INCL, ">=1 b tag", "inclusive single b (row 4)", "tab:blue", "s"),
             ("ge1b_alt", n1, cm_1b2b, "D3b_alt", "rows 1+2 (single b + double b)", ">=1 b tag", "single b + double b (rows 1+2)", "tab:green", "^"),
             ("excl1b", n1 - n2, tabs[T_1B], "D3c", T_1B, "exactly 1 b tag", "single b (row 2)", "tab:purple", "v")]
    fig, axs = plt.subplots(2, 1, figsize=(10, 10), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    ax, rax = axs
    LUMI_UNC = np.hypot(0.012, 0.012)         # student (Open Data record 1059) and CMS 2016 luminosity uncertainties, assumed 1.2% each
    MASS_SCALE_UNC = 0.01                      # assumed 1% dijet-mass-scale difference (JES, wide jets) -> enters through the spectrum slope
    for key, n_s, cm, tid, tab, slab, clab, col, mk in comps:
        lo = edges_s[:-1]; hi = edges_s[1:]
        ci = {float(l): i for i, l in enumerate(cm["lo"])}
        m = np.array([float(l) in ci for l in lo])
        i_c = np.array([ci[float(l)] for l in lo[m]])
        ds = n_s[m] / (lumi_fb * (hi[m] - lo[m]))                      # fb/GeV
        dse = np.sqrt(np.maximum(n_s[m], 1)) / (lumi_fb * (hi[m] - lo[m]))
        dc = cm["xs"][i_c]; dce = cm["err"][i_c]
        good = (n_s[m] >= 20) & cm["ok"][i_c] & (cm["n"][i_c] >= 20)
        xc = 0.5 * (lo[m] + hi[m])
        R = ds / dc
        Re = R * np.sqrt(1 / np.maximum(n_s[m], 1) + 1 / np.maximum(cm["n"][i_c], 1))
        sl = ratio_slope(xc[good] / 1e3, R[good], Re[good])
        Rint = (n_s[m][good].sum() / lumi_fb) / (cm["n"][i_c][good].sum() / L_cms)
        Rint_err = Rint * np.sqrt(1 / n_s[m][good].sum() + 1 / cm["n"][i_c][good].sum())
        # local power-law index k = -dln(dsigma/dm)/dln m of the CMS spectrum, count-weighted over the range
        kk = -np.gradient(np.log(dc[good]), np.log(xc[good]))
        k_eff = float(np.sum(kk * cm["n"][i_c][good]) / np.sum(cm["n"][i_c][good]))
        env = float(np.hypot(LUMI_UNC, k_eff * MASS_SCALE_UNC))
        nsig_stat = abs(Rint - 1) / Rint_err
        nsig_env = abs(Rint - 1) / np.hypot(Rint_err / Rint, env) / Rint
        log(f"D3 {key}: integrated ratio {Rint:.3f} +- {Rint_err:.3f} (stat) over {xc[good][0]:.0f}-{xc[good][-1]:.0f}; weighted mean {sl['c0']:.3f}; "
            f"slope {sl['b']:+.3f} +- {sl['b_err']:.3f}/TeV; first/last {R[good][0]:.3f}/{R[good][-1]:.3f}; k_eff={k_eff:.1f}, assumed envelope +-{env*100:.1f}% -> {nsig_env:.1f} sigma")
        res3[key] = dict(ratio_integrated=float(Rint), ratio_integrated_err_stat=float(Rint_err), ratio_mean_weighted=sl["c0"], slope_per_TeV=sl["b"], slope_err=sl["b_err"],
                         chi2_vs_one=sl["chi2_one"], ndf=int(good.sum()), range_GeV=[float(xc[good][0]), float(xc[good][-1])], n_bins=int(good.sum()),
                         ratio_first=float(R[good][0]), ratio_last=float(R[good][-1]), chi2_const=sl["chi2_const"], p_const=pvalue(sl["chi2_const"], good.sum() - 1),
                         nsigma_stat_only=float(nsig_stat), assumed_syst_envelope_rel=env, k_eff=k_eff, nsigma_with_envelope=float(nsig_env),
                         envelope_assumptions="lumi 1.2% (student) + 1.2% (CMS) in quadrature, plus 1% dijet-mass-scale x local spectrum index k; b-tag and other CMS systematics NOT included")
        if key in ("2b", "ge1b"):
            ax.errorbar(xc[good], ds[good], yerr=dse[good], fmt=mk, color=col, ms=4, label=f"Student {slab} (L={lumi_fb:.1f} fb$^{{-1}}$)")
            ax.errorbar(xc[good], dc[good], yerr=dce[good], fmt=mk, color="tab:red" if key == "2b" else "tab:orange", ms=4, mfc="none", label=f"CMS-EXO-20-008 {clab}")
        rax.errorbar(xc[good], R[good], yerr=Re[good], fmt=mk, color=col, ms=4, label=f"{slab} / {clab.split(' (')[0]}")
    ax.set_yscale("log")
    ax.set_ylabel("$d\\sigma/dm_{jj}$ [fb/GeV]")
    ax.legend(fontsize=11, loc="upper right")
    ax.text(0.04, 0.05, "CMS-EXO-20-008, PRD 108 (2023) 012009, 2016 spectra\n(HEPData qualifier says 138 fb$^{-1}$; implied L = %.1f fb$^{-1}$)" % L_cms, transform=ax.transAxes, fontsize=12)
    rax.axhline(1, color="gray", ls="--")
    rax.set_ylabel("Student / CMS")
    rax.set_xlabel("$m_{jj}$ [GeV]")
    rax.set_ylim(0.2, 1.4)
    rax.legend(fontsize=9, ncol=2, loc="lower left")
    open_data_label(ax, hep, lumi=round(lumi_fb, 1))
    savefig(fig, "D3_dsigma_dm_vs_EXO20008")

    # ---- supplementary: b-tag fraction, cancels any flat selection/normalisation factor common to all categories
    supp = None
    hist5 = Path(a.cache) / "d5_student_hist.npz"
    if hist5.exists():
        H = np.load(hist5)
        e5 = H["edges"]
        # student b-tag fraction = N_btag / N_incl, same |deta|<1.1 selection.  CMS: sigma_btag(EXO-20-008, |deta|<1.1) / [sigma_incl(EXO-16-056, |deta|<1.3) x f_deta(m)],
        # with f_deta(m) = N(|deta|<1.1)/N(|deta|<1.3) measured per bin in the student's own data
        rec16 = hepdata_dir(a.cache, 1676214)
        t16 = read_table(rec16, "Differential dijet spectrum (High-mass analysis)")
        c16 = {float(l): i for i, l in enumerate(t16["indep"][0]["low"])}
        L16 = 35.9
        sup = {}
        for key, n_s, cm in (("2b", n2, cm2), ("ge1b", n1, cm4), ("ge1b_alt", n1, cm_1b2b)):
            fr_s, fr_c, frs_e, frc_e, xcs = [], [], [], [], []
            for i, l in enumerate(edges_s[:-1]):
                lc, hc = float(l), float(edges_s[i + 1])
                if lc not in c16 or lc not in {float(q) for q in cm["lo"]}:
                    continue
                j = int(np.where(np.isclose(cm["lo"], lc))[0][0])
                k = int(np.where(np.isclose(e5[:-1], lc))[0][0])
                nin_s = H["incl"][k]
                fdeta = H["incl"][k] / H["incl_deta13"][k]
                nb_cms = cm["n"][j]
                nin_c = t16["dep"][0]["value"][c16[lc]]
                if min(n_s[i], nb_cms) < 50 or nin_c < 50 or nin_s < 50:
                    continue
                fs = n_s[i] / nin_s
                fc = (nb_cms / L_cms) / (nin_c / L16 * fdeta)
                fr_s.append(fs); fr_c.append(fc); frs_e.append(fs * np.sqrt(1 / n_s[i] + 1 / nin_s)); frc_e.append(fc * np.sqrt(1 / nb_cms + 1 / nin_c)); xcs.append(0.5 * (lc + hc))
            fr_s, fr_c = np.array(fr_s), np.array(fr_c)
            R = fr_s / fr_c
            Re = R * np.sqrt((np.array(frs_e) / fr_s) ** 2 + (np.array(frc_e) / fr_c) ** 2)
            sl = ratio_slope(np.array(xcs) / 1e3, R, Re)
            sup[key] = dict(mean_ratio=sl["c0"], mean_err=sl["c0_err"], slope_per_TeV=sl["b"], slope_err=sl["b_err"], first=float(R[0]), last=float(R[-1]), n_bins=len(R),
                            range_GeV=[float(xcs[0]), float(xcs[-1])], x=np.array(xcs), R=R, Re=Re)
            log(f"D3 supplementary b-tag fraction ratio {key}: mean {sl['c0']:.3f} +- {sl['c0_err']:.3f}, slope {sl['b']:+.3f} +- {sl['b_err']:.3f}/TeV, first/last {R[0]:.3f}/{R[-1]:.3f}")
        supp = {k: {kk: vv for kk, vv in v.items() if kk not in ("x", "R", "Re")} for k, v in sup.items()}
        fig, ax = plt.subplots(figsize=(10, 7))
        sty = {"2b": ("black", "o", "2 b tags / double b"), "ge1b": ("tab:blue", "s", "$\\geq$1b / inclusive single b"), "ge1b_alt": ("tab:green", "^", "$\\geq$1b / (single b + double b)")}
        for key, (col, mk, lab) in sty.items():
            ax.errorbar(sup[key]["x"], sup[key]["R"], yerr=sup[key]["Re"], fmt=mk, color=col, ms=4, label=lab)
        ax.axhline(1, color="gray", ls="--")
        ax.set_xlabel("$m_{jj}$ [GeV]")
        ax.set_ylabel("b-tag fraction of inclusive dijets: student / CMS")
        ax.set_ylim(0.4, 2.2)
        ax.legend(fontsize=12)
        ax.text(0.04, 0.05, "CMS fraction = EXO-20-008 b-tag / EXO-16-056 inclusive, corrected from |$\\Delta\\eta$|<1.3 to <1.1", transform=ax.transAxes, fontsize=10)
        open_data_label(ax, hep, lumi=round(lumi_fb, 1))
        savefig(fig, "D3c_btag_fraction_ratio")

    def v3(r):
        n = r["nsigma_with_envelope"]
        return "INCONSISTENT" if n > 3 else ("TENSION" if n > 2 else "CONSISTENT")
    for key, n_s, cm, tid, tab, slab, clab, col, mk in comps:
        r = res3[key]
        counterpart = cparts(tab) if tab.startswith("Figure") else {**cparts("Figure 3 first row + second row first column (sum)")}
        save_result(tid, student_result=f"dsigma/dm = N/(L dm) [fb/GeV], {slab}, 2016G+H, L = {lumi_fb:.3f} fb^-1, |deta|<1.1",
                    counterpart=counterpart, level="absolute: student detector-level N/(L dm) vs CMS dsigma/dm (fb/GeV, detector level), same |deta| cut, same bins; wide vs AK4 jets, L differs",
                    statistic=r["nsigma_with_envelope"], statistic_name="n sigma of (ratio-1) with stat + assumed systematic envelope", ndf=None, p_value=None,
                    ratio=r["ratio_integrated"], ratio_err=r["ratio_integrated_err_stat"], details=r, cms_implied_lumi_fb=L_cms, cms_lumi_qualifier_in_record=138,
                    btag_fraction_supplementary=(supp or {}).get(key), verdict=v3(r),
                    reason=("integrated ratio %.3f; see details (slope, envelope). Same |deta|<1.1 cut in both; luminosity cancels in a cross section; "
                            "jets (wide vs AK4 CHS), |eta| 2.5 vs 2.4, tagger scale factors and JEC remain." % r["ratio_integrated"]))
    save_result("D3_lumi_check", student_result="normalisation of the 2016 tables of ins1920627", ratio=L_cms / 138.0,
                implied_lumi_fb_per_table={k: v[0] for k, v in lum.items()}, rel_spread={k: v[1] for k, v in lum.items()},
                qualifier=tabs[T_2B]["qual"], verdict="NOT COMPARABLE",
                reason="The 2016 tables carry LUMINOSITY=138 fb^-1 but N/(dsigma/dm * width) = 36.3 fb^-1 (the 2016 luminosity quoted in Fig. 3 of the paper): the qualifier is the Run 2 total, not the normalisation.")


if __name__ == "__main__":
    main()
