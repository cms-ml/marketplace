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
0.02–0.1% in the populated bins. The IsoMu24 offset is the same for every fit
and selection variation tried, but with bit 2 alone as the probe pass the
|η| > 0.9 bins come within 0.1% of the POG (barrel stays +1.1%). An
independent review (`validation/muon-tnp/REVIEW.md`) reproduced all numbers.
