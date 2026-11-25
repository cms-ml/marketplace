"""Independent Poisson generators and coverage accounting, applying the archived estimators."""
import json
import sys
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from scipy.integrate import quad
from scipy.special import ndtr

snapshot = Path(sys.argv[1]).resolve()
sys.path[:0] = [str(snapshot / "plugins/background-est/skills/sideband-fit/scripts"), str(snapshot / "validation/sideband-fit")]
from fit_sidebands import Spectrum, fit_sideband, select_fit, window_prediction
from toys import signed_signal_fit


def summarize(pairs, truth, log_interval):
    arr = np.asarray(pairs)
    est, err = arr.T
    pull = (est-truth)/err
    covered = (abs(np.log(est/truth))*est <= err) if log_interval else (abs(est-truth) <= err)
    return dict(bias=float(np.mean(est-truth)), pull_mean=float(pull.mean()), pull_width=float(pull.std(ddof=1)),
                covered=int(covered.sum()), valid=len(arr), coverage=float(covered.sum()/300),
                mc_se=float(np.sqrt(covered.sum()/300*(1-covered.sum()/300)/300)),
                mean_estimate=float(est.mean()), negative=int(sum(est<0)))


def run(i):
    edges = np.linspace(0,1,41)
    spectrum = Spectrum(edges,"mass")
    mask = (edges[:-1]>=0.4)&(edges[1:]<=0.60000001)
    sb = ~mask
    truth = [lambda x:np.exp(-2*x),lambda x:np.exp(-2*x+1.3*x*x),
             lambda x:np.exp(-2*x)*(1+.25*np.exp(-.5*((x-.52)/.075)**2))][i//2]
    bg=np.array([quad(truth,a,b)[0] for a,b in zip(edges,edges[1:])]); bg*=2000/bg.sum()
    template=np.diff(ndtr((edges-.5)/.055)); template/=template.sum()
    inject=50*(i%2)
    rng=np.random.default_rng(657241+i)
    records={k:[[],[]] for k in ("fixed","selected")}
    bounds=0
    orders=[]
    sig_bounds=0
    for obs in rng.poisson(bg+inject*template,size=(300,40)):
        fits=[fit_sideband(spectrum,sb,obs[sb],j) for j in (1,2)]
        bounds+=sum(f["boundary"] for f in fits)
        selected=select_fit(fits)
        orders.append(selected["order"] if selected else 0)
        cache={}
        for k,f in zip(records,(fits[0],selected)):
            if f is None or not f["valid"]: continue
            m,c=window_prediction(f,mask[None,:])
            records[k][0].append([m[0],c[0,0]**.5])
            if f["order"] not in cache:
                cache[f["order"]]=signed_signal_fit(spectrum,obs,sb,template,f)
                sig_bounds+=int(cache[f["order"]]["boundary"])
            sf=cache[f["order"]]
            if sf["valid"]: records[k][1].append([sf["yield"],sf["std"]])
    return dict(seed=657241+i, attempts=300,injected=inject,truth=["linear","quadratic","bump"][i//2],
                background=float(bg[mask].sum()),sideband_signal_fraction=float(template[sb].sum()),
                candidate_boundaries=int(bounds),signal_boundaries=sig_bounds,
                order_two=orders.count(2),methods={k:dict(background=summarize(b,bg[mask].sum(),True),
                signal=summarize(s,inject,False)) for k,(b,s) in records.items()})

if __name__=="__main__":
    with ProcessPoolExecutor(4) as pool:
        Path("ensembles.json").write_text(json.dumps(list(pool.map(run,range(6))),indent=2)+"\n")
