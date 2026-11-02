"""Shared helpers for the CMS-comparison scripts (HEPData reading, statistics, plotting, result bookkeeping).

Every compare_*.py takes the scratch cache directory (HEPData records, PDG json, histograms) as an argument;
nothing is read from or written to a personal path.  Environment: LCG_109 view (numpy, scipy, iminuit, hist,
mplhep, PyYAML).
"""
import json
import os
import sys

sys.dont_write_bytecode = True      # never leave __pycache__ in the (read-only) student directories we import from
import tarfile
import urllib.request
from pathlib import Path

import numpy as np
import yaml
from scipy import stats

HERE = Path(__file__).resolve().parent
STUDENT_DIR = HERE.parent                      # validation/dijet-2016
PLOTDIR = HERE / "plots"
RESDIR = HERE / "results"                      # one json per test, assembled by make_comparison.py
PLOTDIR.mkdir(exist_ok=True)
RESDIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------------------- HEPData access
HEPDATA_URL = "https://www.hepdata.net/download/submission/ins{ins}/1/yaml"   # returns a gzipped tar, despite 'yaml'


def fetch(url, dest, timeout=120):
    dest = Path(dest)
    if not dest.exists() or dest.stat().st_size == 0:
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "cms-results-validator"})
        with urllib.request.urlopen(req, timeout=timeout) as r, open(dest, "wb") as f:
            f.write(r.read())
    return dest


def hepdata_dir(cache, ins):
    """Download (once) and unpack HEPData record ins<ins> v1 into <cache>/ins<ins>/; returns the directory with the yaml files."""
    top = Path(cache) / f"ins{ins}"
    out = top / f"HEPData-ins{ins}-v1-yaml"
    if not (out / "submission.yaml").exists():
        tgz = fetch(HEPDATA_URL.format(ins=ins), top / "rec.tar.gz")
        with tarfile.open(tgz) as t:
            t.extractall(top, filter="data")
    return out


def table_file(rec_dir, table_name):
    """Map a HEPData table name ('Figure 3 first row first column') to its yaml file through submission.yaml."""
    docs = list(yaml.safe_load_all(open(Path(rec_dir) / "submission.yaml")))
    for t in docs[1:]:
        if t["name"] == table_name:
            return Path(rec_dir) / t["data_file"], t
    raise KeyError(table_name)


def read_table(rec_dir, table_name):
    """Return dict: indep = list of dict(name, units, low, high, value arrays); dep = list of dict(name, units,
    qualifiers, value, stat (symmetrical errors or nan), err_labels, errors (label -> array)); meta = submission entry."""
    f, meta = table_file(rec_dir, table_name)
    d = yaml.safe_load(open(f))
    indep = []
    for iv in d["independent_variables"]:
        vals = iv["values"]
        lo = np.array([v.get("low", np.nan) for v in vals], float)
        hi = np.array([v.get("high", np.nan) for v in vals], float)
        va = np.array([v.get("value", np.nan) if not isinstance(v.get("value", np.nan), str) else np.nan for v in vals], float)
        indep.append({"name": iv["header"]["name"], "units": iv["header"].get("units", ""), "low": lo, "high": hi, "value": va,
                      "raw": vals})
    dep = []
    for dv in d["dependent_variables"]:
        vals = dv["values"]
        v = np.array([x["value"] if not isinstance(x["value"], str) else np.nan for x in vals], float)
        errs = {}
        for i, x in enumerate(vals):
            for e in x.get("errors", []) or []:
                lab = e.get("label", "")
                arr = errs.setdefault(lab, np.full(len(vals), np.nan))
                if "symerror" in e:
                    se = e["symerror"]
                    if isinstance(se, str) and se.endswith("%"):
                        se = float(se[:-1]) / 100.0 * v[i]          # relative error given in percent
                    arr[i] = float(se)
                elif "asymerror" in e:
                    arr[i] = 0.5 * (abs(e["asymerror"]["plus"]) + abs(e["asymerror"]["minus"]))
        dep.append({"name": dv["header"]["name"], "units": dv["header"].get("units", ""), "qualifiers": dv.get("qualifiers"),
                    "value": v, "errors": errs, "raw": vals})
    return {"indep": indep, "dep": dep, "meta": meta, "file": str(f.name)}


# ---------------------------------------------------------------------------------------- statistics
def pvalue(chi2, ndf):
    return float(stats.chi2.sf(chi2, ndf)) if ndf > 0 else float("nan")


def nsigma(p):
    """two-sided Gaussian-equivalent significance of a p-value"""
    p = max(float(p), 1e-300)
    return float(stats.norm.isf(p / 2))


