---
name: bdt-training
description: >-
  Use when training a boosted decision tree or other gradient-boosted
  classifier on flat per-event or per-object features in a HEP analysis:
  choosing between XGBoost, LightGBM and scikit-learn
  HistGradientBoosting, handling event weights and negative generator
  weights, class imbalance, an event-number train/validation/test split,
  early stopping, checking overtraining with a train-vs-test KS test,
  ranking features by gain or SHAP, saving the model as JSON or ONNX, or
  debugging "Weights must be positive values", an ONNX model whose scores
  differ from the native ones, or a venv that imports the wrong package
  version on top of an LCG view.
metadata:
  summary: Gradient-boosted classifiers on flat features with weights, early stopping, overtraining test, SHAP and ONNX
---

# BDT training

## Overview

[scripts/train_bdt.py](scripts/train_bdt.py) trains a gradient-boosted
binary classifier on the table made by the `hep-ml-data-prep` skill and
runs the standard checks in the same call. One command, one run directory,
one `STATUS`.

```bash
set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh
<skill>/scripts/train_bdt.py <work>/table.parquet --out-dir <work>/runs/bdt0 --threads 4 2> bdt0.err
# BACKEND=xgboost N_TRAIN=87714 N_VAL=29200 N_TEST=29031 N_FEATURES=11 BEST_ITER=337
# AUC_TRAIN=0.96893 AUC_VAL=0.95939 AUC_TEST=0.96203 AUC_GAP=0.0069 KS_P_SIG=0.0127 KS_P_BKG=0.0348
# OVERTRAINED=0 TOP_FEATURES=j1_btag,j2_btag,j2_mass_over_pt,j1_mass_over_pt,j2_pt_over_mjj
# SECONDS=5.8 OUT_DIR=runs/bdt0 STATUS=PASS
```

(Z′(2 TeV) → bb̄ vs QCD HT 1000–1500, 146k Open Data events: a test of the
tool, not a physics result.) Exit 0 PASS, 1 FAIL (outputs still written), 2
bad input or missing package.

## When to Use

- Any classifier on ≲ 100 flat features: the default first model, and the
  baseline before any neural network
- **Not** for jet constituents or other variable-length inputs
  (`particlenet-training`)

## Key Concepts

| Backend (`--backend`) | Use when                                                        | Model file   | In LCG_109              |
| --------------------- | --------------------------------------------------------------- | ------------ | ----------------------- |
| `xgboost` (default)   | default; JSON model, built-in SHAP, PROGRESS lines for pruning  | `model.json` | yes (2.1.3)             |
| `hgb`                 | no extra dependency beyond scikit-learn; quick cross-check      | `model.pkl`  | yes (sklearn 1.8.0)     |
| `lightgbm`            | very large tables or many features (fastest histogram training) | `model.txt`  | **no**: venv, pattern 3 |

The three gave the same test AUC within 0.0004 on the example (0.96203,
0.96167, 0.96184), so the choice is practical, not physics.

| Step            | What the script does                                                                                       |
| --------------- | ---------------------------------------------------------------------------------------------------------- |
| Split           | `--train-folds 0,1,2 --val-folds 3 --test-folds 4` of `fold = event % 5`; overlap is an error              |
| Training weight | `--neg-weights abs` (default) \| `zero` \| `drop`, classes balanced to equal sums (`--no-balance`), mean 1 |
| Metrics         | always with the original **signed** weights                                                                |
| Early stopping  | on validation logloss, `--early-stopping 30`; the saved model is cut at the best iteration                 |
| Overtraining    | `OVERTRAINED=1` if AUC_TRAIN − AUC_TEST > 0.02, or KS p < 0.01 (either class) and the gap > 0.01           |
| Importance      | total gain, and mean \|SHAP\| on ≤ 5000 test rows from the library's own TreeSHAP (`pred_contribs`)        |

Defaults that work as a baseline: `--learning-rate 0.1 --max-depth 4
--subsample 0.8 --colsample-bytree 0.8 --n-estimators 1000` with early
stopping. Tune with the `hyperparam-scan` skill only after this baseline.

## Canonical Patterns

### 1. Dry run, baseline, rerun

```bash
T=<skill>/scripts/train_bdt.py
$T table.parquet --out-dir runs/bdt0 --dry-run        # N_TRAIN=87714 N_VAL=29200 N_TEST=29031 FEATURES=...
$T table.parquet --out-dir runs/bdt0                  # train + checks
$T table.parquet --out-dir runs/bdt0 --skip-existing  # same arguments: returns the stored result
```

Outputs in `runs/bdt0/`: `model.json`, `scores.parquet` (score, split,
label, weight, fold, event, sample, `obs_*` for **every** row, the input of
`model-evaluation`, `mass-sculpting-check` and `closure-tests`),
`metrics.json` (summary, parameters, features, importance, SHAP, KS
distances, versions, seed, command). Each run appends a line to
`runs/../runs.jsonl`, the offline experiment log.

### 2. Options that matter

| Option                                     | Use                                                             |
| ------------------------------------------ | --------------------------------------------------------------- |
| `--features a,b,c`                         | explicit inputs (default: all non-reserved, non-`obs_` columns) |
| `--params-json '{"max_depth": 3}'`         | override hyperparameters (used by scans)                        |
| `--progress-every 25`                      | `PROGRESS step=N value=<val AUC>` lines for pruning (xgboost)   |
| `--neg-weights drop`                       | cross-check when many weights are negative                      |
| `--train-folds/--val-folds/--test-folds`   | rotate folds for k-fold models                                  |
| `--onnx`                                   | also write `model.onnx` and compare it with the native scores   |
| `--min-auc`, `--max-auc-gap`, `--min-ks-p` | the pass criteria (change only with a physics reason)           |

