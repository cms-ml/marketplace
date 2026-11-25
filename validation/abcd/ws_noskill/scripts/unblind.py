"""UNBLIND: fill data region A, compare to the frozen prediction in fits/blind_results.json, write fits/prediction.json and plots."""
import json, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, mplhep as hep
from abcd import *
plt.style.use(hep.style.CMS)
r=json.load(open("fits/blind_results.json")); D=derived(load("data"))
sel=(D["pt1"]>PT1MIN)&(D["asym"]<ASYM_SR)&(D["n2b10"]<CUT)&(D["n2b11"]<CUT)
obs=hist(D["mavg"][sel],D["w"][sel])[0]
pred=np.array(r["A_pred"]); st=np.array(r["stat"]); sy=np.array(r["syst"]); oth=np.array(r["other_A"]); eo=np.array(r["other_A_err"])
exp=pred+oth; eexp=np.sqrt(st**2+sy**2+eo**2)
pull=(obs-exp)/np.sqrt(eexp**2+obs); chi2=float((pull**2).sum())
# Poisson-based local significance (Gaussian-smeared expectation approximated by total variance)
res=dict(obs=obs.tolist(),exp=exp.tolist(),eexp=eexp.tolist(),pull=pull.tolist(),chi2=chi2,ndf=NB,obs_total=float(obs.sum()),exp_total=float(exp.sum()),
  max_local_dev=float(np.max(np.abs(pull))),max_bin=int(np.argmax(np.abs(pull))),ratio_total=float(obs.sum()/exp.sum()))
print({k:v for k,v in res.items() if k not in("obs","exp","eexp","pull")}); print("pull",np.round(pull,2)); print("obs/exp",np.round(obs/exp,3))
json.dump(res,open("fits/unblinded.json","w"))
pj=dict(edges=r["edges"],data_A_blinded_fill_removed="observed_A below is filled only after the prediction was frozen",data_B=r["data_B"],data_C=r["data_C"],data_D=r["data_D"],
  other_bkg_B=r["other_B"],other_C=r["other_C"],other_D=r["other_D"],other_bkg_A=r["other_A"],other_bkg_A_by_process=r["other_by_proc"],
  pred_qcd_A=r["A_pred"],stat_err=r["stat"],syst_err=r["syst"],tf=r["tf"],tf_err=r["etf"],observed_A=obs.tolist(),pull=pull.tolist())
pj.pop("data_A_blinded_fill_removed"); json.dump(pj,open("fits/prediction.json","w"),indent=1)
cx=0.5*(EDGES[1:]+EDGES[:-1]); xe=0.5*(EDGES[1:]-EDGES[:-1]); LAB=dict(lumi=16.3,com=13)
fig,(a,b)=plt.subplots(2,1,figsize=(11,11),gridspec_kw=dict(height_ratios=[3,1],hspace=0.05),sharex=True)
tot_err_stat=np.sqrt(st**2+eo**2);
a.stairs(pred,EDGES,color="C0",fill=True,alpha=0.5,label="QCD (ABCD prediction)"); a.stairs(pred+oth,EDGES,baseline=pred,color="C2",fill=True,alpha=0.6,label="W/Z/tt/VV/H (MC)")
band=lambda e:np.repeat(e,2)
a.fill_between(np.repeat(EDGES,2)[1:-1],np.repeat(exp-eexp,2),np.repeat(exp+eexp,2),facecolor="none",edgecolor="gray",hatch="///",label="Stat. $\\oplus$ syst.")
a.errorbar(cx,obs,yerr=np.sqrt(obs),xerr=xe,fmt="ko",label="Data (unblinded)"); a.set_yscale("log"); a.set_ylabel("Events / bin"); a.legend(fontsize=14); hep.cms.label("Private work",data=True,ax=a,**LAB)
b.errorbar(cx,obs/exp,yerr=np.sqrt(obs)/exp,xerr=xe,fmt="ko"); b.fill_between(np.repeat(EDGES,2)[1:-1],np.repeat(1-eexp/exp,2),np.repeat(1+eexp/exp,2),color="gray",alpha=0.4)
b.axhline(1,color="k",lw=0.8); b.set_ylim(0.7,1.3); b.set_ylabel("Data / Pred."); b.set_xlabel("$m_{avg}$ = ($m_{SD,1}+m_{SD,2}$)/2 [GeV]")
fig.savefig("plots/mavg_SR_unblinded.png"); fig.savefig("plots/mavg_SR_unblinded.pdf"); plt.close(fig)
