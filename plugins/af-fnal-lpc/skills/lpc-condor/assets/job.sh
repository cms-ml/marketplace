#!/bin/bash
# LPC condor worker wrapper (template). Copy next to your JDL and edit the PAYLOAD section.
# Args: JOBID INPUTS(comma-separated URLs) OUTDIR(root://cmseos.fnal.gov//store/user/...)
# Tested on LPC workers (Alma9 apptainer, scratch mounted at /srv), 2026-10.
set -eo pipefail
JOBID="$1"; INPUTS="$2"; OUTDIR="$3"
case "$OUTDIR" in root://*) ;; *) echo "OUTDIR must be a root:// URL, got: '$OUTDIR'" >&2; exit 2;; esac
export USER=$(whoami)                       # $USER is empty on LPC workers
echo "job=${JOBID} host=$(hostname) os=$(cat /etc/redhat-release) pwd=$(pwd)"

# ---- environment: pick ONE --------------------------------------------------
ENV_MODE="${ENV_MODE:-lcg}"
if [ "$ENV_MODE" = "lcg" ]; then
  # Modern Python stack from CVMFS (uproot, awkward, hist, iminuit 2.x, coffea, hepdata_lib).
  # LCG setup.sh reads unset variables: never source it under `set -u`.
  source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh
elif [ "$ENV_MODE" = "cmssw" ]; then
  # Your compiled CMSSW area, tarred and copied to EOS beforehand (see SKILL.md).
  : "${CMSSW_TARBALL:?set CMSSW_TARBALL=root://cmseos.fnal.gov//store/user/<you>/CMSSW_X.tgz}"
  source /cvmfs/cms.cern.ch/cmsset_default.sh
  xrdcp -s "$CMSSW_TARBALL" .
  tar -xf "$(basename "$CMSSW_TARBALL")"
  CMSSW_DIR=$(tar -tf "$(basename "$CMSSW_TARBALL")" | head -1 | cut -d/ -f1)
  cd "$CMSSW_DIR/src"
  scramv1 b ProjectRename >/dev/null         # relink the already-compiled area; don't recompile on the worker
  eval "$(scramv1 runtime -sh)"
  cd - >/dev/null
fi
export PYTHONNOUSERSITE=1
python3 --version

# ---- payload: edit this ------------------------------------------------------
# Contract: payload.py gets --inputs <comma-separated root:// URLs> --output <local file name>
# and must write exactly that one file. Its name, output_<jobid>.<OUT_EXT>, is what
# check_outputs.py looks for (OUT_EXT=root by default; set OUT_EXT=json etc. in the JDL).
OUTFILE="output_${JOBID}.${OUT_EXT:-root}"
python3 payload.py --inputs "$INPUTS" --output "$OUTFILE"

# ---- stage out to EOS, verify, clean up --------------------------------------
for f in "$OUTFILE"; do
  ok=0
  for attempt in 1 2 3; do
    if xrdcp -f "$f" "${OUTDIR}/${f}"; then ok=1; break; fi
    echo "xrdcp attempt ${attempt} failed for ${f}, retrying in 30 s" >&2; sleep 30
  done
  [ "$ok" = 1 ] || { echo "stage-out failed for ${f}" >&2; exit 3; }
  rm -f "$f"                                 # don't let condor ship big files back to NFS
done
echo "done job=${JOBID}"
