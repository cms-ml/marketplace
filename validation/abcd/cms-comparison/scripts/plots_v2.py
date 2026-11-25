#!/usr/bin/env python3
"""Extra validation plots: with-skill and without-skill student runs (CMS Open Data, private work)
vs CMS EXO-17-021 (HEPData ins1685989 table 348181; Fig. 2 and Fig. 4 values extracted from the
vector graphics of arXiv:1808.03124, ref/cms_extracted/, validated upstream).

Inputs: out/{compare_cms,recompute,cmslike,tests_perbin}.json, ../ws_*/fits/*.json, ref/.
Outputs: plots/{mavg_SR_vs_cms,cmslike_od_vs_cms,tf_vs_mavg_vs_cms,fig2_<var>,syst_breakdown_vs_cms,
closure_heatmap,nonclosure_heatmap}.{png,pdf} and out/plots_v2.json (key numbers).
Usage: python3 scripts/plots_v2.py
"""
import json, os, sys
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.optimize import curve_fit
from scipy.stats import chi2 as chi2d

WSA, WSB = "../ws_skill", "../ws_noskill"
COL = {"A": "#2a78d6", "B": "#eb6834", "emu": "#1baf7a", "cms": "#333333", "mc": "#e87ba4"}
NAME = {"A": "with skill", "B": "without skill"}
OD = "CMS Open Data, private work"
CMSL = "CMS EXO-17-021"
L = 35.9 / 16.3
KEY = {}


def label(ax, left=OD, right="16.3 fb$^{-1}$ (13 TeV)"):
    ax.text(0.0, 1.01, left, transform=ax.transAxes, fontsize=10, fontweight="bold", va="bottom")
    ax.text(1.0, 1.01, right, transform=ax.transAxes, fontsize=9, ha="right", va="bottom")


def save(fig, name):
    fig.savefig(f"plots/{name}.png", dpi=110, bbox_inches="tight"); fig.savefig(f"plots/{name}.pdf", bbox_inches="tight"); plt.close(fig)


def csv(name):
    rows = [l.strip().split(",") for l in open(f"ref/cms_extracted/{name}") if l[0] not in "#lm"]
    return np.array([[float(x) for x in r] for r in rows])


def load_cms():
    t = json.load(open("ref/table_348181.json"))["values"]
    g = lambda i, k: np.array([float(v["y"][i][k] if k == "value" else v["y"][i]["errors"][0]["symerror"]) for v in t])
    lo = np.array([float(v["x"][0]["low"]) for v in t]); hi = np.array([float(v["x"][0]["high"]) for v in t])
    return dict(edges=np.append(lo, hi[-1]), lo=lo, hi=hi, data=g(0, "value"), edata=g(0, "e"), bkg=g(1, "value"), ebkg=g(1, "e"))


def rebin_density(lo, hi, dens, err, edges):
    val, e = np.zeros(len(edges) - 1), np.zeros(len(edges) - 1)
    for i in range(len(edges) - 1):
        ov = np.clip(np.minimum(hi, edges[i + 1]) - np.maximum(lo, edges[i]), 0, None)
        val[i] = np.sum(ov * dens); e[i] = np.sum(ov * err)
    return val, e


def student(run):
    if run == "A":
        p = json.load(open(f"{WSA}/fits/prediction.json"))
        return dict(edges=np.array(p["edges"]), pred=np.array(p["predicted_total_A_QCD_plus_other"]), qcd=np.array(p["predicted_QCD_A"]),
                    stat=np.array(p["stat_err"]), syst=np.array(p["syst_err"]), obs=np.array(p["observed_A"], float), p=p)
    p = json.load(open(f"{WSB}/fits/prediction.json")); br = json.load(open(f"{WSB}/fits/blind_results.json"))
    return dict(edges=np.array(p["edges"]), pred=np.array(p["pred_qcd_A"]) + np.array(p["other_bkg_A"]), qcd=np.array(p["pred_qcd_A"]),
                stat=np.hypot(np.array(p["stat_err"]), np.array(br["other_A_err"])), syst=np.array(p["syst_err"]), obs=np.array(p["observed_A"], float), p=p, br=br)


def sigmoid(m, p0, p1, p2, p3):
    x = m / 100.0
    return 1.0 / (p0 + np.exp(np.clip(p1 + p2 * x**2 - p3 * x**3, -50, 50)))


