"""Run Poisson ensembles on sideband-calibrated in-family and alternate truths."""

from concurrent.futures import ProcessPoolExecutor
from functools import partial

import numpy as np
from scipy.optimize import brentq
from scipy.special import ndtr, xlogy

from fit_sidebands import (
    SHAPE_BOUNDS,
    SCORE_TOLERANCE,
    fit_sideband,
    fisher_covariance,
    minimize_with_retry,
    projected_score,
    select_fit,
    window_prediction,
    yield_intervals,
)


def signal_template(edges, mass, sigma):
    t = (edges - mass) / sigma
    signal = np.where(t[:-1] < 0, np.diff(ndtr(t)), -np.diff(ndtr(-t)))
    return signal / signal.sum()


def signed_signal_fit(spectrum, counts, sideband, shape, sideband_fit):
    """Profile an unrestricted signed signal with positive total bin means."""
    total = counts.sum()
    normalization = np.exp(sideband_fit["log_sideband_yield"])
    start = np.r_[0.0, sideband_fit["beta"]]
    support = shape > 0
    fraction = 1 - 1e-10

    def profile(parameters):
        bkg, jacobian = spectrum.evaluate(parameters[1:], normalization * np.exp(parameters[0]), sideband)
        admissible = -fraction * bkg[support] / shape[support]
        lower_index = np.flatnonzero(support)[np.argmax(admissible)]
        lo = admissible.max()

        def derivative(signal):
            return np.sum(shape * (1 - counts / (bkg + signal * shape)))

        at_limit = derivative(lo) >= 0
        signal = lo if at_limit else brentq(derivative, lo, total + 1, xtol=1e-8)
        expected = bkg + signal * shape
        residual = 1 - counts / expected
        gradient = residual @ jacobian
        if at_limit:
            gradient -= derivative(signal) * fraction * jacobian[lower_index] / shape[lower_index]
        return (expected, np.column_stack((jacobian, shape)), gradient,
                float(signal), bool(at_limit))

    def objective(parameters):
        expected, _, gradient, _, _ = profile(parameters)
        return np.sum(expected - xlogy(counts, expected)) / total, gradient / total

    bounds = np.array([[-2, 2]] + [SHAPE_BOUNDS] * (len(start) - 1))
    result, attempts = minimize_with_retry(objective, start, bounds, ftol=1e-14, gtol=1e-9)
    expected, jacobian, gradient, signal, signal_boundary = profile(result.x)
    score = projected_score(result.x, gradient / total, bounds.T)
    converged = bool(result.success and score < SCORE_TOLERANCE)
    boundary = signal_boundary or bool(np.any(np.isclose(result.x[:, None], bounds, atol=1e-6, rtol=0)))
    covariance, _ = fisher_covariance(jacobian, expected)
    valid = converged and not boundary and covariance is not None
    return {"valid": valid, "converged": converged, "boundary": boundary,
            "signal_boundary": signal_boundary, "optimizer_attempts": attempts, "yield": signal,
            "std": float(np.sqrt(covariance[-1, -1])) if valid else None}


def truth_shapes(spectrum, sideband, fits, cfg, signal_mass):
    fits = {fit["order"]: fit for fit in fits}
    if not all(fits[order]["valid"] for order in (1, 2)):
        raise ValueError("both sideband fits must be valid for the frozen toy truths")
    linear, quadratic = (fits[order]["prediction"] for order in (1, 2))
    normalization = linear[sideband].sum()
    beta = fits[1]["beta"] - cfg["mixture_slope_shift"]
    steep, _ = spectrum.evaluate(beta, normalization, sideband)
    fraction = cfg["mixture_fraction_in_sidebands"]
    mixture = (1 - fraction) * linear + fraction * steep

    # Reweight at each quadrature node, never at bin centers.
    t = (spectrum.nodes - signal_mass) / (cfg["broad_modulation_relative_sigma"] * signal_mass)
    model = np.exp(spectrum.log_weights + fits[1]["beta"][0] * spectrum.features[..., 0])
    modulation = 1 + cfg["broad_modulation_amplitude"] * np.exp(-0.5 * t ** 2)
    broad = (model * modulation).sum(axis=1)
    broad *= normalization / broad[sideband].sum()
    return {"linear": linear, "quadratic": quadratic, "smooth_mixture": mixture,
            "broad_modulation": broad}


