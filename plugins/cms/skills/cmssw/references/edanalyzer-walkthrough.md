# EDAnalyzer walkthrough (MiniAOD muons → histogram)

Read this reference when writing a first EDAnalyzer, or when a module builds
but produces nothing. Every file below was built with `scram b` and run with
`cmsRun` on `CMSSW_15_0_21` (`el9_amd64_gcc12`) against a CMS Open Data
MiniAOD file.

## Contents

1. [Create the package](#1-create-the-package)
2. [BuildFile.xml](#2-buildfilexml)
3. [The analyzer](#3-the-analyzer)
4. [The configuration](#4-the-configuration)
5. [Build and run](#5-build-and-run)
6. [Adapting it](#6-adapting-it)

## 1. Create the package

CMSSW expects `src/<Subsystem>/<Package>/`. Scripts and the build break with
any other depth.

```bash
cmsrel CMSSW_15_0_21 && cd CMSSW_15_0_21/src && cmsenv
mkdir -p Demo && cd Demo
mkedanlzr DemoAnalyzer             # writes plugins/ and test/ (Catch2)
mkdir -p DemoAnalyzer/test         # put your _cfg.py here
```

Layout after this walkthrough:

```text
Demo/DemoAnalyzer/
├── plugins/
│   ├── BuildFile.xml
│   └── DemoAnalyzer.cc
└── test/
    └── demo_cfg.py
```

## 2. BuildFile.xml

`plugins/BuildFile.xml` lists every package/external the code includes:

```xml
<use name="FWCore/Framework"/>
<use name="FWCore/ParameterSet"/>
<use name="FWCore/PluginManager"/>
<use name="FWCore/ServiceRegistry"/>
<use name="CommonTools/UtilAlgos"/>
<use name="DataFormats/PatCandidates"/>
<use name="root"/>
<flags EDM_PLUGIN="1"/>
```

`EDM_PLUGIN="1"` makes the library loadable by name from a config.

## 3. The analyzer

`plugins/DemoAnalyzer.cc`:

```cpp
#include "FWCore/Framework/interface/Frameworkfwd.h"
#include "FWCore/Framework/interface/one/EDAnalyzer.h"
#include "FWCore/Framework/interface/Event.h"
#include "FWCore/Framework/interface/MakerMacros.h"
#include "FWCore/ParameterSet/interface/ParameterSet.h"
#include "FWCore/ParameterSet/interface/ConfigurationDescriptions.h"
#include "FWCore/ParameterSet/interface/ParameterSetDescription.h"
#include "FWCore/ServiceRegistry/interface/Service.h"
#include "CommonTools/UtilAlgos/interface/TFileService.h"
#include "DataFormats/PatCandidates/interface/Muon.h"
#include "TH1F.h"

class DemoAnalyzer : public edm::one::EDAnalyzer<edm::one::SharedResources> {
public:
  explicit DemoAnalyzer(const edm::ParameterSet&);
  static void fillDescriptions(edm::ConfigurationDescriptions& descriptions);

private:
  void analyze(const edm::Event&, const edm::EventSetup&) override;

  const edm::EDGetTokenT<pat::MuonCollection> muonToken_;
  const double minPt_;
  TH1F* hPt_;
};

DemoAnalyzer::DemoAnalyzer(const edm::ParameterSet& iConfig)
    : muonToken_(consumes<pat::MuonCollection>(iConfig.getParameter<edm::InputTag>("muons"))),
      minPt_(iConfig.getParameter<double>("minPt")) {
  usesResource(TFileService::kSharedResource);
  edm::Service<TFileService> fs;
  hPt_ = fs->make<TH1F>("muon_pt", ";muon p_{T} [GeV];muons", 100, 0., 200.);
}

void DemoAnalyzer::analyze(const edm::Event& iEvent, const edm::EventSetup&) {
  for (const pat::Muon& mu : iEvent.get(muonToken_)) {
    if (mu.pt() > minPt_)
      hPt_->Fill(mu.pt());
  }
}

void DemoAnalyzer::fillDescriptions(edm::ConfigurationDescriptions& descriptions) {
  edm::ParameterSetDescription desc;
  desc.add<edm::InputTag>("muons", edm::InputTag("slimmedMuons"));
  desc.add<double>("minPt", 5.0);
  descriptions.add("demoAnalyzer", desc);
}

DEFINE_FWK_MODULE(DemoAnalyzer);
```

Points to notice:

- The token is created in the constructor with `consumes<>()`. Reading a
  product that was never declared throws at runtime.
- `iEvent.get(token)` returns a const reference and throws if the product is
  missing. Use `iEvent.getHandle(token)` and check `isValid()` when a product
  is optional.
- `usesResource(TFileService::kSharedResource)` is required for a `one::`
  module that uses `TFileService`.
- `fillDescriptions` validates the config parameters and makes scram generate
  `cfipython/<arch>/Demo/DemoAnalyzer/demoAnalyzer_cfi.py`, so configs can
  `import` the module with its defaults instead of retyping them.

## 4. The configuration

`test/demo_cfg.py`:

```python
import FWCore.ParameterSet.Config as cms
from FWCore.ParameterSet.VarParsing import VarParsing

options = VarParsing("analysis")  # provides inputFiles, outputFile, maxEvents
options.setDefault("outputFile", "demo_hists.root")
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

## 5. Build and run

```bash
cd $CMSSW_BASE/src
scram b -j 8
python3 Demo/DemoAnalyzer/test/demo_cfg.py         # parses? then:
cmsRun Demo/DemoAnalyzer/test/demo_cfg.py \
  inputFiles=root://eospublic.cern.ch//eos/opendata/cms/Run2015D/SingleElectron/MINIAOD/08Jun2016-v1/10000/001A703B-B52E-E611-BA13-0025905A60B6.root \
  maxEvents=2000 outputFile=hists.root > run.log 2>&1
```

Because `maxEvents` was set, `VarParsing("analysis")` writes
`hists_numEvent2000.root`, not `hists.root`. The histogram is under the module
label: `demo/muon_pt`. In the tested run, 2000 events gave 113 muons with
pT > 10 GeV.

```bash
python3 -c "import ROOT; f=ROOT.TFile('hists_numEvent2000.root'); print(f.Get('demo/muon_pt').GetEntries())"
```

Keep the `TFile` in a variable. `ROOT.TFile(...).Get(...)` on one line lets the
file close, which deletes the histogram it owns.

## 6. Adapting it

| Want to…                    | Change                                                                                     |
| --------------------------- | ------------------------------------------------------------------------------------------ |
| Read another collection     | Add an `EDGetTokenT<...>`, its `#include`, the `<use>` in BuildFile, and a `desc.add<>()`  |
| Apply a trigger requirement | Put an `HLTHighLevel` EDFilter before the analyzer in the `cms.Path`                       |
| Write a TTree, not hists    | `fs->make<TTree>(...)`, branches bound to member variables, `Fill()` once per event        |
| Add new products            | Use `mkedprod` (EDProducer); `iEvent.emplace(putToken, ...)` with a `produces<>()` token   |
| Run multithreaded           | Switch to `edm::global::EDAnalyzer` / `edm::stream::`; `cmsRun -n 4 cfg.py`                |
| Find collection labels      | `edmDumpEventContent <file>`; see [edm-file-tools.md](edm-file-tools.md)                   |

Trigger filter example (MiniAOD, Run 2015D):

```python
process.hltFilter = cms.EDFilter("HLTHighLevel",
    TriggerResultsTag=cms.InputTag("TriggerResults", "", "HLT"),
    HLTPaths=cms.vstring("HLT_Ele27_WPLoose_Gsf_v*"),
    eventSetupPathsKey=cms.string(""),
    andOr=cms.bool(True),     # True = OR of listed paths
    throw=cms.bool(True),     # throw if a path name is not in the menu
)
process.p = cms.Path(process.hltFilter + process.demo)
```
