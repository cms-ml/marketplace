"""Feature module for nano_to_table.py (hep-ml-data-prep): one row per selected AK4 jet.

nano_to_table.py expects build(ev)["_mask"] to select events; it applies it with numpy indexing
(event, genWeight). Here "_mask" is an INTEGER array of event indices, one entry per selected jet
(np.repeat), so the event number and generator weight are copied to every jet of the event and
fold = event % n keeps all jets of one event in the same fold.

The truth columns obs_parton_flavour and obs_genjet_matched are needed by make_jet_table.py to
define the label; make_jet_table.py removes them from the training tables. Kinematics in GeV.
"""
import awkward as ak
import numpy as np

BRANCHES = ["Jet_pt", "Jet_eta", "Jet_mass", "Jet_jetId", "Jet_genJetIdx", "Jet_partonFlavour",
            "Jet_nConstituents", "Jet_chHEF", "Jet_neHEF", "Jet_chEmEF", "Jet_neEmEF", "Jet_muEF",
            "Jet_chFPV0EF", "Jet_area", "Jet_nMuons", "Jet_nElectrons", "Jet_qgl", "Jet_btagDeepFlavQG",
            "fixedGridRhoFastjetAll"]


def build(ev):
    sel = (ev.Jet_pt >= 30) & (ev.Jet_pt < 1000) & (abs(ev.Jet_eta) < 2.5) & ((ev.Jet_jetId & 2) != 0)
    njet = ak.to_numpy(ak.sum(sel, axis=1))
    idx = np.repeat(np.arange(len(ev)), njet)
    f = lambda x: ak.to_numpy(ak.flatten(x[sel])).astype(np.float32)  # noqa: E731
    rank = ak.local_index(ev.Jet_pt)
    pt = f(ev.Jet_pt)
    return {
        "_mask": idx,
        "n_constituents": f(ev.Jet_nConstituents),
        "ch_had_ef": f(ev.Jet_chHEF),
        "ne_had_ef": f(ev.Jet_neHEF),
        "ch_em_ef": f(ev.Jet_chEmEF),
        "ne_em_ef": f(ev.Jet_neEmEF),
        "mu_ef": f(ev.Jet_muEF),
        "ch_pv0_ef": f(ev.Jet_chFPV0EF),
        "area": f(ev.Jet_area),
        "mass_over_pt": f(ev.Jet_mass) / pt,
        "n_muons": f(ev.Jet_nMuons),
        "n_electrons": f(ev.Jet_nElectrons),
        "rho": np.repeat(ak.to_numpy(ev.fixedGridRhoFastjetAll), njet).astype(np.float32),
        "obs_pt": pt,
        "obs_eta": f(ev.Jet_eta),
        "obs_abseta": np.abs(f(ev.Jet_eta)),
        "obs_qgl": f(ev.Jet_qgl),
        "obs_deepjet_qg": f(ev.Jet_btagDeepFlavQG),
        "obs_jet_idx": f(rank),
        "obs_parton_flavour": f(ev.Jet_partonFlavour),
        "obs_genjet_matched": f(ev.Jet_genJetIdx >= 0),
    }
