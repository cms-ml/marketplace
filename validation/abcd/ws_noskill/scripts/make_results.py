import json, numpy as np
r=json.load(open("fits/blind_results.json")); u=json.load(open("fits/unblinded.json")); dn=json.load(open("fits/design_numbers.json")); co=json.load(open("fits/independence_corr.json")); th=json.load(open("fits/trigger_thresholds.json"))
cl=r["closure"]["SR"]; ok=np.isfinite(cl["pull"])
obs=np.array(cl["obs"]); pred=np.array(cl["pred"]); ep=np.array(cl["epred"])
# MC closure inclusive pull: need MC A stat; use ratio_err per bin: sigma_i = ratio_err_i*pred_i includes both
sig=np.array(cl["ratio_err"])*pred
cl_pull=float((obs.sum()-pred.sum())/np.sqrt((sig**2).sum()))
def vr(name,k,defn):
    v=r["valid"][k]; return dict(name=name,definition=defn,ratio=v["ratio"],pull=None,per_bin_chi2=v["chi2"],ndf=v["ndf"],per_bin_chi2_incl_syst=v["chi2_syst"],ndf_syst=v["ndf_syst"],ratio_per_bin=v["ratio_bins"],
      pull_per_bin_incl_syst=v["pull_syst"])
vrs=[vr("VR_asym","VR_asym","Same selection and tags but mass asymmetry >0.3 (complement of the SR asymmetry cut); A'=both N2<0.3"),
     vr("VR_pt1","VR_pt1","Same as SR but 200<pT2<300 GeV (below the SR pT2 cut)"),
     vr("VR_n2","VR_n2","Both jets fail the SR tag (N2>=0.3); shifted tag N2<0.36 defines A',B',C',D' inside it")]
for v in vrs:
    k=v["name"]; vv=r["valid"][k]; o=np.array(vv["obs"]);e=np.array(vv["exp"]);ee=np.array(vv["eexp"]); m=np.isfinite(vv["pull"])
    v["pull"]=float((o[m].sum()-e[m].sum())/np.sqrt(o[m].sum()+(ee[m]**2).sum()))
