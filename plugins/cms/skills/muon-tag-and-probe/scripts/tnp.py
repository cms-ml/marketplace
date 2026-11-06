#!/usr/bin/env python3
"""Muon tag-and-probe on Z -> mu mu in CMS NanoAOD (Run 2 UL): efficiencies, data/MC scale
factors with stat, MC-stat and syst uncertainties, POG comparison, correctionlib output.

Presets (--wp tightid | tightiso | isomu24) or any working point from boolean expressions
over NanoAOD Muon_ fields (without the "Muon_" prefix):

    tnp.py --data <files> --mc <files> --wp tightid --out tnp_tightid.json
    tnp.py --data <files> --mc <files> --den isTracker --num mediumId \\
           --pog NUM_MediumID_DEN_TrackerMuons --correctionlib sf.json --name mediumid
    tnp.py --data <files> --mc <files> --den "tightId & (pfRelIso04_all < 0.15)" \\
           --num-trigger 2:22 --pt-edges 20 22 25 30 40 60 120 --no-pog --name isomu22

Expressions: field names (tightId, mediumId, looseId, softId, highPtId, mvaId, tkIsoId,
pfRelIso04_all, tkRelIso, dxy, dz, sip3d, ...), numbers, True/False, abs(), comparisons
(< <= > >= == !=, chained), arithmetic (+ - * /), and & | ~ (or: and or not, elementwise).
Python precedence: "tightId & pfRelIso04_all < 0.15" means "(tightId & pfRelIso04_all) < 0.15"
and is rejected; write "tightId & (pfRelIso04_all < 0.15)" or "tightId and pfRelIso04_all < 0.15".
Nothing is passed to eval(): the expression is parsed with ast and only these nodes are allowed.

Trigger match BITS:PTMIN[:DRMAX]: a TrigObj with id 13, pT >= PTMIN (GeV) and filterBits
matching BITS within DeltaR < DRMAX (0.1) of the muon. BITS "2" or "2|8" = any of the
bits, "1&2" = all of them. 2016 NanoAODv9 muon bits (read your file's
Events/TrigObj_filterBits title): 1 TrkIsoVVL (Mu17/Mu8_TrkIsoVVL legs), 2 Iso (IsoMu),
4 OverlapFilter PFTau, 8 IsoTkMu, 1024 1mu (Mu50).

Data efficiency: simultaneous binned fit of the pass and fail m_mumu spectra (70-115 GeV)
with the MC signal template of each category plus an exponential background (iminuit, HESSE).
MC efficiency: counting of generator-matched probes (sign(genWeight) x pileup weight).
Uncertainties per bin (SF units): stat (data fit), mc_stat (Poisson bootstrap of the MC
events: MC efficiency and templates refitted together, --mc-replicas), syst (--syst:
background exp vs Bernstein poly2, window 75-110 GeV, tag pT + 4 GeV or iso < 0.05), total =
quadrature sum. --syst is on by default with --correctionlib (--no-syst to switch it off); without
it a warning says the total holds stat and mc_stat only. Not included in any: the bias of the fit
from finite MC templates (see the skill).

Unreliable bins: fit not ok, fewer than --min-fail (5) data or gen-matched MC probes in the fail
category, or SF data-stat error above --max-sf-stat (0.1). Their raw numbers stay in the result JSON
(bins[], "reliable": false); the correctionlib file uses the nearest reliable pT bin of the same
|eta| row with an extra uncertainty "fill" (see fill_plan()), as for unmeasured bins, and lists
them (also in "correctionlib_filled_bins"). No lumi mask is applied unless --lumi-mask is given.

Offline: if the POG muon JSON or the LUM pileup JSON cannot be read (or --no-pog, --no-pu),
the comparison or the pileup weights are skipped with a warning and recorded in the output.

Stdout: one line per bin, then KEY=VALUE lines (N_BINS, N_FIT_FAILED, MEAN_PULL, RMS_PULL,
MEAN_PULL_TOTAL, RMS_PULL_TOTAL, POG, PILEUP, CORRECTIONLIB, OUT). Diagnostics on stderr.
Exit codes: 0 ok, 1 nominal fit failed in some bins, 2 bad arguments or unreadable input.

Importable: tnp_pairs(), WPS, Expr, parse_trigger(), fit_pass_fail(), pog_sf(), write_correctionlib().
"""
from __future__ import annotations

import argparse
import ast
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
BIT_TRKISOVVL, BIT_ISO, BIT_ISOTK, BIT_MU50 = 1, 2, 8, 1024

ETA_EDGES = [0.0, 0.9, 1.2, 2.1, 2.4]  # the Run 2 UL muon_Z.json.gz binning (|eta|, pT in GeV)
PT_EDGES = [15.0, 20.0, 25.0, 30.0, 40.0, 50.0, 60.0, 120.0, math.inf]

TAG = "tightId & (pfRelIso04_all < 0.15)"
TAG_HLT = "HLT_IsoMu24,HLT_IsoTkMu24"

# Working point = (probe denominator, numerator, POG correction name).
# The denominators follow the POG names: NUM_<num>_DEN_<den>.
WPS = {
    "tightid": dict(den="isTracker", num="tightId", num_trigger=None,
                    pog="NUM_TightID_DEN_TrackerMuons", pt_edges=PT_EDGES),
    "tightiso": dict(den="tightId & (abs(dxy) < 0.2) & (abs(dz) < 0.5)", num="pfRelIso04_all < 0.15",
                     num_trigger=None, pog="NUM_TightRelIso_DEN_TightIDandIPCut", pt_edges=PT_EDGES),
    # Bit 2 (Iso, IsoMu24-type filter) only: the OR with bit 8 (IsoTkMu) gave an IsoMu24 SF
    # 1.0-1.5% above the POG; bit 2 alone agrees within 0.2% for |eta| > 0.9 (validation/muon-tnp).
    "isomu24": dict(den="tightId & (pfRelIso04_all < 0.15)", num=None, num_trigger="2:24",
                    pog="NUM_IsoMu24_or_IsoTkMu24_DEN_CutBasedIdTight_and_PFIsoTight",
                    pt_edges=[26.0, 30.0, 40.0, 50.0, 60.0, 120.0, 200.0, math.inf]),
}


