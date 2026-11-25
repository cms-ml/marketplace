import json, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, mplhep as hep
from abcd import *
plt.style.use(hep.style.CMS); out={}
Q=derived(load("qcd")); Dd=derived(load("data")); 
raw={g:np.load(f"fits/slim_{g}.npz") for g in ["wqq","zqq","vv"]}
# (a) N2 cut: V-matched leading jets vs QCD, 60<msd<120
def vm(z,i): return (np.abs(z[f"bosonId{i}"])>=23)&(np.abs(z[f"bosonId{i}"])<=24)&(z[f"bosonDR{i}"]<0.8)
V=np.concatenate([raw[g]["n2b10"][vm(raw[g],0)&(raw[g]["msoftdrop0"]>60)&(raw[g]["msoftdrop0"]<120)] for g in ["wqq","zqq"]])
Vw=np.concatenate([raw[g]["w"][vm(raw[g],0)&(raw[g]["msoftdrop0"]>60)&(raw[g]["msoftdrop0"]<120)] for g in ["wqq","zqq"]])
m=(Q["msoftdrop0"]>60)&(Q["msoftdrop0"]<120)
fig,ax=plt.subplots(); ax.hist(Q["n2b10"][m],40,(0.0,0.5),weights=Q["w"][m],density=True,histtype="step",label="QCD MC",lw=2); ax.hist(V,40,(0,0.5),weights=Vw,density=True,histtype="step",label="W/Z($qq$) matched",lw=2)
ax.axvline(CUT,color="k",ls="--"); ax.set_xlabel("Jet $N_2^{\\beta=1}$ ($60<m_{SD}<120$ GeV)"); ax.set_ylabel("Normalised")
es=Vw[V<CUT].sum()/Vw.sum(); eb=Q["w"][m][Q["n2b10"][m]<CUT].sum()/Q["w"][m].sum(); out["n2_cut"]=CUT; out["V_eff_n2"]=float(es); out["QCD_eff_n2"]=float(eb)
ax.legend(title=f"cut N2<{CUT}: V eff {es:.2f}, QCD eff {eb:.2f}",fontsize=14); hep.cms.label("Private work",data=False,ax=ax,com=13)
fig.savefig("plots/boundary_n2_cut.png"); fig.savefig("plots/boundary_n2_cut.pdf"); plt.close(fig)
# (b) mass asymmetry: dibosons with both leading jets V-matched vs QCD MC (preselected, pT1>300) 
z=raw["vv"]; both=vm(z,0)&vm(z,1)&(z["pt1"]>PT1MIN); zz=derived({k:z[k] for k in ["msoftdrop0","msoftdrop1","w"]})
fig,ax=plt.subplots(); s=(Q["pt1"]>PT1MIN)&(Q["mavg"]>40)
ax.hist(Q["asym"][s],40,(0,1),weights=Q["w"][s],density=True,histtype="step",label="QCD MC",lw=2)
ax.hist(zz["asym"][both],40,(0,1),density=True,histtype="step",label=f"VV MC, both jets V-matched (N={both.sum()})",lw=2)
ax.axvline(ASYM_SR,color="k",ls="--"); ax.set_xlabel(r"Mass asymmetry $|m_1-m_2|/(m_1+m_2)$"); ax.set_ylabel("Normalised")
out["asym_cut"]=ASYM_SR; out["VV_eff_asym"]=float((zz["asym"][both]<ASYM_SR).mean()); out["QCD_eff_asym"]=float(Q["w"][s&(Q["asym"]<ASYM_SR)].sum()/Q["w"][s].sum())
ax.legend(title=f"cut<{ASYM_SR}: VV eff {out['VV_eff_asym']:.2f}, QCD eff {out['QCD_eff_asym']:.2f}",fontsize=13); hep.cms.label("Private work",data=False,ax=ax,com=13)
fig.savefig("plots/boundary_mass_asym.png"); fig.savefig("plots/boundary_mass_asym.pdf"); plt.close(fig)
# (c) pT1 and N2 from data in region D (both fail) only: blind-safe; pT1 distribution with cut
d=(Dd["n2b10"]>=CUT)&(Dd["n2b11"]>=CUT)
fig,ax=plt.subplots(); ax.hist(Dd["pt1"][d],50,(200,900),histtype="step",label="Data, region D (both N2>0.3)",lw=2)
ax.hist(Q["pt1"][(Q["n2b10"]>=CUT)&(Q["n2b11"]>=CUT)],50,(200,900),weights=Q["w"][(Q["n2b10"]>=CUT)&(Q["n2b11"]>=CUT)],histtype="step",label="QCD MC, region D",lw=2)
ax.axvline(PT1MIN,color="k",ls="--"); ax.set_yscale("log"); ax.set_xlabel("Subleading AK8 jet $p_T$ [GeV]"); ax.set_ylabel("Events / 14 GeV"); ax.legend(fontsize=14); hep.cms.label("Private work",data=True,ax=ax,lumi=16.3,com=13)
fig.savefig("plots/boundary_pt1.png"); fig.savefig("plots/boundary_pt1.pdf"); plt.close(fig)
# (d) m_avg binning: resolution proxy from VV (both V matched): m_avg distribution + bins
fig,ax=plt.subplots(); ax.hist(zz["mavg"][both],np.arange(0,200,5),histtype="step",lw=2,label="VV MC both jets V-matched"); 
for e in EDGES: ax.axvline(e,color="gray",lw=0.5)
ax.set_xlabel("$m_{avg}$ [GeV]"); ax.set_ylabel("Events"); ax.legend(fontsize=14); hep.cms.label("Private work",data=False,ax=ax,com=13)
mm=zz["mavg"][both]; out["VV_mavg_res_rel"]=float(np.std(mm[(mm>60)&(mm<110)])/np.mean(mm[(mm>60)&(mm<110)]))
fig.savefig("plots/binning_mavg_resolution.png"); fig.savefig("plots/binning_mavg_resolution.pdf"); plt.close(fig)
json.dump(out,open("fits/design_numbers.json","w"),indent=1); print(out)
