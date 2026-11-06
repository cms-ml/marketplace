---
name: muon-tag-and-probe
description: >-
  Use when measuring muon efficiencies or data/MC scale factors with tag and
  probe on Z → μμ in CMS NanoAOD: muon ID (loose, medium, tight, soft,
  high-pT, MVA), PF or tracker isolation, single-muon trigger (IsoMu22/24/27,
  IsoTkMu, Mu50) or double-muon trigger leg (Mu17, Mu8) efficiencies in bins
  of pT and |η|; choosing tag and probe definitions; matching muons to
  trigger objects with TrigObj_filterBits; fitting pass and fail m_μμ spectra
  with signal plus background; estimating the MC-statistics or systematic
  uncertainty of a scale factor; writing scale factors as correctionlib JSON,
  or working offline without cvmfs; comparing with or applying the Muon POG
  correctionlib JSON (muon_Z.json.gz, muon_HighPt.json.gz); or debugging
  scale factors that are above 1, differ from the POG by a few percent, or
  fits that fail in the fail category.
metadata:
  summary: Muon ID, isolation and trigger efficiencies and scale factors from Z → μμ tag and probe in NanoAOD, with the Muon POG correctionlib comparison
---

# Muon tag and probe

## Overview

Select Z → μμ events with one well-identified, trigger-matched muon (the
**tag**). The other muon (the **probe**) is an unbiased sample of real muons
for the step you measure. The efficiency is the fraction of probes that pass,
after the background under the Z peak is removed by a fit. Measure it in data
and in DY MC with the same code, in the POG |η| × pT bins (GeV). The
**scale factor** SF = ε_data / ε_MC is what analyses apply to MC.

The Muon POG publishes official SFs as correctionlib JSON on cvmfs. When the
task is to **measure** scale factors (your own selection, Open Data, a
calibration task), the measurement is the answer: compare with the POG as a
sanity check on real CMS data, but never report POG values in place of a
measurement. In simulated or modified-detector samples the true SFs are not
the POG ones.

[scripts/tnp.py](scripts/tnp.py) does the whole chain (pairs, pass/fail fit,
MC counting, SF, uncertainties, comparison with the POG JSON, correctionlib
output, fit plots) for the presets `tightid`, `tightiso`, `isomu24` or any
working point written as expressions over NanoAOD muon fields
(`--num mediumId`, `--num-trigger 2:22`). It runs offline (no POG or LUM
JSON) with a warning. [references/working-points.md](references/working-points.md)
lists the expressions, trigger bits, options and output fields.

## When to Use

- Measuring muon ID, isolation or trigger efficiencies and SFs on Z → μμ
- Cross-checking or applying the Muon POG SFs (`muon_Z.json.gz`)
- Validating a muon selection on Open Data against the official SFs
- **Not** for jet/HT trigger turn-ons with a reference trigger: use the
  `trigger-efficiency` skill. **Not** for J/ψ (low pT) or tracking
  efficiencies (the method is the same, the probes and fits differ)

## Key Concepts

| Term         | Meaning                                                                                                   |
| ------------ | --------------------------------------------------------------------------------------------------------- |
| Tag          | Tight ID, PF iso < 0.15, pT above the trigger plateau (29 GeV for IsoMu24), matched to the trigger object |
| Probe        | Opposite-charge muon passing the **denominator** of the step; m(tag, probe) in 70–115 GeV                 |
| Pass / fail  | Probes passing / failing the **numerator**                                                                |
| Both as tags | Every pair is used twice (each muon as tag once), so a probe that is also a good tag is not lost          |
| Data ε       | Simultaneous pass/fail fit: signal shape from MC per category, exponential background, common N_sig and ε |
| MC ε         | Counting generator-matched probes (`Muon_genPartFlav == 1`), weights sign(genWeight) × pileup             |
| POG name     | `NUM_<numerator>_DEN_<denominator>`; SFs factorise as ID × ISO × HLT, each on the previous step           |
| `stat`       | Data statistical error of the fit (HESSE), in SF units                                                    |
| `mc_stat`    | Spread of the SF over Poisson-bootstrap replicas of the MC events (MC ε and templates refitted together)  |
| `syst`       | `--syst`: background exp vs Bernstein poly2, window 75–110 GeV, tag pT + 4 GeV or iso < 0.05 (max)        |

