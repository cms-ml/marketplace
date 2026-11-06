# Generic working points, MC-statistics uncertainty and correctionlib output (validation of `muon-tag-and-probe`)

Goal: validate the extension of `plugins/cms/skills/muon-tag-and-probe/scripts/tnp.py` from three hard-coded working
points to any NanoAOD muon selection (`--num`, `--den`, `--num-trigger`, `--tag*`), with a bootstrap MC-statistics
uncertainty, optional systematics, an offline mode and correctionlib output. The motivation is a calibration benchmark in
which an agent measures many muon ID and trigger scale factors (SF) on simulated samples, offline, delivers correctionlib
JSON and is scored by pulls, so the uncertainties must cover. The task is in `PROMPT.md`. These are CMS Open Data results,
not CMS results. Counterpart: the CMS Muon POG
`/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/MUO/2016postVFP_UL/muon_Z.json.gz` (late 2016F, G, H);
the previous full validation of `tnp.py` is `validation/muon-tnp/`.

## Inputs

A modest subset, copied to `<scratch>/inputs` (list: `code/input_files.txt`, paths under
`root://eospublic.cern.ch//eos/opendata/cms/`): 2 Run2016G + 2 Run2016H SingleMuon NanoAODv9 files (7.09 M events,
412 k tight-ID tag-probe pairs) and 8 `ZToMuMu_M-50To120` powheg files (1.25 M events, 748 k pairs, MC/data 1.8).
For the MC-statistics test the MC is split by file into half A (`mc0 mc1 mc3 mc4 mc7`) and half B (`mc2 mc8 mc9`).
No golden JSON is applied (as in `tnp.py`); luminosity is not needed for efficiencies. Environment: LCG_109 view
(correctionlib 2.6.4, iminuit, uproot, awkward). Each `tnp.py` run took 22-68 s and at most 2.0 GB; 3 ran in parallel.

## Results

### (a) Preset equivalence

`--wp tightid|tightiso|isomu24` with the new `tnp.py`, the same definitions spelled with
`--den/--num/--num-trigger/--tag/--tag-pt/--tag-trigger/--tag-hlt/--pog` (the tight-ID tag written with `and`), and the
`tnp.py` before this change (commit 337e5b7) give **bit-identical** per-bin results (all 13 legacy fields, 32 + 32 + 26 bins,
max |diff| = 0). The pre-change outputs are stored as `results/pre_change_<wp>.json`; `run_all.sh` uses them if commit
337e5b7 is no longer available (e.g. after a squash merge), and the new presets also equal them bit for bit.

### (b) Working points against the POG

Weighted (inverse total variance) SF/POG over the 30-60 GeV bins, RMS of `pull_total` = (SF - POG)/sqrt(total^2 + POG^2)
over all bins, and the median uncertainties at 30-60 GeV in SF units:

| WP (`--num`, `--den`)                | POG correction                         | SF/POG 30-60 GeV | per abs(eta) bin 0-0.9 / 0.9-1.2 / 1.2-2.1 / 2.1-2.4 | RMS pull | stat   | mc_stat | syst   |
| ------------------------------------ | -------------------------------------- | ---------------- | ---------------------------------------------------- | -------- | ------ | ------- | ------ |
| tight ID (preset)                    | NUM_TightID_DEN_TrackerMuons           | 1.0013           | 1.0035 / 1.0029 / 0.9990 / 0.9993                    | 1.06     | 0.0015 | 0.0009  | 0.0017 |
| tight iso (preset)                   | NUM_TightRelIso_DEN_TightIDandIPCut    | 1.0028           | 1.0025 / 1.0041 / 1.0019 / 1.0063                    | 1.54     | 0.0013 | 0.0011  | 0.0016 |
| IsoMu24 (preset, bit 2)              | NUM*IsoMu24_or_IsoTkMu24_DEN*...       | 1.0073           | 1.0113 / 0.9978 / 0.9974 / 0.9931                    | 2.70     | 0.0023 | 0.0020  | 0.0020 |
| `mediumId` (`isTracker`)             | NUM_MediumID_DEN_TrackerMuons          | 0.9977           | 0.9969 / 1.0009 / 0.9981 / 1.0016                    | 1.69     | 0.0009 | 0.0006  | 0.0012 |
| `looseId` (`isTracker`)              | NUM_LooseID_DEN_TrackerMuons           | 1.0006           | 1.0006 / 1.0015 / 1.0001 / 1.0031                    | 1.39     | 0.0004 | 0.0003  | 0.0004 |
| `highPtId == 2` (`isTracker`)        | NUM_HighPtID_DEN_TrackerMuons          | 1.0006           | 1.0020 / 1.0016 / 0.9992 / 1.0005                    | 0.88     | 0.0012 | 0.0008  | 0.0012 |
| `softId` (`isTracker`)               | NUM_SoftID_DEN_TrackerMuons            | 0.9966           | 0.9958 / 0.9870 / 0.9985 / 1.0014                    | 3.12     | 0.0008 | 0.0005  | 0.0007 |
| `pfRelIso04_all < 0.25` (`mediumId`) | NUM_LooseRelIso_DEN_MediumID           | 1.0004           | 1.0001 / 1.0003 / 1.0001 / 1.0019                    | 1.26     | 0.0008 | 0.0006  | 0.0006 |
| `tkRelIso < 0.1` (`highPtId == 2`)   | NUM_LooseRelTkIso_DEN_HighPtIDandIPCut | 1.0007           | 1.0014 / 1.0013 / 1.0000 / 1.0008                    | 1.22     | 0.0008 | 0.0006  | 0.0009 |

