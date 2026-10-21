# AK4 jets — CMS JME recommendations (NanoAOD)

Source: CMS JME/JERC recommendations (JEC, JER, jet veto maps, uncertainties, PU jet ID), cms-analysis-corrections JME pages, JERC meeting 12 Nov 2024 slides (retrieved 24 Sep 2026) | Campaigns: Run2 UL 2016preVFP/2016postVFP/2017/2018 (NanoAODv9 and NanoAODv15); Run3 2022/2022EE/2023/2023BPix/2024/2025/2026

**JEC, JER, their tags/keys and JES/JER systematics → `references/jets-jerc.md`.**

## 0. Collections
| Dataset | `Jet` (AK4) | `FatJet` (AK8) |
| --- | --- | --- |
| Run2 UL NanoAODv9 | AK4PFchs | AK8PFPuppi |
| Run2 NanoAODv15 | AK4PFPuppi | AK8PFPuppi |
| Run3 | AK4PFPuppi | AK8PFPuppi |

Correction keys end in `_AK4PFchs` (Run2 v9) or `_AK4PFPuppi` (Run2 v15, Run3). Use the one matching your NanoAOD.

## 1. NanoAOD branches (`Jet_*`)
Branch source: NanoAODv15, 2024 MC (`RunIII2024Summer24NanoAODv15`). Older versions differ (e.g. v9 has `Jet_puId` bitmap; v15 has **no** `Jet_jetId` and **no** `Jet_puId`).

`nJet` = slimmedJetsPuppi, i.e. ak4 PFJets Puppi **with JECs applied**, after basic selection (pt > 15).

| Group | Branches |
| --- | --- |
| Kinematics | `pt`, `eta`, `phi`, `mass` (JEC-corrected), `rawFactor` (1 − factor to get back to raw pT), `area` (catchment area, for JECs) |
| Energy fractions (jet ID inputs) | `chHEF`, `neHEF`, `chEmEF`, `neEmEF`, `muEF`; HF: `hfEmEF`, `hfHEF` |
| Multiplicities | `chMultiplicity`, `neMultiplicity` (Puppi-weighted), `nConstituents`, `nElectrons`, `nMuons`, `nSVs` |
| HF noise variables | `hfsigmaEtaEta`, `hfsigmaPhiPhi`, `hfcentralEtaStripSize`, `hfadjacentEtaStripsSize` |
| Pileup ID | `puIdDisc` (BDT, 133X Winter24 PuppiV18 training) |
| Muon subtraction | `muonSubtrFactor` (1 − (muon-subtracted raw pt)/(raw pt)), `muonSubtrDeltaEta`, `muonSubtrDeltaPhi` |
| DeepJet | `btagDeepFlavB`, `btagDeepFlavCvB`, `btagDeepFlavCvL`, `btagDeepFlavQG` |
| ParticleNet | `btagPNetB`, `btagPNetCvB`, `btagPNetCvL`, `btagPNetCvNotB`, `btagPNetQvG`, `btagPNetTauVJet` |
| UnifiedParT | `btagUParTAK4B`, `…CvB`, `…CvL`, `…CvNotB`, `…QvG`, `…SvCB`, `…SvUDG`, `…TauVJet`; raw: `…Ele`, `…Mu`, `…UDG`, `…probb`, `…probbb` |
| pT regression (× raw pT) | `PNetRegPtRawCorr`, `PNetRegPtRawCorrNeutrino`, `PNetRegPtRawRes`; `UParTAK4RegPtRawCorr`, `…CorrNeutrino`, `…Res`; `UParTAK4V1RegPtRawCorr`, `…CorrNeutrino`, `…Res` |
| Links | `electronIdx1/2`, `muonIdx1/2`, `svIdx1/2`, `genJetIdx` |
| MC truth | `hadronFlavour` (hadron ghost clustering), `partonFlavour` (parton matching) |

- Raw pT = `Jet_pt * (1 - Jet_rawFactor)` (input for re-applying JEC).
- Full PNet regression: raw pT × `PNetRegPtRawCorr` × `PNetRegPtRawCorrNeutrino`. `*Res` = (q84 − q16)/2.
- b-tagging WPs/SFs → `references/b-tagging.md`.

## 2. IDs
### Jet ID (noise / badly reconstructed jets)
| Era | How | WPs |
| --- | --- | --- |
| Run3 (all eras), NanoAODv12/v15 | `Jet_jetId` is **not** in NanoAODv15 → evaluate `jetid.json.gz` (per-campaign, see `jets-jerc.md` §1) or apply the legacy Run 3 Jet ID TWiki cuts by hand | `AK4PUPPI_Tight`, `AK4PUPPI_TightLeptonVeto` (also `AK4CHS_*`, `AK8*_*` keys) |
| Run3 2024 Scouting | `Run3-24Scouting-Summer24-ScoutingNanoAODv15/latest/jetid.json.gz` | `ScoutingPFJet_Tight`, `ScoutingPFJet_TightLeptonVeto`, `ScoutingPFJetRecluster_Tight`, `ScoutingPFJetRecluster_TightLeptonVeto` |
| Run2 UL (v9 / v15) | not provided in the source (Run2 veto-map selection only says "tight jet ID") | > TODO: not available |

