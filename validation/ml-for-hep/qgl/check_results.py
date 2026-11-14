#!/usr/bin/env python3
"""Physics and consistency checks on summary.json of the quark/gluon BDT validation (stdlib only).

    python3 check_results.py [summary.json]

Exit 0 all checks pass, 1 a check failed, 2 summary.json missing or unreadable.
Prints one line per check and SUMMARY=<passed>/<total>.
"""
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
TAGGERS = ("bdt", "qgl", "deepjet_qg")
FORBIDDEN_INPUTS = ("Jet_qgl", "Jet_btagDeepFlavQG", "qgl", "deepjet_qg", "obs_qgl", "obs_deepjet_qg",
                    "Jet_partonFlavour", "parton_flavour", "partonflavour", "label")
PERSONAL = re.compile(r"(/uscms(_data)?/|/afs/|/home/|/eos/uscms/store/user/|/store/user/[a-z])")


def main() -> int:
    path = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "summary.json")
    try:
        with open(path) as f:
            s = json.load(f)
    except Exception as e:  # noqa: BLE001
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    res = []

    def check(name, ok, detail=""):
        res.append(bool(ok))
        print(f"{'PASS' if ok else 'FAIL'} {name} {detail}".rstrip())

    try:
        bad_auc, bad_eff, low_wp, n_bins = [], [], [], 0
        for b, tg in s["taggers"].items():
            if tg is None:
                continue
            n_bins += 1
            for t in TAGGERS:
                m = tg[t]
                if not 0.5 < m["auc"] < 1:
                    bad_auc.append(f"{t}:{b}")
                for wn, wp in m["wp"].items():
                    if wp["value"] is None:
                        continue
                    if not 0 <= wp["value"] <= 1:
                        bad_eff.append(f"{t}:{b}:{wn}")
                    if min(wp["n_q_pass"], wp["n_g_pass"]) < 100:
                        low_wp.append(f"{t}:{b}:{wn}")
        check("auc_in_(0.5,1)_every_tagger_and_bin", not bad_auc and n_bins > 0, f"bins={n_bins} bad={bad_auc[:5]}")
        check("efficiencies_and_rejections_in_[0,1]", not bad_eff, f"bad={bad_eff[:5]}")
        check("quoted_working_points_have_100_jets_per_class", not low_wp, f"bad={low_wp[:5]}")
        bdt = s["bdt"]
        check("bdt_auc_test_below_0.99_leakage_guard", bdt["AUC_TEST"] < 0.99, f"AUC_TEST={bdt['AUC_TEST']}")
        inputs = s["inputs"]
        leak = [i for i in inputs if any(f.lower() == i.lower() or f.lower() in i.lower() for f in FORBIDDEN_INPUTS)]
        check("qgl_deepjet_partonflavour_not_inputs", not leak and len(inputs) > 0, f"inputs={len(inputs)} bad={leak}")
        ready = int(s["model_card"]["READY"])
        gap = abs(bdt["AUC_TRAIN"] - bdt["AUC_TEST"])
        check("auc_gap_below_0.02_if_ready", (not ready) or gap < 0.02, f"gap={gap:.5f} ready={ready}")
        check("onnx_frac_diff_below_0.005", bdt["onnx"]["frac_diff"] < 0.005, f"frac={bdt['onnx']['frac_diff']} max={bdt['onnx']['max_abs_diff']}")
        mc = s["model_card"]
        failed = [x for x in str(mc["FAILED"]).split(",") if x and x != "none"]
        missing = [x for x in str(mc["MISSING"]).split(",") if x and x != "none"]
        consistent = ready == int(not failed and not missing)
        check("ready_consistent_with_failed_missing_waived", consistent and int(mc["N_WAIVED"]) == len(mc.get("waivers", {})),
              f"READY={ready} FAILED={failed} MISSING={missing} N_WAIVED={mc['N_WAIVED']}")
        sc = s["scan"]
        sig = int(sc["improvement"] > 2 * sc["noise"])
        check("scan_significant_consistent", sig == int(sc["significant"]),
              f"improvement={sc['improvement']} noise={sc['noise']} significant={sc['significant']}")
        j = s["jets"]
        check("at_least_200k_jets_per_class", min(j["n_quark"], j["n_gluon"]) >= 200000, f"q={j['n_quark']} g={j['n_gluon']}")
        hits = []
        for root, _, files in os.walk(HERE):
            for fn in files:
                if fn.endswith((".png", ".pyc")) or fn == os.path.basename(__file__):
                    continue
                try:
                    txt = open(os.path.join(root, fn), encoding="utf-8").read()
                except (UnicodeDecodeError, OSError):
                    continue
                if PERSONAL.search(txt) or (os.environ.get("USER") and f"/{os.environ['USER']}/" in txt):
                    hits.append(fn)
        check("no_personal_paths", not hits, f"files={hits}")
    except (KeyError, TypeError) as e:
        print(f"error: summary.json lacks {e}", file=sys.stderr)
        return 2
    print(f"SUMMARY={sum(res)}/{len(res)}")
    return 0 if all(res) else 1


if __name__ == "__main__":
    sys.exit(main())
