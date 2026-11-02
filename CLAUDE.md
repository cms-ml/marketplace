# CMS Marketplace: maintenance guide

## Layout

```text
.claude-plugin/marketplace.json     # GENERATED plugin entries (top-level fields hand-edited)
plugins/<plugin>/
  .claude-plugin/plugin.json        # source of truth: name, description, version, keywords
  .mcp.json                         # optional MCP servers
  agents/<name>.md                  # optional subagents
  skills/<name>/SKILL.md            # skills
  skills/<name>/references/*.md     # deep content, loaded on demand
  skills/<name>/{assets,scripts}/   # optional templates / executable helpers
scripts/marketplace.py              # check | sync | bump
examples/<name>/PROMPT.md           # ready-to-paste example requests that exercise the skills
CREDITS.md                          # attribution for third-party teaching material
```

Plugins: `cms` (core: CMSSW, data tools, and the Scikit-HEP stack with CMS
examples, e.g. `awkward-array`), `af-fnal-lpc` (LPC facility: `lpc-condor`)
and `hep-python-tools` (experiment-neutral dev tooling: `standalone-script`,
`cli-creator`) exist. Planned: `cms-ml` (weaver training, ONNX/TF/SONIC
inference in CMSSW). Physics/data libraries with CMS examples go in `cms`, as
ATLAS does with its `atlas` plugin. Only create a plugin directory once
it has at least one skill, since `check` rejects empty plugins.

## Workflow

```bash
python3 scripts/marketplace.py check          # validate everything (also run by CI + pre-commit)
python3 scripts/marketplace.py sync           # regenerate marketplace.json + README block
python3 scripts/marketplace.py bump cms 0.2.0 # bump a plugin; `bump marketplace X` for metadata.version
```

CI also runs pre-commit (prettier, end-of-file, codespell) on **all** files.
On cmslpc, pre-commit's downloaded node.js fails (`libatomic.so.1` missing), so
run prettier with the LCG view's node before pushing:

```bash
(set +u; source /cvmfs/sft.cern.ch/lcg/views/LCG_109/x86_64-el9-gcc15-opt/setup.sh
 git ls-files '*.md' '*.json' '*.yaml' '*.yml' | xargs npx --yes prettier@3.5.3 --prose-wrap=preserve --write)
```

Never hand-edit the `plugins` array of `marketplace.json` or the README
section between `GENERATED` markers. Edit `plugin.json` / frontmatter and run
`sync`.

## Skill rules (enforced by `check`)

- Frontmatter: only `name` and `description` (spec also allows `license`,
  `compatibility`, `metadata`, `allowed-tools`). No invented keys.
- `name` == directory name; lowercase, digits, single hyphens, ≤ 64 chars;
  unique across all plugins.
- `description` ≤ 1024 chars and starts with **"Use when"**. List triggering
  situations only, never a summary of the skill's content.
- Must contain `## Gotchas`. `## Docs` must be the last `##` section.
- ≤ 300 lines is the target (warning above), 500 is a hard error. Move worked
  examples and long tables into `references/`.
- Every file in `references/`, `assets/` and `scripts/` must be linked from
  SKILL.md, and every relative link must resolve.
- For a README summary other than the first clause of the description, set
  `metadata:` → `summary: ...`.

## Writing skills

Recommended section order: Overview → When to Use → Key Concepts → Canonical
Patterns → Gotchas → Reference Files → Docs.

- **Test every command before it goes in.** Run it on cmslpc in a real release
  area (scratch dir), and record the release used in the reference file. If you
  could not run something, say so in the text or leave it out.
- **Don't hard-code a CMSSW release as the answer.** The user chooses the
  release. Versions in examples are "tested with" versions only (see the
  `cmssw` skill's "Choose the release" section).
- Prefer facts the user can re-derive (e.g. `dasgoclient -query="release
dataset=..."`, `/cvmfs/cms.cern.ch/releases.map`, the release notes at
  <https://cmssdt.cern.ch/SDT/ReleaseNotes/>) over hard-coded tables. When a
  table is unavoidable, date it.
- CMS units are **GeV** (MiniAOD, NanoAOD). Note it where kinematics appear.
- Gotchas should come from real failures: the error message plus the fix.
- Reference files start with a "Read this reference when…" sentence and a
  Contents list.
- `scripts/` are for agents to run, not read: non-interactive, `--help`,
  results on stdout (e.g. `KEY=VALUE`), diagnostics on stderr, documented exit
  codes, `--dry-run` for anything that writes. Example:
  `plugins/cms/skills/cmssw/scripts/setup-release.sh`.
- Imperative voice, tables for flags/options, copy-pasteable code.
- Cite upstream docs in `## Docs`. When adapting teaching material (e.g. CMS
  Open Data workshop lessons, CC-BY 4.0), rewrite and re-test it, and add a row
  to `CREDITS.md`.
- When adapting a skill from another marketplace (e.g. IRIS-HEP, BSD-3):
  add it to `plugins/<plugin>/VENDORED-LICENSES.md` with the upstream path and
  commit, original authors, what was kept, what changed (including upstream
  claims you corrected), and the license text verbatim. Also add a row to
  `CREDITS.md` and link the upstream skill in the skill's `## Docs`.

## Subagents

`plugins/<plugin>/agents/<name>.md` with frontmatter `name`, `description`
("Use when…"), `tools`, `model`, optional `color`, and optional `summary`
(README text). Claude Code subagent format, not the skill spec.

## Contribution standard: skill/agent + validation

Every PR that adds or substantially changes a skill or agent also adds a
validation under `validation/<name>/`: an analysis, or part of one, that
uses it on real inputs (Open Data where possible) and is run by an agent.
`validation/dijet-2016/` is the reference example and `validation/lpc-condor/`
a smaller one.

```text
validation/<name>/
  README.md          # goal, credits/references, differences from the reference analysis
  PROMPT.md          # the task given to the agent (headless command + Task section)
  specification.md   # written by the agent with analysis-spec-builder (analyses)
  <code>             # re-runnable; relative paths, no usernames
  plots/ summary.json hepdata/   # outputs (small files only; skims stay on EOS)
  SKILLS_USED.md     # which skill guided each step, what was wrong or missing
  check_results.py   # stdlib-only physics checks on summary.json; run in CI
```

- Run the agent on the task **before** the skill exists too, if you can:
  its `SKILLS_USED.md` notes are the best seed for the new skill. Then rerun
  the relevant steps following the new skill and record what changed.
- Commit outputs, not inputs: no ROOT files or skims. State where they are
  (`/store/user/$USER/...`) and how to rebuild them.
- `check_results.py` tests physics sense (efficiencies in [0, 1], fit
  quality, closure), not exact numbers. Exit 0/1/2, `SUMMARY=n/n` on stdout.
- Fill in `.github/pull_request_template.md`. The contributor-facing
  walkthrough is [CONTRIBUTING.md](CONTRIBUTING.md).

## Commits and PRs

Conventional Commits: `feat(cms): add cmssw skill`, `fix(cms): ...`,
`docs: ...`, `chore: ...`. Work on a feature branch in your fork and open a PR
to `cms-ml/marketplace` `master`.
