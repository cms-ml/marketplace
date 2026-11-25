# Full fit with rhalphalib and Combine

Loaded from SKILL.md when the TF is fitted together with signal and resonant
templates (signal strengths, limits). A TF-only study does not need this:
use `scripts/tf_fit.py`. Written against the rhalphalib 0.3.0 source.
`renderCombine` needs ROOT, so run it inside the Combine environment.

## Model (two-step TF, autoMCStats, masks)

```python
import numpy as np
import rhalphalib as rl
import ROOT

rl.util.install_roofit_helpers()
# ptbins, msdbins, RHO_LO, RHO_HI: your choices (references/selection.md)
msd = rl.Observable("msd", msdbins)
pt, m = np.meshgrid(ptmean, msdbins[:-1] + 0.5 * np.diff(msdbins), indexing="ij")
rho = 2 * np.log(m / pt)
ptscaled = (pt - ptbins[0]) / (ptbins[-1] - ptbins[0])      # real edges
rhoscaled = (rho - RHO_LO) / (RHO_HI - RHO_LO)
valid = (rhoscaled >= 0) & (rhoscaled <= 1)
rhoscaled[~valid] = 1                                       # keep the polynomial defined

# Step 1: QCD-MC pass/fail fit (RooFit only, no Combine)
qcdmodel = rl.Model("qcdmodel")
qcdpass = qcdfail = 0.0
for ipt in range(npt):
    for reg, h in (("fail", qcd_fail), ("pass", qcd_pass)):
        ch = rl.Channel(f"ptbin{ipt}{reg}")
        qcdmodel.addChannel(ch)
        ch.setObservation((h[ipt], msdbins, "msd"))
        ch.mask = valid[ipt]
    qcdfail += qcd_fail[ipt][valid[ipt]].sum()
    qcdpass += qcd_pass[ipt][valid[ipt]].sum()
qcdeff = qcdpass / qcdfail
tf_mc = rl.BasisPoly("tf_mc", (n_pt_mc, n_rho_mc), ["pt", "rho"], basis="Bernstein", limits=(0, 10))
tf_mc_params = qcdeff * tf_mc(ptscaled, rhoscaled)
for ipt in range(npt):
    fail, passed = qcdmodel[f"ptbin{ipt}fail"], qcdmodel[f"ptbin{ipt}pass"]
    obs = fail.getObservation()
    p = np.array([rl.IndependentParameter(f"qcdparam_mc_ptbin{ipt}_msdbin{i}", 0) for i in range(msd.nbins)])
    fq = rl.ParametericSample(f"ptbin{ipt}fail_qcd", rl.Sample.BACKGROUND, msd,
                              obs * (1 + 10.0 / np.maximum(1.0, np.sqrt(obs))) ** p)
    fail.addSample(fq)
    passed.addSample(rl.TransferFactorSample(f"ptbin{ipt}pass_qcd", rl.Sample.BACKGROUND,
                                             tf_mc_params[ipt, :], fq))
ws = ROOT.RooWorkspace("qcdfit_ws")
simpdf, obs = qcdmodel.renderRoofit(ws)
qcdfit = simpdf.fitTo(obs, ROOT.RooFit.Extended(True), ROOT.RooFit.SumW2Error(True),
                      ROOT.RooFit.Strategy(2), ROOT.RooFit.Save(),
                      ROOT.RooFit.Minimizer("Minuit2", "migrad"), ROOT.RooFit.PrintLevel(-1))
if qcdfit.status() != 0:
    # Weighted MC with ~100 free fail parameters often ends with status 3 /
    # covQual 2 here (seen on 2016 Open Data). Use the route below instead.
    raise RuntimeError("QCD MC fit failed")
# carry the MC shape AND its uncertainty: decorrelated constrained nuisances
names = [p.name for p in tf_mc.parameters.reshape(-1)]
deco = rl.DecorrelatedNuisanceVector.fromRooFitResult(tf_mc.name + "_deco", qcdfit, names)
tf_mc.parameters = deco.correlated_params.reshape(tf_mc.parameters.shape)
tf_mc_final = tf_mc(ptscaled, rhoscaled)

# Recommended alternative to the RooFit step 1: take R_MC from
# `scripts/tf_fit.py mc` (same Bernstein basis and parameter order [i_pt, j_rho];
# verified identical to machine precision). It is absolute R_MC, so no qcdeff:
#   mc = json.load(open("mc.json"))["fits"]["1,2"]
#   deco = rl.DecorrelatedNuisanceVector("tf_mc_deco", np.array(mc["coef"]), np.array(mc["cov"]))
#   tf_mc = rl.BasisPoly("tf_mc", (1, 2), ["pt", "rho"], basis="Bernstein")
#   tf_mc.parameters = deco.correlated_params.reshape(tf_mc.parameters.shape)
#   tf_mc_final = tf_mc(ptscaled, rhoscaled)
# with ptscaled/rhoscaled from the same ptmean and rho range as tf_fit.py.

# Step 2: data model with a low-order residual
tf_res = rl.BasisPoly("tf_res", (n_pt_res, n_rho_res), ["pt", "rho"], basis="Bernstein", limits=(0, 10))
tf_params = qcdeff_data_over_mc * tf_mc_final * tf_res(ptscaled, rhoscaled)

lumi = rl.NuisanceParameter("lumi", "lnN")
model = rl.Model("rhalphabet")
for ipt in range(npt):
    for region in ("pass", "fail"):
        ch = rl.Channel(f"ptbin{ipt}{region}")            # no underscore in channel names
        model.addChannel(ch)
        for name in ("zbb", "zqq", "wqq", "top", "hbb"):  # flavour-split, gen-matched templates
            sumw, sumw2 = templates[name][region][ipt]
            stype = rl.Sample.SIGNAL if name in ("zbb", "hbb") else rl.Sample.BACKGROUND
            s = rl.TemplateSample(f"{ch.name}_{name}", stype, (sumw, msdbins, "msd", sumw2))
            s.setParamEffect(lumi, 1.016)                 # your period's value
            ch.addSample(s)
        ch.setObservation((data[region][ipt], msdbins, "msd"))
        ch.mask = valid[ipt].copy()                       # rho mask: SAME in pass and fail
        # autoMCStats BEFORE the QCD samples: it reads sumw2 from every sample in
        # the channel, and ParametericSample / TransferFactorSample have none
        # (AttributeError: '_sumw2').
        ch.autoMCStats()

    fail, passed = model[f"ptbin{ipt}fail"], model[f"ptbin{ipt}pass"]
    init = fail.getObservation().astype(float)
    for s in fail:
        init -= s.getExpectation(nominal=True)            # data minus resonant MC
    if np.any(init[valid[ipt]] < 0):
        raise ValueError("negative initial QCD in fail region")
    pars = np.array([rl.IndependentParameter(f"qcdparam_ptbin{ipt}_msdbin{i}", 0,
                                             constant=not valid[ipt][i])   # masked -> constant
                     for i in range(msd.nbins)])
    fq = rl.ParametericSample(f"ptbin{ipt}fail_qcd", rl.Sample.BACKGROUND, msd,
                              init * (1 + 10.0 / np.maximum(1.0, np.sqrt(init))) ** pars)
    fail.addSample(fq)
    passed.addSample(rl.TransferFactorSample(f"ptbin{ipt}pass_qcd", rl.Sample.BACKGROUND,
                                             tf_params[ipt, :], fq))

model.t2w_config = ("-P HiggsAnalysis.CombinedLimit.PhysicsModel:multiSignalModel "
                    "--PO 'map=.*/zbb:r_Z[1,-2,5]' --PO 'map=.*/hbb:r_H[1,-20,20]'")
model.renderCombine("model_out")                         # cards, workspace, build.sh
```

