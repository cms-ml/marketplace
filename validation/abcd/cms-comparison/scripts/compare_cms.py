#!/usr/bin/env python3
"""Compare the two students' ABCD results (CMS Open Data 2016 G+H, private work) with the
published CMS EXO-17-021 boosted search (HEPData ins1685989, table 348181 = Fig. 5 left).

Inputs (relative to cms-comparison/):
  ref/table_348181.json            HEPData table (fetch_hepdata.sh)
  ../ws_skill/fits/prediction.json ../ws_noskill/fits/prediction.json (+ blind_results.json)
  out/recompute.json out/closure_mc_a.json out/skim_check.json (from the other scripts)
Outputs: out/compare_cms.json, plots/{mavg_A_vs_cms,tf_vs_mavg,closure_summary}.{png,pdf}

Usage: python3 scripts/compare_cms.py
"""
import json, os, sys
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import chi2 as chi2d

WSA, WSB = "../ws_skill", "../ws_noskill"
COL = {"A": "#2a78d6", "B": "#eb6834", "emu": "#1baf7a", "cms": "#333333"}
LUMI_RATIO = 35.9 / 16.3
OD = "CMS Open Data, private work"
NAME = {"A": "with skill", "B": "without skill", "emu": "CMS-like emulation"}


# ---------------------------------------------------------------- HEPData
def load_cms():
    t = json.load(open("ref/table_348181.json"))
    lo = np.array([float(v["x"][0]["low"]) for v in t["values"]])
    hi = np.array([float(v["x"][0]["high"]) for v in t["values"]])
    dat = np.array([float(v["y"][0]["value"]) for v in t["values"]])
    edat = np.array([float(v["y"][0]["errors"][0]["symerror"]) for v in t["values"]])
    bkg = np.array([float(v["y"][1]["value"]) for v in t["values"]])
    ebkg = np.array([float(v["y"][1]["errors"][0]["symerror"]) for v in t["values"]])
    return dict(lo=lo, hi=hi, data=dat, edata=edat, bkg=bkg, ebkg=ebkg)


def rebin_density(lo, hi, dens, err, edges):
    """Integrate a piecewise-constant density (per GeV) into target bins. Errors are summed
    linearly inside a target bin (conservative: CMS bkg errors are correlated) and the
    target bins are treated as independent."""
    n = len(edges) - 1
    val, e = np.zeros(n), np.zeros(n)
    for i in range(n):
        a, b = edges[i], edges[i + 1]
        ov = np.clip(np.minimum(hi, b) - np.maximum(lo, a), 0, None)
        val[i] = np.sum(ov * dens); e[i] = np.sum(ov * err)
    return val, e


# ---------------------------------------------------------------- tests
def norm_cov(x, V):
    s = x.sum(); n = x / s
    J = (np.eye(len(x)) - np.outer(n, np.ones(len(x)))) / s
    return n, J @ V @ J.T


def shape_test(edges, s, Vs, c, Vc):
    """Normalise both over the common range; chi2 with ndf = n-1 (last bin dropped);
    weighted linear fit of the ratio vs m: slope per 100 GeV."""
    ns, Ns = norm_cov(s, Vs); nc, Nc = norm_cov(c, Vc)
    d = (ns - nc)[:-1]; V = (Ns + Nc)[:-1, :-1]
    chi2 = float(d @ np.linalg.solve(V, d)); ndf = len(d)
    r = ns / nc; er = r * np.sqrt(np.diag(Ns) / ns**2 + np.diag(Nc) / nc**2)
    mc = 0.5 * (edges[1:] + edges[:-1])
    A = np.vstack([np.ones_like(mc), (mc - 200) / 100]).T; W = np.diag(1 / er**2)
    cov = np.linalg.inv(A.T @ W @ A); co = cov @ A.T @ W @ r
    return dict(chi2=chi2, ndf=ndf, p=float(chi2d.sf(chi2, ndf)), ratio=r.tolist(), ratio_err=er.tolist(),
                slope_per100GeV=float(co[1]), slope_err=float(np.sqrt(cov[1, 1])),
                slope_sigma=float(co[1] / np.sqrt(cov[1, 1])), ratio_min=float(r.min()), ratio_max=float(r.max()))


