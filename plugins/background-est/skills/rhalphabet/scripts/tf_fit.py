#!/usr/bin/env python3
"""Rhalphabet transfer factor fits without Combine (numpy + scipy + iminuit).

QCD_pass(pT, m) = R(pT, rho) * QCD_fail(pT, m),   rho = 2 ln(m / pT)

Two steps (the default; --no-mc gives the single-step version):
  1. `mc`:   R_MC(pT, rho) = Bernstein polynomial fitted to the QCD-MC pass/fail
             ratio (weighted least squares, coefficients >= 0, analytic F-test
             between orders because the MC is weighted).
  2. `data`: R = R_MC x TF_res(pT, rho), TF_res a low-order Bernstein fitted to
             data. Every fail bin has its own free QCD yield q, profiled
             exactly (Poisson pass + fail likelihood per bin), so the fail data
             uncertainty reaches the pass prediction. Resonant backgrounds
             (W, Z, top, H, ...) enter as fixed MC templates. With --float-mc
             the MC coefficients float with a Gaussian constraint from step 1.
  `ftest`, `gof`: toy F-test between two residual orders (toys generated from
             the lower order) and saturated goodness of fit with toys.
  `loo`:     leave-one-pT-bin-out validation: refit with the pass region of one
             pT bin removed and predict its pass yield (interpolation test).
  `data --pseudo-data`: closure of the full procedure on QCD MC; give a
             histogram file built from events NOT used for `mc` (e.g. odd events).

Deviance: "deviance" is the Poisson deviance of pass + fail bins with the fail
QCD yield profiled per bin; "ndof" = unmasked pass bins - residual parameters
(the fail bins are fitted by their own yields). F-test and GoF use this total.
"dev_pass" alone is what to compare with the pass-bin count.

Input histograms: a .npz or .json with
  ptbins (npt+1), msdbins (nm+1)                          GeV
  data_pass, data_fail                                    (npt, nm) counts
  qcd_pass, qcd_fail, qcd_pass_w2, qcd_fail_w2            (npt, nm) QCD MC sum w, sum w^2
  res_pass, res_fail          optional                    (npt, nm) sum of non-QCD MC
  res_<proc>_pass/_fail       optional                    (npt, nm) per process, for the
                                                          resonant-fraction report
  ptmean                      optional, recommended       (npt,) QCD-weighted mean pT per bin

The rho range (--rho LO HI) defines which bins are used: rho is evaluated at
(ptmean, msd bin centre); bins outside are masked in pass AND fail.
--blind LO HI (repeatable) masks a msd window in PASS only.

Examples:
  python tf_fit.py mc    --hists h.npz --rho LO HI --max-order 3 3 --out mc.json
  python tf_fit.py data  --hists h.npz --rho LO HI --mc mc.json --mc-order 1 2 --order 0 1 --out fit.json
  python tf_fit.py ftest --hists h.npz --rho LO HI --mc mc.json --mc-order 1 2 --lo 0 0 --hi 0 1 --toys 200
  python tf_fit.py gof   --hists h.npz --rho LO HI --mc mc.json --mc-order 1 2 --order 0 1 --toys 500
  python tf_fit.py loo   --hists h.npz --rho LO HI --mc mc.json --mc-order 1 2 --order 0 1 --blind 100 150
  python tf_fit.py data  --hists h_odd.npz --pseudo-data --rho LO HI --mc mc_even.json --mc-order 1 2 --order 0 1
Every command writes JSON (--out) and prints a one-line summary.
"""
import argparse
import json
import sys
from math import comb

import numpy as np

# ----------------------------------------------------------------------------- geometry


def load_hists(path):
    if path.endswith(".npz"):
        z = np.load(path)
        h = {k: np.asarray(z[k], float) for k in z.files}
    else:
        with open(path) as f:
            h = {k: np.asarray(v, float) for k, v in json.load(f).items()}
    npt, nm = len(h["ptbins"]) - 1, len(h["msdbins"]) - 1
    for k in ("data_pass", "data_fail", "qcd_pass", "qcd_fail", "qcd_pass_w2", "qcd_fail_w2"):
        if k not in h:
            raise KeyError(f"missing '{k}' in {path}")
        if h[k].shape != (npt, nm):
            raise ValueError(f"'{k}' has shape {h[k].shape}, expected {(npt, nm)}")
    for k in ("res_pass", "res_fail"):
        h.setdefault(k, np.zeros((npt, nm)))
    if "ptmean" not in h:
        print("WARNING: no ptmean given; using pT bin centres (use the QCD-weighted mean)", file=sys.stderr)
        h["ptmean"] = 0.5 * (h["ptbins"][1:] + h["ptbins"][:-1])
    return h


