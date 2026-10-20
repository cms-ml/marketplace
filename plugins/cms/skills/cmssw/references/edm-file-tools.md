# EDM file inspection tools

Read this reference when you need the exact collection labels for an
`InputTag`, the event count or run/lumi content of a file, which branches
dominate its size, or which releases and configs produced it. All tools come
with any CMSSW release after `cmsenv`. Outputs below are real, from a 2015 Open
Data MiniAOD file on `CMSSW_15_0_21`.

## Contents

1. [Which tool](#which-tool)
2. [edmDumpEventContent](#edmdumpeventcontent)
3. [edmFileUtil](#edmfileutil)
4. [edmEventSize](#edmeventsize)
5. [edmProvDump](#edmprovdump)
6. [File paths: PFN vs LFN](#file-paths-pfn-vs-lfn)

## Which tool

| Question                                         | Command                                       |
| ------------------------------------------------ | --------------------------------------------- |
| What collections / labels are in the file?       | `edmDumpEventContent <file>`                  |
| How many events, lumis, runs; file size?         | `edmFileUtil <file>`                          |
| List every (run, lumi, event)                    | `edmFileUtil -e <file>`                       |
| Which branches take the space?                   | `edmEventSize -v <file>`                      |
| Which CMSSW releases / configs produced it?      | `edmProvDump <file>`                          |
| Fully expanded config of _my_ job                | `edmConfigDump my_cfg.py`                     |

## edmDumpEventContent

```text
$ edmDumpEventContent <file> | grep -E "Jets|slimmedElectrons"
vector<pat::Electron>   "slimmedElectrons"                    ""          "RECO"
vector<pat::Jet>        "slimmedJets"                         ""          "RECO"
vector<pat::Jet>        "slimmedJetsAK8"                      ""          "RECO"
vector<pat::Jet>        "slimmedJetsAK8PFCHSSoftDropPacked"   "SubJets"   "RECO"
```

Columns are C++ type, module label, product instance, process. They map
directly to `cms.InputTag("module", "instance", "process")` and to the C++ type
in `consumes<std::vector<pat::Jet>>(...)`. The process can usually be omitted,
which picks the latest process.

Options: `--regex REGEX` filters, `--name` prints only branch names, `--all`
prints everything, and `--run` / `--lumi` look at run/lumi products instead of
event products.

## edmFileUtil

```text
$ edmFileUtil <file>
<file> (1 runs, 18 lumis, 49871 events, 971558058 bytes)
```

Useful flags: `-e` lists every run/lumi/event with its TTree entry, `-j` gives
JSON output, `-u` prints the file UUID, `-a` the adler32 checksum, and
`-F list.txt` takes a list of files. Use `-d` to convert an LFN to the local
PFN using the site configuration.

## edmEventSize

```text
$ edmEventSize -v <file> | head -5
File <file> Events 49871
Branch Name | Average Uncompressed Size (Bytes/Event) | Average Compressed Size (Bytes/Event)
patPackedCandidates_packedPFCandidates__RECO. 49439.5 8521.96
patElectrons_slimmedElectrons__RECO. 5406.23 1276.61
recoCaloClusters_reducedEgamma_reducedESClusters_RECO. 3754.45 1221.54
```

Output is already sorted by compressed size, largest first. Branch names have
the form `<type>_<module>_<instance>_<process>.`.

## edmProvDump

```text
$ edmProvDump <file> | head
Processing History:
    HLT '"CMSSW_7_4_12_patch4"' [1]  (88dc8964d9253fcc7f49ff819194eb92)
      RECO '"CMSSW_7_6_5_patch1"' [1]  (d5d52422828e141a198234902a935587)
...
```

Shows each processing step with its release, then the parameters of every
module that produced a product. Grep it for a module label to see exactly how a
collection was made (cuts, input tags, global tag).

## File paths: PFN vs LFN

- **LFN** (logical): `/store/mc/...`. Resolved by the site's storage
  configuration. Works in `cmsRun` at a CMS site, but not on every
  machine.
- **PFN via XRootD**: prefix the LFN with a redirector to read from anywhere
  with a grid proxy (`voms-proxy-init -voms cms`):
  - `root://cmsxrootd.fnal.gov//store/...` (US redirector)
  - `root://xrootd-cms.infn.it//store/...` (EU redirector)
  - `root://cms-xrd-global.cern.ch//store/...` (global redirector)
- **CMS Open Data**: `root://eospublic.cern.ch//eos/opendata/cms/...`. No
  proxy needed.

All the edm tools and `cmsRun` accept `root://` URLs directly.
