# Follow-up task for the validator (resumed session): more validation plots

Sent by `run_followups.sh` with `claude -p --resume <validator session>` after the student follow-up.

## Task

Your comparison of run A and run B is done. Add more validation plots to `<OUT>/plots/` and update
`<OUT>/COMPARISON.md` and `<OUT>/comparison.json`. Naming, everywhere (plots, legends, tables, text; also fix the
existing plots and COMPARISON.md): run A = **"with skill"**, run B = **"without skill"**. Keep "CMS Open Data,
private work" on Open Data curves and "CMS EXO-17-021" on published ones.

The with-skill student has just added plots (see `<A>/PLOTS_DONE`, `<A>/plots/`, the "Plots" section of
`<A>/REPORT.md`): review them in a short new section of COMPARISON.md (correct, and do they support the analysis?).

Extracted CMS figure data (vector graphics of arXiv:1808.03124, already validated) are in
`<OUT>/ref/cms_extracted/`: `fig2_*.csv` (N-1 normalised m_asym, Delta-eta, tau21 and tau32 of both jets, data and
QCD), `fig4_points.csv`, `fig4_fit.csv`, `fig4_band_*.csv` (transfer factor B/D vs average pruned mass).

Plots (PNG + PDF), with skill and without skill side by side or overlaid:
1. `mavg_SR_vs_cms`: Fig. 5 style, per run observed and predicted m_avg with band, the CMS HEPData background
   normalised, ratio panels; plus an absolute panel with yields scaled by 35.9/16.3 and the CMS data/background.
2. `cmslike_od_vs_cms`: the EXO-17-021-like selection on Open Data vs CMS data and background.
3. `tf_vs_mavg_vs_cms`: both runs' transfer factors and the CMS-like Open Data B/D, with the CMS Fig. 4 points, fit and
   bands; absolute and normalised to 200-400 GeV.
4. `fig2_<var>` for m_asym, Delta-eta, leading/subleading tau21 and tau32: N-1 normalised Open Data and QCD MC with
   the CMS selection, overlaid with the extracted CMS Fig. 2 data and QCD; CMS cut and each run's cut marked.
5. `syst_breakdown_vs_cms`: background uncertainty by source (non-closure yield, non-closure shape, TF fit or TF
   stat, region-C stat, other backgrounds), % of the signal-region background, both runs and CMS Table 6.
6. `closure_summary`: (exists) relabel; add the CMS +-10% band if missing.
7. `closure_heatmap`: kappa - 1 over a grid of (boundary x, boundary y) in QCD MC, for the CMS pair
   (m_asym x Delta-eta) and for each run's pair; mark the chosen points and the CMS point (0.1, 1.5).
8. `nonclosure_heatmap`: per run, tests x m_avg bins, colour obs/pred - 1, text pull, from their prediction and
   validation files (recompute where needed).
Use a subset of skim files where you need events (as before); the node has ~6 GB free.

Add each plot to COMPARISON.md with one paragraph (key number, caveat) and to comparison.json. Do not change your
verdicts unless a new plot changes them; if it does, say so. Write `<OUT>/PLOTS_DONE` at the end.
