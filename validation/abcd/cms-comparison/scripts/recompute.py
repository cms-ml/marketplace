#!/usr/bin/env python3
"""Recompute the students' inclusive ABCD prediction and the unblinded chi2 from their
fits/*.json (CMS Open Data 2016 G+H, private work; not a CMS result).

Usage: python3 scripts/recompute.py      (from cms-comparison/)
Writes out/recompute.json; KEY=VALUE summary on stdout.
"""
import json, os, sys
import numpy as np
from scipy.stats import chi2 as chi2d, norm

WSA, WSB = "../ws_skill", "../ws_noskill"


def abcd_incl(B, C, D, oB=0.0, oC=0.0, oD=0.0, vB=None, vC=None, vD=None):
    b, c, d = B - oB, C - oC, D - oD
    vB = B if vB is None else vB; vC = C if vC is None else vC; vD = D if vD is None else vD
    p = b * c / d
    return p, p * np.sqrt(vB / b**2 + vC / c**2 + vD / d**2)


def chi2_full(obs, pred, cov):
    r = obs - pred
    V = cov + np.diag(np.maximum(obs, 1))
    c2 = float(r @ np.linalg.solve(V, r))
    return c2, r / np.sqrt(np.diag(V))


def pval(c2, ndf):
    return float(chi2d.sf(c2, ndf))


def sig(p):
    return float(norm.isf(p / 2)) if p > 0 else float("inf")


def run_a():
    p = json.load(open(f"{WSA}/fits/prediction.json"))
    r = json.load(open(f"{WSA}/results.json"))
    fin = json.load(open(f"{WSA}/fits/final.json"))
    B, C, D = (np.array(p[k], float) for k in ("data_B", "data_C", "data_D"))
    obs = np.array(p["observed_A"], float)
    q = np.array(p["predicted_QCD_A"]); st = np.array(p["stat_err"]); sy = np.array(p["syst_err"])
    oth = np.array(p["other_bkg_yield_A"]); tot = np.array(p["predicted_total_A_QCD_plus_other"])
    tff = np.array(p["tf_fit"])
    raw, eraw = abcd_incl(B.sum(), C.sum(), D.sum())
    # implied fraction of C kept after non-QCD subtraction: pred = (C - oC) * TF_fit
    keepC = q / (C * tff)
    # TF definition check: tf_B_over_D == B/D only if no subtraction
    out = dict(
        N=dict(B=B.sum(), C=C.sum(), D=D.sum(), A_obs=obs.sum()),
        incl_raw_BCoverD=raw, incl_raw_err=eraw,
        incl_raw_plus_nothing_vs_obs=obs.sum() / raw,
        student_qcd_sum=q.sum(), student_qcd_plus_other=tot.sum(), student_total_err=r["prediction"]["total_err"],
        student_other_A=oth.sum(),
        err_uncorr=float(np.sqrt((st**2 + sy**2).sum())), err_fullcorr=float((np.sqrt(st**2 + sy**2)).sum()),
        implied_C_keep_fraction=[float(keepC.min()), float(keepC.max())],
        obs_over_pred_total=obs.sum() / tot.sum(),
    )
    # chi2 variants
    c_stat, pul_stat = chi2_full(obs, tot, np.diag(st**2))
    c_diag, pul_diag = chi2_full(obs, tot, np.diag(st**2 + sy**2))
    # rebuild student covariance: corr yield (syst_corr) + shape terms + other-bkg terms are in syst_err; approximate
    corr = fin["syst_corr"]
    shape = np.array(fin["shape_term"])
    cov_rebuilt = np.diag(st**2) + np.outer(q, q) * corr**2 + np.diag((shape * q) ** 2) + np.diag(np.maximum(sy**2 - (corr * q) ** 2 - (shape * q) ** 2, 0))
    c_cov, pul_cov = chi2_full(obs, tot, cov_rebuilt)
    nb = len(obs)
    out["chi2"] = dict(
        student=dict(chi2=r["unblinded"]["chi2"], ndf=r["unblinded"]["ndf"], max_local=r["unblinded"]["max_local_deviation_sigma"]),
        stat_only=dict(chi2=c_stat, ndf=nb, p=pval(c_stat, nb), max_pull=float(np.abs(pul_stat).max()), argmax_bin=int(np.abs(pul_stat).argmax())),
        diag_stat_syst=dict(chi2=c_diag, ndf=nb, p=pval(c_diag, nb), max_pull=float(np.abs(pul_diag).max())),
        rebuilt_cov=dict(chi2=c_cov, ndf=nb, p=pval(c_cov, nb), max_pull=float(np.abs(pul_cov).max())),
        student_p=pval(r["unblinded"]["chi2"], r["unblinded"]["ndf"]),
    )
    out["pulls_stat_only"] = pul_stat.tolist()
    out["obs_over_pred"] = (obs / tot).tolist()
    out["rel_syst"] = (sy / q).tolist()
    out["rel_stat"] = (st / q).tolist()
    return out


