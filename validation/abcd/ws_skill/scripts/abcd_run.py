"""Full ABCD: blind stage (default) and --unblind. Regions (SR):
A: masym<0.2 & deta<1.2 | B: 0.2<=masym<0.4 & deta<1.2 | C: masym<0.2 & deta>=1.2 | D: 0.2<=masym<0.4 & deta>=1.2"""
import odlabel
import sys, json; sys.path.insert(0,'scripts'); import lib
import numpy as np, pandas as pd
from abcd import *
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt, mplhep as hep
from scipy.stats import chi2 as chi2d
plt.style.use(hep.style.CMS)
UNBLIND='--unblind' in sys.argv
EDGES=np.array([40,60,80,100,120,140,160,180,200,230,260,300,350,400,480.]); MC_=0.5*(EDGES[1:]+EDGES[:-1]); NB=len(MC_)
OTHER=['vjets','top','vv','higgs']; OTHER_UNC=0.30
TESTS={ # name: (x pass range, x fail range, y pass range, y fail range)
 'SR':((0,.2),(.2,.4),(0,1.2),(1.2,9)),
 'VR1_xshift':((.2,.4),(.4,.6),(0,1.2),(1.2,9)),
 'VR2_yshift':((0,.2),(.2,.4),(1.2,1.8),(1.8,9)),
 'VR3_xyshift':((.2,.4),(.4,.6),(1.2,1.8),(1.8,9)),
}
def rng(v,r): return (v>=r[0])&(v<r[1])
def hists(d,t):
    xp,xf,yp,yf=TESTS[t]; out={}
    for n,(xr,yr) in dict(A=(xp,yp),B=(xf,yp),C=(xp,yf),D=(xf,yf)).items():
        m=(rng(d.masym.values,xr)&rng(d.deta.values,yr))
        w=d.w.values[m]; x=d.mavg.values[m]
        out[n]=(np.histogram(x,EDGES,weights=w)[0],np.histogram(x,EDGES,weights=w**2)[0])
    return out
qcd=pd.read_parquet('red/qcd.parquet'); dat=pd.read_parquet('red/data.parquet')
oth={g:pd.read_parquet(f'red/{g}.parquet') for g in OTHER}
H_q={t:hists(qcd,t) for t in TESTS}; H_d={t:hists(dat,t) for t in TESTS}
H_o={t:{g:hists(oth[g],t) for g in OTHER} for t in TESTS}
def oth_sum(t,r,scale=1.0):
    v=sum(H_o[t][g][r][0] for g in OTHER)*scale; e2=sum(H_o[t][g][r][1] for g in OTHER)
    return v,e2
def predict(H,t,subtract=None,scale=1.0,order=None):
    """H[t][r]=(sumw,sumw2). subtract: function r->(yield,var) of other bkg to remove."""
    y={};e={}
    for r in 'ABCD':
        v,v2=H[t][r]
        if subtract is not None and r!='A':
            o,o2=subtract(t,r,scale); v=v-o; v2=v2+o2
        y[r]=v; e[r]=np.sqrt(v2)
    B,C,D=y['B'],y['C'],y['D']
    ok=(B>0)&(D>0)
    tf=np.where(ok,B/np.where(D>0,D,1),np.nan); etf=tf*np.sqrt((e['B']/np.where(B>0,B,1))**2+(e['D']/np.where(D>0,D,1))**2)
    ord_,co,cv,chi,ndf=tf_fit_ftest(MC_[ok],tf[ok],etf[ok]) if order is None else (order,)+_fit(MC_[ok],tf[ok],etf[ok],order)
    V=np.vander(MC_,ord_+1)
    tff=V@co; cov_tf=V@cv@V.T
    pred=C*tff
    cov=np.diag((e['C']*tff)**2)+np.outer(C,C)*cov_tf
    return dict(pred=pred,cov=cov,tf=tf,etf=etf,tffit=tff,order=ord_,tf_chi2=chi,tf_ndf=ndf,y=y,e=e,ok=ok,cov_tf=cov_tf)
def _fit(m,r,e,n):
    c,cv=np.polyfit(m,r,n,w=1/e,cov="unscaled"); return c,cv,float(np.sum(((r-np.polyval(c,m))/e)**2)),len(m)-n-1
def compare(obs,eobs,p):
    pred=p['pred']; cov=p['cov']
    tot=pred.sum(); etot=np.sqrt(cov.sum())
    ratio,pull=closure(obs.sum(),tot,etot,np.sqrt((eobs**2).sum()))
    chi2,ndf,pulls=chi2_cov(obs,pred,cov,eobs)
    # shape: normalise pred to obs total
    return dict(ratio=float(ratio),pull=float(pull),rel_stat=float(np.hypot(etot,np.sqrt((eobs**2).sum()))/tot),chi2=float(chi2),ndf=int(ndf),pulls=pulls,obs=obs,pred=pred)
res={'tests':{}}
# --- MC closure & validation (QCD MC only, no subtraction)
for t in TESTS:
    p=predict(H_q,t); a,a2=H_q[t]['A']
    c=compare(a,np.sqrt(a2),p); c['order']=p['order']; res['tests']['MC_'+t]=(p,c)
