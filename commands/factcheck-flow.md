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

Collect every subagent's returned report. A report is one of: `CORRECT: No fix
needed`; a single `REWRITE_REQUIRED: <reason>` line (handle via the Rewrite gate
below — do NOT treat it as a finding); or a two-bucket findings report.

The two buckets are the reporter's own split, and they map straight onto what you do next:

- **`AUTO`** — one line per finding, already in the shape
  `<type> | <location> | <what is wrong> → <the fix>`. These are applied without asking.
  Do NOT expand, re-derive, or re-verify them; pass each line through to Stage 3 verbatim,
  tagged with its article.
- **`ASK`** — the long seven-field form, and the only findings Stage 2 looks at.

Articles that returned `CORRECT: No fix needed` contribute zero findings but still go
through Stage 3.

Briefly tell the user how many findings came back per article, then go to Stage 2.
If there are zero findings across all articles (and none needs a rewrite), tell the
user and skip directly to Stage 3.

### Rewrite gate

An article enters the rewrite path in one of two ways: (a) its Stage 1 report is a bare
`REWRITE_REQUIRED: <reason>` — truncated/incomplete or self-repeating; this is fully
automatic with no user input and runs before Stage 2; or (b) a grave factual error was
**independently verified and then approved by the user** during Stage 2 triage (case 3
below). For each such article:

1. Spawn an **article-editor** subagent in **rewrite mode**: pass the article URL/ID and
   the reason — the `REWRITE_REQUIRED` reason, or, for a verified-and-approved grave
   factual error, that correction — and tell it to complete/rewrite the article so it matches
   the full structure of similar articles on the same site (fill missing sections, remove
   any duplicated/repeated content, correct the confirmed error) and save via
   `wordpress-access`. In rewrite mode it runs no triage, editorial, or link pass.
2. When the rewrite is saved, **re-run the entire /fact pipeline on that article from
   Stage 1** (fresh fact-check → triage → editorial + links).

A truncation/repetition rewrite is never asked about — it happens automatically on
detection. A grave factual error is the one case where a rewrite follows independent
verification plus the user's approval (Stage 2, case 3). Guard against loops: rewrite a given article at most
**twice**. If it still returns `REWRITE_REQUIRED` after the second rewrite, stop looping
it and flag it for manual attention in the final report. Articles that did not trigger a
rewrite proceed through Stage 2 as normal (they do not wait on rewriting articles).

## Stage 2 — Triage gate (mostly automatic — the human is asked in only three cases)

**The whole `AUTO` bucket is applied automatically** — route it straight to Stage 3
without inspection. (`publishing`: a draft stays a draft and a published article stays
published — the editor already targets the right one, so never ask. Categories and tags
are owned by the editorial pass, which also strips "Uncategorized" — nothing to ask here.
Block-contract gaps are not reported at all now: the editor's Pass D enforces the contract
unconditionally, so there is nothing to triage.)

Only the `ASK` bucket reaches this stage, via the `AskUserQuestion` tool (batch up to 4
per call; label each with its article + location). If the `ASK` bucket is empty across
every article, skip the questions entirely and go straight to Stage 3. Case 3 is special:
a flagged grave error reaches the human **only after an independent agent verifies it**.
Run those verifications first (see case 3) so that a confirmed error joins cases 1–2 in
the same `AskUserQuestion` batch, while an unconfirmed one is dropped and never asked.

1. **Listicle review scores** — any finding with `NEEDS_USER_VALUE: true`. The reporter
   can't reach Capterra/G2/Trustpilot, so ask the user for the correct current score for
   each service; offer sensible options plus the free-text "Other" field. Apply the
   supplied value in Stage 3.

2. **Pabau's own ranking position** — a `listicle-rank` finding flagged `CONFIRM: true`,
   i.e. one that would move Pabau up or down from where the article currently places it.
   Show the proposed position vs. current and ask **Apply / Reject**. Re-ranking of every
   other service is automatic and is never asked.

3. **Grave factual error (rewrite-scale)** — a `factual` finding flagged `CONFIRM: true`:
   one whose correction would require a full rewrite or rewriting large parts of the
   article (e.g. the central ICD/CPT code the article is built on is wrong). **Do not ask
   the human about it yet — first verify the error with an independent agent.** Spawn a
   fresh, read-only fact-checker subagent (a `general-purpose` agent; run all such
   verifications together in a single message when more than one grave error was caught)
   and hand it only what it needs to judge the claim from scratch: the article's exact
   statement, the reporter's proposed `CORRECT` value, and the reporter's `EVIDENCE`
   line. Do not send it the article or any other finding. Tell
   it to research the point independently — actively trying to establish whether the
   article could in fact be right — to write nothing anywhere, and to return **exactly one
   verdict line**:
   `VERIFIED_ERROR: <why the article is genuinely wrong>` **or**
   `NOT_AN_ERROR: <why the article's statement is actually fine>`.
   - **Verifier returns `NOT_AN_ERROR`** → the flagged error is not real. **Drop the
     finding, leave the article unchanged on that point, and do NOT contact the human.**
     Record it as "grave error flagged but not confirmed on verification" for the summary.
   - **Verifier returns `VERIFIED_ERROR`** → the error is real, so **contact the human for
     input** via `AskUserQuestion`: show the article's statement, the verified correction,
     and that an independent check confirmed it, then ask **Apply (rewrite) / Reject**.
     - **Apply** → do not apply it as a normal in-place fix; route the article into the
       Rewrite gate path above (article-editor rewrite mode, then re-run /fact from
       Stage 1), passing the verified correction as the basis for the rewrite.
     - **Reject** → drop the finding and leave the article unchanged on that point.

Record a decision for every finding that was asked; everything else is already marked
Apply. Nothing has been written to WordPress yet. After the last batch, show a short
summary of what will be applied / rewritten / rejected / dropped-after-verification per
article, then proceed to Stage 3 automatically (no further prompts).

## Stage 3 — Apply + editorial + links (parallel, automated)

Spawn one **article-editor** subagent per article, **all in a single message** (so
articles process concurrently). To each subagent pass:
- its article URL/ID,
- that article's `AUTO` lines verbatim, and
- the **approved** `ASK` decisions for that article from Stage 2 (include any
  user-supplied values/edits; omit rejected findings).

Each subagent fetches its article ONCE, runs its four sequential passes (approved
fact-check fixes → editorial → link audit → block guarantees) in memory, and writes
everything back in a SINGLE save via the `wordpress-access` skill. They do not ask
further questions.

The block-guarantee pass ALWAYS runs last and enforces the contract in
`~/.claude/factcheck-flow/guides/WordPress-blocks.md` — required document order plus the
eight always-on guarantees (Key takeaways, template download box, Pabau section + CTA
block, Conclusion, Continue your research, Yoast FAQ, listicle pricing segments, image
captions). That file and the article-editor's own Pass D own the detail; you are the
orchestrator and never perform this work, so do not restate the contract to the subagents
— they read it themselves.

## Final report

Once all Stage 3 subagents return, compile a single consolidated summary for the user.
Each editor returns a compact change-log; relay it, don't re-derive it. Per article:
fact-check fixes applied, editorial highlights, link changes, the one-line block-contract
status the editor reported for each of the eight guarantees, and anything skipped. Note
any article whose grave error was flagged but dropped after independent verification, and
any article that hit the two-rewrite ceiling and needs manual attention. End with the
reminder to purge the WP Rocket cache for each edited URL.
