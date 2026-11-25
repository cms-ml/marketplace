#!/usr/bin/env python3
"""Assemble comparison.json (per run, per item: verdict + numbers) from out/*.json.
CMS Open Data, private work: the students' results are not CMS results.

Verdict thresholds (stated once, used for every numerical test):
  CONSISTENT    p >= 0.05 (|z| < 2) and, for shapes, |ratio slope| < 2 sigma
  TENSION       0.0027 <= p < 0.05 (2-3 sigma) or slope 2-3 sigma, or a clear trend
  INCONSISTENT  p < 0.0027 (> 3 sigma), slope > 3 sigma, or off by a known factor
  NOT COMPARABLE  differences that can neither be corrected nor bounded
Items 1 and 6 (set-up and method choices) are judged on definitions, see each entry.

Usage: python3 scripts/write_json.py  -> comparison.json
"""
import json, sys
from scipy.stats import norm

NAME = {"A": "with skill", "B": "without skill"}
R = json.load(open("out/recompute.json")); C = json.load(open("out/compare_cms.json"))
S = json.load(open("out/skim_check.json")); M = json.load(open("out/closure_mc_a.json"))
RA = json.load(open("../ws_skill/results.json")); RB = json.load(open("../ws_noskill/results.json"))


def z(p):
    return float(norm.isf(p / 2)) if p > 0 else 99.0


def shape_verdict(t):
    zs, zl = z(t["p"]), abs(t["slope_sigma"])
    if t["p"] < 0.0027 or zl > 3: return "INCONSISTENT"
    if t["p"] < 0.05 or zl > 2: return "TENSION"
    return "CONSISTENT"


out = {"disclaimer": "CMS Open Data (2016 G+H, UL NanoAODv9) studies by two agent runs, private work; not CMS results. "
                     "'CMS' refers to EXO-17-021 (arXiv:1808.03124, PRD 98 (2018) 112014, HEPData ins1685989 recid 85857, table 348181).",
       "thresholds": __doc__.split("Verdict thresholds")[1].split("Usage")[0].strip(),
       "reference": {"hepdata_table": 348181, "cms_bkg_total_64_503": C["cms_totals_64_503"]["bkg"],
                     "cms_data_total_64_503": C["cms_totals_64_503"]["data"], "lumi_fb": 35.9,
                     "selection": "HT_AK8>900, 2 AK8 pT>150 |eta|<2.5, tau21<0.45, tau32>0.57 (both), masym<0.1, deta<1.5, pruned mass, 60-450 GeV",
                     "abcd": "A: masym<0.1 & deta<1.5; B: masym<0.1 & deta>1.5; C: masym>0.1 & deta<1.5; D: both fail; TF=B/D sigmoid in m, applied to C",
                     "closure_syst": "10% yield (MC closure within +-10%); TF fit 1-4% shape; region-C count 1-23% shape; resonant 10% yield"},
       "emulation": C["emulation"], "skim_recount": {"files": [f["file"] for f in S["files"]], "all_agree": S["all_agree"]},
       "runs": {}}

