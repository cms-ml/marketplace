#!/usr/bin/env python3
"""Assemble comparison.json and the verdict table (results/summary_table.md) from results/*.json written by the compare_*.py scripts."""
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
RES = HERE / "results"
ORDER = ["D1a", "D1b", "D2a", "D2b", "D2b_alt", "D2c", "D3a", "D3b", "D3b_alt", "D3c", "D4a", "D4b", "D4c", "D5", "D5b", "M1", "M2a", "M2b", "M3a", "M3b", "M4"]
AUX = ["D1c_context", "D3_lumi_check", "D4d_per_jet", "D5c_diag", "M4b_table3"]
KEYS = ["id", "student_result", "counterpart", "level", "statistic", "statistic_name", "ndf", "p_value", "ratio", "verdict", "reason"]


def load(i):
    return json.load(open(RES / f"{i}.json"))


def fmt(r):
    p = r.get("p_value")
    if r.get("ratio") is not None and p is None:
        return f"ratio {r['ratio']:.3f}"
    if p is not None:
        return f"chi2/ndf {r['statistic']:.1f}/{r['ndf']}, p={p:.2g}"
    if r.get("statistic") is not None:
        return f"{r.get('statistic_name', 'stat')}: {r['statistic']:.3g}"
    return ""


tests = []
for i in ORDER:
    if (RES / f"{i}.json").exists():
        r = load(i)
        tests.append({k: r.get(k) for k in KEYS} | {"details": {k: v for k, v in r.items() if k not in KEYS}})
aux = [load(i) for i in AUX if (RES / f"{i}.json").exists()]
out = {"description": "Comparison of two Open Data student analyses with published CMS results; verdicts CONSISTENT / TENSION / INCONSISTENT / NOT COMPARABLE",
       "tests": tests, "auxiliary": aux}
json.dump(out, open(HERE / "comparison.json", "w"), indent=1)
lines = ["| ID | Test | CMS counterpart | Number | Verdict |", "| --- | --- | --- | --- | --- |"]
for t in tests:
    c = t["counterpart"] or {}
    cp = f"{c.get('report', '')} / {c.get('hepdata_table') or c.get('source', '')}"
    lines.append(f"| {t['id']} | {t['student_result'][:70]} | {cp[:70]} | {fmt(t)} | {t['verdict']} |")
(RES / "summary_table.md").write_text("\n".join(lines) + "\n")
print("\n".join(lines))
