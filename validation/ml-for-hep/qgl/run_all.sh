#!/usr/bin/env bash
# Rerun the quark/gluon BDT validation from the tables on (set BUILD_TABLES=1 to rebuild them too).
#
#   export WORK=~/nobackup/ml_validation/qgl      # large-file work area, outside the repository
#   bash validation/ml-for-hep/qgl/run_all.sh
#
# Needs: LCG_109 view (sourced below), and $WORK/venv-extras with onnxmltools, skl2onnx, lightgbm
# (created here if missing, as in the bdt-training skill). Threads: THREADS (default 4).
# Every step writes its log to $WORK/logs/ and prints only its KEY=VALUE lines.
set -o pipefail
: "${WORK:?set WORK to the work area (e.g. ~/nobackup/ml_validation/qgl)}"
THREADS=${THREADS:-4}
HERE=$(cd "$(dirname "$0")" && pwd)
SK=$HERE/../../../plugins/ml-for-hep/skills
PREP=$SK/hep-ml-data-prep/scripts
T=$SK/bdt-training/scripts/train_bdt.py
SCAN=$SK/hyperparam-scan
EV=$SK/model-evaluation/scripts
SC=$SK/mass-sculpting-check/scripts
CL=$SK/closure-tests/scripts/closure.py
PTCAT=obs_pt:30,50,80,120,200,400,1000
WPS="0.5 0.3 0.1"
mkdir -p "$WORK/logs"
set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh; set -u
if [ ! -x "$WORK/venv-extras/bin/python3" ]; then
  python3 -m venv --system-site-packages "$WORK/venv-extras"
  "$WORK/venv-extras/bin/pip" install -q lightgbm onnxmltools skl2onnx
fi
. "$WORK/venv-extras/bin/activate"
export PYTHONPATH=$VIRTUAL_ENV/lib/python3.13/site-packages:$PYTHONPATH

# step NAME CMD...: run with time -v, log, print KEY=VALUE lines, keep the exit code
step() {
  local name=$1; shift
  /usr/bin/time -v "$@" > "$WORK/logs/$name.log" 2>&1; local rc=$?
  echo "EXIT $rc" >> "$WORK/logs/$name.log"
  echo "== $name (exit $rc)"; grep -E '^[A-Z][A-Z0-9_.]*=' "$WORK/logs/$name.log" | grep -v '^FEATURES=' | tr '\n' ' '; echo
  return $rc
}
kv() { grep -E "^$2=" "$WORK/logs/$1.log" | tail -1 | cut -d= -f2-; }

if [ "${BUILD_TABLES:-0}" = 1 ]; then
  python3 "$HERE/make_samples.py" --n-files 8,4,2,2 -o "$WORK/samples.json"
  step prep python3 "$PREP/nano_to_table.py" --samples "$WORK/samples.json" --features "$HERE/features_qgl.py" \
    --lumi 1 --max-events 30000 -o "$WORK/raw.parquet" --force || exit 1
  step label python3 "$HERE/make_jet_table.py" "$WORK/raw.parquet" --out "$WORK/table.parquet" \
    --out-q15 "$WORK/table_q15.parquet" --json "$WORK/composition.json" --min-per-class 200000 || exit 1
fi

# 1. table checks (gate)
step check python3 "$PREP/check_table.py" "$WORK/table.parquet" --mass obs_pt --json "$WORK/checks.json" || exit 1
step check_q15 python3 "$PREP/check_table.py" "$WORK/table_q15.parquet" --mass obs_pt --json "$WORK/checks_q15.json"

# 2. baseline (xgboost defaults) + backend cross-checks
step bdt0 python3 "$T" "$WORK/table.parquet" --out-dir "$WORK/runs/bdt0" --threads "$THREADS" --seed 1 --onnx --skip-existing
for b in hgb lightgbm; do
  step ${b}0 python3 "$T" "$WORK/table.parquet" --out-dir "$WORK/runs/${b}0" --backend $b --threads "$THREADS" --seed 1 --onnx --skip-existing
done
step eval0 python3 "$EV/evaluate.py" "$WORK/runs/bdt0/scores.parquet" --out-dir "$WORK/runs/bdt0/eval" --category $PTCAT

