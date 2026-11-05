#!/usr/bin/env python3
"""Condor payload: Z -> mu mu tag-and-probe pair skim of Open Data NanoAOD (one npz per job).

Contract of the lpc-condor job.sh: skim.py --inputs <comma-separated root:// URLs> --output <file.npz>.
Writes one flat row per (tag, probe) ordered pair (each muon is tag once) that is WP-agnostic:
the probe is any tracker muon (the loosest POG denominator); tight ID, IP, isolation and the
trigger-object match of the probe are stored as columns, so that the three working points,
the systematics and the filter-bit study are all done later without touching the NanoAOD again.

Tag: tight ID, PF iso < 0.15, pT > 29 GeV, |eta| < 2.4, matched (dR < 0.1) to a muon TrigObj with
filter bit 2 (Iso) or 8 (IsoTkMu) and pT >= 24 GeV (the skill's definition, tnp.py).
Pair: opposite charge, 70 < m < 115 GeV. No golden-JSON or HLT requirement here (applied later).
Units GeV. Stdout: KEY=VALUE lines. Exit 0 ok, 2 bad input.
"""
import argparse
import json
import os
import sys

import awkward as ak
import numpy as np
import uproot
import vector

vector.register_awkward()
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tnp  # shipped next to this file (copy of the skill script: constants, _trigger_match)

HLT_NAMES = ["HLT_IsoMu24", "HLT_IsoTkMu24", "HLT_IsoMu22", "HLT_IsoMu22_eta2p1", "HLT_IsoTkMu22",
             "HLT_IsoTkMu22_eta2p1", "HLT_IsoMu27", "HLT_IsoTkMu27", "HLT_Mu50"]  # bit i of 'hlt'
MU = ["pt", "eta", "phi", "charge", "isTracker", "tightId", "pfRelIso04_all", "dxy", "dz"]
TO = ["id", "filterBits", "pt", "eta", "phi"]


def match_pt(mu, events, bits, dr_max=0.1):
    """Max pT [GeV] of the muon TrigObj with any of `bits` within dr_max of each muon (0 if none)."""
    to = ak.zip({"pt": events.TrigObj_pt, "eta": events.TrigObj_eta, "phi": events.TrigObj_phi,
                 "id": events.TrigObj_id, "bits": events.TrigObj_filterBits})
    to = to[(to.id == 13) & ((to.bits & bits) != 0)]
    pr = ak.cartesian({"m": mu, "t": to}, nested=True)
    deta = pr.m.eta - pr.t.eta
    dphi = (pr.m.phi - pr.t.phi + np.pi) % (2 * np.pi) - np.pi
    pt = ak.where(deta**2 + dphi**2 < dr_max**2, pr.t.pt, 0.0)
    return ak.fill_none(ak.max(pt, axis=-1, initial=0.0), 0.0)


