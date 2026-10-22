# AK8 jets (FatJet) - CMS JME/JMAR recommendations (NanoAOD)

Read this reference when selecting AK8 PUPPI jets, choosing or constructing a boosted top/W/Z/H tagger discriminant, applying boosted-tagging scale factors, or correcting multi-prong signal jets with Lund jet-plane reweighting.

Source: CMS JME/JMAR pages "Boosted-object tagging" and "Lund jet-plane reweighting"; XPOG NanoAOD autoDoc v12 (Run3Summer22) and v15 (RunIII2024Summer24) `FatJet` tables (retrieved 22 Oct 2026) | Campaigns: Run2 UL NanoAODv9; Run3 NanoAODv12/v15

**Shared with AK4:** JEC/JER keys (`fatJet_jerc.json.gz`, `*_AK8PFPuppi`) and JES correlations -> `jets-jerc.md`; jet veto maps -> `jets.md` Section 3. Units: GeV.

## Contents
0. Collections and branches
1. Jet ID
2. Jet mass
3. Taggers by NanoAOD version
4. Discriminant definitions
5. Scale factors
6. Lund jet-plane reweighting (LPR)
7. Pitfalls

## 0. Collections and branches
`FatJet` = `slimmedJetsAK8`, AK8 **PUPPI** jets, in all of v9, v12 and v15. Subjets: `SubJet` via `FatJet_subJetIdx1/2`.

| Group | Branches |
| --- | --- |
| Kinematics | `pt`, `eta`, `phi`, `mass` (JEC-corrected), `rawFactor`, `area` |
| Groomed mass | `msoftdrop` (corrected soft-drop mass, PUPPI) |
| Substructure | `tau1`-`tau4` (N-subjettiness), `n2b1`, `n3b1` (only for raw pT > 250 GeV), `lsf3` (lepton subjet fraction) |
| Energy fractions (v15 only) | `chHEF`, `neHEF`, `chEmEF`, `neEmEF`, `muEF`, `hfHEF`, `hfEmEF` |
| Multiplicities | `nConstituents`; v15: `chMultiplicity`, `neMultiplicity` (Puppi-weighted) |
| Links | `subJetIdx1/2`, `electronIdx3SJ`, `muonIdx3SJ`, `genJetAK8Idx` |
| MC truth | `hadronFlavour`; v12: `nBHadrons`, `nCHadrons` |
| Jet ID | v9/v12: `jetId` bitmap; v15: **none** (see Section 1) |
| Constituents (v15) | `FatJetPFCand` (`jetIdx`, `pfCandIdx`) -> `PFCand` (Puppi-weighted `pt`, `mass`; `eta`, `phi`, `pdgId`), only \|eta\| <= 2.5 |

v12 also has older taggers: `btagDDBvLV2`, `btagDDCvBV2`, `btagDDCvLV2` (DeepDoubleX), `btagDeepB`, `btagHbb`.

## 1. Jet ID
AK8 jets use the AK4 Jet ID of the same type, which is PUPPI for `FatJet`. Cut tables are in `jets.md` Section 2.

| NanoAOD | How |
| --- | --- |
| v9 (Run2 UL), v12 | `FatJet_jetId` bitmap: bit 2 = tight, bit 3 = tightLepVeto. Test `(FatJet_jetId & 2) != 0` / `(FatJet_jetId & 4) != 0`. (v12 doc: bit 1 = loose, always false in 2017.) |
| v15 Run3 | No `FatJet_jetId`. Evaluate `jetid.json.gz` with the `AK8*` key of the campaign (see `jets.md` Section 2). |
| v15 Run2 UL | No `FatJet_jetId`. Apply the Run2 UL AK4 PUPPI cuts from `jets.md` Section 2 to the `FatJet_*EF` / multiplicity branches. |

## 2. Jet mass
| Quantity | Formula / branch | NanoAOD |
| --- | --- | --- |
| Soft-drop mass | `FatJet_msoftdrop` | all |
| GlobalParT-3 regressed mass (generic) | `globalParT3_massCorrGeneric * mass * (1 - rawFactor)` | v15 |
| GlobalParT-3 regressed mass (2-prong bb/cc/cs/ss/qq) | `globalParT3_massCorrX2p * mass * (1 - rawFactor)` | v15 |
| ParticleNet (Run 3) regression | `particleNet_massCorr * mass` (relative to JEC-corrected mass, no soft-drop) | v12, v15 |
| ParticleNet legacy regression | `particleNetLegacy_mass` | v15 |

Note that GloParT-3 corrections multiply the **raw** mass, while `particleNet_massCorr` multiplies the JEC-corrected mass.
JMS/JMR (mass scale and resolution) corrections are not covered in these sources. > TODO: add from the JMAR jet-mass recommendation page.

