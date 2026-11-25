"""Fit Poisson sidebands in an unweighted integer-count mass histogram."""

import argparse
import json
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile

import numpy as np
from numpy.polynomial.legendre import leggauss
from scipy.optimize import minimize
from scipy.special import logsumexp, ndtr, xlogy
from scipy.stats import nbinom, poisson


SHAPE_BOUNDS = (-12.0, 12.0)
QUADRATURE_ORDER = 32
SCORE_TOLERANCE = 1e-6


def checked_edges(edges):
    edges = np.asarray(edges, dtype=float)
    if (edges.ndim != 1 or edges.size < 2 or not np.all(np.isfinite(edges))
            or np.any(np.diff(edges) <= 0)):
        raise ValueError("edges must be finite, strictly increasing and one-dimensional")
    return edges


def window_masks(edges, intervals):
    """Return one mask per window. Each endpoint must match one known edge."""
    edges = checked_edges(edges)
    windows = []
    used = np.zeros(edges.size - 1, dtype=bool)
    for lower, upper in intervals:
        left = np.flatnonzero(np.isclose(edges, lower, rtol=1e-12, atol=1e-12))
        right = np.flatnonzero(np.isclose(edges, upper, rtol=1e-12, atol=1e-12))
        if left.size != 1 or right.size != 1 or left[0] >= right[0]:
            raise ValueError(f"window [{lower}, {upper}] must match ordered bin edges")
        window = np.zeros_like(used)
        window[left[0]:right[0]] = True
        if np.any(used & window):
            raise ValueError("excluded windows must be disjoint")
        used |= window
        windows.append(window)
    if not windows:
        raise ValueError("specify at least one excluded window")
    return np.array(windows)


def integer_counts(counts):
    counts = np.asarray(counts, dtype=float)
    if (counts.ndim != 1 or not np.all(np.isfinite(counts)) or np.any(counts < 0)
            or np.any(counts != np.floor(counts))):
        raise ValueError("observations must be finite unweighted nonnegative integer counts")
    return counts


class Spectrum:
    """Gauss-Legendre integration of exp(beta[0]*t + beta[1]*t**2) over mass."""

    def __init__(self, edges, coordinate, quadrature_order=QUADRATURE_ORDER):
        self.edges = checked_edges(edges)
        if coordinate not in ("mass", "log_mass"):
            raise ValueError("coordinate must be mass or log_mass")
        if coordinate == "log_mass" and self.edges[0] <= 0:
            raise ValueError("log_mass requires positive edges")
        self.coordinate = coordinate
        nodes, weights = leggauss(quadrature_order)
        halfwidth = np.diff(self.edges) / 2
        self.nodes = self.edges[:-1, None] + halfwidth[:, None] * (nodes + 1)
        self.log_weights = np.log(halfwidth[:, None] * weights)
        transform = np.log if coordinate == "log_mass" else np.asarray
        lo, hi = transform(self.edges[[0, -1]])
        t = 2 * (transform(self.nodes) - lo) / (hi - lo) - 1
        self.features = np.stack((t, t ** 2), axis=-1)

    def moments(self, beta):
        """Return log bin integrals and their shape gradients."""
        features = self.features[..., :len(beta)]
        log_integrand = self.log_weights + features @ beta
        log_integrals = logsumexp(log_integrand, axis=1)
        weights = np.exp(log_integrand - log_integrals[:, None])
        gradient = np.einsum("ij,ijk->ik", weights, features)
        return log_integrals, gradient

    def evaluate(self, beta, normalization, sideband):
        log_q, dlog_q = self.moments(beta)
        log_qsb = logsumexp(log_q[sideband])
        p_sb = np.exp(log_q[sideband] - log_qsb)
        centered = dlog_q - p_sb @ dlog_q[sideband]
        prediction = normalization * np.exp(log_q - log_qsb)
        jacobian = prediction[:, None] * np.column_stack((np.ones(len(log_q)), centered))
        return prediction, jacobian


def deviance_residual(counts, expected):
    """Signed square-root Poisson deviance residual, defined also for zero counts."""
    terms = xlogy(counts, counts / expected) - counts + expected
    return np.sign(counts - expected) * np.sqrt(2 * np.maximum(terms, 0))


