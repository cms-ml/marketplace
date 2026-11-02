"""Helpers for the dijet validation: loading skims, binning, dijet-function fits (iminuit 2.x).

Units: GeV. Imported by analysis.py. Environment: LCG_109 view.
"""
import gzip
import json
import re
import numpy as np
from iminuit import Minuit
from scipy import stats

SQRTS = 13000.0

# CMS dijet binning (resolution-motivated variable bins, GeV)
DIJET_EDGES = np.array([
    1, 3, 6, 10, 16, 23, 31, 40, 50, 61, 74, 88, 103, 119, 137, 156, 176, 197, 220, 244, 270, 296, 325,
    354, 386, 419, 453, 489, 526, 565, 606, 649, 693, 740, 788, 838, 890, 944, 1000, 1058, 1118, 1181,
    1246, 1313, 1383, 1455, 1530, 1607, 1687, 1770, 1856, 1945, 2037, 2132, 2231, 2332, 2438, 2546, 2659,
    2775, 2895, 3019, 3147, 3279, 3416, 3558, 3704, 3854, 4010, 4171, 4337, 4509, 4686, 4869, 5058, 5253,
    5455, 5663, 5877, 6099, 6328, 6564, 6808, 7060, 7320, 7589, 7866, 8152, 8447, 8752, 9067, 9391, 9726,
    10072, 10430, 10798, 11179, 11571, 11977, 12395, 12827, 13272, 13732, 14000], dtype=float)

WP = {"L": 0.048, "M": 0.2489, "T": 0.6377}   # overwritten from the BTV POG json by analysis.py

# ---------------------------------------------------------------- inputs

def sample_name(url):
    if "/Run2016G/JetHT/" in url or "/Run2016H/JetHT/" in url:
        return "data"
    m = re.search(r"ZprimeToBB_narrow_M-(\d+)_", url)
    if m:
        return f"sig_{m.group(1)}"
    m = re.search(r"QCD_HT([0-9a-zA-Z]+)_TuneCP5_PSWeights", url)
    if m:
        return f"qcd_{m.group(1)}"
    raise ValueError(url)


def read_meta(paths):
    """Per-sample metadata from all skims (no event arrays): files, n_total, sumw, processed (run, ls) keys."""
    infos = {}
    first = None
    for p in paths:
        d = np.load(p)
        info = json.loads(str(d["info"]))
        first = first or info
        for f in info["files"]:
            s = sample_name(f["url"])
            I = infos.setdefault(s, {"files": [], "n_total": 0, "n_sel": 0, "sumw": 0.0, "ls": []})
            I["files"].append(f["url"]); I["n_total"] += f["n_total"]; I["n_sel"] += f["n_sel"]; I["sumw"] += f["sumw"]
        if "data" in {sample_name(f["url"]) for f in info["files"]}:
            infos["data"]["ls"].append(d["ls_keys"])
    for s, I in infos.items():
        I["ls"] = np.unique(np.concatenate(I["ls"])) if I["ls"] else np.zeros(0, np.int64)
        if len(set(I["files"])) != len(I["files"]):
            raise RuntimeError(f"duplicate input files for {s}")
    return infos, first


def iter_events(paths, cols, mjj_min, golden=None, only=None):
    """Stream the skims one .npz at a time (memory!). Yields (sample, arrays, n_before_golden, n_after_golden).

    cols: column names to return. mjj_min: dict sample-kind ('data','sig','qcd') -> minimum m_jj (GeV).
    golden: sorted array of valid run*100000+lumi keys, applied to data only. only: restrict to a sample kind.
    """
    for p in paths:
        d = np.load(p)
        info = json.loads(str(d["info"]))
        samples = np.array([sample_name(f["url"]) for f in info["files"]])
        fidx = d["file_idx"]
        mjj = d["mjj"]
        for s in np.unique(samples):
            kind = s.split("_")[0]
            if only and kind != only:
                continue
            m = (samples[fidx] == s) & (mjj >= mjj_min.get(kind, 0.0))
            nb = int(m.sum())
            if golden is not None and kind == "data":
                key = d["run"][m].astype(np.int64) * 100000 + d["lumi"][m].astype(np.int64)
                ok = np.isin(key, golden)
                idx = np.flatnonzero(m)[ok]
                m = np.zeros(len(mjj), bool); m[idx] = True
            out = {c: d[c][m] for c in cols if c in d.files}
            yield s, out, nb, int(m.sum())


