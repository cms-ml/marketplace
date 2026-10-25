# Ranges and binning for CMS NanoAOD variables

Read this reference when choosing histogram ranges and binning before you
have looked at the data, or when slicing, rebinning or projecting with UHI.
Measured ranges come from 50,000 events of CMS Open Data
`DYJetsToLL_M-50_TuneCP5_13TeV-amcatnloFXFX-pythia8`
(RunIISummer20UL16NanoAODv9). Other samples, especially high-pT or BSM ones,
need wider ranges.

## Contents

1. [Starting points](#starting-points)
2. [Mass windows](#mass-windows)
3. [Measured NanoAOD ranges](#measured-nanoaod-ranges)
4. [UHI slicing and rebinning](#uhi-slicing-and-rebinning)

## Starting points

| Variable                                   | Suggested axis                           | Why                                      |
| ------------------------------------------ | ---------------------------------------- | ---------------------------------------- |
| Muon / electron pT                         | `Reg(50, 0, 200)` or `Var` with a tail   | NanoAOD muons start at 3 GeV             |
| Jet pT                                     | `Reg(50, 0, 300)`                        | NanoAOD AK4 jets start at 15 GeV         |
| Muon η                                     | `Reg(48, -2.4, 2.4)`                     | muon-system acceptance                   |
| Electron η                                 | `Reg(50, -2.5, 2.5)`                     | tracker acceptance                       |
| Jet η                                      | `Reg(50, -5, 5)` (or ±2.4/2.5 for b-tag) | jets extend into the forward calorimeter |
| φ                                          | `Reg(64, -π, π)`                         |                                          |
| MET pT                                     | `Reg(50, 0, 200)`                        | DY 99th percentile ≈ 90 GeV              |
| b-tag score (`Jet_btagDeepFlavB`, PNet, …) | `Reg(50, 0, 1)`                          | scores are probabilities in [0, 1]       |
| Multiplicities (`nJet`, `PV_npvsGood`)     | `Integer(0, 16)` / `Integer(0, 80)`      | integer axis, one bin per value          |
| ΔR                                         | `Reg(50, 0, 6)`                          |                                          |

## Mass windows

| Resonance | Mass (GeV) | Window                |
| --------- | ---------- | --------------------- |
| J/ψ       | 3.097      | `Reg(60, 2.6, 3.6)`   |
| Υ(1S)     | 9.46       | `Reg(60, 8.5, 11.5)`  |
| W         | 80.4       | mT: `Reg(50, 0, 160)` |
| Z         | 91.2       | `Reg(60, 60, 120)`    |
| H         | 125        | `Reg(60, 100, 160)`   |
| top       | 172.5      | `Reg(50, 0, 400)`     |

## Measured NanoAOD ranges

DY aMC@NLO, 50k events (all objects, before selection):

| Branch              | min   | 1%    | median | 99%  | max   |
| ------------------- | ----- | ----- | ------ | ---- | ----- |
| `Muon_pt`           | 3.0   | 3.1   | 30.6   | 138  | 34129 |
| `Muon_eta`          | −5.9  | −2.39 | 0.02   | 2.39 | 3.7   |
| `Jet_pt`            | 15.0  | 15.1  | 25.9   | 122  | 690   |
| `Jet_eta`           | −5.1  | −4.57 | 0.01   | 4.55 | 5.1   |
| `Jet_btagDeepFlavB` | 0.001 | 0.003 | 0.041  | 0.54 | 1.0   |
| `MET_pt`            | 0.06  | 2.9   | 25.7   | 90   | 312   |
| `nJet`              | 0     | 0     | 3      | 9    | 16    |
| `PV_npvsGood`       | 1     | 5     | 15     | 31   | 44    |

Rare extreme values (a 34 TeV muon, |η| > 2.4 muons) exist in NanoAOD before
quality cuts. They end up in the overflow bins, which is expected; select
objects before histogramming.

## UHI slicing and rebinning

```python
h[5j]                    # bin containing x = 5
h[0.3j:]                 # from x = 0.3 to the end (keeps overflow)
h[::2j]                  # rebin by 2      (same as h[::hist.rebin(2)])
h[:, sum]                # integrate the 2nd axis -> 1D
h.project("pt")          # keep only the named axis
h[{"region": "SR"}]      # dict form with axis names
h[hist.overflow]         # overflow bin content
h.values(), h.variances()  # NumPy arrays; errors = np.sqrt(h.variances())
```
