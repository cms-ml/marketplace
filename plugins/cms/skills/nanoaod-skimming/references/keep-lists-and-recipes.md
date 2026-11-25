# Keep lists and skimming recipes

Read this reference when choosing which NanoAOD branches to keep for a
common analysis type, when skimming with RDataFrame instead of
`scripts/skim.py`, or when wiring the skim into batch jobs.

Contents:

- Keep lists
- RDataFrame Snapshot
- NanoAODTools post-processor
- Batch jobs

## Keep lists

Glob patterns, one per line, for `skim.py --keep-file`. Checked with
`--dry-run` against 2016 UL NanoAODv9 data (SingleMuon) and MC (DY
amcatnlo), 2026-11. Branch names differ in Run 3 NanoAOD v12+: check each
campaign with `--dry-run`. `run`, `luminosityBlock`, `event`, `genWeight`
are always added. A pattern that matches nothing (MC-only branches on data)
is reported as `MISSING_PATTERNS=` and skipped, so one list can serve data
and MC. Check that line for typos.

Common to most analyses (`common.txt`):

```text
PV_npvs
PV_npvsGood
Flag_*
MET_pt
MET_phi
PuppiMET_pt
PuppiMET_phi
```

MC additions (`mc.txt`):

```text
Pileup_nTrueInt
Pileup_nPU
LHEScaleWeight
LHEPdfWeight
PSWeight
LHEWeight_originalXWGTUP
GenPart_*
GenJet_*
```

Dimuon or single-muon (`muon.txt`), with the trigger paths for the year:

```text
Muon_*
HLT_IsoMu24
HLT_IsoTkMu24
HLT_Mu50
TrigObj_*
```

Electrons and photons (`egamma.txt`):

```text
Electron_*
Photon_*
HLT_Ele27_WPTight_Gsf
```

Jets and b tagging, AK4 (`jets.txt`):

```text
Jet_pt
Jet_eta
Jet_phi
Jet_mass
Jet_jetId
Jet_puId
Jet_btagDeepFlavB
Jet_rawFactor
Jet_area
# MC only
Jet_hadronFlavour
Jet_partonFlavour
Jet_genJetIdx
fixedGridRhoFastjetAll
RawMET_*
HLT_PFHT*
```

`Jet_rawFactor`, `Jet_area` and `fixedGridRhoFastjetAll` are needed to
re-apply JEC. `Jet_genJetIdx` and `GenJet_*` are needed for JER smearing.
Drop them and the corrections cannot be redone from the skim.

Boosted jets, AK8 (`fatjets.txt`):

```text
FatJet_*
SubJet_*
HLT_AK8PFJet*
HLT_PFHT*
```

Pass several files: `--keep-file common.txt mc.txt muon.txt`.

## RDataFrame Snapshot

Tested with ROOT 6.38 (LCG_109): the full 1.43M-event DY file in 33 s with
4 threads, 28 MB output for 63 branches.

```python
import ROOT
ROOT.EnableImplicitMT(4)          # event order in the output is then not the input order
src = "root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/30000/0A995C8D-0ACC-7E45-8C7A-16AC51398938.root"
out = "skim.root"
keep = "^(run|luminosityBlock|event|genWeight|nMuon|Muon_.*|HLT_IsoMu24)$"   # regex, not globs

df = ROOT.RDataFrame("Events", src).Filter("Sum(Muon_pt > 20) >= 2", "two muons pT>20")
df.Snapshot("Events", out, keep)

opts = ROOT.RDF.RSnapshotOptions()
opts.fMode = "UPDATE"              # add to the same file instead of overwriting it
ROOT.RDataFrame("Runs", src).Snapshot("Runs", out, "", opts)
ROOT.RDataFrame("LuminosityBlocks", src).Snapshot("LuminosityBlocks", out, "", opts)
```

- Keep the counter `nMuon` in the regex together with `Muon_.*`.
- For data, apply the golden JSON before the Filter. The simplest way is
  a C++ helper or, on several files, `skim.py`. Then also filter the
  LuminosityBlocks Snapshot by the same JSON.
- ROOT 6.38 changed the Snapshot default compression to ZSTD level 5 and
  prints an info message about it. Set `ROOT_RDF_SNAPSHOT_INFO=0` to
  silence it.

## NanoAODTools post-processor

Inside CMSSW, `PhysicsTools/NanoAODTools` provides `nano_postproc.py` with a
cut string, `--bi`/`--bo` keep-and-drop files and a golden JSON option, and
`haddnano.py`, which merges the Runs tree into one entry. It is useful when
the skim must also run NanoAODTools modules (e.g. JME corrections).
Not tested for this skill: follow the package README for the release you use.

## Batch jobs

- cmslpc: use the `lpc-condor` skill. The worker sets up the LCG view,
  runs `skim.py -i <its files> -o skim_<job>.root ...`, then
  `xrdcp -f skim_<job>.root root://cmseos.fnal.gov//store/user/$USER/skims/...`.
  Ship `skim.py` and the keep and golden JSON files with
  `transfer_input_files`.
- Keep each job's stdout. Summing `EVENTS_IN` over jobs and comparing with
  the dataset's event count (`dasgoclient -query="summary dataset=..."`)
  finds jobs that read only part of their input.
- Large central samples on the grid: CRAB with a NanoAOD input and a
  script executable: see the `crab` skill (plugin `af-cern-lxplus`). On
  lxplus use `lxplus-htcondor` in place of `lpc-condor`.
