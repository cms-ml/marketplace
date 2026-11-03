#!/usr/bin/env python3
"""Muon tag-and-probe on Z -> mu mu in CMS NanoAOD (Run 2 UL), with a POG comparison.

Measures a muon efficiency (tight ID, tight PF isolation, or IsoMu24 trigger)
in data and DY MC in |eta| x pT bins, and the data/MC scale factor, and
compares it with the Muon POG correctionlib JSON (muon_Z.json.gz).

    tnp.py --data <files...> --mc <files...> --wp tightid --era 2016postVFP_UL \
           --max-events 2000000 --out tnp_tightid.json [--plots plots/]

Data efficiency: simultaneous binned fit of the pass and fail m_mumu spectra
(70-115 GeV) with the MC signal template of each category plus an exponential
background, common signal yield and efficiency (iminuit, HESSE errors).
MC efficiency: counting of generator-matched probes (genWeight sign, pileup
weight from the LUM POG JSON).

Stdout: one line per bin, then KEY=VALUE lines (N_BINS, MEAN_PULL, RMS_PULL,
OUT). Diagnostics on stderr. Exit 0 ok, 1 fit failures in some bins,
2 bad arguments or unreadable input.

Importable: tnp_pairs(), WPS, fit_pass_fail(), pog_sf().
"""
from __future__ import annotations

import argparse
import json
import math
import os
import sys

import awkward as ak
import numpy as np
import uproot
import vector

vector.register_awkward()

POG = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG"
MU_MASS = 0.1056583745  # GeV
M_LO, M_HI, M_BINS = 70.0, 115.0, 45  # GeV, as the POG Z tag and probe

# TrigObj_filterBits for muons (TrigObj_id == 13) in Run 2 NanoAODv9; read the
# branch title of your file (uproot: tree["TrigObj_filterBits"].title) to confirm.
BIT_ISO, BIT_ISOTK, BIT_MU50 = 2, 8, 1024

BRANCHES = [
    "Muon_pt", "Muon_eta", "Muon_phi", "Muon_charge", "Muon_isTracker", "Muon_isGlobal",
    "Muon_tightId", "Muon_pfRelIso04_all", "Muon_dxy", "Muon_dz",
    "TrigObj_id", "TrigObj_filterBits", "TrigObj_pt", "TrigObj_eta", "TrigObj_phi",
    "HLT_IsoMu24", "HLT_IsoTkMu24",
]
MC_BRANCHES = ["genWeight", "Pileup_nTrueInt", "Muon_genPartFlav"]


def _ip(mu):
    return (abs(mu.dxy) < 0.2) & (abs(mu.dz) < 0.5)


def _tight_iso(mu):
    return mu.pfRelIso04_all < 0.15


# Working point = (probe denominator, numerator, POG correction name).
# The denominators follow the POG names: NUM_<num>_DEN_<den>.
WPS = {
    "tightid": dict(
        den=lambda mu: mu.isTracker,
        num=lambda mu: mu.tightId,
        pog="NUM_TightID_DEN_TrackerMuons",
    ),
    "tightiso": dict(
        den=lambda mu: mu.tightId & _ip(mu),
        num=_tight_iso,
        pog="NUM_TightRelIso_DEN_TightIDandIPCut",
    ),
    "isomu24": dict(
        den=lambda mu: mu.tightId & _tight_iso(mu),
        num=lambda mu: mu.trig_matched,
        pog="NUM_IsoMu24_or_IsoTkMu24_DEN_CutBasedIdTight_and_PFIsoTight",
    ),
}


def _trigger_match(mu, events, bits, pt_min=24.0, dr_max=0.1):
    """True for each muon within dr_max of a TrigObj muon with any of `bits` and pT >= pt_min (GeV).

    A filter bit marks a filter type, not a path, so the bit alone does not fix the path
    or its threshold (see the skill's "Filter bits are not paths" gotcha).
    """
    to = ak.zip({"pt": events.TrigObj_pt, "eta": events.TrigObj_eta, "phi": events.TrigObj_phi,
                 "id": events.TrigObj_id, "bits": events.TrigObj_filterBits})
    to = to[(to.id == 13) & ((to.bits & bits) != 0) & (to.pt >= pt_min)]
    pairs = ak.cartesian({"m": mu, "t": to}, nested=True)
    deta = pairs.m.eta - pairs.t.eta
    dphi = (pairs.m.phi - pairs.t.phi + np.pi) % (2 * np.pi) - np.pi
    return ak.fill_none(ak.any(deta**2 + dphi**2 < dr_max**2, axis=-1), False)


