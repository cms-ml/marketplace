#!/usr/bin/env python3
"""Exploratory checks on the IsoMu24 trigger measurement (not part of the main chain), on a few files, read over XRootD.

Part 1 (event level, the skill's check): among events that fired neither HLT_IsoMu24 nor HLT_IsoTkMu24, the fraction that
still have a muon TrigObj with bit 2 or 8 and pT >= 24 GeV; and among events with such an object, the fraction that fired neither path.
Part 2: sensitivity of the raw data and MC trigger efficiency (tight+iso probes, 80 < m < 100 GeV, 40 < pT < 50 GeV, event fired)
to the trigger-object matching cone dR and to the object pT threshold. Raw (no background subtraction: the background is
below about 0.5 percent in this window) so it only shows how the numbers move. NOTE: probes are 40-50 GeV only, where the HLT object pT is close to the offline pT, so the
threshold scan is vacuous here; the threshold scan in the 26-30 and 30-40 GeV bins and the bit-2-only / bit-8-only pass variants are in
analysis.py (summary.json filter_bits.object_pt_threshold_scan and filter_bits.measurement).

Usage: explore_trigger.py --data <root files> --mc <root files> [--max-events N] -o explore_trigger.json
"""
import argparse, json, os, sys
import awkward as ak
import numpy as np
import uproot
import vector
vector.register_awkward()
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "plugins", "cms", "skills", "muon-tag-and-probe", "scripts"))
sys.path.insert(0, os.path.join(HERE, "condor"))
import skim  # noqa: E402
import tnp   # noqa: E402

BR = (["run", "luminosityBlock", "nMuon", "HLT_IsoMu24", "HLT_IsoTkMu24"] + [f"Muon_{x}" for x in skim.MU]
      + [f"TrigObj_{x}" for x in skim.TO])
DRS = (0.05, 0.1, 0.2, 0.3, 0.5)
THR = (24, 26, 27)


def run(files, is_mc, max_events):
    ev1 = dict(n=0, n_fired=0, n_neither=0, n_neither_with_obj=0, n_obj=0, n_obj_neither=0)
    cnt = {}  # (dr, thr, region) -> [n_pass_w, n_total_w]
    for f in files:
        t = uproot.open(f)["Events"]
        br = BR + (["Muon_genPartFlav", "genWeight"] if is_mc else [])
        for ev in t.iterate(br, step_size="100 MB", entry_stop=max_events or None, library="ak"):
            fired = ev.HLT_IsoMu24 | ev.HLT_IsoTkMu24
            to = ak.zip({"pt": ev.TrigObj_pt, "id": ev.TrigObj_id, "b": ev.TrigObj_filterBits})
            has = ak.any((to.id == 13) & ((to.b & 10) != 0) & (to.pt >= 24), axis=1)
            fired, has = ak.to_numpy(fired), ak.to_numpy(has)
            ev1["n"] += len(ev); ev1["n_fired"] += int(fired.sum()); ev1["n_neither"] += int((~fired).sum())
            ev1["n_neither_with_obj"] += int((~fired & has).sum()); ev1["n_obj"] += int(has.sum()); ev1["n_obj_neither"] += int((~fired & has).sum())
            ev = ev[(ev.nMuon >= 2) & fired]
            mu = ak.zip({"pt": ev.Muon_pt, "eta": ev.Muon_eta, "phi": ev.Muon_phi, "mass": ak.full_like(ev.Muon_pt, tnp.MU_MASS),
                         "charge": ev.Muon_charge, "tight": ev.Muon_tightId, "iso": ev.Muon_pfRelIso04_all}, with_name="Momentum4D")
            keep = (abs(mu.eta) < 2.4) & (mu.pt > 15) & mu.tight & (mu.iso < 0.15)
            mu = mu[keep]
            tagm = skim.match_pt(mu, ev, 10, 0.1)
            is_tag = (mu.pt > 29) & (tagm >= 24)
            pr = ak.argcartesian([mu, mu], axis=1)
            t, p = mu[pr["0"]], mu[pr["1"]]
            m = (t + p).mass
            good = (pr["0"] != pr["1"]) & is_tag[pr["0"]] & (t.charge * p.charge < 0) & (m > 80) & (m < 100) & (p.pt > 40) & (p.pt < 50)
            w = ak.broadcast_arrays(np.sign(ak.to_numpy(ev.genWeight)) if is_mc else np.ones(len(ev)), m)[0]
            sel = lambda x: ak.to_numpy(ak.flatten(x[good]))
            ae, ww = np.abs(sel(p.eta)), sel(w)
            gen = sel(ak.broadcast_arrays(ev.Muon_genPartFlav[keep] == 1, ev.Muon_genPartFlav[keep])[0][pr["1"]]) if is_mc else np.ones(len(ww), bool)
            for dr in DRS:
                mp = skim.match_pt(mu, ev, 10, dr)
                mpp = sel(mp[pr["1"]])
                for thr in THR:
                    for reg, rm in (("0-0.9", ae < 0.9), ("1.2-2.1", (ae >= 1.2) & (ae < 2.1))):
                        s = rm & gen
                        c = cnt.setdefault(f"dr{dr}_thr{thr}_eta{reg}", [0.0, 0.0])
                        c[0] += float(ww[s & (mpp >= thr)].sum()); c[1] += float(ww[s].sum())
    return ev1, {k: dict(eff=v[0] / v[1], n=v[1]) for k, v in cnt.items()}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", nargs="+", required=True); ap.add_argument("--mc", nargs="+", required=True)
    ap.add_argument("--max-events", type=int, default=0); ap.add_argument("-o", default="explore_trigger.json")
    a = ap.parse_args()
    e1d, cd = run(a.data, False, a.max_events)
    e1m, cm = run(a.mc, True, a.max_events)
    out = dict(event_level_data=e1d, event_level_mc=e1m, scan={})
    for k in cd:
        out["scan"][k] = dict(eff_data=cd[k]["eff"], eff_mc=cm[k]["eff"], sf_raw=cd[k]["eff"] / cm[k]["eff"], n_data=cd[k]["n"], n_mc=cm[k]["n"])
        print(k, f"data {cd[k]['eff']:.4f} mc {cm[k]['eff']:.4f} SF {cd[k]['eff']/cm[k]['eff']:.4f}")
    for n, e in (("data", e1d), ("mc", e1m)):
        print(n, "neither-path events with an Iso/IsoTk object >= 24 GeV:", e["n_neither_with_obj"] / e["n_neither"],
              "; events with such an object that fired neither:", e["n_obj_neither"] / e["n_obj"])
    json.dump(out, open(a.o, "w"), indent=1)


if __name__ == "__main__":
    main()
