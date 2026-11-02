#!/usr/bin/env python3
"""M3 (shape): dimuon pT and |y| in the Z window vs the NORMALISED, unfolded, dressed-lepton distributions of CMS-SMP-17-010
(JHEP 12 (2019) 061, INSPIRE 1753680, HEPData tables 'Figure 14a' (pT) and 'Figure 14c' (|y|)).

* Figure 14a/c are the COMBINED dimuon+dielectron ('Normalized dilepton cross section'), values are per-bin fractions (sum = 1, not per GeV).
* The covariance tables ('Covariance Matrix auxiliary Figure 1a' / '1c') are for the ABSOLUTE DIMUON cross sections (pb/GeV, pb), dressed level, i.e. they
  match the 'Dimuon cross section (pb)' columns of 'Figure 6' / 'Figure 5', not the normalised combined values.  The normalised dimuon covariance is
  derived here by linear error propagation p_i = sigma_i w_i / sum_j sigma_j w_j (the luminosity part cancels).
* Student: win_pt / win_y 'z' (81-101 GeV, 2 GeV and 0.1 bins) from the unchanged histograms.pkl; variants from rerun_dimuon.py (CMS binning).

Usage: compare_m3_z_pt_y.py --dimuon-dir <dir with histograms.pkl> --cache <cache>
"""
import argparse
import pickle
import sys

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import *   # noqa

REC = 1753680
PT_EDGES = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 18, 20, 22, 25, 28, 32, 37, 43, 52, 65, 85, 120, 160, 190, 220, 250, 300, 400, 500, 800, 1500], float)
Y_EDGES = np.round(np.arange(0, 2.41, 0.2), 6)


def cms_norm(rec, tab_abs, cov_name, edges):
    """absolute dimuon sigma (pb per unit of the variable) + covariance -> merged-bin vector A_i = sigma_i*w_i (pb) and covariance"""
    t = read_table(rec, tab_abs)
    x = t["indep"][0]["value"]
    sig = t["dep"][0]["value"]                           # dimuon cross section (pb per GeV or per unit |y|)
    ce = 0.5 * (edges[1:] + edges[:-1])
    assert np.allclose(x, ce, atol=1e-6), "bin centres do not match the assumed edges"
    w = np.diff(edges)
    c = read_table(rec, cov_name)
    n = len(sig)
    C = c["dep"][0]["value"].reshape(n, n)
    return sig, w, C, t["dep"][0]["name"]


def norm_cov(sig, w, C, sel, groups=None):
    """normalised fractions p over the bins `sel` (optionally merged in `groups`: list of index lists into sel) and their covariance"""
    A = sig * w
    Cs = C * np.outer(w, w)                              # covariance of A_i = sigma_i w_i
    if groups is None:
        groups = [[i] for i in sel]
    M = np.zeros((len(groups), len(A)))
    for g, idx in enumerate(groups):
        M[g, idx] = 1.0
    Ag = M @ A
    Cg = M @ Cs @ M.T
    S = Ag.sum()
    p = Ag / S
    J = (np.eye(len(Ag)) - np.outer(p, np.ones(len(Ag)))) / S      # dp_i/dA_k
    return p, J @ Cg @ J.T


def chi2_cov(d, Cv):
    """chi2 of a difference vector of normalised distributions (drop the last bin: the sum constraint makes the covariance singular)"""
    n = len(d)
    dd = d[:-1]
    Cm = Cv[:-1, :-1]
    return float(dd @ np.linalg.solve(Cm, dd)), n - 1


