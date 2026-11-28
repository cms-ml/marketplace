import numpy as np, pandas as pd, itertools, json
cols=['mavg','deta','masym','ptasym','t21avg','t21max','n2avg','n2max','HT','ptavg','w','j0_msoftdrop','j1_msoftdrop']
q=pd.read_parquet('sel/qcd.parquet',columns=cols)
q=q[(q.mavg>40)&(q.mavg<450)&(q.j0_msoftdrop>0)&(q.j1_msoftdrop>0)]
print(len(q))
edges=np.array([40,60,80,100,130,170,220,300,450.])
V=['deta','masym','ptasym','t21avg','n2avg','ptavg']
res=[]
for x,y in itertools.combinations(V,2):
    for fx in (.3,.5,.7):
      for fy in (.3,.5,.7):
        cx=q[x].quantile(fx) if False else np.quantile(q[x],fx); cy=np.quantile(q[y],fy)
        px=q[x]<=cx; py=q[y]<=cy   # pass = low value
        kap=[];err=[]
        N={}
        for nm,m in (('A',px&py),('B',~px&py),('C',px&~py),('D',~px&~py)):
            N[nm]=np.histogram(q.mavg[m],edges,weights=q.w[m])[0]
        # inclusive kappa and per-bin
        k=N['A']*N['D']/(N['B']*N['C'])
        # error via effective stats
        vs={}
        for nm,m in (('A',px&py),('B',~px&py),('C',px&~py),('D',~px&~py)):
            vs[nm]=np.histogram(q.mavg[m],edges,weights=q.w[m]**2)[0]
        e=k*np.sqrt(sum(vs[n]/N[n]**2 for n in 'ABCD'))
        ki=sum(N['A'])*sum(N['D'])/(sum(N['B'])*sum(N['C']))
        chi=np.sum(((k-ki)/e)**2)
        res.append((x,y,fx,fy,ki,chi,k.min(),k.max(),sum(N['A'])/sum(N.values()[0] if False else [sum(v) for v in N.values()])))
r=pd.DataFrame(res,columns=['x','y','fx','fy','kappa_incl','chi2_vs_m(7dof)','kmin','kmax','fracA'])
r['dev']=abs(r.kappa_incl-1)
r.to_csv('fits/rank_pairs.csv',index=False)
b=r.sort_values('chi2_vs_m(7dof)').groupby(['x','y']).head(1)
print(b.round(3).to_string())
