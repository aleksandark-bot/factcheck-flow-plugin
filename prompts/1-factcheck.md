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

Otherwise, return your findings in **two buckets**. Almost every finding is applied
automatically without a human ever reading it, so only the small "needs a human" bucket
gets the full seven-field form. Writing the long form for every finding costs the
orchestrator a large context for no decision.

### Bucket 1 — `AUTO` (applied without asking)

Everything of type `factual`, `Pabau-fact`, `link`, `publishing`, or `missing-section`,
plus any `listicle-rank` change that does NOT move Pabau's own position. **One line each**,
numbered, in this exact shape:

```
AUTO 1. <type> | <location> | <what is wrong> → <the correct value / the change to make>
```

Keep each line to about 30 words. No labelled sub-lines, no evidence, no reasoning — the
editor applies these as written.

### Bucket 2 — `ASK` (the human decides)

Only two kinds of finding reach a human, and they are the only ones that get the long
form. For EACH, include these labelled lines:

- `LOCATION:` where in the article the fix applies (section heading / paragraph / link anchor)
- `TYPE:` `factual` or `listicle-rank`
- `ISSUE:` exactly what is wrong
- `CORRECT:` the correct information / value
- `FIX:` the specific change to make
- `EVIDENCE:` what you checked and what it showed (an independent verifier reads this)
- `NEEDS_USER_VALUE:` `true` if this needs a value only the human can supply
  (e.g. correct Capterra/G2/Trustpilot score); otherwise `false`.
- `CONFIRM:` `true` if this fix must get the human's explicit sign-off before it is
  applied. Set it `true` in only two cases: (1) a **grave factual error** whose correction
  cannot be a simple in-place edit because it would require a full rewrite or rewriting
  large parts of the article (e.g. the central ICD/CPT code the whole article is built
  around is wrong) — report it as a `factual` finding with `CONFIRM: true`, and do NOT emit
  a bare `REWRITE_REQUIRED` for it; (2) a `listicle-rank` change that moves **Pabau's own
  position** up or down.

A finding belongs in bucket 2 only if `CONFIRM: true` or `NEEDS_USER_VALUE: true`.
Everything else goes in bucket 1, however important it feels.

If the article is entirely fine, reply with exactly: `CORRECT: No fix needed`.
If one bucket is empty, write the header and `(none)`.

## Blocks — do NOT audit them here

**You do not check the block contract.** The article-editor's final pass (Pass D) enforces
all of it unconditionally at the end of Stage 3 — Key takeaways, the template download box,
the Pabau section and its CTA block, the Conclusion, Continue your research, the Yoast FAQ
block, listicle pricing segments, and image captions. It locates and re-derives each one
from the raw markup regardless of what you say, so a block audit here is work that gets
redone twice and read by nobody. Skip it, and do not read `WordPress-blocks.md`.

**The one exception:** if the article has **no FAQ section at all** and its type calls for
one, report that as a single `missing-section` line in bucket 1. Pass D deliberately never
invents a missing FAQ — it only converts one that exists — so that gap has to be caught
here or it ships. A malformed or non-Yoast FAQ is NOT your problem; Pass D converts it.

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
(no intro, no FAQ, no conclusion, etc.) is NOT a rewrite. Pass D adds the block-contract
sections automatically in Stage 3, so the only absence you report is a wholly missing FAQ
(see "Blocks — do NOT audit them here").

---

## Review instructions

Review the content of this article carefully for factual and medical/coding accuracy. Also check the link status: whether the internal/external links are broken or not (this is the one link check that lives in this pass — the editorial/link stage handles redirects, nofollow, anchor text, counts, and replacements). Do NOT audit the block contract (see the section above); the only structural gaps you report are a wholly missing FAQ and missing documentation requirements where the topic calls for them. Do NOT flag Healthcode references that appear in images or image captions — the editorial step replaces those automatically, so there is no need to report them. If something is wrong, report the correction (do NOT apply it in this pass; if the article is a draft, note it should be saved as a draft; if it's published, note the change targets the published article). If the article is a listicle, then ensure everyone is ranked fairly (do additional research, be completely objective (do not be fooled by the original framing of the article!), be completely unbiased, and then place every service in its appropriate order. If your fair re-ranking moves **Pabau itself** up or down from where the article currently ranks it, flag that specific finding with `CONFIRM: true` — the human signs off on Pabau's own position, while the re-ordering of every other service applies automatically. For listicles, you can't actually access Capterra/G2/Trustpilot to fact check if the scores are correct, so always ask for the correct score for each service (flag each as NEEDS_USER_VALUE: true). For listicles DO NOT base your entire opinion around Capterra/G2/Trustpilot scores, as these are overall scores, whereas the listicle will always have a specific theme (the ranking must reflect the best fit for the purpose of the reader, not overall best for any purpose). [year] and %%currentyear%% are modifiers and apply the correct year on the front end (not a placeholder). Tell me if the content is correct or not. If the article is correct, just say "CORRECT: No fix needed" — this is a perfectly good answer. If it is not correct, give me a report on what you found, listing all issues in a numbered list. The report should specify exactly what is wrong, what the correct information is, and where in the article the fix needs to be applied.

Note: This is a newly published article or draft that may not yet be indexed by search engines, so don't rely on a search index to read it.

**Fetch it ONCE, via the REST API, using the `wordpress-access` skill (SKILL.md)** — with `context=edit` and that skill's `_fields=` list. Do NOT WebFetch the public URL: the site's navigation and footer are very large and would eat most of the response before the body appears, which is why older versions of this prompt told you to raise the token limit. The REST response has no nav in it, so the workaround is unnecessary. In this pass you only READ — no PUT, no POST.
