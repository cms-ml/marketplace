import glob, numpy as np, collections
G={"data":["data_JetHT_2016G","data_JetHT_2016H"],"qcd":["qcd_HT%s"%s for s in ["300to500","500to700","700to1000","1000to1500","1500to2000","2000toInf"]],
   "wqq":["wqq_HT400to600","wqq_HT600to800","wqq_HT800toInf"],"zqq":["zqq_HT400to600","zqq_HT600to800","zqq_HT800toInf"],
   "tt":["tt_had","tt_semilep"],"vv":["ww","wz","zz"],"hbb":["hbb_ggf","hbb_vbf"]}
for g,ss in G.items():
    parts=[]
    for s in ss:
        for f in sorted(glob.glob(f"fits/base/{s}__*.npz")):
            z=np.load(f); d={}
            for i in (0,1):
                for v in ["pt","eta","phi","mass","msoftdrop","btagHbb","n2b1","n3b1"]: d[f"{v}{i}"]=z[f"j{i}_{v}"].astype(np.float32)
                d[f"tau21_{i}"]=(z[f"j{i}_tau2"]/np.maximum(z[f"j{i}_tau1"],1e-6)).astype(np.float32)
                d[f"tau32_{i}"]=(z[f"j{i}_tau3"]/np.maximum(z[f"j{i}_tau2"],1e-6)).astype(np.float32)
            for k in ["HT","MET_pt","j2_pt"]: d[k]=z[k].astype(np.float32)
            d["w"]=z["w"].astype(np.float64)
            if g=="data": d["run"]=z["run"]; d["sample"]=np.full(len(z["w"]),0 if s.endswith("G") else 1,np.int8)
            else:
                for i in (0,1): d[f"bosonDR{i}"]=z[f"j{i}_bosonDR"].astype(np.float32); d[f"bosonId{i}"]=z[f"j{i}_bosonId"].astype(np.int16)
                d["sample"]=np.full(len(z["w"]),ss.index(s),np.int8)
            parts.append(d)
    out={k:np.concatenate([p[k] for p in parts]) for k in parts[0]}
    np.savez(f"fits/slim_{g}.npz",**out); print(g,len(out["w"]),flush=True)
