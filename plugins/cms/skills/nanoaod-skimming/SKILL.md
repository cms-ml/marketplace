---
name: nanoaod-skimming
description: >-
  Use when reducing CMS NanoAOD before an analysis: skimming events with a
  preselection, slimming to a list of kept branches, applying the golden JSON
  (lumi mask) to data, keeping or rebuilding MC normalisation from the Runs
  tree (genEventSumw, genEventCount, LHEScaleSumw, LHEPdfSumw), computing the
  integrated luminosity of the processed data, merging skims with hadd,
  writing skims to EOS, or splitting a skim over many files with Condor or
  CRAB. Also when MC normalised from a skim looks wrong by a large factor, the
  luminosity of a skim disagrees with brilcalc, a skim lost the Runs or
  LuminosityBlocks tree, nMuon or other counters are missing after writing
  with uproot, or RDataFrame Snapshot only wrote the Events tree.
metadata:
  summary: Skim and slim NanoAOD (uproot or RDataFrame) with golden JSON, genEventSumw bookkeeping and luminosity accounting
---

# NanoAOD skimming

## Overview

A skim keeps the events that can pass the analysis (**skimming**) and the
branches the analysis reads (**slimming**). A NanoAOD file has about 1400
branches. An analysis typically needs 50 to 150 and a few percent to a few tens
of percent of events, so a skim is often 50 to 500 times smaller and every later
pass runs in minutes instead of hours.

What a skim must not lose is the **bookkeeping**:

- **Runs** tree: `genEventSumw` etc. for MC normalisation. It describes all
  events generated, not the ones that passed, and must be copied unchanged.
- **LuminosityBlocks** tree: which lumi sections were processed. This is
  what the data luminosity is computed from.
- `run`, `luminosityBlock`, `event` for every event, and `genWeight` for MC.

Three scripts do the work (tested with LCG_109, Python 3.13, uproot 5.6,
awkward 2.8, ROOT 6.38 on cmslpc, 2016 UL NanoAODv9 Open Data):

| Script                             | Does                                                                                        | Prints                                      |
| ---------------------------------- | ------------------------------------------------------------------------------------------- | ------------------------------------------- |
| [scripts/skim.py](scripts/skim.py) | keep/drop globs, `--cut` expression, golden JSON for data, copies Runs and LuminosityBlocks | `EVENTS_IN`, `EVENTS_OUT`, `SUMW_READ`, ... |
| [scripts/sumw.py](scripts/sumw.py) | sums Runs over files, combines LHE variation sums correctly, `--xsec --lumi` weight factor  | `SUMW`, `N_EFF`, `WEIGHT_FACTOR`, ...       |
| [scripts/lumi.py](scripts/lumi.py) | integrated luminosity of the skims' lumi sections, or of a whole golden JSON                | `LUMI_PB`, `LUMI_FB`, `N_LS_MISSING`        |

All take `--help`, write `KEY=VALUE` to stdout and progress to stderr, and
read local paths or `root://` URLs. Kinematics in NanoAOD are in **GeV**.

## When to Use

- Before any analysis that will read the same NanoAOD more than once.
- To make a small, shareable input for plotting, fits or ML training.
- When normalising MC or quoting the luminosity of data that went through a
  skim (use the bookkeeping steps below even if someone else made the skim).

Do not skim when a single pass over the full sample is all you need: the
skim costs one full read anyway.

## Key Concepts

**Preselection is looser than the analysis.** Cut only on quantities that
will never change: trigger bits, object multiplicities with thresholds below
the analysis ones, `MET_pt` loosely. Leave room for systematic variations:
a jet-pT cut at 30 GeV in the analysis wants a skim at 20 to 25 GeV, so that
JEC/JER-up jets migrating across the threshold are still in the skim.

**Normalisation.** For an MC sample with cross section σ (pb) and data
luminosity L (/pb), each event's weight is

```text
w = genWeight * σ * L / Σ genEventSumw     (Σ over the Runs trees of ALL files of the sample)
```

The denominator is the sum over every generated event, including those that
failed the skim and those in files whose jobs failed. Not Σ `genWeight` over
the skim, and not the number of events. With NLO samples (amcatnlo) a
fraction of `genWeight` values is negative, so the number of events is wrong
by a large factor.

**LHE variations.** The Runs `LHEScaleSumw[i]` and `LHEPdfSumw[i]` are stored
**divided by that file's `genEventSumw`**. To combine files, weight each by
its `genEventSumw` (`sumw.py` does this). For the usual 9 scale weights the
nominal (muR = muF = 1) is index 4 and the central PDF is index 0: both
equal `SUMW` after combining, which is a quick check.

