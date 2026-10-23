# muons - CMS POG recommendations (NanoAOD)

Source: https://muon-wiki.docs.cern.ch/guidelines/ | Campaigns: Run2 UL 2016preVFP/2016postVFP/2017/2018; Run3 2022/2022EE/2023/2023BPix/2024/2025

## 1. NanoAOD branches (`Muon_*`)
Branch source: https://cms-xpog.docs.cern.ch/autoDoc/NanoAODv15/2024/doc_TTH-Hto2G_Par-M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2.html#Muon (NanoAOD v15, 2024 MC; older versions may lack some branches, e.g. `promptMVA`/`softMvaRun3` need >= v14, `mvaMuID` >= v11).

`nMuon` = slimmedMuons after `pt > 15 || (pt > 3 && (passed('CutBasedIdLoose') || passed('SoftCutBasedId') || passed('SoftMvaId') || passed('CutBasedIdGlobalHighPt') || passed('CutBasedIdTrkHighPt')))`.

| Group | Branches |
| --- | --- |
| Kinematics | `pt`, `eta`, `phi`, `mass`, `charge`, `pdgId`, `ptErr`, `tightCharge` (0 fail, 2 pass; pterr/pt of muonBestTrack) |
| TuneP | `tunepRelPt` (tunePpt/pt), `tuneP_pterr`, `tuneP_charge`, `bestTrackType` (1=inner, 2=STA, 3=global, 4=TPFMS, 5=Picky, 6=DYT) |
| Beamspot-constrained | `bsConstrainedPt`, `bsConstrainedPtErr`, `bsConstrainedChi2` |
| Impact parameter | `dxy`, `dxyErr`, `dz`, `dzErr` (signed, wrt first PV, cm); `dxybs`, `dxybsErr` (wrt beam spot); `ip3d`, `sip3d`, `ipLengthSig`, `IPx`, `IPy`, `IPz`, `VXBS_Cov00`, `VXBS_Cov03`, `VXBS_Cov33` |
| Reco type / quality | `isGlobal`, `isTracker`, `isStandalone`, `isPFcand`, `highPurity`, `nStations`, `nTrackerLayers`, `segmentComp`, `inTimeMuon` |
| Cut-based IDs (Bool) | `looseId`, `mediumId`, `mediumPromptId`, `tightId`, `softId`, `triggerIdLoose` |
| High-pT ID (UChar) | `highPtId`: 1 = tracker high pT, 2 = global high pT (includes tracker high pT) |
| MVA IDs | `mvaMuID` (score), `mvaMuID_WP` (1=MVAIDwpMedium, 2=MVAIDwpTight), `promptMVA` (ex-mvaTTH), `softMva`, `softMvaId`, `softMvaRun3`, `mvaLowPt`, `pnScore_prompt`, `pnScore_heavy`, `pnScore_light`, `pnScore_tau` (PNet) |
| Isolation values | `pfRelIso03_all`, `pfRelIso03_chg`, `pfRelIso04_all` (deltaBeta-corrected), `miniPFRelIso_all`, `miniPFRelIso_chg`, `tkRelIso` (deltaR 0.3, uses TuneP pT) |
| Isolation WPs (UChar) | `pfIsoId` (1=VeryLoose ... 6=VeryVeryTight), `tkIsoId` (1=Loose, 2=Tight), `miniIsoId` (1=Loose ... 4=VeryTight), `multiIsoId` (1=Loose, 2=Medium), `puppiIsoId` (1=Loose, 2=Medium, 3=Tight) |
| Jet association | `jetIdx`, `jetRelIso` (1/ptRatio-1, -1 if none), `jetPtRelv2`, `jetNDauCharged`, `jetDF` (DeepJet of associated jet) |
| Links / MC | `fsrPhotonIdx`, `svIdx`, `genPartIdx`, `genPartFlav` (1 prompt, 15 from tau, 5 from b, 4 from c, 3 light/unknown, 0 unmatched) |

