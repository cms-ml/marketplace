import numpy as np, json
q=np.load("fits/slim_qcd.npz")
pt1=q["pt1"]; sel=(pt1>300)
d={k:q[k][sel] for k in ["pt0","pt1","eta0","eta1","msoftdrop0","msoftdrop1","n2b10","n2b11","tau21_0","tau21_1","w"]}
mavg=0.5*(d["msoftdrop0"]+d["msoftdrop1"]); asym=np.abs(d["msoftdrop0"]-d["msoftdrop1"])/np.maximum(d["msoftdrop0"]+d["msoftdrop1"],1e-3)
deta=np.abs(d["eta0"]-d["eta1"]); w=d["w"]
edges=np.array([40,80,120,160,200,260,340,440.])
inr=(mavg>edges[0])&(mavg<edges[-1])
print("QCD yield in range",w[inr].sum(),"N",inr.sum(), "eff sumw^2/sumw2 :",w[inr].sum()**2/(w[inr]**2).sum())
def tf(x_pass,y_pass,label):
    r=[]
    for lo,hi in zip(edges[:-1],edges[1:]):
        m=inr&(mavg>=lo)&(mavg<hi)
        N={}
        for nm,(a,b) in {"A":(1,1),"B":(1,0),"C":(0,1),"D":(0,0)}.items():
            s=m&(x_pass==a)&(y_pass==b); N[nm]=(w[s].sum(),np.sqrt((w[s]**2).sum()),s.sum())
        rho=N["A"][0]*N["D"][0]/(N["B"][0]*N["C"][0]) if N["B"][0]*N["C"][0]>0 else np.nan
        rel=np.sqrt(sum((N[k][1]/max(N[k][0],1e-9))**2 for k in N))
        r.append((lo,round(rho,3),round(rho*rel,3),round(N["A"][0],1),round(N["D"][0]/max(N["B"][0],1e-9),1)))
    print(label); print("  ",[(x[0],x[1],x[2]) for x in r]); print("   A yields",[x[3] for x in r])
n20=d["n2b10"];n21=d["n2b11"]
for c in [0.25,0.30,0.35]:
    tf(n20<c,n21<c,f"O1 jet0 N2<{c} x jet1 N2<{c}")
    tf(np.maximum(n20,n21)<c,deta<1.3,f"O2 max N2<{c} x deta<1.3")
    tf(np.maximum(n20,n21)<c,asym<0.1,f"O3 max N2<{c} x asym<0.1")
tf(np.maximum(d["tau21_0"],d["tau21_1"])<0.5,deta<1.3,"O2' max tau21<0.5 x deta")