def run_b():
    p = json.load(open(f"{WSB}/fits/prediction.json"))
    r = json.load(open(f"{WSB}/results.json"))
    br = json.load(open(f"{WSB}/fits/blind_results.json"))
    B, C, D = (np.array(p[k], float) for k in ("data_B", "data_C", "data_D"))
    oB, oC, oD = (np.array(p[k], float) for k in ("other_bkg_B", "other_C", "other_D"))
    obs = np.array(p["observed_A"], float)
    q = np.array(p["pred_qcd_A"]); st = np.array(p["stat_err"]); sy = np.array(p["syst_err"])
    oth = np.array(p["other_bkg_A"]); eoth = np.array(br["other_A_err"])
    tot = q + oth
    raw, eraw = abcd_incl(B.sum(), C.sum(), D.sum())
    sub, esub = abcd_incl(B.sum(), C.sum(), D.sum(), oB.sum(), oC.sum(), oD.sum())
    perbin = (B - oB) * (C - oC) / (D - oD)
    out = dict(
        N=dict(B=B.sum(), C=C.sum(), D=D.sum(), A_obs=obs.sum()),
        incl_raw_BCoverD=raw, incl_raw_err=eraw, incl_sub=sub, incl_sub_err=esub,
        student_inclTF=float(np.sum(br["pred_inclusiveTF"])),
        perbin_recomputed_sum=float(perbin.sum()), perbin_max_rel_diff=float(np.max(np.abs(perbin / q - 1))),
        student_qcd_sum=q.sum(), student_qcd_plus_other=tot.sum(), student_total_err=r["prediction"]["total_err"],
        stat_quad=float(np.sqrt((st**2).sum())), syst_linear=float(sy.sum()), syst_quad=float(np.sqrt((sy**2).sum())),
        obs_over_pred_total=obs.sum() / tot.sum(), incl_raw_plus_other_vs_obs=obs.sum() / (raw + oth.sum()),
    )
    nb = len(obs)
    c_stat, pul_stat = chi2_full(obs, tot, np.diag(st**2 + eoth**2))
    c_diag, pul_diag = chi2_full(obs, tot, np.diag(st**2 + sy**2 + eoth**2))
    # 5% flat term fully correlated (as the student says it is a common data-vs-MC rho shift), rest per bin
    nc = np.array(br["nonclosure_rel"]); so = np.array(br["syst_other"])
    rest = np.sqrt(np.maximum(nc**2 - 0.05**2, 0)) * q
    cov_c = np.diag(st**2 + eoth**2 + rest**2) + np.outer(so, so) + np.outer(0.05 * q, 0.05 * q)
    c_corr, pul_corr = chi2_full(obs, tot, cov_c)
    out["chi2"] = dict(
        student=dict(chi2=r["unblinded"]["chi2"], ndf=r["unblinded"]["ndf"], max_local=r["unblinded"]["max_local_deviation_sigma"]),
        stat_only=dict(chi2=c_stat, ndf=nb, p=pval(c_stat, nb), max_pull=float(np.abs(pul_stat).max()), argmax_bin=int(np.abs(pul_stat).argmax())),
        diag_stat_syst=dict(chi2=c_diag, ndf=nb, p=pval(c_diag, nb), max_pull=float(np.abs(pul_diag).max())),
        flat5_correlated=dict(chi2=c_corr, ndf=nb, p=pval(c_corr, nb), max_pull=float(np.abs(pul_corr).max())),
        student_p=pval(r["unblinded"]["chi2"], r["unblinded"]["ndf"]),
    )
    out["pulls_stat_only"] = pul_stat.tolist()
    out["obs_over_pred"] = (obs / tot).tolist()
    out["rel_syst"] = (sy / q).tolist()
    out["rel_stat"] = (st / q).tolist()
    # MC closure summary (per bin) from their blind_results
    cl = br["closure"]
    out["mc_closure_tests"] = {k: dict(ratio_incl=cl[k]["ratio_incl"], chi2=cl[k]["chi2"], ndf=cl[k]["ndf"]) for k in cl}
    return out


def main():
    res = {"note": "CMS Open Data 2016 G+H, private work; not a CMS result", "A": run_a(), "B": run_b()}
    os.makedirs("out", exist_ok=True)
    json.dump(res, open("out/recompute.json", "w"), indent=1, default=float)
    for k in ("A", "B"):
        x = res[k]
        print(f"{k}_INCL_RAW={x['incl_raw_BCoverD']:.0f}+-{x['incl_raw_err']:.0f} {k}_STUDENT_QCD={x['student_qcd_sum']:.0f} "
              f"{k}_STUDENT_TOT={x['student_qcd_plus_other']:.0f}+-{x['student_total_err']:.0f} {k}_OBS={x['N']['A_obs']:.0f}")
        for t, v in x["chi2"].items():
            print(f"{k}_CHI2_{t}={v}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
