# Skills used by the cms-results-validator agent (first run, before `cms-results-comparison` exists)

Task: compare two Open Data student analyses (b-tagged dijet 2016G+H, opposite-sign dimuon 2016H) with published CMS results, see
[COMPARISON.md](COMPARISON.md). This file seeds the `cms-results-comparison` skill: it lists what had to be worked out without a skill, with the
exact URLs, YAML structures and traps that worked.

## Which skills were used

| Step                                       | Skill                                                                              | Comment                                                                                                   |
| ------------------------------------------ | ---------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| Reading the student's analyses             | none (Read/Bash)                                                                   | `specification.md`, `summary.json`, HEPData yaml, `SKILLS_USED.md` were enough                            |
| Histograms and plots                       | `cms:hist` conventions (mplhep CMS style, `hep.cms.label("Open Data", data=True)`) | Followed from memory; ratio-panel layout written by hand                                                  |
| Event-level re-run of the dimuon selection | `cms:awkward-array`, `cms:vector-awkward` conventions                              | The student's module was imported (`importlib`) and its `process_chunk` reused for an exact closure check |
| HEPData reading                            | `cms:hepdata` skill is about WRITING records; nothing for reading                  | Everything below was worked out                                                                           |
| Choosing tests, statistics, verdict rules  | none                                                                               | Everything below                                                                                          |

## What I had to work out alone

### 1. Finding and verifying the records

- INSPIRE metadata (works from cmslpc, no key):
  `https://inspirehep.net/api/literature?q=reportnumber:CMS-EXO-20-008&fields=control_number,titles.title,arxiv_eprints,publication_info,report_numbers`
  (JSON: `hits.hits[].metadata`). Report-number search returns **different** records for paper and PAS:
  `CMS-EXO-20-008` -> 2676943 (PRD 108 (2023) 012009, arXiv:2205.01835); `CMS-PAS-EXO-20-008` -> 1920627 (no journal). HEPData is attached to the PAS (ins1920627).
  Others verified: EXO-16-056 -> 1676214; SMP-17-001 -> 1711625; SMP-17-010 -> 1753680; BPH-15-005 -> 1633431.
- HEPData whole record: `https://www.hepdata.net/download/submission/ins<INSPIRE>/1/yaml`. **The file is a gzipped tar although the name says zip**:
  `mv rec.zip rec.tar.gz; tar xzf rec.tar.gz` gives `HEPData-ins<N>-v1-yaml/{submission.yaml, *.yaml}`. Python: `tarfile.open(f).extractall(dir, filter="data")`.
- `submission.yaml` is a multi-document YAML: first document is the record abstract, then one document per table with `name`, `description`, `data_file`, `keywords`.
  Table names are human strings ("Figure 3 first row first column"), file names are lower-case/underscore. Map name -> `data_file` through `submission.yaml`, do not guess file names.
- Table yaml: `independent_variables[i] = {header:{name,units}, values:[{low,high} | {value}]}`; `dependent_variables[j] = {header, qualifiers, values:[{value, errors:[{label, symerror | asymerror:{plus,minus}}]}]}`.
  Errors may be strings with percent (`'1.7%'`, BPH-15-005): convert with the value. Zero-count bins may be stored as a tiny negative number (`-1.77e-08`) with error `1.77e-10`.
- Papers for text-only facts (selection, lumi per year, fiducial cuts): `https://arxiv.org/pdf/<id>` then `pdftotext -layout`. Needed because HEPData does not carry cuts.
- PDG masses: `https://pdgapi.lbl.gov/summaries/<PDGID>` (edition 2026); IDs worked out by scanning: J/psi M070, psi(2S) M071, Upsilon(1S) M049, (2S) M052, (3S) M048, Z S044
  (`summaries.properties[].pdgid == '<id>M'`, value in MeV, Z in GeV via `S044M`, width `S044W`). `M068`, `M061`, `M062` are NOT the psi(2S)/Upsilons.
- Open Data luminosity: `https://opendata.cern.ch/record/1059/files/Run2016Glumi.txt` (and `Run2016Hlumi.txt`, `pp_2016lumibyls.csv`), golden JSON
  `https://opendata.cern.ch/record/14220/files/Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt`. The last `|`-row of `Run2016G/Hlumi.txt` holds the totals
  (delivered, recorded in /fb). `pp_2016lumibyls.csv` header says "Norm tag: None"; the sums still agree with the composite-normtag totals to 4e-5.
- BTV POG working points: `/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/BTV/2016postVFP_UL/btagging.json.gz`, `correctionlib`, `cs["deepJet_wp_values"].evaluate("M")`.
  postVFP M = 0.2489, preVFP M = 0.2598.
- Dataset completeness: `https://opendata.cern.ch/api/records/?q=<dataset name>` -> `metadata.distribution.number_events/number_files`.

### 2. Traps in the HEPData records (each cost time)

- **ins1920627 `LUMINOSITY: 138` qualifier on the 2016 tables is wrong for normalisation.** `N = (value/err)^2` (Poisson errors) and `L = N/(value * bin width)` give 36.3 fb^-1
  in every bin (36.3 fb^-1 is the 2016 value in Fig. 3 of the paper). Use this "recover N and L from Poisson errors" trick for every CMS spectrum with Poisson errors
  (counts come out as integers to < 0.25 sqrt(N); EXO-16-056 gives the yield directly and L = 35.9 fb^-1).
- **Bin edges are missing** (only centres) in ins1920627 Fig. 3 and Fig. 2. Recover them from the standard CMS dijet binning: edge pair with (lo+hi)/2 == centre (atol 0.01). It matched in all 39 bins.
- **'Inclusive single b' (row 4) is not the sum of single-b (row 2) and double-b (row 1)**: ratio 1.17 at 1.5 TeV falling to 1.08 at 4 TeV. The paper text says the b\* category is "at least one b tag".
  Always test sums of categories before choosing the counterpart of an inclusive student category; compare against both.