class Geometry:
    """Scaled (pT, rho) per bin and the masks."""

    def __init__(self, h, rho_lo, rho_hi, blind=()):
        pb, mb = h["ptbins"], h["msdbins"]
        self.ptbins, self.msdbins = pb, mb
        self.mcen = 0.5 * (mb[1:] + mb[:-1])
        ptm = np.asarray(h["ptmean"], float)
        if np.any(ptm < pb[0]) or np.any(ptm > pb[-1]):
            raise ValueError("ptmean outside the pT bin range")
        pt, m = np.meshgrid(ptm, self.mcen, indexing="ij")
        self.rho = 2 * np.log(m / pt)
        self.ptsc = (pt - pb[0]) / (pb[-1] - pb[0])
        rs = (self.rho - rho_lo) / (rho_hi - rho_lo)
        self.valid = (rs >= 0) & (rs <= 1)
        self.rhosc = np.clip(rs, 0, 1)
        self.rho_lo, self.rho_hi = rho_lo, rho_hi
        win = np.zeros_like(self.valid)
        for lo, hi in blind:
            win |= (self.mcen >= lo) & (self.mcen < hi)
        self.blind = list(blind)
        self.use_fail = self.valid
        self.use_pass = self.valid & ~win


def bernstein(order, x):
    """(len(x), order+1) Bernstein basis on [0, 1]."""
    x = np.asarray(x, float)
    return np.stack([comb(order, i) * x**i * (1 - x) ** (order - i) for i in range(order + 1)], axis=-1)


def design(geo, order):
    """(npt, nm, k) tensor-product Bernstein design matrix; params ordered [i_pt, j_rho]."""
    bp = bernstein(order[0], geo.ptsc)
    br = bernstein(order[1], geo.rhosc)
    return np.einsum("...i,...j->...ij", bp, br).reshape(geo.ptsc.shape + (-1,))


# ----------------------------------------------------------------------------- step 1: QCD MC


def fit_mc(h, geo, order):
    from scipy.optimize import lsq_linear

    p, f, p2, f2 = h["qcd_pass"], h["qcd_fail"], h["qcd_pass_w2"], h["qcd_fail_w2"]
    use = geo.valid & (p > 0) & (f > 0)
    with np.errstate(divide="ignore", invalid="ignore"):
        R = p / f
        var = R**2 * (p2 / p**2 + f2 / f**2)
    A = design(geo, order)
    Au, Ru, su = A[use], R[use], np.sqrt(var[use])
    res = lsq_linear(Au / su[:, None], Ru / su, bounds=(0, np.inf))
    c = res.x
    W = Au / su[:, None]
    cov = np.linalg.pinv(W.T @ W)
    chi2 = float(np.sum(((Ru - Au @ c) / su) ** 2))
    n, k = int(use.sum()), len(c)
    at_bound = int(np.sum(c <= 1e-12))
    return {"order": list(order), "coef": c.tolist(), "cov": cov.tolist(), "chi2": chi2,
            "nbins": n, "npar": k, "ndof": n - k, "n_coef_at_zero": at_bound,
            "n_bins_skipped_empty": int((geo.valid & ~use).sum()),
            "R_mc": (A @ c).tolist()}


def scan_mc(h, geo, max_order):
    from scipy.stats import f as fdist

    fits = {}
    for a in range(max_order[0] + 1):
        for b in range(max_order[1] + 1):
            fits[(a, b)] = fit_mc(h, geo, (a, b))
    tests = []
    for (a, b), lo in fits.items():
        for hi_o in ((a + 1, b), (a, b + 1)):
            if hi_o not in fits:
                continue
            hi = fits[hi_o]
            dk = hi["npar"] - lo["npar"]
            F = ((lo["chi2"] - hi["chi2"]) / dk) / (hi["chi2"] / hi["ndof"])
            tests.append({"lo": [a, b], "hi": list(hi_o), "F": F,
                          "p_analytic": float(fdist.sf(F, dk, hi["ndof"]))})
    # sequential choice from (0, 0): move to the better significant neighbour; raise rho on a tie
    cur = (0, 0)
    while True:
        cand = [t for t in tests if tuple(t["lo"]) == cur and t["p_analytic"] < 0.05]
        if not cand:
            break
        cand.sort(key=lambda t: (t["p_analytic"], -t["hi"][1]))
        cur = tuple(cand[0]["hi"])
    return fits, tests, cur


