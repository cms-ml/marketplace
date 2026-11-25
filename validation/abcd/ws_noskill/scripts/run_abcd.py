"""Blinded ABCD: builds all region histograms, TF, prediction, closure and validation. Data region A is never histogrammed here."""
import json, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, mplhep as hep
from abcd import *
plt.style.use(hep.style.CMS)
LAB=dict(lumi=16.3,com=13)
D=derived(load("data")); Q=derived(load("qcd"))
OTH={g:derived(load(g)) for g in ["wqq","zqq","tt","vv","hbb"]}
cx=0.5*(EDGES[1:]+EDGES[:-1]); xe=0.5*(EDGES[1:]-EDGES[:-1])
def passf(z,c=CUT): return z["n2b10"]<c, z["n2b11"]<c
def region_set(z,kind,blind=False):
    p0,p1=passf(z)
    if kind=="SR": sel=(z["pt1"]>PT1MIN)&(z["asym"]<ASYM_SR)
    elif kind=="VR_asym": sel=(z["pt1"]>PT1MIN)&(z["asym"]>0.3)
    elif kind=="VR_pt1": sel=(z["pt1"]>200)&(z["pt1"]<PT1MIN)&(z["asym"]<ASYM_SR)
    elif kind=="VR_n2":   # both jets fail the SR tag (N2>0.3); sub-divide at N2<0.36
        sel=(z["pt1"]>PT1MIN)&(z["asym"]<ASYM_SR)&(z["n2b10"]>=CUT)&(z["n2b11"]>=CUT); p0=z["n2b10"]<0.36; p1=z["n2b11"]<0.36
    return four(z,sel,p0,p1,blind=blind and kind=="SR")
def others(kind):
    tot=None
    for g,z in OTH.items():
        r=region_set(z,kind)
        tot=r if tot is None else {k:(tot[k][0]+r[k][0],tot[k][1]+r[k][1]) for k in r}
    return tot
def chi(obs,vobs,pred,epred,extra=0):
    pull=(obs-pred)/np.sqrt(vobs+epred**2+extra**2); ok=np.isfinite(pull)&(obs>0)&(pred>0)&(vobs>0)
    pull=np.where(ok,pull,np.nan); return pull,float(np.nansum(pull**2)),int(ok.sum())
res={}; H={}
# ---- MC QCD closure for all region sets
closure={}
for kind in ["SR","VR_asym","VR_pt1","VR_n2"]:
    R=region_set(Q,kind); pred,epred,tf,etf=predict(R["B"],R["C"],R["D"])
    obs,vobs=R["A"]; pull,c2,nd=chi(obs,vobs,pred,epred)
    closure[kind]=dict(obs=obs.tolist(),pred=pred.tolist(),epred=epred.tolist(),ratio_bins=(obs/pred).tolist(),ratio_err=(np.sqrt(vobs+epred**2)/pred).tolist(),pull=pull.tolist(),chi2=c2,ndf=nd,
        ratio_incl=float(np.nansum(np.where(np.isfinite(pred)&(obs>0),obs,0))/np.nansum(np.where(np.isfinite(pred)&(obs>0),pred,0))),pull_incl=float(np.nan),
        tf=tf.tolist(),etf=etf.tolist(),rhoA=R["A"][0].tolist())
# ---- data validation regions (blind of SR)
OT={k:others(k) for k in ["SR","VR_asym","VR_pt1","VR_n2"]}
DR={k:region_set(D,k,blind=True) for k in ["SR","VR_asym","VR_pt1","VR_n2"]}
def datapred(kind,f=1.0):
    Rs=sub({k:DR[kind][k] for k in "BCD"},{k:OT[kind][k] for k in "BCD"},f)
    return predict(Rs["B"],Rs["C"],Rs["D"])+(Rs,)
