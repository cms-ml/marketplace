#!/usr/bin/env python3
"""Per-bin closure / validation tests of both runs (CMS Open Data, private work).

With skill: recomputed from its reduced files (../ws_skill/red/*.parquet) with its definitions
(abcd_run.py: TESTS, quadratic TF fit B/D applied to C, non-QCD subtracted in data); checked against its
stored inclusive ratios and chi2 (fits/stage1_rerun.json). Unblinded SR from fits/prediction.json.
Without skill: read from fits/blind_results.json (closure, valid) and fits/prediction.json.

Usage: python3 scripts/tests_perbin.py -> out/tests_perbin.json
"""
import json, os, sys
import numpy as np, pyarrow.parquet as pq

WSA, WSB = "../ws_skill", "../ws_noskill"
EDGES = np.array([40, 60, 80, 100, 120, 140, 160, 180, 200, 230, 260, 300, 350, 400, 480.]); MC = 0.5 * (EDGES[1:] + EDGES[:-1])
TESTS = {"SR": ((0, .2), (.2, .4), (0, 1.2), (1.2, 9)), "VR1_xshift": ((.2, .4), (.4, .6), (0, 1.2), (1.2, 9)),
         "VR2_yshift": ((0, .2), (.2, .4), (1.2, 1.8), (1.8, 9)), "VR3_xyshift": ((.2, .4), (.4, .6), (1.2, 1.8), (1.8, 9))}


def rng(v, r): return (v >= r[0]) & (v < r[1])


def hists(d, t):
    xp, xf, yp, yf = TESTS[t]; out = {}
    for n, (xr, yr) in dict(A=(xp, yp), B=(xf, yp), C=(xp, yf), D=(xf, yf)).items():
        m = rng(d["masym"], xr) & rng(d["deta"], yr)
        out[n] = (np.histogram(d["mavg"][m], EDGES, weights=d["w"][m])[0], np.histogram(d["mavg"][m], EDGES, weights=d["w"][m] ** 2)[0])
    return out


def predict(H, O=None):
    y, v = {}, {}
    for r in "ABCD":
        y[r], v[r] = H[r][0].copy(), H[r][1].copy()
        if O is not None and r != "A":
            y[r] -= O[r][0]; v[r] += O[r][1]
    tf = y["B"] / y["D"]; etf = tf * np.sqrt(v["B"] / y["B"] ** 2 + v["D"] / y["D"] ** 2)
    co, cv = np.polyfit(MC, tf, 2, w=1 / etf, cov="unscaled")
    V = np.vander(MC, 3); tff = V @ co
    pred = y["C"] * tff
    cov = np.diag(v["C"] * tff ** 2) + np.outer(y["C"], y["C"]) * (V @ cv @ V.T)
    return pred, cov


def load(g):
    t = pq.read_table(f"{WSA}/red/{g}.parquet", columns=["mavg", "masym", "deta", "w"]).to_pandas()
    return {k: t[k].values.astype("f8") for k in ("mavg", "masym", "deta", "w")}


def with_skill():
    stored = json.load(open(f"{WSA}/fits/stage1_rerun.json"))["tests"]
    q = load("qcd"); d = load("data"); d["w"] = np.ones_like(d["w"])
    oth = [load(g) for g in ("vjets", "top", "vv", "higgs")]
    rows = []
    for t in TESTS:
        H = hists(q, t); pred, cov = predict(H); obs, vobs = H["A"]
        rows.append((f"MC {t}", obs, vobs, pred, cov, stored[f"MC_{t}"]))
    for t in list(TESTS)[1:]:
        H = hists(d, t); Os = [hists(o, t) for o in oth]
        O = {r: (sum(o[r][0] for o in Os), sum(o[r][1] for o in Os)) for r in "ABCD"}
        pred, cov = predict(H, O)
        obs = H["A"][0] - O["A"][0]; vobs = H["A"][1] + O["A"][1]
        rows.append((f"data {t}", obs, vobs, pred, cov, stored[f"DATA_{t}"]))
    out = []
    for name, obs, vobs, pred, cov, st in rows:
        r = obs - pred; chi2 = float(r @ np.linalg.solve(cov + np.diag(vobs), r))
        e = np.sqrt(vobs + np.diag(cov))
        out.append(dict(test=name, ratio=(obs / pred).tolist(), pull=(r / e).tolist(), incl_ratio=float(obs.sum() / pred.sum()),
                        chi2=chi2, stored_ratio=st["ratio"], stored_chi2=st["chi2"]))
    p = json.load(open(f"{WSA}/fits/prediction.json")); fin = json.load(open(f"{WSA}/fits/final.json"))
    o = np.array(p["observed_A"]); e = np.array(p["predicted_total_A_QCD_plus_other"])
    out.append(dict(test="data SR (unblinded)", ratio=(o / e).tolist(), pull=fin["pulls"], incl_ratio=float(o.sum() / e.sum()), chi2=fin["chi2"]))
    return dict(edges=EDGES.tolist(), tests=out)


def without_skill():
    br = json.load(open(f"{WSB}/fits/blind_results.json")); p = json.load(open(f"{WSB}/fits/prediction.json"))
    out = []
    for k, c in br["closure"].items():
        r = np.array(c["ratio_bins"], float); e = np.array(c["ratio_err"], float)
        out.append(dict(test=f"MC {k}", ratio=r.tolist(), pull=((r - 1) / e).tolist(), incl_ratio=c["ratio_incl"], chi2=c["chi2"]))
    for k, v in br["valid"].items():
        out.append(dict(test=f"data {k}", ratio=v["ratio_bins"], pull=v["pull"], incl_ratio=v["ratio"], chi2=v["chi2"]))
    o = np.array(p["observed_A"]); e = np.array(p["pred_qcd_A"]) + np.array(p["other_bkg_A"])
    out.append(dict(test="data SR (unblinded)", ratio=(o / e).tolist(), pull=p["pull"], incl_ratio=float(o.sum() / e.sum()),
                    chi2=json.load(open(f"{WSB}/fits/unblinded.json"))["chi2"]))
    return dict(edges=p["edges"], tests=out)


def main():
    res = {"note": "CMS Open Data, private work; not CMS results", "with_skill": with_skill(), "without_skill": without_skill()}
    os.makedirs("out", exist_ok=True)
    json.dump(res, open("out/tests_perbin.json", "w"), indent=1, default=lambda x: None if x != x else x)
    for t in res["with_skill"]["tests"]:
        print(f"WS {t['test']}: ratio={t['incl_ratio']:.4f} (stored {t.get('stored_ratio', float('nan')):.4f}) chi2={t['chi2']:.1f} (stored {t.get('stored_chi2', float('nan')):.1f})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
