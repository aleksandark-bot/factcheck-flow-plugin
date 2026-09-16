# Required WordPress blocks & article structure

The block contract every Pabau article must satisfy. Reference article (copy its block
formatting exactly): **https://pabau.com/templates/accutite/** (post `151170` — fetch it
with `context=edit` to see the raw markup).

Read this before writing, editing, or QA-ing any article. `/fact` enforces it in the
article-editor's final block pass; `/SEO` must produce it when it writes.

---

## 1. Required document order

Most articles:

```
H1 (post title)
Intro paragraphs                    ← required, no heading of its own; main keyword in the FIRST sentence; answers the query in full
Key takeaways block                 ← required, directly below the intro — nothing between them
[YouTube embed]                     ← IF the article has a video: the last block before the first body heading
H2 … body sections                  ← the article itself
H2 <Pabau-for-this-purpose section> ← required; contains the Pabau CTA block
H2 Conclusion                       ← required, exactly this word, concludes + links book-demo
Continue your research block        ← required (expert-picks); no wrapper H2 of its own
H2 Frequently asked questions
Yoast FAQ block
```

**Template articles (`/templates/`) only — the download box sits between the intro and Key
takeaways, not after it:**

```
H1 (post title)
Intro paragraphs
Download box                        ← has its own built-in H2
Key takeaways block                 ← directly below the download box
[YouTube embed]                     ← IF the article has a video: the last block before the first body heading
H2 … body sections
H2 <Pabau-for-this-purpose section>
H2 Conclusion
Continue your research block
H2 Frequently asked questions
Yoast FAQ block
```

**Templated code pages (`/diagnostic-codes/` and `/procedure-codes/` — one template serves
both routes) only — the whole top area is rendered by the page template out of post meta, so the
body starts at Key takeaways:**

```
H1 + Code Definition + Related Information + Pabau CTA + trust card   ← ALL template-rendered from post meta; NOT in post_content
Key takeaways block                 ← the FIRST block in the body; there is no intro above it
[YouTube embed]                     ← IF the article has a video: directly beneath Key takeaways
H2 <opening section>                ← body starts here
H2 … body sections
H2 <Pabau-for-this-purpose section>
H2 Conclusion
Continue your research block
H2 Frequently asked questions
Yoast FAQ block
```

Detect the page and check its `pdc_*` fields per **section 13** — a code page that is *not*
templated keeps the "Most articles" shape above, intro first.

Notes on order:
- **The intro comes first.** On a non-template article, Key takeaways sits directly below it
  with nothing in between — no image, no spacer, no video, no comparison table, no pro-tip. On
  a **template article**, the download box sits in that seam instead, and Key takeaways follows
  the download box. The reader gets the answer in prose, then (on a template) the download,
  then the summary.
- **On a templated code page the intro is not in the body at all.** It lives in the
  `pdc_definition` meta field, which the template renders as *Code Definition* above the
  body, so Key takeaways is the first block in `post_content` and the intro/takeaways seam
  rule has nothing to govern. Never write a body intro on such a page. Detection, the field
  contract, and the four page states are in section 13.
- **The intro must answer the keyword's main query completely**, and the main keyword must
  appear in the article's **first sentence** — the rules for both are in `core-rules.md`
  ("Answer-first"); the listicle takeaway form is section 2a below.
- Schema JSON-LD in a `wp:html` block may sit above the intro — leave it there.
- `pro-tip` blocks may appear anywhere in the body; they are optional.
- Images may appear anywhere in the body; every one of them needs a caption (section 10).
- **Every article carries at least one original visual we built** — a rendered image, or one
  CSS-only interactive `pv-viz` block. It sits in the body section whose point it makes,
  never inside Key takeaways, the download box, the Pabau section, the Conclusion, the FAQ,
  or Continue your research. What to build and how is `Visuals.md`; a rendered one is an
  ordinary image block and must satisfy section 10 here.
- **In a listicle, every provider review opens with a provider card** directly below the
  provider's heading (section 9a) and closes with a pricing segment (section 9).
- **A YouTube video belongs at the end of the opening run, never inside the intro prose** —
  the last block before the first body heading, after Key takeaways (and, on a template
  article, after the download box that now sits ahead of Key takeaways). Most articles have
  one and about half have it in the wrong place; section 11 is the rule and the fix.
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

**Placement: directly below the intro** on most articles — the block is no longer the first
body element; the intro paragraphs come first, and Key takeaways follows the last of them with
nothing in between. **On a template article, Key takeaways sits directly below the download
box instead** (section 3), so the seam after the intro belongs to the download box, not to Key
takeaways. An article whose Key takeaways sits above the intro, or above the download box on a
template article, gets the block moved down.

