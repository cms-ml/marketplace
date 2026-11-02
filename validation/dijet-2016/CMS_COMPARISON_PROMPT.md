# Task for the cms-results-validator agent: compare with published CMS results

This is the first run of the `cms-results-validator` agent, made **before**
the `cms-results-comparison` skill exists. What the agent has to work out
alone (finding records, reading HEPData, choosing tests) seeds that skill.
The second run, after the skill is written, uses the same prompt.

## How to run

From the repository root on cmslpc, inside `tmux`:

```bash
tmux new -s validator
cd <repo>                                   # the marketplace checkout, branch feat/results-validator
DIMUON_DIR=<path to the dimuon demo outputs>   # directory with histograms.pkl, specification.md, dimuon_analysis.py
{ sed -n '/^## Task/,$p' validation/dijet-2016/CMS_COMPARISON_PROMPT.md; echo; echo "DIMUON_DIR=$DIMUON_DIR"; } | \
  claude -p --agent cms:cms-results-validator \
    --plugin-dir plugins/cms --plugin-dir plugins/af-fnal-lpc --plugin-dir plugins/hep-python-tools \
    --permission-mode acceptEdits --allowedTools "Bash Read Write Edit Glob Grep Skill TodoWrite" \
    > validation/dijet-2016/cms-comparison-agent-report.md 2>&1
```

Or paste the Task section into a Claude Code chat and start it with "Use the
cms-results-validator agent to …", adding the `DIMUON_DIR=...` line at the end.

Check progress with `ls -lt validation/dijet-2016/cms-comparison/`.

## Task

You are reviewing two student analyses on 2016 CMS Open Data and comparing
them with the published CMS results. Work in
`validation/dijet-2016/cms-comparison/` (create it). Do not modify anything
else under `validation/` or the student's directories.

Environment: `set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh`
(Python 3.13, numpy, scipy, iminuit, hist, mplhep, PyYAML, uproot). The
interactive node has about 6 GB of free memory. Run long commands with
`/usr/bin/time -v ... > log 2>&1; echo EXIT $? >> log`. HEPData and INSPIRE
are reachable from cmslpc. Download records into a scratch directory
outside the repository (for example `/uscms_data/d3/$USER/hepdata_cache/`).

### The student results

1. **b-tagged dijet search, 2016G+H JetHT Open Data**: `validation/dijet-2016/`.
   Read `README.md`, `specification.md`, `summary.json`, `hepdata/` (the
   student's HEPData record) and `plots/`. 142 files, 16.4 fb⁻¹, AK4 CHS jets
   |η| < 2.4, |Δη_jj| < 1.1, DeepJet medium WP, m_jj > 1058 GeV, categories
   ≥1 b tag and 2 b tags. The condor skims are in
   `/uscms_data/d3/$USER/dijet2016_work/skims/` if you need to rebuild a
   distribution (stream one file at a time; see `dijetlib.iter_events`).
2. **Opposite-sign dimuon spectrum, 2016H DoubleMuon Open Data**: the
   directory given as `DIMUON_DIR` at the end of this prompt. Read
   `specification.md` and `SKILLS_USED.md`. Histograms are in
   `histograms.pkl` (a dict of `hist` objects: `m_full`, `m_jpsi`, `m_ups`,
   `m_z`, `win_pt`, `win_y`, ...). Two files only, loose muon ID, no
   isolation, no momentum corrections, no luminosity. You may rerun
   `dimuon_analysis.py` on the same 2 files **into your scratch area** with a
   selection matched to a CMS fiducial region. Do not overwrite the
   student's files.

### CMS counterparts (verified on INSPIRE and HEPData, October 2026)

Open each record yourself and confirm before using it. Download a whole
record with `https://www.hepdata.net/download/submission/ins<INSPIRE>/1/yaml`;
search with `https://www.hepdata.net/search/?q=<query>&format=json`; INSPIRE
metadata from `https://inspirehep.net/api/literature?q=reportnumber:<RN>`.

| Student result                        | Counterpart                                                                                                  | HEPData                                                  | Tables                                                                                                                                                                        |
| ------------------------------------- | ------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| dijet 2 b tags, ≥1 b tag m_jj spectra | CMS-EXO-20-008, b-tagged dijet, 13 TeV, 2016–2018 (paper: INSPIRE 2676943, PRD 108 (2023), arXiv:2205.01835) | **ins1920627** (attached to the PAS, CMS-PAS-EXO-20-008) | "Figure 3 first row first column" (double b, 2016), "... second row first column" (single b, 2016), "... fourth row first column" (inclusive single b, 2016); dσ/dm in fb/GeV |
| dijet Z′ signal efficiency vs mass    | same                                                                                                         | ins1920627                                               | "Figure 2" (Z′→bb̄ acceptance × efficiency)                                                                                                                                    |
| dijet inclusive spectrum              | CMS-EXO-16-056, dijet, 2016, 36 fb⁻¹ (JHEP 08 (2018) 130)                                                    | ins1676214                                               | "Differential dijet spectrum (High-mass analysis)"                                                                                                                            |
| dimuon Z-region mass shape            | CMS-SMP-17-001, Drell-Yan dσ/dm, 13 TeV 2015 (JHEP 12 (2019) 059)                                            | ins1711625                                               | "Table 5" (dimuon, fiducial, no FSR correction), "Table 3" (full phase space)                                                                                                 |
| dimuon Z pT and rapidity              | CMS-SMP-17-010, Z differential, **2016 data**, 35.9 fb⁻¹ (JHEP 12 (2019) 061)                                | ins1753680                                               | "Figure 14a" (normalised Z pT), "Figure 14c" (normalised \|y(Z)\|), dressed leptons, with covariance tables; check whether these are dimuon or combined dilepton              |
| dimuon quarkonium peaks               | CMS-BPH-15-005, quarkonium cross sections, 13 TeV 2015 (PLB 780 (2018) 251)                                  | ins1633431                                               | "Table 3"–"Table 5" (Υ(1S,2S,3S) double-differential); "Table 1", "Table 2" (J/ψ, ψ(2S))                                                                                      |

Traps already found: CMS-EXO-16-057 is the **8 TeV** b-tagged dijet search,
not 2016. The 2016 tables of ins1920627 carry a `LUMINOSITY: 138` qualifier
although they are per year: check what the normalisation really is and
report it. CMS-MUO-16-001 has no HEPData record. Wide jets (EXO-16-056,
EXO-20-008) are not AK4 jets. HEPData units differ from the student's
(fb/GeV vs events/GeV).

### Tests to run

For each, state the comparability first, then the test, the number and the
verdict (CONSISTENT, TENSION, INCONSISTENT, NOT COMPARABLE).

**Dijet**

- D1 (exact): the student's DeepJet WPs against the BTV POG JSON, and the
  2016G+H luminosity against the Open Data luminosity records.
- D2 (shape): the 2 b-tag and ≥1 b-tag m_jj spectra against the 2016
  EXO-20-008 spectra (double b and single/inclusive single b). Use the common
  mass range above both thresholds, rebin to common bins, normalise, and
  compute χ²/ndf and the slope of the ratio vs m_jj.
- D3 (absolute): the student's dσ/dm = N / (L Δm) against EXO-20-008. Give
  the ratio, and say whether jets, tagger, η and Δη cuts and luminosity
  explain it.
- D4 (trend): the student's Z′→bb̄ selection efficiency vs mass (from
  `summary.json`) against EXO-20-008 Figure 2. Compare the shape vs mass;
  explain any offset by selection differences.