# ----------------------------------------------------------------------------- step 2: data


def _profile_q(nf, rf, npass, rp, R, inc):
    """Per-bin MLE of the fail QCD yield q >= 0 (vectorised bisection; the score is decreasing in q)."""
    Ri = R * inc

    def g(q):
        return nf / (q + rf) + Ri * npass / (Ri * q + rp + (1 - inc)) - (1 + Ri)

    lo = np.full_like(nf, 1e-9)
    hi = (nf + inc * npass) / (1 + Ri) + 1.0
    pos = g(lo) > 0
    for _ in range(80):
        mid = 0.5 * (lo + hi)
        gm = g(mid)
        lo = np.where(gm > 0, mid, lo)
        hi = np.where(gm > 0, hi, mid)
    return np.where(pos, 0.5 * (lo + hi), 1e-9)


def _dev_terms(n, mu):
    with np.errstate(divide="ignore", invalid="ignore"):
        t = mu - n + np.where(n > 0, n * np.log(n / mu), 0.0)
    return 2 * t


class DataModel:
    def __init__(self, h, geo, order, mc=None, float_mc=False, dp=None, df=None):
        self.geo, self.order = geo, tuple(order)
        self.dp = h["data_pass"] if dp is None else dp
        self.df = h["data_fail"] if df is None else df
        self.rp, self.rf = h["res_pass"], h["res_fail"]
        self.Ares = design(geo, order)
        self.k_res = self.Ares.shape[-1]
        self.mc = mc
        self.float_mc = bool(mc is not None and float_mc)
        if mc is not None:
            self.Amc = design(geo, mc["order"])
            self.c_mc0 = np.asarray(mc["coef"])
            self.cov_mc = np.asarray(mc["cov"])
            self.base0 = self.Amc @ self.c_mc0
            if self.float_mc:
                self.icov_mc = np.linalg.pinv(self.cov_mc)
        else:
            self.base0 = np.ones(geo.valid.shape)
        v = geo.use_fail
        npass = np.where(geo.use_pass, self.dp, 0).sum() - np.where(geo.use_pass, self.rp, 0).sum()
        nfail_base = np.sum(np.where(geo.use_pass, (self.df - self.rf) * self.base0, 0))
        self.scale = max(npass, 1.0) / max(nfail_base, 1.0)
        self.f, self.inc = v, geo.use_pass.astype(float)

    def npar(self):
        return self.k_res + (len(self.c_mc0) if self.float_mc else 0)

    def R(self, x):
        c_res = x[: self.k_res]
        base = self.Amc @ x[self.k_res:] if self.float_mc else self.base0
        return self.scale * base * (self.Ares @ c_res)

    def profile(self, x):
        R = np.clip(self.R(x), 1e-12, None)
        v = self.f
        q = np.zeros_like(R)
        q[v] = _profile_q(self.df[v], self.rf[v], self.dp[v], self.rp[v], R[v], self.inc[v])
        return R, q

    def deviance(self, x, split=False):
        R, q = self.profile(x)
        v, vp = self.f, self.geo.use_pass
        dfail = _dev_terms(self.df[v], q[v] + self.rf[v]).sum()
        dpass = _dev_terms(self.dp[vp], R[vp] * q[vp] + self.rp[vp]).sum()
        pen = 0.0
        if self.float_mc:
            d = x[self.k_res:] - self.c_mc0
            pen = float(d @ self.icov_mc @ d)
        if split:
            return dpass, dfail, pen
        return dpass + dfail + pen

    def fit(self, x0=None, hesse=True):
        from iminuit import Minuit

        x0 = np.ones(self.npar()) if x0 is None else np.asarray(x0, float)
        if self.float_mc:
            x0[self.k_res:] = self.c_mc0
        m = Minuit(lambda x: 0.5 * self.deviance(x), x0)
        m.errordef = Minuit.LIKELIHOOD
        m.limits = [(0, 10)] * self.k_res + [(None, None)] * (self.npar() - self.k_res)
        m.strategy = 1
        m.migrad()
        if hesse:
            m.hesse()
        x = np.array(m.values)
        dpass, dfail, pen = self.deviance(x, split=True)
        npass = int(self.geo.use_pass.sum())
        err = np.array(m.errors)
        cov = np.array(m.covariance) if (hesse and m.covariance is not None) else None
        near = [i for i in range(self.k_res) if x[i] - err[i] < 0 or x[i] + err[i] > 10]
        return {"x": x, "cov": cov, "valid": bool(m.valid), "edm": float(m.fmin.edm),
                "deviance": float(dpass + dfail), "dev_pass": float(dpass), "dev_fail": float(dfail),
                "npass_bins": npass, "npar": self.npar(), "ndof": npass - self.k_res,
                "params_within_1sigma_of_limit": near}

    def expectation(self, x):
        R, q = self.profile(x)
        return R * q + self.rp, q + self.rf, R, q


