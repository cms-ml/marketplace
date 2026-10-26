---
name: hist
description: >-
  Use when creating, filling, slicing, rebinning, normalising or plotting
  histograms in Python with scikit-hep hist / boost-histogram and mplhep,
  especially from CMS NanoAOD arrays: choosing axes and binning for GeV
  quantities, weighted fills with genWeight (including negative weights),
  normalising MC to cross section times luminosity, categorical axes for
  regions, processes or systematics, UHI indexing, CMS-style plots with
  hep.cms.label, ratio panels, or errors such as "has no attribute 'Weight'",
  "Select 'histtype' from" or "cannot convert to RegularArray" when filling.
metadata:
  summary: Histograms with hist + mplhep for CMS (weights, normalisation, UHI, CMS-style plots)
---

# hist

## Overview

`hist` builds N-dimensional histograms (boost-histogram underneath) with
named axes, weighted storage and UHI indexing. `mplhep` plots them in the CMS
style. On CMS NanoAOD, values are in **GeV** and MC events carry `genWeight`,
which can be negative.

Typical flow: define axes and storage → fill with flattened arrays and
weights → normalise MC → slice/project → plot with the CMS label → save.

## When to Use

- Booking histograms for NanoAOD quantities; picking ranges and binning
- Weighted fills, MC normalisation, sum-of-weights errors
- Region/process/systematic bookkeeping with categorical axes
- CMS-style 1D/2D plots, stacks, ratio panels; plot errors

## Key Concepts

| Piece                                    | Use                                                                          |
| ---------------------------------------- | ---------------------------------------------------------------------------- |
| `Hist.new.Reg(n, lo, hi, name=, label=)` | Uniform bins                                                                 |
| `.Var([edges], name=)`                   | Variable bins (e.g. pT tails)                                                |
| `.Integer(lo, hi)`                       | Counts such as `nJet`, `PV_npvsGood`                                         |
| `.StrCat([...], growth=True)`            | Regions, processes, systematics                                              |
| `.Int64()` / `.Weight()`                 | Exactly one storage. `Weight` keeps Σw and Σw² for correct errors            |
| Flow bins                                | Under/overflow are kept. `h.values(flow=True)`, `h[hist.overflow]`           |
| UHI                                      | `h[5j]` = bin containing 5, `h[0.3j:]`, `h[::2j]` rebin, `h[:, sum]` project |

## Canonical Patterns

### Book and fill from NanoAOD

```python
import awkward as ak, numpy as np, hist
from hist import Hist

h_mll = Hist.new.Reg(60, 60, 120, name="mll", label=r"$m_{\mu\mu}$ [GeV]").Weight()
h_mll.fill(mll=ak.to_numpy(mll), weight=ak.to_numpy(w))     # 1 value per event

h_pt = Hist.new.Reg(50, 0, 200, name="pt", label=r"Muon $p_{T}$ [GeV]").Weight()
pt_flat = ak.flatten(muons.pt, axis=1)                         # jagged -> one entry per muon
w_flat = ak.flatten(ak.broadcast_arrays(w, muons.pt)[0], axis=1)
h_pt.fill(pt=pt_flat, weight=w_flat)
```

Jagged arrays must be flattened. Broadcast the per-event weight to objects
first, as above.

### Normalise MC to cross section × luminosity

```python
sumw = sum(float(ak.sum(uproot.open(f)["Runs"]["genEventSumw"].array()))
           for f in all_files_of_the_dataset)          # ALL files, before any cut
w = genWeight * xsec_pb * lumi_invpb / sumw            # per-event weight, float64
```

`Runs/genEventSumw` equals the sum of `genWeight` over every generated event.
Using the event count, or the sum after cuts, gives the wrong normalisation for
samples with negative weights.

### Regions, processes, systematics in one object