# ---------------------------------------------------------------- safe expressions
class Expr:
    """Boolean expression over muon fields, parsed with ast and evaluated node by node (no eval)."""

    _CMP = {ast.Lt: np.less, ast.LtE: np.less_equal, ast.Gt: np.greater, ast.GtE: np.greater_equal,
            ast.Eq: np.equal, ast.NotEq: np.not_equal}
    _ARITH = {ast.Add: np.add, ast.Sub: np.subtract, ast.Mult: np.multiply, ast.Div: np.divide}

    def __init__(self, text: str):
        self.text = text.strip()
        try:
            tree = ast.parse(self.text, mode="eval")
        except SyntaxError as e:
            raise ValueError(f"cannot parse expression {text!r}: {e.msg}") from None
        except (RecursionError, MemoryError):
            raise ValueError(f"expression too deeply nested or too long: {text[:60]!r}...") from None
        self.names: set[str] = set()
        try:
            self._check(tree.body)
        except (RecursionError, MemoryError):
            raise ValueError(f"expression too deeply nested or too long: {text[:60]!r}...") from None
        self.tree = tree.body

    def _check(self, n):
        if isinstance(n, ast.Constant):
            if not isinstance(n.value, (bool, int, float)):
                raise ValueError(f"only numbers and True/False allowed in {self.text!r}, got {n.value!r}")
        elif isinstance(n, ast.Name):
            if n.id in ("abs",):
                raise ValueError(f"'abs' must be called: abs(x), in {self.text!r}")
            self.names.add(n.id)
        elif isinstance(n, ast.Call):
            if not (isinstance(n.func, ast.Name) and n.func.id == "abs" and len(n.args) == 1 and not n.keywords):
                raise ValueError(f"only abs(x) may be called, in {self.text!r}")
            self._check(n.args[0])
        elif isinstance(n, ast.BoolOp):
            for v in n.values:
                self._check(v)
        elif isinstance(n, ast.UnaryOp):
            if not isinstance(n.op, (ast.Not, ast.Invert, ast.USub, ast.UAdd)):
                raise ValueError(f"operator not allowed in {self.text!r}")
            self._check(n.operand)
        elif isinstance(n, ast.BinOp):
            if not isinstance(n.op, (ast.BitAnd, ast.BitOr, *self._ARITH)):
                raise ValueError(f"operator {type(n.op).__name__} not allowed in {self.text!r}")
            self._check(n.left)
            self._check(n.right)
        elif isinstance(n, ast.Compare):
            for o in [n.left, *n.comparators]:
                if isinstance(o, ast.BinOp) and isinstance(o.op, (ast.BitAnd, ast.BitOr)):
                    raise ValueError(
                        f"{self.text!r}: '&' and '|' bind tighter than comparisons in Python, so "
                        f"'a & b < c' means '(a & b) < c'. Add parentheses: 'a & (b < c)'.")
                self._check(o)
            for op in n.ops:
                if type(op) not in self._CMP:
                    raise ValueError(f"comparison {type(op).__name__} not allowed in {self.text!r}")
        else:
            raise ValueError(f"{type(n).__name__} not allowed in expression {self.text!r}")

    @staticmethod
    def _bool(x, what):
        if isinstance(x, (bool, np.bool_)):
            return x
        if str(ak.type(x)).split("*")[-1].strip().endswith("bool"):
            return x
        raise ValueError(f"{what} needs booleans, got {ak.type(x)}: compare integers explicitly "
                         f"(e.g. highPtId == 2, mvaId >= 2)")

    def _ev(self, n, mu):
        if isinstance(n, ast.Constant):
            return n.value
        if isinstance(n, ast.Name):
            return mu[n.id]
        if isinstance(n, ast.Call):
            return abs(self._ev(n.args[0], mu))
        if isinstance(n, ast.BoolOp):
            vals = [self._bool(self._ev(v, mu), self.text) for v in n.values]
            out = vals[0]
            for v in vals[1:]:
                out = (out & v) if isinstance(n.op, ast.And) else (out | v)
            return out
        if isinstance(n, ast.UnaryOp):
            v = self._ev(n.operand, mu)
            if isinstance(n.op, (ast.Not, ast.Invert)):
                v = self._bool(v, self.text)
                return (not v) if isinstance(v, bool) else ~v
            return -v if isinstance(n.op, ast.USub) else v
        if isinstance(n, ast.BinOp):
            a, b = self._ev(n.left, mu), self._ev(n.right, mu)
            if isinstance(n.op, ast.BitAnd):
                return self._bool(a, self.text) & self._bool(b, self.text)
            if isinstance(n.op, ast.BitOr):
                return self._bool(a, self.text) | self._bool(b, self.text)
            return self._ARITH[type(n.op)](a, b)
        if isinstance(n, ast.Compare):
            out, left = None, self._ev(n.left, mu)
            for op, c in zip(n.ops, n.comparators):
                right = self._ev(c, mu)
                r = self._CMP[type(op)](left, right)
                out = r if out is None else (out & r)
                left = right
            return out
        raise ValueError(n)

    def __call__(self, mu):
        try:
            r = self._ev(self.tree, mu)
        except (RecursionError, MemoryError):
            raise ValueError(f"expression too deeply nested: {self.text[:60]!r}...") from None
        if isinstance(r, (bool, np.bool_)):
            return ak.full_like(mu.pt, bool(r), dtype=bool)
        return self._bool(r, f"expression {self.text!r}")

    def __repr__(self):
        return self.text


def parse_trigger(spec):
    """'BITS:PTMIN[:DRMAX]' -> dict(mask, all, pt_min, dr_max); None/'' -> None. BITS: 2, 2|8, 1&2, 0x2."""
    if not spec or spec.lower() == "none":
        return None
    parts = spec.split(":")
    if len(parts) not in (2, 3):
        raise ValueError(f"trigger spec {spec!r}: expected BITS:PTMIN[:DRMAX], e.g. 2:24")
    if "&" in parts[0] and "|" in parts[0]:
        raise ValueError(f"trigger spec {spec!r}: mixing '|' (any of) and '&' (all of) is ambiguous; use one")
    req_all = "&" in parts[0]
    try:
        bits = [int(b, 0) for b in parts[0].replace("&", "|").split("|")]
        pt_min, dr = float(parts[1]), float(parts[2]) if len(parts) == 3 else 0.1
    except ValueError:
        raise ValueError(f"trigger spec {spec!r}: BITS must be integers joined by | or &, PTMIN a number") from None
    mask = 0
    for b in bits:
        if b <= 0:
            raise ValueError(f"trigger spec {spec!r}: bits must be positive integers")
        mask |= b
    if not (pt_min >= 0 and dr > 0 and math.isfinite(dr)):
        raise ValueError(f"trigger spec {spec!r}: PTMIN must be >= 0 and DRMAX > 0")
    return dict(mask=mask, all=req_all, pt_min=pt_min, dr_max=dr, spec=spec)


def make_selection(wp=None, num=None, den=None, num_trigger=None, tag=TAG, tag_pt=29.0,
                   tag_trigger="2:24", tag_hlt=TAG_HLT, probe_pt_min=15.0):
    """Selection dict from a preset and/or expressions (explicit arguments override the preset)."""
    p = WPS[wp] if wp else {}
    num = num if num is not None else p.get("num")
    den = den if den is not None else p.get("den")
    num_trigger = num_trigger if num_trigger is not None else p.get("num_trigger")
    if den is None:
        raise ValueError("no probe denominator: give --wp or --den")
    if num is None and not num_trigger:
        raise ValueError("no numerator: give --wp, --num or --num-trigger")
    hlt = [h.strip() for h in (tag_hlt or "").split(",") if h.strip() and h.strip().lower() != "none"]
    return dict(den=Expr(den), num=Expr(num) if num else None, num_trigger=parse_trigger(num_trigger),
                tag=Expr(tag), tag_pt=float(tag_pt), tag_trigger=parse_trigger(tag_trigger), tag_hlt=hlt,
                probe_pt_min=float(probe_pt_min))


def _fields(sel):
    names = {"pt", "eta", "phi", "charge", "pfRelIso04_all"}
    for k in ("den", "num", "tag"):
        if sel[k] is not None:
            names |= sel[k].names
    return sorted(names)


