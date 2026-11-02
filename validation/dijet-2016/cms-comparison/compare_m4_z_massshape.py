#!/usr/bin/env python3
"""M4 (shape): dimuon mass shape around the Z vs CMS-SMP-17-001 Table 5 (HEPData ins1711625: fiducial dsigma/dm in the dimuon channel, NO FSR correction,
detector-resolution unfolded, efficiency/acceptance-corrected, stat and exp uncertainties separately).  The Table 5 columns are in pb/GeV.

Fiducial region of SMP-17-001 (read from the paper, arXiv:1812.10529, Sec. 3): leading muon pT>22 GeV, subleading pT>10 GeV, |eta|<2.4, opposite charge.
Student selection re-run on the same 2 files with that fiducial cut (rerun_dimuon.py variants 'smp001' and 'smp001_id'), 1 GeV bins rebinned to the
CMS bins (60, 64, 68, 72, 76, 81, 86, 91, 96, 101, 106, 110, 115, 120 GeV).  Both normalised to unit sum over 60-120 GeV.
CMS errors: stat (+) exp in quadrature, treated as uncorrelated (no covariance is published for the fiducial result; this is conservative for a shape).

Usage: compare_m4_z_massshape.py --dimuon-dir <dir with histograms.pkl> --cache <cache>
"""
import argparse
import pickle
import sys

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import *   # noqa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dimuon-dir", required=True)
    ap.add_argument("--cache", required=True)
    a = ap.parse_args()
    h = pickle.load(open(Path(a.dimuon_dir) / "histograms.pkl", "rb"))
    R = pickle.load(open(Path(a.cache) / "dimuon_rerun.pkl", "rb"))
    rec = hepdata_dir(a.cache, 1711625)
    t = read_table(rec, "Table 5")
    lo, hi = t["indep"][0]["low"], t["indep"][0]["high"]
    d = t["dep"][0]
    sig = d["value"]; es = d["errors"]["$\\delta_{\\text{stat}}$"]; ee = d["errors"]["$\\delta_{\\text{exp}}$"]
    tot = t["dep"][1]["value"]
    log("Table 5 dependent variables:", [(x["name"], x["units"]) for x in t["dep"]], "; total = sqrt(stat^2+exp^2) check:", float(np.max(np.abs(np.hypot(es, ee) - tot) / tot)))
    # Z-region bins 60-120
    sel = (lo >= 60 - 1e-9) & (hi <= 120 + 1e-9)
    lo, hi, sig, es, ee = lo[sel], hi[sel], sig[sel], es[sel], ee[sel]
    edges = np.append(lo, hi[-1])
    w = np.diff(edges)
    A = sig * w
    pc = A / A.sum()
    # relative errors on the bin yields, then on the normalised fractions assuming uncorrelated
    err_tot = np.hypot(es, ee) * w / A.sum()
    err_stat = es * w / A.sum()
    zedges = R["edges"]["zm"]

    def rebin(counts):
        idx = [int(np.where(np.isclose(zedges, e))[0][0]) for e in edges]
        return np.add.reduceat(counts, idx[:-1])
    out = {}
    plt, hep = setup_mpl()
    variants = {"student (unchanged, loose pT>3)": h["m_z"].values(), "smp001": R["hist"]["zmass_smp001"], "smp001_id": R["hist"]["zmass_smp001_id"]}
    keys = {"student (unchanged, loose pT>3)": "student", "smp001": "smp001", "smp001_id": "smp001_id"}
    for name, cnt in variants.items():
        ns = rebin(cnt)
        N = ns.sum()
        ps = ns / N
        es_ = np.sqrt(ns) / N
        dd = ps - pc
        chi2_tot = float(np.sum(dd[:-1] ** 2 / (es_[:-1] ** 2 + err_tot[:-1] ** 2)))       # drop one bin (unit-sum constraint), diagonal approximation
        chi2_stat = float(np.sum(dd[:-1] ** 2 / (es_[:-1] ** 2 + err_stat[:-1] ** 2)))
        ndf = len(ps) - 1
        r = ps / pc
        rerr = r * np.sqrt((es_ / ps) ** 2 + (err_tot / pc) ** 2)
        sl = ratio_slope(0.5 * (edges[1:] + edges[:-1]) / 100.0, r, rerr)
        out[keys[name]] = dict(N=float(N), chi2_total=chi2_tot, chi2_statonly=chi2_stat, ndf=ndf, p_total=pvalue(chi2_tot, ndf), p_statonly=pvalue(chi2_stat, ndf),
                               ratio=r.tolist(), ratio_err=rerr.tolist(), slope_per_100GeV=sl["b"], slope_err=sl["b_err"], p_s=ps.tolist())
        log(f"M4 [{name}]: N = {N:.0f}; chi2/ndf = {chi2_tot:.1f}/{ndf} (CMS stat+exp, p={pvalue(chi2_tot, ndf):.2e}); with CMS stat only {chi2_stat:.1f}; ratio per bin: {np.round(r, 3).tolist()}")
    # ---- resolution estimate for the 5-GeV bins: Z Breit-Wigner (PDG width) folded with a Gaussian of sigma_eff, bin-integrated ratio folded/unfolded
    from scipy import special
    def bw_frac(sig_res):
        xs = np.arange(40, 140, 0.02)
        bw = (2.4955 / 2 / np.pi) / ((xs - 91.1876) ** 2 + (2.4955 / 2) ** 2)
        if sig_res > 0:
            dens = special.voigt_profile(xs - 91.1876, sig_res, 2.4955 / 2)
        else:
            dens = bw
        idx = np.digitize(xs, edges) - 1
        ok = (idx >= 0) & (idx < len(edges) - 1)
        return np.bincount(idx[ok], weights=dens[ok] * 0.02, minlength=len(edges) - 1)
    fold = bw_frac(1.34) / bw_frac(0.0)
    log("Breit-Wigner peak region: folded/unfolded per CMS bin for sigma=1.34 GeV (M1 core+tail effective width):", np.round(fold, 3).tolist())
    # student (fiducial, id) corrected by the folding factors, as an estimate of the resolution effect only
    ns = rebin(R["hist"]["zmass_smp001_id"])
    ps_corr = ns / fold
    ps_corr = ps_corr / ps_corr.sum()
    es_ = np.sqrt(ns) / ns.sum()
    chi2c = float(np.sum((ps_corr - pc)[:-1] ** 2 / (es_[:-1] ** 2 + err_tot[:-1] ** 2)))
    out["resolution_corrected_smp001_id"] = dict(chi2_total=chi2c, ndf=len(pc) - 1, fold=fold.tolist(), p=pvalue(chi2c, len(pc) - 1))
    log(f"smp001_id corrected by BW-resolution folding factors: chi2/ndf = {chi2c:.1f}/{len(pc)-1}")
    # ---- plot
    xc = 0.5 * (edges[1:] + edges[:-1])
    fig, (ax, rax) = plt.subplots(2, 1, figsize=(10, 10), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    cols = {"student": ("tab:gray", "o"), "smp001": ("black", "s"), "smp001_id": ("tab:blue", "^")}
    for k, lab in (("student", "Student histogram (unchanged, loose pT>3 GeV)"), ("smp001", "re-run: pT>22/10 GeV, |$\\eta$|<2.4"), ("smp001_id", "re-run: pT>22/10, tight ID + iso<0.15")):
        ns = rebin({"student": h["m_z"].values(), "smp001": R["hist"]["zmass_smp001"], "smp001_id": R["hist"]["zmass_smp001_id"]}[k])
        ps = ns / ns.sum()
        ax.errorbar(xc, ps / w, yerr=np.sqrt(ns) / ns.sum() / w, fmt=cols[k][1], color=cols[k][0], ms=5, label=f"{lab}: $\\chi^2$/ndf={out[k]['chi2_total']:.0f}/{out[k]['ndf']}")
        rax.errorbar(xc, np.array(out[k]["ratio"]), yerr=np.array(out[k]["ratio_err"]), fmt=cols[k][1], color=cols[k][0], ms=5)
    ax.errorbar(xc, pc / w, yerr=err_tot / w, fmt="D", color="tab:red", mfc="none", ms=6, label="CMS-SMP-17-001 Table 5 (fiducial, no FSR corr., 2015)")
    ax.set_yscale("log")
    ax.set_ylabel("normalised $(1/N)\\,dN/dm$ [1/GeV]")
    ax.legend(fontsize=11, loc="upper right")
    rax.axhline(1, color="gray", ls="--"); rax.set_ylabel("Student / CMS"); rax.set_xlabel("$m_{\\mu\\mu}$ [GeV]"); rax.set_ylim(0.6, 1.4)
    open_data_label(ax, hep)
    savefig(fig, "M4_Z_massshape_vs_SMP17001")
    v = out["smp001"]            # primary: the student's code with the kinematic fiducial region only (as specified); smp001_id reported alongside
    n_tot = nsigma(v["p_total"])
    verdict = "INCONSISTENT" if n_tot > 3 else ("TENSION" if n_tot > 2 else "CONSISTENT")
    save_result("M4", student_result="dimuon mass 60-120 GeV, re-run on the same 2 files with the SMP-17-001 fiducial cuts (leading pT>22, subleading pT>10, |eta|<2.4; student loose ID, no isolation); shape normalised to 60-120 GeV",
                counterpart={"report": "CMS-SMP-17-001", "inspire_paper": 1711625, "paper": "JHEP 12 (2019) 059, arXiv:1812.10529", "hepdata_record": "ins1711625",
                             "hepdata_table": "Table 5 (fiducial, dimuon, no FSR correction); Table 3 (full phase space, FSR-corrected) is not comparable"},
                level="shape: detector-level counts vs efficiency/acceptance-corrected, resolution-unfolded fiducial dsigma/dm (post-FSR), 2015 data, both normalised on 60-120 GeV",
                statistic=v["chi2_total"], statistic_name="chi2, student stat + CMS (stat (+) exp) uncorrelated", ndf=v["ndf"], p_value=v["p_total"], ratio=None, details=out, variant_tight_id_iso={k_: out["smp001_id"][k_] for k_ in ("chi2_total", "ndf", "p_total", "chi2_statonly")}, verdict=verdict,
                reason="Detector-level vs unfolded (resolution moves events out of the peak bins), no efficiency correction vs mass, 2016H vs 2015, no momentum corrections; CMS errors treated uncorrelated (conservative); "
                       "stat-only CMS version in details.")
    save_result("M4b_table3", student_result="dimuon mass shape vs SMP-17-001 Table 3 (full phase space, FSR-corrected)", counterpart={"report": "CMS-SMP-17-001", "hepdata_table": "Table 3"},
                verdict="NOT COMPARABLE", reason="Table 3 is acceptance-corrected to the full phase space and FSR-corrected (dressed leptons); the student data are fiducial detector-level with no acceptance/FSR correction. "
                "Needs the acceptance and FSR response from simulation (not available here).")


if __name__ == "__main__":
    main()
