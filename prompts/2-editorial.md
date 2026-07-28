<!--
  PROMPT 2 — EDITORIAL PASS (applied automatically in Stage 3)
  Edit freely for your own site's style guide.
-->

## Read these first — Pabau voice & positioning

Before applying anything below, read both guides and treat them as the source of truth for voice, terminology, and how we talk about Pabau. They live in the factcheck-flow `guides/` folder — `~/.claude/factcheck-flow/guides/` for a script install, or `${CLAUDE_PLUGIN_ROOT}/guides/` for a plugin install:

- `Pabau-style-guide.md` — tone of voice, benefit framing, US/UK terminology table, formatting mechanics, and the treatments/regulation glossary.
- `About-Pabau.md` — what Pabau is, the product family and naming rules, pricing model, competitors, and the customer journey.
- `Meta-title-best-practices.md` — SERP title optimization: listicle numbers, year usage, matching micro-intent, differentiating in the SERP, and solving the pain point in the title.
- `Originality-and-search-intent.md` — the two-bar rule: every article must fit searcher intent (answer the query's actual question, in the SERP-dominant format and depth) AND carry at least one originality nugget (a unique angle no top-10 result has). Cut mirage/fluff; be specific.
- `WordPress-blocks.md` — the block contract: required document order, and the exact markup for the Key takeaways block, the template download box, the Pabau CTA (`book-demo`) block, the Continue your research (`expert-picks`) block, the Yoast FAQ block, and listicle pricing tables. Reference article: https://pabau.com/templates/accutite/. It is the source of truth for block markup; the structure rules below tell you what must exist, that file tells you exactly how to write it.

Non-negotiable rules from those guides that must hold in every edit:

- **Introduce Pabau on first mention** for cold search readers — e.g. "practice management software like Pabau", not a bare "Pabau".
- **Qualify product names on first mention:** "Pabau GO, our iOS app", "Pabau Scribe, our AI scribe", "Pabau Pay, our card terminals". **Never use "Pabau Connect" externally** — say "online booking" or "our online booking portal".
- **Don't undermine the core product** when describing Plus add-ons — use "additional"/"specialist", never "advanced"/"basic marketing"/"limited reporting". Every subscription includes a full marketing, patient care, and reporting suite.
- **No feature gating** — every subscription gets every feature; don't imply lower tiers lock functionality.
- **No free trial** — frame as structured onboarding; never apologize for a missing trial.
- **Lead with outcomes, not features.** Spell the benefit out ("so you can…"); don't imply it or leave the reader to join the dots.
- **Verify Pabau facts** (product family, pricing model, integrations, competitor framing) against About-Pabau; never name specific customers without the team's confirmation.
- **Fit intent + be original** (per Originality-and-search-intent.md): the article must answer the query's actual question in the SERP-rewarded format AND have a unique angle. To judge this, pull the SERP for the focus keyphrase with **WebSearch** (you don't have DataForSEO in this pass) and read the top ~10 organic results. Flag generic me-too content and mirage fluff (obvious "no shit" advice, platitudes, no real examples) for rewrite. If the article is the wrong format for the SERP, that's a structural change, not a copy tweak.

Precedence: the two guides govern **voice, terminology, and Pabau positioning**. The rules below govern **article structure** (H1 > Key takeaways > Intro > H2), **meta descriptions**, and **AI-tell removal**. Where a US/UK spelling or term is in question, the style guide's terminology table wins.

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

Intro must exist. The proper structure — see `WordPress-blocks.md` for the exact markup of every block named here — is:

H1 > Key takeaways block > Intro > H2 body sections > H2 Pabau section (containing the Pabau CTA block) > H2 Conclusion > Continue your research block > H2 Frequently asked questions > Yoast FAQ block.

Template articles have one extra element: H1 > Key takeaways block > **Download box** (with built-in H2) > Intro > … (rest identical).

Add any missing section or block automatically — including any `missing-section` fixes handed to you from Stage 1 (intro, Key takeaways, download box, Pabau section, Pabau CTA block, Conclusion, Continue your research block, FAQ, etc.). Write the section to match the depth and tone of the rest of the article; never ask about it. Never put a heading above a block that renders its own heading (Key takeaways, Continue your research) — that ships a duplicate title.

Key takeaways must ALWAYS be a proper WP Key takeaways block — the self-closing custom block `<!-- wp:gutenberg-custom-blocks/key-takeaways {"title":"Key takeaways","items":[{"text":"…"},{"text":"…"}]} /-->`, one `items` entry per takeaway — never a plain heading + bullet list, never a pasted rendered `<div id="key_takeaways">`. The `"title":"Key takeaways"` attribute is MANDATORY: the block hardcodes "Key Takeaways" when no title is passed, and the required casing is **Key takeaways** (capital K, everything else lowercase). An existing block that is correct except for the missing title attribute gets the attribute added. Write every takeaway in sentence case (capitalize only the first word and genuine proper nouns; a full sentence, never Title Case or ALL CAPS). If you are unsure of the site's attribute format, copy it from https://pabau.com/templates/accutite/. (The article-editor's final block-guarantee pass double-checks this — block form, title attribute, sentence case — so at minimum leave the takeaways clean and correctly cased here.)