def branches_for(sel, is_mc, lumi=False):
    br = [f"Muon_{n}" for n in _fields(sel)] + list(sel["tag_hlt"])
    if lumi and not is_mc:
        br += ["run", "luminosityBlock"]
    if sel["num_trigger"] or sel["tag_trigger"]:
        br += ["TrigObj_id", "TrigObj_filterBits", "TrigObj_pt", "TrigObj_eta", "TrigObj_phi"]
    if is_mc:
        br += ["genWeight", "Pileup_nTrueInt", "Muon_genPartFlav"]
    return br


# ---------------------------------------------------------------- pairs
def _trigger_match(mu, events, bits, pt_min=24.0, dr_max=0.1, require_all=False):
    """True for each muon within dr_max of a TrigObj muon with any (or all) of `bits` and pT >= pt_min (GeV).

    A filter bit marks a filter type, not a path, so the bit alone does not fix the path
    or its threshold (see the skill's "Filter bits are not paths" gotcha).
    """
    to = ak.zip({"pt": events.TrigObj_pt, "eta": events.TrigObj_eta, "phi": events.TrigObj_phi,
                 "id": events.TrigObj_id, "bits": events.TrigObj_filterBits})
    hit = ((to.bits & bits) == bits) if require_all else ((to.bits & bits) != 0)
    to = to[(to.id == 13) & hit & (to.pt >= pt_min)]
    pairs = ak.cartesian({"m": mu, "t": to}, nested=True)
    deta = pairs.m.eta - pairs.t.eta
    dphi = (pairs.m.phi - pairs.t.phi + np.pi) % (2 * np.pi) - np.pi
    return ak.fill_none(ak.any(deta**2 + dphi**2 < dr_max**2, axis=-1), False)


def _match(mu, events, spec):
    return _trigger_match(mu, events, spec["mask"], spec["pt_min"], spec["dr_max"], spec["all"])


def tnp_pairs(events, sel, is_mc, tag_pt=None):
    """Flat arrays (mass, probe pt, probe |eta|, passing, weight, genmatch, tag pt/iso, event) of pairs.

    `sel` is a make_selection() dict or a preset name. Every muon pair is used twice (each muon
    as tag once), so a probe that is also a good tag is not biased. Tag: sel["tag"], pT > tag_pt
    (GeV, above the trigger turn-on), |eta| < 2.4, matched to the tag trigger object, in an event
    that fired one of sel["tag_hlt"].
    """
    if isinstance(sel, str):
        sel = make_selection(sel)
    if tag_pt is not None:
        sel = dict(sel, tag_pt=tag_pt)
    rec = {n: events[f"Muon_{n}"] for n in _fields(sel) if n != "mass"}
    rec["mass"] = ak.full_like(events.Muon_pt, MU_MASS)
    rec["genPartFlav"] = events.Muon_genPartFlav if is_mc else ak.zeros_like(events.Muon_charge)
    mu = ak.zip(rec, with_name="Momentum4D")
    if sel["tag_trigger"]:
        mu["tag_matched"] = _match(mu, events, sel["tag_trigger"])
    else:
        mu["tag_matched"] = ak.ones_like(mu.pt, dtype=bool)
    if sel["num_trigger"]:
        if sel["num_trigger"] == sel["tag_trigger"]:
            mu["num_matched"] = mu.tag_matched
        else:
            mu["num_matched"] = _match(mu, events, sel["num_trigger"])
    fired = None
    for h in sel["tag_hlt"]:
        fired = events[h] if fired is None else (fired | events[h])
    mu = mu[(abs(mu.eta) < 2.4) & (mu.pt > sel["probe_pt_min"])]

    is_tag = sel["tag"](mu) & (mu.pt > sel["tag_pt"]) & mu.tag_matched
    pair = ak.argcartesian([mu, mu], axis=1)
    t, p = mu[pair["0"]], mu[pair["1"]]
    tag_ok = is_tag[pair["0"]]
    good = (pair["0"] != pair["1"]) & tag_ok & (t.charge * p.charge < 0) & sel["den"](p)
    if fired is not None:
        good = good & fired
    m = (t + p).mass
    good = good & (m > M_LO) & (m < M_HI)

    passing = sel["num"](p) if sel["num"] is not None else None
    if sel["num_trigger"]:
        passing = p.num_matched if passing is None else (passing & p.num_matched)

    w = np.ones(len(events))
    if is_mc:
        w = np.sign(ak.to_numpy(events.genWeight)) * events["puw"]
    wpair = ak.broadcast_arrays(w, m)[0]
    evt = ak.broadcast_arrays(np.arange(len(events)), m)[0]
    sel_ = lambda x: ak.to_numpy(ak.flatten(x[good]))
    return dict(m=sel_(m), pt=sel_(p.pt), aeta=sel_(abs(p.eta)), passing=sel_(passing),
                w=sel_(wpair), gen=sel_(p.genPartFlav == 1), tpt=sel_(t.pt), tiso=sel_(t.pfRelIso04_all),
                evt=sel_(evt))


def check_branches(f, branches):
    keys = set(uproot.open(f"{f}:Events").keys())
    missing = [b for b in branches if b not in keys]
    if missing:
        mu = sorted(k[5:] for k in keys if k.startswith("Muon_"))
        raise KeyError(f"branches not in {f}: {missing}. Muon fields: {' '.join(mu)}")


def load_lumi_mask(path):
    """CMS certification JSON {"run": [[first_ls, last_ls], ...]} -> {run: int array (n, 2)}."""
    with open(path) as f:
        d = json.load(f)
    return {int(r): np.asarray(v, dtype=np.int64).reshape(-1, 2) for r, v in d.items()}


def in_lumi_mask(runs, lumis, mask):
    runs, lumis = np.asarray(runs), np.asarray(lumis)
    ok = np.zeros(len(runs), dtype=bool)
    for r in np.unique(runs):
        rng = mask.get(int(r))
        if rng is None:
            continue
        s = runs == r
        lv = lumis[s][:, None]
        ok[s] = ((lv >= rng[:, 0]) & (lv <= rng[:, 1])).any(axis=1)
    return ok


def read(files, sel, is_mc, puw, max_events, step="200 MB", lumi_mask=None, stats=None):
    """Pairs of all files; puw = correctionlib pileup correction or None (weight 1).

    lumi_mask (data only): load_lumi_mask() dict; events outside it are dropped (stats["n_in_mask"]).
    """
    if isinstance(sel, str):
        sel = make_selection(sel)
    out, n, n_in = [], 0, 0
    use_mask = lumi_mask is not None and not is_mc
    branches = branches_for(sel, is_mc, use_mask)
    check_branches(files[0], branches)
    for arrays in uproot.iterate([f"{f}:Events" for f in files], branches, step_size=step):
        if max_events:
            arrays = arrays[: max_events - n]   # stop at max_events, not at the end of the chunk
        n_chunk = len(arrays)
        if use_mask:
            arrays = arrays[in_lumi_mask(ak.to_numpy(arrays.run), ak.to_numpy(arrays.luminosityBlock), lumi_mask)]
        n_in += len(arrays)
        if is_mc:
            if puw is not None:
                arrays["puw"] = puw.evaluate(np.clip(ak.to_numpy(arrays.Pileup_nTrueInt), 0, 98.9), "nominal")
            else:
                arrays["puw"] = np.ones(len(arrays))
        o = tnp_pairs(arrays, sel, is_mc)
        o["evt"] = o["evt"] + n
        out.append(o)
        n += n_chunk
        print(f"[{'mc' if is_mc else 'data'}] {n} events, {sum(len(o['m']) for o in out)} pairs", file=sys.stderr)
        if max_events and n >= max_events:
            break
    if stats is not None:
        stats["n_in_mask"] = n_in
    return {k: np.concatenate([o[k] for o in out]) for k in out[0]}, n


