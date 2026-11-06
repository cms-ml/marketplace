# Task for the agent: generic working points, MC-statistics uncertainty and correctionlib output in `tnp.py`

This validates the extension of the `muon-tag-and-probe` skill (`scripts/tnp.py`)
from three hard-coded working points to any NanoAOD muon selection, with an
MC-statistics uncertainty, an offline mode and correctionlib output. The
motivation is a calibration benchmark in which an agent measures muon ID and
trigger scale factors for many working points on simulated samples, offline,
delivers correctionlib JSON, and is scored by pulls against hidden truth (so
the uncertainties must cover).

## How to run

From the repository root on cmslpc, on branch `feat/tnp-correctionlib-generic`:

```bash
sed -n '/^## Task/,$p' validation/muon-tnp-generic/PROMPT.md | \
  claude -p --plugin-dir plugins/cms --plugin-dir plugins/af-fnal-lpc \
    --permission-mode acceptEdits --allowedTools "Bash Read Write Edit Glob Grep Skill TodoWrite" \
    > validation/muon-tnp-generic/agent_report.md 2>&1
```

## Task

Extend `plugins/cms/skills/muon-tag-and-probe/scripts/tnp.py` (keep it one
runnable script; keep the existing presets and their exact results) and
validate the change in `validation/muon-tnp-generic/`. Read `CLAUDE.md` and
`validation/muon-tnp/` (README.md, REVIEW.md) first.

1. **Generic interface.** `--num EXPR` / `--den EXPR` as boolean expressions
   over muon fields (`tightId`, `mediumId`, `looseId`, `softId`,
   `highPtId==2`, `mvaId>=2`, `pfRelIso04_all<0.15`, `tkRelIso<0.1`,
   `abs(dxy)<0.2`, combinations with `&`, `|`, `~`), parsed safely (no bare
   `eval`). Trigger numerator `--num-trigger BITS:PTMIN` (ΔR < 0.1); tag
   options `--tag-trigger`, `--tag-pt`, `--tag-hlt`. `--wp` presets map onto
   these bit for bit. `--pt-edges` / `--eta-edges`, optional `--pog NAME`.
2. **Offline mode.** Without the POG or LUM JSON (or with `--no-pog`,
   `--no-pu`) still run, warn and record it.
3. **MC-statistics uncertainty** (MC efficiency and the MC templates of the
   data fit), e.g. Poisson bootstrap of the MC, as component `mc_stat`, kept
   separate from the data `stat`; optional `--syst` (background shape, mass
   window, tag).
4. **correctionlib output** (`--correctionlib FILE`, `--name`): schema v2,
   inputs |η|, pT, `scale_factors` (`nominal`, `up`, `down`, `stat`,
   `mc_stat`, `syst`), clamped MultiBinning; efficiencies as extra
   corrections. It must load and pass `correction validate`.

Update SKILL.md (generic interface, table of expressions and trigger bits,
offline mode, uncertainty components, correctionlib pattern, gotchas from
real failures; under 300 lines) and `references/tested-2016.md`.

Validation (2016G/H SingleMuon Open Data + ZToMuMu powheg MC, a modest
subset, outputs outside the repository):

- a. presets and the same definitions spelled with the new options give
  identical per-bin results, also identical to the pre-change `tnp.py`;
- b. new working points against the POG (at least medium and loose ID and one
  more), SF/POG and pulls; one trigger without a POG counterpart in offline
  mode with explicit edges;
- c. correctionlib: loads, nominal equals the JSON SF in every bin, up/down
  consistent, clamping, an end-to-end weighting example;
- d. MC-statistics coverage: two independent halves of the MC,
  (SF_1 − SF_2)/sqrt(σ_mc_stat,1² + σ_mc_stat,2²) has RMS ≈ 1, and mc_stat
  scales as 1/sqrt(N_MC); report honestly if it does not;
- e. offline mode with the JSONs disabled and with an unreachable path;
- f. `--syst` components per bin.

Deliverables: README.md, this PROMPT.md, `code/run_all.sh`, summary.json,
plots/, SKILLS_USED.md, stdlib-only `check_results.py` (exit 0/1/2,
`SUMMARY=n/n`). No commits, no personal paths, never fabricate numbers.
