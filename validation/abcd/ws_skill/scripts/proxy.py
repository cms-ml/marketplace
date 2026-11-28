import numpy as np, pandas as pd, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, mplhep as hep
plt.style.use(hep.style.CMS)
cols=['mavg','deta','masym','ptasym','t21avg','n2avg','ptavg','w','j0_msoftdrop','j1_msoftdrop','j0_bosonDR','j1_bosonDR','j0_bosonId','j1_bosonId','sample']
q=pd.read_parquet('sel/qcd.parquet',columns=cols); t=pd.read_parquet('sel/top.parquet',columns=cols); v=pd.read_parquet('sel/vjets.parquet',columns=cols); vv=pd.read_parquet('sel/vv.parquet',columns=cols)
t=t[(t['sample']=='tt_had')&(t.j0_bosonDR<0.8)&(t.j1_bosonDR<0.8)&(abs(t.j0_bosonId)==6)&(abs(t.j1_bosonId)==6)]
vv=vv[(vv.j0_bosonDR<0.8)&(vv.j1_bosonDR<0.8)]
print('proxy counts raw: tt both-matched',len(t),'vv matched',len(vv))
rng={'deta':(0,2.6,26),'ptasym':(0,.6,30),'masym':(0,1,25),'t21avg':(0,1,25),'n2avg':(0,0.5,25),'mavg':(0,400,40)}
fig,axs=plt.subplots(2,3,figsize=(21,12))
for ax,(k,(a,b,n)) in zip(axs.flat,rng.items()):
    for d,l,c in ((q[(q.mavg>40)],'QCD MC (mavg>40)','C0'),(t,'t$\\bar{t}$ both jets top-matched (pair proxy)','C3'),(vv,'VV both jets matched','C2')):
        h,e=np.histogram(d[k],n and np.linspace(a,b,n+1),weights=d.w); h=h/max(h.sum(),1e-9)
        ax.stairs(h,e,label=l,color=c,lw=2)
    ax.set_xlabel(k); ax.set_ylabel('Fraction of events')
axs[0,0].legend(fontsize=10)
fig.savefig('plots/var_shapes_proxy.png'); fig.savefig('plots/var_shapes_proxy.pdf')
for k,cut in (('deta',1.3),('deta',1.0),('ptasym',0.1),('masym',0.2),('t21avg',0.5),('n2avg',0.2)):
    f=lambda d:(d[k]<cut).mul(d.w).sum()/d.w.sum()
    print(k,cut,'eff QCD %.3f tt %.3f vv %.3f'%(f(q[q.mavg>40]),f(t),f(vv)))
