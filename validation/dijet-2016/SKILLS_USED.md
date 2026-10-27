# Skills used in the dijet-2016 validation

Run by the agent on cmslpc, October 2026. Python environment: LCG_109 view
(`/cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh`): Python 3.13, iminuit 2.31.1, uproot 5.6.0,
awkward 2.8.9, hist 2.9.0, mplhep 0.4.1, hepdata_lib 0.20.0, hepdata-validator, correctionlib. This satisfies the PROMPT's
"iminuit from a pip/uv environment" requirement (modern iminuit, not CMSSW's 1.2) and works on condor workers, so no uv
environment was built. The `standalone-script` skill was therefore only read, not applied (see below).

## Skills that existed

| Step                                                 | Skill                                                            | How it helped / where it fell short                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ---------------------------------------------------- | ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Writing `specification.md`                           | `analysis-spec-builder`                                          | Template and defaults were directly usable. Gaps: the template has no place for a luminosity source for Open Data (I used the Golden JSON and `pp_2016lumibyls.csv` from the Open Data portal, records 14220 and 1059; the skill only says "Golden JSON"), no section for "assumptions that replace missing inputs" (Z' cross section absent from the records), and nothing on how to word a statistical-model section (fit function, F-test, injection) beyond "Combine". I added an "Open questions" section at the end.                                                                                                                                                                                                                                                                                              |
| Condor skim of 142 data + 118 QCD + 120 signal files | `lpc-condor` (templates `job.sh`, `job.jdl`, `make_filelist.py`) | Worked almost unchanged. Wrapper tested locally, one job as the condor test, then the rest. What I changed: the payload name (`skim.py`), output extension `npz`, string job ids (`d0`.. `q0`.. `s0`) in `jobs.txt` instead of numbers, `request_memory = 4000`. Missing: (a) nothing about packing several samples into one job and mapping files back to samples (I wrote `make_jobs.py` and put the URL in the output metadata); (b) nothing on choosing the number of jobs under a hard job cap (I measured about 25 s per 1.8M-event data file locally and ran 24 files per job); (c) `condor_q` without `-name` only shows jobs on the schedd that answers, so a freshly submitted cluster looked absent for a minute; the skill already says this. `check_outputs.py` was not needed because all jobs succeeded. |
| Reading NanoAOD and selection                        | `awkward-array`                                                  | `ak.local_index(...)[good][:, :2]` for "two leading good jets" and `T.iterate(...)` chunking are not in the skill; I derived them. The skill's `ak.firsts` / `x[:, 0]` warnings were relevant. It does not mention `uproot.iterate` for 2M-event files (memory) at all.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| Dijet mass                                           | `vector-awkward`                                                 | Used `vector.arr({...})` (NumPy backend) for the pair mass of two already-selected jets, because after `ak.to_numpy` the two jets were plain arrays. The skill shows `vector.array` in a sentence but no example of the NumPy backend with the `pt, eta, phi, mass` dict form; `vector.arr` worked.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     |
| Histograms and plots                                 | `hist`                                                           | CMS-style plotting recipes (`hep.cms.label`) worked, with mplhep 0.4.1 `hep.cms.label("Open Data", data=..., lumi=..., com=13)` giving "CMS Open Data" and "CMS Simulation Open Data". The skill's examples use `Preliminary`; the Open Data wording is not given there (must never be "Preliminary"). I mostly used `np.histogram` with variable CMS dijet bins and `stairs`/`errorbar` since the fits need raw arrays; `hist` was not used for storage. No guidance on variable-bin density plots (events/GeV), pulls panels or log-y with ratio.                                                                                                                                                                                                                                                                     |
| Python tooling                                       | `standalone-script`                                              | Read only. The skim runs in the LCG view on workers where uv is not available/needed; the PEP 723 route would need uv on the worker. The skill does not say how to choose between PEP 723 and an LCG view for condor payloads.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          |
| Trigger efficiency                                   | none (skill `trigger-efficiency` does not exist)                 | Done from own knowledge, see "Missing guidance" below.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| HEPData                                              | none (skill `hepdata` does not exist)                            | Done with `hepdata_lib` and `hepdata-validate`, see "Missing guidance" below.                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           |

## Missing guidance: trigger efficiency (content for a future `trigger-efficiency` skill)

Decisions I had to make with no guidance, and what I did:

1. **Choice of reference trigger and its bias.** For a JetHT dijet analysis the signal OR (PFHT900, PFJet450/500, CaloJet500,
   AK8PFJet450/500) has no unprescaled lower path. I used the prescaled `HLT_PFJet260` as the main reference and
   `HLT_PFHT475`, `HLT_PFJet400` as cross-checks. A skill should say: pick a reference that is fully efficient
   where the signal path turns on, check it with two others, and state that prescales cancel in the ratio
   but that the reference and signal bits must be read from the same events.
2. **Which paths to OR, and which exist in the file.** The NanoAOD HLT branch list for 2016 JetHT has to be
   listed from the file (`T.keys()` filtered on `HLT_`) because path names changed between 2016 menus. `PFHT800` exists but
   is 0 for part of the data. A skill should include a one-liner to list paths with their firing fraction.
3. **Variable to plot efficiency against.** The offline m_jj of the two leading jets after the full offline selection
   (tight ID, |eta| < 2.4, |deta| < 1.1), not the trigger-object pT. This matters because the |deta| cut changes the
   turn-on position.
4. **Binning.** I reused the CMS dijet bins; a skill should recommend bins and a minimum number of events per bin.
5. **Uncertainties near 100%.** Gaussian errors are zero at eff = 1; I used Clopper-Pearson 68% intervals (scipy
   `beta.ppf`). The skill should give this snippet and say how to draw asymmetric errors (and that NaN appears for empty
   denominators and breaks `errorbar`).
6. **Defining the threshold and plateau.** No convention was given. My rule: the lowest bin edge where every higher bin has
   CP upper bound >= 99.5% and the pooled efficiency above it is >= 99.5%; plateau value = pooled efficiency above the
   threshold. A skill should give a rule like this and note that with a handful of events per bin a "compatible with 1"
   test is weak (the rule is permissive in sparsely populated high-mass bins), so it also needs a minimum-statistics
   check.
7. **Event cleaning and certification before the efficiency.** Golden JSON and MET filters must be applied first.
8. **MC.** I did not trigger-emulate the MC (the HLT branches exist but the menu differs); I required m_jj above the data
   plateau. The skill should say whether MC trigger bits are usable for 2016 UL.

## Missing guidance: HEPData (content for a future `hepdata` skill)

Concrete things hit or decided:

1. **Validator CLI.** `hepdata-validate <dir>` fails with `Error: Got unexpected extra argument (dir)`. The directory goes
   with `-d <dir>` (default: the current directory), archives with `-a`. Run it with the submission directory as cwd
   if the output is saved to a file, otherwise absolute paths leak into the log. Exit code 0 means valid.
2. **hepdata_lib version and API.** 0.20.0 in LCG_109. `Submission()`, `Table(name)`, `Variable(name, is_independent, is_binned, units)`,
   `Uncertainty(name, is_symmetric)`, `table.keywords[...]`, `submission.create_files(dir)`. Binned independent
   variables take a list of `(low, high)` tuples. Asymmetric uncertainties take `(minus, plus)` tuples with the minus value negative.
3. **File names.** The table name becomes the YAML file name; a name with an apostrophe
   (`b-tag efficiency vs Z' mass`) produced `b-tag_efficiency_vs_z'_mass.yaml`. Keep table names ASCII without quotes.
4. **Zero-content bins.** The library prints `Note that bins with zero content should preferably be omitted completely from
the HEPData table.` once per zero value. It is a note, not an error. For spectra with a likelihood fit the zero bins at
   high mass carry information, so I kept them. A skill should say when to trim and when to keep.
5. **NaN.** Efficiencies from empty denominators are NaN; the YAML is then invalid or misleading. I replaced them by 0
   with 0 events, which is a decision; better to drop the bin or document it.
6. **Non-numeric or index-like independent variables.** Tables such as "fit results per category and number of parameters"
   have no natural independent variable. I used an integer index (`10*category + n`) and spelled it out in the
   description. A skill should give the preferred pattern (one table per category, or a string-valued independent variable).
7. **Metadata that a reviewer expects:** `keywords` (`cmenergies`, `reactions`, `observables`, `phrases`), `comment`, license (hepdata_lib sets CC0),
   `location`, and per-variable qualifiers (`SQRT(S)`, selection). The skill should list the minimal set and which keywords have controlled vocabularies.
8. **Open Data and "not a CMS result".** No guidance on how to label the record; I put "NOT an official CMS result" in
   the submission comment and every description. A record built from Open Data should not claim a CMS collaboration identity.
9. **Online validation is not possible offline.** `hepdata-validate` only checks syntax and schema (and `is valid` messages per file); it does not check
   that the number of values matches between variables (hepdata_lib asserts that at write time) nor physical sense.
10. **Tarball.** `create_files(dir)` writes the YAML directory (and, in other versions, `submission.tar.gz` next to it);
    I only keep the directory.
11. **Fit and pull information:** where to put parameters and covariance (HEPData has no native place; I used a
    table with an index). A skill should recommend a pattern.

## Gaps and bugs hit in the other skills (summary)

- `lpc-condor`: none blocking. Suggestion: mention string job ids in `queue jobid,inputs from` and a pattern for multi-sample jobs.
- `awkward-array` / `vector-awkward`: no example of the `vector.arr` NumPy backend with the `pt, eta, phi, mass` dict form (worked, see above).
- `hist`: no variable-width dijet binning, no density-per-GeV, no pulls panel, no Open Data label. `hep.cms.label` kwarg
  `lumi` expects a number or string, `com=13` works in mplhep 0.4.1.
- `analysis-spec-builder`: see table.
- Environment pitfall (not in any skill): after `source LCG setup.sh`, an inline `PYTHONPATH=dir python3` prefix replaces the
  view's `PYTHONPATH` and breaks `import numpy`; use `export PYTHONPATH=dir:$PYTHONPATH` or `sys.path.insert` in the script.

## Run log notes (added after the condor skims finished)

- **Condor jobs**: 9 jobs in 2 clusters (1 signal job as the condor test, then 8: 6 data, 2 QCD), all exit code 0, no resubmission.
  Each data job read 23-24 files (about 40M events); the signal job took about 10 minutes and the data/QCD jobs 25-45 minutes
  (one data job was 3-4x slower per file than the others: node/XRootD variability, so the skill's "3-10x slower than local" holds).
- **Failed analysis run, cause and fix.** The first full run of `analysis.py` over all 9 skims printed nothing and left an empty output
  directory: the shell showed `Killed` and `dmesg` showed `Out of memory: Killed process (python3) ... anon-rss 3.2 GB`
  (global OOM: the interactive cmslpc node had only about 6 GB free of 11 GB). The first version concatenated all 95M skimmed events
  (about 20 arrays each, plus float64 copies from masks). Fix: stream one `.npz` at a time (`dijetlib.iter_events`), keep only the columns
  needed, apply the golden JSON and the signal trigger while loading, and use a two-pass design (trigger turn-on first, then only events
  above the m_jj threshold). Peak memory went to 3.5 GB (`/usr/bin/time -v`), runtime about 100 s. Lesson for the `lpc-condor` /
  `awkward-array` skills: a skim output of a few hundred MB compressed is several GB in memory; say so, and recommend writing the
  skim as histograms or per-sample files, or iterating per file; also redirect the log and append the exit code (`echo EXIT $?`),
  because a background job killed by the OOM killer leaves an empty log.
- **`.npz` as condor output** (`OUT_EXT=npz`) worked with the wrapper; the `info` entry stores the file list and per-file event
  counts and `Runs/genEventSumw`, so MC normalisation is exact for the files actually processed.
- **Bash tool pitfall:** `sleep` longer than a couple of seconds in the foreground is rejected; background `until grep ...` loops work.
- **Dijet fit practice (could go into a future fit skill):** fit `ln p0` instead of `p0`, seed the 4- and 5-parameter fits from the
  previous fit, Poisson deviance for chi2 and signed-deviance pulls (the Pearson chi2 is wrong in the empty high-mass bins).
  In the 1b category the 4- and 5-parameter fits converge to p3, p4 consistent with 0 (identical deviance), so the F-test correctly picks 3.

## Validation of the new trigger-efficiency and hepdata skills

Second pass, October 2026, cmslpc, LCG_109 view (Python 3.13, hepdata_lib 0.20.0, hepdata-validate, ImageMagick `convert`
present). The two skills did not exist during the first pass (the "Missing guidance" sections above are the seed for them).
This pass refactored `analysis.py` and `make_hepdata.py` to follow the skills, and reran everything on the same 9 condor
skims (no resubmission). The old first-pass rows above ("none (skill ... does not exist)") are kept as history.

### What I changed

| File                                         | Change                                                                                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `analysis.py`                                | Imports `efficiency`, `find_threshold`, `plateau`, `plot_turnon` from `plugins/cms/skills/trigger-efficiency/scripts/turnon.py` (repo root found by walking up from `__file__`). The local `find_threshold` and the trigger use of `D.clopper_pearson` are gone. Target 0.995 and the same bins (`DIJET_EDGES` between 800 and 2500 GeV, i.e. 838 to 2438). `min_events=100` is the skill default. The skill's `DIJET_EDGES` is asserted to be a subset of `dijetlib.DIJET_EDGES`. |
| `make_hepdata.py`                            | Rewritten from `assets/make_hepdata.py`: helpers, guards, `require_files`, validator call kept as in the template; `build(sub, args)` filled from `summary.json` and the PDFs in `plots/`; images attached to all 6 tables; `phrases` keyword added; string `Category` independent variable; empty-denominator bins dropped (none were empty in this data, see below); every description and `submission.comment` say NOT a CMS result.                                            |
| `summary.json`                               | Additive keys only: `fit/<cat>/{data_counts,fit_edges_GeV,fit_expectation_chosen}` (so the record can be rebuilt without arrays being passed in), `trigger/{threshold_target,threshold_min_ref_events_above}`.                                                                                                                                                                                                                                                                     |
| `hlt_paths_2016G.txt`, `hlt_paths_2016H.txt` | `list_hlt_paths.py <file> --match '^(PFJet\|PFHT\|AK8PFJet\|CaloJet)[0-9]'` on the first file of `data_G.txt` and `data_H.txt` (100000 events each). 53 paths in G, 54 in H. `HLT_PFHT800` is in G (0.21907 fired) and not in H, as the skill says.                                                                                                                                                                                                                                |

### Skill instructions followed and result

- `trigger-efficiency` pattern 1 (list paths per era) and pattern 2 (`efficiency` -> `find_threshold` -> `plateau` -> `plot_turnon`): worked as written
  and reproduced the first-pass numbers bit for bit (table in the report; the only differences in `summary.json` are the added keys and `runtime_s`).
  `turnon.py --demo` on the first 3 G + first 3 H files of the lists gave exactly the numbers quoted in the skill
  (`THRESHOLD_GEV=1058 PLATEAU=0.99873 PLATEAU_LO=0.99705 PLATEAU_HI=0.99955 N_REF_ABOVE=1572`; 80 s, 2.0 GB).
  `list_hlt_paths.py` on one file takes 6 to 7 s and about 0.1 GB.
- `hepdata` template: `--demo` builds and validates (3 tables, VALID=1). Dropping a bin was checked with a negative test:
  setting num = den = 0 in the last trigger bin in a copy of `summary.json` gives a 20-bin table, no `.nan`, a description that names the omitted bin, VALID=1.
  The real data had no empty-denominator bin (21 bins, smallest reference count well above 0), so the "replaced by 0" problem of the first pass was latent here, not an actual wrong value in the old record.
- Peak memory of `analysis.py` unchanged at 3.55 GB (`/usr/bin/time -v`, old 3.5 GB). Wall time was 135 to 181 s versus 94 s in the first pass; the two runs here had 65% CPU utilisation on a busy interactive node (I have no `time -v` record of the first pass to compare user time), so I do not attribute the difference to the skills; the trigger part works on the same arrays as before.

### Problems and gaps in the skills (quote, then what I did)

`trigger-efficiency`

1. **`list_hlt_paths.py` dilutes the firing fraction when a path is missing in some files** (bug, on the exact use the skill recommends). SKILL.md:
   "Run it on **one file from every era** you use." The script does `total += n` for every file that has any matching path but adds to `fired[k]` only
   in files that have path `k`. Test with one G and one H file: `--match '^PFHT(800|900)$'` prints `0.10953   21907 HLT_PFHT800` and `0.11594   23188 HLT_PFHT900`;
   the G file alone gives 0.21907 for PFHT800. The fraction for a path absent in H is halved. Fix: keep a per-path event count (only files containing the path),
   or add a column with the number of files that have the path.
2. The same script prints nothing about which file contributed what on stdout (only on stderr), so a saved stdout file is anonymous. I prepended a `#` header from stderr in the `hlt_paths_*.txt` files. A `--per-file` flag, or a header line on stdout, would make the output self-describing.
3. **The skill's `DIJET_EDGES` stops at 3019 GeV** (`turnon.py`, "CMS dijet binning ... use it for m_jj turn-ons so they line up with the fit bins"). The fit bins of this analysis run to 8152 GeV, so I still need the full table in `dijetlib.py`; the skill's table is a duplicate that can drift. I added an assert that it is a subset. Either ship the full table (649 to 14000 GeV, the CMS one) in `turnon.py` or say it is a turn-on-only excerpt.
4. **`find_threshold` rule vs the rule text.** The Key Concepts table says "Lowest bin edge above which every bin is compatible with full efficiency and the pooled ε ≥ target". The function also requires `min_events` reference events above the edge (default 100). It does not change the result here (45776 reference events above 1058 GeV), but the rule as documented in the table and in `references/dijet-2016-example.md` section 3 ("The threshold is the lowest bin edge such that every populated bin above it has a CP upper bound ≥ 0.995 and the pooled efficiency above it is ≥ 0.995") omits it. Mention `min_events` in both, and that `target` has no default shared with the validation (SKILL.md pattern 2 shows `target=0.99` while the quoted `summary.json` numbers use 0.995; the Gotcha "The target changes the threshold" covers it, but the snippet and the quoted numbers sit next to each other).
5. **`plot_turnon` is not documented in SKILL.md beyond its name.** It always draws x error bars and has no offset argument. To overlay the two cross-checks without overlapping markers I passed `edges + 6` as the edges, which works but is a hack. Say that `**kw` goes to `errorbar` (`fmt`, `color`, `ms`, `alpha` all worked), and that the x error bars cannot be switched off (the cross-check markers now have them, the only visible change in the plot).
6. `efficiency()` returns `eff = NaN`, `lo = 0`, `hi = 1` for an empty bin. SKILL.md says "Mask empty bins before plotting ... Never write NaN to HEPData or JSON" but gives no pointer on how to mask for HEPData. A two-line example (`keep = e["den"] > 0`) and a link to the `hepdata` skill would close the loop. I used exactly that mask.
7. The demo line "scripts/turnon.py --demo <3 Run2016G + 3 Run2016H JetHT NanoAOD URLs>" does not say which files; the quoted numbers are reproduced by the first three of each era in the file lists, which I only found by trying. Give the six URLs or say "first three of each list".
8. Scripts are called as `scripts/list_hlt_paths.py` in the examples, relative to the skill directory, which only works from there. Use `<skill>/scripts/...` as the hepdata skill does.
9. Not a skill bug, found while using it: `specification.md` of this validation says the signal paths are "all present in the files; none prescaled". `hlt_paths_2016H.txt` shows `HLT_PFHT800` is absent from 2016H (the skill is right). The analysis already handles it (the skim OR is built from the paths present per file) but the spec sentence is wrong and should be fixed by whoever owns it; I left the spec unchanged.

`hepdata`

1. **`main()` in the template cannot be driven from another script** and `build(sub, args)` has no way to receive inputs: the parser only knows `-o` and `--demo`, `main()` calls `parse_args()` on `sys.argv`, and the validator output goes to stderr only. To call it from `analysis.py` and to keep `hepdata_validation.txt` I changed `main()` to `main(argv=None)` and added `--summary`, `--plots`, `--log`. Suggest shipping `main(argv=None)` and a `--log` option, and a sentence in SKILL.md "add your own arguments for build()".
2. **`phrases` is required by the skill but not set by the template.** SKILL.md Key Concepts: "Keywords | `observables` ..., `reactions` ..., `cmenergies` ..., `phrases`"; `references/cms-procedure.md` checklist: "Keywords: `observables`, `reactions`, `cmenergies` on every table, plus `phrases`". `figure_table()` sets the first three only. I set `t.keywords["phrases"]` after the call. Add a `phrases` argument to `figure_table()`.
3. **`figure_table(..., image=)` and relative paths.** The template `chdir`s to the parent of the output directory before `create_files()`, and hepdata_lib resolves image paths then. SKILL.md shows `t.add_image("plots/mjj_2b.pdf")` with a relative path, which only works if `plots/` sits next to the output directory. I confirmed a relative path fails with `RuntimeError: File plots/trigger_efficiency.pdf does not exist!` when cwd at `create_files` differs. I use absolute paths in memory (they are not written to the YAML: the record only contains `image.png`/`thumb_image.png` names). Say so in the Gotchas.
4. **The multi-index case is not covered.** SKILL.md Gotcha: "Per-category tables: use a string independent variable (`["1 b tag", "2 b tags"]`) rather than an encoded integer index." The demo has one row per category. My fit-results table has 3 fits per category and the injection table 5 scan points per category. I used two independent variables, `category_x("Category", [...])` (repeated labels) plus a numeric non-binned variable (`Number of fit parameters`, `Injection scale factor k`). The validator accepts it. The skill should show this pattern, or say to make one table per category. The injection table had the same encoded integer index (`10*category + j`) as the fit table; the task named only the fit table, I fixed both.
5. **`y_var()` casts every value to `float`**, so counts and ndf are written as `45.0`, `1388.0`. Harmless, but unneeded in a record whose values are integers. Keep ints when the input is integer.
6. **`finite()` misses `numpy.float32` NaN** (`isinstance(np.float32("nan"), float)` is False, tested: it passes). The helpers cast to `float` first so they are safe, but `finite()` called directly on a float32 array is not. Use `np.isfinite` or `numbers.Real`.
7. **Table naming for studies without a paper.** SKILL.md Key Concepts: "Name it after the paper object (`Figure 3a`)". An Open Data study has no figure numbers; I kept descriptive ASCII names ("Trigger efficiency", "Fit results"; the file names are unchanged from the first pass). Add a sentence for that case.
8. **The tarball and the images end up in the committed validation directory.** `create_files()` wrote `submission.tar.gz` (935 KB, with images) next to `hepdata/` as the Gotcha says; I deleted it after each run (it is regenerable) because validation directories should hold small files only. The images in `hepdata/` (PDF converted to PNG plus a thumbnail each, 1.2 MB for 6 tables) are what the skill says `add_image` does but the size is not mentioned. A `--no-tar` option, or tarball into the output directory's parent being optional, would help. `convert` worked from the LCG view as the skill says.
9. `y_var(..., zero_ok=...)` is the template's name for hepdata_lib's `zero_uncertainties_warning=False`; the SKILL.md Gotcha uses the library name. One line connecting the two avoids a search.
10. Statistical choice I kept, not from the skill: data uncertainty is sqrt(N), as in the plots and the first-pass record. For empty high-mass bins this gives a zero uncertainty; the template's own demo uses Poisson (Garwood) intervals, which are better. A sentence in the skill on when to use which would settle this.
11. `references/cms-procedure.md` section 6 describes `validation/dijet-2016/hepdata/` as "6 tables (m_jj spectra per category, fit results, trigger efficiency, b-tag efficiency, signal injection)". Still true; it could now add "with images and string-valued category variables".

Skills not used in this pass: `standalone-script` (LCG view), `lpc-condor` (no resubmission), `awkward-array`/`vector-awkward`/`hist` (not touched).

### Reproduce (this pass)

```bash
set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh
cd validation/dijet-2016
# HLT menus (first file of each era list; second column of data_G.txt / data_H.txt)
../../plugins/cms/skills/trigger-efficiency/scripts/list_hlt_paths.py <2016G file URL> --match '^(PFJet|PFHT|AK8PFJet|CaloJet)[0-9]'
../../plugins/cms/skills/trigger-efficiency/scripts/list_hlt_paths.py <2016H file URL> --match '^(PFJet|PFHT|AK8PFJet|CaloJet)[0-9]'
# full analysis on the 9 local skims (plots/, summary.json, hepdata/, hepdata_validation.txt); peak 3.55 GB
rm -rf plots hepdata
/usr/bin/time -v python3 analysis.py --skims '<scratch>/skims/*.npz' --outdir . --work <scratch>/cache --toys 200 > run.log 2>&1; echo EXIT $? >> run.log
rm -rf __pycache__ submission.tar.gz        # regenerable artefacts
# HEPData only, from summary.json and plots/
python3 make_hepdata.py --summary summary.json --plots plots -o hepdata --log hepdata_validation.txt
python3 check_results.py .                   # 29/29
```
