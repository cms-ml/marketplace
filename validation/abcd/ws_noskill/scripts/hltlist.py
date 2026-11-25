import sys, fsspec, pyarrow.parquet as pq, numpy as np
for era in ["G","H"]:
    u=open(f"inputs/skim_files/data_JetHT_2016{era}.txt").readline().strip()
    with fsspec.open(u,"rb") as f:
        pf=pq.ParquetFile(f)
        print(era,u.split('/')[-1],pf.metadata.num_rows,pf.metadata.num_row_groups)
        hl=[c for c in pf.schema_arrow.names if c.startswith("HLT_")]
        t=pf.read_row_group(0,columns=hl+["trig_present"]).to_pandas()
        print(era,"rows rg0",len(t),"trig_present",t.trig_present.iloc[0])
        for c in hl: print(f"{t[c].mean():.4f} {c}")
