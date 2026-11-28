#!/usr/bin/env python3
"""ABCD background estimate (inclusive or binned), closure pull, transfer-factor
flatness test, non-closure systematic and correlated chi2.

Regions: A = signal region (pass x, pass y), B = (fail x, pass y),
C = (pass x, fail y), D = (fail x, fail y).  Prediction: A = B * C / D.

Import the functions, or run a self-test on toy data:

    abcd.py --demo [--rho 0.0] [--seed 1]
    abcd.py --B 120 --C 80 --D 400 [--A 22]

stdout: KEY=VALUE lines.  Exit 0 ok, 1 closure pull > 2 sigma, 2 bad input.
"""

import argparse
import sys

import numpy as np


def abcd(nB, nC, nD, eB=None, eC=None, eD=None):
    """Return (prediction, uncertainty). Errors default to sqrt(N).

    Works on scalars or per-bin arrays (binned ABCD: shape from C, B/D per bin
    or inclusive). For weighted or MC-subtracted yields pass sqrt(sumw2).
    """
    nB, nC, nD = (np.asarray(v, dtype=float) for v in (nB, nC, nD))
    eB = np.sqrt(nB) if eB is None else np.asarray(eB, dtype=float)
    eC = np.sqrt(nC) if eC is None else np.asarray(eC, dtype=float)
    eD = np.sqrt(nD) if eD is None else np.asarray(eD, dtype=float)
    if np.any(nD <= 0) or np.any(nB < 0) or np.any(nC < 0):
        raise ValueError("need D > 0 and B, C >= 0 (after any MC subtraction)")
    pred = nB * nC / nD
    with np.errstate(divide="ignore", invalid="ignore"):
        rel2 = (
            np.where(nB > 0, (eB / nB) ** 2, 0)
            + np.where(nC > 0, (eC / nC) ** 2, 0)
            + (eD / nD) ** 2
        )
    return pred, pred * np.sqrt(rel2)


def abcd_binned(nB, nC, nD, eB=None, eC=None, eD=None, tf="inclusive", shape="C"):
    """Binned ABCD in the fit variable: shape from one side region, scaled by the
    transfer factor measured with the other one and D.

    shape="C": pred = C(m) * B/D.  shape="B": pred = B(m) * C/D (choose the side
    region that shares A's cut on the variable that sculpts m).
    tf="inclusive": one ratio from the summed yields (use when the TF is flat in the
    fit variable; empty or sparse bins are harmless). tf="perbin": ratio per bin
    (every D bin must be > 0). For a fitted TF use tf_fit_ftest. Returns (pred, cov);
    cov includes the TF error, fully correlated across bins for the inclusive TF.
    """
    if shape == "B":
        nB, nC, eB, eC = nC, nB, eC, eB
    nB, nC, nD = (np.asarray(v, dtype=float) for v in (nB, nC, nD))
    eB = np.sqrt(nB) if eB is None else np.asarray(eB, dtype=float)
    eC = np.sqrt(nC) if eC is None else np.asarray(eC, dtype=float)
    eD = np.sqrt(nD) if eD is None else np.asarray(eD, dtype=float)
    if tf == "perbin":
        pred, err = abcd(nB, nC, nD, eB, eC, eD)
        return pred, np.diag(err**2)
    sB, sD = nB.sum(), nD.sum()
    if sD <= 0 or sB < 0 or np.any(nC < 0):
        raise ValueError("need sum(D) > 0, sum(B) >= 0 and C >= 0")
    r = sB / sD
    er = r * np.sqrt(np.sum(eB**2) / sB**2 + np.sum(eD**2) / sD**2) if sB > 0 else 0.0
    pred = nC * r
    return pred, np.diag((eC * r) ** 2) + np.outer(nC, nC) * er**2


def tf_fit_ftest(m, r, e, max_order=4, alpha=0.05):
    """Fit the per-bin transfer factor r(m) +- e with polynomials of increasing
    order and pick the order by an F-test (stop when the next order improves chi2
    with p > alpha). Returns (order, coeffs, cov, chi2, ndf); evaluate with
    np.polyval(coeffs, m). Use the fit (and its band as a shape systematic)
    before falling back to a per-bin TF; if no order fits (chi2 p < alpha), the
    variables are correlated in m: say so."""
    from scipy.stats import f as fdist

    m, r, e = (np.asarray(v, float) for v in (m, r, e))
    res = []
    for n in range(min(max_order, len(m) - 2) + 1):
        c, cov = np.polyfit(m, r, n, w=1 / e, cov="unscaled")
        res.append(
            (
                n,
                c,
                cov,
                float(np.sum(((r - np.polyval(c, m)) / e) ** 2)),
                len(m) - n - 1,
            )
        )
    best = res[0]
    for nxt in res[1:]:
        F = (best[3] - nxt[3]) / (nxt[0] - best[0]) / (nxt[3] / nxt[4])
        if fdist.sf(F, nxt[0] - best[0], nxt[4]) > alpha:
            break
        best = nxt
    return best


