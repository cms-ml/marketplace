# AK4 jets — JEC, JER and JES/JER systematics (NanoAOD, correctionlib)

Source: CMS JME/JERC recommendations (JES, JER, Uncertainties and Correlations), cms-analysis-corrections JME pages (`docs/corrections/JME`), "Practical Application of JER Smearing" (June 5, 2026), JERC meeting 12 Nov 2024 slides (retrieved 24 Sep 2026), JME "Mitigation techniques" slide (A. Benecke; Run3 2022–2025 forward-region mitigations) | Campaigns: Run2 UL (NanoAODv9, NanoAODv15); Run3 2022–2026

Selection/IDs/veto maps → `references/jets.md`.

## 1. Where to get files
- CVMFS: `/cvmfs/cms-griddata.cern.ch/cat/metadata/JME/<campaign>/latest/<file>`
- GitLab: `https://gitlab.cern.ch/cms-analysis-corrections/JME/<campaign>/-/tree/latest`
- JER smearing tool (all eras): `/cvmfs/cms-griddata.cern.ch/cat/metadata/JME/JER-Smearing/latest/jer_smear.json.gz` (key `JERSmear`)
- TXT/TAR/DB payloads also exist per tag (JECDatabase / JRDatabase); JERC viewer to inspect them.

Files per campaign: `jet_jerc.json.gz` (AK4 JEC+JER+JES unc), `fatJet_jerc.json.gz` (AK8), `jetvetomaps.json.gz`; Run3 also `jetid.json.gz`; Run2 v9 also `jmar.json.gz` (PU jet ID SFs), `met.json.gz`.

| Era | `<campaign>` | Algo | JEC tag | JER tag | Data eras in JEC tag |
| --- | --- | --- | --- | --- | --- |
| 2016preVFP (APV) v9 | `Run2-2016preVFP-UL-NanoAODv9` | AK4PFchs | `Summer19UL16APV_V7` | `Summer20UL16APV_JRV5` | RunBCD, RunEF |
| 2016postVFP v9 | `Run2-2016postVFP-UL-NanoAODv9` | AK4PFchs | `Summer19UL16_V7` | `Summer20UL16_JRV5` | RunFGH |
| 2017 v9 | `Run2-2017-UL-NanoAODv9` | AK4PFchs | `Summer19UL17_V5` | `Summer19UL17_JRV4` | RunB–F |
| 2018 v9 | `Run2-2018-UL-NanoAODv9` | AK4PFchs | `Summer19UL18_V5` | `Summer19UL18_JRV3` | RunA–D |
| 2016preVFP (APV) v15 | `Run2-2016preVFP-UL-NanoAODv15` | AK4PFPuppi | `Summer20UL16APVNanoV15_V1` | `Summer20UL16APV_JRV5` | RunBCD, RunEF |
| 2016postVFP v15 | `Run2-2016postVFP-UL-NanoAODv15` | AK4PFPuppi | `Summer20UL16NanoV15_V1` | `Summer20UL16_JRV5` | RunFGH |
| 2017 v15 | `Run2-2017-UL-NanoAODv15` | AK4PFPuppi | `Summer20UL17NanoV15_V1` | `Summer19UL17_JRV4` | RunB–F |
| 2018 v15 | `Run2-2018-UL-NanoAODv15` | AK4PFPuppi | `Summer20UL18NanoV15_V1` | `Summer19UL18_JRV3` | RunA–D |
| 2022 (PreEE) | `Run3-22CDSep23-Summer22-NanoAODv12` | AK4PFPuppi | `Summer22_22Sep2023_V4` | `Summer22_22Sep2023_JRV2` | RunCD (ReReco) |
| 2022EE (PostEE) | `Run3-22EFGSep23-Summer22EE-NanoAODv12` | AK4PFPuppi | `Summer22EE_22Sep2023_V4` | `Summer22EE_22Sep2023_JRV2` | RunE (ReReco), F, G (Prompt) |
| 2023 (PreBPix) | `Run3-23CSep23-Summer23-NanoAODv12` | AK4PFPuppi | `Summer23Prompt23_V4` | `Summer23Prompt23_RunCv1234_JRV3` | RunCv123, RunCv4 |
| 2023BPix (PostBPix) | `Run3-23DSep23-Summer23BPix-NanoAODv12` | AK4PFPuppi | `Summer23BPixPrompt23_V4` | `Summer23BPixPrompt23_RunD_JRV3` | RunD |
| 2024 | `Run3-24CDEReprocessingFGHIPrompt-Summer24-NanoAODv15` | AK4PFPuppi | `Summer24Prompt24_V5` | `Summer24Prompt24_JRV2` | C–E nib1 (ReReco), F nib1–3, G nib1–2, H nib1, I nib1 (Prompt) |
| 2025 | `Run3-25Prompt-Summer24-NanoAODv15` | AK4PFPuppi | `Summer24Prompt25_V3` | `Summer24Prompt25_JRV2` | RunC–G (Prompt) |
| 2026 B, D | `Run3-26Prompt-Summer24-NanoAODv15` | AK4PFPuppi | `Summer24Prompt26_V1` | `Summer24Prompt26_RunBD_JRV1` | RunB, RunD |
| 2026 C (low-PU) | same | AK4PFPuppi | `Summer24Prompt26_V1` (preliminary for C) | `Summer24Prompt26_RunC_JRV1` | RunC |

