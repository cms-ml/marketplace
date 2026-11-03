# Task for the cms-analysis-coder agent: muon scale factors with tag and probe

This validates the `muon-tag-and-probe` skill. The agent measures the muon
tight-ID, tight-isolation and IsoMu24 trigger efficiencies and data/MC scale
factors on Z → μμ in the full 2016G+H CMS Open Data, and compares them bin
by bin with the official Muon POG scale factors (correctionlib JSON on
cvmfs), which are the CMS counterpart.

## How to run

From the repository root on cmslpc, on branch `feat/muon-tag-and-probe`,
inside `tmux` (it needs a valid grid proxy for Condor and XRootD):

```bash
tmux new -s tnp
voms-proxy-init -voms cms -valid 192:00
sed -n '/^## Task/,$p' validation/muon-tnp/PROMPT.md | \
  claude -p --agent cms:cms-analysis-coder \
    --plugin-dir plugins/cms --plugin-dir plugins/af-fnal-lpc --plugin-dir plugins/hep-python-tools \
    --permission-mode acceptEdits --allowedTools "Bash Read Write Edit Glob Grep Skill TodoWrite" \
    > validation/muon-tnp/agent_report.md 2>&1
```

Or, in a Claude Code chat opened on this repository: "Use the
cms-analysis-coder agent to do the task in `validation/muon-tnp/PROMPT.md`
(everything from '## Task' on)."

Check progress with `ls -lt validation/muon-tnp/` and `condor_q`.

## Task

Measure muon efficiencies and data/MC scale factors with tag and probe on
Z → μμ in the 2016G+H CMS Open Data, and compare them with the official Muon
POG scale factors. Use the **`muon-tag-and-probe` skill** (load it first and
follow it, including `scripts/tnp.py` where it fits), and `lpc-condor`,
`awkward-array`, `vector-awkward` and `hist` for the steps they cover. Work
in `validation/muon-tnp/` (create it). Do not modify any skill or other
validation.

Start by writing `specification.md` with the analysis-spec-builder skill.

### Environment

- Python: `set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh`
  (uproot, awkward, vector, hist, mplhep, iminuit, correctionlib).
- Run long commands with `/usr/bin/time -v ... > log 2>&1; echo EXIT $? >> log`.
  The interactive node has about 6 GB of free memory: run the pair selection
  on Condor and write its outputs to EOS or a scratch area outside the
  repository (`<scratch>` below), never into `validation/`.
- `validation/dijet-2016/` is a worked example of the Open Data workflow
  (golden JSON, luminosity, Condor skims).

### Inputs

- Data: `/eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/`
  and the Run2016H counterpart, all files; golden JSON (Open Data record
  14220). Report the luminosity of the processed, certified lumi sections
  from `pp_2016lumibyls.csv` (record 1059).
- MC: `ZToMuMu_M-50To120_TuneCP5_13TeV-powheg-pythia8` in
  `RunIISummer20UL16NanoAODv9` (postVFP, matching G+H), enough files that
  the MC has at least as many tag-probe pairs as the data (see the skill's
  MC-statistics gotcha).
- Counterpart: `/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/MUO/2016postVFP_UL/muon_Z.json.gz`.
  It covers 2016F (late), G and H; say what that means for a G+H-only
  comparison.

### Measurements

For each of `NUM_TightID_DEN_TrackerMuons`,
`NUM_TightRelIso_DEN_TightIDandIPCut` and
`NUM_IsoMu24_or_IsoTkMu24_DEN_CutBasedIdTight_and_PFIsoTight`, in the POG
|η| × pT bins:

1. ε_data (pass/fail fit), ε_MC, SF, with statistical uncertainties.
2. Systematics, at least: the background shape (exponential vs. another
   function), the mass window (70–115 vs. 75–110 GeV), the tag selection
   (tighter tag pT or isolation). Quote each per bin and the total.
3. Comparison with the POG: pull per bin with the POG `systup − nominal` and
   your total uncertainty; mean and RMS of the pulls per WP; a plot of
   SF_ours / SF_POG per bin.
4. Run dependence: the trigger and isolation SFs for G and for H separately.
5. The trigger filter-bit problem in the skill: measure, on the full data,
   how often a probe matched to an `Iso`/`IsoTkMu` object above 24 GeV sits
   in an event that fired neither path, and estimate how much that biases
   ε_data and the SF. If you find a better NanoAOD-level definition, show it.

### Deliverables in `validation/muon-tnp/`

- `specification.md`
- the code (pair selection, Condor submit and wrapper, fits, systematics,
  comparison, plotting) with relative paths, and a `run_all.sh` that reruns
  everything after the Condor step
- `summary.json`: luminosity, event and pair counts, per WP and bin ε_data,
  ε_MC, SF with stat and syst, POG SF and uncertainty, pull; mean and RMS
  pull per WP; the G vs H results; the filter-bit fraction
- `plots/` (PNG + PDF, "CMS Open Data", luminosity): efficiency vs pT per
  |η| bin (data, MC, ratio panel with the SF and the POG SF), SF_ours /
  SF_POG maps, fit plots for a few representative and the worst bins
- `check_results.py` (stdlib only, reads `summary.json`, exit 0/1/2,
  `SUMMARY=n/n`): efficiencies in [0, 1]; SFs between 0.9 and 1.1; tight-ID
  and isolation RMS pull below 2; no bin with |pull| > 5 that is not
  explained in `summary.json`; trigger SF agreement reported (no threshold);
  no personal paths
- `SKILLS_USED.md`: for each step, what the `muon-tag-and-probe` skill (and
  `tnp.py`) told you, what worked as written, and every place it was wrong,
  unclear or missing (quote it)
- `README.md`: goal, the counterpart, results table (mean/RMS pull per WP,
  SF at 40–50 GeV per |η| bin vs POG), the main skill findings, how to
  reproduce

Rules: no git commits; no personal paths, usernames or absolute home/data
paths in any file under `validation/` (write `$USER`, `<scratch>` or relative
paths); outputs from Condor stay outside the repository; never fabricate
numbers; Open Data results are not CMS results. Finish with a short report:
luminosity, pair counts, mean/RMS pull per WP, the G vs H trigger SFs, the
filter-bit bias, the most important skill gaps, and the commands to
reproduce.