- The paper's single-b category is EXACTLY one b tag (Fig. 2 "total = 1b + 2b + muon"), the student's `1b` is >= 1 b tag. Build exclusive 1b = (>=1b) - 2b for the like-for-like test.
- **ins1753680 Fig. 14a/14c ("Normalized dilepton cross section") are the COMBINED dimuon+dielectron and are not fractions or densities**: the values sum to 1 over bins of UNEQUAL width
  (v_i = (dsigma/dpT)\_i / sum_j (dsigma/dpT)\_j). Convert with the widths before using. Always compute `sum(v)` and `sum(v*w)` of a "normalized" table.
- **The covariance tables of ins1753680 ("Covariance Matrix auxiliary Figure 1a/1c") are for the ABSOLUTE DIMUON cross sections in pb/GeV and pb** (diag sqrt = 2.5% lumi-dominated),
  not for the normalised values (check: `sqrt(diag)` equals the symerror of the dimuon column of Figure 6/5, and is ~1200x the Fig. 14 errors). They have 36x36 = 1296 (pT) or 12x12 (|y|) entries in `Bin X`/`Bin Y` order;
  `reshape(n, n)`. Derive the normalised covariance by linear error propagation (the lumi part cancels). The bin edges are not given: centres only; edges recovered (0..14 in 1 GeV, 16, 18, 20, 22, 25, 28, 32, 37, 43, 52, 65, 85, 120, 160, 190, 220, 250, 300, 400, 500, 800, 1500).
- ins1633431 Table 12 header unit is `PCT` but the values are plain ratios (0.42 = Upsilon(2S)/Upsilon(1S)); errors are strings `'1.7%'`; values have 2 digits, so the ratio of Tables 4/3 (3 digits) is a better central value.
- SMP-17-001 Table 5 (fiducial, no FSR correction) and Table 3 (full phase space, FSR-corrected) have the same 43 mass bins, units pb/GeV, errors `$\delta_{stat}$`, `$\delta_{exp}$` as `symerror`; no covariance for the fiducial table (Tables 8-10 are for the FSR-corrected full-phase-space result).
- `read_table` helper (in `common.py`) handles all of these: name -> file through `submission.yaml`, `low/high` vs `value`, percent strings, `asymerror`.

### 3. Matching bins and units

- Student `dsigma/dm = N/(L dm)` in fb/GeV; CMS HEPData fb/GeV for EXO-20-008, pb/TeV for EXO-16-056 (1 pb/TeV = 1 fb/GeV). Both use the same CMS dijet bins, so no rebinning was needed;
  high-mass bins were merged from the top until every merged bin has >= 20 events in both (`common.merge_high_bins`).
- Shape test between two count histograms: two-sample Pearson chi2 `sum (sqrt(N2/N1) n1 - sqrt(N1/N2) n2)^2/(n1+n2)`, ndf = nbins-1. For the ratio plot take `r = p_S/p_C` of unit-normalised histograms and fit `r = a + b (m - <m>)`; `b` is the "slope of the ratio".
- Student rapidity histograms are signed, CMS uses |y|: fold. Student pT bins are 2 GeV, CMS bins are irregular: only edges present in both can be used (here up to 52 GeV); the re-run with CMS edges removes this limit.
- Spectra between 2015, 2016 and 2016G+H data: only the shape is comparable; for cross sections the luminosity cancels but JES/wide-jet/tagger differences (see COMPARISON.md) are assumed as a stated envelope.

### 4. Choosing the tests

- Exact: constants and totals (WPs, lumi, PDG masses). Shape: normalised in a common range, chi2 + slope. Absolute: only with an explicit systematic envelope (here lumi 1.2%+1.2% and 1% mass scale times the local spectrum index k, my assumption).
- A **closure check on every re-run** (the re-run with the student's selection must reproduce the student's histograms exactly: `max|diff| = 0`) is cheap and catches environment drift.
- When the disagreement is a flat factor, check run-by-run event rates per fb^-1 (`diag_d5_rate_vs_run.py`) and the b-tag-purity pattern (ratio rises with b purity) before suggesting a cause.
- The re-run of the dimuon selection takes 40 s for the 2 files over XRootD (`uproot.iterate(step_size=500_000)` with an integer step; the student already found that a byte-size step fails).

### 5. Environment notes

- LCG_109 has `correctionlib`, `iminuit`, `hist`, `mplhep`, `uproot`, XRootD python bindings, `typer`. `python3 -I` ignores `PYTHONPATH`, so it cannot be used with the LCG view.
- Importing student code creates `__pycache__` in the student's directory: set `sys.dont_write_bytecode = True` before the import (I created and removed two such directories before I noticed).
- `pkill -f <script>` inside the same shell command kills your own shell (exit 144): use a PID from `ps`.
- Long fits with numerical Breit-Wigner convolution: 0.2 GeV grid, ~8 minutes total for the Z fit with variations. Run in the background with `nohup`.

## What was missing or wrong in the skills the student used (observations)

- The `hepdata` skill covers writing only; the student's `1b` HEPData table is rounded to 5 significant digits (191092 -> 191090, 150725 -> 150720 in the two lowest bins); counts should be integers.
- None of the student-side skills record which jets/trigger bits are used with which luminosity; this review had to read `skim.py` to confirm the leading-jet logic (two leading tight-ID jets over all |eta|, then |eta|<2.4; checked on one file that this does not change the yield: 240 events in all variants).