def process(ev, is_mc, puw, selfcheck):
    mu = ak.zip({"pt": ev.Muon_pt, "eta": ev.Muon_eta, "phi": ev.Muon_phi,
                 "mass": ak.full_like(ev.Muon_pt, tnp.MU_MASS), "charge": ev.Muon_charge,
                 "isTracker": ev.Muon_isTracker, "tightId": ev.Muon_tightId,
                 "iso": ev.Muon_pfRelIso04_all, "dxy": ev.Muon_dxy, "dz": ev.Muon_dz,
                 "gen": (ev.Muon_genPartFlav == 1) if is_mc else ak.zeros_like(ev.Muon_charge) == 1},
                with_name="Momentum4D")
    keep = (abs(mu.eta) < 2.4) & (mu.pt > 15) & mu.isTracker
    mu = mu[keep]
    mu["m2pt"] = match_pt(mu, ev, tnp.BIT_ISO)
    mu["m8pt"] = match_pt(mu, ev, tnp.BIT_ISOTK)
    if selfcheck:  # agreement with the skill's boolean match on this chunk
        ref = tnp._trigger_match(mu, ev, tnp.BIT_ISO | tnp.BIT_ISOTK)
        mine = (mu.m2pt >= 24) | (mu.m8pt >= 24)
        assert ak.all(ref == mine), "own trigger match differs from tnp._trigger_match"
    is_tag = mu.tightId & (mu.iso < 0.15) & (mu.pt > 29) & ((mu.m2pt >= 24) | (mu.m8pt >= 24))
    pair = ak.argcartesian([mu, mu], axis=1)
    t, p = mu[pair["0"]], mu[pair["1"]]
    m = (t + p).mass
    good = (pair["0"] != pair["1"]) & is_tag[pair["0"]] & (t.charge * p.charge < 0) & (m > tnp.M_LO) & (m < tnp.M_HI)
    hlt = np.zeros(len(ev), dtype=np.int32)
    for i, n in enumerate(HLT_NAMES):
        if n in ev.fields:
            hlt |= (ak.to_numpy(ev[n]).astype(np.int32) << i)
    b = lambda x: ak.broadcast_arrays(x, m)[0]
    w = np.ones(len(ev), dtype=np.float32)
    if is_mc:
        w = (np.sign(ak.to_numpy(ev.genWeight)) * puw).astype(np.float32)
    cols = {"m": m, "tpt": t.pt, "teta": t.eta, "tiso": t.iso, "ppt": p.pt, "peta": p.eta, "piso": p.iso,
            "ptight": p.tightId, "pip": (abs(p.dxy) < 0.2) & (abs(p.dz) < 0.5), "m2pt": p.m2pt, "m8pt": p.m8pt,
            "hlt": b(hlt), "run": b(ev.run), "lumi": b(ev.luminosityBlock), "gen": p.gen, "w": b(w)}
    return {k: ak.to_numpy(ak.flatten(v[good])) for k, v in cols.items()}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--inputs", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--max-events", type=int, default=0, help="per file, for tests; 0 = all")
    ap.add_argument("--mc", action="store_true", help="force MC mode (default: guess from the URL)")
    ap.add_argument("--era", default="2016postVFP_UL")
    a = ap.parse_args(argv)
    files = [f for f in a.inputs.split(",") if f]
    is_mc = a.mc or "/mc/" in files[0]
    puw = None
    if is_mc:
        import correctionlib
        cs = correctionlib.CorrectionSet.from_file(f"{tnp.POG}/LUM/{a.era}/puWeights.json.gz")
        puw = list(cs.values())[0]
    br = (["run", "luminosityBlock", "nMuon"] + [f"Muon_{x}" for x in MU] + [f"TrigObj_{x}" for x in TO]
          + (["genWeight", "Pileup_nTrueInt", "Muon_genPartFlav"] if is_mc else []))
    out, ls, info = [], [], {"files": [], "is_mc": is_mc, "hlt_names": HLT_NAMES}
    first = True
    for f in files:
        try:
            tree = uproot.open(f)["Events"]
        except Exception as e:
            print(f"error: cannot open {f}: {e}", file=sys.stderr)
            return 2
        hl = [n for n in HLT_NAMES if n in tree.keys()]
        n_f, n_p, entry_stop = 0, 0, (a.max_events or None)
        for ev in tree.iterate(br + hl, step_size="100 MB", entry_stop=entry_stop, library="ak"):
            n_f += len(ev)
            ls.append(np.unique(ak.to_numpy(ev.run).astype(np.int64) * 100000 + ak.to_numpy(ev.luminosityBlock)))
            ev = ev[ev.nMuon >= 2]
            if len(ev) == 0:
                continue
            pw = None
            if is_mc:
                pw = puw.evaluate(np.clip(ak.to_numpy(ev.Pileup_nTrueInt), 0, 98.9), "nominal")
            o = process(ev, is_mc, pw, first)
            first = False
            n_p += len(o["m"])
            out.append(o)
        info["files"].append({"url": f, "n_events": n_f, "n_pairs": n_p})
        print(f"{f.split('/')[-1]} events={n_f} pairs={n_p}", file=sys.stderr)
    arr = {k: np.concatenate([o[k] for o in out]) for k in out[0]}
    for k in ("m", "tpt", "teta", "tiso", "ppt", "peta", "piso", "m2pt", "m8pt", "w"):
        arr[k] = arr[k].astype(np.float32)
    arr["ls"] = np.unique(np.concatenate(ls))
    arr["info"] = np.array(json.dumps(info))
    np.savez_compressed(a.output, **arr)
    print(f"N_EVENTS={sum(f['n_events'] for f in info['files'])}")
    print(f"N_PAIRS={len(arr['m'])}")
    print(f"OUT={a.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
