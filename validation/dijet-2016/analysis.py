#!/usr/bin/env python3
"""Dijet b-tag resonance validation: histograms, trigger turn-on, fits, injection, plots, summary.json, HEPData.

Usage (LCG_109 view sourced):
    python3 analysis.py --skims '<dir>/output_*.npz' --outdir <dir-for-plots-summary> [--toys 200]

Reads the flat skims written by skim.py (condor payload). Units: GeV, luminosity in fb^-1.
"""
import argparse, glob, json, os, subprocess, sys, time
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dijetlib as D


def find_repo_root(start):
    """Walk up from `start` to the directory that contains plugins/cms/skills/trigger-efficiency (no absolute paths)."""
    p = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(p, "plugins", "cms", "skills", "trigger-efficiency", "scripts")):
            return p
        if os.path.dirname(p) == p:
            raise RuntimeError("repository root (with plugins/cms/skills/trigger-efficiency) not found above " + start)
        p = os.path.dirname(p)


REPO_ROOT = find_repo_root(HERE)
# trigger-efficiency skill helpers: efficiency (Clopper-Pearson), find_threshold, plateau, plot_turnon
sys.path.insert(0, os.path.join(REPO_ROOT, "plugins", "cms", "skills", "trigger-efficiency", "scripts"))
import turnon as skill_turnon
from turnon import efficiency, find_threshold, plateau, plot_turnon

# the skill's dijet edges must be a subset of the local full table (same bins as before)
assert set(skill_turnon.DIJET_EDGES) <= set(D.DIJET_EDGES), "skill DIJET_EDGES differ from dijetlib.DIJET_EDGES"

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplhep as hep
from hist import Hist

plt.style.use(hep.style.CMS)

BTAG_JSON = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/BTV/2016postVFP_UL/btagging.json.gz"
GOLDEN_URL = "root://eospublic.cern.ch//eos/opendata/cms/validated-runs/2016/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt"
LUMI_URL = "root://eospublic.cern.ch//eos/opendata/cms/luminosity/2016/pp_2016lumibyls.csv"
# GenXsecAnalyzer values (pb) from the Open Data MINIAODSIM records, see specification.md
QCD_XSEC = {"700to1000": (6425.0, 63139), "1000to1500": (1117.0, 63078),
            "1500to2000": (108.3, 63094), "2000toInf": (21.94, 63102)}
SIG_XSEC_PB = 1.0          # assumed sigma x B for Z' (no value in the records)
PSIG_XSEC_PB = 1e-3        # sigma used for the pseudo-significance (small-signal regime)
SIG_TRIG_MASK = None       # set from skim info
FIT_MAX = 8152.0
TRIGGER_TARGET = 0.995     # plateau target (same as before the refactor)
MIN_REF_EVENTS = 100       # find_threshold default: reference events required above the threshold
CATS = ["incl", "1b", "2b"]
LABEL_TXT = "Open Data"

plot_files = []


def savefig(fig, outdir, name):
    os.makedirs(os.path.join(outdir, "plots"), exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(outdir, "plots", f"{name}.{ext}"), bbox_inches="tight", dpi=130)
    plot_files.append(f"plots/{name}.png")
    plt.close(fig)


def cms_label(ax, lumi, mc_only=False):
    hep.cms.label(LABEL_TXT, data=not mc_only, lumi=f"{lumi:.1f}" if lumi else None, com=13, ax=ax, loc=0)


def fetch(url, dest):
    if not os.path.exists(dest):
        subprocess.run(["xrdcp", "-f", "-s", url, dest], check=True)
    return dest


# ------------------------------------------------------------------ event-level quantities

def derive(s, with_bhi=True):
    s["deta"] = np.abs(s["eta1"] - s["eta2"]).astype(np.float32)
    if with_bhi:
        s["bhi"] = np.maximum(s["btag1"], s["btag2"]); s["blo"] = np.minimum(s["btag1"], s["btag2"])
    s["nbM"] = ((s["btag1"] > D.WP["M"]).astype(np.int8) + (s["btag2"] > D.WP["M"]).astype(np.int8))
    if "trig" in s:
        s["sigtrig"] = (s["trig"] & SIG_TRIG_MASK) > 0
    return s


def cat_mask(s, cat):
    if cat == "incl":
        return np.ones(len(s["mjj"]), bool)
    return s["nbM"] >= (1 if cat == "1b" else 2)


def hist_dijet(vals, edges, w=None):
    n, _ = np.histogram(vals, edges, weights=w)
    if w is None:
        return n.astype(float), np.sqrt(n)
    n2, _ = np.histogram(vals, edges, weights=w ** 2)
    return n, np.sqrt(n2)


# ------------------------------------------------------------------ main

