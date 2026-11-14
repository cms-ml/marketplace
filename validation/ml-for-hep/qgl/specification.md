# Quark/gluon jet BDT on 2016 Open Data simulation, compared with Jet_qgl and DeepJet QG

Per-jet quark vs gluon classifier (BDT on jet-level NanoAODv9 quantities) trained on QCD multijet
simulation and compared, on the same test jets, with the CMS quark-gluon likelihood and the DeepJet q/g output.

## Data Samples

| Dataset (Open Data path)                                                                                                                         | Tier       | Era / campaign             | Role(s) in analysis                  |
| ------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | -------------------------- | ------------------------------------ |
| `/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/QCD_HT700to1000_TuneCP5_PSWeights_13TeV-madgraphMLM-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/`   | NANOAODSIM | RunIISummer20UL16NanoAODv9 | quark and gluon jets (training/test) |
| `/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/QCD_HT1000to1500_TuneCP5_PSWeights_13TeV-madgraphMLM-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/`  | NANOAODSIM | RunIISummer20UL16NanoAODv9 | quark and gluon jets (training/test) |
| `/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/QCD_HT1500to2000_TuneCP5_PSWeights_13TeV-madgraphMLM-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/`  | NANOAODSIM | RunIISummer20UL16NanoAODv9 | quark and gluon jets (training/test) |
| `/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/QCD_HT2000toInf_TuneCP5_PSWeights_13TeV-madgraphMLM-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/`   | NANOAODSIM | RunIISummer20UL16NanoAODv9 | quark and gluon jets (training/test) |

- Files: the first 8, 4, 2, 2 files of the HT bins in `validation/dijet-2016/input_files.json`
  (keys `qcd_700to1000`, `qcd_1000to1500`, `qcd_1500to2000`, `qcd_2000toInf`), at most 30 000 events
  read per file. More files in the low-HT bins because they carry the largest weight per event
  (changed from 3 files each after the development run gave few effective events and an
  overtrained BDT). Development: the first file of each bin, 5 000 events per file.
- Luminosity / certification: MC only. No data.
- Triggers: none (simulation only; the HT-binned generation is the only event-level selection).
- MC normalisation: weight = `genWeight x sigma x L / sum(genWeight over the events read)` per HT bin
  (`nano_to_table.py`), L = 1 pb^-1 (arbitrary: only relative weights matter). sigma (pb) from
  `validation/dijet-2016/specification.md` (GenXsecAnalyzer, Open Data records 63139, 63078, 63094,
  63102): HT700to1000 6425, HT1000to1500 1117, HT1500to2000 108.3, HT2000toInf 21.94. Every jet of an
  event carries the event weight.
- Optional quark-enriched Z(->mumu)+jets sample: not used. Directories
  `DYJetsToLL_M-50_TuneCP5_13TeV-madgraphMLM-pythia8` (and amcatnloFXFX) exist under
  `/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/`, but the Open Data record number and a cross
  section from a source already used in this repository were not established, so it is left out
  (the task forbids inventing cross sections).

## Histograms

1. ROC curves of BDT, `Jet_qgl` and `1 - Jet_btagDeepFlavQG`
   - x: quark efficiency, y: gluon rejection (1 - gluon efficiency); inclusive and per pT x |eta| bin.
   - Entries: one per jet (test fold only). Weights: physics weight (signed; all weights are +1 x norm here).
2. AUC vs jet pT for the three taggers, separately for |eta| < 1.3 and 1.3 < |eta| < 2.5.
3. `Jet_qgl` normalised distributions for quark and gluon jets, per pT x |eta| bin
   - x: `Jet_qgl` (0 to 1, 20 bins); area-normalised, weighted; test fold.
4. BDT score, train vs test, quark and gluon (overtraining).
5. Feature importance (total gain and mean |SHAP|).
6. Gluon pT spectrum before and after the BDT working points (sculpting check, obs = jet pT).

## Analysis Steps

