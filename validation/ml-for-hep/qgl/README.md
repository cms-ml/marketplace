# Quark/gluon jet BDT vs the CMS quark-gluon likelihood (Part C of the ml-for-hep validation)

## Goal

Train a BDT that separates quark from gluon AK4 jets with the `ml-for-hep` skills, compare it on the
same test jets with the CMS quark-gluon likelihood (`Jet_qgl`) and the DeepJet q/g output
(`Jet_btagDeepFlavQG`), and let `model_card.py` decide whether it is READY. The task is in
`../PROMPT.md` ("Task C"); the definitions are in [specification.md](specification.md) and
[TASK.md](TASK.md). Everything here is **CMS Open Data simulation**, not a CMS result.

## Inputs

- RunIISummer20UL16NanoAODv9 `QCD_HT{700to1000,1000to1500,1500to2000,2000toInf}` madgraphMLM-pythia8,
  files from `../../dijet-2016/input_files.json`: 8, 4, 2, 2 files, at most 30 000 events per file
  (461 656 events read). Cross sections 6425, 1117, 108.3, 21.94 pb from
  `../../dijet-2016/specification.md`. All `genWeight` = +1 here (negative-weight fraction 0).
- Z(->mumu)+jets was **not used** (no record number or cross section established; see specification).
- Jets: every jet with 30 <= pT < 1000 GeV, |eta| < 2.5, tight ID, `Jet_genJetIdx >= 0`. All jets of
  the event, not only the two leading ones: the samples start at HT = 700 GeV and the leading two jets
  would leave the 30-120 GeV bins almost empty.
- Labels from `Jet_partonFlavour`: quark = |flavour| 1-3 (440 805 jets), gluon = 21 (1 108 010 jets).
  Before the label cut (1 789 547 jets): 11 582 unmatched (0.6% weighted), and among matched jets uds
  24.2%, c 8.6%, b 4.1%, g 63.1%, flavour 0 0.01% (weighted fractions; `summary.json`).
- **NanoAODv9 limitation**: the CMS QGL is built from the jet shape variables `axis2`, `ptD` and the
  QGL particle multiplicity, computed from PF candidates. NanoAODv9 stores none of them and no PF
  candidates, so this BDT uses only jet-level quantities: `n_constituents`, charged/neutral
  hadron and EM energy fractions, muon fraction, charged-from-PU fraction (`chFPV0EF`), area,
  mass/pT, numbers of muons and electrons, and the event `rho`. `Jet_qgl`, every DeepJet/DeepCSV
  output, `Jet_puIdDisc`, pT and eta are not inputs.

## Results (test fold, 309 494 jets; per-bin working points)

AUC with bootstrap error; R50 = gluon rejection (1 - gluon efficiency) at 50% quark efficiency.
`1 - Jet_btagDeepFlavQG` is used for DeepJet (the branch is g/(g+uds)).

| pT [GeV] | abs(eta) | N quark / gluon (test) | AUC BDT | AUC Jet_qgl | AUC DeepJet | R50 BDT | R50 Jet_qgl | R50 DeepJet |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 30-50 | 0.0-2.5 | 5345 / 44575 | 0.7225 ± 0.0043 | 0.7219 ± 0.0049 | 0.7677 ± 0.0045 | 0.810 | 0.805 | 0.860 |
| 50-80 | 0.0-2.5 | 4772 / 33273 | 0.7527 ± 0.0047 | 0.7732 ± 0.0044 | 0.8066 ± 0.0039 | 0.847 | 0.861 | 0.902 |
| 80-120 | 0.0-2.5 | 4775 / 24745 | 0.7537 ± 0.0050 | 0.7914 ± 0.0042 | 0.8227 ± 0.0044 | 0.855 | 0.879 | 0.912 |
| 120-200 | 0.0-2.5 | 8035 / 29179 | 0.7573 ± 0.0035 | 0.8044 ± 0.0033 | 0.8409 ± 0.0027 | 0.868 | 0.896 | 0.927 |
| 200-400 | 0.0-2.5 | 29551 / 54965 | 0.7854 ± 0.0018 | 0.8208 ± 0.0017 | 0.8619 ± 0.0013 | 0.893 | 0.919 | 0.947 |
| 400-1000 | 0.0-2.5 | 35656 / 34623 | 0.8027 ± 0.0023 | 0.8390 ± 0.0019 | 0.8796 ± 0.0014 | 0.907 | 0.935 | 0.961 |
| 30-1000 | 0.0-1.3 | 51997 / 163330 | 0.8037 ± 0.0015 | 0.8018 ± 0.0014 | 0.8497 ± 0.0010 | 0.908 | 0.910 | 0.942 |
| 30-1000 | 1.3-2.5 | 36137 / 58030 | 0.8187 ± 0.0017 | 0.7851 ± 0.0019 | 0.8380 ± 0.0013 | 0.916 | 0.894 | 0.936 |
| 30-1000 (inclusive) | 0.0-2.5 | 88134 / 221360 | 0.8107 ± 0.0011 | 0.7961 ± 0.0011 | 0.8487 ± 0.0008 | 0.912 | 0.901 | 0.942 |

