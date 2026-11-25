# Task for the cms-results-validator agent: compare two ABCD estimates with CMS EXO-17-021

Run after both student runs of [PROMPT.md](PROMPT.md) have finished (`run_validator.sh` does this).

## Task

Two students did the same thing on the same data with the same model and prompt: an ABCD estimate of the QCD
multijet background versus the average soft-drop mass of the two leading AK8 jets (m_avg), for a search for
pair-produced boosted resonances each decaying to two quarks, in the CMS 2016 G+H JetHT Open Data (UL
NanoAODv9, ~16.3 fb-1). They chose the ABCD variables, cuts and validation blind. Run A is `<TESTS>/ws_skill`
(had the `background-est:abcd` skill), run B is `<TESTS>/ws_noskill` (had not). Their task is in
`<TESTS>/ws_skill/TASK.md` and inputs in `<TESTS>/ws_skill/INPUTS.md`. Each workspace has results.json, fits/,
plots/, scripts/, logs/, REPORT.md, SKILLS_USED.md. Write everything into `<OUT>` (create it); do not modify the
workspaces and do not rerun the students' full analyses (you may run small scripts of your own on their
histogram and prediction files, and read a few skim files to recompute a check).

These are Open Data studies, not CMS results; say so in every output.

Reference (public sources only): CMS EXO-17-021, "Search for pair-produced resonances decaying to quark pairs in
proton-proton collisions at sqrt(s) = 13 TeV", arXiv:1808.03124, Phys. Rev. D 98 (2018) 112014, HEPData
ins1685989. Use its **boosted search** (80-400 GeV): read the paper for the trigger and preselection, the
substructure cuts, the two ABCD variables and boundaries, the region layout, the transfer-factor form versus
the average mass, the closure test and the background systematics (yield and shape), and the data period (all
of 2016, 35.9 fb-1, legacy reconstruction, average **pruned** mass; the Open Data are the G+H subset in the UL
reprocessing and NanoAOD has soft-drop mass only). HEPData: `curl -sL
"https://www.hepdata.net/record/ins1685989?format=json"` lists the tables (each has an `id`; the record id is in
the JSON); `curl -sL https://www.hepdata.net/record/data/<recid>/<table_id>/<version>` returns one table as JSON.
The `/download/` links are behind a browser challenge. Find the table(s) with the boosted average-mass
distribution of data and the background prediction.

For each run, give a verdict (CONSISTENT / TENSION / INCONSISTENT / NOT COMPARABLE, with your thresholds stated)
and one or two sentences per item:
1. **Comparability**: trigger, offline thresholds, preselection, substructure, ABCD variables and boundaries vs
   EXO-17-021; data completeness (skim files and events vs the inputs).
2. **Method validity on the student's own data**: independence test, MC closure, data validation regions,
   non-closure systematic, treatment of non-QCD backgrounds, sparse-region handling, uncertainty propagation.
   Recompute at least the inclusive prediction N_B*N_C/N_D and its error from their fits/prediction.json.
3. **Prediction vs observed** in their unblinded signal region: chi2 per bin, total, largest local deviation;
   is it consistent with no signal, as EXO-17-021 found.
4. **Versus CMS, shape**: student predicted background vs the CMS background prediction versus average mass,
   each normalised over the common mass range (rebin or interpolate to common bins); chi2 and the slope of
   the ratio. State how pruned vs soft-drop mass and different cuts limit this.
5. **Versus CMS, level and closure**: student yield in A scaled by 35.9/16.3 vs the CMS prediction; the student's
   closure and non-closure systematic vs the CMS closure and systematics. Explain or bound the differences
   (cuts, mass definition, reprocessing, period) and say what part is unexplained.
6. **Method choices vs CMS**: whether the student found the same or equivalent ABCD variables, the
   transfer-factor form (inclusive, per bin, fitted function), and blinding/unblinding order.
7. **Skill effect** (A vs B): a table of the items above side by side, and which differences trace to the skill
   (cite SKILLS_USED.md, REPORT.md and the scripts). Also list what the skill got wrong or did not cover.

Plots (PNG + PDF, labelled "CMS Open Data, private work" for the students and "CMS" for the published values):
predicted and observed m_avg in A for A, B with the CMS background prediction (normalised) and a ratio panel;
transfer factor versus mass for A and B; closure summary (MC and validation regions) for A and B with the CMS
closure band.

Write `<OUT>/COMPARISON.md` (summary table first, <= 3 pages), `<OUT>/comparison.json` (per run, per item:
verdict, numbers), the plots, and the scripts that made them (re-runnable, relative paths).
