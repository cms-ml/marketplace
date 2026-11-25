# Independent review of the sideband estimator

**Implementation passes the checks exercised. Both published-spectrum predictions agree with the held-out observations at the tested predictive level. Calibration depends on the procedure and truth.** The nominal 68.27% interval for expected background covers only 58.0% of fresh experiments with an exact linear background, a 50-event injected signal and repeated model selection. A localized background excess gives a substantial signed spurious signal. These results support use for diagnostic interpolation with analysis-specific calibration.

The independent plan was frozen in commit `fe68cfd`. The student snapshot is `58243a33463cfffa0f7f618bb853ede1cf3f8396`. Its archive digest and the input histogram digest are in [comparison.json](comparison.json). See the [independent plan](VALIDATION_PLAN.md), [source manifest](source_manifest.json), and [ensemble results](ensembles.json).

## Published dimuon spectrum

The 2016 CMS search publishes reconstructed opposite-sign dimuon densities in variable logarithmic bins. For each of the eleven bins completely inside 400–1000 GeV, we allowed half a unit in the last printed decimal for the density and each edge, then bounded the product of density and width. Every interval contained exactly one integer. The two predefined center rules select the full bins shown below. Counts outside the mask were the only observations supplied to the student fit and AIC selection. The CMS curve comes from estimated SM processes, normalized using the Z region. It uses a different background construction. [CMS paper](https://arxiv.org/abs/1803.06292) · [Figure 1 right](https://doi.org/10.17182/hepdata.83971.v1/t4) · [Table 3](https://doi.org/10.17182/hepdata.83971.v1/t2)

| Held-out mass (GeV) | Observed | Fit expectation ± fit SD | 68% future-count interval | Published background | Observed minus fit, in predictive SD |
| ------------------- | -------: | -----------------------: | ------------------------: | -------------------: | -----------------------------------: |
| 550.56–645.22       |     1086 |            1063.1 ± 26.4 |                 1021–1105 |               1207.7 |                                +0.55 |
| 756.15–818.57       |      156 |            169.95 ± 6.44 |                   155–184 |               199.95 |                                −0.96 |

Both fits select order 2. Sideband deviances are 9.49 for 6 degrees of freedom and 10.97 for 7. Bounds target future counts in the omitted bins. Their measured counts include potential signal. The two tests share events and sidebands. The JSON retains asymmetric published systematic-plus-statistical background errors bin by bin. HEPData gives no interbin covariance, so the first row has no combined CMS error or significance against the curve. The second row uses a single published bin. CMS and the fitted estimate also share data and have different normalizations.

[Lower window plot](published_1.pdf) · [Upper window plot](published_2.pdf)

The scouting analysis EXO-21-005 uses mass sidebands inside local fit ranges extending multiple detector resolutions around the signal hypothesis. Its 2017–18 dedicated low-threshold trigger and reconstruction select a different population. Its HEPData v1 contains acceptance, efficiencies, limits and interpretations. Figure 3 observations are absent. For an example of an explicit sideband extraction, the CMS Higgs discovery paper HIG-12-036 shows the six diphoton sidebands used for the background interpolation. These are methodology references. [EXO-21-005 paper](https://arxiv.org/html/2309.16003) · [scouting tables](https://www.hepdata.net/record/ins2704121) · [CMS diphoton sideband analysis](https://cms-results.web.cern.ch/cms-results/public-results/publications/HIG-12-036/index.html)

## Open Data comparability

| Quantity                | Student 2016G/H Open Data                                                     | Published EXO-16-047                                                           | Scope                                                        |
| ----------------------- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------ |
| Era, exposure           | 16.3927 fb⁻¹, G/H, UL reprocessing                                            | 36.3 fb⁻¹, all 2016, dimuon channel                                            | Overlapping recorded events and different period mix         |
| Trigger                 | Mu50 or TkMu50, no object matching                                            | Single-muon 50 GeV trigger, offline matching                                   | Similar plateau, different selection                         |
| Reconstruction and mass | TuneP transverse momentum, PF directions, reconstructed pair mass             | High-momentum muon reconstruction and calibration, reconstructed pair mass     | Comparable observable with migration differences             |
| Selection               | Opposite signs, both above 53 GeV, tracker isolation, cosmic veto, high-pT ID | Similar kinematics and isolation, includes vertex quality and trigger matching | Acceptance differences persist                               |
| Normalization           | Integer observations, sideband fit                                            | Observations and Z-normalized SM contributions                                 | Absolute background yields across samples **NOT COMPARABLE** |
| Binning and level       | 150 detector-level logarithmic bins over 300–6000 GeV                         | Variable detector-level bins, densities                                        | Compare shapes with edge ambiguity bounded                   |

A descriptive shape check divides 400.87–959.30 GeV at 645.22 GeV. The published upper fraction is 12.96%. Assigning all ambiguous boundary-bin events in the Open Data histogram either way gives conservative bounds of 12.55–15.46%. This supports shape compatibility at available bin resolution. The bounds describe event assignment, not statistical intervals. The samples overlap and their joint covariance is unknown. Neither an absolute reproduction nor an independent-sample p-value follows.

## Independent fits and toys

A separate extended Poisson fit uses adaptive quadrature and a free log-amplitude. Nelder–Mead optimizes its likelihood. Finite differences of integrated bin means give a Fisher covariance which includes normalization and shape. For both published windows its estimated yield and variance agree with the student result to fractional precision better than 2×10⁻⁷. Replacing every masked observation with a billion events gave identical reports for both fits. The independent fit also repeats the two simultaneously masked Open Data integrals and their cross-covariance on the archived input spectrum.

Fresh Poisson ensembles used the frozen six seeds and 300 attempts per row, each with 2,000 expected background events. The independent generator integrates all bin means. A Gaussian injects 0 or 50 events with 6.90% of its yield in the sidebands. The archived fitter runs on each pseudoexperiment. The signed signal fit then uses all bins. Every fit succeeded with no boundary solutions. Consequently coverage conditioned on success equals full-procedure coverage for these ensembles. The table gives mean estimate minus truth, mean and width of (estimate − truth)/estimated SD, and empirical coverage for the selected procedure.

| Truth     | Signal injected | Background bias | B pull mean / SD | B coverage ± MC SE | Signed signal bias | Signal pull mean / SD | Signal coverage ± MC SE |
| --------- | --------------: | --------------: | ---------------: | -----------------: | -----------------: | --------------------: | ----------------------: |
| linear    |               0 |           +0.21 |     +0.00 / 1.13 |        63.7 ± 2.8% |              +0.76 |          +0.02 / 1.05 |             65.0 ± 2.8% |
| linear    |              50 |           +0.47 |     +0.03 / 1.19 |        58.0 ± 2.8% |              -0.96 |          -0.06 / 0.99 |             69.0 ± 2.7% |
| quadratic |               0 |           -2.71 |     -0.20 / 1.05 |        64.0 ± 2.8% |              +2.50 |          +0.09 / 0.96 |             71.0 ± 2.6% |
| quadratic |              50 |           +3.75 |     +0.26 / 1.33 |        65.3 ± 2.7% |              -2.08 |          -0.10 / 1.05 |             67.0 ± 2.7% |
| bump      |               0 |          -52.46 |     -4.98 / 1.58 |         1.0 ± 0.6% |             +58.18 |          +2.54 / 0.95 |              6.0 ± 1.4% |
| bump      |              50 |          -51.30 |     -4.89 / 1.72 |         3.0 ± 1.0% |             +56.30 |          +2.33 / 1.04 |             11.3 ± 1.8% |

Fixed-linear background coverages for the same rows were 67.3%, 63.3%, 0%, 0%, 0%, and 0%. Selected-order background coverage crosses the predeclared three-standard-error deficit threshold for linear truth with injection and both bump scenarios. The quadratic truth's selected background pull means also cross the predeclared three-standard-error threshold for bias. Without injection on the localized bump, selected signed signal bias is +58.2 events, and its nominal one-standard-deviation interval covers zero in 18/300 trials. With a fixed linear model on quadratic truth, background-only signed signal bias is −47.1 events. Both signs matter. The complete-selection toy results and fixed-order controls include valid/covered counts, negative signed fits, boundary counts, bias and pull widths. The six separate scenarios have finite precision and share no random streams.

**Method verdict.** Retain the estimator as a masked-count fit and qualify its intervals as within-model approximations. The data test supports interpolation in the two chosen windows. Analysis use requiring calibrated coverage needs a declared selection-aware construction tested with independent truths, including sideband signal leakage. Changing the uncertainties to repair these six observed results would consume the validation sample.

## Reproduction

This review and the [student analysis](../README.md) are in the same branch.
The numerical review remains pinned to the original student commit. To
recreate that snapshot from the repository root without changing checkouts:

```bash
export STUDENT_SNAPSHOT=$(mktemp -d)
git archive 58243a33463cfffa0f7f618bb853ede1cf3f8396 > "$STUDENT_SNAPSHOT/student.tar"
printf '%s  %s\n' \
  07ec561c67344d4351d34749e47ccead6baae2a12a22e452757aaf82d4875819 \
  "$STUDENT_SNAPSHOT/student.tar" | sha256sum --check
tar -xf "$STUDENT_SNAPSHOT/student.tar" -C "$STUDENT_SNAPSHOT"
```

Use the LCG_109 x86_64 EL9 GCC15 view with Python, NumPy, SciPy, PyYAML, hist, Matplotlib and mplhep. From this directory, run the following with paths to the immutable student archive root, the extracted HEPData v1 directory, and the fixed Open Data input histogram.

```bash
python3 published.py "$STUDENT_SNAPSHOT" "$EXO16_TABLE_DIRECTORY" "$OPEN_DATA_TEMPLATES"
OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1 python3 toys_review.py "$STUDENT_SNAPSHOT"
python3 check_results.py
```

## Review disposition

The independent Open Data integrals are 599.5313 and 56.62386 events against 587 and 69 observed. The variance pair is 142.3313 and 7.69166 events² with cross-covariance 9.48510 events², reproduced from the raw histogram. For the published coarse 600–900 GeV slice, Table 3 records 1,311 events. The fine-bin containment bounds are 862–1,420 because both table boundaries cut fine bins. For the single-bin second holdout, the published 199.95-event background has asymmetric errors −12.12/+11.64 events.

Sol addressed the interval-interpretation finding in `49756e8feed255da2e3ec84f95f756dd5ba9da10`. Independent Git-tree comparison shows changes only to the skill and its histogram reference. Both now explicitly address omitted order-selection uncertainty and potential in-family background undercoverage from signal leakage. Documentation review **PASS**. Numerical results above remain pinned to the original review SHA. The qualification on method coverage still applies.
