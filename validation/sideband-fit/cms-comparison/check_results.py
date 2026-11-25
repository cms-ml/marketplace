"""Check independent numerical agreements and preserved stress-test evidence."""
import argparse
import json
import math
from pathlib import Path
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("directory", type=Path, nargs="?", default=Path(__file__).resolve().parent,
                    help="directory containing comparison.json and ensembles.json")
base = parser.parse_args().directory
try:
    data = json.loads((base / "comparison.json").read_text())
    ensembles = json.loads((base / "ensembles.json").read_text())
    tests = list(data["tests"].values())
    open_fit = data["open_refit"]
    coarse = data["table3_crosscheck"]
    checks = {
        "recoverable count in every bin": all(a == b for _, _, (a, b), _ in data["rows"]),
        "coarse observed count respects edge ambiguity": coarse["lower"] <= coarse["observed"] <= coarse["upper"],
        "mask replacement and independent integration": all(t["mask_invariant"] and math.isclose(t["independent_mean"],t["mean"],rel_tol=2e-5) for t in tests),
        "independent propagated covariance": all(math.isclose(t["independent_variance"],t["variance"],rel_tol=2e-5) for t in tests),
        "original continuum independent means and correlations": all(math.isclose(x,y,rel_tol=2e-5) for x,y in zip(open_fit["mean"],open_fit["student"])) and all(math.isclose(x,y,rel_tol=2e-5) for a,b in zip(open_fit["covariance"],open_fit["student_covariance"]) for x,y in zip(a,b)),
        "ensemble accounting": len(ensembles)==6 and all(0<=m["covered"]<=m["valid"]<=r["attempts"] and r["attempts"]==300 for r in ensembles for method in r["methods"].values() for m in method.values()),
        "stress signal detected": ensembles[4]["methods"]["selected"]["signal"]["bias"]>30 and ensembles[4]["methods"]["selected"]["background"]["coverage"]<.2,
    }
except (OSError,ValueError,KeyError) as exc:
    print(exc, file=sys.stderr)
    sys.exit(2)
for name,ok in checks.items():
    print(("PASS" if ok else "FAIL"),name)
print(f"SUMMARY={sum(checks.values())}/{len(checks)}")
sys.exit(0 if all(checks.values()) else 1)
