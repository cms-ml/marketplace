---
name: hep-ml-data-prep
description: >-
  Use when preparing training data for a machine-learning model in a HEP
  analysis: turning NanoAOD or other ROOT ntuples into a flat feature table
  (Parquet) with labels, building per-event weights from cross section,
  luminosity and genWeight (including negative weights), choosing a
  train/validation/test split, padding jagged per-object inputs to a fixed
  length with a mask, deciding which variables may be inputs, checking a
  table for label leakage, truth-level inputs, NaN or constant features
  before training, or debugging a classifier whose AUC is suspiciously close
  to 1 or whose test performance collapses.
metadata:
  summary: Leakage-safe feature tables from NanoAOD (weights, event-number folds, pre-training checks)
---

# HEP ML data preparation

## Overview

Most broken HEP classifiers are broken in the data, not the model. This
skill produces **one flat Parquet table** with a fixed column contract that
every other `ml-for-hep` script reads, and checks it before any training.

| Script                                               | Does                                                                |
| ---------------------------------------------------- | ------------------------------------------------------------------- |
| [scripts/nano_to_table.py](scripts/nano_to_table.py) | ROOT samples → table with features, observers, label, weight, fold  |
| [scripts/check_table.py](scripts/check_table.py)     | PASS/FAIL: bad values, constants, truth-named inputs, label proxies |
| [assets/features_dijet.py](assets/features_dijet.py) | Example feature module (dijet resonance vs QCD); copy and edit      |

Both scripts: `--help`, `KEY=VALUE` on stdout, diagnostics on stderr, exit
0 ok / 1 check failed / 2 bad input. Kinematics are in **GeV**.

## When to Use

- Before any training with `bdt-training` (flat features)
- To decide the split and the weights once, for all later steps
- **Not** for constituent-level inputs of a jet tagger: `particlenet-training`
  reads and pads those itself (the padding pattern is below)

## Key Concepts

| Column       | Meaning                                                                                        |
| ------------ | ---------------------------------------------------------------------------------------------- |
| features     | every column that is not reserved and does not start with `obs_`                               |
| `obs_*`      | observers: mass, pT, the fit variable. Kept for sculpting/closure checks, **never trained on** |
| `label`      | 1 signal, 0 background, −1 data                                                                |
| `weight`     | `xsec × lumi × genWeight / Σ genWeight` (sign kept); 1 for data                                |
| `gen_weight` | raw generator weight                                                                           |
| `event`      | event number                                                                                   |
| `fold`       | `event % n_folds` (default 5): **the only split key**                                          |
| `sample`     | sample name                                                                                    |

**Split by event number.** Default use of the folds: 0–2 train, 3 validation
(early stopping, scans), 4 test (used once). A random row split puts jets or
candidates of one event on both sides and is not reproducible; a per-file
split correlates with run conditions. The event-number fold is also what
lets the analysis apply the model to the same MC it was trained on (apply
model k only to events not in its training folds).

**Weights.** Σ genWeight runs over all events **read** (before selection),
so the normalisation is right with `--max-events` too. Training later uses
|w| with balanced classes; all metrics use the signed weight.

**Inputs.** Allowed: reconstructed quantities available identically in data.
Not allowed: generator-level quantities (`GenPart_*`, `Jet_hadronFlavour`,
`Jet_genJetIdx`), anything derived from the label or sample, weights, event
or run numbers. The variable the analysis fits is an observer unless the
analysis decides otherwise.

## Canonical Patterns

### 1. Build the table

```bash
set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh
<skill>/scripts/nano_to_table.py --features <skill>/assets/features_dijet.py --lumi 16400 \
    --sample zp2000:1:1.0:<file>[,<file>...] --sample qcd1000:0:1117:<file> \
    --max-events 40000 -o <work>/table.parquet 2> prep.err
# N_ROWS=145945 N_SIG=106025 N_BKG=39920 N_DATA=0 N_FEATURES=11 NEG_WEIGHT_FRAC=0.0 OUTPUT=table.parquet
```

`--sample NAME:LABEL:XSEC_PB:FILES` (repeat per sample; `XSEC_PB` = `data`
for data), or `--samples samples.json`. Files may be `root://` URLs.
`--dry-run` reads 1000 events per file and writes nothing. The run also
writes `table.parquet.meta.json` (features, per-sample counts, Σ weights,
versions, command). Tested: 7 Z′ files + 40k QCD events over XRootD in about
a minute, 0.25 GB RSS for 31k events.

