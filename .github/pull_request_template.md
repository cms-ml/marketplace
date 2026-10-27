<!-- How to make a PR here, with recipes for a skill, an agent or a plugin: CONTRIBUTING.md -->

## What this adds

<!-- One line per skill or agent: name, plugin, what it is for. -->

- `plugin/skill-or-agent`: ...

## Validation

<!-- Every skill or agent PR comes with a validation in validation/<name>/:
     an analysis (or part of one) that uses it, run by an agent, with its outputs committed. -->

- Directory: `validation/<name>/`
- Task given to the agent: `validation/<name>/PROMPT.md`
- Results: plots / `summary.json` / `RESULTS.md`, and `SKILLS_USED.md` (what worked, what was missing)
- Physics checks: `python3 validation/<name>/check_results.py` → `SUMMARY=n/n`
- Where it ran: cmslpc / lxplus / other, with the environment (LCG view, CMSSW release, uv)

## Checklist

- [ ] `python3 scripts/marketplace.py check` passes (`sync` run if README/marketplace.json changed)
- [ ] Prettier run (see CLAUDE.md for the cmslpc command); pre-commit passes in CI
- [ ] Every command in the skill was run, with "tested with" versions stated; untested parts say so
- [ ] Gotchas come from real failures (error message + fix)
- [ ] Sources cited in `## Docs`; adapted material credited in `CREDITS.md` / `VENDORED-LICENSES.md`
- [ ] No personal paths, usernames or CMS-internal content in committed files
- [ ] Open Data results labelled "CMS Open Data" / "Private work", never "CMS Preliminary"
- [ ] Large outputs (skims, ROOT files) not committed; the README says where they live and how to rebuild them
