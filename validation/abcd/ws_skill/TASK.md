
Work only inside your workspace `/uscms_data/d3/ashrivas/AGENTS-AI/cms/marketplace/validation/abcd/run3/ws_skill` (the current directory; create scripts/, logs/, plots/, fits/ there).
Do not read, list or search any file outside it, except /cvmfs, the targets of inputs/py_env.sh, the EOS files
listed in inputs/, your EOS scratch directory and the skill files your Skill tool loads. Do not look up or cite
CMS papers or results: this is a method test. Read `INPUTS.md` first.

Physics target: pair production of two equal-mass resonances, each decaying to two light quarks, with resonance
masses of roughly 80-400 GeV. At these masses each resonance is boosted and its two quarks merge into one AK8
jet, so the signature is two AK8 jets. The observable is the **average soft-drop mass of the two leading AK8
jets**, m_avg = (m_SD,1 + m_SD,2)/2, where a signal would appear as a peak. No signal simulation is provided.

Goal: estimate the QCD multijet background in the signal region as a function of m_avg from data with an
**ABCD method**, in the 2016 G+H JetHT data (~16.3 fb-1), and validate it. Everything is your choice and must
be justified from the expected signal topology, simulation or data outside the signal region: trigger and
offline thresholds, jet and event preselection (substructure, leptons, ...), the two ABCD variables and their
boundaries, the m_avg binning and range, whether the transfer factor is inclusive, per bin or a function of
m_avg, how non-QCD backgrounds are handled, and how you test independence and closure and set the
systematic uncertainty. Keep the signal region blinded in data until the prediction and its uncertainties are
final; then unblind it and compare observed with predicted per m_avg bin.

Use the skills available to you for every step they cover (load each with the Skill tool before the step):
`cms:trigger-efficiency` for the trigger, `cms:awkward-array`, `cms:hist`, and `af-fnal-lpc:lpc-condor` if you
run on condor.
Before designing the background estimate, load `background-est:abcd` with the Skill tool and follow it, including its scripts (read them from the skill's directory).

1. Design the selection, the ABCD variables, boundaries and binning; show the plots that justify each choice.
2. Test the independence of the two variables, measure the transfer factor and the prediction in the signal
   region with stat and syst uncertainties, and validate it (simulation closure and data validation regions).
3. Unblind the signal region and compare.

Deliverables (all required, including the .md files; write them even if a default rule says not to create
documentation files):
- `results.json` with keys: trigger {paths, offline_threshold, method}, preselection (list),
  abcd_variables [{name, definition, cut, signal_side}], regions {A, B, C, D: one-line definitions, A = signal
  region}, mavg_bins (edges), independence {method, result}, tf {form (one sentence), values, uncertainty},
  other_backgrounds {method, fraction_in {A, B, C, D}}, prediction {edges, value, stat_err, syst_err,
  total_inclusive, total_err}, closure_mc {ratio, pull, per_bin_chi2, ndf}, validation_regions [{definition,
  ratio, pull, per_bin_chi2, ndf}], non_closure_syst, unblinded {observed per bin, observed_total, chi2, ndf,
  max_local_deviation_sigma}, n_events {A, B, C, D} (data), checks_done (list), checks_not_done (list),
  notes (<= 5 lines);
- `fits/prediction.json`: per m_avg bin: edges, data counts in A, B, C, D, other-background yields, predicted QCD
  in A with stat and syst errors, observed in A;
- `plots/`: m_avg in A with prediction, uncertainty band and ratio panel; the transfer factor versus m_avg; the
  independence tests; MC closure; validation regions; every plot used to justify a choice (trigger turn-on,
  boundaries, substructure cuts);
- `REPORT.md` (<= 2 pages) and `SKILLS_USED.md` (what you loaded, followed, and what was missing or wrong).

Waiting: this is a headless run. If you end your turn while a job is running, the run stops and you are not
woken up. Wait for condor jobs and long scripts in the FOREGROUND with blocking loops that each stay under
10 minutes (e.g. `timeout 540 bash -c 'until <done-check>; do sleep 30; done'`), repeated as needed; do not
use run_in_background or the Monitor tool to wait. End your last turn only when every deliverable exists.
Keep intermediate files inside the workspace (never /tmp).

Rules: everything runs as scripts with output to logs/; read only `tail -n 30` of logs; never print arrays,
dataframes or branch lists; the interactive node has about 6 GB of free memory (read only the columns you need,
in chunks, or on condor). If a step fails three times, record it in results.json and go on.
