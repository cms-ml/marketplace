"""Accumulate trigger turn-on counts (den/num) over all data files. Output fits/trig_counts.npz"""
import glob, numpy as np, pyarrow.parquet as pq
from multiprocessing import Pool
SIG=["HLT_PFHT900","HLT_PFJet450","HLT_AK8PFJet450"]
REFS=["HLT_PFJet260","HLT_AK8PFJet260","HLT_PFJet320"]
pt_e=np.arange(200,1201,25.); ht_e=np.arange(400,2001,50.)
def work(f):
    cols=["j0_pt","j1_pt","j0_eta","j1_eta","HT","run"]+SIG+REFS
    d=pq.read_table(f,columns=cols).to_pydict() if False else {c:pq.read_table(f,columns=[c])[c].to_numpy() for c in cols}
    fired=np.zeros(len(d["run"]),bool)
    for s in SIG: fired|=d[s]
    out={}
    for r in REFS:
        ref=d[r]
        # 2D (j0pt, j1pt) for the 2D map
        out[f"{r}_den2"]=np.histogram2d(d["j0_pt"][ref],d["j1_pt"][ref],[pt_e,pt_e])[0]
        out[f"{r}_num2"]=np.histogram2d(d["j0_pt"][ref&fired],d["j1_pt"][ref&fired],[pt_e,pt_e])[0]
        for nm,x,extra in [("j0",d["j0_pt"],d["j1_pt"]>200),("j1",d["j1_pt"],d["j0_pt"]>550),("HT",d["HT"],d["j1_pt"]>200),
                           ("j0b",d["j0_pt"],d["j1_pt"]>300)]:
            e=ht_e if nm=="HT" else pt_e
            m=ref&extra
            out[f"{r}_{nm}_den"]=np.histogram(x[m],e)[0]; out[f"{r}_{nm}_num"]=np.histogram(x[m&fired],e)[0]
    # per-path individual efficiencies vs j0 pt with ref PFJet260
    ref=d["HLT_PFJet260"]&(d["j1_pt"]>200)
    for s in SIG: out[f"ind_{s}"]=np.histogram(d["j0_pt"][ref&d[s]],pt_e)[0]
    return out
if __name__=="__main__":
    fs=sorted(glob.glob("fits/ntuples/data_*.parquet"))
    tot=None
    with Pool(5) as p:
        for o in p.imap_unordered(work,fs):
            tot=o if tot is None else {k:tot[k]+o[k] for k in o}
    np.savez("fits/trig_counts.npz",pt_e=pt_e,ht_e=ht_e,**tot); print("done",len(fs))
