---
name: lpc-condor
description: >-
  Use when running analysis jobs on the CMS LPC batch system at Fermilab
  (cmslpc, HTCondor): splitting a dataset or Open Data file list into jobs,
  writing the condor submit file (.jdl) and worker wrapper script, setting
  up Python or CMSSW on worker nodes, reading inputs over XRootD and writing
  outputs to EOS (root://cmseos.fnal.gov), submitting, monitoring, finding
  failed or held jobs and resubmitting them, or debugging errors such as
  jobs exiting immediately, "unbound variable", empty $USER, missing
  output, GSI/proxy authentication failures, or files not found on the
  worker.
metadata:
  summary: HTCondor batch jobs on cmslpc with XRootD in, EOS out, check and resubmit (tested on real jobs)
---

# LPC condor

## Overview

The LPC HTCondor pool runs your jobs on Fermilab worker nodes inside an
**Alma9 Apptainer container**. The job's scratch directory is mounted at
`/srv`, and the container sees `/cvmfs` but **not** NFS (`/uscms_data`,
nobackup, home) and not the EOS FUSE mount. So:

- **Inputs:** read over XRootD (`root://...`), or ship small files with the job (< 1 GB total).
- **Software:** take it from CVMFS (an LCG view or a CMSSW release), or ship a tarball via EOS.
- **Outputs:** copy to EOS with `xrdcp` to `root://cmseos.fnal.gov//store/user/<you>/...`.

The workflow is: build `jobs.txt` → test the wrapper locally → submit **one**
job → submit everything → check outputs → resubmit the failures.

## When to Use

- Running a NanoAOD/uproot/coffea analysis over many files (e.g. all 2016 JetHT)
- Writing or fixing a `.jdl` and its `job.sh` wrapper
- Jobs that fail, hold or produce no output; resubmitting a subset
- Choosing the job environment (LCG view vs CMSSW tarball) and the OS container

## Key Concepts

| Item             | Fact (checked on cmslpc, 2026-10)                                                                                                                                                 |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Submit host      | An EL9 `cmslpc` node. The `condor_submit` wrapper picks a schedd: `lpcschedd3/4/5.fnal.gov`                                                                                       |
| Proxy            | `voms-proxy-init --valid 192:00 -voms cms`. Picked up automatically; no `x509userproxy` line                                                                                      |
| Worker container | `cms:rhel9` Apptainer (Alma9). Select another with `+DesiredOS = "SL7"` (or `EL8`, `EL9`)                                                                                         |
| Scratch          | `$_CONDOR_SCRATCH_DIR` = `/srv`, about 40 GB disk per job                                                                                                                         |
| Python stack     | `/cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt`: Python 3.13, uproot 5.6, awkward 2.8, hist, iminuit 2.31, vector, mplhep, XRootD, fsspec-xrootd, coffea, hepdata_lib |
| Job index        | `queue jobid,inputs from jobs.txt`. A fixed index survives resubmission (unlike `$(Process)`)                                                                                     |

## Canonical Patterns

### 1. Check proxy and EOS space

```bash
voms-proxy-info -timeleft            # > 0, else voms-proxy-init --valid 192:00 -voms cms
eosquota                             # outputs count against your EOS user quota
eos root://cmseos.fnal.gov mkdir -p /store/user/$USER/myanalysis/out    # one path per call
eos root://cmseos.fnal.gov mkdir -p /store/user/$USER/myanalysis/test   # for the one-job test (step 4)
```

### 2. Build the job list

[scripts/make_filelist.py](scripts/make_filelist.py) recurses an XRootD
directory (Open Data, EOS) or a DAS dataset, and writes
`<index> <url1,url2,...>` lines:

```bash
S=<skill-dir>/scripts      # <skill-dir> = the directory holding this SKILL.md
                           # (in the cms-ml/marketplace repo: plugins/af-fnal-lpc/skills/lpc-condor)
$S/make_filelist.py --xrootd-dir root://eospublic.cern.ch//eos/opendata/cms/Run2016H/JetHT/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1 \
                    --files-per-job 5 -o jobs.txt            # 72 files -> 15 jobs
$S/make_filelist.py --das /JetHT/Run2016H-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD -o jobs.txt   # needs proxy
```

`--max-files N` takes the first N files in sorted path order (for test runs).
Choose `--files-per-job` from the **one-job condor test** (step 4), not the
local run: in validation, workers took 3–10× longer than the same work run
locally (cold CVMFS/XRootD). Aim for 30 min to a few hours per job.

### 3. Wrapper and submit file

Copy [assets/job.sh](assets/job.sh), [assets/job.jdl](assets/job.jdl) and, as a
starting point, [assets/payload.py](assets/payload.py) into your job directory.
Then set the `OUTDIR` default in the `.jdl`. The snippet below shows only the
key lines; the asset is the complete file.

**Payload contract:** `job.sh` runs
`python3 payload.py --inputs <comma-separated root:// URLs> --output output_<jobid>.<OUT_EXT>`.
Your payload must accept those two options and write exactly that one file.
`OUT_EXT` is `root` by default; change it in the `.jdl` `environment` line
(e.g. `OUT_EXT=json`). `check_outputs.py --pattern` must use the same name. To
run something other than `payload.py`, edit that one line in `job.sh`.

The wrapper:

- sets `USER`
- loads the environment (`ENV_MODE=lcg` by default, or `cmssw` with a tarball from EOS)
- runs the payload
- `xrdcp`s each output with 3 retries, removes the local copy, and exits non-zero on failure

```text
executable            = job.sh
transfer_input_files  = payload.py
if !defined JOBS                                  # defaults, overridable on the command line
  JOBS = jobs.txt
endif
if !defined OUTDIR
  OUTDIR = root://cmseos.fnal.gov//store/user/<you>/<area>
endif
arguments = "$(jobid) $(inputs) $(OUTDIR)"
output = logs/job_$(Cluster)_$(jobid).out       # cluster in the name: test logs aren't overwritten
log    = logs/cluster_$(Cluster).log
queue jobid,inputs from $(JOBS)
```

### 4. Test locally, then one job, then all

```bash
OUT_EXT=root bash job.sh 0 "$(head -1 jobs.txt | cut -d' ' -f2)" root://cmseos.fnal.gov//store/user/$USER/myanalysis/test
# local runs don't read the .jdl `environment` line: pass the same OUT_EXT (and ENV_MODE) yourself
head -1 jobs.txt > jobs_one.txt
mkdir -p logs
condor_submit JOBS=jobs_one.txt OUTDIR=root://cmseos.fnal.gov//store/user/$USER/myanalysis/test job.jdl  # 1 job, separate output
condor_submit job.jdl                                                                                    # then everything
```

### 5. Monitor

```bash
condor_q                               # your jobs, but may lag ~1 min or miss a schedd: trust the job log
condor_q -name lpcschedd4.fnal.gov <cluster>            # ask the schedd that has the job directly
condor_q -hold                         # held jobs and the reason
grep -E '^(005|012)' logs/cluster_*.log                 # terminated / held events
grep -A2 '^005' logs/cluster_*.log | grep 'return value' # exit codes
condor_tail -name lpcschedd4.fnal.gov <cluster>.<proc>  # live stdout; needs the schedd
condor_rm   -name lpcschedd4.fnal.gov <cluster>         # remove; needs the schedd
```

`condor_submit` prints the cluster ("N job(s) submitted to cluster X") and
the schedd it used ("Attempting to submit jobs to lpcschedd4.fnal.gov"). The
cluster line can appear _before_ the schedd line. Record both, because `rm`,
`tail`, `hold` and `release` need `-name`.

### 6. Check outputs and resubmit failures

[scripts/check_outputs.py](scripts/check_outputs.py) lists the EOS area and
writes the lines of missing or too-small jobs to a resubmit file. The index is
kept, so outputs land under the same names:

```bash
$S/check_outputs.py --jobs jobs.txt --outdir root://cmseos.fnal.gov//store/user/$USER/myanalysis/out \
                    --pattern 'output_{jobid}.root' --min-bytes 1000   # pick for your output type (small JSON: ~100)
# exit 2 -> jobs_resubmit.txt written; set `queue jobid,inputs from jobs_resubmit.txt` and resubmit
```

Then merge the outputs: `hadd` from CMSSW/ROOT, or sum histograms in Python
reading `root://cmseos.fnal.gov//...` directly.

## Gotchas

- **`set -u` breaks the LCG setup.** Sourcing the LCG view under `set -u`
  fails with `setup.sh: line 18: COMPILER: unbound variable`, so the job
  exits within seconds with return value 1. Use `set -eo pipefail`, or
  `set +u` around the `source`.
- **`$(VAR:default)` silently breaks on hyphens.** In a `.jdl`,
  `OUTDIR = $(OUTDIR:root://.../cms-tests)` is passed to the job as the
  literal unexpanded text whenever the default contains `-`. Then `xrdcp` writes
  to a local file and the job still "succeeds" with no output on EOS (seen in
  validation). Use `if !defined OUTDIR … endif` as in the template. The template
  wrapper also refuses any `OUTDIR` that isn't `root://` (exit 2).
- **No NFS on workers.** Files under nobackup or home are invisible to the
  job. Ship small inputs with `transfer_input_files` (< 1 GB) and put large
  ones on EOS.
- **No EOS FUSE in jobs.** Use `xrdcp` and `root://cmseos.fnal.gov//store/...`,
  never `/eos/uscms/...` paths.
- **`$USER` is empty on workers.** The wrapper exports it.
- **Don't add `getenv = true`** or a hard-coded `x509userproxy`. Set the
  environment inside the wrapper, and let LPC handle the proxy.
- **The first line of `job.sh` must be `#!/bin/bash`**, with nothing before it.
- **`-name` is required** for `condor_rm/tail/hold/release` on the
  refactored pool. Cluster IDs differ between schedds (we saw 4739665,
  86238726 and 30979433 from different schedds).
- **Leftover outputs come back to your submit directory** at job end. Remove
  big files in the wrapper after the copy succeeds, or they fill NFS.
- **Don't submit from `/eos`.** Submit from an NFS directory (nobackup is
  fine). Logs are written there.
