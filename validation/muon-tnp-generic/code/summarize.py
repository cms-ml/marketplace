#!/usr/bin/env python3
"""Collect the tnp.py runs of run_all.sh into summary.json, plots/ and results/ (tests a-f of README.md).

Usage: summarize.py <runs dir> <validation dir>
Needs the LCG view (numpy, matplotlib, mplhep, correctionlib, uproot, awkward).
"""
from __future__ import annotations

import json
import math
import os
import re
import shutil
import subprocess
import sys

import numpy as np

R, V = sys.argv[1], sys.argv[2]
PLOTS, RES = os.path.join(V, "plots"), os.path.join(V, "results")
os.makedirs(PLOTS, exist_ok=True)
os.makedirs(RES, exist_ok=True)
LEGACY = ["aeta", "pt", "n_data", "eff_data", "eff_data_err", "eff_mc", "eff_mc_err", "sf", "sf_err",
          "pog_sf", "pog_unc", "pull", "fit_ok"]


def load(name):
    p = os.path.join(R, f"{name}.json")
    if not os.path.exists(p):
        return None
    with open(p) as f:
        return json.load(f)


def out(name):
    p = os.path.join(R, f"{name}.out")
    txt = open(p).read() if os.path.exists(p) else ""
    kv = {k: v.replace(os.path.abspath(R), "<scratch>/runs") for k, v in re.findall(r"^([A-Z_]+)=(.*)$", txt, re.M)}
    m = re.search(r"^EXIT (\d+)", txt, re.M)
    log = os.path.join(R, f"{name}.log")
    t = re.search(r"TIME ([\d.]+) s MAXRSS (\d+) kB", open(log).read()) if os.path.exists(log) else None
    return kv, int(m.group(1)) if m else None, (float(t.group(1)), int(t.group(2)) / 1e6) if t else None


def key(r):
    return (round(r["aeta"][0], 3), round(r["pt"][0], 3))


def cmp_rows(a, b, fields=LEGACY):
    """max |difference| over common bins and fields; identical = bitwise equal (None == None)."""
    ra, rb = {key(r): r for r in a["bins"]}, {key(r): r for r in b["bins"]}
    maxd, identical = 0.0, set(ra) == set(rb)
    for k in set(ra) & set(rb):
        for f in fields:
            x, y = ra[k][f], rb[k][f]
            if x != y:
                identical = False
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    maxd = max(maxd, abs(x - y))
                else:
                    maxd = math.inf
    return dict(bins_a=len(ra), bins_b=len(rb), identical=identical, max_abs_diff=maxd)


def wratio(rows, lo=30.0, hi=60.0, eta=None):
    num = den = 0.0
    for r in rows:
        if r["pog_sf"] is None or not (lo <= r["pt"][0] < hi):
            continue
        if eta is not None and abs(r["aeta"][0] - eta) > 1e-6:
            continue
        e = r["sf_total_err"] / r["pog_sf"]
        num += r["sf"] / r["pog_sf"] / e**2
        den += 1 / e**2
    return (num / den, 1 / math.sqrt(den)) if den else (None, None)


summary = dict(note="CMS Open Data 2016G+H subset; not CMS results. Units: GeV.", runs={})
for line in open(os.path.join(R, "joblist.txt")):
    name = line.split("|")[0]
    kv, ex, t = out(name)
    d = load(name)
    summary["runs"][name] = dict(exit=ex, time_s=t[0] if t else None, maxrss_GB=t[1] if t else None,
                                 stdout=kv, n_bins=len(d["bins"]) if d else None)
ref = load("wp_tightid")
summary["inputs"] = dict(data_files=["G1", "G2", "H2", "H4"], mc_files=["mc0", "mc1", "mc2", "mc3", "mc4", "mc7", "mc8", "mc9"],
                         mc_half_A=["mc0", "mc1", "mc3", "mc4", "mc7"], mc_half_B=["mc2", "mc8", "mc9"],
                         list="code/input_files.txt",
                         n_events_data=ref["n_events_data"], n_events_mc=ref["n_events_mc"],
                         n_pairs_data_tightid=ref["n_pairs_data"], n_pairs_mc_tightid=ref["n_pairs_mc"])

