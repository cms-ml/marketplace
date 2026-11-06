# Tests on 2016 Open Data

Read this reference when you want to know how `scripts/tnp.py` was tested,
what agreement with the Muon POG to expect from a small sample, or how the
trigger filter-bit problem was found.

Contents:

- Environment and inputs
- Tight ID: MC statistics
- Isolation and IsoMu24: run dependence
- The filter-bit check
- Full G+H subset: comparison with the POG
- Generic working points, uncertainties and correctionlib output

Tested November 2026 on cmslpc (EL9) with the LCG_109 view
(`/cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt`: uproot,
awkward, vector, iminuit 2.31.1, correctionlib 2.6.4). POG file:
`/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/MUO/2016postVFP_UL/muon_Z.json.gz`.

## Environment and inputs

| Sample | Path under `root://eospublic.cern.ch//eos/opendata/cms/`                                                                                                                    |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Data G | `Run2016G/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/70000/` (files 5 and 20 of the listing; 3.96 M events)                                                           |
| Data H | `Run2016H/SingleMuon/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1/120000/61FC1E38-...root`, `130000/0107961B-...root`                                                              |
| DY MC  | `mc/RunIISummer20UL16NanoAODv9/ZToMuMu_M-50To120_TuneCP5_13TeV-powheg-pythia8/NANOAODSIM/106X_mcRun2_asymptotic_v17-v1/{260000,270000}/` (first 8 + 7 files; 1.06 M events) |

```bash
python3 scripts/tnp.py --data <data files> --mc <mc files> --wp tightid --out tightid.json
```

Speed: one 1.5 M-event data file plus two MC files took 32 s and 1.3 GB.

## Tight ID: MC statistics

| Sample                      | Bins | Mean pull | RMS pull | Barrel 40–50 GeV SF (POG 0.9867) |
| --------------------------- | ---- | --------- | -------- | -------------------------------- |
| 1 data file, 30 k MC events | 25   | +2.12     | 2.29     | 0.9976 ± 0.0034                  |
| 2 data files (G), 1.06 M MC | 31   | +0.92     | 1.19     | 0.9878 ± 0.0011                  |

With little MC the template and the MC efficiency fluctuate together and
bias every bin the same way. Pulls use the POG `systup − nominal` as its
uncertainty. On the 3.55 fb⁻¹ subset (below), random fractions of the MC
pairs gave a tight-ID mean SF/POG of 1.011, 1.0145, 1.0077 and 1.0046 at
MC/data pair ratios 0.009, 0.044, 0.22 and 0.44 (all 2.96 M events of the
powheg sample).

## Isolation and IsoMu24: run dependence

SF at 40 < pT < 50 GeV from the first small tests, same MC (1.06 M events)
for both data samples:

| WP         | \|η\|   | Run2016G (2 files) | Run2016H (2 files) | POG    |
| ---------- | ------- | ------------------ | ------------------ | ------ |
| `isomu24`  | 0–0.9   | 0.9807 ± 0.0014    | 0.9733 ± 0.0007    | 0.9627 |
| `isomu24`  | 0.9–1.2 | 0.9682 ± 0.0024    | 0.9706 ± 0.0030    | 0.9631 |
| `isomu24`  | 1.2–2.1 | 1.0104 ± 0.0025    | 1.0059 ± 0.0031    | 0.9964 |
| `isomu24`  | 2.1–2.4 | 0.9903 ± 0.0070    | 0.9628 ± 0.0090    | 0.9607 |
| `tightiso` | 0–0.9   | 1.0012 ± 0.0011    | 0.9990 ± 0.0006    | 0.9969 |
| `tightiso` | 2.1–2.4 | 1.0083 ± 0.0022    | 1.0098 ± 0.0024    | 1.0014 |

The G–H difference at |η| 2.1–2.4 (0.990 vs 0.963) did **not** reproduce
with 14 G and 17 H files: 0.9783 ± 0.0031 vs 0.9747 ± 0.0030. It was a 2.4σ
fluctuation of two-file samples. With the larger sample, G and H differ by at
most 0.4% per bin (mean SF_G − SF_H: IsoMu24 −0.0014 ± 0.0004, tight iso
−0.0002 ± 0.0003, tight ID +0.0012 ± 0.0002).