```python
h = (Hist.new.Reg(60, 60, 120, name="mll", label=r"$m_{\mu\mu}$ [GeV]")
     .StrCat(["SR", "CR"], name="region")
     .StrCat([], name="process", growth=True)
     .StrCat([], name="syst", growth=True)
     .Weight())
h.fill(mll=x, region="SR", process="DY", syst="nominal", weight=w)
h[:, "SR", "DY", "nominal"]              # 1D slice
h[:, "SR", sum, "nominal"]               # sum over processes
```

### Plot in the CMS style

```python
import matplotlib.pyplot as plt, mplhep as hep
plt.style.use(hep.style.CMS)
fig, ax = plt.subplots()
h[:, "SR", "DY", "nominal"].plot(ax=ax, histtype="fill", label="DY")
hep.cms.label("Preliminary", data=True, lumi=16.8, com=13, ax=ax)   # MC only: data=False
ax.set_ylabel("Events / 1 GeV")
ax.legend()
fig.savefig("mll.png")
plt.close(fig)
```

Stacks, data/MC ratio panels and 2D plots are in
[references/plotting-cms.md](references/plotting-cms.md). Suggested CMS
ranges and binning are in
[references/cms-binning.md](references/cms-binning.md).

## Gotchas

- **`Int64` silently ignores the meaning of weights.** Filling `.Int64()` with
  `weight=` raises no error, but the storage is integer and no Σw² is kept.
  Use `.Weight()` for any weighted fill.
- **Chaining storages fails.** `.Int64().Weight()` gives
  `AttributeError: 'Hist' object has no attribute 'Weight'`.
- **Negative weights.** aMC@NLO samples have negative `genWeight`s (16% of
  events in the tested DY sample, all with the same magnitude). Bins can go
  negative, so always use `Weight` storage and normalise with `genEventSumw`.
- **Jagged input fails** with `cannot convert to RegularArray`. Flatten with
  `ak.flatten(x, axis=1)` and broadcast weights to the same shape.
- **float32 sums.** `genWeight` is float32. Cast to float64 before summing
  (in CMSSW, a direct sum differed from the histogram's by 5,000 out of 1.1e8).
- **`histtype` depends on the mplhep version.** `fill, step, errorbar, band`
  always work. `bar, barstep` exist only in newer mplhep (1.x), and fail in
  CMSSW_15_0_21's 0.3.47 with `Select 'histtype' from: [...]`.
- **Un-normalised weights collide with the CMS label.** Raw `genWeight`
  (~25,000 per event) gives a `1e7` axis offset that mplhep 0.3.x draws under
  the "CMS" text. Normalise to σ×L first.
- **`.fill` returns the histogram**, not `None`, so `h = Hist...().fill(...)`
  chains.
- **Flow bins** are on by default. Values outside the axis land in
  under/overflow and are not shown. Check `h[hist.overflow]` when totals don't
  match.
- **Units are GeV** in NanoAOD. Put units in axis labels (`[GeV]`), and use raw
  strings for LaTeX (`r"$p_{T}$"`). In f-strings, double the braces.

## Reference Files

- [references/plotting-cms.md](references/plotting-cms.md): read for CMS
  labels (`hep.cms.label` options), stacked MC, data/MC ratio panels, 2D
  plots, and differences between mplhep 0.3.x (CMSSW) and 1.x (pip).
- [references/cms-binning.md](references/cms-binning.md): read when choosing
  axis ranges and binning for NanoAOD variables. It has measured ranges from
  NanoAOD, physics mass windows, and UHI rebinning/slicing recipes.

## Docs

- hist: <https://hist.readthedocs.io/>
- mplhep: <https://mplhep.readthedocs.io/>
- UHI indexing: <https://uhi.readthedocs.io/en/latest/indexing.html>
- Adapted from the IRIS-HEP marketplace `hist` skill (BSD 3-Clause; see
  `plugins/cms/VENDORED-LICENSES.md`):
  <https://github.com/iris-hep/marketplace/tree/main/iris-hep/skills/hist>
