import numpy as np, pandas as pd, sys
sys.path.insert(0,'/uscms_data/d3/ashrivas/AGENTS-AI/cms/marketplace/plugins/background-est/skills/abcd/scripts')
MASYM_CUT=0.2; DETA_CUT=1.2
MLO,MHI=40.,480.
COLS=['mavg','masym','deta','t21avg','t21max','n2avg','ptavg','HT','MET','j0_msoftdrop','j1_msoftdrop','j0_pt','j1_pt','j0_bosonId','j1_bosonId','j0_bosonDR','j1_bosonDR','w']
def load(group, blind=True, cols=None):
    cols=list(dict.fromkeys(cols or COLS))
    cc=[c for c in cols if not (group=='data' and c in ('j0_bosonId','j1_bosonId','j0_bosonDR','j1_bosonDR'))]
    d=pd.read_parquet(f'sel/{group}.parquet',columns=cc)
    d=d[(d.mavg>=MLO)&(d.mavg<MHI)]
    if group=='data' and blind:
        d=d[~((d.masym<MASYM_CUT)&(d.deta<DETA_CUT))]
    return d.astype({c:'f4' for c in d.columns if d[c].dtype=='f8' and c!='w'})
def regions(d,xc=MASYM_CUT,yc=DETA_CUT):
    px=(d.masym<xc).values; py=(d.deta<yc).values
    return {'A':px&py,'B':~px&py,'C':px&~py,'D':~px&~py}
