# Rhalphabet for a resonance search (signal mass scan)

Loaded from SKILL.md, for searches for a new resonance in the jet mass
(e.g. a leptophobic Z' or a scalar decaying to quarks) rather than a measurement
of a known peak. Everything in SKILL.md still applies; this adds the scan.

## Signal templates

- One signal sample per generated mass point. Fill the pass and fail `msd`
  templates per pT bin from each, with the same selection as data.
- **Signal in fail**: a signal at 5% pass efficiency still puts 95% of its
  events in fail. Always add it there.
- **Between generated masses**: either fit only at generated masses, or
  morph templates (shift and stretch the peak by the mass ratio, interpolate
  efficiency linearly). State which. Do not quote a limit at a mass with no
  template.
- **rho coverage**: a signal mass `M` at pT `p` sits at
  `rho = 2 ln(M/p)`. In low pT bins a heavy signal can fall outside the rho
  window (masked), and in high pT bins a light one can. Tabulate, per mass,
  which pT bins keep the peak inside the window, and expect the sensitivity
  to come from those.
- **Normalisation**: the template is `sigma x B x L x efficiency`. If the
  sample has a generator filter (e.g. a boson-pT cut), sigma must be the
  cross section after the filter (GenXSecAnalyzer "After filter: final cross
  section").

## Fit and limits

One model per mass point (same QCD model, same TF order as chosen with the
signal-free fit; check the F-test does not change with the signal mass).

```bash
for M in 50 75 100 ...; do
  combine -M AsymptoticLimits -d M$M/model_combined.root -n _M$M -m $M \
          --rMin 0 --rMax 50 --run both
done
```

`r` is in units of the template normalisation. For a coupling `g`, with
`sigma proportional to g^2` at fixed width over mass (check your model; the
width also grows with `g`), the limit is `g_lim = g_ref * sqrt(r_lim)`.
State the coupling convention: different papers normalise `g` differently,
so convert before comparing.

Cross-check at one or two masses with toys (`HybridNew`), since asymptotics
can be off when the expected signal is a few events; see the `combine` skill.

## Significance and look-elsewhere

- Local significance per mass: `combine -M Significance` at each mass.
- The largest local excess over the scan overstates the evidence. Quote a
  global significance (trials factor from toys, or the Gross-Vitells upcrossing
  estimate) next to the local one.

## Plots expected in a report

- Expected and observed limit versus mass with 1 and 2 sigma bands.
- Local p-value versus mass.
- Post-fit pass mass spectra per pT bin with the best-fit signal at the most
  significant mass.
- Signal efficiency (pass) and acceptance versus mass.

## Gotchas

- **Signal near W or Z**: a signal at 80-100 GeV is degenerate with the V
  peaks; let V float with its own SF and say the limit there is weaker.
- **Same TF for all masses**: re-choosing the TF order per mass is a
  look-elsewhere effect of its own. Fix it once, from the signal-free fit.
- **Signal width**: check the generated width at your reference coupling;
  a narrow-width template is wrong where the natural width is comparable to
  the jet mass resolution.