valid={}
for kind in ["VR_asym","VR_pt1","VR_n2"]:
    pred,epred,tf,etf,Rs=datapred(kind)
    obs,vobs=DR[kind]["A"]; oa=OT[kind]["A"]
    # total expectation = QCD prediction + other bkg in A
    exp=pred+oa[0]; eexp=np.sqrt(epred**2+oa[1])
    pull,c2,nd=chi(obs,obs,exp,eexp)
    cm=closure[kind]; rr=np.array(cm["ratio_bins"]); er=np.array(cm["ratio_err"]); ncv=np.nan_to_num(np.sqrt((rr-1)**2+er**2),nan=0,posinf=0)
    pulls,c2s,nds=chi(obs,obs,exp,eexp,extra=pred*np.sqrt(ncv**2+0.05**2))
    valid[kind]=dict(pull_syst=pulls.tolist(),chi2_syst=c2s,ndf_syst=nds,nc_rel=ncv.tolist(),obs=obs.tolist(),pred_qcd=pred.tolist(),other=oa[0].tolist(),exp=exp.tolist(),eexp=eexp.tolist(),pull=pull.tolist(),chi2=c2,ndf=nd,
         ratio=float(np.nansum(np.where(np.isfinite(pull),obs,0))/np.nansum(np.where(np.isfinite(pull),exp,0))),pull_incl=float(np.nan),ratio_bins=(obs/exp).tolist(),ratio_err=(np.sqrt(obs+eexp**2)/exp).tolist())
# ---- SR prediction
pred,epred,tf,etf,Rs=datapred("SR")
# non-closure syst from MC: |rho-1| (+) MC stat error on rho; rho=obsA/pred in QCD MC
cl=closure["SR"]; rho=np.array(cl["ratio_bins"]); erho=np.array(cl["ratio_err"])
FLAT=0.05  # extra flat relative syst: mean |rho_data-rho_MC| in the data VRs (asym VR ~5%), fixed before unblinding
nonclos=np.sqrt((rho-1)**2+erho**2+FLAT**2)
# other-bkg normalisation systematic: +-50% on all non-QCD MC
pu=datapred("SR",1.5)[0]; pd=datapred("SR",0.5)[0]
syst_oth=np.abs(pu-pd)/2
syst=np.sqrt((pred*nonclos)**2+syst_oth**2)
oA=OT["SR"]["A"]
# inclusive-TF cross-check
Bs,Cs,Ds=Rs["B"],Rs["C"],Rs["D"]
tf_incl=Cs[0].sum()/Ds[0].sum(); pred_incl=Bs[0]*tf_incl
out=dict(edges=EDGES.tolist(),A_pred=pred.tolist(),stat=epred.tolist(),syst=syst.tolist(),syst_nonclosure=(pred*nonclos).tolist(),syst_other=syst_oth.tolist(),tf=tf.tolist(),etf=etf.tolist(),
  nonclosure_rel=nonclos.tolist(),other_A=oA[0].tolist(),other_A_err=np.sqrt(oA[1]).tolist(),
  data_B=DR["SR"]["B"][0].tolist(),data_C=DR["SR"]["C"][0].tolist(),data_D=DR["SR"]["D"][0].tolist(),
  other_B=OT["SR"]["B"][0].tolist(),other_C=OT["SR"]["C"][0].tolist(),other_D=OT["SR"]["D"][0].tolist(),
  pred_inclusiveTF=pred_incl.tolist(),tf_inclusive=float(tf_incl),closure=closure,valid=valid,
  other_by_proc={g:region_set(z,"SR")["A"][0].tolist() for g,z in OTH.items()})