# ------------------------------------------------------------------ plot 1
def plot_mavg(cms, S, C):
    fig, axs = plt.subplots(4, 2, figsize=(14, 16), sharex="col", gridspec_kw=dict(height_ratios=[3, 1.2, 3, 1.2], hspace=0.07))
    for j, run in enumerate("AB"):
        s = S[run]; e = s["edges"]; c = C[run]; ce = np.array(c["common_edges"])
        sel = (e[:-1] >= ce[0] - 1e-6) & (e[1:] <= ce[-1] + 1e-6)
        sp, so = s["pred"][sel], s["obs"][sel]; tot = np.hypot(s["stat"], s["syst"])[sel]
        cb, ceb = rebin_density(cms["lo"], cms["hi"], cms["bkg"], cms["ebkg"], ce)
        cd, ced = rebin_density(cms["lo"], cms["hi"], cms["data"], cms["edata"], ce)
        w = np.diff(ce); mc = 0.5 * (ce[1:] + ce[:-1]); k = sp.sum() / cb.sum()
        ax = axs[0, j]
        ax.stairs((sp + tot) / w, ce, baseline=(sp - tot) / w, fill=True, color=COL[run], alpha=0.25, lw=0)
        ax.stairs(sp / w, ce, color=COL[run], lw=2, label=f"{OD} ({NAME[run]}): ABCD prediction, stat$\\oplus$syst")
        ax.errorbar(mc, so / w, np.sqrt(so) / w, xerr=w / 2, fmt="o", ms=4, color="k", label=f"{OD} ({NAME[run]}): observed in A")
        ax.stairs(k * (cb + ceb) / w, ce, baseline=k * (cb - ceb) / w, fill=True, color="0.6", alpha=0.35, lw=0, hatch="//")
        ax.stairs(k * cb / w, ce, color=COL["cms"], lw=2, ls="--", label=f"{CMSL} bkg. (HEPData), normalised to the prediction")
        ax.set_yscale("log"); ax.set_ylabel("Events / GeV (16.3 fb$^{-1}$)"); ax.legend(fontsize=8, loc="lower left")
        label(ax, OD); ax.text(0.98, 0.96, f"{NAME[run]}: shape (normalised to the prediction)", transform=ax.transAxes, ha="right", va="top", fontsize=10)
        rx = axs[1, j]; rx.axhline(1, color="0.5", lw=1)
        rx.stairs(1 + tot / sp, ce, baseline=1 - tot / sp, fill=True, color=COL[run], alpha=0.25, lw=0)
        rx.errorbar(mc, so / sp, np.sqrt(so) / sp, fmt="o", ms=4, color="k", label="observed / prediction")
        sf = c["shape_full_unc"]
        rx.errorbar(mc + 2, sf["ratio"], sf["ratio_err"], fmt="D", ms=4, color=COL["cms"], label=f"prediction / {CMSL} (normalised)")
        rx.set_ylim(0, 3.2 if run == "B" else 2.0); rx.set_ylabel("Ratio"); rx.legend(fontsize=7.5, ncol=2, loc="upper left")
        rx.text(0.98, 0.06, f"shape $\\chi^2$/ndf = {sf['chi2']:.0f}/{sf['ndf']}, slope {sf['slope_per100GeV']:+.2f}$\\pm${sf['slope_err']:.2f} /100 GeV",
                transform=rx.transAxes, ha="right", fontsize=8)
        # absolute
        ax = axs[2, j]; ef = s["edges"]; wf = np.diff(ef); mf = 0.5 * (ef[1:] + ef[:-1]); totf = np.hypot(s["stat"], s["syst"])
        ax.stairs(L * (s["pred"] + totf) / wf, ef, baseline=L * (s["pred"] - totf) / wf, fill=True, color=COL[run], alpha=0.25, lw=0)
        ax.stairs(L * s["pred"] / wf, ef, color=COL[run], lw=2, label=f"{OD} ({NAME[run]}): prediction $\\times$35.9/16.3")
        ax.errorbar(mf, L * s["obs"] / wf, L * np.sqrt(s["obs"]) / wf, xerr=wf / 2, fmt="o", ms=4, color="k", label=f"{OD} ({NAME[run]}): observed $\\times$35.9/16.3")
        cw = cms["hi"] - cms["lo"]; cm = 0.5 * (cms["hi"] + cms["lo"])
        ax.stairs(cms["bkg"] + cms["ebkg"], cms["edges"], baseline=cms["bkg"] - cms["ebkg"], fill=True, color="0.6", alpha=0.35, lw=0, hatch="//")
        ax.stairs(cms["bkg"], cms["edges"], color=COL["cms"], lw=2, ls="--", label=f"{CMSL} bkg. (HEPData), 35.9 fb$^{{-1}}$, pruned mass")
        ax.errorbar(cm, cms["data"], cms["edata"], xerr=cw / 2, fmt="s", ms=3, mfc="none", color=COL["cms"], label=f"{CMSL} data (HEPData)")
        ax.set_yscale("log"); ax.set_ylabel("Events / GeV (35.9 fb$^{-1}$)"); ax.legend(fontsize=8, loc="lower left")
        label(ax, OD, "35.9 fb$^{-1}$ (13 TeV)"); ax.text(0.98, 0.96, f"{NAME[run]}: absolute, scaled 35.9/16.3", transform=ax.transAxes, ha="right", va="top", fontsize=10)
        rx = axs[3, j]
        r = L * sp / cb; er = r * np.hypot(tot / sp, ceb / cb)
        rx.errorbar(mc, r, er, xerr=w / 2, fmt="o", ms=4, color=COL[run], label=f"{NAME[run]} prediction (scaled) / {CMSL} bkg.")
        ro = L * so / cd
        rx.errorbar(mc + 2, ro, ro * np.hypot(1 / np.sqrt(so), ced / cd), fmt="s", ms=4, mfc="none", color="k", label=f"{NAME[run]} observed (scaled) / {CMSL} data")
        rx.axhline(1, color="0.5", lw=1); rx.set_yscale("log"); rx.set_ylim(0.3, 30); rx.set_ylabel("Ratio to CMS"); rx.set_xlabel(r"$m_{avg}$ [GeV]")
        rx.legend(fontsize=7.5, loc="upper left"); rx.text(0.98, 0.06, f"integral ratio {c['level']['ratio_pred_scaled_over_cms']:.2f}", transform=rx.transAxes, ha="right", fontsize=8)
        KEY[f"mavg_SR_vs_cms_{run}"] = dict(shape_chi2=sf["chi2"], ndf=sf["ndf"], slope=sf["slope_per100GeV"], slope_err=sf["slope_err"],
                                          level_ratio=c["level"]["ratio_pred_scaled_over_cms"], perbin_level_ratio_range=[float(r.min()), float(r.max())])
    save(fig, "mavg_SR_vs_cms")


