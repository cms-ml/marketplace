---
name: combine
description: >-
  Use when working with CMS Combine (HiggsAnalysis-CombinedLimit): writing or
  debugging a datacard or physics model, choosing or running a Combine method
  (AsymptoticLimits, FitDiagnostics, MultiDimFit, HybridNew, Significance,
  GoodnessOfFit, ChannelCompatibilityCheck, Impacts), interpreting Combine
  output, explaining a Combine error message or warning, asking how or why
  Combine does something, or running a Combine command (combine,
  text2workspace.py, combineCards.py, combineTool.py) to reproduce, diagnose
  or confirm a result.
metadata:
  summary: Answer Combine questions from docs, paper, code and forum; run and debug Combine
---

# Combine

## Overview

[Combine](https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/latest)
is the CMS statistical-analysis tool: datacards, physics models, limits, fits,
significances and goodness-of-fit. This skill does two things:

- **Answer questions** with citations, through the `combine` MCP server:
  read-only retrieval over the official docs, the Combine paper, the source
  code and the CMS forums (`search_docs`, `fetch_doc`).
- **Run Combine**: in the shell when `combine` is on the user's `PATH`,
  otherwise through the `combine-run-remote` MCP server (`run_combine`), a
  CERN service that runs one command in a throwaway workspace.

Most requests need retrieval only. Run something when the user reports a
command that misbehaves, asks you to run or try something, or when
reproducing a result would confirm a diagnosis.

## When to Use

- A question about a Combine method, option, datacard directive or physics
  model ("how do I…", "what does `--X` do", "why does Combine…")
- A Combine error message, warning or unexpected result
- Running or reproducing a `combine`, `text2workspace.py`, `combineCards.py`
  or `combineTool.py` command
- Interpreting Combine output: limits, fit results, impacts, scans

## Key Concepts

### Tool names

This skill uses short tool names. The tools you can call carry the plugin
prefix:

| This skill says | Call it as                                        |
| --------------- | ------------------------------------------------- |
| `search_docs`   | `mcp__plugin_cms_combine__search_docs`            |
| `fetch_doc`     | `mcp__plugin_cms_combine__fetch_doc`              |
| `run_combine`   | `mcp__plugin_cms_combine-run-remote__run_combine` |

If the names in your tool list differ, use those, copied character for
character (the prefixes mix `_` and `-`).

### Sources (`source` argument of `search_docs` / `fetch_doc`)

| Source ID           | Covers                                                                                                |
| ------------------- | ----------------------------------------------------------------------------------------------------- |
| `combine-docs`      | Official docs (MkDocs): how-to, CLI options, tutorials, reference                                     |
| `combine-paper`     | The Combine paper, arXiv:2404.06614v2: methodology, definitions, the "why"                            |
| `combine-code`      | The source tree at a pinned release: what the implementation actually does                            |
| `combine-forum`     | cms-talk Statistics category (2022 onward): errors, workarounds, real-world edge cases                |
| `combine-hypernews` | Archived HyperNews (pre-2022): same kind of Q&A, older; lower priority, may describe outdated options |

### How to behave