def tnp_pairs(events, wp, is_mc, tag_pt=29.0):
    """Flat arrays (mass, probe pt, probe |eta|, passing, weight, genmatch) of tag-probe pairs.

    Every muon pair is used twice (each muon as tag once), so a probe that is also a
    good tag is not biased. Tag: tight ID, tight PF iso, pT > tag_pt (GeV, above the
    IsoMu24 turn-on), |eta| < 2.4, matched to an IsoMu24/IsoTkMu24 trigger object,
    in an event that fired one of the two paths.
    """
    mu = ak.zip({
        "pt": events.Muon_pt, "eta": events.Muon_eta, "phi": events.Muon_phi,
        "mass": ak.full_like(events.Muon_pt, MU_MASS), "charge": events.Muon_charge,
        "isTracker": events.Muon_isTracker, "tightId": events.Muon_tightId,
        "pfRelIso04_all": events.Muon_pfRelIso04_all, "dxy": events.Muon_dxy, "dz": events.Muon_dz,
        "genPartFlav": events.Muon_genPartFlav if is_mc else ak.zeros_like(events.Muon_charge),
    }, with_name="Momentum4D")
    mu["trig_matched"] = _trigger_match(mu, events, BIT_ISO | BIT_ISOTK)
    fired = events.HLT_IsoMu24 | events.HLT_IsoTkMu24
    mu = mu[(abs(mu.eta) < 2.4) & (mu.pt > 15)]

    is_tag = mu.tightId & _tight_iso(mu) & (mu.pt > tag_pt) & mu.trig_matched
    pair = ak.argcartesian([mu, mu], axis=1)
    t, p = mu[pair["0"]], mu[pair["1"]]
    tag_ok = is_tag[pair["0"]]
    good = (pair["0"] != pair["1"]) & tag_ok & (t.charge * p.charge < 0) & WPS[wp]["den"](p)
    good = good & fired
    m = (t + p).mass
    good = good & (m > M_LO) & (m < M_HI)

    w = np.ones(len(events))
    if is_mc:
        w = np.sign(ak.to_numpy(events.genWeight)) * events["puw"]
    wpair = ak.broadcast_arrays(w, m)[0]
    sel = lambda x: ak.to_numpy(ak.flatten(x[good]))
    return dict(m=sel(m), pt=sel(p.pt), aeta=sel(abs(p.eta)), passing=sel(WPS[wp]["num"](p)),
                w=sel(wpair), gen=sel(p.genPartFlav == 1))


def read(files, wp, is_mc, era, max_events, step="200 MB"):
    puw = None
    if is_mc:
        import correctionlib
        cs = correctionlib.CorrectionSet.from_file(f"{POG}/LUM/{era}/puWeights.json.gz")
        puw = list(cs.values())[0]
    out, n = [], 0
    branches = BRANCHES + (MC_BRANCHES if is_mc else [])
    for arrays in uproot.iterate([f"{f}:Events" for f in files], branches, step_size=step):
        if is_mc:
            arrays["puw"] = puw.evaluate(np.clip(ak.to_numpy(arrays.Pileup_nTrueInt), 0, 98.9), "nominal")
        out.append(tnp_pairs(arrays, wp, is_mc))
        n += len(arrays)
        print(f"[{'mc' if is_mc else 'data'}] {n} events, {sum(len(o['m']) for o in out)} pairs", file=sys.stderr)
        if max_events and n >= max_events:
            break
    return {k: np.concatenate([o[k] for o in out]) for k in out[0]}, n


def _hist(m, w=None):
    h, _ = np.histogram(m, bins=M_BINS, range=(M_LO, M_HI), weights=w)
    return h


