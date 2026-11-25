#!/usr/bin/env python3
"""EXO-17-021-like boosted selection on a subset of the Open Data skim (CMS Open Data 2016 G+H, private work),
plus QCD-MC kappa grids for the CMS pair and for each student's pair.

Inputs: skimcache/output_*.parquet (4 data + 13 QCD files, list in skimcache/list.txt; see run_all.sh),
        ../ws_skill/red/qcd.parquet (with-skill reduced QCD MC), ../ws_noskill/fits/slim_qcd.npz (without-skill QCD MC),
        ref/cms_extracted/fig2_*.csv and fig4_points.csv (binning only).
Selection (same as skim_check.py): golden+filters (data), trigger OR(PFHT800, PFHT900, AK8PFJet360_TrimMass30,
AK8PFHT750_TrimMass50, AK8PFHT700_TrimR0p1PT0p03Mass50) on data only, HT_AK8 (3 leading AK8, pT>150, |eta|<2.5) > 900,
2 AK8 pT>150 |eta|<2.5, tau21<0.45, tau32>0.57 both jets, masym<0.1, deta<1.5, 60<=m_avg<450 for N-1 plots.
QCD MC weight = xsec*16.3/fb*genWeight/sumw * (skim rows of the sample)/(skim rows in the used files).

Usage: python3 scripts/cmslike.py  -> out/cmslike.json
"""
import glob, json, os, re, sys
import numpy as np, pyarrow.parquet as pq

WSA, WSB = "../ws_skill", "../ws_noskill"
GOLD = json.load(open(f"{WSA}/inputs/golden_2016.json"))
XS = {l.split(",")[0]: float(l.split(",")[1]) for l in open(f"{WSA}/inputs/xsec.csv") if not l.startswith(("#", "sample"))}
SUMW = json.load(open(f"{WSA}/inputs/sumw.json"))
VARS = ["masym", "deta", "tau21_lead", "tau21_sub", "tau32_lead", "tau32_sub"]


def csv_edges(name):
    rows = [l.strip().split(",") for l in open(f"ref/cms_extracted/{name}") if l[0] not in "#l"]
    lo = [float(r[0]) for r in rows]; hi = [float(r[1]) for r in rows]
    return np.array(lo + [hi[-1]])


def skim_totals():
    tot = {}
    for l in open(f"{WSA}/logs/slim_all.log"):
        m = re.match(r"(\S+) \d+ of (\d+)", l.strip())
        if m: tot[m.group(1)] = tot.get(m.group(1), 0) + int(m.group(2))
    return tot


def golden(run, lb):
    ok = np.zeros(len(run), bool)
    for r in np.unique(run):
        s = run == r
        for a, b in GOLD.get(str(int(r)), []):
            ok |= s & (lb >= a) & (lb <= b)
    return ok


def load(f, isdata):
    pf = pq.ParquetFile(f); names = pf.schema_arrow.names
    cols = ["filters", "j2_pt", "j2_eta"] + [f"j{i}_{v}" for i in (0, 1) for v in ("pt", "eta", "msoftdrop", "tau1", "tau2", "tau3")]
    trig = ["HLT_PFHT800", "HLT_PFHT900", "HLT_AK8PFJet360_TrimMass30", "HLT_AK8PFHT750_TrimMass50", "HLT_AK8PFHT700_TrimR0p1PT0p03Mass50"]
    cols += (["run", "luminosityBlock"] + [t for t in trig if t in names]) if isdata else ["genWeight"]
    t = pf.read(columns=cols); d = {c: t[c].to_numpy(zero_copy_only=False) for c in cols}
    n = len(d["filters"]); ok = d["filters"].astype(bool)
    if isdata:
        tr = np.zeros(n, bool)
        for c in trig:
            if c in d: tr |= d[c]
        ok &= golden(d["run"], d["luminosityBlock"]) & tr
    ht8 = np.zeros(n)
    for j in ("j0", "j1", "j2"):
        ht8 += np.where((d[f"{j}_pt"] > 150) & (np.abs(d[f"{j}_eta"]) < 2.5), d[f"{j}_pt"], 0.0)
    ok &= (ht8 > 900) & (d["j0_pt"] > 150) & (d["j1_pt"] > 150) & (np.abs(d["j0_eta"]) < 2.5) & (np.abs(d["j1_eta"]) < 2.5)
    m0, m1 = d["j0_msoftdrop"], d["j1_msoftdrop"]
    v = dict(mavg=0.5 * (m0 + m1), masym=np.abs(m0 - m1) / np.clip(m0 + m1, 1e-3, None), deta=np.abs(d["j0_eta"] - d["j1_eta"]),
             tau21_lead=d["j0_tau2"] / np.clip(d["j0_tau1"], 1e-6, None), tau21_sub=d["j1_tau2"] / np.clip(d["j1_tau1"], 1e-6, None),
             tau32_lead=d["j0_tau3"] / np.clip(d["j0_tau2"], 1e-6, None), tau32_sub=d["j1_tau3"] / np.clip(d["j1_tau2"], 1e-6, None))
    v = {k: x[ok] for k, x in v.items()}
    v["w"] = np.ones(ok.sum()) if isdata else d["genWeight"][ok].astype("f8")
    return v, n


