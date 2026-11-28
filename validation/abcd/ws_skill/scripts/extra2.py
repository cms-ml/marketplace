import sys; sys.path.insert(0,'scripts'); from core import *
from matplotlib.colors import LogNorm
q,dat,O=load_all()
# 4: 2D
xe=np.linspace(0,1,41); ye=np.linspace(0,2.6,27)
fig,axs=plt.subplots(1,2,figsize=(22,9))
for ax,d,t,dd in ((axs[0],q,'QCD MC (weighted)',False),(axs[1],dat,'Data (SR A removed: blinded)',True)):
    h=np.histogram2d(d.masym,d.deta,[xe,ye],weights=d.w)[0]; h=np.where(h>0,h,np.nan)
    m=ax.pcolormesh(xe,ye,h.T,norm=LogNorm(),cmap='viridis'); plt.colorbar(m,ax=ax,label='Events')
    for x in (.2,.4): ax.axvline(x,c='w',ls='--',lw=2)
    ax.axhline(1.2,c='w',ls='--',lw=2)
    for (x,y,s) in ((.1,.5,'A'),(.3,.5,'B'),(.1,2.0,'C'),(.3,2.0,'D')): ax.text(x,y,s,color='w',fontsize=30,ha='center')
    ax.set_xlabel('mass asymmetry $|m_1-m_2|/(m_1+m_2)$'); ax.set_ylabel('$|\\Delta\\eta_{jj}|$'); ax.set_title(t,fontsize=18); label(ax,data=dd)
save(fig,'design_2d_masym_deta')
# 5: boundary scan with proxy eff
cols=['masym','deta','w','j0_bosonDR','j1_bosonDR','j0_bosonId','j1_bosonId','sample','mavg']
t=pd.read_parquet('sel/top.parquet',columns=cols); t=t[(t['sample']=='tt_had')&(t.j0_bosonDR<.8)&(t.j1_bosonDR<.8)&(abs(t.j0_bosonId)==6)&(abs(t.j1_bosonId)==6)]
vv=pd.read_parquet('sel/vv.parquet',columns=cols); vv=vv[(vv.j0_bosonDR<.8)&(vv.j1_bosonDR<.8)]
t=t[(t.mavg>=40)&(t.mavg<480)]; vv=vv[(vv.mavg>=40)&(vv.mavg<480)]
def kap(d,xp,xf,yp,yf):
    H=hists(d,xp,xf,yp,yf); s={r:H[r][0].sum() for r in 'ABCD'}; v={r:H[r][1].sum() for r in 'ABCD'}
    k=s['A']*s['D']/(s['B']*s['C']); return k,k*np.sqrt(sum(v[r]/s[r]**2 for r in 'ABCD'))
def eff(d,mx=None,my=None):
    m=np.ones(len(d),bool)
    if mx is not None: m&=d.masym.values<mx
    if my is not None: m&=d.deta.values<my
    return d.w.values[m].sum()/d.w.sum()
fig,axs=plt.subplots(2,3,figsize=(27,14),sharex='col',gridspec_kw=dict(height_ratios=[1,1],hspace=0.05))
xs=np.array([.05,.1,.15,.2,.25,.3,.4,.5]); ys=np.array([.6,.8,1.0,1.2,1.4,1.6,1.8,2.2]); hs=np.array([.3,.4,.5,.6,.8,1.01])
def panel(j,vals,kf,ef,xl,chosen):
    ax=axs[0,j]; bx=axs[1,j]
    k=[kf(v) for v in vals]; ax.errorbar(vals,[a for a,b in k],[b for a,b in k],fmt='ko-')
    ax.axhline(1,c='gray',ls=':'); ax.set_ylabel('$\\kappa=AD/(BC)$ (QCD MC)'); ax.axvline(chosen,c='r',ls='--',label='chosen'); ax.legend(fontsize=13,loc='upper left')
    for d,l,c in ((vv,'VV-matched jets','C2'),(t,'t$\\bar t$ both jets top-matched','C1'),(q,'QCD','C0')):
        bx.plot(vals,[ef(d,v) for v in vals],'s--',color=c,label=l)
    bx.axvline(chosen,c='r',ls='--'); bx.set_ylabel('efficiency of the pass cut'); bx.set_xlabel(xl)
    if j==0: bx.legend(fontsize=13)
    label(ax,data=False)
panel(0,xs,lambda x:kap(q,(0,x),(x,x+.2),NOM['yp'],NOM['yf']),lambda d,x:eff(d,mx=x),'masym pass boundary (fail band = next 0.2)',0.2)
panel(1,ys,lambda y:kap(q,NOM['xp'],NOM['xf'],(0,y),(y,INF)),lambda d,y:eff(d,my=y),'$|\\Delta\\eta|$ pass boundary',1.2)
panel(2,hs,lambda h:kap(q,NOM['xp'],(.2,h),NOM['yp'],NOM['yf']),lambda d,h:eff(d,mx=.2),'upper edge of masym fail band (eff.: masym<0.2 fixed)',0.4)
save(fig,'design_boundary_scan')
# 6: masym pass/fail ratio vs deta
de=np.array([0,.3,.6,.9,1.2,1.5,1.8,2.1,2.6])
fig,ax=plt.subplots(figsize=(11,9))
for d,l,c,sub in ((q,'QCD MC','C0',None),(dat,'Data (bins containing A are blinded)','k',O)):
    xs_=[];r=[];er=[]
    for lo,hi in zip(de[:-1],de[1:]):
        if d is dat and lo<1.2: continue
        yr=(lo,hi); H=hists(d,(0,.2),(.2,.4),yr,yr); a=H['A'];b=H['B']
        if d is dat:
            S=oth_sub(O,(0,.2),(.2,.4),yr,yr); a=(a[0]-S['A'][0],a[1]+S['A'][1]); b=(b[0]-S['B'][0],b[1]+S['B'][1])
        A_,B_=a[0].sum(),b[0].sum(); rr=A_/B_; xs_.append(0.5*(lo+hi)); r.append(rr); er.append(rr*np.sqrt(a[1].sum()/A_**2+b[1].sum()/B_**2))
    ax.errorbar(xs_,r,er,fmt='o',color=c,label=l)
ax.axvline(1.2,c='gray',ls='--'); ax.set_xlabel('$|\\Delta\\eta_{jj}|$'); ax.set_ylabel('N(masym<0.2) / N(0.2<masym<0.4)'); ax.legend(); label(ax)
save(fig,'independence_ratio_vs_deta')
