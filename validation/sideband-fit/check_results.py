"""Check a final benchmark summary using only the standard library."""

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path


HERE = Path(__file__).resolve().parent


def independent_integrals(edges, coordinate, beta):
    """Evaluate the declared density with composite Simpson integration."""
    transform = math.log if coordinate == "log_mass" else float
    lower = transform(edges[0])
    span = transform(edges[-1]) - lower

    def density(x):
        t = 2 * (transform(x) - lower) / span - 1
        return math.exp(sum(value * t ** (i + 1) for i, value in enumerate(beta)))

    integrals = []
    for lo, hi in zip(edges, edges[1:]):
        dx = (hi - lo) / 128
        weighted = sum((4 if i % 2 else 2) * density(lo + dx * i) for i in range(1, 128))
        integrals.append((density(lo) + density(hi) + weighted) * dx / 3)
    return integrals


def consistent_case(case):
    counts, masks, sideband = case["counts"], case["window_masks"], case["sideband_mask"]
    n = case["nbins"]
    if not (len(case["edges"]) == n + 1 and len(counts) == len(sideband) == n
            and all(len(row) == n for row in masks)
            and all(obs >= 0 and obs == int(obs) for obs in counts)):
        return False
    expected_masks = [[lo <= a + 1e-12 and b <= hi + 1e-12
                       for a, b in zip(case["edges"], case["edges"][1:])]
                      for lo, hi in case["excluded_intervals"]]
    if masks != expected_masks or any((sum(column) + keep != 1) for column, keep in zip(zip(*masks), sideband)):
        return False
    if case["sideband_counts"] != [count if keep else None for count, keep in zip(counts, sideband)]:
        return False
    return case["masked_observed"] == [sum(n for n, keep in zip(counts, mask) if keep) for mask in masks]


def consistent_models(case):
    fitted = case["candidates"]
    sideband = case["sideband_mask"]
    total = sum(n for n in case["sideband_counts"] if n is not None)
    if not all(candidate["valid"] and candidate["converged"] and not candidate["boundary"] for candidate in fitted):
        return False
    selected = min(fitted, key=lambda candidate: (candidate["aic_deviance"], candidate["order"]))
    if selected["order"] != case["selected_order"]:
        return False
    for candidate in fitted:
        prediction = candidate["prediction"]
        independent = independent_integrals(case["edges"], case["coordinate"], candidate["beta"])
        norm = total / sum(q for q, keep in zip(independent, sideband) if keep)
        if not all(mu > 0 and math.isclose(mu, norm * q, rel_tol=2e-7)
                   for mu, q in zip(prediction, independent)):
            return False
        covariance = candidate["parameter_covariance"]
        if not math.isclose(covariance[0][0], 1 / total, rel_tol=1e-9):
            return False
        if any(abs(covariance[0][i]) > 1e-10 for i in range(1, len(covariance))):
            return False
        for i, mask in enumerate(case["window_masks"]):
            norm = sum(mu for mu, keep in zip(prediction, mask) if keep)
            mean = candidate["window_expected"][i]
            c = candidate["window_covariance"]
            lo, hi = candidate["window_expected_intervals"][i]
            if not (0 < lo < mean < hi and math.isclose(mean, norm, rel_tol=1e-9)
                    and c[i][i] > 0 and all(abs(c[i][j]) <= math.sqrt(c[i][i] * c[j][j]) + 1e-9
                                           for j in range(len(c)))):
                return False
    return True


def consistent_coverage(coverage, denominator):
    k = coverage["covered"]
    p = coverage["fraction"]
    error = coverage["mc_standard_error"]
    lo, hi = coverage["mc_wilson_interval"]
    return (coverage["denominator"] == denominator and 0 <= k <= denominator and
            math.isclose(p, k / denominator) and
            math.isclose(error, math.sqrt(p * (1 - p) / denominator)) and 0 <= lo <= p <= hi <= 1)


