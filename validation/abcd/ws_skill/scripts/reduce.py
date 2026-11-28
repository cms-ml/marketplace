import sys; sys.path.insert(0,'scripts')
from lib import *
import os; os.makedirs('red',exist_ok=True)
for g in ['data','qcd','vjets','top','vv','higgs']:
    d=load(g)
    if g=='data': d['w']=1.0
    d.to_parquet(f'red/{g}.parquet',compression='snappy'); print(g,len(d),d.w.sum())