## 3. Taggers by NanoAOD version
All outputs below are for AK8 PUPPI jets.

| Model | Mass-decorrelated (MD) | Mass-correlated | NanoAOD |
| --- | --- | --- | --- |
| GlobalParT-3 | `FatJet_globalParT3_*` | `FatJet_globalParT3_withMass*` | v15 |
| ParticleNet (Run 3) | `FatJet_particleNet_*` | - | v12, v15 |
| ParticleNet legacy (Run 2) | `FatJet_particleNetLegacy_*` | `FatJet_particleNetWithMass_*` | v12, v15 |
| ParticleNet legacy (Run 2) | `FatJet_particleNetMD_*` | `FatJet_particleNet_*` | v9 |

**The same prefix means different models in different versions.** In v9, `particleNet_*` is the mass-correlated legacy model, called `particleNetWithMass_*` in v12/v15. In v12/v15, `particleNet_*` is the Run 3 MD model.
Mass-correlated outputs sculpt the background jet-mass distribution. Validate before using them in a mass fit.

GlobalParT-3 raw classes (v15): `QCD`, `Xbb`, `Xcc`, `Xcs`, `Xqq`, `Xtauhtaue`, `Xtauhtaum`, `Xtauhtauh`, `XWW4q`, `XWW3q`, `XWWqqev`, `XWWqqmv`, `TopbWqq`, `TopbWq`, `TopbWev`, `TopbWmv`, `TopbWtauhv`.

## 4. Discriminant definitions
Build MD discriminants from the raw class scores, `P(X)` = `FatJet_<prefix>_X`.

| Target | GlobalParT-3 (v15) | ParticleNet Run 3 (v12/v15) | ParticleNet legacy (`Legacy_` v12/v15, `MD_` v9) |
| --- | --- | --- | --- |
| Top | (TopbWqq + TopbWq) / (TopbWqq + TopbWq + QCD) | no MD top score | no MD top score |
| W | (Xcs + Xqq/3) / (Xcs + Xqq/3 + QCD) | stored `particleNet_WVsQCD` | (Xcc + Xqq) / (Xcc + Xqq + QCD) |
| Z | (Xbb + Xcc + Xqq) / (... + QCD) | rZ = sum of s/(1-s) over `XbbVsQCD`, `XccVsQCD`, `XqqVsQCD`; DZ = rZ/(1+rZ) | (Xbb + Xcc + Xqq) / (... + QCD) |
| H->bb | Xbb / (Xbb + QCD) | stored `particleNet_XbbVsQCD` | Xbb / (Xbb + QCD) |
| H->cc | Xcc / (Xcc + QCD) | stored `particleNet_XccVsQCD` | Xcc / (Xcc + QCD) |

- **Don't use the stored `FatJet_globalParT3_WvsQCD`** for W tagging. It uses Xcs + Xqq without the 1/3 factor, and the GloParT recipe advises against it.
- The legacy W definition is unweighted. Adding a 1/3 factor makes a different discriminant that needs its own calibration.
- Mass-correlated discriminants are stored directly. GloParT-3: `globalParT3_withMass{Top,W,Z}vsQCD`. Legacy: `particleNetWithMass_{T,W,Z}vsQCD` (v9: `particleNet_{T,W,Z}vsQCD`).
- Never use a `withMass` working point on an MD discriminant, and never swap in a similarly named score from another model generation.
- **H->bb with top veto (GloParT-3):** Xbb / (Xbb + QCD + alpha(TopbWq + TopbWqq)). Optimize alpha for the analysis. This is a new discriminator and needs its own calibration.
- **H->WW / multi-prong (GloParT-3):** P_S = XWW4q + XWW3q + XWWqqev + XWWqqmv; P_top = TopbWqq + TopbWq + TopbWev + TopbWmv + ... (the source equation is truncated; check the GloParT multi-prong recommendation); D_WW = P_S / (P_S + alpha_top P_top + alpha_QCD QCD). Only the ratio alpha_top : alpha_QCD matters; tune it to the expected top/QCD mix after preselection.

```python
# GloParT-3 MD discriminants (NanoAOD v15); not run yet.
F = events.FatJet
p = lambda c: getattr(F, f"globalParT3_{c}")
top = p("TopbWqq") + p("TopbWq")
D_top = top / (top + p("QCD"))
w = p("Xcs") + p("Xqq") / 3
D_W = w / (w + p("QCD"))
z = p("Xbb") + p("Xcc") + p("Xqq")
D_Z = z / (z + p("QCD"))
D_bb = p("Xbb") / (p("Xbb") + p("QCD"))
```

