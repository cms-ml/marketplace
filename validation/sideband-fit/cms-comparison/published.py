"""Compare the archived estimator against published CMS tables and independent fits.

Run with the archived student directory, extracted EXO-16 YAML directory and
Open Data templates.json as the three positional arguments, in this directory.
"""
import hashlib
import json
import sys
from decimal import Decimal, ROUND_CEILING, ROUND_FLOOR
from pathlib import Path
import numpy as np
import yaml
import hist
import mplhep as hep
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.integrate import quad
from scipy.optimize import minimize
from scipy.optimize._numdiff import approx_derivative
from scipy.stats import chi2
from scipy.special import xlogy

snapshot, tables, odfile = map(Path, sys.argv[1:4])
sys.path.insert(0,str(snapshot/"plugins/background-est/skills/sideband-fit/scripts"))
from fit_sidebands import fit_histogram, json_text


def recover(low, high, density):
    def interval(raw):
        value=Decimal(raw)
        # Include trailing zero suppression by the exporter using the displayed precision.
        half=Decimal(1).scaleb(value.as_tuple().exponent)/2
        return value-half,value+half
    a,b=interval(low),interval(high)
    d=interval(density)
    lower=(b[0]-a[1])*d[0]
    upper=(b[1]-a[0])*d[1]
    return [int(lower.to_integral_value(rounding=ROUND_CEILING)),int(upper.to_integral_value(rounding=ROUND_FLOOR))]


def refit(edges, counts, mask, order):
    t=lambda x: 2*np.log(x/edges[0])/np.log(edges[-1]/edges[0])-1
    def means(p):
        return np.array([quad(lambda x: np.exp(p[0]+p[1]*t(x)+(p[2]*t(x)**2 if order==2 else 0)),a,b)[0]
                         for a,b in zip(edges,edges[1:])])
    def nll(p):
        mu=means(p)[~mask]
        return np.sum(mu-xlogy(counts[~mask],mu))
    opt=minimize(nll,np.zeros(order+1),method="Nelder-Mead",options=dict(maxiter=5000,xatol=1e-9,fatol=1e-11))
    assert opt.success
    mu=means(opt.x)
    j=approx_derivative(means,opt.x)
    cov=np.linalg.inv((j[~mask].T/mu[~mask])@j[~mask])
    return mu,j@cov@j.T


def run(edges, counts, mask, cms, prefix, lumi=36.3):
    intervals=[[edges[:-1][mask][0],edges[1:][mask][-1]]]
    blind=[None if m else int(n) for n,m in zip(counts,mask)]
    report=fit_histogram(edges,blind,intervals,"log_mass",[1,2])
    assert json_text(report)==json_text(fit_histogram(edges,[10**9 if m else n for m,n in zip(mask,blind)],intervals,"log_mass",[1,2]))
    fit=next(f for f in report["candidates"] if f["order"]==report["selected_order"])
    mu=fit["prediction"]; c=fit["prediction_covariance"]
    expected=mu[mask].sum();var=c[np.ix_(mask,mask)].sum()
    ref,rcov=refit(edges,counts,mask,fit["order"])
    independent_mu=ref[mask].sum(); independent_var=rcov[np.ix_(mask,mask)].sum()
    result=dict(interval=intervals[0],order=fit["order"],mean=expected,std=var**.5,observed=int(counts[mask].sum()),
                published_background=float(cms[mask].sum()),observed_interval=fit["window_observed_intervals"][0],
                expected_interval=fit["window_expected_intervals"][0], independent_mean=independent_mu,
                independent_variance=independent_var,variance=var,mask_invariant=True,sideband_deviance=fit["deviance"],
                ndf=fit["ndf"],standardized_difference=(counts[mask].sum()-expected)/np.sqrt(expected+var))
    plt.style.use(hep.style.CMS)
    fig,(ax,ratio)=plt.subplots(2,1,figsize=(10,8),sharex=True,gridspec_kw=dict(height_ratios=(3,1),hspace=.05))
    widths=np.diff(edges); centers=(edges[:-1]+edges[1:])/2
    h=hist.Hist.new.Variable(edges).Double();h.view()[:]=counts/widths
    e_down=counts-chi2.ppf(.158655,2*counts)/2
    e_up=chi2.ppf(.841345,2*counts+2)/2-counts
    hep.histplot(h,yerr=np.array([e_down,e_up])/widths,histtype="errorbar",color="black",label="Published data",ax=ax)
    ax.stairs(mu/widths,edges,color="red",label="Sideband fit")
    err=np.sqrt(np.diag(c))
    ax.stairs((mu+err)/widths,edges,baseline=(mu-err)/widths,fill=True,color="red",alpha=.25,label="Fit uncertainty")
    ax.stairs(cms/widths,edges,color="navy",ls=":",label="Published background")
    for a in (ax,ratio): a.axvspan(*intervals[0],color="gray",alpha=.15)
    ax.set_yscale("log");ax.set_ylabel("Events / GeV"); ax.legend(fontsize=14); ax.set_xlabel("")
    hep.cms.label("Published data",data=True,lumi=lumi,com=13,ax=ax)
    ratio.errorbar(centers,counts/mu,yerr=np.array([e_down,e_up])/mu,fmt="o",color="black",ms=4)
    ratio.axhline(1,color="red");ratio.set_ylabel("Data / fit");ratio.set_xlabel(r"$m_{\mu\mu}$ [GeV]")
    fig.subplots_adjust(left=.15,right=.96,bottom=.14,top=.9)
    for ext in ("png","pdf"): fig.savefig(prefix+"."+ext)
    plt.close(fig)
    return result