pred_t=np.array(r["A_pred"]); st=np.array(r["stat"]); sy=np.array(r["syst"])
B=np.array(r["data_B"]);C=np.array(r["data_C"]);D=np.array(r["data_D"])
nA=int(sum(u["obs"]))
res=dict(
 trigger=dict(paths=["HLT_PFHT900","HLT_PFJet450","HLT_AK8PFJet450"],offline_threshold="leading AK8 pT > 550 GeV (and pT2>300 GeV); plateau eff target 0.99 (found 0.998)",
   method="Reference-trigger (HLT_PFJet260, cross-checked with HLT_AK8PFJet260 and HLT_PFJet320) turn-on of the signal OR vs leading-jet pT, HT and subleading pT, Clopper-Pearson; paths present in both 2016G and H (HT800 absent in H, mass-trimmed paths deliberately not used to avoid mass bias). Data only; no trigger applied to MC (above plateau)."),
 trigger_numbers={k:v for k,v in th.items() if k.startswith("j0_")},
 preselection=["golden JSON (data), MET filters, trigger OR (data)","both leading AK8 jets tight jetId (>=2), |eta|<2.5","pT1>550 GeV, pT2>300 GeV","lepton veto: no loose muon/electron pT>10 GeV","mass asymmetry |m1-m2|/(m1+m2)<0.2 (equal-mass pair)","40<m_avg<440 GeV"],
 abcd_variables=[dict(name="N2_jet1",definition="N2^(beta=1) of the leading AK8 jet",cut="N2<0.30",signal_side="pass (N2<0.30, two-prong)"),
                 dict(name="N2_jet2",definition="N2^(beta=1) of the subleading AK8 jet",cut="N2<0.30",signal_side="pass (N2<0.30, two-prong)")],
 regions=dict(A="SIGNAL REGION: jet1 N2<0.3 and jet2 N2<0.3",B="jet1 N2<0.3, jet2 N2>=0.3",C="jet1 N2>=0.3, jet2 N2<0.3",D="jet1 N2>=0.3, jet2 N2>=0.3 (all with the common preselection)"),
 mavg_bins=r["edges"],
 independence=dict(method="MC QCD: weighted Pearson correlation of N2_1 vs N2_2 in 3 m_avg slices; per-bin rho=A*D/(B*C) in QCD MC; same rho in 3 data validation regions (A never used in the SR)",
   result=dict(pearson=co,rho_mc_per_bin=cl["ratio_bins"],rho_mc_mean_abs_dev_from_1=float(np.nanmean(np.abs(np.array(cl["ratio_bins"])-1))),
     conclusion="Variables are uncorrelated to ~1-3% inclusively, but TF depends strongly on m_avg (0.28->2), so the TF is measured per m_avg bin; residual rho deviates from 1 by 0-12%")),
 tf=dict(form="Per-m_avg-bin transfer factor TF(m_avg)=N_C/N_D (probability of jet2 passing N2 given jet1 fails), measured in data after subtracting non-QCD MC, applied to region B: A_pred=TF*B",
   values=r["tf"],uncertainty=r["etf"]),
 other_backgrounds=dict(method="W/Z+jets, ttbar, VV, H->bb from MC (xsec*lumi) subtracted from data in B, C, D before the TF; added back to the QCD prediction in A; +-50% normalisation variation in syst",
   fraction_in=r["other_frac"],note="fraction_in B,C,D = MC non-QCD / data; A = non-QCD/(non-QCD+QCD pred)"),
 prediction=dict(edges=r["edges"],value=r["A_pred"],stat_err=r["stat"],syst_err=r["syst"],total_inclusive=float(pred_t.sum()),
   total_err=float(np.sqrt((st**2).sum()+sy.sum()**2)),note="stat added in quadrature across bins; syst summed linearly (fully correlated); QCD only; non-QCD expectation in A in fits/prediction.json"),
 closure_mc=dict(ratio=cl["ratio_incl"],pull=cl_pull,per_bin_chi2=cl["chi2"],ndf=cl["ndf"],ratio_per_bin=cl["ratio_bins"],comment="stat-only chi2 is large (MC stat is very high): residual non-closure of 0-12% per bin is assigned as systematic"),
 validation_regions=vrs,
 non_closure_syst=dict(recipe="per bin sqrt((rho_MC-1)^2 + stat_rho^2 + 0.05^2), 0.05 flat added from VR_asym data-vs-MC rho differences; quadrature with +-50% non-QCD normalisation",relative_per_bin=r["nonclosure_rel"]),
 unblinded=dict(observed=u["obs"],expected=u["exp"],pulls=u["pull"],observed_total=u["obs_total"],expected_total=u["exp_total"],chi2=u["chi2"],ndf=u["ndf"],max_local_deviation_sigma=u["max_local_dev"]),
 n_events=dict(A=nA,B=int(B.sum()),C=int(C.sum()),D=int(D.sum()),note="data events in 40<m_avg<440 after full selection"),
 checks_done=["trigger turn-on with 3 independent references, vs j0pT, j1pT, HT, 2D map","N2 vs tau21 vs tau32/N3 discrimination (W/Z-matched vs QCD)","independence: correlation, per-bin rho in MC, 3 data VRs","MC closure (SR selection and 3 VR selections)","data validation regions (blind of SR)","smooth-TF and inclusive-TF cross-checks (inclusive TF fails: pred differs by 11%; pol2 fit chi2 poor, per-bin TF kept)","non-QCD MC subtraction and +-50% variation","unblinding only after prediction frozen (fits/blind_results.json)"],
 checks_not_done=["no signal MC: signal efficiency and signal contamination of B and C not evaluated (B,C contain 2eps(1-eps) of signal)","jet mass scale/resolution and JES/JER systematics on non-QCD MC not evaluated","MC trigger emulation not used; MC above data plateau only","no b-tag or flavour split; no pileup reweighting of MC (not needed for data-driven QCD, small for non-QCD)","VR_asym only passes after including flat 5% syst (derived from it)"],
 notes=["Open Data study, not official CMS result. Signal acceptance is limited by the high pT thresholds (pT1>550, pT2>300) required for a non-mass-biased trigger.",
  "Data in A are consistent with prediction: obs/exp total %.3f, chi2/ndf %.1f/%d, max local |pull| %.2f."%(u["ratio_total"],u["chi2"],u["ndf"],u["max_local_dev"]),
  "QCD MC is only used for design, independence and closure, never for the nominal normalisation.",
  "m_avg bins have 12-13% resolution proxy (VV MC); highest bins statistically limited (TF error 20-40%).","VR_asym is a region where independence is intrinsically worse; handled by flat 5%."])
json.dump(res,open("results.json","w"),indent=1); print("ok",nA,res["prediction"]["total_inclusive"],res["prediction"]["total_err"],cl_pull,[ (v['name'],round(v['pull'],2)) for v in vrs])
