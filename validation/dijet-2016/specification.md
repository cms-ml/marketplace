# B-tagged high-mass dijet resonance search, 2016 CMS Open Data (tool validation)

Reproduce the plot set of the b-tagged dijet resonance search (APS lightning talk by A. Mankel, 10 March 2026, CMS B2G; published Run 2 analysis CMS-EXO-20-008) with 2016G+H JetHT NanoAODv9. This is an Open Data tool validation, not a CMS result: no physics claim, plots labelled "CMS Open Data".

## Data Samples

| Dataset (DAS name or Open Data path)                                                                                                                | Tier       | Era / campaign             | Role(s) in analysis                                                                                                             |
| --------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| `/eos/opendata/cms/Run2016G/JetHT/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/` (70 files, DAS `/JetHT/Run2016G-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD`)   | NANOAOD    | Run2016G (postVFP)         | Data                                                                                                                            |
| `/eos/opendata/cms/Run2016H/JetHT/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/` (72 files, DAS `/JetHT/Run2016H-UL2016_MiniAODv2_NanoAODv9-v1/NANOAOD`)   | NANOAOD    | Run2016H (postVFP)         | Data                                                                                                                            |
| `/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/ZprimeToBB_narrow_M-<M>_TuneCP5_13TeV-madgraph-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v2/`  | NANOAODSIM | RunIISummer20UL16NanoAODv9 | Signal, M = 500 to 5000 GeV (15 points) skimmed; M >= 1000 GeV used (lower masses are truncated by the skim cut m_jj > 800 GeV) |
| `/eos/opendata/cms/mc/RunIISummer20UL16NanoAODv9/QCD_HT<bin>_TuneCP5_PSWeights_13TeV-madgraphMLM-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/` | NANOAODSIM | RunIISummer20UL16NanoAODv9 | Background (data/MC comparison only), HT bins 700to1000, 1000to1500, 1500to2000, 2000toInf                                      |

- Data and MC are 2016 postVFP (G, H and the `RunIISummer20UL16NanoAODv9` campaign, i.e. not the `...APVv9` preVFP one), consistent with the 2016postVFP_UL b-tag working points.
- Luminosity / certification: Golden JSON `Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt` (Open Data record 14220, `/eos/opendata/cms/validated-runs/2016/`). Luminosity per lumi section from `pp_2016lumibyls.csv` (Open Data record 1059), recorded column, summed over the (run, lumi) pairs that were actually processed and are in the JSON. Uncertainty 1.2% (record 1059, not propagated here).
- Triggers (signal): OR of `HLT_PFHT900`, `HLT_PFHT800`, `HLT_PFJet450`, `HLT_PFJet500`, `HLT_CaloJet500_NoJetID`, `HLT_AK8PFJet450`, `HLT_AK8PFJet500` (none prescaled; `HLT_PFHT800` is absent from the Run2016H files, so the OR uses the paths present in each file). The `WideJetMJJ` paths are not used (their dEta cut differs from the analysis one).
- Triggers (reference for efficiency): prescaled `HLT_PFJet260` (main), `HLT_PFHT475` and `HLT_PFJet400` (cross-checks). The reference is orthogonal to the signal-trigger decision only in the sense that it is a lower-threshold path of the same dataset, which is the standard CMS procedure; the bias is discussed in the summary.
- MC normalisation: weight = `genWeight x sigma x L / sum(Runs/genEventSumw)` per HT bin. QCD sigma (pb), GenXsecAnalyzer values from the Open Data MINIAODSIM records (no K factor): HT700to1000 6425 (rec. 63139), HT1000to1500 1117 (63078), HT1500to2000 108.3 (63094), HT2000toInf 21.94 (63102). Sum of weights is taken over the files actually processed, L is the luminosity of the data subset actually processed (so partial runs stay self-consistent). The Z' narrow samples have no cross section in the records: signal is normalised to an assumed sigma x B = 1 pb (arbitrary, stated on every plot where used).
- Environment: LCG_109 view (Python 3.13, iminuit 2.31, uproot 5.6, awkward 2.8, hist, mplhep, hepdata_lib, hepdata-validator). It replaces the "pip/uv environment with a new iminuit" requirement: it gives modern iminuit and also works on condor workers.

## Histograms

Categories: `1b` = at least one of the two selected jets passes DeepJet Medium; `2b` = both pass Medium. `incl` = no b-tag requirement (used for the trigger and shape checks only). `1b` includes `2b` (as in the reference). Selections below are "full selection": trigger, m_jj threshold, jets, |Delta eta| < 1.1.

