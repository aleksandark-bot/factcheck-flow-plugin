# Required WordPress blocks & article structure

The block contract every Pabau article must satisfy. Reference article (copy its block
formatting exactly): **https://pabau.com/templates/accutite/** (post `151170` — fetch it
with `context=edit` to see the raw markup).

Read this before writing, editing, or QA-ing any article. `/fact` enforces it in the
article-editor's final block pass; `/SEO` must produce it when it writes.

---

## 1. Required document order

Every article, regardless of type:

```
H1 (post title)
Key takeaways block                 ← required, always first body element
[Download box]                      ← TEMPLATE ARTICLES ONLY (has its own built-in H2)
Intro paragraphs                    ← required, no heading of its own
H2 … body sections                  ← the article itself
H2 <Pabau-for-this-purpose section> ← required; contains the Pabau CTA block
H2 Conclusion                       ← required, exactly this word, concludes + links book-demo
Continue your research block        ← required (expert-picks); no wrapper H2 of its own
H2 Frequently asked questions
Yoast FAQ block
```

Notes on order:
- Schema JSON-LD in a `wp:html` block may sit above Key takeaways — leave it there.
- `pro-tip` blocks may appear anywhere in the body; they are optional.
- Images may appear anywhere in the body; every one of them needs a caption (section 10).
- The **Pabau section** must come *before* Conclusion. It may be preceded by other body
  sections; nothing may sit between Conclusion and the Continue your research block
  except the conclusion's own paragraphs.
- Never place a `<h2>`/`<h3>` above the Key takeaways or Continue your research blocks —
  both render their own heading, so a wrapper heading ships a duplicate title.

---

## 2. Key takeaways block

Capitalization is **"Key takeaways"** — capital K, everything else lowercase. The block
hardcodes "Key Takeaways" when no title is passed, so the `title` attribute is
**mandatory**; without it the page renders the wrong casing.

```
<!-- wp:gutenberg-custom-blocks/key-takeaways {"title":"Key takeaways","items":[{"text":"Takeaway one, written as a full sentence in sentence case."},{"text":"Takeaway two, same treatment."}]} /-->
```

- Self-closing (`/-->`), one `items` entry per takeaway, JSON must be valid (escape `"`).
- 4–5 takeaways is the norm; each is a full sentence in **sentence case** (capitalize only
  the first word and genuine proper nouns — Pabau, ICD-10, HIPAA, CQC).
- Never a plain heading + `<ul>`, never a pasted rendered `<div id="key_takeaways">`.
- An existing block that is otherwise correct but missing `"title":"Key takeaways"` gets
  the attribute added — that alone is a fix worth making.

---

## 3. Download box — template articles only

Sits directly below Key takeaways and above the intro. Raw `wp:html`, with a built-in H2
(so no separate heading block).

The example below is the live AccuTite box — **the wrapper is fixed, the content is not.**
Reuse the markup and styling exactly; write the H2, the description, and the `href` fresh
for each article. Never carry another article's heading text, description, or PDF URL into
a new download box.

```
<!-- wp:html -->
<div style="background: linear-gradient(135deg, #E2F2FD 0%, #DFE3FD 100%); border-radius: 16px; padding: 40px; margin: 32px 0;">
<h2 style="margin: 0 0 12px 0; font-size: 22px; color: #121d36;">Download your free AccuTite aftercare instructions template</h2>
<p style="margin: 0 0 20px 0; color: #444; font-size: 15px;">A comprehensive post-procedure care guide covering activity restrictions, wound care protocols, pain management, recovery timelines, and warning signs that require medical attention. Ready to distribute to patients immediately after their AccuTite treatment.</p>
<a style="display: inline-block; background: #037CD2; color: #fff; padding: 14px 28px; border-radius: 8px; text-decoration: none; font-weight: 600; font-size: 15px;" href="https://cdn.pabau.com/cdn/attachments/pulse/content-engine/templates/accutite/accutite.pdf" target="_blank" rel="noopener">Download template</a>
</div>
<!-- /wp:html -->
```

Rules:
- **Fixed (copy byte-for-byte):** the `wp:html` wrapper, the gradient, border radius,
  padding and margins, the `<h2>`/`<p>`/`<a>` inline styles, the `#037CD2` button, the
  `target="_blank" rel="noopener"`, and the `Download template` button label. This is the
  site's download box, not a design decision — don't restyle it, don't rename the button.
- **Written per article:** the H2 text, the description, and the download `href`. Every
  template has its own file and its own wording; nothing article-specific is ever carried
  over from the example or from another post.
