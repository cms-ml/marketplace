#!/usr/bin/env python3
"""Template: build and validate a HEPData submission with hepdata_lib.

Copy this file next to your analysis and replace build() with your tables.
Read every number from the same files your plotting code reads (JSON,
ROOT, hist pickles). Never digitise a figure.

Usage:
    make_hepdata.py --demo -o hepdata_demo     # toy record, exercises every helper
    make_hepdata.py -o hepdata --input summary.json --input plots   # your record (after you fill build())
    make_hepdata.py ... --no-tar               # don't keep the submission.tar.gz next to the outdir

From another script: `import make_hepdata; make_hepdata.main(["-o", "hepdata", "--input", "summary.json"])`.

What it does: builds the tables, refuses NaN/inf and length mismatches,
writes the YAML directory, then runs `hepdata-validate -d <outdir>`.
Stdout: TABLES=<n>, OUTDIR=<dir>, VALID=1|0. Diagnostics on stderr.
Exit codes: 0 valid, 1 validation failed, 2 bad input (missing file, NaN, ...).
Tested with hepdata_lib 0.20.0 and hepdata-validator from the LCG_109 view.
"""
from __future__ import annotations

import argparse
import math
import numbers
import os
import subprocess
import sys

from hepdata_lib import Submission, Table, Uncertainty, Variable

SQRTS_GEV = 13000.0
REACTION = "P P --> JET JET"


# ----------------------------------------------------------------------------- guards

def require_files(paths):
    missing = [p for p in paths if not os.path.isfile(p)]
    if missing:
        print("error: missing input(s):\n  " + "\n  ".join(missing), file=sys.stderr)
        sys.exit(2)


def finite(name, values):
    """hepdata_lib writes NaN as `.nan` and hepdata-validate accepts it: stop it here."""
    flat = [x for v in values for x in (v if isinstance(v, (tuple, list)) else (v,))]
    # numbers.Real also covers numpy scalars (float32 NaN is not an instance of float)
    bad = [x for x in flat if isinstance(x, numbers.Real) and not math.isfinite(float(x))]
    if bad:
        print(f"error: {name}: {len(bad)} non-finite value(s); drop those bins or document them", file=sys.stderr)
        sys.exit(2)
    return list(values)


# ----------------------------------------------------------------------------- table helpers

def figure_table(name, description, location, observables, image=None, phrases=None):
    """One table per figure panel. Name it after the paper object ("Figure 3a"); without a paper,
    use a short ASCII name ("mjj spectrum 2b"). The name becomes the YAML file name."""
    t = Table(name)
    t.description = description
    t.location = location
    t.keywords["observables"] = observables
    t.keywords["reactions"] = [REACTION]
    t.keywords["cmenergies"] = [SQRTS_GEV]
    if phrases:
        t.keywords["phrases"] = phrases     # free-text search terms, e.g. ["Dijet", "Resonance", "b tagging"]
    if image:
        # absolute now: create_files() runs later from another directory (see main())
        t.add_image(os.path.abspath(image))  # PDF or PNG; writes a PNG and thumb_*.png (needs ImageMagick)
    return t


def binned_x(name, edges, units="GeV"):
    v = Variable(name, is_independent=True, is_binned=True, units=units)
    v.values = [(float(lo), float(hi)) for lo, hi in zip(edges[:-1], edges[1:])]
    return v


def y_var(name, values, units="", qualifiers=None, zero_ok=False):
    """zero_ok=True sets hepdata_lib's zero_uncertainties_warning=False (values without errors).
    Integers stay integers (counts are written as 45, not 45.0)."""
    v = Variable(name, is_independent=False, is_binned=False, units=units,
                 zero_uncertainties_warning=not zero_ok)
    v.values = finite(name, [int(x) if isinstance(x, numbers.Integral) else float(x) for x in values])
    for k, q in (qualifiers or {}).items():
        v.add_qualifier(k, q)
    return v


def add_sym(var, label, errors):
    u = Uncertainty(label, is_symmetric=True)
    u.values = finite(label, [float(e) for e in errors])
    var.add_uncertainty(u)


def add_asym(var, label, down, up):
    """down/up are positive sizes; HEPData wants (minus, plus) with the minus value negative."""
    u = Uncertainty(label, is_symmetric=False)
    u.values = finite(label, [(-abs(float(d)), abs(float(p))) for d, p in zip(down, up)])
    var.add_uncertainty(u)


def category_x(name, labels):
    """String-valued independent variable: use it for per-category tables (fit results, yields)
    instead of an artificial integer index."""
    v = Variable(name, is_independent=True, is_binned=False)
    v.values = [str(x) for x in labels]
    return v


# ----------------------------------------------------------------------------- your record

