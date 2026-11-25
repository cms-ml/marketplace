# Control regions

Loaded from SKILL.md ("Full fit"; also the selection in selection.md).

## Why a top control region

Hadronic top jets pass most two-prong taggers at a rate the simulation does
not get right, and a loose or non-decorrelated tagger can let top dominate the
pass region above about 150 GeV in jet mass. Always plot the pass-region
composition per process (data minus fitted QCD, stacked W, Z, top, signal).
If top is large, constrain it with data.

## Muon (semileptonic ttbar) control region

Selection idea, to be tuned on your samples:

- one tight muon (well above the single-muon trigger plateau), opposite
  hemisphere to the large-radius jet (delta phi > 2/3 pi or so);
- at least one b-tagged small-radius jet away from the large-radius jet;
- the same large-radius jet selection, split by the same tagger into pass and
  fail;
- a single-muon trigger (orthogonal to the hadronic signal triggers).

In rhalphalib, the control region is two more channels (`muonCRpass`,
`muonCRfail`) in the same model, with the top samples sharing two
parameters with the signal region:

```python
top_norm = rl.IndependentParameter("top_norm", 1.0, 0, 10)   # overall top yield
top_eff  = rl.IndependentParameter("top_eff",  1.0, 0, 10)   # top pass/fail SF

def attach_top(pass_s, fail_s):
    pf = pass_s.getExpectation(nominal=True).sum() / fail_s.getExpectation(nominal=True).sum()
    pass_s.setParamEffect(top_eff, 1 * top_eff)
    fail_s.setParamEffect(top_eff, (1 - top_eff) * pf + 1)   # conserves pass+fail
    pass_s.setParamEffect(top_norm, 1 * top_norm)
    fail_s.setParamEffect(top_norm, 1 * top_norm)

for ipt in range(npt):                              # signal-region pT bins
    attach_top(model[f"ptbin{ipt}pass"][f"ptbin{ipt}pass_top"],
               model[f"ptbin{ipt}fail"][f"ptbin{ipt}fail_top"])
attach_top(model["muonCRpass"]["muonCRpass_top"], model["muonCRfail"]["muonCRfail_top"])
```

The control region has no QCD transfer factor; its non-top backgrounds
(W+jets, single top, QCD with a muon) come from simulation with their own
normalisation uncertainties. Mask nothing by rho there unless the binning
requires it. Report `top_norm` and `top_eff` with errors.

## W/Z peak as an in-situ calibration

In a search for a new resonance, the W and Z peaks in the pass region
measure the tagger SF, jet mass scale and resolution for two-prong jets in
situ. Let the V samples carry the same `jms`, `jmr` and tagger-SF nuisances as
the signal, so the fit constrains them from the peaks and carries the
constraint to the signal. Check the post-fit values against any external
calibration.

## Muon control region as counting channels

The simplest form, and enough to constrain top: one bin per region. Use a
single-bin observable spanning the msd range:

```python
one = rl.Observable("msd", np.array([msd_lo, msd_hi]))
for region in ("pass", "fail"):
    ch = rl.Channel(f"muonCR{region}")
    model.addChannel(ch)
    for name, (sumw, sumw2) in cr_templates[region].items():   # summed over msd
        ch.addSample(rl.TemplateSample(f"{ch.name}_{name}", rl.Sample.BACKGROUND,
                                       (np.array([sumw]), one.binning, "msd", np.array([sumw2]))))
    ch.setObservation((np.array([n_data[region]]), one.binning, "msd"))
```

Attach `top_norm` and `top_eff` as above. Use the msd-shape version only if
the top peak shape itself needs a constraint.

## W-tag control region (jet mass scale, resolution, substructure SF)

Semileptonic ttbar with a muon gives a clean sample of hadronic W jets:
muon + b-tagged AK4 jet, the AK8 jet in the opposite hemisphere, msd in a
window around the W and top peaks. Split by the same two-prong preselection
into pass and fail, gen-match the AK8 jet to the hadronic W (matched,
top-merged, unmatched templates), and fit the msd distribution in pass and
fail together:

- the substructure SF = data/MC pass fraction of matched W jets;
- the jet mass scale (peak shift) and resolution (width ratio) from morphing
  the matched template (`rhalphalib.template_morph.MorphHistW2` shifts and
  smears a histogram with its sumw2).

Apply the three results to the W, Z, H and signal templates in the signal
region as nuisances with the measured central values and errors
([systematics.md](systematics.md)). Without this CR, state the omission and
use external values if any.
