import odlabel
import sys, glob, json, numpy as np, pandas as pd
sys.path.insert(0,'/uscms_data/d3/ashrivas/AGENTS-AI/cms/marketplace/plugins/cms/skills/trigger-efficiency/scripts')
from turnon import efficiency, find_threshold, plateau
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, mplhep as hep
plt.style.use(hep.style.CMS)
edges=np.array([400,500,600,650,700,750,800,850,900,950,1000,1050,1100,1150,1200,1300,1400,1600,2000.])
H=['PFJet260','AK8PFJet260','PFJet450','AK8PFJet450','PFJet500','PFHT900','PFHT800']
combos={'PFHT900':['PFHT900'],'PFHT900|PFJet450':['PFHT900','PFJet450'],'PFHT900|PFJet450|AK8PFJet450':['PFHT900','PFJet450','AK8PFJet450'],'PFHT800|PFHT900|PFJet450|AK8PFJet450':['PFHT800','PFHT900','PFJet450','AK8PFJet450']}
refs=['PFJet260','AK8PFJet260']
acc={}; 
fired_frac={}
for fn in sorted(glob.glob('slim/data_*.parquet')):
    d=pd.read_parquet(fn,columns=['HT','j0_pt','j1_pt','j0_jetId','j1_jetId','j0_eta','j1_eta']+['HLT_'+t for t in H])
    era=fn.split('JetHT_2016')[1][0]
    sel=(d.j0_pt>250)&(d.j1_pt>250)&(abs(d.j0_eta)<2.4)&(abs(d.j1_eta)<2.4)&(d.j0_jetId>=2)&(d.j1_jetId>=2)
    d=d[sel]
    for t in H: fired_frac.setdefault(era,{}).setdefault(t,[]).append(d['HLT_'+t].mean())
    for r in refs:
        ref=d['HLT_'+r].values
        for cn,c in combos.items():
            f=np.logical_or.reduce([d['HLT_'+t].values for t in c])
            for var in ('HT','j0_pt'):
                x=d[var].values
                for tag,m in (('all',slice(None)),):
                    k=(r,cn,var)
                    a=acc.setdefault(k,[np.zeros(len(edges)-1),np.zeros(len(edges)-1)])
                    a[1]+=np.histogram(x[ref],edges)[0]; a[0]+=np.histogram(x[ref&f],edges)[0]
print({e:{t:float(np.mean(v)) for t,v in dd.items()} for e,dd in fired_frac.items()})
res={}
fig,axs=plt.subplots(1,2,figsize=(18,7))
for ax,var in zip(axs,('HT','j0_pt')):
  for (r,cn,v),(n,den) in acc.items():
    if v!=var or r!='PFJet260': continue
    e=efficiency(n,den); thr,i=find_threshold(e,edges,target=0.99,min_events=100)
    out=plateau(e,i) if i>=0 else None
    res[f'{r}/{cn}/{var}']={'thr':thr,'plateau':None if out is None else [float(o) for o in out]}
    c=0.5*(edges[1:]+edges[:-1]); ok=den>0
    ax.errorbar(c[ok],e['eff'][ok],yerr=[(e['eff']-e['lo'])[ok],(e['hi']-e['eff'])[ok]],fmt='o',ms=4,label=cn)
  ax.set_xlabel(f'offline {var} [GeV]'); ax.set_ylabel('Efficiency (ref. HLT_PFJet260)'); ax.set_ylim(0,1.05); ax.legend(fontsize=11); ax.axhline(1,c='gray',ls=':')
  odlabel.label(ax,data=True,lumi=16.3)
fig.savefig('plots/trigger_turnon.png'); fig.savefig('plots/trigger_turnon.pdf')
# cross-check with AK8 ref
for (r,cn,v),(n,den) in acc.items():
    if r=='AK8PFJet260':
        e=efficiency(n,den); thr,i=find_threshold(e,edges,target=0.99,min_events=100)
        res[f'{r}/{cn}/{v}']={'thr':thr,'plateau':None if i<0 else [float(o) for o in plateau(e,i)]}
    res[f'nref/{r}/{cn}/{v}']=int(den.sum())
json.dump(res,open('fits/trigger.json','w'),indent=1,default=float)