1. |Delta eta(j1,j2)| and eta(j)
   - x: `$|\Delta\eta_{jj}|$` (0 to 2.6) and `$\eta_{j}$` (both jets, -2.4 to 2.4); entries per event: 1 and 2.
   - Selection: trigger, m_jj above the derived threshold, |eta| < 2.4, and no |Delta eta| cut for the first plot (cut line drawn at 1.1); for eta(j) the |Delta eta| cut is applied. Shown for `1b` and `2b`, data and QCD MC, area-normalised shapes.
2. Trigger efficiency vs m_jj
   - x: `$m_{jj}$ [GeV]`, variable CMS dijet binning; y: efficiency of the signal-trigger OR in events passing the reference trigger, jet selection and |Delta eta| < 1.1. Binomial (Clopper-Pearson) uncertainties. Plateau and threshold marked.
3. b-tag efficiency vs Z' mass
   - Per-jet efficiency of Loose/Medium/Tight DeepJet WPs for true b jets (`Jet_hadronFlavour == 5`) among the two selected jets, per Z' mass point. Also event efficiency of `1b` and `2b` at Medium (selected events / generated events).
4. Pseudo-significance vs Z' mass for WP combinations (`2b` category)
   - WP pair (WP of leading jet, WP of sub-leading jet) in {LL, MM, TT, ML, TM, TL} (first = WP applied to the jet with the higher DeepJet score, second = WP applied to the lower-score jet).
   - Window `[max(0.8 M, threshold), 1.05 M]` (the reconstructed peak sits at about 0.9 M because wide-jet FSR recombination is not done), s from MC at sigma x B = 1 fb (small-signal regime, so that the ranking reflects s/sqrt(b) and does not saturate), L = processed luminosity; b from a 3-parameter dijet fit to the data m_jj spectrum of that WP combination (integrated in the window). Z = Asimov `sqrt(2((s+b) ln(1+s/b) - s))`, b floored at 1 event. Best combination = largest sum in quadrature of Z over the mass points.
5. m_jj spectrum: data vs QCD MC with Z' overlays
   - x: `$m_{jj}$ [GeV]`, CMS dijet binning from the threshold; y: events per GeV; data (weight 1) vs QCD (normalised as above) stacked by HT bin, ratio panel, Z' signals (M = 1600, 2000, 3000, 4000 GeV, sigma = 1 pb) overlaid. For `incl`, `1b`, `2b`. No b-tag scale factors and no pileup reweighting are applied to the MC, so only shape (and gross normalisation) is compared.
6. Background fit
   - Data m*jj in `1b` and `2b`, fit function `$p_0 (1-x)^{p_1} / x^{p_2 + p_3 \ln x + p_4 \ln^2 x}$`, `$x = m*{jj}/13000$`, 3, 4 and 5 parameters (p0 counts as a parameter; the 3- and 4-parameter fits fix the higher p_i to 0). Binned Poisson likelihood (iminuit 2.x), chi2 = Poisson deviance, signed-deviance pulls. F-test table for 3 vs 4 and 4 vs 5 parameters; the chosen number of parameters per category is the lowest n with p(F, n to n+1) > 0.05. Z' shapes overlaid (sigma = 1 pb).
7. Signal injection
   - Z' with M = 2000 GeV, MC m_jj shape in each category, injected into the data spectrum at several yields (0, 0.5x, 1x, 2x of a nominal injected yield N_inj ~ 3 sigma of the background in the signal window), refit with background + signal-shape (signal strength free, background function with the chosen number of parameters), compare recovered with injected yield; toy ensemble (Poisson fluctuations) for the bias and pulls.

## Analysis Steps

1. Event selection (data and MC)
   - Skim (on the workers): event cleaning flags `Flag_goodVertices`, `Flag_globalSuperTightHalo2016Filter`, `Flag_HBHENoiseFilter`, `Flag_HBHENoiseIsoFilter`, `Flag_EcalDeadCellTriggerPrimitiveFilter`, `Flag_BadPFMuonFilter`, `Flag_BadPFMuonDzFilter`, `Flag_eeBadScFilter` all true.
   - Jets: AK4 CHS `Jet_*`, with tight jet ID (`Jet_jetId & 2`), `Jet_pt > 30` GeV. Take the two leading (highest `Jet_pt`) such jets; require both |eta| < 2.4 (b-tag acceptance in 2016). Events with fewer than two such jets are dropped. No wide-jet FSR recombination (shortcut, differs from the reference).
   - Skim keeps events with m_jj > 800 GeV; no |Delta eta| cut in the skim.
   - Analysis: Golden JSON (data), |Delta eta_jj| < 1.1 (kept from the reference: suppresses t-channel QCD), signal trigger OR (data only; MC not trigger-emulated, the m_jj threshold is above the plateau), m_jj > threshold.