# ---------------------------------------------------------------- fit
def _nb(mrange):
    return int(round((mrange[1] - mrange[0]) * M_BINS / (M_HI - M_LO)))


def _hist(m, w=None, mrange=(M_LO, M_HI)):
    h, _ = np.histogram(m, bins=_nb(mrange), range=mrange, weights=w)
    return h


def fit_pass_fail(data_pass, data_fail, tmpl_pass, tmpl_fail, bkg="exp", mrange=(M_LO, M_HI)):
    """Simultaneous binned Poisson fit; returns (eff, err, ok, details). bkg: exp | poly2 (Bernstein)."""
    from iminuit import Minuit

    edges = np.linspace(mrange[0], mrange[1], _nb(mrange) + 1)
    x = 0.5 * (edges[1:] + edges[:-1]) - 90.0
    sp = np.clip(tmpl_pass, 0, None); sp = sp / max(sp.sum(), 1e-12)
    sf = np.clip(tmpl_fail, 0, None); sf = sf / max(sf.sum(), 1e-12)
    ntot = data_pass.sum() + data_fail.sum()
    e0 = data_pass.sum() / max(ntot, 1)
    start = dict(nsig=0.9 * ntot, eff=min(max(e0, 0.05), 0.995), bp=0.05 * data_pass.sum() + 1,
                 bf=0.3 * data_fail.sum() + 1)

    if bkg == "exp":
        def expo(norm, slope):
            e = np.exp(slope * x)
            return norm * e / e.sum()

        def nll(nsig, eff, bp, sp_, bf, sf_):
            mp = nsig * eff * sp + expo(bp, sp_) + 1e-9
            mf = nsig * (1 - eff) * sf + expo(bf, sf_) + 1e-9
            return float(np.sum(mp - data_pass * np.log(mp)) + np.sum(mf - data_fail * np.log(mf)))

        m = Minuit(nll, nsig=start["nsig"], eff=start["eff"], bp=start["bp"], sp_=-0.02, bf=start["bf"], sf_=-0.02)
        shape = ("sp_", "sf_")
    else:
        # second-order Bernstein polynomial: non-negative coefficients keep it positive and smooth
        # (a plain clipped 1 + a x + b x^2 went negative at the edges and MIGRAD returned invalid minima)
        u = (x - x.min()) / max(x.max() - x.min(), 1e-9)
        b0, b1, b2 = (1 - u) ** 2, 2 * u * (1 - u), u * u

        def poly(norm, c1, c2):
            e = b0 + c1 * b1 + c2 * b2 + 1e-9
            return norm * e / e.sum()

        def nll(nsig, eff, bp, p1, p2, bf, f1, f2):
            mp = nsig * eff * sp + poly(bp, p1, p2) + 1e-9
            mf = nsig * (1 - eff) * sf + poly(bf, f1, f2) + 1e-9
            return float(np.sum(mp - data_pass * np.log(mp)) + np.sum(mf - data_fail * np.log(mf)))

        m = Minuit(nll, nsig=start["nsig"], eff=start["eff"], bp=start["bp"], p1=0.8, p2=0.6,
                   bf=start["bf"], f1=0.8, f2=0.6)
        for k in ("p1", "p2", "f1", "f2"):
            m.limits[k] = (0, 20)
        shape = ()
    m.errordef = Minuit.LIKELIHOOD
    m.limits["nsig"] = (0, 2 * ntot + 10)
    m.limits["eff"] = (0, 1)
    m.limits["bp"] = (0, ntot + 10)
    m.limits["bf"] = (0, ntot + 10)
    for k in shape:
        m.limits[k] = (-0.5, 0.5)
    m.migrad()
    m.hesse()
    ok = bool(m.valid and m.accurate)
    details = {k: m.values[k] for k in m.parameters}
    details["migrad_valid"] = bool(m.valid)
    return m.values["eff"], m.errors["eff"], ok, details


def mc_eff(d, mask, wmul=None):
    w = d["w"][mask & d["gen"]]
    if wmul is not None:
        w = w * wmul
    p = d["passing"][mask & d["gen"]]
    sw, sw2 = w.sum(), (w**2).sum()
    if sw <= 0:
        return math.nan, math.nan
    e = (w * p).sum() / sw
    neff = sw**2 / sw2
    return e, math.sqrt(max(e * (1 - e), 1.0 / neff**2) / neff)


def measure(dd, dm, md, mm, bkg="exp", mrange=(M_LO, M_HI), wboot=None):
    """One bin: (eff_data, err, ok, par, eff_mc, err_mc). wboot: per-MC-pair multiplier (bootstrap)."""
    gp, gf = mm & dm["gen"] & dm["passing"], mm & dm["gen"] & ~dm["passing"]
    wp = dm["w"][gp] if wboot is None else dm["w"][gp] * wboot[gp]
    wf = dm["w"][gf] if wboot is None else dm["w"][gf] * wboot[gf]
    ed, eed, ok, par = fit_pass_fail(_hist(dd["m"][md & dd["passing"]], mrange=mrange),
                                     _hist(dd["m"][md & ~dd["passing"]], mrange=mrange),
                                     _hist(dm["m"][gp], wp, mrange), _hist(dm["m"][gf], wf, mrange), bkg, mrange)
    em, eem = mc_eff(dm, mm, None if wboot is None else wboot[mm & dm["gen"]])
    return ed, eed, ok, par, em, eem


# ---------------------------------------------------------------- POG and pileup
def load_pog(path, name):
    """correctionlib Correction, or raise (OSError/KeyError/ValueError)."""
    import correctionlib
    if not os.path.exists(path):
        raise OSError(f"{path} not found")
    cs = correctionlib.CorrectionSet.from_file(path)
    return cs[name]


def pog_sf(era, name, aeta, pt, var="nominal", path=None):
    return load_pog(path or f"{POG}/MUO/{era}/muon_Z.json.gz", name).evaluate(aeta, pt, var)


def pog_edges(era, name, path=None):
    import gzip
    path = path or f"{POG}/MUO/{era}/muon_Z.json.gz"
    d = json.load(gzip.open(path) if path.endswith(".gz") else open(path))
    c = next(c for c in d["corrections"] if c["name"] == name)
    node = c["data"]["content"]  # transform abs(eta) -> binning eta
    return node["edges"], node["content"][0]["edges"]


def load_pu(path):
    import correctionlib
    if not os.path.exists(path):
        raise OSError(f"{path} not found")
    return list(correctionlib.CorrectionSet.from_file(path).values())[0]