def build(sub: Submission, args) -> None:
    """Fill with your tables. See demo() for one example of each kind.
    args.input holds the --input paths (absolute), e.g. summary.json and the plots directory."""
    print("error: build() is a stub: copy this template and fill it, or run --demo", file=sys.stderr)
    sys.exit(2)


def demo(sub: Submission, args) -> None:
    sub.comment = ("Toy record made by the hepdata skill template. NOT a CMS result: "
                   "values are invented to exercise the helpers.")
    # 1) spectrum with Poisson (Garwood) errors, one qualifier
    edges = [1058, 1118, 1181, 1246, 1313]
    counts = [1200, 830, 0, 410]
    t = figure_table("Figure 1", "Dijet invariant mass spectrum (toy).", "Data from Figure 1.", ["N"],
                     phrases=["Dijet", "Resonance"])
    t.add_variable(binned_x("$m_{jj}$", edges))
    y = y_var("Events", counts, qualifiers={"SQRT(S)": f"{SQRTS_GEV:g} GeV", "Category": "2 b tags"}, zero_ok=True)
    from scipy import stats
    lo = [n - (stats.chi2.ppf(0.15865, 2 * n) / 2 if n > 0 else 0.0) for n in counts]
    hi = [stats.chi2.ppf(0.84135, 2 * (n + 1)) / 2 - n for n in counts]
    add_asym(y, "stat", lo, hi)
    t.add_variable(y)
    sub.add_table(t)
    # 2) efficiency with asymmetric Clopper-Pearson errors
    t = figure_table("Figure 2", "Trigger efficiency vs m_jj (toy).", "Data from Figure 2.", ["EFF"])
    t.add_variable(binned_x("$m_{jj}$", edges))
    e = y_var("Efficiency", [0.95, 0.99, 0.999, 1.0])
    add_asym(e, "stat", [0.01, 0.004, 0.001, 0.002], [0.01, 0.003, 0.0008, 0.0])
    t.add_variable(e)
    sub.add_table(t)
    # 3) per-category summary with a string independent variable
    t = figure_table("Table 1", "Background fit quality per category (toy).", "Data from Table 1.", ["CHI2/NDF"])
    t.add_variable(category_x("Category", ["1 b tag", "2 b tags"]))
    t.add_variable(y_var("Chosen number of fit parameters", [3, 4], zero_ok=True))
    t.add_variable(y_var("$\\chi^2$/ndf", [0.95, 0.83], zero_ok=True))
    sub.add_table(t)
    # 4) category x scan point: two independent variables, one row per combination
    t = figure_table("Table 2", "Fit quality vs number of parameters, per category (toy).",
                     "Data from Table 2.", ["CHI2/NDF"])
    cats, npars = ["1 b tag", "2 b tags"], [3, 4, 5]
    t.add_variable(category_x("Category", [c for c in cats for _ in npars]))
    n = Variable("Number of fit parameters", is_independent=True, is_binned=False)
    n.values = [k for _ in cats for k in npars]
    t.add_variable(n)
    t.add_variable(y_var("$\\chi^2$/ndf", [0.95, 0.97, 0.98, 0.91, 0.83, 0.85], zero_ok=True))
    sub.add_table(t)


# ----------------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--outdir", default="hepdata", help="output directory (replaced)")
    ap.add_argument("--input", action="append", default=[], help="input file or directory for build(), repeatable")
    ap.add_argument("--demo", action="store_true", help="build the toy record instead of build()")
    ap.add_argument("--no-tar", action="store_true", help="delete the submission.tar.gz create_files() writes")
    args = ap.parse_args(argv)
    args.input = [os.path.abspath(x) for x in args.input]   # build() may run after a chdir

    sub = Submission()
    (demo if args.demo else build)(sub, args)
    outdir = os.path.abspath(args.outdir)
    # create_files() also writes submission.tar.gz into the *current* directory: run it from the
    # parent of outdir so the tarball lands next to it, not wherever you happen to be.
    os.makedirs(os.path.dirname(outdir), exist_ok=True)
    cwd = os.getcwd()
    os.chdir(os.path.dirname(outdir))
    try:
        sub.create_files(os.path.basename(outdir), remove_old=True)
    except AssertionError as e:      # raised after writing when the YAML fails validation
        print(f"error: hepdata_lib: {e}", file=sys.stderr)
    finally:
        os.chdir(cwd)
    tarball = os.path.join(os.path.dirname(outdir), "submission.tar.gz")
    if args.no_tar and os.path.exists(tarball):
        os.remove(tarball)
    # run the validator from inside outdir so the log has no absolute paths
    res = subprocess.run(["hepdata-validate", "-d", "."], cwd=outdir, capture_output=True, text=True)
    print(res.stdout.strip(), file=sys.stderr)
    print(f"TABLES={len(sub.tables)}")
    print(f"OUTDIR={args.outdir}")
    print(f"VALID={int(res.returncode == 0)}")
    return 0 if res.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
