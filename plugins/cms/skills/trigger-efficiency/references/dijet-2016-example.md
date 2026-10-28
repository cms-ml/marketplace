# Worked example: 2016 b-tagged dijet trigger turn-on

Read this reference when setting up a jet/HT trigger efficiency for a
high-mass dijet (or similar all-hadronic) analysis, or when you want numbers
to compare a new measurement against. It summarises what the
`cms-analysis-coder` agent did in `validation/dijet-2016/` (October 2026,
cmslpc, LCG_109).

Contents:

1. Inputs and selection
2. Paths
3. Method and rule
4. Results
5. Decisions worth copying

## 1. Inputs and selection

- Data: JetHT Run2016G + Run2016H, `UL2016_MiniAODv2_NanoAODv9-v1`, all
  142 files (70 + 72) from `root://eospublic.cern.ch//eos/opendata/cms/`,
  16.4 fb⁻¹ after the golden JSON (Open Data records 14220 and 1059).
- Offline selection in both numerator and denominator: golden JSON, event
  filters (`Flag_goodVertices`, `Flag_globalSuperTightHalo2016Filter`,
  `Flag_HBHENoiseFilter`, `Flag_HBHENoiseIsoFilter`,
  `Flag_EcalDeadCellTriggerPrimitiveFilter`, `Flag_BadPFMuonFilter`,
  `Flag_BadPFMuonDzFilter`, `Flag_eeBadScFilter`), two leading AK4 jets with
  pT > 30 GeV and tight ID (`Jet_jetId & 2`), both |η| < 2.4, |Δη_jj| < 1.1.
- Variable: m_jj of the two leading jets, in the CMS dijet bins (`DIJET_EDGES`
  in [../scripts/turnon.py](../scripts/turnon.py)).

## 2. Paths

| Role             | Paths                                                                                                                                     |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Signal OR        | `HLT_PFHT900`, `HLT_PFHT800` (2016G only), `HLT_PFJet450`, `HLT_PFJet500`, `HLT_CaloJet500_NoJetID`, `HLT_AK8PFJet450`, `HLT_AK8PFJet500` |
| Reference (main) | `HLT_PFJet260` (prescaled)                                                                                                                |
| Cross-checks     | `HLT_PFHT475`, `HLT_PFJet400`                                                                                                             |

`list_hlt_paths.py` on one 2016G and one 2016H file showed the menus differ:
`HLT_PFHT800` exists only in the G file.

## 3. Method and rule

Counts were accumulated per file in condor skims and summed. ε = num/den per
bin, with 68% Clopper-Pearson intervals. The threshold is the lowest bin edge
such that every populated bin above it has a CP upper bound ≥ 0.995 and the
pooled efficiency above it is ≥ 0.995. The plateau is the pooled efficiency
above the threshold.

## 4. Results (from `summary.json`)

| Reference    | Plateau above 1058 GeV      | Ref. events above | Own threshold |
| ------------ | --------------------------- | ----------------- | ------------- |
| HLT_PFJet260 | 0.99928 (+0.00012 −0.00015) | 45 776            | 1058 GeV      |
| HLT_PFHT475  | 0.99931                     | 23 160            | 1058 GeV      |
| HLT_PFJet400 | 0.99941                     | 412 046           | 1058 GeV      |

All three references agree. The 6-file `turnon.py --demo` (no golden JSON or
filters, target 0.99) also gives 1058 GeV, with plateau 0.9987.

For comparison, the Run 3 b-tagged dijet analysis that this validation
follows (A. Mankel, APS 2026) cuts at m_jj > 1455 GeV, because its trigger
thresholds are higher.

## 5. Decisions worth copying

- Use the offline analysis selection in the denominator, including |Δη_jj|.
- Use three references. Disagreement means a biased reference.
- Use the threshold from data for the fit range (here 1058–8152 GeV). Apply
  no trigger to MC; require m_jj above the threshold instead.
- Store num/den per bin (not ε) in `summary.json`, so HEPData and plots can be
  rebuilt without rerunning.
