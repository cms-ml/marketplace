import numpy as np
EDGES=np.array([40,60,80,100,120,140,160,180,200,220,240,260,280,300,330,360,400,440.])
CUT=0.30; PT1MIN=300.; ASYM_SR=0.2
NB=len(EDGES)-1
def load(g):
    z=np.load(f"fits/slim_{g}.npz"); return {k:z[k] for k in ["pt0","pt1","eta0","eta1","msoftdrop0","msoftdrop1","n2b10","n2b11","w"]}
def derived(z):
    z["mavg"]=0.5*(z["msoftdrop0"]+z["msoftdrop1"])
    z["asym"]=np.abs(z["msoftdrop0"]-z["msoftdrop1"])/np.maximum(z["msoftdrop0"]+z["msoftdrop1"],1e-3)
    return z
def hist(x,w):
    h=np.histogram(x,EDGES,weights=w)[0]; v=np.histogram(x,EDGES,weights=w**2)[0]; return h,v
def four(z,sel,p0,p1,blind=False):
    """returns dict region -> (sumw, sumw2) per m_avg bin. p0,p1: pass flags of jet0, jet1. A=both pass. blind: A not histogrammed for data."""
    out={}
    for nm,m in {"A":p0&p1,"B":p0&~p1,"C":~p0&p1,"D":~p0&~p1}.items():
        if nm=="A" and blind: out[nm]=(np.full(NB,np.nan),np.full(NB,np.nan)); continue
        s=sel&m; out[nm]=hist(z["mavg"][s],z["w"][s])
    return out
def predict(B,C,D):
    """B,C,D: (val,var). Prediction A=B*C/D, TF=C/D. returns value, stat err, tf, tf err"""
    b,vb=B;c,vc=C;d,vd=D
    tf=c/d; pred=b*tf
    rel=np.sqrt(vb/b**2+vc/c**2+vd/d**2)
    return pred,pred*rel,tf,tf*np.sqrt(vc/c**2+vd/d**2)
def sub(R,O,f=1.0):
    return {k:(R[k][0]-f*O[k][0],R[k][1]+f*f*O[k][1]) for k in R}
