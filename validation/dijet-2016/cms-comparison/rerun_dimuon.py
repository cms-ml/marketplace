#!/usr/bin/env python3
"""Re-run the student's dimuon selection on the same 2 Open Data files, with extra CMS-matched selections, into the cache.

The student's files are only read: the module dimuon_analysis.py is imported from --dimuon-dir (for the golden-JSON mask, trigger OR,
muon selection and branch list) and its histograms.pkl is used for a closure check.  Outputs go to <cache>/dimuon_rerun.pkl.

Selections (all start from the student's: golden JSON, trigger OR, loose ID, pT>3, |eta|<2.4, leading OS pair = two highest-pT selected muons):
  student      : unchanged (closure check against histograms.pkl)
  smp001       : leading muon pT>22, subleading pT>10 (CMS-SMP-17-001 fiducial region, JHEP 12 (2019) 059)
  smp001_id    : smp001 + both muons tightId + pfRelIso04_all<0.15 (generic POG tight isolation; my choice, not read from the paper)
  win15        : |m - 91.1876| < 15 GeV, student muon kinematics
  smp010       : both muons pT>25 and |eta|<2.4, |m - 91.1876| < 15 GeV (CMS-SMP-17-010 fiducial region, JHEP 12 (2019) 061)
  smp010_id    : smp010 + tightId + pfRelIso04_all<0.15
  ups_student  : Upsilon region, |y(mumu)|<1.2, student muons
  ups_bph      : + CMS-BPH-15-005 offline muon kinematics: pT>4.5 (|eta|<0.3) or pT>4.0 (0.3<|eta|<1.4)
Usage: rerun_dimuon.py --dimuon-dir <dir with dimuon_analysis.py and histograms.pkl> --cache <cache> [--max-events N]
"""
import sys
sys.dont_write_bytecode = True
import argparse
import importlib.util
import pickle
import sys
import time
from pathlib import Path

import awkward as ak
import numpy as np
import uproot
import vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import log   # noqa

vector.register_awkward()
MZ = 91.1876
PT_EDGES = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 16, 18, 20, 22, 25, 28, 32, 37, 43, 52, 65, 85, 120], float)   # SMP-17-010 Z pT bins
Y_EDGES = np.round(np.arange(0, 2.41, 0.2), 6)                                  # SMP-17-010 |y| bins
ZM_EDGES = np.arange(60, 121, 1.0)                                              # student's Z histogram binning
UPT_EDGES = np.array([0, 5, 10, 15, 20, 22, 24, 26, 28, 30, 32, 34, 36, 38, 40, 43, 46, 50, 55, 60, 70, 100, 130, 200], float)   # BPH-15-005 + lower
UM_EDGES = np.linspace(8.5, 11.5, 121)                                          # student's Upsilon binning (25 MeV)