MC for 2024/2025/2026 is Summer24; 2025/2026 JER SFs were derived directly vs Summer24 MC.

### correctionlib keys in `jet_jerc.json.gz` (`<algo>` = `AK4PFchs` or `AK4PFPuppi`)
| Purpose | Key | Inputs (by name) |
| --- | --- | --- |
| JEC, MC (L1FastJet×L2Relative×L3Absolute×L2L3Residual) | `<JEC>_MC_L1L2L3Res_<algo>` | `JetA`, `JetEta`, `JetPt` (raw), `Rho`, `JetPhi` |
| JEC, data | `<JEC>_DATA_L1L2L3Res_<algo>` | same + `run` |
| Single levels | `<JEC>_{MC,DATA}_{L1FastJet,L2Relative,L3Absolute,L2L3Residual}_<algo>` | – |
| JER: MC resolution σ_JER | `<JER>_MC_PtResolution_<algo>` | `JetEta`, `JetPt`, `Rho` |
| JER: data/MC SF s_JER | `<JER>_MC_ScaleFactor_<algo>` | `JetEta`, `JetPt` |
| JER: SF uncertainty | `<JER>_MC_SFUncertainty_<algo>` | `JetEta`, `JetPt` |
| JES uncertainty per source | `<JEC>_MC_<source>_<algo>` | `JetEta`, `JetPt` |

Run2 v9 also has `…_EtaResolution_…`, `…_PhiResolution_…`. `JetPt` for JER and uncertainties = pT **after** all corrections applied.
Data L2L3Residual is **run-based** (JSON takes `run`; Run2 v15 and Run3, and present in Run2 v9 JSONs too) — no per-era data keys needed. 2024 "nibs" are handled this way.

`JERSmear` inputs: `JetPt`, `JetEta`, `GenPt` (matched gen pT or −1), `Rho`, `EventID` (int), `JER` (σ_JER), `JERSF` (s_JER); output `smear` (c_JER).

## 2. How to apply
Order: **JEC (data + MC) → JER smearing (MC only) → variations**.
1. **JEC**: raw pT = `Jet_pt * (1 - Jet_rawFactor)` (same for mass); pT_JEC = raw × `L1L2L3Res`. Use `_DATA_` key (with `run`) on data, `_MC_` on MC.
   If AK8 JECs are unavailable, apply AK4 JECs of the same campaign to AK8.
2. **JER (MC only; data c_JER = 1; data files are not used)** — hybrid method, evaluated on JEC-corrected jets:
   - Gen match if ΔR(reco, gen) < R_cone/2 (R_cone = 0.4 for AK4) **and** |pT_JEC − pT_gen| < 3 σ_JER pT_JEC.
   - Matched: c = 1 + (s_JER − 1)(pT_JEC − pT_gen)/pT_JEC. Unmatched (`GenPt = -1`): c = 1 + N(0, σ_JER)·√max(s_JER² − 1, 0).
   - N(0,σ) from hashPRNG (entropy: `JetPt`, `JetEta`, `Rho`, `EventID`) → deterministic; no TRandom3. Non-finite/non-positive c → 1; negative c truncated to 0; smeared pT min cut 0.01 (2026-09-18 fix).
   - Scale **both pT and mass** (full four-momentum): p_JER = c_JER × p_JEC.