## 5. Scale factors
These are **signal-efficiency SFs only**. Derive background mistag corrections in situ in analysis control regions.

### Calibration sources
| Target | Calibration |
| --- | --- |
| Top, W | JMAR ParticleNetSFs framework (semileptonic ttbar, pass/fail fit in soft-drop mass) |
| Z->bb, Z->cc (MD) | BTV boosted proxy-jet calibrations; Z->qq: W jets as proxy; or a boosted-Z fit in Z+jets (MD or mass-correlated) |
| H->bb, H->cc | BTV boosted-object calibration recommendations |
| Multi-prong (H->WW, ...) without direct calibration | LPR (Section 6) |

### correctionlib: `jmar.json.gz`
`/cvmfs/cms-griddata.cern.ch/cat/metadata/JME/<campaign>/latest/jmar.json.gz`. ParticleNet inputs: `eta`, `pt`, `systematic`, `workingpoint`.

| Campaign | Keys |
| --- | --- |
| `Run2-2016preVFP-UL-NanoAODv9`, `Run2-2016postVFP-UL-NanoAODv9` | `ParticleNet_Top_Nominal`, `ParticleNet_W_Nominal`, `ParticleNet_W_MD` |
| `Run2-2017-UL-NanoAODv9`, `Run2-2018-UL-NanoAODv9` | same, plus `Top_tagging_PUPPI_FullyMerged`, `Top_tagging_PUPPI_NotMerged` (two-category merge scheme) |

```python
import correctionlib
sf = correctionlib.CorrectionSet.from_file("jmar.json.gz")["ParticleNet_Top_Nominal"]
vals = {"eta": FatJet_eta, "pt": FatJet_pt, "systematic": "nom", "workingpoint": "0p1"}
w = sf.evaluate(*(vals[i.name] for i in sf.inputs))
```
Valid `workingpoint` strings differ per key, so list them from the payload before use.

### Run2 UL ParticleNet (NanoAODv9, CMS-DP-2025-010)
Fully merged hadronic top/W, |eta| < 2.4, per era (2016preVFP, 2016postVFP, 2017, 2018). Covers no partially merged jets, no other targets, and nothing outside these ranges.

| Discriminant | WPs (target QCD mistag) | pT range [GeV] |
| --- | --- | --- |
| Top nominal | 0.1%, 0.5%, 1.0% | 300 < pT <= 1200 |
| W nominal | 0.5%, 1.0%, 5.0% | 200 < pT <= 800 |
| W MD | 0.5%, 1.0%, 2.5% | 200 < pT <= 800 |

### Run2 UL tau32 top tagging (AK8)
SFs derived with RunIISummer20UL16APV/UL16/UL17/UL18 MC, PUPPI v15 tune (the PUPPI tune version, not NanoAOD v15). They apply only to those campaigns.
Require 105 < m_SD < 210 GeV, with m_SD built from the four-vector sum of soft-drop subjets corrected with **AK4 PUPPI** JECs. SF coverage: pT > 300 GeV (prefer pT > 400), |eta| < 2.5.

| WP | tau32 = tau3/tau2 | Target mistag (no subjet b-tag) |
| --- | --- | --- |
| Very tight | < 0.38 | 0.1% |
| Tight | < 0.47 | 0.5% |
| Medium | < 0.52 | 1.0% |
| Loose | < 0.61 | 2.5% |
| Very loose | < 0.69 | 5.0% |

Optionally also require >= 1 subjet passing loose DeepJet, `btagDeepFlavB` > 0.0508 (UL16preVFP), 0.0480 (UL16postVFP), 0.0532 (UL17), 0.0490 (UL18). In MiniAOD, use probb + probbb + problepb. Don't also apply a BTV subjet SF, because the JMAR SF already covers it.

### Run2 UL HOTVR top tagging
Cluster PUPPI candidates with Rmin = 0.1, Rmax = 1.5, rho = 600 GeV, mu = 30 GeV, theta = 0.7, subjet pT > 30 GeV. Correct the subjets with AK4 PUPPI JECs, and define the jet four-vector as the sum of the subjets (no HOTVR JEC). The single WP requires all of:
- 140 < m_jet < 220 GeV
- >= 3 subjets
- min pairwise mass of the 3 leading subjets > 50 GeV
- pT(leading subjet)/pT(jet) < 0.8
- tau32 < 0.56

SF coverage: pT > 200 GeV, |eta| < 2.5. Efficiency is stable above about 500 GeV.

