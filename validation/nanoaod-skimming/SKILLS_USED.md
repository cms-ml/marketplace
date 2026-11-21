# SKILLS_USED: nanoaod-skimming validation

Run 2 (cutflow, 2026-11-20) is the first section. Run 1 (2026-11-16, before the cutflow) follows unchanged.

## Run 2: cutflow (2026-11-20)

Environment: `set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh; export PYTHONNOUSERSITE=1` on cmslpc. Python 3.13.11, uproot 5.6.0, awkward 2.8.9, hist 2.9.0, mplhep 0.4.1, hadd and xrdcp from the same view. Full chain: `bash validation/nanoaod-skimming/run_all.sh`, run twice end to end (the second run is the final one, after a plot-only fix in `zpeak.py`). Each full run took about 5 min with `MAX_JOBS=2`.

### How the skill was loaded

- `nanoaod-skimming` was **not** loaded with the Skill tool, as instructed by the task. `SKILL.md`, `references/keep-lists-and-recipes.md` and the four scripts were read directly. `--help` was run for all four scripts.
- `cms:hist` was loaded with the Skill tool. The loaded copy came from the user's main marketplace checkout (an older branch), not from this worktree. Its CMS-label example still reads `hep.cms.label("Preliminary", data=True, lumi=16.8, com=13, ax=ax)`. That conflicts with the Open Data labelling rule, so I used `hep.cms.label(label="Open Data", ...)` as in run 1.

### Step 1: skims (SKILL.md "Canonical Patterns 2" and "3. Record the cutflow", `scripts/skim.py`)

- Used `--step 'trigger=HLT_IsoMu24 | HLT_IsoTkMu24' --step 'two_muons=ak.sum(Muon_pt > 20, axis=1) >= 2'` in place of run 1's single `--cut`. Each step got its own Cutflow entry. This worked on the first try.
- Keep list: as run 1, `Muon_*`, `HLT_IsoMu24`, `HLT_IsoTkMu24`, `PV_npvs`, `MET_pt`, `MET_phi`, `Pileup_nTrueInt`, `LHEScaleWeight`. The PROMPT says "MET"; I read that as `MET_pt` and `MET_phi`, as in run 1. Data logs: `MISSING_PATTERNS=Pileup_nTrueInt,LHEScaleWeight` (expected). MC: none missing.
- Golden JSON applied to data: `EVENTS_IN` 9457915, `EVENTS_AFTER_LUMIMASK` 9441598, `EVENTS_OUT` 645024. The skim cutflow `n_lumimask` equals the lumimask count.
- `skim.py --help` lists `MISSING_PATTERNS` and `SUMW_READ` as expected. `SUMW_READ` now prints with `.10g` (HEAD also has `.10g`). See the run 1 section for the precision note.
- I did not use `--dry-run` this run (it was used in run 1). I did run a 100k-event test of one MC file into the scratchpad (`--max-events`, marked `PARTIAL_FILES=1`), to check the step and cutflow mechanics before the full run.

### Step 1b: skim cutflow (SKILL.md "3. Record the cutflow", `scripts/cutflow.py`)

- `cutflow.py -i per_file/skim_*.root` and `cutflow.py -i merged/*.root` both ran with `--json`. Both give identical integers (`n_all`, `n_lumimask`, sequential, N-1). The MC Σ genWeight values agree to within 1e-9 relative. The merged file reports `N_FILES=1 N_INPUT_FILES=3`.
- Independent check of the N-1 logic on 100k MC events, with uproot and awkward directly: `trigger` 21647, `two_muons` 14186, `trigger & two_muons` 13550. These match `cutflow.py`: `CUTFLOW_trigger=21647`, `NMINUS1_trigger=14186` (passes `two_muons`), `CUTFLOW_two_muons=13550`, `NMINUS1_two_muons=21647` (passes `trigger`). The Σ genWeight agrees to 1e-7 (float32 accumulation in my direct sum).

