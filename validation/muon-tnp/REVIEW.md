# ARC review of the muon-tnp validation

Reviewed: `validation/muon-tnp/` (student outputs) against `plugins/cms/skills/muon-tag-and-probe/`
(SKILL.md, `scripts/tnp.py`, `references/tested-2016.md`), 2016G+H Open Data, every 5th data file.
All numbers below were recomputed in a scratch area (`$SCRATCH/review/`: `pogcheck.py`, `lumicheck.py`,
`trigtests.py`, `trigtests2.py`, `trigtests3.py`, with outputs `*.out`); nothing outside this file was changed.
These are Open Data results, not CMS results.

## Verdicts per item

| #   | Item                                                                  | Verdict                                                                                                             |
| --- | --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| 1   | Reproducibility                                                       | CONSISTENT                                                                                                          |
| 2   | Correctness of the POG comparison                                     | CONSISTENT, with caveats (2a-2d)                                                                                    |
| 3   | Plausibility of the IsoMu24 +1-1.5% offset (is it a method artefact?) | TENSION: the offset is robust; cause not found; the student's "independent of the match definition" is over-claimed |
| 4   | Unsupported or fabricated numbers, paths, claims                      | TENSION: no fabricated numbers, no personal paths, but 5 over-claims (4a-4e)                                        |
| 5   | Skill statements contradicted by the validation                       | INCONSISTENT: 4 statements must change (section 5)                                                                  |
| -   | Overall                                                               | Sound enough to accompany the PR **after** the fixes in section 6                                                   |

### 1. Reproducibility: CONSISTENT

- Reran `run_all.sh` on a copy of the tree (`SCRATCH` pointing at the existing skims, golden JSON and lumi CSV re-downloaded from
  Open Data EOS). The new `summary.json` equals the committed one in every field (0 differences, only `runtime_s` ignored),
  including the re-run `explore_trigger` scan. `check_results.py` gives `SUMMARY=13/14`, exit 1 (the one failure is the
  tight-iso RMS pull 2.54 > 2, which the student reports openly).
- POG values re-evaluated with plain `correctionlib` on `muon_Z.json.gz` (2016postVFP_UL) at the bin centres: maximum
  |difference| to `summary.json` for nominal and `systup - nominal` over all 91 bins = 0. Pulls recomputed from `sf`,
  `sf_total_err`, `pog_sf`, `pog_unc`: mean/RMS = +0.515/0.781 (tight ID), +1.848/2.540 (tight iso), +4.897/6.631 (IsoMu24), as reported.
- Luminosity recomputed with my own code from the skim lumi-section list, the golden JSON and the `recorded` column (index 6) of
  `pp_2016lumibyls.csv`: 20069 LS processed, 19319 certified, all 19319 found in the CSV, **3.5534 fb^-1** (G 1.6214, H 1.9320),
  full G+H golden 16.393 fb^-1, fraction 21.7%. Run range 278820-284043 (no 2016F). Matches the student to 4 digits.
- Not checked: that the golden file and CSV are Open Data records 14220 and 1059 (taken from PROMPT.md; I did not open the records);
  that no lumi section straddles processed and unprocessed files (the lumi is the full CSV value of every LS seen, so a split LS
  would overestimate by at most a boundary-LS fraction; lumi is not used in any ratio).

### 2. Correctness of the comparison: CONSISTENT, with caveats

- Correction names, era file and denominators are right: `NUM_TightID_DEN_TrackerMuons` (isTracker, tightId),
  `NUM_TightRelIso_DEN_TightIDandIPCut` (tight ID, |dxy|<0.2, |dz|<0.5, pfRelIso04<0.15),
  `NUM_IsoMu24_or_IsoTkMu24_DEN_CutBasedIdTight_and_PFIsoTight` (tight ID, iso<0.15). POG file `2016postVFP_UL`; bins come from the JSON
  edges; |eta| clamping is unnecessary because only in-range bins are evaluated (pT edges 15 or 26 GeV verified in the JSON).
- Pileup weights: `puWeights.json.gz` of 2016postVFP_UL has a single correction (`Collisions16_UltraLegacy_goldenJSON`), so "first correction" is right.
  Removing the PU weights changes the barrel 40-50 GeV IsoMu24 SF by only -0.0007.
