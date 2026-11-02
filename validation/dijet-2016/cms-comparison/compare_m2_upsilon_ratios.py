#!/usr/bin/env python3
"""M2 (ratio): Upsilon(2S)/Upsilon(1S) and Upsilon(3S)/Upsilon(1S) yield ratios from the student's data (rerun histograms, |y|<1.2, pT bins of
CMS-BPH-15-005) vs the cross-section-times-branching-fraction ratios of CMS-BPH-15-005 (PLB 780 (2018) 251, INSPIRE 1633431):
HEPData Tables 3, 4, 5 (double differential, 0.0-1.2 column) and Table 12 (ratios with uncertainties).

Student yields come from binned-likelihood fits (3 resonances: Crystal-Ball core + wide Gaussian, shared shape, mass scale common, widths tied to the mass,
exp-polynomial continuum) in pT groups.  The CMS ratio of a pT group is sum_i(w_i sigma2S_i)/sum_i(w_i sigma1S_i) (3-digit tables), with per-bin relative
uncertainties of Table 12 (stat uncorrelated, syst fully correlated across the bins of a group).

Usage: compare_m2_upsilon_ratios.py --cache <cache>      (needs <cache>/dimuon_rerun.pkl from rerun_dimuon.py)
"""
import argparse
import pickle
import sys

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import *   # noqa
from dimuon_fits import *   # noqa

M_PDG = {1: 9.4604, 2: 10.0234, 3: 10.3551}
GROUPS = [(20, 24), (24, 28), (28, 32), (32, 40), (40, 50), (50, 70), (70, 130)]