1. Jet selection (per jet, every jet of the event, not only the leading two)
   - `Jet_pt` in [30, 1000) GeV, |`Jet_eta`| < 2.5, tight jet ID (`Jet_jetId & 2`).
   - Matched to a generator jet: `Jet_genJetIdx >= 0` (simulation-only selection, applied to both classes).
   - Deviation from the suggested "leading two jets": the samples start at HT = 700 GeV, so the two
     leading jets almost always have pT > 120 GeV (measured on 20k HT700to1000 events: 140 of
     40k leading-two jets in 30-50 GeV, versus 12 374 with all jets). All selected jets are used so that
     the 30-120 GeV bins are populated. Non-leading jets in these events are soft radiation:
     the gluon fraction of the low-pT bins is therefore higher than in a dijet-balanced sample. The
     jet rank in the event is kept as observer `obs_jet_idx`.
2. Label (per jet, from `Jet_partonFlavour`, physics definition)
   - quark (label 1): |partonFlavour| in {1, 2, 3}; gluon (label 0): partonFlavour == 21.
   - c (4), b (5), undefined (0) and unmatched (`genJetIdx < 0`) jets: counted (flavour composition
     before the label cut) and excluded.
   - Cross-check: quark = |partonFlavour| in {1..5} (c and b added), same gluon definition: the
     baseline BDT is retrained and all taggers re-evaluated on that table.
3. Split
   - fold = event % 5 by event number, so all jets of one event are in the same fold.
     Folds 0, 1, 2 train; 3 validation (early stopping, scan); 4 test (touched once). k-fold closure
     rotates the test fold over 0..4.
4. Weights and reweighting
   - Metrics: physics weight (above). Training: |w| with the two classes scaled to equal sums
     (`train_bdt.py` default). pT and eta are NOT flattened between classes: `train_bdt.py` uses
     one weight column for training and metrics, so flattening would change every quoted number;
     instead jet pT and eta are not inputs, and the pT dependence is measured with the sculpting
     check (score vs `obs_pt`) and per-bin metrics. The quark fraction rises with pT, so any input
     correlated with pT (e.g. constituent multiplicity) lets the BDT partly learn the pT prior; this
     is what the sculpting check quantifies.
5. Inputs (reconstructed, available identically in data)
   - `n_constituents` (`Jet_nConstituents`), `ch_had_ef` (`Jet_chHEF`), `ne_had_ef` (`Jet_neHEF`),
     `ch_em_ef` (`Jet_chEmEF`), `ne_em_ef` (`Jet_neEmEF`), `mu_ef` (`Jet_muEF`),
     `ch_pv0_ef` (`Jet_chFPV0EF`), `area` (`Jet_area`), `mass_over_pt` (`Jet_mass/Jet_pt`),
     `n_muons` (`Jet_nMuons`), `n_electrons` (`Jet_nElectrons`), `rho` (`fixedGridRhoFastjetAll`,
     per event, as the CMS QGL also conditions on rho).
   - Not inputs: `Jet_qgl` and `Jet_btagDeepFlavQG` (baselines), the other DeepJet/DeepCSV/CSV outputs
     and the b/c regressions (they come from the same constituent-level networks and would leak the
     DeepJet baseline), `Jet_puIdDisc` (an MVA on jet-shape variables), pT and eta (bins), all
     generator-level branches.
   - NanoAODv9 limitation: the CMS QGL inputs (major-axis width `axis2`, `ptD`, QGL charged+neutral
     multiplicity) and PF candidates are not stored, so this BDT cannot use them.
6. Observers (never inputs): `obs_pt`, `obs_eta`, `obs_abseta`, `obs_qgl` (`Jet_qgl`),
   `obs_deepjet_qg` (`Jet_btagDeepFlavQG`), `obs_jet_idx`.

## Corrections and Systematics

None (NanoAOD JEC as stored; no pileup reweighting; MC only). Non-closure from the k-fold test is
reported as the stability systematic of the working point.

