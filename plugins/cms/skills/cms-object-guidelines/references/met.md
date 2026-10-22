# MET — CMS JME MET recommendations (NanoAOD / MiniAOD)

Read this reference when choosing a MET estimator, applying or recomputing Type-1 / XY / recoil corrections, propagating object uncertainties to MET, applying MET noise filters (needed in **every** analysis), using DeepMET or MET significance, or investigating large-MET tails.

Source: CMS JME/JMAR MET recommendations, https://cms-jme-jmar.docs.cern.ch/recommendations/met/ — pages "Missing transverse momentum" (overview), "MET corrections", "Noise filters", "DeepMET", "MET significance", "MET scanners" (retrieved 22 Oct 2026) | Campaigns: Run2 UL 2016preVFP/2016postVFP/2017/2018; Run3 2022–2026. Units: GeV.

**Shared with jets:** JEC/JER tags and JES/JER correlations → `jets-jerc.md`; Jet ID, jet veto maps → `jets.md`.

## Contents
1. Which MET to use
2. Estimators and where they are stored
3. Noise filters (all analyses)
4. Corrections: Type-1, JER, XY, recoil
5. Uncertainties
6. DeepMET
7. MET significance
8. Large-MET tails / scanning
9. Pitfalls

## 1. Which MET to use
| Run | Default | NanoAOD | MiniAOD |
| --- | --- | --- | --- |
| Run 3 | **Type-1 PUPPI MET** | `PuppiMET_*` | `slimmedMETsPuppi` |
| Run 2 | **Type-1 PF MET** | `MET_*` (v9, v12); `PFMET_*` (v15) | `slimmedMETs` |
| Either | DeepMET (response / resolution tune): available, **not** the default | `DeepMETResponseTune_*`, `DeepMETResolutionTune_*` | packed in `slimmedMETs` |