# ------------------------------------------------------------------ plot 2
def plot_cmslike(cms, E, C):
    f = C["emulation"]["lumi_frac_from_runA"]; ed = cms["edges"]; w = np.diff(ed); m = 0.5 * (ed[1:] + ed[:-1])
    d, q = E["data"], E["qcd"]
    A = np.array(d["cms_A"]); Cr = np.array(d["cms_C"])
    te = np.array(E["tf_edges"]); tm = 0.5 * (te[1:] + te[:-1])
    tB, tD = np.array(d["tf_B"]), np.array(d["tf_D"]); ok = (tB > 0) & (tD > 0)
    tf = tB[ok] / tD[ok]; etf = tf * np.sqrt(1 / tB[ok] + 1 / tD[ok])
    try:
        par, cov = curve_fit(sigmoid, tm[ok], tf, p0=[1.6, 2.0, -0.5, 0.0], sigma=etf, absolute_sigma=True, maxfev=50000, bounds=([0.0, -20, -20, 0.0], [50, 20, 20, 20])); form = "sigmoid (CMS Eq. 2)"
        tfm = sigmoid(m, *par)
        fchi2 = float(np.sum(((tf - sigmoid(tm[ok], *par)) / etf) ** 2)); fndf = int(ok.sum() - 4)
    except Exception:
        co = np.polyfit(tm[ok], tf, 2, w=1 / etf); tfm = np.polyval(co, m); form = "quadratic"; fchi2 = float("nan"); fndf = int(ok.sum() - 3)
    pred = Cr * tfm; epred = np.sqrt(Cr) * tfm
    sc = L / f
    qA = np.array(q["cms_A"]) * L; eqA = np.sqrt(np.array(q["cms_A_w2"])) * L
    fig, axs = plt.subplots(2, 2, figsize=(15, 9), sharex=True, gridspec_kw=dict(height_ratios=[3, 1.3], hspace=0.06))
    ax = axs[0, 0]
    ax.errorbar(m, sc * A / w, sc * np.sqrt(A) / w, xerr=w / 2, fmt="o", ms=4, color=COL["emu"], label=f"{OD}: CMS-like selection, observed A (4/48 files, scaled to 35.9 fb$^{{-1}}$)")
    ax.stairs(sc * pred / w, ed, color=COL["emu"], lw=1.5, label=f"{OD}: CMS-like ABCD prediction C$\\times$TF ({form}), scaled")
    ax.stairs(qA / w, ed, color=COL["mc"], lw=1.5, ls=":", label=f"{OD}: QCD MC (subset), CMS-like A, $\\sigma\\times$35.9 fb$^{{-1}}$")
    ax.stairs(cms["bkg"] + cms["ebkg"], ed, baseline=cms["bkg"] - cms["ebkg"], fill=True, color="0.6", alpha=0.35, lw=0, hatch="//")
    ax.stairs(cms["bkg"], ed, color=COL["cms"], lw=2, ls="--", label=f"{CMSL} bkg. (HEPData)")
    ax.errorbar(m, cms["data"], cms["edata"], fmt="s", ms=3, mfc="none", color=COL["cms"], label=f"{CMSL} data (HEPData)")
    ax.set_yscale("log"); ax.set_ylabel("Events / GeV (35.9 fb$^{-1}$)"); ax.legend(fontsize=7.5, loc="lower left"); ax.set_ylim(1e-2, 1e4); label(ax, f"{OD} vs {CMSL} (absolute)", "")
    rx = axs[1, 0]; rx.axhline(1, color="0.5")
    rd = sc * A / w / cms["data"]
    rx.errorbar(m, rd, rd * np.hypot(1 / np.sqrt(np.maximum(A, 1)), cms["edata"] / cms["data"]), fmt="o", ms=4, color=COL["emu"], label="Open Data CMS-like observed / CMS data")
    rx.errorbar(m + 2, qA / w / cms["bkg"], eqA / w / cms["bkg"], fmt="^", ms=4, mfc="none", color=COL["mc"], label="QCD MC / CMS bkg.")
    rx.set_ylim(0, 5); rx.set_ylabel("Ratio to CMS"); rx.set_xlabel(r"$m_{avg}$ [GeV]"); rx.legend(fontsize=7.5, loc="upper left")
    # normalised (64-503)
    ax = axs[0, 1]; nA = A / A.sum(); nC = cms["data"] * w / np.sum(cms["data"] * w); nB = cms["bkg"] * w / np.sum(cms["bkg"] * w); nP = pred / pred.sum(); nQ = qA / qA.sum()
    ax.errorbar(m, nA / w, np.sqrt(A) / A.sum() / w, xerr=w / 2, fmt="o", ms=4, color=COL["emu"], label=f"{OD}: CMS-like observed A")
    ax.stairs(nP / w, ed, color=COL["emu"], lw=1.5, label=f"{OD}: CMS-like ABCD prediction")
    ax.stairs(nQ / w, ed, color=COL["mc"], lw=1.5, ls=":", label=f"{OD}: QCD MC, CMS-like A")
    ax.stairs(nB / w, ed, color=COL["cms"], lw=2, ls="--", label=f"{CMSL} bkg.")
    ax.errorbar(m, nC / w, cms["edata"] / np.sum(cms["data"] * w), fmt="s", ms=3, mfc="none", color=COL["cms"], label=f"{CMSL} data")
    ax.set_yscale("log"); ax.set_ylim(1e-7, 3e-2); ax.set_ylabel("Fraction / GeV"); ax.legend(fontsize=7.5, loc="lower left"); label(ax, f"{OD} vs {CMSL} (normalised 64-503 GeV)", "")
    rx = axs[1, 1]; rx.axhline(1, color="0.5")
    ea = np.sqrt(np.maximum(A, 1)) / A.sum(); ec = cms["edata"] * w / np.sum(cms["data"] * w)
    rr = nA / nC; err = rr * np.hypot(ea / np.maximum(nA, 1e-12), ec / nC)
    rx.errorbar(m, rr, err, fmt="o", ms=4, color=COL["emu"], label="Open Data observed / CMS data")
    rx.stairs(nP / nB, ed, color=COL["emu"], lw=1.5, label="Open Data ABCD prediction / CMS bkg.")
    rx.set_ylim(0, 3); rx.set_ylabel("Ratio (normalised)"); rx.set_xlabel(r"$m_{avg}$ [GeV]"); rx.legend(fontsize=7.5, loc="upper left")
    okb = A > 0
    c2 = float(np.sum(((nA - nC) ** 2 / (ea**2 + ec**2))[okb])); ndf = int(okb.sum() - 1)
    rx.text(0.98, 0.06, f"obs. shape $\\chi^2$/ndf = {c2:.0f}/{ndf}", transform=rx.transAxes, ha="right", fontsize=8)
    save(fig, "cmslike_od_vs_cms")
    KEY["cmslike_od_vs_cms"] = dict(od_obs_scaled=float(sc * A.sum()), cms_data=float(np.sum(cms["data"] * w)), cms_bkg=float(np.sum(cms["bkg"] * w)),
                                    od_over_cms_data=float(sc * A.sum() / np.sum(cms["data"] * w)), qcd_mc_over_cms_bkg=float(qA.sum() / np.sum(cms["bkg"] * w)),
                                    od_pred_over_obs=float(pred.sum() / A.sum()), tf_form=form, tf_fit_chi2=fchi2, tf_fit_ndf=fndf,
                                    shape_chi2_obs_vs_cms_data=c2, shape_ndf=ndf, shape_p=float(chi2d.sf(c2, ndf)))


