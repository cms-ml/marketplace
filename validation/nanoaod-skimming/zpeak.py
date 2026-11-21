#!/usr/bin/env python3
"""Step 4 of the nanoaod-skimming validation: Z -> mumu peak in the merged skims
(CMS Open Data, 2016 UL NanoAODv9, SingleMuon Run2016G and DYJetsToLL M-50 amcatnlo).

Also assembles summary.json from the KEY=VALUE logs and cutflow JSON written by run_all.sh.

Selection (both data and MC, no scale factors, no pileup weights):
  - muons with pT > 20 GeV, |eta| < 2.4, tightId, pfRelIso04_all < 0.15   (the selected muons)
  - exactly two such muons, opposite charge, leading pT > 26 GeV
  - 81 < m_mumu < 101 GeV
MC weight: genWeight * XSEC * LUMI / SUMW (WEIGHT_FACTOR from sumw.py on the original files).

Cutflow (analysis steps, on the merged skims; the skim steps come from the Cutflow trees):
  Muon-level steps (muon_pt, muon_eta, muon_tight_id, muon_iso) are cumulative requirements on
  the muons. Their sequential predicate is "at least two muons pass all muon requirements so far".
  Event-level steps (exactly_two, opposite_charge, leading_pt, z_window) use the selected muons,
  pT-sorted: exactly_two = number of selected muons == 2; opposite_charge, leading_pt and z_window
  use the two leading selected muons (False when fewer than two are selected).
  Sequential: each step is ANDed onto the previous ones.
  N-1 of a muon-level step s: the muons are selected without s; all the other analysis steps are
  applied (event-level ones on those muons). N-1 of an event-level step e: all muon requirements
  and all other event-level steps are applied.
  The skim steps in the normalised MC cutflow are Sum(genWeight) * WEIGHT_FACTOR from the Cutflow trees.
  Cutflow trees store Sum(genWeight), not Sum(genWeight^2): skim steps have no MC stat uncertainty here.

Exit codes: 0 all checks pass, 1 a check failed (printed), 2 bad inputs.
stdout: KEY=VALUE, table and CHECK lines.
"""
import argparse
import glob
import json
import os
import sys

import awkward as ak
import matplotlib

matplotlib.use("Agg")
import hist  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
import mplhep as hep  # noqa: E402
import numpy as np  # noqa: E402
import uproot  # noqa: E402

XSEC_PB = 6077.22
MUON_FIELDS = ["Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass", "Muon_charge", "Muon_tightId", "Muon_pfRelIso04_all"]
MC_BRANCHES = ["genWeight"]
SKIM_STEPS = ["trigger", "two_muons"]
MUON_STEPS = ["muon_pt", "muon_eta", "muon_tight_id", "muon_iso"]
EVENT_STEPS = ["exactly_two", "opposite_charge", "leading_pt", "z_window"]
ANALYSIS_STEPS = MUON_STEPS + EVENT_STEPS
CUTFLOW_STEPS = ["all", "lumimask"] + SKIM_STEPS + ANALYSIS_STEPS

CHECKS = []


def check(name, ok, detail):
    CHECKS.append(bool(ok))
    print(f"CHECK {'PASS' if ok else 'FAIL'} {name}: {detail}")


