import odlabel
import sys; sys.path.insert(0,'scripts'); import lib
import numpy as np, pandas as pd, matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, mplhep as hep
plt.style.use(hep.style.CMS)
q=pd.read_parquet('red/qcd.parquet')
medges=np.array([40,60,80,100,130,170,220,300,480.])
rows=[]; fig,ax=plt.subplots(figsize=(10,8)); c_=0.5*(medges[1:]+medges[:-1])
for hi in (0.3,0.4,0.5,0.7,1.01):
  for yc in (1.2,):
    px=(q.masym<0.2).values; pxf=((q.masym>=0.2)&(q.masym<hi)).values; py=(q.deta<yc).values
    N={};V={}
    for n,m in (('A',px&py),('B',pxf&py),('C',px&~py),('D',pxf&~py)):
        N[n]=np.histogram(q.mavg[m],medges,weights=q.w[m])[0]; V[n]=np.histogram(q.mavg[m],medges,weights=q.w[m]**2)[0]
    k=N['A']*N['D']/(N['B']*N['C']); e=k*np.sqrt(sum(V[n]/N[n]**2 for n in 'ABCD'))
    s={n:N[n].sum() for n in 'ABCD'}; ki=s['A']*s['D']/(s['B']*s['C'])
    rows.append((hi,yc,round(ki,3),round(k.min(),3),round(k.max(),3),int(s['B']),int(s['D'])))
    ax.errorbar(c_*(1+0.01*hi),k,e,fmt='o-',label=f'fail-x band 0.2<masym<{min(hi,1):.1f}')
ax.axhline(1,c='gray',ls=':'); ax.set_xlabel('$m_{avg}$ [GeV]'); ax.set_ylabel('$\\kappa = A D/(B C)$ (QCD MC)'); ax.legend(fontsize=12)
odlabel.label(ax,data=False,lumi=16.3)
fig.savefig('plots/kappa_vs_mavg_failband.png'); fig.savefig('plots/kappa_vs_mavg_failband.pdf')
print(pd.DataFrame(rows,columns=['band_hi','deta_cut','kappa_incl','kmin','kmax','B_wsum','D_wsum']).to_string())
