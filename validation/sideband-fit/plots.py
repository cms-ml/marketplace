"""Render the sideband fits and pseudoexperiment diagnostics."""

import hist
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import mplhep as hep
import numpy as np
from scipy.stats import gamma, norm

from fit_sidebands import deviance_residual


def save(fig, path):
    for extension in ("pdf", "png"):
        fig.savefig(path.with_suffix(f".{extension}"), dpi=150)
    plt.close(fig)


def fit_plot(name, edges, counts, fit, intervals, info, path):
    h = hist.Hist(hist.axis.Variable(edges, label=r"$m_{\mu\mu}$ [GeV]"), storage=hist.storage.Int64())
    h.view()[...] = counts
    edges, centers, n = h.axes[0].edges, h.axes[0].centers, h.values()
    spacing = h.axes[0].widths
    count_scale = spacing if name == "continuum" else np.ones_like(spacing)
    prediction = fit["prediction"]
    uncertainty = np.sqrt(np.diag(fit["prediction_covariance"]))
    band_low = prediction * np.exp(-uncertainty / prediction) / count_scale
    band_high = prediction * np.exp(uncertainty / prediction) / count_scale
    density = prediction / count_scale
    positive = n > 0
    alpha = norm.cdf(-1)
    down = np.zeros_like(n, dtype=float)
    down[positive] = gamma.ppf(alpha, n[positive])
    up = gamma.isf(alpha, n + 1)
    yerr = np.array([n - down, up - n]) / count_scale

    plt.style.use(hep.style.CMS)
    fig, (ax, rax) = plt.subplots(2, 1, sharex=True, figsize=(9, 8),
                                 gridspec_kw={"height_ratios": [3, 1], "hspace": 0.08})
    fig.subplots_adjust(left=0.16, right=0.975, top=0.89, bottom=0.13)
    for index, (lo, hi) in enumerate(intervals):
        label = "Excluded from fit" if index == 0 else None
        ax.axvspan(lo, hi, facecolor="#695d75", alpha=0.14, label=label, zorder=0)
        rax.axvspan(lo, hi, facecolor="#695d75", alpha=0.14, zorder=0)
    ax.fill_between(edges, np.r_[band_low, band_low[-1]], np.r_[band_high, band_high[-1]],
                    step="post", color="#ef4646", alpha=0.23, linewidth=0,
                    label="68% fitted mean band")
    ax.stairs(density, edges, color="#c12323", lw=1.8, label=f"Sideband fit (order {fit['order']})")
    visible = positive if name == "continuum" else np.ones_like(positive)
    ax.errorbar(centers[visible], n[visible] / count_scale[visible], yerr=yerr[:, visible],
                color="black", fmt="o", markersize=3, lw=0.8, label="Data")
    if name == "continuum":
        ax.plot(centers[~positive], up[~positive] / count_scale[~positive], "v", color="black",
                fillstyle="none", markersize=4, label="Zero-bin upper endpoint")
        rax.set_xscale("log")
        ax.set_yscale("log")
        ax.set_ylim(band_low.min() * 0.6, density.max() * 3)
        ax.set_ylabel("Events / GeV")
        hep.cms.label("Open Data", data=True, lumi=round(info["luminosity_fb"], 1), com=13, ax=ax)
        rax.set_xticks([300, 500, 1000, 2000, 6000],
                       ["300", "500", "1000", "2000", "6000"])
        rax.get_xticklabels()[-1].set_ha("right")
    else:
        ax.set_ylim(0, up.max() * 1.30)
        ax.set_ylabel("Events / 0.02 GeV")
        hep.cms.label("Open Data", data=True, rlabel="Workshop dimuons", ax=ax)
    ax.legend(loc="upper right", fontsize=13, labelspacing=0.3)
    annotation_y = 0.66 if name == "continuum" else 0.53
    ax.text(0.97, annotation_y, f"Sideband deviance / ndf = {fit['deviance']:.1f} / {fit['ndf']}",
            ha="right", fontsize=12, transform=ax.transAxes)

    residuals = deviance_residual(n, prediction)
    lim = max(3.65, 0.3 + np.max(np.abs(residuals))) if name == "continuum" else 3.65
    clipped = np.clip(residuals, -lim + 0.35, lim - 0.35)
    rax.axhline(0, color="0.45", lw=0.9)
    rax.stairs(clipped, edges, baseline=None, color="#224c72", lw=1.2)
    for side, marker in ((1, "^"), (-1, "v")):
        outside = side * residuals > lim - 0.35
        rax.plot(centers[outside], clipped[outside], ls="", marker=marker,
                 color="#224c72", markersize=4)
    rax.set_ylim(-lim, lim)
    rax.set_ylabel("Deviance\nresidual", fontsize=16)
    rax.set_xlabel(h.axes[0].label)
    ax.set_xlim(edges[0], edges[-1])
    save(fig, path)


def toy_plot(samples, path):
    plt.style.use(hep.style.CMS)
    fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
    fig.subplots_adjust(left=0.11, right=0.98, top=0.82, bottom=0.12, wspace=0.25, hspace=0.32)
    panel_names = {"linear": "Linear truth", "quadratic": "Quadratic truth",
                   "smooth_mixture": "Two-shape mixture", "broad_modulation": "Broad modulation"}
    extent = max(5, np.ceil(max(abs(value) for scenario in samples.values()
                                 for series in scenario.values() for value in series)))
    bins = np.arange(-extent, extent + 0.25, 0.25)
    x = np.linspace(-extent, extent, 150)
    ymax = 0.5
    for ax, (key, title) in zip(axes.ravel(), panel_names.items()):
        for kind, injected, color, style, label in (
            ("background", 0, "#28558a", "-", "Background, 0 injected"),
            ("signal", 0, "#bc2d34", "-", "Signed signal, 0 injected"),
            ("signal", 45, "#bc2d34", "--", "Signed signal, 45 injected"),
        ):
            values = samples[f"{key}_inject_{injected}"][kind]
            h = hist.Hist(hist.axis.Variable(bins), storage=hist.storage.Int64()).fill(values)
            density = h.values() / (len(values) * h.axes[0].widths)
            ymax = max(ymax, density.max() * 1.10)
            hep.histplot(density, bins, color=color, linestyle=style, lw=1.5,
                         histtype="step", ax=ax, label=label)
        ax.plot(x, norm.pdf(x), color="0.5", lw=1, ls=":")
        ax.set_title(title, loc="left", pad=7, fontsize=16)
        ax.set_xlim(-extent, extent)
    for ax in axes.ravel():
        ax.set_ylim(0, ymax)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, fontsize=11, loc="upper center", bbox_to_anchor=(0.53, 0.912), ncol=3)
    for ax in axes[:, 0]:
        ax.set_ylabel("Probability density", fontsize=18)
    for ax in axes[1]:
        ax.set_xlabel(r"$(\hat{y}-y_{\mathrm{true}})/\sigma_{\hat y}$", fontsize=18)
    fig.text(0.11, 0.96, "Pseudoexperiments", fontsize=24, weight="bold")
    fig.text(0.98, 0.96, "Sideband AIC selection", fontsize=16, ha="right")
    save(fig, path)
