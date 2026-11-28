#!/usr/bin/env bash
# Rerun the whole comparison from cms-comparison/ (CMS Open Data, private work).
# Needs read access to ../ws_skill and ../ws_noskill and to the EOS skim (4 files are copied to skimcache/).
set -eo pipefail
cd "$(dirname "$0")/.."
set +u; source ../ws_skill/inputs/py_env.sh; set -u
[ -f ref/table_348181.json ] || bash scripts/fetch_hepdata.sh
mkdir -p skimcache logs
for f in G_0 G_12 H_0 H_12; do  # data subset
  [ -f skimcache/output_data_JetHT_2016${f}.parquet ] || \
    xrdcp -f -s "$(grep "_2016${f}.parquet" ../ws_skill/inputs/skim_files/data_JetHT_2016${f%%_*}.txt)" skimcache/
done
# QCD MC subset for the CMS-like selection (13 files)
for spec in qcd_HT500to700:1,8,15 qcd_HT700to1000:1,5,9,13 qcd_HT1000to1500:1,3,5 qcd_HT1500to2000:1,4 qcd_HT2000toInf:1; do
  s=${spec%%:*}
  for i in $(echo ${spec#*:} | tr , ' '); do
    u=$(sed -n "${i}p" ../ws_skill/inputs/skim_files/$s.txt); [ -f "skimcache/$(basename $u)" ] || xrdcp -f -s "$u" skimcache/
  done
done
python3 scripts/skim_check.py   > logs/skim_check.log 2>&1
python3 scripts/recompute.py    > logs/recompute.log 2>&1
python3 scripts/closure_mc_a.py > logs/closure_mc_a.log 2>&1
python3 scripts/compare_cms.py  > logs/compare_cms.log 2>&1
python3 scripts/cmslike.py      > logs/cmslike.log 2>&1
python3 scripts/tests_perbin.py > logs/tests_perbin.log 2>&1
python3 scripts/plots_v2.py     > logs/plots_v2.log 2>&1
python3 scripts/write_json.py   > logs/write_json.log 2>&1
tail -n 3 logs/*.log
