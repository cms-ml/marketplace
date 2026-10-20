# {{Analysis/Workflow Name}}

{{Short description of the analysis (no more than 2 lines)}}

## Data Samples

{{List every sample needed. Keep DAS names exactly as given. Leave the release/version columns blank unless the dataset name or the user states them.}}

| Dataset (DAS name or Open Data path) | Tier | Era / campaign | Role(s) in analysis |
| --- | --- | --- | --- |
| {{dataset 1}} | {{NANOAOD / NANOAODSIM / MINIAOD(SIM)}} | {{e.g. Run2016H, RunIISummer20UL16NanoAODv9}} | {{Data / Signal / Background / Control region}} |
| {{dataset 2}} | {{tier}} | {{era}} | {{role}} |

* Luminosity / certification: {{Golden JSON and integrated luminosity for data, or "MC only"}}
* Triggers: {{HLT paths per dataset/era, or "none specified"}}
* MC normalisation: {{cross sections (pb) and source, sum of weights from Runs/genEventSumw, or "shape only"}}

## Histograms

{{List each summary histogram (inputs to the statistical analysis or cross-checks).}}

1. {{Histogram 1 Title}}
    * x Axis
        * {{What is plotted, precisely (which object, which combination)}}
        * {{Axis label with units in LaTeX, e.g. `$p_{T}$ [GeV]`, `$\eta$`}}
        * {{Binning and range if the user gave them; otherwise leave for the implementation}}
        * {{Entries per event: one per event / per object / per combination}}
    * {{Other axes (e.g. region, process, systematic) if any}}
    * Weights: {{e.g. genWeight x xsec x lumi / sumw, x scale factors; "unweighted" for data}}
2. {{Histogram 2 Title}}
    * ...

## Analysis Steps

{{High-level manipulations needed to go from NanoAOD to the histograms, as reusable calculations.}}

1. {{Selection}}
    * {{Event-level cuts (trigger, MET filters, object counts) and object-level cuts (pT, eta, ID, isolation)}}
1. {{Variable Name}}
    * {{How it is calculated}}
    * {{Combinatorics stated explicitly, in particular how the best combination is chosen}}
1. {{Repeat as needed}}

## Corrections and Systematics

{{Corrections to apply and uncertainties to propagate. Write "None" if not required.}}

* {{e.g. jet energy corrections/resolution, pileup reweighting, lepton ID/ISO/trigger scale factors, b-tag scale factors (via correctionlib), with their up/down variations}}

## Workflow

{{Steps to process the files into the final histograms. Add others (e.g. ML training) as needed.}}

1. Data Extraction and Skimming
    * {{Filtering at the source: e.g. "events with >= 2 muons with pT > 20 GeV". Say `No Filtering` if none.}}
    * {{Branches to read (NanoAOD names such as Muon_pt, Jet_btagDeepFlavB, MET_pt, genWeight)}}
2. Analysis and Histogramming
    * {{Derived variables, combinatorics, final selections}}
    * {{Fill the histograms above}}

{{If systematics are needed, note that steps above repeat per variation. Omit otherwise.}}

## Statistical Analysis

{{Fit/limit/significance to perform, e.g. a binned shape fit with Combine, or "None".}}

## Tools

{{Guidance on tools for each part.}}

* {{tool 1}}
  * {{How it is used}}
* {{tool 2}}
  * ...
