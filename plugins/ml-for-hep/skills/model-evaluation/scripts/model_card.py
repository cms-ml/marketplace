#!/usr/bin/env python3
"""Gate and document a model: collect the check results and write MODEL_CARD.md.

    model_card.py --name zprime_bdt --out MODEL_CARD.md \
        --check table=checks.json --check training=runs/bdt0/metrics.json \
        --check evaluation=eval/evaluation.json --check sculpting=sculpt/sculpting.json \
        --check closure=closure/closure.json \
        [--field "Intended use=..."] [--waive sculpting="score is the fit variable's complement, see note"]

Every --check file is a JSON written by a script of this plugin: it has a "summary" dict with a
STATUS key (PASS/FAIL). A model is READY only if every name in --require (default:
table,training,evaluation,sculpting,closure) is present and PASS. --waive NAME=REASON accepts
a missing or failed check with a written reason: the card then says WAIVED and READY=0 becomes
READY=1 only if all remaining checks pass; waivers are listed at the top of the card.
--field "Key=text" adds free-text rows (task, labels, samples, intended use, limitations).

Stdout KEY=VALUE: N_CHECKS N_PASS N_FAIL N_MISSING N_WAIVED FAILED MISSING READY OUTPUT.
Exit codes: 0 READY=1, 1 READY=0 (the card is still written and says NOT READY), 2 bad input.
--dry-run prints the verdict and writes nothing.
"""
from __future__ import annotations

import argparse
import json
import sys
import time


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--name", required=True)
    p.add_argument("--out", default="MODEL_CARD.md")
    p.add_argument("--check", action="append", default=[], help="NAME=path/to/json (repeatable)")
    p.add_argument("--require", default="table,training,evaluation,sculpting,closure")
    p.add_argument("--waive", action="append", default=[], help="NAME=REASON (repeatable)")
    p.add_argument("--field", action="append", default=[], help="'Key=text' row for the card (repeatable)")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    try:
        checks = {}
        for c in a.check:
            name, path = c.split("=", 1)
            checks[name] = (path, json.load(open(path))["summary"])
        waived = dict(w.split("=", 1) for w in a.waive)
        fields = [f.split("=", 1) for f in a.field]
        if any(not r.strip() for r in waived.values()):
            raise ValueError("--waive needs a reason")
    except Exception as e:  # noqa: BLE001
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    required = [r for r in a.require.split(",") if r]
    missing = [r for r in required if r not in checks and r not in waived]
    failed = [n for n, (_, s) in checks.items() if s.get("STATUS") != "PASS" and n not in waived]
    npass = sum(s.get("STATUS") == "PASS" for _, s in checks.values())
    ready = not missing and not failed
    res = {"N_CHECKS": len(checks), "N_PASS": npass, "N_FAIL": len(failed), "N_MISSING": len(missing),
           "N_WAIVED": len(waived), "FAILED": ",".join(failed) or "none", "MISSING": ",".join(missing) or "none",
           "READY": int(ready), "OUTPUT": a.out}
    if not a.dry_run:
        L = [f"# Model card: {a.name}", "",
             f"**Verdict: {'READY' if ready else 'NOT READY'}** ({time.strftime('%Y-%m-%d')}; "
             f"{npass} passed, {len(failed)} failed, {len(missing)} missing, {len(waived)} waived)", ""]
        if waived:
            L += ["## Waivers", ""] + [f"- **{n}**: {r}" for n, r in waived.items()] + [""]
        if fields:
            L += ["## Description", "", "| Item | Value |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in fields] + [""]
        L += ["## Checks", "", "| Check | Status | File |", "| --- | --- | --- |"]
        for n in dict.fromkeys(required + list(checks)):
            st = "WAIVED" if n in waived else (checks[n][1].get("STATUS", "?") if n in checks else "MISSING")
            L.append(f"| {n} | {st} | {checks[n][0] if n in checks else ''} |")
        for n, (path, s) in checks.items():
            L += ["", f"### {n}", "", "| Key | Value |", "| --- | --- |"] + [f"| {k} | {v} |" for k, v in s.items()]
        with open(a.out, "w") as f:
            f.write("\n".join(L) + "\n")
    print("\n".join(f"{k}={v}" for k, v in res.items()))
    return 0 if ready else 1


if __name__ == "__main__":
    sys.exit(main())
