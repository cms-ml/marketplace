"""Selection, fits and POG comparison on the flat pair skims written by condor/skim.py.

Imports the skill script plugins/cms/skills/muon-tag-and-probe/scripts/tnp.py (POG binning, POG SF, MC counting).
The fit is re-implemented here (same likelihood as tnp.fit_pass_fail) so that the background shape and the mass
window can be varied; `selftest()` checks that the nominal fit agrees with the skill's.
Units: GeV.
"""
import glob
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "plugins", "cms", "skills", "muon-tag-and-probe", "scripts"))
import tnp  # noqa: E402  (skill script)

ERA = "2016postVFP_UL"
HLT_BITS = {"IsoMu24": 0, "IsoTkMu24": 1, "IsoMu22": 2, "IsoMu22_eta2p1": 3, "IsoTkMu22": 4,
            "IsoTkMu22_eta2p1": 5, "IsoMu27": 6, "IsoTkMu27": 7, "Mu50": 8}
G_LAST_RUN = 280385  # Run2016G ends at run 280385, Run2016H starts at 280919
WP_NAMES = {"tightid": "NUM_TightID_DEN_TrackerMuons",
            "tightiso": "NUM_TightRelIso_DEN_TightIDandIPCut",
            "isomu24": "NUM_IsoMu24_or_IsoTkMu24_DEN_CutBasedIdTight_and_PFIsoTight"}


def load_skims(files):
    """Concatenate npz skims; returns (dict of arrays, list of per-job info dicts, set of lumi-section keys)."""
    parts, infos, ls = [], [], []
    for f in files:
        z = np.load(f)
        parts.append({k: z[k] for k in z.files if k not in ("info", "ls")})
        infos.append(json.loads(str(z["info"])))
        ls.append(z["ls"])
    d = {k: np.concatenate([p[k] for p in parts]) for k in parts[0]}
    d["aeta"] = np.abs(d["peta"])
    return d, infos, np.unique(np.concatenate(ls))


def golden_keys(path):
    j = json.load(open(path))
    ks = [int(r) * 100000 + np.arange(a, b + 1, dtype=np.int64) for r, ivs in j.items() for a, b in ivs]
    return np.unique(np.concatenate(ks))


def recorded_lumi_fb(csv_path, keys):
    """Sum of the 'recorded' column (/fb) over run*100000+ls keys; also returns n LS matched and n keys requested."""
    runs, lss, rec = [], [], []
    for line in open(csv_path):
        if line.startswith("#"):
            continue
        c = line.strip().split(",")
        runs.append(int(c[0].split(":")[0])); lss.append(int(c[1].split(":")[0])); rec.append(float(c[6]))
    k = np.array(runs, dtype=np.int64) * 100000 + np.array(lss, dtype=np.int64)
    m = np.isin(k, keys)
    return float(np.array(rec)[m].sum()), int(m.sum()), int(len(keys))


# ------------------------------------------------------------------ selection
# IsoMu24 trigger-matching definitions: name -> (tag match, probe pass, HLT requirement of the event).
# Match kinds: 'or' = bit 2 or bit 8 object, '2' = bit 2 (Iso) object only, '8' = bit 8 (IsoTkMu) object only,
# 'path' = bit 2 object if HLT_IsoMu24 fired or bit 8 object if HLT_IsoTkMu24 fired. Object pT >= 24 GeV (probe: `thr`), dR < 0.1.
# HLT kinds: 'or' = HLT_IsoMu24 or HLT_IsoTkMu24, 'mu24' / 'tk24' = that path alone, 'none' = no HLT requirement.
TRIG_DEFS = {
    "a": ("or", "or", "or"),       # the skill (tnp.py): tag and probe bit 2|8
    "b": ("2", "2", "or"),         # tag bit 2, probe bit 2
    "c": ("or", "2", "or"),        # tag bit 2|8, probe bit 2 (the previous round's "B2")
    "d": ("8", "8", "or"),         # tag bit 8, probe bit 8
    "e": ("path", "path", "or"),   # path-aware tag and probe
    "e2": ("or", "path", "or"),    # path-aware probe, tag bit 2|8 (the previous round's "C")
    "n": ("or", "or", "none"),     # bit 2|8 and pT only, no HLT requirement (the previous round's "A")
    "b_hlt": ("2", "2", "mu24"),   # as b, event fired HLT_IsoMu24
    "d_hlt": ("8", "8", "tk24"),   # as d, event fired HLT_IsoTkMu24
}


