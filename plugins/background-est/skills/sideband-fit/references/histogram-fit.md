# Histogram fit interface

Read this reference when running the histogram CLI on a held-out spectrum or
using its covariance in another analysis.

## Contents

- [Input and invocation](#input-and-invocation)
- [Likelihood and covariance](#likelihood-and-covariance)
- [Intervals and diagnostics](#intervals-and-diagnostics)

## Input and invocation

Supply a JSON object with `edges` (strictly increasing GeV boundaries) and
`counts` (one integer count per bin, with `null` for blinded bins). Count
positions follow the intervals between consecutive edges. The example uses
the workshop histogram prepared with its 2.8–3.4 GeV range and 0.02 GeV bins.
From the repository root, with the blinded JSON in your current directory:

```bash
python3 plugins/background-est/skills/sideband-fit/scripts/fit_sidebands.py \
  jpsi-blinded.json --mask 3.0 3.2 --coordinate mass --orders 1 2 --output jpsi-fit.json
```

Repeat `--mask LOW HIGH` for disjoint windows, using histogram edges as
arguments. Use `--coordinate log_mass` for a supported log-mass shape on a
positive mass axis. The integration is always over mass, including bin
widths. Without `--output` or with `--dry-run`, the result goes to standard
output and no file is written. With `--output`, the program writes the
report and prints `FIT_JSON=<path>`. Exit status is 0 for a selected
candidate, 1 if all fits are unusable, or 2 for invalid input/output.

Tested at cmslpc in LCG_109 (`x86_64-el9-gcc15-opt`), Python 3.13.11,
NumPy 2.2.6 and SciPy 1.16.3.

## Likelihood and covariance

For bin \(i\), integrate \(q*i=\int_i\exp(\beta_1t+\beta_2t^2)\,dm\) with
32-point Gauss–Legendre quadrature. The coordinate \(t\) runs from −1 to 1
in mass or log mass over the entire histogram range. The order-one model
sets \(\beta_2=0\). Coefficients range from −12 to 12.
The expected bin count is \(\lambda_i=N*{\rm SB}q*i/\sum*{\rm SB}q*i\).
The unconstrained Poisson estimate of \(N*{\rm SB}\) is the total count in
the sidebands. Optimization profiles this normalization and minimizes the
equivalent shape likelihood with bounded L-BFGS-B. If the optimizer reports
failure, retry once from its endpoint with a score tolerance of `1e-7`.
The final fit must still meet the projected-score acceptance threshold
of `1e-6` per event. The report records the number of optimizer attempts.

The returned parameters run in order `log_sideband_yield, beta_1, [beta_2]`.
The expected Poisson Fisher information sums
\(J_i^\mathsf{T}J_i/\lambda_i\) over sideband bins, with \(J_i\) the
derivative of \(\lambda_i\) with respect to all the parameters. Invert this
matrix for the parameter covariance \(C\), then propagate \(JCJ^\mathsf{T}\)
to all bins. Window sums use the full bin covariance, including cross-window
entries. The shape family describes the spectrum after selection.

## Intervals and diagnostics

- `sideband_counts` is null in every excluded bin even if full counts
  were supplied to the CLI. `window_masks` and `sideband_mask` index rows
  and columns in ascending mass order.
- Each candidate has `prediction`, `parameter_covariance`,
  `prediction_covariance`, `window_expected` and `window_covariance`.
  Covariances are null if Fisher inversion is unreliable. Candidate validity
  requires convergence, sufficient information and an interior solution.
  AIC is the sideband Poisson deviance plus twice the parameter count,
  including normalization. Unusable fits are skipped in the ranking.
- `window_expected_intervals` are marginal bands \(\hat{\mu}
  \exp(\pm\sigma\_{\hat\mu}/\hat\mu)\) for the fitted means based on a
  log-delta approximation. `window_observed_intervals` are central
  Poisson-gamma quantile intervals with gamma mean and variance set to
  the fitted expectation and its covariance. These plug-in approximations
  require coverage checks. They propagate only the chosen model's parameter
  covariance and omit the variation from data-dependent order selection.
  Test the whole selection procedure with pseudoexperiments. If a signal
  contributes in the sidebands, test the background intervals at nonzero
  injection even for in-family backgrounds. Cross-bin covariance allows joint summaries,
  while the reported marginal intervals have no simultaneous guarantee.
- Signed square-root deviance residuals show where fit discrepancies occur.
  The observation variance is incorporated by the Poisson deviance itself.
  Pointwise plots of these residuals are diagnostics. For a held-out
  window sum, the benchmark uses \((n-\hat\mu)/
  \sqrt{\hat\mu+\operatorname{Var}(\hat\mu)}\) descriptively and saves a
  separate count interval. In fitted bins, the model estimate depends on
  the same observations.