def coverage(successes, denominator):
    if denominator == 0:
        return {"covered": 0, "denominator": 0, "fraction": None,
                "mc_standard_error": None, "mc_wilson_interval": None}
    fraction = successes / denominator
    variance = fraction * (1 - fraction) / denominator
    correction = 1 / denominator
    center = (fraction + correction / 2) / (1 + correction)
    half_width = np.sqrt(variance + correction ** 2 / 4) / (1 + correction)
    return {"covered": successes, "denominator": denominator, "fraction": fraction,
            "mc_standard_error": float(np.sqrt(variance)),
            "mc_wilson_interval": [max(0, center - half_width), min(1, center + half_width)]}


def moments(values):
    if not len(values):
        return {"mean": None, "sd": None, "mean_mc_standard_error": None}
    sd = float(np.std(values, ddof=1)) if len(values) > 1 else None
    return {"mean": float(np.mean(values)), "sd": sd,
            "mean_mc_standard_error": sd / np.sqrt(len(values)) if sd is not None else None}


def metrics(values, truth, attempts, integer_prediction=False, z=1.0):
    """Values columns: estimate, sigma, expected lo/hi, observed lo/hi, observed."""
    values = np.asarray(values).reshape(-1, 7)
    fit, error, lo, hi, count_lo, count_hi, count = values.T
    residual = fit - truth
    covered = int(np.sum((lo <= truth) & (truth <= hi)))
    result = {
        "truth": float(truth), "nominal_probability": float(ndtr(z) - ndtr(-z)),
        "valid_results": len(values),
        "estimate": moments(fit), "bias": moments(residual), "pull": moments(residual / error),
        "expected_interval_width": moments(hi - lo),
        "expected_coverage_conditional_on_valid": coverage(covered, len(values)),
        "expected_coverage_failed_as_uncovered": coverage(covered, attempts),
    }
    if integer_prediction:
        covered_count = int(np.sum((count_lo <= count) & (count <= count_hi)))
        result.update(observed_interval_width=moments(count_hi - count_lo),
                      observed_coverage_conditional_on_valid=coverage(covered_count, len(values)),
                      observed_coverage_failed_as_uncovered=coverage(covered_count, attempts))
    return result


