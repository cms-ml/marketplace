---
name: vector-awkward
description: >-
  Use when computing kinematics in Python with the scikit-hep vector library,
  especially on Awkward arrays from CMS NanoAOD: building Momentum4D,
  Momentum3D or Momentum2D records with ak.zip(with_name=...), invariant
  masses of pairs (Z, dijet), deltaR or deltaphi between objects, finding
  the nearest jet to a lepton, transverse mass with MET, boosting to a rest
  frame, summing four-vectors, or debugging vector errors such as "no field
  named 'pt'" or "array does not have azimuthal coordinates".
metadata:
  summary: Four-vector kinematics on NanoAOD with vector + Awkward (masses, deltaR, mT, boosts)
---

# Vector with Awkward

## Overview

`vector` gives Awkward records physics behaviour: `.mass`, `.deltaR()`, `+`,
boosts. You tag a record with a vector type name and use standard field
names, so no hand-written kinematics are needed. CMS NanoAOD provides
`pt/eta/phi/mass` per object (`Muon_*`, `Jet_*`, `Electron_*`) and
`MET_pt/MET_phi` per event, all in **GeV**.

vector also works without Awkward, through NumPy (`vector.array`) and single
objects (`vector.obj`). Awkward is just the natural backend for jagged event
data.

## When to Use

- Invariant mass of pairs/triplets (Z→ℓℓ, dijet, top candidates)
- ΔR / Δφ between objects, nearest-object matching, isolation-style cones
- Transverse mass with MET, vector sums (MHT, system pT), boosts
- Errors about missing coordinates or fields on vector records

## Key Concepts

| Type name    | Use for                                   | Field names it understands                                 |
| ------------ | ----------------------------------------- | ---------------------------------------------------------- |
| `Momentum4D` | Particles (mass, boosts, sums)            | `pt, eta, phi, mass` / `px, py, pz, E` (also `energy`, `M`) |
| `Momentum3D` | Directions (deltaR) without mass          | `pt, eta, phi` / `px, py, pz`                              |
| `Momentum2D` | MET, transverse quantities                | `pt, phi` / `px, py`                                       |
| `Vector4D`   | Generic (non-momentum) 4-vectors          | `x, y, z, t` (**not** `px…E` and **no** `.pt`)             |

Extra fields (e.g. `charge`, `btag`) ride along on the record and survive
selections. They are dropped by arithmetic (`a + b`).

## Canonical Patterns

### Register and build records

```python
import awkward as ak, numpy as np, vector
vector.register_awkward()                      # once per session, before using vector methods

mu  = ak.zip({"pt": arr.Muon_pt, "eta": arr.Muon_eta, "phi": arr.Muon_phi,
              "mass": arr.Muon_mass, "charge": arr.Muon_charge}, with_name="Momentum4D")
jet = ak.zip({"pt": arr.Jet_pt, "eta": arr.Jet_eta, "phi": arr.Jet_phi,
              "mass": arr.Jet_mass}, with_name="Momentum4D")
met = ak.zip({"pt": arr.MET_pt, "phi": arr.MET_phi}, with_name="Momentum2D")   # one per event
```

Reading NanoAOD with uproot (including the XRootD backend) is covered by the
`awkward-array` skill.

### Pair mass, ΔR, Δφ

```python
p = ak.combinations(mu, 2, fields=["a", "b"])
p = p[p.a.charge != p.b.charge]          # charge still available here
z = p.a + p.b                            # Momentum4D; .mass .pt .rapidity
mll = ak.flatten(z.mass, axis=1)         # ~91 GeV peak on DY
dr, dphi = p.a.deltaR(p.b), p.a.deltaphi(p.b)
```

### Nearest jet to each muon

```python
mj = ak.cartesian({"m": mu, "j": jet}, axis=1, nested=True)   # per muon: all jets
dr = mj.m.deltaR(mj.j)                                         # events * muons * jets
i  = ak.argmin(dr, axis=2, keepdims=True)
nearest_jet, nearest_dr = ak.firsts(mj.j[i], axis=2), ak.firsts(dr[i], axis=2)
```

### Transverse mass with MET

```python
lead = ak.firsts(mu)                                            # None if no muon
mt = np.sqrt(2 * lead.pt * met.pt * (1 - np.cos(lead.deltaphi(met))))
```

`Momentum4D.deltaphi(Momentum2D)` works directly. `met.px` and `met.py` are
available, but `met.eta` is not (it's 2D).

### Sums and boosts

```python
jets_p4 = ak.sum(jet, axis=1)            # per-event vector sum of all jets (Momentum4D)
ht = ak.sum(jet.pt, axis=1)              # scalar HT
a_rf = p.a.boostCM_of_p4(z)              # muon in the Z rest frame
```

More recipes and the NumPy/object backends:
[references/recipes.md](references/recipes.md).

## Gotchas

- **`Vector4D` with `px/py/pz/E` has no `.pt`**: it raises `AttributeError: no
  field named 'pt'`. Use `Momentum4D` for momentum-named fields.
- **Field names must match exactly.** `Pt` or `Muon_pt` give `ValueError: array
  does not have azimuthal coordinates (x/px, y/py or rho/pt, phi)`. Rename in
  `ak.zip` (NanoAOD branches → `pt/eta/phi/mass`).
- **Arithmetic drops extra fields and changes storage.** `(a + b).fields` is
  `['rho', 'phi', 'eta', 'tau']` and `ak.sum(jets, axis=1)` gives
  `['t', 'z', 'x', 'y']`, with `charge` gone in both. Use the properties
  (`.pt`, `.mass`), not `["pt"]`, and keep metadata from the inputs (`p.a.charge`).
- **Call `vector.register_awkward()` before `ak.zip`.** Records zipped
  _before_ registering stay plain even after you register:
  `AttributeError: no field named 'deltaR'`. Re-zip them. Before
  registration, a `.mass` you see is just the raw field.
- **Keep the mass.** NanoAOD stores `*_mass` for muons, electrons and jets.
  `Momentum3D` has no mass, so sums of `Momentum3D` cannot give invariant
  masses. Zip `mass` in and use `Momentum4D`.
- **Nested shapes.** `ak.cartesian(..., nested=True)` adds a level, so reduce
  with `axis=2` (or `-1`). `ak.firsts(..., axis=2)` removes the `keepdims`
  level.
- **Units are GeV** in NanoAOD.
- **Versions.** Tested with vector 1.4.0 (CMSSW_15_0_21) and 1.7.0 (pip),
  with identical results.

## Reference Files

- [references/recipes.md](references/recipes.md): read for more patterns
  (system pT/MHT, rapidity and η, Δφ conventions, boosts, combining
  collections), the NumPy and `vector.obj` backends, and coordinate
  conversions.

## Docs

- vector: <https://vector.readthedocs.io/>
- Awkward integration: <https://vector.readthedocs.io/en/latest/src/awkward.html>
- Adapted from the IRIS-HEP marketplace `vector-awkward` skill
  (BSD 3-Clause; see `plugins/cms/VENDORED-LICENSES.md`):
  <https://github.com/iris-hep/marketplace/tree/main/iris-hep/skills/vector-awkward>
