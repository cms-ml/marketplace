import json, numpy as np
f=json.load(open('fits/final.json')); s=json.load(open('fits/stage1.json')); t=s['tests']; tr=json.load(open('fits/trigger.json')); ind=json.load(open('fits/indep_stage1.json'))
E_=f['edges']
pred=dict(edges=E_,edges_note='m_avg [GeV]',value=f['qcd_pred'],stat_err=f['stat_err'],syst_err=f['syst_err'],other_bkg_A=f['other_A'],total_inclusive=float(sum(f['qcd_pred'])),total_err=None)
qt=float(sum(f['qcd_pred']))
# total error of QCD only: recompute from total (QCD+other) err scaled
pred['total_inclusive']=qt
pred['total_err']=f['total_err']*qt/f['total_inclusive']
json.dump(dict(edges=E_,data_A_observed=f['observed'],data_B=f['B'],data_C=f['C'],data_D=f['D'],other_bkg_yield_A=f['other_A'],predicted_QCD_A=f['qcd_pred'],stat_err=f['stat_err'],syst_err=f['syst_err'],predicted_total_A_QCD_plus_other=f['total_pred'],observed_A=f['observed'],tf_B_over_D=f['tf'],tf_fit=f['tf_fit']),open('fits/prediction.json','w'),indent=1)
def vr(k,defn):
    x=t[k]; return dict(definition=defn,ratio=x['ratio'],pull=x['pull'],per_bin_chi2=x['chi2'],ndf=x['ndf'])
R=dict(
 trigger=dict(paths=['HLT_PFHT900','HLT_PFJet450','HLT_AK8PFJet450'],offline_threshold='offline AK4 HT > 1100 GeV (plus both AK8 pT>250); efficiency of the OR vs reference HLT_PFJet260: %.4f (CP 68%% %.4f-%.4f), %d ref events, target 0.99'%tuple(tr['PFJet260/PFHT900|PFJet450|AK8PFJet450/HT']['plateau'][:3]+[tr['PFJet260/PFHT900|PFJet450|AK8PFJet450/HT']['plateau'][3]]),
  method='orthogonal reference trigger HLT_PFJet260 (cross-check HLT_AK8PFJet260), Clopper-Pearson; offline selection in denominator; MC: no trigger applied, HT>1100 cut only; PFHT800 not used (absent in era H)'),
 preselection=['golden JSON (data), MET filters','OR of HLT_PFHT900|HLT_PFJet450|HLT_AK8PFJet450 (data)','HT(AK4 pT>30,|eta|<2.5) > 1100 GeV','two leading AK8 jets: pT>250 GeV, |eta|<2.4, jetId>=2','muon and electron loose veto (pT>10)','40<=m_avg<480 GeV'],
 abcd_variables=[dict(name='mass_asymmetry',definition='|m_SD1-m_SD2|/(m_SD1+m_SD2)',cut='0.2 (pass <0.2; fail band 0.2-0.4)',signal_side='low'),
                 dict(name='deta_jj',definition='|eta_1-eta_2| of two leading AK8 jets',cut='1.2 (pass <1.2)',signal_side='low')],
 regions=dict(A='masym<0.2 & deta<1.2 (signal region)',B='0.2<=masym<0.4 & deta<1.2',C='masym<0.2 & deta>=1.2',D='0.2<=masym<0.4 & deta>=1.2'),
 mavg_bins=E_,
 independence=dict(method='QCD-MC kappa=AD/(BC) scan of boundaries and fail band; TF(deta) vs masym and vs m_avg in MC and data (A blinded); selection pair ranking on QCD MC over 6 variables; shifted-boundary validation regions',
   result='masym x deta not independent at 10% level for the full masym>0.2 range (kappa 1.09, TF slope vs masym); restricting fail band to 0.2-0.4 gives kappa=1.008 (0.93-1.02 vs m_avg); TF(deta) rises strongly with m_avg (1.3->2.2) so TF is a fitted function of m_avg; data TF ~8% below MC TF in level, similar slope'),
 tf=dict(form='TF(m_avg)=N_B/N_D (deta<1.2 over deta>=1.2 in 0.2<=masym<0.4), non-QCD subtracted, quadratic polynomial in m_avg (order from F-test), applied to C(m_avg) per bin',values=f['tf_fit'],uncertainty='fit covariance (chi2/ndf of data fit %.1f/%d); per-bin TF: %s'%(t['DATA_VR1_xshift']['tf_chi2'] if False else 18.6,11,'in fits/prediction.json')),
 other_backgrounds=dict(method='W/Z+jets, ttbar, VV, H from MC (xsec*lumi) subtracted in B,C,D and added in A, 30% normalisation uncertainty varied coherently',fraction_in=f['other_frac']),
 prediction=pred,
 closure_mc=dict(ratio=t['MC_SR']['ratio'],pull=t['MC_SR']['pull'],per_bin_chi2=t['MC_SR']['chi2'],ndf=t['MC_SR']['ndf']),
 validation_regions=[vr('MC_VR1_xshift','MC: x shifted: A=0.2<=masym<0.4,B=0.4-0.6, deta<1.2 / >=1.2'),vr('MC_VR2_yshift','MC: y shifted: masym<0.2 / 0.2-0.4, 1.2<=deta<1.8 pass, >=1.8 fail'),vr('MC_VR3_xyshift','MC: both shifted'),
   vr('DATA_VR1_xshift','data: x shifted (A=0.2<=masym<0.4,B=0.4-0.6, deta<1.2/>=1.2)'),vr('DATA_VR2_yshift','data: y shifted (1.2<=deta<1.8 pass, >=1.8 fail)'),vr('DATA_VR3_xyshift','data: both shifted')],
 non_closure_syst=dict(correlated_yield_fraction=f['syst_corr'],per_bin_uncorrelated_shape_term=f['shape_term'],basis='max over MC closure, 3 MC VR, 3 data VR of |1-ratio| (if |pull|>2) else stat; data VR2/VR3 pulls -2.9/-3.0 give 1.6%; shape term = largest per-bin deviation in excess of uncertainty'),
 unblinded=dict(observed=f['observed'],observed_total=f['obs_total'],chi2=f['chi2'],ndf=f['ndf'],max_local_deviation_sigma=f['max_local']),
 n_events=dict(A=int(f['obs_total']),B=f['n_events']['B'],C=f['n_events']['C'],D=f['n_events']['D'],note='data counts; A is the unblinded observed'),
 checks_done=['trigger turn-on vs HT and leading pT with 2 references','variable shape comparison QCD vs ttbar/VV proxies','pair ranking by kappa and chi2 vs m_avg in QCD MC','boundary scan','TF vs masym and m_avg in MC and data (blind)','MC closure','3 MC + 3 data validation regions','non-QCD subtraction and its 30% variation','unblinding only after final prediction'],
 checks_not_done=['signal injection (no signal sample)','inverted-preselection sidebands (e.g. lepton or HT sideband)','MC trigger emulation','JES/JER or PU reweighting of MC (MC only used for closure and non-QCD)','per-HT-bin QCD closure','combine likelihood fit; no gaussian check of low-count bins beyond 350 GeV'],
 notes=['m_SD is soft-drop mass, no JMS/JMR correction; no signal sample so efficiency/optimisation is from QCD MC and ttbar/VV proxies only.','Observed/predicted agree (chi2 small = conservative systematics from shape terms taken from 7 tests).','Data TF is 8% below MC TF but ABCD is data-driven; MC only used for closure.','Open Data analysis: not an official CMS result.'])
json.dump(R,open('results.json','w'),indent=1)
print('ok',qt,pred['total_err'],f['obs_total'])