The pT x |eta| bins, the 70% quark-efficiency point, quark efficiency at 10% gluon efficiency, the jet
counts behind every number and the normalised `Jet_qgl` quark/gluon shapes per bin are in
`summary.json` (`taggers`, `qgl_shapes`) and `plots/`.

Reading: inside every pT bin above 50 GeV the BDT is below `Jet_qgl` and both are below DeepJet, as
expected without the shape variables. In 30-50 GeV BDT and QGL agree within errors. Inclusively the
BDT looks better than QGL only because it partly learns the pT dependence of the quark fraction
(raw score vs gluon pT: Pearson r = 0.38); the per-bin numbers are the fair comparison.

Cross-checks: hgb and LightGBM give AUC_TEST 0.81095 and 0.81132 (xgboost 0.81074). With quark =
|flavour| 1-5 the inclusive AUCs drop to 0.749 (BDT), 0.725 (QGL), 0.781 (DeepJet).

## Gate

`model_card.py`: **READY=1, with one waiver** (`MODEL_CARD_qgl.md`). Checks: table PASS, training PASS
(AUC_TRAIN 0.81754, AUC_TEST 0.81074, gap 0.0068, ONNX max diff 3.7e-07), evaluation PASS (worst pT
category AUC 0.7225), closure PASS (5-rotation k-fold at gluon efficiency 0.1: p = 0.491,
non-closure syst 0.35%; at 0.5: p = 0.377).

Sculpting against jet pT: a single cut on the raw score **is SCULPTED** at gluon efficiency 0.5, 0.3
and 0.1 (chi2/ndf 877, 733, 610). The remedy from `mass-sculpting-check` (a DDT-style map in pT,
fitted on the training folds) gives a pT-dependent threshold with fixed gluon efficiency; after it all
three working points pass (p = 0.11, 0.47, 0.028). The model is therefore defined as **BDT + pT-DDT map**
(`score_ddt > 0`, one map per working point), and the raw-score sculpting check is waived with that
evidence. Not checked: data/MC agreement (no data in this study), k-fold closure of the DDT score
(closure was run on the raw score), other generators.

## Skill findings (details in SKILLS_USED.md)

- `nano_to_table.py` has no per-object (jet) mode and only per-sample labels; worked around with an
  integer `_mask` and `make_jet_table.py`.
- `train_bdt.py` has one weight column for training and metrics, so pT/eta flattening between classes
  is not possible without changing every metric.
- `evaluate.py` gives only signal efficiency at fixed background efficiency, one category column, an
  inclusive threshold inside categories, and no way to compare with an existing tagger: `qg_compare.py`.
- `model_card.py` writes absolute paths into the card and has no JSON output.

## Reproduce

```bash
export WORK=~/nobackup/ml_validation/qgl            # <work>, outside the repository
BUILD_TABLES=1 bash validation/ml-for-hep/qgl/run_all.sh   # tables (about 1.5 min over XRootD) + everything
bash validation/ml-for-hep/qgl/run_all.sh                  # from the tables on (about 3-10 min, 4 threads)
python3 validation/ml-for-hep/qgl/check_results.py          # SUMMARY=11/11
```

Tables, models, scores and logs stay in `<work>` (`table.parquet`, `runs/bdt0/{model.json,model.onnx}`,
`runs/bdt0/ddt/*.map.json`, `logs/`). Tested on cmslpc EL9 with LCG_109 (xgboost 2.1.3) plus a venv with
lightgbm 4.7.0, onnxmltools 1.16.0, skl2onnx 1.20.0.
