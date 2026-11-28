"""Slim one skim file: golden JSON (data), MET filters, >=2 AK8 jets pT>170. Usage: slim.py sample url outfile"""
import sys, json, subprocess, os
import numpy as np, pyarrow.parquet as pq, pyarrow as pa
sample,url,out=sys.argv[1:4]
isdata=sample.startswith('data')
loc=out+'.in'
subprocess.run(['xrdcp','-f','-s',url,loc],check=True)
f=pq.ParquetFile(loc)
names=f.schema_arrow.names
trig=['PFJet260','PFJet400','PFJet450','PFJet500','AK8PFJet260','AK8PFJet400','AK8PFJet450','AK8PFJet500','PFHT650','PFHT800','PFHT900','DiPFJetAve260','DiPFJetAve400','AK8PFJet360_TrimMass30','AK8PFHT800_TrimMass50']
vars_=['pt','eta','phi','mass','msoftdrop','btagHbb','tau1','tau2','tau3','n2b1','n3b1','jetId']
cols=['run','luminosityBlock','event','MET_pt','fixedGridRhoFastjetAll','filters','HT','nMuLoose','nEleLoose','nFatJet','j2_pt']+['HLT_'+t for t in trig]+['j%d_%s'%(i,v) for i in (0,1) for v in vars_]
if not isdata:
    cols+=['genWeight','nTrueInt']+['j%d_%s'%(i,v) for i in (0,1) for v in ('bosonDR','bosonId','hadronFlavour')]
cols=[c for c in cols if c in names]
gj=json.load(open('inputs/golden_2016.json')) if isdata else None
outs=[]
for rg in range(f.metadata.num_row_groups):
    t=f.read_row_group(rg,columns=cols).to_pandas()
    m=(t.j1_pt>170)&t.filters
    if isdata:
        ok=np.zeros(len(t),bool)
        for r in np.unique(t.run):
            if str(r) not in gj: continue
            sel=(t.run==r).values
            ll=t.luminosityBlock.values
            for a,b in gj[str(r)]: ok|=sel&(ll>=a)&(ll<=b)
        m&=ok
    outs.append(t[m])
import pandas as pd
d=pd.concat(outs)
# fill missing trigger columns
for t in trig:
    if 'HLT_'+t not in d: d['HLT_'+t]=False
d.to_parquet(out,compression='snappy')
os.remove(loc)
print(sample,len(d),'of',f.metadata.num_rows)
