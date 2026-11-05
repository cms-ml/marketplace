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
fit once at the end. Do not reuse `tnp_pairs()` for that: it returns one
working point's arrays, applies the HLT requirement itself, and keeps no
run, lumi or HLT columns, so you cannot apply the golden JSON, compute the
luminosity or split by era. Store per pair: run, luminosityBlock, the HLT
flags, m, tag and probe pT/η/ID/iso/IP and the matched trigger-object pT per
filter bit; build every working point and systematic from that table.
`fit_pass_fail()` can be imported. `validation/muon-tnp/condor/skim.py` in
the marketplace repository is a tested example.

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

- **The NanoAOD IsoMu24 SF sits above the POG, cause open.** On 3.55 fb⁻¹ of
  2016G+H (probe pass = muon object with bit 2 or 8, pT ≥ 24 GeV, ΔR < 0.1)
  the SF is 0.8–1.5% above `NUM_IsoMu24_or_IsoTkMu24_DEN_..._PFIsoTight` at
  30–60 GeV (barrel 40–50 GeV: 0.9767 vs 0.9627). It does not move with the
  fit, mass window, background shape, pileup weights, tag pT, era or the
  event-level HLT requirement. It does depend on the pass definition: bit 2
  alone brings |η| > 0.9 within 0.1% of the POG (barrel stays +1.1%). Use the
  POG HLT SFs in analyses and treat a NanoAOD trigger SF as a cross-check.
- **Filter bits are not paths.** A bit marks a type of filter (64% of the
  unfired events with a bit-2 object fired IsoMu22), not one path. Always add the pT threshold to
  the match: it matters for probes below about 30 GeV (26–30 GeV: ε_data 0.87
  at ≥ 24 GeV, 0.71 at ≥ 27 GeV), not above. Require the event to have fired
  `HLT_IsoMu24 | HLT_IsoTkMu24` (`tnp.py` does). With that, probes matched in
  events that fired neither path are 5 × 10⁻⁵ of all matched probes, and
  dropping or tightening the requirement moves the SF by < 0.001: this is not
  the cause of the offset above.
- **Too little MC fakes a bias.** The template and the MC efficiency
  fluctuate together and push every bin the same way: tight-ID mean SF/POG was
  1.011, 1.015, 1.008, 1.005 at MC/data pair ratios 0.009, 0.044, 0.22, 0.44.
  Aim for MC/data ≥ 0.5. The 2016postVFP `ZToMuMu_M-50To120` powheg sample has
  only 2.96 M events (1.8 M pairs), against about 19 M pairs in full G+H data,
  so subsample the data or add `DYJetsToLL_M-50` (negative weights: use
  sign(genWeight)).
- **Run-period dependence is small; state it anyway.** Between Run2016G and
  Run2016H (14 and 17 files) the SFs differ by at most 0.4% per bin: mean
  SF_G − SF_H is −0.0014 ± 0.0004 (IsoMu24), −0.0002 ± 0.0003 (tight iso),
  +0.0012 ± 0.0002 (tight ID). Two-file samples are too small to see this
  (a 2.4σ fluctuation looked like a 3% IsoMu24 change). The postVFP POG JSON
  covers late F, G and H; say which runs you used.
- **Fits at ε → 1.** When the fail category is almost empty (isolation at
  high pT), Minuit may report invalid errors (`FIT-NOT-OK`), or a valid status
  with a useless error (tight iso, |η| 2.1–2.4, pT > 120 GeV: SF error 0.53).
  Check the error size, not only the status; merge pT bins or quote the
  counting result with a Clopper-Pearson interval
  (`scipy.stats.beta.ppf([0.16, 0.84], [k, k + 1], [n - k + 1, n - k])`).
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
