# Task for the hep-ml-trainer agent: a gated BDT and a ParticleNet smoke test

This validates the `ml-for-hep` plugin: the `hep-ml-trainer` agent and the
skills `hep-ml-data-prep`, `bdt-training`, `hyperparam-scan`,
`model-evaluation`, `mass-sculpting-check`, `closure-tests` and
`particlenet-training`. The agent trains a Z′ → bb̄ vs QCD event classifier
on 2016 CMS Open Data NanoAOD simulation, tunes it, runs every gate check
and writes a model card; it then runs a small ParticleNet H → bb̄ vs QCD jet
tagger as a CPU smoke test and puts it through the same checks. There is no
published CMS counterpart for these exact models: the validation tests that
the workflow runs unattended and that the gate reports honestly, not that a
number is reproduced.

## How to run

From the repository root on cmslpc, on branch `feat/ml-for-hep`, inside
`tmux` (a grid proxy is needed only for the optional Condor scan):

```bash
tmux new -s ml
mkdir -p ~/nobackup/ml_validation      # the <work> area, outside the repository
sed -n '/^## Task/,$p' validation/ml-for-hep/PROMPT.md | \
  claude -p --agent ml-for-hep:hep-ml-trainer \
    --plugin-dir plugins/ml-for-hep --plugin-dir plugins/cms --plugin-dir plugins/af-fnal-lpc \
    --permission-mode acceptEdits --allowedTools "Bash Read Write Edit Glob Grep Skill TodoWrite" \
    > validation/ml-for-hep/agent_report.md 2>&1
```

Or, in a Claude Code chat opened on this repository: "Use the
hep-ml-trainer agent to do the task in `validation/ml-for-hep/PROMPT.md`
(everything from '## Task' on)."

Check progress with `ls -lt validation/ml-for-hep/` and
`tail ~/nobackup/ml_validation/runs.jsonl`.

## Task

Train, tune and validate two classifiers with the `ml-for-hep` skills and
decide for each, with `model_card.py`, whether it is READY. Load each skill
before using its scripts and follow it. Work area for all large files:
`<work>` = `~/nobackup/ml_validation` (create it). Deliverables go
in `validation/ml-for-hep/`. Do not modify any skill or other validation.

### Environment

- Python: `set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh`
  (xgboost, scikit-learn, optuna, torch CPU, onnx, onnxruntime, uproot,
  awkward). LightGBM and the tree → ONNX converters need the venv described
  in `bdt-training`; build it under `<work>`.
- The interactive node is shared and has about 6 GB of free memory and no
  GPU: use `--threads 2` to `4`, run long commands as
  `/usr/bin/time -v ... > log 2>&1; echo EXIT $? >> log`, and read only the
  `KEY=VALUE` lines.
- Never write tables, models or ROOT files into the repository.

### Part A: Z′ → bb̄ vs QCD event BDT

Inputs (paths and cross sections in `validation/dijet-2016/specification.md`
and `validation/dijet-2016/input_files.json`; use those values, do not
invent any):

- Signal: `ZprimeToBB_narrow_M-2000` (all files), RunIISummer20UL16NanoAODv9.
  The Z′ cross section is not in the records: use 1 pb and say so.
- Background: the four `QCD_HT*` bins (700to1000, 1000to1500, 1500to2000,
  2000toInf) with their cross sections, enough files per bin that every bin
  has at least 50 000 selected events.
- Luminosity for the weights: the 2016G+H value in the dijet specification.

Steps:

1. `TASK.md` in `<work>` (copy to the deliverables): signal, background,
   unit, allowed inputs, observers (`obs_mjj` is the fit variable and is
   not an input), intended use (a cut at 10% and at 1% background
   efficiency before a dijet-mass fit), target metric, acceptance criteria.
2. Table with `nano_to_table.py` (start from `features_dijet.py`; you may
   add reconstructed features, with a reason each) and `check_table.py`.
3. Baseline `train_bdt.py` (xgboost, defaults) and a second backend as a
   cross-check.
4. Scan: the quick scan; then decide with the skill's rule whether a
   30-trial TPE scan with pruning is justified, and run it if so (or run it
   anyway with `--timeout 900` and report that the rule said no). Interrupt
   and resume it once to show that the journal works. Optional: a 4-worker
   Condor scan (`scan.py condor`), reporting exactly what happened.