## The filter-bit check

On 300 000 events of the Run2016H file `130000/0107961B-...root`, fraction
of events with a muon `TrigObj` carrying the bit (and pT ≥ 24 GeV):

| Bit         | Events with `HLT_IsoMu24` | `HLT_IsoTkMu24` only | Neither path |
| ----------- | ------------------------- | -------------------- | ------------ |
| 2 (Iso)     | 1.000                     | 0.045                | 0.039        |
| 8 (IsoTkMu) | 0.913                     | 1.000                | 0.022        |

Bits 2 and 8 are necessary for the paths but not sufficient: about 4% of
events that fired neither path still have an object with the bit above
threshold (4.7% on 1.0 M G+H events). That is the wrong denominator for tag
and probe, though: in Z events with a matched tag, only 146 of 3.20 M matched
probes (4.6 × 10⁻⁵; MC 6.5 × 10⁻⁵) sit in an event that fired neither path,
and 64% of those events fired `HLT_IsoMu22`. Dropping the event-level HLT
requirement moves the SF by +0.0007, a path-specific match (IsoMu24 fired
and bit 2, or IsoTkMu24 fired and bit 8) by −0.0001. The event-level
filter-bit bias is negligible; it does not explain the IsoMu24 offset below.

## Full G+H subset: comparison with the POG

`validation/muon-tnp/` in the marketplace repository (November 2026): every
5th file of the Run2016G and Run2016H SingleMuon listings (14 + 17 files,
70.3 M events, 3.553 fb⁻¹ = 21.7% of G+H), all 28 `ZToMuMu_M-50To120` files
(2.96 M events), pair selection on Condor, fits and systematics offline.

| WP         | Bins | Mean pull | RMS pull | SF/POG, 30–60 GeV         |
| ---------- | ---- | --------- | -------- | ------------------------- |
| `tightid`  | 32   | +0.51     | 0.78     | agrees, no bin > 3σ       |
| `tightiso` | 32   | +1.85     | 2.54     | +0.2–0.5% (also counting) |
| `isomu24`  | 27   | +4.90     | 6.63     | +0.8–1.5%, cause open     |

Pulls are large for small offsets because the POG uncertainty is only
0.02–0.1% in the populated bins. The `isomu24` row uses the bit 2 | 8 match.
Trigger-match definitions, SF/POG at 40–50 GeV per |η| bin and weighted over
30–60 GeV:

| Probe pass (tag)                  | 0–0.9  | 0.9–1.2 | 1.2–2.1 | 2.1–2.4 | 30–60 GeV |
| --------------------------------- | ------ | ------- | ------- | ------- | --------- |
| bit 2 \| 8 (bit 2 \| 8)           | 1.0145 | 1.0094  | 1.0084  | 1.0162  | 1.0127    |
| **bit 2 (bit 2)**                 | 1.0121 | 1.0000  | 1.0010  | 1.0010  | 1.0082    |
| bit 2 (bit 2 \| 8)                | 1.0118 | 1.0000  | 1.0009  | 1.0002  | 1.0081    |
| bit 8 (bit 8)                     | 0.9880 | 0.9687  | 0.9600  | 0.9814  | 0.9766    |
| path-aware (IsoMu24→2, IsoTkMu→8) | 1.0145 | 1.0093  | 1.0084  | 1.0163  | 1.0127    |

Bit 2 closes the gap outside the barrel; the barrel stays +1.2% for every
definition, fit and selection variation tried. An independent review
(`validation/muon-tnp/REVIEW.md`) reproduced the nominal numbers.

## Generic working points, uncertainties and correctionlib output

`validation/muon-tnp-generic/` in the marketplace repository (November 2026,
LCG_109, same POG file): 2 Run2016G + 2 Run2016H SingleMuon files (7.09 M
events, 412 k tight-ID pairs) and 8 `ZToMuMu_M-50To120` files (1.25 M events,
748 k pairs, MC/data 1.8), copied locally. Each `tnp.py` run took about
1 min and 1.9 GB with 50 bootstrap replicas and `--syst`.