def projected_score(values, gradient, bounds=SHAPE_BOUNDS):
    gradient = np.asarray(gradient).copy()
    gradient[(values <= bounds[0] + 1e-7) & (gradient > 0)] = 0
    gradient[(values >= bounds[1] - 1e-7) & (gradient < 0)] = 0
    return float(np.max(np.abs(gradient)))



def minimize_with_retry(objective, start, bounds, *, ftol, gtol):
    """Retry a failed line search from its endpoint at a relaxed score tolerance."""
    options = {"ftol": ftol, "gtol": gtol, "maxiter": 400}
    result = minimize(objective, start, method="L-BFGS-B", jac=True, bounds=bounds, options=options)
    if result.success:
        return result, 1
    options["gtol"] = 1e-7
    return minimize(objective, result.x, method="L-BFGS-B", jac=True, bounds=bounds, options=options), 2


def fisher_covariance(jacobian, expected):
    scaled = jacobian / np.sqrt(expected[:, None])
    information = scaled.T @ scaled
    eigenvalues = np.linalg.eigvalsh(information)
    if eigenvalues[0] <= eigenvalues[-1] * 1e-12 or eigenvalues[0] <= 0:
        return None, None
    return np.linalg.inv(information), float(eigenvalues[-1] / eigenvalues[0])


def fit_sideband(spectrum, sideband, observations, order):
    """Fit using only the supplied sideband observations, in ascending bin order."""
    sideband = np.asarray(sideband, dtype=bool)
    observations = integer_counts(observations)
    if order not in (1, 2):
        raise ValueError("supported shape orders are 1 and 2")
    if sideband.shape != (len(spectrum.edges) - 1,) or sideband.sum() != len(observations):
        raise ValueError("sideband mask and supplied observations disagree")
    if len(observations) <= order + 1 or observations.sum() <= 0:
        raise ValueError("positive total and more sideband bins than parameters required")
    total = observations.sum()
    fractions = observations / total

    def objective(beta):
        log_q, dlog_q = spectrum.moments(beta)
        log_q = log_q[sideband]
        dlog_q = dlog_q[sideband]
        log_p = log_q - logsumexp(log_q)
        return -fractions @ log_p, (np.exp(log_p) - fractions) @ dlog_q

    result, attempts = minimize_with_retry(objective, np.zeros(order), [SHAPE_BOUNDS] * order,
                                           ftol=1e-15, gtol=1e-10)
    beta = result.x
    score = projected_score(beta, result.jac)
    boundary = bool(np.any(np.isclose(beta[:, None], SHAPE_BOUNDS, rtol=0, atol=1e-6)))
    prediction, jacobian = spectrum.evaluate(beta, total, sideband)
    covariance, condition = fisher_covariance(jacobian[sideband], prediction[sideband])
    deviance = float(np.sum(deviance_residual(observations, prediction[sideband]) ** 2))
    converged = bool(result.success and score < SCORE_TOLERANCE)
    return {
        "order": order, "log_sideband_yield": float(np.log(total)), "beta": beta,
        "converged": converged, "boundary": boundary, "optimizer_status": int(result.status),
        "optimizer_message": str(result.message), "optimizer_attempts": attempts,
        "iterations": int(result.nit),
        "projected_score_per_event": score, "fisher_condition": condition,
        "valid": converged and not boundary and covariance is not None,
        "deviance": deviance, "ndf": int(len(observations) - order - 1),
        "aic_deviance": deviance + 2 * (order + 1), "prediction": prediction,
        "parameter_covariance": covariance, "jacobian": jacobian,
    }


def select_fit(fits):
    return min((fit for fit in fits if fit["valid"]), default=None,
               key=lambda fit: (fit["aic_deviance"], fit["order"]))


def yield_intervals(expected, variance, z=1.0):
    """Log-delta mean CI and moment-matched Poisson-gamma predictive interval."""
    relative = np.sqrt(variance) / expected
    mean_interval = expected * np.exp(np.array([-z, z]) * relative)
    probability = ndtr([-z, z])
    if relative < 1e-5:
        count_interval = poisson.ppf(probability, expected)
    else:
        count_interval = nbinom.ppf(probability, 1 / relative ** 2,
                                   1 / (1 + variance / expected))
    return mean_interval, count_interval


