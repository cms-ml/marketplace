---
name: abcd
description: >-
  Use when estimating a background from data with the ABCD (matrix, two-variable
  sideband) method in a CMS analysis: choosing the two discriminating variables
  and region boundaries, predicting the signal-region yield or shape from three
  control regions, propagating statistical uncertainties, testing independence
  of the variables and closure in simulation or validation regions, assigning a
  non-closure systematic, handling signal contamination or other backgrounds in
  the control regions, writing the ABCD as a simultaneous likelihood fit with
  Combine rateParam, or debugging a prediction that is negative, does not
  close, or has a huge uncertainty from a nearly empty region.
metadata:
  summary: ABCD background estimate (independence and closure tests, uncertainties, Combine rateParam version)
---

# ABCD background estimation

## Overview

Two variables `x` and `y` that are **independent for the background** split
the events into four regions. Three are background-dominated and predict the
fourth:

```text
        fail x   pass x
pass y    B        A  (signal region)        N_A = N_B * N_C / N_D
fail y    D        C
```

[scripts/abcd.py](scripts/abcd.py) has the estimate (inclusive and binned),
closure pull, transfer-factor flatness test, non-closure systematic and a chi2
with correlated systematics (`abcd.py --demo` runs a toy).

## When to Use

- A background (typically QCD multijet, or fakes) that simulation models
  poorly but that has two uncorrelated handles, e.g. isolation and MET, a
  tagger score and a mass, displaced-vertex counts in two detectors
- **Not** when the handles are correlated by construction (both built from the
  same jet constituents) unless one is explicitly decorrelated
- For a smooth mass spectrum in a pass/fail tagger split, use `rhalphabet`

## Key Concepts

| Term            | Meaning                                                                       |
| --------------- | ----------------------------------------------------------------------------- |
| Transfer factor | `N_B / N_D` (or `N_C / N_D`); must not depend on the other variable           |
| Closure         | `N_A(observed) / N_A(predicted)` where A is known: MC, or a validation region |
| Non-closure     | Deviation of closure from 1 beyond its stat error; taken as a systematic      |
| Contamination   | Signal or other backgrounds in B, C, D; biases the prediction upward          |
| Binned ABCD     | Shape of the fit variable from C, scaled by `B/D` (inclusive or per bin)      |

## Canonical Patterns

### 1. Choose variables and boundaries blind

1. Keep A blinded. Pick boundaries from signal MC efficiency and CR
   statistics, never from data in A.
2. Shortlist several candidate pairs and rank them on background MC by
   `kappa = A*D/(B*C)` (1 = independent) and its dependence on the fit
   variable; pick by these numbers, not by category. Include pairs of two
   event-level kinematic variables (rapidity or angular separation, momentum
   or mass balance between objects), event x object pairs (tagger,
   substructure, isolation), and object x object pairs. Watch for: two
   substructure variables, of one jet or of two jets in an event, correlated
   through jet mass and pT; and any axis that is a function of the fit variable
   (a substructure cut sculpts a mass spectrum), which makes the TF depend on it.
   A cut on such a variable is better placed in the preselection, applied to
   all four regions.
3. Check independence on background MC and on data outside A: plot the
   transfer factor against the other variable and fit a constant.

```python
from abcd import abcd, abcd_binned, tf_fit_ftest, closure, tf_flatness, nonclosure_syst, syst_cov, chi2_cov

r, e, chi2, ndf = tf_flatness(x, y, ycut, xedges, w=weights)  # weighted; flat => independent
```

A linear correlation coefficient near 0 is not enough: tails drive the
estimate, so check the flatness in the region next to A, and against the fit
variable too when the ABCD is binned in it.

### 2. Estimate

```python
pred, err = abcd(nB, nC, nD)                   # data counts, sqrt(N) errors
pred, err = abcd(nB, nC, nD, eB, eC, eD)       # after MC subtraction: sqrt(sumw2)
```

Subtract other backgrounds (from MC, with their uncertainties) in B, C and D
before the estimate, and add them back in A from MC.

**Binned in a fit variable `m`** (a mass spectrum in A): the shape comes from one
side region (C by default; `shape="B"` takes it from B), the normalisation from
the transfer factor measured with the other side region and D, e.g.
`TF(m) = B(m)/D(m)` applied to C.

```python
pred, cov = abcd_binned(B_m, C_m, D_m, eB, eC, eD, tf="inclusive")  # or "perbin"
order, coeffs, tf_cov, chi2, ndf = tf_fit_ftest(m_centres, tf_m, tf_err)
```

Go down this table in order and record why each step was or was not taken:

| TF(m) behaviour (in data and MC) | Use                                                                                        |
| -------------------------------- | ------------------------------------------------------------------------------------------ |
| Flat (`tf_flatness` p > 0.05)    | Inclusive TF: smallest error, sparse or empty bins harmless                                |
| Smooth trend                     | `tf_fit_ftest` (polynomial; a sigmoid if it saturates): order by F-test, band = shape syst |
| No order fits (chi2 p < 0.05)    | The variables are correlated in `m`: change variables, or per-bin TF as a last resort      |