- H2 wording: "Download your free <template name>", grammatical, not exact-match keyword
  stuffing ("Download your free doctor's note for work", not "Download your free doctors
  note for work template free").
- The description is 1–2 sentences naming what is actually inside THIS file — the sections,
  fields, or guidance a reader gets when they open it. Never a generic blurb, and never the
  neighbouring article's description with the template name swapped.
- **Download URL:** reuse the article's existing PDF URL if one is already present
  anywhere in the post or its schema. If there is none, use the site pattern
  `https://cdn.pabau.com/cdn/attachments/pulse/content-engine/templates/<slug>/<slug>.pdf`
  and **verify it returns HTTP 200 before shipping** (`curl -sI -o /dev/null -w '%{http_code}'`).
  Never invent or guess a URL that 404s; if no working file exists, keep the box but report
  the missing asset rather than shipping a dead download.

---

## 4. Pabau CTA block (`book-demo`)

The Pabau CTA. Self-closing custom block; renders the Pabau logo, heading, description, a
**Book a demo** button pointing at `/book-demo/`, and a dashboard image.

```
<!-- wp:gutenberg-custom-blocks/book-demo {"heading":"Automate aftercare delivery and compliance documentation","description":"Pabau's digital forms and compliance tools streamline AccuTite aftercare delivery, automate follow-up reminders, and archive patient education records. This reduces missing documentation and supports optimal patient outcomes.","imageAlt":"Pabau clinic management dashboard"} /-->
```

- The three attributes above (`heading`, `description`, `imageAlt`) are the canonical
  minimum and what the site uses on most articles. The longer form
  (`logoUrl`, `logoAlt`, `demoButtonText`, `demoButtonUrl`, `imageUrl`) is also valid —
  if you use it, set `demoButtonUrl` to `/book-demo/`.
- `heading` names the outcome for *this* article's job (max ~8 words, sentence case).
  `description` is 1–2 sentences tying Pabau's actual capability to the article's purpose —
  lead with the outcome, obey the About-Pabau naming rules, and never invent features.
- One CTA block per article is the norm. It belongs in the required Pabau section (§5);
  a second `book-demo` mid-article is acceptable only in long code/reference articles that
  already carry one, and never two in a row.

---

## 5. Required Pabau section (immediately before Conclusion)

Every article carries an H2 section that promotes Pabau **for that article's specific
purpose** and contains the Pabau CTA block. Not a generic advert — it explains how Pabau
does the job the article is about.

```
<!-- wp:heading -->
<h2 class="wp-block-heading">How Pabau automates aftercare delivery and documentation</h2>
<!-- /wp:heading -->

<!-- wp:paragraph -->
<p>…2–4 paragraphs on the specific workflow: what the practice does today, what Pabau
does instead, and the outcome. Introduce Pabau on first mention if it is the first time
the article names it.</p>
<!-- /wp:paragraph -->

<!-- wp:gutenberg-custom-blocks/book-demo {"heading":"…","description":"…","imageAlt":"Pabau clinic management dashboard"} /-->
```

- Heading is topic-specific ("How Pabau supports exercise monitoring and documentation",
  "How claims management software reduces errors for CPT code 00450") — never "Why choose
  Pabau" or "About Pabau".
- Tie it to the article's job: template articles → distributing/storing the form and
  chasing acknowledgment; code articles → claim accuracy, documentation, denial
  prevention; listicles → why Pabau fits the reader's use case; guides → the workflow the
  guide describes.
- Obey the Pabau non-negotiables (introduce on first mention, qualify product names,
  never "Pabau Connect", no free trial, no feature gating, no undermining the core
  product with Plus add-ons).
- If the article already has a Pabau section elsewhere in the body, move/rework it into
  this slot rather than writing a second one.

---

## 6. Conclusion (required, exactly "Conclusion")

```
<!-- wp:heading -->
<h2 class="wp-block-heading">Conclusion</h2>
<!-- /wp:heading -->
```

- The heading text is the single word **Conclusion**. Replace any variant — "The bottom
  line", "The bottom line on X", "Final thoughts", "Wrapping up", "Key points",
  "Getting started with…", or a topic-specific sign-off — with `Conclusion`.
- It must **conclude**, not summarize. No restating the takeaways or listing what the
  article covered. Land the judgment the article earned: what the reader should now do,
  what changes if they do it, and the trade-off worth remembering. 2–4 short paragraphs.
- It must end with a Pabau CTA sentence containing an inline link to the book-demo URL:

```
<!-- wp:paragraph -->
<p>…closing judgment. <a href="https://pabau.com/book-demo/">Book a demo</a> to see how Pabau streamlines aftercare delivery and compliance documentation for aesthetic practices.</p>
<!-- /wp:paragraph -->
```

  Anchor text is short ("Book a demo"), the link is internal (same tab, no `nofollow`),
  and the sentence names the benefit for this article's reader. `https://pabau.com/book-demo/`
  and `/book-demo/` are both acceptable hrefs; do not link a tracking or campaign URL.
- The `book-demo` CTA block does **not** go inside the Conclusion — it lives in the Pabau
  section above it. The Conclusion's CTA is the inline text link.

---

## 7. Continue your research block (`expert-picks`)

The box of further-reading links. It renders its own "Continue your research" heading, so
it needs **no wrapper H2**. Placed directly after the Conclusion section, before the FAQ
heading.

```
<!-- wp:gutenberg-custom-blocks/expert-picks {"items":[{"text":"\u003cstrong\u003eNeed to set clear treatment expectations?\u003c/strong\u003e \u003ca href=\u0022https://pabau.com/blog/performing-consultations-that-convert/\u0022\u003ePerforming consultations that convert\u003c/a\u003e provides a framework for structuring pre-procedure conversations that build patient confidence."}]} /-->
```

- Self-closing custom block. Inline HTML inside the JSON is **unicode-escaped** the way
  the site stores it (285 of 288 live articles do this, and it is what the block editor
  writes back): `\u003c` and `\u003e` for the tag brackets, `\u0022` for attribute quotes, `\u0026`
  for an ampersand. Validate the JSON before saving — a broken attribute string silently
  kills the block.
- Item shape: a bold hook question (`strong` tag), then the link, then one clause on what
  the reader gets. Anchor text names the article.
- **Max 5 items.** Internal links, same tab, no `nofollow`. Every item is a real, working
  link to a real article — no "list item #1", no bare "list item", no `#` hrefs, no empty
  entries. If nothing genuine remains after cleanup, delete the block entirely.
- Target selection (orphan/near-orphan pages, under 5 inbound links) is governed by
  `3-links.md` — that file owns which articles go in; this file owns the markup.
- If the article has a leftover `<h2>Expert picks…</h2>` above the block, delete the
  heading (the block already renders "Continue your research").

---

## 8. FAQ (Yoast block)

`<!-- wp:yoast/faq-block --> … <!-- /wp:yoast/faq-block -->` under an H2 "Frequently asked
questions", with the `questions` attribute carrying `question` / `answer` /
`jsonQuestion` / `jsonAnswer` per pair so Yoast emits the FAQPage schema. Never a
hand-built `application/ld+json` FAQ alongside it. Full conversion rules live in the
article-editor's block pass.

---

## 9. Listicles — pricing segment per provider

Every provider review in a listicle **ends with a pricing segment**: an H3/H4 `Pricing`
heading, a pricing table, then one sentence of context (what the tiers mean, or that the
vendor doesn't publish prices). The pricing segment closes the provider's review — it
comes after the shines/falls-short material, before the next provider.

**Pricing data is gathered from the provider's own website only** — their pricing page,
their published plan sheet. Never Capterra, G2, GetApp, Software Advice, Trustpilot,
review round-ups, or another blog. For Pabau, use pabau.com only. If the provider does
not publish prices, that *is* the finding — say "Contact sales / no published pricing"
in the table and explain it in the sentence below. Never carry a number you cannot trace
to the vendor's own site, and never leave a stale price in place because it was already
there.

Two acceptable table forms:

**a) The site's pricing-table block** (preferred when the provider is in the site's
pricing dataset — the block pulls maintained figures):