# ---------------- (a) preset equivalence
a = {}
for wp in ("tightid", "tightiso", "isomu24"):
    old, new, expr = load(f"old_{wp}"), load(f"wp_{wp}"), load(f"expr_{wp}")
    refp = os.path.join(RES, f"pre_change_{wp}.json")
    if out(f"old_{wp}")[1] is not None:  # the old script ran: keep its output as the stored reference
        with open(os.path.join(R, f"old_{wp}.json")) as fo_, open(refp, "w") as fr_:
            fr_.write(fo_.read().rstrip("\n") + "\n")  # end with a newline (pre-commit end-of-file-fixer)
    with open(refp) as fr:
        stored = json.load(fr)
    a[wp] = dict(new_vs_old=cmp_rows(new, old), expr_vs_preset=cmp_rows(expr, new),
                 new_vs_stored_reference=cmp_rows(new, stored), old_ran=out(f"old_{wp}")[1] is not None,
                 old_mean_pull=old["mean_pull"], new_mean_pull=new["mean_pull"])
summary["a_preset_equivalence"] = a

# ---------------- (b) working points vs POG, triggers without POG
b = {}
WPS_B = [("wp_tightid", "NUM_TightID_DEN_TrackerMuons"), ("wp_tightiso", "NUM_TightRelIso_DEN_TightIDandIPCut"),
         ("wp_isomu24", "NUM_IsoMu24_or_IsoTkMu24_DEN_CutBasedIdTight_and_PFIsoTight"),
         ("mediumid", "NUM_MediumID_DEN_TrackerMuons"), ("looseid", "NUM_LooseID_DEN_TrackerMuons"),
         ("softid", "NUM_SoftID_DEN_TrackerMuons"), ("highptid", "NUM_HighPtID_DEN_TrackerMuons"),
         ("looseiso_med", "NUM_LooseRelIso_DEN_MediumID"), ("tkiso_loose", "NUM_LooseRelTkIso_DEN_HighPtIDandIPCut")]
for name, pogname in WPS_B:
    d = load(name)
    if d is None:
        continue
    rows = d["bins"]
    w, we = wratio(rows)
    per_eta = {f"{e0}-{e1}": wratio(rows, eta=e0)[0] for e0, e1 in zip(d["eta_edges"][:-1], d["eta_edges"][1:])}
    sel = [r for r in rows if 30 <= r["pt"][0] < 60]
    med = lambda k: float(np.median([r[k] for r in sel])) if sel else None
    pulls = [r["pull_total"] for r in rows if r["pull_total"] is not None]
    b[name] = dict(pog=pogname, definition=d["definition"], n_bins=len(rows),
                   n_fit_failed=sum(not r["fit_ok"] for r in rows),
                   mean_pull_total=d["mean_pull_total"], rms_pull_total=d["rms_pull_total"],
                   n_abs_pull_total_gt3=sum(abs(p) > 3 for p in pulls),
                   weighted_sf_over_pog_30_60=w, weighted_sf_over_pog_30_60_err=we,
                   per_eta_weighted_30_60=per_eta,
                   median_30_60=dict(stat=med("sf_stat"), mc_stat=med("sf_mc_stat"), syst=med("sf_syst"), total=med("sf_total_err"),
                                     pog_unc=med("pog_unc")),
                   sf_40_50={f"{r['aeta'][0]}-{r['aeta'][1]}": [r["sf"], r["sf_total_err"], r["pog_sf"]]
                             for r in rows if r["pt"][0] == 40.0})
for name in ("isomu22", "mu17leg"):
    d = load(name)
    if d is None:
        continue
    kv, ex, _ = out(name)
    b[name] = dict(definition=d["definition"], pog_available=d["pog_available"], pileup_weights=d["pileup_weights"],
                   binning_source=d["binning_source"], exit=ex, n_bins=len(d["bins"]),
                   n_fit_failed=sum(not r["fit_ok"] for r in d["bins"]),
                   bins=[dict(aeta=r["aeta"], pt=r["pt"], eff_data=r["eff_data"], eff_mc=r["eff_mc"], sf=r["sf"],
                              sf_total_err=r["sf_total_err"], fit_ok=r["fit_ok"]) for r in d["bins"]])
summary["b_working_points"] = b

# ---------------- (c) correctionlib
import correctionlib  # noqa: E402

