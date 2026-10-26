---
name: awkward-array
description: >-
  Use when working with jagged or variable-length arrays in Python with
  Awkward Array 2 (import awkward as ak): reading CMS NanoAOD or other ROOT
  ntuples into arrays with uproot, building per-object records with ak.zip,
  selecting objects or events with masks, counting with ak.num or ak.count,
  pairing objects with ak.combinations or ak.cartesian (dilepton masses,
  deltaR, jet cleaning), taking the leading object or argmax per event,
  following NanoAOD index branches such as Jet_muonIdx1, flattening for
  histograms, writing Parquet or JSON, or debugging awkward errors such as
  "cannot slice", "index out of range" or None values appearing in results.
metadata:
  summary: Jagged arrays with Awkward 2 on CMS NanoAOD (records, selection, combinatorics, indices, I/O)
---

# Awkward Array

## Overview

Awkward Array handles nested, variable-length data such as "a list of muons per
event" with NumPy-style vectorized operations, so no Python loops over events
are needed. CMS NanoAOD stores each collection as flat branches (`Muon_pt`,
`Muon_eta`, …) plus a counter (`nMuon`). uproot reads them as jagged arrays
(`N * var * float32`), and you zip them into records.

Workflow (from the IRIS-HEP skill this one is adapted from):

1. Build an event data model: `ak.zip` the branches of each collection.
2. Filter early: object masks, then event masks, before heavy combinatorics.
3. Do combinatorics and derived quantities.
4. Add derived values back as fields; repeat.
5. Flatten to NumPy only at the end, for histograms or fits.

CMS NanoAOD kinematics are in **GeV**.

## When to Use

- Reading NanoAOD or flat ntuples with uproot and selecting objects/events
- Dilepton/dijet masses, ΔR, pairings, jet–lepton cleaning
- Leading object, argmax/argmin per event, index branches (`*Idx*`)
- Shape errors (`cannot slice`, `index out of range`), unexpected `None`s
- Saving selected events to Parquet/JSON

For physics vectors (`Momentum4D`, `.deltaR`, `.mass`) use the `vector`
library with `vector.register_awkward()`. A short example is in the asset
script.

## Key Concepts

| Concept          | Meaning                                                                                             |
| ---------------- | --------------------------------------------------------------------------------------------------- |
| `axis=0`         | Events. `axis=1` (or `-1` for the innermost) is objects within an event                             |
| Type string      | `20000 * var * float32` means 20000 events, variable number of floats each. Print with `ak.type(x)` |
| Record           | `ak.zip({"pt": ..., "eta": ...})` gives `var * {pt, eta}`; access fields as `mu.pt` or `mu["pt"]`   |
| `ak.num(x, 1)`   | Number of entries per event (equals NanoAOD `nMuon`)                                                |
| `ak.count(x, 1)` | Number of **non-None** entries per event                                                            |
| Option type      | `?float32`: values may be `None`, produced by `ak.firsts`, `ak.mask`, `ak.pad_none`, argmax         |
| Masks            | Boolean arrays with the same jagged structure select objects; 1D per-event booleans select events   |

## Canonical Patterns

### Read NanoAOD

```python
import awkward as ak, numpy as np, uproot

url = "root://eospublic.cern.ch//eos/opendata/cms/.../NANOAODSIM/.../0082C29D-....root"
f = uproot.open(url)                                                   # pip env with fsspec-xrootd
# f = uproot.open(url, handler=uproot.source.xrootd.XRootDSource)      # inside CMSSW
arr = f["Events"].arrays(["Muon_pt", "Muon_eta", "Muon_phi", "Muon_mass", "Muon_charge",
                          "Jet_pt", "Jet_eta", "Jet_phi", "genWeight"],
                         entry_stop=20000)            # read only needed branches
mu_all = f["Events"].arrays(filter_name="Muon_*", how="zip", entry_stop=5).Muon  # auto-zip by prefix
```

See [io-and-environments.md](references/io-and-environments.md) for XRootD
backends, `cut=`, Parquet and JSON.

### Build records, select objects, then events

```python
muons = ak.zip({"pt": arr.Muon_pt, "eta": arr.Muon_eta, "phi": arr.Muon_phi,
                "mass": arr.Muon_mass, "charge": arr.Muon_charge})
jets = ak.zip({"pt": arr.Jet_pt, "eta": arr.Jet_eta, "phi": arr.Jet_phi})
good = muons[(muons.pt > 20) & (abs(muons.eta) < 2.4)]     # object mask: jagged booleans
sel = ak.num(good, axis=1) >= 2                           # event mask: one bool per event
good, jets, weights = good[sel], jets[sel], arr.genWeight[sel]   # SAME mask on every per-event array
```

### Pairs and cross-collection loops

```python
pairs = ak.combinations(good, 2, fields=["m1", "m2"])          # unique pairs within a collection
pairs = pairs[pairs.m1.charge != pairs.m2.charge]              # opposite sign
mll = np.sqrt(2 * pairs.m1.pt * pairs.m2.pt *
              (np.cosh(pairs.m1.eta - pairs.m2.eta) - np.cos(pairs.m1.phi - pairs.m2.phi)))

j, m = ak.unzip(ak.cartesian([jets, good], axis=1, nested=True))   # per jet: all muons
dphi = (j.phi - m.phi + np.pi) % (2 * np.pi) - np.pi
clean_jets = jets[ak.all(np.sqrt((j.eta - m.eta) ** 2 + dphi**2) > 0.4, axis=-1)]
```