```
<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Pricing</h3>
<!-- /wp:heading -->

<!-- wp:gutenberg-custom-blocks/pricing-table {"company":"Nextech"} /-->
```

Use the provider's exact name as the site stores it (`Pabau`, `SimplePractice`, `Nextech`,
`ModMed EMR`, `Tebra (formerly Kareo)`, `Carepatron`). After saving, load the front end and
confirm the table rendered with real rows — if it comes back empty, that company isn't in
the dataset, so use form (b) instead.

**b) A standard table block** built from the vendor's pricing page:

```
<!-- wp:heading {"level":3} -->
<h3 class="wp-block-heading">Pricing</h3>
<!-- /wp:heading -->

<!-- wp:table -->
<figure class="wp-block-table"><table class="has-fixed-layout"><thead><tr><th>Plan</th><th>Price</th><th>Users</th><th>Key inclusions</th></tr></thead><tbody><tr><td><b>Starter</b></td><td>$62 / month</td><td>1</td><td>Full feature set</td></tr><tr><td><b>Enterprise</b></td><td>Custom quote</td><td>15+ users</td><td>Dedicated onboarding + full feature set</td></tr></tbody></table></figure>
<!-- /wp:table -->

<!-- wp:paragraph -->
<p>You can see the full breakdown on <a href="https://pabau.com/pricing/">Pabau's pricing page</a>.</p>
<!-- /wp:paragraph -->
```

