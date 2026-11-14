#!/usr/bin/env python3
"""Compare the BDT score with Jet_qgl and DeepJet q/g on the same test jets, per pT x |eta| bin.

    qg_compare.py scores.parquet --out compare.json [--plots-dir plots] [--tag bdt=score ...]

Input: scores.parquet of train_bdt.py (score, label 1 quark / 0 gluon, weight, split, obs_pt,
obs_abseta, obs_qgl, obs_deepjet_qg). Taggers, all oriented so that high = quark-like:
  bdt = score, qgl = obs_qgl, deepjet_qg = 1 - obs_deepjet_qg (btagDeepFlavQG is g/(g+uds)).
Rows: split == --test-split (default test). Bins: every pT x |eta| bin, every pT bin over
|eta| < 2.5, every |eta| bin over 30-1000 GeV, and inclusive. Per tagger and bin:
  auc, auc_err (bootstrap, --n-boot resamples, weighted), gluon rejection 1 - eff_g at
  eff_q = 0.5 and 0.7, eff_q at eff_g = 0.1. Thresholds are set inside each bin. Each working
  point has n_q_pass and n_g_pass (raw jets above the cut); with fewer than --min-jets (100)
  of either class the value is null and low_stat = true.
Also per bin: raw and effective jet counts per class and split, and the normalised quark and
gluon Jet_qgl histograms (20 bins in [0, 1]; jets with Jet_qgl < 0 counted separately).

Stdout KEY=VALUE: N_TEST_Q N_TEST_G AUC_<TAGGER>_INCL AUC_ERR_<TAGGER>_INCL
GREJ50_<TAGGER>_INCL N_LOW_STAT STATUS (PASS if every AUC is in (0.5, 1)).
Exit 0 pass, 1 an AUC outside (0.5, 1), 2 bad input. Plots (PNG) with --plots-dir.
"""
import argparse
import json
import os
import sys

import numpy as np

PT = [30, 50, 80, 120, 200, 400, 1000]
ETA = [0.0, 1.3, 2.5]


def wauc(y, s, w):
    o = np.argsort(-s, kind="stable")
    y, s, w = y[o], s[o], w[o]
    tp, fp = np.cumsum(w * y), np.cumsum(w * (1 - y))
    if tp[-1] <= 0 or fp[-1] <= 0:
        return float("nan")
    last = np.r_[s[1:] != s[:-1], True]
    tpr, fpr = np.r_[0, tp[last] / tp[-1]], np.r_[0, fp[last] / fp[-1]]
    return float(np.sum(0.5 * (tpr[1:] + tpr[:-1]) * np.diff(fpr)))


def wquantile(x, w, q):
    """Threshold t such that the weighted fraction with x > t is q (as evaluate.py)."""
    o = np.argsort(-x, kind="stable")
    c = np.cumsum(w[o]) / w.sum()
    i = min(int(np.searchsorted(c, q)), len(x) - 1)
    return float(x[o][i])


def neff(w):
    return float(w.sum() ** 2 / (w**2).sum()) if len(w) and (w**2).sum() > 0 else 0.0


def roc(y, s, w, n=200):
    o = np.argsort(-s, kind="stable")
    tq = np.cumsum((w * y)[o]) / (w * y).sum()
    tg = np.cumsum((w * (1 - y))[o]) / (w * (1 - y)).sum()
    i = np.unique(np.searchsorted(tq, np.linspace(0.005, 1, n)).clip(0, len(tq) - 1))
    return tq[i].tolist(), (1 - tg[i]).tolist()


