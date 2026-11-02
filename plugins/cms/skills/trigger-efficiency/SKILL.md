---
name: trigger-efficiency
description: >-
  Use when measuring or applying an HLT trigger efficiency in a CMS analysis:
  choosing signal and reference triggers from NanoAOD HLT_ branches, measuring
  a turn-on curve versus an offline variable (m_jj, HT, leading-jet pT, lepton
  pT) with the reference-trigger (orthogonal) method, computing Clopper-Pearson
  uncertainties near 100%, deciding the offline threshold where the efficiency
  plateaus, checking that a path exists in every run era of the data, or
  debugging a turn-on that is NaN, above 1, has zero error bars, or a KeyError
  on an HLT_ branch.
metadata:
  summary: Trigger turn-ons and offline thresholds from NanoAOD (reference method, Clopper-Pearson, plateau rule)
---

# Trigger efficiency

## Overview

An analysis trigger (or an OR of paths) is efficient only above some offline
threshold. Measure the efficiency in data with a **reference trigger** that
is independent of the signal paths, plot it against the offline variable the
analysis cuts on, and cut where it has plateaued. On NanoAOD each HLT path is
a boolean branch `HLT_<name>`. Offline kinematics are in **GeV**.

[scripts/list_hlt_paths.py](scripts/list_hlt_paths.py) shows which paths a
file has and how often they fire.
[scripts/turnon.py](scripts/turnon.py) holds the efficiency, threshold and
plotting helpers, plus a demo that measures the 2016 dijet turn-on from
JetHT Open Data.

## When to Use

- Choosing the signal-trigger OR and a reference trigger for a new analysis
- Measuring a turn-on curve and setting the offline cut (m_jj, HT, pT)
- Quoting a plateau efficiency and its uncertainty in `summary.json` or a note
- **Not** for trigger scale factors with tag-and-probe on leptons (use the
  POG recipes and their correctionlib JSON instead)

## Key Concepts

| Term                 | Meaning                                                                                                                                 |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------------- |
| Signal trigger(s)    | Paths the analysis selects events with; usually an OR of the lowest unprescaled jet/HT paths                                            |
| Reference trigger    | Lower-threshold path (often prescaled) or an orthogonal-dataset path, fully efficient where the signal turns on                         |
| Denominator          | Events passing the **full offline selection** and the reference trigger                                                                 |
| Numerator            | Denominator events that also fire the signal OR                                                                                         |
| Clopper-Pearson (CP) | Exact binomial interval; correct at ε → 1 where the Gaussian error goes to 0                                                            |
| Plateau / threshold  | Lowest bin edge above which every populated bin has CP upper bound ≥ target, the pooled ε ≥ target, and ≥ `min_events` reference events |

Prescales cancel in the ratio because numerator and denominator come from the
same events. Never take the numerator from one dataset and the denominator
from another.

## Canonical Patterns

### 1. See which paths exist and fire

```bash
source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh
<skill>/scripts/list_hlt_paths.py <one file per run era> --match '^(PFJet|PFHT|AK8PFJet|CaloJet)[0-9]'
# # files=2 events=200000 match=...
# 0.21907    21907 HLT_PFHT800  (absent in 1/2 files)     fraction over the files that have the path
# 0.11594    23188 HLT_PFHT900
```

Save the output (`> hlt_paths_2016G.txt`) as evidence of which menu you saw.

Run it on **one file from every era** you use. The output is the menu as
stored, which is the ground truth. Twikis list what was planned. In 2016,
`HLT_PFHT800` is a branch in Run2016G files but is **absent** from Run2016H
files (tested).

### 2. Measure the turn-on

```python
import sys; sys.path.insert(0, "<skill>/scripts")
from turnon import efficiency, find_threshold, plateau, plot_turnon

# per chunk: offline selection first, then the trigger bits of the SAME events
ref  = offline_sel & events["HLT_PFJet260"]
sigs = [t for t in SIGNAL if t in events.fields]           # some eras lack some paths
fired = np.logical_or.reduce([events[t] for t in sigs])
den += np.histogram(mjj[ref], edges)[0]
num += np.histogram(mjj[ref & fired], edges)[0]

e = efficiency(num, den)                       # eff, lo, hi (68% CP); NaN where den == 0
thr, i = find_threshold(e, edges, target=0.995, min_events=100)   # state target and min_events with the result
eff, lo, hi, n = plateau(e, i)                 # pooled efficiency above thr
plot_turnon(ax, e, edges, "ref. HLT_PFJet260", color="k")
plot_turnon(ax, e2, edges, "ref. HLT_PFHT475", dx=6, xerr=False, fmt="s")   # offset cross-check overlay
```

