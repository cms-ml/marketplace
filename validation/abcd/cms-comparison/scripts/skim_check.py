#!/usr/bin/env python3
"""Independent recount on a few raw skim files (CMS Open Data 2016 G+H, private work).

For each skim file in skimcache/ this script
  1. applies the with-skill and without-skill full selections written from scratch (from their
     results.json/REPORT.md definitions, not their code) and counts regions A, B, C, D;
  2. applies the same final cuts to the students' own per-file intermediates
     (with skill: slim/<file>.parquet, without skill: fits/base/<file>.npz) and counts again;
  3. applies an EXO-17-021-like boosted selection (HT_AK8>900, tau21<0.45, tau32>0.57,
     masym<0.1, deta<1.5; soft-drop mass instead of pruned) and histograms m_avg in the
     CMS layout (A, B, C, D of the paper's Table 2) on the CMS binning.

Usage: python3 scripts/skim_check.py   (from cms-comparison/; needs the LCG env)
Writes out/skim_check.json.  Exit 0 if all recounts agree, 1 otherwise.
"""
import glob, json, os, sys
import numpy as np, pyarrow.parquet as pq

WSA, WSB = "../ws_skill", "../ws_noskill"
GOLD = json.load(open(f"{WSA}/inputs/golden_2016.json"))
CMS_EDGES = None  # filled from HEPData table


def golden(run, lb):
    ok = np.zeros(len(run), bool)
    for r in np.unique(run):
        sel = run == r
        for a, b in GOLD.get(str(int(r)), []):
            ok |= sel & (lb >= a) & (lb <= b)
    return ok


def derived(d, m0="j0_msoftdrop", m1="j1_msoftdrop"):
    s = d[m0] + d[m1]
    mavg = 0.5 * s
    masym = np.abs(d[m0] - d[m1]) / np.clip(s, 1e-3, None)
    deta = np.abs(d["j0_eta"] - d["j1_eta"])
    return mavg, masym, deta


def regions_A(mavg, masym, deta, base):
    m = base & (mavg >= 40) & (mavg < 480)
    px, fx = masym < 0.2, (masym >= 0.2) & (masym < 0.4)
    py = deta < 1.2
    return {"A": int((m & px & py).sum()), "B": int((m & fx & py).sum()),
            "C": int((m & px & ~py).sum()), "D": int((m & fx & ~py).sum())}


def regions_B(mavg, masym, n0, n1, base):
    m = base & (mavg >= 40) & (mavg < 440) & (masym < 0.2)
    p0, p1 = n0 < 0.3, n1 < 0.3
    return {"A": int((m & p0 & p1).sum()), "B": int((m & p0 & ~p1).sum()),
            "C": int((m & ~p0 & p1).sum()), "D": int((m & ~p0 & ~p1).sum())}


