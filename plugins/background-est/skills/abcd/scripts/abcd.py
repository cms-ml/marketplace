#!/usr/bin/env python3
"""ABCD background estimate, closure pull and transfer-factor flatness test.

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