**On a templated code page Key takeaways is the first body element** — what it used to be
everywhere — because the intro sits in the `pdc_definition` meta field and not in
`post_content` (section 13). Leave it at the top and never write an intro above it.

- Self-closing (`/-->`), one `items` entry per takeaway, JSON must be valid (escape `"`).
- 4–5 takeaways is the norm; each is a full sentence in **sentence case** (capitalize only
  the first word and genuine proper nouns — Pabau, ICD-10, HIPAA, CQC). On a **listicle** the
  items are the ranked provider list instead, one per provider — section 2a.
- Never a plain heading + `<ul>`, never a pasted rendered `<div id="key_takeaways">`.
- An existing block that is otherwise correct but missing `"title":"Key takeaways"` gets
  the attribute added — that alone is a fix worth making.

### 2a. Listicles — Key takeaways IS the ranked list

On a listicle, Key takeaways is not a set of lessons. It is the ranked shortlist of the
providers the article chose, in the article's own order, one `items` entry per provider:

```
#. [Provider] — Short reason why they're on the list.
```

- Written literally as `1. Pabau — …`, `2. Jane App — …`: the number and the period are part
  of the item text, because the block renders an unordered list and the numbering has to come
  from the copy.
- One entry per provider reviewed, in the same order as the body sections. No provider in the
  list that the article doesn't review, and no reviewed provider missing from the list.
- The reason is one short clause — who this pick is for, or the one thing it does best — under
  the 25-word sentence ceiling and in sentence case after the provider name.
- The em dash separates the provider from the reason. Keep the provider name bare: no link, no
  rank label ("Best overall"), no price.
- Nothing else goes in the block: no "what to look for" takeaway, no methodology note. The
  number of items equals the number of providers.

```
<!-- wp:gutenberg-custom-blocks/key-takeaways {"title":"Key takeaways","items":[{"text":"1. Pabau — best all-in-one option for practices that want booking, charting and billing in one system."},{"text":"2. Jane App — strongest fit for small multi-disciplinary practices that bill insurance."},{"text":"3. Cliniko — the cheapest way for a solo practitioner to get online booking running."}]} /-->
```

The comparison table still follows the block, and the per-provider sections follow the table.

---

## 3. Download box — template articles only

Sits directly below the intro, before the Key takeaways block (section 1). Raw `wp:html`,
with a built-in H2 (so no separate heading block).

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

The FAQ sits under an H2 "Frequently asked questions" and must be a real Yoast FAQ block —
that block is what emits the FAQPage schema, so "proper FAQ schema attached" means exactly
"it is a `wp:yoast/faq-block`". No hand-built `application/ld+json` FAQ alongside it.

One `.schema-faq-section` per Q&A pair, each with a unique `id`:

```
<!-- wp:yoast/faq-block -->
<div class="schema-faq wp-block-yoast-faq-block">
<div class="schema-faq-section" id="faq-question-1700000000001"><strong class="schema-faq-question">Question one?</strong> <p class="schema-faq-answer">Answer one.</p></div>
<div class="schema-faq-section" id="faq-question-1700000000002"><strong class="schema-faq-question">Question two?</strong> <p class="schema-faq-answer">Answer two.</p></div>
</div>
<!-- /wp:yoast/faq-block -->
```

Yoast versions differ in how the block stores its attributes, so before hand-building one,
fetch another published article on the same site that already has a working Yoast FAQ block
(`context=edit`) and copy its exact delimiter and attribute format. Matching the site's real
output beats a hand-built guess.

Conversion rules:

- **Already a proper Yoast block** → leave it exactly as-is.
- **Plain HTML, `<h3>`/`<strong>` pairs, an accordion, a raw `<div>`, or `wp:heading` +
  `wp:paragraph` pairs** → convert to the block above. Keep any introductory FAQ H2 heading
  above the block; the questions and answers go inside it. **Preserve every question's and
  answer's exact wording**, plus any inline links or formatting inside the answers — this is
  a wrapper change, never a rewrite. If a separate hand-built FAQ `application/ld+json`
  script exists in a `wp:html` block, remove it once the Yoast block is in place, so the page
  doesn't carry duplicate FAQ schema.
- **No FAQ section at all** → this contract does not invent one. A genuinely missing FAQ is
  written in the editorial pass (`2-editorial.md`), only where the article type calls for it.

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

