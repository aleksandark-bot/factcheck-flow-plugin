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
  order**, passing that answer into S0 (do not ask this question again). Note S1B, the
  ownership pre-flight: it runs on BOTH branches, and a blocker there is a question on the
  refresh path and a decision you make and state on the new-article path.
- That file ends by telling you to read `~/.claude/factcheck-flow/prompts/seo-write.md` for
  **S4 → S9**. Read it THEN, not now — the flow is split in two so the writing instructions
  and the writing guides stay out of context during the research stages.
- Honor the scarcity fallback and the "Do you want to proceed with optimization?" gate. On a
  skip, go straight to the `/fact` hand-off and never read part 2.
- If no article argument was given, ask for the URL/ID first (after the new-vs-refresh question).

Follow those two files exactly, including the CONFIG, the keyword-selection logic, and the
final `/fact` hand-off in S9.

Three things /SEO produces that live OUTSIDE the article, and that you must report rather than
act on — they are edits to other pages or to a live URL, and each has its own sign-off:

- **Ownership findings** — keywords another pabau.com page already holds. Name the competing
  URL; never edit it.
- **Corner-stone links** — the 3-5 already-ranking pages that should link INTO this article,
  with proposed anchors. Named in S9, executed by David or the interlinking project.
- **Slug findings on a published post** — if the slug is genuinely the problem, say so. Never
  change a live URL, and never change publish status.

On a CODE ARTICLE, S9 adds a `Code page:` line — the page's state (one of the four: templated /
broken / half-migrated / old shape) and which `pdc_*` meta fields the writer rewrote or filled.
Relay it verbatim.
/SEO optimizes the shape it finds and NEVER migrates a code page, so when the state is
half-migrated, surface `CODE_PAGE_HALF_MIGRATED` to the user and say the page needs the site
migration process rather than another /SEO pass — the ordinary optimization work still happened.
One template, `template-diagnostic-code.php`, serves both code routes, so the state never
depends on whether the article is a `/diagnostic-codes/` or a `/procedure-codes/` page. The
contract is `WordPress-blocks.md` §13, which
the `seo-writer` subagent carries: do not read it here, and do not restate it in any dispatch.

On a published article S9 also writes a dated BASELINE to
`~/.claude/factcheck-flow/cache/seo-baselines/` and requests a re-crawl of the (already public)
URL. The baseline is what lets the next run tell improvement from noise, so it is not optional.

You RESEARCH and PLAN; you do not write the article. S8 dispatches the `seo-writer` subagent,
which reads the writing guides, fetches the body, writes every section, and saves. Do not read
`WordPress-blocks.md`, `Pabau-style-guide.md`, `2-editorial.md`, `About-Pabau.md`,
`Visuals.md`, or `Meta-title-best-practices.md` in this conversation — that agent carries all
of them, and loading them here keeps ~40k tokens resident for the rest of the run.

What the writer saves must already satisfy the block contract in
`~/.claude/factcheck-flow/guides/WordPress-blocks.md` — the single source of truth for the
required document order and every block's markup. `/fact` enforces the same contract afterward,
but shipping it right the first time avoids a second rewrite.