### Step 4: analysis cutflow (`zpeak.py`, the skill has no text for it)

The SKILL says "Continue the cutflow in the analysis from the skim's last step ... Analysis cuts can only be studied N-1 if the preselection is looser than them". It does not say how per-muon cuts or pair-based cuts count as events, so I had to define them. My definitions are stated in the `zpeak.py` docstring:

- Muon-level steps (`muon_pt`, `muon_eta`, `muon_tight_id`, `muon_iso`), sequential: "at least two muons pass all muon requirements so far".
- Event-level steps use the pT-sorted selected muons. `exactly_two` is "exactly 2 selected". `opposite_charge`, `leading_pt` and `z_window` use the two leading selected muons, and fail when fewer than two are selected.
- N-1 of a muon-level step: muons selected without that cut, all other steps applied (event-level steps included).
- N-1 of an event-level step: all muon requirements and all other event-level steps applied.

Checks on these definitions: the sequential `muon_pt` equals the skim `two_muons` count (data 645024, MC 408892.66 both ways), and the last sequential `z_window` equals the independent run-1 selection (data 281527, MC 297829.249). The sequential cutflow is non-increasing.

### Step 4 plot

- `plots/cutflow.png/pdf`: top panel log-scale, data vs normalised MC, all 12 steps. Bottom panel: data/MC from `trigger` on, log scale.
- Problem: a linear ratio range of 0.5 to 1.5 hid the first four steps (data/MC 9.7 at `trigger`, 1.58 at `two_muons`, `muon_pt` and `muon_eta`). These are not a mistake. The data are the SingleMuon primary dataset, and the MC is the inclusive DY sample, so before the muon selection they are different populations. I changed the ratio to a log scale (0.1 to 20) and documented that in the code.
- MC stat uncertainty on the skim steps is not shown (see gaps below).

### Gaps and problems in the skill (run 2)

1. **The Cutflow tree has no Σ genWeight², so MC stat errors are impossible for skim steps.** SKILL.md says "`w_*` , `wm1_<step>` the same as sums of genWeight (MC only)". For a normalised MC plot the stat error on skim steps needs Σw², which is not stored. Suggestion: add `w2_<step>` to the Cutflow tree.
2. **`cutflow.py` `cum` column is confusing for the `all` row.** The `all` row prints `cum 1.0017` for data, because `cum` is N / n_lumimask and `all` > `lumimask`. The docstring says `cum  N / n_lumimask (cumulative efficiency)`. Suggest `cum` relative to `n_all`, or print `-` on `all`.
3. **`cutflow.py` prints `N_FILES` and `N_INPUT_FILES`, and the names are easy to confuse.** On the merged file it prints `N_FILES=1 N_INPUT_FILES=3`. The docstring does not say that `N_FILES` counts the files passed on the command line.
4. **No guidance for analysis steps after the skim.** Quoted from SKILL.md "3. Record the cutflow": "Continue the cutflow in the analysis from the skim's last step ... append the analysis steps counted on the skimmed events." The definition of a per-muon step, and of N-1 for a pair-based step, is missing (see above). A short recipe or a helper would help.
5. **Units of normalised MC in the skim cutflow.** SKILL.md says "For MC the cutflow in Σ genWeight, not the event count, is the one to compare with data". The PROMPT wants normalised events (`genWeight * xsec * lumi / SUMW`). I applied `WEIGHT_FACTOR` to Σ genWeight, and the `all` row is then `xsec * lumi` (2980196.6 against 2980195.8, relative 2.8e-7). The skill could state this identity directly, because it is a good check.
6. **Run time.** Measured: each data skim about 50 s with two in parallel, each MC skim 10 to 17 s. The whole chain took about 5 min.
7. **Earlier note on `SUMW_READ` (run 1, see below) does not match the current code.** HEAD `skim.py` prints `SUMW_READ={sumw_read:.10g}`. The run 1 summary already held `48548789980.0`, so the 6-digit observation in run 1 could not be reproduced.

   Supervisor: the run 1 note was right when it was written. `skim.py` was changed from 6 to 10 digits after run 1, and the chain was rerun before run 1 was committed (see README).