c = {}
# The correctionlib paths are given explicitly in jobs.txt; read them from the joblist.
cl_of = {}
for line in open(os.path.join(R, "joblist.txt")):
    name, _, _, _, args = line.rstrip("\n").split("|", 4)
    m = re.search(r"--correctionlib (\S+)", args)
    if m:
        cl_of[name] = m.group(1)
for name, clpath in cl_of.items():
    d = load(name)
    res = dict(file=os.path.basename(clpath))
    try:
        cs = correctionlib.CorrectionSet.from_file(clpath)
        res["loads"] = True
    except Exception as e:  # noqa: BLE001
        c[name] = dict(res, loads=False, error=str(e))
        continue
    res["corrections"] = sorted(cs)
    v = subprocess.run(["correction", "validate", clpath], capture_output=True, text=True)
    res["correction_validate_exit"] = v.returncode
    corr = cs[d["name"]]
    ced, cem = cs[d["name"] + "_eff_data"], cs[d["name"] + "_eff_mc"]
    by = {(r["ieta"], r["ipt"]): r for r in d["bins"]}
    fills = {(f["ieta"], f["ipt"]): f for f in d["correctionlib_filled_bins"]}
    dn = du = dd_ = dcomp = 0.0
    min_down, alias_ok, n_filled = math.inf, True, 0
    eta_e, pt_e = d["eta_edges"], [float(x) for x in d["pt_edges"]]
    for i in range(len(eta_e) - 1):
        for j in range(len(pt_e) - 1):
            lo, hi = pt_e[j], min(pt_e[j + 1], 1e4)
            ptc = 0.5 * (lo + min(hi, 2 * lo))
            ec = 0.5 * (eta_e[i] + eta_e[i + 1])
            fl = fills.get((i, j))
            if fl is None:
                r, fsf, fed, fem = by[(i, j)], 0.0, 0.0, 0.0
            elif fl["src_ipt"] is None:
                r = None
            else:
                r, fsf, fed, fem = by[(i, fl["src_ipt"])], fl["fill_sf"], fl["fill_eff_data"], fl["fill_eff_mc"]
            n_filled += fl is not None
            if r is None:
                exp = (1.0, 1.0, 0.5, 0.5)
                tot = 1.0
            else:
                tot = math.sqrt(r["sf_stat"] ** 2 + r["sf_mc_stat"] ** 2 + r["sf_syst"] ** 2 + fsf ** 2)
                exp = (r["sf"], tot, r["eff_data"], r["eff_mc"])
            nom = corr.evaluate(ec, ptc, "nominal")
            dn = max(dn, abs(nom - exp[0]), abs(corr.evaluate(-ec, ptc, "nominal") - exp[0]))
            du = max(du, abs(corr.evaluate(ec, ptc, "up") - (exp[0] + tot)))
            dd_ = max(dd_, abs(corr.evaluate(ec, ptc, "down") - max(exp[0] - tot, 0.0)))
            min_down = min(min_down, corr.evaluate(ec, ptc, "down"))
            alias_ok &= corr.evaluate(ec, ptc, "systup") == corr.evaluate(ec, ptc, "up") and \
                corr.evaluate(ec, ptc, "systdown") == corr.evaluate(ec, ptc, "down")
            q = [corr.evaluate(ec, ptc, k) for k in ("stat", "mc_stat", "syst", "fill")]
            dcomp = max(dcomp, abs(math.sqrt(sum(x * x for x in q)) - tot),
                        abs(ced.evaluate(ec, ptc, "nominal") - exp[2]), abs(cem.evaluate(ec, ptc, "nominal") - exp[3]))
    res.update(max_abs_nominal_minus_json=dn, max_abs_up_minus_sf_plus_total=du, max_abs_down_minus_sf_minus_total=dd_,
               max_abs_quadrature_or_eff_mismatch=dcomp, min_down=min_down, systup_systdown_aliases_ok=bool(alias_ok),
               n_grid_bins=(len(eta_e) - 1) * (len(pt_e) - 1), n_filled=n_filled, syst_on=d["syst"],
               filled=[dict(f, raw_sf=by[(f["ieta"], f["ipt"])]["sf"] if (f["ieta"], f["ipt"]) in by else None,
                            filled_sf=by[(f["ieta"], f["src_ipt"])]["sf"] if f["src_ipt"] is not None else 1.0)
                       for f in d["correctionlib_filled_bins"]],
               description_lists_filled=all(f"({f['ieta']},{f['ipt']})<-" in corr.description for f in d["correctionlib_filled_bins"]))
    pt0, ptl = d["pt_edges"][0], d["pt_edges"][-2]
    clamp = dict(
        eta_3p0_eq_2p35=corr.evaluate(3.0, 45.0, "nominal") == corr.evaluate(2.35, 45.0, "nominal"),
        pt_below_first_eq_first=corr.evaluate(0.5, pt0 - 5, "nominal") == corr.evaluate(0.5, pt0 + 0.01, "nominal"),
        pt_1e5_eq_last=corr.evaluate(0.5, 1e5, "nominal") == corr.evaluate(0.5, ptl + 1, "nominal"),
    )
    res["clamp"] = clamp
    shutil.copy(clpath, os.path.join(RES, f"{d['name']}_correctionlib.json"))
    c[name] = res