for run, rr, res in (("A", R["A"], RA), ("B", R["B"], RB)):
    c = C[run]; lv = c["level"]
    d = {}
    d["1_comparability"] = dict(
        verdict="TENSION" if run == "A" else "INCONSISTENT",
        data_completeness=dict(verdict="CONSISTENT", data_skim_files_processed="48/48", all_skim_files="224/224",
                               recount_4_files_exact=S["all_agree"], n_events=res["n_events"]),
        numbers=dict(trigger=res["trigger"]["paths"], offline=res["trigger"]["offline_threshold"][:120],
                     abcd_variables=[v["name"] + " " + str(v["cut"]) for v in res["abcd_variables"]]),
        text=("Same ABCD pair as CMS (masym x deta) but boundaries 0.2/1.2 vs 0.1/1.5, fail band 0.2-0.4, no tau21/tau32 cuts, "
              "HT_AK4>1100 vs HT_AK8>900, no trimmed-mass triggers, soft-drop vs pruned mass." if run == "A" else
              "Different ABCD variables (N2 of jet 1 x N2 of jet 2), masym<0.2 as preselection, no deta cut, no tau32 cut, "
              "pT1>550/pT2>300 instead of HT_AK8>900; soft-drop vs pruned mass."))
    ch = rr["chi2"]
    d["2_method_validity"] = dict(
        verdict="CONSISTENT" if run == "A" else "TENSION",
        numbers=dict(incl_raw_BC_over_D=rr["incl_raw_BCoverD"], incl_raw_err=rr["incl_raw_err"],
                     student_qcd=rr["student_qcd_sum"], student_total=rr["student_qcd_plus_other"], student_total_err=rr["student_total_err"],
                     **({"mc_closure_incl": M["inclusive_ratio"], "mc_closure_err": M["inclusive_err"], "mc_closure_chi2": M["chi2"],
                         "mc_closure_slope_per100GeV": M["slope_per100GeV"], "mc_closure_slope_err": M["slope_err"], "mc_closure_last_bin": M["ratio"][-1],
                         "data_VR_pulls": [v["pull"] for v in res["validation_regions"] if v["definition"].startswith("data")],
                         "nonclosure_yield": res["non_closure_syst"]["correlated_yield_fraction"],
                         "shape_term_range": [min(res["non_closure_syst"]["per_bin_uncorrelated_shape_term"]), max(res["non_closure_syst"]["per_bin_uncorrelated_shape_term"])]}
                        if run == "A" else
                        {"perbin_TF_reproduced_max_rel_diff": rr["perbin_max_rel_diff"], "incl_TF_after_subtraction": rr["incl_sub"],
                         "mc_closure": rr["mc_closure_tests"], "nonclosure_rel_range": [min(res["non_closure_syst"]["relative_per_bin"]), max(res["non_closure_syst"]["relative_per_bin"])]})),
        text=("Inclusive B*C/D = %.0f +- %.0f reproduces the data (A obs %.0f, ratio %.3f); the student's fitted-TF prediction reproduces. "
              "MC closure 1.0006 inclusive but slopes (-2.8%%/100 GeV, 0.83 in 400-480); two data VRs at -2.9/-3.0 sigma enter the 1.6%% yield syst; "
              "per-bin shape term 1-20%% makes the unblinded chi2 p=0.9998 (over-coverage)." % (rr["incl_raw_BCoverD"], rr["incl_raw_err"], rr["N"]["A_obs"], rr["incl_raw_plus_nothing_vs_obs"])
              if run == "A" else
              "Per-bin TF prediction reproduced to 1e-16 (sum 80202); inclusive B*C/D = %.0f is 7%% lower because TF rises 0.28->2 with m_avg. "
              "MC VR_asym closes at 0.940+-0.002 and MC VR_pt1 at 0.90+-0.07, data VR_asym 1.009+-0.002 (4.4 sigma): the 5%% flat syst is taken from the VR it is then validated on; "
              "signal leakage into B and C (two-prong tag on each jet) not addressed." % rr["incl_raw_BCoverD"]))
    d["3_pred_vs_obs"] = dict(
        verdict="CONSISTENT",
        numbers=dict(student_chi2=ch["student"]["chi2"], ndf=ch["student"]["ndf"], p=ch["student_p"], max_local_sigma=ch["student"]["max_local"],
                     chi2_stat_only=ch["stat_only"]["chi2"], p_stat_only=ch["stat_only"]["p"], max_pull_stat_only=ch["stat_only"]["max_pull"],
                     obs_total=rr["N"]["A_obs"], pred_total=rr["student_qcd_plus_other"], obs_over_pred=rr["obs_over_pred_total"],
                     **({"chi2_diag_recomputed": ch["diag_stat_syst"]["chi2"]} if run == "A" else {"chi2_with_5pc_correlated": ch["flat5_correlated"]["chi2"], "p_5pc_correlated": ch["flat5_correlated"]["p"]})),
        text=("No local excess (max 0.66 sigma), as in EXO-17-021; chi2 2.2/14 is too small (p=0.9998): the systematics over-cover. "
              "Stat-only chi2 49.7/14 shows a real residual shape (+3.7 sigma at 60-80 GeV, -2 to -3 sigma at 140-260 GeV) absorbed by the shape term."
              if run == "A" else
              "No significant excess (max 1.35 sigma, 300-330 GeV), as in EXO-17-021; recomputed with the 5%% term correlated chi2 = %.1f/17. "
              "Data exceed prediction by 1.9%% overall and by 2-4.5%% in the four lowest bins (stat-only +2.8 sigma at 40-60 GeV)." % ch["flat5_correlated"]["chi2"]))
    sf = c["shape_full_unc"]
    d["4_shape_vs_cms"] = dict(
        verdict=shape_verdict(sf),
        numbers=dict(common_range=lv["range"], nbins=len(c["common_edges"]) - 1, chi2=sf["chi2"], ndf=sf["ndf"], p=sf["p"],
                     slope_per100GeV=sf["slope_per100GeV"], slope_err=sf["slope_err"], ratio_range=[sf["ratio_min"], sf["ratio_max"]],
                     chi2_cms_shape_only_unc=c["shape_cms_shape_only_unc"]["chi2"], p_cms_shape_only_unc=c["shape_cms_shape_only_unc"]["p"],
                     emulation_vs_cms_chi2=c["shape_emulation_vs_cms"]["chi2"], emulation_vs_cms_p=c["shape_emulation_vs_cms"]["p"],
                     emulation_vs_cms_slope=c["shape_emulation_vs_cms"]["slope_per100GeV"], emulation_vs_cms_slope_err=c["shape_emulation_vs_cms"]["slope_err"],
                     student_vs_emulation_chi2=c["shape_student_vs_emulation"]["chi2"], student_vs_emulation_p=c["shape_student_vs_emulation"]["p"],
                     ratio_per_bin=sf["ratio"]),
        text=("Predicted shape within 0.82-1.45 of CMS, no slope (-0.01+-0.05/100 GeV); chi2 27/11 (p=0.004) driven by 80-100 GeV (+45%%) and a dip at 140-180 GeV. "
              "A CMS-like selection on the same Open Data matches CMS on these bins (4.7/11) but not on the fine CMS bins (73/37) and its TF is 0.4-0.7x CMS below 100 GeV, so soft-drop vs pruned matters at low mass; the 140-180 GeV dip vs CMS remains attributed to the student's selection (75/11 vs the emulation)."
              if run == "A" else
              "Prediction much harder than CMS: ratio 0.67 at 100-140 GeV to 2-5 above 200 GeV, slope +0.86+-0.08/100 GeV (10 sigma). "
              "A CMS-like selection on the same Open Data is much closer to CMS (6.2/14 on these bins, 73/37 on CMS bins): the bulk of the difference is the student's pT1>550/pT2>300 and N2 selection."))
    d["5_level_and_closure_vs_cms"] = dict(
        verdict="INCONSISTENT (level) / CONSISTENT (closure)",
        numbers=dict(range=lv["range"], student_pred_scaled=lv["student_pred_scaled"], student_obs_scaled=lv["student_obs_scaled"], cms_bkg=lv["cms_bkg"],
                     ratio_student_over_cms=lv["ratio_pred_scaled_over_cms"], emulation_scaled=lv["emu_A_scaled"],
                     emulation_over_cms=lv["emu_over_cms_bkg"], student_over_emulation=lv["student_over_emu"],
                     cms_closure_yield_syst=0.10, student_mc_closure=(M["inclusive_ratio"] if run == "A" else rr["mc_closure_tests"]["SR"]["ratio_incl"]),
                     emulation_data_closure=C["emulation"]["incl_closure"], emulation_data_closure_err=C["emulation"]["incl_closure_err"]),
        text=("Yield x35.9/16.3 is %.2f x CMS. Measured on 4/48 files: %.2f from the student's selection vs a CMS-like one (explained: no substructure cuts, looser masym, HT>1100), "
              "%.2f between CMS-like Open Data and CMS (unexplained). Fig. 2 shows the per-jet tau21<0.45 efficiency is 4.7x higher with PUPPI tau21 than in CMS (CHS), so the CMS-like emulation is not faithful at the substructure level and 1.9 is a net of large compensating differences. "
              "Closure: inclusive MC 1.001 and 1.6%% yield syst vs CMS +-10%%; per bin within +-10%% except 400-480 GeV (0.83)."
              % (lv["ratio_pred_scaled_over_cms"], lv["student_over_emu"], lv["emu_over_cms_bkg"]) if run == "A" else
              "Yield x35.9/16.3 is %.2f x CMS, a near-agreement by accident: student/CMS-like = %.2f (tighter pT, looser masym, no deta cut) times CMS-like/CMS = %.2f (unexplained, common to both runs; the emulation differs from CMS in tau21 efficiency by 4.7x per jet, Fig. 2). "
              "Closure: MC SR 0.991, per bin 0.90-1.11, syst 5.5-17%% per bin, comparable to CMS +-10%%; MC VR_asym 0.94 and VR_pt1 0.90 at the edge of it."
              % (lv["ratio_pred_scaled_over_cms"], lv["student_over_emu"], lv["emu_over_cms_bkg"])))
    d["6_method_choices_vs_cms"] = dict(
        verdict="CONSISTENT" if run == "A" else "INCONSISTENT",
        numbers=dict(variables=[v["name"] for v in res["abcd_variables"]], tf_form=res["tf"]["form"][:160],
                     blinding="prediction frozen (fits/stage1.json) before --unblind" if run == "A" else "prediction frozen (fits/blind_results.json) before unblind.py"),
        text=("Same variables as CMS (masym, deta); TF is the deta ratio (CMS: masym ratio), algebraically the same A=BC/D; "
              "fitted smooth function of m_avg (quadratic by F-test vs CMS sigmoid); VRs then unblinding, in the right order."
              if run == "A" else
              "Not the CMS variables: N2 x N2 (CMS used substructure as preselection, kinematic masym x deta for ABCD); per-bin TF instead of a fitted function; "
              "blinding order correct."))
    out["runs"][NAME[run]] = d