def syst_cov(pred, rel_corr=0.0, rel_shape=None):
    """Covariance of a non-closure systematic: a fully correlated yield term
    rel_corr*pred plus an optional uncorrelated per-bin shape term."""
    pred = np.asarray(pred, float)
    cov = np.outer(pred, pred) * rel_corr**2
    if rel_shape is not None:
        cov += np.diag((np.asarray(rel_shape, float) * pred) ** 2)
    return cov


def chi2_cov(obs, pred, cov_pred, eobs=None):
    """Chi2 of observed vs predicted with the full prediction covariance
    (stat + correlated syst) plus data stat. Returns (chi2, ndf, pulls); pulls
    are per bin, (obs - pred)/sqrt(diag). Quote this chi2, not one with the
    systematic added per bin, when the systematic is correlated across bins."""
    obs, pred = np.asarray(obs, float), np.asarray(pred, float)
    eobs = np.sqrt(np.maximum(obs, 1)) if eobs is None else np.asarray(eobs, float)
    cov = np.asarray(cov_pred, float) + np.diag(eobs**2)
    d = obs - pred
    return float(d @ np.linalg.solve(cov, d)), len(d), d / np.sqrt(np.diag(cov))


def nonclosure_syst(tests):
    """Yield non-closure systematic from closure tests.

    tests: (ratio, pull, rel_stat) for EVERY test you ran: MC closure in A, MC
    and data validation regions, sidebands made by inverting a cut, and the
    data-vs-MC independence test expressed as a ratio. Each contributes rel_stat
    if |pull| <= 2, else |1 - ratio|; the systematic is the largest.
    """
    return max(s if abs(p) <= 2 else abs(1 - r) for r, p, s in tests)


def closure(obs, pred, epred, eobs=None):
    """Return (obs/pred, pull). |pull| > 2 means the method does not close."""
    eobs = np.sqrt(obs) if eobs is None else eobs
    return obs / pred, (obs - pred) / np.hypot(eobs, epred)


def tf_flatness(x, y, ycut, xedges, w=None):
    """Pass/fail ratio in y, in bins of x. Returns (ratio, error, chi2, ndf)
    of a constant fit. A slope means x and y are correlated: ABCD is biased."""
    w = np.ones_like(x, dtype=float) if w is None else w
    p = y > ycut
    hp, _ = np.histogram(x[p], xedges, weights=w[p])
    hf, _ = np.histogram(x[~p], xedges, weights=w[~p])
    vp, _ = np.histogram(x[p], xedges, weights=w[p] ** 2)
    vf, _ = np.histogram(x[~p], xedges, weights=w[~p] ** 2)
    ok = (hp > 0) & (hf > 0)
    r = hp[ok] / hf[ok]
    e = r * np.sqrt(vp[ok] / hp[ok] ** 2 + vf[ok] / hf[ok] ** 2)
    mean = np.sum(r / e**2) / np.sum(1 / e**2)
    return r, e, float(np.sum(((r - mean) / e) ** 2)), int(ok.sum() - 1)


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--demo", action="store_true", help="toy bivariate Gaussian")
    ap.add_argument("--rho", type=float, default=0.0, help="toy x-y correlation")
    ap.add_argument("--seed", type=int, default=1)
    for k in "ABCD":
        ap.add_argument(f"--{k}", type=float, help=f"yield in region {k}")
    a = ap.parse_args()

    if a.demo:
        rng = np.random.default_rng(a.seed)
        cov = [[1, a.rho], [a.rho, 1]]
        x, y = rng.multivariate_normal([0, 0], cov, 200_000).T
        px, py = x > 1.0, y > 1.0
        a.A, a.B = float((px & py).sum()), float((~px & py).sum())
        a.C, a.D = float((px & ~py).sum()), float((~px & ~py).sum())
        _, _, chi2, ndf = tf_flatness(x, y, 1.0, np.linspace(-2, 2, 9))
        print(f"TF_CHI2={chi2:.1f}\nTF_NDF={ndf}")
        # binned ABCD in an independent third variable z, inclusive TF
        z = rng.exponential(1.0, x.size)
        ze = np.array([0, 0.5, 1, 2, 4, 50])

        def h(m):
            return np.histogram(z[m], ze)[0].astype(float)

        pb, cb = abcd_binned(h(~px & py), h(px & ~py), h(~px & ~py))
        c2, nb, _ = chi2_cov(h(px & py), pb, cb)
        print(f"BINNED_CHI2={c2:.1f}\nBINNED_NDF={nb}")
    if None in (a.B, a.C, a.D):
        print("need --B --C --D or --demo", file=sys.stderr)
        return 2
    try:
        pred, err = abcd(a.B, a.C, a.D)
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 2
    print(f"PRED={pred:.2f}\nPRED_ERR={err:.2f}")
    if a.A is not None:
        ratio, pull = closure(a.A, pred, err)
        print(f"OBS={a.A:.0f}\nRATIO={ratio:.3f}\nPULL={pull:.2f}")
        return 0 if abs(pull) <= 2 else 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
