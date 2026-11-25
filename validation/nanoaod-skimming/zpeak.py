#!/usr/bin/env python3
"""Step 4 of the nanoaod-skimming validation: Z -> mumu peak in the merged skims
(CMS Open Data, 2016 UL NanoAODv9, SingleMuon Run2016G and DYJetsToLL M-50 amcatnlo).

Also assembles summary.json from the KEY=VALUE logs written by run_all.sh.

Selection (both data and MC, no scale factors, no pileup weights):
  - muons with pT > 20 GeV, |eta| < 2.4, tightId, pfRelIso04_all < 0.15
  - exactly two such muons, opposite charge, leading pT > 26 GeV
MC weight: genWeight * XSEC * LUMI / SUMW (WEIGHT_FACTOR from sumw.py on the original files).

Exit codes: 0 all checks pass, 1 a check failed (printed), 2 bad inputs.
stdout: KEY=VALUE and CHECK lines.
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

CHECKS = []


def check(name, ok, detail):
    CHECKS.append(ok)
    print(f"CHECK {'PASS' if ok else 'FAIL'} {name}: {detail}")


def read_kv(path):
    out = {}
    with open(path) as f:
        for line in f:
            if "=" in line and not line.startswith("#"):
                k, v = line.strip().split("=", 1)
                out[k] = v
    return out


def select_zpeak(ev):
    """Return (mask over events, mu_pair records with exactly 2 muons, lead/sub pass mask)."""
    good = (ev["Muon_pt"] > 20) & (np.abs(ev["Muon_eta"]) < 2.4) & ev["Muon_tightId"] & (ev["Muon_pfRelIso04_all"] < 0.15)
    mus = ak.zip({k.replace("Muon_", ""): ev[k] for k in MUON_FIELDS})[good]
    mus = mus[ak.argsort(mus.pt, axis=1, ascending=False)]
    two = ak.num(mus, axis=1) == 2
    mus2 = mus[two]
    lead, sub = mus2[:, 0], mus2[:, 1]
    ok_pair = (lead.pt > 26) & (sub.pt > 20) & (lead.charge + sub.charge == 0)
    full = np.zeros(len(ev), dtype=bool)
    full[np.asarray(two)] = np.asarray(ok_pair)
    # records for the events that pass (same order as the masked events)
    pass_lead = lead[ok_pair]
    pass_sub = sub[ok_pair]
    return full, pass_lead, pass_sub


def dimuon_mass(a, b):
    """Invariant mass in GeV from pt, eta, phi, mass (awkward records with those fields)."""
    px1, py1, pz1 = a.pt * np.cos(a.phi), a.pt * np.sin(a.phi), a.pt * np.sinh(a.eta)
    px2, py2, pz2 = b.pt * np.cos(b.phi), b.pt * np.sin(b.phi), b.pt * np.sinh(b.eta)
    e1 = np.sqrt(px1**2 + py1**2 + pz1**2 + a.mass**2)
    e2 = np.sqrt(px2**2 + py2**2 + pz2**2 + b.mass**2)
    m2 = (e1 + e2) ** 2 - ((px1 + px2) ** 2 + (py1 + py2) ** 2 + (pz1 + pz2) ** 2)
    return np.sqrt(np.maximum(ak.to_numpy(m2), 0.0))


def load(fn, is_mc):
    branches = MUON_FIELDS + (MC_BRANCHES if is_mc else [])
    with uproot.open(fn) as f:
        return f["Events"].arrays(branches, library="ak")


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

    # ---- physics selection ----
    d = load(a.data, is_mc=False)
    m = load(a.mc, is_mc=True)
    sel_d, lead_d, sub_d = select_zpeak(d)
    sel_m, lead_m, sub_m = select_zpeak(m)
    mll_d = dimuon_mass(lead_d, sub_d)
    mll_m = dimuon_mass(lead_m, sub_m)
    w_m = ak.to_numpy(m["genWeight"])[sel_m] * weight_factor
    neg_frac = float(np.mean(ak.to_numpy(m["genWeight"]) < 0))

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
    # relative errors added in quadrature: sigma_r = r * sqrt(ed/vd^2 + em/vm^2)
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

    # ---- checks ----
    n_out_d = sum(int(r["EVENTS_OUT"]) for r in data_logs)
    n_out_m = sum(int(r["EVENTS_OUT"]) for r in mc_logs)
    merged_d = int(uproot.open(a.data)["Events"].num_entries)
    merged_m = int(uproot.open(a.mc)["Events"].num_entries)
    check("data events_out equals merged entries", n_out_d == merged_d, f"{n_out_d} vs {merged_d}")
    check("mc events_out equals merged entries", n_out_m == merged_m, f"{n_out_m} vs {merged_m}")
    rel = abs(sumw_orig - sumw_merged) / sumw_orig
    check("SUMW original == merged skim", rel < 1e-9, f"{sumw_orig:.10g} vs {sumw_merged:.10g} (rel {rel:.2e})")
    sumw_read = sum(float(r["SUMW_READ"]) for r in mc_logs)
    rel_read = abs(sumw_read - sumw_orig) / sumw_orig
    check("SUMW_READ over full files == Runs SUMW", rel_read < 1e-4, f"{sumw_read:.8g} vs {sumw_orig:.8g} (rel {rel_read:.2e})")
    check("lumi: no missing lumi sections", int(lumi["N_LS_MISSING"]) == 0, f"N_LS_MISSING={lumi['N_LS_MISSING']}")
    check("efficiency-like fraction in [0,1]", 0.0 <= neg_frac <= 1.0 and 0.0 <= data_events / max(len(mll_d), 1) <= 1.0,
          f"neg_frac={neg_frac:.4f}")
    check("Z window populated in data", data_events > 1000, f"{data_events} events in 81-101 GeV")
    check("data/MC in window in plausible range", 0.5 < data_over_mc < 2.0, f"{data_over_mc:.4f}")

    # ---- summary.json (exact keys from PROMPT.md) ----
    def total(logs, key):
        return sum(int(r[key]) for r in logs)

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
