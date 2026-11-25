import odlabel
import sys, json; sys.path.insert(0,'scripts'); import lib
import numpy as np, pandas as pd, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, mplhep as hep
plt.style.use(hep.style.CMS)
from abcd import tf_flatness
q=pd.read_parquet('red/qcd.parquet'); dt=pd.read_parquet('red/data.parquet')
out={}
# 1. scan
rows=[]
medges=np.array([40,60,80,100,130,170,220,300,480.])
for xc in (0.1,0.15,0.2,0.3):
  for yc in (1.0,1.2,1.5,1.8):
    px=(q.masym<xc).values; py=(q.deta<yc).values
    N={};V={}
    for n,m in (('A',px&py),('B',~px&py),('C',px&~py),('D',~px&~py)):
        N[n]=np.histogram(q.mavg[m],medges,weights=q.w[m])[0]; V[n]=np.histogram(q.mavg[m],medges,weights=q.w[m]**2)[0]
    k=N['A']*N['D']/(N['B']*N['C']); e=k*np.sqrt(sum(V[n]/N[n]**2 for n in 'ABCD'))
    s={n:N[n].sum() for n in 'ABCD'}; ki=s['A']*s['D']/(s['B']*s['C'])
    ew=ki*np.sqrt(sum(V[n].sum()/s[n]**2 for n in 'ABCD'))
    wm=np.sum(k/e**2)/np.sum(1/e**2); chi=np.sum(((k-wm)/e)**2)
    rows.append(dict(masym_cut=xc,deta_cut=yc,kappa=ki,kappa_err=ew,chi2_flat_vs_m=chi,ndf=len(k)-1,kmin=k.min(),kmax=k.max(),fracA=s['A']/sum(s.values())))
pd.DataFrame(rows).round(4).to_csv('fits/boundary_scan.csv',index=False)
print(pd.DataFrame(rows).round(3).to_string())
# 2. independence: TF = P(deta<1.2)/P(deta>1.2) vs masym
xe=np.array([0,.05,.1,.15,.2,.3,.4,.5,.6,.7,.8,.9,1.0001])
fig,axs=plt.subplots(1,2,figsize=(18,7))
ax=axs[0]
for d,l,c in ((q,'QCD MC','C0'),(dt[dt.masym>=0.2],'Data (masym>0.2 only; A blinded)','k')):
    r,e,chi,ndf=tf_flatness(d.masym.values.astype('f8'),-d.deta.values.astype('f8'),-1.2,xe,w=d.w.values)
    ok=np.ones(len(xe)-1,bool)
    # recompute centers for populated bins
    p=(d.deta<1.2).values; hp=np.histogram(d.masym[p],xe,weights=d.w[p])[0]; hf=np.histogram(d.masym[~p],xe,weights=d.w[~p])[0]; ok=(hp>0)&(hf>0)
    c_=0.5*(xe[1:]+xe[:-1])[ok]
    ax.errorbar(c_,r,e,fmt='o',color=c,label=f'{l}: $\\chi^2$/ndf={chi:.0f}/{ndf}')
    out['tf_vs_masym_'+l.split()[0]]=dict(chi2=chi,ndf=ndf)
ax.axvline(0.2,ls='--',c='gray'); ax.set_xlabel('mass asymmetry $|m_1-m_2|/(m_1+m_2)$'); ax.set_ylabel('N($\\Delta\\eta<1.2$) / N($\\Delta\\eta>1.2$)'); ax.legend(fontsize=11)
odlabel.label(ax,data=True,lumi=16.3)
# vs mavg in masym>=0.2 (B/D) both, and masym<0.2 (A/C) MC only
ax=axs[1]
for d,sel,l,c,mk in ((q,q.masym>=0.2,'MC B/D (masym>0.2)','C0','o'),(q,q.masym<0.2,'MC A/C (masym<0.2) [truth]','C3','s'),(dt,dt.masym>=0.2,'Data B/D (masym>0.2)','k','^')):
    dd=d[sel]; p=(dd.deta<1.2).values
    hp=np.histogram(dd.mavg[p],medges,weights=dd.w[p])[0]; hf=np.histogram(dd.mavg[~p],medges,weights=dd.w[~p])[0]
    vp=np.histogram(dd.mavg[p],medges,weights=dd.w[p]**2)[0]; vf=np.histogram(dd.mavg[~p],medges,weights=dd.w[~p]**2)[0]
    r=hp/hf; e=r*np.sqrt(vp/hp**2+vf/hf**2); c_=0.5*(medges[1:]+medges[:-1])
    ax.errorbar(c_,r,e,fmt=mk,color=c,label=l)
ax.set_xlabel('$m_{avg}$ [GeV]'); ax.set_ylabel('N($\\Delta\\eta<1.2$) / N($\\Delta\\eta>1.2$)'); ax.legend(fontsize=11)
odlabel.label(ax,data=True,lumi=16.3)
fig.savefig('plots/independence_tf_vs_masym_mavg.png'); fig.savefig('plots/independence_tf_vs_masym_mavg.pdf')
json.dump(out,open('fits/indep_stage1.json','w'),indent=1)
print(out)
