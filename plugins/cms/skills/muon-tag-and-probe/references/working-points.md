# Working points, trigger bits and tnp.py options

Read this reference when you need the NanoAOD expression for a muon ID,
isolation or trigger working point, the POG correction it corresponds to, or
the full list of `scripts/tnp.py` options and output fields, or want to
build tag-probe pairs and trigger matches in your own Awkward code.

Contents:

- ID and isolation expressions
- Trigger filter bits and `--num-trigger`
- tnp.py options
- Output JSON and correctionlib layout
- Pairs and trigger matching in your own code

Field names and value meanings are from the branch titles of 2016 UL
NanoAODv9 (`uproot.open(f)["Events"]["Muon_mvaId"].title`); check your own
file, they change between NanoAOD versions. Checked November 2026.

## ID and isolation expressions

Write the field names without the `Muon_` prefix. Integer fields must be
compared (`highPtId == 2`), not used as booleans: `tnp.py` rejects
`--num highPtId` with "needs booleans".

| Working point         | `--num`                                                   | `--den` (POG denominator)                      | POG correction (Run 2 UL `muon_Z.json.gz`)    |
| --------------------- | --------------------------------------------------------- | ---------------------------------------------- | --------------------------------------------- |
| Loose ID              | `looseId`                                                 | `isTracker`                                    | `NUM_LooseID_DEN_TrackerMuons`                |
| Medium ID             | `mediumId`                                                | `isTracker`                                    | `NUM_MediumID_DEN_TrackerMuons`               |
| Medium prompt ID      | `mediumPromptId`                                          | `isTracker`                                    | `NUM_MediumPromptID_DEN_TrackerMuons`         |
| Tight ID              | `tightId`                                                 | `isTracker`                                    | `NUM_TightID_DEN_TrackerMuons`                |
| Soft ID               | `softId`                                                  | `isTracker`                                    | `NUM_SoftID_DEN_TrackerMuons`                 |
| High-pT ID (global)   | `highPtId == 2`                                           | `isTracker`                                    | `NUM_HighPtID_DEN_TrackerMuons`               |
| Tracker high-pT ID    | `highPtId >= 1`                                           | `isTracker`                                    | `NUM_TrkHighPtID_DEN_TrackerMuons`            |
| MVA ID loose / medium | `mvaId >= 1`, `mvaId >= 2` (3 tight, 4 VTight, 5 VVTight) | `isTracker`                                    | none in 2016 UL `muon_Z`                      |
| Loose PF iso          | `pfRelIso04_all < 0.25`                                   | `mediumId`, `looseId` or tight ID + IP         | `NUM_LooseRelIso_DEN_MediumID`, `..._LooseID` |
| Tight PF iso          | `pfRelIso04_all < 0.15`                                   | `tightId & (abs(dxy) < 0.2) & (abs(dz) < 0.5)` | `NUM_TightRelIso_DEN_TightIDandIPCut`         |
| Loose tracker iso     | `tkRelIso < 0.10`                                         | `highPtId == 2` (includes the IP cuts)         | `NUM_LooseRelTkIso_DEN_HighPtIDandIPCut`      |
| Tight tracker iso     | `tkRelIso < 0.05`                                         | `highPtId == 2`                                | `NUM_TightRelTkIso_DEN_HighPtIDandIPCut`      |
| PF iso ID flags       | `pfIsoId >= 2` (1 VLoose, 2 Loose, 3 Medium, 4 Tight, …)  | as for the PF iso cut                          | same as the cut values                        |
| Tracker iso ID flags  | `tkIsoId >= 1` (1 Loose, 2 Tight)                         | `highPtId == 2`                                | same as the cut values                        |

The high-pT ID and `tkRelIso` are defined with the TuneP momentum
(`tunepRelPt * pt`); `tnp.py` bins in PF pT, which differs little at the Z.
List every correction of a POG file with
`python3 -c 'import correctionlib,sys; print(*correctionlib.CorrectionSet.from_file(sys.argv[1]), sep="\n")' <file>`.

Expression grammar: field names, numbers, `True`/`False`, `abs()`,
comparisons (also chained, `20 < pt < 30`), `+ - * /`, and `&`, `|`, `~`
or `and`, `or`, `not` (all elementwise). Parsed with `ast`; attribute access,
subscripts, other calls and strings are rejected (exit 2).