def fired(d):
    return (d["hlt"] & 3) != 0


def _match(d, kind, who, thr):
    if who == "tag":
        b2, b8 = d["tag2"], d["tag8"]
    else:
        b2, b8 = d["m2pt"] >= thr, d["m8pt"] >= thr
    if kind == "or":
        return b2 | b8
    if kind == "2":
        return b2
    if kind == "8":
        return b8
    if kind == "path":
        return (((d["hlt"] & 1) != 0) & b2) | (((d["hlt"] & 2) != 0) & b8)
    raise ValueError(kind)


def wp_masks(d, wp, trig="a", tag_pt=29.0, tag_iso=0.15, mlo=70.0, mhi=115.0, thr=24.0):
    """(denominator mask, passing mask) of the probes of working point `wp`.

    trig selects the IsoMu24 matching definition in TRIG_DEFS (tag match, probe pass, event HLT requirement). It also sets the tag
    match and the HLT requirement of the tight-ID and tight-iso pairs ('a' = the skill's selection, the nominal one).
    thr: matched-object pT threshold [GeV] of the probe (the tag match is at 24 GeV, fixed in the skim).
    """
    tagk, prbk, hltk = TRIG_DEFS[trig]
    base = (d["tpt"] > tag_pt) & (d["tiso"] < tag_iso) & (d["m"] > mlo) & (d["m"] < mhi)
    if tagk != "or":
        base &= _match(d, tagk, "tag", thr)
    if hltk == "or":
        base &= fired(d)
    elif hltk == "mu24":
        base &= (d["hlt"] & 1) != 0
    elif hltk == "tk24":
        base &= (d["hlt"] & 2) != 0
    if wp == "tightid":
        return base, d["ptight"]
    if wp == "tightiso":
        return base & d["ptight"] & d["pip"], d["piso"] < 0.15
    if wp == "isomu24":
        return base & d["ptight"] & (d["piso"] < 0.15), _match(d, prbk, "probe", thr)
    raise ValueError(wp)