def fit_group(e, y, shape, order=2, nCB=5.0, free_shape=False):
    """3-resonance fit in one pT group; params: N1, R2=N2/N1, R3=N3/N1, scale s (m_i = s*PDG_i), sigma0 (width of the 1S), bkg."""
    x0 = (0.5 * (e[0] + e[-1]), 0.5 * (e[-1] - e[0]))
    f, r, alpha = shape

    def model(N1, R2, R3, s, sig0, *c):
        mu = [s * M_PDG[i] for i in (1, 2, 3)]
        sg = [sig0 * M_PDG[i] / M_PDG[1] for i in (1, 2, 3)]
        return (mix_counts(e, N1, mu[0], sg[0], f, r, alpha, nCB) + mix_counts(e, N1 * R2, mu[1], sg[1], f, r, alpha, nCB)
                + mix_counts(e, N1 * R3, mu[2], sg[2], f, r, alpha, nCB) + exp_poly_counts(e, c, x0))
    ntot = y.sum()
    bk = np.median(y[:10]) if len(y) > 20 else max(y.min(), 0.5)
    p0 = dict(N1=max(ntot * 0.3, 10), R2=0.45, R3=0.3, s=1.0, sig0=0.12, c0=np.log(max(bk, 0.3) / (e[1] - e[0])))
    for i in range(1, order + 1):
        p0[f"c{i}"] = 0.0
    lim = dict(N1=(0, None), R2=(0, 3), R3=(0, 3), s=(0.99, 1.01), sig0=(0.05, 0.3))
    m, info = run_fit(model, y, p0, limits=lim)
    return m, info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    a = ap.parse_args()
    R = pickle.load(open(Path(a.cache) / "dimuon_rerun.pkl", "rb"))
    upt, um = R["edges"]["upt"], R["edges"]["um"]
    # ---- CMS-BPH-15-005 tables
    rec = hepdata_dir(a.cache, 1633431)
    T = {n: read_table(rec, n) for n in ("Table 3", "Table 4", "Table 5", "Table 12")}
    def col(t, rapidity):
        for d in t["dep"]:
            q = {x["name"]: x["value"] for x in d["qualifiers"]}
            if q.get("ABS(YRAP)") == rapidity:
                return d
        raise KeyError(rapidity)
    ptlo, pthi = T["Table 3"]["indep"][0]["low"], T["Table 3"]["indep"][0]["high"]
    s1, s2, s3 = (col(T[f"Table {k}"], "0.0-1.2") for k in (3, 4, 5))
    def rel(d, lab):
        e = d["errors"][lab]
        return e / d["value"]
    w = pthi - ptlo
    # Table 12 (ratio) per bin: it has the same pT edges?
    t12lo, t12hi = T["Table 12"]["indep"][0]["low"], T["Table 12"]["indep"][0]["high"]
    r21 = T["Table 12"]["dep"][0]; r31 = T["Table 12"]["dep"][1]
    assert np.allclose(t12lo, ptlo) and np.allclose(t12hi, pthi), "Table 12 and Tables 3-5 have different pT bins"
    # cross-check Table 4/Table 3 against Table 12 (Table 12 is quoted to 2 digits)
    log("Table4/Table3 vs Table12 (2S/1S), first 5 bins:", np.round(s2["value"] / s1["value"], 3)[:5].tolist(), r21["value"][:5].tolist())
    log("Table5/Table3 vs Table12 (3S/1S), first 5 bins:", np.round(s3["value"] / s1["value"], 3)[:5].tolist(), r31["value"][:5].tolist())
    log("Table 12 units header:", r21["units"], "(values are ratios ~0.4, not percent)")

    def cms_group(lo, hi, num):
        idx = np.where((ptlo >= lo - 1e-9) & (pthi <= hi + 1e-9))[0]
        c = w[idx] * s1["value"][idx]
        c = c / c.sum()
        Rb = (s2 if num == 2 else s3)["value"][idx] / s1["value"][idx]
        ratio_t = r21 if num == 2 else r31
        es = np.abs(ratio_t["errors"]["stat"][idx]) / ratio_t["value"][idx]
        ey = np.abs(ratio_t["errors"]["syst"][idx]) / ratio_t["value"][idx]
        Rg = float(np.sum(c * Rb))
        stat = float(np.sqrt(np.sum((c * Rb * es) ** 2)))
        syst = float(np.sum(c * Rb * ey))
        return Rg, stat, syst, idx
    # ---- student fits
    out = {}
    plt, hep = setup_mpl()
    sel_names = {"ups_bph": "BPH-15-005 muon kinematics (pT>4.5/4.0 GeV, |eta|<1.4), |y|<1.2", "ups_student": "student muons (loose, pT>3, |eta|<2.4), |y|<1.2"}
    # shape from a fit to the whole 20-130 sample
    for key in ("ups_bph", "ups_student"):
        H2 = R["hist"][key]                              # [pT bin, mass bin]
        ipt = {float(l): i for i, l in enumerate(upt[:-1])}
        # reference fit: all pT 20-130, shape (f, r, alpha) free for the reference
        yall = H2[ipt[20.0]: ipt[100.0] + 2].sum(0)
        def model_ref(N1, N2, N3, mu1, mu2, mu3, s1_, f, r, alpha, *c):
            x0 = (10.0, 1.5)
            sg = lambda m: s1_ * m / 9.46
            return (mix_counts(um, N1, mu1, sg(mu1), f, r, alpha, 5.0) + mix_counts(um, N2, mu2, sg(mu2), f, r, alpha, 5.0) + mix_counts(um, N3, mu3, sg(mu3), f, r, alpha, 5.0)
                    + exp_poly_counts(um, c, x0))
        p0 = dict(N1=yall.sum() * 0.3, N2=yall.sum() * 0.12, N3=yall.sum() * 0.08, mu1=9.46, mu2=10.02, mu3=10.35, s1_=0.12, f=0.6, r=2.0, alpha=2.0, c0=np.log(max(np.median(yall[:10]), 1) / 0.025), c1=0.0, c2=0.0)
        lim = dict(mu1=(9.38, 9.54), mu2=(9.95, 10.09), mu3=(10.28, 10.42), s1_=(0.04, 0.4), f=(0.05, 0.99), r=(1.2, 5), alpha=(0.5, 5), N1=(0, None), N2=(0, None), N3=(0, None))
        mref, iref = run_fit(model_ref, yall, p0, limits=lim)
        shape = (mref.values["f"], mref.values["r"], mref.values["alpha"])
        log(f"[{key}] reference fit 20-130 GeV: deviance/ndf {iref['deviance']:.0f}/{iref['ndf']}, shape f,r,alpha = {np.round(shape,2)}, sigma1 = {mref.values['s1_']*1e3:.0f} MeV, "
            f"N1,N2,N3 = {mref.values['N1']:.0f} {mref.values['N2']:.0f} {mref.values['N3']:.0f}")
        rows = []
        for lo, hi in GROUPS:
            i0, i1 = ipt[float(lo)], ipt[float(hi)] if float(hi) in ipt else len(upt) - 1
            if hi == 130:
                i1 = ipt[130.0]
            y = H2[i0:i1].sum(0)
            m, info = fit_group(um, y, shape)
            # systematic: background order 1 and 3, CB n 2 / 10
            vars_ = {}
            for lab, kw in {"bkg1": dict(order=1), "bkg3": dict(order=3), "n2": dict(nCB=2.0), "n10": dict(nCB=10.0)}.items():
                mv, iv = fit_group(um, y, shape, **kw)
                vars_[lab] = (mv.values["R2"], mv.values["R3"], iv["valid"])
            row = dict(lo=lo, hi=hi, N1=m.values["N1"], R2=m.values["R2"], R2_err=m.errors["R2"], R3=m.values["R3"], R3_err=m.errors["R3"],
                       R2_syst=max(abs(v[0] - m.values["R2"]) for v in vars_.values() if v[2]), R3_syst=max(abs(v[1] - m.values["R3"]) for v in vars_.values() if v[2]),
                       deviance=info["deviance"], ndf=info["ndf"], sigma1_MeV=m.values["sig0"] * 1e3, scale=m.values["s"])
            for num, nm in ((2, "R2"), (3, "R3")):
                Rg, st, sy, idx = cms_group(lo, hi, num)
                row[f"cms_{nm}"], row[f"cms_{nm}_stat"], row[f"cms_{nm}_syst"] = Rg, st, sy
            rows.append(row)
            log(f"[{key}] pT {lo}-{hi}: N1 = {row['N1']:.0f}; R2 = {row['R2']:.3f} +- {row['R2_err']:.3f} (syst {row['R2_syst']:.3f}) vs CMS {row['cms_R2']:.3f} +- {row['cms_R2_stat']:.3f} +- {row['cms_R2_syst']:.3f}; "
                f"R3 = {row['R3']:.3f} +- {row['R3_err']:.3f} (syst {row['R3_syst']:.3f}) vs CMS {row['cms_R3']:.3f}; dev/ndf {row['deviance']:.0f}/{row['ndf']}")
        out[key] = rows
    # ---- statistics (primary: BPH-matched muon kinematics)
    ASSUMED_AEFF = 0.05     # assumed relative uncertainty of the ratio of acceptance x efficiency (not corrected in the student's data): my assumption
    summary = {}
    for key in ("ups_bph", "ups_student"):
        rows = out[key]
        for nm in ("R2", "R3"):
            d = np.array([r[nm] for r in rows]); c = np.array([r[f"cms_{nm}"] for r in rows])
            es = np.array([np.hypot(r[f"{nm}_err"], r[f"{nm}_syst"]) for r in rows])
            ec = np.array([np.hypot(r[f"cms_{nm}_stat"], r[f"cms_{nm}_syst"]) for r in rows])
            ea = ASSUMED_AEFF * c
            chi2_a = float(np.sum((d - c) ** 2 / (es ** 2 + ec ** 2)))
            chi2_b = float(np.sum((d - c) ** 2 / (es ** 2 + ec ** 2 + ea ** 2)))
            ratio = d / c
            sl = ratio_slope(0.5 * np.array([r["lo"] + r["hi"] for r in rows]), ratio, ratio * np.sqrt((es / d) ** 2 + (ec / c) ** 2 + ASSUMED_AEFF ** 2))
            wmean = sl["c0"]
            summary[(key, nm)] = dict(chi2_no_aeff=chi2_a, chi2_with_aeff=chi2_b, ndf=len(rows), p_no_aeff=pvalue(chi2_a, len(rows)), p_with_aeff=pvalue(chi2_b, len(rows)),
                                      ratio_mean=wmean, ratio_mean_err=sl["c0_err"], ratio_first=float(ratio[0]), ratio_last=float(ratio[-1]), slope_per_GeV=sl["b"], slope_err=sl["b_err"])
            log(f"M2 [{key}] {nm}: chi2/ndf = {chi2_a:.1f}/{len(rows)} (p={pvalue(chi2_a, len(rows)):.2e}) without, {chi2_b:.1f} with {ASSUMED_AEFF:.0%} A*eff ratio uncertainty (p={pvalue(chi2_b, len(rows)):.2e}); "
                f"student/CMS: mean {wmean:.3f} +- {sl['c0_err']:.3f}, first {ratio[0]:.3f}, last {ratio[-1]:.3f}")
    # ---- plot (primary selection)
    fig, axs = plt.subplots(2, 2, figsize=(16, 10), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    for j, nm in enumerate(("R2", "R3")):
        ax, rax = axs[0, j], axs[1, j]
        rows = out["ups_bph"]
        xc = np.array([0.5 * (r["lo"] + r["hi"]) for r in rows]); xe = np.array([0.5 * (r["hi"] - r["lo"]) for r in rows])
        d = np.array([r[nm] for r in rows]); c = np.array([r[f"cms_{nm}"] for r in rows])
        es = np.array([np.hypot(r[f"{nm}_err"], r[f"{nm}_syst"]) for r in rows]); ec = np.array([np.hypot(r[f"cms_{nm}_stat"], r[f"cms_{nm}_syst"]) for r in rows])
        ax.errorbar(xc, d, xerr=xe, yerr=es, fmt="o", color="black", label="Student: fit yield ratio (2016H DoubleMuon, 2 files)")
        ax.errorbar(xc, c, xerr=xe, yerr=ec, fmt="s", color="tab:red", mfc="none", label="CMS-BPH-15-005 $\\sigma B$ ratio (13 TeV, 2015)")
        ax.set_ylabel("$\\Upsilon$(2S)/$\\Upsilon$(1S)" if nm == "R2" else "$\\Upsilon$(3S)/$\\Upsilon$(1S)")
        ax.set_ylim(0, 0.9 if nm == "R2" else 0.7)
        ax.legend(fontsize=11, loc="lower right")
        s_ = summary[("ups_bph", nm)]
        ax.text(0.03, 0.95, f"$|y|$<1.2; $\\chi^2$/ndf = {s_['chi2_no_aeff']:.1f}/{s_['ndf']} (no A$\\epsilon$ term)\nmean student/CMS = {s_['ratio_mean']:.2f} $\\pm$ {s_['ratio_mean_err']:.2f}", transform=ax.transAxes, va="top", fontsize=12)
        rax.errorbar(xc, d / c, xerr=xe, yerr=d / c * np.sqrt((es / d) ** 2 + (ec / c) ** 2), fmt="o", color="black")
        rax.axhline(1, color="gray", ls="--"); rax.set_ylim(0.4, 1.8); rax.set_ylabel("Student / CMS"); rax.set_xlabel("dimuon $p_T$ [GeV]")
        open_data_label(ax, hep, fontsize=14)
    savefig(fig, "M2_upsilon_ratios_vs_BPH15005")
    pickle.dump({"rows": out, "summary": {f"{k[0]}|{k[1]}": v for k, v in summary.items()}}, open(RESDIR / "M2_rows.pkl", "wb"))
    for nm, tid, name in (("R2", "M2a", "Upsilon(2S)/Upsilon(1S)"), ("R3", "M2b", "Upsilon(3S)/Upsilon(1S)")):
        s_ = summary[("ups_bph", nm)]
        n = nsigma(s_["p_with_aeff"])
        v = "INCONSISTENT" if n > 3 else ("TENSION" if n > 2 else "CONSISTENT")
        save_result(tid, student_result=f"{name} fitted yield ratio in pT groups 20-130 GeV, |y|<1.2, BPH-15-005 muon kinematics, 2016H DoubleMuon, 2 files",
                    counterpart={"report": "CMS-BPH-15-005", "inspire_paper": 1633431, "paper": "PLB 780 (2018) 251, arXiv:1710.11002", "hepdata_record": "ins1633431",
                                 "hepdata_table": "Table 12 (ratios), Tables 3, 4, 5 (cross sections)"},
                    level="ratio of detector-level fitted yields vs ratio of corrected cross sections x BF (unpolarised); acceptance*efficiency ratio not corrected in the student's data",
                    statistic=s_["chi2_with_aeff"], statistic_name=f"chi2 over pT groups (with assumed {ASSUMED_AEFF:.0%} A*eff ratio uncertainty)", ndf=s_["ndf"], p_value=s_["p_with_aeff"],
                    ratio=s_["ratio_mean"], ratio_err=s_["ratio_mean_err"], details={k_[0]: v_ for k_, v_ in summary.items() if k_[1] == nm},
                    student_selection_variant=summary[("ups_student", nm)], rows=out["ups_bph"], verdict=v,
                    reason="Trigger (DoubleMuon dimuon paths, not the BPH Upsilon trigger), no acceptance/efficiency correction, no vertex/bending requirement, 2015 vs 2016 data.")


if __name__ == "__main__":
    main()
