# Skills used: quark/gluon BDT (Part C)

Agent run on cmslpc (EL9, 8 cores shared, load about 7, about 7 GB available), LCG_109, 4 threads.
Wall time and peak RSS from `/usr/bin/time -v` (logs in `<work>/logs/`). Times marked (1st) are from
the first run; `run_all.sh` later returned the stored results with `--skip-existing` or the scan journal.

| Step | Skill / script | Wall time | Peak RSS |
| --- | --- | --- | --- |
| 1 Specification | `cms:analysis-spec-builder` (template) | - | - |
| 2 Branch survey, dry run, dev table (20k events) | `hep-ml-data-prep` `nano_to_table.py --dry-run` | 0:18 | 0.23 GB |
| 2 Full table (461 656 events, 1.79 M jets, XRootD) | `nano_to_table.py` + `features_qgl.py` | 1:24 | 1.12 GB |
| 2 Labels, composition | `make_jet_table.py` (own) | 0:05 | 1.22 GB |
| 2 Table check (main / q15) | `check_table.py` | 0:04 / 0:05 | 0.75 / 0.83 GB |
| 3 venv (lightgbm, onnxmltools, skl2onnx) | `bdt-training` pattern 3 | not timed | - |
| 3 Baseline xgboost + ONNX | `train_bdt.py` | 0:42 (1st) | 1.09 GB |
| 3 Cross-check hgb / lightgbm + ONNX | `train_bdt.py --backend` | 0:25 / 0:27 (1st) | 1.10 / 1.11 GB |
| 3 Baseline evaluation (AUC_ERR for the scan) | `model-evaluation` `evaluate.py` | 0:07 | 0.64 GB |
| 3 Quick scan, 4 trials | `hyperparam-scan` `scan.py --mode quick` | 3:01 (1st) | 1.08 GB |
| 4 Evaluation, |eta| categories | `evaluate.py` | 0:05 | 0.59 GB |
| 4 Three-tagger comparison + plots | `qg_compare.py` (own) | 0:33 | 0.58 GB |
| 5 Sculpting raw score vs pT | `mass-sculpting-check` `sculpting.py` | 0:05 | 0.70 GB |
| 5 pT-DDT maps, re-check, re-evaluate (x3) | `ddt.py`, `sculpting.py`, `evaluate.py` | 0:02 + 0:04 + 0:05 each | 0.70 GB |
| 5 k-fold models, 5 rotations | `train_bdt.py --train/val/test-folds` | 0:35-0:42 each (1st) | 1.04 GB |
| 5 k-fold closure (eff_g 0.1, 0.5) | `closure-tests` `closure.py kfold` | 0:04 | 0.75 GB |
| 5 Label cross-check q = 1-5 | `train_bdt.py`, `qg_compare.py` | 0:52 + 0:34 | 1.11 GB |
| 6 Gate | `model_card.py` | 0:00 | 0.01 GB |
| all `run_all.sh` from the tables (with stored runs) | | 3:20 | 1.16 GB |

## Step by step

**1. Specification (`cms:analysis-spec-builder`).** The template worked. There was no user to answer
questions, so the decisions (all jets instead of the leading two, no flattening, inputs excluded,
Z+jets not used) are written as decisions with reasons. The skill's step 6 ("When the user confirms,
write `specification.md`") has no path for an unattended agent; I wrote it without confirmation.

**2. Table (`hep-ml-data-prep`).**
- Worked: `--samples` JSON, Σ genWeight over the events read, `--dry-run`, the `.meta.json`, and
  `check_table.py` (its `mass_corr` warning with `--mass obs_pt` flagged `n_constituents` and
  `mass_over_pt` correctly: these are the inputs that later drove the pT sculpting).
- **Missing: per-object rows.** The contract is event-level: "`build(ev)` returns flat numpy arrays
  for the selected events plus `"_mask"`" and the feature-module docstring says "one entry per
  SELECTED event, plus "_mask": bool array over ALL events". A jet tagger needs one row per jet. It
  works, undocumented, with an **integer** `_mask` (`np.repeat(arange(n_events), n_jets)`), because the
  script indexes `event` and `genWeight` with numpy (`[m]`). Worth documenting as the jet-level mode.
- **Missing: per-row labels.** The label is per sample (`--sample NAME:LABEL:...`). Quark/gluon comes
  from `Jet_partonFlavour`, so the truth had to go through an `obs_` column and a second script
  (`make_jet_table.py`) that sets the label and drops the truth columns. The skill should say how to
  do truth-matched object labels without putting the truth into the training table.
