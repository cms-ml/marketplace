#!/usr/bin/env python3
"""Skim NanoAOD (2016 JetHT or MC) to flat per-event dijet arrays.

Contract of the lpc-condor job.sh wrapper:
    skim.py --inputs <comma-separated root:// URLs> --output output_<id>.npz

Selection (see specification.md): event-cleaning flags, two leading jets with
pt > 30 GeV and tight ID (Jet_jetId & 2), both |eta| < 2.4, m_jj > MJJ_MIN GeV.
Runs with the LCG_109 view (uproot, awkward, vector, numpy). Units: GeV.
"""
import argparse, json, sys, time
import numpy as np
import awkward as ak
import uproot
import vector

vector.register_awkward()

MJJ_MIN = 800.0
FLAGS = ["Flag_goodVertices", "Flag_globalSuperTightHalo2016Filter", "Flag_HBHENoiseFilter",
         "Flag_HBHENoiseIsoFilter", "Flag_EcalDeadCellTriggerPrimitiveFilter",
         "Flag_BadPFMuonFilter", "Flag_BadPFMuonDzFilter", "Flag_eeBadScFilter"]
# signal-trigger paths (OR) and reference paths; order defines the bit in `trig`
SIG_TRIGS = ["HLT_PFHT900", "HLT_PFHT800", "HLT_PFJet450", "HLT_PFJet500",
             "HLT_CaloJet500_NoJetID", "HLT_AK8PFJet450", "HLT_AK8PFJet500"]
REF_TRIGS = ["HLT_PFJet260", "HLT_PFHT475", "HLT_PFJet400"]
TRIGS = SIG_TRIGS + REF_TRIGS


def process_file(url, step):
    f = uproot.open(url)
    T = f["Events"]
    keys = set(T.keys())
    is_mc = "genWeight" in keys
    out = {k: [] for k in ["run", "lumi", "pt1", "eta1", "phi1", "m1", "pt2", "eta2", "phi2", "m2",
                           "mjj", "btag1", "btag2", "trig", "flav1", "flav2", "genw"]}
    missing = [t for t in TRIGS if t not in keys]
    flags = [x for x in FLAGS if x in keys]
    br = ["run", "luminosityBlock", "Jet_pt", "Jet_eta", "Jet_phi", "Jet_mass", "Jet_jetId",
          "Jet_btagDeepFlavB"] + [t for t in TRIGS if t in keys] + flags
    if is_mc:
        br += ["genWeight", "Jet_hadronFlavour"]
    info = {"url": url, "is_mc": is_mc, "n_total": int(T.num_entries), "n_sel": 0,
            "missing_trig": missing, "flags_used": flags}
    info["sumw"] = float(np.sum(f["Runs"]["genEventSumw"].array(library="np"), dtype=np.float64)) if is_mc else 0.0
    lskeys = []
    for a in T.iterate(br, step_size=step, library="ak"):
        lskeys.append(np.unique(ak.to_numpy(a["run"]).astype(np.int64) * 100000 + ak.to_numpy(a["luminosityBlock"]).astype(np.int64)))
        ok = np.ones(len(a), dtype=bool)
        for fl in flags:
            ok &= ak.to_numpy(a[fl]).astype(bool)
        good = (a["Jet_pt"] > 30) & ((a["Jet_jetId"] & 2) > 0)
        sel = ok & (ak.num(a["Jet_pt"][good]) >= 2)
        a, good = a[sel], good[sel]
        idx = ak.local_index(a["Jet_pt"])[good][:, :2]          # two leading good jets (pt-ordered)
        def g(name):
            return ak.to_numpy(a[name][idx])
        pt, eta, phi, m, b = g("Jet_pt"), g("Jet_eta"), g("Jet_phi"), g("Jet_mass"), g("Jet_btagDeepFlavB")
        j1 = vector.arr({"pt": pt[:, 0], "eta": eta[:, 0], "phi": phi[:, 0], "mass": m[:, 0]})
        j2 = vector.arr({"pt": pt[:, 1], "eta": eta[:, 1], "phi": phi[:, 1], "mass": m[:, 1]})
        mjj = (j1 + j2).mass
        keep = (np.abs(eta[:, 0]) < 2.4) & (np.abs(eta[:, 1]) < 2.4) & (mjj > MJJ_MIN)
        n = int(keep.sum())
        info["n_sel"] += n
        if n == 0:
            continue
        trig = np.zeros(len(a), dtype=np.uint32)
        for i, t in enumerate(TRIGS):
            if t in keys:
                trig |= (ak.to_numpy(a[t]).astype(np.uint32) << i)
        out["run"].append(ak.to_numpy(a["run"])[keep]); out["lumi"].append(ak.to_numpy(a["luminosityBlock"])[keep])
        for nm, arr in [("pt", pt), ("eta", eta), ("phi", phi), ("m", m)]:
            out[nm + "1"].append(arr[keep, 0].astype(np.float32)); out[nm + "2"].append(arr[keep, 1].astype(np.float32))
        out["mjj"].append(np.asarray(mjj)[keep].astype(np.float32))
        out["btag1"].append(b[keep, 0].astype(np.float32)); out["btag2"].append(b[keep, 1].astype(np.float32))
        out["trig"].append(trig[keep])
        if is_mc:
            fl = g("Jet_hadronFlavour")
            out["flav1"].append(fl[keep, 0].astype(np.int8)); out["flav2"].append(fl[keep, 1].astype(np.int8))
            out["genw"].append(ak.to_numpy(a["genWeight"])[keep].astype(np.float32))
    ls = np.unique(np.concatenate(lskeys)) if lskeys else np.zeros(0, np.int64)
    return out, info, ls


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inputs", required=True, help="comma-separated root:// URLs")
    ap.add_argument("--output", required=True, help="output .npz file")
    ap.add_argument("--step", type=int, default=250000, help="events per chunk")
    args = ap.parse_args()
    urls = [u for u in args.inputs.split(",") if u]
    cols = {}
    infos, lsall = [], []
    fidx = []
    for i, u in enumerate(urls):
        t0 = time.time()
        out, info, ls = process_file(u, args.step)
        n = info["n_sel"]
        for k, v in out.items():
            if v:
                cols.setdefault(k, []).append(np.concatenate(v))
        fidx.append(np.full(n, i, dtype=np.int16))
        infos.append(info); lsall.append(ls)
        print(f"[{i+1}/{len(urls)}] {u.split('/')[-1]} total={info['n_total']} selected={n} {time.time()-t0:.0f}s", file=sys.stderr, flush=True)
    res = {k: np.concatenate(v) for k, v in cols.items()}
    res["file_idx"] = np.concatenate(fidx)
    res["ls_keys"] = np.unique(np.concatenate(lsall)) if lsall else np.zeros(0, np.int64)
    res["info"] = np.array(json.dumps({"trigs": TRIGS, "n_sig_trigs": len(SIG_TRIGS), "mjj_min": MJJ_MIN, "files": infos}))
    np.savez_compressed(args.output, **res)
    print(f"wrote {args.output}: {len(res['file_idx'])} events", file=sys.stderr)


if __name__ == "__main__":
    main()