def read_kv(path):
    out = {}
    with open(path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                out[k] = v
    return out


def read_json(path):
    with open(path) as f:
        return json.load(f)


# ---------------------------------------------------------------- physics helpers
def muon_pass(ev, step):
    if step == "muon_pt":
        return ev["Muon_pt"] > 20
    if step == "muon_eta":
        return np.abs(ev["Muon_eta"]) < 2.4
    if step == "muon_tight_id":
        return ev["Muon_tightId"]
    if step == "muon_iso":
        return ev["Muon_pfRelIso04_all"] < 0.15
    raise KeyError(step)


def dimuon_mass(a, b):
    """Invariant mass in GeV from pt, eta, phi, mass (awkward records with those fields)."""
    px1, py1, pz1 = a.pt * np.cos(a.phi), a.pt * np.sin(a.phi), a.pt * np.sinh(a.eta)
    px2, py2, pz2 = b.pt * np.cos(b.phi), b.pt * np.sin(b.phi), b.pt * np.sinh(b.eta)
    e1 = np.sqrt(px1**2 + py1**2 + pz1**2 + a.mass**2)
    e2 = np.sqrt(px2**2 + py2**2 + pz2**2 + b.mass**2)
    m2 = (e1 + e2) ** 2 - ((px1 + px2) ** 2 + (py1 + py2) ** 2 + (pz1 + pz2) ** 2)
    return np.sqrt(np.maximum(ak.to_numpy(m2), 0.0))


def event_flags(ev, muon_steps):
    """Event predicates for the muon requirements in muon_steps (all must be listed).
    Returns a dict of boolean arrays (one per event): ge2, exactly_two, opposite_charge,
    leading_pt, z_window. The leading two selected muons are used for the pair quantities."""
    good = muon_pass(ev, muon_steps[0])
    for s in muon_steps[1:]:
        good = good & muon_pass(ev, s)
    mus = ak.zip({k.replace("Muon_", ""): ev[k] for k in MUON_FIELDS})[good]
    mus = mus[ak.argsort(mus.pt, axis=1, ascending=False)]
    n = ak.to_numpy(ak.num(mus, axis=1))
    ge2 = n >= 2
    lead_pt = ak.to_numpy(ak.fill_none(ak.firsts(mus.pt, axis=1), -1.0))
    lead_q = ak.to_numpy(ak.fill_none(ak.firsts(mus.charge, axis=1), 0))
    sub_q = ak.to_numpy(ak.fill_none(ak.firsts(mus.charge[:, 1:], axis=1), 0))
    mll = np.zeros(len(n))
    s2 = mus[ge2]
    if len(s2):
        a = ak.firsts(s2, axis=1)
        b = ak.firsts(s2[:, 1:], axis=1)
        mll[ge2] = dimuon_mass(a, b)
    return {
        "ge2": ge2,
        "exactly_two": n == 2,
        "opposite_charge": ge2 & (lead_q + sub_q == 0),
        "leading_pt": lead_pt > 26,
        "z_window": ge2 & (mll > 81) & (mll < 101),
    }


def analysis_cutflow(ev, w):
    """Sequential and N-1 weighted counts of the analysis steps on the merged skim events.
    w: per-event weight (1 for data, genWeight * WEIGHT_FACTOR for MC). Returns (seq, nm1) dicts."""
    seq, nm1 = {}, {}
    full = event_flags(ev, MUON_STEPS)
    cum = np.ones(len(w), bool)
    prefix = []
    for s in MUON_STEPS:
        prefix.append(s)
        cum = cum & event_flags(ev, prefix)["ge2"]
        seq[s] = float(np.sum(w[cum]))
    for e in EVENT_STEPS:
        cum = cum & full[e]
        seq[e] = float(np.sum(w[cum]))
    for s in MUON_STEPS:  # N-1 of a muon-level step: muons without s, all other steps applied
        f = event_flags(ev, [x for x in MUON_STEPS if x != s])
        ok = f["ge2"] & f["exactly_two"] & f["opposite_charge"] & f["leading_pt"] & f["z_window"]
        nm1[s] = float(np.sum(w[ok]))
    for e in EVENT_STEPS:  # N-1 of an event-level step: all muon requirements, other event steps
        ok = full["ge2"].copy()
        for x in EVENT_STEPS:
            if x != e:
                ok = ok & full[x]
        nm1[e] = float(np.sum(w[ok]))
    return seq, nm1


def select_zpeak(ev):
    """Independent (run 1) selection, used only as a cross-check of the cutflow code path."""
    good = (ev["Muon_pt"] > 20) & (np.abs(ev["Muon_eta"]) < 2.4) & ev["Muon_tightId"] & (ev["Muon_pfRelIso04_all"] < 0.15)
    mus = ak.zip({k.replace("Muon_", ""): ev[k] for k in MUON_FIELDS})[good]
    mus = mus[ak.argsort(mus.pt, axis=1, ascending=False)]
    two = ak.num(mus, axis=1) == 2
    mus2 = mus[two]
    lead, sub = mus2[:, 0], mus2[:, 1]
    ok_pair = (lead.pt > 26) & (sub.pt > 20) & (lead.charge + sub.charge == 0)
    full = np.zeros(len(ev), dtype=bool)
    full[np.asarray(two)] = np.asarray(ok_pair)
    pass_lead = lead[ok_pair]
    pass_sub = sub[ok_pair]
    return full, pass_lead, pass_sub


def load(fn, is_mc):
    branches = MUON_FIELDS + (MC_BRANCHES if is_mc else [])
    with uproot.open(fn) as f:
        return f["Events"].arrays(branches, library="ak")


def cutflow_rows(cf_json, sumw_weight, is_mc, n_all_key="n_all"):
    """Skim-part cutflow of one kind (data or MC), as (sequential, nminus1) lists over
    ['all', 'lumimask'] + SKIM_STEPS. MC values are normalised: Sum(genWeight) * WEIGHT_FACTOR."""
    if is_mc:
        f = sumw_weight
        seq = [cf_json["w_all"] * f, cf_json["w_lumimask"] * f] + [cf_json["cutflow_w"][s] * f for s in SKIM_STEPS]
        nm1 = [None, None] + [cf_json["nminus1_w"][s] * f for s in SKIM_STEPS]
    else:
        seq = [cf_json["n_all"], cf_json["n_lumimask"]] + [cf_json["cutflow"][s] for s in SKIM_STEPS]
        nm1 = [None, None] + [cf_json["nminus1"][s] for s in SKIM_STEPS]
    return seq, nm1


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--data", required=True, help="merged data skim")
    p.add_argument("--mc", required=True, help="merged MC skim")
    p.add_argument("--per-file", required=True, help="directory with the per-input skims")
    p.add_argument("--logs", required=True, help="directory with run_all.sh logs")
    p.add_argument("--out-dir", required=True, help="directory for plots/ and summary.json")
    a = p.parse_args()

    L = a.logs
    lumi = read_kv(os.path.join(L, "lumi_data_merged.log"))
    golden = read_kv(os.path.join(L, "lumi_golden_2016.log"))
    sw_orig = read_kv(os.path.join(L, "sumw_mc_original.log"))
    sw_merged = read_kv(os.path.join(L, "sumw_mc_merged.log"))
    sizes = read_kv(os.path.join(L, "input_sizes.log"))
    lumi_pb = float(lumi["LUMI_PB"])
    weight_factor = float(sw_orig["WEIGHT_FACTOR"])
    sumw_orig = float(sw_orig["SUMW"])
    sumw_merged = float(sw_merged["SUMW"])

    data_logs = [read_kv(f) for f in sorted(glob.glob(os.path.join(L, "skim_SingleMuon_2016G_*.log")))]
    mc_logs = [read_kv(f) for f in sorted(glob.glob(os.path.join(L, "skim_DYJetsToLL_M50_*.log")))]
    if len(data_logs) != 3 or len(mc_logs) != 3:
        print("ERROR: expected 3 data and 3 MC skim logs", file=sys.stderr)
        return 2
    data_files = sorted(glob.glob(os.path.join(a.per_file, "skim_SingleMuon_2016G_*.root")))
    mc_files = sorted(glob.glob(os.path.join(a.per_file, "skim_DYJetsToLL_M50_*.root")))

    cf_d_file = read_json(os.path.join(L, "cutflow_data_per_file.json"))
    cf_d_merged = read_json(os.path.join(L, "cutflow_data_merged.json"))
    cf_m_file = read_json(os.path.join(L, "cutflow_mc_per_file.json"))
    cf_m_merged = read_json(os.path.join(L, "cutflow_mc_merged.json"))

    # ---- physics selection (independent cross-check and the analysis cutflow) ----
    d = load(a.data, is_mc=False)
    m = load(a.mc, is_mc=True)
    sel_d, lead_d, sub_d = select_zpeak(d)
    sel_m, lead_m, sub_m = select_zpeak(m)
    mll_d = dimuon_mass(lead_d, sub_d)
    mll_m = dimuon_mass(lead_m, sub_m)
    gw_m = ak.to_numpy(m["genWeight"]).astype(np.float64)
    w_m = gw_m[sel_m] * weight_factor
    neg_frac = float(np.mean(gw_m < 0))

    in_win_d = (mll_d > 81) & (mll_d < 101)
    in_win_m = (mll_m > 81) & (mll_m < 101)
    data_events = int(np.sum(in_win_d))
    mc_norm = float(np.sum(w_m[in_win_m]))
    mc_stat = float(np.sqrt(np.sum(w_m[in_win_m] ** 2)))
    data_over_mc = data_events / mc_norm

    print(f"N_PAIR_DATA={len(mll_d)}\nN_PAIR_MC_SKIM={len(mll_m)}")
    print(f"LUMI_PB_USED={lumi_pb:.6g}\nWEIGHT_FACTOR={weight_factor:.6g}\nNEG_WEIGHT_FRACTION={neg_frac:.6g}")
    print(f"DATA_EVENTS_81_101={data_events}\nMC_NORM_81_101={mc_norm:.6g}\nMC_STAT_UNC={mc_stat:.6g}")
    print(f"DATA_OVER_MC={data_over_mc:.6g}")

    # analysis cutflow on the merged skims
    seq_d, nm1_d = analysis_cutflow(d, np.ones(len(d), np.float64))
    seq_m, nm1_m = analysis_cutflow(m, gw_m * weight_factor)

    # skim part: data counts, MC normalised
    sk_seq_d, sk_nm1_d = cutflow_rows(cf_d_merged, None, is_mc=False)
    sk_seq_m, sk_nm1_m = cutflow_rows(cf_m_merged, weight_factor, is_mc=True)

    data_seq = sk_seq_d + [seq_d[s] for s in ANALYSIS_STEPS]
    data_nm1 = sk_nm1_d + [nm1_d[s] for s in ANALYSIS_STEPS]
    mc_seq = sk_seq_m + [seq_m[s] for s in ANALYSIS_STEPS]
    mc_nm1 = sk_nm1_m + [nm1_m[s] for s in ANALYSIS_STEPS]

    print("\nCUTFLOW (data: events; MC: normalised events = genWeight*xsec*lumi/SUMW)")
    print(f"{'step':<18}{'data seq':>12}{'data N-1':>12}{'MC seq':>14}{'MC N-1':>14}")
    for i, s in enumerate(CUTFLOW_STEPS):
        dn = "" if data_nm1[i] is None else f"{data_nm1[i]:.0f}"
        mn = "" if mc_nm1[i] is None else f"{mc_nm1[i]:.4f}"
        print(f"{s:<18}{data_seq[i]:>12.0f}{dn:>12}{mc_seq[i]:>14.4f}{mn:>14}")
    for i, s in enumerate(CUTFLOW_STEPS):
        print(f"CUTFLOW_DATA_SEQ_{s}={data_seq[i]:.6g}")
        if data_nm1[i] is not None:
            print(f"CUTFLOW_DATA_NM1_{s}={data_nm1[i]:.6g}")
        print(f"CUTFLOW_MC_SEQ_{s}={mc_seq[i]:.10g}")
        if mc_nm1[i] is not None:
            print(f"CUTFLOW_MC_NM1_{s}={mc_nm1[i]:.10g}")

    # ---- plot m_mumu 60-120 GeV ----
    axis = hist.axis.Regular(60, 60, 120, name="mll", label=r"$m_{\mu\mu}$ [GeV]")
    h_d = hist.Hist(axis, storage=hist.storage.Weight())
    h_m = hist.Hist(axis, storage=hist.storage.Weight())
    h_d.fill(mll=mll_d)
    h_m.fill(mll=mll_m, weight=w_m)
    vd, ed = h_d.values(), h_d.variances()
    vm, em = h_m.values(), h_m.variances()
    centers = axis.centers
    edges = axis.edges
    ok = vm > 0
    ratio = np.divide(vd, vm, out=np.zeros_like(vd), where=ok)
    rel2 = np.divide(ed, vd**2, out=np.zeros_like(vd), where=vd > 0) + np.divide(em, vm**2, out=np.zeros_like(vd), where=ok)
    ratio_err = ratio * np.sqrt(rel2)

    plt.style.use(hep.style.CMS)
    fig, (ax, rax) = plt.subplots(2, 1, figsize=(10, 10), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    hep.histplot(vm, edges, w2=em, ax=ax, histtype="fill", color="C0", alpha=0.5, label="DY M-50 amcatnlo (MC)", stack=False)
    hep.histplot(vm, edges, w2=em, ax=ax, histtype="step", color="C0")
    hep.histplot(vd, edges, w2=ed, ax=ax, histtype="errorbar", color="k", label="Data (SingleMuon 2016G)")
    ax.set_ylabel("Events / 1 GeV")
    ax.set_ylim(0, 1.45 * max(vm.max(), vd.max()))  # headroom for the legend
    ax.legend(loc="upper left")
    hep.cms.label(label="Open Data", data=True, lumi=round(lumi_pb / 1000.0, 2), year=2016, com=13, ax=ax)
    rax.errorbar(centers, ratio, yerr=ratio_err, fmt="ko", ms=3)
    rax.axhline(1.0, color="gray", ls="--")
    rax.set_ylim(0.5, 1.5)
    rax.set_ylabel("Data / MC")
    rax.set_xlabel(r"$m_{\mu\mu}$ [GeV]")
    os.makedirs(os.path.join(a.out_dir, "plots"), exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(a.out_dir, "plots", f"mmumu.{ext}"), dpi=150 if ext == "png" else None, bbox_inches="tight")
    plt.close(fig)

    # ---- cutflow plot: sequential, data vs normalised MC, ratio from 'trigger' on ----
    n_steps = len(CUTFLOW_STEPS)
    xedges = np.arange(n_steps + 1) - 0.0
    xc = np.arange(n_steps) + 0.5
    cd = np.array(data_seq, float)
    cm = np.array(mc_seq, float)
    # Ratio error: data Poisson stat only. The Cutflow tree stores Sum(genWeight), not Sum(genWeight^2),
    # so the MC stat uncertainty of the skim steps is not available here (noted in SKILLS_USED.md).
    fig, (cax, rax) = plt.subplots(2, 1, figsize=(12, 10), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    cax.set_yscale("log")
    hep.histplot(cm, xedges, ax=cax, histtype="fill", color="C0", alpha=0.5, label="DY M-50 amcatnlo (MC, normalised)",
                 stack=False)
    hep.histplot(cm, xedges, ax=cax, histtype="step", color="C0")
    cax.errorbar(xc, cd, yerr=np.sqrt(cd), fmt="ko", ms=4, label="Data (SingleMuon 2016G)")
    cax.set_ylabel("Events (MC normalised)")
    cax.set_ylim(1e3, 5e7)  # headroom for the legend
    cax.legend(loc="upper right")
    hep.cms.label(label="Open Data", data=True, lumi=round(lumi_pb / 1000.0, 2), year=2016, com=13, ax=cax)
    sel = slice(CUTFLOW_STEPS.index("trigger"), n_steps)
    r = np.divide(cd, cm, out=np.full(n_steps, np.nan), where=cm > 0)
    r_err = r * np.sqrt(np.divide(1.0, cd, out=np.full(n_steps, np.nan), where=cd > 0))
    rax.errorbar(xc[sel], r[sel], yerr=r_err[sel], fmt="ko", ms=4)
    rax.axhline(1.0, color="gray", ls="--")
    rax.set_yscale("log")
    rax.set_ylim(0.1, 20)  # log: the early steps compare different populations (SingleMuon PD vs inclusive DY)
    rax.set_ylabel("Data / MC (log)")
    rax.set_xticks(xc)
    rax.set_xticklabels(CUTFLOW_STEPS, rotation=45, ha="right")
    rax.set_xlabel("Selection step (cumulative)")
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(a.out_dir, "plots", f"cutflow.{ext}"), dpi=150 if ext == "png" else None,
                    bbox_inches="tight")
    plt.close(fig)

    # ---- checks ----
    n_out_d = sum(int(r_["EVENTS_OUT"]) for r_ in data_logs)
    n_out_m = sum(int(r_["EVENTS_OUT"]) for r_ in mc_logs)
    merged_d = int(uproot.open(a.data)["Events"].num_entries)
    merged_m = int(uproot.open(a.mc)["Events"].num_entries)
    check("data events_out equals merged entries", n_out_d == merged_d, f"{n_out_d} vs {merged_d}")
    check("mc events_out equals merged entries", n_out_m == merged_m, f"{n_out_m} vs {merged_m}")
    rel = abs(sumw_orig - sumw_merged) / sumw_orig
    check("SUMW original == merged skim", rel < 1e-9, f"{sumw_orig:.10g} vs {sumw_merged:.10g} (rel {rel:.2e})")
    sumw_read = sum(float(r_["SUMW_READ"]) for r_ in mc_logs)
    rel_read = abs(sumw_read - sumw_orig) / sumw_orig
    check("SUMW_READ over full files == Runs SUMW", rel_read < 1e-4, f"{sumw_read:.10g} vs {sumw_orig:.10g} (rel {rel_read:.2e})")
    check("lumi: no missing lumi sections", int(lumi["N_LS_MISSING"]) == 0, f"N_LS_MISSING={lumi['N_LS_MISSING']}")
    check("efficiency-like fraction in [0,1]", 0.0 <= neg_frac <= 1.0 and 0.0 <= data_events / max(len(mll_d), 1) <= 1.0,
          f"neg_frac={neg_frac:.4f}")
    check("Z window populated in data", data_events > 1000, f"{data_events} events in 81-101 GeV")
    check("data/MC in window in plausible range", 0.5 < data_over_mc < 2.0, f"{data_over_mc:.4f}")
    # cutflow checks
    cf_data_eq = (cf_d_file["n_all"] == cf_d_merged["n_all"] and cf_d_file["n_lumimask"] == cf_d_merged["n_lumimask"]
                  and cf_d_file["cutflow"] == cf_d_merged["cutflow"] and cf_d_file["nminus1"] == cf_d_merged["nminus1"])
    cf_mc_eq = (cf_m_file["n_all"] == cf_m_merged["n_all"] and cf_m_file["cutflow"] == cf_m_merged["cutflow"]
                and cf_m_file["nminus1"] == cf_m_merged["nminus1"])
    w_keys = ("w_all", "w_lumimask")
    cf_mc_w_eq = all(abs(cf_m_file[k] - cf_m_merged[k]) <= 1e-9 * abs(cf_m_file[k]) for k in w_keys) and all(
        abs(cf_m_file["cutflow_w"][s] - cf_m_merged["cutflow_w"][s]) <= 1e-9 * abs(cf_m_file["cutflow_w"][s])
        and abs(cf_m_file["nminus1_w"][s] - cf_m_merged["nminus1_w"][s]) <= 1e-9 * abs(cf_m_file["nminus1_w"][s])
        for s in SKIM_STEPS)
    skim_per_file_equals_merged = bool(cf_data_eq and cf_mc_eq and cf_mc_w_eq)
    check("skim cutflow: per-file sum == merged (data, MC)", skim_per_file_equals_merged,
          f"data counts {cf_data_eq}, MC counts {cf_mc_eq}, MC weights {cf_mc_w_eq}")
    check("skim cutflow: merged input files == 3", cf_d_merged["n_input_files"] == 3 and cf_m_merged["n_input_files"] == 3,
          f"{cf_d_merged['n_input_files']}, {cf_m_merged['n_input_files']}")
    last_d = cf_d_merged["cutflow"][SKIM_STEPS[-1]]
    last_m = cf_m_merged["cutflow"][SKIM_STEPS[-1]]
    check("skim cutflow: last skim step == merged Events entries (data, MC)", last_d == merged_d and last_m == merged_m,
          f"{last_d} vs {merged_d}; {last_m} vs {merged_m}")
    check("cutflow all (data) == events_in", cf_d_merged["n_all"] == sum(int(r_["EVENTS_IN"]) for r_ in data_logs),
          f"{cf_d_merged['n_all']}")
    all_mc_norm = mc_seq[0]
    rel_all = abs(all_mc_norm - XSEC_PB * lumi_pb) / (XSEC_PB * lumi_pb)
    check("MC normalised 'all' == xsec * lumi (W_ALL/SUMW ~ 1)", rel_all < 1e-4,
          f"{all_mc_norm:.8g} vs {XSEC_PB * lumi_pb:.8g} (rel {rel_all:.2e})")
    check("analysis z_window (cutflow) == z_peak (independent selection), data",
          int(round(data_seq[-1])) == data_events, f"{data_seq[-1]:.0f} vs {data_events}")
    rel_mc = abs(mc_seq[-1] - mc_norm) / mc_norm
    check("analysis z_window (cutflow) == z_peak (independent selection), MC", rel_mc < 1e-9,
          f"{mc_seq[-1]:.10g} vs {mc_norm:.10g} (rel {rel_mc:.2e})")
    check("skim muon_pt sequential == two_muons skim count (data, MC)",
          data_seq[CUTFLOW_STEPS.index("muon_pt")] == data_seq[CUTFLOW_STEPS.index("two_muons")]
          and abs(mc_seq[CUTFLOW_STEPS.index("muon_pt")] - mc_seq[CUTFLOW_STEPS.index("two_muons")]) < 1e-9 * mc_seq[0],
          f"{data_seq[CUTFLOW_STEPS.index('muon_pt')]:.0f} vs {data_seq[CUTFLOW_STEPS.index('two_muons')]:.0f}")
    mono_d = all(data_seq[i + 1] <= data_seq[i] for i in range(1, n_steps - 1))
    mono_m = all(mc_seq[i + 1] <= mc_seq[i] for i in range(1, n_steps - 1))
    check("sequential cutflow is non-increasing (data, MC)", mono_d and mono_m, f"{mono_d}, {mono_m}")

    # ---- summary.json (exact keys from PROMPT.md) ----
    def total(logs, key):
        return sum(int(r_[key]) for r_ in logs)

    cutflow_block = {
        "steps": CUTFLOW_STEPS,
        "skim_steps": SKIM_STEPS,
        "data": {"sequential": [int(round(x)) for x in data_seq],
                 "nminus1": [None if x is None else int(round(x)) for x in data_nm1]},
        "mc_normalised": {"sequential": [float(x) for x in mc_seq],
                          "nminus1": [None if x is None else float(x) for x in mc_nm1]},
        "skim_per_file_equals_merged": skim_per_file_equals_merged,
    }
    summary = {
        "data": {
            "n_files": len(data_logs),
            "events_in": total(data_logs, "EVENTS_IN"),
            "events_after_lumimask": total(data_logs, "EVENTS_AFTER_LUMIMASK"),
            "events_out": n_out_d,
            "merged_entries": merged_d,
            "n_ls": int(lumi["N_LS"]),
            "lumi_pb": round(lumi_pb, 6),
            "input_bytes": int(sizes["INPUT_BYTES_DATA"]),
            "skim_bytes": sum(os.path.getsize(f) for f in data_files),
        },
        "mc": {
            "n_files": len(mc_logs),
            "events_in": total(mc_logs, "EVENTS_IN"),
            "events_out": n_out_m,
            "merged_entries": merged_m,
            "sumw_runs_original": sumw_orig,
            "sumw_runs_merged_skim": sumw_merged,
            "sumw_read": sumw_read,
            "neg_weight_fraction": neg_frac,
            "xsec_pb": XSEC_PB,
            "weight_factor": weight_factor,
            "input_bytes": int(sizes["INPUT_BYTES_MC"]),
            "skim_bytes": sum(os.path.getsize(f) for f in mc_files),
        },
        "golden_2016_lumi_fb": float(golden["LUMI_FB"]),
        "z_peak": {
            "data_events": data_events,
            "mc_events_normalised": mc_norm,
            "mc_stat_unc": mc_stat,
            "data_over_mc": data_over_mc,
        },
        "cutflow": cutflow_block,
    }
    with open(os.path.join(a.out_dir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
        f.write("\n")
    print(json.dumps(summary, indent=2))

    n_ok = sum(CHECKS)
    print(f"SUMMARY={n_ok}/{len(CHECKS)}")
    return 0 if n_ok == len(CHECKS) else 1


if __name__ == "__main__":
    sys.exit(main())