# other-bkg fractions in regions (of data for B,C,D; of data-pred for A unknown -> of QCD pred+other)
frac={k:float(OT["SR"][k][0].sum()/DR["SR"][k][0].sum()) for k in "BCD"}
frac["A"]=float(oA[0].sum()/(oA[0].sum()+pred.sum()))
out["other_frac"]=frac
json.dump(out,open("fits/blind_results.json","w"))
# smooth-TF cross-check: weighted pol2 fit of log TF vs m_avg (not used for the nominal)
co=np.polyfit(cx,np.log(tf),2,w=tf/etf); tfs=np.exp(np.polyval(co,cx)); chi_smooth=float((((tf-tfs)/etf)**2).sum())
out["smooth_tf_chi2"]=chi_smooth; out["pred_smoothTF"]=(Bs[0]*tfs).tolist(); json.dump(out,open("fits/blind_results.json","w"))
print("frac",frac,"tf_incl",tf_incl,"smooth chi2/ndf",chi_smooth,NB-3)
print("pred tot",pred.sum(),"stat",np.sqrt((epred**2).sum()),"syst lin",syst.sum(),"inclTF pred",pred_incl.sum(),"smooth",(Bs[0]*tfs).sum())
for k in closure: print("MC closure",k,"ratio_incl",round(closure[k]["ratio_incl"],3),"chi2/ndf",round(closure[k]["chi2"],1),closure[k]["ndf"])
for k in valid: print("DATA VR",k,"ratio",round(valid[k]["ratio"],3),"chi2/ndf",round(valid[k]["chi2"],1),valid[k]["ndf"],"| with syst:",round(valid[k]["chi2_syst"],1),valid[k]["ndf_syst"])
# ---------------- plots
def ratio_plot(name,obs,exp,eexp,ratio,rerr,title,xl,obslab,explab,logy=True):
    fig,(a,b)=plt.subplots(2,1,figsize=(11,11),gridspec_kw=dict(height_ratios=[3,1],hspace=0.05),sharex=True)
    a.stairs(exp,EDGES,color="C0",label=explab,linewidth=2)
    a.errorbar(cx,obs,yerr=np.sqrt(np.maximum(obs,0)),fmt="ko",label=obslab)
    a.fill_between(np.repeat(EDGES,2)[1:-1],np.repeat(exp-eexp,2),np.repeat(exp+eexp,2),color="C0",alpha=0.3,step=None,label="Pred. unc.")
    if logy:a.set_yscale("log")
    a.set_ylabel("Events / bin"); a.legend(title=title,fontsize=14); hep.cms.label("Private work",data=True,ax=a,**LAB)
    b.errorbar(cx,ratio,yerr=rerr,xerr=xe,fmt="ko"); b.axhline(1,color="gray"); b.set_ylim(0.5,1.5); b.set_ylabel("Obs / Pred"); b.set_xlabel(xl)
    fig.savefig(f"plots/{name}.png"); fig.savefig(f"plots/{name}.pdf"); plt.close(fig)
XL="$m_{avg}$ = ($m_{SD,1}+m_{SD,2}$)/2 [GeV]"
for k,t in [("SR","MC QCD closure, SR selection"),("VR_asym","MC closure VR asym>0.3"),("VR_pt1","MC closure VR $p_{T,2}$<300"),("VR_n2","MC closure VR N2 shifted")]:
    c=closure[k]; ratio_plot(f"closure_mc_{k}",np.array(c["obs"]),np.array(c["pred"]),np.array(c["epred"]),np.array(c["ratio_bins"]),np.array(c["ratio_err"]),t,XL,"QCD MC, true A","QCD MC, B$\\cdot$C/D")
for k,t in [("VR_asym","Data VR: $\\Delta m$/m>0.3"),("VR_pt1","Data VR: 200<$p_{T,2}$<300"),("VR_n2","Data VR: both N2>0.3, shifted tag 0.36")]:
    v=valid[k]; ratio_plot(f"validation_data_{k}",np.array(v["obs"]),np.array(v["exp"]),np.array(v["eexp"]),np.array(v["ratio_bins"]),np.array(v["ratio_err"]),t,XL,"Data, region A'","Pred. QCD + other")