# end-to-end: weight gen-matched medium-ID MC muons (first 20000 events of one MC file) with the mediumid SF
try:
    import awkward as ak
    import uproot

    mcfile = os.path.join(os.path.dirname(R), "inputs", "mc0.root")
    ev = uproot.open(f"{mcfile}:Events").arrays(["Muon_pt", "Muon_eta", "Muon_mediumId", "Muon_genPartFlav"], entry_stop=20000)
    mu = ev[(ev.Muon_mediumId) & (ev.Muon_genPartFlav == 1) & (ev.Muon_pt > 15) & (abs(ev.Muon_eta) < 2.4)]
    cs = correctionlib.CorrectionSet.from_file(cl_of["mediumid"])
    flat_eta, flat_pt = ak.to_numpy(ak.flatten(mu.Muon_eta)), ak.to_numpy(ak.flatten(mu.Muon_pt))
    sf_nom = cs["mediumid"].evaluate(flat_eta, flat_pt, "nominal")
    sf_up = cs["mediumid"].evaluate(flat_eta, flat_pt, "up")
    w_ev = ak.prod(ak.unflatten(sf_nom, ak.num(mu.Muon_pt)), axis=1)  # per-event weight = product over muons
    c["end_to_end_mediumid"] = dict(n_muons=int(len(flat_pt)), n_events=int(ak.sum(ak.num(mu.Muon_pt) > 0)),
                                    mean_sf=float(sf_nom.mean()), mean_sf_up=float(sf_up.mean()),
                                    min_sf=float(sf_nom.min()), max_sf=float(sf_nom.max()),
                                    mean_event_weight_2mu=float(ak.mean(w_ev[ak.num(mu.Muon_pt) == 2])))
except Exception as e:  # noqa: BLE001
    c["end_to_end_mediumid"] = dict(error=str(e))
summary["c_correctionlib"] = c