# 3. quick scan; baseline = validation AUC of bdt0, noise = AUC_ERR of its evaluation
BASE=$(kv bdt0 AUC_VAL); NOISE=$(kv eval0 AUC_ERR)
CMD="python3 $T $WORK/table.parquet --out-dir {out_dir} --params-json '{params_json}' --progress-every 25 --threads $THREADS"
step scan_quick python3 "$SCAN/scripts/scan.py" run --study-dir "$WORK/scan_quick" --space "$SCAN/assets/space_quick.json" \
  --mode quick --cmd "$CMD" --baseline "$BASE" --noise "$NOISE"
if [ "$(kv scan_quick SIGNIFICANT)" != 0 ]; then
  echo "SCAN_SIGNIFICANT=1: run the TPE scan and retrain BEST_PARAMS before going on (not automated here)"; exit 1
fi
echo "SCAN_DECISION=keep_defaults FINAL_RUN=runs/bdt0"

# 4. evaluation and three-tagger comparison (test fold, once)
step eval_eta python3 "$EV/evaluate.py" "$WORK/runs/bdt0/scores.parquet" --out-dir "$WORK/runs/bdt0/eval_eta" \
  --category obs_abseta:0,1.3,2.5 --no-plots
step compare python3 "$HERE/qg_compare.py" "$WORK/runs/bdt0/scores.parquet" --out "$WORK/runs/bdt0/compare/compare.json" \
  --plots-dir "$WORK/runs/bdt0/compare/plots"

# 5. sculpting against jet pT: raw score, then the pT-DDT maps (one per gluon-efficiency working point)
step sculpt python3 "$SC/sculpting.py" "$WORK/runs/bdt0/scores.parquet" --mass obs_pt --mass-range 30,1000 --log-bins \
  --bkg-effs 0.5,0.3,0.1 --out-dir "$WORK/runs/bdt0/sculpt"
mkdir -p "$WORK/runs/bdt0/ddt"
for e in $WPS; do
  step ddt_$e python3 "$SC/ddt.py" "$WORK/runs/bdt0/scores.parquet" --mass obs_pt --bkg-eff $e --column score_ddt \
    -o "$WORK/runs/bdt0/ddt/scores_ddt_$e.parquet"
  step sculpt_ddt_$e python3 "$SC/sculpting.py" "$WORK/runs/bdt0/ddt/scores_ddt_$e.parquet" --score score_ddt --mass obs_pt \
    --mass-range 30,1000 --log-bins --bkg-effs $e --out-dir "$WORK/runs/bdt0/sculpt_ddt_$e"
  step eval_ddt_$e python3 "$EV/evaluate.py" "$WORK/runs/bdt0/ddt/scores_ddt_$e.parquet" --score score_ddt --bkg-effs $e \
    --out-dir "$WORK/runs/bdt0/eval_ddt_$e" --category $PTCAT --no-plots
done

# 6. k-fold: five rotations (test k, validation k-1, train the other three; k = 4 is bdt0's split)
for k in 0 1 2 3 4; do
  v=$(( (k + 4) % 5 )); tr=$(python3 -c "print(','.join(str(i) for i in range(5) if i not in ($k, $v)))")
  step kfold_f$k python3 "$T" "$WORK/table.parquet" --out-dir "$WORK/kfold/f$k" --train-folds $tr --val-folds $v \
    --test-folds $k --threads "$THREADS" --seed 1 --skip-existing
done
for e in 0.1 0.5; do
  step closure_kfold_$e python3 "$CL" kfold "$WORK"/kfold/f{0,1,2,3,4}/scores.parquet --bkg-eff $e --out-dir "$WORK/closure_kfold_$e"
done

# 7. label cross-check: quark = |partonFlavour| 1-5
step bdt0_q15 python3 "$T" "$WORK/table_q15.parquet" --out-dir "$WORK/runs_q15/bdt0" --threads "$THREADS" --seed 1 --skip-existing
step compare_q15 python3 "$HERE/qg_compare.py" "$WORK/runs_q15/bdt0/scores.parquet" --out "$WORK/runs_q15/bdt0/compare/compare.json" \
  --label-note "quark = |partonFlavour| 1-5, gluon = 21"

