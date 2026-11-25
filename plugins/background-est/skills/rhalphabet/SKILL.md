---
name: rhalphabet
description: >-
  Use when estimating the QCD multijet background under a jet-mass peak with
  the Rhalphabet or Alphabet method in a CMS boosted-jet analysis: measuring
  the pass-to-fail transfer factor of a jet tagger as a polynomial in jet pT
  and rho = 2 ln(m_SD/pT), with or without Combine; building an N2 DDT or a
  tagger cut map at constant QCD efficiency; choosing the rho range, pT and
  mass bins; fitting the transfer factor to QCD simulation and a residual to
  data (two-step TF); choosing the polynomial order with a toy F-test and
  checking goodness of fit; building the full pass and fail model with
  rhalphalib and Combine datacards; or debugging fits where transfer-factor
  parameters hit their limits, the fail-region parameters do not converge, or
  the pass prediction goes negative.
metadata:
  summary: Rhalphabet transfer factor (DDT preselection, two-step TF, toy F-test, GoF) with scripts, plus the full rhalphalib/Combine fit
---

# Rhalphabet

## Overview

For a large-radius jet, split events by a flavour or substructure tagger into
**pass** and **fail**. QCD in the pass region is the fail-region QCD times a
smooth transfer factor (TF):

```text
QCD_pass(pT, m) = R(pT, rho) * QCD_fail(pT, m),       rho = 2 ln(m_SD / pT)
R(pT, rho)      = R_MC(pT, rho) * TF_res(pT, rho)     (two-step, the default)
```

`R_MC` is fitted to QCD simulation; `TF_res`, a low-order polynomial (often
order 0 or 1), corrects it to data. Fail-region QCD has one free yield per
bin, so it comes from data. Resonant processes (W, Z, top, H) come from
simulation. Masses and pT in **GeV**.

Everything up to a measured TF needs only numpy, scipy and iminuit:
[scripts/tf_fit.py](scripts/tf_fit.py) and
[scripts/ddt_map.py](scripts/ddt_map.py). Combine is needed only for the full
fit with signal strengths or limits
([references/rhalphalib-model.md](references/rhalphalib-model.md)).

## When to Use

- QCD under a resonance in the soft-drop mass of a tagged AK8 (or wider) jet
- Measuring and validating the pass/fail transfer factor of a jet tagger
- 2D variant: jet mass against a second mass, `R` a 2D polynomial in both
- **Not** for a counting experiment with two independent variables (`abcd`)

## Workflow

Do the steps in order; each one's output is an input of the next.

1. **Selection** ([references/selection.md](references/selection.md)): a
   decorrelated two-prong preselection (N2 DDT) in pass AND fail, the tagger
   working point, candidate jet, lepton/MET/top suppression, gen-matched and
   flavour-split resonant templates, trigger plateau.
2. **Binning and rho range from simulation**: fail-region QCD msd shapes in
   rho per pT bin; keep the window where they agree. QCD-weighted mean pT per
   bin.
3. **Histograms** in the `tf_fit.py` format (pT x msd arrays): `data_pass`,
   `data_fail`, `qcd_pass`, `qcd_fail` and their `_w2`, `res_pass`, `res_fail`
   (all non-QCD MC), `ptmean`, `ptbins`, `msdbins`. Save as `.npz` or JSON.
4. **R_MC from QCD MC**:
   `python tf_fit.py mc --hists h.npz --rho LO HI --max-order 3 3 --out mc.json`.
   It fits every order up to the maximum and suggests one by a sequential
   F-test from (0, 0). Look at the chi2 table yourself; prefer the lowest
   order that describes the MC.
5. **TF_res in data**, signal window blinded in pass (`--blind LO HI`):
   `python tf_fit.py data --hists h.npz --rho LO HI --mc mc.json --mc-order a b --order 0 0 --blind LO HI --out fit.json`
   then the toy F-test from (0, 0) and the GoF:
   `python tf_fit.py ftest ... --lo 0 0 --hi 0 1 --toys 200`,
   `python tf_fit.py gof ... --order c d --toys 500`.
   `--float-mc` lets the MC coefficients float within their covariance;
   `--no-mc` gives the single-step TF for comparison. The `data` output
   includes `resonant_fraction` (pass and fail, per `res_<proc>_*` key).
6. **Validate beyond the fit** (checks 12-13):
   `python tf_fit.py loo ... --order c d` predicts each pT bin's pass yield
   from a fit without it; build the histograms twice (even / odd events),
   run `mc` on even and `data --pseudo-data --hists h_odd.npz` for the closure
   of the whole procedure on QCD MC.
7. **Report the TF**: map of `R` in (pT, rho) with its band (`R_lo`, `R_hi`),
   parameters and covariance, residual order, and the pT-summed ratio of
   fitted pass to fail QCD versus msd (`R_pf_vs_msd`, the quantity papers
   show). Plot post-fit pass data / prediction per pT bin. The quoted band is
   the statistical band **plus** the form systematic (check 11).

## Required before quoting a transfer factor

A TF is **not a result** until every row is done and written in the report.
If one is missing, say so next to the number.

