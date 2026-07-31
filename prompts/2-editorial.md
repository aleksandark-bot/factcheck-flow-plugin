<!--
  PROMPT 2 — EDITORIAL PASS (applied automatically in Stage 3)
  Edit freely for your own site's style guide.
-->

## Read these first

Guides live in `~/.claude/factcheck-flow/guides/` (script install) or `${CLAUDE_PLUGIN_ROOT}/guides/` (plugin install).

**Always, before applying anything below:**

- `core-rules.md` — the always-on baseline: the Pabau non-negotiables, voice and mechanics, the AI tells, the two-bar rule, and the required document order. Everything in it holds in every edit.
- `Pabau-style-guide.md` — tone of voice, benefit framing, US/UK terminology table, formatting mechanics, and the treatments/regulation glossary. You are rewriting prose, so this one is not optional.

**When their trigger fires — not before, because a guide you open stays in context for the whole pass:**

- `WordPress-blocks.md` — **the moment you touch, add, convert, or move any block.** It is the single source of truth for the block contract: required document order and the exact markup for Key takeaways, the template download box, the `book-demo` CTA block, the required Pabau section, the `Conclusion`, the `expert-picks` block, the Yoast FAQ block, listicle pricing tables, image captions and spacers. The rules below say what must exist and how to write the copy; that file says exactly how to mark it up. Never reconstruct block markup from memory.
- `About-Pabau.md` — writing new Pabau copy (the Pabau section, CTA text, a Pabau-feature caption) or checking a Pabau claim: product family, naming rules, pricing model, competitors.
- `Meta-title-best-practices.md` — writing or re-optimizing the SERP title. Only then.
- `Originality-and-search-intent.md` — judging intent from a SERP or deciding a restructure. `core-rules.md`'s two-bar summary is enough for a light pass; open the full guide when you are actually reshaping the article.

Precedence: the style guide governs **voice, terminology, and Pabau positioning**; `WordPress-blocks.md` governs **block markup and document order**; the rules below govern **copy, meta descriptions, and AI-tell removal**. Where a US/UK spelling or term is in question, the style guide's terminology table wins.

Two rules from `core-rules.md` worth restating because this pass is where they bite:

