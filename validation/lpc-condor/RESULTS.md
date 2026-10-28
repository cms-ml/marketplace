# lpc-condor validation results

The validating agent (Claude Sonnet, no prior context) performed the task in
[PROMPT.md](PROMPT.md) on the LPC condor pool using only the `lpc-condor`
skill. It ran twice: once on the first draft, and again after its findings
were fixed.

| Run           | Skill version | Jobs (test + main)                     | Exit codes | Resubmissions | Totals (160k events)                    | Blocking problems |
| ------------- | ------------- | -------------------------------------- | ---------- | ------------- | --------------------------------------- | ----------------- |
| [run1](run1/) | first draft   | 30979599 (schedd5) + 4739979 (schedd4) | all 0      | 0             | HLT_PFHT900 22493; ≥2 jets pT>500: 3239 | none              |
| [run2](run2/) | final         | 4740442 + 4740495 (schedd4)            | all 0      | 0             | HLT_PFHT900 21383; ≥2 jets pT>500: 2987 | none              |

The totals differ because `--max-files` changed between runs (it now takes
the first N files in sorted order), so the runs used different files.

## Fixed after run1

- Documented the payload contract (`--inputs`, `--output`, `OUT_EXT`).
- Added the cluster ID to log names, so test logs are not overwritten.
- The one-job test now has its own job list and output folder via command-line overrides.
- `--max-files` is now deterministic.
- Doc fixes: `condor_q -name`, the order of `condor_submit` output, workers 3–10× slower than local runs, `-dry-run | grep`.

## Found while re-testing those fixes

- `$(VAR:default)` in a `.jdl` is not expanded when the default contains `-`.
  Jobs then return 0 but write no output to EOS. The template now uses
  `if !defined … endif`, and the wrapper rejects any `OUTDIR` that is not
  `root://`. This was verified on real jobs.

## Fixed after run2

- `eos mkdir` takes one path per call, and the skill now says to create `test/`.
- Local runs need `OUT_EXT` passed explicitly.
- `--min-bytes` must be chosen per output type.
- `check_outputs.py` removes a stale resubmit list once all jobs pass.
- Added a tested `assets/payload.py` skeleton.

## Not exercised

- `+DesiredOS` containers
- `ENV_MODE=cmssw` tarball mode
- `make_filelist.py --das`
- held-job recovery

These are candidates for the next validation run.
