#!/usr/bin/env python3
"""Muon tag-and-probe analysis on the Condor pair skims: fits, systematics, POG comparison, G vs H, filter bits.

Usage: analysis.py --skims <dir with output_{G0,G1,H0,H1,mc0,mc1}.npz> [--work <scratch for downloads>]
Writes summary.json and plots/ next to this file. Stdout: progress and KEY=VALUE lines. Units: GeV.
Exit 0 ok, 2 missing inputs.
"""
import argparse
import glob
import json
import math
import os
import subprocess
import sys
import time

import numpy as np

import tnplib as T

HERE = os.path.dirname(os.path.abspath(__file__))
OD = "root://eospublic.cern.ch//eos/opendata/cms"
GOLDEN_URL = f"{OD}/validated-runs/2016/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
LUMI_URL = f"{OD}/luminosity/2016/pp_2016lumibyls.csv"
FIRST_RUN_G = 278820  # Run2016G starts; earlier runs are 2016F (not in the data used here)
WPS = ["tightid", "tightiso", "isomu24"]
VARS = {"bkg_poly2": dict(bkg="poly2"), "window_75_110": dict(mlo=75.0, mhi=110.0),
        "tag_pt33": dict(tag_pt=33.0), "tag_iso005": dict(tag_iso=0.05)}


def fetch(url, dest):
    if not os.path.exists(dest):
        subprocess.run(["xrdcp", "-f", "-s", url, dest], check=True)
    return dest


def binlab(k, eta_e, pt_e):
    hi = pt_e[k[1] + 1]
    return f"eta{eta_e[k[0]]:.1f}-{eta_e[k[0]+1]:.1f}_pt{pt_e[k[1]]:.0f}-{'inf' if hi > 1e3 else int(hi)}"