**Read their pricing page, never link to it.** The sourcing rule above is about where the
numbers come from, not about where the article points. A competitor's pricing page is never
a link destination: if the context sentence names their site, link their **homepage**
(nofollow, new tab) or nothing at all. Only `pabau.com/pricing/` may be linked as a pricing
page, as in the example below.

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

## 9a. Listicles — provider card directly below each provider heading

Every provider review in a listicle **opens with a provider card**: the `pabau/provider-card`
block placed **directly below the provider's H2** (or H3, if the article's provider hierarchy
runs deeper), before any prose of the review. One card per provider, no exceptions — the
pricing segment (§9) closes the review, the card opens it. A standard 800 × 35 `wp:spacer`
follows the card, then the review's first paragraph.

The block is server-rendered by the "Pabau Provider Card" plugin and self-closing; its CSS
ships with the plugin, so **no per-article `<style>` block is needed** (and none should be
added). Real example, live on post 163682:

```
<!-- wp:pabau/provider-card {"rating":"4.5","bottomLine":"Pabau Scribe writes the note into the client record that already holds the appointment.","who":"Med spas and aesthetics clinics\nDermatology, physical therapy and wellness practices\nMulti-location groups standardizing documentation\nOwners who want HIPAA and GDPR in one platform","price":"From $62/month","siteUrl":"https://pabau.com/pricing/","siteText":"pabau.com/pricing","works":"Notes land in the client record, with no export step\nTuned for aesthetics, wellness and allied health\nEvery subscription includes every feature","doesnt":"Not an add-on for Epic or Oracle Health\nNo standalone scribe plan, you adopt the platform","topPick":true,"pickLabel":"Top pick","priceNote":"one user, full platform"} /-->
```

Attributes (all strings unless noted):

- `rating` — e.g. `"4.5"`; the stars auto-fill from it. Must match any rating stated in the
  review copy.
- `topPick` (boolean) + `pickLabel` — the pill in the card head. `topPick: true` with
  `"pickLabel":"Top pick"` on the #1 provider only; other providers may carry a different
  label (e.g. "Our pick for X") or omit both.
- `bottomLine` — one-sentence verdict, article voice, sentence ceiling applies.
- `who`, `works`, `doesnt` — newline-separated lists (`\n` inside the JSON string): 3–4
  "Who it's for" fits, then What works / What doesn't. Fragments are fine here; no periods.
- `price` + `priceNote` — headline price plus a short qualifier ("one user, full platform").
  §9's sourcing rule applies in full: the figure comes from the provider's own website only.
- `siteUrl` + `siteText` — the Website link. For competitors this is their **homepage**
  (never their pricing page — §9); for Pabau, `https://pabau.com/pricing/` is allowed.

Rules:

- **No logos** on the card, ever.
- Facts on the card must agree with the review and the pricing segment below it — one price,
  one rating, one verdict.
- **Legacy raw-HTML cards get converted.** An older listicle may carry the card as a raw
  `wp:html` `pb-card` block plus a per-article `<style>` block before the first provider
  heading. Rebuild each as a `pabau/provider-card` block (carry the content over, drop
  nothing) and remove the per-article `<style>` block once no raw card remains.
- After saving, confirm the cards rendered:
  `curl -s "$URL" | grep -o 'class="pb-card' | wc -l` — one per provider.

---

## 10. Images — every image carries a caption

**Every image in the body must have a caption.** An image block without a `<figcaption>` is
an incomplete block: a captionless image gets a caption written for it, never left bare.
(Images may sit anywhere in the body; the caption requirement is what's fixed, not the
placement.)

This applies to a visual we generated exactly as it does to a photo or a screenshot — see
`Visuals.md` for what to build and how to render it, and §6 there for the extra rule that a
data visual's caption also names its source. An interactive `pv-viz` block is not an image:
it carries its own `.pv-note` line instead and takes no `<figcaption>`.

Every caption:

