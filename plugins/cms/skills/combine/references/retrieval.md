# Answering Combine questions

Read this reference when routing a question across the `combine` sources,
choosing a `fetch_doc` mode, formatting citations, or when the corpus seems
not to cover the question.

## Contents

1. [Pick the right source](#pick-the-right-source)
2. [Search and read the scores](#search-and-read-the-scores)
3. [Fetch with the right mode](#fetch-with-the-right-mode)
4. [Combine sources when it helps](#combine-sources-when-it-helps)
5. [Output format](#output-format)
6. [When the corpus doesn't have it](#when-the-corpus-doesnt-have-it)
7. [Worked example](#worked-example)

## Pick the right source

- **"How do I X?"** / **"What does option `--Y` do?"** → `combine-docs`.
- **"Why does X work this way?"** / **"What is the formal definition of Y?"** →
  `combine-paper`.
- **"I'm getting this error"** / **"I see this warning"** → `combine-forum`; if
  it comes up empty, `combine-hypernews` (the archived pre-2022 forum; treat
  version-sensitive answers with care).
- **"What does the implementation actually do?"** / **"Is feature Z really
  there?"** → `combine-code`.

The sources are complementary, not redundant. If the first one comes up empty,
fall through to the next most likely.

## Search and read the scores

`search_docs(query, source)` returns up to 10 BM25-ranked hits with a title,
URL, path, score and snippet. Interpret the scores:

- **Top score high (>15) with a clear gap to the runner-up**: the top hit is
  almost certainly right. Fetch it.
- **Top hits within ~3 points of each other**: all are relevant. Skim 2–3
  snippets and pick the best one before fetching.
- **All scores low (<8)**: the search probably missed. Reformulate with
  synonyms, the exact option name, or the verbatim error message.
- **Two reformulations both miss**: the corpus may not cover the question. See
  [When the corpus doesn't have it](#when-the-corpus-doesnt-have-it).

## Fetch with the right mode

`fetch_doc(url_or_path, source, mode)` returns plain text: a `key: value`
header (source, path, URL, mode), a blank line, then the body.

| `mode`               | Use for                                                                                                                                               |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- |
| `markdown` (default) | Paper sections, short forum threads, short code files. Full body                                                                                      |
| `outline`            | Scout first on long docs pages, long forum threads and unfamiliar code files. Headings (docs/paper), defs and classes (code), a per-post list (forum) |
| `sections:<heading>` | One named section of a docs page or paper section. Case-insensitive                                                                                   |
| `post:<N>`           | Forum only. One post's body, with a per-post URL                                                                                                      |
| `post:accepted`      | Forum only. The accepted answer: cheap and high-signal for solved threads. Errors if the thread is unsolved, so use `outline` first if unsure         |

Default to the cheaper projection (`outline`, `sections:…`, `post:accepted`)
when you can, and use `markdown` when you need the full body.

## Combine sources when it helps

Some questions are best answered from two sources:

- **"Why does X work this way and how do I use it?"**: paper for the why, docs
  for the how.
- **"I'm getting this error from HybridNew"**: forum for the diagnosis, docs
  for HybridNew context.
- **"What does `--robustHesse` do under the hood?"**: docs for the description,
  code for the implementation.

Don't query every source routinely. Default to one source per question. Query
two up front only when the question genuinely spans both (how and why, or
reproduce the error and explain the cause). Add a third only when the first two
leave a real gap.

## Output format

- Start with the **direct answer** in 1–3 sentences.
- Cite the URLs the tools returned, **verbatim**, as inline Markdown links.
  Combine users click through to verify.
- For forum citations, use the per-post URL when you fetched a specific post
  (`post:N` or `post:accepted`), the topic URL otherwise.
- If several sources contributed, cite all of them.
- Use code blocks for code and command lines only, not for prose.

## When the corpus doesn't have it

Combine is a domain where a wrong answer can lead to a wrong physics result.
Be conservative:

- After two failed reformulations, **say so explicitly**: "I couldn't find
  this in the Combine docs, paper, code or forum."
- Suggest posting on
  [cms-talk](https://cms-talk.web.cern.ch/c/physics/cat/cat-stats/279).
- Don't answer from prior knowledge without flagging it. If you add context
  beyond what the corpus returned (comparing a fetched method to a related
  one, or a well-known consequence), say so: "not covered in the fetched
  section, but…" or "this is well known but not in the corpus".
- Never paraphrase a forum reply as if it were the canonical documentation.
  Cite the thread and let the user judge.

## Worked example

> _User:_ "I'm running AsymptoticLimits and getting 'cannot compute the
> expected limit'. What's wrong?"

This is an error message, so start with the forum.

1. `search_docs(query="cannot compute expected limit AsymptoticLimits", source="combine-forum")`
   and look at the top hits.
2. For a solved thread:
   `fetch_doc(url_or_path="<topic_id>", source="combine-forum", mode="post:accepted")`.
3. For an unsolved thread:
   `fetch_doc(url_or_path="<topic_id>", source="combine-forum", mode="outline")`,
   then fetch the most relevant reply with `post:<N>`.
4. Optional context: `search_docs(query="AsymptoticLimits", source="combine-docs")`,
   then fetch the section that explains the expected-limit calculation.
5. Answer: the cause (cite the cms-talk URL), the fix (cite the post URL), and
   the docs page as the canonical reference.
