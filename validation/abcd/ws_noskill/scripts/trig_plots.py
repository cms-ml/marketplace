import os
import sys, json, numpy as np, matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt, mplhep as hep
sys.path.insert(0,os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../..', 'plugins/cms/skills/trigger-efficiency/scripts'))
from turnon import efficiency, find_threshold, plateau, plot_turnon
plt.style.use(hep.style.CMS)
z=np.load("fits/trig_counts.npz"); pt_e=z["pt_e"]; ht_e=z["ht_e"]
res={}
def lab(ax,x): ax.set_xlabel(x); ax.set_ylabel("Trigger efficiency"); ax.set_ylim(0,1.1); ax.axhline(1,color="gray",ls=":")
for nm,e_,xl in [("j0",pt_e,"Leading AK8 jet $p_T$ [GeV] ($p_{T,2}>200$ GeV)"),("j0b",pt_e,"Leading AK8 jet $p_T$ [GeV] ($p_{T,2}>300$ GeV)"),
                 ("HT",z["ht_e"],"AK4 $H_T$ [GeV] ($p_{T,2}>200$ GeV)"),("j1",pt_e,"Subleading AK8 jet $p_T$ [GeV] ($p_{T,1}>550$ GeV)")]:
    fig,ax=plt.subplots()
    for r,c,dx in [("HLT_PFJet260","k",0),("HLT_AK8PFJet260","r",3),("HLT_PFJet320","b",6)]:
        e=efficiency(z[f"{r}_{nm}_num"],z[f"{r}_{nm}_den"])
        plot_turnon(ax,e,e_,"ref. "+r,color=c,dx=dx,xerr=False)
        thr,i=find_threshold(e,e_,target=0.99,min_events=100)
        if i>=0:
            p=plateau(e,i); res[f"{nm}_{r}"]=dict(thr=thr,plateau=p[0],lo=p[1],hi=p[2],n=p[3])
    lab(ax,xl); ax.legend(title="Signal OR: PFHT900|PFJet450|AK8PFJet450",fontsize=14,loc="lower right")
    hep.cms.label("Private work",data=True,lumi=16.3,com=13,ax=ax)
    fig.savefig(f"plots/trigger_turnon_{nm}.png"); fig.savefig(f"plots/trigger_turnon_{nm}.pdf"); plt.close(fig)
# 2D map
r="HLT_PFJet260"; e=efficiency(z[f"{r}_num2"],z[f"{r}_den2"])
eff=np.where(z[f"{r}_den2"]>=20,e["eff"],np.nan)
fig,ax=plt.subplots(figsize=(9,8)); m=ax.pcolormesh(pt_e,pt_e,eff.T,vmin=0.5,vmax=1,cmap="viridis"); plt.colorbar(m,label="Efficiency (den $\\geq$20)")
ax.set_xlabel("Leading AK8 $p_T$ [GeV]"); ax.set_ylabel("Subleading AK8 $p_T$ [GeV]"); hep.cms.label("Private work",data=True,lumi=16.3,com=13,ax=ax,fontsize=14)
fig.savefig("plots/trigger_turnon_2d.png"); fig.savefig("plots/trigger_turnon_2d.pdf"); plt.close(fig)
# individual paths
fig,ax=plt.subplots(); den=z["HLT_PFJet260_j0_den"]
for s in ["HLT_PFHT900","HLT_PFJet450","HLT_AK8PFJet450"]:
    e=efficiency(z["ind_"+s],den); plot_turnon(ax,e,pt_e,s,xerr=False)
lab(ax,"Leading AK8 jet $p_T$ [GeV]"); ax.legend(); fig.savefig("plots/trigger_individual_paths.png"); plt.close(fig)
# print rows of 2D eff at selected points
for a in [450,500,550,600,650]:
    ia=np.searchsorted(pt_e,a); print("j0>",a,"min eff over j1 bins:",[ (int(pt_e[j]),round(float(eff[ia,j]),3)) for j in range(0,len(pt_e)-1,4) if not np.isnan(eff[ia,j])])
json.dump(res,open("fits/trigger_thresholds.json","w"),indent=1); print(json.dumps(res,indent=0))