For another analysis, copy `features_dijet.py`: `BRANCHES` lists what to
read, `build(ev)` returns flat numpy arrays for the selected events plus
`"_mask"`. Use the `awkward-array` and `vector-awkward` skills (plugin `cms`)
for the array work.

### 2. Check it (gate: must PASS before training)

```bash
<skill>/scripts/check_table.py <work>/table.parquet --mass obs_mjj --json <work>/checks.json
# N_FEATURES=11 N_FAIL=0 N_WARN=4 FAILED=none
# WARNED=mass_corr:j1_pt_over_mjj,j2_pt_over_mjj,abs_deta_jj;low_neff:sig
# NEFF_SIG=979.0 NEFF_BKG=29940.0 TOP_SINGLE_AUC=j1_btag:0.8917 STATUS=PASS
```

| FAIL             | Meaning                         | Fix                                                  |
| ---------------- | ------------------------------- | ---------------------------------------------------- |
| `bad_values`     | NaN/inf in a feature            | fix the feature (division by zero, missing object)   |
| `constant`       | one value only                  | drop it                                              |
| `forbidden_name` | looks like truth or bookkeeping | drop it, or rename if the name is a false alarm      |
| `leakage`        | single-feature AUC > 0.98       | find out why; drop it unless the physics explains it |
| `fold_class`     | a fold lacks a class            | more events, or fewer folds                          |

Warnings (`mass_corr`, `low_neff`, `neg_weights`) do not fail the check, but
`mass_corr` predicts mass sculpting: plan the `mass-sculpting-check`.

### 3. Pad jagged inputs (per-object features)

```python
import awkward as ak, numpy as np
P = 2                                   # objects kept per event
pad  = ak.to_numpy(ak.fill_none(ak.pad_none(x, P, clip=True), 0.0)).astype(np.float32)
mask = ak.to_numpy(ak.fill_none(ak.pad_none(ak.ones_like(x), P, clip=True), 0.0)).astype(np.float32)
# x = [[1,2,3],[4],[]] -> pad [[1,2],[4,0],[0,0]], mask [[1,1],[1,0],[0,0]]
```

Sort by pT before padding, keep the mask as an input, and standardise with
statistics of the **training folds only**, computed on unmasked entries.
Tree models need no scaling; neural networks do.

## Gotchas

- **AUC ≈ 1 on the first try** is leakage until proven otherwise. Run
  `check_table.py`; look for a feature that differs by construction between
  the samples (a generator filter, a different skim, the sample's mass point).
- **Signal mass points as inputs.** A parametrised network needs the mass
  hypothesis assigned to background at random from the signal distribution;
  otherwise the mass input is a label proxy.
- **Partial samples and Σ genWeight.** Normalising a partly read sample with
  `Runs/genEventSumw` of the whole file overestimates the denominator. The
  script sums over the events it read.
- **`low_neff:sig` with thousands of rows** means few effective events
  (large weight spread, e.g. HT-binned QCD where a low-HT event carries a
  huge weight). Metrics will be noisy: add events in the dominant bins.
- **Different selections per sample** (a skim on one sample only) create
  features that separate samples, not physics. Apply one selection in
  `build()` for all.
- **Open Data Z′ files hold ~1000–20 000 events each**: `--max-events` is per
  file, so list several files for a small sample.
- **`check_table.py --features a,gen_weight`** printed
  `FAILED=constant:gen_weight;forbidden_name:gen_weight STATUS=FAIL` (exit
  1): the name filter also guards explicit feature lists.

## Docs

- Tested on cmslpc EL9 with LCG_109 (Python 3.13, uproot 5.6.0, awkward
  2.8.9, numpy 2.2.6, pandas 2.2.3, pyarrow 20.0.0) on CMS Open Data
  NanoAODv9 (`ZprimeToBB_narrow_M-2000`, `QCD_HT1000to1500`), 2026-11.
- uproot: <https://uproot.readthedocs.io/>; Awkward Array: <https://awkward-array.org/>
- NanoAOD branch documentation: <https://cms-nanoaod-integration.web.cern.ch/autoDoc/>
- P. Baldi et al., "Parameterized neural networks for high-energy physics",
  <https://arxiv.org/abs/1601.07913>