fine=yaml.load((tables/"dimuon_mass_distribution.yaml").read_text(),Loader=yaml.BaseLoader)
rows=[]
for a,v,b in zip(fine["independent_variables"][0]["values"],*[x["values"] for x in fine["dependent_variables"]]):
    lo,hi=a["low"],a["high"]
    if float(lo)>=400 and float(hi)<=1000:
        rows.append([float(lo),float(hi),recover(lo,hi,v["value"]),float(b["value"])*(float(hi)-float(lo))])
assert all(r[2][0]==r[2][1] for r in rows),rows
edges=np.array([r[0] for r in rows]+[rows[-1][1]]); centers=(edges[:-1]+edges[1:])/2
counts=np.array([r[2][0] for r in rows]); cms=np.array([r[3] for r in rows])
out=dict(rows=rows,tests={})
for i,(lo,hi) in enumerate([(550,650),(750,850)]):
    out["tests"][str(i+1)]=run(edges,counts,(centers>=lo)&(centers<hi),cms,"published_"+str(i+1))
od=json.loads(odfile.read_text());oe=np.array(od["edges"]);n=np.asarray(od["data_counts"])
# Bracket unknown event positions in bins that straddle the published boundaries.
def bounds(a,b):
    return [int(n[(oe[:-1]>=a)&(oe[1:]<=b)].sum()),int(n[(oe[1:]>a)&(oe[:-1]<b)].sum())]
mid=edges[6]
a,b=bounds(edges[0],mid),bounds(mid,edges[-1])
out["shape"]=dict(interval=[edges[0],mid,edges[-1]],open_lower=a,open_upper=b,
                   open_high_fraction_bounds=[b[0]/(b[0]+a[1]),b[1]/(b[1]+a[0])],
                   published_high_fraction=float(counts[6:].sum()/counts.sum()),luminosity_fb=od["luminosity_fb"])
out["student_sha"]="58243a33463cfffa0f7f618bb853ede1cf3f8396"
out["archive_sha256"]="07ec561c67344d4351d34749e47ccead6baae2a12a22e452757aaf82d4875819"
out["open_input_sha256"]=hashlib.sha256(odfile.read_bytes()).hexdigest()
# Audit the coarse paper table against fine-bin containment without splitting counts.
coarse=yaml.safe_load((tables/"data_and_estimated_background_yields_in_the_dimuon_channel.yaml").read_text())
idx=next(i for i,a in enumerate(coarse["independent_variables"][0]["values"]) if a==dict(low=600.,high=900.))
cobs=int(coarse["dependent_variables"][0]["values"][idx]["value"])
out["table3_crosscheck"]=dict(interval=[600,900],observed=cobs,lower=int(counts[(edges[:-1]>=600)&(edges[1:]<=900)].sum()),
    upper=int(counts[(edges[1:]>600)&(edges[:-1]<900)].sum()))
for key,row in out["tests"].items():
    low,high=row["interval"]
    component=[]
    for a,b in zip(fine["independent_variables"][0]["values"],fine["dependent_variables"][1]["values"]):
        if float(a["low"])>=low and float(a["high"])<=high:
            err=b["errors"][0]["asymerror"]
            component.append([float(err[z])*(float(a["high"])-float(a["low"])) for z in ("minus","plus")])
    row["cms_bin_errors_minus_plus"]=component
# Independently refit the student's original continuum windows on raw snapshot counts.
original=json.loads((snapshot/"validation/sideband-fit/summary.json").read_text())["continuum"]
wm=np.asarray(original["window_masks"],bool)
chosen=next(c for c in original["candidates"] if c["order"]==original["selected_order"])
om,oc=refit(oe,n,wm.any(axis=0),chosen["order"])
out["open_refit"]=dict(observed=(wm@n).tolist(),mean=(wm@om).tolist(),student=chosen["window_expected"],
    covariance=(wm@oc@wm.T).tolist(),student_covariance=chosen["window_covariance"])
Path("comparison.json").write_text(json_text(out))
