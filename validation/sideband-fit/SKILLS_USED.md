# Skills used in the validation

| Source                                                                                                                                       | Application                                                                                                        |
| -------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| `plugins/background-est/skills/sideband-fit/SKILL.md`                                                                                        | Seed for blinding, integrated yields, covariance and toy diagnostics, then revised and exercised                   |
| `plugins/cms/skills/analysis-spec-builder/SKILL.md` and `plugins/cms/skills/analysis-spec-builder/assets/analysis-specification-template.md` | Specified sources, selections, observables, uncertainties and tooling before opening the held-out continuum counts |
| `plugins/cms/skills/hist/SKILL.md` and `plugins/cms/skills/hist/references/plotting-cms.md`                                                  | Filled a `hist` integer histogram and used `mplhep` CMS style, Open Data labels and a 3:1 main/residual plot       |
| `/uscms_data/d3/ashrivas/.codex/skills/.system/skill-creator/SKILL.md`                                                                       | Kept the entry point compact and put the generic JSON fitter and statistical reference in linked resources         |
| `CLAUDE.md`, `CONTRIBUTING.md`, `plugins/cms/agents/cms-analysis-coder.md`                                                                   | Marketplace structure, lab validation, credit, reproducible outputs and review handoff                             |

The work started from seed commit
`f48e8ccead09a445ca9c75f6add24ebfad25dd8b`, sideband-fit skill Git blob
`aa8b25d921019e6ce712ef249a489830e82d63a0`. The four-vectors in the workshop
CSV were already combined and the continuum input was already histogrammed.
They required neither the Awkward nor vector skills. The skill-creator
location above identifies the local installed skill and is outside the
portable workflow.

## First pass and changes

The seed stated that it had no executable helper. The first pass used its
sideband-normalized likelihood with a new generic NumPy/SciPy routine on
both spectra before revising the text. [First-pass evidence](first_pass.json)
records the selected orders, sideband deviances, expected yields and original
configuration digest. The workflow stores the full temporary first-pass
fit reports alongside the external run inputs.

- The seed specified a full covariance but left the output and parameter
  ordering open. The released CLI associates the normalization and
  shape covariance with bin and window covariance, and its masked counts
  are null. Joining variable-width bins now has a tested interface.
- The seed required distinct expected-yield and observed-count intervals.
  The implementation declares marginal log-delta intervals and integer
  Poisson-gamma quantiles and checks each separately against pseudoexperiments.
- The workshop link by itself did not state the CSV's input filtering.
  Reading the notebook identified combined four-vectors, no additional
  charge requirement and strict edges in the original subtraction.
- On the LCG view the first attempt failed with `No module named 'numpy'`
  when `PYTHONPATH` was replaced. The runner adds the fitter directory to
  `sys.path` and respects the existing environment.
- The initial high-mass figure clipped its last tick label, and the toy
  smoke panel clipped high-density bins. The final plotting code aligns the
  endpoint and scales both toy axes to the data.
- The first full ensemble exposed intermittent L-BFGS-B line-search
  failures. The released fitter retries from the failed endpoint once with a
  gradient tolerance inside the acceptance tolerance. The before-retry
  results and failure counts were preserved, and the same frozen ensemble
  was rerun with no physics changes.

## Rerun using the released skill

The documented histogram CLI was exercised on the workshop histogram
and the frozen continuum histogram. All fitted numbers agree with the
initial use. The release adds an optimizer-attempt count to the report. The final validation uses the
same helper through its Python interface. An independently implemented
composite Simpson integration checks the stored fitted means.