### Changed in the skill after run 2 (supervisor)

- Gap 1: the Cutflow tree now has `w2_<step>` and `w2m1_<step>` (Σ genWeight²), in `skim.py` and in the RDataFrame recipe. `cutflow.py` prints `W err` and `CUTFLOW_WERR_<step>`. Checked against a direct sum on a skim.
- Gap 2: `cum` is now N / `n_all`.
- Gap 3: the `cutflow.py` docstring says what `N_FILES` (skim files read) and `N_INPUT_FILES` (original NanoAOD files) count.
- Gaps 4 and 5: SKILL.md now defines object-level and pair-level steps and their N-1 (the definitions used here), and states the `all` row = σ L check.
- The chain was rerun with the final `skim.py`. `check_results.py` gained 13 cutflow checks.

### Files changed in run 2

- `validation/nanoaod-skimming/run_all.sh`: named `--step` preselection, `cutflow.py` per file and merged (four JSON and log pairs in `logs/`).
- `validation/nanoaod-skimming/zpeak.py`: analysis cutflow (sequential and N-1), cutflow plot, `cutflow` block in `summary.json`, cross-checks.
- `validation/nanoaod-skimming/summary.json`: exact PROMPT keys, plus `cutflow`.
- `validation/nanoaod-skimming/plots/cutflow.png/.pdf` (new), `plots/mmumu.png/.pdf` (regenerated, unchanged).
- `validation/nanoaod-skimming/logs/*`: overwritten by the run, including `cutflow_*.json` and `cutflow_*.log`.
- `validation/nanoaod-skimming/SKILLS_USED.md`: this section.
- Skims in `/uscms_data/d3/$USER/skims/nanoaod-skimming-validation/` (overwritten, outside the repository).
- Not touched: `check_results.py`, `README.md`, `PROMPT.md`, anything under `plugins/`. No git commit, push or stash.

## Run 1 (2026-11-16, before the cutflow)

Run date 2026-11-16, cmslpc. Environment: `source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh` (set +u first), with `PYTHONNOUSERSITE=1`. Versions: Python 3.13.11, uproot 5.6.0, awkward 2.8.9, numpy 2.2.6, hist 2.9.0, mplhep 0.4.1, ROOT 6.38.00, hadd and xrdcp from the same view.

Caveat for every skill step: `python3 -I` drops the view's `PYTHONPATH` and breaks imports (uproot not found). Do not use `-I` with the LCG view.

## Skill loading

- **`cms:nanoaod-skimming` via the Skill tool: failed.** The call returned `Unknown skill: cms:nanoaod-skimming`, and the skill is not in this session's skill list. I read `plugins/cms/skills/nanoaod-skimming/SKILL.md` and `references/keep-lists-and-recipes.md` directly, and used the three scripts in `scripts/` unchanged. The PROMPT's headless command passes `--plugin-dir plugins/cms`, so the skill should be discoverable there; the plugin loading path is worth checking.
- **`cms:hist`: not loaded through the Skill tool.** I read `plugins/cms/skills/hist/SKILL.md` directly (grep for the CMS label section) and followed its `hist.Hist(..., storage=hist.storage.Weight())` plus `hep.histplot` pattern. Its example line is `hep.cms.label("Preliminary", data=True, lumi=16.8, com=13, ax=ax)`. That conflicts with the rule "label Open Data plots CMS Open Data, never CMS Preliminary", so I used `hep.cms.label(label="Open Data", ...)`. Skill feedback: the example should show a neutral label, or the label should be a parameter.
- **`cms:awkward-array` and `cms:vector-awkward`: not loaded.** I wrote the awkward code in `zpeak.py` directly. I hit one error of my own (`ak.zip(..., depth_limit=1)` made per-event records, so the jagged muon mask failed with "cannot broadcast records"). Fixed by dropping `depth_limit`. The invariant mass is computed with numpy on the awkward fields, not with the vector library.

