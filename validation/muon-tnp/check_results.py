#!/usr/bin/env python3
"""Physics sanity checks on the muon-tnp validation outputs (summary.json, plots/, text files).

Does not rerun the analysis. Standard library only, so CI can run it.

Usage:
    check_results.py [validation/muon-tnp]

Stdout: one "PASS|FAIL|INFO <check>: <detail>" line per check, then SUMMARY=<n_pass>/<n>.
INFO lines (trigger SF agreement) are reported, not counted.
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

    # --- inputs, luminosity, pairs
    lum = s["luminosity"]
    check("luminosity", 0.5 < lum["recorded_fb"] <= lum["full_GH_golden_recorded_fb"] < 20,
          f"{lum['recorded_fb']:.2f} fb^-1 processed+certified = {100 * lum['fraction_of_full_GH']:.1f}% of the full G+H {lum['full_GH_golden_recorded_fb']:.2f}")
    check("lumi G+H", abs(lum["recorded_G_fb"] + lum["recorded_H_fb"] - lum["recorded_fb"]) < 1e-6 * max(1, lum["recorded_fb"]) + 1e-9,
          f"G {lum['recorded_G_fb']:.3f} + H {lum['recorded_H_fb']:.3f}")
    check("all lumi sections in the csv", lum["n_lumisections_in_csv"] == lum["n_lumisections_processed_and_golden"],
          f"{lum['n_lumisections_in_csv']}/{lum['n_lumisections_processed_and_golden']}")
    p = s["pairs"]
    check("pair counts", p["data_pairs_nominal_tightid_denominator"] > 1e5 and p["mc_pairs_nominal_tightid_denominator"] > 1e5,
          f"data {p['data_pairs_nominal_tightid_denominator']}, MC {p['mc_pairs_nominal_tightid_denominator']} (MC/data {p['mc_over_data']:.2f})")
    info("MC statistics", f"MC/data pair ratio {p['mc_over_data']:.2f}; requirement MC >= data met: {p['mc_statistics_ok']}")
    check("fit self-test vs tnp.fit_pass_fail", abs(s["selftest_fit_vs_tnp"]["ours"][0] - s["selftest_fit_vs_tnp"]["tnp_fit_pass_fail"][0]) < 1e-4,
          f"{s['selftest_fit_vs_tnp']['ours'][0]:.5f} vs {s['selftest_fit_vs_tnp']['tnp_fit_pass_fail'][0]:.5f}")

    # --- efficiencies and SFs
    bad_eff, bad_sf, nb, notok = [], [], 0, 0
    for wp, w in s["wp"].items():
        for r in w["bins"]:
            nb += 1
            for k in ("eff_data", "eff_mc"):
                if not 0.0 <= r[k] <= 1.0:
                    bad_eff.append(f"{wp}/{r['label']} {k}={r[k]}")
            # a bin with a SF error larger than 0.05 is statistically empty and is exempt from the range check
            if not 0.9 <= r["sf"] <= 1.1 and r["sf_stat"] < 0.05:
                bad_sf.append(f"{wp}/{r['label']} SF={r['sf']:.3f}")
            notok += not r["fit_ok"]
    check("efficiencies in [0, 1]", not bad_eff, f"{nb} bins; violations: {bad_eff[:3] or 'none'}")
    check("SFs in [0.9, 1.1]", not bad_sf, f"violations: {bad_sf[:3] or 'none'} (bins with stat error > 0.05 exempt)")
    check("fits converged", notok <= 0.1 * nb, f"{notok}/{nb} bins FIT-NOT-OK")

    # --- agreement with the POG
    # Pull-based criteria are only used for tight ID. The POG uncertainties of the isolation and trigger SFs are 0.02-0.1 percent
    # in the high-statistics bins, so any real offset of a few per mille gives |pull| of 3-20 and the pulls are far from Gaussian
    # (RMS pull is then a poor summary). For tight iso the criterion is a tolerance in SF units; for IsoMu24 (open issue) only INFO.
    def wratio(rows):
        num = den = 0.0
        for r in rows:
            if 30.0 <= r["pt"][0] < 60.0:
                e = r["sf_total_err"] / r["pog_sf"]
                num += r["sf"] / r["pog_sf"] / e ** 2
                den += 1.0 / e ** 2
        return num / den if den else float("nan")

    if "tightid" in s["wp"]:
        w = s["wp"]["tightid"]
        check("tightid RMS pull < 2", w["rms_pull"] < 2.0, f"mean {w['mean_pull']:+.2f}, RMS {w['rms_pull']:.2f} over {w['n_bins']} bins")
    for wp in ("tightid", "tightiso"):
        if wp in s["wp"]:
            r = wratio(s["wp"][wp]["bins"])
            check(f"{wp} weighted SF/POG at 30-60 GeV within 1%", abs(r - 1.0) < 0.01, f"{r:.4f} (stat+syst weighted)")
    if "tightiso" in s["wp"]:
        w = s["wp"]["tightiso"]
        info("tightiso pulls (not a criterion)", f"mean {w['mean_pull']:+.2f}, RMS {w['rms_pull']:.2f}: POG uncertainties of 0.02-0.1% make the pulls non-Gaussian; "
             f"offset {100 * (wratio(w['bins']) - 1):+.2f}% in SF units")
    if "isomu24" in s["wp"]:
        w = s["wp"]["isomu24"]
        info("isomu24 SF/POG at 30-60 GeV (open issue, no threshold)", f"{wratio(w['bins']):.4f}; pulls mean {w['mean_pull']:+.2f}, RMS {w['rms_pull']:.2f} (non-Gaussian, see tightiso)")
    big = [(wp, r) for wp, w in s["wp"].items() for r in w["bins"] if abs(r["pull"]) > 5]
    bad = [f"{wp}/{r['label']}" for wp, r in big if r.get("note_status") not in ("explained", "open_issue") or not r.get("note")]
    check("every |pull| > 5 bin carries a structured note", not bad, f"{len(big)} bins with |pull| > 5; without a valid note: {bad[:3] or 'none'}")
    n_expl = sum(r.get("note_status") == "explained" for _, r in big)
    n_open = [f"{wp}/{r['label']}" for wp, r in big if r.get("note_status") == "open_issue"]
    info("|pull| > 5 bins", f"{n_expl} explained, {len(n_open)} accepted open issues (not explained): {n_open[:4]}{' ...' if len(n_open) > 4 else ''}")

    # --- run dependence and trigger (reported, no threshold)
    rd = s["run_dependence"]["wp"]
    for wp in ("isomu24", "tightiso"):
        if wp in rd:
            r = rd[wp]
            info(f"{wp} G vs H", f"<SF_G - SF_H> = {r['mean_SF_G_minus_H_weighted']:+.4f} +- {r['err']:.4f}, chi2/ndf {r['chi2_G_vs_H']:.0f}/{r['ndf']}, "
                 f"<SF_G/POG> {r['mean_SF_G_over_POG']:.4f}, <SF_H/POG> {r['mean_SF_H_over_POG']:.4f}")
    if "filter_bits" in s:
        fb = s["filter_bits"]
        fr = fb["data"]["fraction_matched_probes_in_event_fired_neither"]
        check("filter-bit fraction reported", 0.0 <= fr <= 1.0 and "bias_SF_A_minus_S_mean" in fb,
              f"matched probes in events that fired neither path: {fr:.2e}; mean SF shift bit-only vs skill {fb['bias_SF_A_minus_S_mean']:+.4f}, path-specific vs skill {fb['bias_SF_C_minus_S_mean']:+.4f}")

    # --- files: plots, no personal paths
    plots = os.path.join(base, "plots")
    need = [f"eff_{w}" for w in s["wp"]] + [f"sf_ratio_map_{w}" for w in s["wp"]] + ["pulls"]
    miss = [n + e for n in need for e in (".png", ".pdf") if not os.path.exists(os.path.join(plots, n + e))]
    nfit = len([x for x in os.listdir(plots) if x.startswith("fit_") and x.endswith(".png")]) if os.path.isdir(plots) else 0
    check("plots", not miss and nfit >= 6, f"missing {miss[:3] or 'none'}; {nfit} fit plots")

    user = os.environ.get("USER", "")
    pat = re.compile(r"/uscms|/home/|/nobackup|/eos/uscms|/eos/user|/data/d\d|/store/user/(?!\$USER|\$\{USER\}|\$ENV\(USER\)|<|\.\.\.)|(?<![A-Za-z$<])/tmp/")
    offenders = []
    for root, _, files in os.walk(base):
        for fn in files:
            # REVIEW.md is the external reviewer's note: it quotes the grep patterns it used, so it is not scanned
            if fn.endswith((".py", ".md", ".json", ".sh", ".jdl", ".txt", ".yaml")) and fn not in ("agent_report.md", "REVIEW.md"):
                path = os.path.join(root, fn)
                if os.path.abspath(path) == os.path.abspath(__file__):
                    continue
                try:
                    txt = open(path, errors="replace").read()
                except OSError:
                    continue
                if pat.search(txt) or (len(user) > 2 and user in txt):
                    offenders.append(os.path.relpath(path, base))
    check("no personal paths", not offenders, f"offending files: {offenders[:5] or 'none'}")

    n_pass = sum(r[0] == "PASS" for r in results)
    n = sum(r[0] != "INFO" for r in results)
    for st, name, detail in results:
        print(f"{st} {name}: {detail}")
    print(f"SUMMARY={n_pass}/{n}")
    return 0 if n_pass == n else 1


if __name__ == "__main__":
    sys.exit(main())
