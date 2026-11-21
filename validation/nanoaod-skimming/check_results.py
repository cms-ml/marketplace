#!/usr/bin/env python3
"""Sanity checks on the nanoaod-skimming validation outputs.

Reads summary.json (and plots/ next to it) and checks that the skim kept its
bookkeeping: event counts are conserved through merging, the MC sum of
weights in the skim equals the original NanoAOD, the luminosity is
consistent, the normalised DY Z peak agrees with data, and the cutflow
(skim steps from the skims' Cutflow trees, then the analysis steps with
N-1) is consistent with all of these. Standard library
only, so CI can run it. It does not rerun the skim.

Usage:
    check_results.py [validation/nanoaod-skimming]

Stdout: one "PASS|FAIL <check>: <detail>" line per check, then SUMMARY=<n_pass>/<n>.
Exit codes: 0 all pass, 1 some check failed, 2 summary.json missing or unreadable.
"""
from __future__ import annotations

import json
import math
import os
import sys

results: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str) -> None:
    results.append((bool(ok), name, detail))


def rel(a: float, b: float) -> float:
    return abs(a - b) / max(abs(b), 1e-300)


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(base, "summary.json")) as f:
            s = json.load(f)
        d, m, z = s["data"], s["mc"], s["z_peak"]
    except (OSError, json.JSONDecodeError, KeyError) as e:
        print(f"error: cannot read summary.json in {base}: {e}", file=sys.stderr)
        return 2

    # --- event bookkeeping
    check("data files", d["n_files"] == 3, f"{d['n_files']} SingleMuon files (3 expected)")
    check("mc files", m["n_files"] == 3, f"{m['n_files']} DY files (3 expected)")
    check("data counts ordered", d["events_out"] <= d["events_after_lumimask"] <= d["events_in"],
          f"{d['events_out']} <= {d['events_after_lumimask']} <= {d['events_in']}")
    check("mc counts ordered", 0 < m["events_out"] <= m["events_in"], f"0 < {m['events_out']} <= {m['events_in']}")
    check("data merge conserves events", d["merged_entries"] == d["events_out"],
          f"hadd output {d['merged_entries']} vs sum of skims {d['events_out']}")
    check("mc merge conserves events", m["merged_entries"] == m["events_out"],
          f"hadd output {m['merged_entries']} vs sum of skims {m['events_out']}")
    for k, v in (("data", d), ("mc", m)):
        r = v["skim_bytes"] / v["input_bytes"] if v["input_bytes"] else math.inf
        check(f"{k} size reduction", 0 < r < 0.1, f"skim/input = {r:.4f} (< 0.1)")

    # --- MC normalisation
    check("sumw survives skim+merge", rel(m["sumw_runs_merged_skim"], m["sumw_runs_original"]) < 1e-6,
          f"{m['sumw_runs_merged_skim']:.6g} vs original {m['sumw_runs_original']:.6g}")
    check("sumw read == Runs (full files)", rel(m["sumw_read"], m["sumw_runs_original"]) < 1e-4,
          f"sum genWeight {m['sumw_read']:.6g} vs Runs {m['sumw_runs_original']:.6g}")
    f = m["neg_weight_fraction"]
    check("negative-weight fraction", 0.10 < f < 0.22, f"{f:.3f} (about 0.16 for amcatnlo DY)")
    wf = m["xsec_pb"] * d["lumi_pb"] / m["sumw_runs_original"]
    check("weight factor", rel(m["weight_factor"], wf) < 1e-3, f"{m['weight_factor']:.6g} vs xsec*lumi/sumw {wf:.6g}")

    # --- luminosity
    g = s["golden_2016_lumi_fb"]
    check("2016 golden luminosity", 36.0 < g < 36.6, f"{g:.3f} /fb (CMS 2016 UL: 36.31)")
    per_ls = d["lumi_pb"] / d["n_ls"] if d["n_ls"] else 0
    check("lumi per lumi section", 0.02 < per_ls < 0.4, f"{per_ls:.3f} /pb per LS")
    check("data lumi below a year", 0 < d["lumi_pb"] < 0.05 * g * 1000, f"{d['lumi_pb']:.1f} /pb from 3 files")

    # --- physics: Z peak
    r, unc = z["data_over_mc"], z["mc_stat_unc"]
    check("Z peak ratio consistent", rel(r, z["data_events"] / z["mc_events_normalised"]) < 1e-3,
          f"{r:.4f} vs {z['data_events']}/{z['mc_events_normalised']:.1f}")
    check("Z peak data/MC", 0.8 < r < 1.2, f"{r:.3f} in [0.8, 1.2] (no SFs or pileup weights)")
    check("MC stat unc sensible", 0 < unc < 0.1 * z["mc_events_normalised"],
          f"{unc:.1f} on {z['mc_events_normalised']:.1f}")

    # --- cutflow (skim Cutflow trees + analysis steps)
    c = s.get("cutflow")
    check("cutflow present", isinstance(c, dict), "summary.json has a cutflow block")
    if isinstance(c, dict):
        steps = c["steps"]
        cd, cm = c["data"], c["mc_normalised"]
        ok_len = all(len(x) == len(steps) for x in (cd["sequential"], cd["nminus1"], cm["sequential"], cm["nminus1"]))
        check("cutflow lists match steps", ok_len, f"{len(steps)} steps")
        if ok_len:
            i = {k: n for n, k in enumerate(steps)}
            seq_d, seq_m, nm1_d, nm1_m = cd["sequential"], cm["sequential"], cd["nminus1"], cm["nminus1"]
            check("cutflow skim rows = skim counts",
                  seq_d[i["all"]] == d["events_in"] and seq_d[i["lumimask"]] == d["events_after_lumimask"]
                  and seq_d[i[c["skim_steps"][-1]]] == d["events_out"],
                  f"all {seq_d[i['all']]}, lumimask {seq_d[i['lumimask']]}, last skim step {seq_d[i[c['skim_steps'][-1]]]}")
            check("cutflow per-file == merged", c["skim_per_file_equals_merged"] is True,
                  "Cutflow trees of the per-file and merged skims agree")
            check("data cutflow non-increasing", all(a >= b for a, b in zip(seq_d, seq_d[1:])), "sequential counts")
            check("mc cutflow non-increasing", all(a >= b * (1 - 1e-9) for a, b in zip(seq_m, seq_m[1:])), "normalised")
            check("cutflow ends at Z peak", seq_d[-1] == z["data_events"] and rel(seq_m[-1], z["mc_events_normalised"]) < 1e-6,
                  f"data {seq_d[-1]} vs {z['data_events']}, MC {seq_m[-1]:.1f} vs {z['mc_events_normalised']:.1f}")
            xl = m["xsec_pb"] * d["lumi_pb"]
            check("mc all row = xsec * lumi", rel(seq_m[i["all"]], xl) < 1e-4,
                  f"{seq_m[i['all']]:.1f} vs {xl:.1f} (complete files: sum genWeight read = genEventSumw)")
            cuts = [k for k in steps if k not in ("all", "lumimask")]
            check("N-1 >= final", all(nm1_d[i[k]] >= seq_d[-1] and nm1_m[i[k]] >= seq_m[-1] * (1 - 1e-9) for k in cuts),
                  "every N-1 count is at least the final count (data and MC)")
            check("N-1 of last step = previous row", nm1_d[-1] == seq_d[-2] and rel(nm1_m[-1], seq_m[-2]) < 1e-9,
                  f"data {nm1_d[-1]} vs {seq_d[-2]}")
            r_tight = seq_d[-1] / seq_m[-1]
            check("data/MC after full selection", rel(r_tight, z["data_over_mc"]) < 1e-6, f"{r_tight:.4f}")

    for name in ("mmumu", "cutflow"):
        for ext in ("png", "pdf"):
            p = os.path.join(base, "plots", f"{name}.{ext}")
            check(f"plot {name}.{ext}", os.path.isfile(p) and os.path.getsize(p) > 1000, p)

    for ok, name, detail in results:
        print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}")
    n_pass = sum(ok for ok, _, _ in results)
    print(f"SUMMARY={n_pass}/{len(results)}")
    return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
