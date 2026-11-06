#!/bin/bash
# Rerun the muon-tnp-generic validation. Run from any directory:
#   SCRATCH=<scratch dir> bash validation/muon-tnp-generic/code/run_all.sh [job-name-regex]
# Inputs: 4 SingleMuon 2016G/H and 8 ZToMuMu powheg NanoAOD files (code/input_files.txt), copied once to
# $SCRATCH/inputs from the CERN Open Data EOS (about 7.3 GB), and the 2016 golden JSON. Runs code/jobs.txt with
# tnp.py (3 in parallel, about 2 GB each), the IsoMu22 trigger check and the exit-code tests, then
# summarize.py -> ../summary.json, ../plots/, ../results/, then check_results.py.
set -eo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/../../.." && pwd)"
: "${SCRATCH:?set SCRATCH to a scratch directory outside the repository}"
set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh; set -u
export PYTHONNOUSERSITE=1
IN="$SCRATCH/inputs"; R="$SCRATCH/runs"; mkdir -p "$IN" "$R"
OD=root://eospublic.cern.ch//eos/opendata/cms
while read -r tag path; do
  [ -s "$IN/$tag.root" ] || xrdcp -f -s "$OD/$path" "$IN/$tag.root"
done < "$HERE/input_files.txt"
GOLDEN="$IN/golden.json"
[ -s "$GOLDEN" ] || xrdcp -f -s "$OD/validated-runs/2016/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt" "$GOLDEN"
NEW="$REPO/plugins/cms/skills/muon-tag-and-probe/scripts/tnp.py"
# tnp.py before the generic interface (commit 337e5b7). If that commit is gone (squash merge), the "old" jobs
# take the stored outputs ../results/pre_change_<wp>.json, made by it on the same inputs.
OLD="$SCRATCH/tnp_old.py"
HAVE_OLD=1
git -C "$REPO" show 337e5b7:plugins/cms/skills/muon-tag-and-probe/scripts/tnp.py > "$OLD" 2>/dev/null || HAVE_OLD=0
declare -A DATA=([all]="$IN/G1.root $IN/G2.root $IN/H2.root $IN/H4.root" [D1]="$IN/G1.root $IN/H2.root" [D2]="$IN/G2.root $IN/H4.root")
declare -A MC=([all]="$IN/mc0.root $IN/mc1.root $IN/mc2.root $IN/mc3.root $IN/mc4.root $IN/mc7.root $IN/mc8.root $IN/mc9.root"
               [A]="$IN/mc0.root $IN/mc1.root $IN/mc3.root $IN/mc4.root $IN/mc7.root"
               [B]="$IN/mc2.root $IN/mc8.root $IN/mc9.root")
SEL="${1:-.}"   # regex on job names to run (all by default); the job list for summarize.py is always complete
run() {  # name script dataset mcset args...
  local name=$1 script=$2 data=$3 mc=$4; shift 4
  if [ "$script" = old ] && [ "$HAVE_OLD" = 0 ]; then
    cp "$HERE/../results/pre_change_${name#old_}.json" "$R/$name.json"; echo "EXIT stored" > "$R/$name.out"; return
  fi
  local t; [ "$script" = old ] && t="$OLD" || t="$NEW"
  /usr/bin/time -f "TIME %e s MAXRSS %M kB" python3 "$t" --data ${DATA[$data]} --mc ${MC[$mc]} --out "$R/$name.json" "$@" \
    > "$R/$name.out" 2> "$R/$name.log" && rc=0 || rc=$?
  echo "EXIT $rc" >> "$R/$name.out"
}
grep -v '^#' "$HERE/jobs.txt" | while IFS='|' read -r name script data mc args; do
  name=$(echo $name); script=$(echo $script); data=$(echo $data); mc=$(echo $mc)
  args=${args//@R/$R}; args=${args//@G/$GOLDEN}
  echo "$name|$script|$data|$mc|$args"
done > "$R/joblist.txt"
while IFS='|' read -r name script data mc args; do
  [[ "$name" =~ ^($SEL) ]] || continue
  while [ "$(jobs -rp | wc -l)" -ge 3 ]; do sleep 5; done
  echo "start $name"; eval "run $name $script $data $mc $args" &
done < "$R/joblist.txt"
wait
# IsoMu22 activity in data and MC (R2)
python3 "$HERE/isomu22_check.py" -o "$R/isomu22_check.json" G1="$IN/G1.root" G2="$IN/G2.root" H2="$IN/H2.root" \
  H4="$IN/H4.root" mc2="$IN/mc2.root" mc3="$IN/mc3.root" > "$R/isomu22_check.log" 2>&1
# exit codes: --dry-run (0); bad expressions, arguments and trigger specs (2)
set +e
T() {  # name args...: run on one data and one MC file, record the exit code
  local name=$1; shift
  python3 "$NEW" --data "$IN/G1.root" --mc "$IN/mc0.root" --out "$R/bad.json" "$@" > "$R/$name.out" 2>&1; echo "EXIT $?" >> "$R/$name.out"
}
T dryrun --den isTracker --num mediumId --dry-run
T bad_precedence --den isTracker --num "tightId & pfRelIso04_all < 0.15"
T bad_intbool --den isTracker --num "highPtId" --max-events 20000
T bad_call --den isTracker --num "__import__('os').system('true')"
T bad_dryrun_intbool --den isTracker --num "highPtId" --dry-run
T bad_den_only --den mediumId
T bad_recursion --den isTracker --num "$(python3 -c "print('+'.join(['pt'] * 6000) + ' > 1')")" --dry-run
T bad_trigger_zero --den isTracker --num-trigger 0:24 --dry-run
T bad_trigger_mixed --den isTracker --num-trigger "2|8&1:24" --dry-run
T bad_trigger_dr --den isTracker --num-trigger 2:24:0 --dry-run
set -e
python3 "$HERE/summarize.py" "$R" "$HERE/.."
python3 "$HERE/../check_results.py"
