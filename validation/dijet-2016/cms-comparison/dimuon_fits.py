"""Binned Poisson-likelihood peak fits used by M1 and M2 (iminuit): Crystal Ball signals + smooth background, Voigt for the Z.

All signal yields are integrated over each bin (CDF differences), so the 10-25 MeV (J/psi, Upsilon) and 1 GeV (Z) bins are treated exactly.
"""
import numpy as np
from iminuit import Minuit
from scipy import special, stats


def cb_counts(edges, N, mu, sigma, alpha, n):
    """expected counts per bin of N * CrystalBall (scipy crystalball: tail on the low side for alpha>0)."""
    c = stats.crystalball.cdf(edges, alpha, n, loc=mu, scale=sigma)
    return N * np.diff(c)


def gauss_counts(edges, N, mu, sigma):
    return N * np.diff(stats.norm.cdf(edges, mu, sigma))


def voigt_counts(edges, N, mu, sigma, gamma_fwhm, ngrid=8):
    """N * integral over each bin of the Voigt profile (BW with FWHM gamma convolved with Gaussian sigma); Simpson-like sub-sampling."""
    lo, hi = edges[:-1], edges[1:]
    xs = (np.arange(ngrid) + 0.5) / ngrid
    x = lo[:, None] + (hi - lo)[:, None] * xs[None, :]
    f = special.voigt_profile(x - mu, sigma, gamma_fwhm / 2.0)
    return N * f.mean(1) * (hi - lo)


def exp_poly_counts(edges, coefs, x0):
    """exp(c0 + c1 u + c2 u^2 + ...) per GeV, u = (m - x0)/(range), integrated with 4-point Gauss-Legendre per bin."""
    xg, wg = np.polynomial.legendre.leggauss(4)
    lo, hi = edges[:-1], edges[1:]
    mid, half = 0.5 * (hi + lo), 0.5 * (hi - lo)
    m = mid[:, None] + half[:, None] * xg[None, :]
    u = (m - x0[0]) / x0[1]
    poly = sum(c * u ** i for i, c in enumerate(coefs))
    return (np.exp(poly) * wg[None, :]).sum(1) * half


def deviance(n, mu):
    mu = np.maximum(mu, 1e-12)
    t = np.where(n > 0, n * np.log(np.where(n > 0, n, 1) / mu), 0.0)
    return float(2.0 * np.sum(mu - n + t))


def run_fit(model, n, par0, limits=None, fixed=(), edges=None, retries=4):
    """model(**params) -> expected counts. Returns Minuit object and summary dict."""
    def nll(*p):
        mu = np.maximum(model(*p), 1e-12)
        return float(np.sum(mu - n * np.log(mu)))
    names = list(par0)
    best = None
    rng = np.random.default_rng(3)
    for k in range(retries):
        start = dict(par0)
        if k > 0:
            for nm in names:
                start[nm] = par0[nm] * (1 + rng.normal(0, 0.02)) if par0[nm] != 0 else rng.normal(0, 0.01)
        m = Minuit(nll, *[start[k_] for k_ in names], name=names)
        m.errordef = Minuit.LIKELIHOOD
        for k_, (lo, hi) in (limits or {}).items():
            m.limits[k_] = (lo, hi)
        for k_ in fixed:
            m.fixed[k_] = True
        m.strategy = 2
        m.simplex(ncall=5000)
        m.migrad(ncall=20000)
        m.hesse()
        if best is None or (m.valid and (not best.valid or m.fval < best.fval)) or (m.fval < best.fval - 1e-6 and m.valid == best.valid):
            best = m
        if m.valid and m.accurate:
            break
    mu = model(*[best.values[k_] for k_ in names])
    nfree = sum(1 for k_ in names if not best.fixed[k_])
    dev = deviance(n, mu)
    return best, dict(deviance=dev, ndf=len(n) - nfree, valid=bool(best.valid), mu=mu, nfree=nfree)


def mix_counts(edges, N, mu, sigma, f, r, alpha, n):
    """N * [ f CrystalBall(mu, sigma, alpha, n) + (1-f) Gauss(mu, r*sigma) ] per bin: core with a radiative/non-Gaussian tail plus a wide Gaussian."""
    return N * (f * np.diff(stats.crystalball.cdf(edges, alpha, n, loc=mu, scale=sigma)) + (1 - f) * np.diff(stats.norm.cdf(edges, mu, r * sigma)))


def sigma_eff(sigma, f, r):
    """RMS-like effective width of the mixture without the CB tail: sqrt(f sigma^2 + (1-f) (r sigma)^2)."""
    return sigma * np.sqrt(f + (1 - f) * r * r)


def bw_conv_mix_counts(edges, N, delta, sigma, f, r, alpha, n, m0, gamma, step=0.2, pad=12.0):
    """N * [Breit-Wigner(m0 fixed, FWHM gamma) convolved with the response f CB(delta, sigma, alpha, n) + (1-f) Gauss(delta, r sigma)] per bin.
    delta is the shift of the response core (detector-level mass-scale offset in GeV); numerical convolution on a 0.2 GeV grid (bins are 1 GeV, core sigma >~ 1 GeV)."""
    g = np.arange(edges[0] - pad, edges[-1] + pad + 1e-9, step)
    bw = (gamma / 2 / np.pi) / ((g - m0) ** 2 + (gamma / 2) ** 2) * step                # BW weight per grid point (sums to ~1 over a wide range)
    x = np.arange(edges[0], edges[-1] + 1e-9, step) + step / 2                           # evaluation points (bin sub-sampling)
    d = x[:, None] - g[None, :]
    resp = f * stats.crystalball.pdf(d, alpha, n, loc=delta, scale=sigma) + (1 - f) * stats.norm.pdf(d, delta, r * sigma)
    dens = resp @ bw                                                                      # density per GeV at x
    idx = np.digitize(x, edges) - 1
    ok = (idx >= 0) & (idx < len(edges) - 1)
    out = np.bincount(idx[ok], weights=dens[ok] * step, minlength=len(edges) - 1)
    return N * out