def load_events(paths, cols, mjj_min, golden=None):
    chunks = {}
    for s, out, nb, na in iter_events(paths, cols, mjj_min, golden):
        for k, v in out.items():
            chunks.setdefault(s, {}).setdefault(k, []).append(v)
    return {s: {k: np.concatenate(v) for k, v in c.items()} for s, c in chunks.items()}


def golden_keys(path):
    j = json.load(open(path))
    ks = []
    for run, ivs in j.items():
        for a, b in ivs:
            ks.append(int(run) * 100000 + np.arange(a, b + 1, dtype=np.int64))
    return np.unique(np.concatenate(ks))


def recorded_lumi_fb(csv_path, keys):
    """Sum of the 'recorded' column (/fb) over the given run*100000+ls keys."""
    runs, lss, rec = [], [], []
    for line in open(csv_path):
        if line.startswith("#"):
            continue
        c = line.strip().split(",")
        runs.append(int(c[0].split(":")[0])); lss.append(int(c[1].split(":")[0])); rec.append(float(c[6]))
    k = np.array(runs, dtype=np.int64) * 100000 + np.array(lss, dtype=np.int64)
    rec = np.array(rec)
    m = np.isin(k, keys)
    return float(rec[m].sum()), int(m.sum()), int(len(keys))


# ---------------------------------------------------------------- stats helpers

def clopper_pearson(k, n, cl=0.6827):
    k = np.asarray(k, float); n = np.asarray(n, float)
    a = (1 - cl) / 2
    lo = np.where(k > 0, stats.beta.ppf(a, k, n - k + 1), 0.0)
    hi = np.where(k < n, stats.beta.ppf(1 - a, k + 1, n - k), 1.0)
    with np.errstate(invalid="ignore", divide="ignore"):
        eff = np.where(n > 0, k / n, np.nan)
    return eff, lo, hi


def asimov_z(s, b):
    return np.sqrt(2 * ((s + b) * np.log1p(s / b) - s))


# ---------------------------------------------------------------- dijet function and fits

_GL_X, _GL_W = np.polynomial.legendre.leggauss(6)


def dijet_f(m, lnp0, p1, p2, p3=0.0, p4=0.0):
    """p0 (1-x)^p1 / x^(p2 + p3 ln x + p4 ln^2 x), x = m/sqrt(s). Returns density per GeV (p0 = exp(lnp0))."""
    x = m / SQRTS
    L = np.log(x)
    return np.exp(lnp0 + p1 * np.log1p(-x) - (p2 + p3 * L + p4 * L * L) * L)


def bin_integral(edges, *pars):
    lo, hi = edges[:-1, None], edges[1:, None]
    mid, half = 0.5 * (hi + lo), 0.5 * (hi - lo)
    m = mid + half * _GL_X[None, :]
    return (dijet_f(m, *pars) * _GL_W[None, :]).sum(1) * half[:, 0]


def deviance(n, mu):
    mu = np.maximum(mu, 1e-12)
    term = np.where(n > 0, n * np.log(np.where(n > 0, n, 1) / mu), 0.0)
    return 2.0 * np.sum(mu - n + term)


def signed_pulls(n, mu):
    mu = np.maximum(mu, 1e-12)
    term = np.where(n > 0, n * np.log(np.where(n > 0, n, 1) / mu), 0.0)
    d = np.maximum(2.0 * (mu - n + term), 0.0)
    return np.sign(n - mu) * np.sqrt(d)


PNAMES = ["lnp0", "p1", "p2", "p3", "p4"]