# ------------------------------------------------------------------ plot 3
def plot_tf(S, E):
    pts = csv("fig4_points.csv"); fit = csv("fig4_fit.csv"); bg = csv("fig4_band_inclusive_grey.csv"); br = csv("fig4_band_btag_red.csv")
    f4e = np.append(pts[:, 0], pts[-1, 1]).round(0)
    te = np.array(E["tf_edges"])
    def regroup(h):
        idx = [int(np.argmin(np.abs(te - x))) for x in f4e]
        return np.array([np.sum(h[idx[i]:idx[i + 1]]) for i in range(len(idx) - 1)])
    series = {}
    for g, lab, col, mk in (("data", f"{OD}: CMS-like selection, data B/D (4 files)", COL["emu"], "s"), ("qcd", f"{OD}: CMS-like selection, QCD MC B/D", COL["mc"], "^")):
        B = regroup(np.array(E[g]["tf_B"])); D = regroup(np.array(E[g]["tf_D"]))
        B2 = regroup(np.array(E[g]["tf_B_w2"])); D2 = regroup(np.array(E[g]["tf_D_w2"]))
        ok = (B > 0) & (D > 0)
        r = np.where(ok, B / np.where(D > 0, D, 1), np.nan); e = r * np.sqrt(np.where(ok, B2 / np.maximum(B, 1e-9) ** 2 + D2 / np.maximum(D, 1e-9) ** 2, np.nan))
        series[g] = (pts[:, 2], r, e, lab, col, mk)
    pa = S["A"]["p"]; ea = np.array(pa["edges"]); ma = 0.5 * (ea[1:] + ea[:-1])
    Bd, Dd, Cd = (np.array(pa[k], float) for k in ("data_B", "data_D", "data_C"))
    series["A_tf"] = (ma, np.array(pa["tf_B_over_D"]), np.array(pa["tf_B_over_D"]) * np.sqrt(1 / Bd + 1 / Dd), f"{OD} ({NAME['A']}): its TF = N($\\Delta\\eta<1.2$)/N($\\Delta\\eta\\geq1.2$), masym 0.2-0.4", COL["A"], "o")
    series["A_cmsconv"] = (ma, Cd / Dd, Cd / Dd * np.sqrt(1 / Cd + 1 / Dd), f"{OD} ({NAME['A']}): CMS convention N(masym<0.2)/N(0.2-0.4), $\\Delta\\eta\\geq1.2$", COL["A"], "v")
    pb = S["B"]["p"]; eb = np.array(pb["edges"]); mb = 0.5 * (eb[1:] + eb[:-1])
    series["B_tf"] = (mb, np.array(pb["tf"]), np.array(pb["tf_err"]), f"{OD} ({NAME['B']}): its TF = N2 pass/fail of jet 2 (jet 1 fails)", COL["B"], "o")
    cerr = np.where(np.isnan(pts[:, 4]), 0, (pts[:, 5] - pts[:, 4]) / 2)
    def nrm(mm, r, e=None):
        sel = (mm >= 200) & (mm < 400) & np.isfinite(r)
        if e is None: return np.mean(r[sel])
        ee = np.where(e > 0, e, np.nanmedian(e[e > 0]) if np.any(e > 0) else 1)
        return np.sum(r[sel] / ee[sel] ** 2) / np.sum(1 / ee[sel] ** 2)
    fig, axs = plt.subplots(1, 2, figsize=(16, 6.5))
    norms = {}
    for j, ax in enumerate(axs):
        n_c = nrm(pts[:, 2], pts[:, 3], np.where(cerr > 0, cerr, 0.01)) if j else 1.0
        n_f = nrm(fit[:, 0], fit[:, 1]) if j else 1.0
        ax.fill_between(br[:, 0], br[:, 1] / n_f, br[:, 2] / n_f, color="#d55181", alpha=0.25, lw=0, label=f"{CMSL} Fig. 4: fit unc. (b-tagged)")
        ax.fill_between(bg[:, 0], bg[:, 1] / n_f, bg[:, 2] / n_f, color="0.6", alpha=0.5, lw=0, label=f"{CMSL} Fig. 4: fit unc. (inclusive)")
        ax.plot(fit[:, 0], fit[:, 1] / n_f, ":", color="k", lw=2, label=f"{CMSL} Fig. 4: sigmoid fit")
        ax.errorbar(pts[:, 2], pts[:, 3] / n_c, cerr / n_c, xerr=(pts[:, 1] - pts[:, 0]) / 2, fmt="o", ms=6, color="k", label=f"{CMSL} Fig. 4: data B/D (corrected)")
        for k, (mm, r, e, lab, col, mk) in series.items():
            n = nrm(mm, r, e) if j else 1.0; norms[k] = float(n)
            ax.errorbar(mm + (2 if "B" in k else 0), r / n, e / n, fmt=mk, ms=5, mfc="none" if k in ("data", "A_cmsconv", "qcd") else col, color=col, label=lab)
        ax.set_xlabel(r"$m_{avg}$ [GeV] (CMS: pruned, Open Data: soft-drop)"); ax.set_xlim(40, 500)
        ax.set_ylabel("Transfer factor" + (" / mean(200-400 GeV)" if j else "")); ax.set_ylim(0, 3.0 if not j else 2.6)
        label(ax, f"{OD} vs {CMSL}" + (" (normalised to 200-400 GeV)" if j else " (absolute)"), "")
    fig.legend(*axs[0].get_legend_handles_labels(), fontsize=7.5, loc="lower center", ncol=2, bbox_to_anchor=(0.5, -0.17))
    save(fig, "tf_vs_mavg_vs_cms")
    # key numbers: CMS-like data B/D vs CMS points on the Fig. 4 bins
    _, r, e, *_ = series["data"]; ok = np.isfinite(r) & (e > 0)
    c2 = float(np.sum(((r - pts[:, 3]) / np.hypot(e, cerr))[ok] ** 2))
    lo = (pts[:, 2] < 125); KEY["tf_vs_mavg_vs_cms"] = dict(
        od_over_cms_tf_per_bin=(r / pts[:, 3]).tolist(), od_vs_cms_chi2=c2, ndf=int(ok.sum()),
        od_over_cms_low_mass_mean=float(np.nanmean((r / pts[:, 3])[lo])), od_over_cms_200_400=float(np.nanmean((r / pts[:, 3])[(pts[:, 2] >= 200) & (pts[:, 2] < 400)])),
        cms_tf_rise_60_to_225=float(pts[6, 3] / pts[0, 3]), od_tf_rise_60_to_225=float(r[6] / r[0]),
        with_skill_cmsconv_rise_50_to_215=float(series["A_cmsconv"][1][8] / series["A_cmsconv"][1][0]),
        without_skill_tf_rise_50_to_210=float(series["B_tf"][1][8] / series["B_tf"][1][0]), norms=norms)


