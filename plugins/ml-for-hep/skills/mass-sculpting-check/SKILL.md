---
name: mass-sculpting-check
description: >-
  Use when a classifier or tagger score is cut on in an analysis that fits or
  uses a mass (or any other spectrum): checking whether the cut changes the
  background mass shape, comparing the background before and after cuts at
  several working points, quantifying decorrelation with distance
  correlation or 1/JSD at fixed signal efficiency, deciding whether a tagger
  needs mass decorrelation, applying a DDT-style fixed-efficiency map,
  choosing between DDT, flattened or planed training, adversarial or DisCo
  training, or answering a reviewer who asks whether the tagger sculpts a
  bump into the background.
metadata:
  summary: Background mass shape before/after score cuts (chi2, JSD, distance correlation), with a DDT map and decorrelation remedies
---

# Mass sculpting check

## Overview

A classifier that learned the signal mass turns a smooth background into a
peak under the signal: the background model fails, sidebands stop
predicting the signal region, and a bump hunt can find its own tagger. Any
score that is cut on **must** be tested against the mass the analysis uses.

| Script                                       | Does                                                                      |
| -------------------------------------------- | ------------------------------------------------------------------------- |
| [scripts/sculpting.py](scripts/sculpting.py) | pass vs fail background mass shape per working point, PASS/FAIL           |
| [scripts/ddt.py](scripts/ddt.py)             | post-training remedy: a fixed-background-efficiency (DDT-style) score map |

Input: a scores table (score, label, weight, mass column, optional split),
as written by `train_bdt.py` or `train_pnet_lite.py`. Masses in **GeV**.
Remedies and their references:
[references/decorrelation-methods.md](references/decorrelation-methods.md).

## When to Use

- Every model whose score is cut on while a mass is fitted, used for
  sidebands, or used in an ABCD/transfer-factor estimate
- After decorrelating, to prove it worked
- **Not** needed when the score itself is the fit variable and the mass is
  not used; say so in the model card waiver

## Key Concepts

| Quantity            | Meaning                                                                                                        |
| ------------------- | -------------------------------------------------------------------------------------------------------------- |
| working point       | score cut keeping a fraction `--bkg-effs` of the background (test the ones the analysis uses, and one tighter) |
| `CHI2_NDF`, `P`     | χ² between the **pass** and **fail** mass histograms (independent samples; low-statistics bins merged)         |
| `JSD`, `JSD_FLOOR`  | Jensen–Shannon divergence (base 2) of pass vs fail, and the same for a random split of equal size              |
| `MAX_DEV`           | largest \|pass/expected − 1\| over the merged bins                                                             |
| `DCOR`, `PEARSON_R` | distance correlation (0 only if independent) and linear correlation of score and mass in background            |
| `R50`, `INV_JSD_50` | background rejection and 1/JSD at 50% signal efficiency: the usual benchmark pair for decorrelated taggers     |
| verdict             | `SCULPTED`: p < 0.01 **and** JSD > 2 × floor. `LOW_STAT`: < 200 effective events pass, not judged. Else `OK`   |

`STATUS=FAIL` if any working point is SCULPTED, or if all are LOW_STAT
(nothing was verified).

## Canonical Patterns

### 1. Check

```bash
set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh
<skill>/scripts/sculpting.py runs/bdt0/scores.parquet --mass obs_mjj --mass-range 1200,4000 \
    --bkg-effs 0.5,0.1,0.01 --out-dir sculpt 2> sculpt.err
# N_BKG=2873 PEARSON_R=0.0948 DCOR=0.1135 R50=239.42 INV_JSD_50=2.4
# CHI2_NDF_0.5=4.52 P_0.5=3.87e-09 JSD_0.5=0.0186 JSD_FLOOR_0.5=0.00441 MAX_DEV_0.5=0.482 VERDICT_0.5=SCULPTED
# CHI2_NDF_0.1=2.28 P_0.1=0.0113 JSD_0.1=0.0169 JSD_FLOOR_0.1=0.00746 VERDICT_0.1=OK
# CHI2_NDF_0.01=3.65 P_0.01=0.0562 VERDICT_0.01=LOW_STAT  N_SCULPTED=1 N_LOW_STAT=1 STATUS=FAIL     (exit 1)
```

Writes `sculpting.json` and `sculpting.png` (normalised mass, all vs pass
per working point, ratio). The example (the `bdt-training` test BDT, QCD
HT 1000–1500 only, 2873 test events in range) is sculpted at the loosest
cut even though its inputs are mass-scaled: m_jj correlates with the
remaining kinematics.

