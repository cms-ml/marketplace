# vector recipes for CMS analysis

Read this reference for kinematic patterns beyond the basics in SKILL.md:
system pT and MHT, rapidity vs pseudorapidity, Δφ conventions, boosts,
merging collections, coordinate conversions, and using vector without Awkward.
Snippets were run on CMS Open Data NanoAOD (RunIISummer20UL16 DY) with
vector 1.4.0 / awkward 2.6.3 (CMSSW_15_0_21) and vector 1.7.0 / awkward
2.8.12 (pip).

## Contents

1. [Event-level sums: system pT, MHT](#event-level-sums-system-pt-mht)
2. [Rapidity, pseudorapidity, angles](#rapidity-pseudorapidity-angles)
3. [Boosts](#boosts)
4. [Combining collections](#combining-collections)
5. [Coordinate conversions](#coordinate-conversions)
6. [vector without Awkward](#vector-without-awkward)

## Event-level sums: system pT, MHT

```python
sel_jets = jet[(jet.pt > 30) & (abs(jet.eta) < 2.4)]
jets_p4 = ak.sum(sel_jets, axis=1)          # Momentum4D per event (empty event -> zero vector)
ht  = ak.sum(sel_jets.pt, axis=1)           # scalar sum
mht = jets_p4.pt                            # |vector sum| in the transverse plane
mjj_all = jets_p4.mass                      # mass of all selected jets together
```

`ak.sum` over vector records gives a vector sum (vector registers this with
Awkward). Summing the `.pt` field gives the scalar HT.

## Rapidity, pseudorapidity, angles

| Quantity          | Property / method       | Note                                           |
| ----------------- | ----------------------- | ---------------------------------------------- |
| pseudorapidity η  | `.eta`                  | NanoAOD stores η                               |
| rapidity y        | `.rapidity`             | needs mass; differs from η for massive objects |
| Δφ in (−π, π]     | `a.deltaphi(b)`         | signed; take `abs()` for cuts                  |
| ΔR = √(Δη² + Δφ²) | `a.deltaR(b)`           | uses η                                         |
| ΔR with rapidity  | `a.deltaRapidityPhi(b)` | jet-clustering style ΔR                        |
| polar angle θ     | `.theta`                |                                                |

## Boosts

```python
z = p.a + p.b
a_rf = p.a.boostCM_of_p4(z)        # muon in the Z rest frame
(a_rf + p.b.boostCM_of_p4(z)).pt   # ~0 (checked: ~1e-6 GeV)
cos_theta = np.cos(a_rf.theta)     # helicity-style angle w.r.t. the lab z-axis
```

`boostCM_of_p4(parent)` boosts into the parent's centre-of-mass frame. The
general forms are `boost_p4(p4)` (boost _by_ the four-vector's velocity) and
`boost_beta3(beta3)`.

## Combining collections

```python
leptons = ak.concatenate([muons_p4, electrons_p4], axis=1)   # same fields + with_name on both
leptons = leptons[ak.argsort(leptons.pt, axis=1, ascending=False)]
```

Both inputs must have the same fields (e.g. zip both with `pt, eta, phi, mass,
charge`) for the result to stay a `Momentum4D` record.

## Coordinate conversions

```python
mu.px, mu.py, mu.pz, mu.E          # derived from pt/eta/phi/mass on the fly
mu.to_Vector2D()                   # drop to the transverse plane (px, py access)
mu.to_xyzt()                       # convert storage to Cartesian
```

Results are stored in whatever system the operation produces: `a + b` gives
`rho, phi, eta, tau`, and `ak.sum(..., axis=1)` gives `x, y, z, t`. Always read
them through properties (`.pt`, `.mass`, `.eta`), never by field name.

## vector without Awkward

```python
v = vector.array({"pt": [10.0, 20.0], "eta": [0.0, 1.0], "phi": [0.0, 1.0], "mass": [0.1, 0.1]})
v.mass                                   # NumPy-backed, flat arrays
o = vector.obj(pt=10, eta=0, phi=0, mass=0) + vector.obj(pt=10, eta=0, phi=np.pi, mass=0)
o.mass                                   # 20.0: two back-to-back 10 GeV massless particles
```

Use these for flat (one object per event) data or quick checks. Use Awkward
for jagged NanoAOD collections.