## 2. IDs and isolation
### Cut-based IDs
| ID | Branch | Definition | Use case |
| --- | --- | --- | --- |
| Loose | `looseId` | PF muon AND (global OR arbitrated tracker) | very efficient, prompt + HF + light decays; add IP cuts for prompt signals |
| Medium | `mediumId` | Loose + innerTrack validFraction > 0.8 (0.49 for runs 272728-278808, 2016 HIP; NanoAOD already handles it) + segComp > 0.303 if good global (global chi2/ndof < 3, chi2LocalPosition < 12, trkKink < 20), else segComp > 0.451 | prompt + HF; add IP cuts for prompt signals |
| Tight | `tightId` | global, PF, global chi2/ndof < 10, >=1 valid muon hit, >1 matched station, \|dxy\| < 0.2 cm, \|dz\| < 0.5 cm, >0 pixel hits, >5 tracker layers | standard prompt; inefficient for pT > 200 GeV |
| HighPt | `highPtId == 2` | global, >=1 muon hit (global or TuneP), >1 station (or 1 with tracker-muon exceptions), TuneP ptErr/pt < 0.3, \|dxy\| < 0.2, \|dz\| < 0.5, >0 pixel hits, >5 layers. **Not PF.** Use pT = `pt * tunepRelPt` | pT > 200 GeV |
| TrkHighPt | `highPtId >= 1` | tracker muon, >1 station, rest as HighPt; worse resolution | close-by boosted muons (Z -> mumu) |
| Soft | `softId` | `TMOneStationTight`, >5 tracker layers, >0 pixel layers, highPurity, \|dxy\| < 0.3, \|dz\| < 20. **Not PF.** | low-pT / B physics, non-PF analyses only |
| TriggerIdLoose | `triggerIdLoose` | `TMOneStationTight`, >5 layers, >0 pixel layers, global chi2 < 20 if global, >1 station or expected stations < 2 | HLT-like ID (from 2018) |
| In-time | `inTimeMuon` | rejects out-of-time muons (RPC time, else DT/CSC) | needed only for selections looser than Tight |

### MVA IDs
| MVA | Branch | WPs | Validity |
| --- | --- | --- | --- |
| Muon MVA (pT > 10) | `mvaMuID`, `mvaMuID_WP` | Medium > 0.08, Tight > 0.2 | NanoAOD >= v11; final training CMSSW_13_2_X+ |
| Prompt MVA (includes isolation) | `promptMVA` (NanoAOD >= v14), `mvaTTH` (<= v13) | not given by POG | Run3 retraining from NanoAOD v14 |
| Soft MVA | `softMva` / `softMvaId` (> 0.58) Run2; `softMvaRun3` Run3 | Run3: Soft > 0.47, Loose > 0.63, Medium > 0.74, Tight > 0.83 | Run3 score from NanoAOD v14, 2024 Data/MC |
| Low-pT MVA | `mvaLowPt` | - | Run2 MC training, preselection `pt>5 && looseID && sip3D<4. && abs(dxy)<0.5 && abs(dz) < 1` |

### Isolation working points
| Type | WP branch | Cuts | Pair with |
| --- | --- | --- | --- |
| PF deltaR 0.4, deltaBeta (`pfRelIso04_all`) | `pfIsoId` 1..6 | VeryLoose 0.4, Loose 0.25, Medium 0.20, Tight 0.15, VeryTight 0.10, VeryVeryTight 0.05 | Loose/Medium/Tight IDs |
| Tracker deltaR 0.3 (`tkRelIso`) | `tkIsoId` 1..2 | Loose 0.10, Tight 0.05 | HighPt IDs |
| Mini-iso (`miniPFRelIso_all`) | `miniIsoId` 1..4 | Loose 0.40, Medium 0.20, Tight 0.10, VeryTight 0.05 | boosted topologies |
| Multi-iso | `multiIsoId` | only Medium is meaningful | - |

## 3. Corrections
Choose ONE pT regime for the whole analysis based on where most muons are: low (< 30 GeV, J/psi SFs), medium (30-200 GeV, Z SFs), high (> 200 GeV, HighPt SFs). Signal spanning 50 GeV-1 TeV -> high-pT set everywhere (valid from pT = 50 GeV).

