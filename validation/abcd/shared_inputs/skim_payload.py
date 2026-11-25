import argparse, re, numpy as np, awkward as ak, uproot
ap=argparse.ArgumentParser(); ap.add_argument("--inputs"); ap.add_argument("--output"); a=ap.parse_args()
NJ=3
TRIGS=[f"HLT_{x}" for x in ["PFJet200","PFJet260","PFJet320","PFJet400","PFJet450","PFJet500",
 "AK8PFJet200","AK8PFJet260","AK8PFJet320","AK8PFJet360_TrimMass30","AK8PFJet400","AK8PFJet400_TrimMass30","AK8PFJet450","AK8PFJet500",
 "PFHT650","PFHT800","PFHT900","AK8PFHT650_TrimR0p1PT0p03Mass50","AK8PFHT700_TrimR0p1PT0p03Mass50","AK8PFHT750_TrimMass50","AK8PFHT800_TrimMass50",
 "AK8DiPFJet280_200_TrimMass30","AK8DiPFJet300_200_TrimMass30","PFHT650_WideJetMJJ900DEtaJJ1p5","PFHT300_PFMET110","DiPFJetAve260","DiPFJetAve400"]]
JV=["pt","eta","phi","mass","msoftdrop","btagHbb","tau1","tau2","tau3","tau4","n2b1","n3b1","jetId"]
JMC=["hadronFlavour","nBHadrons","nCHadrons"]
FLAGS=["goodVertices","globalSuperTightHalo2016Filter","HBHENoiseFilter","HBHENoiseIsoFilter","EcalDeadCellTriggerPrimitiveFilter","BadPFMuonFilter","eeBadScFilter"]
out=[]
for url in a.inputs.split(","):
    f=uproot.open(url)["Events"]; keys=set(f.keys()); mc="genWeight" in keys
    br=["run","luminosityBlock","event","MET_pt","PuppiMET_pt","fixedGridRhoFastjetAll","nFatJet"]
    br+=["FatJet_"+v for v in JV]+["Jet_pt","Jet_eta","Jet_jetId","Muon_pt","Muon_looseId","Electron_pt","Electron_cutBased","Muon_eta","Electron_eta"]
    br+=["Flag_"+x for x in FLAGS]+[t for t in TRIGS if t in keys]
    if mc: br+=["genWeight","Pileup_nTrueInt","FatJet_eta","FatJet_phi"]+["FatJet_"+v for v in JMC]+["GenPart_pdgId","GenPart_statusFlags","GenPart_pt","GenPart_eta","GenPart_phi","GenPart_mass"]
    for ch in f.iterate(br,step_size=100000,library="ak"):
        sel=ak.num(ch.FatJet_pt)>0
        sel=sel&(ak.fill_none(ak.firsts(ch.FatJet_pt),0)>250)
        ch=ch[sel]
        if len(ch)==0: continue
        d={}
        for k in ["run","luminosityBlock","event","MET_pt","PuppiMET_pt","fixedGridRhoFastjetAll"]: d[k]=ak.to_numpy(ch[k])
        d["nFatJet"]=ak.to_numpy(ch.nFatJet)
        okf=np.ones(len(ch),bool)
        for x in FLAGS: okf&=ak.to_numpy(ch["Flag_"+x])
        d["filters"]=okf
        for t in TRIGS: d[t]=ak.to_numpy(ch[t]) if t in keys else np.zeros(len(ch),bool)
        d["trig_present"]=np.array([sum(t in keys for t in TRIGS)]*len(ch))
        # fatjets are pT ordered in NanoAOD
        jv=JV+(JMC if mc else [])
        for i in range(NJ):
            for v in jv:
                d[f"j{i}_{v}"]=ak.to_numpy(ak.fill_none(ak.pad_none(ch["FatJet_"+v],NJ,clip=True)[:,i],-999)).astype("float32")
        ak4=ch.Jet_pt[(ch.Jet_pt>30)&(abs(ch.Jet_eta)<2.5)]
        d["HT"]=ak.to_numpy(ak.sum(ak4,axis=1)).astype("float32")
        d["nMuLoose"]=ak.to_numpy(ak.sum((ch.Muon_pt>10)&(abs(ch.Muon_eta)<2.4)&ch.Muon_looseId,axis=1))
        d["nEleLoose"]=ak.to_numpy(ak.sum((ch.Electron_pt>10)&(abs(ch.Electron_eta)<2.5)&(ch.Electron_cutBased>=2),axis=1))
        if mc:
            d["genWeight"]=ak.to_numpy(ch.genWeight).astype("float64"); d["nTrueInt"]=ak.to_numpy(ch.Pileup_nTrueInt)
            isB=((abs(ch.GenPart_pdgId)==23)|(abs(ch.GenPart_pdgId)==24)|(abs(ch.GenPart_pdgId)==25)|(abs(ch.GenPart_pdgId)==6))&(((ch.GenPart_statusFlags>>13)&1)==1)
            bp=ch.GenPart_pt[isB]; be=ch.GenPart_eta[isB]; bph=ch.GenPart_phi[isB]; bid=abs(ch.GenPart_pdgId[isB])
            for i in range(NJ):
                je=ak.fill_none(ak.pad_none(ch.FatJet_eta,NJ,clip=True)[:,i],0); jp=ak.fill_none(ak.pad_none(ch.FatJet_phi,NJ,clip=True)[:,i],0)
                dphi=(bph-jp+np.pi)%(2*np.pi)-np.pi
                dr=np.sqrt((be-je)**2+dphi**2)
                dr=ak.fill_none(ak.pad_none(dr,1),99.)
                idx=ak.argmin(dr,axis=1,keepdims=True)
                d[f"j{i}_bosonDR"]=ak.to_numpy(ak.fill_none(ak.firsts(dr[idx]),99.)).astype("float32")
                bidp=ak.pad_none(bid,1)
                d[f"j{i}_bosonId"]=ak.to_numpy(ak.fill_none(ak.firsts(bidp[idx]),0)).astype("int32")
        out.append(ak.Array(d))
res=ak.concatenate(out) if out else ak.Array({"run":[]})
import pyarrow.parquet as pq
pq.write_table(ak.to_arrow_table(res),a.output,compression="snappy")
print("rows",len(res))
