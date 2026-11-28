import pyarrow.parquet as pq, numpy as np
t=pq.read_table('tmp/g0.parquet',columns=['run','j0_pt','j1_pt','j0_msoftdrop','j1_msoftdrop','HLT_AK8PFJet400_TrimMass30','HLT_PFHT900','HLT_AK8PFHT800_TrimMass50','HLT_PFJet450','HLT_PFJet260','HLT_AK8PFJet360_TrimMass30','HLT_AK8DiPFJet300_200_TrimMass30','HLT_PFHT800','trig_present','j0_jetId','j0_eta','HT']).to_pandas()
for c in t.columns:
    if c.startswith('HLT') : print(c, t[c].mean())
print(t.run.min(),t.run.max(),t.trig_present.unique())
print(t[['j0_pt','j1_pt','HT']].describe().T.to_string())
print((t.j1_pt>0).mean())
