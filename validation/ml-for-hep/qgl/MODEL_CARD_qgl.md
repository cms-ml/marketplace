# Model card: qgl_bdt_ddt

**Verdict: READY** (2026-11-14; 11 passed, 0 failed, 0 missing, 1 waived)

## Waivers

- **sculpting_raw_score**: one global threshold on the raw score sculpts the gluon pT spectrum (runs/bdt0/sculpt/sculpting.json: PEARSON_R=0.3771, CHI2_NDF_0.1=609.88); the model is used only through the pT-DDT maps runs/bdt0/ddt/scores_ddt_<eff>.parquet.map.json, whose checks pass: eff 0.5: CHI2_NDF=1.33 P=0.11 PASS, eff 0.3: CHI2_NDF=1.0 P=0.466 PASS, eff 0.1: CHI2_NDF=1.56 P=0.0278 PASS

## Description

| Item | Value |
| --- | --- |
| Task | quark (|partonFlavour| 1-3) vs gluon (21) AK4 jets, one row per jet, CMS Open Data simulation (QCD HT700-Inf, RunIISummer20UL16NanoAODv9); not a CMS result |
| Inputs | n_constituents, ch_had_ef, ne_had_ef, ch_em_ef, ne_em_ef, mu_ef, ch_pv0_ef, area, mass_over_pt, n_muons, n_electrons, rho (no QGL shape variables: not in NanoAODv9) |
| Intended use | quark selection by score_ddt > 0 with the pT-DDT map of the chosen gluon efficiency (0.5, 0.3 or 0.1), jets with 30 <= pT < 1000 GeV and |eta| < 2.5 |
| Baselines | Jet_qgl and 1 - Jet_btagDeepFlavQG on the same test jets: see summary.json (taggers) |
| Limitations | pT/eta not flattened; per-bin performance below Jet_qgl and DeepJet; simulation only, no data/MC check; one generator (madgraphMLM-pythia8) |

## Checks

| Check | Status | File |
| --- | --- | --- |
| table | PASS | <work>/checks.json |
| training | PASS | <work>/runs/bdt0/metrics.json |
| evaluation | PASS | <work>/runs/bdt0/eval/evaluation.json |
| sculpting | PASS | <work>/runs/bdt0/sculpt_ddt_0.5/sculpting.json |
| closure | PASS | <work>/closure_kfold_0.1/closure.json |
| evaluation_ddt_0.5 | PASS | <work>/runs/bdt0/eval_ddt_0.5/evaluation.json |
| evaluation_ddt_0.3 | PASS | <work>/runs/bdt0/eval_ddt_0.3/evaluation.json |
| evaluation_ddt_0.1 | PASS | <work>/runs/bdt0/eval_ddt_0.1/evaluation.json |
| sculpting_ddt_0.3 | PASS | <work>/runs/bdt0/sculpt_ddt_0.3/sculpting.json |
| sculpting_ddt_0.1 | PASS | <work>/runs/bdt0/sculpt_ddt_0.1/sculpting.json |
| sculpting_raw_score | WAIVED | <work>/runs/bdt0/sculpt/sculpting.json |
| closure_kfold_0.5 | PASS | <work>/closure_kfold_0.5/closure.json |

### table

| Key | Value |
| --- | --- |
| N_FEATURES | 12 |
| N_FAIL | 0 |
| N_WARN | 2 |
| FAILED | none |
| WARNED | mass_corr:n_constituents,mass_over_pt |
| NEFF_SIG | 281665.5 |
| NEFF_BKG | 722302.8 |
| NEG_WEIGHT_FRAC | 0.0 |
| TOP_SINGLE_AUC | mass_over_pt:0.7772 |
| STATUS | PASS |

### training

| Key | Value |
| --- | --- |
| BACKEND | xgboost |
| N_TRAIN | 929956 |
| N_VAL | 309365 |
| N_TEST | 309494 |
| N_FEATURES | 12 |
| BEST_ITER | 470 |
| AUC_TRAIN | 0.81754 |
| AUC_VAL | 0.81177 |
| AUC_TEST | 0.81074 |
| AUC_GAP | 0.00679 |
| KS_P_SIG | 0.0124 |
| KS_P_BKG | 0.00134 |
| OVERTRAINED | 0 |
| TOP_FEATURES | mass_over_pt,n_constituents,rho,ch_pv0_ef,area |
| ONNX_MAX_ABS_DIFF | 3.73e-07 |
| ONNX_FRAC_DIFF | 0.0 |
| SECONDS | 41.6 |
| OUT_DIR | <work>/runs/bdt0 |
| STATUS | PASS |

