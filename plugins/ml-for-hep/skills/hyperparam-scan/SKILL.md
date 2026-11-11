---
name: hyperparam-scan
description: >-
  Use when tuning the hyperparameters of a HEP machine-learning model or
  deciding whether tuning is worth it: a quick sanity scan of two or three
  parameters, a random or Bayesian (Optuna TPE) search with pruning and a
  trial or time budget, a large parallel scan on HTCondor, k-fold
  cross-validation for small samples, resuming an interrupted scan, merging
  results from many workers into a leaderboard, choosing search ranges for a
  BDT or a network, or debugging a scan whose trials all fail, never prune,
  or whose "best" point is just a statistical fluctuation.
metadata:
  summary: Grid, random and Optuna scans around any KEY=VALUE trainer, resumable, with pruning, k-fold CV and HTCondor workers
---

# Hyperparameter scans

## Overview

[scripts/scan.py](scripts/scan.py) wraps **any training command** that
prints `KEY=VALUE` (all trainers in this plugin do) and turns it into a
scan with a machine-readable leaderboard. The trainer is a black box: the
scan fills placeholders in a command template, reads the metric from
stdout, and can kill a trial early from its `PROGRESS` lines.

Scans cost CPU and overfit the validation set. Climb the ladder only as far
as the evidence justifies:

| Level      | Command                                          | Cost (BDT example) | Go on when                                            |
| ---------- | ------------------------------------------------ | ------------------ | ----------------------------------------------------- |
| 0 baseline | one default training                             | seconds            | always                                                |
| 1 quick    | `--mode quick`, 2–3 parameters, 4–9 trials       | ~1 min             | `SPREAD_TOP5` or `IMPROVEMENT` > 2 × `AUC_ERR`        |
| 2 Optuna   | `--mode tpe --prune --n-trials 30–100 --timeout` | minutes–1 h        | still improving and each trial is cheap               |
| 3 Condor   | `scan.py condor`, N workers × M trials           | hours of batch     | trials are expensive (networks) or the space is large |

**Rule for "is a scan worth running":** take `AUC_ERR` from
`model-evaluation` (bootstrap error of the metric). If the quick scan's
best value beats the baseline by less than twice that
(`SIGNIFICANT=0` with `--baseline V --noise E`), stop: the model is limited
by features or statistics, not hyperparameters. In the tested example the
quick scan improved the validation AUC by 0.00013 with a noise of 0.001, so
the right decision was to keep the defaults.

## When to Use

- After a baseline exists and passes its checks
- For small samples: `--kfold` to make the metric less noisy
- **Not** to rescue a model that fails the leakage, overtraining or
  sculpting checks; fix those first

## Key Concepts

| Term         | Meaning                                                                                                          |
| ------------ | ---------------------------------------------------------------------------------------------------------------- |
| `--cmd`      | template with `{out_dir}`, `{params_json}`, `{seed}`, `{<param>}`, and with k-fold `{train_folds}` `{val_folds}` |
| `--space`    | JSON: `{"name": {"type": "float"\|"int"\|"categorical", "low", "high", "log", "choices"}}`                       |
| `--metric`   | KEY read from the trainer's stdout (default `AUC_VAL`: a **validation** number, never the test fold)             |
| journal      | `<study-dir>/journal.log`, Optuna journal-file storage: resumable, NFS-safe, shared by parallel workers          |
| pruning      | `--prune`: median rule on `PROGRESS step=N value=V` lines; the trial's process is killed                         |
| trial states | COMPLETE, PRUNED, FAILED (exit 2, timeout, no metric); `STATUS=FAIL` trials are kept but never `BEST`            |

Search spaces: [assets/space_quick.json](assets/space_quick.json) (2 × 2
grid: depth, learning rate) and [assets/space_bdt.json](assets/space_bdt.json)
(six parameters with log ranges for `train_bdt.py`).

## Canonical Patterns

```bash
set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh   # optuna 4.4.0
T=<bdt-training>/scripts/train_bdt.py; S=<skill>
CMD="python3 $T table.parquet --out-dir {out_dir} --params-json '{params_json}' --progress-every 25 --threads 2"
```

### 1. Quick scan

```bash
$S/scripts/scan.py run --study-dir scan_quick --space $S/assets/space_quick.json --mode quick \
    --cmd "$CMD" --baseline 0.95939 --noise 0.001 2> scan_quick.err
# N_COMPLETE=4 N_PRUNED=0 N_FAILED=0 N_STATUS_FAIL=0 BEST_VALUE=0.95952 BEST_TRIAL=3
# BEST_PARAMS={"max_depth": 5, "learning_rate": 0.05} BEST_OUT_DIR=scan_quick/trials/w0_t3
# SPREAD_TOP5=0.00086 BASELINE=0.95939 IMPROVEMENT=0.00013 SIGNIFICANT=0 SECONDS=68.3 STATUS=PASS
```

`--dry-run` prints the grid size and the first command without running.

### 2. Optuna TPE with pruning and a budget; resume

```bash
$S/scripts/scan.py run --study-dir scan_tpe --space $S/assets/space_bdt.json --mode tpe \
    --prune --prune-warmup 50 --n-trials 30 --timeout 1800 --cmd "$CMD"
```

