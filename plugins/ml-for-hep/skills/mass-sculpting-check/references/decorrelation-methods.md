# Decorrelation methods

Read this reference when `sculpting.py` reports `SCULPTED` and you must
choose how to decorrelate the score from the mass, or when a reviewer asks
which method was used and why.

## Contents

1. Choosing a method
2. After training: DDT / fixed-efficiency maps
3. Before training: remove the mass information (inputs, flattening, planing)
4. During training: adversary, DisCo, MoDe
5. How to report it

## 1. Choosing a method

| Method                                    | When it fits                                        | Cost                                           | In this plugin                                                          |
| ----------------------------------------- | --------------------------------------------------- | ---------------------------------------------- | ----------------------------------------------------------------------- |
| DDT / fixed-efficiency map                | one or a few working points, model already trained  | none (post-processing); loses rejection        | `ddt.py` (tested)                                                       |
| Drop or rescale mass-like inputs          | BDT with explicit kinematic inputs                  | retrain                                        | feature module (`pt / m`)                                               |
| Flatten / plane the training              | any model; standard for jet taggers                 | retrain; needs events over the full mass range | weaver `reweight_method: flat` (smoke-tested in `particlenet-training`) |
| Mass-decorrelated ("MD") training samples | taggers: signal generated with a flat mass spectrum | dedicated samples                              | not available here                                                      |
| Adversarial training                      | strong decorrelation needed at all working points   | two networks, unstable, tuning                 | not implemented                                                         |
| DisCo (distance-correlation penalty)      | as above, one extra loss term                       | large batches, one hyperparameter              | not implemented (metric only)                                           |
| MoDe                                      | allow a controlled linear/quadratic dependence      | custom loss                                    | not implemented                                                         |

Start with the cheapest that passes the check. Only the first three rows
were exercised when this skill was written; the training-time methods are
described from the literature and are untested here.

## 2. After training: DDT / fixed-efficiency maps

Original DDT: transform a substructure variable (τ21) linearly in
ρ = log(m²/pT²) so that its background distribution no longer depends on
the mass. Generalised form used by CMS taggers: in bins of (ρ, pT), find
the score threshold with background efficiency X% and cut on
`score − threshold(ρ, pT)`. `ddt.py` implements the one-dimensional version
(mass only) with quantile bins and linear interpolation.

- Fit the map on a sample independent of the one used for the test and for
  the analysis (training folds here; in data, a control region).
- One map per working point.
- If the tagger also depends on pT, bin the map in pT too (make one map per
  pT bin with a pandas query on the input table).
- The map is smooth only if every bin has enough background (`ddt.py`
  refuses fewer than 50 events per bin).

## 3. Before training: remove the mass information

- **Inputs.** Divide momenta by the mass (`pt / m_jj`), use angles and
  ratios, leave out the mass itself. Necessary but not sufficient: the
  example BDT uses only mass-scaled inputs and still fails at the loose
  working point.
- **Flattening.** Weight signal and background so that both have the same
  (flat) distribution in mass and pT during training; the network cannot
  gain by learning the mass prior. weaver does this with `reweight_method:
flat`, `reweight_vars` and `reweight_classes` in the data config.
- **Planing.** The same idea as a diagnostic: weight away one variable and
  see how much performance is lost; what is left is information beyond that
  variable.
- Weights from flattening can be large in sparse bins: cap them, and check
  the effective sample size.
- Flattening removes the prior, not the dependence: a network can still
  reconstruct the mass from the constituents. Always re-run the check.

## 4. During training

- **Adversary.** A second network tries to predict the mass from the
  classifier output; the classifier is penalised when it succeeds
  (loss = L_class − λ L_adv).
- **DisCo.** Add λ × dCorr²(score, mass) computed on the background of each
  batch. One network, one λ; needs batches of a few thousand for a stable
  estimate. `sculpting.py` reports the same distance correlation as `DCOR`.
- **MoDe.** Constrain the background efficiency to be flat, linear or
  quadratic in the mass by penalising higher Legendre moments.
- For each, scan λ and plot rejection (R50) against 1/JSD: report the curve,
  then choose the point the background model can live with.

## 5. How to report it

State the method, the working points, and for each working point χ²/ndf,
p-value, JSD with its statistical floor, and the before/after pair
(R50, 1/JSD at 50% signal efficiency). Put `sculpting.json` (before and
after) in the model card.

## References

- J. Dolen et al., DDT, JHEP 05 (2016) 156, <https://arxiv.org/abs/1603.00027>
- G. Louppe, M. Kagan, K. Cranmer, "Learning to Pivot with Adversarial
  Networks", <https://arxiv.org/abs/1611.01046>
- C. Shimmin et al., "Decorrelated Jet Substructure Tagging using
  Adversarial Neural Networks", <https://arxiv.org/abs/1703.03507>
- S. Chang, T. Cohen, B. Ostdiek, "What is the Machine Learning?"
  (planing), <https://arxiv.org/abs/1709.10106>
- G. Kasieczka, D. Shih, "DisCo Fever: Robust Networks Through Distance
  Correlation", <https://arxiv.org/abs/2001.05310>
- O. Kitouni et al., "Enhancing searches for resonances with machine
  learning and moment decomposition" (MoDe), <https://arxiv.org/abs/2010.09745>
- CMS, JINST 15 (2020) P06005, <https://arxiv.org/abs/2004.08262>
  (mass-decorrelated DeepAK8)
