#!/usr/bin/env python3
"""Collect every JSON the scripts wrote under $WORK into validation/ml-for-hep/qgl/summary.json.

    make_summary.py --work $WORK -o summary.json

Only copies numbers from script outputs (no new computation except unit-free bookkeeping).
Paths inside the summary are relative to <work>. Stdout: N_KEYS READY OUTPUT. Exit 0 ok, 2 missing input.
"""
import argparse
import json
import os
import sys


def load(work, rel):
    with open(os.path.join(work, rel)) as f:
        return json.load(f)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--work", required=True)
    p.add_argument("-o", "--output", required=True)
    p.add_argument("--run", default="runs/bdt0")
    p.add_argument("--wps", default="0.5,0.3,0.1")
    a = p.parse_args()
    W, R = a.work, a.run
    wps = a.wps.split(",")
    try:
        meta = load(W, "raw.parquet.meta.json")
        comp = load(W, "composition.json")
        table = load(W, "checks.json")
        met = load(W, f"{R}/metrics.json")
        ev = load(W, f"{R}/eval/evaluation.json")
        ev_eta = load(W, f"{R}/eval_eta/evaluation.json")
        cmp_ = load(W, f"{R}/compare/compare.json")
        scan = load(W, "scan_quick/leaderboard.json")
        sc_raw = load(W, f"{R}/sculpt/sculpting.json")
        sc_ddt = {e: load(W, f"{R}/sculpt_ddt_{e}/sculpting.json") for e in wps}
        ev_ddt = {e: load(W, f"{R}/eval_ddt_{e}/evaluation.json") for e in wps}
        maps = {e: load(W, f"{R}/ddt/scores_ddt_{e}.parquet.map.json") for e in wps}
        clo = {k: load(W, f"closure_kfold_{k}/closure.json") for k in ("0.1", "0.5")}
        card = load(W, "model_card_result.json")
        xb = {b: load(W, f"runs/{b}0/metrics.json")["summary"] for b in ("hgb", "lightgbm")}
        q15 = {"training": load(W, "runs_q15/bdt0/metrics.json")["summary"],
               "compare_inclusive": load(W, "runs_q15/bdt0/compare/compare.json")["bins"]["inclusive"]["taggers"],
               "compare_summary": load(W, "runs_q15/bdt0/compare/compare.json")["summary"]}
        kf = {f"f{k}": load(W, f"kfold/f{k}/metrics.json")["summary"] for k in range(5)}
    except Exception as e:  # noqa: BLE001
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    s = met["summary"]
    ss = scan["summary"]
    noise = ss.get("NOISE", ev["summary"]["AUC_ERR"])
    out = {
        "description": "Quark/gluon jet BDT vs Jet_qgl vs DeepJet QG, CMS Open Data simulation "
                       "(RunIISummer20UL16NanoAODv9 QCD HT700-Inf). Not a CMS result.",
        "selection": {"jets": "all jets with 30 <= pT < 1000 GeV, |eta| < 2.5, tight ID (jetId & 2), genJetIdx >= 0",
                      "label": comp["label_definition"], "split": "fold = event % 5; train 0,1,2; val 3; test 4",
                      "pt_edges_gev": cmp_["pt_edges"], "abseta_edges": cmp_["abseta_edges"],
                      "working_points": cmp_["working_points"], "tagger_orientation": cmp_["orientation"]},
        "samples": [{k: x[k] for k in ("name", "xsec_pb", "n_read", "n_selected", "sum_gen_weight")} | {"n_files": len(x["files"])}
                    for x in meta["samples"]],
        "jets": {"n_quark": comp["N_QUARK"], "n_gluon": comp["N_GLUON"], "n_quark_q15": comp["N_QUARK_Q15"],
                 "neff_quark": table["summary"]["NEFF_SIG"], "neff_gluon": table["summary"]["NEFF_BKG"],
                 "per_bin_split": {k: b["counts"] for k, b in cmp_["bins"].items()}},
        "flavour_composition_before_label_cut": {"n_raw": comp["n_raw"], "n_unmatched": comp["n_unmatched"],
                                                 "unmatched_weighted_frac": comp["unmatched_weighted_frac"],
                                                 "matched": comp["matched"], "per_sample": comp["per_sample"]},
        "neg_weight_frac": table["summary"]["NEG_WEIGHT_FRAC"],
        "inputs": met["config"]["features"],
        "observers": meta["observers"],
        "table_check": table["summary"],
        "taggers": {k: b["taggers"] for k, b in cmp_["bins"].items()},
        "qgl_shapes": {k: b.get("qgl_shapes") for k, b in cmp_["bins"].items()},
        "bdt": {"AUC_TRAIN": s["AUC_TRAIN"], "AUC_VAL": s["AUC_VAL"], "AUC_TEST": s["AUC_TEST"], "AUC_GAP": s["AUC_GAP"],
                "AUC_ERR": ev["summary"]["AUC_ERR"], "KS_P_SIG": s["KS_P_SIG"], "KS_P_BKG": s["KS_P_BKG"],
                "OVERTRAINED": s["OVERTRAINED"], "BEST_ITER": s["BEST_ITER"], "params": met["config"]["hp"],
                "seed": met["config"]["seed"], "STATUS": s["STATUS"],
                "onnx": {"max_abs_diff": s["ONNX_MAX_ABS_DIFF"], "frac_diff": s["ONNX_FRAC_DIFF"]},
                "evaluation": ev["summary"], "evaluation_pt_categories": ev["categories"],
                "evaluation_eta_categories": ev_eta["categories"], "evaluation_ddt": {e: v["summary"] for e, v in ev_ddt.items()},
                "top_features": s["TOP_FEATURES"], "importance_total_gain": met["importance_total_gain"],
                "mean_abs_shap": met["mean_abs_shap"]},
        "backend_crosscheck": xb,
        "label_crosscheck_q15": q15,
        "scan": {"mode": "quick", "space": "space_quick.json (max_depth 3/5 x learning_rate 0.05/0.2)",
                 "n_complete": ss["N_COMPLETE"], "n_pruned": ss["N_PRUNED"], "n_failed": ss["N_FAILED"],
                 "baseline": ss["BASELINE"], "best": ss["BEST_VALUE"], "best_params": ss["BEST_PARAMS"],
                 "improvement": ss["IMPROVEMENT"], "noise": noise, "spread_top5": ss["SPREAD_TOP5"],
                 "significant": ss["SIGNIFICANT"],
                 "decision": "no longer scan; final model = defaults (bdt0)" if not ss["SIGNIFICANT"] else "longer scan"},
        "sculpting": {"observable": "obs_pt (gluon jets, test fold)",
                      "raw_score": sc_raw["summary"],
                      "pt_ddt": {e: v["summary"] for e, v in sc_ddt.items()},
                      "ddt_maps": {e: f"{R}/ddt/scores_ddt_{e}.parquet.map.json" for e in wps},
                      "ddt_thresholds": {e: {k: v for k, v in m.items() if k != "command"} for e, m in maps.items()}},
        "closure_kfold": {k: v["summary"] for k, v in clo.items()},
        "kfold_models": kf,
        "model_card": card,
        "versions": met["versions"] | meta["versions"],
    }
    with open(a.output, "w") as f:
        json.dump(out, f, indent=1)
    print(f"N_KEYS={len(out)}\nREADY={card['READY']}\nOUTPUT={a.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
