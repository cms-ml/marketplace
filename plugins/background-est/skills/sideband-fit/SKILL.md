---
name: sideband-fit
description: >-
  Use when estimating a smooth background beneath a resonance from mass
  sidebands, subtracting a fitted background to extract a resonance yield,
  comparing analytic background functions, or testing sideband predictions
  with held-out windows, spurious-signal toys, signal injections and coverage.
---

# Sideband background fitting

## Overview

Fit the background using the allowed sidebands and predict its integral in
an excluded mass window. Use this for a smooth continuum with enough nearby
data to constrain its shape. A threshold, another resonance or an abrupt
selection change needs an explicit model or a different fit range.

**Initial, unvalidated skill seed.** No executable helper or environment has
been validated for this skill yet. Record assumptions, tested implementations
and failures during the student analysis before promoting it to a release.
Masses and transverse momenta in CMS MiniAOD/NanoAOD are in **GeV**.

## Define the inference task

- Fix the observable, event/candidate definition, bin edges, fit range,
  sidebands and excluded intervals before examining excluded-bin contents.
  Preserve a machine-readable mask and its provenance.
- Separate resonance-yield extraction from background prediction. A J/psi
  peak is a useful extraction example, but its observed count contains
  signal and cannot serve as the true background underneath that peak.
- State whether the desired interval covers an expected background yield,
  a future observed count, or a fitted signal yield. These are different
  targets; a prediction interval for counts also includes counting noise.
- Use integer, nonnegative counts for the Poisson model below. Multiple
  correlated candidates from one event need an explicit treatment or a
  defined single-candidate selection. Weighted/subtracted histograms are
  not Poisson counts; model their components or use a justified likelihood.

## Sideband likelihood and prediction

For a positive shape f(x; theta), define the expected shape integral in bin i:

```text
q_i(theta) = integral over bin i of e(x) * f(x; theta) dx
Q_SB(theta) = sum of q_i(theta) over fitted sideband bins
lambda_i = N_SB * q_i(theta) / Q_SB(theta)
-log L_SB = sum_SB [lambda_i - n_i * log(lambda_i)] + constraints
B_W = N_SB * Q_W(theta) / Q_SB(theta)
```

Here N_SB is the expected sideband count and e(x) is any known exposure or
acceptance factor used in the chosen model. Set e(x)=1 when f already models
the selected-event spectrum. Do not apply acceptance twice. Include separate
region exposures explicitly if predicting a different sample or luminosity.

- Integrate the model over bin edges, including variable-width bins; a
  function value at the bin center is not an expected count.
- Include zero-count sideband bins in the likelihood. They constrain the
  model through their expected counts.
- Excluded bins enter neither the likelihood nor sideband normalization,
  fit-quality selection or tuning. Their edges may define the prediction
  integral, but their observed contents remain inaccessible to fitting.
- Align masks to bin boundaries, or rebuild bins from the events. Do not
  assign a fractional observed count to a partially masked Poisson bin.
- For a simple unconstrained fit, N_SB estimates the observed sideband
  total. Retain its uncertainty when predicting B_W.

## Choose and check candidate models

Use a small, declared set of positive shapes appropriate to the mass range,
such as an exponential, positive-coefficient Bernstein polynomial, or an
exponential of a low-order polynomial in a rescaled mass coordinate. Restrict
complexity using sideband information; document parameter bounds and checks
for numerical positivity and stability throughout the excluded window.

Fit every candidate with the same data mask and integration convention.
Record convergence, boundary solutions, covariance quality and goodness of
fit. Check initialization sensitivity when the fit has competing minima.
A small sideband residual does not establish reliable interpolation.

Freeze the selection rule before testing held-out regions. If a discrete
profile is used, specify its model set and complexity penalty, and validate
the resulting intervals. A spread between fitted functions is a diagnostic,
not automatically a calibrated one-standard-deviation uncertainty.

Propagate the full fitted parameter covariance, including normalization-shape
correlations, to all predicted bins. Predictions in different bins share
parameters and are correlated. Use profile likelihood or calibrated toys
when a local Gaussian covariance is unreliable; document the interval rule.

## Validate on data and pseudoexperiments

### Data validation

Start with the official CMS Open Data J/psi sideband exercise to check input
handling, sideband scaling and yield extraction. Record its actual source
files, selections and histogram conventions rather than copying a figure.
Then extend to the existing dimuon analysis with a declared continuum range
away from known peaks, trigger turn-ons and selection discontinuities.

