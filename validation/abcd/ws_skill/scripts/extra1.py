import sys; sys.path.insert(0,'scripts'); from core import *
q,dat,O=load_all()
# sanity: reproduce frozen MC closure
p,c=mc_test(q,**NOM); print('MC closure ratio %.4f (frozen 1.001) chi2 %.1f/%d'%(c['ratio'],c['chi2'],c['ndf']))
tests={}
# 1 per-bin MC closure
sb,eb=band(c,p)
fig,(ax,rx)=plt.subplots(2,1,figsize=(11,10),gridspec_kw=dict(height_ratios=[3,1.3]),sharex=True)
ax.stairs(c['obs'],EDGES,color='k',lw=2,label='QCD MC truth in A'); ax.stairs(c['pred'],EDGES,color='C3',lw=2,label='ABCD prediction from MC B, C, D')
ax.set_yscale('log'); ax.set_ylabel('Weighted events / bin'); ax.legend(); label(ax,data=False)
r=c['obs']/c['pred']; er=np.sqrt(c['eobs']**2)/c['pred']
tot=np.sqrt(eb**2+sb**2)
rx.stairs(1+tot,EDGES,baseline=1-tot,fill=True,color='gold',alpha=.5,label='stat $\\oplus$ frozen syst (1.6% corr. + shape)')
rx.stairs(1+eb,EDGES,baseline=1-eb,fill=True,color='C2',alpha=.6,label='prediction stat')
rx.errorbar(MC_,r,er,xerr=np.diff(EDGES)/2,fmt='ko'); rx.axhline(1,c='gray',ls=':'); rx.set_ylim(.7,1.3); rx.set_ylabel('MC A / pred'); rx.set_xlabel('$m_{avg}$ [GeV]'); rx.legend(fontsize=12,ncol=2)
save(fig,'closure_mc_perbin')
# 2 variations
V=[('nominal',{}, 'poly')]
for xc in (0.15,0.25): V.append((f'masym boundary {xc}',dict(xp=(0,xc),xf=(xc,xc+.2)),'poly'))
for yc in (1.0,1.4): V.append((f'|$\\Delta\\eta$| boundary {yc}',dict(yp=(0,yc),yf=(yc,INF)),'poly'))
for hi,nm in ((.3,'0.2-0.3'),(.6,'0.2-0.6'),(INF,'all >0.2')): V.append((f'fail band {nm}',dict(xf=(.2,hi)),'poly'))
for ht in (1200,1400): V.append((f'HT > {ht}',dict(mask=q.HT.values>ht),'poly'))
V.append(('TF inclusive (constant)',{},'incl')); V.append(('TF per bin',{},'perbin'))
rows=[]
for nm,kw,mode in V:
    a=dict(NOM); a.update({k:v for k,v in kw.items()})
    pp,cc=mc_test(q,**a,mode=mode); rows.append((nm,cc,pp)); print(nm,'ratio %.4f +- %.4f chi2/ndf %.0f/%d'%(cc['ratio'],cc['err_ratio'],cc['chi2'],cc['ndf']))
fig,ax=plt.subplots(figsize=(14,9)); fig.subplots_adjust(left=0.3); yy=np.arange(len(rows))[::-1]
ax.errorbar([r[1]['ratio'] for r in rows],yy,xerr=[r[1]['err_ratio'] for r in rows],fmt='ko')
ax.axvline(1,c='gray',ls=':'); ax.axvspan(1-SYST_CORR,1+SYST_CORR,color='gold',alpha=.4,label=f'frozen corr. syst $\\pm${SYST_CORR*100:.1f}%')
ax.set_yticks(yy); ax.set_yticklabels([r[0] for r in rows],fontsize=13)
ax.set_xlabel('QCD MC closure: A$_{MC}$ / predicted (inclusive in $m_{avg}$)'); ax.legend(loc='lower right')
for y_,r in zip(yy,rows): ax.text(1.0+0.0,y_+0.25,f"  $\\chi^2$/ndf {r[1]['chi2']:.0f}/{r[1]['ndf']}",fontsize=10,color='C0')
label(ax,data=False); save(fig,'closure_mc_variations')
import pickle; pickle.dump({n:(c_['ratio'],c_['err_ratio'],c_['pulls'],c_['obs'],c_['pred'],c_['eobs'],np.diag(p_['cov'])) for n,c_,p_ in rows},open('fits/variations_mc.pkl','wb'))
# 3 data validation per bin
fig,axs=plt.subplots(2,3,figsize=(30,10),gridspec_kw=dict(height_ratios=[3,1.3]),sharex='col')
for j,(k,kw) in enumerate(VR.items()):
    p,c=data_test(dat,O,**kw); sb,eb=band(c,p); ax,rx=axs[0,j],axs[1,j]
    ax.stairs(c['obs'],EDGES,color='k',lw=2,label="data A$'$ (non-QCD subtracted)"); ax.stairs(c['pred'],EDGES,color='C3',lw=2,label='ABCD prediction')
    ax.set_yscale('log'); ax.set_ylabel('Events / bin'); ax.legend(fontsize=13)
    ax.set_title(f"{k}: obs/pred {c['ratio']:.3f}, pull {c['pull']:.1f}, per-bin $\\chi^2$/ndf {c['chi2']:.0f}/{c['ndf']}",fontsize=15); label(ax)
    tot=np.sqrt(eb**2+sb**2)
    rx.stairs(1+tot,EDGES,baseline=1-tot,fill=True,color='gold',alpha=.5,label='stat $\\oplus$ frozen syst'); rx.stairs(1+eb,EDGES,baseline=1-eb,fill=True,color='C2',alpha=.6,label='pred. stat')
    rx.errorbar(MC_,c['obs']/c['pred'],c['eobs']/c['pred'],xerr=np.diff(EDGES)/2,fmt='ko'); rx.axhline(1,c='gray',ls=':'); rx.set_ylim(.7,1.3); rx.set_xlabel('$m_{avg}$ [GeV]'); rx.set_ylabel('obs / pred')
    if j==0: rx.legend(fontsize=12)
save(fig,'validation_regions_data_perbin')