Then `cd model_out && bash build.sh`; Combine commands are in
[combine-recipes.md](combine-recipes.md).

## Rules

- **Never replace the free fail parameters with a fixed "data minus MC"
  template.** The fail statistical uncertainty then never reaches the pass
  prediction and errors come out too small.
- **At least one SIGNAL sample** is required by `text2workspace`, also in
  signal-free models used for the F-test: keep the V(bb) template as SIGNAL.
- `BernsteinPoly` is deprecated; use `BasisPoly(..., basis="Bernstein")`.
  `basis="Chebyshev"` gives the alternative-function check.
- `update_from_roofit` rounds to 3 decimals and fixes the shape without its
  uncertainty; prefer the `DecorrelatedNuisanceVector` route above.
- `TemplateSample` for MC templates; a `ParametericSample` built as rate x
  constant is normalised to 1.
- Template tuple order is `(sumw, binning, observable_name, sumw2)`.
- Sample names are `f"{channel}_{process}"`; `t2w_config` maps the process part.
- Several data-taking periods: one `tf_res` per period (independent
  parameters), shared POIs; lumi partly correlated, tagger SFs per period.

## Blinding and several POIs

- **Blinding mask** in pass only: `passed.mask = valid[ipt] & ~in_window`;
  freeze the blinded POI. Unblind by rebuilding without the window.
- **W/Z degeneracy**: W and Z peaks overlap at soft-drop resolution. Report
  `r_Z` with `r_W` floating (and their correlation) and with `r_W` fixed; if
  `r_Z` is far from 1, check the working point, the flavour split and the
  tagger SF before quoting it.
- **Tagger SF in situ**: give Z(bb) and H(bb) the same pass/fail SF nuisance
  (pass up, fail down, total conserved; [systematics.md](systematics.md)) so
  the Z(bb) peak constrains it.