def window_prediction(fit, windows):
    prediction = fit["prediction"]
    jacobian = fit["jacobian"]
    windows = np.asarray(windows, dtype=float)
    means = windows @ prediction
    if fit["parameter_covariance"] is None:
        return means, None
    window_jacobian = windows @ jacobian
    return means, window_jacobian @ fit["parameter_covariance"] @ window_jacobian.T


def report_fit(fit, windows):
    report = {key: value for key, value in fit.items() if key != "jacobian"}
    jacobian, covariance = fit["jacobian"], fit["parameter_covariance"]
    means, window_covariance = window_prediction(fit, windows)
    report.update(window_expected=means, window_covariance=window_covariance,
                  prediction_covariance=None if covariance is None else jacobian @ covariance @ jacobian.T)
    if fit["valid"]:
        intervals = [yield_intervals(m, v) for m, v in zip(means, window_covariance.diagonal())]
        report["window_expected_intervals"] = [pair[0] for pair in intervals]
        report["window_observed_intervals"] = [pair[1] for pair in intervals]
    return report


def fit_histogram(edges, counts, intervals, coordinate, orders):
    """Create a complete report based exclusively on unmasked observations."""
    windows = window_masks(edges, intervals)
    sideband = ~np.any(windows, axis=0)
    counts = np.asarray(counts, dtype=object)
    if counts.shape != sideband.shape:
        raise ValueError("counts must contain one value per bin")
    observations = integer_counts(counts[sideband])
    spectrum = Spectrum(edges, coordinate)
    if not orders or len(set(orders)) != len(orders):
        raise ValueError("orders must be nonempty and unique")
    fits = [fit_sideband(spectrum, sideband, observations, order) for order in orders]
    selected = select_fit(fits)
    return {
        "schema_version": 1, "edges": spectrum.edges, "coordinate": coordinate,
        "ordered_parameters": "log_sideband_yield, beta_1, [beta_2]",
        "mass_unit": "GeV", "count_unit": "events", "quadrature_order": QUADRATURE_ORDER,
        "shape_bounds": SHAPE_BOUNDS, "excluded_intervals": intervals, "window_masks": windows,
        "sideband_mask": sideband,
        "sideband_counts": [int(value) if keep else None for value, keep in zip(counts, sideband)],
        "selected_order": None if selected is None else selected["order"],
        "candidates": [report_fit(fit, windows) for fit in fits],
    }


def json_text(payload):
    return json.dumps(payload, default=lambda value: value.tolist(), allow_nan=False, indent=2) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="JSON with GeV edges and one integer count per bin")
    parser.add_argument("--mask", type=float, nargs=2, action="append", required=True,
                        metavar=("LOW", "HIGH"), help="exclude a range bounded by exact histogram edges")
    parser.add_argument("--coordinate", choices=["mass", "log_mass"], default="mass")
    parser.add_argument("--orders", type=int, choices=[1, 2], nargs="+", default=[1, 2])
    parser.add_argument("--output", type=Path, help="write JSON to this path (default stdout)")
    parser.add_argument("--dry-run", action="store_true", help="run fit and emit JSON without writing a file")
    args = parser.parse_args()
    try:
        source = json.loads(args.input.read_text())
        report = fit_histogram(source["edges"], source["counts"], args.mask,
                               args.coordinate, args.orders)
        output = json_text(report)
        if args.output and not args.dry_run:
            with NamedTemporaryFile("w", dir=args.output.parent, delete=False) as destination:
                temporary = Path(destination.name)
                try:
                    destination.write(output)
                    destination.close()
                    temporary.replace(args.output)
                finally:
                    temporary.unlink(missing_ok=True)
            print(f"FIT_JSON={args.output}")
        else:
            print(output, end="")
        return 0 if report["selected_order"] is not None else 1
    except (OSError, TypeError, ValueError, KeyError) as error:
        print(f"sideband fit: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
