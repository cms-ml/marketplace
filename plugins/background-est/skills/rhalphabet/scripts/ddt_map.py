#!/usr/bin/env python3
"""Decorrelation map (DDT / cut map) at constant QCD efficiency in (rho, pT).

A substructure variable x (e.g. N2) or a tagger score is decorrelated from the
jet mass by cutting on x - X(rho, pT) instead of x, where X is the weighted
quantile of x in QCD simulation in each (rho, pT) cell at the target
efficiency. The cut then keeps the same QCD fraction everywhere, so it does
not sculpt the mass spectrum.

Library use (numpy only, scipy optional for smoothing):

    from ddt_map import build_map, threshold, closure
    m = build_map(x, rho, pt, w, eff=0.2, rho_bins=..., pt_bins=..., direction="below")
    passes = x < threshold(m, rho, pt)          # direction="below": pass = x < X
    print(closure(m, x, rho, pt, w))            # QCD efficiency per cell after the cut

CLI (reads Parquet with pyarrow):

    python ddt_map.py build --files qcd_*.parquet --var n2b1 --weight xsec_weight \
        --eff 0.2 --direction below --rho-bins -7 -1 60 --pt-bins 400 1200 32 \
        --out n2ddt_map.json
    python ddt_map.py closure --map n2ddt_map.json --files qcd_odd.parquet ...

Choose the efficiency yourself (scan it); this script only implements the map.
"""
import argparse
import sys
import json

import numpy as np


def _wquantile(x, w, q):
    """Weighted quantile q in [0, 1]; negative weights are kept (MC@NLO)."""
    order = np.argsort(x)
    x, w = x[order], w[order]
    cw = np.cumsum(w)
    if cw[-1] <= 0:
        return np.nan
    return float(np.interp(q * cw[-1], cw, x))