# ---------------------------------------------------------------- correctionlib output
def fill_plan(rows, n_eta, n_pt):
    """Which measured bin feeds each |eta| x pT bin of the correctionlib file.

    A bin that is unmeasured or not `reliable` takes the nearest reliable pT bin of the same |eta|
    row (ties: the lower pT bin) and gets an extra uncertainty `fill`: |raw value - source value|
    for an unreliable measured bin, |source - next-nearest reliable bin| for an unmeasured one (the
    source's total uncertainty if the row has one reliable bin). A row without any reliable bin
    gives SF 1 +- 1 and efficiencies 0.5 +- 0.5. Returns {(ieta, ipt): dict(src, reason, fill_*)}.
    """
    by = {(r["ieta"], r["ipt"]): r for r in rows}
    plan = {}
    for i in range(n_eta):
        good = [j for j in range(n_pt) if (i, j) in by and by[(i, j)]["reliable"]]
        for j in range(n_pt):
            r = by.get((i, j))
            if r is not None and r["reliable"]:
                plan[(i, j)] = dict(src=j, reason=None, fill_sf=0.0, fill_eff_data=0.0, fill_eff_mc=0.0)
                continue
            reason = "unmeasured" if r is None else "unreliable (" + ", ".join(r["unreliable_reasons"]) + ")"
            if not good:
                plan[(i, j)] = dict(src=None, reason=reason, fill_sf=1.0, fill_eff_data=0.5, fill_eff_mc=0.5)
                continue
            k = min(good, key=lambda g: (abs(g - j), g))
            src = by[(i, k)]
            ref = None
            if r is not None and all(math.isfinite(r[x]) for x in ("sf", "eff_data", "eff_mc")):
                ref = r
            else:
                others = [g for g in good if g != k]
                if others:
                    ref = by[(i, min(others, key=lambda g: (abs(g - j), g)))]
            if ref is not None:
                f = dict(fill_sf=abs(ref["sf"] - src["sf"]), fill_eff_data=abs(ref["eff_data"] - src["eff_data"]),
                         fill_eff_mc=abs(ref["eff_mc"] - src["eff_mc"]))
            else:
                f = dict(fill_sf=src["sf_total_err"], fill_eff_data=src["eff_data_total_err"],
                         fill_eff_mc=src["eff_mc_stat"])
            plan[(i, j)] = dict(src=k, reason=reason, **f)
    return plan


def correction_grids(rows, plan, n_eta, n_pt):
    """Arrays (n_eta, n_pt) of every correctionlib key, after filling (see fill_plan)."""
    by = {(r["ieta"], r["ipt"]): r for r in rows}
    keys = ("sf", "sf_stat", "sf_mc_stat", "sf_syst", "eff_data", "eff_data_stat", "eff_data_mc_stat",
            "eff_data_syst", "eff_mc", "eff_mc_stat")
    g = {k: np.zeros((n_eta, n_pt)) for k in keys + ("fill_sf", "fill_eff_data", "fill_eff_mc")}
    for (i, j), pl in plan.items():
        for k in ("fill_sf", "fill_eff_data", "fill_eff_mc"):
            g[k][i, j] = pl[k]
        if pl["src"] is None:
            g["sf"][i, j], g["eff_data"][i, j], g["eff_mc"][i, j] = 1.0, 0.5, 0.5
            continue
        src = by[(i, pl["src"])]
        for k in keys:
            g[k][i, j] = src[k]
    tot = np.sqrt(g["sf_stat"] ** 2 + g["sf_mc_stat"] ** 2 + g["sf_syst"] ** 2 + g["fill_sf"] ** 2)
    up, down = g["sf"] + tot, np.maximum(g["sf"] - tot, 0.0)
    sf = dict(nominal=g["sf"], up=up, down=down, systup=up, systdown=down, stat=g["sf_stat"],
              mc_stat=g["sf_mc_stat"], syst=g["sf_syst"], fill=g["fill_sf"])
    ted = np.sqrt(g["eff_data_stat"] ** 2 + g["eff_data_mc_stat"] ** 2 + g["eff_data_syst"] ** 2 + g["fill_eff_data"] ** 2)
    ed = dict(nominal=g["eff_data"], up=np.minimum(g["eff_data"] + ted, 1), down=np.maximum(g["eff_data"] - ted, 0),
              stat=g["eff_data_stat"], mc_stat=g["eff_data_mc_stat"], syst=g["eff_data_syst"], fill=g["fill_eff_data"])
    tem = np.hypot(g["eff_mc_stat"], g["fill_eff_mc"])
    em = dict(nominal=g["eff_mc"], up=np.minimum(g["eff_mc"] + tem, 1), down=np.maximum(g["eff_mc"] - tem, 0),
              stat=g["eff_mc_stat"], fill=g["fill_eff_mc"])
    return sf, ed, em


def write_correctionlib(path, name, rows, eta_edges, pt_edges, plan, description=""):
    """CorrectionSet (schema v2) with <name> (SF), <name>_eff_data and <name>_eff_mc.

    Inputs: abseta (abs taken inside, so eta works too), pt [GeV], scale_factors / valtype (string).
    SF keys: nominal, up, down (nominal +- total, down clipped at 0), systup / systdown (aliases of
    up / down, as in the POG files), and the uncertainties stat, mc_stat, syst, fill (not SFs);
    total = quadrature sum. Binning flow: clamp (values outside the edges are the edge bins'). Bins
    that are unmeasured or unreliable are filled as described in fill_plan() and listed in the
    correction descriptions.
    """
    import correctionlib.schemav2 as cs

    n_eta, n_pt = len(eta_edges) - 1, len(pt_edges) - 1
    edges_pt = [("inf" if math.isinf(e) else float(e)) for e in pt_edges]
    edges_eta = [float(e) for e in eta_edges]
    sf, ed, em = correction_grids(rows, plan, n_eta, n_pt)
    filled = [f"({i},{j})<-{'none' if pl['src'] is None else '(%d,%d)' % (i, pl['src'])} {pl['reason']}"
              for (i, j), pl in sorted(plan.items()) if pl["reason"]]
    fill_txt = (" Filled bins (|eta| index, pT index) <- source, reason: " + "; ".join(filled) + "."
                if filled else " No filled bins.")

    def mb(v):
        return cs.MultiBinning(nodetype="multibinning", inputs=["abseta", "pt"], edges=[edges_eta, edges_pt],
                               content=[float(x) for x in np.asarray(v).flatten()], flow="clamp")

    def corr(cname, desc, keyname, comps):
        cat = cs.Category(nodetype="category", input=keyname,
                          content=[cs.CategoryItem(key=k, value=mb(v)) for k, v in comps.items()])
        tr = cs.Transform(nodetype="transform", input="abseta",
                          rule=cs.Formula(nodetype="formula", expression="abs(x)", parser="TFormula",
                                          variables=["abseta"]),
                          content=cat)
        return cs.Correction(
            name=cname, description=desc + fill_txt, version=1,
            inputs=[cs.Variable(name="abseta", type="real", description="muon eta (abs taken inside, so |eta| or eta)"),
                    cs.Variable(name="pt", type="real", description="muon pT [GeV]"),
                    cs.Variable(name=keyname, type="string", description=", ".join(comps))],
            output=cs.Variable(name="weight", type="real"), data=tr)

    cset = cs.CorrectionSet(
        schema_version=2, description=description,
        corrections=[corr(name, f"data/MC scale factor, Z->mumu tag and probe. {description}. Values outside the "
                          "binning are clamped to the edge bins (extrapolation).", "scale_factors", sf),
                     corr(f"{name}_eff_data", "data efficiency (fit).", "valtype", ed),
                     corr(f"{name}_eff_mc", "MC efficiency (counting, gen-matched).", "valtype", em)])
    text = cset.model_dump_json(exclude_unset=True, indent=1)
    if path.endswith(".gz"):
        import gzip
        with gzip.open(path, "wt") as f:
            f.write(text)
    else:
        with open(path, "w") as f:
            f.write(text + "\n")


