import numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, mplhep as hep, json
plt.style.use(hep.style.CMS)
q=np.load("fits/slim_qcd.npz"); w_=np.load("fits/slim_wqq.npz"); z_=np.load("fits/slim_zqq.npz")
def jets(z,sel=None):
    out={}
    for v in ["pt","msoftdrop","n2b1","n3b1","tau21_","tau32_"]:
        pass
    return out
def getj(z,i,names): return {n:z[f"{n}{i}"] for n in names}
names=["pt","msoftdrop","n2b1","tau21_","tau32_","n3b1"]
# V-jets: leading jets matched to W/Z (|id| 23/24, dR<0.8); QCD: all leading jets (use mass window 60-120)
V={n:np.concatenate([np.concatenate([zz[f"{n}0"][(np.abs(zz["bosonId0"])>=23)&(np.abs(zz["bosonId0"])<=24)&(zz["bosonDR0"]<0.8)] for zz in (w_,z_)])]) for n in names}
Vw=np.concatenate([zz["w"][(np.abs(zz["bosonId0"])>=23)&(np.abs(zz["bosonId0"])<=24)&(zz["bosonDR0"]<0.8)] for zz in (w_,z_)])
# unmatched QCD jets (QCD has no bosons; bosonId may be 0) -> all
Q={n:q[f"{n}0"] for n in names}; Qw=q["w"]
mw=lambda d:(d["msoftdrop"]>60)&(d["msoftdrop"]<120)
Vm=mw(V); Qm=mw(Q)
print("V jets",Vm.sum(),Vw[Vm].sum(),"QCD jets in 60-120",Qm.sum(),Qw[Qm].sum())
res={}
fig,axs=plt.subplots(2,3,figsize=(22,12))
for ax,(n,rng,lab) in zip(axs.flat,[("n2b1",(0,0.5),"$N_2^{\\beta=1}$"),("tau21_",(0,1.2),"$\\tau_{21}$"),("tau32_",(0,1.2),"$\\tau_{32}$"),("n3b1",(0,3),"$N_3^{\\beta=1}$"),("msoftdrop",(0,300),"$m_{SD}$ [GeV]"),("pt",(550,1500),"$p_T$ [GeV]")]):
    ax.hist(Q[n][Qm],bins=40,range=rng,weights=Qw[Qm],density=True,histtype="step",label="QCD MC, $60<m_{SD}<120$",color="C0")
    ax.hist(V[n][Vm],bins=40,range=rng,weights=Vw[Vm],density=True,histtype="step",label="W/Z(qq) matched, $60<m_{SD}<120$",color="C3")
    if n in("msoftdrop","pt"):
        ax.cla(); ax.hist(Q[n],bins=40,range=rng,weights=Qw,density=True,histtype="step",label="QCD MC (all)",color="C0"); ax.hist(V[n],bins=40,range=rng,weights=Vw,density=True,histtype="step",label="W/Z(qq) matched",color="C3")
    ax.set_xlabel(lab); ax.set_ylabel("Normalised"); ax.legend(fontsize=13)
fig.savefig("plots/design_substructure_dists.png"); fig.savefig("plots/design_substructure_dists.pdf"); plt.close(fig)
# ROC: signal eff vs QCD mistag for N2<c, tau21<c  (low = signal-like)
fig,ax=plt.subplots()
for n,lab in [("n2b1","$N_2$"),("tau21_","$\\tau_{21}$"),("tau32_","$\\tau_{32}$"),("n3b1","$N_3$")]:
    c=np.quantile(V[n][Vm],np.linspace(0.02,0.98,60)) 
    es=[Vw[Vm][V[n][Vm]<x].sum()/Vw[Vm].sum() for x in c]; eb=[Qw[Qm][Q[n][Qm]<x].sum()/Qw[Qm].sum() for x in c]
    ax.plot(es,eb,label=lab); res[n]={"bkg_eff_at_sig50":float(np.interp(0.5,es,eb)),"bkg_eff_at_sig70":float(np.interp(0.7,es,eb))}
ax.set_yscale("log"); ax.set_xlabel("W/Z jet efficiency"); ax.set_ylabel("QCD jet efficiency"); ax.legend()
fig.savefig("plots/design_substructure_roc.png"); fig.savefig("plots/design_substructure_roc.pdf"); plt.close(fig)
# mass dependence of N2 in QCD: median N2 vs msd
fig,ax=plt.subplots(); e=np.arange(0,401,20); c=0.5*(e[1:]+e[:-1])
for n,lab in [("n2b1","$N_2$"),("tau21_","$\\tau_{21}$")]:
    med=[np.median(Q[n][(Q["msoftdrop"]>=a)&(Q["msoftdrop"]<b)]) if ((Q["msoftdrop"]>=a)&(Q["msoftdrop"]<b)).sum()>100 else np.nan for a,b in zip(e[:-1],e[1:])]
    ax.plot(c,med,"o-",label="QCD median "+lab)
ax.set_xlabel("Jet $m_{SD}$ [GeV]"); ax.set_ylabel("Median"); ax.legend(); fig.savefig("plots/design_n2_vs_mass.png"); plt.close(fig)
print(json.dumps(res,indent=1)); json.dump(res,open("fits/design_roc.json","w"))