out["7_skill_effect"] = dict(
    with_skill_loaded=["background-est:abcd", "cms:trigger-efficiency", "cms:awkward-array", "cms:hist", "af-fnal-lpc:lpc-condor"],
    without_skill_loaded=["cms:trigger-efficiency", "cms:awkward-array", "cms:hist", "af-fnal-lpc:lpc-condor"],
    traced_to_skill=[
        "variable pair: skill pattern 1 asks to rank kinematic pairs (rapidity separation, mass balance) by kappa and warns against two substructure variables of two jets; with skill ranked 6 variables and chose masym x deta (the CMS pair); without skill chose N2 x N2, the warned-against case, and found TF 0.28->2 in m_avg",
        "TF form: skill table (flat -> inclusive, smooth -> tf_fit_ftest, per bin last resort); with skill fitted a quadratic by F-test; without skill used per-bin TF",
        "validation: skill's shifted-boundary VRs in MC and data; with skill ran 3+3; without skill ran 3 including two inverted-cut sidebands",
        "non-closure: skill rule (|1-ratio| if |pull|>2) gave with skill 1.6% from the -3 sigma data VR; without skill derived a flat 5% from the VR it then used as validation, which the skill forbids",
        "unblinded chi2: with skill used chi2_cov with the full covariance; without skill a diagonal chi2"],
    skill_wrong_or_missing=[
        "no helper to apply a fitted TF(m) to C with covariance propagation (the with-skill run wrote it)",
        "no guidance on the per-bin shape term; the with-skill 'largest excess over 7 tests' rule over-covers: unblinded chi2 2.2/14, p=0.9998",
        "no check for a chi2 that is too small (over-coverage) at unblinding",
        "fail-band width (kappa 1.09 -> 1.008 when D is restricted to 0.2-0.4) not mentioned",
        "tf_fit_ftest fits polynomials only, although the text mentions a sigmoid (the CMS choice)",
        "tf_flatness assumes pass = y > ycut",
        "signal contamination without signal MC: no recipe (both runs skipped signal injection)",
        "nothing on comparing to a published analysis or on soft-drop vs pruned / PUPPI vs CHS substructure differences"])
