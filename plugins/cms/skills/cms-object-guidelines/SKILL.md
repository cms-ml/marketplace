---
name: cms-object-guidelines
description: Use when the user asks to select, define, or document CMS analysis objects (muons, electrons, photons, AK4/AK8 jets, b-tagging, MET) or apply CMS POG recommendations in NanoAOD or MiniAOD. Triggers on requests for object selection criteria, working points, scale factors (SFs), JEC/JER, jet veto maps, MET filters, pileup reweighting, golden JSON lumimask, or object systematic uncertainties (e.g., "select baseline muons", "apply JEC to AK4 jets", "how to reweight pileup in NanoAOD").
---

# Instructions

When asked to select, define, or document CMS analysis objects or event filters:

1. Provide standard CMS Physics Object Group (POG) recommendations for object selection criteria, IDs, and working points.
2. Guide the user in writing idiomatic selection code, cutflows, and object-level systematic uncertainties (e.g., JEC, JER, scale factors).
3. Ensure proper data quality and event-level filters are applied (e.g., golden JSON, MET noise filters, pileup reweighting).

## Reference Guides

Refer strictly to the relevant reference files based on the specific physics object or task:

- **Muons**: `references/muons.md`
- **Electrons**: `references/electrons.md`
- **AK4 Jets**: `references/jets.md` (NanoAOD branches, jet ID, PU jet ID, jet veto maps, pitfalls)
- **Jet energy corrections**: `references/jets-jerc.md` (JEC/JER tags and correctionlib keys per era, JER smearing, JES/JER systematics and correlations)
- **AK8 Fat Jets**: `references/fat-jets.md` (FatJet branches, AK8 jet ID, soft-drop/regressed mass, GloParT-3/ParticleNet discriminants per NanoAOD version, top/W tagging SFs, Lund jet-plane reweighting)
- **B-tagging**: `references/b-tagging.md`
- **MET**: `references/met.md` (Transverse momentum, MET noise/event filters)
- **Luminosity**: `references/lumi.md` (Integrated luminosity, golden JSON, lumi uncertainties)
- **Pileup**: `references/pileup.md` (Pileup reweighting and profile matching)
