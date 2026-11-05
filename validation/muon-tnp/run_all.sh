#!/bin/bash
# Rerun everything after the Condor step (pair skims already on EOS). Run from any directory.
# Usage: SCRATCH=<scratch dir> bash validation/muon-tnp/run_all.sh
#   SCRATCH holds the skims (SCRATCH/skim/output_*.npz are copied from EOS if missing) and downloaded Open Data metadata.
# Outputs next to this script: summary.json, plots/, explore_trigger.json, logs in $SCRATCH.
set -eo pipefail
cd "$(dirname "$0")"
: "${SCRATCH:?set SCRATCH to a scratch directory outside the repository}"
mkdir -p "$SCRATCH/skim"
set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh
export PYTHONNOUSERSITE=1
EOS_SKIM="root://cmseos.fnal.gov//store/user/${USER}/tnp/skim"
for j in G0 G1 H0 H1 mc0 mc1; do
  [ -s "$SCRATCH/skim/output_$j.npz" ] || xrdcp -f -s "$EOS_SKIM/output_$j.npz" "$SCRATCH/skim/"
done
# exploratory trigger checks on the first selected G and H data file and one MC file (XRootD, about 30 s)
S=root://eospublic.cern.ch//eos/opendata/cms
read -r DG DH MC < <(python3 - <<'P'
import json
j = json.load(open("condor/input_files.json"))["selected"]
print("root://eospublic.cern.ch//eos/opendata/cms/" + j["G"][0], "root://eospublic.cern.ch//eos/opendata/cms/" + j["H"][0],
      "root://eospublic.cern.ch//eos/opendata/cms/" + j["mc"][16])
P
)
/usr/bin/time -v python3 explore_trigger.py --data "$DG" "$DH" --mc "$MC" --max-events 1000000 -o explore_trigger.json > "$SCRATCH/explore.log" 2>&1; echo EXIT $? >> "$SCRATCH/explore.log"
/usr/bin/time -v python3 analysis.py --skims "$SCRATCH/skim" --work "$SCRATCH" > "$SCRATCH/analysis.log" 2>&1; echo EXIT $? >> "$SCRATCH/analysis.log"
tail -3 "$SCRATCH/analysis.log"
python3 plot_cms_comparison.py summary.json plots   # ours vs CMS Muon POG SF plots
python3 check_results.py
