---
name: cms-object-guidelines
description: Use when the user asks to select, define, or document CMS analysis objects (muons, electrons, photons, AK4/AK8 jets, b-tagging, MET) or apply CMS POG recommendations in NanoAOD or MiniAOD. Triggers on requests for object selection criteria, working points, scale factors (SFs), JEC/JER, jet veto maps, MET filters, pileup reweighting, golden JSON lumimask, or object systematic uncertainties (e.g., "select baseline muons", "apply JEC to AK4 jets", "how to reweight pileup in NanoAOD").
---

# CMS object guidelines

## Overview

When asked to select, define, or document CMS analysis objects or event filters:

1. Provide standard CMS Physics Object Group (POG) recommendations for object selection criteria, IDs, and working points.
2. Guide the user in writing idiomatic selection code, cutflows, and object-level systematic uncertainties (e.g., JEC, JER, scale factors).
3. Ensure proper data quality and event-level filters are applied (e.g., golden JSON, MET noise filters, pileup reweighting).

Kinematics are in **GeV**. For exact NanoAOD branch names and v12/v15 differences, use the `nanoaod-branches` skill.

## Reference Files

Refer strictly to the relevant reference file for the object or task:

- **Muons**: [references/muons.md](references/muons.md) (IDs, isolation, momentum corrections, SFs per pT regime)
- **Electrons**: [references/electrons.md](references/electrons.md) (cut-based/MVA IDs, scale and smearing, SFs)
- **AK4 jets**: [references/jets.md](references/jets.md) (NanoAOD branches, jet ID, PU jet ID, jet veto maps, pitfalls)
- **Jet energy corrections**: [references/jets-jerc.md](references/jets-jerc.md) (JEC/JER tags and correctionlib keys per era, JER smearing, JES/JER systematics and correlations)
- **AK8 fat jets**: [references/fat-jets.md](references/fat-jets.md) (FatJet branches, AK8 jet ID, soft-drop/regressed mass, GloParT-3/ParticleNet discriminants per NanoAOD version, top/W tagging SFs, Lund jet-plane reweighting)
- **MET**: [references/met.md](references/met.md) (Run2 PF / Run3 PUPPI Type-1 MET, noise-filter flags per era, Type-1/XY/recoil corrections, MET uncertainties, DeepMET, MET significance)
- **Luminosity**: [references/lumi.md](references/lumi.md) (integrated luminosity, golden JSON, lumi uncertainties)
- **Pileup**: [references/pileup.md](references/pileup.md) (placeholder: the file is empty. Say that pileup-reweighting guidance isn't available yet; don't invent it)
- **B-tagging**: [references/b-tagging.md](references/b-tagging.md) (AK4 b/c/q-g taggers and branches, WP cuts per era, fixedWP and shape SF application, MC efficiencies, uncertainties and correlations, Run2 subjet and AK8 X->bb/cc WPs)
- **Photons, taus**: no reference yet. Say so instead of guessing WPs or SFs, and point to the EGM and TAU POG pages.

## Gotchas

- **NanoAODv15 drops branches older code relies on**: `Jet_jetId`, `FatJet_jetId`, `Flag_METFilters` (and the `Jet_puId` WP bitmap exists only in Run2 NanoAODv9). PF MET is `PFMET_*` (not `MET_*`). Compute Jet ID yourself ([jets.md](references/jets.md) Section 2) and AND the individual `Flag_*` ([met.md](references/met.md) Section 3).
- **Noise filters apply to every analysis**, including ones that don't use MET.
- **Bitmap branches**: test bits, never compare the full value. The UL2016 PU jet ID Loose/Tight bits are swapped.
- **Correction keys must match the jet collection**: `*_AK4PFchs` for Run2 NanoAODv9, `*_AK4PFPuppi` for Run2 v15 and Run3.
- **Stored Type-1 MET uses the production-time JEC**: recompute it if you re-correct the jets.
- **Jet veto maps**: in Run3 they veto the **event**; in Run2 they veto the **jet**.
- **Era splits have separate files and constants**: 2016preVFP/postVFP, 2022/2022EE, 2023/2023BPix.
- **High-pT muons**: with the HighPt ID use `Muon_pt * Muon_tunepRelPt`. `Muon_mvaTTH`/`Electron_mvaTTH` are `promptMVA` from NanoAOD v14 on.
- **Electron veto**: `cutBased >= 1` is Veto-or-better. To veto electrons, require none with `cutBased >= 1`.
- **Lumi nuisances**: in Run 2, include every nuisance whose name contains the year. In Run 3, the brilcalc normtag differs by year.
- **b-tagging SFs need your own MC tagging efficiencies** (per flavour, pT, eta, derived before any b-tag cut), and apply to every jet whose tag status you use, including 0-tag regions.
- **Before evaluating a correctionlib payload**, list `cset.keys()` and each correction's `inputs`: names differ between eras.

## Docs

- Muon POG guidelines: https://muon-wiki.docs.cern.ch/guidelines/
- EGamma POG Run 3 ID: https://egammapog.docs.cern.ch/Run3/Run3_ID/
- JME/JMAR recommendations (jets, boosted objects, MET): https://cms-jme-jmar.docs.cern.ch/ (MET: https://cms-jme-jmar.docs.cern.ch/recommendations/met/)
- Run 2 UL Jet ID: https://twiki.cern.ch/twiki/bin/view/CMS/JetID13TeVUL
- BTV POG wiki (b/c/q-g tagging): https://btv-wiki.docs.cern.ch/
- Central correctionlib payloads: https://cms-analysis-corrections.docs.cern.ch/
- Luminosity: https://twiki.cern.ch/twiki/bin/view/CMS/LumiRecommendationsRun2, https://twiki.cern.ch/twiki/bin/view/CMS/LumiRecommendationsRun3, https://twiki.cern.ch/twiki/bin/view/CMS/PdmVRun3Analysis
- NanoAOD content (autoDoc): https://cms-xpog.docs.cern.ch/autoDoc/