Columns: `Plan` and `Price` are mandatory; add up to two more axes that actually decide the
purchase (users, patient/client limits, key inclusions). Keep the columns consistent across
every provider in the same listicle. Heading level matches the article's provider-review
hierarchy (H3 under H2 provider headings, H4 under H3s).

This is separate from the article's top-of-page comparison table (the skim-reader's ranked
shortlist right after the intro) — a listicle needs both.

---

## 10. Images — every image carries a caption

**Every image in the body must have a caption.** An image block without a `<figcaption>` is
an incomplete block: a captionless image gets a caption written for it, never left bare.
(Images may sit anywhere in the body; the caption requirement is what's fixed, not the
placement.)

Every caption:

- **Is a full sentence and ends with a period.** Not a label, not a fragment, not a
  colon-prefixed title. "Pabau's calendar view" is a caption that failed; write the sentence
  that says what the reader is looking at and why it matters here.
- **Is italic, in real markup** — wrap the caption text in `<em>`. Never use asterisks:
  `*Ranges follow StatPearls.*` ships a literal `*` to the front end (this is live on the
  site today), so when auditing an existing caption, strip stray leading/trailing `*` and
  wrap the text properly.
- Is sentence case, US English, in the article's voice. Inline links inside a caption are fine.
- Adds something. It doesn't restate the alt text or echo the heading above the image.

**Pabau feature screenshots carry one extra requirement:** the caption must say how that
feature helps the reader do the specific thing *this article* is about. Name the feature,
name the job it does for this article's purpose. Generic product praise doesn't qualify, and
neither does a bare feature label.

- BAD: `<em>Pabau's stock inventory feature.</em>` — a label, says nothing.
- BAD: `<em>Pabau is a powerful all-in-one platform for med spas.</em>` — generic, and not
  tied to what the article is helping the reader do.
- GOOD: `<em>Pabau's stock tracking logs every unit of Botox against the treatment note, so
  your face-mapping records and your inventory stay in step without a second spreadsheet.</em>`

Alt text is still required and stays separate: alt describes the image for screen readers and
search engines, the caption speaks to the reader. Don't paste one into the other.

Markup — WordPress core image block; the site renders captions with the `wp-element-caption`
class:

```
<!-- wp:image {"id":<media id>,"sizeSlug":"large"} -->
<figure class="wp-block-image size-large"><img src="<source_url>" alt="<descriptive alt>" class="wp-image-<media id>"/><figcaption class="wp-element-caption"><em>Full-sentence caption that ends with a period.</em></figcaption></figure>
<!-- /wp:image -->
```

The `id` attribute and `wp-image-<id>` class are present for media-library images and omitted
when the `src` is an external URL. The `<figcaption>` is required either way.

---

## 11. Quick QA checklist

- [ ] Key takeaways block present, first body element, `"title":"Key takeaways"` set, items in sentence case
- [ ] Template article: download box below Key takeaways, above intro, built-in H2, download URL returns 200
- [ ] Intro exists and follows the Key takeaways (and download box, if any)
- [ ] Pabau section immediately before Conclusion, topic-specific H2, contains the `book-demo` CTA block
- [ ] H2 `Conclusion` present (exact word), concludes rather than summarizes, ends with an inline book-demo CTA link
- [ ] Continue your research (`expert-picks`) block after the Conclusion, ≤5 real working links, no wrapper H2
- [ ] FAQ is a Yoast FAQ block with schema, under an H2
- [ ] Listicle: comparison table after intro; every provider review ends with a `Pricing` heading + pricing table, all figures from the provider's own site
- [ ] Every image has a `<figcaption>`: full sentence, ends in a period, wrapped in `<em>`, no stray `*`; Pabau-feature screenshots tie the feature to this article's purpose; alt text present and not duplicated into the caption
- [ ] No duplicate headings above self-heading blocks; no placeholder items anywhere
