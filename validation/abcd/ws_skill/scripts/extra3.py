import sys; sys.path.insert(0,'scripts'); from core import *
def jets(g,only=None):
    cols=['w','sample']+[f'j{i}_{v}' for i in (0,1) for v in ('tau1','tau2','tau3','n2b1','msoftdrop','bosonId','bosonDR')]
    d=pd.read_parquet(f'sel/{g}.parquet',columns=cols)
    if only: d=d[d['sample']==only]
    out=[]
    for i in (0,1):
        o=pd.DataFrame({'w':d.w.values,'msd':d[f'j{i}_msoftdrop'].values,'bid':d[f'j{i}_bosonId'].values,'dr':d[f'j{i}_bosonDR'].values,
          't21':d[f'j{i}_tau2'].values/np.clip(d[f'j{i}_tau1'].values,1e-6,None),'t32':d[f'j{i}_tau3'].values/np.clip(d[f'j{i}_tau2'].values,1e-6,None),'n2':d[f'j{i}_n2b1'].values})
        out.append(o)
    return pd.concat(out,ignore_index=True)
Q=jets('qcd'); VJ=pd.concat([jets('vjets'),jets('vv')]); T=jets('top','tt_had')
V=VJ[(VJ.dr<.8)&(VJ.bid.abs().isin([23,24]))]; Tj=T[(T.dr<.8)&(T.bid.abs()==6)]
wins={'V-like jets: 60<m$_{SD}$<110 GeV':((60,110),V,'W/Z-matched jets (V+jets, VV MC)'),'top-like jets: 140<m$_{SD}$<220 GeV':((140,220),Tj,'top-matched jets (t$\\bar t$ MC)')}
vars_={'t21':('$\\tau_{2}/\\tau_{1}$',(0,1.01,40)),'t32':('$\\tau_{3}/\\tau_{2}$',(0,1.01,40)),'n2':('$N_2^{\\beta=1}$',(0,.5,40))}
fig,axs=plt.subplots(2,3,figsize=(27,16)); roc={}
for r,(wn,((lo,hi),S,sl)) in enumerate(wins.items()):
    q=Q[(Q.msd>=lo)&(Q.msd<hi)]; s=S[(S.msd>=lo)&(S.msd<hi)]
    for c,(v,(xl,(a,b,n))) in enumerate(vars_.items()):
        ax=axs[r,c]; e=np.linspace(a,b,n+1)
        for d,l,col in ((q,'QCD jets','C0'),(s,sl,'C3')):
            h=np.histogram(np.clip(d[v],a,b-1e-6),e,weights=d.w)[0]; ax.stairs(h/h.sum(),e,label=l,color=col,lw=2)
        ax.set_xlabel(xl+' (pooled leading+subleading jet)'); ax.set_ylabel('Fraction of jets'); ax.set_title(wn,fontsize=15,pad=45)
        if c==0: ax.legend(fontsize=12)
        label(ax,data=False)
        # ROC: cut v<x
        xs=np.linspace(a,b,400); es=[(s.w[s[v]<x].sum()/s.w.sum()) for x in xs]; eq=[(q.w[q[v]<x].sum()/q.w.sum()) for x in xs]
        roc[(r,v)]=(np.array(es),np.array(eq))
save(fig,'substructure_dists')
fig,axs=plt.subplots(1,2,figsize=(20,9)); txt={}
for r,(wn,_) in enumerate(wins.items()):
    ax=axs[r]
    for v,(xl,_) in vars_.items():
        es,eq=roc[(r,v)]; ax.plot(es,eq,label=xl,lw=2)
        i=np.argmin(abs(es-0.6)); txt[f'{wn}|{v}']=float(eq[i])
    ax.plot([0,1],[0,1],'k:'); ax.set_xlabel('proxy jet efficiency (cut: variable < x)'); ax.set_ylabel('QCD jet efficiency (mistag)'); ax.set_yscale('log'); ax.set_ylim(1e-3,1.05); ax.set_title(wn,fontsize=15,pad=45); ax.legend(); label(ax,data=False)
save(fig,'substructure_roc'); print(txt)
json.dump(txt,open('fits/substructure_roc_numbers.json','w'),indent=1)