def fit_pass_fail(data_pass, data_fail, tmpl_pass, tmpl_fail):
    """Simultaneous binned Poisson fit; returns (eff, err, ok, details)."""
    from iminuit import Minuit

    edges = np.linspace(M_LO, M_HI, M_BINS + 1)
    x = 0.5 * (edges[1:] + edges[:-1]) - 90.0
    sp = np.clip(tmpl_pass, 0, None); sp = sp / max(sp.sum(), 1e-12)
    sf = np.clip(tmpl_fail, 0, None); sf = sf / max(sf.sum(), 1e-12)

    def expo(norm, slope):
        e = np.exp(slope * x)
        return norm * e / e.sum()

    def nll(nsig, eff, bp, sp_, bf, sf_):
        mp = nsig * eff * sp + expo(bp, sp_) + 1e-9
        mf = nsig * (1 - eff) * sf + expo(bf, sf_) + 1e-9
        return float(np.sum(mp - data_pass * np.log(mp)) + np.sum(mf - data_fail * np.log(mf)))

    ntot = data_pass.sum() + data_fail.sum()
    e0 = data_pass.sum() / max(ntot, 1)
    m = Minuit(nll, nsig=0.9 * ntot, eff=min(max(e0, 0.05), 0.995), bp=0.05 * data_pass.sum() + 1,
               sp_=-0.02, bf=0.3 * data_fail.sum() + 1, sf_=-0.02)
    m.errordef = Minuit.LIKELIHOOD
    m.limits["nsig"] = (0, 2 * ntot + 10)
    m.limits["eff"] = (0, 1)
    m.limits["bp"] = (0, ntot + 10)
    m.limits["bf"] = (0, ntot + 10)
    m.limits["sp_"] = (-0.5, 0.5)
    m.limits["sf_"] = (-0.5, 0.5)
    m.migrad()
    m.hesse()
    ok = bool(m.valid and m.accurate)
    return m.values["eff"], m.errors["eff"], ok, {k: m.values[k] for k in m.parameters}


def pog_sf(era, name, aeta, pt, var="nominal"):
    import correctionlib
    cs = correctionlib.CorrectionSet.from_file(f"{POG}/MUO/{era}/muon_Z.json.gz")
    return cs[name].evaluate(aeta, pt, var)


def pog_edges(era, name):
    import gzip
    d = json.load(gzip.open(f"{POG}/MUO/{era}/muon_Z.json.gz"))
    c = next(c for c in d["corrections"] if c["name"] == name)
    node = c["data"]["content"]  # transform abs(eta) -> binning eta
    return node["edges"], node["content"][0]["edges"]


