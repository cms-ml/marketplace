# Blinded dimuon sideband fits

This validation applies the `background-est:sideband-fit` skill to the
official CMS Open Data workshop dimuons and the frozen 2016G/H
high-mass Open Data snapshot. It then tests the inference using separate
Poisson pseudoexperiments. The [specification](specification.md) and
[frozen configuration](frozen.json) fix the range, exclusions, candidates,
selection and toy truths. The student analysis and independent Astra review
are packaged together in this branch:

```text
validation/sideband-fit/
  plots/                 Sol's Open Data fits and toy diagnostics
  summary.json           Student results
  cms-comparison/        Astra's independent CMS/HEPData review
    COMPARISON.md        Findings and comparability matrix
    comparison.json      Published-spectrum and independent-fit checks
    ensembles.json       Independent toy results
    published_*.pdf/png  CMS spectrum comparison plots
```

Read the [independent CMS/HEPData comparison](cms-comparison/COMPARISON.md)
alongside the student results below. It preserves the reviewed student
commit and the frozen validation plan, including the uncertainty-coverage
limitations found by the independent tests.

## Workshop J/psi extraction

The notebook uses a public CSV linked from Matt Bellis's educational
repository. Each row contains the energy and momentum of a combined
dimuon plus its charge category. The lesson uses all charge categories.
The source links and byte checksums are in the [input manifest](input_manifest.json).
The exact original strict-window calculation gives 2,839 left, 10,098
peak and 1,866 right entries, for 2,352.5 expected background and 7,745.5
subtracted events. This reproduces the lesson's result. The CSV does not
provide the original trigger, certification, and integrated luminosity for
this particular derived sample. See the [CMS Open Data workshop
lesson](https://cms-opendata-workshop.github.io/workshop2024-lesson-background-modeling/aio.html)
and [source notebook](https://github.com/cms-opendata-workshop/workshop2024-lesson-background-modeling/blob/main/instructors/background_modeling_lesson.ipynb).

The nominal order-two fit predicts **2,627.5 ± 75.0** continuum events in
3.0–3.2 GeV. The subtraction is **7,470.5 ± 125.4** events, combining
the independent peak count and fitted mean errors. Order one predicts
2,306.5 ± 34.2 in the same window. This spread and the residual just below
3.0 GeV make the extraction sensitive to the assumed shape and possible
resonance tails. The errors here are statistical. This peak cannot
establish the true background under the resonance.

[PDF](plots/jpsi.pdf) · [PNG](plots/jpsi.png)

## Masked high-mass continuum

The validated raw count and edge vectors from the snapshot's
`results/templates.json` exactly match the corresponding vectors in
`results/bkg_fit.json`. The fit consumes only the edges and unmasked
counts. The source analysis selects opposing-charge high-pT isolated
muons with TuneP momentum, muon trigger paths and event-quality filters.
The snapshot reports 16.3927 fb⁻¹ at 13 TeV. The benchmark does not use its
previous full-range background fit.

| Omitted window [GeV] | Observed | Expected ± stat. (AIC) | Nominal 68% observed-count interval |
| -------------------- | -------: | ---------------------: | ----------------------------------- |
| 494.26–557.19        |      587 |           599.5 ± 11.9 | [572, 627]                          |
| 899.84–1014.39       |       69 |             56.6 ± 2.8 | [49, 65]                            |

The total count in the second window exceeds the upper endpoint by four.
The descriptive window residuals are −0.46 and +1.54. The order-two fit has
sideband deviance 95.2 for 135 degrees of freedom. The fitted window totals
have covariance 9.49 events² and correlation 0.29. The figure includes
zero-event bins as open down triangles at their Garwood upper endpoints.
In the workshop figure, triangles at the residual panel limit show residuals
outside the displayed range. Both figures shade excluded windows and show
a marginal 68% fitted-mean band. The full bin covariance is saved by the
runner and CLI.

[PDF](plots/continuum.pdf) · [PNG](plots/continuum.png)

## Pseudoexperiments

The toy repetitions use fixed sideband-derived truth parameters. Each
of four background shapes and two signal strengths has 600 independent
draws. Both procedures share the same draw within a scenario. The
signal has mass 524.8 GeV, width 13.1 GeV and 1.68% of its template in the
fitted sidebands. After choosing the order from the sidebands, the
signed signal fit uses the full spectrum, including the signal tail
expectation in the sidebands. It profiles over signed signal yield
subject to positivity of every expected bin. The numerical lower bound
keeps the total expectation above `1e-10` times its background term.
The log normalization may shift by up to two units from the sideband
solution, and the shape bounds are the same as the sideband bounds.
The fitted uncertainty is the joint Poisson Fisher error.

The local modulation is a stress test with a broad positive deviation
centered in the first masked window. It is out of the fitted family and
does not model a verified feature of the real data. It produced roughly
−29 events of first-window background bias and +25 events of signed
spurious signal under AIC selection. Nominal 68% expected-mean coverage
dropped to roughly 3–5% in that window, and signed signal coverage
dropped to roughly 39–45%. On the linear control the fixed-order
coverage is near nominal. On quadratic truth the linear model has
negligible window-mean coverage, while AIC selection recovers most of the
coverage. These checks show the effect of shape assumptions on inference.
They do not establish calibrated coverage across unknown real spectra.

[Summary](summary.json) contains attempted, valid, failed, retried and
boundary fit counts, fitted order frequencies, signed estimates,
bias, pull location and width, interval widths and coverages. The
fixed-order estimates condition on the declared model. The AIC toys
repeat the full selection on every draw. Each has an additional
success-conditioned calculation and one treating failures as uncovered.
Monte Carlo errors use the binomial plug-in standard error and a Wilson
one-standard-deviation interval. All 4,800 draws returned usable
sideband and signal fits for both procedures after numerical retries,
with no boundary solutions. The maximum standard error at this
ensemble size is 2.04 percentage points. Expected background intervals
are log-delta, and observed-count intervals are Poisson-gamma. The latter
are only scored at zero injection because the injected observation also
includes signal. The pull figures use signed residuals divided by fitted
standard deviations. The gray dotted curve is the standard Gaussian.

[Pulls PDF](plots/toy_pulls.pdf) · [Pulls PNG](plots/toy_pulls.png)

## Reproduce

Run from the marketplace root with NumPy, SciPy, hist, Matplotlib and
mplhep. The tested cmslpc environment was LCG_109, Python 3.13.11, NumPy
2.2.6, SciPy 1.16.3, hist 2.9.0, Matplotlib 3.10.8 and mplhep 0.4.1.

Place the two public workshop files and the dimuon snapshot under
the paths in the [input manifest](input_manifest.json). In a deployed
run these files already exist under its `inputs/` directory. Set
`SIDEBAND_INPUTS` to that directory. The runner verifies the declared
SHA-256 values. Keep the raw files and temporary covariance and pull
arrays in scratch space.

```bash
sideband_output=$(mktemp -d)
mkdir -p "$sideband_output/cache/matplotlib"
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
export XDG_CACHE_HOME="$sideband_output/cache"
export MPLCONFIGDIR="$sideband_output/cache/matplotlib"
python3 validation/sideband-fit/run_validation.py \
  --inputs "$SIDEBAND_INPUTS" --output "$sideband_output/smoke" --smoke
python3 validation/sideband-fit/run_validation.py \
  --inputs "$SIDEBAND_INPUTS" --output "$sideband_output/final" --workers 4
python3 validation/sideband-fit/check_results.py "$sideband_output/final/summary.json"
```

The smoke run uses a distinct seed and 12 toys per scenario. The final
command uses four single-threaded worker processes. Each scenario has its
own deterministic seed stream. The check
targets the final ensemble. The committed summary also passes
`python3 validation/sideband-fit/check_results.py`. The runner writes
full per-bin covariance in `jpsi_fit.json` and `continuum_fit.json`,
and exact numerical pulls in `toy_pulls.json`. See the
[generic histogram interface](../../plugins/background-est/skills/sideband-fit/references/histogram-fit.md)
to run on a published spectrum using a verified integer histogram.

Check both sets of committed results from the repository root:

```bash
python3 validation/sideband-fit/check_results.py
python3 validation/sideband-fit/cms-comparison/check_results.py
```