| #  | Check | Pass condition |
| -- | ----- | -------------- |
| 1  | Decorrelation closure | `ddt_map.py closure --parity odd` on events not used for the map: `"pass": true`, i.e. global efficiency within 3% (relative) of the target and cell pull rms < 1.5 (or cell rms < 5% relative). Otherwise coarser cells or more smoothing |
| 2  | rho range | Plot of fail msd shapes vs rho per pT bin; masked bins identical in pass and fail |
| 3  | R_MC order | chi2/ndof of the chosen order ~1; next order not significant; no coefficient at 0 |
| 4  | TF_res order | Toy F-test from (0, 0), both directions at each step; go higher only if p < 0.05; on a tie raise rho first. **Borderline** (0.01 < p < 0.05) and the higher order has a coefficient at or within 1 sigma of a limit (check 6): take the lower order as nominal and the higher one as an alternative (check 8) |
| 5  | Goodness of fit | Saturated GoF with toys, p > 0.05 (0.05-0.1: say "borderline") |
| 6  | Parameters | None within 1 sigma of a limit; R positive everywhere |
| 7  | TF_res size | Within tens of percent of 1; if larger, explain (data/MC tagger differences) |
| 8  | Alternative function | One order higher in each direction, and the single-step TF (`--no-mc`), change R inside the band |
| 9  | Resonant subtraction | Pass-region fraction of W, Z, top, H stated; templates gen-matched |
| 10 | Blinding | Signal window masked in pass until 1-9 and 12-13 are done. Never print, plot, count or histogram data **pass** events in the window before that, not even in a diagnostic; apply the mask when reading the data, not only in the fit |
| 11 | Uncertainty | Statistical band (R_MC covariance + TF_res covariance) **plus** a form systematic: per bin, the largest change of R among the check-8 alternatives, added in quadrature. Quote both parts |
| 12 | Interpolation | `tf_fit.py loo`: every inner pT bin predicted within its band (\|pull\| < 2); edge bins are extrapolations, report them separately. A failure means the band is too small: enlarge the systematic or raise the pT order |
| 13 | Procedure closure | `--pseudo-data` on QCD MC events not used for `mc` (odd events): fitted pass QCD / true pass QCD per pT bin within MC statistics |
| 14 | Periods | With several data-taking periods, one TF_res per period or a test that one TF_res describes each (fit per period, compare) |

Not a check: **the fail region agrees with data by construction** (one free
yield per bin). Never quote fail-region agreement as validation.

## Comparing a TF with a published one

`R_pf_vs_msd` is summed over pT, and the rho window decides which pT bins
contribute at each msd (rho = 2 ln(m/pT)): steps appear where a pT bin enters
or leaves. Two TFs with different pT ranges or rho windows differ in shape for
that reason alone. Before comparing:

- match the paper's pT range, rho window, tagger working point (QCD mistag
  rate), two-prong preselection and vetoes, or list each difference;
- compare per pT bin if the paper gives them; otherwise only in the msd range
  where the same pT bins contribute in both (mark the steps on the plot);
- an extra selection the paper does not have (e.g. an AK4 b-veto) changes the
  QCD flavour composition and therefore the TF shape: compare without it, or
  show the TF with and without.

## Full fit (signal strengths, limits)

Build the pass/fail model with rhalphalib, the two-step TF carried by
decorrelated nuisances, and fit with Combine:
[references/rhalphalib-model.md](references/rhalphalib-model.md) (model,
blinding, several POIs, W/Z degeneracy),
[references/combine-recipes.md](references/combine-recipes.md) (toy F-test,
GoF, bias test, fit status),
[references/systematics.md](references/systematics.md),
[references/control-regions.md](references/control-regions.md) (muon top CR,
W-tag CR) and
[references/resonance-search.md](references/resonance-search.md) (mass scan).
The checks above still apply, plus a bias test and the W/Z signal strength.

## Gotchas

- **Scale pT and rho to [0, 1]** with the real first and last pT edges; a
  Bernstein polynomial is positive there for coefficients >= 0.
- **Mask the same rho bins in pass and fail.** Only the blinding window is
  pass-only.
- **Tagger not decorrelated** forces a high-order TF that can sculpt a peak:
  decorrelate first (step 1), then let `R_MC` absorb what is left.
- **TF parameter at a limit**: the order is too low or the normalisation is
  far from the data ratio; `tf_fit.py` normalises `TF_res` to the data, so
  coefficients start at 1.
- **Negative "data minus resonant MC"** in a fail bin: check the template
  normalisation and the mass binning.
- **Analytic F distribution** is fine for the weighted-MC chi2 (step 4) but
  not for the data residual: use toys generated from the lower order.
- **n_bins in the F-test** is the number of unmasked **pass** bins (the fail
  bins are fitted by their own yields).
- **Signal in fail**: keep it in the fail model or blind the window there too.
- **Data pass fraction differs from QCD MC** by tens of percent is common;
  that is what `TF_res` is for. Do not tune the MC to the data.
- **Several periods**: one `TF_res` per period; different taggers or
  calibrations per period change `R` (check 14).
- **Statistical band too small**: with many pass events the TF_res covariance
  is tiny; the leave-one-out test (check 12) and the alternatives (check 8)
  show the real precision. Report the form systematic, not just the band.
- **Plain Python vs Combine environment**: `tf_fit.py` and `ddt_map.py` run in
  a plain Python stack; rhalphalib's `renderCombine` needs ROOT. Pass arrays
  between them as JSON or `.npz` (numpy-2 pickles do not load in older CMSSW).

## Docs

- rhalphalib: <https://github.com/nsmith-/rhalphalib>
- 2DAlphabet: <https://github.com/ammitra/2DAlphabet>
- DDT: J. Dolen et al., "Thinking outside the ROCs", JHEP 05 (2016) 156, arXiv:1603.00027
- Combine: <https://cms-analysis.github.io/HiggsAnalysisCombinedLimit/>
