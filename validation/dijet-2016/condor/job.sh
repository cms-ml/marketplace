#!/bin/bash
# LPC condor worker wrapper, adapted from the lpc-condor skill template (assets/job.sh).
# Args: JOBID INPUTS(comma-separated URLs) OUTDIR(root://cmseos.fnal.gov//store/user/...)
set -eo pipefail
JOBID="$1"; INPUTS="$2"; OUTDIR="$3"
case "$OUTDIR" in root://*) ;; *) echo "OUTDIR must be a root:// URL, got: '$OUTDIR'" >&2; exit 2;; esac
export USER=$(whoami)                       # $USER is empty on LPC workers
echo "job=${JOBID} host=$(hostname) os=$(cat /etc/redhat-release) pwd=$(pwd)"
# LCG setup.sh reads unset variables: never source it under `set -u`.
source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh
export PYTHONNOUSERSITE=1
python3 --version
OUTFILE="output_${JOBID}.${OUT_EXT:-npz}"
python3 skim.py --inputs "$INPUTS" --output "$OUTFILE"
for f in "$OUTFILE"; do
  ok=0
  for attempt in 1 2 3; do
    if xrdcp -f "$f" "${OUTDIR}/${f}"; then ok=1; break; fi
    echo "xrdcp attempt ${attempt} failed for ${f}, retrying in 30 s" >&2; sleep 30
  done
  [ "$ok" = 1 ] || { echo "stage-out failed for ${f}" >&2; exit 3; }
  rm -f "$f"
done
echo "done job=${JOBID}"
