---
name: muon-tag-and-probe
description: >-
  Use when measuring muon efficiencies or data/MC scale factors with tag and
  probe on Z → μμ in CMS NanoAOD: muon ID (tight, medium, high-pT),
  isolation or single-muon trigger (IsoMu24, Mu50) efficiencies in bins of pT
  and |η|; choosing tag and probe definitions; matching muons to trigger
  objects with TrigObj_filterBits; fitting pass and fail m_μμ spectra with
  signal plus background; comparing with or applying the Muon POG
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

The Muon POG publishes official SFs as correctionlib JSON on cvmfs. Use those
in an analysis. Measure your own when you need a selection the POG does not
cover, a cross-check, or Open Data validation.

[scripts/tnp.py](scripts/tnp.py) does the whole chain (pairs, pass/fail fit,
MC counting, SF, comparison with the POG JSON, fit plots) for three working
points: `tightid`, `tightiso`, `isomu24`.

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

The denominators follow the POG chain:

| Step       | Denominator (probe)                      | Numerator                              | POG correction (Run 2 UL)                                     |
| ---------- | ---------------------------------------- | -------------------------------------- | ------------------------------------------------------------- |
| `tightid`  | `Muon_isTracker`                         | `Muon_tightId`                         | `NUM_TightID_DEN_TrackerMuons`                                |
| `tightiso` | tight ID, \|dxy\| < 0.2, \|dz\| < 0.5 cm | `Muon_pfRelIso04_all < 0.15`           | `NUM_TightRelIso_DEN_TightIDandIPCut`                         |
| `isomu24`  | tight ID and tight iso                   | matched to an IsoMu24/IsoTkMu24 object | `NUM_IsoMu24_or_IsoTkMu24_DEN_CutBasedIdTight_and_PFIsoTight` |

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
# variations: nominal, systup, systdown, stat, syst (+ AltSig, massBin, massRange, tagIso)
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

One 2016 SingleMuon file (1.5 M events) gives about 94 000 pairs in 30 s and
1.3 GB. For the full G+H dataset, run the pair selection on Condor
(`lpc-condor` skill), save the flat pair arrays, and fit once at the end.
`tnp_pairs()` and `fit_pass_fail()` can be imported for that.

### 3. Pairs in Awkward

```python
pair = ak.argcartesian([mu, mu], axis=1)          # ordered pairs: each muon is tag once
t, p = mu[pair["0"]], mu[pair["1"]]
good = (pair["0"] != pair["1"]) & is_tag[pair["0"]] & (t.charge * p.charge < 0) & den(p)
m = (t + p).mass                                   # Momentum4D records (vector-awkward skill)
good = good & (m > 70) & (m < 115)
passing = ak.flatten(num(p)[good])
```

### 4. Trigger matching

```python
to = events.TrigObj
sel = (to.id == 13) & ((to.filterBits & (2 | 8)) != 0) & (to.pt >= 24)  # Iso | IsoTkMu, threshold
# deltaR(muon, object) < 0.1 with ak.cartesian(..., nested=True), then ak.any(axis=-1)
```

Read the bit meanings from the branch title of **your** file:
`uproot.open(f)["Events"]["TrigObj_filterBits"].title`. In 2016 NanoAODv9,
muon bits are 1 = TrkIsoVVL, 2 = Iso, 4 = OverlapFilter PFTau, 8 = IsoTkMu,
1024 = 1mu (Mu50).

### 5. Report

Per bin: ε_data, ε_MC, SF with errors, the POG SF with its `systup − nominal`
uncertainty, and pull = (SF − SF_POG) / √(σ² + σ_POG²). Over all bins, the
mean and RMS of the pulls. Look at the fit plots of the bins with the largest
pulls and every `FIT-NOT-OK` bin.

## Gotchas

- **Filter bits are not paths.** A bit marks a type of filter, not one path,
  so the "Iso" bit (2) does not mean the object fired IsoMu24. In a Run2016H file,
  4% of events that fired **neither** `HLT_IsoMu24` nor `HLT_IsoTkMu24` still
  have a muon object with bit 2 and pT ≥ 24 GeV. A bit + pT match therefore
  overestimates the IsoMu24 efficiency, and the measured trigger SF differed
  from the POG by 1–3% (tested). Use the POG HLT SFs in analyses, treat a
  NanoAOD trigger measurement as a cross-check, and always add the pT
  threshold to the match.
- **Too little MC fakes a bias.** With 30 000 DY MC events the tight-ID SF
  was 1.5% above the POG in every bin (mean pull +2.1); with 1 M events the
  same data gave mean pull +0.9 and RMS 1.2. Use at least as many MC events
  as data pairs.
- **Run-period dependence.** Trigger and isolation efficiencies change
  through 2016: the IsoMu24 SF at |η| 2.1–2.4 was 0.990 in two Run2016G files
  and 0.963 in two Run2016H files. Compare with the POG only with data that
  spans the same luminosity-weighted period, or say which runs you used.
- **Fits at ε → 1.** When the fail category is almost empty (isolation at
  high pT), Minuit reports invalid errors (`FIT-NOT-OK`). Merge pT bins or
  quote the counting result with a Clopper-Pearson interval.
- **Use the POG denominator.** A tight-ID SF on all reconstructed muons is
  not the same as `..._DEN_TrackerMuons`, and an isolation SF without the IP
  cut is not `..._DEN_TightIDandIPCut`. A different denominator gives a
  different (and not comparable) SF.
- **Out-of-range inputs raise.** `evaluate(1.0, 10.0, "nominal")` fails with
  `Index below bounds in Binning for input argument 1 value: 10.000000`, and
  |η| ≥ 2.4 with `Index above bounds ... argument 0`. Clamp pT to the first
  edge (15 or 26 GeV) and select |η| < 2.4 first; pT above the last edge is
  fine (overflow bin). η may be signed: the JSON applies `abs(x)` itself.
- **Pileup weights.** Isolation depends on pileup. Weight MC with
  `POG/LUM/<era>/puWeights.json.gz` (`Collisions16_UltraLegacy_goldenJSON`,
  input `Pileup_nTrueInt`).
- **Tag pT above the plateau.** A tag just above 24 GeV sits on the IsoMu24
  turn-on; use 29 GeV (or higher) so the tag selection does not depend on
  the trigger efficiency you may be measuring.
- **High-pT muons.** For pT above about 120 GeV use `muon_HighPt.json.gz` and
  the high-pT ID (`Muon_highPtId == 2`) with TuneP momentum
  (`Muon_tunepRelPt × Muon_pt`); the Z sample runs out of probes there.

## Reference Files

- [references/tested-2016.md](references/tested-2016.md): the 2016 Open Data
  tests behind the numbers above (files, commands, per-bin tables, run
  dependence, the filter-bit check)

## Docs

- Muon POG Run 2 recommendations and SF JSON: <https://muon-wiki.docs.cern.ch/guidelines/>
- jsonpog-integration (correctionlib files on cvmfs): <https://gitlab.cern.ch/cms-nanoAOD/jsonpog-integration>
- correctionlib: <https://cms-nanoaod.github.io/correctionlib/>
- NanoAOD muon and TrigObj branch documentation: <https://cms-nanoaod-integration.web.cern.ch/autoDoc/>
- spark_tnp (POG tag-and-probe framework): <https://gitlab.cern.ch/cms-muonPOG/spark_tnp>
