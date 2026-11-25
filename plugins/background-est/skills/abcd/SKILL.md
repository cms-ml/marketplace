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

[scripts/abcd.py](scripts/abcd.py) has the estimate, closure pull and
transfer-factor flatness test (`abcd.py --demo` runs a toy).

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
2. Check independence on background MC and on data outside A: plot the
   transfer factor against the other variable and fit a constant.

```python
from abcd import abcd, closure, tf_flatness

r, e, chi2, ndf = tf_flatness(x, y, ycut, xedges, w=weights)  # flat => independent
```

A linear correlation coefficient near 0 is not enough: tails drive the
estimate, so check the flatness in the region next to A.

### 2. Estimate

```python
pred, err = abcd(nB, nC, nD)                   # data counts, sqrt(N) errors
pred, err = abcd(nB, nC, nD, eB, eC, eD)       # after MC subtraction: sqrt(sumw2)
```

Subtract other backgrounds (from MC, with their uncertainties) in B, C and D
before the estimate, and add them back in A from MC.

### 3. Closure and validation

| Test                  | How                                                                           |
| --------------------- | ----------------------------------------------------------------------------- |
| MC closure            | Run the full method on background MC; compare with MC truth in A              |
| Data validation       | Shift one boundary so A', B', C', D' all sit inside the control regions       |
| Signal-injection test | Add signal MC to B, C, D at the expected strength; see the shift in `pred`    |

```python
ratio, pull = closure(obs, pred, err)
```

Systematic: if `|pull| <= 2`, use the stat precision of the test, otherwise
`|1 - ratio|`; take the larger of MC and data-validation results. If the
transfer factor has a slope, either correct with a factor `kappa =
A_MC * D_MC / (B_MC * C_MC)` and assign its uncertainty, or change variables.

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
the signal rates. Add the non-closure as an `lnN` on `bkg` in A. This card
layout is the standard Combine pattern but was **not run** for this skill.

## Gotchas

- **D is the denominator.** Put the most populated region there. `D = 0`
  raises `ValueError` in `abcd()`; merge bins or loosen the boundary.
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