def tagger_metrics(y, s, w, rng, nboot, min_jets):
    q, g = y == 1, y == 0
    out = {"auc": wauc(y, s, w)}
    b = [wauc(y[i], s[i], w[i]) for i in (rng.integers(0, len(y), len(y)) for _ in range(nboot))]
    out["auc_err"] = float(np.nanstd(b))
    wps = {}
    for name, ref, other, target in (("grej_at_qeff_0.5", q, g, 0.5), ("grej_at_qeff_0.7", q, g, 0.7),
                                     ("qeff_at_geff_0.1", g, q, 0.1)):
        thr = wquantile(s[ref], w[ref], target)
        pq, pg = q & (s > thr), g & (s > thr)
        eq, eg = w[pq].sum() / w[q].sum(), w[pg].sum() / w[g].sum()
        nq, ng = int(pq.sum()), int(pg.sum())
        low = nq < min_jets or ng < min_jets
        val = (1 - eg) if name.startswith("grej") else eq
        nn = neff(w[g]) if name.startswith("grej") else neff(w[q])
        p = eg if name.startswith("grej") else eq
        wps[name] = {"value": None if low else float(val), "err": None if low else float(np.sqrt(max(p * (1 - p), 0) / nn)),
                     "threshold": thr, "achieved_qeff": float(eq), "achieved_geff": float(eg),
                     "n_q_pass": nq, "n_g_pass": ng, "low_stat": bool(low)}
    out["wp"] = wps
    return out


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("scores")
    p.add_argument("--out", required=True)
    p.add_argument("--plots-dir")
    p.add_argument("--test-split", default="test")
    p.add_argument("--n-boot", type=int, default=50)
    p.add_argument("--min-jets", type=int, default=100)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--label-note", default="quark = |partonFlavour| 1-3, gluon = 21")
    a = p.parse_args()
    try:
        import pandas as pd

        t = pd.read_parquet(a.scores)
        t = t[t.label >= 0]
        for c in ("score", "weight", "split", "obs_pt", "obs_abseta", "obs_qgl", "obs_deepjet_qg"):
            t[c]
    except Exception as e:  # noqa: BLE001
        print(f"error: {type(e).__name__}: {e}", file=sys.stderr)
        return 2
    rng = np.random.default_rng(a.seed)
    taggers = {"bdt": t["score"].to_numpy(float), "qgl": t["obs_qgl"].to_numpy(float),
               "deepjet_qg": 1.0 - t["obs_deepjet_qg"].to_numpy(float)}
    y, w = t["label"].to_numpy(int), t["weight"].to_numpy(float)
    pt, ae, split = t["obs_pt"].to_numpy(float), t["obs_abseta"].to_numpy(float), t["split"].to_numpy()
    qgl = taggers["qgl"]
    te = split == a.test_split
    bins = []
    for i in range(len(PT) - 1):
        for j in range(len(ETA) - 1):
            bins.append((f"pt{PT[i]}-{PT[i+1]}_eta{ETA[j]}-{ETA[j+1]}", PT[i], PT[i + 1], ETA[j], ETA[j + 1]))
    for i in range(len(PT) - 1):
        bins.append((f"pt{PT[i]}-{PT[i+1]}_eta0.0-2.5", PT[i], PT[i + 1], 0.0, 2.5))
    for j in range(len(ETA) - 1):
        bins.append((f"pt30-1000_eta{ETA[j]}-{ETA[j+1]}", 30, 1000, ETA[j], ETA[j + 1]))
    bins.append(("inclusive", 30, 1000, 0.0, 2.5))
    res, rocs, failed = {}, {}, []
    hedges = np.linspace(0, 1, 21)
    for name, plo, phi, elo, ehi in bins:
        inb = (pt >= plo) & (pt < phi) & (ae >= elo) & (ae < ehi)
        m = inb & te
        d = {"pt": [plo, phi], "abseta": [elo, ehi], "counts": {}}
        for sp in ("train", "val", "test"):
            for cl, lab in (("quark", 1), ("gluon", 0)):
                mm = inb & (split == sp) & (y == lab)
                d["counts"][f"{sp}_{cl}"] = {"raw": int(mm.sum()), "eff": round(neff(w[mm]), 1)}
        if (m & (y == 1)).sum() < 2 or (m & (y == 0)).sum() < 2:
            d["taggers"] = None
            res[name] = d
            continue
        d["taggers"] = {}
        for tg, s in taggers.items():
            mt = tagger_metrics(y[m], s[m], w[m], rng, a.n_boot, a.min_jets)
            d["taggers"][tg] = mt
            if not 0.5 < mt["auc"] < 1:
                failed.append(f"{tg}:{name}")
            rocs.setdefault(name, {})[tg] = roc(y[m], s[m], w[m])
        sh = {}
        for cl, lab in (("quark", 1), ("gluon", 0)):
            mm = m & (y == lab)
            v = qgl[mm]
            h = np.histogram(v, hedges, weights=w[mm])[0]
            sh[cl] = {"density": (h / max(h.sum(), 1e-300) / np.diff(hedges)).tolist(),
                      "n_raw": int((v >= 0).sum()), "n_undefined_qgl": int((v < 0).sum())}
        d["qgl_shapes"] = {"edges": hedges.tolist(), **sh}
        res[name] = d
    inc = res["inclusive"]["taggers"]
    nlow = sum(1 for d in res.values() if d["taggers"] for m in d["taggers"].values() for wp in m["wp"].values() if wp["low_stat"])
    summ = {"N_TEST_Q": res["inclusive"]["counts"]["test_quark"]["raw"], "N_TEST_G": res["inclusive"]["counts"]["test_gluon"]["raw"]}
    for tg in taggers:
        summ[f"AUC_{tg.upper()}_INCL"] = round(inc[tg]["auc"], 5)
        summ[f"AUC_ERR_{tg.upper()}_INCL"] = round(inc[tg]["auc_err"], 5)
        summ[f"GREJ50_{tg.upper()}_INCL"] = round(inc[tg]["wp"]["grej_at_qeff_0.5"]["value"], 4)
    summ.update({"N_LOW_STAT": nlow, "FAILED": ",".join(failed) or "none", "STATUS": "FAIL" if failed else "PASS"})
    out = {"summary": summ, "label": a.label_note, "pt_edges": PT, "abseta_edges": ETA,
           "orientation": {"bdt": "score", "qgl": "Jet_qgl", "deepjet_qg": "1 - Jet_btagDeepFlavQG"},
           "working_points": "thresholds set per bin on the test jets of that bin", "bins": res,
           "command": " ".join(sys.argv)}
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w") as f:
        json.dump(out, f, indent=1)
    if a.plots_dir:
        plots(a.plots_dir, res, rocs, a.label_note)
    print("\n".join(f"{k}={v}" for k, v in summ.items()))
    return 1 if failed else 0