def toys_from(model, fitres, ntoys, seed):
    rng = np.random.default_rng(seed)
    mp, mf, _, _ = model.expectation(fitres["x"])
    for _ in range(ntoys):
        yield rng.poisson(np.where(model.geo.use_pass, mp, 0)).astype(float), \
            rng.poisson(np.where(model.geo.use_fail, mf, 0)).astype(float)


def band_and_projection(model, fitres, nsample=500, seed=7):
    """TF band (16/84 %) per bin and the pT-summed pass/fail ratio of fitted QCD vs msd."""
    rng = np.random.default_rng(seed)
    x = fitres["x"]
    R, q = model.profile(x)
    v = model.geo.use_fail
    samples = []
    if fitres["cov"] is not None:
        xs = rng.multivariate_normal(x, fitres["cov"], size=nsample)
        for xi in xs:
            xi = xi.copy()
            xi[: model.k_res] = np.clip(xi[: model.k_res], 0, None)
            Ri = model.R(xi)
            if model.mc is not None and not model.float_mc:
                cm = rng.multivariate_normal(model.c_mc0, model.cov_mc)
                Ri = Ri / model.base0 * (model.Amc @ cm)
            samples.append(Ri)
    samples = np.array(samples) if samples else None
    num = np.where(v, R * q, 0).sum(0)
    den = np.where(v, q, 0).sum(0)
    with np.errstate(divide="ignore", invalid="ignore"):
        proj = num / den
    out = {"msd_centres": model.geo.mcen.tolist(), "R_pf_vs_msd": np.nan_to_num(proj, nan=-1).tolist(),
           "R": R.tolist(), "q_fail": q.tolist()}
    if samples is not None:
        lo, hi = np.percentile(samples, [16, 84], axis=0)
        ps = np.array([np.where(v, s * q, 0).sum(0) for s in samples]) / np.where(den > 0, den, 1)
        plo, phi = np.percentile(ps, [16, 84], axis=0)
        out.update({"R_lo": lo.tolist(), "R_hi": hi.tolist(),
                    "R_pf_vs_msd_lo": plo.tolist(), "R_pf_vs_msd_hi": phi.tolist()})
    return out


# ----------------------------------------------------------------------------- CLI


def _model(a, h, geo, order, dp=None, df=None):
    mc = None
    if not a.no_mc:
        with open(a.mc) as f:
            mcj = json.load(f)
        key = f"{a.mc_order[0]},{a.mc_order[1]}"
        mc = mcj["fits"][key] if "fits" in mcj else mcj
    return DataModel(h, geo, order, mc=mc, float_mc=a.float_mc, dp=dp, df=df)


def resonant_fractions(h, geo):
    """Fraction of data in the used bins that the resonant MC accounts for, total and per process."""
    out = {}
    for reg, use in (("pass", geo.use_pass), ("fail", geo.use_fail)):
        tot = float(np.where(use, h[f"data_{reg}"], 0).sum())
        d = {"data": tot, "res_total": float(np.where(use, h[f"res_{reg}"], 0).sum()) / max(tot, 1)}
        for k in h:
            if k.startswith("res_") and k.endswith(f"_{reg}") and k != f"res_{reg}":
                d[k[4:-len(reg) - 1]] = float(np.where(use, h[k], 0).sum()) / max(tot, 1)
        out[reg] = d
    return out


