# electrons - CMS POG recommendations (NanoAOD)

Source: https://egammapog.docs.cern.ch/Run3/Run3_ID/ (+ cut-based ID, MVA ID, Scale & Smearing pages, old EGM SF twiki) | Campaigns: Run3 2022/2022EE/2023/2023BPix/2024/2025 (S&S also 2026)
Run2 UL: > TODO: not available (the source only covers Run3; Run2 HEEP is mentioned via https://twiki.cern.ch/twiki/bin/view/CMS/EgammaIDRecipesRun2)

## 1. NanoAOD branches (`Electron_*`)
Branch source: https://cms-xpog.docs.cern.ch/autoDoc/NanoAODv15/2024/doc_TTH-Hto2G_Par-M-125_TuneCP5_13p6TeV_amcatnloFXFX-pythia8_RunIII2024Summer24NanoAODv15-150X_mcRun3_2024_realistic_v2-v2.html#Electron (NanoAOD v15, 2024 MC). Older versions: noIso MVA IDs buggy in v11/v12 (see Section 5).

`nElectron` = slimmedElectrons after basic selection (`pt > 5`).

| Group | Branches |
| --- | --- |
| Kinematics | `pt`, `eta`, `phi`, `mass`, `charge`, `pdgId` (from reco, not MC truth), `tightCharge` (0 none, 1 isGsfScPixChargeConsistent, 2 isGsfCtfScPixChargeConsistent) |
| Supercluster / energy | `superclusterEta`, `deltaEtaSC` (signed), `scEtOverPt` (SC E_T/pt - 1), `rawEnergy` (raw SC), `ecalEnergy` (ECAL-only regression), `ecalEnergyError`, `energyErr` (cluster-track combination), `PreshowerEnergy` |
| ECAL seed / region | `isEB` (from seed crystal detID), `seedGain`, `seediEtaOriX` (iEta -85..85 barrel / iX 1..100 endcap), `seediPhiOriY` (iPhi 1..360 / iY 1..100) |
| Shower shape / ID vars | `sieie` (full 5x5), `r9` (full 5x5), `hoe`, `eInvMinusPInv` (1/E_SC - 1/p_trk), `fbrem`, `lostHits` (missing inner hits), `convVeto`, `isEcalDriven`, `isPFcand` |
| GSF track | `gsfTrketaMode`, `gsfTrkphiMode`, `gsfTrkpMode`, `gsfTrkpModeErr` |
| Impact parameter | `dxy`, `dxyErr`, `dz`, `dzErr` (signed, wrt first PV, cm); `ip3d`, `sip3d`, `ipLengthSig`, `IPx`, `IPy`, `IPz` |
| Cut-based ID (UChar) | `cutBased` (RunIII Winter22): 0 fail, >=1 veto, >=2 loose, >=3 medium, >=4 tight; `vidNestedWPBitmap` (3 bits per cut) |
| HEEP (Bool) | `cutBased_HEEP`, `vidNestedWPBitmapHEEP` (1 bit per cut) |
| MVA IDs (Winter22V1) | `mvaIso`, `mvaIso_WP80`, `mvaIso_WP90`, `mvaIso_WPHZZ`, `mvaNoIso`, `mvaNoIso_WP80`, `mvaNoIso_WP90`, `mvaHZZIso` (HZZ MVA Iso score), `promptMVA` (ex-mvaTTH) |
| PF isolation | `pfRelIso03_all`, `pfRelIso04_all` (rho x EA PU corr., Winter22V1), `pfRelIso03_chg`, `miniPFRelIso_all` (scaled rho x EA, Winter22V1), `miniPFRelIso_chg` |
| Non-PF isolation (deltaR 0.3, pt > 35 GeV) | `dr03EcalRecHitSumEt`, `dr03HcalDepth1TowerSumEt`, `dr03TkSumPt`, `dr03TkSumPtHEEP` (HEEP) |
| Jet association | `jetIdx`, `jetRelIso` (1/ptRatio-1, -1 if none), `jetPtRelv2`, `jetNDauCharged`, `jetDF` (DeepJet of associated jet, 0 if none) |
| Links / MC | `photonIdx`, `fsrPhotonIdx`, `svIdx`, `genPartIdx`, `genPartFlav` (1 prompt, 15 from prompt tau, 22 prompt photon/conversion, 5 from b, 4 from c, 3 light/unknown, 0 unmatched) |

## 2. IDs
EGM strongly recommends the official WPs + their SFs, via VID in CMSSW (don't re-implement by hand). Performance: DP note https://cds.cern.ch/record/2904365.

### Cut-based (Run3, 122X-tuned, `cutBasedElectronID_RunIII_V1_cff`; NanoAOD `Electron_cutBased`)
| WP | `cutBased` | Eff. | Use case |
| --- | --- | --- | --- |
| Veto | >= 1 | ~95% | lepton veto / counting |
| Loose | >= 2 | ~90% | low backgrounds |
| Medium | >= 3 | ~80% | generic W/Z measurements (good starting point) |
| Tight | >= 4 | ~70% | backgrounds are a serious problem |

Barrel `|eta_SC| <= 1.479` / endcap `|eta_SC| > 1.479` (E_sc in GeV, rho = event energy density):

| Cut | Veto B / E | Loose B / E | Medium B / E | Tight B / E |
| --- | --- | --- | --- | --- |
| full5x5_sigmaIetaIeta < | 0.0117 / 0.0298 | 0.0107 / 0.0275 | 0.0103 / 0.0272 | 0.0101 / 0.027 |
| abs(dEtaSeed) < | 0.0071 / 0.0173 | 0.00691 / 0.0121 | 0.00481 / 0.00951 | 0.00411 / 0.00938 |
| abs(dPhiIn) < | 0.208 / 0.234 | 0.175 / 0.228 | 0.127 / 0.221 | 0.116 / 0.164 |
| H/E < (B) | 0.05+1.28/E_sc+0.0422rho/E_sc | 0.05+1.28/E_sc+0.0422rho/E_sc | 0.0241+1.28/E_sc+0.0422rho/E_sc | 0.02+1.16/E_sc+0.0422rho/E_sc |
| H/E < (E) | 0.05+2.3/E_sc+0.262rho/E_sc | 0.05+2.3/E_sc+0.262rho/E_sc | 0.05+2.3/E_sc+0.262rho/E_sc | 0.02+0.5/E_sc+0.262rho/E_sc |
| relIsoWithEA < (B) | 0.406+0.535/p_T | 0.194+0.535/p_T | 0.0837+0.535/p_T | 0.0388+0.535/p_T |
| relIsoWithEA < (E) | 0.342+0.519/p_T | 0.184+0.519/p_T | 0.0741+0.519/p_T | 0.0544+0.519/p_T |
| abs(1/E - 1/p) < | 0.178 / 0.137 | 0.138 / 0.127 | 0.0966 / 0.111 | 0.023 / 0.018 |
| expected missing inner hits <= | 2 / 3 | 1 / 1 | 1 / 1 | 1 / 1 |
| pass conversion veto | yes | yes | yes | yes |

Isolation is **inside** the cut-based ID (relIsoWithEA) -> no separate isolation WP/SF.

### MVA (Run3 Winter22 V1, trained in 122X; NanoAOD `Electron_mvaIso*` / `Electron_mvaNoIso*`)
| ID | VID tags | NanoAOD | WPs |
| --- | --- | --- | --- |
| Iso | `mvaEleID-RunIIIWinter22-iso-V1-wp80`, `mvaEleID-RunIIIWinter22-iso-V1-wp90` | `mvaIso_WP80`, `mvaIso_WP90` (score `mvaIso`) | wp80 / wp90 = 80% / 90% on the training dataset |
| NoIso | `mvaEleID-RunIIIWinter22-noIso-V1-wp80`, `mvaEleID-RunIIIWinter22-noIso-V1-wp90` | `mvaNoIso_WP80`, `mvaNoIso_WP90` (score `mvaNoIso`) | same |

Both use shower-shape, track-cluster matching, track-quality, conversion and rho inputs (list: https://github.com/cms-sw/cmssw/blob/master/RecoEgamma/ElectronIdentification/data/ElectronIDVariablesRun3.txt); Iso adds 6 isolations (photon, neutral hadron, charged hadron, HCAL cluster, ECAL cluster, tracker).
`mvaIso_WPHZZ`, `mvaHZZIso`, `promptMVA`: branches exist; > TODO: not available (no POG recommendation or SFs in source).

### HEEP (high energy, ~1+ TeV; `Electron_cutBased_HEEP`)
- Cut-based ID page: no Run3 HEEP developed yet -> use Run2 HEEP (EgammaIDRecipesRun2), report worse performance to EGM.
- Run3_ID page: "HEEP ID jsons available now in 2024 and 2025". Cut values: > TODO: not available.

Custom IDs: motivation + SFs must be presented to EGM for approval, **>= 1 month before a conference deadline**; SFs must be in the central format.

## 3. Corrections
### Where to get files (correctionlib)
- CVMFS (use this, always the latest): `/cvmfs/cms-griddata.cern.ch/cat/metadata/EGM/<tag>/latest/` 
- Docs: `https://cms-analysis-corrections.docs.cern.ch/corrections_era/<tag>/EGM/latest/` (2024: `.../EGM/2025-10-22/`; 2025: `https://cms-analysis-corrections.docs.cern.ch/corrections/EGM/Run3-25Prompt-Summer24-NanoAODv15/latest/`)
- Examples: https://gitlab.cern.ch/cms-analysis-corrections/EGM/examples/-/blob/latest/egmScaleAndSmearingExample.py

| Era | `<tag>` | ID SF file (from docs anchor) | S&S file |
| --- | --- | --- | --- |
| 2022 (CD) | `Run3-22CDSep23-Summer22-NanoAODv12` | `electron.json.gz` | `electronSS_EtDependent.json.gz` (NanoAODv12/13) |
| 2022EE (EFG) | `Run3-22EFGSep23-Summer22EE-NanoAODv12` | `electron.json.gz` | same |
| 2023 (C) | `Run3-23CSep23-Summer23-NanoAODv12` | `electron.json.gz` | same |
| 2023BPix (D) | `Run3-23DSep23-Summer23BPix-NanoAODv12` | `electron.json.gz` | same |
| 2024 | `Run3-24CDEReprocessingFGHIPrompt-Summer24-NanoAODv15` | `electron.json.gz` | `electronSS_EtDependent.json.gz` (NanoAODv15) |
| 2025 | `Run3-25Prompt-Summer24-NanoAODv15` | `electron.json.gz` | same (NanoAODv15) |
| 2026 | > TODO: not available | > TODO: not available | same (NanoAODv15) |
| 2022/2023 on NanoAODv15 | - | - | not yet available |

Trigger (HLT) SF JSON: only for 2022 Prompt FG in the old twiki (`Electron-HLT-SF`, see below). For re-reco 2022 and later eras: > TODO: not available.

### How to apply
1. **Energy scale & smearing** (eT-dependent; method: https://cds.cern.ch/record/2920027). Not for e/gamma below ~10 GeV; may be ineffective at very high pT (hundreds of GeV).
   - **Data**: scale only. `scale = cset.compound["Scale"].evaluate("scale", run, scEta, r9, pt, float(seedGain))`; `pt_corr = pt * scale`.
     Correct the regression energy error too: `energyErr_corr = sqrt(energyErr**2 + (energy*smear)**2) * scale`, with `smear` evaluated at `pt*scale`. Energy = `pt*cosh(eta)` (!= `ecalEnergy` for electrons).
   - **MC**: smearing only. `smear = cset["SmearAndSyst"].evaluate("smear", pt, r9, scEta)`; `pt_corr = pt * (1 + smear * N(0,1))`; `energyErr_corr = sqrt(energyErr**2 + (energy*smear)**2) * (1 + smear*N)`.
   - `scEta` is **signed** for corrections released after August 2025 (the older ones took abs(scEta) as well).
2. **ID + Reco SFs (MC only)**: `cset["Electron-ID-SF"].evaluate(year, "sf", WP, eta, pt)`.
   - WP strings: `"RecoBelow20"`, `"Reco20to75"`, `"RecoAbove75"` (Reco SF, pick by electron pT: < 20, 20-75, > 75 GeV), `"Veto"`, `"Loose"`, `"Medium"`, `"Tight"`, `"wp80iso"`, `"wp90iso"`.
   - Per-electron SF = Reco SF x ID SF; event weight = product over selected electrons (standard practice; not spelled out in the source).
   - `year` for 2022 BCD: `"2022Re-recoBCD"`; for 2022 E+Prompt FG: `"2022Re-recoE+PromptFG"`. Other eras: check `cset["Electron-ID-SF"].inputs`.
3. **Trigger SFs (2022 Prompt FG only, old twiki)**: `cset["Electron-HLT-SF"].evaluate("2022FG", "sf", WP, eta, pt)` with WP `"HLT_Ele30_WPTight_Gsf_and_Loose_ID"`, `"HLT_Ele30_WPTight_Gsf_and_Medium_ID"`, `"HLT_Ele30_WPTight_Gsf_and_Tight_ID"`. Measured on offline electrons with ID only.

```python
import awkward as ak, numpy as np, correctionlib

ele = events.Electron
good = ele[(ele.pt > 30) & (abs(ele.superclusterEta) < 2.5)   # kinematic cuts: analysis choice
           & (ele.cutBased >= 3)]                              # Run3 cut-based Medium (iso included)

base = "/cvmfs/cms-griddata.cern.ch/cat/metadata/EGM/"          # pick era subfolder from there
ss = correctionlib.CorrectionSet.from_file(base + ".../electronSS_EtDependent.json.gz")
flat = ak.flatten(good)
pt, r9, sceta = ak.to_numpy(flat.pt), ak.to_numpy(flat.r9), ak.to_numpy(flat.superclusterEta)

if is_data:
    run = ak.to_numpy(ak.flatten(ak.broadcast_arrays(events.run, good.pt)[0]))
    scale = ss.compound["Scale"].evaluate("scale", run, sceta, r9, pt, ak.to_numpy(flat.seedGain).astype(float))
    pt_corr = pt * scale
else:
    smear = ss["SmearAndSyst"].evaluate("smear", pt, r9, sceta)
    rnd = np.random.default_rng(seed).normal(0.0, 1.0, len(pt))   # keep rnd for smear_up/down
    pt_corr = pt * (1 + smear * rnd)

    idsf = correctionlib.CorrectionSet.from_file(base + ".../electron.json.gz")
    eta = ak.to_numpy(flat.eta)                                   # eta vs scEta: not specified in source
    reco_wp = np.where(pt < 20, "RecoBelow20", np.where(pt < 75, "Reco20to75", "RecoAbove75"))
    sf = (np.array([idsf["Electron-ID-SF"].evaluate("2022Re-recoBCD", "sf", w, e, p)
                    for w, e, p in zip(reco_wp, eta, pt)])
          * idsf["Electron-ID-SF"].evaluate("2022Re-recoBCD", "sf", "Medium", eta, pt))
    w_ele = ak.prod(ak.unflatten(sf, ak.num(good)), axis=1)
```

## 4. Systematics
| Source | What to do | Correlation |
| --- | --- | --- |
| ID / Reco / HLT SFs | evaluate with `"sfup"` / `"sfdown"` instead of `"sf"` | > TODO: not available |
| Reco SF, 10-20 GeV | larger systematics (huge background) - expect bigger uncertainty | - |
| Energy scale (MC) | `scale_up/down = cset["SmearAndSyst"].evaluate("scale_up"/"scale_down", pt, r9, scEta)`; apply on the **smeared** MC: `pt_nom_smeared * scale_up`, also scale `energyErr` | separate source; **correlated across years** |
| Energy smearing (MC) | `smear_up/down = cset["SmearAndSyst"].evaluate("smear_up"/"smear_down", pt, r9, scEta)`; apply on the **original** MC pT with the **same random numbers**: `pt * (1 + smear_up * rnd)`; recompute `energyErr` with `smear_up` | separate source; **correlated across years** |
| S&S alt. form | `"escale"`, `"esmear"`: `scale_up = 1 + escale`, `scale_down = 1 - escale`, `smear_up = smear + esmear`, `smear_down = max(0, smear - esmear)` | - |
| Trigger SF + extra offline cuts | trigger SFs measured with ID only; with strong extra isolation / special IP cuts, or removed ID cuts -> re-measure and present to EGM (TnP ntuples: `/eos/cms/store/group/phys_egamma/ec/tnpTuples/rsalvatico/ntuples_Run3/`) | analysis-defined |

S&S systematics go on MC only, never on data.

## 5. Pitfalls / do NOT use
- **noIso MVA IDs in NanoAOD v11/v12** (and MiniAOD v3/v4 `slimmedElectrons`): barrel noIso IDs contain isolation (identical to Iso). NanoAOD fixed in v13 only; contact EGM. MiniAOD fix: `EgammaPostRecoTools` with `setupEgammaPostRecoSeq(..., runVID=True, eleIDModules=[...])`, needs **CMSSW >= 13_3_0**.
- MVA NoIso WP80/WP90 SFs for 2022: "not to be used".
- Old S&S CVMFS path `/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/EGM/` -> use `/cvmfs/cms-griddata.cern.ch/cat/metadata/EGM/`.
- Old twiki S&S JSONs (`electronSS.json.gz` / `SS.json.gz` on `/eos/.../akapoor/S+SJSON/`, keys `Prompt2022FG_ScaleJSON`, `Prompt2022FG_SmearingJSON` with `"total_correction"`, `"rho"`, `"err_rho"`) and the old `/eos/.../akapoor/SFs_PromptReco2022FG/` SF files -> superseded; use eT-dependent `electronSS_EtDependent.json.gz` and the XPOG files.
- Passing `abs(scEta)` to corrections released after August 2025 (they take signed scEta). Using `eta` instead of `superclusterEta` for S&S (the old twiki did so only because scEta was missing in NanoAOD then; v15 has `Electron_superclusterEta`).
- Applying smearing to data or scale to MC; applying S&S below ~10 GeV; trusting S&S at hundreds of GeV without checks.
- Drawing new random numbers for the smear_up/down variations (use the nominal ones).
- Using the `ecalEnergy` branch as "energy" in the S&S energyErr formula (energy = `pt*cosh(eta)` for electrons).
- `cutBased >= 1` is Veto-or-better; to **veto** electrons, require no electron with `cutBased >= 1` (source: "to veto, ask for <1").
- Picking the wrong Reco WP string for the electron pT (`RecoBelow20` / `Reco20to75` / `RecoAbove75`).
- Mixing eras: 2022/2022EE, 2023/2023BPix, and NanoAODv12/13 vs v15 S&S files are separate.
- Custom or hand-modified IDs without EGM approval and SFs.
- Always list `cset.keys()` and each correction's `inputs` before use; key names/years differ between eras.