All new working points agree with the POG within 0.3 percent at 30-60 GeV, except soft ID at |eta| 0.9-1.2 (-1.3 percent;
5 of 32 bins above 3 sigma; the barrel is -0.4 percent, 0.9958; an independent review found the same offset with a
fit-free counting method and in G and H separately, cause not found). The IsoMu24 barrel offset (+1.1 percent) is the known open issue of
`validation/muon-tnp/`. The POG uncertainties at 30-60 GeV (0.01-0.3 percent) are often smaller than ours, so a per-mille
offset already gives |pull| of 3-6 (medium ID barrel 40-50 GeV: SF 0.9961 vs POG 0.9993, total 0.0006).
Plots: `plots/sf_over_pog_<wp>` (ours/POG per |eta| bin, total and data-stat errors, POG band) and
`plots/unc_components_<wp>` (stat, mc_stat, syst, total and POG uncertainty per bin).

Without a POG counterpart, offline (`--no-pog --no-pu`, explicit `--pt-edges`; `plots/eff_isomu22`, `eff_mu17leg`):

- **IsoMu22** (`--num-trigger 2:22`, tight ID + tight iso probes): turn-on from 0.02 below 22 GeV to 0.75-0.94 at
  30-120 GeV; SF 0.93-0.99 at 30-120 GeV but 0.53 at |eta| 2.1-2.4, 22-24 GeV. `code/isomu22_check.py`
  (`summary.json` `isomu22_activity`): `HLT_IsoMu22` fired in 0.611 / 0.633 (G1 / G2) and 0.480 / 0.489 (H2 / H4) of the
  `HLT_IsoMu24` events, and in 0.991 of the `HLT_IsoMu24 | HLT_IsoTkMu24` events in MC (1.000 of `HLT_IsoMu24`). Per lumi
  section (at least 5 IsoMu24 events) it fired in more than 95 percent or less than 5 percent of them, never in between: the path
  is switched on and off by lumi section, not randomly prescaled. Bit-2 objects at 22-24 GeV (none above 24 GeV) exist in
  103-227 k events per data file, of which only 0.49-0.63 fired IsoMu22: other Iso-filter paths such as `IsoMu22_eta2p1`
  (fired in 0.905-0.908 of IsoMu24 events, MC 0.915-0.917) set the same bit, but not at |eta| > 2.1, which is why only the
  endcap breaks. A property of the data (the first version of this README quoted 63 / 75 percent: the H number came from the
  first 500 k events of one file and was wrong); a new skill gotcha.
- **Mu17 leg** of `Mu17_TrkIsoVVL_Mu8_TrkIsoVVL` (`--num-trigger 1:17`, bit 1 = TrkIsoVVL): ε_data 0.96-0.99 and
  SF 0.97-1.00 on the plateau (30-120 GeV). The Mu8 leg was not run (it needs probes below 15 GeV).
- An MVA working point (`mvaId >= 2`, no POG counterpart, default binning) ran and wrote a correctionlib file.

### (c) correctionlib