def ensemble_accounting(toys, config):
    expected = {(kind, injected) for kind in config["truths"]
                for injected in config["injected_signal_events"]}
    scenarios = toys["scenarios"].values()
    if {(case["truth"], case["injected"]) for case in scenarios} != expected:
        return False
    if len({tuple(case["spawn_key"]) for case in scenarios}) != len(expected):
        return False
    if not 0 < toys["signal_sideband_fraction"] < 0.2 or not math.isclose(sum(toys["signal_template"]), 1):
        return False
    for case in scenarios:
        attempts = case["attempts"]
        if attempts != config["attempts_per_scenario"]:
            return False
        for method, result in case["methods"].items():
            sideband = result["sideband_valid"]
            if (sideband + result["sideband_failed"] != attempts or
                    sideband != result["signal_attempted"] or sum(result["orders"].values()) != sideband or
                    result["signal_valid"] + result["signal_failed"] != sideband or
                    not 0 <= result["signed_yield_boundary"] <= result["signal_boundary"] <= result["signal_failed"] or
                    (method == "fixed_linear" and result["orders"]["2"] != 0)):
                return False
            for entry, usable in [(result["signal"], result["signal_valid"]),
                                  *((bkg, sideband) for bkg in result["background"])]:
                if entry["valid_results"] != usable or usable < attempts * 0.95:
                    return False
                for target in ("expected", "observed"):
                    if target == "observed" and "observed_interval_width" not in entry:
                        continue
                    conditional = entry[f"{target}_coverage_conditional_on_valid"]
                    unconditional = entry[f"{target}_coverage_failed_as_uncovered"]
                    if conditional["covered"] != unconditional["covered"]:
                        return False
                    if not (consistent_coverage(conditional, usable) and
                            consistent_coverage(unconditional, attempts)):
                        return False
    return True


def nominal_controls(toys):
    """In-family fixed-order checks; misspecification results have no pass threshold."""
    for injected in (0, 45):
        result = toys["scenarios"][f"linear_inject_{injected}"]["methods"]["fixed_linear"]
        for metric in [result["signal"], *result["background"]]:
            fraction = metric["expected_coverage_failed_as_uncovered"]["fraction"]
            scale = metric["pull"]["sd"]
            if not 0.58 <= fraction <= 0.79 or not 0.75 <= scale <= 1.25:
                return False
    no_signal = toys["scenarios"]["linear_inject_0"]["methods"]["fixed_linear"]
    return (0 < no_signal["negative_signed_estimates"] < no_signal["signal_valid"]
            and all(item["observed_coverage_failed_as_uncovered"]["fraction"] >= 0.6
                    for item in no_signal["background"]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("summary", type=Path, nargs="?", default=HERE / "summary.json",
                        help="summary JSON file or validation directory")
    args = parser.parse_args()
    summary_path = args.summary / "summary.json" if args.summary.is_dir() else args.summary
    try:
        summary = json.loads(summary_path.read_text())
        raw = (HERE / "frozen.json").read_bytes()
        frozen = json.loads(raw)
        jpsi, continuum, toys = (summary[key] for key in ("jpsi", "continuum", "toys"))
        checks = {
            "frozen configuration and seed": (
                summary["configuration_sha256"] == hashlib.sha256(raw).hexdigest()
                and toys["seed"] == frozen["toys"]["master_seed"]),
            "independent workshop count benchmark": (
                jpsi["metadata"]["all_rows"] == 100000
                and jpsi["metadata"]["workshop_subtraction"] == 7745.5),
            "valid blind masks and count bookkeeping": consistent_case(jpsi) and consistent_case(continuum),
            "independent bin integration and covariance": consistent_models(jpsi) and consistent_models(continuum),
            "positive resonance extraction with counting and fit error": (
                jpsi["window_subtraction"][0] > 0
                and jpsi["window_subtraction_stat_std"][0] > math.sqrt(jpsi["masked_observed"][0])),
            "continuum window separation and retained zero bins": (
                len(continuum["excluded_intervals"]) == 2 and 0 in continuum["sideband_counts"]),
            "toy attempts, signed fits and coverage bookkeeping": ensemble_accounting(toys, frozen["toys"]),
            "in-family fixed-model pull and coverage control": nominal_controls(toys),
        }
    except (OSError, ValueError, KeyError, TypeError, ZeroDivisionError, IndexError) as error:
        print(f"Invalid sideband validation result: {error}", file=sys.stderr)
        return 2
    for label, valid in checks.items():
        print(f"{'PASS' if valid else 'FAIL'} {label}")
    print(f"SUMMARY={sum(checks.values())}/{len(checks)}")
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