# ---------------- (d) MC-statistics coverage and scaling
dres, zall, zcnt_all = {}, [], []
for wp in ("tightid", "tightiso", "isomu24", "mediumid"):
    A, B = load(f"halfA_{wp}"), load(f"halfB_{wp}")
    full = load(f"wp_{wp}") if wp != "mediumid" else load("mediumid")
    if A is None or B is None:
        continue
    ra, rb, rf = {key(r): r for r in A["bins"]}, {key(r): r for r in B["bins"]}, {key(r): r for r in full["bins"]}
    z, zc, ratio_a, ratio_b, pred_a, pred_b, nboot_ok = [], [], [], [], [], [], []
    dsf = []  # (SF_A + SF_B)/2 - SF_full: zero for an estimator linear in the MC; the finite-MC bias otherwise
    for k in sorted(set(ra) & set(rb) & set(rf)):
        if ra[k]["fit_ok"] and rb[k]["fit_ok"] and rf[k]["fit_ok"]:
            dsf.append(0.5 * (ra[k]["sf"] + rb[k]["sf"]) - rf[k]["sf"])
    for k in sorted(set(ra) & set(rb)):
        x, y = ra[k], rb[k]
        if not (x["fit_ok"] and y["fit_ok"]) or x["mc_stat_method"] != "bootstrap" or y["mc_stat_method"] != "bootstrap":
            continue
        s = math.hypot(x["sf_mc_stat"], y["sf_mc_stat"])
        z.append((x["sf"] - y["sf"]) / s)
        sc = math.hypot(x["sf"] * x["eff_mc_err"] / x["eff_mc"], y["sf"] * y["eff_mc_err"] / y["eff_mc"])
        zc.append((x["sf"] - y["sf"]) / sc)
        if k in rf and rf[k]["mc_stat_method"] == "bootstrap":
            ratio_a.append(x["sf_mc_stat"] / rf[k]["sf_mc_stat"])
            ratio_b.append(y["sf_mc_stat"] / rf[k]["sf_mc_stat"])
            pred_a.append(math.sqrt(rf[k]["n_mc_gen"] / x["n_mc_gen"]))
            pred_b.append(math.sqrt(rf[k]["n_mc_gen"] / y["n_mc_gen"]))
    z, zc = np.array(z), np.array(zc)
    zall += list(z)
    zcnt_all += list(zc)
    dres[wp] = dict(n_bins=len(z), mean_z=float(z.mean()), rms_z=float(np.sqrt((z**2).mean())),
                    rms_z_counting_only=float(np.sqrt((zc**2).mean())),
                    n_abs_z_gt3=int((abs(z) > 3).sum()),
                    mean_sf_halves_minus_full=float(np.mean(dsf)), mean_sf_halves_minus_full_sem=float(np.std(dsf) / math.sqrt(len(dsf))),
                    mean_mc_stat_full=float(np.mean([r["sf_mc_stat"] for r in full["bins"] if r["mc_stat_method"] == "bootstrap"])),
                    median_mc_stat_ratio_halfA_over_full=float(np.median(ratio_a)),
                    median_expected_sqrt_nfull_over_nA=float(np.median(pred_a)),
                    median_mc_stat_ratio_halfB_over_full=float(np.median(ratio_b)),
                    median_expected_sqrt_nfull_over_nB=float(np.median(pred_b)))
zall, zcnt_all = np.array(zall), np.array(zcnt_all)
n = len(zall)
dres["combined"] = dict(n_bins=n, mean_z=float(zall.mean()), rms_z=float(np.sqrt((zall**2).mean())),
                        rms_z_err_approx=float(np.sqrt((zall**2).mean()) / math.sqrt(2 * n)),
                        rms_z_counting_only=float(np.sqrt((zcnt_all**2).mean())),
                        frac_abs_z_lt1=float((abs(zall) < 1).mean()), frac_abs_z_lt2=float((abs(zall) < 2).mean()))
summary["d_mc_stat_coverage"] = dres

# ---------------- (d2) data-statistics coverage: two halves of the data, same MC
d2, zall2 = {}, []
for wp in ("tightid", "mediumid", "tightiso"):
    A, B = load(f"dsplit1_{wp}"), load(f"dsplit2_{wp}")
    if A is None or B is None:
        continue
    ra, rb = {key(r): r for r in A["bins"]}, {key(r): r for r in B["bins"]}
    z = [(ra[k]["sf"] - rb[k]["sf"]) / math.hypot(ra[k]["sf_stat"], rb[k]["sf_stat"]) for k in sorted(set(ra) & set(rb))
         if ra[k]["fit_ok"] and rb[k]["fit_ok"] and ra[k]["sf_stat"] < 0.05 and rb[k]["sf_stat"] < 0.05]
    zall2 += z
    z = np.array(z)
    d2[wp] = dict(n_bins=len(z), rms_z=float(np.sqrt((z ** 2).mean())), mean_z=float(z.mean()))
zall2 = np.array(zall2)
d2["combined"] = dict(n_bins=len(zall2), rms_z=float(np.sqrt((zall2 ** 2).mean())), mean_z=float(zall2.mean()),
                      rms_z_err_approx=float(np.sqrt((zall2 ** 2).mean()) / math.sqrt(2 * len(zall2))),
                      n_abs_z_gt3=int((abs(zall2) > 3).sum()))
summary["d2_data_stat_coverage"] = d2