# ------------------------------------------------------------------ fit
def fit_pf(hp, hf, tp, tf, lo, hi, bkg="exp"):
    """Simultaneous pass/fail binned Poisson fit; 1 GeV bins in [lo, hi]. Returns (eff, err, ok, par).

    Signal: MC template of each category (normalised), common N_sig and efficiency. Background per category:
    'exp' exp(slope*(m-90)) or 'poly2' 1 + a*u + b*u^2 (u = (m-center)/half-width, clipped at 0), each normalised
    to a free yield. Same likelihood as tnp.fit_pass_fail for 'exp'.
    """
    from iminuit import Minuit
    nb = len(hp)
    edges = np.linspace(lo, hi, nb + 1)
    c = 0.5 * (edges[1:] + edges[:-1])
    x = c - 90.0
    u = (c - 0.5 * (lo + hi)) / (0.5 * (hi - lo))
    sp = np.clip(tp, 0, None); sp = sp / max(sp.sum(), 1e-12)
    sf = np.clip(tf, 0, None); sf = sf / max(sf.sum(), 1e-12)

    def shape(norm, a, b):
        if bkg == "exp":
            e = np.exp(a * x)
        else:
            e = np.clip(1.0 + a * u + b * u * u, 1e-6, None)
        return norm * e / e.sum()

    def nll(nsig, eff, bp, ap, cp, bf, af, cf):
        mp = nsig * eff * sp + shape(bp, ap, cp) + 1e-9
        mf = nsig * (1 - eff) * sf + shape(bf, af, cf) + 1e-9
        return float(np.sum(mp - hp * np.log(mp)) + np.sum(mf - hf * np.log(mf)))

    ntot = hp.sum() + hf.sum()
    e0 = hp.sum() / max(ntot, 1)
    a0 = -0.02 if bkg == "exp" else 0.0
    best = None
    for start_scale in (1.0, 0.5):
        m = Minuit(nll, nsig=0.9 * ntot, eff=min(max(e0, 0.05), 0.995), bp=start_scale * 0.05 * hp.sum() + 1, ap=a0, cp=0.0,
                   bf=start_scale * 0.3 * hf.sum() + 1, af=a0, cf=0.0)
        m.errordef = Minuit.LIKELIHOOD
        m.limits["nsig"] = (0, 2 * ntot + 10); m.limits["eff"] = (0, 1)
        m.limits["bp"] = (0, ntot + 10); m.limits["bf"] = (0, ntot + 10)
        if bkg == "exp":
            for k in ("ap", "af"):
                m.limits[k] = (-0.5, 0.5)
            m.fixed["cp"] = True; m.fixed["cf"] = True
        else:
            for k in ("ap", "af", "cp", "cf"):
                m.limits[k] = (-3, 3)
        m.migrad(); m.hesse()
        ok = bool(m.valid and m.accurate)
        if best is None or (ok and not best[2]):
            best = (m.values["eff"], m.errors["eff"], ok, {k: m.values[k] for k in m.parameters}, m.fval)
        if ok:
            break
    return best[0], best[1], best[2], best[3]


def hist(m, lo, hi, w=None):
    h, _ = np.histogram(m, bins=int(round(hi - lo)), range=(lo, hi), weights=w)
    return h


def mc_eff(w, ps):
    """Weighted counting efficiency and error, identical to tnp.mc_eff."""
    sw, sw2 = w.sum(), (w ** 2).sum()
    if sw <= 0:
        return math.nan, math.nan
    e = (w * ps).sum() / sw
    neff = sw ** 2 / sw2
    return e, math.sqrt(max(e * (1 - e), 1.0 / neff ** 2) / neff)


# ------------------------------------------------------------------ bins and measurement
def pog_bins(wp):
    eta_e, pt_e = tnp.pog_edges(ERA, WP_NAMES[wp])
    return np.array(eta_e), np.array(pt_e)