`DIJET_EDGES` in `turnon.py` is the full CMS dijet bin table (1–14000 GeV).
Slice it for the turn-on range, and use the same table for the fit so the
threshold is a bin edge. For HEPData or JSON, keep only bins with `den > 0`;
the efficiency is NaN elsewhere.

Accumulate counts, not efficiencies, over chunks, files and condor jobs. Add
`num` and `den` and form the ratio once at the end.

### 3. Check it

- Repeat with a **second and third reference** (e.g. `HLT_PFHT475`,
  `HLT_PFJet400`). The plateau and threshold should agree.
- The offline selection in the denominator must be the **analysis selection**
  (jet ID, |η|, |Δη_jj|, event filters, golden JSON). A looser selection moves
  the turn-on.
- Record the reference, the rule, the threshold, the plateau with its CP
  interval and the event counts. For example, from
  `validation/dijet-2016/summary.json` (all 142 files):
  `threshold 1058 GeV, plateau 0.99928 (+0.00012 −0.00015), 45776 ref. events`.

### Demo (also the skill's test)

```bash
F=$(for era in Run2016G Run2016H; do
      xrdfs root://eospublic.cern.ch ls -R /eos/opendata/cms/$era/JetHT/NANOAOD/UL2016_MiniAODv2_NanoAODv9-v1 \
        | grep '\.root$' | sort | head -3 | sed "s|^|root://eospublic.cern.ch/|"; done)
<skill>/scripts/turnon.py --demo $F --out turnon.png   # target 0.99
# THRESHOLD_GEV=1058  PLATEAU=0.99873  PLATEAU_LO=0.99705  PLATEAU_HI=0.99955  N_REF_ABOVE=1572
```

Tested on cmslpc (LCG_109): 6 files, 75 s, 2 GB RSS. It reproduces the
threshold of the full 142-file validation. The demo skips the golden JSON and
event filters, so use it as a check, not as a result.

## Gotchas

- **`KeyError: 'HLT_PFHT800'`** (or any path) when reading several eras: the
  branch exists only in some files. Build the path list per file from
  `tree.keys()` and OR only the present ones.
- **Zero error bars at ε = 1** come from Gaussian/binomial `sqrt(ε(1−ε)/n)`.
  Use Clopper-Pearson (`scipy.stats.beta.ppf`, as in `turnon.py`).
- **`errorbar` draws nothing or warns** when a bin has `den == 0`: ε is NaN.
  Mask empty bins before plotting (`plot_turnon` does). Never write NaN to
  HEPData or JSON.
- **ε > 1** means the numerator is not a subset of the denominator. The
  reference or the offline selection was applied to the denominator only.
  `efficiency()` raises on this.
- **Threshold too low in sparse bins.** With a handful of events, every
  high-mass bin is "compatible with 1". Require a minimum number of reference
  events above the threshold (`min_events`) and quote the pooled plateau.
- **The target changes the threshold.** The full validation (target 0.995)
  and the 6-file demo (0.99) both gave 1058 GeV, but that need not hold
  elsewhere. State the target with the result.
- **`no plateau found`** (exit 1 from the demo) on one file: the prescaled
  reference has only a few hundred events per file above 1 TeV. Use more
  files.
- **Reference prescales change with run.** That is fine for the ratio, but a
  reference with very few events above the turn-on gives a weak plateau.
  Pick the reference with the most events where it matters, then cross-check.
- **MC trigger emulation** was not validated here. The dijet validation
  requires m_jj above the data plateau and applies no trigger to MC. Do the
  same, or validate the MC HLT bits against data first.
- **Memory.** Read only the needed branches (`tree.iterate(cols,
step_size=...)`). The demo peaks at 2 GB for 6 JetHT files.

## Reference Files

- [scripts/list_hlt_paths.py](scripts/list_hlt_paths.py): HLT paths in a
  file with firing fractions (`--match`, `--json`; exit 1 if none match).
- [scripts/turnon.py](scripts/turnon.py): `clopper_pearson`, `efficiency`,
  `find_threshold`, `plateau`, `plot_turnon`, the CMS dijet bin edges, and
  the `--demo`.
- [references/dijet-2016-example.md](references/dijet-2016-example.md): the
  full worked example from the dijet-2016 validation (triggers, numbers,
  cross-checks, decisions).

## Docs

- CMS Collaboration, "The CMS trigger system", JINST 12 (2017) P01020,
  <https://arxiv.org/abs/1609.02366>
- CMS Open Data guide, triggers:
  <https://cms-opendata-guide.web.cern.ch/analysis/selection/triggers/>
- Dijet trigger-efficiency method in a CMS search: CMS-EXO-16-056,
  <https://arxiv.org/abs/1806.00843>
- Clopper-Pearson via the beta distribution:
  <https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.beta.html>
- Golden JSON for 2016 Open Data: <https://opendata.cern.ch/record/14220>