### evaluation

| Key | Value |
| --- | --- |
| N_TEST_SIG | 88134 |
| N_TEST_BKG | 221360 |
| AUC_TEST | 0.81074 |
| AUC_ERR | 0.00124 |
| AUC_TRAIN | 0.81754 |
| AUC_GAP | 0.00679 |
| KS_P_SIG | 0.0124 |
| KS_P_BKG | 0.00134 |
| OVERTRAINED | 0 |
| SIG_EFF_AT_BKG_0.1 | 0.5253 |
| THR_AT_BKG_0.1 | 0.66084 |
| SIG_EFF_AT_BKG_0.01 | 0.1942 |
| THR_AT_BKG_0.01 | 0.90516 |
| SIG_EFF_AT_BKG_0.001 | 0.0499 |
| THR_AT_BKG_0.001 | 0.97105 |
| ECE | 0.0037 |
| AUC_CAT_MIN | 0.7225 |
| FAILED | none |
| STATUS | PASS |

### evaluation_ddt_0.5

| Key | Value |
| --- | --- |
| N_TEST_SIG | 88134 |
| N_TEST_BKG | 221360 |
| AUC_TEST | 0.77734 |
| AUC_ERR | 0.00117 |
| AUC_TRAIN | 0.78546 |
| AUC_GAP | 0.00813 |
| KS_P_SIG | 0.0031 |
| KS_P_BKG | 0.000411 |
| OVERTRAINED | 0 |
| SIG_EFF_AT_BKG_0.5 | 0.8415 |
| THR_AT_BKG_0.5 | 0.00181 |
| ECE | 0.3445 |
| AUC_CAT_MIN | 0.72267 |
| FAILED | none |
| STATUS | PASS |

### evaluation_ddt_0.3

| Key | Value |
| --- | --- |
| N_TEST_SIG | 88134 |
| N_TEST_BKG | 221360 |
| AUC_TEST | 0.76344 |
| AUC_ERR | 0.00117 |
| AUC_TRAIN | 0.77158 |
| AUC_GAP | 0.00813 |
| KS_P_SIG | 0.0046 |
| KS_P_BKG | 0.00302 |
| OVERTRAINED | 0 |
| SIG_EFF_AT_BKG_0.3 | 0.7114 |
| THR_AT_BKG_0.3 | 0.00282 |
| ECE | 0.4609 |
| AUC_CAT_MIN | 0.72276 |
| FAILED | none |
| STATUS | PASS |

### evaluation_ddt_0.1

| Key | Value |
| --- | --- |
| N_TEST_SIG | 88134 |
| N_TEST_BKG | 221360 |
| AUC_TEST | 0.75713 |
| AUC_ERR | 0.00115 |
| AUC_TRAIN | 0.76523 |
| AUC_GAP | 0.0081 |
| KS_P_SIG | 0.00542 |
| KS_P_BKG | 0.00477 |
| OVERTRAINED | 0 |
| SIG_EFF_AT_BKG_0.1 | 0.464 |
| THR_AT_BKG_0.1 | 0.00472 |
| ECE | 0.6597 |
| AUC_CAT_MIN | 0.7224 |
| FAILED | none |
| STATUS | PASS |

### sculpting

| Key | Value |
| --- | --- |
| N_BKG | 221360 |
| PEARSON_R | -0.0452 |
| DCOR | 0.1396 |
| R50 | 9.36 |
| INV_JSD_50 | 68.2 |
| CHI2_NDF_0.5 | 1.33 |
| P_0.5 | 0.11 |
| JSD_0.5 | 0.000169 |
| JSD_FLOOR_0.5 | 0.000132 |
| MAX_DEV_0.5 | 0.044 |
| VERDICT_0.5 | OK |
| N_SCULPTED | 0 |
| N_LOW_STAT | 0 |
| STATUS | PASS |