- The presets, the same definitions spelled with `--den/--num/--num-trigger/--tag*`,
  and the `tnp.py` before this change give bit-identical per-bin results
  (`tightid` 32, `tightiso` 32, `isomu24` 26 bins).
- New working points, weighted SF/POG over 30–60 GeV (total uncertainty):

| `--num` (`--den`)                    | POG correction                           | SF/POG | RMS pull (total) |
| ------------------------------------ | ---------------------------------------- | ------ | ---------------- |
| `mediumId` (`isTracker`)             | `NUM_MediumID_DEN_TrackerMuons`          | 0.9977 | 1.69             |
| `looseId` (`isTracker`)              | `NUM_LooseID_DEN_TrackerMuons`           | 1.0006 | 1.39             |
| `highPtId == 2` (`isTracker`)        | `NUM_HighPtID_DEN_TrackerMuons`          | 1.0006 | 0.88             |
| `softId` (`isTracker`)               | `NUM_SoftID_DEN_TrackerMuons`            | 0.9966 | 3.12             |
| `pfRelIso04_all < 0.25` (`mediumId`) | `NUM_LooseRelIso_DEN_MediumID`           | 1.0004 | 1.26             |
| `tkRelIso < 0.1` (`highPtId == 2`)   | `NUM_LooseRelTkIso_DEN_HighPtIDandIPCut` | 1.0007 | 1.22             |

Soft ID is 1.3% below the POG at |η| 0.9–1.2 (other |η| bins within 0.5%).

- Without a POG counterpart, offline (`--no-pog --no-pu`, explicit edges):
  IsoMu22 (`--num-trigger 2:22`) and the Mu17 leg (`1:17`) run; the Mu17 leg
  plateau (30–120 GeV) is ε_data 0.96–0.99, SF 0.97–1.00. IsoMu22 is switched off in part
  of the data (fired in 0.61–0.63 of `HLT_IsoMu24` events in the G files,
  0.48–0.49 in H, 0.99 in MC; on or off per lumi section), so its SF is
  0.93–0.99 at 30–120 GeV and 0.53 at |η| 2.1–2.4, 22–24 GeV, where
  `IsoMu22_eta2p1` cannot provide the bit-2 object.
- MC statistics: on two independent halves of the MC (same data), the RMS of
  (SF_A − SF_B)/√(σ_mc,A² + σ_mc,B²) over 111 bins of tight ID, tight iso,
  IsoMu24 and medium ID was 1.04 ± 0.07 (with the MC counting error instead:
  4.7; 8.8 for tight iso); `mc_stat` of a half over the full sample followed √(N_full/N_half)
  within 15%. The finite-MC bias, (SF_A + SF_B)/2 − SF_full, was +0.001 to
  +0.004 per working point; the bootstrap mean and a split-half jackknife did
  not predict it.
- Median uncertainties at 30–60 GeV (tight ID, SF units): stat 0.0015, mc_stat
  0.0009, syst 0.0017 (background 0.0011, window 0.0004, tag 0.0007); POG systup −
  nominal 0.0032.
- correctionlib: every file loads and passes `correction validate`; nominal,
  `up`/`down` (`down` clipped at 0), `systup`/`systdown` and the quadrature
  of `stat`, `mc_stat`, `syst`, `fill` equal the `tnp.py` JSON or the
  documented fill to 2 × 10⁻¹⁶; η beyond 2.4 and pT outside the edges clamp.
  1–11 bins per file are filled from a neighbour; e.g. medium ID |η| 0.9–1.2,
  pT > 120 GeV (no failing MC probe) had a raw SF 0.877 ± 0.886 and is
  written as 1.002 ± 0.125.
- Data statistics: two halves of the data with the same MC gave an RMS of
  (SF_1 − SF_2)/√(stat_1² + stat_2²) of 0.85 ± 0.07 over 81 bins.
- Golden JSON: 95.6% of the data events are certified; with `--lumi-mask`
  the medium- and soft-ID SFs moved by at most 0.0009 at 30–60 GeV
  (0.0015 in any bin, at most 0.55 × the data-stat error).
- Soft ID is also 0.4% low in the barrel (0.9958); an independent review
  found the offset with a fit-free counting method and in G and H
  separately.