Name a MET quantity by its input plus the corrections applied to it, e.g. "raw PF MET" or "Type-1 + XY corrected PUPPI MET".
Branches and stored variations depend on the production, so check the NanoAOD autoDoc for your sample (https://cms-xpog.docs.cern.ch/autoDoc/). Raw MET is `RawMET_*` (v15: `RawPFMET_*`) / `RawPuppiMET_*`. Low-pT jets for Type-1 are in `CorrT1METJet_*`. In v15, `PuppiMET` stores only unclustered variations (no JES/JER shifts), so propagate jet variations yourself. Look up exact branches with the `nanoaod-branches` skill.

## 2. Estimators
```text
MET_vec = -Σ_i w_i * pT_vec_i     # sum over the inputs; default w_i = 1
```
`sumEt` (ΣET) is the scalar sum of input ET, not an imbalance.

| Estimator | Inputs / weights |
| --- | --- |
| PF MET | all PF candidates, w = 1 |
| PUPPI MET | PF candidates × **no-lepton** PUPPI weight (MiniAOD: `puppiWeightNoLep()`). PUPPI jets use the regular PUPPI weight. |
| CHS MET | PF MET on CHS candidates: drop charged hadrons from PU, keeping a PU-assigned one only if vertex index ≤ 2 and \|dz(PV)\| < 0.2 |
| Track MET | charged candidates (h±, e, μ) assigned to the PV (`pvAssociationQuality` requirement) |
| Calo MET | calorimeter deposits (not PF-based) |
| DeepMET | DNN per-candidate weights (§6) |

In MiniAOD, Calo, CHS, Track and DeepMET are packed into `slimmedMETs` (`pat::MET` accessors).
PF `pdgId` 1 and 2 are HF hadron and HF EM (`h_HF`, `egamma_HF`), not quarks.
Pileup adds no mean MET but broadens the resolution and fills the tails.

## 3. Noise filters
**Apply to data and MC in every analysis, even analyses that don't use MET.** Use the stored flags unless a note below says to rerun. Validate the filter efficiency on signal MC, especially for unusual detector signatures or very energetic objects.
- **NanoAOD:** AND the individual `Flag_*` branches. **Never use `Flag_METFilters`**: it includes deprecated filters, and it was removed in NanoAODv15.
- **MiniAOD:** the decisions are in `TriggerResults` of the `PAT` process.

| Flag | Run2 UL (2016–2018) | Run3 (2022–2026) |
| --- | --- | --- |
| `Flag_goodVertices` | ✓ | ✓ |
| `Flag_globalSuperTightHalo2016Filter` | ✓ | ✓ |
| `Flag_EcalDeadCellTriggerPrimitiveFilter` | ✓ | ✓ |
| `Flag_BadPFMuonFilter` | ✓ | ✓ |
| `Flag_BadPFMuonDzFilter` | ✓ (UL MiniAODv1: rerun, see below) | ✓ |
| `Flag_eeBadScFilter` | ✓ | ✓ |
| `Flag_hfNoisyHitsFilter` | optional (UL MiniAODv2 only) | ✓ |
| `Flag_HBHENoiseFilter`, `Flag_HBHENoiseIsoFilter` | ✓ | not required |
| `Flag_ecalBadCalibFilter` | 2017, 2018 only (not 2016) | 2024: stored flag; 2022–23 prompt: special handling below; 2025–26: under review |
| `Flag_BadChargedCandidateFilter` | **not recommended** | — |

```python
# NanoAOD: build the filter mask from individual flags (choose the list for your era from the table)
RUN3 = ["goodVertices", "globalSuperTightHalo2016Filter", "EcalDeadCellTriggerPrimitiveFilter",
        "BadPFMuonFilter", "BadPFMuonDzFilter", "hfNoisyHitsFilter", "eeBadScFilter", "ecalBadCalibFilter"]
pass_filters = np.logical_and.reduce([events.Flag[f] for f in RUN3])
```

**2022–2023 prompt-reco ECAL bad crystal (detector ID 838871812).** Don't use the stored `Flag_ecalBadCalibFilter` for the affected prompt data. Re-reconstructed datasets don't need this. A second 2022 crystal is covered by the jet veto maps.
- *NanoAOD (data only, not MC; loses < 0.2% of good events):* for runs 362433–367144, reject the event if `PuppiMET_pt > 100` and any AK4 jet (no `Jet_jetId` requirement) has `Jet_pt > 50`, `-0.5 < Jet_eta < -0.1`, `-2.1 < Jet_phi < -1.8`, (`Jet_neEmEF > 0.9` or `Jet_chEmEF > 0.9`), and Δφ(PuppiMET, jet) > 2.9.

```python
# Transcribed from the JME noise-filter page; not run yet.
J = events.Jet
dphi = np.abs((J.phi - events.PuppiMET.phi + np.pi) % (2 * np.pi) - np.pi)
bad = (J.pt > 50) & (J.eta > -0.5) & (J.eta < -0.1) & (J.phi > -2.1) & (J.phi < -1.8) \
      & ((J.neEmEF > 0.9) | (J.chEmEF > 0.9)) & (dphi > 2.9)
runs = (events.run >= 362433) & (events.run <= 367144)
veto = runs & (events.PuppiMET.pt > 100) & ak.any(bad, axis=1)   # data only
```
- *MiniAOD (data and MC):* rerun the filter with the crystal:
```python
process.load("RecoMET.METFilters.ecalBadCalibFilter_cfi")
process.ecalBadCalibReducedMINIAODFilter = cms.EDFilter("EcalBadCalibFilter",
    EcalRecHitSource=cms.InputTag("reducedEgamma:reducedEBRecHits"),
    ecalMinEt=cms.double(50.0), baddetEcal=cms.vuint32([838871812]),
    taggingMode=cms.bool(True), debug=cms.bool(False))
```

**Run2 UL MiniAODv1, BadPFMuonDz** (it's stored in MiniAODv2). Rerun with CMSSW ≥ 10_6_X:
```python
from RecoMET.METFilters.BadPFMuonDzFilter_cfi import BadPFMuonDzFilter
process.BadPFMuonFilterUpdateDz = BadPFMuonDzFilter.clone(
    muons=cms.InputTag("slimmedMuons"), vtx=cms.InputTag("offlineSlimmedPrimaryVertices"),
    PFCandidates=cms.InputTag("packedPFCandidates"), minDzBestTrack=cms.double(0.5),
    taggingMode=cms.bool(True))
```

## 4. Corrections
Apply all corrections to the components `px = pt*cos(phi)`, `py = pt*sin(phi)` (NanoAOD stores only `pt`/`phi`), then recompute `pt = hypot(px, py)` and `phi = atan2(py, px)`.

| Correction | What it does | Use |
| --- | --- | --- |
| Type-1 | replace raw AK4 jet contributions by calibrated jets (PF or PUPPI MET) | **mandatory** |
| JER propagation | propagate MC AK4 JER smearing to MET | optional (jet smearing itself is mandatory) |
| XY shift | remove mean p_x/p_y offsets (φ modulation, pileup-dependent) | optional |
| Recoil calibration | match the simulated hadronic-recoil response/resolution to data | optional, analysis-specific |

### Type-1
- The stored Type-1 MET uses the **JEC from production time**. If you apply a different JEC to your jets, recompute Type-1 MET and its JEC variations from the same corrected jets. Never mix the two.
- Propagate only the AK4 jets used by Type-1. Never propagate AK8 or other jet collections.
- If you propagate JER, use the nominal smearing applied to each Type-1 jet.
- **NanoAOD:** the CMSSW tool doesn't run on NanoAOD. Start from raw MET and use **both** `Jet` and `CorrT1METJet` (which holds the low-pT jets); `Jet` alone is incomplete. Apply the same Type-1 prescription to nominal and varied jets. Jet thresholds, EM-fraction and muon-subtraction rules: follow the JERC Type-1 MET page.
- **MiniAOD:** use the CMSSW MET corrections and uncertainties tool (`runMetCorAndUncFromMiniAOD`) with the chosen PF/PUPPI MET, AK4 jets, JEC and JER. It can reapply JEC.

### XY corrections
These must match the full MET input (PF vs PUPPI) and the data period or MC campaign. They aren't needed in every analysis. When you apply them, validate both the MET pT and MET φ distributions. On MiniAOD, use the CMSSW MET tool.

| Campaign | File (JME correctionlib) |
| --- | --- |
| 2016preVFP / 2016postVFP / 2017 / 2018 UL | `met.json.gz` (per-campaign `Run2-<era>-UL-NanoAODv9`) |
| 22CDSep23 / Summer22 | `met_xyCorrections_2022_2022.json.gz` |
| 22EFGSep23 / Summer22EE | `met_xyCorrections_2022_2022EE.json.gz` |
| 23CSep23 / Summer23 | `met_xyCorrections_2023_2023.json.gz` |
| 23DSep23 / Summer23BPix | `met_xyCorrections_2023_2023BPix.json.gz` |

None are listed for 2024–2026. Correction keys and inputs aren't given in the source, so list them from the payload (`correction summary <file>`) before use.

### Recoil calibration
Hadronic recoil (all vectors in the transverse plane):

```text
u_T    = -(MET_vec + q_T)       # q_T = pT vector of the reference system (dilepton or photon)
u_par  = u_T · q_T / |q_T|      # component along q_T;  response = -<u_par>/|q_T| (≈ 1 if perfect)
u_perp = u_T · n_perp           # component perpendicular to q_T
```
This follows from momentum balance: everything visible except the reference system is the hadronic recoil, so `MET_vec = -(q_T + u_T)`. The mean of `u_par` probes the response, and the widths of `u_par` and `u_perp` probe the resolution. Some software uses the opposite sign for `u_T`, so check the convention.
- It works for any MET definition (PF, PUPPI, DeepMET, custom). Apply it after Type-1, **to MC only, once**.
- Derive it in Z→ℓℓ or γ+jets, parameterized in qT (and in categories such as N_jets, pileup or boson rapidity), never as one global set. Methods: fit `u_par` / `u_perp` and transform them, or map the cumulative distributions (this handles non-Gaussian shapes).
- Typical targets are Z→νν and W→ℓν. For different topologies (QCD multijet, ttbar), validate the transfer and add an extrapolation uncertainty.
- Use a calibration only if it matches the MET definition, the corrections applied before it, the era/campaign, the reference process and categories, the method, the sign convention and the uncertainty model.
- Don't also apply JER smearing unless the calibration was derived on JER-smeared MET.
- Validate closure for `u_par`, `u_perp`, MET pT and MET φ in every category.
- Uncertainties: fit covariance (eigenvariations), model and qT parameterization, control-sample background, reference-object scale and resolution, and process extrapolation. Cross-check under JEC and unclustered variations without double counting.

## 5. Uncertainties
| Variation | Use |
| --- | --- |
| JEC (each source) → MET | **mandatory** |
| JER → MET | optional |
| e / γ / μ / τ → MET | optional |
| Unclustered energy | optional |

- **Correlation:** a jet or object shift and its MET shift are **one** nuisance parameter, not two. Use the same JEC source and the same JER up/down variation for jets and MET.
- **No double counting:** an object propagated on its own must not also be varied through jets or the unclustered term. There is no single process-independent MET uncertainty.
- **Object shifts:** the legacy CMSSW tool shifts the full four-momentum by 1 ± δ. These are average effects; use the current POG object uncertainties instead where available.

| Object | δ |
| --- | --- |
| Electron | 0.6% (\|η\| < 1.479), 1.5% otherwise |
| Photon | 1.0% (\|η\| < 1.479), 2.5% otherwise |
| Muon | 0.2% (pT < 100 GeV), 5% otherwise |
| Tau | 3% |

Unclustered energy (legacy Run 2): scale every remaining PF candidate by 1 ± δ, all in the same direction. pT and E are in GeV, θ = 2·atan(exp(−η)).

| PF component | δ |
| --- | --- |
| Charged hadron | `sqrt((0.00009*pT)**2 + (0.0085/sqrt(sin(theta)))**2)` |
| Neutral hadron, \|η\| < 1.3 | `min(0.25, sqrt(0.64/E + 0.0025))` |
| Neutral hadron, \|η\| ≥ 1.3 | `min(0.30, sqrt(1/E + 0.0016))` |
| Photon | `sqrt(0.0009/E + 0.000001)` |
| HF hadron / EM | `sqrt(1/E + 0.0025)` |

The NanoAOD MET table stores some unclustered shifts as deltas. Check your sample's autoDoc for which ones.

## 6. DeepMET
- **What it is:** a DNN on all `packedPFCandidates` that predicts per-candidate weights and biases for p_x and p_y. Inputs: `dxy`, `dz`, `eta`, `mass`, `pt`, `puppiWeight`, `px`, `py`, `charge`, `pdgId`, `fromPV`.
- **Run 2 training:** 2016 and 2018 models, trained on DY+jets and ttbar. Validated in DY, Z→νν, W→ℓν and data. Compared with PF/PUPPI MET it has similar response, better resolution and less pileup dependence (CMS-JME-24-001).
- **Tunes:** two of them, **with separate corrections and systematics**.

| Tune | Optimizes | NanoAOD | MiniAOD (`slimmedMETs`) |
| --- | --- | --- | --- |
| Response | response, still better resolution than PF/PUPPI | `DeepMETResponseTune_pt`, `_phi` | `met.corPt(pat::MET::RawDeepResponseTune)`, `corPhi(...)` |
| Resolution | resolution (lower response) | `DeepMETResolutionTune_pt`, `_phi` | `met.corPt(pat::MET::RawDeepResolutionTune)`, `corPhi(...)` |

If the MiniAOD has no DeepMET, run the official DeepMET producers with the config and model for the CMSSW era. The UL-v1 hard-coded graph recipe from the legacy TWiki is not general.

## 7. MET significance
```text
S = MET_vec^T · V^(-1) · MET_vec     # MET_vec = (px, py) of the MET
```
V is the 2×2 MET covariance built from jet resolutions and unclustered activity (CMS-JME-13-003).
- With zero true MET and Gaussian resolution, S follows χ² with 2 degrees of freedom. A large S means a fluctuation is unlikely; it does **not** by itself prove genuine invisible momentum.
- Under JEC/JER variations, **recompute S** from the varied jets and MET (JER enters V). Don't treat it as an independent uncertainty.
- No campaign-specific application or uncertainty recipe is defined yet.
- CMSSW: `METSignificance.cc`, `METSignificanceProducer.cc` (output `METSignificance`, `METCovariance`), with configs `METSignificance_cfi.py`, `METSignificanceObjects_cfi.py`, `METSignificanceParams_cfi.py`.

## 8. Large-MET tails / scanning
Large MET alone doesn't establish invisible particles. Beam halo, for example, can fake a ~10 TeV MET with a jet of uniform φ spread in η plus CSC hits.
- **Which plots:** PF and PUPPI MET, significance vs MET, N_PV, MET φ, and per-filter and combined filter pass fractions.
- **How to check filters:** run them in tagging mode (no rejection), store the decisions, and follow up rate changes and the failing events.
- **Where it comes from:** classify odd events by source (μ, e/γ, jets, calorimeter noise, beam background, PF reconstruction).
- **Who to tell:** report serious problems to cms-met-scanning@cern.ch.

## 9. Pitfalls
- `Flag_METFilters` (aggregate) — don't use it. AND the individual flags for your era.
- Skipping noise filters because the analysis "doesn't use MET": they are required everywhere.
- `Flag_ecalBadCalibFilter` on 2016 UL (not recommended) or on 2022–23 prompt data (use the crystal veto instead). `Flag_BadChargedCandidateFilter` in UL (not recommended). HBHE flags required in Run 3 (they aren't).
- Stored Type-1 MET combined with re-corrected jets (JEC mismatch). Type-1 recomputed on NanoAOD from `Jet` only (missing `CorrT1METJet`).
- Propagating AK8 jets to MET, or treating jet and MET JEC shifts as separate nuisances.
- PF MET in Run 3 or PUPPI MET in Run 2 as the default. Run-2 PF XY corrections on PUPPI MET, or the reverse.
- Recoil calibration plus independent JER propagation, recoil applied to data, or recoil applied twice.
- Mixing DeepMET response- and resolution-tune corrections or uncertainties.
- Treating MET significance as an independent systematic instead of recomputing it.
