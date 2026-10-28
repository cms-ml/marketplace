#!/usr/bin/env python3
"""HEPData record of the dijet-2016 Open Data validation (NOT a CMS result).

Started from the hepdata skill template (assets/make_hepdata.py): helpers, guards and validation are
unchanged; build() is filled from summary.json (everything numeric) and plots/ (images). Called by
analysis.py, or standalone:

    make_hepdata.py --summary summary.json --plots plots -o hepdata --log hepdata_validation.txt

Stdout: TABLES=<n>, OUTDIR=<dir>, VALID=1|0. Diagnostics on stderr.
Exit codes: 0 valid, 1 validation failed, 2 bad input (missing file, NaN, ...).
Tested with hepdata_lib 0.20.0 and hepdata-validator from the LCG_109 view.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)


def _repo_root(start):
    p = start
    while os.path.dirname(p) != p:
        if os.path.isdir(os.path.join(p, "plugins", "cms", "skills", "trigger-efficiency", "scripts")):
            return p
        p = os.path.dirname(p)
    raise RuntimeError("repository root not found above " + start)


# the efficiency table is recomputed from num/den with the trigger-efficiency skill helper
sys.path.insert(0, os.path.join(_repo_root(HERE), "plugins", "cms", "skills", "trigger-efficiency", "scripts"))
from turnon import efficiency  # noqa: E402

from hepdata_lib import Submission, Table, Uncertainty, Variable  # noqa: E402

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
    bad = [x for x in flat if isinstance(x, float) and not math.isfinite(x)]
    if bad:
        print(f"error: {name}: {len(bad)} non-finite value(s); drop those bins or document them", file=sys.stderr)
        sys.exit(2)
    return list(values)


# ----------------------------------------------------------------------------- table helpers

def figure_table(name, description, location, observables, image=None):
    """One table per figure panel. Name it after the paper object ("Figure 3a"), ASCII only:
    the name becomes the YAML file name."""
    t = Table(name)
    t.description = description
    t.location = location
    t.keywords["observables"] = observables
    t.keywords["reactions"] = [REACTION]
    t.keywords["cmenergies"] = [SQRTS_GEV]
    if image:
        t.add_image(image)          # PDF or PNG; writes a PNG and thumb_*.png (needs ImageMagick)
    return t


def binned_x(name, edges, units="GeV"):
    v = Variable(name, is_independent=True, is_binned=True, units=units)
    v.values = [(float(lo), float(hi)) for lo, hi in zip(edges[:-1], edges[1:])]
    return v


def y_var(name, values, units="", qualifiers=None, zero_ok=False):
    v = Variable(name, is_independent=False, is_binned=False, units=units,
                 zero_uncertainties_warning=not zero_ok)
    v.values = finite(name, [float(x) for x in values])
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

NOT_CMS = " Open Data validation of analysis tooling: NOT a CMS result, no physics claim."
PHRASES = ["CMS Open Data", "dijet", "b tagging", "validation"]
COMMON_Q = {"SQRT(S)": f"{SQRTS_GEV:g} GeV", "Dataset": "Run2016G+H JetHT NanoAODv9 (CMS Open Data)",
            "Selection": "2 leading AK4 CHS jets, tight ID, |eta|<2.4, |deta|<1.1"}


def new_table(name, description, plot_stems, observables, plots_dir, location):
    """figure_table() plus the plot images (resolved from the given directory) and the phrases keyword."""
    imgs = [os.path.join(plots_dir, f"{p}.pdf") for p in plot_stems]
    require_files(imgs)
    t = figure_table(name, description + NOT_CMS, location, observables)
    t.keywords["phrases"] = PHRASES        # the template's figure_table() does not set phrases
    for im in imgs:
        t.add_image(im)
    return t


def build(sub: Submission, args) -> None:
    require_files([args.summary])
    summary = json.load(open(args.summary))
    lumi = summary["luminosity"]["recorded_fb"]
    thr = summary["trigger"]["threshold_mjj_GeV"]
    sub.comment = ("Validation of analysis tooling on 2016G+H CMS Open Data (JetHT NanoAODv9). Search for b-tagged dijet "
                   "resonances, strategy after CMS-EXO-20-008. NOT an official CMS result and no physics claim. "
                   f"Integrated luminosity of the processed subset: {lumi:.3f} fb^-1 at 13 TeV.")
    P = os.path.abspath(args.plots)      # add_image() paths are resolved after a chdir: make them absolute

    # 1. trigger efficiency: recompute eff and CP errors from num/den, DROP bins with an empty denominator
    tr = summary["trigger"]["efficiency_vs_mjj"]
    edges = [float(x) for x in tr["edges"]]
    e = efficiency(tr["num"], tr["den"])
    keep = [i for i in range(len(e["den"])) if e["den"][i] > 0]
    dropped = [f"{edges[i]:g}-{edges[i + 1]:g}" for i in range(len(e["den"])) if e["den"][i] == 0]
    print(f"trigger table: {len(keep)} bins kept, dropped empty-denominator bins: {dropped or 'none'}", file=sys.stderr)
    t = new_table("Trigger efficiency",
                  "Efficiency of the OR of HLT_PFHT900, PFHT800, PFJet450, PFJet500, CaloJet500_NoJetID, AK8PFJet450, AK8PFJet500, "
                  "measured in events passing the prescaled reference HLT_PFJet260 (golden JSON, event filters, selection as in the "
                  "qualifiers). Clopper-Pearson 68% intervals."
                  + (f" Bins with no reference events are omitted ({', '.join(dropped)} GeV)." if dropped else "")
                  + f" Chosen threshold m_jj > {thr:.0f} GeV.",
                  ["trigger_efficiency"], ["EFF"], P, "Data from plots/trigger_efficiency.png (validation/dijet-2016).")
    t.add_variable(_binned_subset(edges, keep))
    y = y_var("Efficiency", [round(float(e["eff"][i]), 5) for i in keep], qualifiers={**COMMON_Q, "Reference trigger": "HLT_PFJet260"}, zero_ok=True)
    add_asym(y, "stat (Clopper-Pearson)", [round(float(e["eff"][i] - e["lo"][i]), 5) for i in keep],
             [round(float(e["hi"][i] - e["eff"][i]), 5) for i in keep])
    t.add_variable(y)
    t.add_variable(y_var("Events passing reference and signal trigger", [e["num"][i] for i in keep], units="Events", zero_ok=True))
    t.add_variable(y_var("Events passing reference trigger", [e["den"][i] for i in keep], units="Events", zero_ok=True))
    sub.add_table(t)

    # 2. m_jj spectra with the chosen dijet fit
    for cat in ("1b", "2b"):
        fs = summary["fit"][cat]
        t = new_table(f"mjj spectrum {cat}",
                      f"Dijet invariant mass spectrum in the category '{cat}' ({'>=1' if cat == '1b' else '2'} DeepJet Medium b tag(s)), "
                      f"data counts and the {fs['chosen_nparams']}-parameter dijet-function fit "
                      "p0 (1-x)^p1 / x^(p2+p3 ln x+p4 ln^2 x), x=m_jj/13000 (Poisson likelihood). Zero-content bins are kept "
                      "because they were part of the fit. Uncertainty on data: sqrt(N).",
                      [f"fit_{cat}"], ["N"], P, f"Data from plots/fit_{cat}.png (validation/dijet-2016).")
        t.add_variable(binned_x("$m_{jj}$", fs["fit_edges_GeV"]))
        n = fs["data_counts"]
        yd = y_var("Data events", n, units="Events", qualifiers={**COMMON_Q, "Category": cat}, zero_ok=True)
        add_sym(yd, "stat (sqrt N)", [round(math.sqrt(v), 4) for v in n])
        t.add_variable(yd)
        t.add_variable(y_var("Fit expectation", [round(v, 5) for v in fs["fit_expectation_chosen"]], units="Events",
                             qualifiers={"Fit parameters": str(fs["chosen_nparams"])}, zero_ok=True))
        sub.add_table(t)

    # 3. fit results: string category variable + number of parameters (no encoded integer index)
    t = new_table("Fit results",
                  "Dijet-function fit results per category and number of parameters: Poisson deviance chi2, ndf and F-test p-value "
                  "for adding one parameter (n to n+1; 0 for the last function). 'Chosen' is 1 for the number of parameters selected "
                  "by the F-test (lowest n with p > 0.05).",
                  ["ftest_1b", "ftest_2b"], ["CHI2/NDF"], P, "Data from summary.json (fit) and plots/ftest_*.png (validation/dijet-2016).")
    cats, npars, chi2, ndf, chi2n, pval, chosen_flag = [], [], [], [], [], [], []
    for cat in ("1b", "2b"):
        fs = summary["fit"][cat]
        for npar in (3, 4, 5):
            f = fs["fits"][str(npar)]
            row = [r for r in fs["ftest"] if r["n_from"] == npar]
            cats.append(cat); npars.append(npar)
            chi2.append(round(f["chi2_poisson_deviance"], 3)); ndf.append(int(f["ndf"])); chi2n.append(round(f["chi2_ndf"], 4))
            pval.append(round(row[0]["p"], 4) if row else 0.0)
            chosen_flag.append(1 if fs["chosen_nparams"] == npar else 0)
    t.add_variable(category_x("Category", cats))
    nx = Variable("Number of fit parameters", is_independent=True, is_binned=False)
    nx.values = npars
    t.add_variable(nx)
    for name, vals in (("chi2 (Poisson deviance)", chi2), ("ndf", ndf), ("chi2/ndf", chi2n),
                       ("F-test p-value for n+1 parameters", pval), ("Chosen (1=yes)", chosen_flag)):
        t.add_variable(y_var(name, vals, zero_ok=True, qualifiers={"SQRT(S)": f"{SQRTS_GEV:g} GeV"}))
    sub.add_table(t)

    # 4. b-tag efficiency vs Z' mass
    rows = summary["btag_efficiency"]
    t = new_table("btag efficiency vs Zprime mass",
                  "DeepJet (2016postVFP_UL working points) b-tagging efficiency for true b jets (hadronFlavour 5) among the two "
                  "selected jets of Z'->bb (narrow) MC, |deta|<1.1, no scale factors. Event efficiencies for the categories at "
                  "Medium relative to all generated events (include m_jj threshold and acceptance).",
                  ["btag_efficiency_vs_mass"], ["EFF"], P, "Data from plots/btag_efficiency_vs_mass.png (validation/dijet-2016).")
    x = Variable("Z' mass", is_independent=True, is_binned=False, units="GeV")
    x.values = [float(r["mass"]) for r in rows]
    t.add_variable(x)
    for k, nm in (("L", "Loose"), ("M", "Medium"), ("T", "Tight")):
        v = y_var(f"b-tag efficiency {nm}", [round(r[f"eff_{k}"], 5) for r in rows], zero_ok=True,
                  qualifiers={"SQRT(S)": f"{SQRTS_GEV:g} GeV"})
        add_asym(v, "stat (Clopper-Pearson)", [round(r[f"eff_{k}_lo"], 5) for r in rows], [round(r[f"eff_{k}_hi"], 5) for r in rows])
        t.add_variable(v)
    for c in ("1b", "2b"):
        v = y_var(f"Event efficiency {c} Medium", [round(r[f"event_eff_{c}_medium"], 5) for r in rows], zero_ok=True)
        add_sym(v, "stat", [round(r[f"event_eff_{c}_medium_err"], 5) for r in rows])
        t.add_variable(v)
    sub.add_table(t)

    # 5. signal injection: string category + scan factor k (no encoded integer index)
    inj = summary["injection"]
    t = new_table("Signal injection",
                  f"Injection of a Z' (M = {inj['1b']['mass']} GeV, MC shape) into the data spectrum and recovery with a signal+background "
                  "fit. The scan factor k multiplies the nominal injected yield (about 3 sigma of the background in the signal window); "
                  "the injected number of events is a Poisson draw of k times the nominal yield.",
                  ["injection_linearity_1b", "injection_linearity_2b"], ["N"], P,
                  "Data from summary.json (injection) and plots/injection_linearity_*.png (validation/dijet-2016).")
    cats, ks, injv, rec, err = [], [], [], [], []
    for cat in ("1b", "2b"):
        for e_ in inj[cat]["scan"]:
            cats.append(cat); ks.append(float(e_["k"])); injv.append(e_["S_injected_actual"])
            rec.append(round(e_["S_recovered"], 3)); err.append(round(e_["S_err"], 3))
    t.add_variable(category_x("Category", cats))
    kx = Variable("Injection scale factor k", is_independent=True, is_binned=False)
    kx.values = ks
    t.add_variable(kx)
    t.add_variable(y_var("Injected events", injv, units="Events", zero_ok=True))
    v = y_var("Recovered signal yield", rec, units="Events", zero_ok=True)
    add_sym(v, "fit (HESSE)", err)
    t.add_variable(v)
    sub.add_table(t)


def _binned_subset(edges, keep):
    """Bins (edges[i], edges[i+1]) for i in keep; a dropped bin leaves a gap, which HEPData allows."""
    v = Variable("$m_{jj}$", is_independent=True, is_binned=True, units="GeV")
    v.values = [(edges[i], edges[i + 1]) for i in keep]
    return v


# ----------------------------------------------------------------------------- main

def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-o", "--outdir", default="hepdata", help="output directory (replaced)")
    ap.add_argument("--summary", required=True, help="summary.json written by analysis.py")
    ap.add_argument("--plots", required=True, help="directory with the PDF plots attached to the tables")
    ap.add_argument("--log", default=None, help="also write the validator output to this file")
    args = ap.parse_args(argv)

    sub = Submission()
    build(sub, args)
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
    # run the validator from inside outdir so the log has no absolute paths
    res = subprocess.run(["hepdata-validate", "-d", "."], cwd=outdir, capture_output=True, text=True)
    print(res.stdout.strip(), file=sys.stderr)
    if args.log:
        with open(args.log, "w") as f:
            f.write(f"hepdata-validate exit code {res.returncode}\n{res.stdout}{res.stderr}")
    print(f"TABLES={len(sub.tables)}")
    print(f"OUTDIR={args.outdir}")
    print(f"VALID={int(res.returncode == 0)}")
    return 0 if res.returncode == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
