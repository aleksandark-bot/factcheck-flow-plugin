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

Once answered, map the choice and then read the full flow and execute it end to end:

- **New article → `is_draft = true`** (quick / automatic path; no GSC list).
- **Refresh → `is_draft = false`** (manual update path; GSC list + browser pickers).
- Read `~/.claude/factcheck-flow/prompts/seo.md` and perform stages **S0 → S9 in order**,
  passing that answer into S0 (do not ask this question again).
- Honor the scarcity fallback and the "Do you want to proceed with optimization?" gate.
- If no article argument was given, ask for the URL/ID first (after the new-vs-refresh question).

Follow `seo.md` exactly, including its CONFIG, keyword-selection logic, and the final `/fact`
hand-off in S9.
