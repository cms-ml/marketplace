# SKILLS_USED: lpc-condor validation (user <user>)

Result: full workflow succeeded. 4 jobs (cluster 4739979, lpcschedd4) + 1 test job (cluster 30979599, lpcschedd5), 0 resubmissions, all exit codes 0.
Totals over 8 files x 20000 events: 160000 events, HLT_PFHT900 fired 22493, >=2 jets pT>500 GeV 3239.

## Steps and the part of the skill that guided each

1. Read SKILL.md, assets/job.sh, assets/job.jdl, both scripts, references/troubleshooting.md.
2. Proxy/quota/EOS dir: "Canonical Patterns 1" (`voms-proxy-info -timeleft`, `eosquota`, `eos ... mkdir -p`). Worked as written.
3. Job list: Pattern 2, `make_filelist.py --xrootd-dir <2016G url> --files-per-job 2 --max-files 8 -o jobs.txt` -> {"files": 8, "jobs": 4}. `--max-files` is in the script's docstring, not in SKILL.md.
4. Wrapper/JDL: Pattern 3. Copied assets/job.sh and job.jdl, wrote payload.py (uproot + awkward from the LCG view, JSON output), edited the OUTFILE line in job.sh (.root -> .json) and OUTDIR in job.jdl.
5. Local test: Pattern 4 `bash job.sh 0 "$(head -1 jobs.txt | cut -d' ' -f2)" <EOS test dir>`. Worked on cmslpc, 13 s, output staged to EOS.
6. One-job test: Pattern 4 (`head -1 jobs.txt > jobs_one.txt`, then job_one.jdl made by sed from job.jdl with `queue ... from jobs_one.txt` and OUTDIR=.../test). Cluster 30979599 on lpcschedd5, return 0, TimeExecute 112 s.
7. Full submit: `condor_submit job.jdl`, cluster 4739979 on lpcschedd4, 4 jobs.
8. Monitor: used the job log (`grep -E '^(001|005|012)'`, `return value`) as recommended in Gotchas ("Don't trust condor_q alone"). Also used `condor_q` (showed only my unrelated job on lpcschedd5, not the new cluster on lpcschedd4, immediately after submission).
9. Output check: `check_outputs.py --pattern 'output_{jobid}.json' --min-bytes 100` -> 4/4 OK, exit 0. Also self-tested the failure path with `--min-bytes 565` (all flagged too_small, exit 2, resubmit file written with unchanged lines); no real resubmission was needed.
10. Merge: summed the per-job JSON files in Python (results/output\_\*.json fetched with xrdcp).
11. `condor_submit -dry-run - job.jdl` from troubleshooting.md worked and printed job ClassAds (not just arguments; see below).

## Unclear / missing / wrong / work-arounds

1. job.sh hard-codes `OUTFILE="output_${JOBID}.root"` and the stage-out loop; a JSON-output payload requires editing it (I used sed). SKILL.md says only "Edit the payload line in job.sh", but the payload section is three things (OUTFILE name, the python3 call, and the `for f in "$OUTFILE"` loop). Also `--output` is an invented payload CLI (`payload.py --inputs --output`), which SKILL.md does not document; a user must read job.sh to learn the payload contract. Suggest documenting it in SKILL.md.
2. The one-job test and the full run both use `logs/job_$(jobid).out/err`, so `logs/job_0.*` from the test was overwritten by the full run's job 0. The test cluster log survives (`cluster_<Cluster>.log`). Suggest a separate log dir or a note.
3. The one-job test also writes to the same OUTDIR as the real run unless the JDL is edited; SKILL.md Pattern 4 only says "point `queue ... from` at it". I made a second jdl with a different OUTDIR (.../test). Suggest saying so (or passing OUTDIR via `condor_submit -append`).
4. "first N files": `make_filelist.py --max-files 8` returns the first 8 files found in directory-traversal order and then sorts them, so you get 1 file from 130000/ and 7 from 260000/. This is deterministic but not necessarily "the first 8" by sorted full path; in `list_xrootd` the early return happens during traversal. Not documented in SKILL.md; `--max-files` itself is not in SKILL.md at all (only in the script docstring and `make_filelist.py ... --max-files 10` example).
5. condor_submit output order: it prints "1 job(s) submitted to cluster N." BEFORE "Attempting to submit jobs to lpcscheddX", which is confusing when reading. Skill says to record the schedd from the "Attempting to submit" line; that works, but the cluster-then-schedd order is worth a remark. Also the cluster ID alone doesn't identify the schedd; cluster 30979599 vs 4739979 differ by schedd, consistent with the skill's note.
6. `condor_q` right after submission showed only my older unrelated job on lpcschedd5 and not the new cluster on lpcschedd4 (skill says "all schedds, can lag ~1 min"). The skill's advice to use the job log was what I relied on. Minor: suggest `condor_q -name lpcschedd4.fnal.gov <cluster>` as an explicit alternative.
7. `condor_submit -dry-run - job.jdl` prints full job ClassAds (ClusterId=1, Cmd=..., Err=...) rather than just "each job's arguments"; the troubleshooting text slightly understates it (works, just verbose; `| grep -E '^(Arguments|Args)'` would be needed).
8. Wall time: job 0 took 126 s while jobs 1-3 took 33-44 s and the test job 112 s, with the same payload; first-touch CVMFS/XRootD latency probably. The skill's "~1 minute each" expectation is fine but not guaranteed. Skill says to choose --files-per-job from a timed local test: my local test took 13 s for 2 files at 20k events, while condor wall time was 33-126 s, so local timing underestimates the on-worker time by 3-10x (no guidance in skill about the overhead).
9. Pattern 1's `eosquota` output is fine; `eos root://cmseos.fnal.gov mkdir -p` printed nothing on success; fine.
10. The jdl says `+DesiredOS = "SL7"` in a comment and the Key Concepts table lists EL8/EL9 values; not exercised.
11. Skill header examples use `S=<skill-dir>/scripts` but never state how to find `<skill-dir>` when installed as a plugin; I used the absolute path I was given.
12. I removed my temporary `resubmit_selftest.txt` after the failure-path self-test (not part of the deliverables).

Nothing in the skill was wrong to the point of failing: no command in it errored. All problems above are documentation gaps or ergonomics.