For each of the 7 files written (tight ID, tight iso, IsoMu24, medium ID, loose ID, MVA medium, IsoMu22; copies in
`results/`): it loads with `correctionlib.CorrectionSet.from_file`, `correction validate` gives "All OK", and in every
bin centre of the grid (signed and unsigned η) `nominal` equals the `tnp.py` SF of the bin (or of its source bin, below),
`up` = SF + total, `down` = max(SF - total, 0), `systup`/`systdown` equal `up`/`down`, the quadrature of `stat`, `mc_stat`,
`syst`, `fill` equals the total, and `<name>_eff_data` / `<name>_eff_mc` equal the efficiencies, all to 2.2e-16. Clamping:
η = 3.0 gives the 2.1-2.4 value, pT below the first edge the first bin, pT = 1e5 GeV the last bin. All 7 have `syst` on
(`mvamedium` and `isomu22` through the new default).

**Unreliable and unmeasured bins** (after review). A measured bin is unreliable if its fit is not ok, the data or the
gen-matched MC fail category has fewer than 5 probes, or the SF data-stat error is above 0.1 (`--min-fail`, `--max-sf-stat`).
Its raw numbers stay in the result JSON; the correctionlib file uses the nearest reliable pT bin of the same |eta| row and adds
`fill` = |raw SF - source SF| (for an unmeasured bin, |source - next-nearest reliable bin|), and every filled bin is listed
in the correction descriptions and in `correctionlib_filled_bins`. In the 7 files 1-11 of 28-32 bins are filled (11 for loose ID, whose fail categories are nearly empty). Examples
(raw SF -> written SF ± fill): medium ID |eta| 0.9-1.2, pT > 120 GeV (no failing MC probe) 0.877 ± 0.886 -> 1.002 ± 0.125;
2.1-2.4, pT > 120 GeV 0.769 -> 0.988 ± 0.218; tight iso 2.1-2.4, pT > 120 GeV 0.903 -> 1.003 ± 0.100; IsoMu24 1.2-2.1,
pT > 200 GeV (data fail < 5) 1.081 -> 0.992 ± 0.088. Fits flagged only for "fit not ok" move by at most 0.003. The rule also
flags three of the four sub-threshold IsoMu22 bins (20-22 GeV, SF 0.53-0.69 with stat > 0.1; the fourth, 0.25 ± 0.09, stays) and writes the 22-24 GeV SF there with a
fill of 0.32-0.41: for a turn-on that is a covering but crude value; raise `--max-sf-stat` or start the binning at the
threshold. Before this fix the file carried 0.877 (down -0.009) for medium ID above 120 GeV.

End to end: 24 073 gen-matched medium-ID muons (15 322 events, first 20 000 events of one MC file) weighted with `mediumid`:
mean SF 0.9948 (up 0.9972), range 0.975-1.003 (0.769-1.004 before the fix), mean event weight of two-muon events 0.9901.

### (d) MC-statistics uncertainty

Two independent halves of the MC with the same data; z = (SF_A - SF_B)/sqrt(mc_stat_A^2 + mc_stat_B^2) over the bins where
both fits converged (tight ID, tight iso, IsoMu24, medium ID; `plots/mc_stat_coverage`):

| WP        | bins | RMS z       | RMS z with the binomial MC counting error | mc_stat half/full (expected sqrt(N_full/N_half)) A; B |
| --------- | ---- | ----------- | ----------------------------------------- | ----------------------------------------------------- |
| tight ID  | 30   | 0.98        | 1.27                                      | 1.48 (1.48); 1.38 (1.36)                              |
| tight iso | 30   | 1.07        | 8.77                                      | 1.40 (1.48); 1.25 (1.36)                              |
| IsoMu24   | 22   | 1.07        | 1.17                                      | 1.38 (1.48); 1.26 (1.36)                              |
| medium ID | 29   | 1.02        | 1.37                                      | 1.36 (1.48); 1.22 (1.36)                              |
| all       | 111  | 1.04 ± 0.07 | 4.69                                      |                                                       |

The bootstrap `mc_stat` covers the MC fluctuations (mean z +0.12, 69 percent of |z| < 1, 94 percent < 2), and scales as
1/sqrt(N_MC) to within 0-10 percent (slightly below). The binomial MC counting error used before
(`eff_mc_err`, kept as the legacy `sf_err`) undercovers, by a factor 8.8 for tight isolation, because it ignores the MC
templates of the data fit.