# --- data validation (non-QCD subtracted from B,C,D and A)
for t in TESTS:
    if t=='SR': continue
    p=predict(H_d,t,subtract=oth_sum)
    a=H_d[t]['A'][0]-oth_sum(t,'A')[0]; ea=np.sqrt(H_d[t]['A'][1]+oth_sum(t,'A')[1])
    c=compare(a,ea,p); c['order']=p['order']; res['tests']['DATA_'+t]=(p,c)
# print summary of tests
tests_for_syst=[]; shape_terms=[]
for k,(p,c) in res['tests'].items():
    print(k,'order',c['order'],'ratio %.3f pull %.1f chi2/ndf %.1f/%d tfchi2/ndf %.1f/%d'%(c['ratio'],c['pull'],c['chi2'],c['ndf'],p['tf_chi2'],p['tf_ndf']))
    if k=='MC_SR' or k.startswith('MC_VR') or k.startswith('DATA_VR'):
        tests_for_syst.append((c['ratio'],c['pull'],c['rel_stat']))
        # per-bin shape deviation of obs/pred after normalising to the inclusive ratio
        dev=c['obs']/c['pred']/c['ratio']-1
        est=np.sqrt(np.maximum(c['obs'],1))/c['pred']  # approx per-bin stat (data) ; MC: sumw2 smaller
        eo=np.sqrt(np.diag(p['cov']))/c['pred']
        # use pulls to decide: excess over per-bin total uncertainty
        tot=np.hypot(eo,np.sqrt(1/np.maximum(c['obs'],1)) if k.startswith('DATA') else 0.0)
        shape_terms.append(np.sqrt(np.maximum(0,dev**2-tot**2)))
syst_corr=float(nonclosure_syst(tests_for_syst))
shape=np.max(shape_terms,axis=0)
print('non-closure corr syst %.4f'%syst_corr); print('shape terms',np.round(shape,3))
# --- signal-region prediction from data
pD=predict(H_d,'SR',subtract=oth_sum)
pD_up=predict(H_d,'SR',subtract=oth_sum,scale=1+OTHER_UNC); pD_dn=predict(H_d,'SR',subtract=oth_sum,scale=1-OTHER_UNC)
oth_A=oth_sum('SR','A')[0]
other_syst=0.5*np.abs(pD_up['pred']-pD_dn['pred'])  # + effect of other-A scale added below on the A side
other_A_unc=OTHER_UNC*oth_A
qcd_pred=pD['pred']; stat_err=np.sqrt(np.diag(pD['cov']))
Sc=syst_cov(qcd_pred,syst_corr,shape)+np.outer(other_syst,other_syst)+np.diag(other_A_unc**2)
syst_err=np.sqrt(np.diag(Sc))
total_pred=qcd_pred+oth_A
cov_tot=pD['cov']+Sc
tot=float(total_pred.sum()); etot=float(np.sqrt(cov_tot.sum()))
# regions yield / fractions
nev={r:int(H_d['SR'][r][0].sum()) for r in 'BCD'}
frac={}
for r in 'ABCD':
    o=oth_sum('SR',r)[0].sum(); frac[r]=float(o/(o+H_q['SR'][r][0].sum()))
print('other fraction (MC QCD+other) per region',frac)
print('pred total %.0f +- %.0f ; TF order %d chi2/ndf %.1f/%d'%(tot,etot,pD['order'],pD['tf_chi2'],pD['tf_ndf']))
out=dict(edges=EDGES.tolist(),qcd_pred=qcd_pred.tolist(),stat_err=stat_err.tolist(),syst_err=syst_err.tolist(),other_A=oth_A.tolist(),
 total_pred=total_pred.tolist(),B=H_d['SR']['B'][0].tolist(),C=H_d['SR']['C'][0].tolist(),D=H_d['SR']['D'][0].tolist(),
 tf=np.where(pD['ok'],pD['tf'],0).tolist(),tf_err=np.nan_to_num(pD['etf']).tolist(),tf_fit=pD['tffit'].tolist(),tf_order=pD['order'],
 syst_corr=syst_corr,shape_term=shape.tolist(),other_frac=frac,n_events=nev)
# ---------- plots
def ratio_panel(fig_name,items,title):
    pass
for k,(p,c) in res['tests'].items():
    pass