def pulls_of(rows, key="pull"):
    p = np.array([r[key] for r in rows if r.get(key) is not None and math.isfinite(r[key])])
    return (float(p.mean()), float(np.sqrt((p ** 2).mean())), len(p)) if len(p) else (None, None, 0)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skims", required=True)
    ap.add_argument("--work", default=None, help="scratch directory for the golden JSON and lumi CSV")
    ap.add_argument("--out", default=HERE)
    ap.add_argument("--notes", default=os.path.join(HERE, "large_pull_notes.json"))
    ap.add_argument("--no-plots", action="store_true")
    ap.add_argument("--wps", nargs="+", default=WPS)
    a = ap.parse_args()
    work = a.work or os.path.join(a.skims, ".cache")
    os.makedirs(work, exist_ok=True)
    t0 = time.time()
    fd = sorted(glob.glob(os.path.join(a.skims, "output_[GH]*.npz")))
    fm = sorted(glob.glob(os.path.join(a.skims, "output_mc*.npz")))
    if not fd or not fm:
        print("error: need output_G*.npz, output_H*.npz and output_mc*.npz in --skims", file=sys.stderr)
        return 2
    import iminuit, uproot, awkward, correctionlib, matplotlib, mplhep
    S = {"environment": dict(python=sys.version.split()[0], numpy=np.__version__, iminuit=iminuit.__version__,
                             uproot=uproot.__version__, awkward=awkward.__version__, correctionlib=correctionlib.__version__,
                             mplhep=mplhep.__version__, matplotlib=matplotlib.__version__)}
    dd, info_d, ls_d = T.load_skims(fd)
    dm, info_m, _ = T.load_skims(fm)

    # ---- inputs, certification, luminosity
    golden = T.golden_keys(fetch(GOLDEN_URL, os.path.join(work, "golden.json")))
    lumi_csv = fetch(LUMI_URL, os.path.join(work, "lumibyls.csv"))
    run_ls = ls_d // 100000
    proc = np.intersect1d(ls_d, golden)
    lumi_fb, n_ls_csv, n_ls = T.recorded_lumi_fb(lumi_csv, proc)
    lumiG, _, nG = T.recorded_lumi_fb(lumi_csv, proc[proc // 100000 <= T.G_LAST_RUN])
    lumiH, _, nH = T.recorded_lumi_fb(lumi_csv, proc[proc // 100000 > T.G_LAST_RUN])
    full = golden[golden // 100000 >= FIRST_RUN_G]
    lumi_full, _, n_full = T.recorded_lumi_fb(lumi_csv, full)
    lumi_fullG, _, _ = T.recorded_lumi_fb(lumi_csv, full[full // 100000 <= T.G_LAST_RUN])
    lumi_fullH, _, _ = T.recorded_lumi_fb(lumi_csv, full[full // 100000 > T.G_LAST_RUN])
    files_d = [f for i in info_d for f in i["files"]]
    files_m = [f for i in info_m for f in i["files"]]
    sel_json = json.load(open(os.path.join(HERE, "condor", "input_files.json")))
    S["inputs"] = dict(
        subset_rule="every %d-th file (sorted path order, files 0, 5, 10, ...) of each of the Run2016G and Run2016H SingleMuon listings; all MC files" % sel_json["step"],
        n_files_listed=sel_json["n_listed"], n_data_files_G=len(sel_json["selected"]["G"]), n_data_files_H=len(sel_json["selected"]["H"]),
        n_mc_files=len(files_m), n_data_events=int(sum(f["n_events"] for f in files_d)), n_mc_events=int(sum(f["n_events"] for f in files_m)),
        lumi_fraction_of_full_GH=lumi_fb / lumi_full,
        reason="speed: the validation is a test of the skill, a run-representative subset is enough for a few per mille statistics")
    S["luminosity"] = dict(recorded_fb=lumi_fb, recorded_G_fb=lumiG, recorded_H_fb=lumiH, n_lumisections_processed_and_golden=n_ls,
                           n_lumisections_in_csv=n_ls_csv, n_lumisections_processed=int(len(ls_d)),
                           full_GH_golden_recorded_fb=lumi_full, full_G_fb=lumi_fullG, full_H_fb=lumi_fullH,
                           fraction_of_full_GH=lumi_fb / lumi_full, uncertainty_pct=1.2,
                           source="Open Data record 1059 pp_2016lumibyls.csv, 'recorded' column, summed over the lumi sections present in the processed files and in the golden JSON (record 14220)")
    print(f"lumi {lumi_fb:.3f}/fb (G {lumiG:.3f}, H {lumiH:.3f}); full G+H golden {lumi_full:.3f}/fb; {n_ls_csv}/{n_ls} LS in csv", flush=True)

    # ---- golden JSON on data; era
    key = dd["run"].astype(np.int64) * 100000 + dd["lumi"].astype(np.int64)
    n_before = len(key)
    g = np.isin(key, golden)
    dd = {k: v[g] for k, v in dd.items()}
    isG = dd["run"] <= T.G_LAST_RUN
    cnt = {}
    for nm, d in (("data", dd), ("mc", dm)):
        den, ps = T.wp_masks(d, "tightid")
        cnt[nm] = int(den.sum())
    S["pairs"] = dict(data_pairs_skimmed=n_before, data_pairs_after_golden=int(len(key[g])),
                      data_pairs_nominal_tightid_denominator=cnt["data"], mc_pairs_nominal_tightid_denominator=cnt["mc"],
                      mc_genmatched_tightid_denominator=int(T.wp_masks(dm, "tightid")[0][dm["gen"]].sum()),
                      mc_over_data=cnt["mc"] / cnt["data"], data_pairs_G=int(T.wp_masks(dd, "tightid")[0][isG].sum()),
                      data_pairs_H=int(T.wp_masks(dd, "tightid")[0][~isG].sum()),
                      definition="pairs (each muon once as tag; tag pT>29 GeV tight+iso+trigger-matched; event fired IsoMu24 or IsoTkMu24; 70<m<115 GeV; probe a tracker muon)",
                      mc_statistics_ok=bool(cnt["mc"] >= cnt["data"]))
    for wp in WPS:
        S["pairs"][f"data_{wp}_denominator"] = int(T.wp_masks(dd, wp)[0].sum())
        S["pairs"][f"mc_{wp}_denominator"] = int(T.wp_masks(dm, wp)[0].sum())
    print(json.dumps(S["pairs"]), flush=True)

    # ---- fit self-test against the skill
    ours, skill = T.selftest(dd, dm)
    S["selftest_fit_vs_tnp"] = dict(ours=list(ours), tnp_fit_pass_fail=list(skill), bin="tightid |eta| 0-0.9 pT 30-40")
    print("selftest ours", ours, "skill", skill, flush=True)

    notes = json.load(open(a.notes)) if os.path.exists(a.notes) else {}
    plot_data = {}
    S["wp"] = {}
    for wp in a.wps:
        eta_e, pt_e = T.pog_bins(wp)
        nom = T.measure(dd, dm, wp, keep_hists=True)
        var = {n: T.measure(dd, dm, wp, **kw) for n, kw in VARS.items()}
        print(f"[{wp}] {len(nom)} bins, nominal+{len(var)} variations, {time.time()-t0:.0f} s", flush=True)
        denD = T.wp_masks(dd, wp)[0]
        pt_min = 26.0 if wp == "isomu24" else 15.0
        rows = []
        for k, r in sorted(nom.items()):
            lo, hi = pt_e[k[1]], pt_e[k[1] + 1]
            pog, pun = T.pog_values(wp, eta_e[k[0]], eta_e[k[0] + 1], lo, hi)
            row = dict(label=binlab(k, eta_e, pt_e), aeta=[float(eta_e[k[0]]), float(eta_e[k[0] + 1])],
                       pt=[float(lo), float(hi) if hi < 1e3 else None], **{x: r[x] for x in (
                           "n_data", "n_pass_data", "n_mc", "eff_data", "eff_data_err", "eff_mc", "eff_mc_err", "sf", "sf_stat", "fit_ok")})
            syst = {}
            for n, v in var.items():
                syst[n] = (v[k]["sf"] - r["sf"]) if k in v else 0.0
            tag = syst.pop("tag_pt33"), syst.pop("tag_iso005")
            syst["tag"] = tag[0] if abs(tag[0]) >= abs(tag[1]) else tag[1]
            row["syst_components"] = {"background_shape": syst["bkg_poly2"], "mass_window": syst["window_75_110"], "tag_selection": syst["tag"],
                                      "tag_pt33": tag[0], "tag_iso005": tag[1]}
            row["fit_ok_variations"] = {n: bool(v[k]["fit_ok"]) if k in v else None for n, v in var.items()}
            row["sf_syst"] = math.sqrt(syst["bkg_poly2"] ** 2 + syst["window_75_110"] ** 2 + syst["tag"] ** 2)
            row["sf_total_err"] = math.hypot(row["sf_stat"], row["sf_syst"])
            row["pog_sf"], row["pog_unc"] = pog, pun
            row["pull_stat_only"] = (r["sf"] - pog) / math.hypot(r["sf_stat"], pun)
            row["pull"] = (r["sf"] - pog) / math.hypot(row["sf_total_err"], pun)
            row["sf_over_pog"] = r["sf"] / pog
            # cross-check: POG averaged over the probes of the bin instead of the bin centre
            ig = _bin_index(dd, denD, eta_e, pt_e)[k]
            pa, pua = T.pog_average(wp, dd, ig, pt_min)
            row["pog_sf_avg_over_probes"], row["pog_unc_avg_over_probes"] = pa, pua
            row["pull_pog_avg"] = (r["sf"] - pa) / math.hypot(row["sf_total_err"], pua)
            nt = notes.get(f"{wp}/{row['label']}", {})
            row["note"] = nt.get("note", "") if isinstance(nt, dict) else str(nt)
            row["note_status"] = nt.get("status", "") if isinstance(nt, dict) else ""
            row["low_stat"] = bool(row["sf_stat"] > 0.05)
            rows.append(row)
        mp, rp, n = pulls_of(rows)
        mps, rps, _ = pulls_of(rows, "pull_stat_only")
        mpa, rpa, _ = pulls_of(rows, "pull_pog_avg")
        S["wp"][wp] = dict(pog_correction=T.WP_NAMES[wp], n_bins=n, mean_pull=mp, rms_pull=rp, mean_pull_stat_only=mps,
                           rms_pull_stat_only=rps, mean_pull_pog_avg_over_probes=mpa, rms_pull_pog_avg_over_probes=rpa,
                           n_fit_not_ok=int(sum(not r["fit_ok"] for r in rows)),
                           mean_sf_over_pog_all_bins_unweighted=float(np.mean([r["sf_over_pog"] for r in rows])),
                           weighted_sf_over_pog_30_60GeV=T.weighted_ratio_30_60(rows),
                           large_pull_bins=[r["label"] for r in rows if abs(r["pull"]) > 5], bins=rows)
        print(f"[{wp}] weighted SF/POG 30-60 GeV = {S['wp'][wp]['weighted_sf_over_pog_30_60GeV']:.4f}")
        print(f"[{wp}] N_BINS={n} MEAN_PULL={mp:.3f} RMS_PULL={rp:.3f} (stat only {mps:.2f}/{rps:.2f}; POG averaged {mpa:.2f}/{rpa:.2f}) "
              f"fit-not-ok={S['wp'][wp]['n_fit_not_ok']}", flush=True)
        plot_data[wp] = dict(eta_e=eta_e, pt_e=pt_e, nom=nom, rows=rows)

    # ---- run dependence: G vs H
    S["run_dependence"] = dict(lumi_G_fb=lumiG, lumi_H_fb=lumiH, wp={})
    for wp in a.wps:
        eta_e, pt_e = plot_data[wp]["eta_e"], plot_data[wp]["pt_e"]
        rG = T.measure(dd, dm, wp, sel_d=isG)
        rH = T.measure(dd, dm, wp, sel_d=~isG)
        rows = []
        for k in sorted(set(rG) & set(rH)):
            pog, pun = T.pog_values(wp, eta_e[k[0]], eta_e[k[0] + 1], pt_e[k[1]], pt_e[k[1] + 1])
            d = rG[k]["sf"] - rH[k]["sf"]
            e = math.hypot(rG[k]["sf_stat"], rH[k]["sf_stat"])
            rows.append(dict(label=binlab(k, eta_e, pt_e), aeta=[float(eta_e[k[0]]), float(eta_e[k[0] + 1])],
                             pt=[float(pt_e[k[1]]), float(pt_e[k[1] + 1]) if pt_e[k[1] + 1] < 1e3 else None],
                             sf_G=rG[k]["sf"], sf_G_stat=rG[k]["sf_stat"], sf_H=rH[k]["sf"], sf_H_stat=rH[k]["sf_stat"],
                             eff_data_G=rG[k]["eff_data"], eff_data_H=rH[k]["eff_data"], eff_mc=rG[k]["eff_mc"],
                             sf_G_minus_H=d, sf_G_minus_H_err=e, pull_G_vs_H=d / e, pog_sf=pog,
                             fit_ok_G=rG[k]["fit_ok"], fit_ok_H=rH[k]["fit_ok"]))
        dG = np.array([r["sf_G_minus_H"] for r in rows]); eG = np.array([r["sf_G_minus_H_err"] for r in rows])
        wgt = 1 / eG ** 2
        S["run_dependence"]["wp"][wp] = dict(
            mean_SF_G_minus_H_weighted=float((dG * wgt).sum() / wgt.sum()), err=float(1 / np.sqrt(wgt.sum())),
            chi2_G_vs_H=float(((dG / eG) ** 2).sum()), ndf=int(len(dG)),
            mean_SF_G_over_POG=float(np.mean([r["sf_G"] / r["pog_sf"] for r in rows])),
            mean_SF_H_over_POG=float(np.mean([r["sf_H"] / r["pog_sf"] for r in rows])),
            bins=rows, bins_40_50=[r for r in rows if r["pt"][0] == 40.0])
        print(f"[G vs H {wp}] weighted <SF_G-SF_H> = {S['run_dependence']['wp'][wp]['mean_SF_G_minus_H_weighted']:+.4f} "
              f"+- {S['run_dependence']['wp'][wp]['err']:.4f}, chi2/ndf {S['run_dependence']['wp'][wp]['chi2_G_vs_H']:.1f}/{len(dG)}", flush=True)

    # ---- MC statistics test (skill gotcha: too little MC fakes a bias): tight ID with random fractions of the MC pairs
    if "tightid" in a.wps:
        rng = np.random.default_rng(12345)
        S["mc_statistics_test"] = {}
        eta_e, pt_e = plot_data["tightid"]["eta_e"], plot_data["tightid"]["pt_e"]
        for frac in (0.02, 0.1, 0.5, 1.0):
            sub = rng.random(len(dm["m"])) < frac
            dsub = {k: v[sub] for k, v in dm.items()}
            r = T.measure(dd, dsub, "tightid")
            pl = []
            for k, v in r.items():
                p, pu = T.pog_values("tightid", eta_e[k[0]], eta_e[k[0] + 1], pt_e[k[1]], pt_e[k[1] + 1])
                pl.append((v["sf"] - p) / math.hypot(v["sf_stat"], pu))
            pl = np.array(pl)
            S["mc_statistics_test"][str(frac)] = dict(n_mc_pairs=int(sub.sum()), mc_over_data_pairs=float(sub.sum() / cnt["data"]), n_bins=len(pl),
                                                    mean_pull_stat_only=float(pl.mean()), rms_pull_stat_only=float(np.sqrt((pl ** 2).mean())),
                                                    mean_sf_over_pog=float(np.mean([v["sf"] / T.pog_values("tightid", eta_e[k[0]], eta_e[k[0] + 1], pt_e[k[1]], pt_e[k[1] + 1])[0] for k, v in r.items()])))
            print("[mc stat test]", frac, S["mc_statistics_test"][str(frac)], flush=True)

    # ---- trigger filter bits
    if "isomu24" in a.wps:
        S["filter_bits"], fb_plot = filter_bit_study(dd, dm, isG, plot_data["isomu24"], S["wp"]["isomu24"])
        print(json.dumps({k: v for k, v in S["filter_bits"].items() if not isinstance(v, (list, dict))}), flush=True)

    ex = os.path.join(a.out, "explore_trigger.json")
    if os.path.exists(ex):
        S["trigger_exploration"] = json.load(open(ex))
    S["lumi_note"] = ("POG muon_Z.json.gz covers 2016F(late)+G+H; the data here are G+H only (see run_dependence for the era split)")
    S["runtime_s"] = time.time() - t0
    os.makedirs(a.out, exist_ok=True)
    json.dump(S, open(os.path.join(a.out, "summary.json"), "w"), indent=1, default=_js)
    if not a.no_plots:
        import plotlib
        plotlib.make_all(S, plot_data, dd, dm, os.path.join(a.out, "plots"), lumi_fb)
    print(f"SUMMARY_JSON={os.path.join(a.out, 'summary.json')}")
    return 0


def _js(o):
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, np.bool_):
        return bool(o)
    raise TypeError(type(o))


def _bin_index(d, mask, eta_e, pt_e):
    return T._groups(d, mask, eta_e, pt_e)


def filter_bit_study(dd, dm, isG, pdat, wpsum):
    """How often a probe matched to an Iso/IsoTkMu object (pT >= 24 GeV) is in an event that fired neither path, and its effect."""
    out = {}
    for nm, d in (("data", dd), ("mc", dm)):
        den, _ = T.wp_masks(d, "isomu24", "A")           # denominator without any HLT requirement
        matched = den & ((d["m2pt"] >= 24) | (d["m8pt"] >= 24))
        f = T.fired(d)
        neither = ~f
        o = dict(n_denominator_probes=int(den.sum()), n_matched=int(matched.sum()),
                 n_matched_in_event_fired_neither=int((matched & neither).sum()),
                 fraction_matched_probes_in_event_fired_neither=float((matched & neither).sum() / matched.sum()),
                 fraction_denominator_probes_in_event_fired_neither=float((den & neither).sum() / den.sum()),
                 fraction_bit2_matched_in_neither=float((den & (d["m2pt"] >= 24) & neither).sum() / (den & (d["m2pt"] >= 24)).sum()),
                 fraction_bit8_matched_in_neither=float((den & (d["m8pt"] >= 24) & neither).sum() / (den & (d["m8pt"] >= 24)).sum()))
        # which other paths fired in those events (probes matched, neither IsoMu24 nor IsoTkMu24)
        sel = matched & neither
        o["neither_events_other_paths_fraction"] = {n: float((((d["hlt"][sel] >> b) & 1) != 0).mean()) if sel.sum() else None
                                                    for n, b in T.HLT_BITS.items() if n not in ("IsoMu24", "IsoTkMu24")}
        o["neither_events_no_listed_path_fraction"] = float((d["hlt"][sel] == 0).mean()) if sel.sum() else None
        # same with a higher HLT pT threshold on the object
        for thr in (24, 26, 27):
            mt = den & ((d["m2pt"] >= thr) | (d["m8pt"] >= thr))
            o[f"fraction_matched_in_neither_objpt_ge_{thr}"] = float((mt & neither).sum() / mt.sum())
        out[nm] = o
    # effect on the measurement: skill definition (S), bit-only (A), path-specific (C), bit-2-only (B2), bit-8-only (B8)
    # (the tag match stays the stored OR of bits 2|8 for all variants: it cannot be changed offline)
    res = {t: T.measure(dd, dm, "isomu24", trig=t) for t in ("S", "A", "C", "B2", "B8")}
    eta_e, pt_e = pdat["eta_e"], pdat["pt_e"]
    pog = {k: T.pog_values("isomu24", eta_e[k[0]], eta_e[k[0] + 1], pt_e[k[1]], pt_e[k[1] + 1]) for k in res["S"]}

    def pack(r):
        rows = []
        for k in sorted(r):
            if k not in res["S"]:
                continue
            p, pu = pog[k]
            rows.append(dict(label=binlab(k, eta_e, pt_e), eff_data=r[k]["eff_data"], eff_mc=r[k]["eff_mc"], sf=r[k]["sf"], sf_stat=r[k]["sf_stat"],
                             pog_sf=p, pull_stat_only=(r[k]["sf"] - p) / math.hypot(r[k]["sf_stat"], pu), fit_ok=r[k]["fit_ok"],
                             pt=[float(pt_e[k[1]]), float(pt_e[k[1] + 1])], pt_lo=float(pt_e[k[1]]), aeta_lo=float(eta_e[k[0]])))
        return rows

    defs = {}
    for t, r in res.items():
        rows = pack(r)
        m, rm, _ = pulls_of(rows, "pull_stat_only")
        defs[t] = dict(bins=rows, mean_pull_stat_only=m, rms_pull_stat_only=rm,
                       mean_SF_over_POG_all_bins_unweighted=float(np.mean([x["sf"] / x["pog_sf"] for x in rows])),
                       weighted_SF_over_POG_30_60GeV=T.weighted_ratio_30_60(rows),
                       SF_40_50_by_eta={x["aeta_lo"]: x["sf"] for x in rows if x["pt_lo"] == 40.0},
                       SF_over_POG_40_50_by_eta={x["aeta_lo"]: x["sf"] / x["pog_sf"] for x in rows if x["pt_lo"] == 40.0},
                       mean_eff_data=float(np.mean([x["eff_data"] for x in rows])), mean_eff_mc=float(np.mean([x["eff_mc"] for x in rows])))
    ref = {r["label"]: r for r in defs["S"]["bins"]}
    for t in ("A", "C", "B2", "B8"):
        dsf = [x["sf"] - ref[x["label"]]["sf"] for x in defs[t]["bins"] if x["label"] in ref]
        d_eff_data = [x["eff_data"] - ref[x["label"]]["eff_data"] for x in defs[t]["bins"] if x["label"] in ref]
        dem = [x["eff_mc"] - ref[x["label"]]["eff_mc"] for x in defs[t]["bins"] if x["label"] in ref]
        defs[t]["mean_delta_SF_vs_S"] = float(np.mean(dsf)); defs[t]["max_abs_delta_SF_vs_S"] = float(np.max(np.abs(dsf)))
        defs[t]["mean_delta_eff_data_vs_S"] = float(np.mean(d_eff_data)); defs[t]["mean_delta_eff_mc_vs_S"] = float(np.mean(dem))
        defs[t]["delta_SF_40_50_by_eta"] = {x["aeta_lo"]: x["sf"] - ref[x["label"]]["sf"] for x in defs[t]["bins"] if x["pt_lo"] == 40.0 and x["label"] in ref}
    out["definitions"] = {"S_skill_event_fired_plus_bit2or8_and_pt": "S", "A_bit2or8_and_pt_only_no_HLT": "A", "C_path_specific": "C",
                          "B2_event_fired_bit2_only": "B2", "B8_event_fired_bit8_only": "B8"}
    out["measurement"] = defs
    out["measurement_caveat"] = "the tag match is the stored OR of bits 2|8 and is not varied (skim); only the probe pass definition changes"

    # probe-matched object pT: threshold scan (OR definition S, probe pT bins 26-30, 30-40, 40-50 GeV)
    den_d, _ = T.wp_masks(dd, "isomu24", "S")
    mx = np.maximum(dd["m2pt"], dd["m8pt"])
    matched_d = den_d & (mx >= 24)
    out["fraction_matched_probes_objpt_24_27_data"] = float((matched_d & (mx < 27)).sum() / matched_d.sum())
    scan = {}
    for thr in (24.0, 26.0, 27.0, 30.0):
        r = T.measure(dd, dm, "isomu24", trig="S", thr=thr)
        bins = []
        for k in sorted(r):
            if pt_e[k[1]] in (26.0, 30.0, 40.0):
                bins.append(dict(label=binlab(k, eta_e, pt_e), aeta_lo=float(eta_e[k[0]]), pt_lo=float(pt_e[k[1]]), eff_data=r[k]["eff_data"], eff_mc=r[k]["eff_mc"],
                                 sf=r[k]["sf"], sf_stat=r[k]["sf_stat"], fit_ok=r[k]["fit_ok"], pog_sf=pog[k][0]))
        # all-eta counting efficiency (80 < m < 100 GeV window, no background subtraction) per pT bin
        cnt = {}
        for lo, hi in ((26, 30), (30, 40), (40, 50)):
            for nm, d in (("data", dd), ("mc", dm)):
                den, ps = T.wp_masks(d, "isomu24", "S", thr=thr)
                sel = den & (d["ppt"] >= lo) & (d["ppt"] < hi) & (d["m"] > 80) & (d["m"] < 100)
                if nm == "mc":
                    sel &= d["gen"]
                w = d["w"][sel] if nm == "mc" else np.ones(sel.sum())
                cnt[f"{nm}_{lo}_{hi}"] = float((w * ps[sel]).sum() / w.sum())
        scan[f"{thr:g}"] = dict(bins=bins, counting_alleta_80_100=cnt,
                                weighted_SF_over_POG_26_50=float(np.average([b["sf"] / b["pog_sf"] for b in bins if b["pt_lo"] in (26.0, 30.0, 40.0)],
                                                                            weights=[1 / (b["sf_stat"] / b["pog_sf"]) ** 2 for b in bins if b["pt_lo"] in (26.0, 30.0, 40.0)])))
    out["object_pt_threshold_scan"] = scan
    # headline numbers for the check script / README
    out["fraction_probe_matched_in_event_fired_neither_data"] = out["data"]["fraction_matched_probes_in_event_fired_neither"]
    out["bias_eff_data_A_minus_S_mean"] = defs["A"]["mean_delta_eff_data_vs_S"]
    out["bias_SF_A_minus_S_mean"] = defs["A"]["mean_delta_SF_vs_S"]
    out["bias_SF_C_minus_S_mean"] = defs["C"]["mean_delta_SF_vs_S"]
    out["event_level_bias_negligible"] = bool(abs(defs["A"]["mean_delta_SF_vs_S"]) < 0.002 and abs(defs["C"]["mean_delta_SF_vs_S"]) < 0.002)
    return out, defs


if __name__ == "__main__":
    sys.exit(main())
