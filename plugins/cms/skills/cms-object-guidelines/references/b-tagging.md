# AK4 b/c/qg tagging and AK8 X->bb/cc - CMS BTV recommendations (NanoAOD)

Read this reference when choosing a b-, c- or q/g-tagger and working point (WP), looking up a WP cut for an era, applying BTV fixedWP or shape-correction scale factors (SFs), deriving MC tagging efficiencies, or setting up b-tagging uncertainties and their correlations across eras.

Source: BTV POG wiki (https://btv-wiki.docs.cern.ch/), pages `ScaleFactors/` (index and one page per campaign) and `PerformanceCalibration/` (fixedWP and shape-correction recommendations, SF uncertainties and correlations), local copy retrieved 22 Oct 2026 | Campaigns: Run2 UL 2016preVFP/2016postVFP/2017/2018 (NanoAODv9 and NanoAODv15); Run3 2022/2022EE/2023/2023BPix/2024/2025. Units: GeV.

## Contents
1. Jet selection for BTV SFs
2. Taggers and branches
3. Campaigns: payload paths and supported taggers
4. AK4 b-tagging WPs
5. AK4 c-tagging WPs
6. AK4 q/g-tagging WPs
7. Run2 subjet and AK8 X->bb/cc WPs
8. Applying fixedWP SFs (default)
9. Applying shape-correction SFs
10. Uncertainties and correlations
11. correctionlib usage
12. Pitfalls

## 1. Jet selection for BTV SFs
Apply SFs only to jets that pass:
- AK4CHS (Run2) or AK4PUPPI (Run3)
- pT > 20 GeV
- |eta| < 2.4 for 2016, |eta| < 2.5 for 2017 onward
- tight jet ID (see `jets.md` Section 2)
- loose PU jet ID for pT < 50 GeV (CHS jets only)

Jet flavour = hadron-based definition, `Jet_hadronFlavour`: 5 = b, 4 = c, 0 = light (udsg).

## 2. Taggers and branches
WPs and SFs are valid only for these exact discriminants.

| Tagger | b tag (NanoAOD) | CvL / CvB (NanoAOD) | Where |
| --- | --- | --- | --- |
| UParTAK4 (UnifiedParT) | `Jet_btagUParTAK4B` | `Jet_btagUParTAK4CvL` / `Jet_btagUParTAK4CvB` | Run2 v15, Run3 2024+ (only supported tagger there) |
| RobustParT | `Jet_btagRobustParTAK4B` | `Jet_btagRobustParTAK4CvL` / `Jet_btagRobustParTAK4CvB` | Run3 2022-2023 (NanoAODv12) |
| ParticleNet | `Jet_btagPNetB` | `Jet_btagPNetCvL` / `Jet_btagPNetCvB` | Run3 2022-2023 |
| DeepJet | `Jet_btagDeepFlavB` | `Jet_btagDeepFlavCvL` / `Jet_btagDeepFlavCvB` | Run2 v9, Run3 2022-2023 |
| DeepCSV | `Jet_btagDeepB` | `Jet_btagDeepCvL` / `Jet_btagDeepCvB` | Run2 v9 only |

MiniAOD equivalents:
- UParT: `pfUnifiedParticleTransformerAK4DiscriminatorsJetTags:BvsAll`, `:CvsL`, `:CvsB`.
- PNet: `pfParticleNetFromMiniAODAK4PuppiCentralDiscriminatorsJetTags:BvsAll`, `:CvsL`, `:CvsB`.
- DeepJet: `pfDeepFlavourJetTags:probb + probbb + problepb`; CvL = probc / (probc + probuds + probg); CvB = probc / (probc + probb + probbb + problepb).
- RobustParT: same sums as DeepJet with `pfParticleTransformerAK4JetTags`.
- DeepCSV: `pfDeepCSVJetTags:probb + probbb`; CvL = probc / (probc + probudsg); CvB = probc / (probc + probb + probbb).

q/g taggers:

| Tagger | NanoAOD |
| --- | --- |
| UParT | `Jet_btagUParTAK4QvG` (after NanoAODv12) |
| RobustParT | `Jet_btagRobustParTAK4QG` (NanoAODv12 only) |
| ParticleNet | Run3 `Jet_btagPNetQvG`; Run2 only in JMENano (`particleNetAK4_QvsG`), not in NanoAODv9 |
| DeepJet | `Jet_btagDeepFlavQG`. WPs and SFs are defined for **1 - DeepJet** (flipped likelihood) |
| QGL | `Jet_qgl` (Run2 only) |

AK8 X->bb/cc (Run2 v9): ParticleNet-MD `particleNetMD_Xbb / (particleNetMD_Xbb + particleNetMD_QCD)` (and `Xcc` likewise), `btagDDBvLV2`/`btagDDCvLV2` (DeepDoubleX), `deepTagMD_ZHbbvsQCD`/`deepTagMD_ZHccvsQCD` (DeepAK8-MD), `btagHbb` (double-b). For Run3 boosted tagging see `fat-jets.md`.

## 3. Campaigns: payload paths and supported taggers
Payloads: `/cvmfs/cms-griddata.cern.ch/cat/metadata/BTV/<tag>/latest/` with `btagging.json.gz`, `ctagging.json.gz` (Run2 v9 also `qgtagging.json.gz`, `ak8_xbbcc_tagging.json.gz`). Synced to https://gitlab.cern.ch/cms-analysis-corrections/BTV.

| Era | MC campaign | `<tag>` | Taggers | Status |
| --- | --- | --- | --- | --- |
| 2016preVFP | RunIISummer20UL16 (APV) NanoAODv9 | `Run2-2016preVFP-UL-NanoAODv9` | DeepJet, DeepCSV | final |
| 2016postVFP | RunIISummer20UL16 NanoAODv9 | `Run2-2016postVFP-UL-NanoAODv9` | DeepJet, DeepCSV | final |
| 2017 | RunIISummer20UL17NanoAODv9 | `Run2-2017-UL-NanoAODv9` | DeepJet, DeepCSV | final |
| 2018 | RunIISummer20UL18NanoAODv9 | `Run2-2018-UL-NanoAODv9` | DeepJet, DeepCSV | final |
| 2016preVFP / 2016postVFP / 2017 / 2018 | RunIISummer20UL1x NanoAODv15 | `Run2-<era>-UL-NanoAODv15` | UParTAK4 only (json only) | WIP: b WPs (Mar 2026), preliminary fixedWP SFs (Jun 2026); c and q/g WIP |
| 2022 (CD) | Run3Summer22 | `Run3-22CDSep23-Summer22-NanoAODv12` | DeepJet, RobustParT, PNet | WIP |
| 2022EE (EFG) | Run3Summer22EE | `Run3-22EFGSep23-Summer22EE-NanoAODv12` | DeepJet, RobustParT, PNet | WIP |
| 2023 (C) | Run3Summer23 | `Run3-23CSep23-Summer23-NanoAODv12` | DeepJet, RobustParT, PNet | WIP |
| 2023BPix (D) | Run3Summer23BPix | `Run3-23DSep23-Summer23BPix-NanoAODv12` | DeepJet, RobustParT, PNet | WIP |
| 2024 | RunIII2024Summer24 | `Run3-24CDEReprocessingFGHIPrompt-Summer24-NanoAODv15` | UParTAK4 only (json only) | WIP |
| 2025 | RunIII2024Summer24 | `Run3-25Prompt-Summer24-NanoAODv15` | UParTAK4 only (json only) | WIP: preliminary fixedWP SFs |

Note on 2016: by CMS convention the APV MC (`RunIISummer20UL16APV`) is **preVFP**. The BTV index table lists the APV campaign next to postVFP, so match by era name (preVFP/postVFP), not by that table row.

Run 3 SF availability (from BTV CMSTalk announcements):
- 2022/2022EE: b fixedWP combined SFs with split uncertainties, shape SFs, c fixedWP SFs (Jul 2025).
- 2023/2023BPix: b fixedWP combined SFs, mistag SFs, shape SFs, c fixedWP SFs. PNet combination added Sep 2025, but not in the muon-enriched phase space.
- 2024: first b fixedWP combination (Mar 2026), with `comb` = kinFit (ttbar) + pTRel (QCD) and `mujets` = pTRel only; light SFs preliminary (negtagDY, Dec 2025).

Superseded partial re-reco campaigns (NanoAODv11 only): 2022 C+D `27Jun2023` and 2022 E+F+G `27Jun2023EE` (paths `/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/2022_27Jun2023` and `.../POG/BTV/2022_27Jun2023EE`) with tagger `deepJetRun2`. Valid **only** for the old Run2-trained CHS DeepJet in NanoAODv11; never use them for another NanoAOD release.

## 4. AK4 b-tagging WPs
WP definitions by light-jet mistag rate: L 10%, M 1%, T 0.1%, XT 0.05%, XXT 0.01%. **XT and XXT are experimental** (Run3 and Run2 v15 only): test before use.
Cuts are on the b discriminant (`> cut` passes). Read them from the payload rather than copying (Section 11); these tables are for orientation.

Run2 UL NanoAODv9:

| Era | DeepJet L | DeepJet M | DeepJet T | DeepCSV L | DeepCSV M | DeepCSV T |
| --- | --- | --- | --- | --- | --- | --- |
| 2016preVFP | 0.0508 | 0.2598 | 0.6502 | 0.2027 | 0.6001 | 0.8819 |
| 2016postVFP | 0.0480 | 0.2489 | 0.6377 | 0.1918 | 0.5847 | 0.8767 |
| 2017 | 0.0532 | 0.3040 | 0.7476 | 0.1355 | 0.4506 | 0.7738 |
| 2018 | 0.0490 | 0.2783 | 0.7100 | 0.1208 | 0.4168 | 0.7665 |

Run2 UL NanoAODv15 and Run3 2024/2025, UParTAK4:

| Era | L | M | T | XT | XXT |
| --- | --- | --- | --- | --- | --- |
| 2016preVFP v15 | 0.0387 | 0.1847 | 0.5467 | 0.6777 | 0.9218 |
| 2016postVFP v15 | 0.0400 | 0.1898 | 0.5538 | 0.6872 | 0.9353 |
| 2017 v15 | 0.0331 | 0.1776 | 0.5755 | 0.7274 | 0.9666 |
| 2018 v15 | 0.0308 | 0.1610 | 0.5405 | 0.6992 | 0.9655 |
| 2024 | 0.0246 | 0.1272 | 0.4648 | 0.6298 | 0.9739 |
| 2025 | 0.0246 | 0.1272 | 0.4648 | 0.6298 | 0.9739 |

Run3 2022-2023 (NanoAODv12):

| Era | Tagger | L | M | T | XT | XXT |
| --- | --- | --- | --- | --- | --- | --- |
| 2022 | DeepJet | 0.0583 | 0.3086 | 0.7183 | 0.8111 | 0.9512 |
| 2022 | RobustParT | 0.0849 | 0.4319 | 0.8482 | 0.9151 | 0.9874 |
| 2022 | PNet | 0.047 | 0.245 | 0.6734 | 0.7862 | 0.961 |
| 2022EE | DeepJet | 0.0614 | 0.3196 | 0.73 | 0.8184 | 0.9542 |
| 2022EE | RobustParT | 0.0897 | 0.451 | 0.8604 | 0.9234 | 0.9893 |
| 2022EE | PNet | 0.0499 | 0.2605 | 0.6915 | 0.8033 | 0.9664 |
| 2023 | DeepJet | 0.0479 | 0.2431 | 0.6553 | 0.7667 | 0.9459 |
| 2023 | RobustParT | 0.0681 | 0.3487 | 0.7969 | 0.8882 | 0.9883 |
| 2023 | PNet | 0.0358 | 0.1917 | 0.6172 | 0.7515 | 0.9659 |
| 2023BPix | DeepJet | 0.048 | 0.2435 | 0.6563 | 0.7671 | 0.9483 |
| 2023BPix | RobustParT | 0.0683 | 0.3494 | 0.7994 | 0.8877 | 0.9883 |
| 2023BPix | PNet | 0.0359 | 0.1919 | 0.6133 | 0.7544 | 0.9688 |

Reference b-jet efficiencies (before SFs) are on each campaign's BTV page (e.g. at M in QCD: 71-81% for DeepJet Run2, 79-84% for the Run3 taggers).

## 5. AK4 c-tagging WPs
WP definitions: L (b eff. 35%, light eff. 90%), M (25%, 25%), T (20%, 3%), XT (10%, 1%; experimental, Run3 only). A jet is c-tagged if **CvL > cut and CvB > cut**.

| Era | Tagger | L (CvL, CvB) | M (CvL, CvB) | T (CvL, CvB) | XT (CvL, CvB) |
| --- | --- | --- | --- | --- | --- |
| 2016preVFP v9 | DeepJet | 0.039, 0.327 | 0.098, 0.370 | 0.270, 0.256 | - |
| 2016preVFP v9 | DeepCSV | 0.088, 0.214 | 0.181, 0.228 | 0.417, 0.138 | - |
| 2016postVFP v9 | DeepJet | 0.039, 0.305 | 0.099, 0.353 | 0.269, 0.247 | - |
| 2016postVFP v9 | DeepCSV | 0.088, 0.204 | 0.180, 0.221 | 0.407, 0.136 | - |
| 2017 v9 | DeepJet | 0.030, 0.400 | 0.085, 0.340 | 0.520, 0.050 | - |
| 2017 v9 | DeepCSV | 0.040, 0.345 | 0.144, 0.290 | 0.730, 0.100 | - |
| 2018 v9 | DeepJet | 0.038, 0.246 | 0.099, 0.325 | 0.282, 0.267 | - |
| 2018 v9 | DeepCSV | 0.064, 0.313 | 0.153, 0.363 | 0.405, 0.288 | - |
| 2022 | DeepJet | 0.042, 0.208 | 0.108, 0.299 | 0.303, 0.243 | - |
| 2022 | RobustParT | 0.039, 0.068 | 0.117, 0.130 | 0.360, 0.095 | - |
| 2022 | PNet | 0.054, 0.181 | 0.160, 0.306 | 0.492, 0.259 | - |
| 2022EE | DeepJet | 0.042, 0.206 | 0.108, 0.298 | 0.305, 0.241 | - |
| 2022EE | RobustParT | 0.039, 0.067 | 0.117, 0.128 | 0.358, 0.095 | - |
| 2022EE | PNet | 0.054, 0.182 | 0.160, 0.304 | 0.491, 0.258 | - |
| 2023 | DeepJet | 0.042, 0.235 | 0.102, 0.322 | 0.250, 0.262 | 0.371, 0.441 |
| 2023 | RobustParT | 0.038, 0.087 | 0.109, 0.153 | 0.308, 0.113 | 0.469, 0.275 |
| 2023 | PNet | 0.052, 0.221 | 0.148, 0.353 | 0.434, 0.300 | 0.634, 0.549 |
| 2023BPix | DeepJet | 0.042, 0.242 | 0.102, 0.328 | 0.250, 0.267 | 0.371, 0.444 |
| 2023BPix | RobustParT | 0.038, 0.091 | 0.110, 0.157 | 0.308, 0.116 | 0.469, 0.281 |
| 2023BPix | PNet | 0.052, 0.228 | 0.149, 0.358 | 0.436, 0.303 | 0.634, 0.552 |
| 2024, 2025 | UParTAK4 | 0.086, 0.233 | 0.291, 0.457 | 0.650, 0.421 | 0.810, 0.736 |

Run2 NanoAODv15: c-tagging WPs are WIP (not available).

## 6. AK4 q/g-tagging WPs
Run2 UL NanoAODv9 only (json only, `qgtagging.json.gz`); Run3 and Run2 v15 are WIP. WP definitions: L (quark eff. about 90%), M (gluon eff. about 33%), T (gluon eff. about 10%).

| Era | QGL L / M / T | DeepJet (1 - score) L / M / T | PNet (JMENano) L / M / T |
| --- | --- | --- | --- |
| 2016preVFP | 0.09 / 0.59 / 0.91 | 0.14 / 0.32 / 0.55 | 0.20 / 0.38 / 0.59 |
| 2016postVFP | 0.09 / 0.57 / 0.91 | 0.13 / 0.30 / 0.53 | 0.19 / 0.35 / 0.57 |
| 2017 | 0.07 / 0.54 / 0.90 | 0.12 / 0.27 / 0.48 | 0.16 / 0.32 / 0.54 |
| 2018 | 0.07 / 0.50 / 0.89 | 0.12 / 0.27 / 0.48 | 0.16 / 0.33 / 0.55 |

## 7. Run2 subjet and AK8 X->bb/cc WPs
Run2 UL NanoAODv9 only.

Soft-drop subjet b-tagging: **DeepCSV only**, L and M (csv files only):

| Era | L | M |
| --- | --- | --- |
| 2016preVFP | 0.2027 | 0.6001 |
| 2016postVFP | 0.1918 | 0.5847 |
| 2017 | 0.1355 | 0.4506 |
| 2018 | 0.1208 | 0.4506 |

(2018 subjet M = 0.4506 as listed by BTV, which differs from the 2018 AK4 DeepCSV M = 0.4168; check the payload.)

AK8 X->bb vs QCD (H->bb eff.: L 80%, M 60%, T 40%):

| Tagger | 2016preVFP L/M/T | 2016postVFP L/M/T | 2017 L/M/T | 2018 L/M/T |
| --- | --- | --- | --- | --- |
| ParticleNet-MD XbbvsQCD | 0.9088 / 0.9737 / 0.9883 | 0.9137 / 0.9735 / 0.9883 | 0.9105 / 0.9714 / 0.9870 | 0.9172 / 0.9734 / 0.9880 |
| btagDDBvLV2 | 0.0256 / 0.1180 / 0.2739 | 0.0270 / 0.1213 / 0.2786 | 0.0404 / 0.1566 / 0.3154 | 0.0399 / 0.1566 / 0.3140 |
| deepTagMD_ZHbbvsQCD | 0.7021 / 0.8940 / 0.9521 | 0.6890 / 0.8877 / 0.9507 | 0.7422 / 0.9033 / 0.9546 | 0.7432 / 0.9058 / 0.9551 |
| btagHbb | 0.3104 / 0.7559 / 0.8926 | 0.3279 / 0.7646 / 0.8955 | 0.5068 / 0.8237 / 0.9185 | 0.4939 / 0.8193 / 0.9175 |

AK8 X->cc vs QCD (H->cc eff.: L 50%, M 30%, T 15%):

| Tagger | 2016preVFP L/M/T | 2016postVFP L/M/T | 2017 L/M/T | 2018 L/M/T |
| --- | --- | --- | --- | --- |
| ParticleNet-MD XccvsQCD | 0.9252 / 0.9751 / 0.9909 | 0.9252 / 0.9743 / 0.9905 | 0.9347 / 0.9765 / 0.9909 | 0.9368 / 0.9777 / 0.9917 |
| btagDDCvLV2 | 0.0327 / 0.1043 / 0.2568 | 0.0321 / 0.1021 / 0.2505 | 0.0457 / 0.1361 / 0.3013 | 0.0425 / 0.1322 / 0.3013 |
| deepTagMD_ZHccvsQCD | 0.6733 / 0.8496 / 0.9326 | 0.6458 / 0.8369 / 0.9277 | 0.7100 / 0.8677 / 0.9390 | 0.7017 / 0.8662 / 0.9390 |

## 8. Applying fixedWP SFs (default)
**Default: Method 1a (event reweighting with SFs and MC efficiencies).** No events migrate between b-tag multiplicity bins.

- Apply to **every jet whose tag status the analysis queries**, including "0 b-tag" control regions. Ignore jets the analysis never uses (e.g. pT < 30 GeV if you only use jets above 30).
- "b-tagged" (reco: passes WP) is not "b jet" (truth: `hadronFlavour == 5`).
- Which SF per flavour (b-tagging): b and c jets (flavour 5, 4) use `comb` or `mujets`; light jets (0) use `incl`. In b-tagging, c jets share the b-jet SF and uncertainty.
  - `mujets` = QCD/muon-enriched methods; `comb` = `mujets` + ttbar methods. 2022: mujets = pTRel + system8, comb = + TnP. 2023: mujets = pTRel + system8 + LTSV, comb = + TnP. 2024: mujets = pTRel, comb = + kinFit.
- One WP, per event:

```text
w = prod_{tagged j} SF_j  *  prod_{not tagged j} (1 - SF_j * eff_j) / (1 - eff_j)
```
  where SF_j = SF(pT, eta, flavour) from BTV and eff_j = MC tagging efficiency (below).
- Several WPs (e.g. L and T): tagged at T -> SF_T; tagged at L but not T -> (SF_L * eff_L - SF_T * eff_T) / (eff_L - eff_T); not tagged at L -> (1 - SF_L * eff_L) / (1 - eff_L). If the numerator of the middle factor is negative (happens when SF_T > SF_L in a bin), **set that factor to 1**.
- BTV example implementation: https://gitlab.cern.ch/cms-analysis-corrections/BTV/examples/-/blob/latest/lib/btag_sf.py

**MC tagging efficiencies (you must derive them):**
- eff[pT, eta, flavour] = N(tagged) / N(all) per truth flavour (b, c, light separately), for each WP used.
- Derive after the analysis selection but **before any b-tag requirement**.
- Suggested pT bins: `[20, 30, 50, 70, 100, 140, 200, 300, 600, 1000]`. eta: one bin, barrel/endcap, or a few bins, depending on MC statistics.
- Derive per process group (e.g. ttbar vs multijet differ by a few percent).

**b- and c-tagging together:** fixedWP b and c SFs are not multiplicative, so they can't both be used. If you need both, use the c-tagging shape-correction SFs. c-tagging fixedWP SFs: b jets `TnP`, c jets `wcharm`/`wc`, light `incl`/`light`; one c WP at a time and no b WP alongside.
**q/g tagging together with b tagging:** compute the two event weights independently.

## 9. Applying shape-correction SFs
Use only if you use the full discriminant distribution (e.g. as an MVA input). Uncertainties are larger than for fixedWP.

```text
w = prod_{selected jets i} SF(discriminant_i, pT_i, eta_i, flavour_i)
```
- c jets get SF = 1 (uncertainty `cferr1/2` only).
- **Normalization is mandatory**: the weights must preserve yields before any b-tag selection. Compute r = sum(w_before) / sum(w_after) with no b-tag requirement, and multiply the weight by r. Derive r per jet-multiplicity bin (and per flavour composition, process and uncertainty variation where relevant). Every analysis must cross-check this.
- After a b-tag multiplicity selection, yields are allowed to change.
- c-tagging shape SFs (CvL/CvB) apply the same SF to all jets and also correct the b-tag distribution, so b WPs can be used with them.

## 10. Uncertainties and correlations
**fixedWP b-tagging:**
- One era: `up` / `down`, separately for b/c jets and light jets.
- Several eras: use `up/down_correlated` and `up/down_uncorrelated`. For all of Run 2 that gives 10 nuisances: `btagSFbc_correlated`, `btagSFlight_correlated`, plus `btagSFbc_<era>` and `btagSFlight_<era>` for 2016preVFP, 2016postVFP, 2017, 2018. Same scheme for Run 3.
- A finer split of the b/c uncertainty exists for analyses dominated by b-tagging; ask the BTV conveners or PAG contacts before using it.

**fixedWP c-tagging:** `up/down` for b, c and light jets, each correlated between eras.

**Shape (iterativeFit) b-tagging:**

| Source | Applies to | Across eras |
| --- | --- | --- |
| `hf`, `lf` (purity, +/-20% contamination) | b and light simultaneously | correlated |
| `hfstats1/2`, `lfstats1/2` (statistics) | b and light simultaneously | uncorrelated |
| `cferr1/2` | c jets only | correlated |
| `jes`, `jes_<source>` (`up/down_JESRegrouped_<source>`) | b and light | follow the JERC scheme; use the JES-varied SF on the JES-varied template **instead of** the nominal |

Variations are named `up_<source>` / `down_<source>`.

**Shape c-tagging:** 13 sources (`Extrap`, `Interp`, `LHEScaleWeight_muF`, `LHEScaleWeight_muR`, `PSWeightFSR`, `PSWeightISR`, `PUWeight`, `Stat`, `XSec_BRUnc_DYJets_b`, `XSec_BRUnc_DYJets_c`, `XSec_BRUnc_WJets_c`, `jer`, `jesTotal`). All are correlated across eras except `Stat`, and all are correlated across flavours.

## 11. correctionlib usage
Read WPs from the payload (from the BTV index):

```python
import correctionlib
BASE = "/cvmfs/cms-griddata.cern.ch/cat/metadata/BTV/Run3-24CDEReprocessingFGHIPrompt-Summer24-NanoAODv15/latest"
cset = correctionlib.CorrectionSet.from_file(f"{BASE}/btagging.json.gz")
print(list(cset.keys()))                          # correction names differ per campaign and tagger
print(cset["deepJet_wp_values"].evaluate("M"))    # pattern from the BTV index; use the key present in your file
ccset = correctionlib.CorrectionSet.from_file(f"{BASE}/ctagging.json.gz")
print(ccset["deepJet_wp_values"].evaluate("M", "CvL"), ccset["deepJet_wp_values"].evaluate("M", "CvB"))
```

Evaluate fixedWP SFs generically, by input name (sketch, not run; check names with `[i.name for i in c.inputs]`):

```python
c = cset[f"{tagger}_comb"]          # b/c jets; f"{tagger}_incl" for light jets
args = {"systematic": "central", "working_point": "M", "flavor": flav, "abseta": abs(eta), "pt": pt}
sf = c.evaluate(*[args[i.name] for i in c.inputs])
```
Payload descriptions: https://cms-analysis-corrections.docs.cern.ch/corrections/BTV/ ; examples: https://gitlab.cern.ch/cms-analysis-corrections/BTV/examples

## 12. Pitfalls
- Using a WP or SF from another tagger, era or NanoAOD version. Each campaign's WPs and SFs are valid only for its exact discriminant.
- Run2 NanoAODv15 and Run3 2024/2025: **only UParTAK4** is supported, and only as json (no csv). DeepJet/PNet SFs don't exist there.
- Partial re-reco 2022 (`27Jun2023`, `27Jun2023EE`) `deepJetRun2` WPs/SFs on NanoAODv12+ (they are only for NanoAODv11 CHS DeepJet).
- Treating XT/XXT as validated: they are experimental.
- Copying MC efficiencies from another analysis or deriving them after a b-tag selection.
- Not applying SFs to jets in 0-tag regions while still using their tag status.
- Using b- and c-tagging fixedWP SFs together (not multiplicative).
- DeepJet q/g: WPs and SFs are on `1 - btagDeepFlavQG`.
- Shape SFs without the yield normalization factor r.
- 2016postVFP light SFs (`incl`, v9): BTV saw problems in some measurements. If you see issues, contact your PAG BTV contacts; the recommended fix is to use the 2016preVFP light SFs for 2016postVFP.
- Run3 2023 PNet: the `comb` SF is TnP (ttbar) only, and there is no PNet combination in the muon-enriched phase space. The combination may also be limited above jet pT of about 300 GeV, and methods show 1-2 sigma tensions in some bins.
- Run3 2022: `isr`, `fsr`, `qcdscale` uncertainties are not available in `comb`; `bfragmentation`, `colorreconnection` and `pdf` were added.
- Most Run3 and all Run2 v15 campaigns are marked WIP by BTV: re-check the campaign page before unblinding.
