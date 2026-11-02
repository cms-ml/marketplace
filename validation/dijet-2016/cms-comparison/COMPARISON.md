# Comparison of two CMS Open Data student analyses with published CMS results

Reviewer: cms-results-validator agent, first run (before the `cms-results-comparison` skill existed). Date of the review: 27 October 2026.
All numbers come from the scripts in this directory (`run_all.sh`), machine-readable in [comparison.json](comparison.json), per-test files in `results/`, plots in `plots/` (PNG + PDF; not committed to keep the repository small: `run_all.sh` rebuilds them).
The student results are CMS **Open Data** results (labelled "CMS Open Data" in the plots), not CMS results. Nothing in the students' directories was changed; the student's histograms,
binning and selections are used as delivered (the dimuon re-runs are separate, labelled variants).

## Verdict rules

Shape tests: two-sample (or covariance) chi2 with the statistical errors of both sides unless stated; INCONSISTENT if p < 0.0027 (> 3 sigma), TENSION if 2-3 sigma **or** a ratio slope more than 3 sigma from zero, else CONSISTENT.
Absolute tests: ratio with statistical error plus an explicit, assumed systematic envelope (lumi 1.2 % (+) 1.2 % in quadrature, 1 % dijet-mass-scale times the local spectrum index k; b-tag and other CMS systematics NOT included), same 3 sigma / 2 sigma rule.
Exact tests: stat (+) fit-systematic uncertainty. NOT COMPARABLE when the quantities cannot be related without simulation.

## Summary of verdicts

| ID      | Test                                                      | Level    | CMS counterpart (HEPData table)                                                             | Number                                                                                                  | Verdict                                                           |
| ------- | --------------------------------------------------------- | -------- | ------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| D1a     | DeepJet working points                                    | exact    | BTV POG json 2016postVFP_UL                                                                 | max abs diff 0 (L 0.048, M 0.2489, T 0.6377)                                                            | CONSISTENT                                                        |
| D1b     | Luminosity 2016G+H                                        | exact    | Open Data record 1059, Run2016G+H lumi files                                                | 16.3927 vs 16.3934 fb^-1, ratio 1 - 4.2e-5 (unc. 1.2 %)                                                 | CONSISTENT                                                        |
| D2a     | m_jj shape, 2 b tags                                      | shape    | EXO-20-008, ins1920627 "Figure 3 first row first column"                                    | chi2/ndf 22.3/23 (p 0.50), slope -0.000 +- 0.023 /TeV                                                   | CONSISTENT                                                        |
| D2b     | m_jj shape, >=1 b tag vs "inclusive single b"             | shape    | "Figure 3 fourth row first column"                                                          | chi2/ndf 38.7/28 (p 0.086), slope +0.034 +- 0.008 /TeV (4.2 sigma)                                      | TENSION                                                           |
| D2b-alt | m_jj shape, >=1 b tag vs single b + double b              | shape    | rows 1 + 2                                                                                  | chi2/ndf 24.9/28 (p 0.63), slope +0.015 +- 0.008                                                        | CONSISTENT                                                        |
| D2c     | m_jj shape, exactly 1 b tag (>=1b minus 2b)               | shape    | "Figure 3 second row first column"                                                          | chi2/ndf 19.8/28 (p 0.87), slope +0.009 +- 0.009                                                        | CONSISTENT                                                        |
| D3a     | dsigma/dm, 2 b tags                                       | absolute | row 1                                                                                       | ratio 0.968 +- 0.009 (stat), 0.6 sigma with envelope                                                    | CONSISTENT                                                        |
| D3b     | dsigma/dm, >=1 b vs "inclusive single b"                  | absolute | row 4                                                                                       | ratio 0.719 +- 0.002, 6.2 sigma                                                                         | INCONSISTENT                                                      |
| D3b-alt | dsigma/dm, >=1 b vs single b + double b                   | absolute | rows 1 + 2                                                                                  | ratio 0.836 +- 0.003, 3.1 sigma                                                                         | INCONSISTENT (borderline)                                         |
| D3c     | dsigma/dm, exactly 1 b                                    | absolute | row 2                                                                                       | ratio 0.823 +- 0.003, 3.4 sigma                                                                         | INCONSISTENT                                                      |
| D4a     | Z' event efficiency vs mass, 2 b                          | trend    | EXO-20-008 "Figure 2"                                                                       | ratio student/CMS 1.63 (1.8 TeV) rising to 2.63 (5 TeV); mean 1.87                                      | INCONSISTENT                                                      |
| D4b     | same, exactly 1 b                                         | trend    | "Figure 2"                                                                                  | ratio 1.35 / 1.12 (min, 2.5 TeV) / 1.43; mean 1.25                                                      | INCONSISTENT                                                      |
| D4c     | same, acceptance before b tagging                         | trend    | "Figure 2"                                                                                  | ratio 1.55 (1.8 TeV), 1.17-1.20 plateau from 3 TeV                                                      | INCONSISTENT                                                      |
| D5      | inclusive m_jj shape                                      | shape    | EXO-16-056, ins1676214 "Differential dijet spectrum (High-mass analysis)"                   | chi2/ndf 43.2/34 (p 0.13), slope -0.006 +- 0.003 /TeV                                                   | CONSISTENT                                                        |
| D5b     | inclusive dsigma/dm                                       | absolute | same                                                                                        | ratio 0.505 (0.650 after matching the \|deta\| cut), flat in m_jj                                       | INCONSISTENT                                                      |
| M1      | peak positions and widths vs PDG                          | exact    | PDG API (edition 2026)                                                                      | offsets -0.7 ... -2.2 per mille, all negative; Upsilon(1S) 9.2 sigma, (2S) 3.9 sigma; sigma/m 1.1-1.4 % | INCONSISTENT (formal; size expected without momentum corrections) |
| M2a     | Upsilon(2S)/(1S) yield ratio                              | ratio    | BPH-15-005, ins1633431 "Table 12" (+ Tables 3, 4)                                           | student/CMS 1.017 +- 0.045, chi2/ndf 1.1/7                                                              | CONSISTENT                                                        |
| M2b     | Upsilon(3S)/(1S) yield ratio                              | ratio    | "Table 12" (+ Tables 3, 5)                                                                  | student/CMS 1.021 +- 0.053, chi2/ndf 3.8/7                                                              | CONSISTENT                                                        |
| M3a     | Z pT shape, 0-52 GeV                                      | shape    | SMP-17-010, ins1753680 "Figure 14a" (+ "Figure 6", "Covariance Matrix auxiliary Figure 1a") | chi2/ndf 1128/13; student/CMS 0.85 ... 1.16                                                             | INCONSISTENT                                                      |
| M3b     | Z \|y\| shape                                             | shape    | "Figure 14c" (+ "Figure 5", "... Figure 1c")                                                | chi2/ndf 3454/11; student/CMS 1.13 ... 0.80                                                             | INCONSISTENT                                                      |
| M4      | Z-region mass shape, re-run with SMP-17-001 fiducial cuts | shape    | SMP-17-001, ins1711625 "Table 5"                                                            | chi2/ndf 2440/12 (kinematic fiducial); 239/12 with tight ID + iso                                       | INCONSISTENT                                                      |
| M4b     | mass shape vs Table 3 (full phase space, FSR-corrected)   | shape    | "Table 3"                                                                                   | needs acceptance and FSR correction from simulation                                                     | NOT COMPARABLE                                                    |

