#!/usr/bin/env python3
"""Physics-sense checks on the ABCD validation (Open Data, with and without the abcd skill) and on the
validator's comparison with CMS EXO-17-021.

Reads ws_skill/ and ws_noskill/ (results.json, fits/prediction.json, plots/) and cms-comparison/comparison.json
(stdlib only).

Usage:  check_results.py [validation/abcd]
Stdout: one "PASS|FAIL|INFO <check>: <detail>" line per check, then SUMMARY=<n_pass>/<n_checks> (INFO lines are not counted).
Exit codes: 0 all checks pass, 1 some check failed, 2 an input file is missing or unreadable.
"""

import json
import math
import os
import re
import sys

VERDICTS = {"CONSISTENT", "TENSION", "INCONSISTENT", "NOT COMPARABLE"}
RUNS = {"with skill": "ws_skill", "without skill": "ws_noskill"}
PERSONAL = re.compile("|".join(["/us" + "cms_data", "/us" + "cms/ho" + "me", "no" + "backup", "/tm" + "p/cl" + "aude", "ash" + "rivas"]))
SKIP_DIRS = {"inputs", "slim", "compact", "nt", "red", "sel", "tmp", "cache", "skimcache", "out", "__pycache__", "condor"}
TEXT_EXT = (".md", ".py", ".sh", ".json", ".txt", ".csv", ".jdl")

results = []


def check(name, ok, detail):
    results.append((bool(ok), name, detail))


def info(name, detail):
    print(f"INFO {name}: {detail}")


def fin(x):
    return isinstance(x, (int, float)) and math.isfinite(x)


def first(d, *keys):
    for k in keys:
        if k in d:
            return d[k]
    raise KeyError(keys)


def main():
    base = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    try:
        res = {r: json.load(open(os.path.join(base, ws, "results.json"))) for r, ws in RUNS.items()}
        pred = {r: json.load(open(os.path.join(base, ws, "fits", "prediction.json"))) for r, ws in RUNS.items()}
        cmp_ = json.load(open(os.path.join(base, "cms-comparison", "comparison.json")))
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: cannot read inputs in {base}: {e}", file=sys.stderr)
        return 2

    required = ["trigger", "preselection", "abcd_variables", "regions", "mavg_bins", "independence", "tf", "prediction",
                "closure_mc", "validation_regions", "non_closure_syst", "unblinded", "n_events", "checks_done"]
    for r, ws in RUNS.items():
        R, P = res[r], pred[r]
        missing = [k for k in required if k not in R]
        check(f"{r}: results.json complete", not missing, f"missing keys: {missing or 'none'}")

        edges = P["edges"]
        B, C, D = P["data_B"], P["data_C"], P["data_D"]
        qcd = first(P, "predicted_QCD_A", "pred_qcd_A")
        obs = first(P, "observed_A", "data_A_observed")
        n = len(edges) - 1
        arrays = {"B": B, "C": C, "D": D, "pred": qcd, "obs": obs}
        bad = [k for k, a in arrays.items() if len(a) != n or not all(fin(x) and x >= 0 for x in a)]
        check(f"{r}: per-bin arrays finite, non-negative, {n} bins", not bad and all(b > a for a, b in zip(edges, edges[1:])),
              f"bad arrays: {bad or 'none'}; edges increasing")

        incl = sum(B) * sum(C) / sum(D)
        ref = cmp_["runs"][r]["2_method_validity"]["numbers"]["incl_raw_BC_over_D"]
        check(f"{r}: inclusive B*C/D recomputed", abs(incl / ref - 1) < 1e-6, f"{incl:.1f} vs validator {ref:.1f}")

        other = first(P, "other_bkg_yield_A", "other_bkg_A")
        tot_pred, tot_obs = sum(qcd) + sum(other), sum(obs)
        check(f"{r}: observed total in A matches the prediction within 5%", abs(tot_obs / tot_pred - 1) < 0.05,
              f"obs {tot_obs:.0f} / pred {tot_pred:.0f} = {tot_obs / tot_pred:.3f}")

        cl = R["closure_mc"]["ratio"]
        check(f"{r}: MC closure inside the CMS +-10% band", fin(cl) and abs(cl - 1) < 0.10, f"ratio {cl:.3f}")

        u = cmp_["runs"][r]["3_pred_vs_obs"]["numbers"]
        check(f"{r}: no local excess in the unblinded signal region (< 3 sigma)", u["max_local_sigma"] < 3,
              f"max local {u['max_local_sigma']:.2f} sigma, chi2 {u['student_chi2']:.1f}/{u['ndf']}")
        if u["p"] > 0.99:
            info(f"{r}: over-coverage", f"unblinded chi2 p = {u['p']:.4f}: the systematics over-cover")

        plots = os.path.join(base, ws, "plots")
        n_png = len([f for f in os.listdir(plots) if f.endswith(".png")]) if os.path.isdir(plots) else 0
        check(f"{r}: plots present", n_png >= 5, f"{n_png} PNG files in {ws}/plots")

    for r in RUNS:
        bad = [k for k, v in cmp_["runs"][r].items() if isinstance(v, dict) and "verdict" in v
               and not any(v["verdict"].startswith(x) or x in v["verdict"] for x in VERDICTS)]
        check(f"{r}: comparison verdicts are valid labels", not bad, f"bad: {bad or 'none'}")

    names = " ".join(v["name"].lower() for v in res["with skill"]["abcd_variables"])
    check("with skill: ABCD axes are mass asymmetry and |delta eta| (the EXO-17-021 pair)",
          ("asym" in names) and ("eta" in names), f"axes: {names}")

    s_with = cmp_["runs"]["with skill"]["4_shape_vs_cms"]["numbers"]
    s_wo = cmp_["runs"]["without skill"]["4_shape_vs_cms"]["numbers"]
    check("shape vs CMS: with skill closer than without skill", s_with["chi2"] / s_with["ndf"] < s_wo["chi2"] / s_wo["ndf"],
          f"chi2/ndf {s_with['chi2']:.1f}/{s_with['ndf']} vs {s_wo['chi2']:.1f}/{s_wo['ndf']}")
    emu = s_with["emulation_vs_cms_p"]
    check("CMS-like selection on Open Data reproduces the CMS shape (p > 0.05)", emu > 0.05,
          f"p = {emu:.3f}, chi2 {s_with['emulation_vs_cms_chi2']:.1f}")
    lvl = cmp_["runs"]["with skill"]["5_level_and_closure_vs_cms"]["numbers"]["emulation_over_cms"]
    info("unexplained level factor", f"CMS-like Open Data / CMS = {lvl:.2f} (PUPPI vs CHS, soft-drop vs pruned)")

    check("comparison labelled CMS Open Data, not a CMS result",
          "Open Data" in cmp_["disclaimer"] and "not CMS results" in cmp_["disclaimer"], cmp_["disclaimer"][:60] + "...")

    hits = []
    for root, dirs, files in os.walk(base):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            if f.endswith(TEXT_EXT) and not f.endswith(".jsonl"):
                p = os.path.join(root, f)
                try:
                    if PERSONAL.search(open(p, errors="ignore").read()):
                        hits.append(os.path.relpath(p, base))
                except OSError:
                    pass
    check("no personal paths in committed text files", not hits, f"files: {hits[:5] or 'none'}")

    for ok, name, detail in results:
        print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}")
    n_pass = sum(ok for ok, _, _ in results)
    print(f"SUMMARY={n_pass}/{len(results)}")
    return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