def main():
    hep = json.load(open("ref/table_348181.json"))
    edges = [float(v["x"][0]["low"]) for v in hep["values"]] + [float(hep["values"][-1]["x"][0]["high"])]
    edges = np.array(edges)
    files = sorted(glob.glob("skimcache/output_data_JetHT_2016*.parquet"))
    if not files:
        print("no skim files in skimcache/", file=sys.stderr); return 2
    out = {"files": [], "cms_like": {}, "note": "CMS Open Data, private work; not a CMS result"}
    hsum = {r: np.zeros(len(edges) - 1) for r in "ABCD"}
    tot_ok = True
    for f in files:
        tag = os.path.basename(f).replace("output_", "").replace(".parquet", "")  # data_JetHT_2016G_0
        era_i = tag.rsplit("_", 1)
        stem = era_i[0] + "__" + era_i[1]
        pf = pq.ParquetFile(f)
        cols = ["run", "luminosityBlock", "filters", "HT", "nMuLoose", "nEleLoose",
                "HLT_PFHT800", "HLT_PFHT900", "HLT_PFJet450", "HLT_AK8PFJet450",
                "HLT_AK8PFJet360_TrimMass30", "HLT_AK8PFHT750_TrimMass50", "HLT_AK8PFHT700_TrimR0p1PT0p03Mass50"]
        cols += [f"j{i}_{v}" for i in (0, 1) for v in ("pt", "eta", "msoftdrop", "tau1", "tau2", "tau3", "n2b1", "jetId")]
        cols += ["j2_pt", "j2_eta"]
        cols = [c for c in cols if c in pf.schema_arrow.names]
        t = pf.read(columns=cols)
        d = {c: t[c].to_numpy(zero_copy_only=False) for c in cols}
        for c in ("HLT_PFHT800", "HLT_AK8PFHT750_TrimMass50", "HLT_AK8PFHT700_TrimR0p1PT0p03Mass50"):
            d.setdefault(c, np.zeros(len(d["run"]), bool))
        n_raw = len(d["run"])
        gl = golden(d["run"], d["luminosityBlock"]) & d["filters"].astype(bool)
        mavg, masym, deta = derived(d)
        lepveto = (d["nMuLoose"] == 0) & (d["nEleLoose"] == 0)
        trigA = d["HLT_PFHT900"] | d["HLT_PFJet450"] | d["HLT_AK8PFJet450"]
        # --- with-skill selection from scratch
        baseA = gl & trigA & (d["HT"] > 1100) & (d["j0_pt"] > 250) & (d["j1_pt"] > 250) & \
            (np.abs(d["j0_eta"]) < 2.4) & (np.abs(d["j1_eta"]) < 2.4) & (d["j0_jetId"] >= 2) & (d["j1_jetId"] >= 2) & lepveto
        mineA = regions_A(mavg, masym, deta, baseA)
        # --- with-skill from their slim file
        s = pq.read_table(f"{WSA}/slim/{stem}.parquet").to_pandas()
        bA = ((s.HLT_PFHT900 | s.HLT_PFJet450 | s.HLT_AK8PFJet450) & (s.HT > 1100) & (s.j0_pt > 250) & (s.j1_pt > 250)
              & (s.j0_eta.abs() < 2.4) & (s.j1_eta.abs() < 2.4) & (s.j0_jetId >= 2) & (s.j1_jetId >= 2)
              & (s.nMuLoose == 0) & (s.nEleLoose == 0)).values
        sm, sa, se = derived({k: s[k].values for k in ("j0_msoftdrop", "j1_msoftdrop", "j0_eta", "j1_eta")})
        theirsA = regions_A(sm, sa, se, bA)
        # --- without-skill selection from scratch
        baseB = gl & trigA & (d["j0_jetId"] >= 2) & (d["j1_jetId"] >= 2) & (np.abs(d["j0_eta"]) < 2.5) & \
            (np.abs(d["j1_eta"]) < 2.5) & (d["j0_pt"] > 550) & (d["j1_pt"] > 300) & lepveto
        mineB = regions_B(mavg, masym, d["j0_n2b1"], d["j1_n2b1"], baseB)
        z = np.load(f"{WSB}/fits/base/{stem}.npz")
        zb = {k: z[k] for k in ("j0_msoftdrop", "j1_msoftdrop", "j0_eta", "j1_eta")}
        zm, za, _ = derived(zb)
        theirsB = regions_B(zm, za, z["j0_n2b1"], z["j1_n2b1"], z["j1_pt"] > 300)
        agree = mineA == theirsA and mineB == theirsB
        tot_ok &= agree
        # --- EXO-17-021-like boosted selection (soft-drop instead of pruned mass)
        ht8 = np.zeros(n_raw)
        for j in ("j0", "j1", "j2"):
            pt, eta = d[f"{j}_pt"], d[f"{j}_eta"]
            ht8 += np.where((pt > 150) & (np.abs(eta) < 2.5), pt, 0.0)
        trigC = d["HLT_PFHT800"] | d["HLT_PFHT900"] | d["HLT_AK8PFJet360_TrimMass30"] | d["HLT_AK8PFHT750_TrimMass50"] | d["HLT_AK8PFHT700_TrimR0p1PT0p03Mass50"]
        t21 = [d[f"j{i}_tau2"] / np.clip(d[f"j{i}_tau1"], 1e-6, None) for i in (0, 1)]
        t32 = [d[f"j{i}_tau3"] / np.clip(d[f"j{i}_tau2"], 1e-6, None) for i in (0, 1)]
        baseC = gl & trigC & (ht8 > 900) & (d["j0_pt"] > 150) & (d["j1_pt"] > 150) & \
            (np.abs(d["j0_eta"]) < 2.5) & (np.abs(d["j1_eta"]) < 2.5) & \
            (t21[0] < 0.45) & (t21[1] < 0.45) & (t32[0] > 0.57) & (t32[1] > 0.57)
        px, py = masym < 0.1, deta < 1.5
        # paper Table 2: A = masym<0.1 & deta<1.5 ; B = masym<0.1 & deta>1.5 ; C = masym>0.1 & deta<1.5 ; D = both fail
        reg = {"A": px & py, "B": px & ~py, "C": ~px & py, "D": ~px & ~py}
        cnt = {}
        for r, m in reg.items():
            hsum[r] += np.histogram(mavg[baseC & m], edges)[0]
            cnt[r] = int((baseC & m & (mavg >= 64) & (mavg < 503)).sum())
        # same files: student-A and student-B signal-region counts in the CMS mass range (for level scaling)
        out["files"].append(dict(file=tag, n_raw=n_raw, runA_mine=mineA, runA_theirs=theirsA, runB_mine=mineB,
                                 runB_theirs=theirsB, agree=agree, cms_like_counts=cnt))
        print(f"{tag}: raw={n_raw} A-run mine={mineA} theirs={theirsA} | B-run mine={mineB} theirs={theirsB} | agree={agree}", file=sys.stderr)
    out["cms_like"] = {"edges": edges.tolist(), **{r: hsum[r].tolist() for r in "ABCD"},
                       "selection": "trigger OR(PFHT800,PFHT900,AK8PFJet360_TrimMass30,AK8PFHT750_TrimMass50,AK8PFHT700_TrimR0p1PT0p03Mass50); "
                                    "golden+filters; HT_AK8(3 leading AK8, pT>150,|eta|<2.5)>900; 2 AK8 pT>150 |eta|<2.5; "
                                    "tau21<0.45, tau32>0.57 both jets; regions masym 0.1 x deta 1.5; m_SD instead of m_pruned; no lepton veto, no jetId"}
    out["all_agree"] = bool(tot_ok)
    os.makedirs("out", exist_ok=True)
    json.dump(out, open("out/skim_check.json", "w"), indent=1)
    print(f"FILES={len(files)}"); print(f"ALL_AGREE={tot_ok}")
    return 0 if tot_ok else 1


if __name__ == "__main__":
    sys.exit(main())
