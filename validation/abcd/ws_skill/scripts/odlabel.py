"""Plot header for Open Data plots: plain 'CMS Open Data, private work' (no CMS logo) and the luminosity."""


def label(ax, data=True, lumi=16.3):
    tag = "CMS Open Data, private work" + ("" if data else " (QCD simulation)")
    ax.text(0.0, 1.01, tag, transform=ax.transAxes, ha="left", va="bottom", fontsize=12, fontweight="bold")
    ax.text(1.0, 1.01, f"{lumi} fb$^{{-1}}$ (13 TeV)", transform=ax.transAxes, ha="right", va="bottom", fontsize=12)
