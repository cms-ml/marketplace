import numpy as np
q=np.load("fits/slim_qcd.npz")
edges=np.array([40,60,80,100,120,140,160,180,200,220,240,260,280,300,330,360,400,440.])
def run(pt1cut,asymcut,c,detacut=9):
    s=q["pt1"]>pt1cut
    m0=q["msoftdrop0"][s];m1=q["msoftdrop1"][s];w=q["w"][s];n0=q["n2b10"][s];n1=q["n2b11"][s]
    mavg=0.5*(m0+m1); asym=np.abs(m0-m1)/np.maximum(m0+m1,1e-3); de=np.abs(q["eta0"][s]-q["eta1"][s])
    ok=(asym<asymcut)&(de<detacut)&(mavg>40)&(mavg<440)
    rho=[];err=[];fa=0
    for lo,hi in zip(edges[:-1],edges[1:]):
        m=ok&(mavg>=lo)&(mavg<hi); N={};E={}
        for nm,(a,b) in {"A":(1,1),"B":(1,0),"C":(0,1),"D":(0,0)}.items():
            t=m&((n0<c)==a)&((n1<c)==b); N[nm]=w[t].sum(); E[nm]=np.sqrt((w[t]**2).sum())
        r=N["A"]*N["D"]/(N["B"]*N["C"]); rho.append(r); err.append(r*np.sqrt(sum((E[k]/N[k])**2 for k in N)))
    rho=np.array(rho);err=np.array(err)
    print(f"pt1>{pt1cut} asym<{asymcut} deta<{detacut} c={c}: rho=",np.round(rho,2),"chi2 to 1:",round(float((((rho-1)/err)**2).sum()),0),"mean|rho-1|",round(float(np.abs(rho-1).mean()),3))
for a in [9,0.3,0.2,0.1]: run(300,a,0.3)
run(250,0.2,0.3); run(300,0.2,0.25); run(300,0.2,0.35); run(300,0.2,0.3,1.3)