The denominators follow the POG chain:

| Step       | Denominator (probe)                      | Numerator                       | POG correction (Run 2 UL)                                     |
| ---------- | ---------------------------------------- | ------------------------------- | ------------------------------------------------------------- |
| `tightid`  | `Muon_isTracker`                         | `Muon_tightId`                  | `NUM_TightID_DEN_TrackerMuons`                                |
| `tightiso` | tight ID, \|dxy\| < 0.2, \|dz\| < 0.5 cm | `Muon_pfRelIso04_all < 0.15`    | `NUM_TightRelIso_DEN_TightIDandIPCut`                         |
| `isomu24`  | tight ID and tight iso                   | matched to a bit-2 (Iso) object | `NUM_IsoMu24_or_IsoTkMu24_DEN_CutBasedIdTight_and_PFIsoTight` |

## Canonical Patterns

### 1. Look at the official SFs first

```bash
source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh   # correctionlib 2.6.4
ls /cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/MUO/2016postVFP_UL/
# muon_HighPt.json.gz  muon_JPsi.json.gz  muon_Z.json.gz
python3 -c 'import correctionlib, sys; print(*correctionlib.CorrectionSet.from_file(sys.argv[1]), sep="\n")' \
  /cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/MUO/2016postVFP_UL/muon_Z.json.gz
# NUM_GlobalMuons_DEN_genTracks ... NUM_TightID_DEN_TrackerMuons ... (29 corrections)
```

(`correction summary <file>` fails on this file in the LCG_109 view with a
pydantic `Input should be a valid number [type=float_type ...]` error; the
Python listing works.)

```python
import correctionlib
cs = correctionlib.CorrectionSet.from_file(".../POG/MUO/2016postVFP_UL/muon_Z.json.gz")
sf = cs["NUM_TightID_DEN_TrackerMuons"]
sf.evaluate(-1.5, 35.0, "nominal")   # eta (abs taken inside), pt [GeV], variation -> 0.9905
sf.evaluate(-1.5, 35.0, "systup")    # stat+syst up boundary   -> 0.9944
# SFs: nominal, systup, systdown. Uncertainties (not SFs): stat, syst, AltSig, massBin,
# massRange, tagIso; systup - nominal = hypot(stat, syst). The IsoMu24 correction has no
# tagIso ("Index not available in Category ... tagIso").
```

Pick the era directory that matches the data: `2016preVFP_UL` (B–F early) or
`2016postVFP_UL` (F late, G, H), `2017_UL`, `2018_UL`, `2022_Summer22`, ....
The pT edges start at 15 GeV (ID, iso) or 26 GeV (IsoMu24); clamp pT into
range before evaluating. Arrays work: `sf.evaluate(abs_eta_np, pt_np, "nominal")`.

### 2. Run the measurement

```bash
S=root://eospublic.cern.ch//eos/opendata/cms
python3 <skill>/scripts/tnp.py \
  --data $S/Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/70000/<file>.root ... \
  --mc   $S/mc/RunIISummer20UL16NanoAODv9/ZToMuMu_M-50To120_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/260000/<file>.root ... \
  --wp tightid --era 2016postVFP_UL --out tnp_tightid.json --plots plots/
# |eta| 0.0-0.9 pt 40-50: eff data 0.9630+-0.0010 mc 0.9749+-0.0005 SF 0.9878+-0.0011 POG 0.9867+-0.0031 pull +0.33
# ...
# N_BINS=31  MEAN_PULL=0.92  RMS_PULL=1.19  OUT=tnp_tightid.json
```

2016 SingleMuon files hold 1.3–3.4 M events (mean 2.3 M); `tnp.py` needs
about 30 s and 1.3 GB per 1.5 M events (2.5 GB for a 2.9 M-event file). For more than a few files, run the
pair selection on Condor (`lpc-condor` skill), write a flat pair table, and
fit once at the end. `tnp_pairs()` keeps no run, lumi or HLT columns (no
golden JSON, luminosity or era split): store per pair run, luminosityBlock,
HLT flags, m, tag and probe pT/η/ID/iso/IP and the matched trigger-object pT
per filter bit, and build every working point from that table
(`validation/muon-tnp/condor/skim.py` in the marketplace repository).