def _groups(d, mask, eta_e, pt_e):
    idx = np.flatnonzero(mask)
    ie = np.searchsorted(eta_e, d["aeta"][idx], "right") - 1
    ij = np.searchsorted(pt_e, d["ppt"][idx], "right") - 1
    ok = (ie >= 0) & (ie < len(eta_e) - 1) & (ij >= 0) & (ij < len(pt_e) - 1)
    idx, ie, ij = idx[ok], ie[ok], ij[ok]
    bid = ie * (len(pt_e) - 1) + ij
    order = np.argsort(bid, kind="stable")
    idx, bid = idx[order], bid[order]
    cuts = np.flatnonzero(np.diff(bid)) + 1
    starts = np.r_[0, cuts]
    out = {}
    for s, e in zip(starts, np.r_[cuts, len(idx)]):
        b = int(bid[s])
        out[(b // (len(pt_e) - 1), b % (len(pt_e) - 1))] = idx[s:e]
    return out


def measure(dd, dm, wp, trig="a", tag_pt=29.0, tag_iso=0.15, mlo=70.0, mhi=115.0, bkg="exp", sel_d=None, min_n=50,
            keep_hists=False, thr=24.0):
    """Per-bin efficiencies and SF for one analysis variation.

    sel_d: optional boolean mask on the data pairs (e.g. one run era). Returns {(ieta, ipt): dict}.
    """
    eta_e, pt_e = pog_bins(wp)
    denD, psD = wp_masks(dd, wp, trig, tag_pt, tag_iso, mlo, mhi, thr)
    if sel_d is not None:
        denD = denD & sel_d
    denM, psM = wp_masks(dm, wp, trig, tag_pt, tag_iso, mlo, mhi, thr)
    denM = denM & dm["gen"]
    gD, gM = _groups(dd, denD, eta_e, pt_e), _groups(dm, denM, eta_e, pt_e)
    res = {}
    for key, iD in gD.items():
        iM = gM.get(key)
        if iM is None or len(iD) < min_n or len(iM) < min_n:
            continue
        pD, pM = psD[iD], psM[iM]
        mD, mM, wM = dd["m"][iD], dm["m"][iM], dm["w"][iM]
        hp, hf = hist(mD[pD], mlo, mhi), hist(mD[~pD], mlo, mhi)
        tp, tf = hist(mM[pM], mlo, mhi, wM[pM]), hist(mM[~pM], mlo, mhi, wM[~pM])
        ed, eed, ok, par = fit_pf(hp, hf, tp, tf, mlo, mhi, bkg)
        em, eem = mc_eff(wM, pM)
        sf = ed / em
        r = dict(n_data=int(len(iD)), n_pass_data=int(pD.sum()), n_mc=int(len(iM)), eff_data=float(ed), eff_data_err=float(eed),
                 eff_mc=float(em), eff_mc_err=float(eem), sf=float(sf),
                 sf_stat=float(sf * math.hypot(eed / ed, eem / em)) if ed > 0 else math.nan, fit_ok=ok)
        if keep_hists:
            r["hists"] = dict(hp=hp, hf=hf, tp=tp, tf=tf, par=par)
        res[key] = r
    return res


def pog_values(wp, eta_lo, eta_hi, pt_lo, pt_hi):
    """POG SF and uncertainty (systup - nominal) at the bin centre as tnp.py does (pT centre = 0.5*(lo + min(hi, 2 lo)))."""
    ptc = 0.5 * (pt_lo + min(pt_hi, 2 * pt_lo))
    etac = 0.5 * (eta_lo + eta_hi)
    nom = float(tnp.pog_sf(ERA, WP_NAMES[wp], etac, ptc))
    up = float(tnp.pog_sf(ERA, WP_NAMES[wp], etac, ptc, "systup"))
    return nom, up - nom


def pog_average(wp, d, idx, pt_min):
    """POG SF and uncertainty averaged over the probes of a bin (event-level evaluation) as a cross-check."""
    ae = d["aeta"][idx].astype(float)
    pt = np.clip(d["ppt"][idx].astype(float), pt_min, None)
    nom = tnp.pog_sf(ERA, WP_NAMES[wp], ae, pt)
    up = tnp.pog_sf(ERA, WP_NAMES[wp], ae, pt, "systup")
    return float(nom.mean()), float((up - nom).mean())


def selftest(dd, dm, wp="tightid", bin_key=(0, 4)):
    """Compare the nominal fit of this module with tnp.fit_pass_fail on one bin. Returns (ours, skill)."""
    r = measure(dd, dm, wp, keep_hists=True)[bin_key]
    h = r["hists"]
    e, ee, ok, _ = tnp.fit_pass_fail(h["hp"], h["hf"], h["tp"], h["tf"])
    return (r["eff_data"], r["eff_data_err"]), (float(e), float(ee))


def weighted_ratio_30_60(rows):
    """Inverse-variance weighted mean of SF/POG over the bins with 30 <= pT < 60 GeV (uses sf_total_err or sf_stat)."""
    num = den = 0.0
    for r in rows:
        if 30.0 <= r["pt"][0] < 60.0:
            e = r.get("sf_total_err", r.get("sf_stat")) / r["pog_sf"]
            w = 1.0 / (e * e)
            num += w * r["sf"] / r["pog_sf"]
            den += w
    return num / den if den else None
