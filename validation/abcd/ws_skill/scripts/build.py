"""Base selection + derived vars -> sel/<group>.parquet. Base: trigger OR (data), HT>1100, 2 leading AK8 jetId, |eta|<2.4, pT>250, lepton veto."""
import glob, json, numpy as np, pandas as pd, os, sys
os.makedirs('sel',exist_ok=True)
sumw=json.load(open('inputs/sumw.json'))
xs={l.split(',')[0]:float(l.split(',')[1]) for l in open('inputs/xsec.csv') if l[0]!='#'}
LUMI=16300.
groups={}
for fn in sorted(glob.glob('slim/*.parquet')):
    s=os.path.basename(fn).split('__')[0]
    g='data' if s.startswith('data') else ('qcd' if s.startswith('qcd') else ('vjets' if s[:3] in('wqq','zqq') else ('top' if s.startswith('tt') else ('vv' if s in('ww','wz','zz') else 'higgs'))))
    groups.setdefault(g,[]).append((s,fn))
for g,lst in groups.items():
    out=[]
    for s,fn in lst:
        d=pd.read_parquet(fn)
        trig=(d.HLT_PFHT900|d.HLT_PFJet450|d.HLT_AK8PFJet450)
        m=(d.HT>1100)&(d.j0_pt>250)&(d.j1_pt>250)&(abs(d.j0_eta)<2.4)&(abs(d.j1_eta)<2.4)&(d.j0_jetId>=2)&(d.j1_jetId>=2)&(d.nMuLoose==0)&(d.nEleLoose==0)
        if g=='data': m&=trig
        d=d[m]
        o=pd.DataFrame({'sample':s,'run':d.run.values if 'run' in d else 0,'HT':d.HT,'MET':d.MET_pt})
        for i in (0,1):
            for v in ('pt','eta','phi','mass','msoftdrop','tau1','tau2','tau3','n2b1','n3b1','btagHbb'): o[f'j{i}_{v}']=d[f'j{i}_{v}'].values
        if g!='data':
            o['w']=(d.genWeight.values.astype('f8')*xs[s]*LUMI/sumw[s]);
            for i in (0,1):
                o[f'j{i}_bosonDR']=d[f'j{i}_bosonDR'].values; o[f'j{i}_bosonId']=d[f'j{i}_bosonId'].values
        else: o['w']=1.0
        out.append(o)
    o=pd.concat(out,ignore_index=True)
    o['mavg']=0.5*(o.j0_msoftdrop+o.j1_msoftdrop)
    o['deta']=abs(o.j0_eta-o.j1_eta)
    o['masym']=abs(o.j0_msoftdrop-o.j1_msoftdrop)/(o.j0_msoftdrop+o.j1_msoftdrop).clip(lower=1e-3)
    o['ptasym']=abs(o.j0_pt-o.j1_pt)/(o.j0_pt+o.j1_pt)
    for i in (0,1):
        o[f'j{i}_t21']=o[f'j{i}_tau2']/o[f'j{i}_tau1'].clip(lower=1e-6)
        o[f'j{i}_t32']=o[f'j{i}_tau3']/o[f'j{i}_tau2'].clip(lower=1e-6)
    o['t21avg']=0.5*(o.j0_t21+o.j1_t21); o['t21max']=np.maximum(o.j0_t21,o.j1_t21)
    o['n2avg']=0.5*(o.j0_n2b1+o.j1_n2b1); o['n2max']=np.maximum(o.j0_n2b1,o.j1_n2b1)
    o['ptavg']=0.5*(o.j0_pt+o.j1_pt)
    o.to_parquet(f'sel/{g}.parquet',compression='snappy'); print(g,len(o),o.w.sum())