`jetid.json.gz` description: "Jet Identification Criteria for Run3 Rereco2022CDE from https://twiki.cern.ch/twiki/bin/view/CMS/JetID13p6TeV?rev=18" (same payload in 2024; 2026 copied from 2025).
Inputs (by name): `eta`, `chHEF`, `neHEF`, `chEmEF`, `neEmEF`, `muEF`, `chMultiplicity`, `neMultiplicity`, `multiplicity` (= ch + ne). Output: `jet id` (real). Numeric cut values: > TODO: not available (in the JSON/TWiki only).

```python
import correctionlib, awkward as ak, numpy as np
BASE = "/cvmfs/cms-griddata.cern.ch/cat/metadata/JME/Run3-24CDEReprocessingFGHIPrompt-Summer24-NanoAODv15/latest"
jid = correctionlib.CorrectionSet.from_file(f"{BASE}/jetid.json.gz")["AK4PUPPI_TightLeptonVeto"]
j = ak.flatten(events.Jet)
args = dict(eta=j.eta, chHEF=j.chHEF, neHEF=j.neHEF, chEmEF=j.chEmEF, neEmEF=j.neEmEF, muEF=j.muEF,
            chMultiplicity=j.chMultiplicity, neMultiplicity=j.neMultiplicity,
            multiplicity=j.chMultiplicity + j.neMultiplicity)
out = jid.evaluate(*[ak.to_numpy(args[i.name]) for i in jid.inputs])
jet_id = ak.unflatten(out, ak.num(events.Jet))   # verify pass convention (e.g. out > 0) on your file
```

### Pileup jet ID
BDT separating hard-interaction jets from PU jets (vertex compatibility, shape, multiplicity). Separate from Jet ID.
- Apply **only to JEC-corrected AK4 jets with pT < 50 GeV**; jets ≥ 50 GeV pass without a requirement.
- Same WP in data and MC; apply efficiency SFs in MC where available. **Mistag SFs are not provided centrally** — derive/validate in the analysis if needed.

| Era | Collection | Branches | WPs / SFs |
| --- | --- | --- | --- |
| Run3 (NanoAODv15) | AK4PFPuppi | `Jet_puIdDisc` (133X Winter24 PuppiV18); no `Jet_puId` bitmap | WPs and SFs **in progress**. Do NOT use the Run 2 CHS prescription |
| Run2 UL (NanoAODv9) | AK4PFchs | `Jet_puId` (WP bitmap), `Jet_puIdDisc` | L/M/T + efficiency SFs: key `PUJetID_eff` in `jmar.json.gz` |

Run2 UL NanoAODv9 bitmap — test the bit, never compare the full value. **Loose and Tight bits are swapped in all UL2016 (preVFP and postVFP) samples.**

| WP | UL2016 test | UL2017 / UL2018 test | Target prompt-jet eff. |
| --- | --- | --- | --- |
| Tight (T) | `(Jet_puId & 4) != 0` | `(Jet_puId & 1) != 0` | 80% |
| Medium (M) | `(Jet_puId & 2) != 0` | `(Jet_puId & 2) != 0` | 90% |
| Loose (L) | `(Jet_puId & 1) != 0` | `(Jet_puId & 4) != 0` | 99% (\|η\|<2.5) / 95% (\|η\|>2.5) per JSON description |

`PUJetID_eff` (Run2 UL v9, `/cvmfs/cms-griddata.cern.ch/cat/metadata/JME/Run2-<era>-UL-NanoAODv9/latest/jmar.json.gz`): inputs `eta`, `pt` (range [12.5, 57.5)), `systematic` ∈ {`nom`, `up`, `down`, `MCEff`}, `workingpoint` ∈ {`L`, `M`, `T`}; output `weight`. Thresholds depend on jet pT, η, era and WP (in the payload).

## 3. Jet veto maps
### Run3 — **mandatory**; reject the **whole event** if any selected jet is in a vetoed region
Minimal jet selection before checking the map (from the legacy selection discussion):
- jet pT > 15 GeV
- `tightLepVeto` jet ID (NanoAODv15: no `Jet_jetId` → apply manually per the legacy Run 3 Jet ID TWiki, or via `jetid.json.gz`, see §2)
- `Jet_chEmEF + Jet_neEmEF < 0.9` (EM-fraction cut follows the legacy Run 2 Type-I MET TWiki)

