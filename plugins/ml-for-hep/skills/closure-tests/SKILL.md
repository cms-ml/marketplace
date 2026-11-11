---
name: closure-tests
description: >-
  Use when validating a background estimate or a machine-learning-based
  method by closure in a HEP analysis: an ABCD prediction that uses a
  classifier score as one axis, checking that the two ABCD variables are
  independent, comparing a predicted with an observed distribution in
  simulation or in a validation region, computing pulls, chi2 and a
  p-value, testing that k-fold models agree with each other, turning a
  non-closure into a systematic uncertainty, or debugging an ABCD that does
  not close after cutting on a tagger.
metadata:
  summary: ABCD, predicted-vs-observed and k-fold closure with pulls, chi2 and a non-closure systematic
---

# Closure tests

## Overview

A closure test applies a method where the answer is known and compares:
the ABCD prediction with the true yield in simulation, a transfer-factor
prediction with the observed shape in a validation region, the K models of
a k-fold scheme with each other. [scripts/closure.py](scripts/closure.py)
has one subcommand per case and the same verdict logic for all.

| Subcommand | Predicted                         | Observed                        | Typical use                                              |
| ---------- | --------------------------------- | ------------------------------- | -------------------------------------------------------- |
| `abcd`     | B × C / D                         | A                               | score vs an independent variable (b tags, isolation, Δη) |
| `hist`     | histogram of `--pred-query` rows  | histogram of `--obs-query` rows | reweighting / transfer-factor / sideband shape closure   |
| `kfold`    | the nominal background efficiency | efficiency per fold model       | k-fold stability; split-key leakage                      |

Exit 0 PASS, 1 FAIL, 2 bad input. Writes `closure.json` and `closure.png`.

## When to Use

- Any data-driven estimate that involves the classifier (a cut, a category,
  a reweighting) before it is used in a signal region
- After k-fold training, before the K models are used as one
- To derive the non-closure systematic
- **Not** a substitute for unblinding rules: run it in simulation and in
  validation regions only

## Key Concepts

| Quantity                | Meaning                                                                                    |
| ----------------------- | ------------------------------------------------------------------------------------------ |
| pull                    | (observed − predicted) / √(σ_obs² + σ_pred²), per bin and inclusive                        |
| `CHI2_NDF`, `P_VALUE`   | sum of squared pulls over bins; FAIL below `--min-p` 0.01                                  |
| `PULL_MEAN`, `PULL_RMS` | mean ≠ 0: a bias; RMS ≫ 1: underestimated uncertainties or a shape effect                  |
| `NONCLOSURE`            | observed / predicted − 1 (inclusive), with `NONCLOSURE_ERR`                                |
| `NONCLOSURE_SYST`       | max(\|non-closure\|, its statistical error): the systematic to assign when the test passes |
| `CORR_XY`               | Pearson correlation of the ABCD variables in the selected rows (should be ≈ 0)             |
| `N_A` … `N_D`           | effective events per region; any below `--min-events` 10 gives `FAILED=low_stat`           |

Regions: A = x pass & y pass, B = x pass & y fail, C = x fail & y pass,
D = x fail & y fail ("pass" = value > cut).

## Canonical Patterns

```bash
set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh
C=<skill>/scripts/closure.py; S=runs/bdt0/scores.parquet
```

### 1. ABCD with the score as one axis

```bash
$C abcd $S --x score --x-cut 0.5 --y obs_ht --y-cut 1400 --query "label == 0 and split == 'test'" \
    --bin-col obs_mjj --bin-edges 1000,1500,2000,4000 --out-dir closure_abcd
# TEST=abcd N_BINS=3 CHI2_NDF=0.793 P_VALUE=0.497 PULL_INCL=0.799 PULL_RMS=0.76 MAX_ABS_PULL=1.529
# NONCLOSURE=0.1291 NONCLOSURE_ERR=0.1646 NONCLOSURE_SYST=0.1646 CORR_XY=-0.0182
# N_A=57.0 N_B=740.0 N_C=451.0 N_D=6611.0 A_PRED=23119.0 A_OBS=26104.0 FAILED=none STATUS=PASS
```

