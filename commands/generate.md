---
description: Generate ONE new WordPress article as a DRAFT — commission check, keyword discovery, competitor source harvest, human-approved outline, then write and create the post. Routes to /templates/, /diagnostic-codes/, /procedure-codes/ or /blog/.
argument-hint: "<topic or target keyword>   (one article)"
---

Topic / keyword: **$ARGUMENTS**

STOP — your VERY FIRST action, before reading any file, fetching anything, calling any tool,
or reasoning about the topic, is to ask the user this one question and wait.

Ask it immediately with AskUserQuestion, with EXACTLY these two options, in THIS exact order
and wording, EVERY time — verbatim, no additions, no rephrasing:

> **Is this a locked target keyword, or a topic to research?**
> 1. **Locked keyword**
> 2. **Topic**

Do not run tools first. Do not think for long. Just ask.

Once answered, map the choice and then execute the flow end to end:

- **Locked keyword → `keyword_locked = true`.** The phrase you were given IS the main keyword.
  Research still runs — it decides the supporting keywords, the SERP profile and the outline —
  but you never retarget the main keyword. The ownership veto is the one exception: a blocker
  is still a question, never a silent override.
- **Topic → `keyword_locked = false`.** The argument is a SEED. G3 picks the main keyword from
  the data, automatically, using the new-page priority order.
- Read `~/.claude/factcheck-flow/prompts/generate-research.md` and perform stages **G0 → G4 in
  order**, passing that answer into G0 (do not ask this question again).
- That file ends by telling you to read `~/.claude/factcheck-flow/prompts/generate-write.md`
  for **G5 → G10**. Read it THEN, not now — the flow is split in two so the writing
  instructions and the writing guides stay out of context during the research stages.
- If no topic argument was given, ask for it first (after the locked-vs-topic question).

Follow those two files exactly, including the CONFIG, the ROUTE TABLE, the commission gate,
the outline gate, and the final `/fact` hand-off in G10.

**This command creates a DRAFT and nothing else.** `status: draft`, always, with no exception
and no "it looked ready". Publishing is a separate, explicitly-requested job that belongs to a
human. Never call the indexing API on what you create here — the URL does not exist yet.

**The route is decided by the taxonomy you set, not by the slug.** G0 fixes it and the brief
carries the term IDs:

| Destination | What puts it there |
|---|---|
| `/templates/` | the **tag** `template` (ID 1382) |
| `/diagnostic-codes/` | the **category** `diagnostic-codes` (1549) + its subcategory |
| `/procedure-codes/` | the **category** `billing-codes` (1433) + its subcategory |
| `/blog/` | none of the above — the default for every other article |

Two human gates, and only two. Everything else runs automatically:

- **COMMISSION GATE (G2)** — asked only when a pabau.com page already covers this topic or
  already owns the keyword. A duplicate new page is the most expensive mistake this flow can
  make, and refreshing the existing page usually beats writing a new one outright.
- **OUTLINE GATE (G7)** — always asked. Reviewing the outline before any prose exists is the
  cheapest quality gate in the process, and it is what stops the draft from anchoring the
  whole article to a structure nobody chose.

Three things `/generate` produces that live OUTSIDE the article, and that you must report
rather than act on:

- **Corner-stone inbound links** — the 3-5 already-ranking pages that should link INTO the new
  article. A brand-new page has no authority of its own, so this is its single biggest lever.
  Name them with anchors; never edit those pages.
- **Ownership findings** — keywords another pabau.com page already holds, with the competing URL.
- **Deferred keywords** — secondary topics that need their OWN page later, not a section here.

You RESEARCH and PLAN; you do not write the article. G9 dispatches the `article-generator`
subagent, which reads the writing guides, writes every section, builds the visual and the
featured image, and creates the post. Do not read `WordPress-blocks.md`, `Pabau-style-guide.md`,
`2-editorial.md`, `About-Pabau.md`, `Visuals.md`, or `Meta-title-best-practices.md` in this
conversation — that agent carries all of them, and loading them here keeps ~40k tokens resident
for the rest of the run.