def load_student(dimuon_dir):
    spec = importlib.util.spec_from_file_location("dimuon_analysis_student", Path(dimuon_dir) / "dimuon_analysis.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dimuon-dir", required=True)
    ap.add_argument("--cache", required=True)
    ap.add_argument("--max-events", type=int, default=None)
    ap.add_argument("--step-size", type=int, default=500_000)
    a = ap.parse_args()
    S = load_student(a.dimuon_dir)
    golden = S.load_golden(Path(a.cache) / "opendata" / "golden.json") if False else S.load_golden(S.GOLDEN)
    h_student = S.book()                                    # student's own histograms, rebuilt for the closure check
    br = S.BRANCHES + ["Muon_tightId", "Muon_pfRelIso04_all"]
    H = {}

    def add(name, arrs, edges):
        H.setdefault(name, np.zeros(tuple(len(e) - 1 for e in edges)))
        H[name] += np.histogramdd(arrs, bins=edges)[0] if len(arrs) > 1 else np.histogram(arrs[0], bins=edges[0])[0]

    counts = {}
    t0 = time.time()
    for f in S.DEFAULT_FILES:
        log("reading", f.split("/")[-1])
        tree = uproot.open(f)["Events"]
        for a_ in tree.iterate(br, step_size=a.step_size, entry_stop=a.max_events):
            # -------- the student's own processing, for the closure check
            S.process_chunk(a_[S.BRANCHES] if False else a_, h_student, golden)
            # -------- replicate the pre-selection to get the leading pair and extra quantities
            run = ak.to_numpy(a_.run); lumi = ak.to_numpy(a_.luminosityBlock)
            x = a_[S.lumi_mask(run, lumi, golden)]
            trig = np.zeros(len(x), bool)
            for p in S.TRIGGERS:
                trig |= ak.to_numpy(x[p])
            x = x[trig]
            mu = ak.zip({"pt": x.Muon_pt, "eta": x.Muon_eta, "phi": x.Muon_phi, "mass": x.Muon_mass, "charge": x.Muon_charge,
                         "tight": x.Muon_tightId, "iso": x.Muon_pfRelIso04_all}, with_name="Momentum4D")
            mu = mu[x.Muon_looseId & (mu.pt > 3) & (abs(mu.eta) < 2.4)]
            two = ak.num(mu, axis=1) >= 2
            mu = mu[two]
            m1, m2 = mu[:, 0], mu[:, 1]
            os_ = ak.to_numpy(m1.charge != m2.charge)
            d = m1 + m2
            mass, pt, y = ak.to_numpy(d.mass)[os_], ak.to_numpy(d.pt)[os_], ak.to_numpy(d.rapidity)[os_]
            q = lambda m, k: ak.to_numpy(m[k])[os_]
            p1, p2, e1, e2 = q(m1, "pt"), q(m2, "pt"), q(m1, "eta"), q(m2, "eta")
            id12 = q(m1, "tight").astype(bool) & q(m2, "tight").astype(bool) & (q(m1, "iso") < 0.15) & (q(m2, "iso") < 0.15)
            ay = np.abs(y)
            # --- Z mass shape (SMP-17-001)
            v = {"student": np.ones(len(mass), bool), "smp001": (p1 > 22) & (p2 > 10)}
            v["smp001_id"] = v["smp001"] & id12
            for k, m in v.items():
                add(f"zmass_{k}", [mass[m]], [ZM_EDGES])
            # --- Z pT, |y| (SMP-17-010)
            win = np.abs(mass - MZ) < 15
            kin25 = (p1 > 25) & (p2 > 25)
            vz = {"win15": win, "smp010": win & kin25, "smp010_id": win & kin25 & id12}
            for k, m in vz.items():
                add(f"zpt_{k}", [pt[m]], [PT_EDGES])
                add(f"zy_{k}", [ay[m]], [Y_EDGES])
            # student's own window 81-101 with CMS-matched binning (no extra cuts), to separate binning from selection
            ws = (mass > 81) & (mass < 101)
            add("zpt_stud81_101", [pt[ws]], [PT_EDGES]); add("zy_stud81_101", [ay[ws]], [Y_EDGES])
            # --- Upsilon (BPH-15-005)
            yb = ay < 1.2
            def bph_ok(p, e):
                ae = np.abs(e)
                return ((ae < 0.3) & (p > 4.5)) | ((ae >= 0.3) & (ae < 1.4) & (p > 4.0))
            vu = {"ups_student": yb, "ups_bph": yb & bph_ok(p1, e1) & bph_ok(p2, e2)}
            for k, m in vu.items():
                add(k, [pt[m], mass[m]], [UPT_EDGES, UM_EDGES])
            counts["os_events"] = counts.get("os_events", 0) + int(len(mass))
        log(f"  done {f.split('/')[-1]} ({time.time()-t0:.0f} s), OS events so far {counts['os_events']}")
    # ----- closure: the student's histograms rebuilt in this run vs the delivered pickle
    ref = pickle.load(open(Path(a.dimuon_dir) / "histograms.pkl", "rb"))
    clo = {}
    for k in ("m_full", "m_jpsi", "m_ups", "m_z", "win_pt", "win_y"):
        clo[k] = float(np.max(np.abs(h_student[k].values() - ref[k].values())))
    # and: my 'student' mass histogram vs the student's m_z (same 60-120 GeV, 1 GeV bins)
    clo["zmass_student_vs_m_z"] = float(np.max(np.abs(H["zmass_student"] - ref["m_z"].values())))
    full = (ref["m_z"].values().sum(), H["zmass_student"].sum())
    log("closure (max |rebuilt - delivered| per histogram):", clo, "sums", full)
    ok_clo = all(v == 0 for v in clo.values())
    log("CLOSURE", "EXACT" if ok_clo else "NOT exact (see values)")
    out = {"hist": H, "edges": {"pt": PT_EDGES, "y": Y_EDGES, "zm": ZM_EDGES, "upt": UPT_EDGES, "um": UM_EDGES}, "closure": clo,
           "cutflow_rebuilt": {k: v.tolist() for k, v in h_student["cutflow"].items()}, "n_files": len(S.DEFAULT_FILES)}
    pickle.dump(out, open(Path(a.cache) / "dimuon_rerun.pkl", "wb"))
    log("wrote", Path(a.cache) / "dimuon_rerun.pkl")


if __name__ == "__main__":
    main()