**Luminosity.** The luminosity of a data skim is the sum, over the golden
lumi sections that were actually processed, of the recorded luminosity
from brilcalc `--byls`. If a job failed, its lumi sections are not in any
output LuminosityBlocks tree, so `lumi.py -i` on the skims gives the right
number automatically. It counts each (run, lumi section) once, so a lumi
section split across two input files is not double-counted. A skim's
LuminosityBlocks lists every processed lumi section, including those where
no event passed the cut, as it should. The year total (e.g. 36.31 /fb for
2016 UL) is only right when every file was processed.

## Canonical Patterns

### 1. Decide what to keep

```bash
# Which branches does the analysis code read? List them, then turn them into globs.
python3 scripts/skim.py -i $FILE -o x.root --keep-file keep.txt --dry-run   # prints KEEP=... lines
```

Starting keep lists for common analyses are in
[references/keep-lists-and-recipes.md](references/keep-lists-and-recipes.md).
`run`, `luminosityBlock`, `event` and (MC) `genWeight` are always kept.
Without `--keep` every branch is kept (a pure event skim).

### 2. Skim with uproot (no CMSSW needed)

```bash
source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh
python3 scripts/skim.py \
  -i root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/130000/0A4230E2-0C75-604D-890F-A4CE5E5C164E.root \
  -o skim_SingleMuon_2016G_0.root \
  --keep 'Muon_*' 'HLT_IsoMu24' 'HLT_IsoTkMu24' 'MET_pt' 'MET_phi' 'PV_npvs' --drop 'Muon_*Err' \
  --cut '(HLT_IsoMu24 | HLT_IsoTkMu24) & (ak.sum((Muon_pt > 26) & Muon_tightId, axis=1) >= 1)' \
  --lumi-json Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt
```

The `--cut` is a Python expression over branch names with `ak` and `np`.
Branches it needs are read even if not kept. Use `&`, `|`, `~` (not `and`,
`or`). Per-object cuts go through `ak.sum(..., axis=1)` or `ak.any`.
`--lumi-json` takes a local file (download the golden JSON first) and is
ignored for MC. The output is a valid NanoAOD-style
file: collections are written with `n<Coll>` counters, so ROOT, coffea's
NanoEvents and the other skills read it unchanged. The counters come back
as int32 where NanoAOD has uint32, with the same values. Naming a counter
in `--keep` (`nMuon` with `Muon_*`) is allowed and not needed.