def student(run):
    if run == "A":
        p = json.load(open(f"{WSA}/fits/prediction.json"))
        e = np.array(p["edges"]); pred = np.array(p["predicted_total_A_QCD_plus_other"])
        st = np.array(p["stat_err"]); sy = np.array(p["syst_err"]); obs = np.array(p["observed_A"], float)
        tf = dict(m=0.5 * (e[1:] + e[:-1]), tf=np.array(p["tf_B_over_D"]), fit=np.array(p["tf_fit"]),
                  masym_ratio=np.array(p["data_C"]) / np.array(p["data_D"]),
                  emasym=np.array(p["data_C"]) / np.array(p["data_D"]) * np.sqrt(1 / np.array(p["data_C"]) + 1 / np.array(p["data_D"])))
        B, D = np.array(p["data_B"]), np.array(p["data_D"])
        tf["etf"] = tf["tf"] * np.sqrt(1 / B + 1 / D)
    else:
        p = json.load(open(f"{WSB}/fits/prediction.json")); br = json.load(open(f"{WSB}/fits/blind_results.json"))
        e = np.array(p["edges"]); pred = np.array(p["pred_qcd_A"]) + np.array(p["other_bkg_A"])
        st = np.hypot(np.array(p["stat_err"]), np.array(br["other_A_err"])); sy = np.array(p["syst_err"])
        obs = np.array(p["observed_A"], float)
        tf = dict(m=0.5 * (e[1:] + e[:-1]), tf=np.array(p["tf"]), etf=np.array(p["tf_err"]))
    return dict(edges=e, pred=pred, stat=st, syst=sy, obs=obs, tf=tf)


def emulation():
    s = json.load(open("out/skim_check.json"))
    c = s["cms_like"]; e = np.array(c["edges"])
    fa = sum(f["runA_mine"]["A"] for f in s["files"]) / json.load(open(f"{WSA}/results.json"))["n_events"]["A"]
    fb = sum(f["runB_mine"]["A"] for f in s["files"]) / json.load(open(f"{WSB}/results.json"))["n_events"]["A"]
    return dict(edges=e, **{r: np.array(c[r]) for r in "ABCD"}, lumi_frac=fa, lumi_frac_B=fb, files=len(s["files"]))


def hist_on(edges_from, vals, edges_to):
    """Sum histogram contents (fine bins with edges_from) into coarser edges_to (must coincide)."""
    idx = [int(np.argmin(np.abs(edges_from - x))) for x in edges_to]
    assert np.allclose(edges_from[idx], edges_to)
    return np.array([vals[idx[i]:idx[i + 1]].sum() for i in range(len(idx) - 1)])


def label(ax, text=OD, right="16.3 fb$^{-1}$ (13 TeV)"):
    ax.text(0.0, 1.01, text, transform=ax.transAxes, fontsize=11, fontweight="bold", va="bottom")
    ax.text(1.0, 1.01, right, transform=ax.transAxes, fontsize=10, ha="right", va="bottom")


