# Validation: b-tagged dijet resonance search on 2016 CMS Open Data

This validation analysis accompanies the first "Example PR". It exercises the
`cms-analysis-coder` agent and the `trigger-efficiency` and `hepdata` skills
end to end, together with `analysis-spec-builder`, `awkward-array`,
`vector-awkward`, `hist` and `lpc-condor`. Future PRs follow the same pattern:
add a skill or agent, plus a validation like this one that uses it (see
"Contribution standard" in [CLAUDE.md](../../CLAUDE.md)).

## Reference analysis and credits

The plot set and analysis strategy follow:

- **Aaron Mankel (Texas Tech University)**, "Search for narrow resonances with
  b-tagged high-mass dijet distributions in proton-proton collisions at
  √s = 13.6 TeV", APS lightning talk, 10 March 2026. This is the Run 3
  analysis carried out with the **CMS B2G** team.
- **CMS Collaboration**, "Search for heavy resonances decaying to b quarks in
  proton-proton collisions at √s = 13 TeV", CMS-EXO-20-008 (138 fb⁻¹ Run 2),
  INSPIRE 1920627, with its HEPData record.

This is an **Open Data reproduction for validating tools**. It is not a CMS
result and makes no physics claim. Plots are labelled "CMS Open Data".

## Differences from the reference

| Aspect    | Reference (Run 3)                       | This validation (Run 2 Open Data)                                                                          |
| --------- | --------------------------------------- | ---------------------------------------------------------------------------------------------------------- |
| Data      | 2024–25, 13.6 TeV                       | 2016G+H JetHT NanoAODv9, 13 TeV, 16.4 fb⁻¹                                                                 |
| b tagging | UParT                                   | DeepJet (`Jet_btagDeepFlavB`), 2016postVFP_UL WPs from the BTV POG JSON                                    |
| Signals   | b\* → bg (≥1 b tag), Z′ → bb̄ (2 b tags) | Z′ → bb̄ (`ZprimeToBB_narrow`) for both categories. No b\* → bg sample exists in Open Data (only b\* → tW). |
| Jets      | AK4 PUPPI                               | AK4 CHS (`Jet_*` in NanoAODv9)                                                                             |
| Threshold | m_jj > 1455 GeV                         | m_jj > 1058 GeV, from the measured trigger turn-on                                                         |

## Results (all 142 data files)

| Quantity                       | Value                                                    |
| ------------------------------ | -------------------------------------------------------- |
| Trigger plateau (HLT_PFJet260) | 0.99928 (+0.00012 −0.00015) above m_jj = 1058 GeV        |
| Events ≥1 b tag / 2 b tags     | 878 757 / 72 688                                         |
| Background fit, ≥1 b tag       | 3 parameters, χ²/ndf = 0.95                              |
| Background fit, 2 b tags       | 4 parameters, χ²/ndf = 0.83                              |
| Z′ (2 TeV) injection, 200 toys | mean bias +1.5% (1b), −1.5% (2b); pull mean within ±0.05 |

`check_results.py` runs 29 physics checks on `summary.json`. CI runs it.

## How it was made

1. The agent ran [PROMPT.md](PROMPT.md) **before** the `trigger-efficiency`
   and `hepdata` skills existed. Its notes in
   [SKILLS_USED.md](SKILLS_USED.md) seeded both skills.
2. The skills were written and tested on cmslpc. A second agent run then
   redid the trigger and HEPData steps following the skills. All numbers are
   unchanged. The skill issues it found are at the end of `SKILLS_USED.md` and
   have been fixed in the skills.

## Files

| File                                         | What it is                                                                   |
| -------------------------------------------- | ---------------------------------------------------------------------------- |
| [PROMPT.md](PROMPT.md)                       | The task given to the agent (headless command + Task section)                |
| [specification.md](specification.md)         | Analysis specification written by the agent (analysis-spec-builder)          |
| `skim.py`, `condor/`                         | Condor skim of NanoAOD to `.npz` (lpc-condor templates; 9 jobs, all exit 0)  |
| `analysis.py`, `dijetlib.py`                 | Turn-on, selection, b-tag efficiencies, fits, F-test, injection, plots       |
| `make_hepdata.py`, `hepdata/`                | HEPData record (hepdata skill template); `hepdata_validation.txt` is the log |
| `plots/`                                     | The 7 plot types of the APS talk, PNG + PDF                                  |
| `summary.json`, `input_files.json`           | Key numbers; exact input files and event counts per sample                   |
| `hlt_paths_2016G.txt`, `hlt_paths_2016H.txt` | HLT menu seen in one file per era (`list_hlt_paths.py`)                      |
| `SKILLS_USED.md`                             | Which skill guided each step, and what was wrong or missing                  |
| `check_results.py`                           | Physics checks on the outputs (stdlib only; exit 0 = all pass)               |

## Reproduce

Skims (about 2.5 GB) are not committed. Rebuild them with `condor/` (see
`condor/job.jdl`), writing to `/store/user/$USER/...`, then copy them to a
scratch area:

```bash
source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh
cd validation/dijet-2016
python3 analysis.py --skims '<scratch>/skims/*.npz' --outdir . --work <scratch>/cache --toys 200   # ~3.5 GB RSS, 2-3 min
python3 check_results.py .                                                                           # SUMMARY=29/29
```
