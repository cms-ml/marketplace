# Independent review of the generic working-point extension of `muon-tag-and-probe`

Reviewer role: ARC plus code review. Subject: uncommitted changes on `feat/tnp-correctionlib-generic` on top of 337e5b7
(`scripts/tnp.py`, `SKILL.md`, `references/tested-2016.md`, `references/working-points.md`, `validation/muon-tnp-generic/`).
These are CMS Open Data results, not CMS results. Everything below was rerun or recomputed by the reviewer on the scratch
inputs (`<scratch>/inputs`: 4 SingleMuon 2016G/H files, 8 powheg `ZToMuMu_M-50To120` files); reviewer scripts and runs are in
`tnp-scratch/generic-review/` (outside the repository). Nothing in the repository was changed except this file.

Verdict vocabulary: CONSISTENT (reproduced / correct), TENSION (reproduced but a claim is partly unsupported or a weakness
matters), INCONSISTENT (claim contradicted by the reviewer's numbers), NOT CHECKED.

## Overall verdict

**Accept after the required fixes (R1 to R6).** The numbers in `summary.json` and the README reproduce exactly, the presets are
bit-identical to the old script, the expression parser is safe, the bootstrap is implemented correctly and covers the
MC-statistics fluctuation. The weaknesses are not in the headline numbers but in what the correctionlib file hands to a user in
degenerate bins (R1), a claim about IsoMu22 that the reviewer could not reproduce (R2), uncertainties that silently omit the
systematic by default (R3), and several small robustness and documentation items. None of them changes a validated result.

## Summary table

| #   | Item                                                               | Verdict                                                             |
| --- | ------------------------------------------------------------------ | ------------------------------------------------------------------- |
| 1a  | Expression parser: safety                                          | CONSISTENT (one uncaught `RecursionError`, R6)                      |
| 1b  | Expression parser: correctness                                     | CONSISTENT (one over-strict rejection, noted)                       |
| 1c  | Bootstrap implementation, seeding, std, combination                | CONSISTENT                                                          |
| 1d  | correctionlib layout, clamp, `up`/`down`                           | TENSION (negative `down`, no POG aliases)                           |
| 1e  | Unmeasured-bin filling and degenerate bins                         | TENSION (R1)                                                        |
| 1f  | Offline paths, exit codes, `--dry-run`                             | TENSION (dry-run does not type-check; `--den` alone, R4)            |
| 2a  | Preset equivalence (a)                                             | CONSISTENT                                                          |
| 2b  | New WP rerun, summary.json spot checks, correctionlib equality     | CONSISTENT                                                          |
| 2c  | Split-MC coverage of `mc_stat`                                     | CONSISTENT (1.036 +- 0.070); finite-MC bias confirmed, uncovered    |
| 2d  | Data-stat (`stat`) coverage (reviewer test, not in the validation) | CONSISTENT (0.85 +- 0.07, slightly conservative)                    |
| 3a  | NanoAOD field meanings and `working-points.md` expressions         | CONSISTENT                                                          |
| 3b  | POG denominators matched                                           | CONSISTENT                                                          |
| 3c  | Soft ID -1.3% at \|eta\| 0.9-1.2                                   | TENSION (real, not a fit artifact, not run-dependent, unexplained)  |
| 3d  | IsoMu22 "prescaled in data, 63 / 75 percent"                       | INCONSISTENT in the numbers (H), mechanism imprecise (R2)           |
| 4   | Claims vs outputs, SKILL.md rules, `marketplace.py check`, paths   | CONSISTENT except R2, R3, R5                                        |
| 5   | Missing golden-JSON mask                                           | CONSISTENT for SFs (effect <= 0.1%), but the skill must say so (R5) |
| 6   | Robustness to modified detector response (reviewer closure)        | NOT CHECKED beyond a background-free pseudo-data test (see below)   |

## 1. Code

### 1a. Parser safety: CONSISTENT

`Expr` walks the `ast` tree and allows only `Constant` (bool, int, float), `Name`, `abs(x)`, `BoolOp`, `UnaryOp`
(`not ~ - +`), `BinOp` (`& | + - * /`) and `Compare` (`< <= > >= == !=`). Nothing reaches `eval`/`exec`. Hostile inputs tried
(all rejected with `ValueError`, exit 2, no side effect; a `touch` payload did not run): `__import__('os').system(...)`,
`().__class__.__bases__[0].__subclasses__()`, list comprehension, lambda call, attribute access (`pt.__class__`), subscript,
strings, f-strings, `**`, `//`, `%`, `<<`, `@`, `:=`, `None`, `Ellipsis`, complex `1j`, `abs.__call__(pt)`, `abs(pt, eta)`,
`abs(x=pt)`, `await`, `in`/`is`, null byte, 300 nested parentheses, 5000-digit integer. Field names become
`Muon_<name>` branch names that must exist in the file (`check_branches`), so a name cannot be an uproot expression.
`1e999` is accepted (inf), harmless.

One gap (R6): `"+".join(["pt"] * 6000) + " > 1"`, a run of 5000 `-` or 3000 `~` raises an uncaught `RecursionError`
(`Expr.__init__` / `_check`, `tnp.py:100-142`; `make_selection` is only wrapped for `ValueError`, `tnp.py:619-623`). The
result is a traceback and exit 1, which the documented exit codes read as "a fit failed". Not exploitable, but the exit code
is wrong. Catch `RecursionError` and `MemoryError` and return 2.

### 1b. Parser correctness: CONSISTENT

Tested on a synthetic jagged muon array against hand-computed truth (31 expressions). Correct: `a and b or c` precedence
(`tightId or mediumId and iso < 0.15` equals `tightId | (mediumId & iso < 0.15)`), `~tightId & mediumId` (`~` first),
`abs(dxy)`, chained `0.1 < abs(dxy) < 0.3` and `20 < pt < 50 < 45`, `dxy < 0.2 < pt`, arithmetic, unary minus,
`highPtId == 2`, `highPtId >= 1`, `mvaId == 1 or mvaId == 3`, scalar constants (`True`, `1 < 2`, `not True`, `~True`)
broadcast to the muon shape. Integer fields used as booleans (`highPtId`, `highPtId & tightId`, `5`, `pt`) raise "needs
booleans". The `a & b < c` guard fires for any `&`/`|` that is a direct operand of a comparison.

Limitation: the guard cannot see parentheses in the AST, so the legitimate `(tightId & mediumId) == True` is rejected with a
message about precedence. Harmless (drop the comparison). Integer bit masks (`(selectors & 4) != 0`) cannot be written; no 2016
UL NanoAODv9 field needs them.

### 1c. Bootstrap: CONSISTENT

Read at `tnp.py:705-762` and `measure`, `mc_eff` (`431-453`).

- Resampled unit: the MC **event** (`evt` index, global over chunks and files; `np.unique(..., return_inverse=True)`).
  A Poisson(1) weight per event multiplies every pair of that event, so the two tag/probe orderings of one Z stay correlated.
  Correct cluster bootstrap.
- Independence: `rng.poisson(1.0, size=(replicas, n_events))` from one seeded `default_rng`; replicas are independent draws,
  the same replica weights are used in every pT-|eta| bin (events in different bins are different events, so no problem).
  Rerunning with the same seed reproduces the stored result bit for bit (reviewer rerun of `mediumid`, all float fields,
  and the correctionlib file are identical to the stored ones).
- Data held fixed, MC efficiency (weighted counting, `mc_eff` with the multiplier) and both MC templates (pass and fail) are
  refitted per replica; SF replica = `edr / emr`. `mc_stat = std(ddof=1)` over replicas, not a percentile. Replicas whose
  MIGRAD minimum is invalid are dropped (`751`), at least 5 must remain, else the binomial counting error is used and a warning is
  written. Dropping failed replicas can bias the std down slightly; the `mc_stat_replicas_ok` field records the count (50 in
  the bins I inspected, the degenerate ones included).
- Combination: `total = sqrt(stat^2 + mc_stat^2 + syst^2)` (`779`), `syst = 0` unless `--syst` (see R3). Data stat (HESSE with
  fixed templates) and MC stat are independent, so quadrature is right; `eff_data_total_err` and the `eff_mc` errors are
  built the same way.
- With 50 replicas the per-bin `mc_stat` itself has about 10% noise (`1/sqrt(2 * 49)`); the right panel of
  `plots/mc_stat_coverage` shows single-bin half/full ratios between 0.6 and 3.6 around the median expectation. Fine for coverage
  of the ensemble, but not a per-bin precision statement.
- Memory: the full `boot` matrix is allocated up front as float64, `replicas x events-with-a-pair` (`708-709`), 400 B
  per MC event that has a pair with 50 replicas (about 0.1-0.2 kB per MC event here). 1.25 M events: no problem (the runs peaked at
  1.9 GB); 10 M MC events adds 1-2 GB, 50 M about 5-10 GB. Draw one replica at a time (reseeding per replica) or use float32 before this meets a larger sample (optional O1).

### 1d. correctionlib output: TENSION

Good: schema v2, `MultiBinning` on (`abseta`, `pt`) inside a `Transform` with `abs(x)`, `flow="clamp"`, `inf` last edge,
string category input; loads, `correction validate` "All OK", strict-JSON parse OK (no `NaN` in any of the 7 stored files).
Reviewer check on my own `mediumid` run: nominal, `up`, `down`, `stat`, `mc_stat`, `syst`, `eff_data`, `eff_mc` equal the
`tnp.py` JSON at every bin centre for +-eta to 2.2e-16, and the quadrature of the components equals the total to 3.5e-18.
Clamping works (eta = 2.5 or NaN returns the last |eta| bin, pT = 10 the first pT bin, pT = 500 the overflow bin).

Weaknesses:

- `down = nominal - total` is not clipped for the SF (`tnp.py:539-540`), unlike the efficiencies (`541-545`). Stored
  `mediumid`, |eta| 0.9-1.2, pT > 120: `nominal 0.877, up 1.763, down -0.0093`: a negative event weight if a user applies the
  down variation. Clip at 0 (and see R1).
- The SF category keys are `nominal/up/down/stat/mc_stat/syst`, while the POG file uses `nominal/systup/systdown/stat/syst`.
  `evaluate(..., "systup")` fails with "Index not available in Category". Not wrong, but a drop-in replacement of the POG
  correction in an analysis (or a benchmark harness that asks for `systup`) needs aliases. Optional O2.
- Clamping is silent for pT below the first edge (15 or 26 GeV) and |eta| > 2.4 with no uncertainty inflation. Document it as
  extrapolation; an out-of-acceptance muon gets the edge-bin value with the edge-bin error (optional O3).

### 1e. Unmeasured bins and degenerate bins: TENSION (R1)

`_grid` (`487-498`) fills a bin that was not measured (fewer than 50 data or gen-matched MC probes, `720`) with the nearest
measured pT bin of the same |eta| row, value and uncertainty alike (`539-545`); with no measured bin in the row the SF is
1 +- 1. This is **documented** (docstring `501-508`, `references/working-points.md`, the `unmeasured_bins` and `warnings`
fields, a stderr warning at `803-805`) but **not** in `SKILL.md`, not in the per-correction `description` of the correctionlib
file, and the copied uncertainty is not inflated. For a plateau (IsoMu24 200+ GeV) that is a reasonable central value, but
an under-stated uncertainty for an extrapolation. Acceptable if flagged in the file and the uncertainty is inflated (R1).

The bigger problem is the opposite case, bins that **are** measured but have an empty or useless fail category. In the stored
runs this happens in the pT > 120 GeV bins of the loose ID (3 of 4 |eta| bins), medium ID (2), tight iso (2, SF values below) and
others (bins with total error > 0.05 read from the stored correctionlib files and run JSONs):

| WP (                                                                 | eta | , pT > 120) | n_data | n_MC gen | eff data      | eff MC       | SF            | total err | fit_ok |
| -------------------------------------------------------------------- | --- | ----------- | ------ | -------- | ------------- | ------------ | ------------- | --------- | ------ |
| medium ID, 0.9-1.2                                                   | 191 | 224         | 0.8769 | 1.0000   | 0.877         | 0.886        | True          |
| medium ID, 2.1-2.4                                                   | 73  | 106         | 0.7693 | 1.0000   | 0.769         | 0.588        | True          |
| loose ID, 1.2-2.1                                                    | 406 | 521         | 0.9455 | 1.0000   | 0.945         | 0.893        | True          |
| tight iso, 0.9-1.2 / 2.1-2.4 (SF from the stored correctionlib file) |     |             |        |          | 0.951 / 0.903 | 0.97 / 0.886 | not inspected |

MC efficiency is exactly 1 (no failing probe), the data fit has no information on the efficiency and returns whatever Minuit
leaves (0.8769 for both medium and loose in the same bin), `fit_ok` is True, and the correctionlib file stores these numbers
as `nominal`. The uncertainty is honest (0.6-0.9), but any user who applies `nominal` to muons above 120 GeV gets a 12-23% wrong
weight, and the README's end-to-end test shows it without explaining it (min SF 0.769). A benchmark scored by pulls survives it
(huge error), an analysis does not. See R1 for the fix. The SKILL.md gotcha "Fits at eps -> 1" describes the symptom but not that
the file inherits it.

### 1f. Offline paths, exit codes, `--dry-run`: TENSION

Reviewer CLI matrix (17 cases, `tnp-scratch/generic-review/cli_test.sh`): `--dry-run` exit 0 and prints definition, binning,
`DRY_RUN=1`; unknown field, unknown `--tag-hlt` path, missing file, bad trigger spec (`2`, `2:abc`), decreasing or non-numeric
edges, `--correctionlib == --out`: all exit 2 with a clear message; a missing second data file with `--max-events` stops before
it (legacy behaviour). `--pog-json /nonexistent` and `--no-pog --no-pu` complete with the warning recorded and exit 0/1 from the
fit status. Problems:

- `--dry-run --num highPtId` exits **0**; the real run fails with exit 2 ("needs booleans") only after reading the first chunk. The README and SKILL.md say `--dry-run` "checks the expressions": it checks syntax and branch names, not
  types. Evaluating the expressions on a 100-event slice of the first file would make the statement true (R4).
- `--den mediumId` with no `--num` silently measures the **tight ID** numerator (`tnp.py:617-618` sets `wp = "tightid"`, then the
  explicit `--den` overrides the preset's denominator). Result: "tight ID with a medium-ID denominator" under the name
  `muon_sf`, no POG. Make "no numerator" an error whenever `--den`, `--tag`... is given without `--num`, `--num-trigger` or
  `--wp` (R4). `--wp isomu24 --num mediumId` ANDs a numerator with the preset's trigger; documented, but surprising.
- `parse_trigger("0:24")` (mask 0) never matches, giving efficiency 0 with no warning; `2:24:0` and negative thresholds are also
  accepted (`tnp.py:199-215`). `2|8&1` silently means "all of 1, 2, 8". Reject mask 0 and mixed `|`/`&` (R6).
- A mistyped `--pog-json` degrades to a warning plus exit 0/1. That is the intended offline behaviour for the benchmark, but an
  interactive user gets no comparison and a normal exit code; consider an explicit `--strict` (O4).
- The bin threshold is "50 data and 50 gen-matched MC probes" (`720`), low for a 45-bin simultaneous fit; this is what produces
  the degenerate bins in 1e.

No bug that changes a validated result was found: `tnp_pairs`, `_trigger_match`, `fit_pass_fail` (exp branch), `mc_eff` and the
bin loop are unchanged in behaviour for the presets (confirmed bitwise, 2a).

## 2. Reproduction

### 2a. Preset equivalence: CONSISTENT

I ran the pre-change script (`git show HEAD:...tnp.py`) and the new script (presets, `--mc-replicas 10`) on the same four data and
eight MC files. Per-bin legacy fields (`n_data eff_data eff_data_err eff_mc eff_mc_err sf sf_err pog_sf pog_unc pull fit_ok`):

| preset   | bins | max abs diff | `RMS_PULL` old / new (stdout)           |
| -------- | ---- | ------------ | --------------------------------------- |
| tightid  | 32   | 0            | 1.2912157651122185 / 1.2912157651122185 |
| tightiso | 32   | 0            | 1.993288326069797 / 1.993288326069797   |
| isomu24  | 26   | 0            | 3.5370441319524843 / 3.5370441319524843 |

(The bootstrap does not touch the nominal fit, the replica count is irrelevant for the legacy fields.) The exit codes agree
(0, 0, 1). The reviewer did not rerun the `--den/--num/...` spelled-out variants; their equality is in `summary.json` (identical
for all three). The old-script file used by `run_all.sh` is pinned to `git show 337e5b7`, which will not resolve after a squash
merge that drops the commit; keep the old script or a note on how to rebuild it (O5).

### 2b. New working point, summary.json, correctionlib: CONSISTENT

`mediumid` with the exact job arguments (`--syst`, 50 replicas, `--correctionlib`): all 32 bins identical to the stored run in every
float field (max abs diff 0), stored correctionlib file identical to the new one, `correction validate` All OK. SF/POG
over 30-60 GeV (inverse total variance), RMS `pull_total` and the number of bins with |pull_total| > 3, recomputed from the stored run
JSONs for 9 working points (`wp_tightid`, `wp_tightiso`, `wp_isomu24`, medium, loose, soft, highPt, loose PF iso, loose tracker
iso) all equal `summary.json` and the README table (e.g. medium 0.9977 / 1.69 / 2; soft 0.9966 / 3.12 / 5; tight iso 1.0028 / 1.54).
Resources match (22-68 s, <= 2.0 GB; mine 31-63 s, 1.65-2.0 GB). `check_results.py`: `SUMMARY=50/50`. Note that the (b) check
tolerance (1% on the weighted SF/POG) is looser than the claims, so it would also pass the soft ID; it is a sanity check, as the
README says.

### 2c. Split-MC coverage: CONSISTENT; finite-MC bias confirmed

Recomputed from the stored `halfA_*`, `halfB_*` runs, z = (SF_A - SF_B) / hypot(mc_stat_A, mc_stat_B), bins where both fits are ok:

| WP        | bins | RMS z              | mean z | RMS z, binomial MC error | median mc_stat half/full A; B |
| --------- | ---- | ------------------ | ------ | ------------------------ | ----------------------------- |
| tight ID  | 30   | 0.980              | +0.03  | 1.27                     | 1.48; 1.38                    |
| tight iso | 30   | 1.074              | +0.52  | 8.77                     | 1.40; 1.25                    |
| IsoMu24   | 22   | 1.074              | +0.15  | 1.17                     | 1.38; 1.26                    |
| medium ID | 29   | 1.023              | -0.23  | 1.37                     | 1.36; 1.22                    |
| all       | 111  | **1.036 +- 0.070** | +0.12  | **4.69**                 |                               |

Identical to the README (1.04 +- 0.07, 4.69, 69% below 1 sigma, 94% below 2 sigma). Expected half/full ratios are 1.48 (A, 46% of
the MC) and 1.36 (B, 54%): the measured ones are 0-10% lower, as stated. Caveats: tight iso has mean z +0.52 (2.8 sigma on 30 bins,
the same sign as the bias below); the halves are split by file, not randomly, and the two halves are unequal; the 111 bins of four
WPs share events.

The finite-MC bias (SF_A + SF_B)/2 - SF_full: at 30-60 GeV the unweighted mean is +0.0021 (tight ID), +0.0011 (tight iso), +0.0016
(IsoMu24), +0.0018 (medium), 42 of 43 bins positive, i.e. 0.8-2.6 x `mc_stat`; precision-weighted it is +0.0005 to +0.0012. This
reproduces "+0.0011 to +0.0020". With a 1/N scaling and halves of 46% and 54%, `(A+B)/2 - full` is about the bias of the full-MC
SF itself, so a +0.1-0.2% one-sided bias in the delivered SFs is likely and **no uncertainty covers it**. The README, SKILL.md and
tested-2016 all say so; that is the honest treatment. For a benchmark with 0.1-0.2% total uncertainties that is about 1 sigma and
one-sided; it should be in the report to the benchmark as a known limitation (O6).

### 2d. Data-statistics coverage (reviewer addition): CONSISTENT

Not tested in the validation. Data split by file (G1+H2 vs G2+H4), same MC (`--mc-replicas 0`), z = (SF_1 - SF_2)/hypot(stat_1,
stat_2) (the MC cancels), bins with a fit ok and stat error < 0.05: tight ID 28 bins RMS 0.80, medium ID 28 bins 0.84, tight iso 25
bins 0.92, together 81 bins RMS **0.85 +- 0.07**, no |z| > 2. The HESSE data-stat error is slightly conservative, so there is
no hidden undercoverage from using each Z muon pair twice (each muon as tag).

## 3. Physics

### 3a. Field meanings and expressions: CONSISTENT

Branch titles read from `G1.root` (2016 UL NanoAODv9): `Muon_highPtId` "1 = tracker high pT, 2 = global high pT, which includes
tracker high pT" (so `== 2` is the global high-pT ID, `>= 1` the tracker high-pT ID, as in the table; values seen 0/1/2 only);
`Muon_mvaId` "1=MvaLoose ... 5=MvaVVTight" (doc: `>= 1`, `>= 2` correct); `Muon_softId` bool; `Muon_tkRelIso` "trkIso/tunePpt";
`Muon_pfIsoId` 1 VeryLoose ... 6 VeryVeryTight; `Muon_tkIsoId` 1 Loose, 2 Tight; `TrigObj_filterBits` for muons "1 = TrkIsoVVL, 2 = Iso,
4 = OverlapFilter PFTau, 8 = IsoTkMu, 1024 = 1mu (Mu50)". Numerical check on 379 k muons: `pfIsoId >= k` equals `pfRelIso04_all <
{0.40, 0.25, 0.20, 0.15, 0.10, 0.05}` for k = 1..6 with **0** mismatches, `tkIsoId >= 1 (2)` equals `tkRelIso < 0.10 (0.05)` with
50 (66) mismatches of 379 k (1e-4, float rounding at the cut). `tightId` is not a subset of `mediumId` (1608 of 300 k tight muons
fail medium in this file), which matters only if someone writes `--den mediumId` expecting the tight set.

### 3b. POG denominators: CONSISTENT

All names in the table exist in the 2016postVFP `muon_Z.json.gz` (29 corrections, listed): `NUM_{Loose,Medium,MediumPrompt,Tight,
Soft,HighPt,TrkHighPt}ID_DEN_TrackerMuons`, `NUM_LooseRelIso_DEN_{LooseID,MediumID,MediumPromptID,TightIDandIPCut}`,
`NUM_TightRelIso_DEN_{MediumID,MediumPromptID,TightIDandIPCut}`, `NUM_{Loose,Tight}RelTkIso_DEN_{HighPtID,TrkHighPtID}andIPCut`.
`NUM_LooseRelIso_DEN_MediumID` (used, `--den mediumId`) and `..._DEN_LooseID` (listed in the doc) both exist, so there is no
mismatch; the run used `mediumId` and agrees at +0.04% (30-60 GeV). The loose tracker-iso denominator `highPtId == 2` matches
"HighPtIDandIPCut" because the CMSSW high-pT ID already contains |dxy| < 0.2 and |dz| < 0.5 (stated in the doc; SF/POG 1.0007).
The tight-iso denominator spelt out with the explicit IP cuts is also right. The doc table lacks the other combinations
(`TightRelIso_DEN_MediumID`, `LooseRelIso_DEN_TightIDandIPCut`, ...) but does not claim them. Mu50 `1024:50` is marked "not tested".

### 3c. Soft ID -1.3% at |eta| 0.9-1.2: TENSION (reproduced, unexplained, not a fit artifact)

README: "cause not studied". Reviewer tests:

1. Per pT bin (stored softid run): |eta| 0.9-1.2, SF 0.9914, 0.9951, 0.9939 at 30-40, 40-50, 50-60 GeV against POG 1.0074, 1.0073,
   1.0069 (pull_total -8, -10, -6); 20-25 GeV agrees (1.0072 vs 1.0068), 25-30 is -0.9%. The POG value is flat in pT to 0.1%.
   Barrel is also low by 0.4% at 25-50 GeV (pull -2.6 to -6.5); |eta| 1.2-2.4 agrees within 0.15%.
2. Not a fit artifact: sideband-subtracted counting (pass and fail, 80-100 GeV signal, 70-80 and 100-115 sidebands, data and MC) at
   30-60 GeV gives SF 0.9945 (barrel), **0.9926** (0.9-1.2), 0.9972, 0.9985, against the template fit 0.9944-0.9962,
   0.9914-0.9951 in the same bins. The same counting for medium ID gives 0.9955 / 0.9952 / 0.9943, i.e. no overlap-region effect in
   the medium ID.
3. Not run-dependent: G only (G1+G2) and H only (H2+H4), `--mc-replicas 0`: at 0.9-1.2, 30-60 GeV SF G 0.9926 / 0.9962 / 0.9992,
   H 0.9908 / 0.9944 / 0.9908; barrel G 0.9957 / 0.9957 / 0.9947, H 0.9941 / 0.9937 / 0.9965.
4. Medium and loose ID, which share most of the quality requirements, agree with the POG in the same bin (+-0.3%), so the data
   and MC samples are not simply different in that detector region.

So this is a real data/MC difference in the soft-ID numerator of these samples compared with the POG SF. A definition mismatch is
possible but cannot be shown from NanoAOD: `Muon_softId` is the miniAOD `SoftCutBasedId` (TMOneStationTight, > 5 tracker layers,

> 0 pixel layers, high-purity track, |dxy| < 0.3, |dz| < 20 cm), which is the only ID here whose numerator depends on the
> single-station segment match and the layer counts; the POG Z-based soft-ID SF comes from its own TnP set-up and possibly a different MC generator (not checked by the reviewer), and a SF
> flat to 0.1% across pT may hint at a parametrised or extrapolated result (speculation). The denominator is not a candidate
> (`isTracker` is the POG `TrackerMuons` selection, and loose/medium/tight/high-pT with the same denominator agree). Next steps:
> a phi-resolved ratio in |eta| 0.9-1.2, the MC generator dependence (the validation only has powheg), the J/psi soft-ID SF at low pT.
> Until then the skill should say that soft ID disagrees with the POG by up to 1.3% at |eta| 0.9-1.2 and 0.4% in the barrel. The
> README sentence "All new working points agree ... within 0.3 percent at 30-60 GeV, except soft ID at |eta| 0.9-1.2" is fair but omits
> the barrel offset; `tested-2016.md` says "other |eta| bins within 0.5%", which is correct but hides pulls of -5 to -6 in the barrel.

### 3d. IsoMu22 "prescaled in data": INCONSISTENT in the numbers, mechanism imprecise (R2)

The claim in README, SKILL.md and `working-points.md`: `HLT_IsoMu22` fired in 63 (G) and 75 (H) percent of the `HLT_IsoMu24`
events (MC 100 percent), "prescaled", "no bit-2 object below 24 GeV is left". The numbers 63/75 are in no stored artifact
(not in `summary.json` or any script). Reviewer, directly on the four data and two MC files:

| file          | P(IsoMu22 given IsoMu24) | P(IsoMu22 given IsoMu24 or IsoTkMu24) | P(IsoMu22 or IsoMu22_eta2p1 or IsoTkMu22) |
| ------------- | ------------------------ | ------------------------------------- | ----------------------------------------- |
| G1            | 0.611                    | 0.591                                 | 0.952                                     |
| G2            | 0.633                    | 0.611                                 | 0.954                                     |
| H2            | 0.480                    | 0.464                                 | 0.934                                     |
| H4            | 0.489                    | 0.473                                 | 0.936                                     |
| MC (mc2, mc3) |                          | 0.991                                 | 1.000                                     |

- G reproduces (63%). **H does not: 48-49%, not 75%.** MC is 99.1%, not 100%.
- The path is **enabled or disabled per run and lumi section, not randomly thinned**: per run P(IsoMu22 given IsoMu24) is 0.00 or
  1.00 for most runs (the intermediate values, e.g. 0.66, 0.51, 0.34, are mixtures of whole lumi sections), and within the largest run of each file no lumi section has a fraction between 0.05 and 0.95 (fraction of LS at
  1.0: 0.71 G1, 0.90 G2, 0.62 H2, 0.39 H4). That is a prescale column switching between 1 and 0, not a prescale N. "Prescaled"
  is an acceptable shorthand, the fraction is a property of the lumi-section mix of the files and changes with the choice of files.
  The sample-to-sample spread (G 0.61-0.63, H 0.48-0.49) is exactly why the fraction cannot be a constant of the dataset.
- "No bit-2 object below 24 GeV is left" is not right: events with a bit-2 object at 22-24 GeV and none at >= 24 GeV (205 k-227 k per H
  file) have `HLT_IsoMu22` fired in only 49-63% of them, i.e. the object exists without IsoMu22 (other Iso-filter paths such as
  `IsoMu22_eta2p1` set the same bit). That is why the SF collapses only at |eta| > 2.1 (0.53), where `IsoMu22_eta2p1` cannot fire.
  `IsoMu22_eta2p1` fired in 87.5% of IsoMu24 events in data against 90.7% in MC (a 3.5% relative gap, so it is not fully
  unprescaled either).

The conclusion (do not measure a lower-threshold path's SF from these files without the trigger-enable information) stands; the
numbers and the mechanism need correcting, and the stored evidence (a small script and its output) is missing.

## 4. Claims against outputs, SKILL.md rules, hygiene

- `python3 scripts/marketplace.py check`: `OK: 3 plugins, 11 skills, 2 agents, 0 errors, 0 warnings`.
- SKILL.md: frontmatter `name` + `description` + `metadata.summary` only, description starts "Use when", **299 lines** (target 300,
  so any addition must be paid for with a move to `references/`), `## Gotchas` present, `## Reference Files` then `## Docs` last,
  both references linked, `scripts/tnp.py` linked. No `ashrivas`, `/uscms`, `/afs` or home paths in the skill or the validation
  (only the regex in `check_results.py`); `<scratch>` placeholders in README/`run_all.sh`. Results JSONs and `summary.json` are
  excluded from prettier in `.pre-commit-config.yaml`. Plots carry the "CMS Open Data" label, no "CMS" result claims in the text.
- Canonical pattern 3 reproduces: `mediumid` 40-50 GeV barrel `SF 0.9961 POG 0.9993 ... total 0.0006`, `N_BINS=32 N_FIT_FAILED=0`.
- Claims the outputs do not back: (i) IsoMu22 63/75/100 percent (3d); (ii) "`--dry-run` checks the expressions" (1f); (iii) the
  `tested-2016.md` sentence "all new working points within ..." is right but the sentence "Soft ID is 1.3% below the POG ... (other
  |eta| bins within 0.5%)" omits that the barrel is 0.4% low at pull -5 to -6; (iv) the default `sf_total_err` and `up`/`down` of the
  correctionlib omit the systematic unless `--syst` is given, while SKILL.md section 6 and the key-concepts table present
  "total" and "up/down" as the uncertainty (R3); (v) "Each run ... about 1 min and 1.9 GB with 50 bootstrap replicas and `--syst`" is
  true for this 7 M + 1.25 M sample only (1c, memory).
- The "syst" components (background shape, window, tag) were never validated against truth; the stored evidence is the comparison with
  the POG, where RMS pull_total is 0.9-1.7 for tight ID, high-pT, loose, medium, loose iso, tracker iso and 2.7-3.1 for IsoMu24 and
  soft ID. With POG uncertainties of 0.01-0.3% a per-mille offset gives |pull| of 3-6, as the README says; pulls against the POG say
  little about coverage. The only coverage tests are the MC-split (2c) and, from this review, the data-split (2d).
- SKILLS_USED.md is accurate to what I can see; it lists no step that used `analysis-spec-builder` (not needed here).

## 5. Golden-JSON lumi mask: CONSISTENT for SFs, but the skill must say it (R5)

`tnp.py` applies no lumi mask (as the old script). Reasoning: the SF is a ratio of data to MC efficiency in the same selection; a
lumi section outside the golden JSON is one the certification flagged (subsystem off, bad DCS, trigger or reconstruction problem).
If the efficiency in those sections is the same, the mask does not matter; if not, an unmasked sample shifts the data efficiency by
`f_bad * (eps_bad - eps_good)`. MC carries no mask. For the pileup-weighting the JSON-based LUM profile refers to certified data.

Measured: the four data files are 95.6% inside `Cert_271036-284044_13TeV_Legacy2016_Collisions16_JSON.txt` (99.0% inside the
`MuonPhys` version), 95.7% / 99.2% of the tag-probe pairs. Medium ID and soft ID SFs refitted at 30-40, 40-50, 50-60 GeV in all
four |eta| bins (12 bins each, 3 selections each, `tnp.measure`, same MC): none vs golden vs MuonPhys differ by **0.0000-0.0006** in all bins except
medium ID 2.1-2.4, 50-60 GeV (+0.0010, golden), always below the data stat error (0.0003-0.0035 in these bins) and below the
per-bin total uncertainty. So omitting the JSON is immaterial at the validated level (<= 0.1%), for a 7 M-event subset. A short
gotcha is needed because (i) the skill's statement "`tnp_pairs()` keeps no run, lumi" is easy to miss, (ii) an analyst may carry the SFs
into an analysis that does apply the mask, and (iii) the number above is the evidence. The benchmark has no certification, so it
is irrelevant there. Also worth stating: the data subset (2 G + 2 H files) has a lumi-section mix that differs from the full postVFP
era the pileup JSON and the POG SF refer to.

## 6. Reviewer closure test of robustness (NOT CHECKED beyond this)

The benchmark uses simulated worlds with modified detector response. The validation only runs on real data against the POG, where
the data and MC Z peaks agree, so nothing tests that. A limited test: templates from MC half A (5 files), pseudo-data from MC half B
(3 files), efficiency fitted in 20 bins of tight ID (|eta| x pT 20-120 GeV), truth = gen-matched efficiency in B. With the mass of
the pseudo-data scaled by +0.2%, +0.5%, +1%, -0.5% or smeared by an extra 1 or 2 GeV, the fitted efficiency moves by at most
0.03% from the unmodified case, so a peak shift of 0.9 GeV is absorbed because pass and fail shift together. This is **not** a
clean test: pseudo-data from DY MC has no real background, and the unmodified case already sits +0.31% (mean pull +1.75, 20 bins)
above the truth, with the true background at its boundary (0) so a positive bias is expected (a variant with the templates taken from the pseudo-data itself gives
invalid fits in 18 of 20 bins). Background-dominated bins, a data-vs-MC resolution difference with real background, and trigger or isolation
variables that depend on the detector response were not tested. Recommendation: a closure with a realistic non-prompt background
and a scale/resolution nuisance (float a Gaussian smearing of the template, or add a template-smear systematic) before claiming
robustness (O7).

## Required fixes before a PR

- **R1. Degenerate and filled bins in the correctionlib output.** In `main`/`write_correctionlib` flag a bin as unreliable when the
  fail yield of either sample is below a few events (MC eff exactly 1, data fail < ~5), or `sf_stat > 0.1`, or the fit status is not ok;
  then do not write the raw SF as `nominal` (use the neighbouring pT bin or SF = 1 with a large uncertainty, as for an unmeasured
  bin), add the bin to `unmeasured_bins` and `warnings`, and write the list of filled/flagged bins into the correctionlib `description`.
  Inflate the uncertainty of filled bins (e.g. add the difference to the next measured bin in quadrature). Clip the SF `down` at 0
  (`tnp.py:539-540`). Failure scenario today: `tnp.py --den isTracker --num mediumId ...` returns a correctionlib file with
  `mediumid(1.0, 500, "nominal") = 0.877` and `down = -0.009`; all muons above 120 GeV at |eta| 0.9-1.2 are corrected by -12%.
  Add the rule to the "Fits at eps -> 1" gotcha.
- **R2. IsoMu22 gotcha.** Replace 63-75/100 percent by what the files give (G 0.61-0.63, H 0.48-0.49, MC 0.99), say the path is switched
  on and off by lumi section (not a random prescale), drop "no bit-2 object is left" (the object is there from other Iso-filter
  paths; `IsoMu22_eta2p1` covers |eta| < 2.1), and add the small script that produces the numbers to the validation so that
  `check_results.py` can test them. Fix README, SKILL.md, `working-points.md`, `tested-2016.md` together.
- **R3. Make the default uncertainty complete.** Without `--syst`, `sf_total_err`, `up`/`down` and the correctionlib `up`/`down` contain
  only `stat` and `mc_stat` (`tnp.py:765-779`). Either switch `--syst` on whenever `--correctionlib` is given (cost: 4 extra fits per bin) or write a warning and say in SKILL.md ("Report", Key Concepts) and `working-points.md` that `up`/`down` exclude the systematic
  unless `--syst` is used, and that the finite-MC bias is in none of them.
- **R4. Argument validation.** (a) `--den`/`--tag*` without `--num`, `--num-trigger` or `--wp` should exit 2, not silently measure tight ID
  (`tnp.py:617-618`). (b) Evaluate every expression on a small slice of the first data and MC file in `--dry-run` so that
  "checks the expressions" is true (integer used as boolean, `Muon_` field present but wrong type), or reword the README and SKILL.md.
- **R5. Golden-JSON gotcha in SKILL.md.** One short entry: `tnp.py` applies no certification JSON; on 4 files 4.4% of events are outside
  the golden JSON (1.0% outside MuonPhys) and the SFs change by <= 0.0006 (one bin 0.0010), below the statistical error; apply the JSON
  if the SFs are to be quoted for a certified-data analysis. SKILL.md is at 299 lines: move the long IsoMu22 / finite-MC-bias gotchas
  or Pattern 4 and 5 text into `references/` to stay under 300.
- **R6. Small robustness items in the parser and trigger spec.** Catch `RecursionError` and `MemoryError` in `make_selection`
  (exit 2, `tnp.py:619-623`); reject `parse_trigger` specs with mask 0, a mixed `|`/`&`, or non-positive DR (`tnp.py:199-215`).

## Optional follow-ups

- O1. Generate the Poisson replicas one at a time (float32 or per-replica reseed) so memory does not scale with replicas x events.
- O2. Add `systup`/`systdown` (and `down`/`up` aliases) so the SF correction is a drop-in for the POG file.
- O3. Document clamping as extrapolation in SKILL.md and in each correction `description`; inflate the uncertainty outside the measured range.
- O4. `--strict` to turn an unreadable `--pog-json`/`--pu-json` into exit 2 for interactive use; keep the lenient default for the benchmark.
- O5. Keep the pre-change script (or a rebuild recipe) in the validation, since `git show 337e5b7` will not survive a squash merge.
- O6. Reduce or model the finite-MC bias: use all available MC, fit with Barlow-Beeston-lite templates or smoothed (Gaussian-convolved
  or analytic) templates, or add a bias term (about 1 x `mc_stat`, one-sided) to the total; test it with the same split-MC protocol on more
  than one pair of random (not file-based) halves. Increase `--mc-replicas` when the per-bin `mc_stat` precision matters.
- O7. A closure with realistic background and with a data/MC mass-scale and resolution difference; a pure-fit closure on MC pseudo-data
  (as above) shows a +0.3% eff offset that should be understood.
- O8. Soft ID: phi-resolved ratio in |eta| 0.9-1.2, powheg vs aMC@NLO, and a statement in the skill that soft ID disagrees with the POG.
- O9. Raise the bin threshold (50 probes) or require a minimum number of fail-category events; add the data-split coverage test (2d) to
  `summarize.py` and `check_results.py`; tighten the (b) tolerance for the presets or state a pull-based expectation.
- O10. The README table in (b) could state the per-|eta| soft-ID barrel offset (0.9958) explicitly.
