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
awk '/^## Task C/{exit} /^## Task$/{f=1} f' validation/ml-for-hep/PROMPT.md | \
  claude -p --agent ml-for-hep:hep-ml-trainer \
    --plugin-dir plugins/ml-for-hep --plugin-dir plugins/cms --plugin-dir plugins/af-fnal-lpc \
    --permission-mode acceptEdits --allowedTools "Bash Read Write Edit Glob Grep Skill TodoWrite" \
    > validation/ml-for-hep/agent_report.md 2>&1
```

To run only Part C (the quark/gluon BDT, the first stage of this
validation), give the agent the "Task C" section instead:

```bash
mkdir -p ~/nobackup/ml_validation/qgl
sed -n '/^## Task C/,$p' validation/ml-for-hep/PROMPT.md | \
  claude -p --agent ml-for-hep:hep-ml-trainer \
    --plugin-dir plugins/ml-for-hep --plugin-dir plugins/cms --plugin-dir plugins/af-fnal-lpc \
    --permission-mode acceptEdits --allowedTools "Bash Read Write Edit Glob Grep Skill TodoWrite" \
    > validation/ml-for-hep/qgl/agent_report.md 2>&1
```

Parts A and B (the "Task" section below, which stops at "## Task C") are
run after Part C has been reviewed.

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

## Task C: quark/gluon jet BDT compared with the CMS quark-gluon likelihood

Train a BDT that separates quark jets from gluon jets with the `ml-for-hep`
skills, compare it with the CMS quark-gluon likelihood (`Jet_qgl`) and the
DeepJet quark/gluon output (`Jet_btagDeepFlavQG`) on the same jets, and
decide with `model_card.py` whether it is READY. Load each skill before
using its scripts and follow it. A separate validator agent will later
compare the results with published CMS quark/gluon performance, so record
everything that defines the comparison (jet selection, pT and η bins, label
definition, the working points). Work area for large files: `<work>` =
`~/nobackup/ml_validation/qgl` (create it). Deliverables go in
`validation/ml-for-hep/qgl/`. Do not modify any skill or other validation.

### Environment

- Python: `set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh`
  (xgboost, scikit-learn, optuna, uproot, awkward, onnx, onnxruntime).
  LightGBM and the tree → ONNX converters need the venv described in
  `bdt-training`; build it under `<work>`.
- Shared interactive node, about 6 GB free memory, no GPU: `--threads 2`
  to `4`, run long commands as
  `/usr/bin/time -v ... > log 2>&1; echo EXIT $? >> log`, and read only the
  `KEY=VALUE` lines. A GPU is not needed for a BDT.
- Never write tables, models or ROOT files into the repository.

### Inputs

- Sample: 2016 CMS Open Data simulation, RunIISummer20UL16NanoAODv9.
  Primary: the `QCD_HT*` files listed in
  `validation/dijet-2016/input_files.json` (cross sections in
  `validation/dijet-2016/specification.md`; use those values, do not invent
  any). Optional, as a second, quark-enriched sample: Z(→μμ)+jets
  (`DYJetsToLL_M-50`, UL16 NanoAODv9) if you can find its Open Data record
  and file list (state the record number); otherwise say it was not used.
- Develop on 2 to 3 files; the final table needs at least 200 000 jets of
  each class after selection.
- Known limitation, check it yourself first: NanoAODv9 does not store the
  per-jet QGL inputs (`axis2`, `ptD`, multiplicity as defined by QGL) or
  PF candidates. List the `Jet_*` branches, and build the features from
  what exists (for example `Jet_nConstituents`, energy fractions, area,
  mass/pt, `Jet_nMuons`, `Jet_nElectrons`). `Jet_qgl` and
  `Jet_btagDeepFlavQG` are baselines, never inputs. Record in the README
  that the CMS QGL uses inputs this BDT does not have.

### Steps

1. `specification.md` with the `analysis-spec-builder` skill (in
   `validation/ml-for-hep/qgl/`), before any code: samples and cross
   sections, jet selection (suggested: pT > 30 GeV, |η| < 2.5 as the main
   region, tight jet ID, matched to a generator jet via `Jet_genJetIdx` ≥ 0,
   leading two jets per event), the label (quark: |`Jet_partonFlavour`| in
   1–3, gluon: 21; report how many jets are c, b or unmatched (0) and
   exclude them, with a cross-check that uses 1–5), event weights and how
   jets are reweighted (state whether you flatten pT and η between classes
   and why), the inputs, the pT bins (suggested 30–50, 50–80, 80–120,
   120–200, 200–400, 400–1000 GeV) and η bins (|η| < 1.3, 1.3–2.5), the
   metrics and the acceptance criteria.
2. `TASK.md` (signal = quark, background = gluon, observers `obs_pt`,
   `obs_eta`, `obs_qgl`, `obs_deepjet_qg`, which are not inputs) and the
   table with `nano_to_table.py` and a feature module of your own, then
   `check_table.py`. Split by event, never by jet, so the two jets of one
   event never land in different folds.
3. Baseline `train_bdt.py` (xgboost, defaults) and a second backend as a
   cross-check. Then the quick scan, and decide with the `hyperparam-scan`
   rule whether a longer scan is justified; run it only if so, and report
   the decision either way.
4. Retrain the chosen parameters, export ONNX, `evaluate.py`. For the BDT,
   `Jet_qgl` and `Jet_btagDeepFlavQG`, in every pT × η bin and inclusive:
   ROC AUC with uncertainty, gluon rejection (1 − gluon efficiency) at quark
   efficiency 0.5 and 0.7, and quark efficiency at gluon efficiency 0.1,
   each with the number of jets behind it. Also the normalised quark and
   gluon distributions of `Jet_qgl` in each bin (these are what a CMS
   comparison will use).
5. Checks: `sculpting.py` of the BDT score against `obs_pt` (the tagger
   should not simply learn jet pT; quote it per working point), and
   `closure.py kfold` with all five rotations. A `hist` closure is not
   required; say why if you skip it.
6. `model_card.py` with all its checks. READY means fit for a quark/gluon
   cut in an analysis within the stated pT and η range; if `READY=0`, do
   not waive without evidence.

### Deliverables in `validation/ml-for-hep/qgl/`

- `specification.md`, `TASK.md`, the feature module, any helper scripts,
  and `run_all.sh` that reruns every step from the tables on (relative
  paths, `WORK` as an environment variable)
- `summary.json`: jet counts per class, split and bin (raw and effective),
  flavour composition before the label cut, negative-weight fraction; for
  `bdt`, `qgl` and `deepjet_qg`, per bin and inclusive, AUC with error,
  the working-point numbers above with jet counts; BDT `AUC_TRAIN`,
  `AUC_TEST`, KS p-values; the scan (`n_complete`, `n_pruned`, baseline,
  best, improvement, noise, `significant`); ONNX maximum difference;
  sculpting per working point; k-fold closure; the model-card verdict;
  the input list; package versions
- `MODEL_CARD_qgl.md`
- `plots/` (PNG): ROC curves (BDT vs QGL vs DeepJet) inclusive and per bin,
  AUC vs pT for the three taggers, `Jet_qgl` quark/gluon shapes per bin,
  BDT score train/test, feature importance; labelled "CMS Open Data
  simulation", never "CMS Preliminary"
- `check_results.py` (stdlib only, reads `summary.json`, exit 0/1/2,
  `SUMMARY=n/n`): AUCs in (0.5, 1) for every tagger and bin; BDT
  `AUC_TEST` < 0.99 (leakage guard: `Jet_qgl` or `Jet_partonFlavour` must
  not be an input); `Jet_qgl` and `Jet_btagDeepFlavQG` absent from the
  input list; efficiencies and rejections in [0, 1]; every quoted working
  point has at least 100 jets of each class; |AUC_TRAIN − AUC_TEST| < 0.02
  for a READY model; ONNX fraction of differing rows < 0.005; `ready`
  consistent with failed, missing and waived checks; scan `significant`
  consistent with improvement > 2 × noise; no personal paths
- `SKILLS_USED.md`: for each step, which skill and script guided it, what
  worked as written, every place a skill or script was wrong, unclear or
  missing (quote it), and the wall time and peak memory of each step
- `README.md`: goal, inputs (with the NanoAODv9 limitation), a results
  table (AUC and gluon rejection at 50% quark efficiency per pT bin for the
  three taggers), the gate verdict, the main skill findings, how to
  reproduce

Rules: no git commits; no personal paths, usernames or absolute home/data
paths in any file under `validation/` (write `$USER`, `<work>` or relative
paths); never fabricate numbers; never change a pass threshold to obtain a
PASS; Open Data results are not CMS results; do not search for or compare
with CMS publications yourself (the validator does that). Finish with a
short report: jet counts and flavour composition, the inputs used, BDT vs
QGL vs DeepJet AUC (inclusive and the lowest and highest pT bin), the scan
decision, the sculpting and closure verdicts, READY or NOT READY with
reasons, the most important skill gaps, and the commands to reproduce.
