---
name: cmssw
description: >-
  Use when setting up or working inside a CMSSW release area (cmsrel, cmsenv,
  scram), choosing a CMSSW release or SCRAM_ARCH for a dataset, running an old
  release inside a cmssw-el7/el8 container, checking out or patching CMSSW
  packages with git cms-addpkg or git cms-merge-topic, writing or building an
  EDAnalyzer, EDProducer or EDFilter, writing or debugging a cmsRun Python
  configuration (_cfg.py, _cfi.py, _cff.py), inspecting EDM ROOT files
  (MiniAOD, AOD, RECO) with edm* tools, or installing extra Python packages on
  top of a CMSSW release.
metadata:
  summary: Release areas, architectures and containers, EDM modules, cmsRun configs, EDM file tools
---

# CMSSW

## Overview

CMSSW is the CMS software framework: C++ modules plugged into an event loop,
wired together by Python configuration files and run with `cmsRun`. Releases
are pre-built on CVMFS. A user only creates a lightweight _developer area_ that
points at a release, adds packages to `src/`, and builds them with `scram`.

Use this skill for the release/area/build/config mechanics. For dataset lookup
(DAS), grid submission (CRAB) or NanoAOD-level columnar analysis, use the
dedicated skills when they exist instead of driving them through `cmsRun`.

## When to Use

- Creating a release area, or `cmsenv`/`scram` errors
- Picking the right release and architecture for a data-taking era, or running
  a release that is not built for the host OS
- Adding official CMSSW packages to edit, or merging someone's branch/PR
- Writing an EDAnalyzer/EDProducer/EDFilter and its `BuildFile.xml`
- Writing, reading, or debugging a `cmsRun` configuration
- Finding out what is inside an EDM file (collections, labels, sizes, history)

## Key Concepts

| Term                          | Meaning                                                                                                   |
| ----------------------------- | --------------------------------------------------------------------------------------------------------- |
| Release                       | `CMSSW_<major>_<minor>_<patch>`, e.g. `CMSSW_15_0_21`; installed read-only under `/cvmfs/cms.cern.ch/`    |
| `SCRAM_ARCH`                  | `<os>_<cpu>_<compiler>`, e.g. `el9_amd64_gcc12`; a release exists only for specific archs                 |
| Developer area                | `CMSSW_X_Y_Z/` made by `cmsrel`; your code lives in `src/<Subsystem>/<Package>/`                          |
| `$CMSSW_BASE`                 | Your developer area; `$CMSSW_RELEASE_BASE` is the CVMFS release it overlays                               |
| `cmsenv`                      | Shell function: `eval $(scramv1 runtime -sh)`; sets PATH, PYTHONPATH, LD_LIBRARY_PATH for the area        |
| Process / Path                | A config builds one `cms.Process`; `cms.Path` lists modules to run in order                               |
| Module types                  | `EDAnalyzer` (read-only), `EDProducer` (adds products), `EDFilter` (can stop a Path), `Source`, `Service` |
| Product label                 | `module:instance:process`, e.g. `slimmedMuons::PAT`; referenced via `cms.InputTag`                        |
| `_cfg.py`/`_cfi.py`/`_cff.py` | Top-level config / one module's defaults / a reusable config fragment                                     |
| Data tiers                    | RAW → RECO → AOD → MiniAOD → NanoAOD (flat ntuple, usually read without CMSSW)                            |

Energies and momenta in CMS data formats are in **GeV**.

## Canonical Patterns

### Choose the release (the user decides)

Never assume a release. Resolve it in this order, and state which one you used:

1. The release the user names (`CMSSW_14_0_15`, or shorthand `14_0_15`).
2. The release already active in the shell: `echo $CMSSW_VERSION $SCRAM_ARCH`
   (empty if `cmsenv` has not been run).
3. A release fixed by the task: the analysis's existing area
   (`ls -d CMSSW_*/`), its README or CI, or the release that produced the input
   data (`dasgoclient -query="release dataset=<dataset>"`).
4. Otherwise, ask. Suggest the newest patch release of the needed cycle from
   <https://cmssdt.cern.ch/SDT/ReleaseNotes/>.

Release numbers in this skill (`CMSSW_15_0_21`) are only the versions the
examples were tested with. Substitute the chosen release everywhere.

### Set up or switch a release area

[scripts/setup-release.sh](scripts/setup-release.sh) creates an area for **any**
release. It picks `SCRAM_ARCH` (a host-OS build if one exists, else the
production arch from `/cvmfs/cms.cern.ch/releases.map`), reports whether a
`cmssw-elX` container is needed, and can carry code over from an old area:

