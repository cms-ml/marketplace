# Sideband-fit validation

Use the official CMS workshop dimuon input for a known-resonance extraction and the fixed 2016G/H dimuon snapshot for background prediction over omitted continuum bins. Quantify interpolation and signed signal behavior with repeated Poisson samples.

## Data samples

| Input                                                                                                                       | Data product                                        | Role                                      |
| --------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------- | ----------------------------------------- |
| CMS workshop notebook's `dimuon_summary_data.csv`                                                                           | 100,000 educational dimuon four-vectors             | Workshop replication and J/psi extraction |
| `Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1` and `Run2016H/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1` | Fixed snapshot of independent selected event counts | Masked continuum interpolation            |
| Poisson ensembles from declared bin expectations                                                                            | Pseudoexperiments                                   | Bias, pull and coverage studies           |

- The workshop uses each row `(E, px, py, pz, charge)` as a preselected dimuon. Mirror its use of all three charge combinations. It supplies no trigger, certification or luminosity metadata for this CSV.
- The snapshot applies the golden JSON, event filters and `HLT_Mu50 OR HLT_TkMu50`. Use the snapshot's recorded triggers, corrections and opposite-sign pair selection. Do not reskim or use its fitted curves.
- Simulation is solely from a declared point-process model. No cross-section normalization is needed.

## Histograms

- Dimuon invariant mass in GeV, unweighted rows or unique selected events. Use 30 bins from 2.8 to 3.4 GeV for the workshop and the original 150 logarithmic bins spanning 300–6000 GeV for the continuum.
- Freeze an excluded workshop interval of 3.0–3.2 GeV. Recalculate the notebook's simple average of the two equal-width sideband yields using its strict inequalities as a separate benchmark.
- In the continuum, freeze bin indices `[25, 31)` and `[55, 61)` using the documented logarithmic grid. These deterministic indices give two separated internal six-bin windows with data on either side. No count was consulted when choosing settings. Hold both windows out together and keep their fitted uncertainties correlated.

## Analysis steps

1. Parse the workshop four-vectors and calculate `sqrt(E²−px²−py²−pz²)` in GeV. Validate schema and inspect nonphysical or nonfinite masses before binning.
2. Verify snapshot provenance and load its raw edges/counts. Hash the payload and record all settings before the analysis.
3. Keep masked observations out of the statistical interface until the predictions and toy truth parameters are fixed. Unmask for residuals, extraction and recorded closure.

## Corrections and systematics

Use the supplied selected spectra directly. Propagate the full Poisson fit covariance. Probe model dependence with two in-family shapes and two out-of-family shapes. Assign no calibrated model-shape systematic or physical signal limit from this exercise.

## Workflow

Use a positive exponential of a first- or second-degree polynomial in rescaled mass (workshop) or rescaled log mass (continuum). Integrate the density over physical bin widths. Compare a fixed linear model with minimum sideband AIC selection, refitting after every Poisson draw. Fit a signed Gaussian signal in a joint likelihood after selection for the toy signal diagnostics. Include the integrated tails in the sidebands, and constrain total expectations to stay positive.

## Statistical analysis

- Parameterize the normalization as expected sideband count. Include zeros and use a Poisson likelihood. Check optimization status, projected score, bounds, and positive-definite covariance. Store both models and their full bin covariance.
- Report nominal 68.27% log-delta intervals for expected masked yields. Use equal-tailed Poisson-gamma intervals (matched to the estimated mean and variance) for observed counts. Discrete coverage can exceed nominal. Report future-count and signal-subtracted expectation targets separately for injections. No combined-window significance is calculated.
- For each background truth and signal strength, fluctuate every bin. Use a Gaussian peak centered at the geometric midpoint of the first mask with width 2.5% of its mass and total in-range injected yields 0 and 45. For both zero and nonzero injection, report expected background closure, the observed-count interval only for background-only experiments, signed signal bias/error, failure/constraint counts, and coverage conditioned on a valid result and over all attempts with failures counted as uncovered.
- Calibrate truth parameters from continuum sidebands only. Use the fitted linear and quadratic shapes and (i) a positive mixture of the linear shape with a component 2 units steeper in the rescaled coordinate, normalized to a 12% sideband fraction, and (ii) a 7% multiplicative broad Gaussian modulation of the linear shape (relative width 4.5%), normalized to the same sideband yield. Center the broad modulation at the injection mass and use it to test local shape bias. Treat its strength and width as stress-test choices.
- Record Monte Carlo standard errors (binomial for coverage), interval widths, pull means and sample standard deviations. Assess each study as evidence, without retuning from masked data or setting universal pass thresholds. Use a 12-toy engineering smoke campaign followed by 600 independent attempts per scenario on a distinct stream.

## Tools

- Use `hist` for histogram storage/fill, NumPy and SciPy for statistics, and `mplhep` for CMS-style PDF/PNG figures.
- Use the same generic integer-bin interface for externally verified HEPData spectra. The independent review owns its source verification, fit range, blind-window choices and comparison with real CMS analyses.
