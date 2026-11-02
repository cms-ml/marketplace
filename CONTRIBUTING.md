# Contributing to the CMS marketplace

New skills, agents and plugins are welcome. This guide explains the pieces,
helps you choose which one to write, and walks through a PR step by step.
[CLAUDE.md](CLAUDE.md) has the authoring rules that `scripts/marketplace.py
check` enforces.

**The rule for every PR:** a new or changed skill or agent comes with a
**validation**: an analysis, or part of one, that uses it on real inputs,
run by an agent, with its outputs committed under `validation/<name>/`.
The reference example is the PR that added `cms-analysis-coder`,
`trigger-efficiency` and `hepdata`, validated by
[validation/dijet-2016](validation/dijet-2016) (a b-tagged dijet search on
2016 Open Data). A smaller one is [validation/lpc-condor](validation/lpc-condor).

Contents:

1. How the pieces fit
2. Which feature do I use?
3. Making a PR, step by step
4. Recipe: a skill
5. Recipe: an agent
6. Recipe: a new plugin
7. The validation
8. Before you open the PR
9. Learn more

## 1. How the pieces fit

```text
marketplace (a git repo: cms-ml/marketplace)
|-- .claude-plugin/marketplace.json      <- catalogue: lists the plugins (generated)
|-- plugins/
|   `-- cms/                             <- a PLUGIN = one installable unit
|       |-- .claude-plugin/plugin.json   <- plugin manifest (name, version, ...)
|       |-- skills/<name>/SKILL.md       <- SKILLS: knowledge/workflows, loaded on demand
|       |-- agents/<name>.md             <- SUBAGENTS: isolated workers with their own context
|       |-- hooks/hooks.json             <- HOOKS: scripts that run on events
|       `-- .mcp.json                    <- MCP servers: connections to external services
`-- validation/<name>/                   <- evidence that a skill/agent works (one per PR)
```

Read it bottom-up: you write skills and subagents, package them into a
plugin, and publish plugins through a marketplace. Plugins here: `cms`
(physics and data tools: CMSSW, the Scikit-HEP stack, analysis workflows),
`af-fnal-lpc` (the LPC facility), `hep-python-tools` (experiment-neutral
Python tooling).

## 2. Which feature do I use?

| Feature     | What it is                                                    | Loads                                                    | Use it for                                                                          |
| ----------- | ------------------------------------------------------------- | -------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| CLAUDE.md   | Persistent instructions                                       | Every session, in full                                   | "Always do X" rules, build commands. Keep under ~200 lines.                         |
| Skill       | Reusable instructions/knowledge (`SKILL.md` + optional files) | Description at start; full body only when used           | Reference material (e.g. hist + mplhep for CMS) and repeatable workflows.           |
| Subagent    | Isolated worker with its own context window and system prompt | When spawned; only a summary returns                     | Tasks that read many files, parallel work, a specialist role (e.g. a stats expert). |
| Hook        | Script, HTTP call or prompt triggered by an event             | On its trigger; no context cost unless it returns output | Things that must happen every time (e.g. lint after every edit).                    |
| MCP server  | Connection to an external service                             | Tool names at start; schemas on demand                   | External data/actions (ATLAS uses one for Rucio/AMI/HTCondor).                      |
| Plugin      | Package of the above                                          | Wherever enabled                                         | Sharing a setup across repositories or people. Skills get namespaced: `cms:hist`.   |
| Marketplace | Catalogue of plugins in a git repo                            | Added once by the user                                   | Distribution. This is what `cms-ml/marketplace` is.                                 |

When to add what (from the Claude Code docs' "build your setup over time"):

- You paste the same playbook into chat for the third time: write a **skill**.
- A side task floods the conversation with output you won't reference again,
  or needs a specialist persona: write a **subagent**.
- You want something to happen every time without asking: write a **hook**.
- You keep copying data from a system Claude can't see: connect an **MCP
  server**.
- A different audience (a facility, an ML workflow) needs its own set: create
  a **plugin**.

Most contributions are a skill in an existing plugin.

## 3. Making a PR, step by step

```bash
# 1. Branch (or fork cms-ml/marketplace and branch in your fork)
git clone https://github.com/cms-ml/marketplace && cd marketplace
git switch -c feat/<name>

# 2. Write the skill/agent (sections 4-6), test every command on cmslpc or lxplus

