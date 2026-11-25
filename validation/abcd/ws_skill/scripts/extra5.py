import sys, pickle; sys.path.insert(0,'scripts'); from core import *
from matplotlib.patches import Rectangle
q,dat,O=load_all()
rows=[]; shape_terms=[]; names7=[]
p,c=mc_test(q,**NOM); rows.append(('MC closure (A)',c['obs']/c['pred']-1,c['pulls'])); names7.append(0)
excess={}
def exc(c,p,isdata):
    dev=c['obs']/c['pred']/c['ratio']-1; eo=np.sqrt(np.diag(p['cov']))/c['pred']
    tot=np.hypot(eo,np.sqrt(1/np.maximum(c['obs'],1)) if isdata else 0.0); return np.sqrt(np.maximum(0,dev**2-tot**2))
excess['MC closure (A)']=exc(c,p,False)
for k,kw in VR.items():
    p,c=mc_test(q,**kw); rows.append((f'MC {k}',c['obs']/c['pred']-1,c['pulls'])); excess[f'MC {k}']=exc(c,p,False)
for k,kw in VR.items():
    p,c=data_test(dat,O,**kw); rows.append((f'DATA {k}',c['obs']/c['pred']-1,c['pulls'])); excess[f'DATA {k}']=exc(c,p,True)
S=np.max(list(excess.values()),axis=0); print('shape recomputed vs frozen max abs diff',np.abs(S-SHAPE).max())
assert np.abs(S-SHAPE).max()<1e-6
var=pickle.load(open('fits/variations_mc.pkl','rb'))
for n,(ra,er,pulls,obs,pred,eobs,dg) in var.items():
    if n=='nominal': continue
    rows.append(('MC var: '+n,obs/pred-1,pulls))
names=[r[0] for r in rows]; M=np.array([r[1] for r in rows]); P=np.array([r[2] for r in rows])
drv=np.argmax(np.array([excess[n] for n in excess]),axis=0); exn=list(excess)
fig,ax=plt.subplots(figsize=(17,14)); lim=0.2
im=ax.imshow(M,aspect='auto',cmap='RdBu_r',vmin=-lim,vmax=lim); plt.colorbar(im,ax=ax,label='obs/pred $-$ 1')
for i in range(M.shape[0]):
    for j in range(M.shape[1]): ax.text(j,i,f'{P[i,j]:+.1f}',ha='center',va='center',fontsize=9)
for j in range(M.shape[1]):
    i=names.index(exn[drv[j]]); ax.add_patch(Rectangle((j-.5,i-.5),1,1,fill=False,ec='k',lw=3))
ax.set_yticks(range(len(names))); ax.set_yticklabels(names,fontsize=12); ax.set_xticks(range(len(MC_)))
ax.set_xticklabels([f'{int(a)}-{int(b)}' for a,b in zip(EDGES[:-1],EDGES[1:])],rotation=45,fontsize=11); ax.set_xlabel('$m_{avg}$ bin [GeV]')
ax.axhline(6.5,c='k',lw=1); ax.axhline(0.5,c='k',lw=1)
ax.set_title('text = pull; black box = frozen test giving the per-bin shape term (7 tests above the lines only)\nfrozen shape term per bin (%): '+' '.join(f'{100*s:.0f}' for s in SHAPE),fontsize=13,pad=45); fig.subplots_adjust(left=0.22)
label(ax); save(fig,'nonclosure_map')
print('driving tests per bin:',[exn[d] for d in drv])
json.dump({'driver_per_bin':[exn[d] for d in drv],'shape_term':SHAPE.tolist()},open('fits/shape_drivers.json','w'),indent=1)