## Workflow

1. Data Extraction
   - `nano_to_table.py` with feature module `features_qgl.py` (one row per selected jet), then
     `make_jet_table.py` applies the matching and label definitions and writes the composition.
   - Branches: `Jet_pt, Jet_eta, Jet_mass, Jet_jetId, Jet_genJetIdx, Jet_partonFlavour,
     Jet_nConstituents, Jet_chHEF, Jet_neHEF, Jet_chEmEF, Jet_neEmEF, Jet_muEF, Jet_chFPV0EF, Jet_area,
     Jet_nMuons, Jet_nElectrons, Jet_qgl, Jet_btagDeepFlavQG, fixedGridRhoFastjetAll, event, genWeight`.
2. Training and evaluation
   - `check_table.py`, `train_bdt.py` (xgboost defaults; hgb cross-check), quick scan
     (`scan.py --mode quick`), longer scan only if improvement > 2 x AUC_ERR.
   - `evaluate.py` (inclusive, categories in `obs_pt`), `qg_compare.py` for the three-tagger table.
   - Bins: pT 30-50, 50-80, 80-120, 120-200, 200-400, 400-1000 GeV; |eta| < 1.3, 1.3-2.5; and
     inclusive (pT 30-1000, |eta| < 2.5).
   - Per tagger and bin (test fold): weighted ROC AUC with bootstrap error (50 resamples); gluon
     rejection 1 - eff_g at eff_q = 0.5 and 0.7; eff_q at eff_g = 0.1. Working-point thresholds are
     set inside each bin (per-bin working points, as in a binned q/g comparison). Each number is quoted
     with the raw quark and gluon jet counts passing the cut and is not quoted (null, low_stat) if
     either is below 100.
   - Taggers' orientation: BDT score and `Jet_qgl` are quark-like when high; DeepJet
     `btagDeepFlavQG` is gluon-like when high (g/(g+uds)), so `1 - btagDeepFlavQG` is used.
     Jets with `Jet_qgl < 0` (undefined) are counted and kept, as the tagger would be cut on.

## Statistical Analysis

None (performance study). Checks: sculpting of the BDT score against `obs_pt` (`sculpting.py`,
log bins 30-1000 GeV, gluon-efficiency working points 0.5, 0.3, 0.1), k-fold closure with all five
test-fold rotations (`closure.py kfold`). If the raw score sculpts the gluon pT spectrum, the
`mass-sculpting-check` remedy is applied: a DDT-style map in pT (`ddt.py --mass obs_pt`, fitted on the
training folds, one map per working point), and the check is repeated on `score_ddt`. The `hist` closure is not run: no background
estimate uses the score in this study.

## Acceptance criteria

- `check_table.py` PASS (no truth or label-proxy input; no single feature AUC > 0.98).
- `train_bdt.py` PASS: AUC_TEST > 0.6, AUC_TRAIN - AUC_TEST < 0.02, ONNX equals native (< 0.5% of rows
  differ by > 1e-4); AUC_TEST < 0.99 (leakage guard).
- `evaluate.py` PASS (no pT category with AUC < 0.6).
- `sculpting.py` PASS and `closure.py kfold` PASS; `model_card.py` READY=1 with every waiver justified.
- At least 200 000 jets of each class in the final table.

## Tools

- LCG_109 view: uproot, awkward, numpy, pandas, xgboost, scikit-learn, optuna, onnx, onnxruntime;
  venv under `<work>` for onnxmltools (xgboost to ONNX).
- `ml-for-hep` scripts: `nano_to_table.py`, `check_table.py`, `train_bdt.py`, `scan.py`,
  `evaluate.py`, `sculpting.py`, `closure.py`, `model_card.py`.
- Helpers in this directory: `make_samples.py`, `features_qgl.py`, `make_jet_table.py`, `qg_compare.py`,
  `make_plots.py`, `make_summary.py`, `check_results.py`, `run_all.sh`.