(A demonstration of the tool on QCD simulation with an arbitrary second
variable, not an analysis design.) Use test-fold background only: the
training rows are biased. `--dry-run` prints the region counts first.

### 2. Predicted vs observed shape

```bash
$C hist $S --var obs_mjj --edges 1200,1400,1600,1800,2000,2400,3000 --normalise \
    --pred-query "label == 0 and fold in [0, 1]" --obs-query "label == 0 and fold in [2, 3]" --out-dir closure_hist
# TEST=hist N_BINS=6 CHI2_NDF=0.933 P_VALUE=0.458 PULL_RMS=0.878 MAX_ABS_PULL=1.46 NONCLOSURE_SYST=0.0188 STATUS=PASS
```

`--pred-weight COL` applies a per-event transfer factor or reweighting to
the prediction rows. `--normalise` tests the shape only. Histograms made
elsewhere go in as `--json` (`edges, pred, pred_err, obs, obs_err`); this
JSON input was not run in the skill's tests.

### 3. k-fold closure

Train K models with rotated folds (`train_bdt.py --test-folds k ...`), then:

```bash
$C kfold kf/f0/scores.parquet kf/f1/scores.parquet kf/f2/scores.parquet --bkg-eff 0.1 --out-dir closure_kfold
# TEST=kfold N_BINS=3 CHI2_NDF=0.754 P_VALUE=0.52 PULL_RMS=0.868 NONCLOSURE=-0.0005 NONCLOSURE_SYST=0.0193
# THRESHOLD=0.51029 AUC_MEAN=0.9601 AUC_STD=0.00054 AUC_MIN=0.95951 AUC_MAX=0.96056 STATUS=PASS
```

One common threshold must give the same background efficiency in every
fold's held-out events. `AUC_STD` across folds is also a direct measure of
the statistical noise of the metric.

### 4. Use the result

- PASS: carry `NONCLOSURE_SYST` as the method's systematic (per bin from
  `closure.json` if the analysis is binned) and add `closure.json` to the
  model card.
- FAIL with `CORR_XY` far from 0: the ABCD variables are correlated. Choose
  another variable, bin in the variable that drives the correlation,
  decorrelate the score (`mass-sculpting-check` reference; ABCDisCo trains
  for this), or derive a correction in a validation region and close that.
- FAIL `low_stat`: the test has no power; loosen a cut for the test or add
  simulation, and say which.

## Gotchas

- **Closure in simulation is necessary, not sufficient.** Repeat in a data
  validation region near the signal region (inverted cut, sideband).
- **Closing "within large errors".** A 16% statistical error (the ABCD
  example) passes almost anything: `NONCLOSURE_SYST` then is that 16%, not
  the central value 13%. Never quote a smaller systematic than the test
  could resolve.
- **Training rows in the test.** The score is sharper on the events it was
  trained on, which changes B/D relative to A/C. Select
  `split == 'test'` or apply each k-fold model to its held-out fold.
- **Signal contamination** in B, C or D biases the prediction; the test on
  background simulation cannot see it. Quote the contamination separately.
- **Cut direction.** "Pass" means value > cut for both variables. For a
  variable where small is signal-like, negate it into a new column first.
- **Correlated bins.** The χ² treats bins as independent; the inclusive
  pull does not use the bin sum but the inclusive regions, so the two can
  disagree when B, C, D are shared across bins of the prediction.
- **Weighted simulation with few events** (HT-binned QCD): `N_A` is the
  effective count (Σw)²/Σw², not the raw one.

## Docs

- Tested on cmslpc EL9, LCG_109 (Python 3.13, numpy 2.2.6, scipy 1.16.3,
  pandas 2.2.3, matplotlib 3.10.8), 2026-11, on the `bdt-training` example
  (QCD HT 1000–1500 simulation).
- G. Kasieczka, B. Nachman, M. Schwartz, D. Shih, "ABCDisCo: Automating the
  ABCD Method with Machine Learning", <https://arxiv.org/abs/2007.14400>
- R. Barlow, "Systematic errors: facts and fictions" (when a check
  becomes a systematic), <https://arxiv.org/abs/hep-ex/0207026>