def kappa_grid(H, V, xe, ye, xcuts, ycuts, band=None):
    """H: 2D sumw in (x,y) fine bins with edges xe, ye. pass x: x<cx; fail x: cx<=x<cx+band (or all >= cx);
    pass y: y<cy. kappa = A*D/(B*C) with A=(px,py), B=(fx,py), C=(px,fy), D=(fx,fy)."""
    K = np.full((len(xcuts), len(ycuts)), np.nan); E = np.full_like(K, np.nan)
    for i, cx in enumerate(xcuts):
        px = xe[1:] <= cx + 1e-9
        fx = (xe[:-1] >= cx - 1e-9) & ((xe[1:] <= cx + band + 1e-9) if band else True)
        for j, cy in enumerate(ycuts):
            py = ye[1:] <= cy + 1e-9; fy = ye[:-1] >= cy - 1e-9
            R = {k: (H[np.ix_(a, b)].sum(), V[np.ix_(a, b)].sum()) for k, (a, b) in dict(A=(px, py), B=(fx, py), C=(px, fy), D=(fx, fy)).items()}
            if min(r[0] for r in R.values()) <= 0: continue
            K[i, j] = R["A"][0] * R["D"][0] / (R["B"][0] * R["C"][0])
            E[i, j] = K[i, j] * np.sqrt(sum(r[1] / r[0] ** 2 for r in R.values()))
    return K, E