# TF vs mavg
fig,ax=plt.subplots(); ax.errorbar(cx,tf,yerr=etf,xerr=xe,fmt="ko",label="Data, C/D (other bkg subtracted)")
ax.errorbar(cx+2,closure["SR"]["tf"],yerr=closure["SR"]["etf"],fmt="s",color="C3",label="QCD MC, C/D")
ax.plot(cx,tfs,"b-",label="pol2 fit to log TF (cross-check)"); ax.axhline(tf_incl,color="gray",ls="--",label="inclusive TF (data)")
ax.set_yscale("log"); ax.set_xlabel(XL); ax.set_ylabel("TF = N(jet-2 pass)/N(jet-2 fail) | jet-1 fail"); ax.legend(fontsize=13); hep.cms.label("Private work",data=True,ax=ax,**LAB)
fig.savefig("plots/tf_vs_mavg.png"); fig.savefig("plots/tf_vs_mavg.pdf"); plt.close(fig)
# independence: rho vs mavg in MC and data VRs
fig,ax=plt.subplots()
ax.errorbar(cx,closure["SR"]["ratio_bins"],yerr=closure["SR"]["ratio_err"],xerr=xe,fmt="ro",label="QCD MC, SR selection")
for k,c in [("VR_asym","C0"),("VR_pt1","C2"),("VR_n2","C4")]:
    ax.errorbar(cx+3*(1+["VR_asym","VR_pt1","VR_n2"].index(k)),valid[k]["ratio_bins"],yerr=valid[k]["ratio_err"],fmt="o",color=c,label="Data "+k,markersize=5)
ax.axhline(1,color="gray"); ax.set_ylim(0.5,1.6); ax.set_xlabel(XL); ax.set_ylabel(r"$\rho$ = A$\cdot$D/(B$\cdot$C)  (obs A / pred A)"); ax.legend(fontsize=12); hep.cms.label("Private work",data=True,ax=ax,**LAB)
fig.savefig("plots/independence_rho_vs_mavg.png"); fig.savefig("plots/independence_rho_vs_mavg.pdf"); plt.close(fig)
# 2D correlation N2_0 vs N2_1 in QCD MC (SR sel, in two mass slices) + correlation coefficients
sel=(Q["pt1"]>PT1MIN)&(Q["asym"]<ASYM_SR)&(Q["mavg"]>40)&(Q["mavg"]<440)
def wcorr(x,y,w):
    mx=np.average(x,weights=w); my=np.average(y,weights=w); return float(np.average((x-mx)*(y-my),weights=w)/np.sqrt(np.average((x-mx)**2,weights=w)*np.average((y-my)**2,weights=w)))
corr={}
fig,axs=plt.subplots(1,3,figsize=(24,7.5))
for ax,(lo,hi) in zip(axs,[(40,100),(100,200),(200,440)]):
    s=sel&(Q["mavg"]>=lo)&(Q["mavg"]<hi); corr[f"{lo}-{hi}"]=wcorr(Q["n2b10"][s],Q["n2b11"][s],Q["w"][s])
    ax.hist2d(Q["n2b10"][s],Q["n2b11"][s],bins=30,range=[[0.05,0.45]]*2,weights=Q["w"][s],cmap="viridis")
    ax.axvline(CUT,color="w",ls="--"); ax.axhline(CUT,color="w",ls="--"); ax.set_title(f"QCD MC, {lo}<$m_{{avg}}$<{hi} GeV, corr={corr[f'{lo}-{hi}']:.3f}",fontsize=16)
    ax.set_xlabel("$N_2$ jet 1 (leading)"); ax.set_ylabel("$N_2$ jet 2")
fig.savefig("plots/independence_2d_n2_mc.png"); fig.savefig("plots/independence_2d_n2_mc.pdf"); plt.close(fig)
corr["inclusive"]=wcorr(Q["n2b10"][sel],Q["n2b11"][sel],Q["w"][sel])
json.dump(corr,open("fits/independence_corr.json","w")); print("corr",corr)
# data vs MC in B,C,D (blind-safe) for the SR selection
fig,axs=plt.subplots(1,3,figsize=(27,8))
for ax,k in zip(axs,"BCD"):
    ax.errorbar(cx,DR["SR"][k][0],yerr=np.sqrt(DR["SR"][k][0]),fmt="ko",label=f"Data {k}")
    ax.stairs(Q and region_set(Q,"SR")[k][0],EDGES,label="QCD MC (xsec-norm.)",color="C3")
    ax.stairs(OT["SR"][k][0],EDGES,label="Non-QCD MC",color="C2"); ax.set_yscale("log"); ax.set_xlabel(XL); ax.set_ylabel("Events / bin"); ax.legend(title=f"Region {k}",fontsize=14)
fig.savefig("plots/datamc_BCD.png"); fig.savefig("plots/datamc_BCD.pdf"); plt.close(fig)
