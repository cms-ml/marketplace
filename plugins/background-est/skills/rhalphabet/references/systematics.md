# Systematic uncertainties in a rhalphabet fit

Loaded from SKILL.md ("Full fit"). QCD needs no MC systematics: it is
the fail data times the TF, and its uncertainty is the fail parameters plus the
TF parameters. Everything else comes from simulation and needs the sources
below. Measure the sizes in your own analysis; do not copy numbers from a paper.

All sources are `rl.NuisanceParameter(name, "lnN")` for a normalisation effect
or `rl.NuisanceParameter(name, "shape")` for a bin-by-bin effect, attached with
`sample.setParamEffect(param, up, down)`. For `lnN`, `up` and `down` are
numbers (1.05, 0.95). For `shape`, pass either relative arrays (up/nominal
per bin) or histograms of the shifted yields.

| Source                                  | Applies to       | Type                          | How to get it                                                                                                       |
| --------------------------------------- | ---------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Luminosity                              | all MC           | lnN                           | Official value for the data-taking period                                                                           |
| Template MC statistics                  | all MC           | `ch.autoMCStats()`            | Needs `sumw2` in every template                                                                                     |
| Tagger efficiency, V/H (true two-prong) | W, Z, H, signal  | lnN, anticorrelated pass/fail | Scale factor from a calibration (SF in pass, compensating change in fail so the total is conserved)                 |
| Tagger efficiency, top                  | top              | lnN or free parameter         | Muon control region ([control-regions.md](control-regions.md))                                                      |
| Jet mass scale                          | resonant samples | shape                         | Shift the jet mass by +-the scale uncertainty, refill the templates                                                 |
| Jet mass resolution                     | resonant samples | shape                         | Smear the jet mass by the extra resolution, refill                                                                  |
| Jet energy scale / resolution           | resonant samples | shape or lnN                  | Shift or smear jet pT; events migrate between pT bins and across the pT cut                                         |
| Trigger efficiency                      | all MC           | lnN (or shape in pT)          | Data/MC turn-on with an orthogonal reference trigger; size set by the plateau precision and any residual difference |
| Top normalisation                       | top              | free parameter or lnN         | Muon control region                                                                                                 |
| V+jets higher-order corrections         | W, Z             | shape in pT                   | NLO QCD and NLO EW k-factors versus boson pT, with their uncertainties; decorrelate W and Z partly                  |
| Signal theory                           | signal           | lnN (acceptance)              | Renormalisation and factorisation scale variations, PDF replicas, parton-shower ISR/FSR weights                     |
| Pileup                                  | all MC           | shape or lnN                  | Vary the minimum-bias cross section                                                                                 |

## Tagger scale factor with a conserved total

A tagger SF moves events between pass and fail; the sum must not change:

```python
sf = rl.NuisanceParameter("vtag_sf", "lnN")
n_pass = passed_sample.getExpectation(nominal=True).sum()
n_fail = failed_sample.getExpectation(nominal=True).sum()
d = 0.10                                     # relative SF uncertainty (your number)
passed_sample.setParamEffect(sf, 1 + d)
failed_sample.setParamEffect(sf, 1 - d * n_pass / n_fail)
```

## Jet mass scale and resolution as shapes

Fill the nominal, scale-up/down and resolution-up/down templates in the same
histogramming pass (one `msd` axis per variation). Then

```python
jms = rl.NuisanceParameter("jms", "shape")
jmr = rl.NuisanceParameter("jmr", "shape")
s.setParamEffect(jms, h_jms_up, h_jms_down)   # histograms of shifted yields
s.setParamEffect(jmr, h_jmr_up, h_jmr_down)
```

A scale shift moves the peak; with coarse mass bins the effect is large in a
few bins, so check that the up/down ratios are below about 1.5, or use the
`scale` argument of `setParamEffect` to keep vertical interpolation sane.

## Gotchas

- **Correlations:** a source shared by several samples (lumi, JMS) must be the
  same `NuisanceParameter` object on all of them, or Combine treats them as
  independent.
- **Signal-strength errors look too small** in a fit without these sources.
  Compare your error with the published one scaled by 1/sqrt(luminosity) as a
  sanity check: being much smaller usually means a missing source.
- **Impacts:** after adding systematics, run impacts (see the Combine docs,
  `combineTool.py -M Impacts`) to see which sources drive the POI.
