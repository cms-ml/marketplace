# Example: dimuon resonances on CMS Open Data

A ready-to-paste request for a new Claude Code conversation with the `cms` and
`hep-python-tools` plugins installed. It exercises five skills:
`analysis-spec-builder`, `awkward-array`, `vector-awkward`, `hist` and
`standalone-script`.

**Data:** 2016H DoubleMuon NanoAOD from CMS Open Data, read over XRootD from
`eospublic.cern.ch`, so no grid proxy is needed. One file has about 2.1M events.
Its first 200k events already contain about 7.7k J/ψ, 3.4k Υ and 25.7k Z
opposite-sign pairs in their mass windows, before any trigger selection.

**Before you start:** do the uv setup in the README's "One-time setup on
cmslpc" section, and change the two directories below if you like.

## Prompt

```text
Use the analysis-spec-builder skill to write a spec, then implement it.

Task: opposite-sign dimuon analysis on CMS Open Data 2016H DoubleMuon NanoAOD
(/eos/opendata/cms/Run2016H/DoubleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/,
read via root://eospublic.cern.ch, no proxy needed). Start with 2 files.
Show the J/psi, psi(2S), Upsilon(1S,2S,3S) and Z resonances.

Work in ~/nobackup/dimuon-demo/. Write the spec to specification.md there.
Implement it as a standalone PEP 723 script (uv), and write all plots as
PNG + PDF to ~/nobackup/dimuon-demo/plots/, CMS style, label
"CMS Open Data", 13 TeV.

Plots wanted (one per file):
1. Full OS dimuon mass spectrum, log-log, 0.25-150 GeV, resonances annotated
2. J/psi + psi(2S) zoom (2.6-4.2 GeV)
3. Upsilon(1S,2S,3S) zoom (8.5-11.5 GeV)
4. Z peak (60-120 GeV)
5. Opposite-sign vs same-sign spectrum overlay, with OS/SS ratio panel
6. Selected muon pT, eta, phi, and muon multiplicity
7. Dimuon pT and rapidity for each resonance window, overlaid
8. 2D: dimuon mass vs dimuon pT
9. Full spectrum for 3-4 different HLT dimuon paths overlaid (trigger sculpting)
10. Cutflow (events and pairs after each selection step)

Finally write SKILLS_USED.md listing which skill guided each step, and any
place where a skill was wrong, missing information, or not used.
```

## What to check afterwards

- **The spec:** `specification.md` has no `{{` placeholders left, and its
  dataset path is exactly the one above.
- **The plots:** peaks appear near 3.10, 3.69, 9.46, 10.02, 10.36 and 91.2 GeV,
  with units in GeV and the CMS Open Data label.
- **The script:** it runs again with `uv run --script <script>.py`.
- **`SKILLS_USED.md`:** please report any "skill was wrong / missing" items as
  an issue or PR. They are how these skills get fixed.
