---
name: analysis-spec-builder
description: >-
  Use when a user wants to plan, scope or write down a CMS physics analysis
  or plotting task before coding it: creating or updating an analysis
  specification, turning a quick request ("plot the dimuon mass in 2016
  data vs DY", "find the best trijet in ttbar") into a structured document,
  listing datasets, triggers, selections, histograms, corrections and
  statistical treatment, or producing a specification.md for later
  implementation.
metadata:
  summary: Turn an analysis request into a structured CMS specification.md (datasets, cuts, histograms, tools)
---

# Analysis Spec Builder

## Overview

Turn an informal analysis request into a concise, structured specification
that someone (or an agent) can implement. Fill the CMS template, ask only the
questions that block progress, iterate until the user confirms, then write
`specification.md`. The spec says _what_ is to be done. It is not an
implementation plan.

## When to Use

- "I want to plot/measure X in dataset Y": formalise before coding
- Updating an existing `specification.md` with new details
- Handing work to another person or agent with an unambiguous brief

## Key Concepts

| Section                      | Must capture                                                                                  |
| ---------------------------- | --------------------------------------------------------------------------------------------- |
| Data Samples                 | Exact DAS names (verbatim), tier, era/campaign, role. Golden JSON, triggers, MC normalisation |
| Histograms                   | Quantity, LaTeX label with units (GeV), binning if given, entries per event, weights          |
| Analysis Steps               | Object and event selections, derived variables, explicit combinatorics                        |
| Corrections and Systematics  | POG corrections/SFs and variations, or "None"                                                 |
| Workflow                     | Source-level skim, branches to read, then histogramming                                       |
| Statistical Analysis / Tools | Fit/limit or "None". Which tool does what                                                     |

## Canonical Patterns

### Workflow

1. Read the template
   [assets/analysis-specification-template.md](assets/analysis-specification-template.md).
2. Draft: replace every `{{...}}` with content derived from the request. Keep
   the section order.
3. Ask focused follow-ups, grouped by section and answerable with yes/no or a
   short answer, only for details that block the spec: datasets, era,
   triggers, key cuts, histogram definitions.
4. When something is unknown, propose a sensible default and mark it inline
   as `(question: ...)` rather than leaving a placeholder.
5. Iterate. On new answers, update only the affected sections and summarise
   what changed.
6. When the user confirms, write `specification.md` (or the path they give)
   and say where it was written.

Check that no placeholder survived:

```bash
grep -n '{{' specification.md || echo "no placeholders left"
```

### Defaults (when the user does not say)

| Topic          | Default                                                                                    |
| -------------- | ------------------------------------------------------------------------------------------ |
| Data format    | NanoAOD (`NANOAOD` / `NANOAODSIM`)                                                         |
| Dataset lookup | `dasgoclient -query="dataset=/<Primary>/<Era>*/NANOAOD*"`. Never invent dataset names; ask |
| Data quality   | Apply the Golden JSON for the era (state it as a question if unconfirmed)                  |
| MC weights     | `genWeight × σ × L / Σ Runs/genEventSumw`. Cross section and its source as a question      |
| Reading/skim   | uproot + awkward (coffea for large multi-file processing)                                  |
| Kinematics     | vector                                                                                     |
| Corrections    | correctionlib with POG JSON files                                                          |
| Histograms     | hist + mplhep (CMS style), PNG output                                                      |
| Statistics     | Combine (binned shape fits, limits) when a fit is requested                                |

The `awkward-array`, `vector-awkward` and `hist` skills cover the
implementation of these tools.

## Gotchas

- **Keep dataset names verbatim**, including campaign and processing
  strings. Never shorten or "fix" them, and never make one up. Look it up or
  ask.
- **Be explicit about combinatorics.** "The trijet closest to 172.5 GeV" or
  "the two leading opposite-sign muons", not "the top candidate".
- **Data vs MC branches differ.** `genWeight`, `Pileup_nTrueInt`, `GenPart_*`
  exist only in MC, so list them separately in the Workflow.
- **Units are GeV** in NanoAOD. Labels need units (`$m_{\mu\mu}$ [GeV]`).
- **Don't over-specify.** Exact object versions, working points or tags
  belong in the spec only if the user gave them. Otherwise mark them as a
  question or leave them for the implementation.
- **Negative MC weights.** aMC@NLO samples carry negative `genWeight`s. The
  normalisation line must use the sum of weights, not the event count.
- **ASCII text**, except LaTeX inside backticks.

## Reference Files

- [assets/analysis-specification-template.md](assets/analysis-specification-template.md):
  the template to fill (CMS sections: Golden JSON, triggers, MC normalisation,
  corrections).
- [references/examples.md](references/examples.md): read to see three
  finished specs: MET in 2016H data, Z→μμ data vs DY MC with corrections, and
  closest-mass trijet in ttbar. All dataset names and branches were checked
  against DAS and real NanoAOD files.

## Docs

- DAS (grid certificate in the browser): <https://cmsweb.cern.ch/das/>
- NanoAOD documentation: <https://cms-nanoaod-integration.web.cern.ch/autoDoc/> (CERN login)
- CMS Open Data: <https://opendata.cern.ch/>
- Combine: <https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/latest/>
- Adapted from the IRIS-HEP marketplace `analysis-spec-builder` skill
  (BSD 3-Clause; see `plugins/cms/VENDORED-LICENSES.md`):
  <https://github.com/iris-hep/marketplace/tree/main/iris-hep/skills/analysis-spec-builder>