- The skill's rule "`Jet_genJetIdx` ... not allowed" as an input is right; it is silent about using it
  in the selection (done here for both classes; simulation only).
- Development run (20k events, 4 files, 78k jets) gave an overtrained BDT (AUC gap 0.051,
  `STATUS=FAIL`) because of few effective events in the HT-weighted mix. The skill's gotcha
  "`low_neff:sig` with thousands of rows" pointed to the fix (more files in the high-weight HT bins).

**3. Baseline, backends, scan (`bdt-training`, `hyperparam-scan`).**
- Worked as written: defaults, `--onnx` (xgboost max diff 3.7e-07, hgb 1.7e-07, lightgbm 1.8e-07,
  0 rows differing), the venv recipe including the `PYTHONPATH` gotcha, `--skip-existing`,
  `runs.jsonl`, and the scan with `--baseline/--noise` (`SIGNIFICANT=0`, improvement 5e-05 vs noise
  0.00124) and journal resume (re-run took 0.5 s).
- **Missing: a separate training weight.** "Training weight = |w| ... classes balanced" and "All metrics
  use the original signed weights" use the same `weight` column, so pT/eta flattening between the
  classes (standard for jet taggers) cannot be done without changing every reported metric. A
  `--train-weight COLUMN` option would allow it.
- The quick-scan leaderboard summary has no `NOISE` key (only `BASELINE`, `IMPROVEMENT`,
  `SIGNIFICANT`), so a summary must take the noise from elsewhere; `BEST_OUT_DIR` and
  `LEADERBOARD` are absolute paths.

**4. Evaluation (`model-evaluation`) and the comparison.**
- Worked: `evaluate.py` with `--category obs_pt:...`, bootstrap `AUC_ERR`, train/test KS.
- **Missing for a tagger comparison**: (a) only "signal efficiency at fixed background efficiency"
  (`--bkg-effs`); background rejection at fixed signal efficiency, the usual q/g figure, is not
  available; (b) one `--category` column, no 2D (pT x eta); (c) inside a category `sig_eff_wp0` uses
  the inclusive threshold, not a per-category working point; (d) no way to put an existing tagger
  (here `Jet_qgl`, DeepJet) in the same table on the same rows. `qg_compare.py` does all four.
- The evaluate plots carry no "simulation" label; the deliverable plots are made by `qg_compare.py`
  and `make_plots.py` with "CMS Open Data simulation".
- `data/MC` could not be run: no data in this study.

**5. Sculpting and closure (`mass-sculpting-check`, `closure-tests`).**
- `sculpting.py --mass obs_pt --log-bins` worked unchanged for pT. Raw score: SCULPTED at all three
  working points (chi2/ndf 877, 733, 610; Pearson r 0.38).
- `ddt.py --mass obs_pt` (the skill's remedy, fitted on the training split) worked as written; all three
  working points then pass (p 0.11, 0.47, 0.028). The decision table ("SCULPTED, smooth change ... may
  be acceptable for a parametric fit") does not cover the jet-tagger case where the cut itself becomes
  pT-dependent; the TASK.md "Use of the score" line was extended after this result.
- **Unclear**: `model_card.py` takes one `sculpting` check, but DDT gives "one map per working point".
  I passed the three DDT checks under extra names and the raw-score check as a waived check; the skill
  does not say how to gate a multi-working-point model.
- `closure.py kfold` with 5 score files worked as written (`P_VALUE` 0.491 at eff 0.1, 0.377 at 0.5;
  `AUC_STD` 0.00124 across folds, equal to the bootstrap AUC_ERR). The skill does not say how to
  rotate the validation fold; I used validation = k-1 so that rotation 4 reproduces the baseline
  exactly (it did: identical AUCs). The k-fold closure of the DDT score was not run (the maps would
  have to be refitted per rotation).
- `hist` closure not run: no background estimate uses the score.

**6. Gate (`model_card.py`).** READY=1 with one waiver. Issues: the card lists absolute check paths
(they had to be replaced by `<work>` before copying into the repository); the result exists only as
stdout, so `run_all.sh` parses the KEY=VALUE lines into `model_card_result.json`.

## Agent definition (`hep-ml-trainer`)

- "Write `<work>/TASK.md`" vs the task's "TASK.md in `validation/ml-for-hep/qgl/`": kept in the
  repository and copied to `<work>`.
- "Training weight = |w| ... report the negative-weight fraction": 0 here (all `genWeight` = 1).
