#!/usr/bin/env bash
# Re-runnable chain for the nanoaod-skimming validation (CMS Open Data, 2016 UL NanoAODv9).
#
#   bash validation/nanoaod-skimming/run_all.sh
#
# Skims go to $SKIMDIR (default: /uscms_data/d3/$USER/skims/nanoaod-skimming-validation),
# never into the repository. Logs (stdout of each script) go to logs/ next to this file.
# Needs cmslpc with /cvmfs and network access to eospublic.cern.ch and opendata.cern.ch.
set -eo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$HERE/../.." && pwd)"
SCR="$REPO/plugins/cms/skills/nanoaod-skimming/scripts"
SKIMDIR="${SKIMDIR:-/uscms_data/d3/$USER/skims/nanoaod-skimming-validation}"
LOGS="$HERE/logs"
PER_FILE="$SKIMDIR/per_file"
MERGED="$SKIMDIR/merged"
GOLDEN="$SKIMDIR/inputs/golden.json"
BYLS="root://eospublic.cern.ch//eos/opendata/cms/luminosity/2016/pp_2016lumibyls.csv"
XSEC_DY=6077.22   # pb, DYJetsToLL_M-50 amcatnloFXFX, used as given

# Environment (setup.sh is not nounset-safe, so relax -u while sourcing)
set +u
source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh
set -u
export PYTHONNOUSERSITE=1

mkdir -p "$LOGS" "$PER_FILE" "$MERGED" "$SKIMDIR/inputs" "$HERE/plots"

DATA=(
  root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/130000/0A4230E2-0C75-604D-890F-A4CE5E5C164E.root
  root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/130000/A3279183-BDA6-F44C-8EF3-C063BC598B68.root
  root://eospublic.cern.ch//eos/opendata/cms/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/130000/C760C7A6-E4AB-E447-93BB-1EAD0177DB41.root
)
MC=(
  root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/30000/6C3CD8A5-A288-724E-BF9F-BAAC46A4C139.root
  root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/30000/18DA8B20-842D-0741-BAFB-1A1C7C522921.root
  root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/30000/A2058F3B-C2A2-4E43-B963-6C5A4DC8084B.root
)

# Golden JSON: fetched once, kept outside the repository
if [ ! -s "$GOLDEN" ]; then
  curl -sSfL -o "$GOLDEN" https://opendata.cern.ch/record/14220/files/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt
fi

# Keep list (same for data and MC; patterns absent in data are reported as MISSING_PATTERNS)
KEEP=(--keep 'Muon_*' 'HLT_IsoMu24' 'HLT_IsoTkMu24' 'PV_npvs' 'MET_pt' 'MET_phi' 'Pileup_nTrueInt' 'LHEScaleWeight')
# Preselection: trigger OR and at least two muons with pT > 20 GeV
PRESEL='(HLT_IsoMu24 | HLT_IsoTkMu24) & (ak.sum(Muon_pt > 20, axis=1) >= 2)'

# ---- 1. skim each input file separately (one output per input) ----
skim_one() {  # name url [extra args]
  local name="$1" url="$2"; shift 2
  python3 "$SCR/skim.py" -i "$url" -o "$PER_FILE/$name.root" "${KEEP[@]}" \
      --cut "$PRESEL" "$@" > "$LOGS/$name.log" 2> "$LOGS/$name.err"
}

# Each skim holds about 2 GB at the default step size; a shared login node can OOM-kill
# six at once, so run at most MAX_JOBS in parallel (batch jobs are the real answer).
MAX_JOBS="${MAX_JOBS:-2}"
rc=0
throttle() { while [ "$(jobs -rp | wc -l)" -ge "$MAX_JOBS" ]; do wait -n || rc=1; done; }
for i in 0 1 2; do
  throttle; skim_one "skim_SingleMuon_2016G_$i" "${DATA[$i]}" --lumi-json "$GOLDEN" &
done
for i in 0 1 2; do
  throttle; skim_one "skim_DYJetsToLL_M50_$i" "${MC[$i]}" &
done
while [ "$(jobs -rp | wc -l)" -gt 0 ]; do wait -n || rc=1; done
if [ "$rc" -ne 0 ]; then echo "ERROR: a skim job failed, see $LOGS/*.err" >&2; exit 1; fi

# Input sizes (bytes) from XRootD stat, for the bookkeeping numbers
size_of() {  # url -> bytes
  local path="${1#root://eospublic.cern.ch/}"
  xrdfs eospublic.cern.ch stat "$path" | awk '/^Size:/{print $2}'
}
{
  in_d=0; in_m=0
  for u in "${DATA[@]}"; do s=$(size_of "$u"); in_d=$((in_d + s)); echo "# data $u $s"; done
  for u in "${MC[@]}";   do s=$(size_of "$u"); in_m=$((in_m + s)); echo "# mc $u $s"; done
  echo "INPUT_BYTES_DATA=$in_d"
  echo "INPUT_BYTES_MC=$in_m"
} > "$LOGS/input_sizes.log"

# ---- 2. merge skims with hadd (one data file, one MC file) ----
hadd -f -k "$MERGED/SingleMuon_2016G.root" "$PER_FILE"/skim_SingleMuon_2016G_*.root > "$LOGS/hadd_data.log" 2>&1
hadd -f -k "$MERGED/DYJetsToLL_M50.root"   "$PER_FILE"/skim_DYJetsToLL_M50_*.root   > "$LOGS/hadd_mc.log" 2>&1

# ---- 3. bookkeeping ----
# Data luminosity of the processed lumi sections (merged data skim)
python3 "$SCR/lumi.py" -i "$MERGED/SingleMuon_2016G.root" --byls "$BYLS" > "$LOGS/lumi_data_merged.log"
LUMI_PB=$(sed -n 's/^LUMI_PB=//p' "$LOGS/lumi_data_merged.log")
# Whole-year cross-check from the golden JSON
python3 "$SCR/lumi.py" --golden "$GOLDEN" --byls "$BYLS" > "$LOGS/lumi_golden_2016.log"
# MC normalisation from the original files and from the merged skim (must agree)
python3 "$SCR/sumw.py" -i "${MC[@]}" --xsec "$XSEC_DY" --lumi "$LUMI_PB" > "$LOGS/sumw_mc_original.log"
python3 "$SCR/sumw.py" -i "$MERGED/DYJetsToLL_M50.root" --xsec "$XSEC_DY" --lumi "$LUMI_PB" > "$LOGS/sumw_mc_merged.log"

# ---- 4. physics check and plot; writes summary.json ----
python3 "$HERE/zpeak.py" --data "$MERGED/SingleMuon_2016G.root" --mc "$MERGED/DYJetsToLL_M50.root" \
    --per-file "$PER_FILE" --logs "$LOGS" --out-dir "$HERE" > "$LOGS/zpeak.log"

echo "done: summary in $HERE/summary.json, logs in $LOGS"
