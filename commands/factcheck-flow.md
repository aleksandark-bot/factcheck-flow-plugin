---
description: Batch-QA WordPress articles — parallel fact-check, per-finding human triage, then automated editorial + link passes.
argument-hint: "<url-or-id> <url-or-id> ... (up to ~5)"
---

You are orchestrating a three-stage WordPress article QA run over the articles the
user passed as arguments.

Articles to process: **$ARGUMENTS**

If no arguments were given, ask the user for the list of article URLs or post IDs and
stop until they provide them. Otherwise parse them into a list (whitespace- or
newline-separated). Treat each token as one article. Proceed through the stages below
in order. Do NOT skip the triage gate.

---

## Stage 1 — Fact-check (report-only, parallel)

Spawn one **factcheck-reporter** subagent per article, **all in a single message**
(so they run concurrently). Give each subagent exactly one article (its URL or ID)
and tell it to produce its findings report per its instructions. These agents are
read-only — nothing is written to WordPress in this stage.

Collect every subagent's returned report. Parse them into a flat list of findings,
tagging each with its article. Keep the `NEEDS_USER_VALUE` flag, `TYPE`, `LOCATION`,
`ISSUE`, `CORRECT`, and `FIX` for each. Articles that returned `CORRECT: No fix
needed` contribute zero findings but still go through Stage 3.

Briefly tell the user how many findings came back per article, then go to Stage 2.
If there are zero findings across all articles, tell the user and skip directly to
Stage 3.

## Stage 2 — Triage gate (interactive — this is the ONLY manual step)

Walk the user through **every** finding using the `AskUserQuestion` tool, in batches
of **up to 4 findings per call** (its per-screen maximum). Preserve article grouping
where practical and label each question with the article + location so the user has
context. For each finding:

- **Normal finding** → options:
  - `Apply suggested fix` — apply the FIX as written.
  - `Reject` — do not change this.
  - `Edit before applying` — user supplies the exact change (via the "Other" field).
- **`NEEDS_USER_VALUE` finding** (e.g. "Correct G2 score for <service>?", ambiguous
  category/tag) → make the question ask for that value; offer sensible options plus
  the free-text "Other" field.

Record a decision for every finding. Nothing has been written to WordPress yet — this
gate exists precisely so the user approves each change first. After the last batch,
show a short confirmation summary of what will be applied vs. rejected per article,
then proceed to Stage 3 automatically (no further prompts).

## Stage 3 — Apply + editorial + links (parallel, automated)

Spawn one **article-editor** subagent per article, **all in a single message** (so
articles process concurrently). To each subagent pass:
- its article URL/ID, and
- the list of **approved** decisions for that article from Stage 2 (include any
  user-supplied values/edits; omit rejected findings).

Each subagent runs its four sequential passes (approved fact-check fixes → editorial
→ link audit → FAQ block guarantee) on its own article and writes changes via the
`wordpress-access` skill. They do not ask further questions. The final pass ALWAYS
runs last: it ensures the article's FAQ is a proper Yoast FAQ block (not plain HTML),
converting it if it isn't. Articles with no FAQ are left untouched by that pass.

## Final report

Once all Stage 3 subagents return, compile a single consolidated summary for the user:
per article — what fact-check fixes were applied, editorial highlights, link changes,
the FAQ block result (already a Yoast block / converted to Yoast block / no FAQ present),
and anything skipped. End with the reminder to purge the WP Rocket cache for each
edited URL.