### sculpting_ddt_0.3

| Key | Value |
| --- | --- |
| N_BKG | 221360 |
| PEARSON_R | -0.1579 |
| DCOR | 0.2007 |
| R50 | 8.63 |
| INV_JSD_50 | 244.0 |
| CHI2_NDF_0.3 | 1.0 |
| P_0.3 | 0.466 |
| JSD_0.3 | 0.000147 |
| JSD_FLOOR_0.3 | 0.000151 |
| MAX_DEV_0.3 | 0.059 |
| VERDICT_0.3 | OK |
| N_SCULPTED | 0 |
| N_LOW_STAT | 0 |
| STATUS | PASS |

### sculpting_ddt_0.1

| Key | Value |
| --- | --- |
| N_BKG | 221360 |
| PEARSON_R | -0.1848 |
| DCOR | 0.2424 |
| R50 | 8.35 |
| INV_JSD_50 | 2842.2 |
| CHI2_NDF_0.1 | 1.56 |
| P_0.1 | 0.0278 |
| JSD_0.1 | 0.000525 |
| JSD_FLOOR_0.1 | 0.000367 |
| MAX_DEV_0.1 | 0.151 |
| VERDICT_0.1 | OK |
| N_SCULPTED | 0 |
| N_LOW_STAT | 0 |
| STATUS | PASS |

### sculpting_raw_score

| Key | Value |
| --- | --- |
| N_BKG | 221360 |
| PEARSON_R | 0.3771 |
| DCOR | 0.4193 |
| R50 | 11.37 |
| INV_JSD_50 | 7.2 |
| CHI2_NDF_0.5 | 876.74 |
| P_0.5 | 0.0 |
| JSD_0.5 | 0.123 |
| JSD_FLOOR_0.5 | 0.000134 |
| MAX_DEV_0.5 | 0.579 |
| VERDICT_0.5 | SCULPTED |
| CHI2_NDF_0.3 | 732.99 |
| P_0.3 | 0.0 |
| JSD_0.3 | 0.11 |
| JSD_FLOOR_0.3 | 0.000148 |
| MAX_DEV_0.3 | 0.855 |
| VERDICT_0.3 | SCULPTED |
| CHI2_NDF_0.1 | 609.88 |
| P_0.1 | 0.0 |
| JSD_0.1 | 0.134 |
| JSD_FLOOR_0.1 | 0.000322 |
| MAX_DEV_0.1 | 1.48 |
| VERDICT_0.1 | SCULPTED |
| N_SCULPTED | 3 |
| N_LOW_STAT | 0 |
| STATUS | FAIL |

### closure

| Key | Value |
| --- | --- |
| TEST | kfold |
| N_BINS | 5 |
| CHI2_NDF | 0.883 |
| P_VALUE | 0.491 |
| PULL_INCL | -0.004 |
| PULL_MEAN | -0.005 |
| PULL_RMS | 0.94 |
| MAX_ABS_PULL | 1.513 |
| NONCLOSURE | -0.0 |
| NONCLOSURE_ERR | 0.0035 |
| NONCLOSURE_SYST | 0.0035 |
| THRESHOLD | 0.66085 |
| AUC_MEAN | 0.81144 |
| AUC_STD | 0.00124 |
| AUC_MIN | 0.81005 |
| AUC_MAX | 0.81332 |
| FAILED | none |
| STATUS | PASS |

### closure_kfold_0.5

| Key | Value |
| --- | --- |
| TEST | kfold |
| N_BINS | 5 |
| CHI2_NDF | 1.065 |
| P_VALUE | 0.377 |
| PULL_INCL | -0.0 |
| PULL_MEAN | -0.0 |
| PULL_RMS | 1.032 |
| MAX_ABS_PULL | 1.22 |
| NONCLOSURE | -0.0 |
| NONCLOSURE_ERR | 0.0012 |
| NONCLOSURE_SYST | 0.0012 |
| THRESHOLD | 0.30652 |
| AUC_MEAN | 0.81144 |
| AUC_STD | 0.00124 |
| AUC_MIN | 0.81005 |
| AUC_MAX | 0.81332 |
| FAILED | none |
| STATUS | PASS |