### Where to get files (correctionlib)
- CVMFS: `/cvmfs/cms-griddata.cern.ch/cat/metadata/MUO/<tag>/latest/`
- GitLab: `https://gitlab.cern.ch/cms-nanoAOD/jsonpog-integration/-/blob/master/POG/MUO/<folder>/<file>`
- Docs: `https://cms-analysis-corrections.docs.cern.ch/corrections/MUO/<tag>/latest/`
- MuonPOG-native (everything, incl. items not yet in XPOG): `https://gitlab.cern.ch/cms-muonPOG/muonefficiencies` (`Run2/UL/<era>/...`, `Run3/<era>/...`)

| Era | `<folder>` | `<tag>` | `muon_Z.json.gz` | `muon_JPsi.json.gz` | `muon_HighPt.json.gz` | pT scale/smearing |
| --- | --- | --- | --- | --- | --- | --- |
| 2016preVFP | `2016preVFP_UL` | `Run2-2016preVFP-UL-NanoAODv9` | RECO, ID, ISO, HLT | ID | RECO, IDISO, HLT | Rochester `Run2.v5` |
| 2016postVFP | `2016postVFP_UL` | `Run2-2016postVFP-UL-NanoAODv9` | RECO, ID, ISO, HLT | ID | RECO, IDISO, HLT | Rochester `Run2.v5` |
| 2017 | `2017_UL` | `Run2-2017-UL-NanoAODv9` | RECO, ID, ISO, HLT | ID | RECO, IDISO, HLT | Rochester `Run2.v5` |
| 2018 | `2018_UL` | `Run2-2018-UL-NanoAODv9` | RECO, ID, ISO, HLT | ID | RECO, IDISO, HLT | Rochester `Run2.v5` |
| 2022 (BCD) | `2022_Summer22` | `Run3-22CDSep23-Summer22-NanoAODv12` | ID, ISO, HLT | ID | RECO, IDISO, HLT | `muon_scalesmearing.json.gz` |
| 2022EE (EFG) | `2022_Summer22EE` | `Run3-22EFGSep23-Summer22EE-NanoAODv12` | ID, ISO, HLT | ID | RECO, IDISO, HLT | same |
| 2023 (C) | `2023_Summer23` | `Run3-23CSep23-Summer23-NanoAODv12` | ID, ISO, HLT | ID | RECO, IDISO, HLT | same |
| 2023BPix (D) | `2023_Summer23BPix` | `Run3-23DSep23-Summer23BPix-NanoAODv12` | ID, ISO, HLT | ID | RECO, IDISO, HLT | same |
| 2024 | - | `Run3-24CDEReprocessingFGHIPrompt-Summer24-NanoAODv15` | ID, ISO, HLT | MuonPOG repo only | MuonPOG repo only | not available |
| 2025 | - | `Run3-25Prompt-Summer24-NanoAODv15` | ID, ISO, HLT | - | - | not available |

Rochester: https://twiki.cern.ch/twiki/bin/view/CMS/RochcorMuon. Run3 scale/smearing code: https://gitlab.cern.ch/cms-muonPOG/muonscarekit, docs https://muon-wiki.docs.cern.ch/code/ptcorr/.

### How to apply
1. **Momentum (data + MC)**: medium pT -> Rochester (Run2) / muonscarekit scale+smearing (Run3). High pT -> Run2: no correction; Run3: correct pT with GE kappab biases (values per era/eta/phi on the muon wiki). High-pT MC resolution smearing: see table below.
2. **Efficiency SFs (MC only)**: per-muon SF = RECO x ID x ISO; event weight = product over selected muons, x trigger SF.
   - ID SFs are w.r.t. trackerMuon -> RECO (trackerMuon) SF goes on top. Run3 RECO SF = 1 (none provided).
   - Run2 medium-pT RECO SF: apply for pT in [10-200] GeV; Run2 low-pT RECO SF only below 10 GeV.
   - High-pT RECO SF is binned in **p**, not pT.
   - Pick ISO SF matching your ID (e.g. TightPFIso on Tight ID, TkIso on HighPt ID).
3. **Trigger SFs** (paths covered):
   - Medium pT Run2: 2016 (IsoMu24 or IsoTkMu24), 2017/18 IsoMu27 [Tight + PFIso < 0.15]; (Mu50 or TkMu50) 2016, (Mu50 or OldMu100 or TkMu100) 2017/18 [HighPt + TkIso < 0.10].
   - High pT: 2016 HLT_Mu50 || HLT_TkMu50; 2017/18 HLT_Mu50 || HLT_TkMu100 || HLT_OldMu100; Run3 HLT_Mu50 || HLT_HighPtTkMu100 || HLT_CascadeMu100.
   - Low pT: none provided.