`nested=True` keeps one list per jet, so reducing with `axis=-1` gives one
boolean per jet.

### Leading object and argmax

```python
lead_pt = ak.firsts(good.pt)                         # None where no muon; good.pt[:, 0] would raise
i = ak.argmax(good.pt, axis=1, keepdims=True)        # keepdims keeps [[i], [None], ...] for slicing
lead = ak.firsts(good[i])                            # general "best candidate" pattern
```

NanoAOD collections are already pt-ordered, so `ak.firsts(good.pt)` is the
leading one. Use argmax for other criteria (e.g. best b-tag score).

### Index branches (`Jet_muonIdx1`, `Electron_jetIdx`, …)

```python
idx = ak.mask(jets.muonIdx1, jets.muonIdx1 >= 0)    # -1 -> None
matched_mu_pt = muons.pt[idx]                       # None where no match
```

Index into the **unfiltered** collection: the indices refer to positions in
the original `Muon_*` arrays.

### Add fields, flatten for histograms

```python
good["pt_x2"] = good.pt * 2                     # top-level field (ak.with_field under the hood)
ev = ak.zip({"mu": good}, depth_limit=1)
ev["mu", "is_hard"] = ev.mu.pt > 50             # nested field
values = ak.to_numpy(ak.flatten(mll, axis=1))   # one entry per pair -> np.histogram / hist
sumw = float(ak.sum(ak.values_astype(weights, np.float64)))
```

The full tested example is
[assets/nanoaod_dimuon.py](assets/nanoaod_dimuon.py): a Z→μμ selection,
cleaning, index branches and weights, identical results in CMSSW and pip
environments.

## Gotchas

- **`-1` index branches silently pick the wrong object.** Awkward treats `-1`
  as "last element", so `muons.pt[jets.muonIdx1]` returns the _last_ muon for
  unmatched jets, and only raises when the event has no muons at all. Use
  `ak.mask(idx, idx >= 0)` first.
- **argmax without `keepdims=True` indexes events.** `a[ak.argmax(a, axis=1)]`
  silently returns whole events. Use `keepdims=True` then `ak.firsts`.
- **`x[:, 0]` raises `index out of range`** if any event's list is empty. Use
  `ak.firsts(x)`, or `ak.pad_none(x, 1, axis=1)[:, 0]`.
- **Mask shapes must match.** An object mask (jagged) and an event mask (1D)
  are different things. After an event mask, apply it to every other per-event
  array you keep (weights, other collections). Otherwise combining them fails
  with `cannot broadcast RegularArray of size N with RegularArray of size M`.
- **`ak.num` vs `ak.count`:** `num` counts slots, `count` skips `None`
  (`[[1, None, 3]]` gives `3` vs `2`).
- **float32 sums drift.** NanoAOD weights are `float32`. Summing millions of
  them is visibly off, so cast with `ak.values_astype(w, np.float64)` first.
- **`root://` needs an XRootD backend.** Plain pip uproot fails with "Install
  fsspec-xrootd". In CMSSW pass `handler=uproot.source.xrootd.XRootDSource`.
- **These functions don't exist:** `ak.abs` (use `abs()` / `np.abs`),
  `ak.take`, `ak.expand_dims`, `ak.stack` (`np.stack` works only on
  rectangular data), `ak.fill_like` (use `ak.full_like` / `ak.zeros_like`).
  `ak.max` and `ak.min` **do** exist.
- **`ak.from_json("file.json")` parses the string itself** as JSON. Pass
  `pathlib.Path("file.json")` to read a file.
- **Arrays are immutable.** `ak.with_field` / `arr["f"] = ...` rebind the
  variable, and attribute assignment (`arr.f = ...`) raises.
- **Versions differ.** CMSSW_15_0_21 ships awkward 2.6.3, while pip gives 2.8.x.
  Everything here was tested on both. In CMSSW, `export PYTHONNOUSERSITE=1` so
  `~/.local` packages don't shadow the release's.
- **Units are GeV** in CMS NanoAOD.

## Reference Files

- [references/operations.md](references/operations.md): read for the exact
  behaviour of reductions (`num`/`count`/`sum`/`max`), `axis` rules, sorting,
  argmin/argmax, flattening, option types, records and NumPy interop.
- [references/io-and-environments.md](references/io-and-environments.md): read
  when opening `root://` files, choosing branches/cuts in uproot, writing
  Parquet/JSON, or setting up awkward in CMSSW vs a pip environment.
- [assets/nanoaod_dimuon.py](assets/nanoaod_dimuon.py): run or adapt for a
  complete NanoAOD analysis skeleton (`--url`, `--entries`).

## Docs

- Awkward Array: <https://awkward-array.org/doc/main/>
- uproot: <https://uproot.readthedocs.io/>
- vector (Awkward behaviours): <https://vector.readthedocs.io/>
- NanoAOD branch documentation (CERN login): <https://cms-nanoaod-integration.web.cern.ch/autoDoc/>
- Adapted from the IRIS-HEP marketplace `awkward-array` skill
  (BSD 3-Clause; see `plugins/cms/VENDORED-LICENSES.md`):
  <https://github.com/iris-hep/marketplace/tree/main/iris-hep/skills/awkward-array>