Level of every test is stated in the sections below. **Detector-level counts (student) are compared with unfolded/corrected CMS results in M3, M4 and (for the efficiency) D4, and with CMS observed detector-level counts in D2, D3, D5.**

## Comparability matrix

| Student result                                                    | Counterpart                                                      | sqrt(s) / year            | Lumi (student / CMS)                           | Selection differences                                                                                          | Object differences                                                                   | Level                                             | Units            | Test            |
| ----------------------------------------------------------------- | ---------------------------------------------------------------- | ------------------------- | ---------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------ | ------------------------------------------------- | ---------------- | --------------- |
| DeepJet WPs                                                       | BTV POG json                                                     | 13 TeV, 2016postVFP       | -                                              | -                                                                                                              | -                                                                                    | constants                                         | -                | exact           |
| Luminosity                                                        | Open Data record 1059                                            | 13 TeV, 2016G+H           | 16.39                                          | -                                                                                                              | -                                                                                    | total                                             | fb^-1            | exact           |
| m_jj, 2b and >=1b (AK4 CHS, \|eta\|<2.4, \|deta\|<1.1, m_jj>1058) | EXO-20-008 (paper 2676943; HEPData on PAS 1920627), 2016 columns | 13 TeV, 2016 (G+H vs B-H) | 16.39 / 36.3 (table qualifier says 138: wrong) | CMS: m_jj>1530, \|eta\|<2.5, same \|deta\|<1.1; exact-1b vs >=1b categories; CMS "inclusive single b" != 1b+2b | CMS wide jets (R=1.1), DeepJet + SF, 2016 legacy JEC; student AK4 CHS, no SF, UL JEC | detector-level counts vs dsigma/dm (not unfolded) | events vs fb/GeV | shape, absolute |
| Z' efficiency vs mass                                             | EXO-20-008 Figure 2                                              | 13 TeV, MC                | -                                              | CMS m_jj>1530, student >1058; 2016-2018 average                                                                | wide jets; student narrow Z' Open Data MC, no SF                                     | MC efficiency vs acceptance x efficiency          | fraction         | trend           |
| inclusive m_jj                                                    | EXO-16-056 (1676214)                                             | 13 TeV, 2016              | 16.39 / 35.9                                   | CMS \|deta\|<1.3, m_jj>1246                                                                                    | wide jets                                                                            | detector-level                                    | events, pb/TeV   | shape, absolute |
| peaks                                                             | PDG                                                              | -                         | -                                              | loose ID, pT>3 GeV, no corrections                                                                             | -                                                                                    | detector-level                                    | GeV              | exact           |
| Upsilon ratios                                                    | BPH-15-005 (1633431)                                             | 13 TeV 2015 vs 2016H      | 2 files, none / 2.7 fb^-1                      | CMS: Upsilon dimuon HLT (pT>7.9, \|y\|<1.25, vertex), muon pT>4.5/4.0, \|y\|<1.2; student: DoubleMuon PD OR    | no A x eps correction, no bending/vertex cut                                         | fitted yields vs corrected sigma B                | ratio            | ratio           |
| Z pT, \|y\|                                                       | SMP-17-010 (1753680)                                             | 13 TeV 2016               | 2 files / 35.9                                 | CMS: 2 isolated muons pT>25, \|eta\|<2.4, \|m-91.19\|<15; student: loose, pT>3, 81-101                         | dressed leptons, unfolded                                                            | detector vs unfolded, normalised                  | fractions        | shape           |
| Z mass                                                            | SMP-17-001 (1711625)                                             | 13 TeV 2015 vs 2016H      | 2 files / 2.8 fb^-1                            | fiducial pT>22/10, \|eta\|<2.4                                                                                 | post-FSR (no FSR corr.), unfolded, efficiency corrected                              | detector vs unfolded fiducial                     | pb/GeV vs counts | shape           |