def leave_one_out(a, h, geo, order):
    """Refit without the pass bins of one pT bin; predict them. Blinded bins stay excluded."""
    import copy
    rows = []
    for i in range(geo.valid.shape[0]):
        g = copy.copy(geo)
        held = np.zeros_like(geo.use_pass)
        held[i] = geo.use_pass[i]
        if not held.any():
            continue
        g.use_pass = geo.use_pass & ~held
        m = _model(a, h, g, order)
        r = m.fit()
        bp = band_and_projection(m, r, nsample=300)
        R, q = m.profile(r["x"])
        pred = float(np.sum((R * q + m.rp)[held]))
        obs = float(np.sum(m.dp[held]))
        if "R_lo" in bp:
            plo = float(np.sum((np.asarray(bp["R_lo"]) * q + m.rp)[held]))
            phi = float(np.sum((np.asarray(bp["R_hi"]) * q + m.rp)[held]))
            band = 0.5 * (phi - plo)
        else:
            band = float("nan")
        pull = (obs - pred) / np.sqrt(max(obs, 1.0) + band**2)
        rows.append({"pt_bin": i, "pt_range": [float(geo.ptbins[i]), float(geo.ptbins[i + 1])],
                     "extrapolation": bool(i == 0 or i == geo.valid.shape[0] - 1),
                     "obs": obs, "pred": pred, "ratio": obs / pred if pred > 0 else float("nan"),
                     "band_rel": band / pred if pred > 0 else float("nan"), "pull": float(pull),
                     "valid": r["valid"]})
    return rows