- **Open Data directories contain `file-indexes/`** (non-ROOT text files).
  `make_filelist.py` only takes `*.root`.
- **Don't trust `condor_q` alone.** It can lag; the job log
  (`logs/cluster_*.log`) is authoritative for submit, start and termination.
- **CMSSW's Python is old for fitting** (CMSSW_15_0_21 has iminuit 1.2), so
  prefer the LCG view for pure-Python analysis.

## Reference Files

- [assets/payload.py](assets/payload.py): copy and edit for a new analysis.
  It's a minimal payload that follows the `job.sh` contract and writes a ROOT
  histogram.
- [references/troubleshooting.md](references/troubleshooting.md): read when
  a job is held, exits non-zero, or produces no output. It covers exit-code
  and hold-reason lookup, `-debugfile`, proxy and DN registration, EOS stage-out
  failures, and LPC support contacts.

## Docs

- LPC batch systems: <https://uscms.org/uscms_at_work/computing/setup/batch_systems.shtml>
- LPC condor refactor (schedds, proxy, `-name`): <https://uscms.org/uscms_at_work/computing/setup/condor_refactor.shtml>
- EOS at the LPC: <https://uscms.org/uscms_at_work/computing/LPC/usingEOSAtLPC.shtml>
- HTCondor submit description: <https://htcondor.readthedocs.io/en/latest/man-pages/condor_submit.html>
- LPC job monitor: <https://landscape.fnal.gov/lpc/>
