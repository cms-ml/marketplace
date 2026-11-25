# Follow-up task for the with-skill student (resumed session): more plots

<!-- prettier-ignore-start -->
<!-- kept verbatim: this is the text the agents were given -->

Sent by `run_followups.sh` with `claude -p --resume <student session>` in the student's workspace.

## Task

Your analysis is final; reviewers asked for more plots documenting it. Do NOT change the frozen prediction,
the systematics or the unblinded numbers in results.json / fits/prediction.json. Same rules as before: work only in
your workspace, scripts with logs, `tail -n 30` of logs, no CMS papers. Reuse your existing slimmed files.

Add these plots to `plots/` (PNG + PDF, label "CMS Open Data, private work"), each justified in one line in REPORT.md:
1. `closure_mc_perbin`: QCD-MC closure in A per m_avg bin (obs/pred with stat error and your syst band).
2. `closure_mc_variations`: MC closure ratio under variations of the method: each ABCD boundary shifted up/down, the
   fail-band width (0.2-0.3, 0.2-0.4, 0.2-0.6, all > 0.2), the HT threshold, inclusive vs fitted TF.
3. `validation_regions_data_perbin`: each data validation region per m_avg bin, obs/pred with ratio panels and bands.
4. `design_2d_masym_deta`: 2D distribution of m_asym vs |Delta eta| in QCD MC and in data outside A, region lines drawn.
5. `design_boundary_scan`: kappa and the signal-proxy efficiency versus each boundary, chosen values marked.
6. `independence_ratio_vs_deta`: the m_asym pass/fail ratio versus |Delta eta| (the other direction of your
   independence test), MC and data outside A.
7. `substructure_dists` and `substructure_roc`: tau21, tau32 and N2 of both jets, QCD vs your proxies, and the
   ROC curves; one line on why none is an ABCD axis or a cut in your selection.
8. **Closure heatmap** `closure_map_mc` and `closure_map_data`: for a grid of (m_asym boundary, |Delta eta| boundary)
   values, kappa = N_A*N_D/(N_B*N_C) (colour = kappa - 1, text = pull) in QCD MC; in data only for grid points
   whose test-A region lies outside your signal region A. Mark your chosen point.
9. **Non-closure heatmap** `nonclosure_map`: rows = every closure/validation test you ran (MC closure, MC and data
   VRs, variations), columns = m_avg bins; colour = obs/pred - 1, text = pull. Show which tests and bins drive
   your per-bin shape term.

Update REPORT.md (a "Plots" section; keep <= 2.5 pages), results.json (add `plots` with one line each) and
SKILLS_USED.md (whether the skill helped with any of these). Write `PLOTS_DONE` in your workspace at the end.
<!-- prettier-ignore-end -->