# 8. plots and the gate
step plots python3 "$HERE/make_plots.py" --run "$WORK/runs/bdt0" --plots-dir "$WORK/runs/bdt0/plots"
WAIVE=$(python3 - "$WORK" <<'EOF'
import json, sys
W = sys.argv[1]
r = json.load(open(f"{W}/runs/bdt0/sculpt/sculpting.json"))["summary"]
d = {e: json.load(open(f"{W}/runs/bdt0/sculpt_ddt_{e}/sculpting.json"))["summary"] for e in ("0.5", "0.3", "0.1")}
print("one global threshold on the raw score sculpts the gluon pT spectrum (runs/bdt0/sculpt/sculpting.json: "
      f"PEARSON_R={r['PEARSON_R']}, CHI2_NDF_0.1={r['CHI2_NDF_0.1']}); the model is used only through the pT-DDT maps "
      "runs/bdt0/ddt/scores_ddt_<eff>.parquet.map.json, whose checks pass: "
      + ", ".join(f"eff {e}: CHI2_NDF={d[e]['CHI2_NDF_' + e]} P={d[e]['P_' + e]} {d[e]['STATUS']}" for e in d))
EOF
)
step model_card python3 "$EV/model_card.py" --name qgl_bdt_ddt --out "$WORK/MODEL_CARD_qgl.md" \
  --check table="$WORK/checks.json" --check training="$WORK/runs/bdt0/metrics.json" \
  --check evaluation="$WORK/runs/bdt0/eval/evaluation.json" \
  --check evaluation_ddt_0.5="$WORK/runs/bdt0/eval_ddt_0.5/evaluation.json" \
  --check evaluation_ddt_0.3="$WORK/runs/bdt0/eval_ddt_0.3/evaluation.json" \
  --check evaluation_ddt_0.1="$WORK/runs/bdt0/eval_ddt_0.1/evaluation.json" \
  --check sculpting="$WORK/runs/bdt0/sculpt_ddt_0.5/sculpting.json" \
  --check sculpting_ddt_0.3="$WORK/runs/bdt0/sculpt_ddt_0.3/sculpting.json" \
  --check sculpting_ddt_0.1="$WORK/runs/bdt0/sculpt_ddt_0.1/sculpting.json" \
  --check sculpting_raw_score="$WORK/runs/bdt0/sculpt/sculpting.json" \
  --check closure="$WORK/closure_kfold_0.1/closure.json" --check closure_kfold_0.5="$WORK/closure_kfold_0.5/closure.json" \
  --waive "sculpting_raw_score=$WAIVE" \
  --field "Task=quark (|partonFlavour| 1-3) vs gluon (21) AK4 jets, one row per jet, CMS Open Data simulation (QCD HT700-Inf, RunIISummer20UL16NanoAODv9); not a CMS result" \
  --field "Inputs=n_constituents, ch_had_ef, ne_had_ef, ch_em_ef, ne_em_ef, mu_ef, ch_pv0_ef, area, mass_over_pt, n_muons, n_electrons, rho (no QGL shape variables: not in NanoAODv9)" \
  --field "Intended use=quark selection by score_ddt > 0 with the pT-DDT map of the chosen gluon efficiency (0.5, 0.3 or 0.1), jets with 30 <= pT < 1000 GeV and |eta| < 2.5" \
  --field "Baselines=Jet_qgl and 1 - Jet_btagDeepFlavQG on the same test jets: see summary.json (taggers)" \
  --field "Limitations=pT/eta not flattened; per-bin performance below Jet_qgl and DeepJet; simulation only, no data/MC check; one generator (madgraphMLM-pythia8)"
python3 - "$WORK" "$WAIVE" <<'EOF'
import json, re, sys
W, waive = sys.argv[1], sys.argv[2]
kv = dict(l.split("=", 1) for l in open(f"{W}/logs/model_card.log") if re.match(r"^[A-Z][A-Z0-9_]*=", l))
kv = {k: v.strip() for k, v in kv.items()}
kv["OUTPUT"] = "MODEL_CARD_qgl.md"
kv["waivers"] = {"sculpting_raw_score": waive}
json.dump(kv, open(f"{W}/model_card_result.json", "w"), indent=1)
EOF

# 9. deliverables into the repository (no tables or models; work-area paths replaced by <work>)
mkdir -p "$HERE/plots"
cp "$WORK"/runs/bdt0/compare/plots/*.png "$WORK"/runs/bdt0/plots/*.png "$HERE/plots/"
sed "s#$WORK#<work>#g; s#$HERE/\.\./\.\./\.\./##g" "$WORK/MODEL_CARD_qgl.md" > "$HERE/MODEL_CARD_qgl.md"
step summary python3 "$HERE/make_summary.py" --work "$WORK" -o "$WORK/summary.json"
sed "s#$WORK#<work>#g" "$WORK/summary.json" > "$HERE/summary.json"
python3 "$HERE/check_results.py" "$HERE/summary.json"