Write the output locally (the job's working directory), then copy it:

```bash
xrdcp -f skim_SingleMuon_2016G_0.root root://cmseos.fnal.gov//store/user/$USER/skims/2016/SingleMuon/
```

### 3. Skim with RDataFrame (faster on big inputs, multithreaded)

Recipe with the Runs and LuminosityBlocks copy in
[references/keep-lists-and-recipes.md](references/keep-lists-and-recipes.md#rdataframe-snapshot).
`Snapshot` writes only the tree it was called on. Copy the other two with
`fMode = "UPDATE"` or the skim has no bookkeeping.

### 4. Run over a dataset

One job per input file (or a few small files) keeps failures cheap. List
files with `dasgoclient -query="file dataset=/SingleMuon/Run2016G-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD"`
(CMS) or the Open Data file index. Submit with the `lpc-condor` skill on
cmslpc, or the `crab` skill for large central samples. Each job runs `skim.py` on its
files and `xrdcp`s the result to EOS. Keep each job's stdout: its
`EVENTS_IN` total must equal the dataset's event count.

### 5. Merge

```bash
hadd -f -k skim_SingleMuon_2016G.root skim_SingleMuon_2016G_*.root   # target 1 to 4 GB per output
```

`hadd` concatenates Events, Runs and LuminosityBlocks. The merged Runs tree
has one entry per input, and `sumw.py` sums them, so normalisation survives.
`-k` skips corrupt inputs instead of failing, so recount the inputs afterwards.

### 6. Bookkeeping: normalisation and luminosity

```bash
python3 scripts/sumw.py -i @dy_files.txt --xsec 6077.22 --lumi 36313.8   # MC: SUMW and WEIGHT_FACTOR
python3 scripts/lumi.py -i @data_skims.txt \
  --byls root://eospublic.cern.ch//eos/opendata/cms/luminosity/2016/pp_2016lumibyls.csv
python3 scripts/lumi.py --golden Cert_...json --byls ...csv               # whole-year cross-check
```

Run `sumw.py` on the original NanoAOD file list when you can: then the
denominator includes files whose skim jobs failed. If you only have the
skims, every skim job must have succeeded, so check against the count of
input files.

`brilcalc` is not installed on cmslpc. Run it on lxplus with the
recommended normtag and keep the `--byls` CSV next to the skims. Open Data
publishes the CSV for each year.

## Gotchas

- **MC normalised by events instead of Σ genEventSumw** gives a wrong
  scale. In 2016 UL amcatnlo DY, 16% of `genWeight` values are negative
  and all have the same magnitude (about 1.7e4). Weighting each event by
  σL/N (ignoring `genWeight`) overestimates the yield by Σ|w|/Σw ≈ 1.46.
  Using `genWeight` × σL/N is off by the weight magnitude, about 1.7e4.
  Only `genWeight` × σL / Σ genEventSumw is right. `N_EFF` from `sumw.py` is
  Σw²-based and is the right number for statistical power, not for
  normalisation.
- **`--max-events` or a job that read part of a file**: Runs still holds the
  whole file's `genEventSumw`. `skim.py` prints `SUMW_READ` (Σ genWeight of
  what it read) and `PARTIAL_FILES=1`. Use `SUMW_READ` for tests and never
  ship a partial skim. On a 100k-event test of a 1.4M-event DY file,
  `SUMW_READ` was 1.71e9 against 2.42e10 in Runs.
- **Runs tree lost**: `RDataFrame.Snapshot` and many hand-written uproot
  skims write only `Events`. `sumw.py` then exits 2 with "no Runs tree".
  Re-skim with the Runs copy. On a data file it exits 2 with
  "Runs has no genEventSumw".
- **Lumi of a partial data read**: `skim.py` keeps only the lumi sections
  it saw when `--max-events` is set, but the last one may be incomplete.
  Quote luminosity only from complete files.
- **`N_LS_MISSING` > 0 in `lumi.py`** (exit 3): the processed lumi sections
  were not filtered by the same golden JSON as the CSV, or the CSV is for
  another year. Re-run the skim with `--lumi-json`.
- **Mixing NanoAOD versions**: v7 and older name the Runs branches
  `genEventSumw_` (trailing underscore). `sumw.py` reads both. Branch names
  also change between versions (e.g. `Jet_btagDeepFlavB` in v9 against
  `Jet_btagPNetB` in Run 3 v12), so a keep list is version-specific: run
  `--dry-run` on one file of each campaign.
- **Branch lists differ between files of one dataset**: in 2016G
  SingleMuon one file has 1370 Events branches and others 1380. `skim.py`
  takes the kept list from the first file and stops with "lacks branches"
  if a later file misses one. Run one job per file, or keep only branches
  present everywhere. `hadd` of skims with different branch lists fails.
- **Several skims in parallel on a login node**: each `skim.py` holds
  about 2 GB at `--step-size 100 MB`. Six at once on an 11 GB cmslpc node
  were killed by the kernel ("Out of memory: Killed process ... python3",
  the shell shows `Killed`). Use batch jobs, run two at a time, or lower
  `--step-size`.
- **`OSError: File did not vector_read properly: [ERROR] Operation expired`**:
  an XRootD read timed out (busy node or EOS). `skim.py` exits 1 and
  leaves only `<output>.part`, never `<output>`, so a merge cannot pick up
  a half-written skim. Rerun that file's job.
- **No event passes in one file**: the output has Runs and LuminosityBlocks
  but no Events tree. That is correct and `hadd` (ROOT 6.38) merges it with
  the others. Do not delete it: its Runs entry is part of the normalisation.
- **Overlapping primary datasets**: an event can be in both SingleMuon and
  SingleElectron (or DoubleMuon). Skimming them separately and adding
  double-counts. Apply the trigger-based veto in the analysis, not the skim.
- **Writing jagged branches with uproot by hand**: a dict of flat names
  (`{"Muon_pt": ..., "Muon_eta": ...}`) gets a counter per branch
  (`nMuon_pt`, `nMuon_eta`). Group by collection with `ak.zip` as `skim.py`
  does to get one `nMuon`.

## Reference Files

- [references/keep-lists-and-recipes.md](references/keep-lists-and-recipes.md):
  starting keep lists (dimuon, single lepton, dijet, boosted jets), the
  RDataFrame Snapshot recipe, the NanoAODTools post-processor, and a
  Condor worker wrapper sketch.

## Docs

- NanoAOD branch documentation: <https://cms-nanoaod-integration.web.cern.ch/autoDoc/>
- uproot writing: <https://uproot.readthedocs.io/en/latest/basic.html#writing-ttrees-to-a-file>
- RDataFrame Snapshot: <https://root.cern/doc/master/classROOT_1_1RDataFrame.html>
- NanoAODTools post-processor: <https://github.com/cms-sw/cmssw/tree/master/PhysicsTools/NanoAODTools>
- brilcalc: <https://cms-service-lumi.web.cern.ch/cms-service-lumi/brilwsdoc.html>
- CMS Open Data luminosity: <https://opendata.cern.ch/docs/cms-guide-luminosity-calculation>
- PocketCoffea skimming recipe: <https://pocketcoffea.readthedocs.io/en/stable/recipes.html>
