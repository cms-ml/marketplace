#!/usr/bin/env python3
"""Worked Awkward Array example on CMS NanoAOD: Z -> mu mu.

Reads a few branches with uproot, builds muon/jet records, selects objects and
events, forms opposite-sign dimuon pairs, cleans jets against muons, follows the
Jet_muonIdx1 index branch safely, and sums weights. Prints a short summary.

Usage:
  python3 nanoaod_dimuon.py [--url URL] [--entries N]

Environments (both tested):
  CMSSW (awkward 2.6.3, uproot 5.3.3): cmsenv; export PYTHONNOUSERSITE=1
  pip   (awkward 2.8.12, uproot 5.6.9): pip install awkward uproot vector fsspec-xrootd xrootd
Default input is public CMS Open Data (no grid proxy needed). Units: GeV.
"""

import argparse

import awkward as ak
import numpy as np
import uproot

DEFAULT_URL = (
    "root://eospublic.cern.ch//eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/"
    "DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8/NANOAODSIM/"
    "106X_mcRun2_asymptotic_v17-v1/30000/0082C29D-E74C-024A-BE9B-97B29EE7A4A2.root"
)


def open_root(url):
    """Open root:// URLs with whatever XRootD backend the environment has."""
    try:
        import fsspec_xrootd  # noqa: F401  pip envs: pip install fsspec-xrootd xrootd
        return uproot.open(url)
    except ImportError:
        # CMSSW ships the XRootD Python bindings but not fsspec-xrootd
        return uproot.open(url, handler=uproot.source.xrootd.XRootDSource)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--url", default=DEFAULT_URL)
    ap.add_argument("--entries", type=int, default=20000)
    args = ap.parse_args()

    events = open_root(args.url)["Events"]
    arr = events.arrays(
        ["Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass", "Muon_charge", "Muon_tightId",
         "Muon_pfRelIso04_all", "Jet_pt", "Jet_eta", "Jet_phi", "Jet_muonIdx1", "genWeight"],
        entry_stop=args.entries,
    )

    # 1. Build records: flat NanoAOD branches -> one jagged record per collection.
    muons = ak.zip({
        "pt": arr.Muon_pt, "eta": arr.Muon_eta, "phi": arr.Muon_phi, "mass": arr.Muon_mass,
        "charge": arr.Muon_charge, "tightId": arr.Muon_tightId, "iso": arr.Muon_pfRelIso04_all,
    })
    jets = ak.zip({"pt": arr.Jet_pt, "eta": arr.Jet_eta, "phi": arr.Jet_phi, "muonIdx1": arr.Jet_muonIdx1})

    # 2. Object selection (mask has the same jagged structure as muons).
    good = muons[(muons.pt > 20) & (abs(muons.eta) < 2.4) & muons.tightId & (muons.iso < 0.15)]

    # 3. Event selection, early: >= 2 good muons. Apply the SAME mask to everything per-event.
    two_mu = ak.num(good, axis=1) >= 2
    good, jets_sel, weights = good[two_mu], jets[two_mu], arr.genWeight[two_mu]

    # 4. Combinatorics: all muon pairs per event, keep opposite sign.
    pairs = ak.combinations(good, 2, fields=["m1", "m2"])
    pairs = pairs[pairs.m1.charge != pairs.m2.charge]
    m1, m2 = pairs.m1, pairs.m2
    mll = np.sqrt(2 * m1.pt * m2.pt * (np.cosh(m1.eta - m2.eta) - np.cos(m1.phi - m2.phi)))

    # 5. Leading object safely: ak.firsts gives None for empty lists ([:, 0] would raise).
    lead_pt = ak.firsts(good.pt)

    # 6. Jet-muon cleaning: nested cartesian -> per jet, all muons; keep jets far from every muon.
    jm = ak.cartesian([jets_sel, good], axis=1, nested=True)
    j, m = ak.unzip(jm)
    dphi = (j.phi - m.phi + np.pi) % (2 * np.pi) - np.pi
    dr = np.sqrt((j.eta - m.eta) ** 2 + dphi**2)
    clean_jets = jets_sel[ak.all(dr > 0.4, axis=-1)]

    # 7. Index branches: -1 means "no match". Mask it to None BEFORE indexing,
    #    otherwise -1 silently selects the LAST muon. (Indexes the full Muon collection.)
    idx = ak.mask(jets.muonIdx1, jets.muonIdx1 >= 0)
    matched_mu_pt = muons.pt[idx]

    # 8. Reduce to NumPy for histogramming; sum float32 weights in float64.
    mll_flat = ak.to_numpy(ak.flatten(mll, axis=1))
    sumw = float(ak.sum(ak.values_astype(weights, np.float64)))

    print(f"events read: {len(arr)}  with >=2 good muons: {int(ak.sum(two_mu))}")
    print(f"OS dimuon pairs: {len(mll_flat)}  median m_mumu: {np.median(mll_flat):.2f} GeV")
    print(f"leading good-muon pt, first 3 selected events: {lead_pt[:3].tolist()}")
    print(f"jets before/after muon cleaning: {int(ak.sum(ak.num(jets_sel)))} / {int(ak.sum(ak.num(clean_jets)))}")
    n_matched = int(ak.sum(~ak.is_none(matched_mu_pt, axis=1)))
    print(f"jets with a matched muon (via Jet_muonIdx1): {n_matched}")
    print(f"sum of genWeight (float64) in selected events: {sumw:.6g}")

    try:
        import vector

        vector.register_awkward()
        mu4 = ak.zip({"pt": good.pt, "eta": good.eta, "phi": good.phi, "mass": good.mass,
                      "charge": good.charge}, with_name="Momentum4D")
        p = ak.combinations(mu4, 2, fields=["m1", "m2"])
        p = p[p.m1.charge != p.m2.charge]
        print(f"vector: median m_mumu {np.median(ak.to_numpy(ak.flatten((p.m1 + p.m2).mass, axis=1))):.2f} GeV")
    except ImportError:
        print("vector not installed; skipped Momentum4D example")


if __name__ == "__main__":
    main()