- **Is a full sentence and ends with a period.** Not a label, not a fragment, not a
  colon-prefixed title. "Pabau's calendar view" is a caption that failed; write the sentence
  that says what the reader is looking at and why it matters here. The article's sentence
  ceiling applies — 25 words, 30 only where a split would break the meaning.
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
  your records and inventory stay in step without a second spreadsheet.</em>` (24 words — the
  25-word sentence ceiling applies to captions too)

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

**Every image is followed by a spacer block (800 × 35).** Immediately after the closing
`<!-- /wp:image -->`, before the next paragraph or heading, add:

```
<!-- wp:spacer {"width":"800px","height":"35px"} -->
<div style="height:35px;width:800px" aria-hidden="true" class="wp-block-spacer"></div>
<!-- /wp:spacer -->
```

One spacer per image, never two in a row. If a spacer already follows the image, leave it —
only correct the dimensions if they differ from 800 × 35.

---

## 11. YouTube videos — end of the opening run, never mid-prose

Most articles already carry a `wp:embed` YouTube block, and roughly half of them have it in
the wrong place. The video is optional; its **placement is not**.

**The one legal slot: the last block before the first body heading** — after everything the
opening run puts ahead of it: the intro wherever the body has one, the download box on a
template article, and the Key takeaways block always. Three article shapes, one rule:

```
Most articles             Old-shape code article    Templated code page (§13)
──────────────────────    ──────────────────────    ─────────────────────────
Intro paragraph           H2 <opening section>      Key takeaways
Intro paragraph           Paragraph                 YouTube embed         ←
Intro paragraph           Paragraph                 H2 <opening section>
Key takeaways             Paragraph                 Paragraph
YouTube embed        ←    Key takeaways
H2 <first body section>   YouTube embed        ←
                          H2 <next section>
```

The middle column is the **old, non-templated** code-article shape: the article opens on an
H2, the prose runs under it, and Key takeaways follows that prose. It still applies to every
code page that is not templated. On a **templated** code page (section 13) there is no body
intro: Key takeaways is the first block, the embed sits directly beneath it, and the first
body H2 follows the embed.

In every shape the reader finishes the opening run — the intro where there is one, then the
takeaways — meets the player, then moves on to the next heading. Nothing else goes between
the embed and that heading.

**A video must never break up a run of prose.** An embed between two paragraphs splits an
argument in half: the reader hits a player mid-thought, and the paragraph after it reads like
the start of something new. The three misplacements that are live on the site today, all of
which get fixed by moving the block:

- **Between intro paragraphs** (the most common) — the intro continues below the player.
  Move the embed down past every remaining intro paragraph.
- **Mid body section** — the embed sits between two paragraphs under a later H2. Move it up to
  the end of the opening run.
- **Between the intro and Key takeaways** — on an article that has a body intro, the only thing
  allowed in that seam is a template article's download box (section 1), so an embed there is a
  misplacement. Move it below the Key takeaways block. A templated code page has no body intro
  and therefore no such seam (section 13).
- **Above the intro** (including the old layout's slot between Key takeaways and the intro) —
  the player lands before the article has said anything. Move it down past the whole intro and
  past Key takeaways.

And never inside the Pabau section, the Conclusion, or the FAQ; never after the Conclusion or
between the Conclusion and the Continue your research block.

When you move one, **move the block byte-for-byte** — do not rewrite the markup or re-embed
the URL. Then clean up after it: if a paragraph was split around the video, rejoin the halves,
and delete any "watch the video below" sentence that no longer points at anything. Never
rewrite surrounding copy to justify the old position, and never add a video to an article that
doesn't have one.

Markup — WordPress core embed block, as it exists on the site:

```
<!-- wp:embed {"url":"https://www.youtube.com/watch?v=<VIDEO_ID>","type":"video","providerNameSlug":"youtube","responsive":true,"className":"wp-embed-aspect-16-9 wp-has-aspect-ratio"} -->
<figure class="wp-block-embed is-type-video is-provider-youtube wp-block-embed-youtube wp-embed-aspect-16-9 wp-has-aspect-ratio">
<div class="wp-block-embed__wrapper">
https://www.youtube.com/watch?v=<VIDEO_ID>
</div>
</figure>
<!-- /wp:embed -->
```

- Both forms are live and both render: some blocks carry the `"className"` attribute, some
  don't. **Leave whichever form the article already has** — this is not something to normalize.
- The URL is the plain `youtube.com/watch?v=` form on its own line inside the wrapper. Never
  hand-roll an `<iframe>` into a `wp:html` block; it loses the responsive wrapper.
- **No spacer after an embed.** Unlike images (section 10), the embed block carries its own
  margins and no article spaces one manually. Don't add one.
- A `<figcaption>` is optional on a video, unlike images, which always need one. If one is
  there, it follows the section 10 caption contract: full sentence, period, `<em>`.
- The video must be relevant to the article's topic and still playable. A dead or private
  video is a broken block: remove it rather than move it.

To find every embed in a body you hold, search for `<!-- wp:embed` — WordPress's REST `search`
parameter does **not** match block markup, so searching the API for "youtube" returns nothing
even on articles that have one.

---

## 12. Quick QA checklist

- [ ] Intro is the first body element (except a templated code page — section 13), its FIRST sentence carries the main keyword, and it answers the keyword's main query completely (a listicle names the top pick; an informational article defines the subject in paragraph one)
- [ ] Key takeaways block sits directly below the intro with nothing in the seam (or, on a template article, directly below the download box; or, on a templated code page, FIRST in the body with no intro above it — section 13), `"title":"Key takeaways"` set, items in sentence case
- [ ] Listicle: Key takeaways is the ranked provider list, `#. [Provider] — reason` per item, one item per provider reviewed, same order as the body (section 2a)
- [ ] Template article: download box directly below the intro, built-in H2, download URL returns 200, with Key takeaways directly below the download box
- [ ] Templated code page (section 13): no intro in the body, Key takeaways is the FIRST block, and the video — if there is one — sits directly beneath it
- [ ] Templated code page: all EIGHT always-required `pdc_*` fields present and correct (`pdc_code_type`, `pdc_code`, `pdc_descriptor`, `pdc_h1_descriptor`, `pdc_definition`, `pdc_chapter`, `pdc_category`, `pdc_group`); the two conditional fields (`pdc_billable`, `pdc_specific`) set to `yes`/`no` on an ICD-10-CM page and left empty where the code system has no billable/specific distinction — empty is correct there, never reported as a gap, and never invented; the five optional fields (`pdc_h1_prefix`, `pdc_also_known`, `pdc_label_1`, `pdc_label_2`, `pdc_label_3`) left empty unless genuinely warranted — never filled in to satisfy a completeness check; nothing blanked or deleted; the `template` value untouched and never sent on an edit
- [ ] Old-shape code page left on the old contract — never migrated; a page with `pdc_*` meta set but `template` empty is `CODE_PAGE_HALF_MIGRATED` (reported, not fixed) on either code route (section 13)
- [ ] Pabau section immediately before Conclusion, topic-specific H2, contains the `book-demo` CTA block
- [ ] H2 `Conclusion` present (exact word), concludes rather than summarizes, ends with an inline book-demo CTA link
- [ ] Continue your research (`expert-picks`) block after the Conclusion, ≤5 real working links, no wrapper H2
- [ ] FAQ is a Yoast FAQ block with schema, under an H2
- [ ] Listicle: comparison table after the Key takeaways block; every provider review ends with a `Pricing` heading + pricing table, all figures from the provider's own site
- [ ] Listicle: a `pabau/provider-card` block directly below each provider's heading, before any prose; no logos, no per-article `<style>` block, card facts match the review
- [ ] Every image has a `<figcaption>`: full sentence, ends in a period, wrapped in `<em>`, no stray `*`; Pabau-feature screenshots tie the feature to this article's purpose; alt text present and not duplicated into the caption
- [ ] Every image is followed by one 800 × 35 `wp:spacer` block
- [ ] Any YouTube embed is the LAST block before the first body heading (after the intro, the download box on a template article, and Key takeaways — or, on a templated code page, directly beneath Key takeaways with no intro above it) — never between paragraphs, never before the intro, never in the seam before Key takeaways, never mid-section; markup unchanged, no spacer added
- [ ] No duplicate headings above self-heading blocks; no placeholder items anywhere

