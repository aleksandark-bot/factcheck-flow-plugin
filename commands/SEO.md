---
description: Optimize ONE WordPress article — GSC + DataForSEO keyword research, keyword selection (auto for new articles, browser picker for refreshes), on-page optimization, then hand off to /fact.
argument-hint: "<url-or-id>   (one article)"
---

Article: **$ARGUMENTS**

STOP — your VERY FIRST action, before reading any file, fetching anything, calling any tool,
or reasoning about the article, is to ask the user this one question and wait.

Ask it immediately with AskUserQuestion, with EXACTLY these two options, in THIS exact order
and wording, EVERY time — verbatim, no additions, no rephrasing:

> **Is this a new article or a refresh?**
> 1. **New article**
> 2. **Refresh**

Do not run tools first. Do not think for long. Just ask.

Once answered, map the choice and then execute the flow end to end:

- **New article → `is_draft = true`** (quick / automatic path; no GSC list).
- **Refresh → `is_draft = false`** (manual update path; GSC list + browser pickers).
- Read `~/.claude/factcheck-flow/prompts/seo-research.md` and perform stages **S0 → S3 in
  order**, passing that answer into S0 (do not ask this question again).
- That file ends by telling you to read `~/.claude/factcheck-flow/prompts/seo-write.md` for
  **S4 → S9**. Read it THEN, not now — the flow is split in two so the writing instructions
  and the writing guides stay out of context during the research stages.
- Honor the scarcity fallback and the "Do you want to proceed with optimization?" gate. On a
  skip, go straight to the `/fact` hand-off and never read part 2.
- If no article argument was given, ask for the URL/ID first (after the new-vs-refresh question).

Follow those two files exactly, including the CONFIG, the keyword-selection logic, and the
final `/fact` hand-off in S9.

Whatever you save must already satisfy the block contract in
`~/.claude/factcheck-flow/guides/WordPress-blocks.md` — that file is the single source of
truth for the required document order and for every block's markup, and `seo-write.md` tells
you when to read it. `/fact` enforces the same contract afterward, but shipping it right the
first time avoids a second rewrite.