4. **Other**: Run2 L1 prefiring weights (in NanoAOD >= V9) for percent-level analyses; Run3 none. Run2 tracking SF ~ 1, skip unless precision analysis.

### High-pT MC resolution smearing: `p -> p * (1 + N(0, sigma(p,eta) * f))`, sigma = c0 + c1 x p + c2 x p^2 + c3 x p^3
| Era | c0 (\|eta\|<1.2 / 1.2-2.4) | c1 | c2 | c3 | nominal f (barrel / endcap) |
| --- | --- | --- | --- | --- | --- |
| 2016preVFP | 0.0112 / 0.013 | 6.87e-5 / 6.93e-5 | -3.88e-8 / -3.46e-8 | 9.03e-12 / 7.72e-12 | none / none |
| 2016postVFP | 0.0102 / 0.0129 | 6.77e-5 / 6.48e-5 | -3.72e-8 / -3.04e-8 | 8.53e-12 / 6.63e-12 | none / none |
| 2017 | 0.0104 / 0.0121 | 6.11e-5 / 5.92e-5 | -3.31e-8 / -2.61e-8 | 6.73e-12 / 5.11e-12 | none / 0.3202 |
| 2018 | 0.0108 / 0.0136 | 5.93e-5 / 5.47e-5 | -3.08e-8 / -2.3e-8 | 6.04e-12 / 4.66e-12 | none / 0.46 |
| 2022 | 0.01152 / 0.01405 | 5.95e-5 / 5.28e-5 | -2.92e-8 / -1.9e-8 | 5.14e-12 / 3.01e-12 | none / 0.32 |
| 2022EE | 0.0126 / 0.0150 | 5.89e-5 / 4.81e-5 | -2.85e-8 / -1.42e-8 | 4.92e-12 / 1.95e-12 | 0.32 / 0.46 |
| 2023 | 0.0172 / 0.01424 | 6.15e-5 / 5.31e-5 | -3.14e-8 / -1.92e-8 | 5.82e-12 / 3.21e-12 | 0.32 / 0.46 |
| 2023BPix | 0.0118 / 0.0141 | 6.14e-5 / 5.38e-5 | -3.12e-8 / -2.0e-8 | 5.74e-12 / 3.42e-12 | none / 0.568 |
| 2024, 2025 | WIP | | | | study non-closure in your phase space |

```python
import awkward as ak, numpy as np, correctionlib

mu = events.Muon
good = mu[(mu.pt > 30) & (abs(mu.eta) < 2.4)        # kinematic cuts: analysis choice
          & mu.tightId & (mu.pfIsoId >= 4)            # Tight ID + PFIsoTight
          & (abs(mu.dxy) < 0.05) & (abs(mu.dz) < 0.1)]  # optional prompt IP cuts, analysis choice

cset = correctionlib.CorrectionSet.from_file(
    "/cvmfs/cms-griddata.cern.ch/cat/metadata/MUO/Run2-2018-UL-NanoAODv9/latest/muon_Z.json.gz")
flat = ak.flatten(good)
# Key names / input order: check cset.keys() or the docs page - not given by the POG wiki
sf = (cset["<ID key>"].evaluate(abs(flat.eta), flat.pt, "nominal")
      * cset["<ISO key>"].evaluate(abs(flat.eta), flat.pt, "nominal"))
w_mu = ak.prod(ak.unflatten(sf, ak.num(good)), axis=1)

# High-pT: HighPt ID, TuneP pT, tracker iso, MC smearing (2018 coefficients)
hp = mu[(mu.highPtId == 2) & (mu.tkIsoId >= 1)]
pt, eta = ak.to_numpy(ak.flatten(hp.pt * hp.tunepRelPt)), ak.to_numpy(ak.flatten(hp.eta))
c = np.where(abs(eta)[:, None] < 1.2, [0.0108, 5.93e-5, -3.08e-8, 6.04e-12],
                                      [0.0136, 5.47e-5, -2.3e-8, 4.66e-12])
p = pt * np.cosh(eta)
sig = c[:, 0] + c[:, 1]*p + c[:, 2]*p**2 + c[:, 3]*p**3
f = np.where(abs(eta) < 1.2, 0.0, 0.46)   # nominal 2018; syst variation: f = 0.46 everywhere
pt_smeared = ak.unflatten(pt * (1 + np.random.default_rng(seed).normal(0, 1, len(p)) * sig * f), ak.num(hp))
```