**Not covered: a finite-MC bias.** (SF_A + SF_B)/2 - SF_full would be zero for an estimator linear in the MC. It is
+0.0035 ± 0.0007 (tight ID), +0.0031 ± 0.0005 (tight iso), +0.0054 ± 0.0018 (IsoMu24), +0.0025 ± 0.0005 (medium ID) over all bins
and +0.0011 to +0.0020 at 30-60 GeV, about 1-3 × mc_stat. If the bias scales as 1/N_MC, the full-MC SFs carry a bias of the
same size. Two estimators were implemented and tested on these runs and removed because they did not predict the shift: the
mean of the bootstrap replicas minus the nominal, and a split-half (event parity) jackknife (the jackknife-corrected half-vs-full
difference was larger than the uncorrected one). The skill states the residual in a gotcha.

### (d2) Data-statistics uncertainty (added after review)

Two independent halves of the data (G1 + H2, G2 + H4), same MC, z = (SF_1 - SF_2)/sqrt(stat_1^2 + stat_2^2) over bins with a
good fit and stat < 0.05: RMS 0.80 (tight ID, 28 bins), 0.84 (medium ID, 28), 0.92 (tight iso, 25), together **0.85 ± 0.07**
(81 bins, no |z| > 3). The HESSE data-stat error covers and is slightly conservative, even though every Z enters twice.

### Golden JSON (added after review)

`tnp.py` applies no certification mask unless `--lumi-mask` is given. 95.6 percent of the data events (95.7 percent of the
tight-ID pairs) are in the 2016 golden JSON. With the mask, the medium-ID SFs move by at most 0.0009 (median 0.0002) and the
soft-ID SFs by at most 0.0006 at 30-60 GeV and 0.0015 in any of 27 reliable bins, at most 0.55 × the data-stat error.

### (e) Offline mode and exit codes

`--wp tightid --no-pog --no-pu` and `--pog-json /nonexistent/... --pu-json /nonexistent/...` (1 M events each) both complete
(30 bins, exit 1 from 2 failed fits in this small sample), print `POG=unavailable` and `PILEUP=off`, write the warnings
("POG correction NUM_TightID_DEN_TrackerMuons unavailable (OSError: ... not found)") into `warnings` and record
`pog_available=false`, `pileup_weights=false`, binning from the preset. `--dry-run` exits 0; an `&`-precedence mistake,
an integer field used as a boolean (`highPtId`), a call (`__import__(...)`) and, after review, `--dry-run --num highPtId`
(the dry run now evaluates every expression on 200 events), `--den` without a numerator (before: silently tight ID), a
6000-term expression (before: `RecursionError`, exit 1), trigger specs with mask 0, mixed `|`/`&` or ΔR 0 exit 2 with a message.
Without `--syst` and `--correctionlib` (e.g. the MC-half runs) the output carries the warning that the total has no systematics.

### IsoMu22 activity (corrected after review)

See (b): `code/isomu22_check.py`, `summary.json` `isomu22_activity`.

### (f) Systematics (`--syst`)

Per bin: background exponential vs second-order Bernstein polynomial, mass window 70-115 vs 75-110 GeV, tag pT > 33 GeV or
tag iso < 0.05 (larger shift). Medians at 30-60 GeV: 0.0002-0.0011 (background), 0.0001-0.0005 (window), 0.0002-0.0014 (tag);
the total syst is comparable to the data stat. The largest values (up to 0.36, tight iso |eta| 2.1-2.4 above 120 GeV, where the fail category is empty and the data-stat error is even larger, 0.80) are in high-pT bins with few probes. A clipped plain
polynomial background gave invalid minima in 46 fits of the first run; the Bernstein form fixed that.

## Checks (`check_results.py`, stdlib only, exit 0/1/2, `SUMMARY=n/n`)

