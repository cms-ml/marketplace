# Troubleshooting LPC condor jobs

Read this reference when a job is held, exits with a non-zero code, finishes
but leaves no output on EOS, or `condor_submit` itself fails. Symptoms and
fixes below were either observed in test jobs on the LPC pool (2026-10) or
come from the LPC documentation (linked at the end).

## Contents

1. [Where to look](#where-to-look)
2. [Symptom → cause → fix](#symptom--cause--fix)
3. [Held jobs](#held-jobs)
4. [Submit-time failures](#submit-time-failures)
5. [Getting help](#getting-help)

## Where to look

| What                    | Where                                                                                 |
| ----------------------- | ------------------------------------------------------------------------------------- |
| Did it start or finish? | `logs/cluster_<id>.log`: `001` executing, `005` terminated, `012` held, `009` aborted |
| Exit code               | `grep -A2 '^005' logs/cluster_*.log \| grep 'return value'`                           |
| Wrapper output          | `logs/job_<jobid>.out` (host, OS, environment versions, payload prints)               |
| Errors                  | `logs/job_<jobid>.err`                                                                |
| Container used          | First lines of `.out`: `[FERMIHTC-APPTAINER] ... cms:rhel9`                           |
| Live output             | `condor_tail -name lpcschedd<N>.fnal.gov <cluster>.<proc>`                            |

The job log is updated by the schedd and is the most reliable record.
`condor_q` summaries can lag about a minute.

## Symptom → cause → fix

| Symptom                                                                                     | Likely cause                                                                          | Fix                                                                                                               |
| ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| Ends in seconds, return value 1, `.err` has `setup.sh: line 18: COMPILER: unbound variable` | LCG view sourced under `set -u` (seen in testing)                                     | `set -eo pipefail` (no `-u`), or `set +u` around the `source`                                                     |
| `No such file or directory` for a file under nobackup or home                               | NFS is not mounted in the job container                                               | `transfer_input_files` (< 1 GB) or put it on EOS and `xrdcp` it in                                                |
| `/eos/uscms/...` path not found in the job                                                  | No EOS FUSE mount on workers                                                          | Use `root://cmseos.fnal.gov//store/user/...` with `xrdcp`/XRootD                                                  |
| Payload error opening `root://...does-not-exist.root`                                       | Bad or moved input file                                                               | Fix `jobs.txt`; `check_outputs.py` puts the job in the resubmit list                                              |
| Return value 0 but no output on EOS; `.out` shows a literal `$(OUTDIR:...)`                 | `$(VAR:default)` macro with a `-` in the default is not expanded (seen in validation) | Use `if !defined OUTDIR ... endif` (template); check with `condor_submit -dry-run - job.jdl \| grep '^Arguments'` |
| Exit code 2 from the template wrapper, "OUTDIR must be a root:// URL"                       | `OUTDIR` empty or not expanded                                                        | Fix the `.jdl` `OUTDIR` definition, as above                                                                      |
| Exit code 3 from the template wrapper                                                       | `xrdcp` stage-out failed 3 times                                                      | Check EOS quota (`eosquota`), the output directory exists, and the DN is registered                               |
| Job finished OK but the submit directory filled up                                          | Output files left in scratch are transferred back                                     | `rm` outputs after a successful `xrdcp` (the template does)                                                       |
| `$USER` empty, paths like `/store/user//...`                                                | Workers don't set `USER`                                                              | `export USER=$(whoami)` in the wrapper, or hard-code the username                                                 |
| Works locally, fails in the job                                                             | Environment differs (no `getenv`, different OS)                                       | Set up everything inside `job.sh`; test with one job first                                                        |

## Held jobs

```bash
condor_q -hold                                  # reason for each held job
condor_q -hold-codes                            # one example per hold code
condor_release -name lpcschedd<N>.fnal.gov <cluster>   # after fixing the cause
condor_rm      -name lpcschedd<N>.fnal.gov <cluster>   # or remove and resubmit
```

Common reasons: memory above `request_memory` (raise it, e.g. 4000), or
input files missing at submit time (`transfer_input_files` path wrong).

## Submit-time failures

| Error                                                | Fix                                                                                                    |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------ |
| GSI/AUTHENTICATE errors suggesting `grid-proxy-init` | `voms-proxy-init --valid 192:00 -voms cms` on an EL9 cmslpc node                                       |
| Jobs can't authenticate or reach EOS                 | Register your DN in the LPC Service Portal ("CMS Storage Space Request" → "Enable"); takes a few hours |
| Need details for a ticket                            | `condor_submit -debugfile /tmp/$USER_$(date +%F).log job.jdl`                                          |
| Nothing submitted                                    | The `.jdl` has no `queue` line, or `jobs.txt` is empty                                                 |

Preview without submitting: `condor_submit -dry-run - job.jdl | grep '^Arguments'`
shows each job's arguments (the full output is every job's ClassAd). It is the
quickest check of the `queue jobid,inputs from ...` parsing and of command-line
overrides such as `JOBS=jobs_one.txt OUTDIR=...`.

## Getting help

- LPC batch documentation:
  <https://uscms.org/uscms_at_work/computing/setup/batch_systems.shtml> and
  <https://uscms.org/uscms_at_work/computing/setup/condor_refactor.shtml>
- LPC Service Portal tickets and the `lpc-howto` mailing list (linked from
  those pages)
- Pool status: <https://landscape.fnal.gov/lpc/> (can lag ~5 minutes)