- D5 (shape, if feasible within memory): the inclusive m_jj spectrum (rebuilt
  from the skims) against EXO-16-056. If you skip it, say why.

**Dimuon**

- M1 (exact): J/ψ, ψ(2S), Υ(1S,2S,3S) and Z peak positions and widths from
  fits to the student's histograms, against PDG values. Quote the mass-scale
  offset in per mille and the resolution, and say whether they are what is
  expected without muon momentum corrections.
- M2 (ratio): Υ(2S)/Υ(1S) and Υ(3S)/Υ(1S) yield ratios (from fits with a
  continuum background) against the ratios implied by BPH-15-005, in a
  comparable pT and |y| range. State the trigger and acceptance differences.
- M3 (shape): the dimuon pT and |y| distributions in the Z window against
  the normalised SMP-17-010 distributions, using the covariance where
  given. These are detector-level vs unfolded distributions: quantify the
  difference and say which part acceptance and resolution explain.
- M4 (shape): the dimuon mass shape around the Z against SMP-17-001
  Table 5, after rerunning the student code on the same 2 files with the
  SMP-17-001 fiducial selection (read it from the paper or record). Keep the
  original student histograms unchanged.

### Deliverables in `validation/dijet-2016/cms-comparison/`

- `COMPARISON.md`: the comparability matrix, one section per test (plot,
  numbers, verdict, explanation), and a summary table of all verdicts at the top
- `comparison.json`: per test `{id, student_result, counterpart (report
number, INSPIRE, HEPData table), level, statistic, ndf, p_value or
ratio, verdict, reason}`
- `plots/`: one comparison plot per test (student vs CMS, ratio panel), PNG + PDF,
  labelled "CMS Open Data" for the student and with the CMS paper cited
- the code that reproduces every number (`compare_*.py`), rerunnable with
  the cache directory as an argument
- `SKILLS_USED.md`: which skills you used, and above all what you had to
  work out yourself to find records, download and read HEPData tables, match
  binnings and units, and choose the tests. Quote the exact URLs and YAML
  structures that worked. This becomes the `cms-results-comparison` skill.

Rules: never change the student's numbers to improve agreement; never call
something consistent without a test statistic; never digitise; no git
commits; no personal paths, usernames or `/uscms_data` in any file under
`validation/` (write `$USER` or relative paths); do not copy HEPData records
into the repository (the cache stays in scratch). Finish with a short report:
the verdict table, the three most important disagreements and their likely
causes, and the commands to reproduce.