# ------------------------------------------------------------------ plot 4
def frac_below(edges, h, cut):
    c = np.cumsum(np.concatenate([[0], h])); return float(np.interp(cut, edges, c) / c[-1])


def plot_fig2(E):
    cuts = {"masym": ("<", 0.1, 0.2, 0.2, "$m_{asym}$"), "deta": ("<", 1.5, 1.2, None, r"$\Delta\eta$"),
            "tau21_lead": ("<", 0.45, None, None, r"leading-jet $\tau_{21}$"), "tau21_sub": ("<", 0.45, None, None, r"subleading-jet $\tau_{21}$"),
            "tau32_lead": (">", 0.57, None, None, r"leading-jet $\tau_{32}$"), "tau32_sub": (">", 0.57, None, None, r"subleading-jet $\tau_{32}$")}
    out = {}
    for v, (sgn, ccms, cws, cwo, xl) in cuts.items():
        ref = csv(f"fig2_{v}.csv"); ed = np.append(ref[:, 0], ref[-1, 1]); mid = 0.5 * (ed[1:] + ed[:-1])
        hd = np.array(E["data"][f"n1_{v}"]); hq = np.array(E["qcd"][f"n1_{v}"])
        pd_, pq = hd / hd.sum(), hq / hq.sum(); epd = np.sqrt(hd) / hd.sum()
        cd = np.clip(np.nan_to_num(ref[:, 2]), 0, None); cq = np.clip(np.nan_to_num(ref[:, 3]), 0, None)
        fig, (ax, rx) = plt.subplots(2, 1, figsize=(8, 7.5), sharex=True, gridspec_kw=dict(height_ratios=[3, 1.2], hspace=0.06))
        ax.errorbar(mid, pd_, epd, xerr=np.diff(ed) / 2, fmt="o", ms=4, color=COL["emu"], label=f"{OD}: data (4/48 files), CMS-like N-1")
        ax.stairs(pq, ed, color=COL["mc"], lw=1.8, label=f"{OD}: QCD MC (subset), CMS-like N-1")
        ax.plot(mid, cd, "s", ms=5, mfc="none", color=COL["cms"], label=f"{CMSL} Fig. 2: data (extracted)")
        ax.stairs(cq, ed, color=COL["cms"], lw=1.8, ls="--", label=f"{CMSL} Fig. 2: QCD multijets (extracted)")
        ymax = max(pd_.max(), cd.max(), pq.max()) * 1.35
        ax.axvline(ccms, color="k", ls="-.", lw=1.5, label=f"{CMSL} cut {sgn}{ccms}")
        if cws is not None: ax.axvline(cws, color=COL["A"], ls="--", lw=1.5, label=f"{NAME['A']} cut <{cws}" + (" (fail band to 0.4)" if v == "masym" else ""))
        if cwo is not None: ax.axvline(cwo + 0.004, color=COL["B"], ls=":", lw=2, label=f"{NAME['B']} preselection <{cwo}")
        note = {"masym": "", "deta": f"{NAME['B']}: no $\\Delta\\eta$ cut", "tau21_lead": f"{NAME['A']}: no cut; {NAME['B']}: N2<0.3 instead",
                "tau21_sub": f"{NAME['A']}: no cut; {NAME['B']}: N2<0.3 instead", "tau32_lead": "neither student cuts on $\\tau_{32}$", "tau32_sub": "neither student cuts on $\\tau_{32}$"}[v]
        ax.text(0.98, 0.97, note, transform=ax.transAxes, ha="right", va="top", fontsize=8)
        ax.set_ylim(0, ymax); ax.set_ylabel("Event fraction"); ax.legend(fontsize=7.5, loc="upper left" if v not in ("tau32_lead", "tau32_sub", "tau21_lead", "tau21_sub") else "center left")
        label(ax, f"{OD} vs {CMSL} Fig. 2", "")
        rx.axhline(1, color="0.5")
        ok = cd > 1e-3
        rx.errorbar(mid[ok], pd_[ok] / cd[ok], epd[ok] / cd[ok], fmt="o", ms=4, color=COL["emu"], label="Open Data / CMS (data)")
        okq = cq > 1e-3
        rx.plot(mid[okq], (pq / np.where(cq > 0, cq, 1))[okq], "^", ms=4, mfc="none", color=COL["mc"], label="QCD MC (OD) / CMS QCD")
        rx.set_ylim(0, 3); rx.set_ylabel("OD / CMS"); rx.set_xlabel(xl); rx.legend(fontsize=7.5, loc="upper right")
        fo, fc = frac_below(ed, hd, ccms), frac_below(ed, cd, ccms)
        if sgn == ">": fo, fc = 1 - fo, 1 - fc
        tvd = 0.5 * float(np.sum(np.abs(pd_ - cd / cd.sum())))
        rx.text(0.02, 0.06, f"eff(cut): OD {fo:.3f}, CMS {fc:.3f}; TVD {tvd:.3f}", transform=rx.transAxes, fontsize=8)
        save(fig, f"fig2_{v}")
        out[v] = dict(eff_od=fo, eff_cms=fc, eff_ratio=fo / fc, total_variation_distance=tvd,
                      mean_od=float(np.sum(mid * pd_)), mean_cms=float(np.sum(mid * cd) / cd.sum()))
    out["product_eff_ratio_tau"] = float(np.prod([out[k]["eff_ratio"] for k in ("tau21_lead", "tau21_sub", "tau32_lead", "tau32_sub")]))
    out["product_eff_ratio_all6"] = float(out["product_eff_ratio_tau"] * out["masym"]["eff_ratio"] * out["deta"]["eff_ratio"])
    KEY["fig2"] = out