## Step 1: skim (SKILL.md "Canonical Patterns 1, 2", `scripts/skim.py`)

- Followed "Decide what to keep": `skim.py --dry-run` on one data and one MC file. Worked. Output: 63 kept branches for data and 68 for MC. `MISSING_PATTERNS=Pileup_nTrueInt,LHEScaleWeight` on data, as the keep-list reference says it should be. Good.
- Followed "Skim with uproot": `--keep ... --cut ... --lumi-json`. All six skims ran in parallel, about 45 s per data file and 11 to 17 s per MC file, and all completed. Per file: EVENTS*IN and EVENTS_OUT are in `logs/skim*\*.log`.
- Cut used: `(HLT_IsoMu24 | HLT_IsoTkMu24) & (ak.sum(Muon_pt > 20, axis=1) >= 2)`. Worked; `cut_inputs` were picked up from the identifiers as the SKILL describes.
- Check: `EVENTS_IN` total data 9457915 and golden JSON removed 16317 events (EVENTS_AFTER_LUMIMASK 9441598). The golden JSON is applied only to data, and the MC log has no `--lumi-json` note, so the MC path is as documented.
- Gap: the SKILL example writes straight to a local file and then says "copy it" with `xrdcp`. For this run the skims went directly to `$SKIMDIR`, which is what the PROMPT asked for. No issue, but the skill could say that the local-then-copy step is optional on a shared filesystem.
- Gap: the golden JSON must be a local file, because `LumiMask` opens the path. The skill does not say so. I downloaded it to `$SKIMDIR/inputs/golden.json`.

## Step 2: merge (SKILL.md "Canonical Patterns 5", `hadd -f -k`)

- Worked. Merged MC has 385701 entries (= 78966 + 147353 + 159382 from the per-file logs). Merged data has 645024 entries (= 206405 + 225787 + 212832). The `-k` option was not needed.
- Measured sizes: merged data 151597338 B against 151752505 B for the three inputs; merged MC 96294500 B against 96474959 B. `hadd` is slightly smaller.

## Step 3: bookkeeping (SKILL.md "Canonical Patterns 6", `sumw.py`, `lumi.py`)

- `lumi.py -i merged/SingleMuon_2016G.root --byls <pp_2016lumibyls.csv>`: N_LS=2852, N_LS_MISSING=0, LUMI_PB=490.388. Worked over `root://` with `xrdcp -s`.
- `lumi.py --golden golden.json`: N_LS=234231, N_LS_MISSING=0, LUMI_FB=36.3138. The SKILL says "The year total (e.g. 36.31 /fb for 2016 UL)". Confirmed.
- `sumw.py` on the original files: SUMW=4.854879031e+10, WEIGHT_FACTOR=6.13856e-05 (6077.22 × 490.388 / SUMW). `sumw.py` on the merged skim gives the same SUMW (relative difference 0).
- Check: `sumw.py` prints the LHE combined sums. `LHESCALESUMW_SUMW` index 4 and `LHEPDFSUMW_SUMW` index 0 both equal SUMW exactly, which confirms that `sumw.py` combines the per-file "divided by genEventSumw" values correctly. Independently recomputed from the Runs tree: relative difference 0.0.
- Check: the sum of `SUMW_READ` over the three full files is 4.85488e10, against Runs SUMW 4.854879e10 (relative difference 2e-7, limited by the rounding below). This confirms the SKILL's point that `SUMW_READ` over a full file equals the Runs sum.
- **Problem in SKILL/script, precision**: `skim.py` prints `SUMW_READ={sumw_read:.6g}` (6 significant digits), while `sumw.py` prints 10. The `summary.json` entry `mc.sumw_read` therefore only has about 6 digits (48548800000.0). The skill says `SUMW_READ` is "Σ genWeight of what it read" but says nothing about precision. Suggest `%.10g` in `skim.py`.
- Gap: `lumi.py` removes duplicate (run, LS) pairs across files (its docstring says so), but SKILL.md does not mention this. It matters when a lumi section is split between files.

