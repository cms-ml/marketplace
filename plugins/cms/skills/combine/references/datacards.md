# Datacard patterns (offline fallback)

Read this reference when you need a datacard, a parametric workspace or a
standard Combine command and the `combine` MCP server is unreachable (off the
CERN network). It is a minimal, tested core, not a substitute for the server:
when the server is available, search the documentation instead, which covers
far more (every method and option, the paper, the source code and the forums).

Every card, script and command below was run with Combine v11.1.0 and ROOT
6.34 (standalone build); the printed numbers are from those runs.

## Contents

1. [Counting experiment](#counting-experiment)
2. [Common commands](#common-commands)
3. [Template shape analysis](#template-shape-analysis)
4. [Unbinned parametric fit](#unbinned-parametric-fit)
5. [Binned parametric background (RooParametricHist)](#binned-parametric-background-rooparametrichist)
6. [Notes](#notes)

## Counting experiment

```text
# Counting experiment: one signal region, one background
imax 1  number of bins
jmax 1  number of backgrounds
kmax *  number of nuisance parameters
------------
bin          sr
observation  12
------------
bin          sr     sr
process      sig    bkg
process      0      1
rate         4.0    9.6
------------
lumi     lnN   1.025  1.025
sig_eff  lnN   1.05   -
bkg_cr   gmN 60  -    0.16
```

- `process` IDs: signal ≤ 0, backgrounds > 0. `rate` is the expected yield.
- `lnN 1.05` is a 5% log-normal normalisation uncertainty; `-` means "does not
  apply".
- `gmN 60 … 0.16`: the background is estimated from 60 events in a control
  region times an extrapolation factor 0.16, so its `rate` must be
  60 × 0.16 = 9.6.

## Common commands

The datacard (`.txt`) can be passed directly, or converted once with
`text2workspace.py card.txt -o card.root` and the `.root` passed instead
(faster when you run several methods, needed for physics models with `-P`).

| Goal                                    | Command                                                                                              | Output on the card above                                |
| --------------------------------------- | ---------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| Upper limit (CLs, asymptotic)           | `combine -M AsymptoticLimits card.txt -m 125`                                                        | `Observed Limit: r < 2.5231`, median `1.9766`           |
| Expected limit only (blind)             | `combine -M AsymptoticLimits card.txt -m 125 --run blind`                                            | median `r < 2.0000`                                     |
| Observed significance                   | `combine -M Significance card.txt -m 125`                                                            | `Significance: 0.686363`                                |
| Expected significance (signal injected) | `combine -M Significance card.txt -m 125 -t -1 --expectSignal 1`                                     | `Significance: 1.1557`                                  |
| Signal strength with uncertainty        | `combine -M MultiDimFit card.txt -m 125 --algo singles`                                              | `r : +0.601 -0.601/+0.996 (68%)`                        |
| Fit diagnostics (pre/post-fit, pulls)   | `combine -M FitDiagnostics card.txt -m 125`                                                          | `Best fit r: 0.600643 -0.600643/+0.99609`               |
| Likelihood scan                         | `combine -M MultiDimFit card.txt -m 125 --algo grid --points 30 --setParameterRanges r=0,5 -n .scan` | 31 points in `higgsCombine.scan.MultiDimFit.mH125.root` |

- `r` is the signal strength (signal yield / `rate`). Its default range is
  [0, 20]; widen or narrow it with `--rMin`/`--rMax` or `--setParameterRanges`.
- `-t -1` fits the Asimov dataset instead of the data.
- `FitDiagnostics --saveShapes --saveWithUncertainties` adds pre- and post-fit
  histograms to `fitDiagnosticsTest.root` (`shapes_prefit/`, `shapes_fit_s/`,
  `shapes_fit_b/`).
- `MultiDimFit --saveFitResult` writes `multidimfitTest.root` with the fitted
  parameters in `fit_mdf`.

## Template shape analysis

Histograms in a ROOT file, one per process, plus `Up`/`Down` templates for
each shape systematic:

```python
import ROOT

f = ROOT.TFile("shapes.root", "RECREATE")
def hist(name, contents):
    h = ROOT.TH1F(name, name, len(contents), 0.0, 100.0)
    for i, c in enumerate(contents, start=1):
        h.SetBinContent(i, c)
        h.SetBinError(i, 0.1 * c)          # MC stat error, used by autoMCStats
    h.Write()

hist("sig",          [1, 3, 6, 3, 1])
hist("bkg",          [40, 30, 20, 12, 8])
hist("bkg_jesUp",    [42, 32, 21, 12, 7])   # shape systematic: up and down
hist("bkg_jesDown",  [38, 28, 19, 12, 9])   # templates, same binning
hist("data_obs",     [41, 33, 27, 15, 9])
f.Close()
```

```text
# Template shape analysis: histograms from shapes.root
imax 1  number of bins
jmax 1  number of backgrounds
kmax *  number of nuisance parameters
------------
shapes * * shapes.root $PROCESS $PROCESS_$SYSTEMATIC
------------
bin          sr
observation  -1
------------
bin          sr     sr
process      sig    bkg
process      0      1
rate         -1     -1
------------
lumi     lnN    1.025  1.025
jes      shape  -      1
bkg_norm rateParam sr bkg 1 [0,5]
* autoMCStats 10
```

- `rate -1` and `observation -1` take the yields from the histograms.
- `shapes * * file $PROCESS $PROCESS_$SYSTEMATIC`: the nominal histogram is
  named after the process, the variations `<process>_<syst>Up/Down`. Use
  `$CHANNEL/$PROCESS` when the file has one directory per bin.
- `jes shape - 1`: the `jes` templates of `bkg`, at 1σ.
- `bkg_norm rateParam sr bkg 1 [0,5]`: a free normalisation factor on `bkg`
  (fitted value 0.991 in this example).
- `* autoMCStats 10`: bin-by-bin MC statistical uncertainties from the
  histogram errors.

## Unbinned parametric fit

Pdfs and data from a RooWorkspace; the background shape and normalisation
float freely:

```python
import ROOT

w = ROOT.RooWorkspace("w")
mass = ROOT.RooRealVar("mass", "m_{#gamma#gamma} [GeV]", 100, 180)

# Signal: fixed shape (constant parameters); its yield is the datacard rate
mean = ROOT.RooRealVar("sig_mean", "", 125.0)
width = ROOT.RooRealVar("sig_width", "", 1.5)
sig = ROOT.RooGaussian("sig", "signal", mass, mean, width)

# Background: free shape parameter and free normalisation <pdf>_norm
p1 = ROOT.RooRealVar("bkg_p1", "slope", 0.03, 0.0, 0.2)
bkg = ROOT.RooGenericPdf("bkg", "background", "exp(-@0*(@1-100))", ROOT.RooArgList(p1, mass))
bkg_norm = ROOT.RooRealVar("bkg_norm", "background yield", 1000, 0, 5000)

# Data: unbinned toy from the background model (use your real dataset instead)
data = bkg.generate(ROOT.RooArgSet(mass), 1000)
data.SetName("data_obs")

for obj in (sig, bkg, bkg_norm, data):
    getattr(w, "import")(obj)
w.writeToFile("param_ws.root")
```

```text
# Unbinned parametric fit: pdfs and data from a RooWorkspace
imax 1  number of bins
jmax 1  number of backgrounds
kmax *  number of nuisance parameters
------------
shapes sig      cat0 param_ws.root w:sig
shapes bkg      cat0 param_ws.root w:bkg
shapes data_obs cat0 param_ws.root w:data_obs
------------
bin          cat0
observation  -1
------------
bin          cat0   cat0
process      sig    bkg
process      0      1
rate         20     1
------------
lumi     lnN   1.025  -
bkg_p1   flatParam
bkg_norm flatParam
```

- `shapes <process> <bin> <file> <workspace>:<object>` points at a pdf or
  dataset in the workspace.
- **`<pdf>_norm`**: a workspace object named after the pdf plus `_norm`
  multiplies that process's `rate`. With `rate 1` the yield is `bkg_norm`
  itself. In fit results it appears as `shapeBkg_bkg_cat0__norm`.
- **`flatParam`** declares a freely floating (unconstrained) parameter of the
  workspace. The docs call it not strictly necessary for profiled-likelihood
  methods, since Combine profiles floating parameters anyway, but it is good
  practice to declare them.
- Combine does not change which workspace parameters are constant: set signal
  shape parameters constant (as here) or constrain them with
  `name param <mean> <sigma>` lines.
- `getattr(w, "import")` works in every ROOT version (`import` is a Python
  keyword); recent ROOT also accepts `w.Import(...)`.

## Binned parametric background (RooParametricHist)

One free yield per bin, e.g. a background to be fixed by data or tied to a
control region:

```python
import array
import ROOT

ROOT.gSystem.Load("libHiggsAnalysisCombinedLimit")   # for RooParametricHist

w = ROOT.RooWorkspace("w")
edges = array.array("d", [200, 400, 600, 800, 1000])
met = ROOT.RooRealVar("met", "p_{T}^{miss} [GeV]", 200, 1000)
met.setBinning(ROOT.RooBinning(len(edges) - 1, edges))

data_th1 = ROOT.TH1F("data_obs_sr", "", len(edges) - 1, edges)
for i, n in enumerate([100, 50, 25, 10], start=1):
    data_th1.SetBinContent(i, n)
data = ROOT.RooDataHist("data_obs", "", ROOT.RooArgList(met), data_th1)

sig_th1 = ROOT.TH1F("sig_sr", "", len(edges) - 1, edges)
for i, n in enumerate([1, 2, 3, 8], start=1):
    sig_th1.SetBinContent(i, n)
sig = ROOT.RooDataHist("sig", "", ROOT.RooArgList(met), sig_th1)

# Background: one free yield per bin, a RooParametricHist over them, and its
# total as <pdf>_norm (a RooAddition of the bin yields)
bins = ROOT.RooArgList()
keep = []
for i, n in enumerate([100, 50, 25, 10], start=1):
    v = ROOT.RooRealVar(f"bkg_sr_bin{i}", "", n, 0, 5 * n)
    bins.add(v)
    keep.append(v)
bkg = ROOT.RooParametricHist("bkg", "", met, bins, data_th1)
bkg_norm = ROOT.RooAddition("bkg_norm", "", bins)

for obj in (data, sig, bkg):
    getattr(w, "import")(obj)
getattr(w, "import")(bkg_norm, ROOT.RooFit.RecycleConflictNodes())
w.writeToFile("parhist_ws.root")
```

```text
# Binned parametric background: one free yield per bin (RooParametricHist)
imax 1  number of bins
jmax 1  number of backgrounds
kmax *  number of nuisance parameters
------------
shapes data_obs sr parhist_ws.root w:data_obs
shapes sig      sr parhist_ws.root w:sig
shapes bkg      sr parhist_ws.root w:bkg
------------
bin          sr
observation  -1
------------
bin          sr     sr
process      sig    bkg
process      0      1
rate         -1     1
------------
lumi         lnN   1.025  -
bkg_sr_bin1  flatParam
bkg_sr_bin2  flatParam
bkg_sr_bin3  flatParam
bkg_sr_bin4  flatParam
```

- The binning of the observable must match the histograms (`setBinning` with
  the same edges).
- `bkg_norm` must be the sum of the bin yields (`RooAddition`) and the `rate`
  of `bkg` is 1. Import it with `RecycleConflictNodes()`, since it shares the
  bin parameters with the pdf.
- `keep` holds Python references so the bin parameters are not deleted before
  the import.
- To tie a control region to these bins, make the control-region yields
  `RooFormulaVar`s of the signal-region ones times a transfer factor; the
  Combine docs ("RooParametricHist gammaN for shapes") give the full example.

## Notes

- Check a new card with `text2workspace.py card.txt -o card.root` first: it
  stops on syntax and naming errors without running a fit, e.g. a misspelled
  systematic gives
  `RuntimeError: Failed to find bkg_jesxUp in file shapes.root (from pattern $PROCESS_$SYSTEMATIC, shapes.root)`.
- `-m 125` only sets the mass label in output file names unless the model
  depends on `MH`.
- For anything beyond these patterns (other methods, physics models,
  impacts, toys, discrete profiling), use the `combine` server's documentation
  search, from lxplus or over the CERN VPN.
