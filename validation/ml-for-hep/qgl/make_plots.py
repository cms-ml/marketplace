#!/usr/bin/env python3
"""BDT score train vs test, feature importance, and gluon pT before/after the DDT cuts.

    make_plots.py --run runs/bdt0 --plots-dir plots

Reads <run>/scores.parquet, <run>/metrics.json and <run>/ddt/scores_ddt_<eff>.parquet (if present).
Writes bdt_score_train_test.png, feature_importance.png, sculpting_pt.png.
Stdout: N_PLOTS PLOTS_DIR. Exit 0 ok, 2 bad input.
"""
import argparse
import glob
import json
import os
import sys

import numpy as np

LAB = "CMS Open Data simulation"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--run", required=True)
    p.add_argument("--plots-dir", required=True)
    a = p.parse_args()
    try:
        import pandas as pd

        t = pd.read_parquet(os.path.join(a.run, "scores.parquet"))
        m = json.load(open(os.path.join(a.run, "metrics.json")))
    except Exception as e:  # noqa: BLE001
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(a.plots_dir, exist_ok=True)
    n = 0
    fig, ax = plt.subplots(figsize=(5.5, 4.2))
    b = np.linspace(0, 1, 41)
    for lab, name, col in ((1, "quark", "C3"), (0, "gluon", "C0")):
        for sp, sty in (("test", "step"), ("train", "dots")):
            r = t[(t.label == lab) & (t.split == sp)]
            h = np.histogram(r.score, b, weights=r.weight, density=True)[0]
            if sty == "step":
                ax.stairs(h, b, color=col, label=f"{name} (test)")
            else:
                ax.plot(0.5 * (b[1:] + b[:-1]), h, ".", color=col, label=f"{name} (train)")
    s = m["summary"]
    ax.set(xlabel="BDT score", ylabel="Normalised", yscale="log",
           title=f"{LAB}\nAUC train {s['AUC_TRAIN']}, test {s['AUC_TEST']}, KS p q {s['KS_P_SIG']}, g {s['KS_P_BKG']}")
    ax.title.set_fontsize(8)
    ax.legend(fontsize=7)
    fig.savefig(os.path.join(a.plots_dir, "bdt_score_train_test.png"), dpi=120, bbox_inches="tight")
    plt.close(fig)
    n += 1
    fig, axs = plt.subplots(1, 2, figsize=(10, 4))
    for ax, key, title in ((axs[0], "importance_total_gain", "total gain"), (axs[1], "mean_abs_shap", "mean |SHAP| (test rows)")):
        d = m.get(key) or {}
        k = sorted(d, key=d.get)
        ax.barh(k, [d[x] / max(sum(d.values()), 1e-300) for x in k])
        ax.set(xlabel=f"{title} (fraction)", title=LAB)
        ax.title.set_fontsize(8)
    fig.tight_layout()
    fig.savefig(os.path.join(a.plots_dir, "feature_importance.png"), dpi=120, bbox_inches="tight")
    plt.close(fig)
    n += 1
    files = sorted(glob.glob(os.path.join(a.run, "ddt", "scores_ddt_*.parquet")))
    if files:
        e = np.geomspace(30, 1000, 31)
        fig, axs = plt.subplots(1, 2, figsize=(10, 4), sharey=True)
        g = t[(t.label == 0) & (t.split == "test")]
        for ax, title in ((axs[0], "cut on BDT score (one threshold)"), (axs[1], "cut on pT-DDT score (score_ddt > 0)")):
            h0 = np.histogram(g.obs_pt, e, weights=g.weight)[0]
            ax.stairs(h0 / h0.sum(), e, color="k", label="gluon, all")
            ax.set(xscale="log", yscale="log", xlabel="Jet pT [GeV]", title=f"{LAB}: {title}")
            ax.title.set_fontsize(8)
        for i, f in enumerate(files):
            eff = f.rsplit("_", 1)[1].replace(".parquet", "")
            d = pd.read_parquet(f, columns=["score", "score_ddt", "label", "split", "weight", "obs_pt"])
            d = d[(d.label == 0) & (d.split == "test")]
            o = np.argsort(-d.score.to_numpy())
            c = np.cumsum(d.weight.to_numpy()[o]) / d.weight.sum()
            thr = d.score.to_numpy()[o][min(np.searchsorted(c, float(eff)), len(c) - 1)]
            for ax, sel in ((axs[0], d.score > thr), (axs[1], d.score_ddt > 0)):
                h = np.histogram(d.obs_pt[sel], e, weights=d.weight[sel])[0]
                ax.stairs(h / h.sum(), e, color=f"C{i}", label=f"gluon pass, eff_g = {eff}")
        axs[0].set_ylabel("Normalised")
        axs[1].legend(fontsize=7)
        fig.tight_layout()
        fig.savefig(os.path.join(a.plots_dir, "sculpting_pt.png"), dpi=120, bbox_inches="tight")
        plt.close(fig)
        n += 1
    print(f"N_PLOTS={n}\nPLOTS_DIR={a.plots_dir}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