P = json.load(open("out/plots_v2.json"))
T = json.load(open("out/tests_perbin.json"))
f2 = P["fig2"]; cl = P["cmslike_od_vs_cms"]; tf = P["tf_vs_mavg_vs_cms"]; kh = P["closure_heatmap"]; sb = P["syst_breakdown_vs_cms"]
out["plots"] = {
    "mavg_SR_vs_cms": dict(files=["plots/mavg_SR_vs_cms.png", "plots/mavg_SR_vs_cms.pdf"],
                           with_skill=P["mavg_SR_vs_cms_A"], without_skill=P["mavg_SR_vs_cms_B"],
                           text="Shape (items 3-4) unchanged; absolute panel: per-bin (prediction x35.9/16.3)/CMS bkg 5.3-9.4 (with skill), 0.89-6.6 (without skill)."),
    "cmslike_od_vs_cms": dict(files=["plots/cmslike_od_vs_cms.png", "plots/cmslike_od_vs_cms.pdf"], **cl,
                              text="EXO-17-021-like selection on 4/48 Open Data files: 1.93x CMS data, flat in m_avg; QCD MC (subset) 1.99x CMS bkg, i.e. Open Data and MC agree with each other; "
                                   "the CMS-like ABCD with a sigmoid TF closes (pred/obs 0.996). Fine-bin shape vs CMS data chi2 73/37 (p=4e-4)."),
    "tf_vs_mavg_vs_cms": dict(files=["plots/tf_vs_mavg_vs_cms.png", "plots/tf_vs_mavg_vs_cms.pdf"], **{k: v for k, v in tf.items() if k != "norms"},
                              text="Normalised to 200-400 GeV, the CMS-like Open Data B/D follows the CMS sigmoid above 125 GeV but is 0.43-0.68x CMS at 60-100 GeV (soft-drop vs pruned at low mass); "
                                   "the with-skill masym ratio (CMS convention) has the CMS shape; the without-skill N2 TF rises 3x, the CMS TF 1.8x."),
    "fig2": dict(files=[f"plots/fig2_{v}.png" for v in ("masym", "deta", "tau21_lead", "tau21_sub", "tau32_lead", "tau32_sub")], **f2,
                 text="masym and deta N-1 shapes agree with CMS to TVD 0.09/0.03; tau21<0.45 keeps 44%/42% of jets in Open Data (PUPPI) vs 9.4%/9.2% in CMS (CHS): 4.7x per jet. "
                      "The product of marginal efficiency ratios (~19x for tau cuts) is far above the observed 1.9x yield ratio, so the CMS-like emulation is not a faithful CMS proxy at the substructure level."),
    "syst_breakdown_vs_cms": dict(files=["plots/syst_breakdown_vs_cms.png", "plots/syst_breakdown_vs_cms.pdf"],
                                  with_skill={k: v for k, v in sb["A"].items() if not k.startswith("_") or k.startswith("_check")},
                                  without_skill={k: v for k, v in sb["B"].items()}, cms=sb["CMS"],
                                  text="Inclusive: with skill 1.6% yield + 1.25% shape + 1.6% other; without skill 4.75% yield + 1.1% shape + 1.85% other; CMS 10% yield. Per-bin shape terms (1-19%, 1.6-14%) reach the CMS region-C count range (1-23%). "
                                       "The without-skill run does not vary the non-QCD yield it adds in A."),
    "closure_summary": dict(files=["plots/closure_summary.png", "plots/closure_summary.pdf"], text="Relabelled; CMS +-10% band shown on both panels."),
    "closure_heatmap": dict(files=["plots/closure_heatmap.png", "plots/closure_heatmap.pdf"], **kh,
                            text="kappa-1 at CMS point in CMS-like QCD MC +0.4+-1.4%; with-skill point in its selection +0.8+-0.4% (band) but +9.4% if the fail side is all masym>0.2; "
                                 "without-skill N2xN2 inclusive kappa-1 = +9.4+-0.6% at (0.3,0.3), 7-37% over the grid (it used a per-bin TF, which absorbs part of this)."),
    "nonclosure_heatmap": dict(files=["plots/nonclosure_heatmap.png", "plots/nonclosure_heatmap.pdf"], with_skill=P["nonclosure_heatmap"]["A"], without_skill=P["nonclosure_heatmap"]["B"],
                               reproduced_with_skill_stored=all(abs(t["incl_ratio"] - t["stored_ratio"]) < 1e-4 for t in T["with_skill"]["tests"] if "stored_ratio" in t),
                               text="With skill: coherent -3 to -6% (|pull| up to 5.7) in 160-300 GeV in MC and data x-shifted VRs, covered by the shape term. "
                                    "Without skill: MC/data VR_asym have |pull| 15-42 in the lowest bins; unblinded SR all |pull|<1.4."),
}
out["review_with_skill_plots"] = dict(
    verdict="mostly correct; supports the analysis with two caveats",
    correct=["closure_mc_perbin, nonclosure_map and closure_map_mc reproduce my independent recomputation (MC closure 0.83 in 400-480 GeV; pulls identical; kappa-1 +0.8% at the chosen point)",
             "closure_mc_variations shows why the 0.2-0.4 fail band and the fitted TF were chosen (+4.4% and chi2 609/14 otherwise)",
             "closure_map_data honestly shows kappa-1 +0.7 to +4.1% (2-8.5 sigma) in shifted data regions, above the 1.6% yield syst"],
    problems=["REPORT.md says the MC closure is '-4% in the last bin'; the plot shows 0.83 (-17%); -4.0 is the pull",
              "independence_ratio_vs_deta: data rise 1.087 -> 1.101 over deta 1.35-2.35 (about 2 sigma) and 2-3% below MC; called 'flat within 1-3%'",
              "substructure_dists/roc show tau21 and N2 are strong discriminators (QCD mistag 0.19-0.20 at 60% V eff.) that were not used, unlike CMS; a missed preselection",
              "cosmetic: bold mplhep 'CMS' + 'Simulation Open Data, private work' header overlaps the luminosity text on most plots; axis labels overlap in design_boundary_scan"],
    verdict_change="none: the data kappa maps strengthen the TENSION-level caveat on the 1.6% yield syst but the matching per-bin VRs (0.984-0.996) remain covered")
out["verdict_changes"] = ("No verdict changed. Explanations changed: (1) Fig. 2 shows the CMS-like Open Data emulation differs from CMS by 4.7x per jet in tau21<0.45 efficiency, "
                          "so the 1.88x yield factor is a net of large compensating differences, not a small residual; (2) on fine CMS bins the emulation shape differs from CMS (73/37) "
                          "and its TF is 0.4-0.7x CMS below 100 GeV, so 'soft-drop vs pruned does not change the shape' is withdrawn below ~100 GeV.")
json.dump(out, open("comparison.json", "w"), indent=1)
for run in "AB":
    print(NAME[run] + ": " + ", ".join(f"{k}={v['verdict']}" for k, v in out["runs"][NAME[run]].items()))
sys.exit(0)