## 4. Systematics
| Source | What to do | Correlation |
| --- | --- | --- |
| RECO/ID/ISO/trigger SFs | vary stat and syst components as **separate** nuisances (Run2 JSON has central, stat, syst entries; ROOT: `_stat`/`_syst` histograms) | syst: correlated across years; stat: uncorrelated across years |
| Run2 low-pT RECO and J/psi ID SFs | statistical uncertainty only | uncorrelated across years |
| IP cuts (Tight, HighPt, or tighter dxy/dz) | SFs measured with dxy < 0.2, dz < 0.5 on the probe -> IP inefficiency not covered. Estimate signal-MC loss vs pileup, add as systematic | analysis-defined |
| Isolation in busy/boosted events | DY-derived ISO SFs may not apply at high jet multiplicity / boosted topologies -> derive own extra systematic | analysis-defined |
| Medium-pT scale/smearing | vary individual components of Rochester / muonscarekit correction | - |
| High-pT scale (GE) | Run2: use kappab (+/- unc.) as systematic only. Run3: from the uncertainties of the applied kappab | - |
| Spectrum across 200 GeV | if pT < 200 matters: medium-pT correction + its syst below 200, GE above; if negligible: no medium-pT correction, GE syst for all muons. If unsure, use the first | - |
| High-pT resolution | 10% shift, all eras, barrel + endcap: `p * (1 + N(0, sigma(p,eta) * 0.46))` (sigma from table above; 2016preVFP: syst only, no nominal smearing) | - |
| Signal muons > 500 GeV | extra check: shift pT by measured scale biases by hand, check the effect on results | - |
| High-pT RECO above p = 1500 GeV (2016) | large uncertainties are valid, apply as given | - |

## 5. Pitfalls / do NOT use
- Tight ID for pT > 200 GeV (inefficient; no recommended high-pT SFs for Tight) -> use HighPt ID.
- Plain `Muon_pt` with HighPt ID -> use `Muon_pt * Muon_tunepRelPt`. But in PF analyses (PF MET, PF iso) keep PF `Muon_pt`; if mixing, propagate TuneP pT into PF MET.
- Soft/HighPt (non-PF) IDs in an analysis using the PF event description.
- Isolation cut on top of `promptMVA` (it already includes isolation).
- `Muon_mvaId` (Lepton MVA): removed after NanoAOD v10. `Muon_mvaTTH` on NanoAOD >= v14: use `Muon_promptMVA`. Muon MVA from CMSSW < 13_2_X: outdated training.
- `puppiIsoId`: branch exists, but POG says PUPPI isolation is NOT SUPPORTED. `multiIsoId == 1` (Loose) is meaningless.
- `tkRelIso` uses TuneP pT but `tkIsoId` bits use default pT -> cutting on each gives slightly different results.
- Switching SF sets (low/medium/high pT) muon-by-muon within one analysis.
- Evaluating high-pT RECO SF in pT (it is in p). Applying Run2 GE kappab as a correction. Mixing GE with medium-pT corrections on the same muon.
- Applying Run3 RECO SFs or Run3 prefiring weights (none exist). Applying Run2 tracking SFs (~ 1) outside precision analyses.
- Era mixing: 2016preVFP/postVFP, 2022/2022EE, 2023/2023BPix each have their own files and constants.
- Low-pT SFs derived with deltaR(mumu) > 0.3: check your signal/background vs deltaR if you don't apply it.
- 2016preVFP high-pT HLT SFs use deltaPhi > 1.39 when both muons have |eta| > 1.24.
- Run2 very high-pT (2-3 TeV) single-muon analyses: consider requiring `Muon_highPurity`.
- for correctionlib key names always list `cset.keys()` and check input order before use.