---

## 13. Code pages — the template-rendered top area

On a **templated code page**, the whole area between the H1 and the first H2 is rendered by
a WordPress page template out of post meta. **None of it lives in `post_content`**, so none
of it is visible in the WordPress editor and none of it comes back in `content.raw`. Read
only the body and you miss page-visible, fact-checkable content.

Reference articles — already verified, never fetch them again. Diagnostic:
`https://pabau.com/diagnostic-codes/icd-10-code-s65419a/` (post `221716`), plus
`icd-10-code-s36418d` (`221711`), `icd-10-code-s82122r` (`221757`), `icd-10-code-t24011s`
(`221743`) and `icd-10-code-s62211b` (`221739`). Procedure:
`https://pabau.com/procedure-codes/hcpcs-code-j8650/` (post `220410`).

### What the template renders, in order

1. Badge — e.g. "ICD-10-CM Code"
2. H1 — e.g. "ICD code S65.419A — Unspecified thumb blood vessel laceration"
3. Flag line — "Billable Code • Specific Code" (rendered only when `pdc_billable`/`pdc_specific` are set; absent on J8650)
4. Horizontal rule
5. **Code Definition** — a titled block of 1–2 prose paragraphs. **This is the article's intro now.**
6. **Related Information** — a card of three labelled rows fed by `pdc_chapter` / `pdc_category` / `pdc_group` (labelled Chapter / Category / Group by default on ICD-10-CM, relabelled by `pdc_label_1-3`), a Billable row when `pdc_billable` is set, plus an optional "Code also known as" row
7. **Automate coding with Pabau** — a dark CTA panel with an animated mock of Pabau suggesting the code, and two `/book-demo/` buttons
8. **Why practices choose Pabau** — a four-item trust card plus a "HIPAA compliant • SOC 2 certified • GDPR-compliant • Trusted by 4,000+ clinics worldwide" line
9. Table of contents rail
10. …then `post_content` begins.

