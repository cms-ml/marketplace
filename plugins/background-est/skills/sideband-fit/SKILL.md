---
name: sideband-fit
description: >-
  Use when estimating a smooth background beneath a resonance from invariant-mass
  sidebands, extracting a background-subtracted yield, predicting omitted bins of
  an unweighted spectrum, or studying spurious signal and interval coverage.
metadata:
  summary: Fit blinded mass sidebands with integrated Poisson models and validate masked predictions
---

# Sideband background fitting

Fit a smooth selected-event continuum using unmasked integer counts. Predict its
integral across an excluded window and retain the correlations from shared fit
parameters. Justify the range if there are thresholds, turn-ons or nearby peaks.

## Freeze the inference

- Record the source, event or candidate definition, units (GeV for CMS
  NanoAOD masses), edges, range, windows, candidate shapes and selection rule
  before inspecting masked counts. Bound windows by existing edges or rebin
  the original events. Use one independent count per event or justify the
  statistical treatment of multiple candidates.
- Use a Poisson likelihood for nonnegative, unweighted integer counts. For
  published densities, recover original counts using the documented bin
  widths and verify the integer normalization before fitting. Weighted or
  background-subtracted bins require a likelihood for their actual sampling
  process.
- Keep the masked counts out of the fit input using JSON `null`. Apply the
  same mask to bin normalization and model selection. Retain zero counts
  in fitted bins. Reveal held-out data only after freezing the prediction.

## Fit and inspect

Use the [histogram fitter](scripts/fit_sidebands.py) for positive first- and
second-order log-density polynomials in scaled mass or log mass. It integrates
each bin over physical mass, profiles the sideband normalization, fits both
orders and selects the best valid sideband AIC. See the
[histogram interface and statistical conventions](references/histogram-fit.md)
for a tested invocation and the complete output schema.

Check each candidate's convergence, projected score, bounds, covariance condition,
deviance and residuals. Compare both window estimates. Include the normalization
contribution and the full covariance when aggregating bins. Large shape spread,
unstable bounds or correlated residual structure warrant an independently
validated model choice or interval. Plot the fitted mean band separately from
the data errors. Fisher intervals treat the selected order as fixed and omit
uncertainty introduced by choosing the order from the same data. Measure
coverage with the selection step repeated before relying on those intervals.
Use `cms:hist` for `hist` and `mplhep` conventions.

## Validate the inference

- Rebuild the workshop J/psi mass histogram and verify its simple sideband
  subtraction. Treat the peak as an extraction example. Use continuum windows
  or pseudoexperiment truth for quantitative closure.
- Predict frozen and omitted continuum windows from their surrounding data.
  If you tune using a window, use fresh validation data afterward. A published
  spectrum can test prediction on different real counts. Verify its source
  version, units and selection and document differences from its published fit.
- In toys, fluctuate all bins, including the sidebands. Test in-family
  and plausible out-of-family truths. Run a signed signal-plus-background fit
  at zero and nonzero injection with positive total bin means, including signal
  tails in fitted regions. Signal leakage into a background-only sideband
  likelihood can shift the fitted normalization, shape and selected order.
  Check background-yield coverage at nonzero injection even when the true
  background is exactly in the fitted family. Distinguish signed diagnostics
  from physical limits.
- Report bias, pull mean/width, interval width, coverage with Monte Carlo error,
  and all attempts, failures and boundary counts. Separate coverage at fixed
  order from coverage rerunning model selection. Also state whether reported
  coverage conditions on a usable fit and how failures enter the denominator.
- Separate intervals for the underlying expected yield from those for future
  observed counts. Count intervals include Poisson noise and can overcover
  discretely. Test the Gaussian-based covariance interval with toys when its use
  matters, particularly for sparse or weakly constrained data.

## Gotchas

- The benchmark uses variable-width continuum bins. A red curve of bin-center
  density values can misrepresent bin means. Display integrated expectations
  divided by widths on an events-per-GeV plot.
- In the J/psi workshop the official CSV has all three charge categories and
  already contains combined dimuon vectors. An opposite-sign cut or reconstructing
  from imagined individual muons changes the workshop sample.
- Most of the high-mass toy intervals can behave differently from data closure
  under localized model misspecification. Sideband AIC and parameter covariance
  capture statistical effects of fitting but do not calibrate shape bias.
- On the tested LCG view, overwriting `PYTHONPATH` after sourcing the view lost
  NumPy. Import the helper using its script directory or append to the existing
  path. Set `MPLCONFIGDIR` and `XDG_CACHE_HOME` to writable scratch directories.

## Docs

- [Official CMS Open Data J/psi lesson](https://cms-opendata-workshop.github.io/workshop2024-lesson-background-modeling/aio.html)
- [Workshop notebook and CSV reference](https://github.com/cms-opendata-workshop/workshop2024-lesson-background-modeling/blob/main/instructors/background_modeling_lesson.ipynb)
- [CMS Combine parametric models and discrete profiling](https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/v11.1.0/tutorial2023/parametric_exercise/)
- [Discrete profiling method](https://arxiv.org/abs/1408.6865)