# ------------------------------------------------------------------ plot 5
def syst_numbers(S):
    res = {}
    s = S["A"]; p = s["p"]; fin = json.load(open(f"{WSA}/fits/final.json"))
    q, tot = s["qcd"], s["pred"]; C = np.array(p["data_C"], float); tff = np.array(p["tf_fit"])
    B, D = np.array(p["data_B"], float), np.array(p["data_D"], float)
    e = np.array(p["edges"]); mc = 0.5 * (e[1:] + e[:-1])
    tf = np.array(p["tf_B_over_D"]); etf = tf * np.sqrt(1 / B + 1 / D)
    co, cv = np.polyfit(mc, tf, 2, w=1 / etf, cov="unscaled"); V = np.vander(mc, 3); ctf = V @ cv @ V.T
    keep = q / (C * tff)
    cstat = np.sqrt(C) * keep * tff
    tffit = np.sqrt(np.maximum(s["stat"] ** 2 - cstat**2, 0))
    Cs = C * keep
    yld = fin["syst_corr"] * q; shp = np.array(fin["shape_term"]) * q
    oth = np.sqrt(np.maximum(s["syst"] ** 2 - yld**2 - shp**2, 0))
    comp = {"non-closure yield": (yld, float(yld.sum())), "non-closure shape": (shp, float(np.sqrt(np.sum(shp**2)))),
            "TF fit / TF stat": (tffit, float(np.sqrt(Cs @ ctf @ Cs))), "shape-region stat": (cstat, float(np.sqrt(np.sum(cstat**2)))),
            "other backgrounds": (oth, float(oth.sum()))}
    res["A"] = {k: dict(perbin_pct=(100 * v / tot).tolist(), min=float(np.min(100 * v / tot)), max=float(np.max(100 * v / tot)), inclusive_pct=100 * i / tot.sum())
                for k, (v, i) in comp.items()}
    res["A"]["_check_tf_fit_perbin_refit_vs_derived"] = [float(np.min(np.sqrt(np.diag(np.outer(Cs, Cs) * ctf)) / np.maximum(tffit, 1e-9))),
                                                         float(np.max(np.sqrt(np.diag(np.outer(Cs, Cs) * ctf)) / np.maximum(tffit, 1e-9)))]
    s = S["B"]; p = s["p"]; br = s["br"]; q, tot = s["qcd"], s["pred"]
    B, oB = np.array(p["data_B"], float), np.array(p["other_bkg_B"])
    nc = np.array(br["nonclosure_rel"]); yld = 0.05 * q; shp = np.sqrt(np.maximum(nc**2 - 0.05**2, 0)) * q
    tfs = np.array(p["tf_err"]) / np.array(p["tf"]) * q; bst = np.sqrt(B) / (B - oB) * q
    oth = np.hypot(np.array(br["syst_other"]), np.array(br["other_A_err"]))
    comp = {"non-closure yield": (yld, float(yld.sum())), "non-closure shape": (shp, float(np.sqrt(np.sum(shp**2)))),
            "TF fit / TF stat": (tfs, float(np.sqrt(np.sum(tfs**2)))), "shape-region stat": (bst, float(np.sqrt(np.sum(bst**2)))),
            "other backgrounds": (oth, float(np.array(br["syst_other"]).sum() + np.sqrt(np.sum(np.array(br["other_A_err"]) ** 2))))}
    res["B"] = {k: dict(perbin_pct=(100 * v / tot).tolist(), min=float(np.min(100 * v / tot)), max=float(np.max(100 * v / tot)), inclusive_pct=100 * i / tot.sum())
                for k, (v, i) in comp.items()}
    res["B"]["_check_stat_quadrature"] = float(np.max(np.abs(np.hypot(tfs, bst) / np.array(p["stat_err"]) - 1)))
    res["B"]["_note"] = "other backgrounds: student varied the subtraction in B,C,D by +-50% but not the non-QCD yield added in A (only its MC stat)"
    res["CMS"] = {"non-closure yield": dict(min=10.0, max=10.0), "non-closure shape": None, "TF fit / TF stat": dict(min=1.0, max=4.0),
                  "shape-region stat": dict(min=1.0, max=23.0), "other backgrounds": dict(min=0.0, max=2.4, note="resonant <8% of bkg: 10% yield -> <=0.8%, MC stat 1-30% -> <=2.4%")}
    return res