The fit-function band is a shape systematic; the C statistics are the other
per-bin term. Check that the cuts defining the regions do not sculpt `m`
differently in A and C (compare the C and A shapes in MC): the TF corrects the
normalisation, not a shape difference between A and C.

### 3. Closure and validation

| Test                  | How                                                                        |
| --------------------- | -------------------------------------------------------------------------- |
| MC closure            | Run the full method on background MC; compare with MC truth in A           |
| MC validation         | The same shifted-boundary regions as below, in background MC               |
| Data validation       | Shift one boundary so A', B', C', D' all sit inside the control regions    |
| Signal-injection test | Add signal MC to B, C, D at the expected strength; see the shift in `pred` |

Build the main validation regions by **shifting an ABCD boundary inside the
control regions**. A sideband made by inverting a preselection cut (pT, mass
balance, lepton veto) tests a sample with a different composition: a pass there
does not validate A, but a **failure there is evidence** and enters the
systematic like any other test.

```python
ratio, pull = closure(obs, pred, err)
syst = nonclosure_syst([(r, p, rel_stat) for every MC and data test])
```

**Non-closure systematic.** Every test you ran counts: MC closure in A, MC and
data validation regions, inverted-cut sidebands, and the independence test in
data (a TF that is flat in MC but slopes in data: express its effect on A as a
ratio). Each contributes its stat precision if `|pull| <= 2`, otherwise
`|1 - ratio|`; the systematic is the largest, applied as a yield term fully
correlated across bins. A test you ran and then left out of the systematic
must be justified in the report; a 3 sigma failure cannot be left out. For a binned estimate also
compare shapes after normalising each test: if the shape chi2 fails, add an
uncorrelated per-bin term from the residuals (`syst_cov(pred, rel_corr,
rel_shape)`). Never take a systematic from the very test it is meant to cover.
If the transfer factor has a slope, either correct with `kappa = A_MC * D_MC /
(B_MC * C_MC)` and assign its uncertainty, or change variables.

**Unblinding A.** Compare observed and predicted with the full covariance
(prediction stat, correlated TF error and systematics, data stat):

```python
chi2, ndf, pulls = chi2_cov(obs_A, pred_A, cov + syst_cov(pred_A, syst))
```

Quote this chi2 and the largest local pull. Adding a correlated systematic in
quadrature bin by bin understates the chi2.

### 4. Likelihood version (low counts, signal contamination)

When any region has fewer than about 10 events, or signal leaks into the
control regions, fit all four regions together. One Combine channel per
region, background rate 1, and the constraint in a formula:

```text
bin          A     A     B     B     C     C     D     D
process      sig   bkg   sig   bkg   sig   bkg   sig   bkg
process      0     1     0     1     0     1     0     1
rate         5.1   1     0.4   1     0.3   1     0.02  1
---------------------------------------------------------
nB    rateParam B bkg 120 [0,1000]
nC    rateParam C bkg 80  [0,1000]
nD    rateParam D bkg 400 [0,5000]
nA    rateParam A bkg (@0*@1/@2) nB,nC,nD
```

The fit gives Poisson uncertainties and accounts for signal in B, C, D through
the signal rates. Add the non-closure yield term as an `lnN` on `bkg` in A
(a per-bin shape term needs one nuisance per bin or a shape template). This card
layout is the standard Combine pattern but was **not run** for this skill.

## Gotchas

- **D is the denominator.** Put the most populated region there. `D = 0`
  raises `ValueError` in `abcd()` and in `abcd_binned(tf="perbin")`; use the
  inclusive TF, merge bins or loosen the boundary.
- **Parquet from the LCG views:** pyarrow may lack zstd; write with
  `compression="snappy"`.
- **Negative yields after MC subtraction** mean the subtracted background is
  mismodelled or dominant: that region is not a control region for this
  process.
- **`sqrt(N)` is wrong for weighted events.** Pass `sqrt(sumw2)`.
- **Gaussian propagation fails below ~10 events.** Use pattern 4.
- **Selections can create correlation.** A trigger or preselection that cuts
  on a function of both variables (e.g. HT and a jet pT) correlates them even
  if they are independent before it. Test after the full selection.
- **MC closes, data does not** (or the reverse): the correlation depends on
  composition. Run closure per background component and in data validation
  regions.
- **Per-bin `B/D` in binned ABCD** inflates the uncertainty in sparse bins. Use
  the inclusive ratio when the flatness test passes.
- **Unblind in order:** validation regions first, A last.

## Docs

- Combine `rateParam` and ABCD-style constraints:
  <https://cms-analysis.github.io/HiggsAnalysisCombinedLimit/>