```bash
S=<skill-dir>/scripts/setup-release.sh
$S CMSSW_14_0_15 --list                      # archs it is built for; production arch marked
$S CMSSW_14_0_15 --dir ~/nobackup/work       # create the area (prints KEY=VALUE lines)
$S CMSSW_10_6_30 --dry-run                   # -> SCRAM_ARCH=slc7_amd64_gcc700, CONTAINER=cmssw-el7
$S CMSSW_15_0_21 --from ../CMSSW_15_0_20     # switch release: new area + copy src/ (no .git)
$S CMSSW_15_0_21 --prod                      # force the production arch (exact reproduction)
```

Run the printed `ENV_CMD` to `cmsenv` and work in the new area, then
`scram b -j 8`. Exit codes: 3 means release/arch not found, 4 means the area
already exists. Old areas are never modified, so switching back is just `cd`
plus `cmsenv` in the old area.

The same thing by hand, for a host-native release:

```bash
source /cvmfs/cms.cern.ch/cmsset_default.sh   # defines cmsrel, cmsenv, scram
cmsrel CMSSW_15_0_21                          # = scram project CMSSW CMSSW_15_0_21
cd CMSSW_15_0_21/src
cmsenv                                        # re-run in every new shell
```

`cmsrel` uses the current `SCRAM_ARCH` (host default, e.g. `el9_amd64_gcc12`).
Use `scram -a <arch> project CMSSW <release>` for another arch, and
`scram project -n <dir> CMSSW <release>` to choose the directory name.

### Run a release built for an older OS

On an EL9 host, releases built only for `slc7_*` or `el8_*` must run in a
container. `cmssw-el6`/`el7`/`el8`/`el9` (in `/cvmfs/cms.cern.ch/common`) start
apptainer. `setup-release.sh` prints the exact command; by hand:

```bash
cmssw-el7 -B /uscms_data -- 'cd ~/nobackup/CMSSW_10_6_30/src \
  && export SCRAM_ARCH=slc7_amd64_gcc700 && cmsenv && scram b -j 4'
cmssw-el7                      # or: interactive shell, then set up as usual
```

On cmslpc, `/uscms_data` (nobackup) is only visible inside with
`-B /uscms_data`. See
[releases-and-containers.md](references/releases-and-containers.md) for the
era → release → arch table and container details.

### Check out and patch official packages

Run in a **fresh, empty** `src/` before creating your own packages:

```bash
git cms-init                                  # one-time: sets up git in src/
git cms-addpkg PhysicsTools/NanoAOD           # sparse-checkout just this package
git cms-merge-topic <github-user>:<branch>    # or a PR number: git cms-merge-topic 12345
scram b -j 8
```

Browse code on <https://github.com/cms-sw/cmssw> on the branch matching your
release cycle (e.g. `CMSSW_15_0_X`), not `master`.

### Write and build a module

```bash
mkdir -p Demo && cd Demo
mkedanlzr DemoAnalyzer        # also: mkedprod, mkedfltr, mkesprod
cd DemoAnalyzer && scram b -j 8
```

Read data through tokens registered in the constructor and use
`iEvent.get(token)`. Declare every dependency in `plugins/BuildFile.xml`.
Define `fillDescriptions` and scram generates an importable `_cfi`
(`from Demo.DemoAnalyzer.demoAnalyzer_cfi import demoAnalyzer`). A complete,
tested analyzer, BuildFile, and config is in
[edanalyzer-walkthrough.md](references/edanalyzer-walkthrough.md).

### Minimal configuration with command-line arguments

```python
import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing

options = VarParsing("analysis")   # gives inputFiles, outputFile, maxEvents
options.parseArguments()

process = cms.Process("Demo")
process.load("FWCore.MessageService.MessageLogger_cfi")
process.MessageLogger.cerr.FwkReport.reportEvery = 1000
process.maxEvents = cms.untracked.PSet(input=cms.untracked.int32(options.maxEvents))
process.source = cms.Source("PoolSource", fileNames=cms.untracked.vstring(options.inputFiles))
process.TFileService = cms.Service("TFileService", fileName=cms.string(options.outputFile))

from Demo.DemoAnalyzer.demoAnalyzer_cfi import demoAnalyzer
process.demo = demoAnalyzer.clone(minPt=10.0)
process.p = cms.Path(process.demo)
```

```bash
python3 demo_cfg.py                                   # syntax check only
edmConfigDump demo_cfg.py > dumped_cfg.py             # fully expanded config
cmsRun demo_cfg.py inputFiles=root://cmsxrootd.fnal.gov//store/... maxEvents=1000
cmsRun -n 4 demo_cfg.py ...                           # 4 threads
```

Use `inputFiles_load=files.txt` (one file per line) for long file lists.

### Inspect an EDM file

