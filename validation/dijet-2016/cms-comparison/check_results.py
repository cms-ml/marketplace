#!/usr/bin/env python3
"""Checks on the cms-results-validator outputs (comparison.json, COMPARISON.md, plots).

The comparison itself needs HEPData downloads and the student skims, so CI
cannot rerun it. These checks make sure the committed review is complete and
internally consistent: every test has a counterpart, a number and a verdict
from the allowed set, appears in COMPARISON.md, and the headline results
still hold. Plots are not committed; they are checked only when present. Standard library only.

Usage:
    check_results.py [validation/dijet-2016/cms-comparison]

Stdout: one "PASS|FAIL <check>: <detail>" line per check, then SUMMARY=<n_pass>/<n>.
Exit codes: 0 all pass, 1 some check failed, 2 comparison.json missing or unreadable.
"""
from __future__ import annotations

import json
import math
import os
import re
import sys

VERDICTS = {"CONSISTENT", "TENSION", "INCONSISTENT", "NOT COMPARABLE"}
PERSONAL = re.compile(r"/uscms_data|/uscms/home|/uscms/homes|nobackup/|/tmp/claude")

results: list[tuple[bool, str, str]] = []


def check(name: str, ok: bool, detail: str) -> None:
    results.append((bool(ok), name, detail))


def finite(x) -> bool:
    return isinstance(x, (int, float)) and math.isfinite(x)


def main() -> int:
    base = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    try:
        with open(os.path.join(base, "comparison.json")) as f:
            tests = json.load(f)["tests"]
    except (OSError, json.JSONDecodeError, KeyError) as e:
        print(f"error: cannot read comparison.json in {base}: {e}", file=sys.stderr)
        return 2
    by_id = {t["id"]: t for t in tests}

    # --- every test is complete
    check("test count", len(tests) >= 15, f"{len(tests)} tests")
    bad = [t["id"] for t in tests if t.get("verdict") not in VERDICTS]
    check("verdicts allowed", not bad, f"verdicts outside {sorted(VERDICTS)}: {bad or 'none'}")
    bad = [t["id"] for t in tests if not t.get("counterpart") or not t.get("reason")]
    check("counterpart and reason", not bad, f"tests missing counterpart/reason: {bad or 'none'}")
    bad = [t["id"] for t in tests
           if t["verdict"] != "NOT COMPARABLE" and not (finite(t.get("statistic")) or finite(t.get("ratio")))]
    check("number behind verdict", not bad, f"tests with a verdict but no finite statistic/ratio: {bad or 'none'}")

    # --- COMPARISON.md covers every test
    try:
        md = open(os.path.join(base, "COMPARISON.md")).read()
    except OSError:
        md = ""
    missing = [i for i in by_id if i.replace("_", "-") not in md and i not in md]
    check("COMPARISON.md lists all tests", md and not missing, f"missing: {missing or 'none'}")
    check("Open Data labelled", "Open Data" in md and "not CMS results" in md,
          "COMPARISON.md says the student results are Open Data, not CMS results")

    # --- headline results (regressions would change these)
    t = by_id.get("D1a", {})
    check("D1a WPs exact", t.get("verdict") == "CONSISTENT", f"D1a {t.get('verdict')}")
    t = by_id.get("D2a", {})
    check("D2a 2b shape", t.get("verdict") == "CONSISTENT" and (t.get("p_value") or 0) > 0.05,
          f"D2a {t.get('verdict')}, p = {t.get('p_value')}")
    t = by_id.get("D3a", {})
    r = t.get("ratio")
    check("D3a 2b dsigma/dm ratio", finite(r) and 0.85 < r < 1.15, f"student/CMS = {r}")
    for i in ("M2a", "M2b"):
        t = by_id.get(i, {})
        r = t.get("ratio")
        check(f"{i} Upsilon ratio", finite(r) and 0.8 < r < 1.2, f"student/CMS = {r}, {t.get('verdict')}")

    # --- plots and hygiene
    pdir = os.path.join(base, "plots")
    files = os.listdir(pdir) if os.path.isdir(pdir) else []
    pngs = {f[:-4] for f in files if f.endswith(".png")}
    pdfs = {f[:-4] for f in files if f.endswith(".pdf")}
    # plots are not committed (run_all.sh rebuilds them); check them only when present
    check("plots PNG + PDF", pngs == pdfs,
          f"{len(pngs)} plots; unpaired: {sorted(pngs ^ pdfs) or 'none'}" if files else "not committed (run_all.sh rebuilds them)")
    leaks = []
    for root, _, names in os.walk(base):
        for n in names:
            if n.endswith((".py", ".md", ".json", ".sh")) and n != os.path.basename(__file__):
                with open(os.path.join(root, n), errors="replace") as f:
                    if PERSONAL.search(f.read()):
                        leaks.append(os.path.relpath(os.path.join(root, n), base))
    check("no personal paths", not leaks, f"files with user paths: {leaks or 'none'}")

    n_pass = sum(ok for ok, _, _ in results)
    for ok, name, detail in results:
        print(f"{'PASS' if ok else 'FAIL'} {name}: {detail}")
    print(f"SUMMARY={n_pass}/{len(results)}")
    return 0 if n_pass == len(results) else 1


if __name__ == "__main__":
    sys.exit(main())