def mc_eff(d, mask):
    w = d["w"][mask & d["gen"]]
    p = d["passing"][mask & d["gen"]]
    sw, sw2 = w.sum(), (w**2).sum()
    if sw <= 0:
        return math.nan, math.nan
    e = (w * p).sum() / sw
    neff = sw**2 / sw2
    return e, math.sqrt(max(e * (1 - e), 1.0 / neff**2) / neff)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", nargs="+", required=True, help="data NanoAOD files (local or root://)")
    ap.add_argument("--mc", nargs="+", required=True, help="DY MC NanoAOD files")
    ap.add_argument("--wp", choices=sorted(WPS), default="tightid")
    ap.add_argument("--era", default="2016postVFP_UL", help="POG directory name, e.g. 2016postVFP_UL")
    ap.add_argument("--max-events", type=int, default=0, help="per sample; 0 = all")
    ap.add_argument("--out", default="tnp.json")
    ap.add_argument("--plots", default="", help="directory for per-bin fit plots (optional)")
    a = ap.parse_args(argv)

    try:
        dd, nd = read(a.data, a.wp, False, a.era, a.max_events)
        dm, nm = read(a.mc, a.wp, True, a.era, a.max_events)
        eta_edges, pt_edges = pog_edges(a.era, WPS[a.wp]["pog"])
    except (OSError, KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    rows, nfail = [], 0
    for i in range(len(eta_edges) - 1):
        for j in range(len(pt_edges) - 1):
            lo, hi = pt_edges[j], min(pt_edges[j + 1], 1e4)
            md = (dd["aeta"] >= eta_edges[i]) & (dd["aeta"] < eta_edges[i + 1]) & (dd["pt"] >= lo) & (dd["pt"] < hi)
            mm = (dm["aeta"] >= eta_edges[i]) & (dm["aeta"] < eta_edges[i + 1]) & (dm["pt"] >= lo) & (dm["pt"] < hi)
            if md.sum() < 50 or (mm & dm["gen"]).sum() < 50:
                continue
            gp, gf = mm & dm["gen"] & dm["passing"], mm & dm["gen"] & ~dm["passing"]
            ed, eed, ok, par = fit_pass_fail(_hist(dd["m"][md & dd["passing"]]), _hist(dd["m"][md & ~dd["passing"]]),
                                             _hist(dm["m"][gp], dm["w"][gp]), _hist(dm["m"][gf], dm["w"][gf]))
            em, eem = mc_eff(dm, mm)
            sf = ed / em
            esf = sf * math.hypot(eed / ed, eem / em) if ed > 0 else math.nan
            ptc = 0.5 * (lo + min(hi, 2 * lo))
            aetac = 0.5 * (eta_edges[i] + eta_edges[i + 1])
            pog = pog_sf(a.era, WPS[a.wp]["pog"], aetac, ptc)
            pog_unc = pog_sf(a.era, WPS[a.wp]["pog"], aetac, ptc, "systup") - pog
            pull = (sf - pog) / math.hypot(esf, pog_unc)
            nfail += not ok
            rows.append(dict(aeta=[eta_edges[i], eta_edges[i + 1]], pt=[lo, pt_edges[j + 1]], n_data=int(md.sum()),
                             eff_data=ed, eff_data_err=eed, eff_mc=em, eff_mc_err=eem, sf=sf, sf_err=esf,
                             pog_sf=pog, pog_unc=pog_unc, pull=pull, fit_ok=ok))
            print(f"|eta| {eta_edges[i]:.1f}-{eta_edges[i+1]:.1f} pt {lo:.0f}-{pt_edges[j+1]:.0f}: "
                  f"eff data {ed:.4f}+-{eed:.4f} mc {em:.4f}+-{eem:.4f} SF {sf:.4f}+-{esf:.4f} "
                  f"POG {pog:.4f}+-{pog_unc:.4f} pull {pull:+.2f}{'' if ok else ' FIT-NOT-OK'}")
            if a.plots:
                _plot(a.plots, a.wp, i, j, dd, dm, md, mm, par, rows[-1])

    pulls = np.array([r["pull"] for r in rows if math.isfinite(r["pull"])])
    res = dict(wp=a.wp, era=a.era, pog_correction=WPS[a.wp]["pog"], n_events_data=nd, n_events_mc=nm,
               mass_window_GeV=[M_LO, M_HI], bins=rows,
               mean_pull=float(pulls.mean()) if len(pulls) else None,
               rms_pull=float(np.sqrt((pulls**2).mean())) if len(pulls) else None)
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    print(f"N_BINS={len(rows)}")
    print(f"MEAN_PULL={res['mean_pull']}")
    print(f"RMS_PULL={res['rms_pull']}")
    print(f"OUT={a.out}")
    return 1 if nfail else 0


def _plot(outdir, wp, i, j, dd, dm, md, mm, par, row):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import mplhep as hep

    os.makedirs(outdir, exist_ok=True)
    edges = np.linspace(M_LO, M_HI, M_BINS + 1)
    x = 0.5 * (edges[1:] + edges[:-1]) - 90.0
    fig, axs = plt.subplots(1, 2, figsize=(11, 4.5))
    for ax, passing, eff, b, s in ((axs[0], True, par["eff"], par["bp"], par["sp_"]),
                                    (axs[1], False, 1 - par["eff"], par["bf"], par["sf_"])):
        h = _hist(dd["m"][md & (dd["passing"] == passing)])
        g = mm & dm["gen"] & (dm["passing"] == passing)
        t = np.clip(_hist(dm["m"][g], dm["w"][g]), 0, None)
        t = t / max(t.sum(), 1e-12)
        e = np.exp(s * x)
        bkg = b * e / e.sum()
        hep.histplot(h, edges, yerr=np.sqrt(h), histtype="errorbar", color="k", label="Data", ax=ax)
        ax.stairs(par["nsig"] * eff * t + bkg, edges, color="tab:blue", label="Fit")
        ax.stairs(bkg, edges, color="tab:red", ls="--", label="Background")
        ax.set_xlabel(r"$m_{\mu\mu}$ [GeV]")
        ax.set_title(f"{'pass' if passing else 'fail'}  |eta| {row['aeta'][0]}-{row['aeta'][1]}, pT {row['pt'][0]:.0f}-{row['pt'][1]:.0f} GeV", fontsize=10)
        ax.legend()
    fig.tight_layout()
    for ext in ("png", "pdf"):
        fig.savefig(os.path.join(outdir, f"fit_{wp}_eta{i}_pt{j}.{ext}"))
    plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
