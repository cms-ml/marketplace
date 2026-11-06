# Muon tight-ID, isolation and IsoMu24 scale factors from Z to mumu tag and probe, 2016G+H Open Data

Measure the muon tight-ID, tight-isolation and IsoMu24-or-IsoTkMu24 efficiencies in Run2016G+H SingleMuon data and
POWHEG Z to mumu MC with tag and probe, form data/MC scale factors, and compare them bin by bin with the Muon POG
`muon_Z.json.gz` (2016postVFP_UL).

## Data Samples

| Dataset (DAS name or Open Data path)                                                                                                                      | Tier       | Era / campaign             | Role(s) in analysis                     |
| --------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | -------------------------- | --------------------------------------- |
| `/eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/` (70 files in the listing; every 5th file used: 14)                         | NANOAOD    | Run2016G                   | Data                                    |
| `/eos/opendata/cms/Run2016H/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/` (82 files in the listing; every 5th file used: 17)                         | NANOAOD    | Run2016H                   | Data                                    |
| `/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/ZToMuMu_M-50To120_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/` (all 28 files) | NANOAODSIM | RunIISummer20UL16NanoAODv9 | Signal MC (efficiency, signal template) |

- Speed subset (decision of the user, to make the validation fast): every 5th file (sorted path order, files 0, 5, 10, ...)
  of each data listing. Both eras are covered roughly in proportion (14 of 70 G files, 17 of 82 H files). The fraction of
  the full G+H certified luminosity this represents is computed in the analysis and stored in `summary.json`
  (`inputs.lumi_fraction_of_full_GH`). The Open Data record lists the complete files, so the subset is not a run-range cut.
- Luminosity / certification: Golden JSON `Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt` (Open Data record
  14220). Integrated luminosity: `recorded` column of `pp_2016lumibyls.csv` (record 1059), summed over exactly the
  lumi sections that are present in the processed files and in the golden JSON. Uncertainty 1.2% (2016 value, not used in the ratios).
- Triggers: `HLT_IsoMu24 || HLT_IsoTkMu24` (events; the tag is matched to its trigger object). Denominator of the trigger step: tight ID + tight iso.
- MC normalisation: none needed (efficiencies, shapes). MC weights: sign(genWeight) x pileup weight from
  `POG/LUM/2016postVFP_UL/puWeights.json.gz` (`Pileup_nTrueInt`).
- MC statistics: the dataset has only 28 files (2.96 M events) and all are used. The skill asks for at least as many MC tag-probe pairs
  as data pairs; this cannot be met (MC/data = 0.44 even for the 22% data subset, see `summary.json` `pairs`), so it is reported as a
  limitation and tested with MC subsamples (`mc_statistics_test`). Closest alternative not used: DYJetsToLL_M-50 (more files, different generator).
- Counterpart: `/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/MUO/2016postVFP_UL/muon_Z.json.gz`. It is
  derived on 2016F (late) + G + H, i.e. a superset of the G+H data used here (the full G+H certified luminosity is computed in the analysis,
  16.39 fb^-1 recorded; the subset is 3.55 fb^-1, 21.7%). Differences from the run mix are checked with the G vs H comparison.

## Histograms

1. Pass and fail m(mumu) spectra per working point (WP) and bin (inputs of the fits)
   - x: m(tag, probe), `$m_{\mu\mu}$ [GeV]`, 70-115 GeV, 45 bins of 1 GeV
   - one entry per tag-probe pair (each muon is tag once)
   - Weights: data unweighted; MC sign(genWeight) x pileup, probe generator-matched (`Muon_genPartFlav == 1`) for the efficiency and templates
2. Efficiency vs probe pT per |eta| bin: data, MC, ratio (SF) with the POG SF
   - x: probe `$p_{T}$ [GeV]` in the POG bins; one panel per |eta| bin (0-0.9, 0.9-1.2, 1.2-2.1, 2.1-2.4)
3. Maps of SF_ours / SF_POG in |eta| x pT, per WP; pull distributions per WP

## Analysis Steps

1. Pair selection (Condor, `condor/skim.py`)
   - Muons: |eta| < 2.4, pT > 15 GeV, `isTracker`
   - Tag: tight ID, `pfRelIso04_all < 0.15`, pT > 29 GeV, matched (dR < 0.1) to a muon TrigObj with filter bit 2 (Iso) or 8 (IsoTkMu), pT >= 24 GeV
   - Probe: the other muon of an opposite-charge pair, 70 < m < 115 GeV; every ordered pair is used (each muon is tag once)
   - Stored per pair: m, tag pT/iso, tag match to bit 2 and to bit 8, probe pT/eta/iso, tight ID, IP cut, probe matched-object pT for bit 2 and bit 8, HLT flags, run, lumi section, MC gen-match and weight
