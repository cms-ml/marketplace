# Sideband-fit skill validation task

Use the repository's `background-est:sideband-fit` seed and CMS analysis
and plotting skills to estimate a smooth continuum from blinded mass
sidebands. Write the analysis specification and freeze the rules before
inspecting continuum test-bin counts.

## Task

- Recompute the exact workshop `J/psi` subtraction from its linked
  public dimuon CSV. Fit positive bin-integrated models outside the
  excluded peak and compare estimates. Use the fixed Open Data 2016G/H
  dimuon-workflow snapshot for a genuine masked closure test. Reuse only
  original event counts and edges there.
- Test zero-count bins, covariance propagation, and a generic histogram
  interface. Produce CMS-style plots with black observations, a red fit,
  uncertainty bands, excluded-window shading, and a 3:1 fit/residual
  layout. Show the correct data and toy labels.
- Run background-only and nonzero signal ensembles using a signed signal
  yield and include integrated tails in the sidebands. Assess unrestricted
  bias and pull distributions on in-family and alternative truth shapes.
  Report coverage for the fixed order and for the model-selection
  procedure, along with fit, failure and boundary accounting.
- Deliver a reusable skill and reproducible evidence, including input
  checksums, a small empirical summary, PDF and PNG figures and a
  stdlib-only check. Use a bounded local smoke run and a final 600 toys
  per truth and injection. Keep source data and large arrays out of Git.
- Hand the immutable student commit to the separate reviewer for
  comparisons to CMS publications and HEPData using its independent
  frozen plan and primary sources.

See [the validation README](README.md) for the runnable entry points.