def _ftest_F(lo, hi):
    dk = hi["npar"] - lo["npar"]
    return ((lo["deviance"] - hi["deviance"]) / dk) / (hi["deviance"] / hi["ndof"])


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--hists", required=True)
    common.add_argument("--rho", nargs=2, type=float, required=True, metavar=("LO", "HI"))
    common.add_argument("--blind", nargs=2, type=float, action="append", default=[], metavar=("LO", "HI"))
    common.add_argument("--out", default=None)
    datac = argparse.ArgumentParser(add_help=False)
    datac.add_argument("--mc", help="output of the `mc` command")
    datac.add_argument("--mc-order", nargs=2, type=int)
    datac.add_argument("--no-mc", action="store_true", help="single-step TF (no MC shape)")
    datac.add_argument("--float-mc", action="store_true", help="float MC coefficients with their covariance")
    datac.add_argument("--seed", type=int, default=1)
    datac.add_argument("--pseudo-data", action="store_true",
                       help="replace data by qcd + res MC of this file (closure; use events not used for `mc`)")

    s = sub.add_parser("mc", parents=[common])
    s.add_argument("--max-order", nargs=2, type=int, default=[3, 3])
    s = sub.add_parser("data", parents=[common, datac])
    s.add_argument("--order", nargs=2, type=int, required=True)
    s = sub.add_parser("ftest", parents=[common, datac])
    s.add_argument("--lo", nargs=2, type=int, required=True)
    s.add_argument("--hi", nargs=2, type=int, required=True)
    s.add_argument("--toys", type=int, default=200)
    s = sub.add_parser("gof", parents=[common, datac])
    s.add_argument("--order", nargs=2, type=int, required=True)
    s.add_argument("--toys", type=int, default=500)
    s = sub.add_parser("loo", parents=[common, datac], help="leave-one-pT-bin-out validation")
    s.add_argument("--order", nargs=2, type=int, required=True)
    a = ap.parse_args()

    h = load_hists(a.hists)
    if getattr(a, "pseudo_data", False):
        h["data_pass"] = h["qcd_pass"] + h["res_pass"]
        h["data_fail"] = h["qcd_fail"] + h["res_fail"]
        print("pseudo-data: data replaced by QCD + resonant MC (closure test)", file=sys.stderr)
    geo = Geometry(h, a.rho[0], a.rho[1], a.blind)
    out = {"cmd": a.cmd, "rho": a.rho, "blind": a.blind, "n_valid_bins": int(geo.valid.sum()),
           "n_pass_bins_used": int(geo.use_pass.sum())}

    if a.cmd != "mc" and not a.no_mc and (a.mc is None or a.mc_order is None):
        ap.error("give --mc and --mc-order, or --no-mc for a single-step TF")

    if a.cmd == "mc":
        fits, tests, chosen = scan_mc(h, geo, a.max_order)
        out.update({"fits": {f"{k[0]},{k[1]}": v for k, v in fits.items()}, "ftests": tests,
                    "suggested_order": list(chosen),
                    "note": "analytic F on weighted-MC chi2; sequential from (0,0), rho raised on ties"})
        best = fits[chosen]
        print(f"MC TF suggested order {chosen}: chi2/ndof = {best['chi2']:.1f}/{best['ndof']}, "
              f"coefficients at 0: {best['n_coef_at_zero']}")
    elif a.cmd == "data":
        m = _model(a, h, geo, a.order)
        r = m.fit()
        bp = band_and_projection(m, r)
        out.update({"order": a.order, "mc_order": None if a.no_mc else a.mc_order, "float_mc": a.float_mc,
                    "scale": m.scale, "params": r["x"].tolist(),
                    "cov": None if r["cov"] is None else r["cov"].tolist(),
                    **{k: r[k] for k in ("valid", "edm", "deviance", "dev_pass", "dev_fail", "npass_bins",
                                         "npar", "ndof", "params_within_1sigma_of_limit")},
                    **bp, "valid_mask": geo.valid.tolist(), "pass_used_mask": geo.use_pass.tolist(),
                    "rho_map": geo.rho.tolist(), "resonant_fraction": resonant_fractions(h, geo),
                    "pseudo_data": bool(a.pseudo_data)})
        if a.pseudo_data:
            R, q = m.profile(r["x"])
            per_pt = []
            for i in range(geo.valid.shape[0]):
                u = geo.use_pass[i]
                if u.any():
                    t, pr = float(h["qcd_pass"][i][u].sum()), float((R * q)[i][u].sum())
                    e = float(np.sqrt(h["qcd_pass_w2"][i][u].sum()))
                    per_pt.append({"pt_bin": i, "truth": t, "pred": pr, "ratio": pr / t if t > 0 else None,
                                   "pull_mcstat": (pr - t) / e if e > 0 else None})
            out["closure_per_pt"] = per_pt
            print("closure pred/truth per pT bin:", [round(c["ratio"], 3) for c in per_pt if c["ratio"]])
        print(f"data fit order {tuple(a.order)}: valid={r['valid']} deviance(pass)={r['dev_pass']:.1f}/"
              f"{r['ndof']} params={np.round(r['x'], 3).tolist()} near-limit={r['params_within_1sigma_of_limit']}")
    elif a.cmd == "ftest":
        mlo, mhi = _model(a, h, geo, a.lo), _model(a, h, geo, a.hi)
        rlo, rhi = mlo.fit(hesse=False), mhi.fit(hesse=False)
        F0 = _ftest_F(rlo, rhi)
        Fs, nfail = [], 0
        for tp, tf in toys_from(mlo, rlo, a.toys, a.seed):
            tl = _model(a, h, geo, a.lo, dp=tp, df=tf).fit(rlo["x"], hesse=False)
            th = _model(a, h, geo, a.hi, dp=tp, df=tf).fit(rhi["x"], hesse=False)
            if not (tl["valid"] and th["valid"]):
                nfail += 1
                continue
            Fs.append(_ftest_F(tl, th))
        Fs = np.array(Fs)
        p = float(np.mean(Fs >= F0)) if len(Fs) else float("nan")
        out.update({"lo": a.lo, "hi": a.hi, "F_data": F0, "F_toys": Fs.tolist(), "p_toys": p,
                    "n_toys_ok": int(len(Fs)), "n_toys_failed": nfail,
                    "dev_lo": rlo["deviance"], "dev_hi": rhi["deviance"]})
        print(f"F-test {tuple(a.lo)} -> {tuple(a.hi)}: F_data={F0:.3f} p(toys)={p:.3f} "
              f"({len(Fs)} ok, {nfail} failed)")
    elif a.cmd == "loo":
        rows = leave_one_out(a, h, geo, a.order)
        out.update({"order": a.order, "leave_one_out": rows})
        for r_ in rows:
            print(f"LOO pT bin {r_['pt_bin']} {'(extrap.)' if r_['extrapolation'] else '         '} "
                  f"obs/pred={r_['ratio']:.3f} band={r_['band_rel']:.3f} pull={r_['pull']:+.2f}")
    elif a.cmd == "gof":
        m = _model(a, h, geo, a.order)
        r = m.fit(hesse=False)
        devs, nfail = [], 0
        for tp, tf in toys_from(m, r, a.toys, a.seed):
            t = _model(a, h, geo, a.order, dp=tp, df=tf).fit(r["x"], hesse=False)
            if not t["valid"]:
                nfail += 1
                continue
            devs.append(t["deviance"])
        devs = np.array(devs)
        p = float(np.mean(devs >= r["deviance"])) if len(devs) else float("nan")
        out.update({"order": a.order, "deviance_data": r["deviance"], "deviance_toys": devs.tolist(),
                    "p_toys": p, "n_toys_ok": int(len(devs)), "n_toys_failed": nfail})
        print(f"GoF order {tuple(a.order)}: deviance={r['deviance']:.1f} p(toys)={p:.3f} ({len(devs)} ok)")

    if a.out:
        with open(a.out, "w") as f:
            json.dump(out, f)


if __name__ == "__main__":
    main()