def student_vs_cms(counts, sig, w, C, sel_idx, groups):
    """counts: student counts in the merged groups (same grouping), returns dict"""
    p_c, C_c = norm_cov(sig, w, C, sel_idx, groups)
    N = counts.sum()
    p_s = counts / N
    C_s = (np.diag(p_s) - np.outer(p_s, p_s)) / N
    d = p_s - p_c
    chi2, ndf = chi2_cov(d, C_c + C_s)
    chi2_stat_only, _ = chi2_cov(d, np.diag(np.diag(C_c)) * 0 + np.diag(np.diag(C_c + C_s)))      # diagonal-only (bin-to-bin uncorrelated) version
    return dict(p_s=p_s, p_c=p_c, err_s=np.sqrt(np.diag(C_s)), err_c=np.sqrt(np.diag(C_c)), chi2=chi2, ndf=ndf, p=pvalue(chi2, ndf), chi2_diag=chi2_stat_only,
                ratio=p_s / p_c, ratio_err=p_s / p_c * np.sqrt((np.sqrt(np.diag(C_s)) / p_s) ** 2 + (np.sqrt(np.diag(C_c)) / p_c) ** 2), N=float(N))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dimuon-dir", required=True)
    ap.add_argument("--cache", required=True)
    a = ap.parse_args()
    h = pickle.load(open(Path(a.dimuon_dir) / "histograms.pkl", "rb"))
    R = pickle.load(open(Path(a.cache) / "dimuon_rerun.pkl", "rb"))
    rec = hepdata_dir(a.cache, REC)
    # ---- what the HEPData tables are
    t14a = read_table(rec, "Figure 14a")
    p_comb = t14a["dep"][0]["value"]
    log("Figure 14a header:", t14a["dep"][0]["name"], "(combined dimuon+dielectron)")
    sig_pt, w_pt, C_pt, nm = cms_norm(rec, "Figure 6", "Covariance Matrix auxiliary Figure 1a", PT_EDGES)
    sig_y, w_y, C_y, nm2 = cms_norm(rec, "Figure 5", "Covariance Matrix auxiliary Figure 1c", Y_EDGES)
    log(f"dimuon absolute: sum sigma*w over pT = {np.sum(sig_pt*w_pt):.1f} pb; over |y| = {np.sum(sig_y*w_y):.1f} pb (paper: 694 pb); sqrt(diag C)/sigma first bins =",
        np.round(np.sqrt(np.diag(C_pt))[:3] / sig_pt[:3], 4).tolist())
    # Figure 14a values are NOT bin fractions and NOT a density normalised to its integral: they sum to 1 over bins of unequal width,
    # i.e. v_i = (dsigma/dpT)_i / sum_j (dsigma/dpT)_j.  Convert to fractions with the bin widths before comparing:
    p14_frac = p_comb * w_pt / np.sum(p_comb * w_pt)
    p_dimu_pt = sig_pt * w_pt / np.sum(sig_pt * w_pt)
    log("Figure 14a: sum(v)=%.6f, sum(v*w)=%.3f -> v is a per-GeV value normalised by sum(v), not by the integral" % (p_comb.sum(), np.sum(p_comb * w_pt)))
    log("dimuon-only fractions (Figure 6 x width) vs combined Figure 14a converted to fractions: max |diff| =", float(np.max(np.abs(p_dimu_pt - p14_frac))),
        " max relative (bins with >0.1% of events)", float(np.max(np.abs(p_dimu_pt / p14_frac - 1)[p14_frac > 1e-3])))
    xs14 = read_table(rec, "Figure 14c")["dep"][0]["value"]
    sy5 = read_table(rec, "Figure 5")["dep"][0]["value"]
    log("Figure 14c: sum(v) = %.6f; dimuon |y| fractions vs Figure 14c, max relative diff %.4f" % (xs14.sum(), float(np.max(np.abs((sy5 / sy5.sum()) / xs14 - 1)))))
    # ---- student's unchanged histograms
    hp = h["win_pt"][:, "z"]; hy = h["win_y"][:, "z"]
    pt_s_edges = hp.axes[0].edges; pt_s = hp.values()
    y_s_edges = hy.axes[0].edges; y_s = hy.values()
    flow = (hp.sum(flow=True).value - hp.sum().value)
    log(f"student win_pt z: {pt_s.sum():.0f} in 0-100 GeV, overflow {flow:.0f}; win_y: {y_s.sum():.0f}")
    # fold |y|
    ny = len(y_s) // 2
    ay = y_s[ny:] + y_s[:ny][::-1]
    ay_edges = y_s_edges[ny:]
    ay12 = ay.reshape(12, 2).sum(1)                       # 0.2-wide bins
    # pT: common edges with CMS up to 52 GeV
    common = [e for e in PT_EDGES if e <= 52 and np.any(np.isclose(pt_s_edges, e))]
    sel_groups, s_counts = [], []
    for lo, hi in zip(common[:-1], common[1:]):
        sel_groups.append([int(i) for i in np.where((PT_EDGES[:-1] >= lo - 1e-9) & (PT_EDGES[1:] <= hi + 1e-9))[0]])
        s_counts.append(pt_s[(pt_s_edges[:-1] >= lo - 1e-9) & (pt_s_edges[1:] <= hi + 1e-9)].sum())
    s_counts = np.array(s_counts)
    sel_idx = [i for g in sel_groups for i in g]
    res_pt = student_vs_cms(s_counts, sig_pt, w_pt, C_pt, sel_idx, sel_groups)
    log(f"M3 pT (student histograms, common range 0-52 GeV, {len(s_counts)} bins): chi2/ndf = {res_pt['chi2']:.1f}/{res_pt['ndf']} (p={res_pt['p']:.1e}); diagonal-only {res_pt['chi2_diag']:.1f}")
    log("   ratio student/CMS per bin:", np.round(res_pt["ratio"], 3).tolist())
    res_y = student_vs_cms(ay12, sig_y, w_y, C_y, list(range(12)), [[i] for i in range(12)])
    log(f"M3 |y| (student histograms, 0-2.4): chi2/ndf = {res_y['chi2']:.1f}/{res_y['ndf']} (p={res_y['p']:.1e}); diagonal-only {res_y['chi2_diag']:.1f}")
    log("   ratio student/CMS per bin:", np.round(res_y["ratio"], 3).tolist())
    # ---- rerun variants with the CMS binning (0-120 GeV in pT)
    var_pt, var_y = {}, {}
    n_pt_bins = 27                                       # CMS bins up to 120 GeV
    g_all = [[i] for i in range(n_pt_bins)]
    for v, lab in (("stud81_101", "student selection, 81-101 GeV (CMS binning)"), ("win15", "window 76.2-106.2 GeV"), ("smp010", "+ both muons pT>25, |eta|<2.4"),
                   ("smp010_id", "+ tightId, PF iso<0.15")):
        cnt = R["hist"][f"zpt_{v}"][:n_pt_bins]
        var_pt[v] = student_vs_cms(cnt, sig_pt, w_pt, C_pt, list(range(n_pt_bins)), g_all)
        var_pt[v]["label"] = lab
        cy = R["hist"][f"zy_{v}"]
        var_y[v] = student_vs_cms(cy, sig_y, w_y, C_y, list(range(12)), [[i] for i in range(12)])
        var_y[v]["label"] = lab
        log(f"variant {v:11s}: pT(0-120): chi2/ndf = {var_pt[v]['chi2']:.1f}/{var_pt[v]['ndf']}, N={var_pt[v]['N']:.0f}; |y|: chi2/ndf = {var_y[v]['chi2']:.1f}/{var_y[v]['ndf']}")
    # ---- resolution estimate: smear the CMS pT distribution with a Gaussian (assumed sigma(pT_Z)) and re-evaluate the student(student-selection)/CMS comparison
    from scipy.interpolate import PchipInterpolator
    cum = np.concatenate([[0], np.cumsum(sig_pt * w_pt)]) / np.sum(sig_pt * w_pt)
    F = PchipInterpolator(PT_EDGES, cum)
    def smeared_fractions(sigma):
        grid = np.linspace(0, 140, 5601)
        dens = F.derivative()(grid)
        # reflect at pT=0 (|pT| of a 2D vector: approximate 1-D smearing with reflection)
        full_g = np.concatenate([-grid[::-1], grid]); full_d = np.concatenate([dens[::-1], dens]) * 0.5
        from scipy.ndimage import gaussian_filter1d
        sm = gaussian_filter1d(full_d, sigma / (grid[1] - grid[0]), mode="nearest")
        sm = sm[len(grid):] * 2
        cs = np.concatenate([[0], np.cumsum(sm) * (grid[1] - grid[0])])
        Fi = np.interp(PT_EDGES[PT_EDGES <= 120], np.concatenate([[0], grid + (grid[1] - grid[0])]), cs)
        return np.diff(Fi)
    base = np.diff(F(PT_EDGES[PT_EDGES <= 120]))
    smear_info = {}
    for sg in (0.5, 1.0, 1.5):
        fr = smeared_fractions(sg)
        rel = fr / base - 1
        smear_info[sg] = dict(max_rel_change=float(np.max(np.abs(rel[:14]))), rel=rel.tolist())
        log(f"smear estimate sigma={sg} GeV: max relative change of the CMS pT-bin fractions in 0-14 GeV = {np.max(np.abs(rel[:14])):.3f}; at 3-5 GeV ~ {np.round(rel[3:5],3).tolist()}")
    # smeared-CMS chi2 for the fully matched variant (assumption: Gaussian sigma(pT_Z) independent of pT)
    smear_chi2 = {}
    p_c27, C_c27 = norm_cov(sig_pt, w_pt, C_pt, list(range(27)), [[i] for i in range(27)])
    for sg in smear_info:
        rel = np.array(smear_info[sg]["rel"])
        p_sm = p_c27 * (1 + rel)
        p_sm = p_sm / p_sm.sum()
        for v in ("smp010", "smp010_id"):
            cnt = R["hist"][f"zpt_{v}"][:27]
            N = cnt.sum(); p_s = cnt / N
            Cs = (np.diag(p_s) - np.outer(p_s, p_s)) / N
            c2, nd = chi2_cov(p_s - p_sm, C_c27 + Cs)
            smear_chi2[f"{v}_sigma{sg}"] = c2
            log(f"   variant {v} vs CMS smeared with sigma={sg} GeV: chi2/ndf = {c2:.1f}/{nd}")
    # ---- plots
    plt, hep = setup_mpl()
    # (a) pT, student histograms vs CMS, common bins (density per GeV)
    ed = np.array([PT_EDGES[g[0]] for g in sel_groups] + [PT_EDGES[sel_groups[-1][-1] + 1]])
    wd = np.diff(ed); xc = 0.5 * (ed[1:] + ed[:-1])
    for tag, res, ed_, xlab, ylab, name, logy in (("pt", res_pt, ed, "dimuon $p_T$ [GeV]", "fraction per GeV", "M3a_Z_pT_vs_SMP17010", True),
                                                ("y", res_y, Y_EDGES, "|y(Z)| (dimuon rapidity)", "fraction per unit |y|", "M3b_Z_absy_vs_SMP17010", False)):
        wd_ = np.diff(ed_); xc_ = 0.5 * (ed_[1:] + ed_[:-1])
        fig, (ax, rax) = plt.subplots(2, 1, figsize=(10, 10), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
        ax.errorbar(xc_, res["p_s"] / wd_, yerr=res["err_s"] / wd_, fmt="o", color="black", ms=4, label="Student: 2016H DoubleMuon, 81-101 GeV, loose $\\mu$ pT>3 GeV")
        ax.errorbar(xc_, res["p_c"] / wd_, yerr=res["err_c"] / wd_, fmt="s", color="tab:red", mfc="none", ms=4, label="CMS-SMP-17-010 (dressed, unfolded, 35.9 fb$^{-1}$)")
        if logy:
            ax.set_yscale("log")
        ax.set_ylabel(ylab)
        ax.legend(fontsize=12)
        ax.text(0.04, 0.05, f"$\\chi^2$/ndf = {res['chi2']:.0f}/{res['ndf']} (CMS covariance from Cov. Matrix aux. Fig. 1{'a' if tag=='pt' else 'c'})", transform=ax.transAxes, fontsize=12)
        rax.errorbar(xc_, res["ratio"], yerr=res["ratio_err"], fmt="o", color="black", ms=4)
        rax.axhline(1, color="gray", ls="--")
        if tag == "pt":
            for v, col in (("smp010", "tab:blue"),):
                pass
        rax.set_ylabel("Student / CMS"); rax.set_xlabel(xlab); rax.set_ylim(0.6, 1.4)
        open_data_label(ax, hep)
        savefig(fig, name)
    # (c) variants ratio plot for pT
    fig, ax = plt.subplots(figsize=(10, 7))
    xc27 = 0.5 * (PT_EDGES[1:28] + PT_EDGES[:27])
    for (v, col, mk) in (("stud81_101", "black", "o"), ("win15", "tab:green", "s"), ("smp010", "tab:blue", "^"), ("smp010_id", "tab:red", "v")):
        ax.errorbar(xc27, var_pt[v]["ratio"], yerr=var_pt[v]["ratio_err"], fmt=mk, color=col, ms=4, label=f"{var_pt[v]['label']}: $\\chi^2$/ndf={var_pt[v]['chi2']:.0f}/{var_pt[v]['ndf']}")
    ax.axhline(1, color="gray", ls="--")
    ax.set_xscale("symlog", linthresh=20); ax.set_xlabel("dimuon $p_T$ [GeV]"); ax.set_ylabel("Student / CMS (normalised)"); ax.set_ylim(0.5, 1.8)
    ax.legend(fontsize=10)
    open_data_label(ax, hep)
    savefig(fig, "M3c_Z_pT_selection_variants")
    fig, ax = plt.subplots(figsize=(10, 7))
    xcy = 0.5 * (Y_EDGES[1:] + Y_EDGES[:-1])
    for (v, col, mk) in (("stud81_101", "black", "o"), ("win15", "tab:green", "s"), ("smp010", "tab:blue", "^"), ("smp010_id", "tab:red", "v")):
        ax.errorbar(xcy, var_y[v]["ratio"], yerr=var_y[v]["ratio_err"], fmt=mk, color=col, ms=4, label=f"{var_y[v]['label']}: $\\chi^2$/ndf={var_y[v]['chi2']:.0f}/{var_y[v]['ndf']}")
    ax.axhline(1, color="gray", ls="--"); ax.set_xlabel("|y(Z)|"); ax.set_ylabel("Student / CMS (normalised)"); ax.set_ylim(0.6, 1.4); ax.legend(fontsize=10)
    open_data_label(ax, hep)
    savefig(fig, "M3d_Z_absy_selection_variants")

    def verdict(res):
        n = nsigma(res["p"])
        return "INCONSISTENT" if n > 3 else ("TENSION" if n > 2 else "CONSISTENT")
    clean = lambda r: {k: (v.tolist() if isinstance(v, np.ndarray) else v) for k, v in r.items()}
    cp = {"report": "CMS-SMP-17-010", "inspire_paper": 1753680, "paper": "JHEP 12 (2019) 061, arXiv:1909.04133", "hepdata_record": "ins1753680"}
    save_result("M3a", student_result="dimuon pT, Z window 81-101 GeV (unchanged histograms.pkl win_pt), shape in 0-52 GeV",
                counterpart={**cp, "hepdata_table": "Figure 14a (normalised, combined dilepton) with Figure 6 (dimuon) + Covariance Matrix auxiliary Figure 1a"},
                level="shape: detector-level, uncorrected loose-ID muons pT>3 GeV vs unfolded dressed-lepton fiducial (pT>25 GeV muons), both normalised to the common range",
                statistic=res_pt["chi2"], statistic_name="chi2 with CMS covariance (derived normalised dimuon) + student multinomial covariance", ndf=res_pt["ndf"], p_value=res_pt["p"], ratio=None,
                details=clean(res_pt), variants={k: clean(v) for k, v in var_pt.items()}, smearing_estimate=smear_info, smeared_cms_chi2=smear_chi2, verdict=verdict(res_pt),
                reason="detector-level, no efficiency/FSR/acceptance correction, muon pT>3 GeV (CMS: >25 GeV), wider kinematic acceptance; see variants.")
    save_result("M3b", student_result="dimuon |y|, Z window 81-101 GeV (unchanged histograms.pkl win_y folded), shape in 0-2.4",
                counterpart={**cp, "hepdata_table": "Figure 14c (normalised, combined dilepton) with Figure 5 (dimuon) + Covariance Matrix auxiliary Figure 1c"},
                level="shape: detector-level vs unfolded, normalised", statistic=res_y["chi2"], statistic_name="chi2 with CMS covariance + student multinomial covariance", ndf=res_y["ndf"],
                p_value=res_y["p"], ratio=None, details=clean(res_y), variants={k: clean(v) for k, v in var_y.items()}, verdict=verdict(res_y),
                reason="acceptance (muon pT>3 GeV vs >25 GeV, ID/iso), trigger efficiency vs |y|, window; see variants.")


if __name__ == "__main__":
    main()