3. **Rare Run3 L2Relative issue**: if corrected pT is anomalously high (> 10 TeV, mostly HF), reject jets with `Jet_rawFactor > 0.9` (affected samples only; see `jets.md` §4).
4. **Run3 forward-region mitigations** (HF/HE/2.0<|η|<2.5, year-dependent): apply per §4 table — pT thresholds, gen-matched-only JER in HE, and the 2024 low-pT L2L3Residual freeze.

```python
import correctionlib, awkward as ak, numpy as np
BASE = "/cvmfs/cms-griddata.cern.ch/cat/metadata/JME/Run3-24CDEReprocessingFGHIPrompt-Summer24-NanoAODv15/latest"
JEC, JER, ALGO = "Summer24Prompt24_V5", "Summer24Prompt24_JRV2", "AK4PFPuppi"
cs  = correctionlib.CorrectionSet.from_file(f"{BASE}/jet_jerc.json.gz")
smr = correctionlib.CorrectionSet.from_file(
    "/cvmfs/cms-griddata.cern.ch/cat/metadata/JME/JER-Smearing/latest/jer_smear.json.gz")["JERSmear"]
ev = lambda c, **kw: c.evaluate(*[kw[i.name] for i in c.inputs])   # input order-safe

jets, n = events.Jet, ak.num(events.Jet)
j = ak.flatten(jets)
# NOT in pasted Jet_ table -- take from your NanoAOD: rho (fixed-grid rho), run, event number, GenJet pt/eta/phi
rho_j = ak.to_numpy(ak.flatten(ak.broadcast_arrays(rho, jets.pt)[0]))
run_j = ak.to_numpy(ak.flatten(ak.broadcast_arrays(run, jets.pt)[0])).astype(float)
evt_j = ak.to_numpy(ak.flatten(ak.broadcast_arrays(event, jets.pt)[0])).astype(np.int64)

raw_pt, raw_m = ak.to_numpy(j.pt * (1 - j.rawFactor)), ak.to_numpy(j.mass * (1 - j.rawFactor))
eta, phi, area = ak.to_numpy(j.eta), ak.to_numpy(j.phi), ak.to_numpy(j.area)
key = f"{JEC}_{'MC' if is_mc else 'DATA'}_L1L2L3Res_{ALGO}"
cjec = ev(cs[key], JetA=area, JetEta=eta, JetPt=raw_pt, Rho=rho_j, JetPhi=phi, run=run_j)
pt, m = raw_pt * cjec, raw_m * cjec

if is_mc:
    res = ev(cs[f"{JER}_MC_PtResolution_{ALGO}"], JetEta=eta, JetPt=pt, Rho=rho_j)
    sf  = ev(cs[f"{JER}_MC_ScaleFactor_{ALGO}"],  JetEta=eta, JetPt=pt)
    unc = ev(cs[f"{JER}_MC_SFUncertainty_{ALGO}"], JetEta=eta, JetPt=pt)
    g = genjets[jets.genJetIdx]                      # None where genJetIdx < 0
    gpt = ak.to_numpy(ak.fill_none(ak.flatten(g.pt), -1.0))
    dR = ak.to_numpy(ak.fill_none(ak.flatten(jets.delta_r(g)), 99.0))
    gpt = np.where((gpt > 0) & (dR < 0.4 / 2) & (np.abs(pt - gpt) < 3 * res * pt), gpt, -1.0)
    smear = lambda s: ev(smr, JetPt=pt, JetEta=eta, GenPt=gpt, Rho=rho_j, EventID=evt_j, JER=res, JERSF=s)
    c_nom, c_up, c_dn = smear(sf), smear(sf * (1 + unc)), smear(sf * (1 - unc))  # same inputs -> correlated draws
    pt_nom, m_nom = pt * c_nom, m * c_nom
```

