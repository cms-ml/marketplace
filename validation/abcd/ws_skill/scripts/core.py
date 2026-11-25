"""Shared ABCD machinery for the extra plots (copy of the frozen logic in abcd_run.py, parametrised; writes nothing)."""
import odlabel
import sys, json; sys.path.insert(0,'scripts'); import lib
import numpy as np, pandas as pd
from abcd import *
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, mplhep as hep
plt.style.use(hep.style.CMS)
EDGES=np.array([40,60,80,100,120,140,160,180,200,230,260,300,350,400,480.]); MC_=0.5*(EDGES[1:]+EDGES[:-1])
OTHER=['vjets','top','vv','higgs']; INF=99.
FINAL=json.load(open('fits/final.json'))
SYST_CORR=FINAL['syst_corr']; SHAPE=np.array(FINAL['shape_term'])
def label(ax,data=True,lumi=16.3):
    odlabel.label(ax,data=data,lumi=lumi)
def save(fig,name):
    fig.savefig(f'plots/{name}.png',dpi=100); fig.savefig(f'plots/{name}.pdf'); plt.close(fig)
def rng(v,r): return (v>=r[0])&(v<r[1])
def hists(d,xp,xf,yp,yf,mask=None):
    out={}
    for n,(xr,yr) in dict(A=(xp,yp),B=(xf,yp),C=(xp,yf),D=(xf,yf)).items():
        m=(rng(d.masym.values,xr)&rng(d.deta.values,yr))
        if mask is not None: m&=mask
        w=d.w.values[m]; x=d.mavg.values[m]
        out[n]=(np.histogram(x,EDGES,weights=w)[0],np.histogram(x,EDGES,weights=w**2)[0])
    return out
def load_all():
    return pd.read_parquet('red/qcd.parquet'),pd.read_parquet('red/data.parquet'),{g:pd.read_parquet(f'red/{g}.parquet') for g in OTHER}
def predict(H,subtract=None,mode='poly'):
    y={};e={}
    for r in 'ABCD':
        v,v2=H[r]
        if subtract is not None and r!='A':
            o,o2=subtract[r]; v=v-o; v2=v2+o2
        y[r]=v; e[r]=np.sqrt(v2)
    B,C,D=y['B'],y['C'],y['D']; ok=(B>0)&(D>0)
    tf=np.where(ok,B/np.where(D>0,D,1),np.nan); etf=tf*np.sqrt((e['B']/np.where(B>0,B,1))**2+(e['D']/np.where(D>0,D,1))**2)
    if mode=='poly':
        o_,co,cv,chi,ndf=tf_fit_ftest(MC_[ok],tf[ok],etf[ok]); V=np.vander(MC_,o_+1); tff=V@co
        cov=np.diag((e['C']*tff)**2)+np.outer(C,C)*(V@cv@V.T); pred=C*tff; order=o_
    elif mode=='incl':
        pred,cov=abcd_binned(B,C,D,e['B'],e['C'],e['D'],tf='inclusive'); tff=np.full_like(MC_,B.sum()/D.sum()); order=0; chi,ndf=np.nan,0
    else:
        pred,err=abcd(B,C,D,e['B'],e['C'],e['D']); cov=np.diag(err**2); tff=tf; order=-1; chi,ndf=np.nan,0
    return dict(pred=pred,cov=cov,tf=tf,etf=etf,tffit=tff,order=order,y=y,e=e,tf_chi2=chi,tf_ndf=ndf)
def compare(obs,eobs,p):
    pred=p['pred']; cov=p['cov']; tot=pred.sum(); etot=np.sqrt(cov.sum())
    ratio,pull=closure(obs.sum(),tot,etot,np.sqrt((eobs**2).sum()))
    chi2,ndf,pulls=chi2_cov(obs,pred,cov,eobs)
    return dict(ratio=float(ratio),pull=float(pull),rel_stat=float(np.hypot(etot,np.sqrt((eobs**2).sum()))/tot),chi2=float(chi2),ndf=int(ndf),pulls=pulls,obs=obs,eobs=eobs,pred=pred,err_ratio=float(np.hypot(etot,np.sqrt((eobs**2).sum()))/tot))
def oth_sub(O,xp,xf,yp,yf,mask=None):
    Ho={g:hists(O[g],xp,xf,yp,yf,mask) for g in OTHER}
    return {r:(sum(Ho[g][r][0] for g in OTHER),sum(Ho[g][r][1] for g in OTHER)) for r in 'ABCD'}
NOM=dict(xp=(0,.2),xf=(.2,.4),yp=(0,1.2),yf=(1.2,INF))
def mc_test(q,xp,xf,yp,yf,mask=None,mode='poly'):
    H=hists(q,xp,xf,yp,yf,mask); p=predict(H,mode=mode); a,a2=H['A']
    return p,compare(a,np.sqrt(a2),p)
def data_test(dat,O,xp,xf,yp,yf,mode='poly'):
    H=hists(dat,xp,xf,yp,yf); S=oth_sub(O,xp,xf,yp,yf); p=predict(H,subtract=S,mode=mode)
    a=H['A'][0]-S['A'][0]; ea=np.sqrt(H['A'][1]+S['A'][1]); return p,compare(a,ea,p)
VR={'VR1_xshift':dict(xp=(.2,.4),xf=(.4,.6),yp=(0,1.2),yf=(1.2,INF)),'VR2_yshift':dict(xp=(0,.2),xf=(.2,.4),yp=(1.2,1.8),yf=(1.8,INF)),'VR3_xyshift':dict(xp=(.2,.4),xf=(.4,.6),yp=(1.2,1.8),yf=(1.8,INF))}
def band(c,p):
    """frozen systematic band (relative) on a test's prediction"""
    Sc=syst_cov(p['pred'],SYST_CORR,SHAPE); return np.sqrt(np.diag(Sc))/p['pred'], np.sqrt(np.diag(p['cov']))/p['pred']