def main():
    os.makedirs("plots", exist_ok=True); os.makedirs("out", exist_ok=True)
    cms = load_cms(); emu = emulation()
    res = {"note": "Students and emulation: CMS Open Data, private work, not CMS results. 'CMS' = EXO-17-021 HEPData ins1685989 table 348181 (Fig. 5 left)."}
    cms_tot = float(np.sum((cms["hi"] - cms["lo"]) * cms["bkg"])); cms_dat = float(np.sum((cms["hi"] - cms["lo"]) * cms["data"]))
    res["cms_totals_64_503"] = dict(bkg=cms_tot, data=cms_dat, data_over_bkg=cms_dat / cms_tot)
    S = {"A": student("A"), "B": student("B")}
    common_hi = {"A": 480.0, "B": 440.0}
    fig, axs = plt.subplots(2, 2, figsize=(14, 9), sharex="col", gridspec_kw=dict(height_ratios=[3, 1.3], hspace=0.05))
    for j, run in enumerate("AB"):
        s = S[run]; e = s["edges"]
        sel = (e[:-1] >= 80) & (e[1:] <= common_hi[run])
        ce = np.concatenate([e[:-1][sel], [e[1:][sel][-1]]])
        sp, sst, ssy, so = s["pred"][sel], s["stat"][sel], s["syst"][sel], s["obs"][sel]
        cb, ceb = rebin_density(cms["lo"], cms["hi"], cms["bkg"], cms["ebkg"], ce)
        cd, ced = rebin_density(cms["lo"], cms["hi"], cms["data"], cms["edata"], ce)
        full = shape_test(ce, sp, np.diag(sst**2 + ssy**2), cb, np.diag(ceb**2))
        # CMS shape-only variant: remove the 10% fully correlated closure (yield) term from the published
        # total, floor at the data stat error (proxy for the region-C count term)
        esh = np.sqrt(np.maximum(cms["ebkg"]**2 - (0.10 * cms["bkg"])**2, cms["edata"]**2))
        _, cebs = rebin_density(cms["lo"], cms["hi"], cms["bkg"], esh, ce)
        shapeonly = shape_test(ce, sp, np.diag(sst**2 + ssy**2), cb, np.diag(cebs**2))
        statonly = shape_test(ce, sp, np.diag(sst**2), cb, np.diag(ceb**2))
        obs_vs_cmsdata = shape_test(ce, so, np.diag(so), cd, np.diag(ced**2))
        # emulation (CMS-like selection on Open Data, 4 files) on the same student bins
        eA, _ = rebin_density(emu["edges"][:-1], emu["edges"][1:], emu["A"] / np.diff(emu["edges"]), 0 * emu["A"], ce)
        emu_vs_cms = shape_test(ce, eA, np.diag(np.maximum(eA, 1)), cb, np.diag(ceb**2))
        stud_vs_emu = shape_test(ce, sp, np.diag(sst**2 + ssy**2), eA, np.diag(np.maximum(eA, 1)))
        # level
        lev = dict(range=[float(ce[0]), float(ce[-1])], cms_bkg=float(cb.sum()), cms_bkg_err_linear=float(ceb.sum()), cms_data=float(cd.sum()),
                   student_obs=float(so.sum()), student_pred=float(sp.sum()),
                   student_obs_scaled=float(so.sum() * LUMI_RATIO), student_pred_scaled=float(sp.sum() * LUMI_RATIO),
                   ratio_pred_scaled_over_cms=float(sp.sum() * LUMI_RATIO / cb.sum()),
                   ratio_obs_scaled_over_cmsdata=float(so.sum() * LUMI_RATIO / cd.sum()),
                   emu_A_scaled=float(eA.sum() / emu["lumi_frac"] * LUMI_RATIO),
                   emu_over_cms_bkg=float(eA.sum() / emu["lumi_frac"] * LUMI_RATIO / cb.sum()),
                   student_over_emu=float(so.sum() / (eA.sum() / emu["lumi_frac"])))
        res[run] = dict(common_edges=ce.tolist(), shape_full_unc=full, shape_cms_shape_only_unc=shapeonly, shape_student_stat_only=statonly,
                        shape_obs_vs_cms_data=obs_vs_cmsdata, shape_emulation_vs_cms=emu_vs_cms,
                        shape_student_vs_emulation=stud_vs_emu, level=lev)
        # ---------------- plot: per-GeV densities, CMS normalised to the student prediction
        w = np.diff(ce); mc = 0.5 * (ce[1:] + ce[:-1])
        k = sp.sum() / cb.sum(); ke = sp.sum() / eA.sum()
        ax, rx = axs[0, j], axs[1, j]
        tot = np.hypot(sst, ssy)
        ax.stairs((sp + tot) / w, ce, baseline=(sp - tot) / w, fill=True, color=COL[run], alpha=0.25, lw=0)
        ax.stairs(sp / w, ce, color=COL[run], lw=2, label=f"{NAME[run]}: ABCD prediction (stat$\\oplus$syst)")
        ax.errorbar(mc, so / w, np.sqrt(so) / w, xerr=w / 2, fmt="o", ms=5, color="k", label=f"{NAME[run]}: observed in A")
        ax.stairs(k * (cb + ceb) / w, ce, baseline=k * (cb - ceb) / w, fill=True, color="0.6", alpha=0.35, lw=0, hatch="//")
        ax.stairs(k * cb / w, ce, color=COL["cms"], lw=2, ls="--", label="CMS EXO-17-021 bkg. prediction (pruned mass, 35.9 fb$^{-1}$), normalised")
        ax.errorbar(mc, ke * eA / w, ke * np.sqrt(eA) / w, fmt="s", ms=5, mfc="none", color=COL["emu"],
                    label="Open Data, CMS-like selection (4/48 files, $m_{SD}$), normalised")
        ax.set_yscale("log"); ax.set_ylabel("Events / GeV"); ax.legend(fontsize=8.5, loc="lower left")
        label(ax, f"{OD} ({NAME[run]})")
        rx.axhline(1, color="0.5", lw=1)
        rx.errorbar(mc, so / sp, np.sqrt(so) / sp, fmt="o", ms=4, color="k", label="obs / pred")
        rx.stairs(1 + tot / sp, ce, baseline=1 - tot / sp, fill=True, color=COL[run], alpha=0.25, lw=0)
        rr = np.array(full["ratio"]); er = np.array(full["ratio_err"])
        rx.errorbar(mc + 2, rr, er, fmt="D", ms=4, color=COL["cms"], label="pred / CMS (both normalised)")
        rx.set_ylim(0, 3.2); rx.set_xlabel(r"$m_{avg}$ [GeV]"); rx.set_ylabel("Ratio"); rx.legend(fontsize=8, ncol=2, loc="upper center")
        rx.text(0.98, 0.05, f"shape $\\chi^2$/ndf = {full['chi2']:.0f}/{full['ndf']}, slope {full['slope_per100GeV']:+.2f}/100 GeV",
                transform=rx.transAxes, ha="right", fontsize=8)
    plt.close(fig)  # superseded by plots/mavg_SR_vs_cms (plots_v2.py)

    # ---------------- emulation ABCD in the CMS layout (data closure) on coarse bins
    ce2 = np.array([64, 100, 137, 174, 217, 265, 318, 503.])
    H = {r: hist_on(emu["edges"], emu[r], ce2) for r in "ABCD"}
    tf_emu = H["B"] / H["D"]; etf_emu = tf_emu * np.sqrt(1 / H["B"] + 1 / H["D"])
    pr = H["C"] * tf_emu; epr = pr * np.sqrt(1 / H["B"] + 1 / H["C"] + 1 / H["D"])
    cl = H["A"] / pr; ecl = np.sqrt(H["A"] / pr**2 + (H["A"] * epr / pr**2) ** 2)
    pin = H["B"].sum() * H["C"].sum() / H["D"].sum(); epin = pin * np.sqrt(sum(1 / H[r].sum() for r in "BCD"))
    res["emulation"] = dict(files=emu["files"], lumi_frac_from_runA=emu["lumi_frac"], lumi_frac_from_runB=emu["lumi_frac_B"],
                            counts={r: float(emu[r][(emu["edges"][:-1] >= 64)].sum()) for r in "ABCD"},
                            incl_closure=float(H["A"].sum() / pin), incl_closure_err=float(np.sqrt(H["A"].sum() / pin**2 + (H["A"].sum() * epin / pin**2) ** 2)),
                            perbin_edges=ce2.tolist(), perbin_closure=cl.tolist(), perbin_closure_err=ecl.tolist(),
                            tf=tf_emu.tolist(), tf_err=etf_emu.tolist(),
                            perbin_chi2=float(np.sum(((cl - 1) / ecl) ** 2)), ndf=len(cl))

    # ---------------- TF plot
    fig, axs = plt.subplots(1, 2, figsize=(14, 5.5))
    ta, tb = S["A"]["tf"], S["B"]["tf"]
    ax = axs[0]
    ax.errorbar(ta["m"], ta["tf"], ta["etf"], fmt="o", ms=5, color=COL["A"], label=r"with skill: TF = B/D = N($\Delta\eta<1.2$)/N($\Delta\eta\geq1.2$), 0.2$\leq m_{asym}<$0.4 (non-QCD subtr.)")
    ax.plot(ta["m"], ta["fit"], "-", color=COL["A"], lw=2, label="with skill: quadratic fit (used)")
    ax.errorbar(ta["m"] + 3, ta["masym_ratio"], ta["emasym"], fmt="^", ms=5, mfc="none", color=COL["A"],
                label=r"with skill data, CMS convention: N($m_{asym}<$0.2)/N(0.2$\leq m_{asym}<$0.4), $\Delta\eta\geq1.2$")
    mc2 = 0.5 * (ce2[1:] + ce2[:-1])
    ax.errorbar(mc2, tf_emu, etf_emu, xerr=np.diff(ce2) / 2, fmt="s", ms=5, mfc="none", color=COL["emu"],
                label=r"Open Data CMS-like: N($m_{asym}<$0.1)/N($m_{asym}>$0.1), $\Delta\eta>1.5$ (4 files)")
    ax.set_xlabel(r"$m_{avg}$ [GeV]"); ax.set_ylabel("Transfer factor"); ax.set_ylim(0, 3.2); ax.legend(fontsize=7.5, loc="upper left")
    label(ax, f"{OD} (with skill)")
    ax = axs[1]
    ax.errorbar(tb["m"], tb["tf"], tb["etf"], fmt="o", ms=5, color=COL["B"], label=r"without skill: TF = C/D = N(N$_2^{(2)}<$0.3)/N(N$_2^{(2)}\geq$0.3), jet 1 fails (per bin, used)")
    ax.set_xlabel(r"$m_{avg}$ [GeV]"); ax.set_ylabel("Transfer factor"); ax.set_ylim(0, 3.2); ax.legend(fontsize=8, loc="upper left")
    ax.text(0.02, 0.72, "CMS EXO-17-021 Fig. 4 (sigmoid TF, masym ratio at $\\Delta\\eta>1.5$)\nis not tabulated in HEPData: not shown, not digitised.",
            transform=ax.transAxes, fontsize=8, color="0.3")
    label(ax, f"{OD} (without skill)")
    plt.close(fig)  # superseded by plots/tf_vs_mavg_vs_cms (plots_v2.py)

    # ---------------- closure summary
    ra = json.load(open(f"{WSA}/results.json")); rb = json.load(open(f"{WSB}/results.json"))
    br = json.load(open(f"{WSB}/fits/blind_results.json")); cma = json.load(open("out/closure_mc_a.json"))
    tests = []
    tests.append(("A", "MC closure (SR)", ra["closure_mc"]["ratio"], abs(ra["closure_mc"]["ratio"] - 1) / abs(ra["closure_mc"]["pull"])))
    for v in ra["validation_regions"]:
        nm = v["definition"].split(":")[0] + ": " + ("x-shift" if "x shifted" in v["definition"] else ("y-shift" if "y shifted" in v["definition"] else "xy-shift"))
        tests.append(("A", nm, v["ratio"], abs(v["ratio"] - 1) / abs(v["pull"])))

    def incl_err(obs, pred, rerr):
        obs, pred, rerr = (np.array(x, float) for x in (obs, pred, rerr))
        ok = np.isfinite(obs / pred) & np.isfinite(rerr) & (pred > 0)
        return float(np.sqrt(np.sum((rerr[ok] * pred[ok]) ** 2)) / pred[ok].sum())
    for k, c in br["closure"].items():
        tests.append(("B", f"MC closure ({k})", c["ratio_incl"], incl_err(c["obs"], c["pred"], c["ratio_err"])))
    for k, v in br["valid"].items():
        tests.append(("B", f"data {k}", v["ratio"], incl_err(v["obs"], v["exp"], v["ratio_err"])))
    tests.append(("emu", "data, A unblinded", res["emulation"]["incl_closure"], res["emulation"]["incl_closure_err"]))
    res["closure_tests"] = [dict(run=a, test=b, ratio=c, err=d) for a, b, c, d in tests]
    fig, axs = plt.subplots(1, 2, figsize=(15, 6), gridspec_kw=dict(width_ratios=[1, 1.3]))
    ax = axs[0]
    ax.axvspan(0.9, 1.1, color="0.85", label="CMS EXO-17-021 MC closure, $\\pm$10% (yield syst.)")
    ax.axvline(1, color="0.4", lw=1)
    for i, (run, nm, r, e) in enumerate(tests):
        mk = "o" if "MC" in nm else ("s" if run != "emu" else "D")
        ax.errorbar(r, i, xerr=e, fmt=mk, ms=6, color=COL[run], mfc=COL[run] if "MC" in nm else "none")
    ax.set_yticks(range(len(tests))); ax.set_yticklabels([f"{NAME[t[0]]}: {t[1]}" for t in tests], fontsize=8)
    ax.invert_yaxis(); ax.set_xlabel("inclusive observed / predicted"); ax.set_xlim(0.85, 1.15); ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.12))
    label(ax, OD + " (all points)", "")
    ax = axs[1]
    ax.axhspan(0.9, 1.1, color="0.85", label="CMS EXO-17-021: MC closure $\\pm$10%")
    ax.axhline(1, color="0.4", lw=1)
    ea = np.array(cma["edges"]); ma = 0.5 * (ea[1:] + ea[:-1])
    ax.errorbar(ma, cma["ratio"], cma["ratio_err"], xerr=np.diff(ea) / 2, fmt="o", ms=5, color=COL["A"], label="with skill: QCD MC closure in A (recomputed)")
    eb = np.array(rb["prediction"]["edges"]); mb = 0.5 * (eb[1:] + eb[:-1]); c = br["closure"]["SR"]
    rbv = np.array(c["ratio_bins"], float); ebv = np.array(c["ratio_err"], float)
    ax.errorbar(mb + 3, rbv, ebv, xerr=np.diff(eb) / 2, fmt="s", ms=5, color=COL["B"], label="without skill: QCD MC closure in A")
    ax.errorbar(mc2, cl, ecl, xerr=np.diff(ce2) / 2, fmt="D", ms=5, mfc="none", color=COL["emu"], label="CMS-like selection on Open Data: data closure (per-bin TF, 4 files)")
    ax.set_ylim(0.6, 1.4); ax.set_xlabel(r"$m_{avg}$ [GeV]"); ax.set_ylabel("observed / predicted"); ax.legend(fontsize=8, loc="upper left")
    label(ax, OD + " (per bin)", "")
    fig.savefig("plots/closure_summary.png", dpi=120, bbox_inches="tight"); fig.savefig("plots/closure_summary.pdf", bbox_inches="tight"); plt.close(fig)

    json.dump(res, open("out/compare_cms.json", "w"), indent=1)
    for run in "AB":
        f = res[run]["shape_full_unc"]; l = res[run]["level"]
        print(f"{run}_SHAPE_CHI2={f['chi2']:.1f}/{f['ndf']} SLOPE={f['slope_per100GeV']:+.3f}+-{f['slope_err']:.3f} "
              f"CMSSHAPEONLY_CHI2={res[run]['shape_cms_shape_only_unc']['chi2']:.1f} STATONLY_CHI2={res[run]['shape_student_stat_only']['chi2']:.1f} OBS_VS_CMSDATA={res[run]['shape_obs_vs_cms_data']['chi2']:.1f} "
              f"EMU_VS_CMS={res[run]['shape_emulation_vs_cms']['chi2']:.1f}/{res[run]['shape_emulation_vs_cms']['ndf']} slope {res[run]['shape_emulation_vs_cms']['slope_per100GeV']:+.3f}+-{res[run]['shape_emulation_vs_cms']['slope_err']:.3f} "
              f"STUD_VS_EMU={res[run]['shape_student_vs_emulation']['chi2']:.1f}")
        print(f"{run}_LEVEL " + " ".join(f"{k}={v:.3g}" if isinstance(v, float) else f"{k}={v}" for k, v in l.items()))
    print("EMU", {k: v for k, v in res["emulation"].items() if k in ("incl_closure", "incl_closure_err", "perbin_chi2", "ndf", "lumi_frac_from_runA", "lumi_frac_from_runB", "counts")})
    print("CMS", res["cms_totals_64_503"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