### 3. LightGBM and ONNX converters (not in LCG_109)

```bash
python3 -m venv --system-site-packages <scratch>/venv-extras && . <scratch>/venv-extras/bin/activate
pip install lightgbm onnxmltools skl2onnx       # tested: lightgbm 4.7.0, onnxmltools 1.16.0, skl2onnx 1.20.0
export PYTHONPATH=$VIRTUAL_ENV/lib/python3.13/site-packages:$PYTHONPATH     # required, see Gotchas
$T table.parquet --out-dir runs/lgb0 --backend lightgbm --onnx
```

| Backend    | Converter                      | Tested ONNX vs native (5000 test rows)                 |
| ---------- | ------------------------------ | ------------------------------------------------------ |
| `xgboost`  | `onnxmltools.convert_xgboost`  | max diff 3.0e-07                                       |
| `hgb`      | `skl2onnx.to_onnx`             | max diff 1.6e-07                                       |
| `lightgbm` | `onnxmltools.convert_lightgbm` | 5 rows differ by up to 0.012, median 2.7e-08 (Gotchas) |

Without the converters, `model.json` (xgboost) is the portable artefact:
`xgboost.Booster(model_file=...)` reads it in any later version.

### 4. Read the result

- `STATUS=FAIL`, `OVERTRAINED=1`: lower `--max-depth`, raise
  `--min-child-weight` or `--reg-lambda`, lower `--subsample`, or get more
  events. Do not loosen the threshold.
- `AUC_TEST` < 0.6: the features carry no information or the labels are
  wrong; go back to `hep-ml-data-prep`.
- `AUC_TEST` > 0.99: suspect leakage; rerun `check_table.py`, look at
  `TOP_FEATURES`.
- Then: `model-evaluation`, `mass-sculpting-check`, `closure-tests`.

## Gotchas

- **`XGBoostError: ... Check failed: valid: Weights must be positive values.`**
  XGBoost 2.1.3 rejects negative sample weights. scikit-learn HGB and
  LightGBM accept them silently, which is worse: negative weights make the
  loss non-convex. The script always trains on |w| (or `zero`/`drop`) and
  evaluates with signed weights.
- **ONNX scores differ by a few percent** (`ONNX_MAX_ABS_DIFF=0.0737` in the
  first test): the converter exported all trees while the native prediction
  stopped at the best iteration. The script now cuts the booster at the best
  iteration before saving and converting. Do the same in your own code
  (`booster[:best_iteration + 1]`, `save_model(num_iteration=...)`).
- **A few LightGBM rows differ by O(0.01) in ONNX**: ONNX tree ensembles
  store float32 thresholds, LightGBM uses doubles, so a value on a split
  boundary can take the other branch. The check therefore fails only when
  more than 0.5% of rows differ by > 1e-4 (`ONNX_FRAC_DIFF`).
- **`AttributeError: module 'narwhals.dependencies' has no attribute
'is_into_dataframe'`** when importing lightgbm in a venv on LCG_109: the
  LCG view puts its own site-packages on `PYTHONPATH`, ahead of the venv, so
  the old LCG `narwhals` shadows the one pip installed. Prepend the venv's
  site-packages to `PYTHONPATH` (pattern 3).
- **Training crawls on a shared node** (a 6 s job took minutes when the load
  was 20 on 8 cores): OpenMP threads spin when oversubscribed. Use
  `--threads 2` (the script also sets `OMP_NUM_THREADS`), or go to Condor.
- **`hgb` early-stops on its own internal 20% split** of the training folds,
  not on the validation folds; `subsample`, `colsample_bytree` and `gamma`
  do not apply to it, and it has no SHAP output (`TOP_FEATURES=n/a`).
- **KS p-values shrink with statistics.** With 10⁵ events a harmless 0.5%
  train/test difference gives p < 0.01, so the rule combines the KS test
  with the AUC gap. Quote both.
- **`model.pkl` is tied to the scikit-learn version** that wrote it (stored
  inside the file). Prefer xgboost JSON or ONNX for anything long-lived.

## Docs

- Tested on cmslpc EL9, LCG_109 (Python 3.13, xgboost 2.1.3, scikit-learn
  1.8.0, onnx 1.16.0, onnxruntime 1.23.2, scipy 1.16.3) plus a venv with
  lightgbm 4.7.0, onnxmltools 1.16.0, skl2onnx 1.20.0; 2026-11.
- XGBoost: <https://xgboost.readthedocs.io/> (T. Chen, C. Guestrin,
  <https://arxiv.org/abs/1603.02754>)
- LightGBM: <https://lightgbm.readthedocs.io/>
- scikit-learn HistGradientBoosting:
  <https://scikit-learn.org/stable/modules/ensemble.html#histogram-based-gradient-boosting>
- TreeSHAP: S. Lundberg et al., <https://arxiv.org/abs/1802.03888>
- onnxmltools: <https://github.com/onnx/onnxmltools>; sklearn-onnx: <https://onnx.ai/sklearn-onnx/>
