"""Feature module for nano_to_table.py: dijet resonance vs QCD on NanoAOD.

Contract (copy this file and edit it for another analysis):
  BRANCHES   list of NanoAOD branches to read (plus event, genWeight, added by the caller)
  build(ev)  takes the awkward record array of one chunk and returns a dict of flat numpy
             arrays, one entry per SELECTED event, plus "_mask": bool array over ALL events
             of the chunk saying which were selected.
Column naming: "obs_*" columns are observers (mass, pT: kept for the sculpting and closure
checks, never trained on). Every other column is a training feature. Never add generator-level
or label-derived quantities as features. Kinematics in GeV.
"""
import awkward as ak
import numpy as np
import vector

BRANCHES = ["Jet_pt", "Jet_eta", "Jet_phi", "Jet_mass", "Jet_jetId", "Jet_btagDeepFlavB"]


def build(ev):
    jets = ak.zip({"pt": ev.Jet_pt, "eta": ev.Jet_eta, "phi": ev.Jet_phi, "mass": ev.Jet_mass,
                   "btag": ev.Jet_btagDeepFlavB}, with_name="Momentum4D", behavior=vector.backends.awkward.behavior)
    jets = jets[(ev.Jet_pt > 30) & (abs(ev.Jet_eta) < 2.5) & (ev.Jet_jetId >= 2)]
    mask = ak.to_numpy(ak.num(jets) >= 2)
    jets = jets[mask]
    j1, j2 = jets[:, 0], jets[:, 1]
    mjj = (j1 + j2).mass
    f = lambda x: ak.to_numpy(x).astype(np.float32)  # noqa: E731
    return {
        "_mask": mask,
        "j1_pt_over_mjj": f(j1.pt / mjj),
        "j2_pt_over_mjj": f(j2.pt / mjj),
        "abs_deta_jj": f(abs(j1.eta - j2.eta)),
        "abs_dphi_jj": f(abs(j1.deltaphi(j2))),
        "j1_eta": f(j1.eta),
        "j2_eta": f(j2.eta),
        "j1_btag": f(j1.btag),
        "j2_btag": f(j2.btag),
        "j1_mass_over_pt": f(j1.mass / j1.pt),
        "j2_mass_over_pt": f(j2.mass / j2.pt),
        "n_jets": f(ak.num(jets)),
        "obs_mjj": f(mjj),
        "obs_j1_pt": f(j1.pt),
        "obs_ht": f(ak.sum(jets.pt, axis=1)),
    }
