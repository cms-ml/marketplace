# Validation task for the `lpc-condor` skill

A fresh agent, with no other context, performs this task using only the
`lpc-condor` skill. Its notes (`SKILLS_USED.md`) and results (`summary.json`)
are committed next to this file as evidence that the skill works as written.

## Task

Using only the `lpc-condor` skill
(`plugins/af-fnal-lpc/skills/lpc-condor/`: SKILL.md, its scripts, assets and
references), run a small batch analysis on the CMS LPC condor pool:

- **Input:** the first 8 ROOT files of 2016G JetHT NanoAOD Open Data,
  `root://eospublic.cern.ch//eos/opendata/cms/Run2016G/JetHT/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1`,
  2 files per job, so 4 jobs.
- **Payload:** for each file, read the first 20,000 events and count those
  with `HLT_PFHT900` fired and those with at least two jets with pT > 500 GeV.
  Write the counts per job to a small ROOT or JSON file.
- **Output:** `root://cmseos.fnal.gov//store/user/<username>/cms-marketplace-tests/lpc-condor/agent-test/`.
- Follow the skill's workflow: proxy and quota check, job list, local wrapper
  test, one-job test, full submission, monitoring, output check (resubmit if
  needed), then merge the per-job counts into totals.

**Limits:** at most 4 jobs plus one test job and resubmissions of failures.
Do not touch any other condor jobs. Work in a fresh directory.

**Deliverables:**

- `summary.json`: job count, cluster IDs and schedds, per-job and total
  counts, wall time per job, number of resubmissions.
- `SKILLS_USED.md`: every step and the part of the skill that guided it.
  List explicitly anything that was unclear, missing, wrong, or that you had
  to work around.