def plots(pdir, res, rocs, note):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    os.makedirs(pdir, exist_ok=True)
    lab = "CMS Open Data simulation"
    names = {"bdt": "BDT (this work)", "qgl": "Jet_qgl", "deepjet_qg": "1 - DeepJet QG"}
    cols = {"bdt": "C3", "qgl": "C0", "deepjet_qg": "C2"}

    def roc_ax(ax, nm, title):
        for tg, (x, yv) in rocs[nm].items():
            ax.plot(x, yv, color=cols[tg], label=f"{names[tg]} AUC={res[nm]['taggers'][tg]['auc']:.3f}")
        ax.set(xlabel="Quark efficiency", ylabel="Gluon rejection (1 - eff_g)", xlim=(0, 1), ylim=(0, 1))
        ax.set_title(title, fontsize=8)
        ax.legend(fontsize=6, loc="lower left")

    fig, ax = plt.subplots(figsize=(5, 4.5))
    roc_ax(ax, "inclusive", f"{lab}\nQCD, AK4, pT 30-1000 GeV, |eta| < 2.5 (test fold)")
    fig.savefig(os.path.join(pdir, "roc_inclusive.png"), dpi=120, bbox_inches="tight")
    plt.close(fig)
    grid = [k for k in res if k.startswith("pt") and not k.endswith("eta0.0-2.5") and not k.startswith("pt30-1000") and k in rocs]
    fig, axs = plt.subplots(len(PT) - 1, 2, figsize=(9, 3.0 * (len(PT) - 1)))
    for k in grid:
        d = res[k]
        i, j = PT.index(d["pt"][0]), ETA.index(d["abseta"][0])
        roc_ax(axs[i, j], k, f"{lab}: pT {d['pt'][0]}-{d['pt'][1]} GeV, |eta| {d['abseta'][0]}-{d['abseta'][1]}")
    fig.tight_layout()
    fig.savefig(os.path.join(pdir, "roc_per_bin.png"), dpi=100, bbox_inches="tight")
    plt.close(fig)
    fig, axs = plt.subplots(1, 2, figsize=(9, 3.8), sharey=True)
    for j in range(len(ETA) - 1):
        for tg in names:
            xs, ys, es = [], [], []
            for i in range(len(PT) - 1):
                d = res.get(f"pt{PT[i]}-{PT[i+1]}_eta{ETA[j]}-{ETA[j+1]}")
                if d and d["taggers"]:
                    xs.append(0.5 * (PT[i] + PT[i + 1]))
                    ys.append(d["taggers"][tg]["auc"])
                    es.append(d["taggers"][tg]["auc_err"])
            axs[j].errorbar(xs, ys, es, fmt="o-", color=cols[tg], label=names[tg])
        axs[j].set(xscale="log", xlabel="Jet pT [GeV]", title=f"{lab}, |eta| {ETA[j]}-{ETA[j+1]}")
        axs[j].title.set_fontsize(8)
    axs[0].set_ylabel("ROC AUC (quark vs gluon)")
    axs[0].legend(fontsize=7)
    fig.savefig(os.path.join(pdir, "auc_vs_pt.png"), dpi=120, bbox_inches="tight")
    plt.close(fig)
    fig, axs = plt.subplots(len(PT) - 1, 2, figsize=(9, 2.6 * (len(PT) - 1)))
    for k in grid:
        d = res[k]
        i, j = PT.index(d["pt"][0]), ETA.index(d["abseta"][0])
        e = np.array(d["qgl_shapes"]["edges"])
        for cl, c in (("quark", "C3"), ("gluon", "C0")):
            axs[i, j].stairs(d["qgl_shapes"][cl]["density"], e, color=c, label=cl)
        axs[i, j].set_title(f"{lab}: pT {d['pt'][0]}-{d['pt'][1]} GeV, |eta| {d['abseta'][0]}-{d['abseta'][1]}", fontsize=7)
        axs[i, j].set(xlabel="Jet_qgl", ylabel="Normalised")
        axs[i, j].legend(fontsize=6)
    fig.tight_layout()
    fig.savefig(os.path.join(pdir, "qgl_shapes_per_bin.png"), dpi=100, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    sys.exit(main())
