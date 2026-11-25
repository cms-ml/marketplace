# Combine recipes for rhalphabet fits

Loaded from SKILL.md ("Full fit") and rhalphalib-model.md. The F-test and goodness-of-fit commands were run in an Open Data rhalphabet fit with Combine v10; the bias-test commands were run on the same fit (50 toys per point, Combine v10). For a TF-only study without Combine, `scripts/tf_fit.py` does the F-test and GoF.

## F-test, goodness of fit and bias test with Combine

Build one model directory per order (same masks, same templates). `L` is the
lower order, `H` the one-step-higher order. `N` toys, at least 200 for the
F-test and 500 for the final GoF.

```bash
# Data: saturated statistic for both orders
combine -M GoodnessOfFit --algo saturated -d L/model_combined.root -n _L
combine -M GoodnessOfFit --algo saturated -d H/model_combined.root -n _H

# Toys generated from the LOWER order (post-fit to data), saved to a file
combine -M GenerateOnly -d L/model_combined.root -t N -s 1 \
        --toysFrequentist --saveToys -n _gen
TOYS=higgsCombine_gen.GenerateOnly.mH120.1.root

# The SAME toys fitted with both orders
combine -M GoodnessOfFit --algo saturated -d L/model_combined.root -t N -s 1 \
        --toysFrequentist --toysFile $TOYS -n _L_toys
combine -M GoodnessOfFit --algo saturated -d H/model_combined.root -t N -s 1 \
        --toysFrequentist --toysFile $TOYS -n _H_toys
```

Read the `limit` branch of each output. Pair toys by the `iToy` index (drop
toys where either fit failed), compute
`F = [(l_L - l_H) / (p_H - p_L)] / [l_H / (n_bins - p_H)]` for data and for
each toy, and take `p = fraction of toys with F >= F_data`. `p` counts TF
parameters. For `n_bins` use the unmasked **pass** bins (equivalently, all
unmasked bins minus the free fail parameters, which fit the fail bins
exactly); counting the fail bins inflates the denominator and changes the
selected order. Do not use the analytic F distribution. Keep `-t N` on the
fitting commands when you pass `--toysFile`: without `-t` Combine fits the
data, and `-t -1` asks for an Asimov toy that is not in the file.

If the model has **no constrained nuisances** (e.g. a stat-only test),
`--toysFrequentist` fails with "no constraint terms"; use
`--toysNoSystematics` instead, and use the same flag for generation and
fitting. Adding the lumi and `autoMCStats` nuisances of the rhalphalib-model.md model avoids this. Start from (0, 0), and test both one-step directions from each
order (`(n+1, m)` and `(n, m+1)`).

**GoF of the chosen order:** the same `GoodnessOfFit` on data plus `-t 500
--toysFrequentist` on the chosen model; `p = fraction of toys >= data`.

**Bias test (do not skip):**

```bash
for R in 0 1; do        # 0 and the expected strength (1 for a known resonance)
  combine -M GenerateOnly -d model_combined.root -t 200 -s 2 --toysFrequentist \
          --saveToys --setParameters r_Z=$R -n _bias$R
  combine -M FitDiagnostics -d model_combined.root -t 200 -s 2 --toysFrequentist \
          --toysFile higgsCombine_bias$R.GenerateOnly.mH120.2.root \
          --redefineSignalPOIs r_Z --setParameterRanges r_Z=-3,5 -n _bias$R
done
```

From `fitDiagnostics_bias$R.root` tree `tree_fit_sb`, read the POI branches,
which are named after the POI (`r_Z`, `r_ZErr`, `r_ZLoErr`, `r_ZHiErr` with
`--redefineSignalPOIs r_Z`; plain `r` only for a single-POI model). Plot
`(r_Z - R) / err` with the asymmetric error on the side facing `R`. Report how
many toys have `fit_status == 0`: in a model with ~100 free fail parameters
about half the toy fits can return status 1 (covariance forced positive
definite). Quote the pull for status 0 only and for status 0 or 1, and use at
least 200 toys so the mean is known to better than 0.1. Report the mean and width of the pull for each `R`. Check on one
toy that the generated value is the one you set. If the bias is large, raise
the TF order or narrow the rho range; do not quote the result as is.

## Reading the fit

| MIGRAD status | covQual | Meaning                             | Action                                                                     |
| ------------- | ------- | ----------------------------------- | -------------------------------------------------------------------------- |
| 0             | 3       | Converged, accurate covariance      | OK                                                                         |
| 1             | 3       | Covariance forced positive definite | Refit with `--cminDefaultMinimizerStrategy 2`; OK only if the same minimum |
| 3             | any     | EDM above tolerance                 | Loosen `--cminDefaultMinimizerTolerance` or improve initial values         |
| any           | < 3     | Covariance not trustworthy          | Do not quote Hesse errors; use likelihood scans                            |
