import sys; sys.path.insert(0,'scripts'); from core import *
from matplotlib.patches import Rectangle
q,dat,O=load_all()
XL=[0,.1,.2,.3,.4,.5]; YC=[.6,.8,1.0,1.2,1.5,1.8,2.1]
def kp(H,S=None):
    s={};v={}
    for r in 'ABCD':
        a,a2=H[r]; a,a2=a.sum(),a2.sum()
        if S is not None: a=a-S[r][0].sum(); a2=a2+S[r][1].sum()
        s[r]=a; v[r]=a2
    k=s['A']*s['D']/(s['B']*s['C']); e=k*np.sqrt(sum(v[r]/s[r]**2 for r in 'ABCD')); return k,(k-1)/e
def grid(d,data):
    K=np.full((len(XL),len(YC)),np.nan); P=K.copy()
    for i,x in enumerate(XL):
        if data and x<0.2-1e-9: continue   # test-A would overlap the blinded SR A
        for j,y in enumerate(YC):
            xp,xf,yp,yf=(x,x+.2),(x+.2,x+.4),(0,y),(y,INF)
            H=hists(d,xp,xf,yp,yf); S=oth_sub(O,xp,xf,yp,yf) if data else None
            K[i,j],P[i,j]=kp(H,S)
    return K,P
def draw(K,P,name,title,data):
    fig,ax=plt.subplots(figsize=(13,10)); lim=0.12
    m=ax.imshow(K.T-1,origin='lower',cmap='RdBu_r',vmin=-lim,vmax=lim,aspect='auto')
    plt.colorbar(m,ax=ax,label='$\\kappa-1$, $\\kappa=N_AN_D/(N_BN_C)$')
    for i in range(len(XL)):
        for j in range(len(YC)):
            if np.isnan(K[i,j]): ax.text(i,j,'blind',ha='center',va='center',fontsize=11,color='gray'); ax.add_patch(Rectangle((i-.5,j-.5),1,1,fill=False,hatch='//',ec='lightgray'))
            else: ax.text(i,j,f'{K[i,j]-1:+.3f}\n({P[i,j]:+.1f}$\\sigma$)',ha='center',va='center',fontsize=11)
    ax.set_xticks(range(len(XL))); ax.set_xticklabels([f'[{x:.1f},{x+.2:.1f})\n fail [{x+.2:.1f},{x+.4:.1f})' for x in XL],fontsize=12)
    ax.set_yticks(range(len(YC))); ax.set_yticklabels([f'{y}' for y in YC])
    ax.set_xlabel('masym: pass band (and fail band)'); ax.set_ylabel('$|\\Delta\\eta|$ boundary (pass $<$ y)')
    ax.add_patch(Rectangle((0-.5,YC.index(1.2)-.5),1,1,fill=False,ec='k',lw=4)); ax.set_title(title+' ; box = chosen point',fontsize=14,pad=45)
    label(ax,data=data); save(fig,name)
Km,Pm=grid(q,False); draw(Km,Pm,'closure_map_mc','QCD MC, inclusive $m_{avg}$ 40-480',False)
Kd,Pd=grid(dat,True); draw(Kd,Pd,'closure_map_data','Data (non-QCD subtracted); blind where test-A overlaps SR A',True)
np.savez('fits/closure_maps.npz',Km=Km,Pm=Pm,Kd=Kd,Pd=Pd,XL=XL,YC=YC)
print('MC kappa-1 range %.3f..%.3f; chosen %.4f'%(np.nanmin(Km-1),np.nanmax(Km-1),Km[0,YC.index(1.2)]-1)); print('data',np.round(Kd-1,3)[2:])