**Items 7 and 8 are fixed template boilerplate.** No per-article copy feeds them — the CTA's
mock screen interpolates `pdc_code` and `pdc_h1_descriptor` and nothing else. There is
nothing in them to write, edit, fact-check, or duplicate: never write copy for them, never
edit them, never copy them into the body, and **never count them toward the body's own Pabau
section or CTA requirements**. The body keeps its own Pabau section and `book-demo` CTA even
though the template already renders one above it — that is correct and intended, not a
duplicate to remove.

`post_content` on a templated code page begins:

```
[optional wp:html JSON-LD schema]
wp:gutenberg-custom-blocks/key-takeaways      ← FIRST content block. No intro above it.
wp:embed  (YouTube)                            ← directly beneath Key takeaways
wp:heading (the opening H2)                    ← body starts here
```

The tail of the article is **unchanged**: body H2s → the H2 Pabau section containing the
`book-demo` CTA (§5) → H2 `Conclusion` ending in a `/book-demo/` link (§6) → Continue your
research (§7) → H2 Frequently asked questions → Yoast FAQ block (§8).

### The `pdc_*` meta fields

All are registered, readable at `context=edit`, and writable over REST.

**Eight are ALWAYS REQUIRED, two are CONDITIONAL, five are OPTIONAL.** A templated page must
carry all eight always-required fields; an empty one is a gap to fill from the article. The
two conditional fields are required only on a code system that reports that status. The five
optional fields are **never** "filled in" to satisfy a completeness check — empty is their
normal, correct state.

| Field | Required? | Feeds | Shape / rule |
|---|---|---|---|
| `pdc_code_type` | **required** | the badge | `ICD-10-CM Code`, `CPT Code`, `HCPCS Code`, … |
| `pdc_code` | **required** | H1, CTA mock | the code itself, dotted — `S65.419A` |
| `pdc_descriptor` | **required** | data, not rendered directly | the **official** descriptor, verbatim, including the 7th-character clause — "Laceration of blood vessel of unspecified thumb, initial encounter" |
| `pdc_h1_descriptor` | **required** | H1 after the dash, CTA mock | a short plain-language descriptor — "Unspecified thumb blood vessel laceration". Not the official text. |
| `pdc_h1_prefix` | *optional* | H1 before the code | **Always left empty.** Empty on every live page; the template falls back to "ICD code". Leave it alone in every state, in every command. |
| `pdc_billable` | **conditional** | flag line + Related Information row | `yes` / `no` on an **ICD-10-CM** page, where it is required (every live diagnostic page sets `yes`). **Left empty** where the code system has no billable/specific distinction to report — the live HCPCS page J8650 has it empty, which is correct and never reported as a gap. Empty hides both the flag line under the H1 and the "Billable" row in Related Information. Never invented to make a page look complete. |
| `pdc_specific` | **conditional** | flag line | Same rule as `pdc_billable`: `yes` / `no` and required on an **ICD-10-CM** page, left empty where the code system has no such distinction (J8650 has it empty). Empty hides the flag line. Never invented. |
| `pdc_definition` | **required** | **Code Definition** | plain text, **no HTML and no links**, 1–2 paragraphs separated by `\n\n`, ~40–110 words on live pages |
| `pdc_chapter` | **required** | Related Information row 1 | A generic slot, labelled by `pdc_label_1`. On ICD-10-CM: `<range> <official chapter title>` — "S00-T88 Injury, poisoning and certain other consequences of external causes". On HCPCS J8650: `Level II`. |
| `pdc_category` | **required** | Related Information row 2 | A generic slot, labelled by `pdc_label_2`. On ICD-10-CM: `<code> <official category title>` — "S65 Injury of blood vessels at wrist and hand level". On HCPCS J8650: `J — Drugs administered other than oral method`. |
| `pdc_group` | **required** | Related Information row 3 | A generic slot, labelled by `pdc_label_3`. On ICD-10-CM: `<code> <official group title>` — "S65.419 Laceration of blood vessel of unspecified thumb". On HCPCS J8650: `Deleted, effective 31 December 2025`. |
| `pdc_also_known` | *optional* | optional Related Information row | Written **only** when the authority names a genuine synonym for the code. Empty is the normal, correct state, and the row is hidden when empty. Never invent one. |
| `pdc_label_1` | *optional* | the Related Information row label for `pdc_chapter` | Empty means "use the template's default label for this code type" — that is the normal state. Set it only to override a default that would be wrong for this code. Never blank one that is already set. |
| `pdc_label_2` | *optional* | the row label for `pdc_category` | Same rule: empty = the code-type default; set only to override a wrong default; never blanked. |
| `pdc_label_3` | *optional* | the row label for `pdc_group` | Same rule. J8650 sets it to `Status`, because its `pdc_group` carries "Deleted, effective 31 December 2025" rather than a code group. |