# test plots
fig,axs=plt.subplots(2,3,figsize=(24,12),gridspec_kw=dict(height_ratios=[3,1]))
names=['MC_SR','MC_VR1_xshift','MC_VR2_yshift','DATA_VR1_xshift','DATA_VR2_yshift','DATA_VR3_xyshift']
fig,axs=plt.subplots(2,6,figsize=(40,10),gridspec_kw=dict(height_ratios=[3,1]),sharex='col')
for j,k in enumerate(names):
    p,c=res['tests'][k]; ax,rx=axs[0,j],axs[1,j]
    ax.stairs(c['obs'],EDGES,label='observed A$_{test}$' ,color='k',lw=2);
    ax.stairs(c['pred'],EDGES,label='predicted',color='C3',lw=2)
    e=np.sqrt(np.diag(p['cov'])); ax.stairs(c['pred']+e,EDGES,baseline=c['pred']-e,fill=True,alpha=.3,color='C3')
    ax.set_yscale('log'); ax.set_title(f"{k}: ratio {c['ratio']:.3f}, $\\chi^2$/ndf {c['chi2']:.0f}/{c['ndf']}",fontsize=16); ax.legend(fontsize=12)
    ax.set_ylabel('Events / bin');
    r=c['obs']/c['pred']; rx.errorbar(MC_,r,e/c['pred'],fmt='ko'); rx.axhline(1,c='gray',ls=':'); rx.set_ylim(.7,1.3); rx.set_xlabel('$m_{avg}$ [GeV]'); rx.set_ylabel('obs/pred')
fig.savefig('plots/closure_and_validation.png',dpi=70); fig.savefig('plots/closure_and_validation.pdf')
# TF vs mavg
fig,ax=plt.subplots(figsize=(10,8))
pm,_=res['tests']['MC_SR']
ax.errorbar(MC_,pm['tf'],pm['etf'],fmt='s',color='C0',label='QCD MC  B/D')
ax.errorbar(MC_*1.01,pD['tf'],pD['etf'],fmt='ko',label='Data  B/D (non-QCD subtracted)')
ax.plot(MC_,pD['tffit'],'C3-',label=f"data fit, order {pD['order']}")
e=np.sqrt(np.diag(pD['cov_tf'])); ax.fill_between(MC_,pD['tffit']-e,pD['tffit']+e,color='C3',alpha=.3)
ax.set_xlabel('$m_{avg}$ [GeV]'); ax.set_ylabel('TF = N($\\Delta\\eta<1.2$)/N($\\Delta\\eta>1.2$), $0.2<$masym$<0.4$'); ax.legend()
odlabel.label(ax,data=True,lumi=16.3); fig.savefig('plots/tf_vs_mavg.png'); fig.savefig('plots/tf_vs_mavg.pdf')
# MC closure per component? (all QCD HT bins already summed)
res_json=dict(out=out,tests={k:dict(ratio=c['ratio'],pull=c['pull'],chi2=c['chi2'],ndf=c['ndf'],rel_stat=c['rel_stat'],tf_order=p['order'],tf_chi2=p['tf_chi2'],tf_ndf=p['tf_ndf']) for k,(p,c) in res['tests'].items()})
json.dump(res_json,open('fits/stage1.json' if not UNBLIND else 'fits/stage1_rerun.json','w'),indent=1)
if UNBLIND:
    full=pd.read_parquet('sel/data.parquet',columns=['mavg','masym','deta'])
    full=full[(full.mavg>=lib.MLO)&(full.mavg<lib.MHI)]
    m=(full.masym<0.2)&(full.deta<1.2)
    obs=np.histogram(full.mavg[m],EDGES)[0].astype(float)
    chi,ndf,pulls=chi2_cov(obs,total_pred,cov_tot)
    # local deviation per bin: use Poisson-ish with full cov diag
    print('UNBLINDED obs total',obs.sum(),'pred',tot,'+-',etot,'chi2/ndf %.1f/%d'%(chi,ndf),'max |pull|',np.abs(pulls).max())
    out.update(observed=obs.tolist(),chi2=float(chi),ndf=int(ndf),pulls=pulls.tolist(),max_local=float(np.abs(pulls).max()),obs_total=float(obs.sum()),total_inclusive=tot,total_err=etot)
    json.dump(out,open('fits/final.json','w'),indent=1)
    fig,(ax,rx)=plt.subplots(2,1,figsize=(11,11),gridspec_kw=dict(height_ratios=[3,1]),sharex=True)
    ax.stairs(oth_A+qcd_pred,EDGES,label='QCD (ABCD) + other',color='C3',lw=2)
    ax.stairs(oth_A,EDGES,label='other bkg (V+jets, top, VV, H; MC)',color='C2',lw=2)
    et=np.sqrt(np.diag(cov_tot)); ax.stairs(total_pred+et,EDGES,baseline=total_pred-et,fill=True,alpha=.3,color='C3',label='stat $\\oplus$ syst')
    ax.errorbar(MC_,obs,np.sqrt(obs),xerr=np.diff(EDGES)/2,fmt='ko',label='Data (unblinded SR)')
    ax.set_yscale('log'); ax.set_ylabel('Events / bin'); ax.legend(); odlabel.label(ax,data=True,lumi=16.3)
    rx.errorbar(MC_,obs/total_pred,np.sqrt(obs)/total_pred,fmt='ko'); rx.stairs(1+et/total_pred,EDGES,baseline=1-et/total_pred,fill=True,alpha=.3,color='C3')
    rx.axhline(1,c='gray',ls=':'); rx.set_ylim(.7,1.3); rx.set_xlabel('$m_{avg}$ [GeV]'); rx.set_ylabel('Obs / pred')
    fig.savefig('plots/mavg_SR_prediction.png'); fig.savefig('plots/mavg_SR_prediction.pdf')