### 3. Any working point, offline, as correctionlib

```bash
T=<skill>/scripts/tnp.py   # D=<data files>, MC=<DY MC files>
python3 $T --data $D --mc $MC --den isTracker --num mediumId --pog NUM_MediumID_DEN_TrackerMuons \
  --syst --name mediumid --out mediumid.json --correctionlib mediumid_sf.json
# |eta| 0.0-0.9 pt 40-50: ... SF 0.9961+-0.0004 POG 0.9993+-0.0002 ... | stat 0.0004 mc_stat 0.0003 syst 0.0004 total 0.0006
# N_BINS=32  N_FIT_FAILED=0 ... POG=NUM_MediumID_DEN_TrackerMuons  PILEUP=on  CORRECTIONLIB=mediumid_sf.json
python3 $T --data $D --mc $MC --den "tightId & (pfRelIso04_all < 0.15)" --num-trigger 2:22 \
  --pt-edges 20 22 24 26 30 40 60 120 inf --no-pog --no-pu --name isomu22 --correctionlib isomu22_sf.json
correction validate mediumid_sf.json      # "All OK"
```

```python
import correctionlib, awkward as ak
cs = correctionlib.CorrectionSet.from_file("mediumid_sf.json")
sf = cs["mediumid"]                 # also mediumid_eff_data, mediumid_eff_mc (third input "valtype")
sf.evaluate(-1.5, 35.0, "nominal")  # eta (abs taken inside), pt [GeV]; out-of-range values are clamped
sf.evaluate(-1.5, 35.0, "up")       # nominal + total ("down": - total); "stat", "mc_stat", "syst" are uncertainties
w = sf.evaluate(ak.to_numpy(ak.flatten(mu.eta)), ak.to_numpy(ak.flatten(mu.pt)), "nominal")
event_weight = ak.prod(ak.unflatten(w, ak.num(mu.pt)), axis=1)   # product over the selected muons
```

Offline (no cvmfs, `--no-pog`, `--no-pu`, or unreadable `--pog-json` /
`--pu-json`): the comparison or the pileup weights are skipped, a warning
goes to stderr and into `warnings`, and the output records `pog_available`,
`pileup_weights` (stdout `POG=unavailable`, `PILEUP=off`). The binning then
comes from `--eta-edges` / `--pt-edges`, the preset, or the default
|η| 0/0.9/1.2/2.1/2.4 × pT 15–120 GeV + overflow. `--dry-run` checks the
branches and evaluates every expression and trigger spec on 200 events. Each run on 7.1 M data and
1.25 M MC events took about 1 min and 1.9 GB with 50 bootstrap replicas and
`--syst`. `--lumi-mask <golden JSON>` drops uncertified data (default: no
mask, see Gotchas).

### 4. Pairs and trigger matching in your own code

`tnp_pairs()` and `_trigger_match()` can be imported; the Awkward pattern
(each muon is tag once, ΔR match to `TrigObj`) is in
[references/working-points.md](references/working-points.md). Read the
filter-bit meanings from the branch title of **your** file:
`uproot.open(f)["Events"]["TrigObj_filterBits"].title`.

### 5. Report

Per bin: ε_data, ε_MC, SF with `stat`, `mc_stat`, `syst` and the total
(`sf_total_err`, also `up`/`down` in the correctionlib file), the POG SF with
its `systup − nominal` uncertainty, and `pull_total` = (SF − SF_POG) /
√(σ_total² + σ_POG²). Over all bins, the mean and RMS of the pulls. Look at
the fit plots of the bins with the largest pulls and every `FIT-NOT-OK` bin.
The legacy `sf_err` / `pull` (data fit + MC counting) are kept for
comparison but undercover (see Gotchas). `--syst` is on by default with
`--correctionlib`; without it a warning says that the total holds `stat`
and `mc_stat` only.

## Gotchas