# 3. Try it locally before publishing
claude --plugin-dir plugins/cms        # starts Claude Code with your working copy of the plugin

# 4. Validate it with an agent (section 7): validation/<name>/

# 5. Check, regenerate, bump, format (section 8)
python3 scripts/marketplace.py check
python3 scripts/marketplace.py sync
python3 scripts/marketplace.py bump cms 0.3.0

# 6. One commit per skill/agent, then the validation, then docs (Conventional Commits)
git commit -m "feat(cms): add <name> skill"
git commit -m "test(cms): add <name> validation"
git push -u origin feat/<name>
gh pr create --repo cms-ml/marketplace --base master   # the PR template opens with a checklist
```

## 4. Recipe: a skill

```text
plugins/<plugin>/skills/<name>/
  SKILL.md              # required; <= 300 lines target, 500 hard limit
  references/*.md       # deep content, loaded only when needed
  scripts/*             # tools the agent runs (--help, exit codes, KEY=VALUE stdout)
  assets/*              # templates the agent copies
```

1. **Frontmatter**: only `name` (= directory name, lowercase-hyphens) and
   `description`, plus optionally `metadata: summary:` for the README.
   The description starts with **"Use when"** and lists the situations
   and error messages that should trigger the skill. It does not summarise
   the content. Claude picks skills by this text alone.
2. **Sections** in this order: Overview, When to Use, Key Concepts,
   Canonical Patterns, **Gotchas**, Reference Files, **Docs** (last).
3. **Test every command** before it goes in, and say what you tested it with
   (release, LCG view, versions). Gotchas come from real failures: the error
   message plus the fix.
4. Link every file in `references/`, `scripts/` and `assets/` from
   `SKILL.md`. `check` fails on orphans.
5. Cite upstream docs in `## Docs`. Credit adapted material in `CREDITS.md`,
   and in `VENDORED-LICENSES.md` when copying from another marketplace.

Examples: `plugins/cms/skills/trigger-efficiency` (scripts plus a worked
example) and `plugins/cms/skills/hepdata` (a template with a `--demo` that
tests itself).

## 5. Recipe: an agent

```markdown
---
name: cms-analysis-coder
description: >-
  Use when a CMS physics analysis ... needs to be implemented end to end ...
summary: Senior CMS PhD student that implements an analysis spec with the marketplace skills
tools: Read, Write, Edit, Bash, Glob, Grep, Skill, TodoWrite
model: sonnet
color: blue
---

You are a senior PhD student on CMS. ... (the system prompt)
```

- The `description` says when Claude should hand work to this agent.
- `tools` lists only what the agent needs. Include `Skill` so it can load the
  marketplace skills.
- The prompt is a role, then how it works (start from a spec, use the
  skills, start small, validate as it goes), then what it never does
  (fabricate numbers, call Open Data "CMS Preliminary"), then what it hands
  back.
- Example: [plugins/cms/agents/cms-analysis-coder.md](plugins/cms/agents/cms-analysis-coder.md).

## 6. Recipe: a new plugin

Create a plugin only for a distinct audience. For example, `af-fnal-lpc` is
only useful on the LPC, and the planned `cms-ml` covers weaver, ONNX and
SONIC. Otherwise add to `cms`.

```json
{
  "name": "af-fnal-lpc",
  "description": "Skills for the CMS LPC analysis facility at Fermilab ...",
  "version": "0.1.0",
  "homepage": "https://uscms.org/uscms_at_work/computing/setup/batch_systems.shtml",
  "repository": "https://github.com/cms-ml/marketplace",
  "license": "MIT",
  "keywords": ["CMS", "LPC", "HTCondor"]
}
```

Put it in `plugins/<name>/.claude-plugin/plugin.json`, add at least one skill
(`check` rejects empty plugins), run `sync` to register it in
`marketplace.json` and the README, and add an install line to the README.

## 7. The validation

```text
validation/<name>/
  README.md          # goal, credits/references, differences from any reference analysis, results
  PROMPT.md          # the exact task given to the agent (headless command + Task section)
  specification.md   # for analyses: written by the agent with analysis-spec-builder
  <code>             # re-runnable, relative paths, no usernames
  plots/ summary.json hepdata/   # outputs (small files; skims stay on EOS)
  SKILLS_USED.md     # which skill guided each step, where it was wrong or missing
  check_results.py   # stdlib-only physics checks on the outputs; CI runs it
```

1. Write `PROMPT.md`: data, deliverables, limits (files, jobs, memory).
   Use the template below.
2. Run it with an agent. In a chat, say "Use the cms-analysis-coder agent
   to …". For long runs, use the headless `tmux` command in the README
   ([Running the agent on a long task](README.md#running-the-agent-on-a-long-task)),
   adding `--plugin-dir plugins/<plugin>` so it uses your working copy.
3. Read its `SKILLS_USED.md` and fix the skill. If you can, run the agent
   once **before** writing the skill: what it had to work out alone is
   exactly what the skill should say.
4. Rerun the relevant steps following the finished skill (second template),
   and record that the results agree.
5. Write `check_results.py`: physics sense (efficiencies in [0, 1], fit
   quality, closure, no NaN), not exact numbers. Exit 0/1/2, `SUMMARY=n/n`.

### Template: `PROMPT.md`

```markdown
# Task for the <agent> agent

Run it headless from the repository root: see README, "Running the agent on a long task".

## Task

<One paragraph: what to reproduce or build, and which reference it follows (cite it).>
Work in `validation/<name>/`. First write `specification.md` with the
analysis-spec-builder skill, then implement it.

**Inputs:** <exact Open Data / DAS / EOS paths, number of files; say "develop on 2-3 files">
**Selection / method:** <what is fixed, and what the agent must decide and justify>
**Outputs:** <plots (CMS style, PNG + PDF, in plots/), summary.json keys, other deliverables>
**Limits:** <max condor jobs, EOS output area /store/user/$USER/..., memory, no commits>
**Report:** `SKILLS_USED.md`: which skill guided each step, and where a skill was wrong,
unclear or missing (quote it). No personal paths in any file.
```

### Template: validating a new skill on an existing analysis

> You are validating the NEW skill `<plugin>/skills/<name>`. If it is not
> installed, read it as files: `plugins/<plugin>/skills/<name>/SKILL.md` and
> everything it links. The analysis is `validation/<name>/`; its inputs are
> in `<where>` (do not regenerate them). Redo `<steps>` by following the
> skill, rerun, and compare the new `summary.json` with the old one: every
> number must agree, or explain why it doesn't. Append "## Validation of the
> `<name>` skill" to `SKILLS_USED.md`: what worked as written, and every place
> the skill was wrong, unclear or missing something (quote the line). Do not
> edit the skill. No commits, no personal paths.

This is the prompt that validated `trigger-efficiency` and `hepdata`. It
found a real bug in `list_hlt_paths.py` and 19 documentation gaps.

## 8. Before you open the PR

- [ ] `python3 scripts/marketplace.py check` passes. Run `sync` after any
      frontmatter or `plugin.json` change.
- [ ] Plugin version bumped (`bump <plugin> X.Y.Z`). Installed copies only
      update on a new version.
- [ ] Prettier and pre-commit pass. On cmslpc, use the LCG node command in
      [CLAUDE.md](CLAUDE.md).
- [ ] No personal paths or usernames (write `$USER`, `<user>`), and no
      CMS-internal content. Link internal twikis; don't copy them.
- [ ] Open Data results are labelled "CMS Open Data" or "Private work".
- [ ] Large inputs are not committed. The validation README says where they
      live and how to rebuild them.

## 9. Learn more

- **Features overview:** <https://code.claude.com/docs/en/features-overview>
- **Skills:** <https://code.claude.com/docs/en/skills>
- **Subagents:** <https://code.claude.com/docs/en/sub-agents>
- **Plugins:** <https://code.claude.com/docs/en/plugins>
- **Plugin reference:** <https://code.claude.com/docs/en/plugins-reference>
- **Marketplaces:** <https://code.claude.com/docs/en/plugin-marketplaces>
- **Plugin evals:** <https://code.claude.com/docs/en/plugin-evals>
- **Debug your config:** <https://code.claude.com/docs/en/debug-your-config>
- **Agent Skills spec:** <https://agentskills.io/specification>
- **Skill best practices:** <https://agentskills.io/skill-creation/best-practices>
- **Evaluating skills:** <https://agentskills.io/skill-creation/evaluating-skills>
- **Anthropic skills:** <https://github.com/anthropics/skills>
- **Official plugins:** <https://github.com/anthropics/claude-plugins-official>
