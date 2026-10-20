# Example specifications (CMS)

Read this reference to see what a finished specification looks like: the
level of detail, how unknowns are handled, and how tools are assigned. All
dataset names were checked with `dasgoclient` on 2026-10-09. The 2016 ones
are also in CMS Open Data.

## Contents

1. [MET distribution in a single dataset](#1-met-distribution-in-a-single-dataset)
2. [Z to mumu mass with data and MC](#2-z-to-mumu-mass-with-data-and-mc)
3. [Hadronic top candidate (closest-mass trijet)](#3-hadronic-top-candidate-closest-mass-trijet)

---

## 1. MET distribution in a single dataset

# Plot MET for SingleMuon 2016H

Plot the missing transverse momentum for all events in the 2016H SingleMuon NanoAOD dataset.

## Data Samples

| Dataset (DAS name or Open Data path) | Tier | Era / campaign | Role(s) in analysis |
| --- | --- | --- | --- |
| /SingleMuon/Run2016H-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD | NANOAOD | Run2016H (UL) | Data |

* Luminosity / certification: Apply the UL2016 Golden JSON (question: confirm, or plot all events?).
* Triggers: none specified.
* MC normalisation: not applicable (data only).

## Histograms

1. MET
    * x Axis
        * Magnitude of the missing transverse momentum per event (`MET_pt`).
        * `$p_{T}^{miss}$ [GeV]`
        * Binning: implementation default.
        * One entry per event.
    * Weights: unweighted (data).

## Analysis Steps

1. Event selection
    * Certified lumisections only (if the Golden JSON is confirmed).
1. MET
    * Read `MET_pt` directly.

## Corrections and Systematics

None.

## Workflow

1. Data Extraction and Skimming
    * No Filtering (beyond the lumi mask).
    * Branches: `MET_pt`, `run`, `luminosityBlock`.
2. Analysis and Histogramming
    * Fill the MET histogram, one entry per event.

## Statistical Analysis

None.

## Tools

* uproot + awkward
  * Read the branches from the NanoAOD files (XRootD).
* hist + mplhep
  * Fill the histogram and save a CMS-style PNG.

---

## 2. Z to mumu mass with data and MC

# Z to mumu invariant mass, 2016H data vs DY MC

Compare the opposite-sign dimuon mass in 2016H SingleMuon data with the DY aMC@NLO prediction normalised to the data luminosity.

## Data Samples

| Dataset (DAS name or Open Data path) | Tier | Era / campaign | Role(s) in analysis |
| --- | --- | --- | --- |
| /SingleMuon/Run2016H-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD | NANOAOD | Run2016H (UL) | Data |
| /DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM | NANOAODSIM | RunIISummer20UL16NanoAODv9 | Background (signal-like Z peak) |

* Luminosity / certification: UL2016 Golden JSON; integrated luminosity of the 2016H certified runs (question: value to use?).
* Triggers: `HLT_IsoMu24` (question: also OR with `HLT_IsoTkMu24`?).
* MC normalisation: DY cross section (question: which value and reference?) x lumi / sum of `Runs/genEventSumw` over all files; aMC@NLO has negative weights.

## Histograms

1. Dimuon invariant mass
    * x Axis
        * Invariant mass of the two leading opposite-sign tight, isolated muons.
        * `$m_{\mu\mu}$ [GeV]`
        * 60 to 120 GeV, 60 bins (user-specified).
        * One entry per selected event.
    * Axis: process (Data, DY).
    * Weights: data unweighted; MC `genWeight x xsec x lumi / sumw x muon SFs`.

## Analysis Steps

1. Muon selection
    * pT > 26 GeV leading, > 15 GeV subleading, |eta| < 2.4, tight ID, PF relative isolation (dR 0.4) < 0.15.
1. Event selection
    * Trigger fired; exactly two selected muons of opposite charge.
1. Dimuon mass
    * Four-vector sum of the two muons (with `Muon_mass`).

## Corrections and Systematics

* Muon ID, isolation and trigger scale factors (MUO POG, via correctionlib), with up/down variations.
* Pileup reweighting (LUM POG) with up/down variations.

## Workflow

1. Data Extraction and Skimming
    * Filtering: events with >= 2 muons with pT > 15 GeV.
    * Branches (data and MC): `Muon_pt, Muon_eta, Muon_phi, Muon_mass, Muon_charge, Muon_tightId, Muon_pfRelIso04_all, HLT_IsoMu24, run, luminosityBlock`.
    * Branches (MC only): `genWeight, Pileup_nTrueInt`.
2. Analysis and Histogramming
    * Apply selections, build the pair, fill per process and per systematic variation.

The histogramming is repeated for each scale-factor and pileup variation.

## Statistical Analysis

None (data/MC comparison only).

## Tools

* uproot + awkward + vector
  * Read NanoAOD, select muons, build the dimuon four-vector.
* correctionlib
  * Muon scale factors and pileup weights from the POG JSON files.
* hist + mplhep
  * Process/systematic axes; stacked CMS-style plot with a data/MC ratio panel.

---

## 3. Hadronic top candidate (closest-mass trijet)

# Trijet pT and max b-tag in the closest-mass trijet

In all-hadronic ttbar events, build all trijets per event, take the one with mass closest to 172.5 GeV, and plot its pT and the highest DeepJet b-tag score among its jets.

## Data Samples

| Dataset (DAS name or Open Data path) | Tier | Era / campaign | Role(s) in analysis |
| --- | --- | --- | --- |
| /TTToHadronic_TuneCP5_13TeV-powheg-pythia8/RunIISummer20UL16NanoAODv9-106X_mcRun2_asymptotic_v17-v1/NANOAODSIM | NANOAODSIM | RunIISummer20UL16NanoAODv9 | Signal (ttbar all-hadronic) |

* Luminosity / certification: MC only.
* Triggers: none specified.
* MC normalisation: shape only (unit-normalised histograms) unless the user asks otherwise.

## Histograms

1. Trijet pT (closest-mass trijet)
    * x Axis
        * pT of the four-vector sum of the three jets whose invariant mass is closest to 172.5 GeV.
        * `$p_{T}^{3j}$ [GeV]`
        * Binning: implementation default.
        * One entry per event with >= 3 selected jets.
2. Max b-tag score in the closest-mass trijet
    * x Axis
        * Maximum `Jet_btagDeepFlavB` among the three jets of that trijet.
        * `max DeepJet b-tag score`
        * 0 to 1.
        * One entry per event with >= 3 selected jets.
    * Weights: `genWeight` (shape only).

## Analysis Steps

1. Jet selection
    * pT > 30 GeV, |eta| < 2.4, tight jet ID (`Jet_jetId`; question: confirm working point).
1. Event selection
    * At least three selected jets.
1. Trijet candidates
    * All 3-jet combinations per event; mass and four-momentum of each.
    * Choose the combination with |m(3j) - 172.5 GeV| minimal.
1. Derived quantities
    * Trijet pT; maximum b-tag score of its three jets.

## Corrections and Systematics

None.

## Workflow

1. Data Extraction and Skimming
    * Filtering: events with >= 3 jets with pT > 30 GeV.
    * Branches: `Jet_pt, Jet_eta, Jet_phi, Jet_mass, Jet_jetId, Jet_btagDeepFlavB, genWeight`.
2. Analysis and Histogramming
    * Build combinations, select the closest-mass trijet, fill both histograms.

## Statistical Analysis

None.

## Tools

* uproot + awkward
  * Read jets; `ak.combinations(jets, 3)` and `ak.argmin(..., keepdims=True)` for the best trijet.
* vector
  * Trijet four-vector sum, mass and pT.
* hist + mplhep
  * Histograms and CMS-style PNGs.