## Step 4: physics check (no skill covers the Z selection; `hist` for the plot)

- Selection and normalisation are in `zpeak.py`. Checks in `logs/zpeak.log`: 8 of 8 pass.
- Results: data 281527 events in 81 to 101 GeV; MC normalised 297829.25 ± 818.37 (stat); data/MC = 0.945. The ratio panel is about 0.92 to 0.95 across the peak, which is consistent with the missing muon ID, isolation and trigger scale factors. That is not a measurement of them.
- Sanity: 6077.22 pb covers ee+μμ+ττ at M > 50, so about 2000 pb per flavour; × 490 /pb × acceptance ~0.3 gives about 3×10^5 in the window, which matches the MC number.
- Plot: `plots/mmumu.png` and `plots/mmumu.pdf`, labelled "CMS Open Data", 0.49 fb⁻¹, 13 TeV. Legend moved and y-axis headroom added after I looked at the first version.

## Gotchas: where the skill was wrong, unclear or missing

1. **Wrong or unreproducible number.** SKILL.md Gotchas: "so dividing by the event count instead of Σ genEventSumw is off by a factor of about 1.5." I could not reproduce this. For this sample the event-count normalisation would be off by a factor of about 1.7×10^4 (Σ genEventSumw / N = 4.85e10 / 2.857e6 ≈ 1.7×10^4 per event), which is a units problem, not 1.5. The number that is about 1.5 is Σ|genWeight| / Σ genWeight over the MC skim: 9.74e9 / 6.66e9 = 1.46. That is a statement about signed versus unsigned weights, not about the event count. Please reword.
2. **The negative fraction matches.** "16% of `genWeight` values are negative" is measured here as 15.8% (60999 of 385701 skim events). Good.
3. **LHE nominal index not stated.** SKILL.md says the Runs `LHEScaleSumw[i]` and `LHEPdfSumw[i]` are stored divided by genEventSumw, and that `sumw.py` combines them. It does not say which index is nominal. Measured: scale index 4 and PDF index 0 are the nominal (muR=1, muF=1 and the central PDF), and both equal Σ genEventSumw exactly. Worth a line in the skill.
4. **`SUMW_READ` precision** (see Step 3). Not mentioned in the SKILL.
5. **Timings missing.** The SKILL gives no run time. Measured on cmslpc with a warm cvmfs cache: data skims 45 to 50 s for 2.9 to 3.3 M events, MC 11 to 17 s for 0.6 to 1.2 M events, six jobs in parallel. The whole chain with the second lumi (`--golden`) and sumw runs took about 1 min 45 s.
6. **The golden JSON must be local.** `skim.py --lumi-json` opens a local path (`LumiMask.__init__`); the SKILL shows the file name but not that it must be downloaded first. Downloaded from the URL in the PROMPT.
7. **Duplicate lumi sections across files** handled by `lumi.py` but not described in the SKILL (see Step 3).
8. **Not a problem, but worth noting**: the LuminosityBlocks tree of a skim lists every lumi section of the input file, including those with no selected events. The data luminosity is therefore the full processed luminosity of the file, which is what the SKILL intends. The SKILL could say so explicitly.
9. **Script output format**: the SKILL's `skim.py --dry-run` lists `KEEP=` lines and `MISSING_PATTERNS=`. Both were as documented.

## Not used

- `--drop 'Muon_*Err'` from the SKILL example: not in the PROMPT's keep list, so not used.
- `--max-events`: not used, as instructed (complete files only).
- RDataFrame Snapshot and CRAB/Condor recipes: not needed here.
- The `N_EFF` output of `sumw.py` (1.29e6, full sample) is printed but not used in the summary.