# ---------------- (R5) golden-JSON lumi mask
lm = {}
for wp in ("mediumid", "softid"):
    G, N = load(f"{wp}_golden"), load(wp)
    if G is None or N is None:
        continue
    rg, rn = {key(r): r for r in G["bins"]}, {key(r): r for r in N["bins"]}
    common = [k for k in sorted(set(rg) & set(rn)) if rg[k]["reliable"] and rn[k]["reliable"]]
    dsf = [abs(rg[k]["sf"] - rn[k]["sf"]) for k in common]
    mid = [k for k in common if 30 <= k[1] < 60]
    lm[wp] = dict(frac_events_in_mask=G["n_events_data_in_lumi_mask"] / G["n_events_data"],
                  frac_pairs_in_mask=G["n_pairs_data"] / N["n_pairs_data"], n_bins=len(common),
                  max_abs_dsf=float(max(dsf)), median_abs_dsf=float(np.median(dsf)),
                  max_abs_dsf_30_60=float(max(abs(rg[k]["sf"] - rn[k]["sf"]) for k in mid)),
                  max_abs_dsf_over_stat=float(max(abs(rg[k]["sf"] - rn[k]["sf"]) / rn[k]["sf_stat"] for k in common)))
summary["lumi_mask"] = lm

# ---------------- (R2) IsoMu22 activity
p22 = os.path.join(R, "isomu22_check.json")
if os.path.exists(p22):
    with open(p22) as f22:
        iso = json.load(f22)
    for v in iso.values():
        v.pop("runs", None)
    summary["isomu22_activity"] = iso

# ---------------- (R3) systematics default
summary["syst_default"] = {n: dict(correctionlib=bool(n in cl_of), syst=load(n)["syst"],
                                   warns_no_syst=any("no systematics" in w for w in load(n)["warnings"]))
                           for n in ("mvamedium", "isomu22", "halfA_tightid", "mediumid")}

# ---------------- (e) offline mode and exit codes
e = {}
for name in ("offline_flags", "offline_badpath"):
    d = load(name)
    kv, ex, _ = out(name)
    e[name] = dict(exit=ex, pog_available=d["pog_available"] if d else None, pileup_weights=d["pileup_weights"] if d else None,
                   n_bins=len(d["bins"]) if d else 0, binning_source=d["binning_source"] if d else None,
                   warnings=d["warnings"][:3] if d else None, stdout_POG=kv.get("POG"), stdout_PILEUP=kv.get("PILEUP"))
for name in ("dryrun", "bad_precedence", "bad_intbool", "bad_call", "bad_dryrun_intbool", "bad_den_only", "bad_recursion",
             "bad_trigger_zero", "bad_trigger_mixed", "bad_trigger_dr"):
    txt = open(os.path.join(R, f"{name}.out")).read()
    ex = int(re.search(r"^EXIT (\d+)", txt, re.M).group(1))
    errl = [ln for ln in txt.splitlines() if ln.startswith("error:")]
    e[name] = dict(exit=ex, message=(errl[0][:300] if errl else None))
summary["e_offline_and_exit_codes"] = e

# ---------------- (f) systematics
f = {}
for name, _ in WPS_B:
    d = load(name)
    if d is None or not d["syst"]:
        continue
    sel = [r for r in d["bins"] if 30 <= r["pt"][0] < 60 and r["sf_syst_components"]]
    comps = {}
    for cname in ("bkg", "window", "tag"):
        v = [r["sf_syst_components"][cname] for r in sel]
        comps[cname] = dict(median=float(np.median(v)), max=float(np.max(v)))
    allv = [r["sf_syst"] for r in d["bins"]]
    f[name] = dict(components_30_60=comps, median_syst_all_bins=float(np.median(allv)), max_syst_all_bins=float(np.max(allv)),
                   median_stat_30_60=float(np.median([r["sf_stat"] for r in sel])),
                   median_mc_stat_30_60=float(np.median([r["sf_mc_stat"] for r in sel])))
summary["f_systematics"] = f