- **IsoMu24: match bit 2 only, not bit 2 | 8.** For
  `NUM_IsoMu24_or_IsoTkMu24_...`, the obvious match (object with bit 2 or 8)
  gives an SF 1.0–1.5% above the POG at 30–60 GeV; bit 8 alone is 1.5–4%
  below. Matching the probe to a bit-2 (Iso) object, pT ≥ 24 GeV, ΔR < 0.1,
  brings |η| 0.9–2.4 within 0.2% of the POG (3.55 fb⁻¹ of 2016G+H). The tag's
  match does not matter (≤ 0.0003), and a path-aware match (bit 2 if IsoMu24
  fired, bit 8 if IsoTkMu24 fired) equals the OR. `tnp.py` uses bit 2.
- **The barrel IsoMu24 SF is still +1.2% above the POG, cause open.** With
  bit 2, |η| < 0.9 stays at SF/POG ≈ 1.012 at every pT from 26 to 120 GeV.
  It does not move with the fit, mass window, background shape, pileup
  weights, tag pT or match, era, HLT requirement or object-pT threshold. On
  real CMS data, quote it as a systematic (or state it) when you compare with
  the POG.
- **Filter bits are not paths.** A bit marks a type of filter (64% of the
  unfired events with a bit-2 object fired IsoMu22), not one path. Always add the pT threshold to
  the match: it matters for probes below about 30 GeV (26–30 GeV: ε_data 0.87
  at ≥ 24 GeV, 0.71 at ≥ 27 GeV), not above. Require the event to have fired
  `HLT_IsoMu24 | HLT_IsoTkMu24` (`tnp.py` does). With that, probes matched in
  events that fired neither path are 5 × 10⁻⁵ of all matched probes, and
  dropping or tightening the requirement moves the SF by < 0.001: this is not
  the cause of the IsoMu24 offsets above. A higher object threshold (27 GeV)
  changes the 26–30 GeV efficiencies a lot but the SF by at most 0.7%.
- **The MC counting error is not the MC-statistics error.** The MC templates
  of the data fit fluctuate too. Between two independent halves of the MC
  (same data, 111 bins of four working points), (SF_A − SF_B)/σ had an RMS
  of 4.7 with the binomial MC-counting error (8.8 for tight iso) and
  1.04 ± 0.07 with the bootstrap `mc_stat`, which scaled as 1/√N_MC
  (0–10% below it). Quote `mc_stat` (default 50 replicas), never `eff_mc_err`.
- **Too little MC fakes a bias, and no uncertainty covers it.** The template
  and the MC efficiency fluctuate together and push every bin the same way:
  tight-ID mean SF/POG was 1.011, 1.015, 1.008, 1.005 at MC/data pair ratios
  0.009, 0.044, 0.22, 0.44. Even at MC/data 1.8 the halves above gave
  (SF_A + SF_B)/2 − SF_full = +0.0011 to +0.0020 at 30–60 GeV (2.5–4σ, about
  1–3 × `mc_stat`), so the full-MC SF is probably biased by as much. Neither
  the bootstrap mean nor a split-half jackknife predicted the shift (both
  tried and dropped). Use all the MC there is and state the residual. The 2016postVFP `ZToMuMu_M-50To120` powheg sample has
  only 2.96 M events (1.8 M pairs), against about 19 M pairs in full G+H data,
  so subsample the data or add `DYJetsToLL_M-50` (negative weights: use
  sign(genWeight)).
- **Run-period dependence is small; state it anyway.** Run2016G and H SFs
  differ by at most 0.4% per bin (14 and 17 files); two-file samples showed a
  fake 3% IsoMu24 change. The postVFP POG JSON covers late F, G and H.
- **`&` binds tighter than `<` in expressions.** `--num "tightId &
pfRelIso04_all < 0.15"` means `(tightId & pfRelIso04_all) < 0.15`;
  `tnp.py` rejects it (exit 2). Write `tightId & (pfRelIso04_all < 0.15)` or
  `tightId and pfRelIso04_all < 0.15`. Integer flags must be compared:
  `--num highPtId` fails with "needs booleans", write `highPtId == 2`.