```bash
edmFileUtil  <file>                        # events, lumis, runs, size
edmDumpEventContent <file>                 # type / module / instance / process
edmEventSize -v <file> | head -20        # per-branch size, largest first
edmProvDump <file>                         # configs that produced the file
```

Details and output examples: [edm-file-tools.md](references/edm-file-tools.md).

### Extra Python packages

```bash
scram-venv && cmsenv                 # once per area: creates $CMSSW_BASE/venv
export PYTHONNOUSERSITE=1
pip3 install <pkg>                   # lands in the area's venv, not ~/.local
scram tool list | grep -i onnx       # check first: many packages already ship
```

## Gotchas

- **`cmsenv` is per shell.** Batch and CRAB jobs, new terminals and
  `cmssw-elX` containers all need `source cmsset_default.sh` + `cmsenv` again.
- **Release not found** (`not available for arch el9_amd64_gcc12`): the release
  is not built for your `SCRAM_ARCH`. Run `setup-release.sh <release>`, which
  picks the arch and container. By hand: `ls -d /cvmfs/cms.cern.ch/*/cms/cmssw*/<release>`,
  `export SCRAM_ARCH=...`, and use the matching `cmssw-elX` container.
- **`git cms-addpkg` fails** with "destination path ... already exists": it
  needs an empty `src/` for `git cms-init`. Create the area, check out
  packages first, then add your own code.
- **`~/.local` shadows CMSSW Python.** Anything installed with
  `pip install --user` for the same Python version overrides CMSSW's packages
  and causes errors like `cannot import name 'version' from 'packaging'`.
  Export `PYTHONNOUSERSITE=1` and use `scram-venv`.
- **`VarParsing("analysis")` renames the output.** Setting `maxEvents` makes
  `outputFile=hists.root` become `hists_numEvent1000.root`. Glob for it or
  register your own option.
- **Config edits need no rebuild; C++ edits do.** Run `scram b` after touching
  `.cc`, `.h` or `BuildFile.xml`. `scram b` in `src/` builds everything; inside
  a package it builds only that package.
- **Missing `<use name=...>` in `BuildFile.xml`** shows up as undefined
  symbols at link time or a plugin load failure at runtime.
- **Modern `mkedanlzr`** writes `plugins/` plus Catch2 tests in `test/`. It no
  longer writes `python/ConfFile_cfg.py`, so write the `_cfg.py` yourself.
- **Use `iEvent.get(token)`**, not `getByLabel`. Every product must be declared
  with `consumes<>()` in the constructor or the framework throws.
- **`one::` modules serialize.** `edm::one::EDAnalyzer` with `SharedResources`
  (needed for `TFileService`) does not run concurrently. Prefer `edm::global`
  or `edm::stream` modules for heavy work in multithreaded jobs.
- **Open Data releases are old.** CMS Open Data 2015 uses `CMSSW_7_6_7`
  (`slc6`/`slc7`) and 2016 uses `CMSSW_10_6_30` (`slc7`). Both need
  `cmssw-el7` on EL9. Long `vstring` lists are fine in Python 3; the old
  255-argument limit no longer applies.
- **Units are GeV** in CMS data formats (unlike ATLAS, which uses MeV).

## Reference Files

- [edanalyzer-walkthrough.md](references/edanalyzer-walkthrough.md): read when
  writing a first analyzer. It covers a full MiniAOD muon analyzer with
  `TFileService`, its `BuildFile.xml`, a `_cfg.py` and the run commands, all
  tested on `CMSSW_15_0_21`.
- [scripts/setup-release.sh](scripts/setup-release.sh): run (don't read) to
  create or switch a release area for any release; `--help` for options.
- [releases-and-containers.md](references/releases-and-containers.md): read
  when choosing a release or `SCRAM_ARCH` for a data era, finding the latest
  release or what changed between releases (release notes), or when a release
  won't set up on the host OS.
- [edm-file-tools.md](references/edm-file-tools.md): read when you need to
  find collection labels, event counts, branch sizes or the production history
  of an EDM file.

## Docs

- CMSSW source: <https://github.com/cms-sw/cmssw>
- CMSSW release notes (updated every release; newest releases, merged PRs,
  external updates): <https://cmssdt.cern.ch/SDT/ReleaseNotes/>
- CMS Open Data workshop CMSSW lesson (introduction, EDAnalyzers, configuration):
  <https://cms-opendata-workshop.github.io/workshop2022-lesson-cmssw/aio/index.html>
- CMS Offline WorkBook: <https://twiki.cern.ch/twiki/bin/view/CMSPublic/WorkBook>
- CMSSW git tutorial (`git cms-*`): <https://cms-sw.github.io/tutorial.html>
