<!--
  PROMPT 1 — FACT-CHECK (report-only mode)
  Edit freely for your own site. The orchestrator runs this in REPORT-ONLY mode:
  the agent must NOT write anything to WordPress here — it only produces a findings
  report that YOU triage before any change is applied in Stage 3.
-->

# REPORT-ONLY MODE — DO NOT WRITE TO WORDPRESS

You are reviewing ONE article. In this pass you make **no changes** to WordPress
(no PUT/POST, no draft save, no category/tag/link edits). You only fetch (GET is
fine) and produce a findings report. All approved changes are applied later, in a
separate stage, after the human has triaged your findings.

**Before anything else, run the truncation / repetition check (see "Truncation or
repetition" below).** If it trips, reply with the single line
`REWRITE_REQUIRED: <one-line reason>` and nothing else — no findings, no other text.
That signal makes the orchestrator rewrite the article and re-run the entire /fact
process on it, with no human triage.

Otherwise, return your findings as a **numbered list**. For EACH finding include, on its own labelled lines:
- `LOCATION:` where in the article the fix applies (section heading / paragraph / link anchor)
- `TYPE:` one of `factual | link | listicle-rank | publishing | missing-section`
- `ISSUE:` exactly what is wrong
- `CORRECT:` the correct information / value
- `FIX:` the specific change to make
- `NEEDS_USER_VALUE:` `true` if this needs a value only the human can supply
  (e.g. correct Capterra/G2/Trustpilot score); otherwise `false`.
- `CONFIRM:` `true` if this fix must get the human's explicit sign-off before it is
  applied; otherwise `false`. Set it `true` in only two cases: (1) a **grave factual
  error** whose correction cannot be a simple in-place edit because it would require a
  full rewrite or rewriting large parts of the article (e.g. the central ICD/CPT code the
  whole article is built around is wrong) — report it as a normal `factual` finding with
  `CONFIRM: true`, and do NOT emit a bare `REWRITE_REQUIRED` for it; (2) a `listicle-rank`
  change that moves **Pabau's own position** up or down. Every other finding is
  `CONFIRM: false` and is applied automatically without asking.

If the article is entirely fine, reply with exactly: `CORRECT: No fix needed`.

`missing-section` findings are applied automatically in Stage 3 — the orchestrator will
not ask the user about them, so never mark them `NEEDS_USER_VALUE`. Just report which
expected section is absent and where it belongs; the editor writes it.

## Required blocks check (report each gap as `missing-section`)

Read `~/.claude/factcheck-flow/guides/WordPress-blocks.md` (reference article:
https://pabau.com/templates/accutite/) and check the article's RAW block markup
(`context=edit` — the rendered page won't show you block names) against the contract.
Report each of these as a `missing-section` finding, `CONFIRM: false`,
`NEEDS_USER_VALUE: false`:

- **Key takeaways** — missing, not a `wp:gutenberg-custom-blocks/key-takeaways` block, or
  missing the mandatory `"title":"Key takeaways"` attribute (without it the page renders
  "Key Takeaways", which is the wrong casing). Also flag takeaways not in sentence case.
- **Download box** (template articles only) — absent, not below Key takeaways / above the
  intro, missing its built-in H2, or pointing at a download URL that does not return 200.
- **Pabau section** — no H2 section immediately before the Conclusion that promotes Pabau
  for this article's purpose, or that section exists but carries no
  `gutenberg-custom-blocks/book-demo` CTA block.
- **Conclusion** — no H2 headed exactly `Conclusion` (a variant such as "The bottom line"
  or "Final thoughts" counts as a finding: report the rename), a conclusion that merely
  summarizes instead of concluding, or one that does not end with an inline
  `/book-demo/` CTA link.
- **Continue your research** — no `gutenberg-custom-blocks/expert-picks` block after the
  Conclusion, one carrying more than 5 items, one carrying placeholder/dead items, or a
  leftover wrapper H2 above it (the block renders its own heading).
- **FAQ** — present but not a `wp:yoast/faq-block` (schema missing), or absent on an
  article type that calls for one.
- **Listicle pricing segments** — any provider review that does not END with a `Pricing`
  heading + pricing table (`gutenberg-custom-blocks/pricing-table` or a `wp:table`).
  Also report the listicle's top-of-page comparison table if it's missing.

Separately, any pricing figure you can trace to a third party (Capterra, G2, GetApp,
Software Advice, Trustpilot, a review round-up, another blog) instead of the provider's own
website is a `factual` finding with `CONFIRM: false` — give the provider's published figure
as `CORRECT`, or "Contact sales / no published pricing" when the vendor publishes none. For
Pabau's own pricing, pabau.com is the only acceptable source.

## Truncation or repetition → automatic rewrite (check this first)

Check whether the article is **truncated or broken** (the body cuts off mid-section or
mid-sentence, or so much is absent that the piece can't stand on its own) OR **repeats
itself** (duplicated sentences, paragraphs, or whole sections). Either problem means the
article can't be QA'd as-is; it needs a rewrite, not findings. When you detect it, reply
with exactly one line: `REWRITE_REQUIRED: <one-line reason>` (e.g. `REWRITE_REQUIRED:
body cuts off mid-sentence under the "Documentation requirements" H2`). Do not list any
other findings — a fresh /fact run happens automatically after the rewrite.

A single expected section merely being **absent** from an otherwise-complete article
(no intro, no Key Takeaways, no FAQ, no conclusion, etc.) is NOT a rewrite — report it
as a `missing-section` finding. Those are added automatically in Stage 3 with no user
approval.

---

## Review instructions

Review the content of this article carefully for factual and medical/coding accuracy. Also check the link status: whether the internal/external links are broken or not (this is the one link check that lives in this pass — the editorial/link stage handles redirects, nofollow, anchor text, counts, and replacements). Also check whether any expected section is absent (intro, Key takeaways, the Pabau section with its CTA block, Conclusion, Continue your research, FAQ, the template download box, listicle pricing segments, and documentation requirements where the topic calls for it) compared with the block contract in `WordPress-blocks.md` — run the "Required blocks check" above and report each gap as a `missing-section` finding — do not ask for approval, these are added automatically. Do NOT flag Healthcode references that appear in images or image captions — the editorial step replaces those automatically, so there is no need to report them. If something is wrong, report the correction (do NOT apply it in this pass; if the article is a draft, note it should be saved as a draft; if it's published, note the change targets the published article). If the article is a listicle, then ensure everyone is ranked fairly (do additional research, be completely objective (do not be fooled by the original framing of the article!), be completely unbiased, and then place every service in its appropriate order. If your fair re-ranking moves **Pabau itself** up or down from where the article currently ranks it, flag that specific finding with `CONFIRM: true` — the human signs off on Pabau's own position, while the re-ordering of every other service applies automatically. For listicles, you can't actually access Capterra/G2/Trustpilot to fact check if the scores are correct, so always ask for the correct score for each service (flag each as NEEDS_USER_VALUE: true). For listicles DO NOT base your entire opinion around Capterra/G2/Trustpilot scores, as these are overall scores, whereas the listicle will always have a specific theme (the ranking must reflect the best fit for the purpose of the reader, not overall best for any purpose). [year] and %%currentyear%% are modifiers and apply the correct year on the front end (not a placeholder). Tell me if the content is correct or not. If the article is correct, just say "CORRECT: No fix needed" — this is a perfectly good answer. If it is not correct, give me a report on what you found, listing all issues in a numbered list. The report should specify exactly what is wrong, what the correct information is, and where in the article the fix needs to be applied.

Note: This is a newly published article or draft that may not yet be indexed by search engines. Fetch the URL directly and review the full article body content. Use a high token limit when fetching because the site has very large navigation menus that consume token space before the article body appears. You have full WordPress read access via the `wordpress-access` skill (SKILL.md) — but remember, in this pass you only READ.
