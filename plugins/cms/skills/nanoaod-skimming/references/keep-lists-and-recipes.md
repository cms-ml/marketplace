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
- Write the Cutflow tree too (next section), so the skim has the same
  bookkeeping as one from `skim.py`.
- ROOT 6.38 changed the Snapshot default compression to ZSTD level 5 and
  prints an info message about it. Set `ROOT_RDF_SNAPSHOT_INFO=0` to
  silence it.

### Cutflow tree with RDataFrame

Same branch names as `skim.py`'s Cutflow, so `scripts/cutflow.py` reads it.
Tested with ROOT 6.38 on the full DY file above: one event loop, about 30 s with 4
threads, `w_all` equal to the Runs `genEventSumw` (2.42e10).

```python
import ROOT, numpy as np
ROOT.EnableImplicitMT(4)
steps = [("trigger", "HLT_IsoMu24 || HLT_IsoTkMu24"), ("two_muons", "Sum(Muon_pt > 20) >= 2")]
is_mc = True                       # data: genWeight does not exist, use 1.0

df = ROOT.RDataFrame("Events", src).Define("w_", "(double)genWeight" if is_mc else "1.0").Define("w2_", "w_ * w_")
for name, expr in steps:
    df = df.Define(f"p_{name}", f"(bool)({expr})")
df = df.Define("nfail_", " + ".join(f"!p_{n}" for n, _ in steps))
cuts = {"all": "true", "lumimask": "true"}  # data: "lumimask" is the golden-JSON column
cuts.update({n: " && ".join(f"p_{m}" for m, _ in steps[: i + 1]) for i, (n, _) in enumerate(steps)})
cuts.update({f"m1_{n}": f"nfail_ == 0 || (nfail_ == 1 && !p_{n})" for n, _ in steps})
res = {}
for k, c in cuts.items():   # booked lazily, filled in one event loop
    f = df.Filter(c)
    res[k] = (f.Count(), f.Sum("w_"), f.Sum("w2_"))

lazy = ROOT.RDF.RSnapshotOptions()
lazy.fLazy = True                  # so the Snapshot and the counts share one event loop
snap = df.Filter(cuts[steps[-1][0]]).Snapshot("Events", out, keep, lazy)
ROOT.RDF.RunGraphs([snap] + [r for res_k in res.values() for r in res_k])

def branch(k, p):                  # prefix n, w or w2: "m1_x" -> nm1_x / wm1_x / w2m1_x, else n_x / w_x / w2_x
    return f"{p}m1_{k[3:]}" if k.startswith("m1_") else f"{p}_{k}"
cf = {}
for k, (c, w, w2) in res.items():
    cf[branch(k, "n")] = np.array([c.GetValue()], np.int64)
    if is_mc:
        cf[branch(k, "w")] = np.array([w.GetValue()], np.float64)
        cf[branch(k, "w2")] = np.array([w2.GetValue()], np.float64)
order = ["all", "lumimask"] + [n for n, _ in steps] + [f"m1_{n}" for n, _ in steps]
names = [branch(k, p) for p in (("n", "w", "w2") if is_mc else ("n",)) for k in order]
opts = ROOT.RDF.RSnapshotOptions()
opts.fMode = "UPDATE"
ROOT.RDF.FromNumpy({b: cf[b] for b in names}).Snapshot("Cutflow", out, "", opts)
# then the Runs and LuminosityBlocks Snapshots above
```

One Cutflow entry per output file. Run one input file per job (as for the
uproot skim) so `hadd` and `cutflow.py` sum entries the same way.

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