**No optional field is ever filled in to satisfy a completeness check.** An empty
`pdc_h1_prefix`, `pdc_also_known` or `pdc_label_*` is not a gap and is never reported as one.
Neither is an empty `pdc_billable`/`pdc_specific` pair on a code system that reports no such
status — J8650 is the live example.

**The three `pdc_label_*` fields relabel the Related Information rows**, in order:
`pdc_label_1` labels the `pdc_chapter` row, `pdc_label_2` the `pdc_category` row, and
`pdc_label_3` the `pdc_group` row. Empty means "use the template's default label for this code
type", and those defaults are code-type-dependent and already correct for the common cases: an
ICD-10-CM page with all three empty renders **Chapter / Category / Group**, and the HCPCS page
renders **Level** for row 1 with `pdc_label_1` empty. Set one **only** to override a default
that would be wrong for this code — J8650 sets `pdc_label_3` to `Status` because its
`pdc_group` carries "Deleted, effective 31 December 2025" rather than a code group, so "Group"
would have been wrong. Never blank a label that is already set, and never set one to the value
the default would produce anyway.

**`pdc_chapter`, `pdc_category` and `pdc_group` are generic slots**, not literally "the
chapter", "the category" and "the group". On J8650 they carry `Level II`, `J — Drugs
administered other than oral method`, and `Deleted, effective 31 December 2025`. They hold the
three most useful reference facts for that code system, labelled by `pdc_label_*` accordingly.

The live `pdc_definition` formula on the ICD-10-CM pages:

> `<CODE> is the billable ICD-10-CM code for <official descriptor>.` — then one or two
> sentences of scope, then (often) a second paragraph on where the code sits and what
> assignment turns on.

### Detecting a templated code page

```
renders the code top area  ==  post.template == "template-diagnostic-code.php"
                               (states 1 and 2 below — Templated, or Broken)

fully Templated            ==  post.template == "template-diagnostic-code.php"
                               AND all eight always-required pdc_* fields are non-empty
                               AND pdc_billable + pdc_specific set, on an ICD-10-CM page