def main():
    global SIG_TRIG_MASK, LABEL_TXT
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skims", required=True, help="glob of skim .npz files (xrdcp them from EOS first)")
    ap.add_argument("--outdir", required=True, help="where plots/, summary.json, hepdata/ are written")
    ap.add_argument("--toys", type=int, default=200)
    ap.add_argument("--work", default=None, help="scratch dir for downloaded POG/lumi files (default: outdir/.cache)")
    ap.add_argument("--no-hepdata", action="store_true")
    a = ap.parse_args()
    outdir = a.outdir
    os.makedirs(outdir, exist_ok=True)
    work = a.work or os.path.join(outdir, ".cache")
    os.makedirs(work, exist_ok=True)
    paths = sorted(glob.glob(a.skims))
    if not paths:
        sys.exit("no skim files found")
    t0 = time.time()
    summary = {"environment": {}, "inputs": {}}
    import iminuit, uproot, hist as histmod, mplhep, awkward
    summary["environment"] = {"python": sys.version.split()[0], "iminuit": iminuit.__version__, "numpy": np.__version__,
                              "hist": histmod.__version__, "mplhep": mplhep.__version__, "uproot": uproot.__version__,
                              "awkward": awkward.__version__}

    # ---- working points from the BTV POG json
    import correctionlib
    cs = correctionlib.CorrectionSet.from_file(BTAG_JSON)
    for k in "LMT":
        D.WP[k] = float(cs["deepJet_wp_values"].evaluate(k))
    summary["btag_wp_deepjet_2016postVFP_UL"] = dict(D.WP)

    # ---- metadata, certification, luminosity
    infos, first = D.read_meta(paths)
    nsig = first["n_sig_trigs"]
    SIG_TRIG_MASK = np.uint32((1 << nsig) - 1)
    trig_names = first["trigs"]
    ref_bit = {n: i for i, n in enumerate(trig_names)}
    summary["triggers"] = {"signal_or": trig_names[:nsig], "reference": trig_names[nsig:]}
    summary["inputs"] = {"skim_files": [os.path.basename(p) for p in paths]}
    for s, I in infos.items():
        summary["inputs"][s] = {"n_files": len(I["files"]), "n_events_total": int(I["n_total"]),
                                "n_events_skim": int(I["n_sel"]), "sumw": I["sumw"]}
    with open(os.path.join(outdir, "input_files.json"), "w") as f:
        json.dump({s: sorted(I["files"]) for s, I in infos.items()}, f, indent=0)
    golden = D.golden_keys(fetch(GOLDEN_URL, os.path.join(work, "golden.json")))
    lumi_csv = fetch(LUMI_URL, os.path.join(work, "lumibyls.csv"))
    proc_keys = np.intersect1d(infos["data"]["ls"], golden)
    lumi_fb, n_ls_csv, n_ls = D.recorded_lumi_fb(lumi_csv, proc_keys)
    L_pb = lumi_fb * 1000.0

    # ================================================================= 2. trigger efficiency (pass 1 over data, streaming)
    EDG = D.DIJET_EDGES
    tedges = EDG[(EDG >= 800) & (EDG <= 2500)]
    tc = 0.5 * (tedges[1:] + tedges[:-1])
    refs = trig_names[nsig:]
    acc = {r_: {"num": np.zeros(len(tedges) - 1), "den": np.zeros(len(tedges) - 1)} for r_ in refs}
    n_before = n_after = 0
    for s_, o, nb, na in D.iter_events(paths, ["run", "lumi", "mjj", "eta1", "eta2", "trig"], {}, golden, only="data"):
        n_before += nb; n_after += na
        base = np.abs(o["eta1"] - o["eta2"]) < 1.1
        sg = (o["trig"] & SIG_TRIG_MASK) > 0
        for r_ in refs:
            rm = base & (((o["trig"] >> ref_bit[r_]) & 1) > 0)
            acc[r_]["den"] += np.histogram(o["mjj"][rm], tedges)[0]
            acc[r_]["num"] += np.histogram(o["mjj"][rm & sg], tedges)[0]
    summary["luminosity"] = {"recorded_fb": lumi_fb, "n_lumisections_processed_and_golden": n_ls,
                             "n_lumisections_found_in_csv": n_ls_csv,
                             "source": "Open Data record 1059 pp_2016lumibyls.csv, recorded column; golden JSON record 14220",
                             "fraction_events_in_golden": n_after / max(n_before, 1), "uncertainty_pct": 1.2}
    print(f"data skim events {n_before}, golden {n_after}, lumi {lumi_fb:.3f}/fb ({n_ls_csv}/{n_ls} LS in csv)", flush=True)
    # counts -> efficiency with the skill helpers (68% Clopper-Pearson; NaN where den == 0)
    trig_res = {r_: efficiency(acc[r_]["num"], acc[r_]["den"]) for r_ in refs}
    thr, ithr = find_threshold(trig_res["HLT_PFJet260"], tedges, target=TRIGGER_TARGET, min_events=MIN_REF_EVENTS)
    if ithr < 0:
        raise RuntimeError("no trigger plateau found")
    THR = thr
    r = trig_res["HLT_PFJet260"]
    pe, plo, phi, n = plateau(r, ithr)
    k = r["num"][ithr:].sum()
    summary["trigger"] = {
        "reference": "HLT_PFJet260", "selection": "tight-ID leading jets |eta|<2.4, |deta|<1.1, golden JSON",
        "threshold_mjj_GeV": THR, "plateau_efficiency": float(pe), "plateau_err_low": float(pe - plo),
        "plateau_err_high": float(phi - pe), "plateau_events_ref": int(n), "plateau_events_pass": int(k),
        "threshold_rule": "lowest dijet-binning edge with all higher bins having Clopper-Pearson (68%) upper bound >= 0.995 and pooled efficiency >= 0.995",
        "threshold_target": TRIGGER_TARGET, "threshold_min_ref_events_above": MIN_REF_EVENTS,
        "crosschecks": {}}
    for refname in ("HLT_PFHT475", "HLT_PFJet400"):
        rr = trig_res[refname]
        e2, l2, h2, nn = plateau(rr, ithr)      # plateau above the main threshold
        thr2, _ = find_threshold(rr, tedges, target=TRIGGER_TARGET, min_events=MIN_REF_EVENTS)
        summary["trigger"]["crosschecks"][refname] = {"plateau_efficiency_above_threshold": float(e2), "events_ref": int(nn),
                                                      "own_threshold_GeV": thr2}
    # efficiency vs mjj plot (skill helper draws asymmetric CP errors and skips empty bins)
    fig, ax = plt.subplots(figsize=(10, 8))
    plot_turnon(ax, r, tedges, "ref. HLT_PFJet260", color="k")
    for refname, col, mk in (("HLT_PFHT475", "tab:blue", "s"), ("HLT_PFJet400", "tab:red", "^")):
        plot_turnon(ax, trig_res[refname], tedges + 6, f"ref. {refname} (cross-check)", fmt=mk, color=col, ms=5, alpha=0.6)
    ax.axvline(THR, color="tab:green", ls="--", label=f"$m_{{jj}}$ > {THR:.0f} GeV")
    ax.axhline(pe, color="gray", ls=":", label=f"plateau {pe:.4f}")
    ax.set_xlabel(r"$m_{jj}$ [GeV]"); ax.set_ylabel("Trigger efficiency")
    ax.set_ylim(0.0, 1.15); ax.legend(loc="lower right", fontsize=14)
    ax.text(0.40, 0.30, "OR of PFHT900/800, PFJet450/500,\nCaloJet500, AK8PFJet450/500\n$|\\eta|<2.4$, $|\\Delta\\eta_{jj}|<1.1$", transform=ax.transAxes, fontsize=14)
    cms_label(ax, lumi_fb)
    savefig(fig, outdir, "trigger_efficiency")
    summary["trigger"]["efficiency_vs_mjj"] = {"edges": tedges.tolist(), "num": r["num"].tolist(), "den": r["den"].tolist()}


    # ---- pass 2: load the events above the threshold (MC signal: everything, for b-tag efficiencies)
    cols = ["eta1", "eta2", "mjj", "btag1", "btag2", "trig", "flav1", "flav2", "genw", "run", "lumi"]
    chunks = {}
    for s_, o, nb, na in D.iter_events(paths, cols, {"data": THR, "qcd": THR, "sig": 0.0}, golden):
        if s_ == "data":     # every data plot/fit uses the signal-trigger OR: apply it here to save memory
            keep = (o["trig"] & SIG_TRIG_MASK) > 0
            o = {k_: v_[keep] for k_, v_ in o.items()}
        for k_, v_ in o.items():
            chunks.setdefault(s_, {}).setdefault(k_, []).append(v_)
    samples = {s_: {k_: np.concatenate(v_) for k_, v_ in c_.items()} for s_, c_ in chunks.items()}
    del chunks
    for s in samples:
        samples[s].pop("run", None); samples[s].pop("lumi", None)
        derive(samples[s], with_bhi=(s == "data" or s.startswith("sig_")))
    dat = samples["data"]
    for s, d in samples.items():
        if s == "data":
            continue
        xs = SIG_XSEC_PB if s.startswith("sig_") else QCD_XSEC[s[4:]][0]
        d["w"] = (d.pop("genw").astype(np.float64) * (xs * L_pb / infos[s]["sumw"]))
    qcd_names = sorted([s for s in samples if s.startswith("qcd_")], key=lambda x: float(x[4:].split("to")[0]))
    # M < 1000 GeV is truncated by the skim cut m_jj > 800 GeV, so those samples are not used
    sig_masses = sorted(int(s[4:]) for s in samples if s.startswith("sig_") and int(s[4:]) >= 1000)
    summary["mc_normalisation"] = {
        "qcd_xsec_pb": {k: {"xsec_pb": v[0], "opendata_record": v[1]} for k, v in QCD_XSEC.items() if f"qcd_{k}" in samples},
        "signal_xsec_pb_assumed": SIG_XSEC_PB, "pseudo_significance_xsec_pb": PSIG_XSEC_PB}
    print({s: len(d["mjj"]) for s, d in samples.items()}, flush=True)

    # ================================================================= full selection
    def full_sel(s, is_data):
        m = (s["deta"] < 1.1) & (s["mjj"] > THR)
        if is_data:
            m &= s["sigtrig"]
        return m

    sel = {s: full_sel(d, s == "data") for s, d in samples.items()}
    ev = {c: int((sel["data"] & cat_mask(dat, c)).sum()) for c in CATS}
    summary["events_data_full_selection"] = ev
    summary["events_qcd_full_selection"] = {c: float(sum(samples[q]["w"][sel[q] & cat_mask(samples[q], c)].sum() for q in qcd_names)) for c in CATS}
    print("data events per category:", ev)

    # ================================================================= 1. deta and eta
    def shape_panel(ax, vals_d, vals_q, wq, vals_s, ws, bins, xlabel):
        hd, _ = np.histogram(vals_d, bins); hd = hd.astype(float)
        hq, _ = np.histogram(vals_q, bins, weights=wq)
        hs, _ = np.histogram(vals_s, bins, weights=ws)
        w = np.diff(bins)
        nd = hd.sum() if hd.sum() > 0 else 1
        ax.stairs(hq / hq.sum() / w, bins, color="tab:orange", fill=True, alpha=0.6, label="QCD MC (shape)")
        ax.stairs(hs / hs.sum() / w, bins, color="tab:red", lw=2, label="Z' 2 TeV MC")
        c = 0.5 * (bins[1:] + bins[:-1])
        ax.errorbar(c, hd / nd / w, yerr=np.sqrt(hd) / nd / w, xerr=w / 2, fmt="ko", label="Data")
        ax.set_xlabel(xlabel); ax.set_ylabel("Normalised events / unit")

    for cat in ("1b", "2b"):
        fig, axs = plt.subplots(1, 2, figsize=(20, 8))
        # delta eta: no deta cut
        def sel_nodeta(s, is_data):
            m = (s["mjj"] > THR) & cat_mask(s, cat)
            return m & s["sigtrig"] if is_data else m
        mq = {q: sel_nodeta(samples[q], False) for q in qcd_names}
        sg = samples["sig_2000"]; ms = sel_nodeta(sg, False)
        md = sel_nodeta(dat, True)
        bins = np.linspace(0, 4.8, 25)
        shape_panel(axs[0], dat["deta"][md], np.concatenate([samples[q]["deta"][mq[q]] for q in qcd_names]),
                    np.concatenate([samples[q]["w"][mq[q]] for q in qcd_names]), sg["deta"][ms], sg["w"][ms], bins,
                    r"$|\Delta\eta(j_1,j_2)|$")
        axs[0].axvline(1.1, color="gray", ls="--"); axs[0].set_yscale("log"); axs[0].legend(fontsize=14)
        # eta of both jets (deta cut)
        md = md & (dat["deta"] < 1.1)
        mq = {q: mq[q] & (samples[q]["deta"] < 1.1) for q in qcd_names}
        ms = ms & (sg["deta"] < 1.1)
        eb = np.linspace(-2.4, 2.4, 25)
        two = lambda s, m: np.concatenate([s["eta1"][m], s["eta2"][m]])
        shape_panel(axs[1], two(dat, md), np.concatenate([two(samples[q], mq[q]) for q in qcd_names]),
                    np.concatenate([np.tile(samples[q]["w"][mq[q]], 2) for q in qcd_names]), two(sg, ms), np.tile(sg["w"][ms], 2), eb,
                    r"$\eta(j)$")
        axs[1].set_ylim(0, axs[1].get_ylim()[1] * 1.3)
        for ax in axs:
            cms_label(ax, lumi_fb)
        axs[0].text(0.5, 0.55, f"{cat}, $m_{{jj}}$ > {THR:.0f} GeV", transform=axs[0].transAxes, fontsize=16)
        savefig(fig, outdir, f"deta_eta_{cat}")

    # ================================================================= 3. b-tag efficiency vs Z' mass
    btag_rows = []
    for M in sig_masses:
        s = samples[f"sig_{M}"]; base_m = s["deta"] < 1.1
        row = {"mass": M, "n_generated": int(infos[f"sig_{M}"]["n_total"]), "n_selected_deta": int(base_m.sum())}
        b1 = base_m & (s["flav1"] == 5); b2 = base_m & (s["flav2"] == 5)
        nb = int(b1.sum() + b2.sum()); row["n_true_b_jets"] = nb
        for k in "LMT":
            kk = int((s["btag1"][b1] > D.WP[k]).sum() + (s["btag2"][b2] > D.WP[k]).sum())
            e, lo, hi = D.clopper_pearson(kk, nb)
            row[f"eff_{k}"] = float(e); row[f"eff_{k}_lo"] = float(e - lo); row[f"eff_{k}_hi"] = float(hi - e)
        full = full_sel(s, False)
        for c in ("1b", "2b"):
            kk = int((full & cat_mask(s, c)).sum()); e, lo, hi = D.clopper_pearson(kk, row["n_generated"])
            row[f"event_eff_{c}_medium"] = float(e); row[f"event_eff_{c}_medium_err"] = float(hi - e)
            row[f"event_eff_{c}_rel_to_selected"] = float(kk / max(full.sum(), 1))
        btag_rows.append(row)
    summary["btag_efficiency"] = btag_rows
    fig, ax = plt.subplots(figsize=(10, 8))
    for k, col in zip("LMT", ("tab:green", "tab:blue", "tab:red")):
        y = np.array([r_[f"eff_{k}"] for r_ in btag_rows])
        ax.errorbar(sig_masses, y, yerr=[[r_[f"eff_{k}_lo"] for r_ in btag_rows], [r_[f"eff_{k}_hi"] for r_ in btag_rows]],
                    fmt="o-", color=col, label={"L": "Loose", "M": "Medium", "T": "Tight"}[k] + f" ({D.WP[k]:.4g})")
    ax.set_xlabel(r"Z' mass [GeV]"); ax.set_ylabel("DeepJet b-tag efficiency (true b jets)")
    ax.set_ylim(0, 1.15); ax.legend(title="DeepJet WP (2016postVFP_UL)", loc="lower left", fontsize=14)
    cms_label(ax, None, mc_only=True)
    savefig(fig, outdir, "btag_efficiency_vs_mass")

    # ================================================================= fit machinery per category
    fit_edges = EDG[(EDG >= THR) & (EDG <= FIT_MAX)]
    fc = 0.5 * (fit_edges[1:] + fit_edges[:-1]); fw = np.diff(fit_edges)
    n_by_cat, fits, chosen, ftests = {}, {}, {}, {}
    for cat in ("1b", "2b"):
        m = sel["data"] & cat_mask(dat, cat)
        n, _ = np.histogram(dat["mjj"][m], fit_edges)
        n_by_cat[cat] = n.astype(float)
        fl = []
        prev = None
        for npar in (3, 4, 5):
            st = None
            if prev is not None:
                st = list(prev["par"])
            r_ = D.fit_background(fit_edges, n, npar, start=st)
            fl.append(r_); prev = r_
        fits[cat] = fl
        ft = D.ftest([f_["dev"] for f_ in fl], [3, 4, 5], len(n))
        ftests[cat] = ft
        # lowest n such that the next function is not significantly better (p > 0.05)
        ch = 3
        for row in ft:
            if row["p"] < 0.05:
                ch = row["n_to"]
            else:
                break
        chosen[cat] = ch
    fit_summary = {}
    for cat in ("1b", "2b"):
        fit_summary[cat] = {
            "n_bins": int(len(fit_edges) - 1), "fit_range_GeV": [float(fit_edges[0]), float(fit_edges[-1])],
            "n_events_in_fit": int(n_by_cat[cat].sum()), "chosen_nparams": chosen[cat],
            "fit_edges_GeV": fit_edges.tolist(), "data_counts": n_by_cat[cat].tolist(),
            "fit_expectation_chosen": fits[cat][chosen[cat] - 3]["mu"].tolist(),
            "fits": {str(f_["npar"]): {"chi2_poisson_deviance": f_["dev"], "ndf": f_["ndf"], "chi2_ndf": f_["dev"] / f_["ndf"],
                                        "valid": f_["valid"], "edm": f_["edm"],
                                        "params": dict(zip(D.PNAMES, f_["par"])), "errors": dict(zip(D.PNAMES, f_["err"]))}
                     for f_ in fits[cat]},
            "ftest": ftests[cat]}
        c = fit_summary[cat]["fits"][str(chosen[cat])]
        fit_summary[cat]["chi2_ndf_chosen"] = c["chi2_ndf"]
    summary["fit"] = fit_summary

    # signal templates (unit sum over the fit range) per category
    def template(M, cat):
        s = samples[f"sig_{M}"]; m = full_sel(s, False) & cat_mask(s, cat)
        h, _ = np.histogram(s["mjj"][m], fit_edges)
        return h.astype(float), s["w"][m]

    # ================================================================= 5. data vs QCD
    qcd_colors = ["#a6cee3", "#1f78b4", "#b2df8a", "#33a02c"]
    plot_mass = [m_ for m_ in (1600, 2000, 3000, 4000) if m_ in sig_masses]
    for cat in CATS:
        pe_edges = EDG[(EDG >= THR) & (EDG <= FIT_MAX)]
        pw = np.diff(pe_edges); pc = 0.5 * (pe_edges[1:] + pe_edges[:-1])
        md = sel["data"] & cat_mask(dat, cat)
        hd, _ = np.histogram(dat["mjj"][md], pe_edges)
        hq = []
        for q in qcd_names:
            mq_ = sel[q] & cat_mask(samples[q], cat)
            h_, _ = np.histogram(samples[q]["mjj"][mq_], pe_edges, weights=samples[q]["w"][mq_]); hq.append(h_)
        tot = np.sum(hq, axis=0)
        fig, (ax, rax) = plt.subplots(2, 1, figsize=(10, 11), gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05}, sharex=True)
        hep.histplot(list(np.array(hq) / pw), pe_edges, stack=True, histtype="fill", color=qcd_colors[:len(qcd_names)],
                     label=[f"QCD HT{q[4:]}" for q in qcd_names], ax=ax)
        ax.errorbar(pc, hd / pw, yerr=np.sqrt(hd) / pw, fmt="ko", ms=5, label="Data")
        for M, col in zip(plot_mass, ("tab:red", "tab:purple", "tab:brown", "tab:pink")):
            s = samples[f"sig_{M}"]; ms = sel[f"sig_{M}"] & cat_mask(s, cat)
            hs, _ = np.histogram(s["mjj"][ms], pe_edges, weights=s["w"][ms])
            ax.stairs(hs / pw, pe_edges, color=col, lw=2, label=f"Z' {M/1000:g} TeV ($\\sigma$B=1 pb)")
        ax.set_yscale("log"); ax.set_ylabel("Events / GeV"); ax.set_ylim(1e-5, None)
        ax.legend(fontsize=13, ncol=2, loc="upper right")
        ax.text(0.04, 0.05, f"category: {cat}, $|\\Delta\\eta_{{jj}}|<1.1$\nMC: no b-tag SF, no PU rw", transform=ax.transAxes, fontsize=14)
        cms_label(ax, lumi_fb)
        with np.errstate(divide="ignore", invalid="ignore"):
            ratio = hd / tot; rerr = np.sqrt(hd) / tot
        rax.errorbar(pc, ratio, yerr=rerr, fmt="ko", ms=5); rax.axhline(1, color="gray", ls="--")
        rax.set_ylim(0, 2.5); rax.set_ylabel("Data / QCD"); rax.set_xlabel(r"$m_{jj}$ [GeV]")
        savefig(fig, outdir, f"mjj_data_vs_qcd_{cat}")
        summary.setdefault("data_over_qcd_integrated", {})[cat] = {"data": float(hd.sum()), "qcd": float(tot.sum()),
                                                                   "ratio": float(hd.sum() / tot.sum()) if tot.sum() > 0 else None}

    # ================================================================= 6. fit plots and F-test table
    for cat in ("1b", "2b"):
        n = n_by_cat[cat]; fch = fits[cat][chosen[cat] - 3]
        fig, (ax, pax) = plt.subplots(2, 1, figsize=(10, 11), gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05}, sharex=True)
        ax.errorbar(fc, n / fw, yerr=np.sqrt(np.maximum(n, 1e-9)) / fw, xerr=fw / 2, fmt="ko", ms=5, label="Data")
        ax.plot(fc, fch["mu"] / fw, "-", color="tab:blue", lw=2,
                label=f"Dijet fit, {chosen[cat]} par.: $\\chi^2$/ndf = {fch['dev']:.1f}/{fch['ndf']} = {fch['dev']/fch['ndf']:.2f}")
        for M, col in zip(plot_mass, ("tab:red", "tab:purple", "tab:brown", "tab:pink")):
            h, w_ = template(M, cat)
            ax.stairs(np.histogram(samples[f"sig_{M}"]["mjj"][full_sel(samples[f"sig_{M}"], False) & cat_mask(samples[f"sig_{M}"], cat)], fit_edges,
                                   weights=w_)[0] / fw, fit_edges, color=col, lw=2, label=f"Z' {M/1000:g} TeV ($\\sigma$B=1 pb)")
        ax.set_yscale("log"); ax.set_ylabel("Events / GeV"); ax.set_ylim(1e-4, None)
        ax.legend(fontsize=13, loc="upper right")
        ax.text(0.04, 0.05, f"category: {cat}\n$p_0 = {np.exp(fch['par'][0]):.3g}$, " + ", ".join(f"$p_{i}$={fch['par'][i]:.3g}" for i in range(1, chosen[cat])),
                transform=ax.transAxes, fontsize=13)
        cms_label(ax, lumi_fb)
        pul = D.signed_pulls(n, fch["mu"])
        pax.bar(fc, pul, width=fw, color=np.where(np.abs(pul) > 2, "tab:red", "tab:blue"))
        pax.axhline(0, color="k", lw=0.8); pax.set_ylim(-4, 4); pax.set_ylabel("Pull"); pax.set_xlabel(r"$m_{jj}$ [GeV]")
        savefig(fig, outdir, f"fit_{cat}")
        fit_summary[cat]["pulls"] = pul.tolist()
        # F-test table
        fig, ax = plt.subplots(figsize=(10, 3.2)); ax.axis("off")
        rows = [[f"{r_['n_from']} to {r_['n_to']}", f"{r_['chi2_from']:.2f}", f"{r_['chi2_to']:.2f}", f"{r_['F']:.3f}", f"{r_['p']:.3f}",
                 "yes" if r_["p"] < 0.05 else "no"] for r_ in ftests[cat]]
        tb = ax.table(cellText=rows, colLabels=["parameters", "$\\chi^2$ (n)", "$\\chi^2$ (n+1)", "F", "p-value", "n+1 needed"], loc="center", cellLoc="center")
        tb.auto_set_font_size(False); tb.set_fontsize(14); tb.scale(1, 2)
        ax.set_title(f"F-test, category {cat}: chosen {chosen[cat]} parameters (CMS Open Data, {lumi_fb:.1f} fb$^{{-1}}$, 13 TeV)", fontsize=14)
        savefig(fig, outdir, f"ftest_{cat}")

    # ================================================================= 4. pseudo-significance
    combos = [("L", "L"), ("M", "M"), ("T", "T"), ("M", "L"), ("T", "M"), ("T", "L")]
    ps_rows = []
    zbest = {}
    ps_fit_cache = {}
    dm = sel["data"]
    for (wa, wb) in combos:
        mm = dm & (dat["bhi"] > D.WP[wa]) & (dat["blo"] > D.WP[wb])
        n, _ = np.histogram(dat["mjj"][mm], fit_edges)
        fb = D.fit_background(fit_edges, n.astype(float), 3)
        ps_fit_cache[(wa, wb)] = (n, fb)
        for M in sig_masses:
            lo_, hi_ = max(0.8 * M, THR), 1.05 * M
            if hi_ <= THR + 1:
                continue
            s = samples[f"sig_{M}"]
            ms = full_sel(s, False) & (s["bhi"] > D.WP[wa]) & (s["blo"] > D.WP[wb]) & (s["mjj"] >= lo_) & (s["mjj"] < hi_)
            # signal yield at sigma = PSIG_XSEC_PB: sum of w scaled from SIG_XSEC_PB
            sy = float(s["w"][ms].sum()) * PSIG_XSEC_PB / SIG_XSEC_PB
            # background: fit function integrated over the window (fine sub-binning)
            xs = np.linspace(lo_, hi_, 401)
            bkg = float(np.trapezoid(D.dijet_f(xs, *fb["par"]), xs))
            bkg_obs = int(((dat["mjj"][mm] >= lo_) & (dat["mjj"][mm] < hi_)).sum())
            bfl = max(bkg, 1.0)
            ps_rows.append({"combo": wa + wb, "mass": M, "s": sy, "b_fit": bkg, "b_obs": bkg_obs, "Z_asimov": float(D.asimov_z(sy, bfl)) if sy > 0 else 0.0})
    summary["pseudo_significance"] = {
        "definition": "Asimov Z with s from MC at sigma*B=1 fb, L=processed lumi; b = 3-par dijet fit of data (this WP combination) integrated in [max(0.8M,thr),1.05M], floored at 1 event",
        "rows": ps_rows}
    fig, ax = plt.subplots(figsize=(10, 8))
    cmap = plt.get_cmap("tab10")
    for i, (wa, wb) in enumerate(combos):
        rr = [r_ for r_ in ps_rows if r_["combo"] == wa + wb]
        ax.plot([r_["mass"] for r_ in rr], [r_["Z_asimov"] for r_ in rr], "o-", color=cmap(i), label=f"{wa}+{wb}")
    ax.set_yscale("log"); ax.set_xlabel(r"Z' mass [GeV]"); ax.set_ylabel(r"Pseudo-significance Z$_{Asimov}$ ($\sigma$B = 1 fb)")
    ax.legend(title="WP (higher+lower score jet)", fontsize=14, ncol=2)
    cms_label(ax, lumi_fb)
    savefig(fig, outdir, "pseudo_significance_2b")
    # best combination: highest Z, summed in quadrature over masses
    tot = {}
    for r_ in ps_rows:
        tot[r_["combo"]] = tot.get(r_["combo"], 0.0) + r_["Z_asimov"] ** 2
    summary["pseudo_significance"]["quadrature_sum_over_masses"] = {k: float(np.sqrt(v)) for k, v in tot.items()}
    summary["pseudo_significance"]["best_combo_quadrature_sum"] = max(tot, key=tot.get)
    per_mass_best = {}
    for M in sig_masses:
        rr = [r_ for r_ in ps_rows if r_["mass"] == M]
        if rr:
            per_mass_best[str(M)] = max(rr, key=lambda r_: r_["Z_asimov"])["combo"]
    summary["pseudo_significance"]["best_combo_per_mass"] = per_mass_best

    # ================================================================= 7. signal injection
    INJ_M = 2000 if 2000 in sig_masses else sig_masses[len(sig_masses) // 2]
    rng = np.random.default_rng(12345)
    inj_summary = {}
    for cat in ("1b", "2b"):
        n = n_by_cat[cat]; npar = chosen[cat]
        h, _ = template(INJ_M, cat)
        T = h / h.sum()
        lo_, hi_ = 0.8 * INJ_M, 1.05 * INJ_M
        wmask = (fc >= lo_) & (fc < hi_)
        frac_win = float(T[wmask].sum())
        b_win = float(n[wmask].sum())
        S_nom = float(3.0 * np.sqrt(max(b_win, 1.0)) / frac_win)
        res = {"mass": INJ_M, "category": cat, "template_events_mc": int(h.sum()), "bkg_events_in_window_data": b_win,
               "window_GeV": [lo_, hi_], "fraction_of_signal_in_window": frac_win, "S_nominal": S_nom, "nparams": npar, "scan": []}
        b0 = fits[cat][npar - 3]
        scan_plot = None
        for k in (0.0, 0.5, 1.0, 2.0, 3.0):
            S_true = k * S_nom
            Sdraw = int(rng.poisson(S_true)) if S_true > 0 else 0
            inj = rng.multinomial(Sdraw, T) if Sdraw > 0 else np.zeros(len(T), int)
            nn = n + inj
            fb_only = D.fit_background(fit_edges, nn, npar, start=b0["par"])
            fsb = D.fit_background(fit_edges, nn, npar, start=fb_only["par"], signal_template=T, s_start=float(Sdraw))
            ent = {"k": k, "S_injected_expected": S_true, "S_injected_actual": Sdraw, "S_recovered": fsb["S"], "S_err": fsb["S_err"],
                   "valid": fsb["valid"], "chi2_ndf_s_plus_b": fsb["dev"] / fsb["ndf"], "chi2_ndf_b_only": fb_only["dev"] / fb_only["ndf"],
                   "delta_nll_2x": float(fb_only["dev"] - fsb["dev"])}
            res["scan"].append(ent)
            if k == 1.0:
                scan_plot = (nn, fb_only, fsb, Sdraw)
        # toys: background from the fitted spectrum of the real data (no signal), signal Poisson at k=1
        toys = []
        mu_b = b0["mu"]
        for t in range(a.toys):
            nb_ = rng.poisson(mu_b).astype(float)
            Sd = int(rng.poisson(S_nom))
            nb_ = nb_ + (rng.multinomial(Sd, T) if Sd > 0 else 0)
            fo = D.fit_background(fit_edges, nb_, npar, start=b0["par"])
            fs = D.fit_background(fit_edges, nb_, npar, start=fo["par"], signal_template=T, s_start=float(Sd))
            if fs["valid"] and fs["S_err"] > 0:
                toys.append((Sd, fs["S"], fs["S_err"]))
        toys = np.array(toys)
        if len(toys):
            pull = (toys[:, 1] - toys[:, 0]) / toys[:, 2]
            res["toys"] = {"n_requested": a.toys, "n_valid": int(len(toys)), "S_true_mean": float(toys[:, 0].mean()),
                           "S_rec_mean": float(toys[:, 1].mean()), "bias_mean_rec_minus_inj": float((toys[:, 1] - toys[:, 0]).mean()),
                           "pull_mean": float(pull.mean()), "pull_std": float(pull.std(ddof=1)), "S_err_mean": float(toys[:, 2].mean())}
        inj_summary[cat] = res
        # ---- plots
        nn, fo, fs, Sd = scan_plot
        fig, (ax, pax) = plt.subplots(2, 1, figsize=(10, 11), gridspec_kw={"height_ratios": [3, 1], "hspace": 0.05}, sharex=True)
        ax.errorbar(fc, nn / fw, yerr=np.sqrt(np.maximum(nn, 1e-9)) / fw, xerr=fw / 2, fmt="ko", ms=5, label=f"Data + injected Z' ({Sd} events)")
        ax.plot(fc, fo["mu"] / fw, "--", color="tab:blue", lw=2, label="Background-only fit")
        ax.plot(fc, fs["mu"] / fw, "-", color="tab:red", lw=2, label=f"S+B fit: S = {fs['S']:.0f} $\\pm$ {fs['S_err']:.0f}")
        ax.plot(fc, fs["mu_b"] / fw, ":", color="tab:green", lw=2, label="B component")
        ax.set_yscale("log"); ax.set_ylabel("Events / GeV"); ax.set_ylim(1e-4, None); ax.legend(fontsize=13)
        ax.text(0.04, 0.05, f"category {cat}, Z' {INJ_M/1000:g} TeV, {npar}-par. background", transform=ax.transAxes, fontsize=14)
        cms_label(ax, lumi_fb)
        pul = D.signed_pulls(nn, fs["mu"])
        pax.bar(fc, pul, width=fw, color="tab:blue"); pax.axhline(0, color="k", lw=0.8); pax.set_ylim(-4, 4)
        pax.set_ylabel("Pull (S+B)"); pax.set_xlabel(r"$m_{jj}$ [GeV]")
        savefig(fig, outdir, f"injection_spectrum_{cat}")
        fig, axs = plt.subplots(1, 2, figsize=(20, 8))
        inj_x = np.array([e["S_injected_actual"] for e in res["scan"]]); rec = np.array([e["S_recovered"] for e in res["scan"]])
        err = np.array([e["S_err"] for e in res["scan"]])
        axs[0].errorbar(inj_x, rec, yerr=err, fmt="ko", label="Real data + injection")
        top = max(inj_x.max(), 1) * 1.1
        axs[0].plot([0, top], [0, top], "r--", label="recovered = injected")
        axs[0].set_xlabel("Injected events (Poisson draw of expected yield)"); axs[0].set_ylabel("Recovered signal yield"); axs[0].legend(fontsize=14)
        axs[0].text(0.04, 0.8, f"{cat}, Z' {INJ_M/1000:g} TeV", transform=axs[0].transAxes, fontsize=16)
        if len(toys):
            axs[1].hist(pull, bins=np.linspace(-5, 5, 21), color="tab:blue", alpha=0.7)
            axs[1].set_xlabel(r"(S$_{rec}$ - S$_{inj}$) / $\sigma_S$ (toys, k = 1)"); axs[1].set_ylabel("Toys")
            axs[1].text(0.04, 0.85, f"mean {pull.mean():.2f}, std {pull.std(ddof=1):.2f}\n{len(toys)} toys", transform=axs[1].transAxes, fontsize=14)
        for ax_ in axs:
            cms_label(ax_, lumi_fb)
        savefig(fig, outdir, f"injection_linearity_{cat}")
    summary["injection"] = inj_summary

    # ================================================================= summary + hepdata
    summary["plots"] = plot_files
    summary["runtime_s"] = time.time() - t0
    with open(os.path.join(outdir, "summary.json"), "w") as f:
        json.dump(summary, f, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else float(o))
    if not a.no_hepdata:
        import make_hepdata      # reads summary.json and plots/ only, so it can also be run standalone
        make_hepdata.main(["--summary", os.path.join(outdir, "summary.json"), "--plots", os.path.join(outdir, "plots"),
                           "-o", os.path.join(outdir, "hepdata"), "--log", os.path.join(outdir, "hepdata_validation.txt")])
    print("done in %.0fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
