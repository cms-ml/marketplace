#!/usr/bin/env bash
# Rerun every comparison.  Usage: run_all.sh <cache dir> <skims glob> <dimuon dir>
#   cache dir : scratch directory for HEPData records, PDG json, Open Data lumi files, intermediate histograms (not in the repository)
#   skims glob: the student's dijet skims, e.g. '<scratch>/skims/output_d*.npz'  (quote it)
#   dimuon dir: directory with dimuon_analysis.py, histograms.pkl (student's dimuon demo)
set -euo pipefail
CACHE=${1:?cache dir}; SKIMS=${2:?skims glob}; DIMU=${3:?dimuon dir}
HERE=$(cd "$(dirname "$0")" && pwd)
set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh; set -u
mkdir -p "$CACHE"
cd "$HERE"
python3 compare_d1_exact.py --cache "$CACHE"
python3 compare_d5_inclusive.py --cache "$CACHE" --skims "$SKIMS"
python3 diag_d5_rate_vs_run.py --cache "$CACHE" --skims "$SKIMS"
python3 compare_d2_d3_btag_spectra.py --cache "$CACHE"      # needs the D5 histogram cache for the supplementary b-tag fraction
python3 compare_d4_efficiency.py --cache "$CACHE"
python3 rerun_dimuon.py --dimuon-dir "$DIMU" --cache "$CACHE"
python3 compare_m1_peaks.py --dimuon-dir "$DIMU" --cache "$CACHE"      # about 8 minutes (numerical Breit-Wigner convolution)
python3 compare_m2_upsilon_ratios.py --cache "$CACHE"
python3 compare_m3_z_pt_y.py --dimuon-dir "$DIMU" --cache "$CACHE"
python3 compare_m4_z_massshape.py --dimuon-dir "$DIMU" --cache "$CACHE"
python3 make_comparison.py