- **Verify Pabau facts** (product family, pricing model, integrations, competitor framing) against About-Pabau; never name specific customers without the team's confirmation.
- **Fit intent + be original.** To judge this, pull the SERP for the focus keyphrase with **WebSearch** (you don't have DataForSEO in this pass) and read the top ~10 organic results. Flag generic me-too content and mirage fluff (obvious "no shit" advice, platitudes, no real examples) for rewrite. If the article is the wrong format for the SERP, that's a structural change, not a copy tweak.

---

You are a seasoned editor with no tolerance for fluff. Apply the following editorial standards:

Remove all fluff: every sentence must be substantial and bring information to the article, it cannot be padding.

Remove Claude speak in intro and the rest of the text.

Do not talk about gaps unless it's an actual, physical gap (like a gap in a brick wall). Remove all mentions of gaps not relating to physical gaps.

Do not talk about things being "real" or "actual", example:
- BAD: A four-clinician dermatology group taking two weeks longer than expected to reach full productivity will absorb that cost invisibly, but it is real.
- GOOD: A four-clinician dermatology group taking two weeks longer than expected to reach full productivity will absorb that cost invisibly, but it still affects the bottom line.

No "it's not X it's Y" phrasing; examples:
- BAD: The comparison is not about which platform is objectively better. It is about fit. A multi-physician ophthalmology group whose revenue is driven primarily by high-volume, complex insurance claims will likely find Nextech's billing depth worth its cost.
- GOOD: But the key factor in this comparison is fit. A multi-physician ophthalmology group whose revenue is driven primarily by high-volume, complex insurance claims will likely find Nextech's billing depth worth its cost.
- BAD: For practices evaluating the best EHR for private practices, the key comparison points are not just feature lists. They are total cost of ownership, implementation timeline, and how quickly a new hire can reach full productivity without expensive consulting hours.
- GOOD: What really counts for private practices evaluating the best EHR is total cost of ownership, implementation timeline, and how fast a new hire can reach full productivity without racking up expensive consulting hours.

Do not talk about things that "most practices miss" or "most [whatevers] miss" — this is a dead giveaway that Claude wrote the text. And I don't mean strictly that exact phrasing, I mean anything approaching it, eg. "But here's the part most dermatology clinics avoid."

Also check for keyword stuffing in headings and body text. Especially check if the headings read naturally, as often they could be shoehorning exact-match keywords.

**Template articles (`/templates/`) — do NOT repeat the main keyword across headings.** The template name is the main keyword, so every H2 tends to end up carrying it ("What is a body dysmorphia worksheet?", "How to use a body dysmorphia worksheet", "Benefits of a body dysmorphia worksheet", "Who is the body dysmorphia worksheet for?"). Read the heading tree as a standalone list: if the same phrase repeats down the page, rewrite it. The full keyword belongs in the H1, the download box H2, and the intro; from there on, use alternatives:

- **Short form / category noun** — "the worksheet", "the form", "this chart", "the questionnaire", "the aftercare instructions", "the log".
- **The reader's task instead of the object** — "What to include", "How to fill it out", "How to score and interpret results", "When to hand it to the patient", "Where it fits in the intake workflow".
- **The clinical subject the section is really about** — "Cognitive distortions worth challenging", "Blood pressure thresholds in pregnancy", "Documentation that satisfies an inspector".
- **Implicit reference** — drop the object entirely where the section's parent context already supplies it ("Common scoring mistakes", "Adapting it for teenagers").

Practical ceiling: at most **two body headings** may carry the full keyword, and never two in a row. Everything else varies. Keep coverage identical — this changes heading wording only, never what the article covers or the content under each heading.

This is not permission for awkward phrasing in either direction. Every heading must read like something a person would write: no stacked qualifiers ("Free printable body dysmorphia worksheet template PDF"), no headings that read as a pasted search query, no grammatical contortion to fit an exact-match phrase in ("Body dysmorphia worksheet how to use"), and no vague heading that hides what the section is about just to avoid the keyword. If the only natural way to word a heading uses the keyword, use the keyword — a clean, clear heading beats an ugly one that dodges repetition. Apply the same test to H3s and H4s, and to the FAQ questions (vary the phrasing across questions; don't open all six with the template name).

Also check for UK spelling / phrasing (it MUST be US English). This includes changing "clinic" to "practice" in most cases, as well as changing any other UK-specific medical language to US. When in doubt, go the moderate route. If the article is UK-specific, still go moderate, keeping references to UK legislation, bodies, etc but mostly using "practice" still.

Unless it's a UK-specific article, remove references to Healthcode and replace with generic claims and billing. Example: OLD: Automate claims through Healthcode. NEW: Automate claims and billing with Pabau. Apply this automatically — never ask about it, just replace. If the reference is in an image caption, don't worry about the image — it's generic enough to just change the caption and be good.

**Every image must have a caption.** Walk every image block in the article; any image without a `<figcaption>` gets one written for it, and any existing caption gets brought up to standard. Never ask about this — write the caption. **The caption contract, the markup, and the required 800 × 35 spacer block are all in `WordPress-blocks.md` §10** — including the rule that a caption on a Pabau-feature screenshot must name the feature and say how it helps the reader do what this article is about. Follow that section; don't work from memory. What is yours in this pass is the writing: a full sentence in the article's voice, under the 25-word ceiling, that adds information rather than restating the alt text.

**A YouTube video never interrupts a prose section.** If the article has an embed, it belongs at the end of the intro — after every intro paragraph, before the first H2. An embed sitting between two body paragraphs, or between a heading and its first paragraph, gets moved to that slot; if a paragraph was split around it, rejoin the halves and delete any "watch the video below" line that no longer points at anything. Placement, markup, and the spacer are in `WordPress-blocks.md` §11.

## Structure and blocks

**`WordPress-blocks.md` is the single source of truth for the required document order and for every block's markup.** Open it whenever you add, convert, or move a block, and copy the markup from there.

Your job in this pass is the *copy* inside that structure, and one structural duty:

**Add any missing section or block automatically** — including any `missing-section` finding handed to you from Stage 1. Write it to match the depth and tone of the rest of the article; never ask about it. This matters most for a **wholly missing FAQ**, because the article-editor's final block pass deliberately never invents one: if the article type calls for an FAQ and there is none, you write it here or it never ships.

When you write those sections, the content rules are:

- **Key takeaways** — every takeaway a full sentence in sentence case (capitalize only the first word and genuine proper nouns). The block form, the mandatory `"title":"Key takeaways"` attribute, and the casing rule are in §2.
- **Download box** (template articles) — the H2 reads "Download your free <template name>", grammatical rather than exact-match; the description names what is actually inside this file, in 1–2 sentences. Verify the download URL returns 200 before saving; if nothing resolves, keep the box and record the missing asset under "Skipped". Markup and the URL pattern are in §3.
- **Pabau section** — 2–4 paragraphs on the actual workflow: what the practice does today, what Pabau does instead, the outcome. Topic-specific H2, never "Why choose Pabau". If a Pabau section already exists elsewhere in the body, move or rework it into this slot rather than writing a second one. Placement, heading rules, and the CTA block are in §4–§5.
- **Conclusion** — it must genuinely conclude, not summarize: no restating the Key takeaways, no listing what the article covered. Land the judgment the article earned — what the reader should do now, what changes if they do, the trade-off worth remembering — in 2–4 short paragraphs, ending with the inline CTA link. Heading rule and CTA markup are in §6.
- **Continue your research** — which articles it links to is governed by `3-links.md`; markup and the 5-item ceiling are in §7.
- **Listicle pricing** — one sentence of context under each pricing table. Every figure comes from the provider's own website only: never Capterra, G2, GetApp, Software Advice, Trustpilot, a round-up, or another blog; pabau.com only for Pabau. If a provider publishes no prices, say "Contact sales / no published pricing" and explain it below. Table forms and columns are in §9.

Fix all improperly formatted HTML.

Leave the FAQ's content clean and well-formed. You do not need to convert it to a Yoast block — the article-editor's final pass does that — but a malformed FAQ you can fix here is one less thing for it to untangle.

Check for proper capitalization of titles and body text (Titles should be sentence case, except when the title starts with a number (first letter of the first proper word must be capitalized then). Another exception is following a period, colon, semicolon or em-dash.

Optimize the SERP title (meta title) per `Meta-title-best-practices.md`: use a number for listicles, include the current year where the topic is time-sensitive, match the searcher's micro-intent, differentiate from the rest of the SERP, and lead with the pain point being solved. Don't just repeat the H1 verbatim if a stronger SERP title is warranted.

For codes, intro starts with a definition — delete all hedging language that sets up stakes etc (the searcher does not need to know that they're liable if they mess up coding, that's why they're looking this up).
- BAD: Most heart transplant complications fall cleanly into a named category: rejection, failure, infection. When the complication doesn't fit any of those, ICD-10 Code T86.298 is the correct billable code. It covers every post-transplant cardiac complication not elsewhere classified within the T86.2x subcategory, and it's the code that coders most frequently reach for when documentation describes something atypical in a transplant recipient's clinical course.
- GOOD: ICD-10 Code T86.298 is a billable code that covers every post-transplant cardiac complication not elsewhere classified within the T86.2x subcategory. It's the code that coders most frequently reach for when documentation describes something atypical in a transplant recipient's clinical course.

Fix outdated feature references, if any (e.g. Echo AI).

Break up long paragraphs (no more than 4 lines or 60 words).

If you find a sentence that lists three or more long items (as in, entire clauses of three or more words are list items), turn that into a wordpress list block instead of a paragraph.

Shorten long sentences to make them more legible. Split off clauses from longer sentences into their own sentences, rather than separating them with em dashes, colons or semicolons.

**Hard ceiling: 25 words per sentence. This one is measured, not eyeballed.** You cannot count words reliably while writing, so don't try — a script does it:

```bash
python3 ~/.claude/factcheck-flow/bin/sentence_check.py --file /tmp/body.html
```

Run it on the body you hold, rewrite every sentence it lists, re-run, and repeat until it exits 0. **Nothing over 30 words ships, ever.** The 26–30 band is a per-sentence exception you have to justify, not a second budget — if you can't say why a split would break the meaning, split it. Splitting one long sentence into two is almost always the fix.

The ceiling covers every piece of prose the checker sees: body paragraphs, list items, table cells, image captions, Key takeaways items, CTA and download-box copy, FAQ answers, meta description.

Short does not mean choppy, and the gate is not an excuse for damage. No dropped subjects, no telegraphic fragments, no clause welded on with a semicolon or em dash so one sentence can pass as two. Vary the length, per the style guide — a run of same-length sentences reads like a metronome. The script counts words; you still own the prose.

(In `/fact` the article-editor runs this as a hard gate before saving — Pass E. Leave the copy clean here and that gate has nothing left to do.)

Ensure headings have correct hierarchy (H1 > H2 > H3 > H4).

Edit meta description to include an answer to the searcher query, written as if it were an excerpt from the article, mentioning particular observations, or our top choice if it's a listicle (no more than 140 characters long):
- BAD: Explore our guide on ModMed vs DrChrono: Which EHR fits your specialty practice?
- GOOD: ModMed suits specialty practices needing built-in workflows, while DrChrono is better for practices prioritizing flexibility and customization.

Add Yoast keywords to headings.

Add tags and categories manually — use existing ones in WordPress, and apply no more than 4 categories. (Stage 1 no longer flags categories/tags; owning them here is the single source of truth.)

When adding categories, always remove the "Uncategorized" category.

Where applicable, check pricing from ONLY the provider website, not third-party sources.

Note: This is a newly published article or draft that may not yet be indexed by search engines, so don't rely on a search index to read it.

**Work from the copy of the article you already hold.** This pass runs inside the article-editor, which fetched the article once at the start — do not re-fetch it. If you somehow need to read it fresh, use the REST API via the `wordpress-access` skill (`context=edit` plus that skill's `_fields=` list), never a WebFetch of the public URL: the site's navigation and footer would consume most of the response before the body appears. Hold your edits for the single save at the end of the run.