def plot_syst(S):
    R = syst_numbers(S); src = ["non-closure yield", "non-closure shape", "TF fit / TF stat", "shape-region stat", "other backgrounds"]
    fig, ax = plt.subplots(figsize=(12, 6))
    for i, sname in enumerate(src):
        for j, (run, col, lab) in enumerate((("A", COL["A"], f"{OD} ({NAME['A']})"), ("B", COL["B"], f"{OD} ({NAME['B']})"), ("CMS", COL["cms"], f"{CMSL} Table 3 (per-bin range)"))):
            x = i + (j - 1) * 0.25; r = R[run][sname]
            if r is None:
                ax.text(x, 0.3, "n/a", ha="center", fontsize=8, color=col); continue
            lo, hi = max(r["min"], 0.1), r["max"]
            if hi - lo < 0.05 * hi:
                ax.plot(x, hi, "_", color=col, ms=22, mew=4, label=(lab + ": per-bin min-max") if i == 0 else None)
            else:
                ax.plot([x, x], [lo, hi], color=col, lw=6, alpha=0.6, solid_capstyle="butt", label=(lab + ": per-bin min-max") if i == 0 else None)
            if "inclusive_pct" in r:
                ax.plot(x, max(r["inclusive_pct"], 0.1), "D", color="k", mfc=col, ms=7, label="inclusive (sum over bins), % of total bkg." if (i == 0 and j == 0) else None)
    ax.set_yscale("log"); ax.set_ylim(0.1, 60); ax.set_xticks(range(len(src))); ax.set_xticklabels(src)
    ax.set_ylabel("uncertainty, % of signal-region background"); ax.legend(fontsize=8, loc="upper right")
    ax.text(0.01, 0.02, "shape-region stat: region C (CMS, with skill), region B (without skill). CMS 'other' is a bound from the resonant fraction (<8%).",
            transform=ax.transAxes, fontsize=7.5)
    label(ax, f"{OD} vs {CMSL}", "")
    save(fig, "syst_breakdown_vs_cms"); KEY["syst_breakdown_vs_cms"] = R


# ------------------------------------------------------------------ plot 7
def plot_kappa(E):
    G = E["kappa_grids"]
    panels = [("cms_pair_cms_sel", f"{OD}: QCD MC, CMS-like selection, CMS pair\nmasym (fail = all above) x $\\Delta\\eta$", "masym boundary", r"$\Delta\eta$ boundary"),
              ("with_skill_pair", f"{OD}: QCD MC, {NAME['A']} selection, its pair\nmasym (fail band cut..cut+0.2) x $\\Delta\\eta$", "masym boundary", r"$\Delta\eta$ boundary"),
              ("with_skill_sel_full_fail", f"{OD}: QCD MC, {NAME['A']} selection\nmasym (fail = all above) x $\\Delta\\eta$", "masym boundary", r"$\Delta\eta$ boundary"),
              ("without_skill_pair", f"{OD}: QCD MC, {NAME['B']} selection, its pair\nN2 jet 1 x N2 jet 2", "N2 jet-1 boundary", "N2 jet-2 boundary")]
    fig, axs = plt.subplots(2, 2, figsize=(16, 13))
    out = {}
    for ax, (k, title, xl, yl) in zip(axs.flat, panels):
        g = G[k]; K = np.array(g["kappa"], float) - 1; Er = np.array(g["err"], float); xc, yc = np.array(g["xcuts"]), np.array(g["ycuts"])
        vmax = 0.4 if k == "without_skill_pair" else 0.15
        im = ax.imshow(K.T, origin="lower", cmap="RdBu_r", vmin=-vmax, vmax=vmax, aspect="auto",
                       extent=[xc[0] - (xc[1] - xc[0]) / 2, xc[-1] + (xc[1] - xc[0]) / 2, yc[0] - (yc[1] - yc[0]) / 2, yc[-1] + (yc[1] - yc[0]) / 2])
        for i, x in enumerate(xc):
            for j, y in enumerate(yc):
                if np.isfinite(K[i, j]): ax.text(x, y, f"{100 * K[i, j]:.0f}", ha="center", va="center", fontsize=6.5, color="k")
        plt.colorbar(im, ax=ax, label=r"$\kappa - 1$ = A$\cdot$D/(B$\cdot$C) $-$ 1")
        marks = g.get("marks", {"with skill": [0.2, 1.2], "CMS": [0.1, 1.5]})
        info = {}
        for nm, (mx, my) in marks.items():
            i = int(np.argmin(np.abs(xc - mx))); j = int(np.argmin(np.abs(yc - my)))
            st = dict(CMS=("*", "k", 18), **{"with skill": ("o", COL["A"], 12), "without skill": ("s", COL["B"], 12)})[nm]
            ax.plot(mx, my, st[0], color=st[1], mfc="none", ms=st[2], mew=2.5, label=f"{nm} point ({mx}, {my}): $\\kappa-1$ = {100 * K[i, j]:+.1f}$\\pm${100 * Er[i, j]:.1f}%")
            info[nm] = dict(kappa_minus_1=float(K[i, j]), err=float(Er[i, j]))
        if k == "without_skill_pair": ax.text(0.02, 0.02, "CMS point (0.1, 1.5) is not on this pair's axes", transform=ax.transAxes, fontsize=8)
        ax.set_xlabel(xl); ax.set_ylabel(yl); ax.set_title(title, fontsize=10); ax.legend(fontsize=7.5, loc="upper right")
        out[k] = dict(min=float(np.nanmin(K)), max=float(np.nanmax(K)), median=float(np.nanmedian(K)), points=info)
    save(fig, "closure_heatmap"); KEY["closure_heatmap"] = out