## 3. Systematics
General: apply **both** JES and JER; treat them **uncorrelated with each other**. Keep the full set (you can collapse later, never expand). Plot nominal ± variations; make impact plots to check the fit does not constrain JES/JER NPs. Non-standard approaches → JME/JERC conveners.

JSON stores JEC and JER uncertainties **symmetrically**: one `unc` per (`JetEta`, `JetPt`), applied as `(1 ± unc)`. JES: pT_up/down = pT × (1 ± unc_source) (and mass). JER: SF_up/down = SF × (1 ± unc), then re-smear (code above). 2023–2026 JER `SFUncertainty` TXT files are asymmetric; the JSON stores the unbounded "up" value (2023 fixed in `…_JRV3`).

### JES
| Case | Sources (`<source>` in `<JEC>_MC_<source>_<algo>`) | When | Correlation |
| --- | --- | --- | --- |
| I Full | 27 sources per year (list: [full JES source table](https://docs.google.com/spreadsheets/d/1JZfk78_9SD225bcUuTWVo4i02vwI5FfeVKH-dwzUdhM/edit?gid=1345121349#gid=1345121349)); JSON has e.g. `AbsoluteStat`, `AbsoluteScale`, `AbsoluteMPFBias`, `Fragmentation`, `SinglePionECAL/HCAL`, `FlavorQCD`, `TimePtEta`, `RelativeJEREC1/2/HF`, `RelativePt*`, `RelativeBal`, `RelativeSample`, `RelativeFSR`, `RelativeStat*`, `PileUp*` | precision / JES-sensitive (can constrain JES NPs) | "Correlations(Ideal)" column of the table |
| II Reduced (**default**) | 11 per period: `Regrouped_Absolute`, `Regrouped_BBEC1`, `Regrouped_EC2`, `Regrouped_FlavorQCD`, `Regrouped_HF`, `Regrouped_RelativeBal` (**correlated across periods**) + `Regrouped_Absolute_<yr>`, `Regrouped_BBEC1_<yr>`, `Regrouped_EC2_<yr>`, `Regrouped_HF_<yr>`, `Regrouped_RelativeSample_<yr>` (**uncorrelated**) | mildly JES-sensitive; must show no over-constraint | Run2 UL: 6 + 5×4 = 26 NPs |
| III Single (`Total`, or `Regrouped_Total`) | 1 NP | **JME approval required** (show at JME/JERC meeting that it stays unconstrained) | start as uncorrelated across years |

`<yr>` in keys: `2016APV`, `2016`, `2017`, `2018`, `2022`, `2022EE`, `2023`, `2023BPix`, `2024`, `2025`, `2026`. Other keys present: `SubTotal*`, `TotalNoFlavor`, `TotalNoTime`, `TotalNoFlavorNoTime`, `CorrelationGroup*`, `Flavor{PureBottom,PureCharm,PureGluon,PureQuark,PhotonJet,ZJet}`; Run2 v9 also `TimeRun{A,B,C,D}`.

- **Run3** uncertainties are currently **copied from 2018**. Nov 2024 slides: for Run3 only full or total set recommended at that time (reduced set planned); Run3 within-year correlations as in Run2 are "probably too restrictive".
- **Run2 + Run3 combination**: most conservative = fully decorrelate Run2 vs Run3 (guidance subject to change).
- **AK4 + AK8** in the same event (non-overlapping): fully correlated per year; use the **same scheme** (27 / 11 / 1) for both. No AK8 unc → use AK4 unc.

### JER
| Case | Treatment | Correlation |
| --- | --- | --- |
| II Default | 1 NP per year (show it is unconstrained) | uncorrelated across years (all Run2 years) |
| I Split (JER-sensitive, preliminary) | 6 NPs per year in (η, pT) bins — each variation applied only to jets in its bin, others nominal; events are not split | correlated among all jets/events within a year, uncorrelated across years |

Split-bin edges: > TODO: not available (lost in source). Current JER SFs are flat in pT (pT-dependent SFs being tested).

## 4. Known issues
### Run3 forward-region mitigations (JME slide "Mitigation techniques", A. Benecke)
| Year | HF (3 < \|η\| < 5) | HE (2.5 < \|η\| < 3) | 2.0 < \|η\| < 2.5 |
| --- | --- | --- | --- |
| 2022 | require pT > 50 GeV | require pT > 50 GeV **+** JER for gen-matched jets only | – |
| 2023 | require pT > 50 GeV | require pT > 50 GeV **+** JER for gen-matched jets only | – |
| 2024 | fixed (no mitigation) | require pT > 50 GeV **+** JER for gen-matched jets only | for MC-truth-corrected pT < 30 GeV, use the L2L3Residual factor evaluated at MC-truth-corrected pT = 30 GeV |
| 2025 | fixed, but worsening with radiation damage | much improved; slide asks whether it is enough for analysers (no firm prescription) | should not be a problem, but **check** |

- "pT" = corrected jet pT (the slide does not say whether before or after JER smearing; > TODO: confirm with JME).
- "JER for gen-matched only": apply the scaling branch of §2 step 2 to matched jets; unmatched jets in HE get c_JER = 1 (no stochastic smearing).
- 2024 residual freeze (data only; MC-truth-corrected pT = L1FastJet×L2Relative×L3Absolute, i.e. before the residual). The slide doesn't specify the correctionlib implementation; one way, using the single-level keys (check `[i.name for i in c.inputs]`):
  ```python
  pt_mct = raw_pt * ev(cs[f"{JEC}_DATA_L1FastJet_{ALGO}"], JetA=area, JetEta=eta, JetPt=raw_pt, Rho=rho_j, JetPhi=phi, run=run_j)
  pt_mct *= ev(cs[f"{JEC}_DATA_L2Relative_{ALGO}"], JetEta=eta, JetPt=pt_mct, JetPhi=phi, run=run_j)
  pt_mct *= ev(cs[f"{JEC}_DATA_L3Absolute_{ALGO}"], JetEta=eta, JetPt=pt_mct, JetPhi=phi, run=run_j)
  freeze = (np.abs(eta) > 2.0) & (np.abs(eta) < 2.5) & (pt_mct < 30)
  res = ev(cs[f"{JEC}_DATA_L2L3Residual_{ALGO}"], JetEta=eta, JetPt=np.where(freeze, 30.0, pt_mct), JetPhi=phi, run=run_j)
  pt = pt_mct * res
  ```
- Earlier (Nov 2024) guidance, now superseded for HE by the table above: case-by-case (a) higher jet pT threshold; (b) drop stochastic smearing (scale matched jets only). Outside the table, (b) needs **explicit JME/JERC approval**.
- MiniAOD/MET: JER smearing is done in MET recomputation (`patSmearedJets`, `shiftedPatSmearedJetResDown`, `shiftedPatSmearedJetResUp`).

## 5. Do NOT use
- `Summer24Prompt24_V3`/`_V4` (2024) and `Summer24Prompt25_V1`/`_V2` (2025): residuals not updated → use `Summer24Prompt24_V5`, `Summer24Prompt25_V3`.
- `Summer23Prompt23_RunCv1234_JRV2_MC`, `Summer23BPixPrompt23_RunD_JRV2_MC` → use `…_JRV3_MC`.
- Campaigns not in the recommendation table: `Run3-22Prompt-Winter22-NanoAODv12` (`Winter22Run3_*`), `Run3-24Prompt-Winter24-NanoAODv14` (`Winter24Prompt24_V3`), `Run3-25Prompt-Winter25-NanoAODv15` (`Winter25Prompt25_V3`), `Run2-*-EOY17-NanoAODv6`.
- CHS keys (`Summer19UL*`, `AK4PFchs`) on NanoAODv15 Puppi jets, or v15 Puppi keys on NanoAODv9.
- JER smearing on data; JER before JEC; evaluating JER/unc at raw pT; smearing only pT but not mass.
- Independent random numbers for nominal vs up/down JER (breaks correlation); TRandom3-based smearing.
- Treating JES and JER as correlated, or JER correlated across years; mixing different JES schemes for AK4 vs AK8.
- 2026 C (low-PU) with the RunBD JER tag, or vice versa.
- Run3 2022–2024 forward jets without the §4 mitigations (e.g. HF/HE jets with pT < 50 GeV in 2022/23, stochastic JER smearing of unmatched HE jets); 2025 forward jets unchecked.
- Always check `list(cs.keys())` and `[i.name for i in c.inputs]` before use.