2. Working points (POG chain, all in `muon_Z.json.gz`)
   - `NUM_TightID_DEN_TrackerMuons`: probe isTracker; pass = tightId
   - `NUM_TightRelIso_DEN_TightIDandIPCut`: probe tight ID, |dxy| < 0.2, |dz| < 0.5 cm; pass = `pfRelIso04_all < 0.15`
   - `NUM_IsoMu24_or_IsoTkMu24_DEN_CutBasedIdTight_and_PFIsoTight`: probe tight ID and iso < 0.15; pass = matched to an Iso/IsoTkMu object with pT >= 24 GeV
   - Bins: POG |eta| x pT edges read from the JSON (pT in GeV)
3. Data efficiency: simultaneous pass/fail binned fit (signal MC template per category + exponential background, common N and eps), iminuit
4. MC efficiency: counting, generator-matched probes, weighted
5. SF = eps_data / eps_MC. POG: nominal and `systup` (uncertainty = systup - nominal), evaluated at the pT bin centre as in `tnp.py`
   (question: the POG value in a wide bin depends on where it is evaluated; the bin-centre choice is the skill's)
6. Pull = (SF - SF_POG) / sqrt(sigma_SF^2 + sigma_POG^2); mean and RMS per WP

## Corrections and Systematics

- Pileup reweighting of MC (LUM POG). No lepton SFs are applied (they are what is measured)
- Systematics on the SF, per bin, each quoted separately and added in quadrature with the statistical uncertainty:
  - background shape: exponential vs. a second-order polynomial (1 + a u + b u^2 in the scaled mass u, clipped at zero)
  - mass window 70-115 vs. 75-110 GeV
  - tag selection: tag pT > 33 GeV vs. 29 GeV; tag isolation < 0.05 vs. < 0.15 (the larger deviation is taken)
  - signal template (the POG `AltSig`) and MC-template statistics are not varied (not part of the minimum set); listed as a limitation
- Trigger matching study (IsoMu24), all offline from the stored columns (the skim stores the tag and probe matches to bit 2 and bit 8 separately, object pT >= 24 GeV, dR < 0.1, and the HLT_IsoMu22 / IsoTkMu22 / IsoMu24 / IsoTkMu24 flags):
  (a) skill: tag and probe bit 2|8 (nominal); (b) tag bit 2, probe bit 2; (c) tag bit 2|8, probe bit 2; (d) tag bit 8, probe bit 8;
  (e) path-aware: bit 2 if IsoMu24 fired, bit 8 if IsoTkMu24 fired (tag and probe); plus no-HLT and HLT-path-specific variants. Each is compared with the POG per bin, per |eta| at 40-50 GeV and weighted over 30-60 GeV.
  A scan of the probe object pT threshold (24, 26, 27, 30 GeV) in the 26-30, 30-40 and 40-50 GeV probe bins for (a) and (b).
- Input subset unchanged in this second round (same files as above, skim redone); the full G+H dataset and additional DY MC are out of scope by decision of the user.

## Workflow

1. Data Extraction and Skimming (Condor, `lpc-condor` templates)
   - Filtering: events with at least two tracker muons, at least one tag; see Analysis Steps 1
   - Branches: `run`, `luminosityBlock`, `Muon_{pt,eta,phi,charge,isTracker,tightId,pfRelIso04_all,dxy,dz}`, `TrigObj_{id,filterBits,pt,eta,phi}`,
     `HLT_IsoMu24`, `HLT_IsoTkMu24` and related paths; MC only: `genWeight`, `Pileup_nTrueInt`, `Muon_genPartFlav`
   - Outputs to EOS (`root://cmseos.fnal.gov//store/user/$USER/tnp/skim`), copied to a scratch area for the analysis
2. Analysis and Histogramming (local, `run_all.sh`)
   - golden JSON + luminosity, WP fits (nominal and variations), POG comparison, run dependence, filter-bit study, plots, `summary.json`
   - Run dependence: repeat the trigger and isolation measurements with Run2016G pairs and Run2016H pairs separately (same MC)

## Statistical Analysis

Binned Poisson likelihood fit per bin and WP (iminuit; HESSE errors). Pass/fail simultaneous with common signal yield and efficiency.
A second start is tried when the first fit is not valid. Bins whose fit is invalid are flagged `fit_ok = false`. Bins with an SF statistical
error above 0.05 (essentially empty fail category, e.g. tight iso, |eta| 2.1-2.4, pT > 120 GeV) are kept, flagged `low_stat` in `summary.json` and
exempt from the SF-range check. A Clopper-Pearson counting replacement is not implemented (open limitation).

## Tools

- uproot + awkward: read NanoAOD in chunks; `ak.argcartesian` for pairs; vector for the pair mass (`awkward-array`, `vector-awkward`)
- correctionlib: POG SFs and pileup weights
- iminuit 2.x (LCG_109 view): fits
- hist/mplhep (CMS style, "CMS Open Data", 13 TeV, luminosity): plots; numpy histograms for the fit inputs
- HTCondor on the LPC (`lpc-condor`): pair selection

## Open questions

- Is the MC (28 files) sufficient? No: all files are used and MC/data pairs = 0.44 (see Data Samples).
- Which pT point of the wide bins to use for the POG value (bin centre, as the skill; the POG itself averages over the bin).
- Is the trigger comparison meaningful for G+H only, given the POG covers F(late)+G+H?
