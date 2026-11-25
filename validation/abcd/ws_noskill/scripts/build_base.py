"""Baseline (pT0>550, pT1>200, lepton veto, trigger OR for data) -> compact per-file npz in fits/base/. Row-group processing to limit memory."""
import glob, os, json, numpy as np, pyarrow.parquet as pq
from multiprocessing import Pool
LUMI=16300.
sumw=json.load(open("inputs/sumw.json"))
xs={l.split(",")[0]:float(l.split(",")[1]) for l in open("inputs/xsec.csv") if l[0]!="#"}
SIG=["HLT_PFHT900","HLT_PFJet450","HLT_AK8PFJet450"]
V=["pt","eta","phi","mass","msoftdrop","btagHbb","tau1","tau2","tau3","n2b1","n3b1"]
def proc(t,cols,isdata,samp):
    d={c:t[c].to_numpy() for c in cols}
    m=(d["j0_pt"]>550)&(d["j1_pt"]>200)&(d["nMuLoose"]==0)&(d["nEleLoose"]==0)
    if isdata: m&=d[SIG[0]]|d[SIG[1]]|d[SIG[2]]
    out={k:v[m] for k,v in d.items() if k not in SIG}
    out["w"]=(np.ones(m.sum()) if isdata else xs[samp]*LUMI*out["genWeight"].astype(float)/sumw[samp])
    return out
def work(f):
    name=os.path.basename(f)[:-8]; samp=name.split("__")[0]; isdata=samp.startswith("data")
    cols=["run","luminosityBlock","event","MET_pt","HT","nMuLoose","nEleLoose","j2_pt"]+[f"j{i}_{v}" for i in (0,1) for v in V]+SIG
    if not isdata: cols+=["genWeight"]+[f"j{i}_{v}" for i in (0,1) for v in ("bosonDR","bosonId","hadronFlavour")]
    pf=pq.ParquetFile(f); parts=[]
    for rg in range(pf.metadata.num_row_groups):
        parts.append(proc(pf.read_row_group(rg,columns=cols),cols,isdata,samp))
    out={k:np.concatenate([p[k] for p in parts]) for k in parts[0]}
    np.savez(f"fits/base/{name}.npz",**out)
    return name,len(out["w"])
if __name__=="__main__":
    os.makedirs("fits/base",exist_ok=True)
    fs=sorted(glob.glob("fits/ntuples/*.parquet"))
    with Pool(3) as p:
        for r in p.imap_unordered(work,fs): print(r,flush=True)