def two_sample_chi2(n1, n2):
    """Pearson chi2 for homogeneity of two unnormalised histograms (shape comparison, counts with Poisson errors).
    chi2 = sum (sqrt(N2/N1) n1 - sqrt(N1/N2) n2)^2 / (n1+n2), ndf = nbins - 1 (bins with n1+n2 = 0 dropped)."""
    n1 = np.asarray(n1, float)
    n2 = np.asarray(n2, float)
    ok = (n1 + n2) > 0
    n1, n2 = n1[ok], n2[ok]
    N1, N2 = n1.sum(), n2.sum()
    chi2 = np.sum((np.sqrt(N2 / N1) * n1 - np.sqrt(N1 / N2) * n2) ** 2 / (n1 + n2))
    return float(chi2), int(len(n1) - 1)


def merge_high_bins(edges, arrays, min_counts, arrays_for_threshold):
    """Merge neighbouring bins from the high-mass end until every merged bin has >= min_counts in every array of
    arrays_for_threshold. Returns new edges and merged arrays (sums)."""
    edges = list(edges)
    arrs = [np.asarray(a, float).copy() for a in arrays]
    thr = [np.asarray(a, float).copy() for a in arrays_for_threshold]
    i = len(edges) - 2
    out_e = [edges[-1]]
    out_a = [[] for _ in arrs]
    cur_a = [0.0] * len(arrs)
    cur_t = [0.0] * len(thr)
    for i in range(len(edges) - 2, -1, -1):
        for k in range(len(arrs)):
            cur_a[k] += arrs[k][i]
        for k in range(len(thr)):
            cur_t[k] += thr[k][i]
        if all(c >= min_counts for c in cur_t):
            for k in range(len(arrs)):
                out_a[k].append(cur_a[k])
            out_e.append(edges[i])
            cur_a = [0.0] * len(arrs)
            cur_t = [0.0] * len(thr)
    if any(c > 0 for c in cur_a) and out_a[0]:          # remainder at the low edge goes into the lowest merged bin
        for k in range(len(arrs)):
            out_a[k][-1] += cur_a[k]
        out_e[-1] = edges[0]
    return np.array(out_e[::-1]), [np.array(a[::-1]) for a in out_a]


def ratio_slope(x, r, err):
    """weighted linear fit r = a + b (x - xmean); returns a, b, err_b, chi2 of the fit, and chi2 of r = const(=1) and of r = const (free)."""
    x = np.asarray(x, float)
    r = np.asarray(r, float)
    w = 1.0 / np.asarray(err, float) ** 2
    xm = np.sum(w * x) / np.sum(w)
    X = np.vstack([np.ones_like(x), x - xm]).T
    A = X.T @ (w[:, None] * X)
    cov = np.linalg.inv(A)
    beta = cov @ (X.T @ (w * r))
    chi2_lin = float(np.sum(w * (r - X @ beta) ** 2))
    c0 = np.sum(w * r) / np.sum(w)
    chi2_const = float(np.sum(w * (r - c0) ** 2))
    chi2_one = float(np.sum(w * (r - 1.0) ** 2))
    return dict(a=float(beta[0]), b=float(beta[1]), b_err=float(np.sqrt(cov[1, 1])), xmean=float(xm), chi2_lin=chi2_lin,
                chi2_const=chi2_const, c0=float(c0), c0_err=float(np.sqrt(1 / np.sum(w))), chi2_one=chi2_one)


# ---------------------------------------------------------------------------------------- results
def save_result(tid, **kw):
    """Write results/<tid>.json  (keys follow comparison.json: id, student_result, counterpart, level, statistic, ndf,
    p_value, ratio, verdict, reason, + free extra keys)."""
    kw = {"id": tid, **kw}

    def clean(o):
        if isinstance(o, dict):
            return {k: clean(v) for k, v in o.items()}
        if isinstance(o, (list, tuple)):
            return [clean(v) for v in o]
        if isinstance(o, (np.floating, float)):
            return None if not np.isfinite(o) else float(o)
        if isinstance(o, (np.integer,)):
            return int(o)
        if isinstance(o, np.ndarray):
            return clean(o.tolist())
        return o

    with open(RESDIR / f"{tid}.json", "w") as f:
        json.dump(clean(kw), f, indent=1)
    return kw


# ---------------------------------------------------------------------------------------- plotting
def setup_mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import mplhep as hep
    plt.style.use(hep.style.CMS)
    return plt, hep


def savefig(fig, name):
    for ext in ("png", "pdf"):
        fig.savefig(PLOTDIR / f"{name}.{ext}", bbox_inches="tight", dpi=120 if ext == "png" else None)
    import matplotlib.pyplot as plt
    plt.close(fig)


def open_data_label(ax, hep, lumi=None, com=13, fontsize=None):
    kw = {} if fontsize is None else {"fontsize": fontsize}
    hep.cms.label("Open Data", data=True, ax=ax, lumi=lumi, com=com, **kw)


def log(*a):
    print(*a, flush=True)