def clean(x):
    if isinstance(x, float) and not math.isfinite(x):
        return str(x)
    if isinstance(x, dict):
        return {k: clean(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [clean(v) for v in x]
    if isinstance(x, (np.floating,)):
        return clean(float(x))
    if isinstance(x, (np.integer,)):
        return int(x)
    if isinstance(x, np.bool_):
        return bool(x)
    return x


with open(os.path.join(V, "summary.json"), "w") as fo:
    json.dump(clean(summary), fo, indent=1)
    fo.write("\n")

# ---------------- plots
import matplotlib  # noqa: E402

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import mplhep as hep  # noqa: E402

hep.style.use("CMS")
LUMI_TXT = "2016G+H subset (13 TeV)"


def save(fig, stem):
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(PLOTS, f"{stem}.{ext}"))
    plt.close(fig)


# SF / POG vs pT per |eta| for every WP with a POG counterpart
for name, pogname in WPS_B:
    d = load(name)
    if d is None:
        continue
    fig, axs = plt.subplots(2, 2, figsize=(14, 10), sharex=True)
    for ax, (e0, e1) in zip(axs.flat, zip(d["eta_edges"][:-1], d["eta_edges"][1:])):
        rr = [r for r in d["bins"] if r["aeta"][0] == e0 and r["pog_sf"] is not None]
        if not rr:
            continue
        x = [0.5 * (r["pt"][0] + min(r["pt"][1], 2 * r["pt"][0])) for r in rr]
        xe = [[xx - r["pt"][0] for xx, r in zip(x, rr)], [min(r["pt"][1], 2 * r["pt"][0]) - xx for xx, r in zip(x, rr)]]
        ax.errorbar(x, [r["sf"] / r["pog_sf"] for r in rr], xerr=xe, yerr=[r["sf_total_err"] / r["pog_sf"] for r in rr],
                    fmt="o", color="k", label="ours / POG (total)")
        ax.errorbar(x, [r["sf"] / r["pog_sf"] for r in rr], yerr=[r["sf_stat"] / r["pog_sf"] for r in rr],
                    fmt="none", color="tab:blue", lw=3, label="data stat")
        ax.fill_between(x, [1 - r["pog_unc"] / r["pog_sf"] for r in rr], [1 + r["pog_unc"] / r["pog_sf"] for r in rr],
                        color="tab:orange", alpha=0.4, step="mid", label="POG unc.")
        ax.axhline(1, color="gray", ls="--")
        ax.set_xscale("log")
        ax.set_xlim(12, 300)
        ax.set_ylim(0.95, 1.05)
        ax.set_title(f"|η| {e0}–{e1}", fontsize=16)
        ax.set_ylabel("SF / SF(POG)", fontsize=16)
    for ax in axs[1]:
        ax.set_xlabel("probe $p_T$ [GeV]", fontsize=16)
    axs[0, 0].legend(fontsize=12)
    hep.cms.label("Open Data", data=True, rlabel="", ax=axs[0, 0], fontsize=14)
    fig.suptitle(f"{name}: {pogname}, {LUMI_TXT}; out-of-range errors are empty high-pT bins", fontsize=13)
    fig.tight_layout()
    save(fig, f"sf_over_pog_{name}")

# coverage
fig, axs = plt.subplots(1, 2, figsize=(15, 6))
hb = np.linspace(-4, 4, 17)
axs[0].hist(np.clip(zall, -3.99, 3.99), bins=hb, histtype="step", color="k", lw=2, label=f"bootstrap mc_stat, RMS {np.sqrt((zall**2).mean()):.2f}")
axs[0].hist(np.clip(zcnt_all, -3.99, 3.99), bins=hb, histtype="step", color="tab:red", ls="--", lw=2,
            label=f"MC counting error only, RMS {np.sqrt((zcnt_all**2).mean()):.2f}")
xx = np.linspace(-4, 4, 200)
axs[0].plot(xx, n * 0.5 * np.exp(-xx**2 / 2) / math.sqrt(2 * math.pi), color="tab:blue", label="unit Gaussian")
axs[0].set_xlabel(r"$(SF_A - SF_B)/\sqrt{\sigma_{A}^2+\sigma_{B}^2}$", fontsize=16)
axs[0].set_ylabel("bins", fontsize=16)
axs[0].legend(fontsize=11)
for wp, col in zip(("tightid", "tightiso", "isomu24", "mediumid"), ("k", "tab:blue", "tab:red", "tab:green")):
    A, full = load(f"halfA_{wp}"), (load(f"wp_{wp}") if wp != "mediumid" else load("mediumid"))
    B = load(f"halfB_{wp}")
    rf = {key(r): r for r in full["bins"]}
    for H, mk in ((A, "o"), (B, "s")):
        pts = [(math.sqrt(rf[key(r)]["n_mc_gen"] / r["n_mc_gen"]), r["sf_mc_stat"] / rf[key(r)]["sf_mc_stat"])
               for r in H["bins"] if key(r) in rf and r["mc_stat_method"] == "bootstrap" and rf[key(r)]["mc_stat_method"] == "bootstrap"]
        if pts:
            p = np.array(pts)
            axs[1].scatter(p[:, 0], p[:, 1], marker=mk, color=col, s=18, label=f"{wp} half {'A' if H is A else 'B'}")
axs[1].plot([1, 2.5], [1, 2.5], color="gray", ls="--", label=r"$1/\sqrt{N}$")
axs[1].set_xlabel(r"$\sqrt{N_{MC}^{full}/N_{MC}^{half}}$", fontsize=16)
axs[1].set_ylabel(r"$\sigma_{mc\,stat}^{half}/\sigma_{mc\,stat}^{full}$", fontsize=16)
axs[1].set_ylim(0, 4)
axs[1].legend(fontsize=9, ncol=2)
hep.cms.label("Open Data", data=True, rlabel=LUMI_TXT, ax=axs[0], fontsize=14)
fig.tight_layout()
save(fig, "mc_stat_coverage")

# uncertainty components, tight ID and medium ID
for name in ("wp_tightid", "mediumid", "wp_isomu24"):
    d = load(name)
    rr = d["bins"]
    lab = [f"{r['aeta'][0]}-{r['aeta'][1]}\n{r['pt'][0]:.0f}" for r in rr]
    fig, ax = plt.subplots(figsize=(18, 6))
    xi = np.arange(len(rr))
    for k, col in (("sf_stat", "tab:blue"), ("sf_mc_stat", "tab:green"), ("sf_syst", "tab:red"), ("sf_total_err", "k")):
        ax.step(xi, [r[k] for r in rr], where="mid", color=col, label=k.replace("sf_", ""), lw=2 if k == "sf_total_err" else 1.5)
    ax.plot(xi, [r["pog_unc"] if r["pog_unc"] is not None else np.nan for r in rr], "x", color="tab:orange", label="POG systup - nominal")
    ax.set_yscale("log")
    ax.set_xticks(xi)
    ax.set_xticklabels(lab, fontsize=7)
    ax.set_xlabel("|η| bin, pT low edge [GeV]", fontsize=14)
    ax.set_ylabel("uncertainty on SF", fontsize=14)
    ax.legend(fontsize=11, ncol=5)
    hep.cms.label("Open Data", data=True, rlabel=LUMI_TXT, ax=ax, fontsize=14)
    fig.tight_layout()
    save(fig, f"unc_components_{name}")

# triggers without POG: efficiency vs pT
for name, title in (("isomu22", "IsoMu22-type (bit 2, object pT ≥ 22 GeV)"), ("mu17leg", "Mu17 TrkIsoVVL leg (bit 1, object pT ≥ 17 GeV)")):
    d = load(name)
    if d is None:
        continue
    fig, axs = plt.subplots(1, 2, figsize=(15, 6))
    for (e0, e1), col in zip(zip(d["eta_edges"][:-1], d["eta_edges"][1:]), ("k", "tab:blue", "tab:red", "tab:green")):
        rr = [r for r in d["bins"] if r["aeta"][0] == e0]
        x = [0.5 * (r["pt"][0] + min(r["pt"][1], 2 * r["pt"][0])) for r in rr]
        axs[0].errorbar(x, [r["eff_data"] for r in rr], yerr=[r["eff_data_total_err"] for r in rr], fmt="o", color=col, label=f"data |η| {e0}-{e1}")
        axs[0].plot(x, [r["eff_mc"] for r in rr], "--", color=col)
        axs[1].errorbar(x, [r["sf"] for r in rr], yerr=[r["sf_total_err"] for r in rr], fmt="o", color=col, label=f"|η| {e0}-{e1}")
    axs[0].set_ylabel("efficiency (dashed: MC)", fontsize=16)
    axs[1].set_ylabel("data / MC", fontsize=16)
    axs[1].set_ylim(0.8, 1.1)
    for ax in axs:
        ax.set_xscale("log")
        ax.set_xlabel("probe $p_T$ [GeV]", fontsize=16)
        ax.legend(fontsize=11)
    axs[0].set_title(title + ", no pileup weights", fontsize=13)
    hep.cms.label("Open Data", data=True, rlabel=LUMI_TXT, ax=axs[1], fontsize=14)
    fig.tight_layout()
    save(fig, f"eff_{name}")

print(f"wrote {os.path.join(V, 'summary.json')}", file=sys.stderr)