For templates, make sure the download box is below Key takeaways, above intro and has a built-in H2 tag (something along the lines of "Download your free [template name]", but make sure it's grammatically correct, not just exact-match). Copy the gradient `wp:html` wrapper from `WordPress-blocks.md` byte-for-byte (styles, button label, and all) — the wrapper is fixed, but the H2 text, the description, and the download `href` are written fresh for this article, since every template has its own file and wording. Reuse the article's existing PDF URL where one exists, and verify the download URL returns HTTP 200 before you save — never ship a dead download link; if no working file exists, keep the box and record the missing asset under "Skipped".

Every article must have an H2 section immediately before the Conclusion that promotes Pabau **for that article's specific purpose** and contains the Pabau CTA block (`<!-- wp:gutenberg-custom-blocks/book-demo {"heading":"…","description":"…","imageAlt":"Pabau clinic management dashboard"} /-->`). The heading is topic-specific ("How Pabau supports exercise monitoring and documentation"), never "Why choose Pabau". Write 2–4 paragraphs on the actual workflow — what the practice does today, what Pabau does instead, the outcome — obeying the Pabau non-negotiables above. If the article already has a Pabau section elsewhere in the body, move or rework it into this slot instead of writing a second one; if it has none, write it.

Every article must have an H2 headed exactly **Conclusion**. Rename any variant to `Conclusion` ("The bottom line", "The bottom line on X", "Final thoughts", "Wrapping up", "Getting started with…", or any topic-specific sign-off). It must genuinely conclude, not summarize: no restating the Key takeaways, no listing what the article covered. Land the judgment the article earned — what the reader should do now, what changes if they do it, the trade-off worth remembering — in 2–4 short paragraphs. It must end with a CTA sentence carrying an inline link to `https://pabau.com/book-demo/` with short anchor text ("Book a demo") that names the benefit for this article's reader. The CTA block itself stays in the Pabau section above; the Conclusion's CTA is the inline text link.

The Continue your research block (`gutenberg-custom-blocks/expert-picks`) sits directly after the Conclusion, before the FAQ heading, with no wrapper H2 — delete any leftover "Expert picks…" heading above it. Which articles it links to is governed by `3-links.md`; the markup and the 5-item ceiling are in `WordPress-blocks.md`.

In listicles, every provider review ENDS with a pricing segment: an H3/H4 `Pricing` heading, a pricing table, then one sentence of context. Use the site's `<!-- wp:gutenberg-custom-blocks/pricing-table {"company":"<Provider>"} /-->` block where the provider is in the site's pricing dataset (verify it renders real rows on the front end after saving), otherwise build a `wp:table` with `Plan` and `Price` columns plus up to two more decision axes, kept consistent across providers. Pricing figures come from the PROVIDER'S OWN WEBSITE ONLY — never Capterra, G2, GetApp, Software Advice, Trustpilot, review round-ups, or another blog; for Pabau, pabau.com only. If a provider publishes no prices, say "Contact sales / no published pricing" in the table and explain it below. This is in addition to the comparison table that follows the intro.

Fix all improperly formatted HTML.

Always check if the FAQ block is malformed. If it is, fix the HTML and apply the proper Yoast FAQ schema. (The article-editor's final FAQ pass guarantees the FAQ ends up as a proper Yoast FAQ block regardless, so at minimum leave the FAQ content clean and well-formed here.)

Check for proper capitalization of titles and body text (Titles should be sentence case, except when the title starts with a number (first letter of the first proper word must be capitalized then). Another exception is following a period, colon, semicolon or em-dash.

Optimize the SERP title (meta title) per `Meta-title-best-practices.md`: use a number for listicles, include the current year where the topic is time-sensitive, match the searcher's micro-intent, differentiate from the rest of the SERP, and lead with the pain point being solved. Don't just repeat the H1 verbatim if a stronger SERP title is warranted.

For codes, intro starts with a definition — delete all hedging language that sets up stakes etc (the searcher does not need to know that they're liable if they mess up coding, that's why they're looking this up).
- BAD: Most heart transplant complications fall cleanly into a named category: rejection, failure, infection. When the complication doesn't fit any of those, ICD-10 Code T86.298 is the correct billable code. It covers every post-transplant cardiac complication not elsewhere classified within the T86.2x subcategory, and it's the code that coders most frequently reach for when documentation describes something atypical in a transplant recipient's clinical course.
- GOOD: ICD-10 Code T86.298 is a billable code that covers every post-transplant cardiac complication not elsewhere classified within the T86.2x subcategory. It's the code that coders most frequently reach for when documentation describes something atypical in a transplant recipient's clinical course.

Fix outdated feature references, if any (e.g. Echo AI).

Break up long paragraphs (no more than 4 lines or 60 words).

If you find a sentence that lists three or more long items (as in, entire clauses of three or more words are list items), turn that into a wordpress list block instead of a paragraph.

Shorten long sentences to make them more legible. Split off clauses from longer sentences into their own sentences, rather than separating them with em dashes, colons or semicolons.

Ensure headings have correct hierarchy (H1 > H2 > H3 > H4).

Edit meta description to include an answer to the searcher query, written as if it were an excerpt from the article, mentioning particular observations, or our top choice if it's a listicle (no more than 140 characters long):
- BAD: Explore our guide on ModMed vs DrChrono: Which EHR fits your specialty practice?
- GOOD: ModMed suits specialty practices needing built-in workflows, while DrChrono is better for practices prioritizing flexibility and customization.

Add Yoast keywords to headings.

Add tags and categories manually — use existing ones in WordPress, and apply no more than 4 categories. (Stage 1 no longer flags categories/tags; owning them here is the single source of truth.)

When adding categories, always remove the "Uncategorized" category.

Where applicable, check pricing from ONLY the provider website, not third-party sources.

Note: This is a newly published article or draft that may not yet be indexed by search engines. Fetch the URL directly and review the full article body content. Use a high token limit when fetching because the site has very large navigation menus that consume token space before the article body appears. You have full WordPress access and login via the `wordpress-access` skill (SKILL.md).