- (2a) The POG uncertainty `systup - nominal` equals hypot(`stat`, `syst`) to 1e-12 in every bin. It is 0.03-0.1% for ID/iso/trigger at 30-60 GeV,
  so pulls are dominated by the POG's tiny quoted error and are not Gaussian. Mean/RMS pull is therefore a poor summary; a relative
  offset (SF/POG - 1 with its uncertainty) is the quantity to quote. README gives it as "mean SF/POG" but see 2b.
- (2b) README's headline `mean SF/POG` = 1.0237 (IsoMu24) is an unweighted mean over all 27 bins including 120-200 and 200+ GeV bins with 1-6% errors.
  The high-statistics 30-60 GeV bins give 1.0128 (mean) and 1.0121 (inverse-variance weighted, my counting). Quote the latter.
- (2c) Bin-centre vs probe-averaged POG: identical pulls (verified from `pull_pog_avg`).
- (2d) The tight-ID result is robust to the method: simple counting in 80-100 GeV (no fit, no background) gives SF 0.9865/0.9786/0.9890/0.9718 at
  40-50 GeV against POG 0.9867/0.9792/0.9915/0.9764. Tight iso counting gives 0.9987/1.0011/1.0014/1.0058 against 0.9969/0.9983/0.9998/1.0014,
  i.e. the +0.2-0.4% iso offset is **not** a fit artefact (README says only that a part may be MC statistics; that was tested for tight ID only, not for iso).

### 3. The IsoMu24 offset: TENSION (robust, unexplained)

