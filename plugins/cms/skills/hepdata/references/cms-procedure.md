# HEPData in CMS: what to provide and who reviews it

Read this reference when planning the HEPData record for a CMS paper (what
tables to include, when to start, who signs it off), or when reviewing a
record before it goes to the physics group's HEPData contact. It summarises
public pages. The CMS-internal publication twiki is linked, not copied.

Contents:

1. Timeline
2. What to include (EXO reinterpretation requirements)
3. Full statistical models
4. B2G submissions
5. Checklist before review
6. Open Data studies

## 1. Timeline

From the EXO MC & Interpretation pages (checked October 2026):

- Contact your group's HEPData contact around the **approval talk / CWR**, so
  that a record is created for the analysis. Submit to that record, not to a
  personal one.
- The contact reviews it and gives a green light or feedback.
- The record goes public with the paper. Put the HEPData link in the draft
  before arXiv submission.
- Group addresses and current contact names are on the EXO page and the CMS
  publication twiki (links below). They change, so look them up rather than
  hard-coding them.

## 2. What to include

The EXO page lists, as the minimum for reinterpretation:

- **Signal generation inputs**: gridpacks or cards, cross sections and
  k-factors used.
- **Cutflows**: for each signal model, relative and absolute efficiencies
  after each event-level selection step in each region, with statistical
  uncertainties or generator-level yields. The page calls this the minimal
  requirement. Include it even when the final selection is a neural network.
- **Figure content**: limits, and the background, signal and data yields in
  the regions used for them, plus other figures useful for reinterpretation
  (spectra, efficiencies).
- **Covariance matrices**: optional. The EXO page notes that full likelihoods
  are now preferred where they can be shared.

## 3. Full statistical models

Datacards and ROOT inputs that reproduce the paper's results, with a README
that explains how to run Combine. They are published through a CERN GitLab
repository and the CMS statistical-models community on the CERN repository,
reviewed by the Combine and HEPData contacts. See the EXO page for the
current process.

## 4. B2G submissions

B2G keeps its HEPData submission repositories in the `cms-b2g-hepdata` group
on CERN GitLab (CERN login). Look at a recent analysis there for the
expected layout and naming before starting a new one.

## 5. Checklist before review

- [ ] One table per figure panel or paper table, named after it (`Figure 3a`, `Table 2`)
- [ ] `description` gives the selection, normalisation and what the uncertainties include
- [ ] Keywords: `observables`, `reactions`, `cmenergies` on every table, plus `phrases`
- [ ] Units on every axis; GeV for CMS kinematics
- [ ] Asymmetric uncertainties with the minus value negative
- [ ] No NaN or inf (`grep -n nan *.yaml` is empty)
- [ ] Values read from the analysis outputs, not digitised (inputs checked by the script)
- [ ] `hepdata-validate -d .` exits 0
- [ ] Sandbox upload renders every table and image
- [ ] Cutflows and signal-model inputs present (EXO minimum)

## 6. Open Data studies

A record built from CMS Open Data is not a CMS result. Label it so in
`submission.comment` and every table description, and don't attach a CMS
paper's INSPIRE id to it. `validation/dijet-2016/hepdata/` in this repository
shows such a record: 6 tables (m_jj spectra per category, fit results,
trigger efficiency, b-tag efficiency, signal injection), each with its plot
image, string category variables instead of encoded indices, and empty
efficiency bins dropped. It is validated offline and not uploaded.

## Links

- EXO MC & Interpretation, reinterpretation materials:
  <https://exo-mc-and-i.gitbook.io/exo-mc-and-interpretation/reinterpretationmaterials>
- CMS publication procedure (internal):
  <https://twiki.cern.ch/twiki/bin/viewauth/CMS/Internal/Publications>
- CMS B2G HEPData repositories: <https://gitlab.cern.ch/cms-b2g-hepdata>
- HEPData about page: <https://www.hepdata.net/about>