- **A lower-threshold trigger is switched off in part of the data.**
  `--num-trigger 2:22` (IsoMu22) gave SF 0.53 at |η| 2.1–2.4, 22–24 GeV and
  0.93–0.99 at 30–120 GeV. `HLT_IsoMu22` fired in 0.61–0.63 (2016G files) and
  0.48–0.49 (H) of the `HLT_IsoMu24` events, in 0.99 in MC, and per lumi
  section it is either on (> 95%) or off (< 5%), never in between. Bit-2
  objects at 22–24 GeV still come from other Iso paths such as
  `IsoMu22_eta2p1`, which does not reach |η| > 2.1: only the endcap breaks.
  Measure such paths only in lumi sections where they ran
  (`validation/muon-tnp-generic/code/isomu22_check.py`), or in simulation.
- **Do not give `--correctionlib` the `--out` path.** A first validation run
  wrote the correctionlib file over the result JSON; `tnp.py` now refuses
  (exit 2).
- **Fits at ε → 1.** When the fail category is almost empty (isolation at
  high pT), Minuit may report invalid errors (`FIT-NOT-OK`), or a valid status
  with a useless error (tight iso, |η| 2.1–2.4, pT > 120 GeV: SF error 0.53).
  Check the error size, not only the status; merge pT bins or quote the
  counting result with a Clopper-Pearson interval
  (`scipy.stats.beta.ppf([0.16, 0.84], [k, k + 1], [n - k + 1, n - k])`).
  With no failing MC probe the fit returns any value: medium ID, |η|
  0.9–1.2, pT > 120 GeV gave SF 0.877 ± 0.886 with `fit_ok`. `tnp.py`
  flags such bins (fit not ok, < 5 fail probes, SF stat > 0.1) and writes
  the nearest reliable pT bin, with an extra `fill` uncertainty, into the
  correctionlib file; the raw numbers stay in the result JSON.
- **Use the POG denominator.** A tight-ID SF on all reconstructed muons is
  not the same as `..._DEN_TrackerMuons`, and an isolation SF without the IP
  cut is not `..._DEN_TightIDandIPCut`. A different denominator gives a
  different (and not comparable) SF.
- **Out-of-range inputs raise.** `evaluate(1.0, 10.0, "nominal")` fails with
  `Index below bounds in Binning for input argument 1 value: 10.000000`, and
  |η| ≥ 2.4 with `Index above bounds ... argument 0`. Clamp pT to the first
  edge (15 or 26 GeV) and select |η| < 2.4 first; pT above the last edge is
  fine (overflow bin). η may be signed: the JSON applies `abs(x)` itself.
- **`tnp.py` applies no golden JSON by default.** On the 4 validation files
  95.6% of the events are certified; with `--lumi-mask` the medium and
  soft ID SFs moved by at most 0.0009 at 30–60 GeV (0.0015 in any bin),
  below the data-stat error. Use the mask when the SFs go into an analysis
  of certified data.
- **Pileup weights.** Isolation depends on pileup. Weight MC with
  `POG/LUM/<era>/puWeights.json.gz` (input `Pileup_nTrueInt`).
- **Tag pT above the plateau.** A tag just above 24 GeV sits on the IsoMu24
  turn-on; use 29 GeV (or higher) so the tag selection does not depend on
  the trigger efficiency you may be measuring.
- **High-pT muons.** For pT above about 120 GeV use `muon_HighPt.json.gz` and
  the high-pT ID (`Muon_highPtId == 2`) with TuneP momentum
  (`Muon_tunepRelPt × Muon_pt`); the Z sample runs out of probes there.

## Reference Files

- [references/working-points.md](references/working-points.md): NanoAOD
  expressions and POG names for ID and isolation working points, trigger bits
  and `--num-trigger` values, all `tnp.py` options and output fields
- [references/tested-2016.md](references/tested-2016.md): the 2016 Open Data
  tests behind the numbers above (files, commands, per-bin tables, run
  dependence, the filter-bit check, the generic working points)

## Docs

- Muon POG Run 2 recommendations and SF JSON: <https://muon-wiki.docs.cern.ch/guidelines/>
- jsonpog-integration (correctionlib files on cvmfs): <https://gitlab.cern.ch/cms-nanoAOD/jsonpog-integration>
- correctionlib: <https://cms-nanoaod.github.io/correctionlib/>
- NanoAOD muon and TrigObj branch documentation: <https://cms-nanoaod-integration.web.cern.ch/autoDoc/>
- spark_tnp (POG tag-and-probe framework): <https://gitlab.cern.ch/cms-muonPOG/spark_tnp>