def build_map(x, rho, pt, w, eff, rho_bins, pt_bins, direction="below",
              min_neff=100, smooth_sigma=0.0):
    """Return a dict with the threshold map X[rho_bin, pt_bin].

    direction="below": pass = x < X, X is the eff-quantile (N2-like).
    direction="above": pass = x > X, X is the (1 - eff)-quantile (tagger score).
    Cells with effective entries (sum w)^2 / sum w^2 < min_neff are filled from
    the nearest good cell; smooth_sigma > 0 applies a Gaussian filter (in
    cells) afterwards (needs scipy).
    """
    x, rho, pt, w = (np.asarray(a, dtype=float) for a in (x, rho, pt, w))
    rho_bins, pt_bins = np.asarray(rho_bins, float), np.asarray(pt_bins, float)
    q = eff if direction == "below" else 1.0 - eff
    ir = np.digitize(rho, rho_bins) - 1
    ip = np.digitize(pt, pt_bins) - 1
    nr, npt = len(rho_bins) - 1, len(pt_bins) - 1
    X = np.full((nr, npt), np.nan)
    neff = np.zeros((nr, npt))
    inside = (ir >= 0) & (ir < nr) & (ip >= 0) & (ip < npt)
    cell = np.where(inside, ir * npt + ip, -1)
    order = np.argsort(cell, kind="stable")
    cs = cell[order]
    starts = np.searchsorted(cs, np.arange(nr * npt))
    ends = np.searchsorted(cs, np.arange(nr * npt), side="right")
    for c in range(nr * npt):
        sel = order[starts[c]:ends[c]]
        if sel.size == 0:
            continue
        ws = w[sel]
        s2 = np.sum(ws**2)
        neff[c // npt, c % npt] = np.sum(ws) ** 2 / s2 if s2 > 0 else 0
        if neff[c // npt, c % npt] >= min_neff:
            X[c // npt, c % npt] = _wquantile(x[sel], ws, q)
    good = np.isfinite(X)
    if not good.any():
        raise ValueError("no cell has enough entries; use coarser bins or lower min_neff")
    n_filled = int((~good).sum())
    if n_filled:
        gi, gj = np.nonzero(good)
        for i, j in zip(*np.nonzero(~good)):
            k = np.argmin((gi - i) ** 2 + (gj - j) ** 2)
            X[i, j] = X[gi[k], gj[k]]
    if smooth_sigma > 0:
        from scipy.ndimage import gaussian_filter
        X = gaussian_filter(X, smooth_sigma, mode="nearest")
    return {"rho_bins": rho_bins.tolist(), "pt_bins": pt_bins.tolist(), "X": X.tolist(),
            "eff": eff, "direction": direction, "min_neff": min_neff,
            "smooth_sigma": smooth_sigma, "n_cells_filled_from_neighbour": n_filled,
            "neff": neff.tolist()}


def threshold(m, rho, pt):
    """Threshold X(rho, pT) per jet by cell lookup (values outside are clipped to the edge cells)."""
    rb, pb, X = np.asarray(m["rho_bins"]), np.asarray(m["pt_bins"]), np.asarray(m["X"])
    ir = np.clip(np.digitize(rho, rb) - 1, 0, len(rb) - 2)
    ip = np.clip(np.digitize(pt, pb) - 1, 0, len(pb) - 2)
    return X[ir, ip]


def passes(m, x, rho, pt):
    t = threshold(m, rho, pt)
    return x < t if m["direction"] == "below" else x > t


def closure(m, x, rho, pt, w, min_neff=100):
    """QCD efficiency of the cut per cell; use an independent sample (e.g. odd events) for an honest test."""
    p = passes(m, x, rho, pt).astype(float)
    rb, pb = np.asarray(m["rho_bins"]), np.asarray(m["pt_bins"])
    num, _, _ = np.histogram2d(rho, pt, [rb, pb], weights=w * p)
    den, _, _ = np.histogram2d(rho, pt, [rb, pb], weights=w)
    den2, _, _ = np.histogram2d(rho, pt, [rb, pb], weights=w**2)
    with np.errstate(divide="ignore", invalid="ignore"):
        eff = num / den
        neff = den**2 / den2
    ok = np.isfinite(eff) & (neff >= min_neff)
    t = m["eff"]
    glob = float(np.sum(w * p) / np.sum(w))
    stat = np.sqrt(t * (1 - t) / neff[ok])                  # binomial error per cell at the target
    pulls = (eff[ok] - t) / stat
    pull_rms = float(np.sqrt(np.mean(pulls**2)))
    rel_rms = float(np.std(eff[ok]) / t)
    # Pass: global within 3% (relative) of the target, and cells scatter no more than
    # statistics allow (pull rms < 1.5) OR by less than 5% relative when the statistics are huge.
    ok_global = abs(glob - t) / t < 0.03
    ok_cells = pull_rms < 1.5 or rel_rms < 0.05
    return {"target": t, "global": glob,
            "cell_mean": float(np.mean(eff[ok])), "cell_rms": float(np.std(eff[ok])),
            "cell_rel_rms": rel_rms, "cell_rel_rms_expected_stat": float(np.sqrt(np.mean(stat**2)) / t),
            "cell_pull_rms": pull_rms, "n_cells_pull_gt3": int(np.sum(np.abs(pulls) > 3)),
            "cell_min": float(np.min(eff[ok])), "cell_max": float(np.max(eff[ok])),
            "n_cells": int(ok.sum()),
            "pass": bool(ok_global and ok_cells),
            "pass_rule": "|global-target|/target<0.03 and (cell pull rms<1.5 or cell rel rms<0.05)"}


def _read(files, cols):
    import pyarrow.parquet as pq
    parts = [pq.read_table(f, columns=cols) for f in files]
    return {c: np.concatenate([p.column(c).to_numpy() for p in parts]) for c in cols}


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("build", "closure"):
        s = sub.add_parser(name)
        s.add_argument("--files", nargs="+", required=True)
        s.add_argument("--var", default="n2b1")
        s.add_argument("--rho", default="rho")
        s.add_argument("--pt", default="pt")
        s.add_argument("--weight", default="xsec_weight")
        s.add_argument("--select", default=None,
                       help="extra numpy expression on columns, e.g. \"(msd>40)&(pt>400)\"")
        s.add_argument("--event", default="event",
                       help="event-number column used by --parity (falls back to row index if absent)")
    b = sub.choices["build"]
    b.add_argument("--eff", type=float, required=True)
    b.add_argument("--direction", choices=["below", "above"], default="below")
    b.add_argument("--rho-bins", nargs=3, type=float, metavar=("LO", "HI", "N"), required=True)
    b.add_argument("--pt-bins", nargs=3, type=float, metavar=("LO", "HI", "N"), required=True)
    b.add_argument("--min-neff", type=float, default=100)
    b.add_argument("--smooth", type=float, default=0.0)
    b.add_argument("--parity", choices=["all", "even", "odd"], default="all",
                   help="split by EVENT number parity (build on even, test closure on odd)")
    b.add_argument("--out", required=True)
    c = sub.choices["closure"]
    c.add_argument("--map", required=True)
    c.add_argument("--parity", choices=["all", "even", "odd"], default="all")
    a = ap.parse_args()

    cols = [a.var, a.rho, a.pt, a.weight]
    extra = []
    if a.select:
        import re
        extra = sorted(set(re.findall(r"[A-Za-z_]\w*", a.select)) - set(cols) - {"np"})
    if a.parity != "all":
        import pyarrow.parquet as pq
        if a.event in pq.read_schema(a.files[0]).names:
            extra = sorted(set(extra) | {a.event})
        else:
            print(f"WARNING: column '{a.event}' not found; --parity falls back to ROW index, which is "
                  "not an independent split if rows are ordered or files are re-read differently. "
                  "Store the event number in the skim.", file=sys.stderr)
    d = _read(a.files, cols + extra)
    sel = np.ones(len(d[a.var]), bool)
    if a.select:
        sel &= eval(a.select, {"np": np}, d)
    sel &= np.isfinite(d[a.var])
    if a.parity != "all":
        idx = d[a.event].astype(np.int64) if a.event in d else np.arange(len(sel))
        sel &= (idx % 2 == 0) if a.parity == "even" else (idx % 2 == 1)
    x, rho, pt, w = (d[k][sel] for k in cols)
    if a.cmd == "build":
        lo, hi, n = a.rho_bins
        rb = np.linspace(lo, hi, int(n) + 1)
        lo, hi, n = a.pt_bins
        pb = np.linspace(lo, hi, int(n) + 1)
        m = build_map(x, rho, pt, w, a.eff, rb, pb, a.direction, a.min_neff, a.smooth)
        m["closure_in_sample"] = closure(m, x, rho, pt, w, a.min_neff)
        with open(a.out, "w") as f:
            json.dump(m, f)
        print(json.dumps({k: m[k] for k in ("eff", "direction", "n_cells_filled_from_neighbour",
                                            "closure_in_sample")}))
    else:
        with open(a.map) as f:
            m = json.load(f)
        print(json.dumps(closure(m, x, rho, pt, w, m.get("min_neff", 100))))


if __name__ == "__main__":
    main()
