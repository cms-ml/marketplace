# Validation task: nanoaod-skimming

Headless command used (from the repository root):

```bash
claude -p "$(cat validation/nanoaod-skimming/PROMPT.md)" --plugin-dir plugins/cms --model haiku
```

In both runs the task was given to the `cms-analysis-coder` agent (model: haiku) from a supervising session.
Run 2 (cms 0.6.0) added the cutflow: steps 1, 4, 5 and 6 below ask for it.

## Task

Use the `cms:nanoaod-skimming` skill (load it with the Skill tool first and follow it). Use its
scripts from `plugins/cms/skills/nanoaod-skimming/scripts/`. Do not write your own skimmer.
Work in `validation/nanoaod-skimming/`. Environment:
`source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh` (run `set +u` first).
Write skims (ROOT files) to `$SKIMDIR=/uscms_data/d3/$USER/skims/nanoaod-skimming-validation`, never into the repository.

Inputs (CMS Open Data, 2016 UL NanoAODv9, complete files only, no `--max-events`):

Data, SingleMuon Run2016G:

```text
root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/130000/0A4230E2-0C75-604D-890F-A4CE5E5C164E.root
root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/130000/A3279183-BDA6-F44C-8EF3-C063BC598B68.root
root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/130000/C760C7A6-E4AB-E447-93BB-1EAD0177DB41.root
```

MC, DYJetsToLL_M-50 amcatnloFXFX (cross section 6077.22 pb, NNLO, use as given):

```text
root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/30000/6C3CD8A5-A288-724E-BF9F-BAAC46A4C139.root
root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/30000/18DA8B20-842D-0741-BAFB-1A1C7C522921.root
root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/30000/A2058F3B-C2A2-4E43-B963-6C5A4DC8084B.root
```

Golden JSON: https://opendata.cern.ch/record/14220/files/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt
Lumi by LS: root://eospublic.cern.ch//eos/opendata/cms/luminosity/2016/pp_2016lumibyls.csv

Steps:

1. Skim each input file separately (one output per input, as a batch job would), same keep list and cut for
   data and MC. Keep muons, `HLT_IsoMu24`, `HLT_IsoTkMu24`, `PV_npvs`, MET, and for MC `Pileup_nTrueInt` and
   `LHEScaleWeight`. Preselection, as two named steps in this order: `trigger` (`HLT_IsoMu24 | HLT_IsoTkMu24`)
   and `two_muons` (at least two muons with pT > 20 GeV).
   Apply the golden JSON to data. Save each script's stdout as `logs/<name>.log`.
2. Merge the data skims and the MC skims with `hadd` (one data file, one MC file).
3. Bookkeeping: `sumw.py` on the original MC files and on the merged MC skim (must agree), `lumi.py` on the
   merged data skim, and `lumi.py --golden` for the whole year as a cross-check.
4. Physics check: in both merged skims select events with two opposite-charge tight-ID muons
   (pT > 26 and > 20 GeV, |eta| < 2.4, `Muon_pfRelIso04_all < 0.15`) and count events with `81 < m_mumu < 101` GeV.
   Normalise MC with `genWeight * xsec * lumi / SUMW`. No scale factors or pileup weights.
   Plot `m_mumu` (60-120 GeV) data vs MC with a ratio panel to `plots/mmumu.png` and `.pdf`
   (use the `cms:hist` skill; label "CMS Open Data").
   Cutflow: get the skim part of the cutflow from the skims' Cutflow trees with the skill's `cutflow.py`, both on
   the per-file skims and on the merged skims (the two must agree, and the last skim step must equal the merged
   Events entries). Then continue it on the merged skims with these analysis steps, in this order:
   `muon_pt` (pT > 20 GeV), `muon_eta` (|eta| < 2.4), `muon_tight_id`, `muon_iso` (`pfRelIso04_all < 0.15`)
   (these four define the selected muons), `exactly_two` (exactly two selected muons), `opposite_charge`,
   `leading_pt` (leading selected muon pT > 26 GeV), `z_window` (81 < m_mumu < 101 GeV). For each step give
   the sequential count and the N-1 count (all other analysis steps applied, this one not; for a muon-level step,
   the muons are selected without that requirement), for data in events and for MC in normalised events
   (`genWeight * xsec * lumi / SUMW`; the skim steps too). The last sequential count must equal the
   `z_peak` numbers. Plot the sequential cutflow, data vs normalised MC with a data/MC ratio panel, to
   `plots/cutflow.png` and `.pdf`.
5. Write `summary.json` with exactly these keys (numbers, not strings):

```json
{
  "data": {
    "n_files": 0,
    "events_in": 0,
    "events_after_lumimask": 0,
    "events_out": 0,
    "merged_entries": 0,
    "n_ls": 0,
    "lumi_pb": 0.0,
    "input_bytes": 0,
    "skim_bytes": 0
  },
  "mc": {
    "n_files": 0,
    "events_in": 0,
    "events_out": 0,
    "merged_entries": 0,
    "sumw_runs_original": 0.0,
    "sumw_runs_merged_skim": 0.0,
    "sumw_read": 0.0,
    "neg_weight_fraction": 0.0,
    "xsec_pb": 6077.22,
    "weight_factor": 0.0,
    "input_bytes": 0,
    "skim_bytes": 0
  },
  "golden_2016_lumi_fb": 0.0,
  "z_peak": {
    "data_events": 0,
    "mc_events_normalised": 0.0,
    "mc_stat_unc": 0.0,
    "data_over_mc": 0.0
  },
  "cutflow": {
    "steps": [
      "all",
      "lumimask",
      "trigger",
      "two_muons",
      "muon_pt",
      "muon_eta",
      "muon_tight_id",
      "muon_iso",
      "exactly_two",
      "opposite_charge",
      "leading_pt",
      "z_window"
    ],
    "skim_steps": ["trigger", "two_muons"],
    "data": { "sequential": [0], "nminus1": [null, null, 0] },
    "mc_normalised": { "sequential": [0.0], "nminus1": [null, null, 0.0] },
    "skim_per_file_equals_merged": true
  }
}
```

In `cutflow`, `sequential` and `nminus1` are lists in the order of `steps` (one number per step);
`nminus1` is `null` for `all` and `lumimask`. The N-1 of a skim step comes from the Cutflow tree, so it is
N-1 within the skim steps only.

`neg_weight_fraction` is the fraction of MC events in the skims with genWeight < 0. 6. Put the re-runnable commands in `run_all.sh` (relative paths, `$USER`, no usernames) and the analysis code
for step 4 in `zpeak.py`. 7. Write `SKILLS_USED.md`: which skill guided each step, and everything in the skill that was wrong, unclear or
missing (quote the text). Be specific; this is the main feedback for the skill. In run 2, keep the run 1
notes and add a section for the run.

Do not edit the skill. Do not write `check_results.py` or `README.md`. Report the numbers in `summary.json`
and any problem you hit.
