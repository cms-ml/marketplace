---
name: model-evaluation
description: >-
  Use when evaluating, comparing or signing off a trained classifier in a HEP
  analysis: ROC curve and AUC with uncertainty, signal efficiency at fixed
  background efficiency, a working-point table with thresholds, overtraining
  (train vs test score distributions), calibration of the score,
  performance per pT, mass or era category, data/MC agreement of the score
  and the inputs in a control region, writing a model card, or deciding
  whether a model is ready for the analysis and which checks are still
  missing.
metadata:
  summary: Model-agnostic evaluation from a scores table (ROC, working points, overtraining, calibration, data/MC) and the model-card gate
---

# Model evaluation

## Overview

Evaluation works on a **scores table**, not on the model, so it is the same
for a BDT, a DNN or a graph network: a Parquet file with a score, a label
(1/0, <0 for data), and optionally weight, split and observers.
`train_bdt.py` writes it as `scores.parquet`; `train_pnet_lite.py` as
`scores_test.parquet` / `scores_train.parquet` (label column `is_signal`).

| Script                                         | Does                                                                    |
| ---------------------------------------------- | ----------------------------------------------------------------------- |
| [scripts/evaluate.py](scripts/evaluate.py)     | metrics, working points, overtraining, calibration, categories, data/MC |
| [scripts/model_card.py](scripts/model_card.py) | collects every check JSON, writes `MODEL_CARD.md`, prints `READY=0/1`   |

Exit codes for both: 0 pass, 1 a check failed (outputs still written), 2 bad
input.

## When to Use

- After every training, before quoting any performance number
- To produce the working-point thresholds the analysis will cut on
- To gate a model: `model_card.py` is the single place that says "done"

## Key Concepts

| Quantity                 | Why                                                                                                |
| ------------------------ | -------------------------------------------------------------------------------------------------- |
| `SIG_EFF_AT_BKG_<eff>`   | the number analyses compare; AUC averages over regions nobody uses                                 |
| `AUC_ERR`                | bootstrap error of the test AUC: differences below ~2× this are noise (scan decisions use it)      |
| `n_bkg_pass`, `low_stat` | a working point with < 10 background test events above the cut is not measured                     |
| `OVERTRAINED`            | AUC_TRAIN − AUC_TEST > 0.02, or KS p < 0.01 with gap > 0.01 (same rule as `train_bdt.py`)          |
| `ECE`                    | calibration error with equal class weights; matters only if the score is used as a probability     |
| `AUC_CAT_MIN`            | worst category: a tagger that works on average can fail at high pT or in one era                   |
| `DATA_MC_CHI2_NDF_MAX`   | shape χ²/ndf, data vs weighted MC, for the score and `--compare` columns (statistical errors only) |

## Canonical Patterns

### 1. Evaluate

```bash
set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh
<skill>/scripts/evaluate.py runs/bdt0/scores.parquet --out-dir runs/bdt0/eval \
    --category obs_j1_pt:0,800,1000,1e9 2> eval.err
# N_TEST_SIG=21172 N_TEST_BKG=7859 AUC_TEST=0.96203 AUC_ERR=0.00095 AUC_TRAIN=0.96893 AUC_GAP=0.0069
# KS_P_SIG=0.0127 KS_P_BKG=0.0348 OVERTRAINED=0 SIG_EFF_AT_BKG_0.1=0.8941 THR_AT_BKG_0.1=0.50381
# SIG_EFF_AT_BKG_0.01=0.5905 THR_AT_BKG_0.01=0.94171 SIG_EFF_AT_BKG_0.001=0.2322 ECE=0.0049
# AUC_CAT_MIN=0.95124 FAILED=none STATUS=PASS
```

Writes `evaluation.json` (summary, working points with errors and
`low_stat`, calibration bins, categories) and `roc.png`, `scores.png`,
`calibration.png`. Read the JSON, not the plots.

