# SKILLS_USED: nanoaod-skimming validation

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
