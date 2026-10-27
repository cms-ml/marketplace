# Task for the cms-analysis-coder agent

Run it headless from the repository root on cmslpc:

```bash
tmux new -s dijet
sed -n '/^## Task/,$p' validation/dijet-2016/PROMPT.md | \
  claude -p --agent cms:cms-analysis-coder \
    --plugin-dir plugins/cms --plugin-dir plugins/af-fnal-lpc --plugin-dir plugins/hep-python-tools \
    --permission-mode acceptEdits --allowedTools "Bash Read Write Edit Glob Grep Skill TodoWrite" \
    > validation/dijet-2016/agent_report.md 2>&1
```

The prompt goes on stdin (`--allowedTools` takes a list and would swallow a
prompt argument). Drop the `--plugin-dir` options if the plugins are
installed from the marketplace.

Or paste the Task section into a Claude Code session with the plugins
installed and ask it to use the `cms-analysis-coder` agent.

## Task

Reproduce, with 2016 CMS Open Data, the plot set of the b-tagged high-mass
dijet resonance search presented by Aaron Mankel (APS lightning talk,
10 March 2026; CMS B2G). The Run 2 published analysis is CMS-EXO-20-008.
Read `validation/dijet-2016/README.md` first for the dataset choices and the
differences from the reference.

Work in `validation/dijet-2016/`. First write `specification.md` with the
analysis-spec-builder skill, then implement it.

**Inputs (CMS Open Data, root://eospublic.cern.ch, no proxy):**

- Data: `/eos/opendata/cms/Run2016G/JetHT/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/`
  and `/eos/opendata/cms/Run2016H/JetHT/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/`
  (70 + 72 ROOT files). Develop on a few files, and record exactly which files
  each result uses.
- Signal: `/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/ZprimeToBB_narrow_M-<mass>_TuneCP5_13TeV-madgraph-pythia8/`
  for M = 1000, 1600, 2000, 3000 and 4000 GeV at least.
- QCD (for the data/MC comparison only):
  `/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/QCD_HT*_TuneCP5_PSWeights_13TeV-madgraphMLM-pythia8/`,
  normalised with `Runs/genEventSumw` and cross sections you look up and cite.
- DeepJet working points: the official 2016postVFP_UL values from
  `/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/BTV/2016postVFP_UL/btagging.json.gz`
  (correction `deepJet_wp_values`).

**Selection (adapt from the reference, justify every change):** two leading
AK4 jets with tight jet ID, |η| < 2.4 (b-tag acceptance in 2016), |Δη_jj| <
1.1. Categories: ≥1 b-tag (Medium WP) and 2 b-tags. Signal triggers are the
OR of the 2016 high-pT jet/HT paths present in the files. Measure the
efficiency with a lower-threshold reference trigger, and set the m_jj
threshold where the efficiency plateaus.

**Plots (the APS talk set), each for ≥1 b-tag and 2 b-tags where relevant,
CMS style, PNG + PDF, in `validation/dijet-2016/plots/`:**

1. |Δη(j1, j2)| and η(j) distributions
2. Trigger efficiency vs m_jj with the chosen threshold marked
3. b-tag efficiency vs Z′ mass for the Loose, Medium and Tight WPs
4. Pseudo-significance vs Z′ mass for WP combinations (2 b-tag category)
5. m_jj spectrum: data vs normalised QCD MC, with Z′ signals overlaid
6. Background fit of the m_jj spectrum with the dijet function
   p0 (1−x)^p1 / x^(p2 + p3 ln x + p4 ln² x), x = m_jj/√s: data, fit, pulls
   panel, χ²/ndf, Z′ shapes overlaid. Also an F-test table for 3/4/5
   parameters.
7. Signal injection: inject a Z′ (e.g. 2 TeV) into the data spectrum, refit,
   and compare recovered with injected yield.

**Deliverables in `validation/dijet-2016/`:**

- `specification.md`
- the analysis code (re-runnable)
- `plots/`
- `summary.json` with at least: trigger plateau efficiency and threshold,
  events per category, the fit's χ²/ndf and chosen number of parameters per
  category, and injected vs recovered signal
- `hepdata/`: a HEPData submission (via the hepdata skill) with the m_jj
  spectra, fit results and trigger efficiency, validated when written
- `SKILLS_USED.md`

Use iminuit from a pip/uv environment (CMSSW ships an old version). Don't run
over all 142 data files interactively. Use a subset now, and list what a full
run needs.