Traps checked: CMS-EXO-16-057 is the 8 TeV search (not used). CMS-MUO-16-001 has no HEPData record (not used). The ins1920627 tables carry `LUMINOSITY = 138 fb^-1`, but the tables are normalised
to **36.3 fb^-1** (N = (value/error)^2 and L = N/(value x width) give a median of 36.34-36.38 fb^-1 in all four 2016 tables (bin-to-bin scatter from the rounding of the tabulated values in sparsely populated bins); the paper's Fig. 3 labels 2016 with 36.3 fb^-1).
Wide jets are not AK4 jets. ins1753680 Figure 14 is the _combined dimuon + dielectron_ result and its covariance tables are for the _absolute dimuon_ cross sections (see M3).

---

## D1: exact constants (CONSISTENT)

D1a. `deepJet_wp_values` of `2016postVFP_UL/btagging.json.gz` (CVMFS BTV POG) = student L/M/T = 0.048 / 0.2489 / 0.6377, difference 0. The preVFP values (0.0508 / 0.2598 / 0.6502) differ, so the era choice matters; Run2016G,H are postVFP.
Caveat: the student's code reads the same json, so this verifies the era and the value, not independent knowledge.
D1b. Open Data record 1059: Run2016G recorded 7.653261 + Run2016H 8.740119 = **16.393381 fb^-1**; recomputed from `pp_2016lumibyls.csv` + golden JSON: identical; student 16.392692 fb^-1 (ratio - 1 = -4.2e-5, record uncertainty 1.2 %).
The student's processed lumisections number 90126 of 90526 in the published tables (0.4 %), consistent with the lumi match. The csv header says "Norm tag: None" but the sums agree with the composite-normtag totals.
Verdict CONSISTENT. (Dataset completeness: JetHT 2016G NANOAOD has 70 files / 120.7 M events in the Open Data record; the student's 142 files are G+H in full.)

## D2: m_jj shapes against EXO-20-008, 2016 (shape, detector-level; 3 of 4 CONSISTENT, one TENSION)

Plots: `plots/D2a_2b_shape_vs_EXO20008`, `D2b_ge1b_shape_vs_EXO20008`, `D2b2_ge1b_shape_vs_EXO20008_1bplus2b`, `D2c_excl1b_shape_vs_EXO20008` (PNG/PDF).
Common range 1530-7589 GeV (above both thresholds; the CMS lower edge), CMS bins reconstructed from the bin centres with the standard CMS dijet binning, high bins merged until >= 20 events in both. Counts of CMS from (value/error)^2.

| Test                                     | N student / N CMS (effective) | chi2/ndf | p     | ratio slope per TeV | mean ratio     |
| ---------------------------------------- | ----------------------------- | -------- | ----- | ------------------- | -------------- |
| 2b vs double b                           | 16 659 / 38 186               | 22.3/23  | 0.50  | -0.000 +- 0.023     | 0.997 +- 0.009 |
| >=1b vs inclusive single b (row 4)       | 157 369 / 485 868             | 38.7/28  | 0.086 | **+0.034 +- 0.008** | 1.000 +- 0.003 |
| >=1b vs single b + double b (rows 1 + 2) | 157 369 / 417 464             | 24.9/28  | 0.63  | +0.015 +- 0.008     | 1.000 +- 0.003 |
| exactly 1b vs single b (row 2)           | 140 710 / 379 279             | 19.8/28  | 0.87  | +0.009 +- 0.009     | 1.000 +- 0.003 |

The student's >=1b category (includes 2b) has no exact HEPData counterpart. The table named "inclusive single b" is **not** the sum of the single-b and double-b tables: its ratio to their sum is 1.166 at 1.5 TeV falling to 1.08 at 4 TeV
(the paper text says the b\* category is "at least one b-tagged jet"); the record does not explain the difference. Against that table the student shows a 4.2 sigma linear trend (verdict TENSION); against 1b + 2b there is none.
Statistics only; CMS uses wide jets, \|eta\|<2.5, scale factors, and a different JEC. Shapes agree to a few per cent over a decade in cross section. Explanation of the TENSION: the inclusive CMS table contains events beyond 1b + 2b whose fraction falls with mass
(unknown tagging definition), not a student problem as far as can be told.

## D3: absolute dsigma/dm = N/(L dm) (2b CONSISTENT; categories with one b tag INCONSISTENT)

Plots: `plots/D3_dsigma_dm_vs_EXO20008`, `D3c_btag_fraction_ratio`. Student: N/(16.393 fb^-1 x width) in fb/GeV; CMS: fb/GeV (same units). Ratio of integrated yields over bins with >= 20 events in both:

| Category                    | Student / CMS | stat. error | slope per TeV   | assumed envelope | significance (with envelope) |
| --------------------------- | ------------- | ----------- | --------------- | ---------------- | ---------------------------- |
| 2b vs double b              | **0.968**     | 0.009       | -0.005 +- 0.024 | 5.6 % (k = 5.3)  | 0.6 sigma                    |
| >=1b vs inclusive single b  | **0.719**     | 0.002       | +0.026 +- 0.006 | 6.3 %            | 6.2 sigma                    |
| >=1b vs single b + double b | **0.836**     | 0.003       | +0.012 +- 0.007 | 6.3 %            | 3.1 sigma                    |
| exactly 1b vs single b      | **0.823**     | 0.003       | +0.006 +- 0.007 | 6.3 %            | 3.4 sigma                    |

Which differences explain it? Same \|deta\|<1.1 in both, so the Delta-eta cut does not. Luminosity cancels in a cross section (the table qualifier of 138 fb^-1 is irrelevant; 36.3 fb^-1 was recovered).
\|eta\|<2.5 vs 2.4 gives at most about +5 % for CMS (flat dsigma/deta, my estimate). The tagger is the same algorithm and operating point (DeepJet medium = 1 % light mistag, as the paper says), no SF is needed on data.
**The pattern is the finding**: the ratio is flat in m_jj, but increases with b purity: 0.97 (2b), 0.82 (exactly 1b), 0.84 (>=1b vs 1b + 2b), and 0.65 for the untagged inclusive spectrum (D5b).
Taking the b-tag fraction N_btag/N_inclusive (cancels any flat factor common to all categories; CMS inclusive from EXO-16-056, corrected from \|deta\|<1.3 to <1.1 with the student's own per-bin ratio) the student/CMS ratio is 1.49 +- 0.01 (2b), 1.29 (>=1b vs 1b + 2b), 1.11 (>=1b vs row 4).
So relative to CMS the student has too few events in the less-tagged samples (or too many fully tagged ones) -- see "Disagreements" below. Likely contributors (not separable here): CMS wide-jet and JEC differences, tagger retraining (2016 UL vs the legacy DeepJet used in EXO-20-008), and the different definition of the CMS inclusive category.

## D4: Z' -> bb efficiency vs mass (INCONSISTENT; trend and offsets)

Plot: `plots/D4_zprime_efficiency_vs_mass_EXO20008`. Overlapping masses 1800-5000 GeV (8 points). Mapping: student n_selected/n_generated -> "Preselection efficiency"; event_eff_2b -> "Double b-tagged"; (1b - 2b) -> "Single b-tagged" (exactly one);
event_eff_1b -> sum of both. CMS values carry no uncertainty (3 digits); student errors are binomial (<= 0.002). The statistic is the student/CMS ratio, not a p-value (any p-value is zero).

| Mass (GeV)                               | 1800 | 2000 | 2500 | 3000 | 3500 | 4000 | 4500 | 5000 |
| ---------------------------------------- | ---- | ---- | ---- | ---- | ---- | ---- | ---- | ---- |
| acceptance, student/CMS                  | 1.55 | 1.32 | 1.20 | 1.18 | 1.17 | 1.19 | 1.18 | 1.19 |
| 2b, student/CMS                          | 1.63 | 1.48 | 1.49 | 1.62 | 1.79 | 2.08 | 2.26 | 2.63 |
| exactly 1b, student/CMS                  | 1.35 | 1.20 | 1.12 | 1.14 | 1.19 | 1.27 | 1.34 | 1.43 |
| 2b given the preselection, student/CMS   | 1.05 | 1.12 | 1.24 | 1.37 | 1.53 | 1.75 | 1.91 | 2.20 |
| >=1b given the preselection, student/CMS | 0.96 | 1.01 | 1.05 | 1.10 | 1.16 | 1.23 | 1.29 | 1.37 |

Two separate effects. (i) Acceptance: the student plateau is 0.42 vs CMS 0.35-0.36 (+18 %); the paper text quotes 41 % for the \|deta\|<1.1 acceptance alone, which matches the student, so the Fig. 2 "preselection efficiency" includes further requirements not documented in the table
(lepton overlap removal, jet ID, ...). At 1800-2000 GeV the CMS m_jj>1530 cut on wide-jet mass bites (0.27-0.32), while the student (m_jj>1058, no wide jets, peak at ~0.9 M) is almost unaffected. (ii) b tagging given the preselection: at 1.8 TeV the two agree (0.96-1.05), but the CMS
efficiency falls faster with mass: student/CMS grows to 1.37 (>=1b) and 2.2 (2b) at 5 TeV. The paper text quotes the per-jet efficiency 75/45/10 % at jet pT 0.2/1/3 TeV; the student's per-jet DeepJet-M efficiency for true b jets is 0.72 at M = 2 TeV and 0.67 at 2.5 TeV (jet pT about 1 TeV), clearly higher than 45 %
(indicative only, text values, `D4d_per_jet`: NOT COMPARABLE). Likely reasons: CMS efficiencies include data/MC scale factors (and are an average over 2016-2018 with different DeepJet versions), the student's are raw UL MC; the Z' models also differ. I could not separate these.

## D5: inclusive m_jj against EXO-16-056 (shape CONSISTENT, absolute INCONSISTENT)

Plots: `plots/D5_inclusive_mjj_vs_EXO16056`, `D5b_inclusive_absolute_ratio_vs_EXO16056`, `D5c_rate_per_fb_vs_run`. Feasible within memory: the six data skims were streamed one at a time (peak 0.8 GB, 17 s). The rebuilt 2b spectrum equals the student's HEPData exactly; the rebuilt >=1b differs by 2 and 5 events in the two lowest bins
(the student's HEPData record is rounded to 5 significant digits: 191092 -> 191090, 150725 -> 150720); total inclusive events 3 512 934 = `summary.json`.
CMS table: event yields (integers) and cross sections in pb/TeV (L = 35.90 fb^-1 recovered; qualifiers absent), 45 bins from 1246 GeV, same binning as the student.

- **Shape (D5): chi2/ndf = 43.2/34, p = 0.13, slope -0.006 +- 0.003 per TeV, range 1246-8152 GeV, N student 1.49 M, N CMS 6.49 M.** With the CMS cut \|deta\|<1.3 applied to the student's own events: 36.8/34 (p 0.34), slope -0.003 +- 0.003. CONSISTENT. A mass-scale factor fitted on the shape alone is 0.995 +- 0.005, i.e. no sign of a wide-jet mass shift in the normalised shape.
- **Absolute (D5b): ratio 0.505**; the \|deta\|<1.1 to <1.3 acceptance factor measured in the student's data is 0.776, leaving **0.650** with the same cut. The ratio is flat to 0.2 % per TeV (0.65 in every merged bin from 1.2 to 4 TeV), so it is not a wide-jet or mass-scale effect (a mass-scale-only fit needs s = 1.083 and leaves deviance 846 for 35 bins).
  Events per recorded fb^-1 (m_jj>1530, \|deta\|<1.3) are the same in G (38 617) and H (37 782), run-to-run rms 2.4 %: no lost runs or prescale change. A check of the leading-jet logic on one file (240 events for four variants of jet ID and |eta| handling) excludes the selection code as the origin. Cause not identified; INCONSISTENT.

## M1: peak positions and widths against PDG (INCONSISTENT formally; size as expected)

Plots: `plots/M1a_peak_fits`, `M1b_offset_and_resolution_vs_PDG`. Fits to the student's unchanged histograms (Poisson likelihood; Crystal Ball core + wide Gaussian per resonance; Z: Breit-Wigner with PDG width convolved with the same response; exp-polynomial background); variations of CB tail, background order and fit range give the fit systematic
(variants that ran into parameter limits excluded). Deviance/ndf: J/psi region 375/147, Upsilon 104/105, Z 298/51 (imperfect; the J/psi and Z shapes are not captured at the percent level, hence the quoted fit systematics).
PDG 2026 via the PDG API (M070, M071, M049, M052, M048, S044).

| State       | PDG (GeV) | fit (GeV) | offset (per mille) stat / fit syst | sigma_eff (MeV) / % | significance |
| ----------- | --------- | --------- | ---------------------------------- | ------------------- | ------------ |
| J/psi       | 3.0969    | 3.0938    | -0.99 +- 0.05 +- 1.10              | 38 / 1.24           | 0.9          |
| psi(2S)     | 3.6861    | 3.6837    | -0.66 +- 0.20 +- 0.65              | 40 / 1.09           | 1.0          |
| Upsilon(1S) | 9.4604    | 9.4469    | -1.43 +- 0.11 +- 0.11              | 128 / 1.36          | 9.2          |
| Upsilon(2S) | 10.0234   | 10.0122   | -1.11 +- 0.23 +- 0.16              | 133 / 1.32          | 3.9          |
| Upsilon(3S) | 10.3551   | 10.3482   | -0.66 +- 0.29 +- 0.05              | 130 / 1.26          | 2.2          |
| Z           | 91.1879   | 90.992    | -2.15 +- 0.17 +- 1.94              | 1170 / 1.29         | 1.1          |

All six offsets are negative, between -0.7 and -2.2 per mille: a common-sign mass-scale shift. Verdict INCONSISTENT by the stated rule (Upsilon(1S) and (2S) > 3 sigma with tiny uncertainties), but the size is what one expects for uncorrected tracker momentum scale (the corrections applied in CMS analyses
are of the order 0.1-0.2 % on dimuon masses; I did not re-measure them here) and the Z value also absorbs the FSR tail. The resolutions (1.1-1.4 % of the mass for the effective width, Z 1.17 GeV) are in the range expected from the muon pT resolution of 1 % (barrel) to < 3 % (endcaps) quoted in SMP-17-010 (dimuon mass resolution = pT resolution / sqrt 2 per muon pair, mixed barrel/endcap sample).
No evidence of anything beyond the missing momentum corrections.

## M2: Upsilon yield ratios against BPH-15-005 (CONSISTENT)

Plot: `plots/M2_upsilon_ratios_vs_BPH15005`. Rerun of the student's selection on the same 2 files with |y(mu mu)| < 1.2, pT groups 20-24, 24-28, 28-32, 32-40, 40-50, 50-70, 70-130 GeV and the BPH-15-005 offline muon kinematics
(pT > 4.5 GeV for |eta| < 0.3, > 4.0 for 0.3-1.4); fit of three resonances with shared shape, mass scale common, width tied to the mass (Upsilon(1S) yields 10 k in 20-130 GeV). The CMS ratio of a group is built from Tables 3, 4, 5 (0.0-1.2 column; Table 12 gives the per-bin errors; note Table 12's unit "PCT" is wrong, the values are ratios).

| Ratio | student/CMS mean | chi2/ndf (stat + CMS stat + syst, no A x eps term) | with 5 % assumed A x eps-ratio uncertainty | first group (20-24) / last |
| ----- | ---------------- | -------------------------------------------------- | ------------------------------------------ | -------------------------- |
| 2S/1S | 1.017 +- 0.045   | 1.2/7                                              | 1.1/7 (p 0.99)                             | 1.20 / 0.98                |
| 3S/1S | 1.021 +- 0.053   | 4.4/7                                              | 3.8/7 (p 0.80)                             | 1.32 / 1.11                |

Example: 28-32 GeV, 2S/1S 0.473 +- 0.019 vs CMS 0.467 +- 0.011 +- 0.033. The lowest pT group (20-24 GeV) is 1.2-1.3 high but with 15-25 % errors. The low chi2 reflects CMS systematics (fully correlated across bins) entering as uncorrelated errors, i.e. the test is conservative.
Differences not corrected: trigger (student: OR of DoubleMuon-PD dimuon paths; BPH: dedicated Upsilon HLT, pT > 7.9 GeV, vertex probability, muons bending away from each other), no acceptance x efficiency (ratio expected ~1 at pT > 20 GeV, assumed 5 %), 2015 (13 TeV, CMS) vs 2016H. The student selection variant without BPH muon kinematics gives the same result (1.020 / 1.033).

## M3: Z pT and |y| against SMP-17-010 (INCONSISTENT, detector level vs unfolded; mostly acceptance)

Plots: `plots/M3a_Z_pT_vs_SMP17010`, `M3b_Z_absy_vs_SMP17010`, `M3c_Z_pT_selection_variants`, `M3d_Z_absy_selection_variants`.
Which tables: Figure 14a/14c are the **combined** dimuon + dielectron normalised result and, despite "normalized", their values sum to 1 over unequal bins (per-GeV values normalised to their sum). The covariance tables (Cov. Matrix auxiliary Fig. 1a/1c, dressed) belong to the **absolute dimuon** cross sections (Figure 6/5, "Dimuon cross section (pb)", sum of sigma x width = 692.6 pb vs 694 pb in the paper).
The derived dimuon-only normalised fractions agree with the converted Figure 14a within 3.2 % (bins with > 0.1 % of events) and with Figure 14c within 2.1 %. The normalised covariance is derived by linear propagation (luminosity cancels); the student's multinomial covariance is added; chi2 drops one bin for the sum constraint.
Student: win_pt / win_y "z" (81-101 GeV window, loose ID, pT > 3 GeV, no isolation), unchanged; pT common edges up to 52 GeV (14 bins), |y| folded to 12 bins of 0.2.

| Selection                                                     | pT chi2/ndf (0-120 GeV unless noted)                                      | \|y\| chi2/ndf                                              |
| ------------------------------------------------------------- | ------------------------------------------------------------------------- | ----------------------------------------------------------- |
| student histogram (0-52 GeV, 14 bins)                         | 1128/13 (p < 1e-200); ratio 0.85 at 0-2 GeV, ~1.0 at 10-16, 1.16 at 32-52 | 3454/11; ratio 1.13 at \|y\|<0.2 falling to 0.80 at 2.2-2.4 |
| student selection, CMS binning (rerun)                        | 1319/26                                                                   | 3454/11                                                     |
| + window 76.2-106.2 GeV                                       | 1717/26                                                                   | 3856/11                                                     |
| + both muons pT > 25 GeV, \|eta\| < 2.4 (SMP-17-010 fiducial) | **217/26**                                                                | **31.7/11**                                                 |
| + tight ID, PF iso < 0.15 (my generic choice)                 | **166/26**                                                                | 176/11                                                      |

Interpretation: acceptance (muon pT > 3 vs > 25 GeV and \|eta\| < 2.4 at both muons) explains almost all of the \|y\| disagreement (chi2 3454 -> 32, ratio within a few per cent) and most of the pT disagreement (1319 -> 217): the student's low muon-pT threshold admits events with large \|y\| and with larger Z pT relative to the CMS fiducial sample.
Adding ID and isolation helps the pT but worsens the \|y\| (isolation/ID efficiency depends on \|eta\|, not corrected). What remains (chi2/ndf about 6-8 for pT with CMS errors of 0.3-1 % per bin) is not removed by resolution as I could model it: Gaussian smearing of the CMS distribution with sigma = 0.5-1.5 GeV (1-D approximation, my assumption)
raises chi2 (217 -> 559 for 0.5 GeV) instead of lowering it, so I cannot attribute the remainder to resolution; candidates are the unmeasured pT dependence of trigger/ID efficiency, FSR (dressed vs undressed), and the missing efficiency corrections. After the fiducial cuts the \|y\| chi2/ndf is 2.9.

## M4: Z mass shape against SMP-17-001 Table 5 (INCONSISTENT)

Plot: `plots/M4_Z_massshape_vs_SMP17001`. Fiducial region read from the paper: leading pT > 22, subleading > 10 GeV, \|eta\| < 2.4, opposite charge; Table 5 is dimuon fiducial dsigma/dm (pb/GeV), no FSR correction, unfolded for detector resolution and corrected for efficiency, 2015 data; errors stat and exp (no covariance for the fiducial result:
treated uncorrelated, conservative). Student re-run on the same 2 files (closure with the delivered histograms exact: max diff 0), 1 GeV bins merged into the 13 CMS bins 60-120 GeV, both normalised to 60-120 GeV.

| Variant                                   | N       | chi2/ndf (CMS stat (+) exp) | chi2 with CMS stat only |
| ----------------------------------------- | ------- | --------------------------- | ----------------------- |
| student histogram unchanged               | 706 184 | 4077/12                     | 22 620                  |
| + pT > 22/10, \|eta\| < 2.4 (**primary**) | 675 132 | **2440/12**                 | 15 447                  |
| + tight ID and PF iso < 0.15              | 522 098 | 239/12                      | 3 228                   |

Ratio student/CMS per bin (primary): 2.13, 1.87, 1.64, 1.45 (60-76 GeV), 1.22, 1.19, 0.98, 0.84 (peak bin 91-96), 1.22, 1.22, 1.34, 1.49, 1.62 (96-120 GeV). With ID and isolation: 0.82 below 76 GeV, 1.12/1.06 at 81-91, 0.92 in the peak bin, 1.25 at 96-101, 1.1-1.2 above.
Understanding: (i) without ID/iso the low and high mass sides are dominated by non-Z dimuons (QCD, heavy flavour, tt) and are 1.5-2 times CMS; (ii) the pattern at the peak (86-91 up, 91-96 down, 96-101 up) is the signature of detector resolution plus the negative mass-scale offset found in M1; the Breit-Wigner folded with the measured response predicts +13 % at 81-86, -5 % at 91-96 and +16 % at 96-101 GeV, and correcting the ID+iso variant for it reduces the chi2 only from 239 to 178; (iii) the 0.82 deficit at 60-76 GeV is not explained (efficiency vs mass, FSR; 2015 vs 2016 conditions). Verdict INCONSISTENT.
M4b: Table 3 (full phase space, FSR corrected) is NOT COMPARABLE without acceptance and FSR corrections from simulation.

---

## The three most important disagreements

1. **Absolute normalisation of untagged and weakly tagged dijets (D5b, D3b, D3b-alt, D3c).** The student's inclusive dsigma/dm is 0.65 of EXO-16-056 after matching the \|deta\| cut, flat from 1.2 to 4 TeV and uniform over runs, while the 2-b-tag spectrum is within 3 % of EXO-20-008 and the ratio rises monotonically with b purity (0.65, 0.72/0.84, 0.82, 0.97). Shapes agree everywhere (D2, D5). Not an m_jj-dependent effect (wide jets, JES), not run-dependent, not the jet-ID/|eta| selection logic. Not resolved.
2. **Z' efficiency vs mass (D4).** Student acceptance +18 % above the CMS preselection efficiency at plateau, and the 2b efficiency (given the preselection) deviates from CMS from 1.05 at 1.8 TeV to 2.2 at 5 TeV: the student's DeepJet-medium efficiency at high pT is much higher than the CMS number (no SF, UL vs legacy tagger, MC vs data).
3. **Dimuon distributions are far from the unfolded CMS shapes (M3, M4)**, dominated by acceptance (muon pT > 3 GeV loose, no isolation): matching the SMP-17-010 fiducial cuts brings chi2 for |y| from 3454 to 32 and for pT from 1319 to 217, matching SMP-17-001 plus ID/isolation brings the mass shape from 4077 to 239, but the residual is still far from consistent, and the common-sign mass-scale offset (-0.7 to -2.2 per mille, M1) is visible in the peak bins.

## What the students should do next

- Dijet: (a) report the absolute normalisation discrepancy to the CMS EXO contact and compare events per fb^-1 with a second independent source (e.g. a few files re-processed with the JME-recommended jet ID and with PF jets instead of CHS); check `Flag_*` filters and the HLT OR event by event against the 2016 trigger menu; (b) apply the BTV data/MC scale factors to the MC-based efficiency (D4) and use the same b-tag definition as CMS (exact 1b category plus a muon category), (c) implement wide jets (R = 1.1 recombination) and the CMS |eta| < 2.5 for a like-for-like absolute comparison; (d) round-trip HEPData counts as integers (the 1b record is rounded to 5 digits).
- Dimuon: apply the Rochester (or the analysis-appropriate) momentum corrections before fitting masses; use tight ID + isolation and the SMP-17-010 fiducial cuts for any comparison to the unfolded Z results; add trigger/ID/isolation efficiencies or compare ratios only; compute the luminosity of the 2 files (brilcalc or the lumi csv) to enable absolute comparisons.
- Both: label comparisons as detector-level vs unfolded; keep the closure test (rerun reproduces the delivered histograms exactly) as a CI check.

## Reproduce

```bash
cd validation/dijet-2016/cms-comparison
./run_all.sh <cache dir> '<skims dir>/output_d*.npz' <dimuon demo dir>     # about 12 minutes on cmslpc; HEPData/PDG/Open Data files are downloaded into <cache dir>
```

Individual scripts: `compare_d1_exact.py`, `compare_d2_d3_btag_spectra.py`, `compare_d4_efficiency.py`, `compare_d5_inclusive.py`, `diag_d5_rate_vs_run.py`, `rerun_dimuon.py`, `compare_m1_peaks.py`, `compare_m2_upsilon_ratios.py`, `compare_m3_z_pt_y.py`, `compare_m4_z_massshape.py`, `make_comparison.py`
(all take `--cache <dir>`; D5/diag take `--skims`, dimuon scripts take `--dimuon-dir`). Environment: LCG_109 view. HEPData records are not copied into the repository.