def run_scenario(job, *, spectrum, sideband, shape, windows, orders, z, attempts, fixed_order):
    truth_name, truth, injected, stream = job
    random = np.random.default_rng(stream)
    scenarios = {"fixed_linear": [], "aic": []}
    candidate_diagnostics = {str(order): {"boundary": 0, "nonconverged": 0, "invalid": 0, "optimizer_retried": 0} for order in orders}
    for observed in random.poisson(truth + injected * shape, size=(attempts, len(truth))):
        candidates = [fit_sideband(spectrum, sideband, observed[sideband], order)
                      for order in orders]
        for fit in candidates:
            diagnostic = candidate_diagnostics[str(fit["order"])]
            diagnostic["boundary"] += fit["boundary"]
            diagnostic["optimizer_retried"] += fit["optimizer_attempts"] > 1
            diagnostic["nonconverged"] += not fit["converged"]
            diagnostic["invalid"] += not fit["valid"]
        fixed = next(fit for fit in candidates if fit["order"] == fixed_order)
        aic = select_fit(candidates)
        # If fixed and selected procedures use the same order, reuse the identical joint fit.
        joint_fits = {}
        for name, chosen in (("fixed_linear", fixed), ("aic", aic)):
            if chosen is None or not chosen["valid"]:
                scenarios[name].append(None)
                continue
            means, covariance = window_prediction(chosen, windows)
            window_values = []
            for mu, var, n in zip(means, covariance.diagonal(), windows @ observed):
                expected, count = yield_intervals(mu, var, z)
                window_values.append([mu, np.sqrt(var), *expected, *count, n])
            order = chosen["order"]
            if order not in joint_fits:
                joint_fits[order] = signed_signal_fit(spectrum, observed, sideband, shape, chosen)
            scenarios[name].append((order, window_values, joint_fits[order]))

    key = f"{truth_name}_inject_{injected}"
    result = {"attempts": attempts, "truth": truth_name, "injected": injected,
                    "spawn_key": stream.spawn_key, "candidates": candidate_diagnostics,
                    "methods": {}}
    pulls = {}
    for name, entries in scenarios.items():
        successful = [entry for entry in entries if entry is not None]
        signal_fits = [entry[2] for entry in successful]
        valid_signals = [fit for fit in signal_fits if fit["valid"]]
        signal_values = [[fit["yield"], fit["std"], fit["yield"] - z * fit["std"],
                          fit["yield"] + z * fit["std"], 0, 0, 0] for fit in valid_signals]
        result["methods"][name] = {
            "sideband_valid": len(successful), "sideband_failed": attempts - len(successful),
            "orders": {str(order): sum(entry[0] == order for entry in successful)
                       for order in (1, 2)},
            "signal_attempted": len(signal_fits), "signal_valid": len(valid_signals),
            "signal_failed": len(signal_fits) - len(valid_signals),
            "signal_nonconverged": sum(not fit["converged"] for fit in signal_fits),
            "signal_optimizer_retried": sum(fit["optimizer_attempts"] > 1 for fit in signal_fits),
            "signal_boundary": sum(fit["boundary"] for fit in signal_fits),
            "signed_yield_boundary": sum(fit["signal_boundary"] for fit in signal_fits),
            "negative_signed_estimates": sum(fit["yield"] < 0 for fit in valid_signals),
            "min_signed_estimate": min((fit["yield"] for fit in valid_signals), default=None),
            "max_signed_estimate": max((fit["yield"] for fit in valid_signals), default=None),
            "background": [metrics([entry[1][i] for entry in successful], t,
                                   attempts, integer_prediction=injected == 0, z=z)
                           for i, t in enumerate(windows @ truth)],
            "signal": metrics(signal_values, injected, attempts, z=z),
        }
        if name == "aic":
            pulls = {
                "background": [(entry[1][0][0] - (windows @ truth)[0]) / entry[1][0][1]
                               for entry in successful],
                "signal": [(fit["yield"] - injected) / fit["std"] for fit in valid_signals],
            }
    return key, result, pulls


def run_ensembles(spectrum, windows, fits, cfg, attempts, seed, fixed_order, workers):
    sideband = ~np.any(windows, axis=0)
    first = np.flatnonzero(windows[0])
    mass = np.sqrt(spectrum.edges[first[0]] * spectrum.edges[first[-1] + 1])
    signal = signal_template(spectrum.edges, mass, cfg["signal_relative_sigma"] * mass)
    # Common numerical support in generation and fitting.
    signal[signal < 1e-200] = 0
    signal /= signal.sum()
    truths = truth_shapes(spectrum, sideband, fits, cfg, mass)
    scenarios = [(name, injected) for name in cfg["truths"] for injected in cfg["injected_signal_events"]]
    streams = np.random.SeedSequence(seed).spawn(len(scenarios))
    jobs = [(name, truths[name], injected, stream) for (name, injected), stream in zip(scenarios, streams)]
    run = partial(run_scenario, spectrum=spectrum, sideband=sideband, shape=signal,
                  windows=windows.astype(float), orders=[fit["order"] for fit in fits],
                  z=cfg["coverage_z"], attempts=attempts, fixed_order=fixed_order)
    if workers == 1:
        outcomes = list(map(run, jobs))
    else:
        with ProcessPoolExecutor(max_workers=workers) as executor:
            outcomes = list(executor.map(run, jobs))
    results = {key: result for key, result, _ in outcomes}
    pull_samples = {key: pulls for key, _, pulls in outcomes}
    return {
        "seed": seed, "seed_bit_generator": "PCG64", "attempts_per_scenario": attempts,
        "signal_mass_GeV": mass, "signal_sigma_GeV": cfg["signal_relative_sigma"] * mass,
        "signal_sideband_fraction": float(signal[sideband].sum()), "signal_template": signal,
        "background_truth_bin_expectations": truths, "scenarios": results,
    }, pull_samples