## Trigger filter bits and `--num-trigger`

`BITS:PTMIN[:DRMAX]`: the probe is matched (ΔR < DRMAX, default 0.1) to a
`TrigObj` with `id == 13`, pT ≥ PTMIN (GeV) and the filter bits. `2|8` means
any of the bits, `1&2` all of them. Muon bits in 2016 NanoAODv9 (branch
title of `TrigObj_filterBits`): 1 = TrkIsoVVL, 2 = Iso, 4 = OverlapFilter
PFTau, 8 = IsoTkMu, 1024 = 1mu (Mu50). There is no separate bit for the
legs of `Mu17_TrkIsoVVL_Mu8_TrkIsoVVL`: the legs differ by threshold.

| Path or leg (2016)                  | `--num-trigger` | Probe denominator   | POG counterpart                                                |
| ----------------------------------- | --------------- | ------------------- | -------------------------------------------------------------- |
| IsoMu24 (POG: IsoMu24 or IsoTkMu24) | `2:24`          | tight ID, tight iso | `NUM_IsoMu24_or_IsoTkMu24_DEN_CutBasedIdTight_and_PFIsoTight`  |
| IsoMu22, IsoMu27                    | `2:22`, `2:27`  | tight ID, tight iso | none; IsoMu22 is off in part of 2016G/H data (SKILL.md gotcha) |
| IsoTkMu22, IsoTkMu24                | `8:22`, `8:24`  | tight ID, tight iso | none                                                           |
| Mu50 (or TkMu50)                    | `1024:50`       | high-pT ID, tk iso  | `NUM_Mu50_or_TkMu50_...` (not tested here)                     |
| Mu17 leg of Mu17_TrkIsoVVL_Mu8\_…   | `1:17`          | tight ID, tight iso | none                                                           |
| Mu8 leg                             | `1:8`           | as above            | none; needs `--pt-edges` from 8 GeV (not tested)               |

Bit 2 | 8 for IsoMu24 or IsoTkMu24 gives SFs 1.0–1.5% above the POG; bit 2
alone matches it (SKILL.md gotcha). A filter bit marks a filter type, so the
threshold is part of the definition: the IsoMu22 match (`2:22`) is a
different efficiency from `2:24`.

Tag options: `--tag EXPR` (default `tightId & (pfRelIso04_all < 0.15)`),
`--tag-pt` (29 GeV), `--tag-trigger` (`2:24`, or `none`), `--tag-hlt`
(`HLT_IsoMu24,HLT_IsoTkMu24`, or `none`). In a single-muon dataset keep the
tag on the path that recorded the event.

## tnp.py options

| Option                            | Meaning                                                                                                                    |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------- |
| `--wp tightid\|tightiso\|isomu24` | preset (explicit `--num/--den/--num-trigger` override it)                                                                  |
| `--num`, `--den`                  | numerator and probe denominator expressions                                                                                |
| `--num-trigger BITS:PTMIN`        | numerator trigger match (ANDed with `--num` if both are given)                                                             |
| `--pog NAME`                      | POG correction for the comparison and the binning                                                                          |
| `--eta-edges`, `--pt-edges`       | binning (pT in GeV, last edge may be `inf`); otherwise from `--pog`, the preset, default                                   |
| `--pog-json`, `--pu-json`         | file locations (default: cvmfs `jsonpog-integration`)                                                                      |
| `--no-pog`, `--no-pu`             | offline: no comparison, no pileup weights                                                                                  |
| `--mc-replicas N`, `--seed`       | Poisson bootstrap of the MC events for `mc_stat` (default 50, 0 = counting only)                                           |
| `--syst`, `--no-syst`             | background (exp vs Bernstein poly2), window 75–110 GeV, tag pT + 4 GeV or iso < 0.05; on by default with `--correctionlib` |
| `--min-fail N`, `--max-sf-stat X` | a bin is unreliable with fewer than N (5) data or MC fail probes or SF stat error > X (0.1)                                |
| `--lumi-mask JSON`                | apply a certification (golden) JSON to the data; default no mask                                                           |
| `--correctionlib FILE`, `--name`  | write a correctionlib JSON (`.json` or `.json.gz`)                                                                         |
| `--plots DIR`                     | pass/fail fit plots per bin                                                                                                |
| `--dry-run`                       | parse, check branches, evaluate every expression and trigger match on 200 events of the first files; write nothing         |

