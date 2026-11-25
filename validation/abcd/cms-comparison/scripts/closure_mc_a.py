#!/usr/bin/env python3
"""Per-bin QCD-MC closure of the with-skill run's SR ABCD (CMS Open Data 2016 simulation, private work).

The with-skill run stored only the inclusive MC closure (ratio, pull, chi2). This rebuilds the per-bin
closure from its reduced QCD MC file (../ws_skill/red/qcd.parquet) with its definitions:
A masym<0.2 & deta<1.2, B 0.2<=masym<0.4 & deta<1.2, C masym<0.2 & deta>=1.2, D 0.2<=masym<0.4 & deta>=1.2,
TF = B/D fitted with a quadratic in m_avg (the order its F-test chose), pred = C * TF_fit.
Check: the inclusive ratio and chi2 must reproduce the with-skill 1.0006 and 45.3/14.

Usage: python3 scripts/closure_mc_a.py   -> out/closure_mc_a.json
"""
import json, os, sys
import numpy as np, pyarrow.parquet as pq

EDGES = np.array([40, 60, 80, 100, 120, 140, 160, 180, 200, 230, 260, 300, 350, 400, 480.])
MC = 0.5 * (EDGES[1:] + EDGES[:-1])


def main():
    t = pq.read_table("../ws_skill/red/qcd.parquet", columns=["mavg", "masym", "deta", "w"]).to_pandas()
    x, y, m, w = t.masym.values, t.deta.values, t.mavg.values, t.w.values.astype("f8")
    reg = {"A": (x < .2) & (y < 1.2), "B": (x >= .2) & (x < .4) & (y < 1.2),
           "C": (x < .2) & (y >= 1.2), "D": (x >= .2) & (x < .4) & (y >= 1.2)}
    h = {r: np.histogram(m[s], EDGES, weights=w[s])[0] for r, s in reg.items()}
    v = {r: np.histogram(m[s], EDGES, weights=w[s] ** 2)[0] for r, s in reg.items()}
    tf = h["B"] / h["D"]; etf = tf * np.sqrt(v["B"] / h["B"] ** 2 + v["D"] / h["D"] ** 2)
    co, cv = np.polyfit(MC, tf, 2, w=1 / etf, cov="unscaled")
    V = np.vander(MC, 3); tff = V @ co; ctf = V @ cv @ V.T
    pred = h["C"] * tff
    cov = np.diag(v["C"] * tff ** 2) + np.outer(h["C"], h["C"]) * ctf
    obs, vobs = h["A"], v["A"]
    r = obs - pred
    chi2 = float(r @ np.linalg.solve(cov + np.diag(vobs), r))
    ratio = obs / pred; eratio = np.sqrt(vobs + np.diag(cov)) / pred
    inc = obs.sum() / pred.sum(); einc = np.sqrt(vobs.sum() + cov.sum()) / pred.sum()
    # linear slope of the per-bin closure ratio
    A = np.vstack([np.ones_like(MC), (MC - 200) / 100]).T
    W = np.diag(1 / eratio ** 2)
    cs = np.linalg.solve(A.T @ W @ A, A.T @ W @ ratio); ecs = np.sqrt(np.diag(np.linalg.inv(A.T @ W @ A)))
    out = dict(note="CMS Open Data simulation, private work", edges=EDGES.tolist(), obs=obs.tolist(), pred=pred.tolist(),
               ratio=ratio.tolist(), ratio_err=eratio.tolist(), inclusive_ratio=float(inc), inclusive_err=float(einc),
               chi2=chi2, ndf=len(obs), slope_per100GeV=float(cs[1]), slope_err=float(ecs[1]),
               max_abs_dev=float(np.max(np.abs(ratio - 1))), tf_mc=tf.tolist(), tf_mc_err=etf.tolist())
    os.makedirs("out", exist_ok=True)
    json.dump(out, open("out/closure_mc_a.json", "w"), indent=1)
    print(f"INCL_RATIO={inc:.4f}+-{einc:.4f} CHI2={chi2:.1f}/{len(obs)} SLOPE={cs[1]:.4f}+-{ecs[1]:.4f}/100GeV MAXDEV={out['max_abs_dev']:.3f}")
    print("RATIO=" + ",".join(f"{q:.3f}" for q in ratio))
    return 0


if __name__ == "__main__":
    sys.exit(main())
