#!/usr/bin/env python3
"""Physics sanity checks on the dijet-2016 validation outputs.

Reads summary.json (and the hepdata/ and plots/ directories next to it) and
checks that the numbers an agent produced are physically sensible and
internally consistent. It does not rerun the analysis. Standard library only,
so CI can run it.

Usage:
    check_results.py [validation/dijet-2016]

Stdout: one "PASS|FAIL <check>: <detail>" line per check, then SUMMARY=<n_pass>/<n>.
Exit codes: 0 all pass, 1 some check failed, 2 summary.json missing or unreadable.
"""
from __future__ import annotations

import json
import math
import os
import sys

# Official DeepJet 2016postVFP_UL working points (BTV POG JSON, deepJet_wp_values)
DEEPJET_WP = {"L": 0.0480, "M": 0.2489, "T": 0.6377}

results: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str) -> None:
    results.append((bool(ok), name, detail))


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(base, "summary.json")) as f:
            s = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        print(f"error: cannot read summary.json in {base}: {e}", file=sys.stderr)
        return 2

    # --- inputs and luminosity
    nfiles = s["inputs"]["data"]["n_files"]
    check("data files", nfiles == 142, f"{nfiles} JetHT files (70 Run2016G + 72 Run2016H expected)")
    lumi = s["luminosity"]["recorded_fb"]
    check("luminosity", 15.0 < lumi < 18.0, f"{lumi:.2f} fb^-1 (2016G+H golden is about 16.4)")

    # --- trigger
    t = s["trigger"]
    check("trigger plateau", t["plateau_efficiency"] >= 0.99, f"{t['plateau_efficiency']:.5f} >= 0.99")
    check("trigger threshold", 900 <= t["threshold_mjj_GeV"] <= 1500,
          f"{t['threshold_mjj_GeV']:.0f} GeV in [900, 1500]")
    for ref, cc in t.get("crosschecks", {}).items():
        d = abs(cc["plateau_efficiency_above_threshold"] - t["plateau_efficiency"])
        check(f"trigger cross-check {ref}", d < 0.002, f"plateau differs by {d:.5f} (< 0.002)")
    num, den = t["efficiency_vs_mjj"]["num"], t["efficiency_vs_mjj"]["den"]
    check("trigger num <= den", all(n <= d for n, d in zip(num, den)), "numerator is a subset of the denominator")

    # --- b tagging
    wp = s["btag_wp_deepjet_2016postVFP_UL"]
    check("DeepJet WPs", all(abs(wp[k] - v) < 1e-4 for k, v in DEEPJET_WP.items()),
          f"{wp} == official {DEEPJET_WP}")
    order = all(r["eff_L"] > r["eff_M"] > r["eff_T"] for r in s["btag_efficiency"])
    check("b-tag efficiency order", order, "eff(L) > eff(M) > eff(T) at every Z' mass")
    effs = [r[f"eff_{k}"] for r in s["btag_efficiency"] for k in "LMT"]
    check("b-tag efficiency range", all(0.0 <= e <= 1.0 for e in effs), "all in [0, 1]")

    # --- event counts
    ev = s["events_data_full_selection"]
    check("category ordering", ev["incl"] > ev["1b"] > ev["2b"] > 0,
          f"incl {ev['incl']} > 1b {ev['1b']} > 2b {ev['2b']} > 0")
    frac = ev["2b"] / ev["1b"]
    check("2b/1b fraction", 0.02 < frac < 0.3, f"{frac:.3f} in (0.02, 0.3)")

    # --- background fits
    for cat in ("1b", "2b"):
        fit = s["fit"][cat]
        n = str(fit["chosen_nparams"])
        chosen = fit["fits"][n]
        check(f"fit {cat} converged", chosen["valid"], f"{n}-parameter fit valid (EDM {chosen['edm']:.1e})")
        check(f"fit {cat} chi2/ndf", 0.5 < fit["chi2_ndf_chosen"] < 2.0,
              f"{fit['chi2_ndf_chosen']:.3f} in (0.5, 2.0)")
        check(f"fit {cat} nparams", fit["chosen_nparams"] in (3, 4, 5), f"F-test chose {n}")
        pulls = [p for p in fit["pulls"] if p is not None and math.isfinite(p)]
        big = sum(abs(p) > 4 for p in pulls)
        check(f"fit {cat} pulls", big == 0, f"{big} of {len(pulls)} bins with |pull| > 4")

    # --- signal injection closure
    for cat in ("1b", "2b"):
        toys = s["injection"][cat]["toys"]
        rel = toys["bias_mean_rec_minus_inj"] / toys["S_true_mean"]
        check(f"injection {cat} bias", abs(rel) < 0.10, f"mean (rec - inj)/inj = {rel:+.3f} (|.| < 0.10)")
        check(f"injection {cat} pull mean", abs(toys["pull_mean"]) < 0.3, f"{toys['pull_mean']:+.3f} (|.| < 0.3)")
        check(f"injection {cat} pull width", 0.7 < toys["pull_std"] < 1.4, f"{toys['pull_std']:.3f} in (0.7, 1.4)")

    # --- deliverables
    missing = [p for p in s.get("plots", []) if not os.path.isfile(os.path.join(base, p))]
    check("plots exist", not missing and s.get("plots"), f"{len(s.get('plots', []))} listed, missing: {missing or 'none'}")
    hd = os.path.join(base, "hepdata", "submission.yaml")
    check("hepdata record", os.path.isfile(hd), "hepdata/submission.yaml present")
    nan_files = []
    for fn in sorted(os.listdir(os.path.join(base, "hepdata"))) if os.path.isdir(os.path.join(base, "hepdata")) else []:
        if fn.endswith(".yaml"):
            with open(os.path.join(base, "hepdata", fn)) as f:
                if ".nan" in f.read().lower():
                    nan_files.append(fn)
    check("hepdata no NaN", not nan_files, f"files with .nan: {nan_files or 'none'}")

    n_pass = sum(ok for ok, _, _ in results)
    for ok, name, detail in results:
        print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}")
    print(f"SUMMARY={n_pass}/{len(results)}")
    return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