Exit codes: 0 ok, 1 the nominal fit failed in some bins, 2 bad arguments,
missing branches or unreadable input.

## Output JSON and correctionlib layout

Per bin (`bins` in `--out`): `eff_data`, `eff_mc`, `sf` and the legacy errors
`eff_data_err`, `eff_mc_err`, `sf_err` (data fit + MC counting, as before),
then the components `sf_stat` (data fit), `sf_mc_stat` (bootstrap),
`sf_syst` (`sf_syst_components`: bkg, window, tag), `sf_total_err`,
`eff_data_stat`, `eff_data_mc_stat`, `eff_data_syst`, `eff_mc_stat`,
`n_mc_gen`, `n_fail_data`, `n_fail_mc`, `reliable`, `unreliable_reasons`,
`pull` (legacy errors) and `pull_total`. The raw numbers of unreliable bins
stay here. Top level: the definition, `syst`, `pog_available`,
`pileup_weights`, `lumi_mask`, `warnings`, `unmeasured_bins`,
`correctionlib_filled_bins`.

The correctionlib file holds `<name>` (inputs `abseta` (signed η works: the
file takes `abs`), `pt` in GeV, `scale_factors`), `<name>_eff_data` and
`<name>_eff_mc` (input `valtype`). Keys `nominal`, `up`, `down` (nominal ±
total, `down` clipped at 0) and `systup`, `systdown` (aliases of `up`,
`down`, as in the POG files) are values; `stat`, `mc_stat`, `syst`, `fill`
are uncertainties, total = their quadrature sum. Without `--syst` the total
holds `stat` and `mc_stat` only; the finite-MC bias is in none of them.
Out-of-range η and pT are clamped to the edge bins: an extrapolation with the
edge bin's uncertainty.

A bin without a measurement (fewer than 50 data or gen-matched MC probes) or
an unreliable one (fit not ok, fewer than `--min-fail` fail probes in data or
MC, SF stat error above `--max-sf-stat`) takes the nominal and components of
the nearest reliable pT bin of its |η| row (ties: the lower pT bin), plus
`fill` = |raw SF − source SF| for an unreliable bin, or |source − next-nearest
reliable bin| for an unmeasured one. A row without a reliable bin gives
SF 1 ± 1. Every filled bin is listed in the correction descriptions and in
`correctionlib_filled_bins`. Example: medium ID, |η| 0.9–1.2, pT > 120 GeV
had no failing MC probe and a raw SF of 0.877 ± 0.886; the file uses the
60–120 GeV bin, SF 1.002 ± 0.125 (`fill` 0.125).

## Pairs and trigger matching in your own code

### Pairs in Awkward

```python
pair = ak.argcartesian([mu, mu], axis=1)          # ordered pairs: each muon is tag once
t, p = mu[pair["0"]], mu[pair["1"]]
good = (pair["0"] != pair["1"]) & is_tag[pair["0"]] & (t.charge * p.charge < 0) & den(p)
m = (t + p).mass                                   # Momentum4D records (vector-awkward skill)
good = good & (m > 70) & (m < 115)
passing = ak.flatten(num(p)[good])
```

### Trigger matching

```python
to = events.TrigObj
sel = (to.id == 13) & ((to.filterBits & 2) != 0) & (to.pt >= 24)  # Iso bit only, plus threshold
# deltaR(muon, object) < 0.1 with ak.cartesian(..., nested=True), then ak.any(axis=-1)
```

Read the bit meanings from the branch title of **your** file:
`uproot.open(f)["Events"]["TrigObj_filterBits"].title`. In 2016 NanoAODv9,
muon bits are 1 = TrkIsoVVL, 2 = Iso, 4 = OverlapFilter PFTau, 8 = IsoTkMu,
1024 = 1mu (Mu50). The legs of `Mu17_TrkIsoVVL_Mu8_TrkIsoVVL` share bit 1 and
differ by threshold (`--num-trigger 1:17`).