```

The template — not the meta — decides whether the top area renders. The required fields then
decide whether it renders complete (**Templated**) or with blanks (**Broken**). Both are
handled under the new contract; only the gap-filling differs.

`template` is not returned by WordPress by default. The wordpress-access `_fields=` list
**already includes it** — use that list unmodified. If you build your own `_fields=` and omit
`template`, every check below silently reads as "not templated".

**There is one code template — `template-diagnostic-code.php` — and it serves both code
routes**, `/diagnostic-codes/` and `/procedure-codes/`, ICD, CPT and HCPCS pages alike
(verified on the HCPCS page J8650). The name is awkward on a procedure page. It is still the
correct value there, so never "fix" it to something else. The full list of registered post
templates, read straight out of WordPress's own validation error: `elementor_canvas,
elementor_header_footer, elementor_theme, template-diagnostic-code.php,
wp-templates/p-medical-certificate-generator.php`. Every rule here is keyed on the `template`
value plus meta presence, never on the URL folder.

Roll-out today: nearly every `/diagnostic-codes/` page is templated, while most
`/procedure-codes/` pages you meet are still old shape.

There are **four states**, disjoint and exhaustive, and every code page is in exactly one of
them. They are the same four on both code routes.

| # | `template` | `pdc_*` meta | State | What you do |
|---|---|---|---|---|
| 1 | `template-diagnostic-code.php` | every required field present | **Templated** | The contract: no body intro, Key takeaways first, meta owned and checked. |
| 2 | `template-diagnostic-code.php` | one or more required fields empty | **Broken** | The top area renders with blanks. Handle exactly as Templated, plus fill the empty required fields from the article. |
| 3 | empty | any `pdc_*` set | **Half-migrated** | A defect — the meta is dead and the page renders the old layout. **Change nothing structural**, treat the body as old shape, and report `CODE_PAGE_HALF_MIGRATED`. |
| 4 | empty | none set | **Old shape** | The old contract, unchanged. Never migrated. |

"Required field" in rows 1 and 2 means the eight always-required fields, plus `pdc_billable`
and `pdc_specific` where the code system reports them. An empty conditional pair on a code
system that has no billable/specific distinction does **not** make a page Broken.
`icd-10-code-t86859` is a live example of state 3.

**One further case, not a state.** A page whose `template` is set to something other than
`template-diagnostic-code.php` (`elementor_canvas`, `elementor_header_footer`, `elementor_theme`,
`wp-templates/p-medical-certificate-generator.php`) does not render the code top area at all.
Treat the body as old shape and report the `template` value; do not try to fix it.

**Never migrate an old-shape page yourself.** Do not set `template` on an existing page, do
not invent `pdc_*` values for a page that has none, and do not strip a body intro from a page
that still needs one. Migration is a separate process. This flow
*preserves* the new top area where it exists and *fills gaps* in it — it never creates or
removes it.

**Never delete, blank, or "clean up" a `pdc_*` field or the `template` value.** A blanked
field silently empties a section of the live page that nobody can see in the editor.

### Who checks and writes the meta

The `pdc_*` values are page-visible factual claims, so the **fact-check checks them** against
the official source — CDC/NCHS ICD-10-CM tabular list for ICD, the AMA for CPT, CMS for
HCPCS — exactly as body claims are verified. Report each finding with a `meta:<field>`
location, so the editor knows it is a meta write and not a body edit:

```
AUTO 3. factual | meta:pdc_category | reads "S65 Injury of blood vessels at hand level" → "S65 Injury of blood vessels at wrist and hand level"
```

- A wrong **`pdc_code`** is the grave-error case (`CONFIRM: true`) — the whole page is built on it.
- `pdc_descriptor`, `pdc_chapter`, `pdc_category`, `pdc_group`, `pdc_code_type`, and
  `pdc_billable`/`pdc_specific` where they are set, are ordinary `factual` AUTO findings. An
  empty conditional field is never a finding.
- `pdc_definition` is prose: check its claims like any body prose.
- `pdc_h1_descriptor` and `pdc_also_known` are editorial, not official text — flag them only
  when they contradict the code.

**The editorial pass owns `pdc_definition` and `pdc_h1_descriptor` as prose.** Everything in
`core-rules.md` and the style guide applies to the Code Definition: US English, the AI tells,
paragraph length, and the 25/30-word sentence ceiling. It stays plain text — no HTML, no
links, `\n\n` between paragraphs.

**Answer-first has two homes on a templated code page.** `pdc_definition` **is the intro**:
its first sentence carries the main keyword — the live formula leads with the bare code,
which satisfies it — and the definition answers the query completely on its own. The
**opening H2 section** carries it too, in more depth: the full main keyword and a complete
answer. The overlap between the two is by design. The rule that a code intro starts with a
definition, with no hedging language setting up stakes, now governs `pdc_definition`.

**Writing meta.** The single PUT gains a `meta` object alongside `content` and any
`featured_media`. Send **only the `pdc_*` keys that changed** — WordPress merges registered
meta, so omitted keys are untouched. **Never send `template` on an edit** — `/fact` and
`/SEO` never write it in any state; the only write that sets it is `/generate`'s **create
POST**, now on either code route. After the save, read back
`?context=edit&_fields=meta` and assert each value you sent came back as you sent it; a
silently-dropped meta write is reported, not assumed.

### Body rules on a templated code page

These apply to **states 1 and 2** — Templated and Broken. A Broken page is treated exactly
like a Templated one here; the only extra work is filling its empty required fields. States
3 and 4 keep the old-shape body rules (intro first, then Key takeaways).

- **Never add an intro to the body.** Key takeaways is the first content block, below the
  optional schema `wp:html` and nothing else.
- **Key takeaways position: first.** The "directly below the intro" rule (§2) does not apply
  — there is no body intro for it to sit below.
- **Video: directly beneath Key takeaways**, still the last block before the first body
  heading (§11). Unchanged in effect; it is now the second content block rather than the fourth.
- **A body intro found on a templated page is a defect** — it duplicates the Code Definition.
  Do not delete the prose: fold its substance into the opening H2 section, then move Key
  takeaways to the top. Nothing is lost and nothing is duplicated.
- Everything after the first H2 is unchanged: the original visual (`Visuals.md`) is still
  required, image captions and spacers unchanged (§10), Pabau section + `book-demo` CTA (§5),
  `Conclusion` (§6), Continue your research (§7), Yoast FAQ (§8).
- Featured images are still **not** built for code articles (`Visuals.md` §11) — unchanged.
