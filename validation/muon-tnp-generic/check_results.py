#!/usr/bin/env python3
"""Checks on the muon-tnp-generic validation outputs (summary.json, plots/, text files).

Does not rerun the analysis. Standard library only, so CI can run it. Tolerances and why: README.md.

Usage:
    check_results.py [validation/muon-tnp-generic]

Stdout: one "PASS|FAIL|INFO <check>: <detail>" line per check, then SUMMARY=<n_pass>/<n>.
Exit codes: 0 all pass, 1 some check failed, 2 summary.json missing or unreadable.
"""
from __future__ import annotations

import json
import os
import re
import sys

results: list[tuple[str, str, str]] = []


def check(name: str, ok: bool, detail: str) -> None:
    results.append(("PASS" if ok else "FAIL", name, detail))


def info(name: str, detail: str) -> None:
    results.append(("INFO", name, detail))


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(base, "summary.json")) as f:
            s = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: cannot read summary.json in {base}: {e}", file=sys.stderr)
        return 2

    # (a) the presets are bit-identical to the pre-change tnp.py and to the spelled-out definitions
    for wp, a in s["a_preset_equivalence"].items():
        check(f"a {wp} new == pre-change tnp.py", a["new_vs_old"]["identical"],
              f"{a['new_vs_old']['bins_a']} bins, max |diff| {a['new_vs_old']['max_abs_diff']}")
        check(f"a {wp} --num/--den/--tag-* == --wp", a["expr_vs_preset"]["identical"],
              f"{a['expr_vs_preset']['bins_a']} bins, max |diff| {a['expr_vs_preset']['max_abs_diff']}")
        check(f"a {wp} new == stored pre-change output (results/pre_change_{wp}.json)", a["new_vs_stored_reference"]["identical"],
              f"max |diff| {a['new_vs_stored_reference']['max_abs_diff']}; pre-change script ran this time: {a['old_ran']}")

    # (b) new working points against the POG: weighted SF/POG over 30-60 GeV within 1 percent
    b = s["b_working_points"]
    for name in ("mediumid", "looseid", "highptid", "softid", "looseiso_med", "tkiso_loose"):
        if name not in b:
            check(f"b {name} present", False, "missing")
            continue
        r = b[name]
        w = r["weighted_sf_over_pog_30_60"]
        check(f"b {name} weighted SF/POG 30-60 GeV", w is not None and abs(w - 1) < 0.01,
              f"{w:.4f} +- {r['weighted_sf_over_pog_30_60_err']:.4f} ({r['pog']}); RMS pull(total) {r['rms_pull_total']:.2f}")
        worst = min(r["per_eta_weighted_30_60"].items(), key=lambda kv: -abs((kv[1] or 1) - 1))
        info(f"b {name} per |eta|", f"worst |eta| bin {worst[0]}: {worst[1]:.4f}; |pull_total| > 3 in {r['n_abs_pull_total_gt3']}/{r['n_bins']} bins")
    for name in ("wp_tightid", "wp_tightiso", "wp_isomu24"):
        r = b[name]
        info(f"b {name} weighted SF/POG 30-60 GeV", f"{r['weighted_sf_over_pog_30_60']:.4f}; per |eta| "
             + ", ".join(f"{k} {v:.4f}" for k, v in r["per_eta_weighted_30_60"].items()))
    bad_eff, bad_sf, nb, nfail = [], [], 0, 0
    for name, r in b.items():
        nb += r["n_bins"]
        nfail += r["n_fit_failed"]
    for name in ("isomu22", "mu17leg"):
        r = b.get(name)
        if r is None:
            check(f"b {name} present", False, "missing")
            continue
        plateau = [x["eff_data"] for x in r["bins"] if x["pt"][0] >= 30]
        check(f"b {name} offline run", r["exit"] in (0, 1) and not r["pog_available"] and not r["pileup_weights"]
              and r["n_bins"] > 0 and r["binning_source"] in ("explicit", "default"),
              f"exit {r['exit']}, {r['n_bins']} bins, POG {r['pog_available']}, pileup {r['pileup_weights']}")
        check(f"b {name} plateau efficiency in [0.5, 1]", bool(plateau) and all(0.5 <= x <= 1 for x in plateau),
              f"data eff at pT >= 30 GeV: {min(plateau):.3f}-{max(plateau):.3f}")
        for x in r["bins"]:
            for k in ("eff_data", "eff_mc"):
                if not 0 <= x[k] <= 1:
                    bad_eff.append(f"{name} {x['aeta']} {x['pt']} {k}")
            if x["pt"][0] >= 30 and x["sf_total_err"] < 0.05 and not 0.8 <= x["sf"] <= 1.2:
                bad_sf.append(f"{name} {x['aeta']} {x['pt']} SF {x['sf']:.3f}")
    for name, r in b.items():
        for k, v in (r.get("sf_40_50") or {}).items():
            if v[1] < 0.05 and not 0.9 <= v[0] <= 1.1:
                bad_sf.append(f"{name} {k} 40-50 SF {v[0]:.3f}")
    check("b efficiencies in [0, 1]", not bad_eff, f"violations: {bad_eff[:3] or 'none'}")
    check("b SFs in range", not bad_sf, f"40-50 GeV SFs in [0.9, 1.1], trigger plateau SFs in [0.8, 1.2]; violations: {bad_sf[:3] or 'none'}")
    check("b fits converged", nfail <= 0.1 * nb, f"{nfail}/{nb} bins FIT-NOT-OK")

    # (c) correctionlib output
    c = s["c_correctionlib"]
    for name, r in c.items():
        if name == "end_to_end_mediumid":
            continue
        ok = (r.get("loads") and r["correction_validate_exit"] == 0 and r["max_abs_nominal_minus_json"] < 1e-9
              and r["max_abs_up_minus_sf_plus_total"] < 1e-9 and r["max_abs_down_minus_sf_minus_total"] < 1e-9
              and r["max_abs_quadrature_or_eff_mismatch"] < 1e-9 and all(r["clamp"].values()))
        check(f"c {name} correctionlib", bool(ok),
              f"loads, validate exit {r.get('correction_validate_exit')}, max |expected - file| {r.get('max_abs_nominal_minus_json', 'n/a'):.1e} "
              f"over {r.get('n_grid_bins')} bins ({r.get('n_filled')} filled), clamp {all(r.get('clamp', {}).values())}")
        check(f"c {name} down >= 0, systup/systdown aliases, filled bins listed, syst on",
              r["min_down"] >= 0 and r["systup_systdown_aliases_ok"] and r["description_lists_filled"] and r["syst_on"],
              f"min down {r['min_down']:.4f}, aliases {r['systup_systdown_aliases_ok']}, listed {r['description_lists_filled']}, syst {r['syst_on']}")
        for f_ in r["filled"]:
            if f_["reason"] != "unmeasured":
                info(f"c {name} filled bin ({f_['ieta']},{f_['ipt']})",
                     f"{f_['reason']}: raw SF {f_['raw_sf']:.4f} -> {f_['filled_sf']:.4f} +- fill {f_['fill_sf']:.4f}")
    e2e = c.get("end_to_end_mediumid", {})
    check("c end-to-end weights", e2e.get("n_muons", 0) > 0 and 0.9 < e2e.get("mean_sf", 0) < 1.1,
          f"{e2e.get('n_muons')} MC muons, mean SF {e2e.get('mean_sf', float('nan')):.4f}, up {e2e.get('mean_sf_up', float('nan')):.4f}")

    # (d) MC-statistics coverage: halves of the MC against each other, scaling with N_MC
    d = s["d_mc_stat_coverage"]
    comb = d["combined"]
    check("d coverage: RMS of (SF_A - SF_B)/mc_stat in [0.75, 1.3]", 0.75 <= comb["rms_z"] <= 1.3,
          f"RMS {comb['rms_z']:.2f} +- {comb['rms_z_err_approx']:.2f} over {comb['n_bins']} bins; "
          f"with the MC counting error only: {comb['rms_z_counting_only']:.2f}")
    check("d coverage: |mean z| < 0.5", abs(comb["mean_z"]) < 0.5, f"mean {comb['mean_z']:+.2f}")
    for wp, r in d.items():
        if wp == "combined":
            continue
        okA = abs(r["median_mc_stat_ratio_halfA_over_full"] / r["median_expected_sqrt_nfull_over_nA"] - 1) < 0.25
        okB = abs(r["median_mc_stat_ratio_halfB_over_full"] / r["median_expected_sqrt_nfull_over_nB"] - 1) < 0.25
        check(f"d {wp} mc_stat ~ 1/sqrt(N_MC)", okA and okB,
              f"half/full {r['median_mc_stat_ratio_halfA_over_full']:.2f} (expected {r['median_expected_sqrt_nfull_over_nA']:.2f}), "
              f"{r['median_mc_stat_ratio_halfB_over_full']:.2f} (expected {r['median_expected_sqrt_nfull_over_nB']:.2f})")
        info(f"d {wp} finite-MC bias", f"mean (SF_A + SF_B)/2 - SF_full {r['mean_sf_halves_minus_full']:+.4f} +- {r['mean_sf_halves_minus_full_sem']:.4f}")

    # (d2) data-statistics coverage: two halves of the data, same MC
    d2 = s["d2_data_stat_coverage"]["combined"]
    check("d2 data-stat coverage: RMS of (SF_1 - SF_2)/stat in [0.6, 1.3]", 0.6 <= d2["rms_z"] <= 1.3,
          f"RMS {d2['rms_z']:.2f} +- {d2['rms_z_err_approx']:.2f} over {d2['n_bins']} bins, mean {d2['mean_z']:+.2f}, |z| > 3: {d2['n_abs_z_gt3']}")

    # (R5) golden JSON: the SFs barely move
    for wp, r in s["lumi_mask"].items():
        check(f"lumi mask {wp}: |dSF| at 30-60 GeV < 0.002", 0.9 < r["frac_events_in_mask"] <= 1 and r["max_abs_dsf_30_60"] < 0.002,
              f"{100 * r['frac_events_in_mask']:.1f}% of events in the golden JSON; max |dSF| {r['max_abs_dsf_30_60']:.4f} (30-60 GeV), "
              f"{r['max_abs_dsf']:.4f} (all {r['n_bins']} reliable bins, at most {r['max_abs_dsf_over_stat']:.2f} x stat)")

    # (R2) IsoMu22 activity: switched on/off per lumi section in data, always on in MC
    iso = s["isomu22_activity"]
    g = [iso[k]["p_isomu22_given_isomu24"] for k in ("G1", "G2")]
    h = [iso[k]["p_isomu22_given_isomu24"] for k in ("H2", "H4")]
    m = [iso[k]["p_isomu22_given_isomu24_or_isotkmu24"] for k in ("mc2", "mc3")]
    btw = max(iso[k]["frac_ls_between"] for k in ("G1", "G2", "H2", "H4"))
    check("R2 IsoMu22 fraction of IsoMu24 events", all(0.55 < x < 0.70 for x in g) and all(0.40 < x < 0.55 for x in h) and all(x > 0.98 for x in m),
          f"G {min(g):.3f}-{max(g):.3f}, H {min(h):.3f}-{max(h):.3f}, MC (IsoMu24 or IsoTkMu24) {min(m):.3f}-{max(m):.3f}")
    check("R2 IsoMu22 is on or off per lumi section", btw < 0.05, f"largest fraction of LS with 5-95% IsoMu22 in IsoMu24 events: {btw:.3f}")

    # (R3) --syst on by default with --correctionlib, warning without systematics
    sd = s["syst_default"]
    check("R3 syst default", sd["mvamedium"]["syst"] and sd["isomu22"]["syst"] and not sd["halfA_tightid"]["syst"]
          and sd["halfA_tightid"]["warns_no_syst"] and not sd["mediumid"]["warns_no_syst"],
          ", ".join(f"{k}: correctionlib {v['correctionlib']} syst {v['syst']} warning {v['warns_no_syst']}" for k, v in sd.items()))

    # (e) offline mode and exit codes
    e = s["e_offline_and_exit_codes"]
    for name in ("offline_flags", "offline_badpath"):
        r = e[name]
        check(f"e {name}", r["exit"] in (0, 1) and r["pog_available"] is False and r["pileup_weights"] is False
              and r["n_bins"] >= 20 and r["stdout_POG"] == "unavailable" and r["stdout_PILEUP"] == "off",
              f"exit {r['exit']}, {r['n_bins']} bins, warnings: {r['warnings'][:2]}")
    check("e --dry-run exit 0", e["dryrun"]["exit"] == 0, "")
    for name in ("bad_precedence", "bad_intbool", "bad_call", "bad_dryrun_intbool", "bad_den_only", "bad_recursion",
                 "bad_trigger_zero", "bad_trigger_mixed", "bad_trigger_dr"):
        check(f"e {name} exit 2", e[name]["exit"] == 2, (e[name]["message"] or "")[:120])

    # (f) systematics: every component present, median at 30-60 GeV below 0.5 percent
    for name, r in s["f_systematics"].items():
        comps = r["components_30_60"]
        check(f"f {name} syst components", set(comps) == {"bkg", "window", "tag"} and all(v["median"] < 0.005 for v in comps.values()),
              ", ".join(f"{k} median {v['median']:.4f} max {v['max']:.4f}" for k, v in comps.items()))

    # plots and personal paths
    need = ["mc_stat_coverage", "sf_over_pog_mediumid", "sf_over_pog_looseid", "unc_components_wp_tightid", "eff_isomu22"]
    missing = [p for p in need if not os.path.exists(os.path.join(base, "plots", p + ".png"))]
    check("plots present", not missing, f"missing: {missing or 'none'}")
    pat = re.compile(r"/uscms(_data)?/|/afs/|/eos/user/|/home/[a-z]|/nobackup/")
    hits = []
    for root, _, files in os.walk(base):
        for fn in files:
            if fn.endswith((".md", ".py", ".sh", ".txt", ".json")) and fn != "check_results.py":
                p = os.path.join(root, fn)
                with open(p, errors="replace") as fh:
                    if pat.search(fh.read()):
                        hits.append(os.path.relpath(p, base))
    check("no personal paths", not hits, f"files: {hits or 'none'}")

    n_pass = sum(r[0] == "PASS" for r in results)
    n = sum(r[0] != "INFO" for r in results)
    for st, name, detail in results:
        print(f"{st} {name}: {detail}")
    print(f"SUMMARY={n_pass}/{n}")
    return 0 if n_pass == n else 1


if __name__ == "__main__":
    sys.exit(main())