| Era | Tag | JSON key in `jetvetomaps.json.gz` | Note |
| --- | --- | --- | --- |
| 2022 (PreEE, CD) | `Summer22_23Sep2023_V1` | `Summer22_23Sep2023_RunCD_V1` | separate CD / EFG maps |
| 2022EE (PostEE, EFG) | `Summer22EE_23Sep2023_V1` | `Summer22EE_23Sep2023_RunEFG_V1` | affected by EE+ leak |
| 2023 (PreBPix) | `Summer23Prompt23_V1` | `Summer23Prompt23_RunC_V1` | |
| 2023BPix (PostBPix) | `Summer23BPixPrompt23_V1` | `Summer23BPixPrompt23_RunD_V1` | |
| 2024 | `Summer24Prompt24_V1` | `Summer24Prompt24_RunBCDEFGHI_V1` | |
| 2025 | `Summer24Prompt25_V1` | `Summer24Prompt25_RunCDEFG_V1` | |
| 2026 | `Summer24Prompt26_V1` | `Summer24Prompt26_RunBCD_V1` | cloned from 2025 |

Inputs: `type` (string, use **`jetvetomap`**), `eta`, `phi`. Output `vetomaps`: non-zero ⇒ vetoed. Apply the map of the matching data period to each MC sample.

### Run2 UL — reject **jets** (not events) in vetoed regions; use the strictest map
| Era | Tag | Strict map (ROOT name) | JSON key / `type` values |
| --- | --- | --- | --- |
| 2016 (preVFP + postVFP, same map) | `Summer19UL16_V0` | `h2hot_ul16_plus_hbm2_hbp12_qie11` **+** `h2hot_mc` | `Summer19UL16_V1`; `jetvetomap`, `jetvetomap_mc`, … |
| 2017 | `Summer19UL17_V2` | `h2hot_ul17_plus_hep17_plus_hbpw89` | `Summer19UL17_V1`; `jetvetomap`, … |
| 2018 | `Summer19UL18_V1` | `h2hot_ul18_plus_hem1516_plus_hbp2m1` | `Summer19UL18_V1`; `jetvetomap`, `jetvetomap_hem1516`, `jetvetomap_hbp2m1`, … |

- 2016: apply `h2hot_mc` **in addition** (MC hot zone absent in data). Beamspot effects largest for non-APV MadGraph HT samples.
- 2018: with HEM-reprocessed 2018CD + standard 2018AB, omitting `hem1516` may be considered; `hbp2m1` must still be applied.
- Nominal loose jet selection: pT > > TODO (lost in source); tight jet ID; PU jet ID for CHS jets (pT < 50 GeV); `chEmEF + neEmEF < 0.9`; no overlap with a PF muon (ΔR: > TODO).
- Large acceptance loss → restricted use (e.g. leading jet only); jet-insensitive measurements may use the basic `h2hot_ul1X` map or no veto. Validate and document.
- Maps labelled `mc`/`hw` are for expert studies (except UL16 `h2hot_mc`). Ref: CMS AN-2022/066.

```python
veto = correctionlib.CorrectionSet.from_file(f"{BASE}/jetvetomaps.json.gz")["Summer24Prompt24_RunBCDEFGHI_V1"]
J = events.Jet
sel = J[(J.pt > 15) & jet_id & (J.chEmEF + J.neEmEF < 0.9)]   # jet_id = AK4PUPPI_TightLeptonVeto (§2)
f = ak.flatten(sel)
v = veto.evaluate("jetvetomap", ak.to_numpy(f.eta), np.clip(ak.to_numpy(f.phi), -3.1415926, 3.1415926))
event_ok = ~ak.any(ak.unflatten(v, ak.num(sel)) != 0, axis=1)   # Run3: drop the event
```

**Always** (Run2 and Run3): same map in data and MC; make jet η–φ maps before/after the veto, check other distributions, document in the AN.

## 4. Pitfalls / do NOT use
- `Jet_jetId` / `Jet_puId` on NanoAODv15 — don't exist. Run3 PU jet ID: no WPs/SFs yet; **never** use Run 2 CHS WPs on Puppi jets.
- Full-bitmap comparisons (`Jet_puId == 7`) and UL2017/18 bit tests on UL2016 (bits swapped).
- PU jet ID on jets with pT ≥ 50 GeV, or on non-JEC-corrected jets.
- Run3: veto maps are mandatory and act on events; Run2: they act on jets. Don't mix up.
- 2022: use CD map for Summer22 MC and EFG map for Summer22EE MC — not one map for both.
- Run3 rare L2Relative blow-up (corrected pT > 10 TeV, mostly HF): if seen, reject jets with `Jet_rawFactor > 0.9`. Only for affected production samples — check https://gitlab.cern.ch/cms-jetmet/coordination/coordination/-/work_items/153#note_9486099.
- Run3 forward jets: 2022/23 HF and 2022–24 HE need pT > 50 GeV (+ gen-matched-only JER in HE); 2024 needs a low-pT L2L3Residual freeze in 2.0<|η|<2.5 — see `jets-jerc.md` §4.
- `*CHS*` jet ID keys / `AK4PFchs` corrections on Puppi NanoAOD (Run2 v15, Run3) and vice versa on Run2 v9.
- Winter22/Winter24/Winter25 correction campaigns: not the recommended tags (see `jets-jerc.md` §5).