Reserve continuum windows that are not used to choose the candidate set,
orders, range or uncertainty prescription. Fit their surrounding sidebands
and predict the omitted counts. Compare yields and shapes with uncertainty
on both observations and predictions. Account for shared sideband data when
combining several window tests. If a validation result causes tuning, label
it development data and use a fresh validation sample or window afterward.

### Toy validation

Declare truth shapes, counts, signal shapes/masses and signal strengths
before running the final ensemble. Include alternative plausible truths
beyond the fitted family and signal tails that enter the sidebands.
Fluctuate all relevant counts and auxiliary measurements according to the
stated repeated-experiment scheme; do not silently fix the sideband total.

- **Background-only spurious signal:** fit signal plus background with a
  signed signal-yield parameter. Permit negative fitted signal while keeping
  every total expected bin count positive. A nonnegative signal constraint
  distorts this diagnostic. Report bias and the distribution of fitted
  signal relative to its uncertainty for each truth and mass.
- **Signal injection:** inject zero and nonzero signals and repeat the fit.
  Test recovery, bias and interval coverage; include sideband contamination
  when the signal model predicts it. Keep diagnostic signed fits distinct
  from any physical-boundary limit construction.
- **Background prediction:** compare predicted expected window yields with
  the known generating expectation. Test observed-count prediction coverage
  separately if that is a deliverable.
- **Pulls and coverage:** state the pull convention, including asymmetric
  errors, and the interval construction and nominal confidence level.
  Report bias, pull mean/width, interval widths and empirical coverage with
  finite-toy uncertainties, plus attempts, successful fits, failures and
  boundary solutions. Do not discard failed toys without reporting their
  effect; give success-conditioned results and a failure accounting for the
  full ensemble under a declared policy.

Distinguish **conditional coverage**, with a model/order/range fixed, from
coverage of the **complete procedure**, which reruns the declared selection
and fitting steps on each toy's allowed data. State what is conditioned on.
Choose toy statistics and acceptance criteria for the precision required;
there is no universal bias cutoff or closure percentage for every analysis.
Coverage for selected simulated truths does not prove correctness for data.

## Deliverables and plots

Save bin edges, counts, masks, exposure conventions, models and bounds,
fit diagnostics, covariance, predictions, selected rule, random seeds and
toy summaries in reproducible machine-readable outputs. Keep blinded-bin
contents out of the fitting interface. Record skill gaps in SKILLS_USED.md.

Use the existing `cms:hist` skill for hist/mplhep conventions. Show sideband
data, the excluded window, the fitted prediction with uncertainty, and
validation residuals with documented errors. Label real public data **CMS
Open Data**, and simulations/toys accurately; do not label private studies
CMS Preliminary. Identify counts versus density axes and preserve bin widths.

## Gotchas

These are risks to test in this seed, not claims of failures observed in a
completed validation run:

- Normalizing a PDF over the full range while interpreting its yield as a
  sideband yield changes the window prediction. Check the integral ratio.
- A good fit to all bins is not a blinded prediction. Refit after masking.
- Subtracting a fitted background and refitting the remainder with independent
  errors loses the correlations introduced by the background fit.
- A polynomial can become negative or unstable inside a gap despite a good
  sideband fit. Check the entire range and enforce a positive model.
- Toys drawn only from the fitted function test numerical self-consistency;
  alternate truths are needed to probe background-model bias.
- Reproducing a published curve is not a closure test when data periods,
  triggers, reconstruction or selections differ. Document comparability.

## Docs

- [CMS Open Data background-modeling workshop, including J/psi sidebands](https://cms-opendata-workshop.github.io/workshop2024-lesson-background-modeling/aio.html)
- [Official workshop notebook](https://github.com/cms-opendata-workshop/workshop2024-lesson-background-modeling/blob/main/instructors/background_modeling_lesson.ipynb)
- [CMS Combine parametric-model tutorial and discrete profiling](https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/v11.1.0/tutorial2023/parametric_exercise/)
- [Discrete profiling method paper](https://arxiv.org/abs/1408.6865)
- [CMS EXO-21-005 dimuon resonance analysis](https://cms-results.web.cern.ch/cms-results/public-results/publications/EXO-21-005/index.html): method reference using dedicated scouting data, not a standard-NanoAOD reproduction target.