| Option                               | Use                                                            |
| ------------------------------------ | -------------------------------------------------------------- |
| `--train other.parquet`              | training-sample scores in a separate file                      |
| `--score/--label/--weight/--split`   | column names (`--label is_signal` for the ParticleNet outputs) |
| `--bkg-effs 0.1,0.01,0.001`          | working points                                                 |
| `--category COL:e0,e1,...`           | per-bin AUC and signal efficiency                              |
| `--data-mc --compare obs_mjj,obs_ht` | data (label < 0) vs MC shapes; needs data rows in the table    |
| `--no-plots`, `--dry-run`            | faster; sizes only                                             |

### 2. Data/MC agreement

Score the data and MC of a **signal-depleted control region** with the same
model, put them in one table (data rows `label = -1`), and run
`--data-mc --compare <columns>`. The columns must be in the scores table:
`scores.parquet` keeps the `obs_*` columns and the row order of the feature
table, so add inputs with `pd.concat([scores, table[features]], axis=1)`
(a missing column is exit 2, `KeyError`). A χ²/ndf above 3 for an input means the
simulation mismodels it: drop the input, correct it, or cover it with a
systematic. A χ²/ndf above 3 for the score alone means the mismodelling is
in a correlation. The test uses statistical errors only, so with very large
samples small systematic shifts fail it: then compare with the systematic
band in the analysis framework and waive this check with that evidence.
Tested only with pseudo-data (one QCD fold relabelled as data:
`DATA_MC_CHI2_NDF_MAX=1.28 DATA_MC_WORST=score STATUS=PASS`), not on
collision data.

### 3. Gate and document

```bash
<skill>/scripts/model_card.py --name zprime_bdt --out MODEL_CARD.md \
    --check table=checks.json --check training=runs/bdt0/metrics.json \
    --check evaluation=runs/bdt0/eval/evaluation.json \
    --check sculpting=sculpt/sculpting.json --check closure=closure/closure.json \
    --field "Task=Z'(bb) vs QCD, per event" --field "Intended use=cut at 10% background efficiency"
# with only the first three: N_CHECKS=3 N_PASS=3 N_FAIL=0 N_MISSING=2 MISSING=sculpting,closure READY=0   (exit 1)
```

`READY=1` needs every `--require` name (default
`table,training,evaluation,sculpting,closure`) present and PASS. A check
that cannot pass for a documented reason is waived explicitly:
`--waive sculpting="score is used only in a mass-binned fit; closure in
closure/closure.json covers the shape"`. Waivers are printed at the top of
the card. Never drop a name from `--require` to get `READY=1`.

## Gotchas

- **Quoting validation numbers as the result.** Early stopping and scans
  selected on the validation folds, so validation metrics are biased up.
  `evaluate.py` uses `split == "test"` only.
- **`SIG_EFF_AT_BKG_0.001` from a handful of events.** With 7859 test
  background events the 0.1% point has 7 events above the cut: check
  `low_stat` in `evaluation.json` before quoting it.
- **`ValueError: x is neither increasing nor decreasing`** from
  `sklearn.metrics.roc_auc_score(..., sample_weight=w)` with negative
  weights (scikit-learn 1.8.0): the weighted ROC is not monotonic. The
  scripts integrate the weighted ROC themselves.
- **ECE is prior-dependent.** A model trained with balanced classes outputs
  P(signal) for a 50/50 mixture, not for the analysis yields. The ParticleNet
  smoke test gave ECE = 0.09 with an AUC of 0.955: poorly calibrated, still
  a valid discriminant.
- **A good AUC with a bad category.** Always pass `--category` for the
  variable the analysis bins in.
- **Plots are for humans.** An agent should act on `STATUS`, `FAILED` and
  the JSON.

## Docs

- Tested on cmslpc EL9, LCG_109 (Python 3.13, numpy 2.2.6, scipy 1.16.3,
  pandas 2.2.3, matplotlib 3.10.8) on the `bdt-training` and
  `particlenet-training` example outputs, 2026-11.
- M. Mitchell et al., "Model Cards for Model Reporting", <https://arxiv.org/abs/1810.03993>
- C. Guo et al., "On Calibration of Modern Neural Networks", <https://arxiv.org/abs/1706.04599>
- scikit-learn model evaluation: <https://scikit-learn.org/stable/modules/model_evaluation.html>