| Check                                                                                                                                                          | Tolerance and why                                                                                                                      |
| -------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- |
| (a) presets identical to the pre-change script and to the spelled-out definitions                                                                              | bitwise: the code paths are meant to be the same                                                                                       |
| (b) weighted SF/POG at 30-60 GeV of medium, loose, high-pT, soft ID, loose PF iso, loose tracker iso                                                           | within 1 percent (as in `validation/muon-tnp`): POG uncertainties are too small for pull criteria; per-abs(eta) values printed as INFO |
| (b) efficiencies in [0, 1]; 40-50 GeV SFs in [0.9, 1.1] and trigger plateau SFs in [0.8, 1.2] (bins with total error < 0.05); fits ok                          | at most 10 percent `FIT-NOT-OK`                                                                                                        |
| (b) IsoMu22 and Mu17-leg offline runs complete; plateau data efficiency in [0.5, 1]                                                                            | the IsoMu22 endcap stays above 0.5                                                                                                     |
| (a) new presets identical to the stored pre-change outputs                                                                                                     | bitwise                                                                                                                                |
| (c) correctionlib: loads, validates, nominal/up/down/components/efficiencies equal the JSON or the documented fill, clamping; end-to-end mean SF in (0.9, 1.1) | 1e-9 (floating point); the correctionlib file must hold exactly the measured or filled numbers                                         |
| (c) `down` ≥ 0, `systup`/`systdown` aliases, every filled bin in the description, `syst` on                                                                    | exact; filled bins printed as INFO with raw and written values                                                                         |
| (d2) data-split RMS z in [0.6, 1.3]                                                                                                                            | ±0.07 statistical; HESSE may be conservative                                                                                           |
| golden JSON: max dSF at 30-60 GeV below 0.002, 90-100 percent of events certified                                                                              | 0.002 is above the 30-60 GeV data-stat errors of a few 1e-3 at most                                                                    |
| IsoMu22: P(IsoMu22 given IsoMu24) in 0.55-0.70 (G), 0.40-0.55 (H), MC above 0.98; fewer than 5 percent of LS in between                                        | the numbers quoted in the skill                                                                                                        |
| `--syst` default: on with `--correctionlib`, warning without                                                                                                   | exact                                                                                                                                  |
| (d) RMS z in [0.75, 1.3], mean z within ±0.5, mc_stat half/full within 25 percent of sqrt(N_full/N_half)                                                       | the statistical precision of an RMS over 111 bins is ±0.07; bins of different WPs share events, so a wider window                      |
| (e) offline runs exit 0 or 1 with POG and pileup off; dry run 0; bad expressions, arguments and trigger specs 2                                                | exact                                                                                                                                  |
| (f) every syst component present, median at 30-60 GeV below 0.005                                                                                              | the variations of `validation/muon-tnp` were 0.0001-0.0007                                                                             |
| plots present, no personal paths                                                                                                                               |                                                                                                                                        |

Result: `SUMMARY=72/72`. The finite-MC shift (d), the IsoMu24 barrel offset and the filled bins are printed as INFO, not tested.

## Reproduce

```bash
SCRATCH=<scratch> bash validation/muon-tnp-generic/code/run_all.sh   # about 15 minutes; copies 7.3 GB of inputs once
# or a subset of jobs (code/jobs.txt names): ... run_all.sh 'mediumid|looseid'
```

| File                           | Purpose                                                                                        |
| ------------------------------ | ---------------------------------------------------------------------------------------------- |
| `code/input_files.txt`         | input files (paths under the Open Data EOS)                                                    |
| `code/jobs.txt`                | every `tnp.py` run: name, script (old = before this change), data set, MC set, arguments       |
| `code/isomu22_check.py`        | IsoMu22 activity per file and lumi section, origin of the 22-24 GeV bit-2 objects              |
| `code/run_all.sh`              | copy inputs, run the jobs (3 in parallel), exit-code tests, `summarize.py`, `check_results.py` |
| `code/summarize.py`            | tests a-f from the run outputs into `summary.json`, `plots/`, `results/` (needs the LCG view)  |
| `summary.json`, `plots/`       | outputs                                                                                        |
| `results/*_correctionlib.json` | the correctionlib files written by `tnp.py` (generated, excluded from prettier)                |
| `results/pre_change_<wp>.json` | outputs of the pre-change `tnp.py` on the same inputs, for the equivalence test                |
| `REVIEW.md`                    | independent review (not edited); fixes R1-R6 and O2, O5, the data-split test are applied       |
| `SKILLS_USED.md`               | what the skill said, what was wrong or missing, failures on the way                            |

Not done: the full G+H dataset (the previous validation covers it for the presets), the Mu8 leg, IsoTkMu22/24 and Mu50
with the new interface, a correction for the finite-MC bias, and from the review: one-replica-at-a-time bootstrap
memory (O1), uncertainty inflation outside the binning (O3, documented as extrapolation only), `--strict` (O4), a closure
with real background and a detector-response change (O7), the soft-ID offset study (O8).
