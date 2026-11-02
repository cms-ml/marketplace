#!/usr/bin/env python3
"""D4 (trend): student's Z' -> bb event efficiencies vs mass (summary.json: btag_efficiency) against CMS-EXO-20-008
Figure 2 (acceptance x efficiency, HEPData ins1920627, table 'Figure 2', average of 2016-2018).

Mapping of the quantities (student -> CMS):
  n_selected_deta / n_generated                         -> 'Preselection efficiency' (acceptance before b tagging)
  event_eff_2b_medium                                   -> 'Double b-tagged efficiency'
  event_eff_1b_medium - event_eff_2b_medium (exactly 1) -> 'Single b-tagged efficiency'
  event_eff_1b_medium (>=1 b)                           -> single + double
  event_eff_*_rel_to_selected                           -> b-tag efficiency given the preselection (CMS: category / preselection)
Usage: compare_d4_efficiency.py --cache <cache dir>
"""
import argparse
import json
import sys

import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parent))
from common import *   # noqa


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--cache", required=True)
    a = ap.parse_args()
    rec = hepdata_dir(a.cache, 1920627)
    t = read_table(rec, "Figure 2")
    M_c = t["indep"][0]["value"]
    cms = {d["name"]: d["value"] for d in t["dep"]}
    log("CMS Figure 2 columns:", list(cms))
    s = json.load(open(STUDENT_DIR / "summary.json"))["btag_efficiency"]
    M_s = np.array([r["mass"] for r in s], float)
    N = np.array([r["n_generated"] for r in s], float)
    sel = np.array([r["n_selected_deta"] for r in s], float)
    e1 = np.array([r["event_eff_1b_medium"] for r in s]); e2 = np.array([r["event_eff_2b_medium"] for r in s])
    n1 = np.round(e1 * N); n2 = np.round(e2 * N)
    # binomial errors
    be = lambda k, n: np.sqrt(np.maximum(k, 1) * (1 - k / n) / n ** 2) * np.sqrt(1.0)
    S = {"presel": (sel / N, be(sel, N)), "2b": (n2 / N, be(n2, N)), "excl1b": ((n1 - n2) / N, np.sqrt(be(n1, N) ** 2 + be(n2, N) ** 2)),
         "ge1b": (n1 / N, be(n1, N))}
    C = {"presel": cms["Preselection efficiency"], "2b": cms["Double b-tagged efficiency"], "excl1b": cms["Single b-tagged efficiency"],
         "ge1b": cms["Single b-tagged efficiency"] + cms["Double b-tagged efficiency"]}
    # overlap in mass: 1800-5000 GeV
    common = [(i, int(np.where(M_c == m)[0][0])) for i, m in enumerate(M_s) if m in M_c]
    si = np.array([i for i, _ in common]); ci = np.array([j for _, j in common])
    M = M_s[si]
    log("overlapping masses:", M.tolist())
    out = {}
    plt, hep = setup_mpl()
    fig, axs = plt.subplots(2, 1, figsize=(10, 10), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    ax, rax = axs
    sty = {"presel": ("tab:gray", "o"), "2b": ("tab:red", "s"), "excl1b": ("tab:blue", "^"), "ge1b": ("tab:green", "v")}
    lab = {"presel": "acceptance (pre b tag)", "2b": "2 b tags", "excl1b": "exactly 1 b tag", "ge1b": ">=1 b tag"}
    for k in ("presel", "2b", "excl1b", "ge1b"):
        v, e = S[k]
        v, e = v[si], e[si]
        c = C[k][ci]
        R = v / c
        Re = R * (e / v)                  # CMS values are given to 3 digits only: add rounding as 0.0005/c
        Re = np.hypot(Re, R * 0.0005 / c)
        sl = ratio_slope(M / 1e3, R, Re)
        # shape-vs-mass statistic: normalise both curves to unit sum over the common masses
        vn, cn = v / v.sum(), c / c.sum()
        chi2_shape = float(np.sum((vn - cn) ** 2 / ((e / v.sum()) ** 2 + (0.0005 / c.sum()) ** 2)))
        # Spearman correlation of the two curves vs mass (trend agreement)
        from scipy import stats as st
        rho, prho = st.spearmanr(v, c)
        out[k] = dict(masses=M.tolist(), student=v.tolist(), cms=c.tolist(), ratio=R.tolist(), ratio_err=Re.tolist(), ratio_mean=float(np.mean(R)),
                      ratio_first=float(R[0]), ratio_last=float(R[-1]), slope_per_TeV=sl["b"], slope_err=sl["b_err"], chi2_shape_normalised=chi2_shape,
                      ndf_shape=len(M) - 1, spearman_rho=float(rho), spearman_p=float(prho))
        log(f"D4 {k:7s}: ratio student/CMS mean {np.mean(R):.3f} (first {R[0]:.3f}, last {R[-1]:.3f}); slope {sl['b']:+.3f}+-{sl['b_err']:.3f} /TeV; "
            f"normalised-shape chi2 {chi2_shape:.0f}/{len(M)-1}; Spearman rho {rho:.2f}")
        col, mk = sty[k]
        ax.errorbar(M, v, yerr=e[si] if False else e, fmt=mk + "-", color=col, ms=5, label=f"Student {lab[k]}")
        ax.plot(M, c, mk, ls="--", color=col, mfc="none", ms=7, label=f"CMS {lab[k]}")
        rax.errorbar(M, R, yerr=Re, fmt=mk + "-", color=col, ms=5)
    # b-tag efficiency GIVEN the preselection (removes the acceptance offset)
    for k in ("2b", "ge1b"):
        v = S[k][0][si] / S["presel"][0][si]
        c = C[k][ci] / C["presel"][ci]
        out[k + "_given_presel"] = dict(student=v.tolist(), cms=c.tolist(), ratio=(v / c).tolist(), ratio_mean=float(np.mean(v / c)))
        log(f"D4 {k} given the preselection: student/CMS = {np.round(v/c,3).tolist()}")
    ax.set_ylabel("acceptance $\\times$ efficiency")
    ax.set_ylim(0, 0.6)
    ax.legend(fontsize=10, ncol=2, loc="upper right")
    ax.text(0.04, 0.05, "CMS-EXO-20-008 (PRD 108 (2023) 012009) Fig. 2: 2016-2018 average, wide jets, mjj>1530 GeV,\nstudent: Z'$\\to$b$\\bar{b}$ (narrow, Open Data MC), AK4 CHS, DeepJet M, no SF, mjj>1058 GeV", transform=ax.transAxes, fontsize=10)
    rax.axhline(1, color="gray", ls="--")
    rax.set_ylabel("Student / CMS")
    rax.set_xlabel("Z' mass [GeV]")
    rax.set_ylim(0.5, 2.5)
    open_data_label(ax, hep)
    savefig(fig, "D4_zprime_efficiency_vs_mass_EXO20008")

    # per-jet b-tag efficiency quoted in the paper text: ~75, 45, 10 % at jet pT 0.2, 1.0, 3.0 TeV (not a HEPData table; text values)
    # student per-jet Medium efficiency for true b jets vs Z' mass
    effM = {r["mass"]: r["eff_M"] for r in json.load(open(STUDENT_DIR / "summary.json"))["btag_efficiency"]}

    def ver(r):
        return "INCONSISTENT"
    for k, tid, name in (("2b", "D4a", "2 b tags"), ("excl1b", "D4b", "exactly 1 b tag"), ("presel", "D4c", "acceptance before b tagging")):
        o = out[k]
        save_result(tid, student_result=f"Z'->bb event efficiency vs mass, {name}: summary.json btag_efficiency (selected/generated, |deta|<1.1, tight jets |eta|<2.4, mjj>1058)",
                    counterpart={"report": "CMS-EXO-20-008", "inspire_paper": 2676943, "hepdata_record": "ins1920627", "hepdata_table": "Figure 2",
                                 "paper": "PRD 108 (2023) 012009, arXiv:2205.01835"},
                    level="trend: MC efficiency vs mass (student detector-level, no SF) vs CMS acceptance x efficiency (2016-2018 average, with SF)",
                    statistic=o["chi2_shape_normalised"], statistic_name="chi2 of the unit-normalised curves (student stat. + CMS 3-digit rounding)", ndf=o["ndf_shape"],
                    p_value=pvalue(o["chi2_shape_normalised"], o["ndf_shape"]), ratio=o["ratio_mean"], details=o,
                    verdict=ver(o),
                    reason=("ratio student/CMS %.2f on average (first %.2f, last %.2f); trend in mass %s; the acceptance offset and the faster fall of the CMS 2b efficiency with mass are "
                            "discussed in COMPARISON.md" % (o["ratio_mean"], o["ratio_first"], o["ratio_last"], "see slope")))
    save_result("D4d_per_jet", student_result="per-jet DeepJet Medium efficiency for true b jets in Z' MC", counterpart={"report": "CMS-EXO-20-008 text (not HEPData)"},
                level="text values ~75/45/10 % at jet pT 0.2/1/3 TeV vs student eff_M", student_eff_M=effM, verdict="NOT COMPARABLE",
                reason="Quoted in the paper text only, at fixed jet pT; the student quotes per Z' mass (jet pT ~0.4 M, broad). Indicative only.")
    json.dump(out, open(RESDIR / "D4_curves.json", "w"), indent=1)


if __name__ == "__main__":
    main()