def main():
    tot = skim_totals()
    fig2_edges = {"masym": csv_edges("fig2_masym.csv"), "deta": csv_edges("fig2_deta.csv")}
    for v in VARS[2:]: fig2_edges[v] = csv_edges(f"fig2_{v}.csv")
    cms_edges = np.array([float(v["x"][0]["low"]) for v in json.load(open("ref/table_348181.json"))["values"]] + [503.0])
    f4 = [l.strip().split(",") for l in open("ref/cms_extracted/fig4_points.csv") if l[0] not in "#m"]
    tf_edges = np.array([60.0, 80, 100, 125, 150, 175, 200, 225, 250, 275, 300, 350, 400, 450, 500])
    xe, ye = np.linspace(0, 1, 101), np.linspace(0, 5, 101)
    out = {"note": "CMS Open Data, private work (EXO-17-021-like selection, soft-drop mass, PUPPI tau_N); not a CMS result",
           "fig4_points_used_for_binning": len(f4), "tf_edges": tf_edges.tolist(), "cms_edges": cms_edges.tolist()}
    acc = {}
    files = sorted(glob.glob("skimcache/output_*.parquet"))
    used_rows = {}
    for f in files:
        s = re.sub(r"_\d+\.parquet$", "", os.path.basename(f)).replace("output_", "")
        used_rows[s] = used_rows.get(s, 0) + pq.ParquetFile(f).metadata.num_rows
    for f in files:
        s = re.sub(r"_\d+\.parquet$", "", os.path.basename(f)).replace("output_", "")
        isdata = s.startswith("data")
        g = "data" if isdata else "qcd"
        v, n = load(f, isdata)
        if not isdata:
            v["w"] = v["w"] * XS[s] * 16300.0 / SUMW[s] * tot[s] / used_rows[s]
        w = v["w"]; a = acc.setdefault(g, {})
        t21 = (v["tau21_lead"] < 0.45) & (v["tau21_sub"] < 0.45); t32 = (v["tau32_lead"] > 0.57) & (v["tau32_sub"] > 0.57)
        cx, cy = v["masym"] < 0.1, v["deta"] < 1.5
        mwin = (v["mavg"] >= 60) & (v["mavg"] < 450)
        nm1 = {"masym": t21 & t32 & cy, "deta": t21 & t32 & cx}
        for k in VARS[2:]: nm1[k] = cx & cy
        for k in VARS:
            sel = nm1[k] & mwin
            h = np.histogram(np.clip(v[k][sel], 0, fig2_edges[k][-1] - 1e-6), fig2_edges[k], weights=w[sel])[0]
            a[f"n1_{k}"] = a.get(f"n1_{k}", 0) + h
        base = t21 & t32
        for r, m in dict(A=cx & cy, B=cx & ~cy, C=~cx & cy, D=~cx & ~cy).items():
            for nme, ed in (("cms", cms_edges), ("tf", tf_edges)):
                a[f"{nme}_{r}"] = a.get(f"{nme}_{r}", 0) + np.histogram(v["mavg"][base & m], ed, weights=w[base & m])[0]
                a[f"{nme}_{r}_w2"] = a.get(f"{nme}_{r}_w2", 0) + np.histogram(v["mavg"][base & m], ed, weights=w[base & m] ** 2)[0]
        if not isdata:
            sel = base & mwin
            a["H2"] = a.get("H2", 0) + np.histogram2d(v["masym"][sel], np.clip(v["deta"][sel], 0, 4.999), [xe, ye], weights=w[sel])[0]
            a["V2"] = a.get("V2", 0) + np.histogram2d(v["masym"][sel], np.clip(v["deta"][sel], 0, 4.999), [xe, ye], weights=w[sel] ** 2)[0]
        print(f"{os.path.basename(f)} rows={n} sel={int(base.sum())}", file=sys.stderr)
    for g in acc:
        out[g] = {k: np.asarray(x).tolist() for k, x in acc[g].items() if k not in ("H2", "V2")}
    out["fig2_edges"] = {k: e.tolist() for k, e in fig2_edges.items()}
    # ---- kappa grids (QCD MC)
    grids = {}
    xc = np.round(np.arange(0.05, 0.301, 0.025), 3); yc = np.round(np.arange(0.8, 2.01, 0.1), 2)
    K, E = kappa_grid(acc["qcd"]["H2"], acc["qcd"]["V2"], xe, ye, xc, yc)
    grids["cms_pair_cms_sel"] = dict(x="masym cut (fail: all above)", y="deta cut", xcuts=xc.tolist(), ycuts=yc.tolist(), kappa=K.tolist(), err=E.tolist(),
                                    marks={"CMS": [0.1, 1.5], "with skill": [0.2, 1.2]}, sample="QCD MC subset, EXO-17-021-like selection, 60-450 GeV")
    import pyarrow.parquet as pq2
    t = pq2.read_table(f"{WSA}/red/qcd.parquet", columns=["masym", "deta", "w"]).to_pandas()
    H, _, _ = np.histogram2d(t.masym, np.clip(t.deta, 0, 4.999), [xe, ye], weights=t.w.astype("f8"))
    V, _, _ = np.histogram2d(t.masym, np.clip(t.deta, 0, 4.999), [xe, ye], weights=t.w.astype("f8") ** 2)
    K, E = kappa_grid(H, V, xe, ye, xc, yc, band=0.2)
    grids["with_skill_pair"] = dict(x="masym cut (fail band: cut to cut+0.2)", y="deta cut", xcuts=xc.tolist(), ycuts=yc.tolist(), kappa=K.tolist(), err=E.tolist(),
                                    marks={"with skill": [0.2, 1.2], "CMS": [0.1, 1.5]}, sample="with-skill QCD MC (its preselection), 40-480 GeV")
    K, E = kappa_grid(H, V, xe, ye, xc, yc)
    grids["with_skill_sel_full_fail"] = dict(xcuts=xc.tolist(), ycuts=yc.tolist(), kappa=K.tolist(), err=E.tolist())
    del t
    z = np.load(f"{WSB}/fits/slim_qcd.npz")
    m0, m1 = z["msoftdrop0"], z["msoftdrop1"]; mavg = 0.5 * (m0 + m1)
    asym = np.abs(m0 - m1) / np.maximum(m0 + m1, 1e-3)
    sel = (z["pt1"] > 300) & (asym < 0.2) & (mavg > 40) & (mavg < 440)
    n0, n1, w = z["n2b10"][sel], z["n2b11"][sel], z["w"][sel]
    ne = np.linspace(0, 0.6, 121)
    H, _, _ = np.histogram2d(np.clip(n0, 0, 0.599), np.clip(n1, 0, 0.599), [ne, ne], weights=w)
    V, _, _ = np.histogram2d(np.clip(n0, 0, 0.599), np.clip(n1, 0, 0.599), [ne, ne], weights=w ** 2)
    nc = np.round(np.arange(0.20, 0.401, 0.02), 2)
    K, E = kappa_grid(H, V, ne, ne, nc, nc)
    grids["without_skill_pair"] = dict(x="N2 jet 1 cut", y="N2 jet 2 cut", xcuts=nc.tolist(), ycuts=nc.tolist(), kappa=K.tolist(), err=E.tolist(),
                                       marks={"without skill": [0.3, 0.3]}, sample="without-skill QCD MC (its preselection), 40-440 GeV")
    out["kappa_grids"] = grids
    os.makedirs("out", exist_ok=True)
    json.dump(out, open("out/cmslike.json", "w"))
    for k, gr in grids.items():
        Kk = np.array(gr["kappa"]); print(f"KAPPA_{k}: min={np.nanmin(Kk):.3f} max={np.nanmax(Kk):.3f}")
    print("DATA_A=%d QCD_A=%.0f" % (sum(out["data"]["cms_A"]), sum(out["qcd"]["cms_A"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
