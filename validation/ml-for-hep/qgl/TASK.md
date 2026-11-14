# TASK: quark/gluon jet BDT (CMS Open Data simulation, 2016 UL NanoAODv9)

Full definitions in `specification.md`; this file is the ML task contract.

- **Unit**: one AK4 jet (all selected jets of an event; pT 30-1000 GeV, |eta| < 2.5, tight ID,
  `Jet_genJetIdx >= 0`).
- **Signal (label 1)**: quark jets, |`Jet_partonFlavour`| in {1, 2, 3}.
- **Background (label 0)**: gluon jets, `Jet_partonFlavour` == 21.
  c, b and flavour-0 jets excluded and counted. Cross-check table: quark = {1..5}.
- **Samples**: QCD_HT700to1000, HT1000to1500, HT1500to2000, HT2000toInf
  (RunIISummer20UL16NanoAODv9, madgraphMLM-pythia8), 8, 4, 2, 2 files, 30 000 events per file at most.
  No data. Z+jets not used.
- **Weights**: physics weight = sigma x L x genWeight / sum(genWeight read), L = 1 pb^-1, sigma from
  `validation/dijet-2016/specification.md`; training weight = |w|, classes balanced (script default).
  No pT/eta flattening (see specification, "Weights and reweighting").
- **Split**: fold = event % 5 (all jets of one event in one fold). Train 0,1,2; validation 3; test 4.
- **Inputs (12)**: `n_constituents, ch_had_ef, ne_had_ef, ch_em_ef, ne_em_ef, mu_ef, ch_pv0_ef,
  area, mass_over_pt, n_muons, n_electrons, rho`.
- **Observers (not inputs)**: `obs_pt`, `obs_eta`, `obs_abseta`, `obs_qgl` (Jet_qgl),
  `obs_deepjet_qg` (Jet_btagDeepFlavQG), `obs_jet_idx`.
- **Use of the score**: a cut (quark selection) in the range above. Performance is quoted with
  per-bin working points; if a single score cut sculpts the gluon pT spectrum, the cut is made
  pT-dependent with a DDT map (`score_ddt > 0`, gluon efficiency 0.5, 0.3 or 0.1).
- **Target metric**: gluon rejection at 50% quark efficiency per pT x |eta| bin (also at 70%, and quark
  efficiency at 10% gluon efficiency); AUC as a proxy. Compared with `Jet_qgl` and
  `1 - Jet_btagDeepFlavQG` on the same test jets.
- **Acceptance**: `model_card.py` READY=1 with checks table, training, evaluation, sculpting
  (score vs `obs_pt`, gluon efficiency 0.5/0.3/0.1), closure (k-fold, 5 rotations); default
  thresholds of every script, unchanged; AUC_TEST < 0.99; at least 200 000 jets per class.
- **Assumptions**: per-bin working points; Jets with `Jet_qgl` = -1 (undefined) kept.
  Open Data simulation study, not a CMS result.