2. m_jj: invariant mass of the two leading selected jets, four-vectors from `(pt, eta, phi, mass)` (vector). GeV.
3. b tagging: `Jet_btagDeepFlavB` against the 2016postVFP_UL DeepJet working points read from `deepJet_wp_values` in the BTV POG `btagging.json.gz` (Loose 0.048, Medium 0.2489, Tight 0.6377 at the time of writing). Categories as above, defined from the two selected jets only.
4. m_jj threshold: lowest edge of the CMS dijet binning such that every bin above it has a Clopper-Pearson (68%) upper bound >= 99.5% on the signal-trigger efficiency (reference `HLT_PFJet260`) and the pooled efficiency above it is >= 99.5%. The plateau value quoted is the pooled efficiency above the threshold. (question: the reference analysis uses 1455 GeV for Run 3.)

## Corrections and Systematics

None applied (shortcut for a tool validation): no JEC/JER re-derivation (NanoAOD jets are already JEC-corrected), no b-tag data/MC scale factors, no pileup reweighting, no QCD K factor, no systematic uncertainties. Statistical uncertainties only. Listed as open items in the summary.

## Workflow

1. Data Extraction and Skimming (condor, `skim.py` payload)
   - Filtering: event cleaning flags, two leading tight-ID jets with |eta| < 2.4, m_jj > 800 GeV.
   - Branches (data and MC): `run`, `luminosityBlock`, `Jet_pt/eta/phi/mass/jetId/btagDeepFlavB`, `HLT_*` paths listed above, `Flag_*` listed above. MC only: `genWeight`, `Jet_hadronFlavour`, `Runs/genEventSumw`.
   - Output per job: one `.npz` with flat per-event arrays, per-file sum of weights and event counts, and the full list of processed (run, lumi) pairs (data).
   - Outputs on EOS under `/store/user/$USER/cms-marketplace-tests/dijet-2016/` (root://cmseos.fnal.gov), at most 10 condor jobs.
2. Analysis and Histogramming (`analysis.py`, local, reads the `.npz`)
   - Streams the skims one file at a time (pass 1: trigger turn-on and threshold from data; pass 2: events above the threshold, golden JSON and signal trigger applied while loading) because holding all 95M skimmed events exceeds the memory of an interactive cmslpc node (about 6 GB free).
   - Derive threshold, fill hists, fits, injection, plots, `summary.json`, HEPData submission.

## Reproduce

```bash
source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh   # wrap in `set +u`
# 1. file lists (lpc-condor make_filelist.py, one file per line) then jobs.txt (9 jobs: d0-d5 data, q0-q1 QCD, s0 signals)
python3 condor/make_jobs.py <listdir> <data_files.txt> -o condor/jobs.txt
# 2. skim on condor (copy skim.py, condor/job.sh, condor/job.jdl to an NFS dir; set OUTDIR in job.jdl)
condor_submit JOBS=jobs.txt job.jdl      # outputs: root://cmseos.fnal.gov//store/user/$USER/cms-marketplace-tests/dijet-2016/skim/output_<id>.npz
# 3. copy the 9 outputs with xrdcp to a scratch dir, then
python3 analysis.py --skims '<scratch>/skims/*.npz' --outdir . --work <scratch>/cache --toys 200
```

## Statistical Analysis

Binned Poisson-likelihood fits with iminuit (dijet function, 3/4/5 parameters), F-test on the deviance for model selection, background + MC-shape signal fit for the injection test, Asimov pseudo-significance. No limits (no Combine in this validation).

## Tools

- uproot + awkward: read NanoAOD, per-event selection (condor payload).
- vector: dijet four-vector sums.
- correctionlib: DeepJet working-point values.
- hist + mplhep: histograms and CMS-style plots (label "CMS Open Data", sqrt(s) = 13 TeV, luminosity).
- iminuit 2.31: fits.
- hepdata_lib + hepdata-validator: HEPData submission and validation.
- lpc-condor skill templates (`job.sh`, `job.jdl`, `make_filelist.py`, `check_outputs.py`): batch skim.

## Open questions (answered with defaults)

- (question: jet ID tight vs tight-lepton-veto: tight chosen, matching the reference dijet selection.)
- (question: Z' cross section: not available in records, 1 pb assumed.)
- (question: should the QCD HT500to700 bin be included: skipped, negligible at m_jj above the threshold and costs 74 files.)
