# SKILLS_USED (lpc-condor, agent-test2, user <user>)

Result: full workflow succeeded. Test job cluster 4740442 and main cluster 4740495, both on lpcschedd4.fnal.gov. 4 jobs, 0 resubmissions.
Totals: 160000 events, 21383 HLT_PFHT900, 2987 with >=2 jets pT>500. Per-job exec-to-terminate wall times: 36, 35, 25, 37 s (test job 78 s).

## Steps and guiding skill sections

1. Proxy/quota/EOS dirs: "Canonical Patterns 1". `voms-proxy-info -timeleft` = 181367, `eosquota` ok.
2. Job list: Pattern 2, `make_filelist.py --xrootd-dir ... --files-per-job 2 --max-files 8 -o jobs.txt` -> 8 files, 4 jobs.
3. Wrapper + jdl: Pattern 3. Copied assets/job.sh and job.jdl unchanged except the jdl OUTDIR default and `OUT_EXT=json`. Wrote payload.py following the "Payload contract" (uproot, first 20000 events/file, JSON out).
4. Local wrapper test: Pattern 4 `bash job.sh 0 ...` (with OUT_EXT=json), then one-job condor test with JOBS=/OUTDIR= overrides, then `condor_submit job.jdl`.
5. Monitoring: Pattern 5 (grep job log for 001/005 and return value; condor_q did not list the job on schedd4 while running).
6. Check outputs: Pattern 6 `check_outputs.py --pattern 'output_{jobid}.json'`. Merged totals with a small python script (summary.json).

## Unclear / missing / worked around

1. `eos root://cmseos.fnal.gov mkdir -p` takes ONE path; I passed two (out and test) and only `out` was created. Skill shows one path in the example but nothing says to make the `test/` dir (the task did). Worked around: second mkdir.
2. Local test command in Pattern 4 omits `OUT_EXT`. With a JSON payload the first local run wrote `output_0.root` (JSON content) to test/. I had to set `OUT_EXT=json bash job.sh ...` and remove the wrong file. The JDL's `environment` is not seen by the local run.
3. `check_outputs.py` example uses `--min-bytes 1000`, which flagged all four valid 602-byte JSON outputs as too_small (exit 2, wrote jobs_resubmit.txt). Nothing says to adapt min-bytes to the output type. Re-ran with `--min-bytes 100`.
4. A stale `jobs_resubmit.txt` listing all jobs remains after the successful re-check (the script doesn't remove/overwrite it when everything is ok), which is confusing.
5. No payload.py template/example is provided; only the contract. It was enough, but a minimal skeleton would help.
6. "set the `OUTDIR` default in the `.jdl`" refers to a placeholder `YOUR_USERNAME/YOUR_OUTPUT_AREA` that I replaced with sed; OK but jdl `environment` OUT_EXT edit also needed (documented).
7. `<skill-dir>` placeholder for `$S`: I had to know the path from the task; the skill says "shown when the skill loads" but I read SKILL.md directly.
8. `condor_q` (no args) showed only my unrelated job on schedd5 while the test job ran on schedd4 and showed nothing for it; job log was the reliable source (as the skill warns).
9. Worker time (payload 12-26 s) vs. local (~9 s): consistent with the 3-10x warning at smaller scale. Condor queue-to-start latency was 20-25 s.