Confirmed independently, without fits, at 40-50 GeV (counting; student's fit values in brackets; POG 0.9627/0.9631/0.9964/0.9607):

| Variation                                          | SF              | eta             | 0-0.9           | 0.9-1.2         | 1.2-2.1 | 2.1-2.4 |
| -------------------------------------------------- | --------------- | --------------- | --------------- | --------------- | ------- | ------- |
| baseline (counting)                                | 0.9766 [0.9767] | 0.9711 [0.9721] | 1.0042 [1.0047] | 0.9745 [0.9763] |
| MC without PU weights                              | 0.9759          | 0.9704          | 1.0018          | 0.9670          |
| window 80-100 / 85-95                              | 0.9766 / 0.9769 | 0.9714 / 0.9714 | 1.0046 / 1.0041 | 0.9753 / 0.9726 |
| tag pT > 35 / > 40                                 | 0.9765 / 0.9765 | 0.9710 / 0.9706 | 1.0042 / 1.0052 | 0.9759 / 0.9772 |
| no HLT requirement / path-specific event match     | 0.9766 / 0.9766 | 0.9710 / 0.9710 | 1.0046 / 1.0042 | 0.9750 / 0.9746 |
| era G / H                                          | 0.9757 / 0.9773 | 0.9722 / 0.9701 | 1.0019 / 1.0061 | 0.9765 / 0.9730 |
| **probe pass = bit 2 only (IsoMu24-type objects)** | **0.9742**      | **0.9625**      | **0.9968**      | **0.9595**      |
| probe pass = bit 8 only (IsoTkMu-type objects)     | 0.9487          | 0.9296          | 0.9593          | 0.9396          |

Findings:

1. The offset (+1.4% barrel, +0.8-1.0% elsewhere at 30-60 GeV) is a property of the data/MC ratio of the chosen pass definition, not of the fit, window,
   background, pileup weights, tag pT, or the event-level HLT requirement. The student's robustness claims for those are correct.
2. **It is not independent of the pass definition.** The student only varied OR-type definitions (skill, bit-only without HLT, event-level path-specific).
   Using only bit 2 (no OR with the IsoTkMu bit 8) moves the SF to within 0.1% of the POG at |eta| 0.9-1.2, 1.2-2.1, 2.1-2.4 (SF/POG at 30-60 GeV 0.998-1.003,
   weighted mean over all 30-60 GeV bins 1.0072; 1.0081 if additionally IsoMu24 must have fired), while the barrel stays +1.1-1.2% high. So the bit 8
   inclusion accounts for roughly 0.8-1.2% of the offset outside the barrel and about 0.2% in the barrel. This is a lead, not a proof: the tag definition in
   the skim cannot be changed offline (stored matching is OR), and I do not know which filters the POG probe definition uses. It should be run properly
   (tag and probe with bit 2 only) and reported; "not explained" is still the honest verdict.
3. **The object pT threshold scan is vacuous.** `explore_trigger.py` scans thresholds 24/26/27 only for probes with 40 < pT < 50 GeV, where the HLT object pT is
   near the offline pT, so no threshold up to 27 can matter. In the 26-30 GeV probe bin the threshold matters a lot (all-eta, data/MC efficiency 0.871/0.897 at >= 24,
   0.705/0.729 at >= 27). 3.2% of matched probes have a matched-object pT in [24, 27), so "the HLT objects are above 27 GeV"
   (`SKILLS_USED.md`) is false. README and `large_pull_notes.json` ("independent of ... object pT threshold") are supported only at 40-50 GeV.
4. Both-as-tags: with every ordered pair used and the tag required to be matched, a pass-pass pair gives two pass entries and a tag-matched/probe-unmatched pair one fail entry,
   so the entry efficiency is P(probe matched | tag matched) = epsilon for independent muons. I find no bias from the double counting (agreeing with the student); the
   tag-pT cuts of 35/40 GeV, which change which probes can also be tags, leave the SF unchanged to 0.0006.
5. MC trigger emulation / generator: the MC has the HLT bits and the same `fired` requirement; I cannot test generator effects (POWHEG Z, M 50-120, vs the POG's
   sample) or the F(late) admixture with these inputs. G and H SFs agree to 0.1-0.4%, so the run mix cannot give 1%. Remaining untested candidates: bit-8 handling (above),
   a probe-level path ambiguity (a probe matched to an object that passed the looser IsoMu22 filter but not the IsoMu24 filter in an event that fired because of the tag; the
   event-level `fired` test cannot see it), generator/mass-range differences, HLT/L1 modelling that the POG SF is meant to absorb. Do not claim any of these.

### 4. Unsupported numbers, paths and claims: TENSION

No fabricated numbers found: every number in the README table, `SKILLS_USED.md` and the filter-bit paragraph traced to `summary.json` or `explore_trigger.json`
(checked: 146 probes = 4.6e-5; 64%/23% IsoMu22/none; G/H 0.9783 vs 0.9747; tight-ID no bin > 3 sigma; tight iso 1 bin > 5, 9 bins > 3; IsoMu24 8 bins > 5, 21.6 sigma;
median systematics; MC-statistics ladder 1.011/1.0145/1.0077/1.0046). Grep for `/uscms`, `/home`, `/data/d`, `/tmp`, the username: nothing; `/store/user` only with `$USER`/`$ENV(USER)`/`<you>`.
Over-claims and defects:

- (4a) "independent of the trigger-match definition ... and object pT threshold" (README, `large_pull_notes.json`, `SKILLS_USED.md`): see section 3, items 2-3.
- (4b) "Filter-bit bias negligible (4.6e-5)": correct for the failure mode tested (probe matched while the event fired neither path, in Z events with a tag) and the skill's wording is indeed
  wrong about it, but the conclusion "the filter-bit problem is not the cause" does not cover the probe-level path ambiguity (3.5). Say "event-level bias negligible".
- (4c) `specification.md` promises a Clopper-Pearson replacement when the fail category is empty and a filter-bit "definition B"; neither is implemented (the code has S/A/C, no Clopper-Pearson).
  `SKILLS_USED.md` itself reports the 0.53 SF error in the tight-iso 120+ bin. Update the spec or implement it.
- (4d) `large_pull_notes.json`: eight IsoMu24 entries are the same paragraph copied; it states "not explained" and still satisfies `check_results.py`'s "no unexplained |pull| > 5".
  The check is satisfied by any non-empty string; make it require a note flagged as an accepted limitation, or report the count of unexplained bins as INFO.
- (4e) Plots: `pulls.png` has the CMS label overlapping the first panel title and a fixed x-range of about +-6 that silently drops the +21.6 IsoMu24 pull (the histogram shows no entry near 21);
  `sf_ratio_map_*` colour scale saturates at 0.97/1.03. Fix the range or add an overflow bin.
- Not checkable here: the Condor timing statements in `SKILLS_USED.md` (3-6 min per job, 7 700 idle jobs, 90 s test job).
- `check_results.py` exits 1 by design on the tight-iso RMS; CLAUDE.md says this script runs in CI. Decide explicitly (documented expected failure, or a tolerance with the reason),
  do not loosen the 2.0 requirement silently.

### 5. Skill statements contradicted (quote, correction)

1. SKILL.md Gotchas, "Filter bits are not paths": _"In a Run2016H file, 4% of events that fired **neither** `HLT_IsoMu24` nor `HLT_IsoTkMu24` still have a muon object with bit 2 and pT >= 24 GeV.
   A bit + pT match therefore overestimates the IsoMu24 efficiency, and the measured trigger SF differed from the POG by 1-3% (tested)."_
   Corrected: the 4% reproduces at event level (4.7% of unfired events in G+H data, 1.3% in MC), but it is the wrong denominator. Only 2.3% of events with such an object are unfired, and in Z
   events with a tag only 146 of 3.20 M matched probes (4.6e-5; MC 6.5e-5) sit in an unfired event. Dropping the `fired` requirement shifts eps_data by -0.0007 and the SF by +0.0007;
   a path-specific event match changes it by -0.0001 (max 0.0004). `tnp.py` already requires `fired`. The 1-3% excess over the POG is not from this effect: at 30-60 GeV the full-data IsoMu24 SF is
   +0.8-1.5% above the POG for all these definitions and is not understood (the bit-8 OR changes it by about 1% outside the barrel). Keep: bits are filter types, always add the pT threshold
   (it matters for probes below about 30 GeV, not above).
2. `tested-2016.md`, "Isolation and IsoMu24": _"Part of the trigger excess is the filter-bit problem below."_ and, in "The filter-bit check", _"A probe matched to such an object counts as passing, so the NanoAOD
   trigger efficiency is biased high."_ Both are not supported (item 1). Also _"presumably from IsoMu22 and similar filters ... not verified"_: verified for the 146 probes (64% of their events fired HLT_IsoMu22, 23% fired none of the nine listed paths).
3. SKILL.md Gotchas, "Run-period dependence": _"the IsoMu24 SF at |eta| 2.1-2.4 was 0.990 in two Run2016G files and 0.963 in two Run2016H files."_ Not reproduced with 3.55 fb^-1 (14 G + 17 H files):
   0.9783 +- 0.0031 (G) vs 0.9747 +- 0.0030 (H) at 40-50 GeV. The two-file errors were 0.007 and 0.009, so the original difference (0.0275 +- 0.0114) was a 2.4-sigma fluctuation. Corrected: the IsoMu24 SF changes
   by <SF_G - SF_H> = -0.0014 +- 0.0004 (chi2/ndf 40/27); tight iso -0.0002 +- 0.0003 (12/32); tight ID +0.0012 +- 0.0002 (64/32); G and H differ by at most 0.4% per bin. Keep the advice to state the runs used.
   Remove the 0.990/0.963 numbers (here and in the `tested-2016.md` table, where the same two-file values appear with +-0.007/0.009).
4. SKILL.md Gotchas, "Too little MC fakes a bias": _"Use at least as many MC events as data pairs."_ Cannot be met: `ZToMuMu_M-50To120_..._powheg` has 28 files = 2.96 M events (1.79 M pairs), and the 22% data subset already has 4.08 M pairs
   (MC/data 0.44; full G+H about 19 M). Quantified (tight ID, random MC subsets): mean SF/POG 1.011 / 1.0145 / 1.0077 / 1.0046 at MC/data pair ratios 0.009 / 0.044 / 0.22 / 0.44; mean stat-only pull 2.2 / 1.9 / 0.97 / 0.58.
   The skill must state the sample size and say to subsample the data to the MC or use `DYJetsToLL_M-50` (negative weights).
5. SKILL.md Canonical Pattern 2: _"One 2016 SingleMuon file (1.5 M events) gives about 94 000 pairs in 30 s and 1.3 GB."_ The 31 files used here average 2.27 M events (70.3 M in total); the student measured 2.5 GB for `tnp.py` on a 2.94 M-event file.
   State "1.3-3.4 M events per file".
6. SKILL.md Canonical Pattern 1: _"variations: nominal, systup, systdown, stat, syst (+ AltSig, massBin, massRange, tagIso)"_. `tagIso` exists for the ID, iso and GlobalMuons corrections but not for the IsoMu24 correction
   (evaluating it raises `Index not available in Category ... tagIso`); `stat`, `syst`, `AltSig`, `massBin`, `massRange`, `tagIso` return uncertainty values, not SFs, and `systup - nominal = hypot(stat, syst)`.
7. SKILL.md Canonical Pattern 2 / `tnp.py`: _"`tnp_pairs()` and `fit_pass_fail()` can be imported for that [full dataset]."_ `tnp_pairs()` returns WP-specific arrays without run, lumi or HLT flags, so no golden JSON, luminosity or era split is possible; `--max-events`
   is checked only after a 200 MB chunk. Document this, or ship the WP-agnostic skim the student wrote.
8. SKILL.md Gotchas, "Fits at eps -> 1": only mentions `FIT-NOT-OK`. The student found a status-OK fit with SF error 0.53 (tight iso, 2.1-2.4, pT > 120): add "check the error size, not only the status", with the Clopper-Pearson snippet.

Statements that were confirmed: bit meanings (1 TrkIsoVVL, 2 Iso, 4 OverlapFilter PFTau, 8 IsoTkMu, 1024 Mu50, read from the branch title of both a data and an MC file); the POG chain names and denominators; the
`evaluate(-1.5, 35.0)` values 0.9905/0.9944; the out-of-range error messages; the tag-pT-above-plateau advice (tag pT 35/40 GeV changes nothing); the isolation offset of 0.2-0.5% (confirmed by counting, section 2d); the tight-ID MC-statistics trend.

## 6. Required fixes before the PR, and follow-ups

Required (skill):

1. Rewrite the filter-bit gotcha and the matching paragraph in `tested-2016.md` as in section 5 items 1-2 (event-level 4% reproduces; probe-level bias 4.6e-5; trigger excess is not from this).
2. Remove the 0.990 vs 0.963 run-dependence claim (SKILL.md and `tested-2016.md`); replace with the G-H numbers above.
3. Replace "at least as many MC events as data pairs" by the achievable statement and the bias ladder; give the DY sample size.
4. Fix the file-size/time sentence, the `tagIso` variation list, and the `tnp_pairs()` "can be imported" sentence (items 5-7); extend the "Fits at eps -> 1" gotcha (item 8).
5. State in the skill that a NanoAOD IsoMu24 measurement on the full G+H sample lies 0.8-1.5% (weighted 1.2%) above the POG at 30-60 GeV, with the pass definition (bit 2 | bit 8 within dR < 0.1, pT >= 24) and that the cause is open.

Required (validation):

6. Correct the over-claims in 4a-4c; report weighted SF/POG in the README table instead of 1.0237; fix `specification.md` (Clopper-Pearson, definition B).
7. Fix `pulls.png` (title overlap, x-range or overflow) and the saturated ratio-map scale.
8. Decide the CI status of `check_results.py` (exit 1) and tighten the "unexplained |pull| > 5" check (4d).

Optional follow-ups:

9. Rerun the skim with separate tag-match columns (bit 2, bit 8) and report the IsoMu24 SF for bit-2-only and bit-8-only definitions for tag and probe; compare each with the POG. This is the single most informative next step for the open offset.
10. Repeat the object-pT threshold scan in the 26-30 and 30-40 GeV probe bins; store the probe-matched object pT (already in the skim, `m2pt`, `m8pt`).
11. Test the iso offset's MC-statistics origin (random-subset ladder for tight iso, and template/efficiency from independent MC halves); add `AltSig` and MC-template statistics as systematics and compare per-bin with the POG `AltSig`, `massRange`, `massBin`.
12. Compare with a second DY sample (`DYJetsToLL_M-50`) to bound generator effects; use the full data to see whether the offset shrinks with the MC statistics available.
13. Open Open Data records 14220 and 1059 and cite the verified identifiers; check that no lumi section straddles files.

## Overall

The validation is honest, reproducible bit-for-bit, and its POG chain, luminosity and pulls are correct. Its central physics outcomes (tight ID agrees, tight iso +0.2-0.4%, IsoMu24 +0.8-1.5% unexplained,
skill's filter-bit conclusion wrong, MC rule unattainable) are supported by independent recomputation. It is sound enough to accompany the skill once the skill statements in section 5 are corrected and the
over-claims about match-definition and threshold independence are removed or qualified. The IsoMu24 offset must be presented as an open issue, with the bit-2-only lead in section 3, not as an explained or definition-independent effect.