Run the **same command again** to resume: finished trials are read from the
journal and `--n-trials` is the total. Tested: 6 trials, then the command
with `--n-trials 10` ran 4 more (2 of them pruned) and reported
`N_COMPLETE=8 N_PRUNED=2`. Several processes with the same `--study-dir`
and different `--worker-id` share one study on one node.

### 3. k-fold cross-validation (small samples)

```bash
$S/scripts/scan.py run --study-dir scan_cv --space $S/assets/space_quick.json --mode random --n-trials 10 \
    --kfold 4 --test-fold 4 --cmd "$CMD --train-folds {train_folds} --val-folds {val_folds}"
```

Each trial trains 4 times (fold k validates, the other three train, fold 4
is never touched) and the value is the mean; the per-fold values are in the
journal (`fold_values`). No pruning with `--kfold`.

### 4. Large scans on HTCondor

Workers cannot share the journal (no shared filesystem on LPC workers), so
each job runs its **own** study with its own seed and returns it; merge
afterwards. Random search parallelises perfectly; TPE per worker only
learns from its own trials.

```bash
cp $T .      # the worker runs in a flat scratch directory
$S/scripts/scan.py condor --study-dir scan_condor --space $S/assets/space_bdt.json --workers 20 \
    --transfer table.parquet,train_bdt.py -- --mode random --n-trials 10 \
    --cmd "python3 train_bdt.py table.parquet --out-dir {out_dir} --params-json '{params_json}' --threads 4"
# WORKERS=20  JDL=scan_condor/condor/scan.jdl  SUBMIT=cd scan_condor/condor && condor_submit scan.jdl
cd scan_condor/condor && condor_submit scan.jdl          # then wait: condor_q; see the lpc-condor skill
for f in scan_w*.tar.gz; do tar xzf $f; done
$S/scripts/scan.py merge scan_w*/ -o leaderboard.json
```

Resubmit failed workers only (missing `scan_w<id>.tar.gz`); finished ones
are already in the merge. `--gpus 1` adds `request_GPUs = 1`.

**Tested:** the generated `scan.jdl` parses (`condor_submit -dry-run`), and
`worker.sh` ran end to end on the interactive node followed by `merge`
(`N_COMPLETE=2 STATUS=PASS`). **Not tested:** an actual Condor submission of
the scan, and anything with GPUs (`condor_status -constraint 'CUDACapability
=!= undefined'` showed no GPU slots in the LPC pool on 2026-11-09).

### 5. After the scan

Retrain the best point as a normal run (`--params-json "$BEST_PARAMS"`),
then repeat **all** checks (`model-evaluation`, `mass-sculpting-check`,
`closure-tests`) on it: the leaderboard ranks validation AUC only.
`leaderboard.json` / `.csv` list every trial, best first.

## Gotchas

- **The "best" trial is a fluctuation.** With 30 trials and a noise of
  0.001, the maximum is biased up by about 2σ. Compare with the baseline
  using `--baseline/--noise`, and confirm on the test fold once.
- **Tuning on the test fold.** `--metric AUC_TEST` makes the test fold a
  second validation set and the final number optimistic. Keep `AUC_VAL`.
- **`N_STATUS_FAIL` > 0**: those trials ran but failed the trainer's own
  checks (the tested TPE scan had one such trial). They are excluded
  from `BEST`. If most trials fail, shrink the space (lower depth, more
  regularisation).
- **`N_FAILED` = all trials**: the command template is wrong. Run the
  `FIRST_CMD` from `--dry-run` by hand; exit code 2 from the trainer or a
  missing `--metric` key marks a trial FAILED.
- **Nothing is ever pruned**: the trainer prints no `PROGRESS` lines (add
  `--progress-every` for `train_bdt.py`), or fewer than 5 trials have
  finished (the median rule needs them).
- **Quotes in the Condor `arguments` line.** The command template contains
  spaces and quotes; `scan.py condor` writes HTCondor "new syntax"
  (`'...'` with doubled quotes). Do not edit that line by hand.
- **Trial directories fill the disk.** Every trial writes a model and a
  scores table. The Condor worker excludes `*.parquet` and `model.*` from
  the tarball; locally, delete `trials/` after retraining the best point.
- **Oversubscribed node**: trials × threads must not exceed the cores you
  may use on a shared interactive node (`--threads 2`).

## Docs

- Tested on cmslpc EL9, LCG_109 (Python 3.13, optuna 4.4.0, xgboost 2.1.3),
  2026-11, with `train_bdt.py` as the trainer. `train_pnet_lite.py` prints
  the same `PROGRESS`/KEY=VALUE lines but was not run inside a scan.
- Optuna: <https://optuna.readthedocs.io/> (T. Akiba et al., <https://arxiv.org/abs/1907.10902>);
  journal storage: <https://optuna.readthedocs.io/en/stable/reference/generated/optuna.storages.JournalStorage.html>
- J. Bergstra, Y. Bengio, "Random Search for Hyper-Parameter Optimization",
  <https://www.jmlr.org/papers/v13/bergstra12a.html>
- HTCondor submit-file `arguments` syntax: <https://htcondor.readthedocs.io/en/latest/man-pages/condor_submit.html>