5. Retrain the chosen parameters, export ONNX, run `evaluate.py` with
   categories in `obs_mjj`.
6. `sculpting.py` on `obs_mjj` in the range the dijet analysis fits, at the
   10% and 1% working points. If sculpted, apply `ddt.py`, re-check, and
   re-evaluate the decorrelated score.
7. Closure: `closure.py kfold` with all five rotations; `closure.py hist`
   comparing the QCD `obs_mjj` shape passing the final cut with the shape
   predicted from the failing events times a transfer factor that you
   derive from the training folds; and an `abcd` test with a second
   variable of your choice, stating whether it is independent of the score.
8. `model_card.py` with all five checks. If `READY=0`, do not waive without
   evidence: report NOT READY and why.

### Part B: ParticleNet H → bb̄ vs QCD jet tagger (CPU smoke test)

Input: the CMS Open Data H → bb̄ ntuples used in `particlenet-training`
(`train/` and `test/` directories of the record). Keep it small: at most
30 000 training jets and 3 epochs with `train_pnet_lite.py`, one
interruption and `--resume`, ONNX export. The weaver route is optional.
Then `evaluate.py`, `sculpting.py` on `fj_sdmass` (40–200 GeV), a k-fold or
`hist` closure that makes sense for a jet tagger, and `model_card.py`. This
model is expected to be NOT READY (undertrained, mass-sculpting): the
validation checks that the gate says so. Do not run a full training and do
not claim tagger performance.

### Deliverables in `validation/ml-for-hep/`

- `TASK.md`, and `run_all.sh` that reruns every step from the tables on
  (relative paths, `WORK` as an environment variable)
- your feature module and any helper scripts
- `summary.json` with, for `bdt` and `pnet`: event counts per class and
  split, effective counts, negative-weight fraction; baseline and final
  `AUC_TEST` with `AUC_ERR`, `AUC_TRAIN`, KS p-values, signal efficiency at
  10% and 1% background efficiency with the number of background events
  above each cut; the scan (`n_complete`, `n_pruned`, baseline, best,
  improvement, noise, `significant`, whether the resume worked); ONNX
  maximum difference; sculpting per working point (χ²/ndf, p, JSD, floor,
  verdict) before and after any decorrelation, with R50 and 1/JSD;
  each closure test (χ²/ndf, p, non-closure, systematic); the model-card
  verdict (`ready`, failed, missing, waived with reasons); package versions
- `MODEL_CARD_bdt.md`, `MODEL_CARD_pnet.md`
- `plots/` (PNG): ROC, train/test scores, sculpting before and after,
  closure; labelled "CMS Open Data simulation", never "CMS Preliminary"
- `check_results.py` (stdlib only, reads `summary.json`, exit 0/1/2,
  `SUMMARY=n/n`): AUCs in (0.5, 1); BDT `AUC_TEST` < 0.999 (leakage guard);
  |AUC_TRAIN − AUC_TEST| < 0.02 for a model reported READY; every quoted
  working point has ≥ 10 background events above the cut; efficiencies in
  [0, 1]; ONNX fraction of differing rows < 0.005; `ready` is true only if
  no check is failed or missing, and every waiver has a non-empty reason;
  a model with a SCULPTED verdict at a used working point is not READY
  unless decorrelated and re-checked or waived; closure p-values in [0, 1]
  and non-closure systematics ≥ 0; the scan reports `significant`
  consistently with improvement > 2 × noise; no personal paths
- `SKILLS_USED.md`: for each step, which skill and script guided it, what
  worked as written, and every place a skill or script was wrong, unclear
  or missing (quote it); the wall time and peak memory of each step
- `README.md`: goal, inputs, a results table for both models, the gate
  verdicts, the main skill findings, how to reproduce

Rules: no git commits; no personal paths, usernames or absolute home/data
paths in any file under `validation/` (write `$USER`, `<work>` or relative
paths); never fabricate numbers; never change a pass threshold to obtain a
PASS; Open Data results are not CMS results. Finish with a short report:
event counts, baseline vs final test metrics, the scan decision, the
sculpting and closure verdicts, READY or NOT READY per model with reasons,
the most important skill gaps, and the commands to reproduce.