| Option                         | Use                                                                             |
| ------------------------------ | ------------------------------------------------------------------------------- |
| `--mass`, `--mass-range lo,hi` | mass column and the range the analysis fits                                     |
| `--bins 30`, `--log-bins`      | binning (log for wide falling spectra)                                          |
| `--score/--label/--weight`     | column names (`--label is_signal --mass fj_sdmass` for the ParticleNet outputs) |
| `--min-pass 200`               | effective events needed to judge a working point                                |
| `--dry-run`                    | N_BKG and bin edges only                                                        |

### 2. Decide

| Result                                | Action                                                                                                                      |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| all `OK`                              | record `sculpting.json` in the model card                                                                                   |
| `SCULPTED`, smooth change (slope)     | may be acceptable for a parametric fit: show the fit function still closes (`closure-tests`), then waive with that evidence |
| `SCULPTED`, peak near the signal mass | decorrelate (pattern 3 or the reference), re-check                                                                          |
| `LOW_STAT`                            | more background events in the test fold, or test a looser working point and state the limit                                 |

### 3. Quick remedy: DDT-style map

```bash
<skill>/scripts/ddt.py runs/bdt0/scores.parquet --mass obs_mjj --bkg-eff 0.1 -o scores_ddt.parquet
# N_FIT=24094 BKG_EFF=0.1 COLUMN=score_ddt THR_MIN=0.33842 THR_MAX=0.56414 OUTPUT=scores_ddt.parquet
<skill>/scripts/sculpting.py scores_ddt.parquet --score score_ddt --bkg-effs 0.1 --mass obs_mjj \
    --mass-range 1200,4000 --out-dir sculpt_ddt
# DCOR=0.1617 R50=106.41 INV_JSD_50=6.0 CHI2_NDF_0.1=1.74 P_0.1=0.0747 VERDICT_0.1=OK STATUS=PASS
```

`score_ddt = score − threshold(mass)`, with the threshold fitted on the
**training-split** background so that `score_ddt > 0` keeps 10% of the
background at every mass. One map per working point. The price is
performance: R50 fell from 239 to 106 here while 1/JSD at 50% signal
efficiency rose from 2.4 to 6.0. Re-run `model-evaluation` on the new
score. The map (`.map.json`) is part of the model: ship it.

## Gotchas

- **Comparing "pass" with "all"** double-counts the passing events and
  understates the χ². The script compares pass with fail.
- **χ² alone flags everything at high statistics, JSD alone flags noise at
  low statistics.** Hence both conditions for SCULPTED, and the random-split
  floor. Quote `MAX_DEV` for the size of the effect.
- **A map fitted on the test rows** removes the sculpting by construction
  and proves nothing. `ddt.py` fits on `--fit-split train`.
- **One DDT map does not flatten other working points** (DCOR even rose
  from 0.11 to 0.16 above while the 10% point became flat). Check the
  point you cut at.
- **Decorrelated in simulation is not decorrelated in data.** Repeat the
  check in a data control region when the background model depends on it.
- **Signal contamination.** The check uses label == 0 only. In data, use a
  region where the signal is negligible.
- **HT-binned or pT-hat-binned QCD** has a few high-weight events: one
  event can make `MAX_DEV` large. Low-statistics bins are merged
  (`--min-bin-neff 10`); look at `neff_pass` in the JSON.
- **`RuntimeWarning: invalid value encountered in divide`** from the plot
  code on empty bins is harmless (stderr only).

## Docs

- Tested on cmslpc EL9, LCG_109 (Python 3.13, numpy 2.2.6, scipy 1.16.3,
  pandas 2.2.3, matplotlib 3.10.8), 2026-11, on the `bdt-training` example
  and the ParticleNet smoke test (m_SD 40–200 GeV: 10% working point
  SCULPTED, χ²/ndf 5.4).
- J. Dolen et al., "Thinking outside the ROCs: Designing Decorrelated
  Taggers (DDT) for jet substructure", <https://arxiv.org/abs/1603.00027>
- ATLAS, "Performance of mass-decorrelated jet substructure observables for
  hadronic two-body decay tagging in ATLAS", ATL-PHYS-PUB-2018-014,
  <https://cds.cern.ch/record/2630973> (1/JSD metric)
- G. Székely, M. Rizzo, N. Bakirov, "Measuring and testing dependence by
  correlation of distances", Ann. Statist. 35 (2007) 2769,
  <https://arxiv.org/abs/0803.4101>
- CMS, "Identification of heavy, energetic, hadronically decaying particles
  using machine-learning techniques", <https://arxiv.org/abs/2004.08262>