### Applying top-tagging SFs (tau32, HOTVR)
- Apply one SF per tagged jet, only in MC with generated top quarks (ttbar, single top, signal with tops). They don't correct mistags in top-less samples.
- Merge category per jet: **fully merged** = all 3 top-decay quarks within deltaR < 0.8 (HOTVR: deltaR < R_eff = min[1.5, max(0.1, 600 GeV / uncorrected pT)]), **semi-merged** = any 2, else **not merged**.
- With N tagged jets, multiply the N SFs.
- Treat the 3 merge categories as uncorrelated.
- Single era: use the total uncertainty. Multi-era fit: per category, use 1 component correlated across eras plus 1 per era, i.e. (1 + 4) x 3 = 15 nuisances. Stat is already inside the era-uncorrelated part.
- Tools: TopTaggingScaleFactors repository (merge-category pseudocode, ROOT reader); central JSON under JME/JMAR.

## 6. Lund jet-plane reweighting (LPR)
Per-prong correction of simulated substructure for **AK8 PUPPI signal jets with quark-initiated prongs**, for multi-prong targets with no direct data calibration (e.g. H->WW->4q). Data/MC ratios are measured in 2-prong W jets and transferred prong by prong (CMS-JME-23-001). LPR does **not** correct background mistags, and it gives no universal WP or SF.

| Campaign | Ratio file |
| --- | --- |
| 2016 / 2017 / 2018 | `ratio_2016.root` / `ratio_2017.root` / `ratio_2018.root` |
| Run 3 | not available |

Inputs: the AK8 jet, its PF candidates and the generator-level quarks. In NanoAOD v15 these are `FatJet`, `PFCand`, `FatJetPFCand` and `GenPart`, so check that they exist in your production. Earlier campaigns need a constituent-level format such as PFNano.

Workflow (LundReweighting code; examples `example.py`, `example_NanoV15.py`):
1. N prongs = number of hard-process gen quarks within deltaR < 0.8 of the jet.
2. Recluster the constituents into exactly N exclusive-kT subjets, and match them to the quarks within deltaR < 0.2.
3. Apply the ratio to every primary splitting with kT > 0.02 GeV. The jet weight is the product of the splitting weights; for several corrected jets in an event, multiply the jet weights.
4. Run `get_all_weights` **once on the full signal sample**, not per event or per chunk.

Use: for efficiency, SF = epsilon_corrected / epsilon_uncorrected; for shape fits, propagate the nominal and varied weights through the fitted shape. Derive and validate separately for each signal sample.

| Variation | Covers |
| --- | --- |
| `stat_vars` | Lund-plane ratio stat (toys -> std dev) |
| `sys_up/down` | ratio extraction systematics |
| `pt_vars` | high-pT extrapolation (toys -> std dev) |
| `bquark_up/down` | b- vs light-quark subjets |
| `prongs_up/down`, `unclust_up/down` | prong assignment, unmatched quarks |
| `distortion_up/down` | W-jet -> target-process transfer |

Keep up and down separately, because they are asymmetric. No cross-year or cross-process correlation is prescribed: document your choice.
Matching QA: report the bad-match and still-unmatched fractions by prong multiplicity and kinematics. Treat f_bad > 0.10 x N_prongs as a warning to investigate. Above about 50% unmatched, the unclustered uncertainty is unreliable, and a fraction near 1 means the reclustering failed.
Limits:
- Doesn't fix displaced-vertex mismodeling.
- Leptons in jets need a topology-specific recipe (HIG-24-008 removed leptons and nearby photons first; get review before reusing that).
- Gluon prongs need a dedicated ratio.
- Published closure: 2-prong (W, data), 3-prong (W->top, data), 4/6-prong (Pythia vs Herwig only).

Record the code and payload versions, prong definition, matching configuration and normalization sample, and get JMAR review.

## 7. Pitfalls
- `FatJet_particleNet_*` in v9 != v12/v15 (mass-correlated legacy vs Run 3 MD). Check the NanoAOD version before picking branches and WPs.
- Using the stored `globalParT3_WvsQCD` for W tagging (missing the 1/3 Xqq weight).
- `withMass` WPs on MD discriminants, or SFs from one model generation applied to another.
- Applying signal SFs to background or mistagged jets. Mistag corrections come from your own control regions.
- Using top-tagging SFs outside their pT/eta range, on partially merged jets with ParticleNet SFs, or in samples without top quarks.
- Applying a BTV subjet b-tag SF on top of the JMAR tau32+subjet-b SF (double counting).
- Mixing raw and corrected mass in regressions: GloParT-3 `massCorr*` x raw mass, PNet `massCorr` x corrected mass.
- `FatJet_jetId` on v15 doesn't exist (see Section 1). `n2b1`/`n3b1` are only filled for raw pT > 250 GeV.
- LPR in Run 3 (no ratios), on background, or normalized per chunk.