# ---------------------------------------------------------------- main
def _warn(msg, warnings):
    warnings.append(msg)
    print(f"warning: {msg}", file=sys.stderr)


def _floats(xs):
    return [math.inf if str(x).lower() in ("inf", "+inf") else float(x) for x in xs]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    g = ap.add_argument_group("inputs")
    g.add_argument("--data", nargs="+", required=True, help="data NanoAOD files (local or root://)")
    g.add_argument("--mc", nargs="+", required=True, help="DY MC NanoAOD files")
    g.add_argument("--max-events", type=int, default=0, help="per sample; 0 = all")
    g.add_argument("--lumi-mask", help="certification JSON (golden JSON) applied to data; default: no mask")
    g = ap.add_argument_group("working point (explicit options override the --wp preset)")
    g.add_argument("--wp", choices=sorted(WPS), default=None,
                   help="preset; default tightid if none of --den/--num/--num-trigger is given")
    g.add_argument("--den", help="probe denominator expression, e.g. isTracker or 'tightId & (pfRelIso04_all < 0.15)'")
    g.add_argument("--num", help="numerator expression, e.g. mediumId, 'highPtId == 2', 'tkRelIso < 0.1'")
    g.add_argument("--num-trigger", help="numerator trigger match BITS:PTMIN[:DRMAX], e.g. 2:24 (IsoMu24), 1:17 (Mu17 leg)")
    g.add_argument("--tag", default=TAG, help=f"tag expression (default: {TAG})")
    g.add_argument("--tag-pt", type=float, default=29.0, help="tag pT threshold, GeV (default 29)")
    g.add_argument("--tag-trigger", default="2:24", help="tag trigger match BITS:PTMIN[:DRMAX] or none (default 2:24)")
    g.add_argument("--tag-hlt", default=TAG_HLT, help=f"event must fire one of these comma-separated paths, or none (default {TAG_HLT})")
    g = ap.add_argument_group("binning and POG")
    g.add_argument("--era", default="2016postVFP_UL", help="POG directory name, e.g. 2016postVFP_UL")
    g.add_argument("--pog", help="POG correction name in muon_Z.json.gz to compare with (default: the preset's)")
    g.add_argument("--pog-json", help="POG muon JSON (default <jsonpog>/MUO/<era>/muon_Z.json.gz on cvmfs)")
    g.add_argument("--pu-json", help="LUM pileup JSON (default <jsonpog>/LUM/<era>/puWeights.json.gz on cvmfs)")
    g.add_argument("--no-pog", action="store_true", help="no POG comparison (offline)")
    g.add_argument("--no-pu", action="store_true", help="no pileup weights (offline)")
    g.add_argument("--eta-edges", nargs="+", help="|eta| edges (default: from --pog, else the preset, else 0 0.9 1.2 2.1 2.4)")
    g.add_argument("--pt-edges", nargs="+", help="pT edges in GeV, last may be inf (default: from --pog, else preset)")
    g = ap.add_argument_group("uncertainties")
    g.add_argument("--mc-replicas", type=int, default=50, help="Poisson bootstrap replicas of the MC for mc_stat (0 = off)")
    g.add_argument("--seed", type=int, default=12345, help="bootstrap seed")
    g.add_argument("--syst", dest="syst", action="store_const", const=True, default=None,
                   help="background (exp vs Bernstein poly2), window (75-110 GeV), tag (pT+4 GeV, iso<0.05); "
                        "on by default with --correctionlib")
    g.add_argument("--no-syst", dest="syst", action="store_const", const=False, help="no systematics, even with --correctionlib")
    g.add_argument("--min-fail", type=float, default=5,
                   help="a bin is unreliable if the data or gen-matched MC fail category has fewer probes (default 5)")
    g.add_argument("--max-sf-stat", type=float, default=0.1,
                   help="a bin is unreliable if the SF data-stat error is larger (default 0.1); unreliable and "
                        "failed-fit bins are filled from a neighbour in the correctionlib file")
    g = ap.add_argument_group("outputs")
    g.add_argument("--out", default="tnp.json", help="result JSON")
    g.add_argument("--correctionlib", default="", help="write a correctionlib JSON (.json or .json.gz)")
    g.add_argument("--name", help="correction name (default: preset name, else muon_sf)")
    g.add_argument("--plots", default="", help="directory for per-bin fit plots (optional)")
    g.add_argument("--dry-run", action="store_true", help="check arguments and branches, print the plan, read and write nothing")
    a = ap.parse_args(argv)

    warnings: list[str] = []
    if a.correctionlib and os.path.abspath(a.correctionlib) == os.path.abspath(a.out):
        print("error: --correctionlib and --out are the same file", file=sys.stderr)
        return 2
    if a.wp is None and a.num is None and a.num_trigger is None:
        if a.den is not None:
            print("error: --den needs a numerator: give --num, --num-trigger or --wp", file=sys.stderr)
            return 2
        a.wp = "tightid"
    if a.syst is None:
        a.syst = bool(a.correctionlib)
    if not a.syst:
        _warn("no systematics: sf_total_err and up/down contain stat and mc_stat only (use --syst)", warnings)
    lumi = None
    if a.lumi_mask:
        try:
            lumi = load_lumi_mask(a.lumi_mask)
        except (OSError, ValueError) as e:
            print(f"error: cannot read --lumi-mask: {e}", file=sys.stderr)
            return 2
    try:
        sel = make_selection(a.wp, a.num, a.den, a.num_trigger, a.tag, a.tag_pt, a.tag_trigger, a.tag_hlt)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        return 2
    custom = a.wp is None or any(x is not None for x in (a.num, a.den, a.num_trigger))
    pog_name = a.pog if a.pog else (WPS[a.wp]["pog"] if a.wp and not custom else None)
    name = a.name or (a.wp if a.wp and not custom else "muon_sf")
    pog_path = a.pog_json or f"{POG}/MUO/{a.era}/muon_Z.json.gz"
    pu_path = a.pu_json or f"{POG}/LUM/{a.era}/puWeights.json.gz"

    pog = None
    if a.no_pog or not pog_name:
        if not pog_name and not a.no_pog:
            print("info: no --pog correction given; no POG comparison", file=sys.stderr)
        else:
            _warn("POG comparison disabled (--no-pog)", warnings)
    else:
        try:
            pog = load_pog(pog_path, pog_name)
        except Exception as e:  # noqa: BLE001 - any failure to read means offline
            _warn(f"POG correction {pog_name} unavailable ({type(e).__name__}: {e}); no POG comparison", warnings)
    puw = None
    if a.no_pu:
        _warn("pileup weights disabled (--no-pu)", warnings)
    elif not a.dry_run:
        try:
            puw = load_pu(pu_path)
        except Exception as e:  # noqa: BLE001
            _warn(f"pileup JSON unavailable ({type(e).__name__}: {e}); MC not pileup-weighted", warnings)

    # binning: explicit > POG correction > preset > generic default
    eta_edges = pt_edges = None
    src = "explicit"
    if pog is not None and not (a.eta_edges and a.pt_edges):
        try:
            eta_edges, pt_edges = pog_edges(a.era, pog_name, pog_path)
            src = "POG"
        except Exception as e:  # noqa: BLE001
            _warn(f"cannot read the POG binning ({e})", warnings)
    if eta_edges is None:
        eta_edges, src = ETA_EDGES, "default"
        pt_edges = WPS[a.wp]["pt_edges"] if a.wp else PT_EDGES
        if not (a.eta_edges and a.pt_edges):
            msg = f"binning from the {'preset ' + a.wp if a.wp else 'generic default'} (no POG binning)"
            print(f"info: {msg}", file=sys.stderr)
    try:
        if a.eta_edges:
            eta_edges = _floats(a.eta_edges)
        if a.pt_edges:
            pt_edges = _floats(a.pt_edges)
    except ValueError as e:
        print(f"error: bad edges: {e}", file=sys.stderr)
        return 2
    if a.eta_edges and a.pt_edges:
        src = "explicit"
    eta_edges, pt_edges = _floats(eta_edges), _floats(pt_edges)
    if any(np.diff(eta_edges) <= 0) or any(np.diff(pt_edges) <= 0) or eta_edges[0] < 0:
        print("error: edges must increase and |eta| edges be >= 0", file=sys.stderr)
        return 2
    sel["probe_pt_min"] = min(15.0, pt_edges[0])

    definition = dict(den=sel["den"].text, num=sel["num"].text if sel["num"] else None,
                      num_trigger=a.num_trigger if a.num_trigger is not None else (WPS[a.wp]["num_trigger"] if a.wp else None),
                      tag=sel["tag"].text, tag_pt=sel["tag_pt"], tag_trigger=a.tag_trigger, tag_hlt=sel["tag_hlt"],
                      probe_pt_min=sel["probe_pt_min"], mass_window_GeV=[M_LO, M_HI])
    if a.dry_run:
        print(f"definition: {json.dumps(definition)}", file=sys.stderr)
        print(f"binning ({src}): |eta| {eta_edges}  pT {pt_edges}", file=sys.stderr)
        try:  # branches, then every expression and trigger match on the first 200 events of each sample
            for f, is_mc in ((a.data[0], False), (a.mc[0], True)):
                br = branches_for(sel, is_mc, lumi is not None)
                check_branches(f, br)
                ev = uproot.open(f"{f}:Events").arrays(br, entry_stop=200)
                if is_mc:
                    ev["puw"] = np.ones(len(ev))
                tnp_pairs(ev, sel, is_mc)
        except (OSError, KeyError, ValueError, TypeError) as e:
            print(f"error: {e}", file=sys.stderr)
            return 2
        print(f"DRY_RUN=1\nNAME={name}\nPOG={pog_name if pog is not None else 'unavailable'}\n"
              f"N_BINS_PLANNED={(len(eta_edges) - 1) * (len(pt_edges) - 1)}\nOUT={a.out}\nCORRECTIONLIB={a.correctionlib}")
        return 0

    try:
        lstats = {}
        dd, nd = read(a.data, sel, False, None, a.max_events, lumi_mask=lumi, stats=lstats)
        dm, nm = read(a.mc, sel, True, puw, a.max_events)
    except (OSError, KeyError, ValueError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    rng = np.random.default_rng(a.seed)
    boot = None
    if a.mc_replicas > 0:
        _, inv = np.unique(dm["evt"], return_inverse=True)
        boot = rng.poisson(1.0, size=(a.mc_replicas, inv.max() + 1)).astype(np.float64)
    tag_tight = (dd["tpt"] > sel["tag_pt"] + 4), (dm["tpt"] > sel["tag_pt"] + 4)
    tag_iso = (dd["tiso"] < 0.05), (dm["tiso"] < 0.05)
    win = (dd["m"] > 75) & (dd["m"] < 110), (dm["m"] > 75) & (dm["m"] < 110)

    rows, nfail = [], 0
    for i in range(len(eta_edges) - 1):
        for j in range(len(pt_edges) - 1):
            lo, hi = pt_edges[j], min(pt_edges[j + 1], 1e4)
            md = (dd["aeta"] >= eta_edges[i]) & (dd["aeta"] < eta_edges[i + 1]) & (dd["pt"] >= lo) & (dd["pt"] < hi)
            mm = (dm["aeta"] >= eta_edges[i]) & (dm["aeta"] < eta_edges[i + 1]) & (dm["pt"] >= lo) & (dm["pt"] < hi)
            if md.sum() < 50 or (mm & dm["gen"]).sum() < 50:
                continue
            ed, eed, ok, par, em, eem = measure(dd, dm, md, mm)
            sf = ed / em
            esf = sf * math.hypot(eed / ed, eem / em) if ed > 0 else math.nan
            ptc = 0.5 * (lo + min(hi, 2 * lo))
            aetac = 0.5 * (eta_edges[i] + eta_edges[i + 1])
            pogv = pog_unc = pull = None
            if pog is not None:
                try:
                    pogv = pog.evaluate(aetac, ptc, "nominal")
                    pog_unc = pog.evaluate(aetac, ptc, "systup") - pogv
                    pull = (sf - pogv) / math.hypot(esf, pog_unc)
                except Exception:  # noqa: BLE001 - bin outside the POG range
                    pogv = pog_unc = pull = None
            nfail += not ok
            row = dict(aeta=[eta_edges[i], eta_edges[i + 1]], pt=[lo, pt_edges[j + 1]], n_data=int(md.sum()),
                       eff_data=ed, eff_data_err=eed, eff_mc=em, eff_mc_err=eem, sf=sf, sf_err=esf,
                       pog_sf=pogv, pog_unc=pog_unc, pull=pull, fit_ok=ok)

            # uncertainty components (SF units unless eff_*)
            sf_stat = sf * eed / ed if ed > 0 else math.nan
            mcs = dict(sf=math.nan, ed=math.nan, em=eem, n_ok=0, method="counting")
            if boot is not None:
                # restrict to the bin first (same result, much faster than full-length masks)
                ddb = {k: v[md] for k, v in dd.items()}
                dmb = {k: v[mm] for k, v in dm.items()}
                allb, allm, invb = np.ones(len(ddb["m"]), bool), np.ones(len(dmb["m"]), bool), inv[mm]
                reps = []
                for r in range(a.mc_replicas):
                    edr, _, _, parr, emr, _ = measure(ddb, dmb, allb, allm, wboot=boot[r][invb])
                    if parr["migrad_valid"] and emr > 0:  # the central value is needed, not HESSE
                        reps.append((edr / emr, edr, emr))
                if len(reps) >= 5:
                    rp = np.array(reps)
                    mcs = dict(sf=float(rp[:, 0].std(ddof=1)), ed=float(rp[:, 1].std(ddof=1)),
                               em=float(rp[:, 2].std(ddof=1)), n_ok=len(reps),
                               method="bootstrap")
                else:
                    _warn(f"bin |eta| {eta_edges[i]}-{eta_edges[i+1]} pt {lo}-{pt_edges[j+1]}: only {len(reps)} "
                          f"bootstrap fits have a valid minimum; mc_stat from MC counting only", warnings)
            if mcs["method"] == "counting":
                mcs["sf"] = sf * eem / em
                mcs["ed"] = 0.0
            comps, ecomps = {}, {}
            if a.syst:
                for cname, kw, cut in (("bkg", dict(bkg="poly2"), None),
                                       ("window", dict(mrange=(75.0, 110.0)), win),
                                       ("tag_pt", {}, tag_tight), ("tag_iso", {}, tag_iso)):
                    mdv, mmv = (md, mm) if cut is None else (md & cut[0], mm & cut[1])
                    edv, _, _, parv, emv, _ = measure(dd, dm, mdv, mmv, **kw)
                    if not parv["migrad_valid"]:  # the central value is needed, not HESSE
                        _warn(f"syst {cname} fit has no valid minimum in |eta| {eta_edges[i]}-{eta_edges[i+1]} pt {lo}-{pt_edges[j+1]}", warnings)
                    comps[cname] = abs(edv / emv - sf)
                    ecomps[cname] = abs(edv - ed)
                comps["tag"] = max(comps.pop("tag_pt"), comps.pop("tag_iso"))
                ecomps["tag"] = max(ecomps.pop("tag_pt"), ecomps.pop("tag_iso"))
            sf_syst = math.sqrt(sum(v**2 for v in comps.values()))
            ed_syst = math.sqrt(sum(v**2 for v in ecomps.values()))
            tot = math.sqrt(sf_stat**2 + mcs["sf"]**2 + sf_syst**2)
            n_fail_d, n_fail_m = int((md & ~dd["passing"]).sum()), int((mm & dm["gen"] & ~dm["passing"]).sum())
            why = [w for w, bad in (("fit not ok", not ok), (f"data fail < {a.min_fail:g}", n_fail_d < a.min_fail),
                                    (f"MC fail < {a.min_fail:g}", n_fail_m < a.min_fail),
                                    (f"sf_stat > {a.max_sf_stat:g}", not sf_stat <= a.max_sf_stat)) if bad]
            row.update(reliable=not why, unreliable_reasons=why, n_fail_data=n_fail_d, n_fail_mc=n_fail_m)
            row.update(ieta=i, ipt=j, sf_stat=sf_stat, sf_mc_stat=mcs["sf"], sf_syst=sf_syst,
                       sf_syst_components=comps or None, sf_total_err=tot,
                       eff_data_stat=eed, eff_data_mc_stat=mcs["ed"], eff_data_syst=ed_syst,
                       eff_data_total_err=math.sqrt(eed**2 + mcs["ed"]**2 + ed_syst**2),
                       eff_mc_stat=mcs["em"], mc_stat_method=mcs["method"], mc_stat_replicas_ok=mcs["n_ok"],
                       n_mc_gen=int((mm & dm["gen"]).sum()),
                       pull_total=(sf - pogv) / math.hypot(tot, pog_unc) if pogv is not None else None)
            rows.append(row)
            pog_txt = f"POG {pogv:.4f}+-{pog_unc:.4f} pull {pull:+.2f}" if pogv is not None else "POG n/a"
            print(f"|eta| {eta_edges[i]:.1f}-{eta_edges[i+1]:.1f} pt {lo:.0f}-{pt_edges[j+1]:.0f}: "
                  f"eff data {ed:.4f}+-{eed:.4f} mc {em:.4f}+-{eem:.4f} SF {sf:.4f}+-{esf:.4f} "
                  f"{pog_txt}{'' if ok else ' FIT-NOT-OK'} | stat {sf_stat:.4f} mc_stat {mcs['sf']:.4f} "
                  f"syst {sf_syst:.4f} total {tot:.4f}")
            if a.plots:
                _plot(a.plots, name, i, j, dd, dm, md, mm, par, rows[-1])

    if not rows:
        print("error: no bin has >= 50 data and 50 gen-matched MC probes", file=sys.stderr)
        return 2
    pulls = np.array([r["pull"] for r in rows if r["pull"] is not None and math.isfinite(r["pull"])])
    pullt = np.array([r["pull_total"] for r in rows if r["pull_total"] is not None and math.isfinite(r["pull_total"])])
    filled = [[i, j] for i in range(len(eta_edges) - 1) for j in range(len(pt_edges) - 1)
              if not any(r["ieta"] == i and r["ipt"] == j for r in rows)]
    if filled:
        _warn(f"{len(filled)} bins without a measurement (|eta|, pT indices {filled}); the correctionlib "
              f"file takes the nearest reliable pT bin of the same |eta| row", warnings)
    unrel = [[r["ieta"], r["ipt"], r["unreliable_reasons"]] for r in rows if not r["reliable"]]
    if unrel:
        _warn(f"{len(unrel)} unreliable bins ({unrel}); raw values kept in bins[], the correctionlib file "
              f"takes the nearest reliable pT bin with an extra 'fill' uncertainty", warnings)
    plan = fill_plan(rows, len(eta_edges) - 1, len(pt_edges) - 1)
    filled_bins = [dict(ieta=i, ipt=j, src_ipt=pl["src"], reason=pl["reason"], fill_sf=pl["fill_sf"],
                        fill_eff_data=pl["fill_eff_data"], fill_eff_mc=pl["fill_eff_mc"])
                   for (i, j), pl in sorted(plan.items()) if pl["reason"]]
    res = dict(wp=a.wp if not custom else None, name=name, era=a.era, definition=definition,
               pog_correction=pog_name, pog_available=pog is not None, pileup_weights=puw is not None,
               binning_source=src, eta_edges=eta_edges, pt_edges=pt_edges,
               mc_replicas=a.mc_replicas, seed=a.seed, syst=a.syst,
               reliability=dict(min_fail=a.min_fail, max_sf_stat=a.max_sf_stat),
               lumi_mask=os.path.basename(a.lumi_mask) if a.lumi_mask else None,
               n_events_data_in_lumi_mask=lstats.get("n_in_mask") if lumi is not None else None,
               n_events_data=nd, n_events_mc=nm, n_pairs_data=int(len(dd["m"])), n_pairs_mc=int(len(dm["m"])),
               mass_window_GeV=[M_LO, M_HI], bins=rows, unmeasured_bins=filled, correctionlib_filled_bins=filled_bins,
               warnings=warnings,
               mean_pull=float(pulls.mean()) if len(pulls) else None,
               rms_pull=float(np.sqrt((pulls**2).mean())) if len(pulls) else None,
               mean_pull_total=float(pullt.mean()) if len(pullt) else None,
               rms_pull_total=float(np.sqrt((pullt**2).mean())) if len(pullt) else None)
    with open(a.out, "w") as f:
        json.dump(res, f, indent=1)
    if a.correctionlib:
        desc = (f"num={definition['num']} num_trigger={definition['num_trigger']} den={definition['den']} "
                f"tag={definition['tag']} pT>{sel['tag_pt']} trigger={a.tag_trigger} hlt={','.join(sel['tag_hlt'])}; "
                f"pileup weights {'on' if puw is not None else 'off'}")
        write_correctionlib(a.correctionlib, name, rows, eta_edges, pt_edges, plan,
                            desc + f"; systematics {'on' if a.syst else 'OFF'}")
    print(f"N_BINS={len(rows)}")
    print(f"N_FIT_FAILED={nfail}")
    print(f"MEAN_PULL={res['mean_pull']}")
    print(f"RMS_PULL={res['rms_pull']}")
    print(f"MEAN_PULL_TOTAL={res['mean_pull_total']}")
    print(f"RMS_PULL_TOTAL={res['rms_pull_total']}")
    print(f"POG={pog_name if pog is not None else 'unavailable'}")
    print(f"PILEUP={'on' if puw is not None else 'off'}")
    print(f"CORRECTIONLIB={a.correctionlib}")
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
