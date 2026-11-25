"""Stage 2: read reduced skim file, apply golden JSON (data), filters, jetId; write slim columns (npz-like parquet) to fits/ntuples/."""
import sys, json, os, numpy as np, fsspec, pyarrow as pa, pyarrow.parquet as pq
from multiprocessing import Pool
BASE="root://cmseos.fnal.gov//store/user/ashrivas/cms-marketplace-tests/abcd-2016/ws_noskill_run3/red/"
OUT="fits/ntuples/"
gold=json.load(open("inputs/golden_2016.json"))
TRIG=["HLT_PFJet200","HLT_PFJet260","HLT_PFJet320","HLT_PFJet400","HLT_PFJet450","HLT_PFJet500","HLT_AK8PFJet200","HLT_AK8PFJet260",
 "HLT_AK8PFJet320","HLT_AK8PFJet400","HLT_AK8PFJet450","HLT_AK8PFJet500","HLT_PFHT650","HLT_PFHT800","HLT_PFHT900","HLT_DiPFJetAve260","HLT_DiPFJetAve400"]
J=["pt","eta","phi","mass","msoftdrop","btagHbb","tau1","tau2","tau3","n2b1","n3b1","jetId"]
COLS=["run","luminosityBlock","event","MET_pt","filters","HT","nMuLoose","nEleLoose","fixedGridRhoFastjetAll","nFatJet","j2_pt"]+[f"j{i}_{v}" for i in (0,1) for v in J]+TRIG
MCC=["genWeight","nTrueInt"]+[f"j{i}_{v}" for i in (0,1) for v in ("hadronFlavour","bosonDR","bosonId")]
def golden_mask(run,lb):
    m=np.zeros(len(run),bool)
    for r in np.unique(run):
        sel=run==r
        for a,b in gold.get(str(r),[]):
            m|=sel&(lb>=a)&(lb<=b)
    return m
def work(job):
    name,url=job
    isdata=name.startswith("data")
    out=OUT+name+".parquet"
    if os.path.exists(out): return name,-1
    with fsspec.open(url,"rb") as f:
        pf=pq.ParquetFile(f)
        have=pf.schema_arrow.names
        cols=[c for c in COLS+([] if isdata else MCC) if c in have]
        t=pf.read(columns=cols)
    d={c:t[c].to_numpy() for c in cols}
    n0=len(d["run"])
    m=d["filters"].astype(bool)&(d["j0_jetId"]>=2)&(d["j1_jetId"]>=2)   # tight (bit1) jet ID; 2016 jetId: 2=tight,6=tight+lepVeto
    if isdata: m&=golden_mask(d["run"],d["luminosityBlock"])
    for c in TRIG:
        if c not in d: d[c]=np.zeros(n0,bool)
    d={k:v[m] for k,v in d.items()}
    pq.write_table(pa.table(d),out,compression="snappy")
    return name,(n0,int(m.sum()))
if __name__=="__main__":
    os.makedirs(OUT,exist_ok=True)
    jobs=[tuple(l.split()) for l in open("condor/jobs.txt")]
    jobs=[(a,BASE+f"output_{a}.parquet") for a,_ in jobs]
    lo,hi=int(sys.argv[1]),int(sys.argv[2])
    with Pool(int(sys.argv[3])) as p:
        for r in p.imap_unordered(work,jobs[lo:hi]): print(r,flush=True)