# ------------------------------------------------------------------ plot 8
def plot_nonclosure(T):
    fig, axs = plt.subplots(2, 1, figsize=(16, 13), gridspec_kw=dict(hspace=0.35))
    out = {}
    for ax, run, key in ((axs[0], "A", "with_skill"), (axs[1], "B", "without_skill")):
        d = T[key]; e = np.array(d["edges"]); tests = d["tests"]
        R = np.array([[np.nan if x is None else x for x in t["ratio"]] for t in tests], float) - 1
        P = np.array([[np.nan if x is None else x for x in t["pull"]] for t in tests], float)
        R[~np.isfinite(R)] = np.nan
        im = ax.pcolormesh(e, np.arange(len(tests) + 1), np.ma.masked_invalid(R), cmap="RdBu_r", vmin=-0.2, vmax=0.2)
        for i in range(len(tests)):
            for j in range(len(e) - 1):
                if np.isfinite(P[i, j]) and np.isfinite(R[i, j]):
                    ax.text(0.5 * (e[j] + e[j + 1]), i + 0.5, f"{P[i, j]:+.1f}", ha="center", va="center", fontsize=7,
                            color="k", fontweight="bold" if abs(P[i, j]) > 3 else "normal")
        ax.set_yticks(np.arange(len(tests)) + 0.5); ax.set_yticklabels([f"{t['test']}  (incl. {t['incl_ratio']:.3f}, $\\chi^2$ {t['chi2']:.0f})" for t in tests], fontsize=8)
        ax.set_xlabel(r"$m_{avg}$ [GeV]"); plt.colorbar(im, ax=ax, label="observed / predicted $-$ 1 (text: pull; bold |pull|>3)")
        label(ax, f"{OD} ({NAME[run]}): non-closure per test and $m_{{avg}}$ bin", "")
        out[run] = {t["test"]: dict(incl=t["incl_ratio"], chi2=t["chi2"], n_pull_gt3=int(np.sum(np.abs(P[i][np.isfinite(P[i])]) > 3)),
                                    max_abs_dev=float(np.nanmax(np.abs(R[i]))) if np.any(np.isfinite(R[i])) else None) for i, t in enumerate(tests)}
    save(fig, "nonclosure_heatmap"); KEY["nonclosure_heatmap"] = out


def main():
    os.makedirs("plots", exist_ok=True)
    cms = load_cms(); C = json.load(open("out/compare_cms.json")); E = json.load(open("out/cmslike.json")); T = json.load(open("out/tests_perbin.json"))
    S = {"A": student("A"), "B": student("B")}
    plot_mavg(cms, S, C); plot_cmslike(cms, E, C); plot_tf(S, E); plot_fig2(E); plot_syst(S); plot_kappa(E); plot_nonclosure(T)
    json.dump(KEY, open("out/plots_v2.json", "w"), indent=1, default=float)
    print("CMSLIKE", {k: v for k, v in KEY["cmslike_od_vs_cms"].items()})
    print("TF", {k: v for k, v in KEY["tf_vs_mavg_vs_cms"].items() if k not in ("od_over_cms_tf_per_bin", "norms")})
    print("FIG2", {k: (round(v["eff_ratio"], 3), round(v["total_variation_distance"], 3)) if isinstance(v, dict) else round(v, 3) for k, v in KEY["fig2"].items()})
    for r in "AB":
        print("SYST", r, {k: (round(v["min"], 1), round(v["max"], 1), round(v["inclusive_pct"], 2)) for k, v in KEY["syst_breakdown_vs_cms"][r].items() if not k.startswith("_")},
              {k: v for k, v in KEY["syst_breakdown_vs_cms"][r].items() if k.startswith("_")})
    print("KAPPA", json.dumps({k: v["points"] for k, v in KEY["closure_heatmap"].items()}))
    print("KAPPA_RANGE", {k: (round(v["min"], 3), round(v["max"], 3)) for k, v in KEY["closure_heatmap"].items()})
    for r in "AB":
        print("NONCL", r, {k: (round(v["incl"], 3), v["n_pull_gt3"]) for k, v in KEY["nonclosure_heatmap"][r].items()})
    return 0


if __name__ == "__main__":
    sys.exit(main())
