#!/usr/bin/env bash
# Fetch the EXO-17-021 HEPData record (ins1685989, recid 85857) and the boosted tables into ref/.
# Usage: bash scripts/fetch_hepdata.sh   (from cms-comparison/). Public data, CC0.
set -euo pipefail
mkdir -p ref
curl -sL "https://www.hepdata.net/record/ins1685989?format=json" -o ref/record.json
for t in 348180 348181 348182; do
  curl -sL "https://www.hepdata.net/record/data/85857/${t}/1" -o "ref/table_${t}.json"
done
curl -sL https://arxiv.org/pdf/1808.03124 -o ref/paper.pdf
echo "FETCHED=ref/record.json,ref/table_348180.json,ref/table_348181.json,ref/table_348182.json,ref/paper.pdf"