These rules come from the combine-assistant persona
([`config/AGENTS.md`](https://github.com/maxgalli/combine-assistant/blob/master/config/AGENTS.md)):

- **Ground answers in the corpus, not priors.** A confident but wrong answer
  can produce wrong physics. Cite the URLs the tools return. If you add
  anything beyond what a tool returned, say so.
- **Reproduce before diagnosing when you can.** If a reported command errors
  or gives an unexpected result and execution is available, run it, then
  cross-check the output against the `combine` sources.
- **Prefer local execution; fall back to remote.** Never fabricate execution
  results. If neither path is available, say so and explain from the corpus.
- **Be precise with commands.** Quote options verbatim and explain what each
  does when it matters.

## Canonical Patterns

### Answer a question

1. **Pick the source** from the question type:

   | Question                                     | Start with                                           |
   | -------------------------------------------- | ---------------------------------------------------- |
   | "How do I X?", "What does `--Y` do?"         | `combine-docs`                                       |
   | "Why does X work this way?", a definition    | `combine-paper`                                      |
   | "I get this error / warning"                 | `combine-forum`, then `combine-hypernews` if nothing |
   | "What does the code do?", "Is Z implemented" | `combine-code`                                       |

   If the first source comes up empty, fall through to the next most likely.
   Query two sources up front only when the question spans both (how and why,
   error and cause).

2. **Search and read the scores.** `search_docs(query, source)` returns up to
   10 BM25 hits. A top score above ~15 with a clear gap: fetch it. Scores
   within ~3 points: skim 2–3 snippets first. All below ~8: reformulate with
   synonyms, the exact option name or the verbatim error text.
3. **Fetch the cheapest view that answers** with
   `fetch_doc(url_or_path, source, mode)`: `outline` to scout a long page or
   thread, `sections:<heading>` for one section, `post:accepted` or
   `post:<N>` for one forum post, `markdown` (default) for the full body.
4. **Answer**: the direct answer in 1–3 sentences, then inline links to the
   URLs the tools returned, verbatim (the per-post URL for a fetched post).

After two failed reformulations, say the corpus doesn't cover it and suggest
posting on [cms-talk](https://cms-talk.web.cern.ch/c/physics/cat/cat-stats/279).
Never present a forum reply as if it were the canonical documentation.

The full procedure, the `mode` table and a worked example are in
[references/retrieval.md](references/retrieval.md).

### Decide whether to run

- **Explain without running** when the cause is visible in the command itself
  (an option outside its allowed range, inconsistent options, a typo, a wrong
  file or mode). Cross-check the rule in the sources; running is then optional
  confirmation.
- **Run** when the cause is not apparent, when the user asks you to run or try
  something, or to confirm a fix.
- **Don't run** batch submission (`combineTool.py --job-mode condor`, crab):
  explain instead. Don't run when no execution path is available, or when the
  inputs are large and only `combine-run-remote` is available.

### Choose how to execute: check `command -v combine` first, every time

- **It prints a path** → run in the **shell** (the Bash tool), in the user's
  working directory, against their real files. Do **not** call `run_combine`
  in that session, even though it is in your tool list.
- **It prints nothing** → use `run_combine`.

Run one Combine command per call: no pipes, redirects or `&&` chains.

```bash
command -v combine        # decides the path
combine -M AsymptoticLimits -d datacard.txt -m 125
```

In the shell, read the exit code, stdout and stderr; outputs such as
`higgsCombine*.root` stay in the working directory.

### Run through `combine-run-remote`

The workspace is remote and empty: only the files you pass exist there.

1. Read the datacard the user points to yourself; don't ask them to paste it.
2. Find its `shapes` lines and read every ROOT file they name, as base64
   (`base64 -i shapes.root`).
3. Call `run_combine` with `command` (one command line), `files` (text inputs
   as `{name: content}`), `files_b64` (binary inputs as `{name: base64}`) and,
   if needed, `timeout_s`. Refer to files by **base name**: the workspace is
   flat.
4. Read the result: `error` set means a setup failure, not a physics result;
   a non-zero `returncode` means Combine failed (read `stderr`); `returncode`
   0 means success (report `stdout` and `artifacts`).

### Reproduce → diagnose → fix

1. **Reproduce** the user's command (shell or `run_combine`).
2. **Read the outcome**: setup error, non-zero exit, or success.
3. **Diagnose**: search the key `stderr` line in `combine-forum`; check
   `combine-code` or `combine-docs` for what the failing option requires.
4. **Fix**: propose a corrected command and explain what changed.
5. **Confirm**: re-run it and report the result, with citations.

Details, the result fields and a worked example are in
[references/execution.md](references/execution.md).

## Gotchas

- **The MCP servers answer only from the CERN network.** Off-site, every
  `search_docs`, `fetch_doc` and `run_combine` call fails to connect (the
  server shows as failed in `/mcp`). Connect to the CERN VPN or work from
  lxplus, then reconnect the servers from `/mcp`. Without them, answer only
  with clearly flagged prior knowledge, or run Combine locally.
- **Short tool names are not callable.** Calling `search_docs` instead of the
  prefixed name fails as an unknown tool. Use the name from your tool list.
- **`run_combine` while Combine is on `PATH` fails with "file not found".**
  The remote workspace can't see the user's files, so a relative path such as
  `data/tutorials/counting/realistic-counting-experiment.txt` doesn't exist
  there. Check `command -v combine` and use the shell.
- **`run_combine` returns `error` "not found on PATH".** The server has no
  Combine environment at that moment. Tell the user; don't guess numbers.
- **Large inputs are rejected by `combine-run-remote`.** Datacards plus shape
  files beyond a few MB exceed its caps. Only a local Combine handles them;
  otherwise explain rather than run.
- **A misspelled `fetch_doc` mode returns the whole page.** For example
  `section:Rate parameters` (missing `s`) silently gives `markdown`. Write
  `sections:<heading>` exactly; if the reply's `mode:` line says `markdown`,
  the mode was not recognised.
- **`post:accepted` errors on an unsolved thread.** Fetch the thread with
  `outline` first and pick a `post:<N>`.
- **HyperNews answers can be outdated.** Threads predate 2022 and may describe
  removed options. Cross-check version-sensitive answers in `combine-docs` or
  `combine-code`.
- **`combineTool.py` can submit batch jobs.** Never submit condor or crab jobs
  on the user's behalf.

## Reference Files

- [retrieval.md](references/retrieval.md): read when routing a question
  across sources, choosing a `fetch_doc` mode, formatting citations, or when
  the corpus seems not to cover the question.
- [execution.md](references/execution.md): read before running a command
  through `combine-run-remote`, when interpreting its JSON result, or when
  working through a failing command.

## Docs

- Combine documentation: <https://cms-analysis.github.io/HiggsAnalysis-CombinedLimit/latest>
- Combine source: <https://github.com/cms-analysis/HiggsAnalysis-CombinedLimit>
- The Combine paper: <https://arxiv.org/abs/2404.06614>
- cms-talk Statistics category: <https://cms-talk.web.cern.ch/c/physics/cat/cat-stats/279>
- Upstream of this skill (combine-assistant): <https://github.com/maxgalli/combine-assistant>
- Retrieval server (combine-mcp): <https://github.com/maxgalli/combine-mcp>
- Execution server (combine-run-mcp): <https://github.com/maxgalli/combine-run-mcp>