def _start(edges, n):
    """Weighted least-squares start values in log space (3 parameters)."""
    from scipy.optimize import curve_fit
    c = 0.5 * (edges[1:] + edges[:-1]); w = np.diff(edges)
    ok = n > 0
    y = np.log(n[ok] / w[ok])
    sig = 1.0 / np.sqrt(n[ok])
    def f(m, lnp0, p1, p2):
        return dijet_f(m, lnp0, p1, p2)
    try:
        p, _ = curve_fit(f, c[ok], y, p0=[np.log(max(n.sum(), 1) / w.sum()) + 10, 10.0, 5.0], sigma=sig, maxfev=20000)
    except Exception:
        p = np.array([np.log(max(n.sum(), 1) / w.sum()) + 10, 10.0, 5.0])
    return list(p)


def fit_background(edges, n, npar, start=None, signal_template=None, s_start=0.0):
    """Binned Poisson-likelihood fit of the dijet function with npar in {3,4,5} (p0 counts).

    If signal_template (unit-sum array per bin) is given, a free signal yield S is added.
    Returns dict(par, err, mu, dev, ndf, valid, S, S_err, edm).
    """
    n = np.asarray(n, float)
    npar = int(npar)
    st = list(start) if start is not None else _start(edges, n)
    st = (st + [0.0, 0.0])[:5]
    for i in range(npar, 5):
        st[i] = 0.0
    T = None if signal_template is None else np.asarray(signal_template, float)

    def _nll(mu):
        mu = np.maximum(mu, 1e-12)
        return float(np.sum(mu - n * np.log(mu)))

    def nll_b(lnp0, p1, p2, p3, p4):
        return _nll(bin_integral(edges, lnp0, p1, p2, p3, p4))

    def nll_s(lnp0, p1, p2, p3, p4, S):
        return _nll(bin_integral(edges, lnp0, p1, p2, p3, p4) + S * T)

    def make(s):
        if T is None:
            m = Minuit(nll_b, lnp0=s[0], p1=s[1], p2=s[2], p3=s[3], p4=s[4])
        else:
            m = Minuit(nll_s, lnp0=s[0], p1=s[1], p2=s[2], p3=s[3], p4=s[4], S=s_start)
        m.errordef = Minuit.LIKELIHOOD
        for i in range(npar, 5):
            m.fixed[PNAMES[i]] = True
        m.strategy = 2
        return m

    best = None
    rng = np.random.default_rng(1)
    for attempt in range(6):
        s = list(st) if attempt == 0 else [v + rng.normal(0, 0.3 * (abs(v) + 1)) * (i < npar) for i, v in enumerate(st)]
        m = make(s)
        m.simplex(ncall=4000)
        m.migrad(ncall=20000)
        m.migrad(ncall=20000)
        if best is None or m.fval < best.fval - 1e-9 or (m.valid and not best.valid):
            best = m
        if m.valid:
            break
    m = best
    par = [m.values[k] for k in PNAMES]
    mu_b = bin_integral(edges, *par)
    S = float(m.values["S"]) if T is not None else 0.0
    mu = mu_b + (S * T if T is not None else 0)
    nfree = npar + (1 if T is not None else 0)
    try:
        err = [m.errors[k] for k in PNAMES]
    except Exception:
        err = [np.nan] * 5
    return dict(par=par, err=err, mu=mu, mu_b=mu_b, dev=deviance(n, mu), ndf=len(n) - nfree,
                valid=bool(m.valid), S=S, S_err=float(m.errors["S"]) if T is not None else 0.0,
                edm=float(m.fmin.edm), npar=npar)


def ftest(devs, npars, ndf_bins):
    """Nested F-tests between consecutive fits. devs/npars lists ordered by npar."""
    rows = []
    for i in range(len(devs) - 1):
        d1, d2 = devs[i], devs[i + 1]
        dp = npars[i + 1] - npars[i]
        ndf2 = ndf_bins - npars[i + 1]
        F = ((d1 - d2) / dp) / (d2 / ndf2) if d2 > 0 else np.inf
        F = max(F, 0.0)
        p = float(stats.f.sf(F, dp, ndf2))
        rows.append(dict(n_from=npars[i], n_to=npars[i + 1], chi2_from=d1, chi2_to=d2, F=float(F), p=p))
    return rows
