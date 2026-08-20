# Visuals — every article ships an original visualization

Every Pabau article gets **at least one original visual** that we built: either a
**rendered image** (built in HTML, screenshotted to WebP, uploaded to the media library) or
an **interactive visualization** (CSS-only HTML, embedded live in a `wp:html` block).

It also owns the **blog featured image** (§11): a `/blog/` article with an empty featured
image slot gets a 1200 × 630 card built the same way.

This file is the single source of truth for all three. It owns *what* to build, *how* it must
look, and the exact commands and markup. `WordPress-blocks.md` still owns the surrounding
block contract — image captions and spacers are its §10, and a rendered visual is an
ordinary `wp:image` block that must satisfy that section in full.

The renderer is `~/.claude/factcheck-flow/bin/render_visual.py`. Run
`python3 ~/.claude/factcheck-flow/bin/render_visual.py --check` once before you build
anything; it reports Chrome, Pillow, the cached brand font, and WordPress credentials.

---

## 1. The rule

**One original visual per article, minimum.** Not a stock photo, not a screenshot someone
else made, not a re-crop of an existing site image — something built for this article out of
this article's own substance.

Two or three is right for a long article (2,000+ words) or a listicle. More than four is
padding. If an article already carries a visual *we* built to this contract, it satisfies
the rule; audit it against §7/§8 and move on.

**The featured image is a separate job** — §11. It is the card the article travels on, not a
visual inside it, so it neither satisfies this rule nor is satisfied by it. A `/blog/` article
with no featured image needs both.

**A visual has to earn its place.** It must carry information the reader cannot get as
quickly from the prose. Before you build, name the job in one sentence: *"this shows the
reader X, which takes three paragraphs to say."* If you cannot write that sentence, you are
about to build decoration — go find the real structure in the article instead.

What genuinely earns one:

- **A range or a comparison the article already states in prose** — unit ranges by treatment
  area, price tiers, dosage bands, timelines, before/after windows.
- **A process with stages** — a patient journey, a claim's path from encounter to payment, a
  consultation-to-treatment sequence, an onboarding flow.
- **A decision** — which code applies when, which document a payer needs, which treatment
  suits which indication.
- **A structure with parts** — what a compliant consent form contains, the fields of a
  SOAP note, the anatomy of a superbill.
- **A ranked or grouped set** — in a listicle, how the providers actually differ on the two
  dimensions the reader cares about.

What never does:

- A visual that restates a single number. That is a sentence.
- A generic "benefits of practice management software" wheel, a stock funnel, an unlabelled
  flow of vague boxes, or icons with one word each.
- Anything whose numbers you invented, estimated, or rounded from memory. See §3.
- A chart of a comparison the article does not actually make. The visual reports the
  article; it does not introduce claims that the prose never supports.

---

## 2. Which one to build

| Build a **rendered image** when… | Build an **interactive visualization** when… |
|---|---|
| The content is a fixed comparison, range, or ranking | The reader benefits from choosing a view — by stage, by treatment area, by provider |
| The visual is dense (many rows, a table-like grid) | There are 2–4 alternative slices of the same structure |
| You want it to appear in search, social, and email | Progressive disclosure genuinely helps — show one thing, reveal detail on tap |
| It illustrates a process the reader just reads once | The reader will compare two options back and forth |

**Default to a rendered image.** It is simpler, it is indexable, it survives every email
client and scraper, and it cannot break on the front end. Reach for interactive only when
the choosing *is* the value — and never more than one interactive visual per article.

Both routes use the same brand system (§4) and the same honesty rules (§3). The difference
is only the output.

---

## 3. The numbers have to be real

A visualization states facts with more authority than a sentence does, and a rendered image
cannot be corrected by editing text — the figures are baked into a PNG. So:

- **Every figure comes from the article, and the article's figure is already sourced.** If
  the number is not in the article, it is not in the visual. If you find yourself needing a
  number the article doesn't have, that is a fact-check job, not a visual job.
- **Pricing follows the Pabau rule with no exceptions:** the provider's own website only,
  never Capterra, G2, GetApp, a round-up, or another blog. For Pabau, `pabau.com` only.
- **Say where it came from, in the visual.** A footer line in the image —
  `Source: <who>, <when>` — or, when the figures are the article's own synthesis, a plain
  statement of that. Ranges get the word "typical" or "reported", never a false precision.
- **Never invent a trend.** No fabricated time series, no "industry average" you did not
  read somewhere real, no illustrative numbers dressed as findings. If the shape is
  genuinely illustrative, label it *Illustrative* in the visual itself.
- **Put the figures in the alt text.** This is not optional on a data visualization: alt is
  how the numbers reach a screen reader, and how the next fact-check pass can audit an image
  it cannot read. `--upload` refuses to run without `--alt`.
- **The caption names the source.** So the whole claim — figure, meaning, provenance — is
  auditable from the article body alone.

If a chart and the prose disagree after an edit, the chart is wrong until proven otherwise;
rebuild it. Never leave a stale figure in an image because the image is inconvenient to
regenerate.

---

## 4. The brand system

You write **layout**. The renderer injects the **brand** — the Satoshi webfont and every
token below — so a rendered visual never has to hardcode a colour or ship a font.

### Tokens (available as CSS custom properties inside a rendered visual)

| Token | Value | Use |
|---|---|---|
| `--pb-ink` | `#121D36` | Headings, big numbers |
| `--pb-body` | `#3D4757` | Body copy, row labels |
| `--pb-muted` | `#8A94A6` | Axis ticks, kickers, footnotes, sources |
| `--pb-blue` | `#037CD2` | Primary series, primary emphasis |
| `--pb-cyan` | `#24BEE1` | The accent — the one row you want read first |
| `--pb-navy` | `#1A2539` | Deep fill, third series |
| `--pb-page` | `#FFFFFF` | Canvas |
| `--pb-surface` | `#F5F8FB` | Tinted panel, inactive chip |
| `--pb-tint` | `#E4F7FC` | Cyan wash — pill backgrounds |
| `--pb-line` | `#E3E8EF` | Borders, gridlines, rules |
| `--pb-track` | `#DDE3EC` | The empty half of a bar or meter |
| `--pb-pro` / `--pb-con` | `#16794C` / `#A8412B` | Yes/no, works/doesn't — **always with a glyph** |
| `--pb-warn` | `#F0A32B` | Caution, partial fill |
| `--pb-wash-a/b` | `#E2F2FD` / `#DFE3FD` | The download-box gradient, for hero panels |
| `--pb-shadow` | see below | Card elevation |
| `--pb-radius` | `14px` | Card corner |

These are not decorative choices — they are the values live on pabau.com (the Elementor kit
and the provider-card stylesheet). A visual reads as ours because it uses the same tokens as
the page around it. Do not substitute "nicer" colours.

Series colours for categorical data, in order:
`--pb-series-1` … `--pb-series-6` = `#037CD2`, `#24BEE1`, `#1A2539`, `#6BA9D8`, `#0B6F86`,
`#9BB4CC`.

### Colour rules, which are not negotiable

- **Hue never carries meaning on its own.** Every colour distinction must be backed by a
  label, a glyph, a position, or a lightness difference. The ramp above is deliberately
  blue→cyan→navy, and adjacent series differ in lightness as well as hue, so it survives
  red-green colour vision deficiency and greyscale printing.
- **Never encode good/bad as red vs green.** Use the ✓/✕ glyphs with `--pb-pro`/`--pb-con`
  (this is exactly what the provider card does), or blue vs amber. The colour is a
  reinforcement, never the signal.
- **One accent per visual.** `--pb-cyan` marks the single row that matters most. If
  everything is highlighted, nothing is.
- **Label directly, drop the legend.** Put the series name on or beside the mark. A legend
  is a lookup table the reader has to hold in memory; only use one when direct labelling is
  genuinely impossible.

### Type

Satoshi, injected by the renderer. Weights: 300, 400, 500, 700.

- Title 28–32px / 700 / `--pb-ink`, `letter-spacing:-.02em`
- Kicker 11–12px / 600 / `--pb-muted`, uppercase, `letter-spacing:.13em`
- Row label 14–15px / 500 / `--pb-ink`
- Value 18–22px / 700 / `--pb-ink`, **tabular numerals** (the base CSS sets this — keep it,
  so digits align down a column)
- Source / footnote 12px / 400 / `--pb-muted`

Sentence case everywhere, US English, and the article's sentence ceiling applies to any real
sentence inside a visual. Labels and fragments are fine as labels.

### Layout

Generous padding (48–64px on a 1200px canvas), one clear grid, left-aligned text, values
right-aligned in their own column. Whitespace is what makes it look considered — resist
filling it. Close with a thin `--pb-line` rule above the source line.

---

## 5. Which form for which shape

Pick from the data's shape, not from what looks impressive:

| The data is… | Build |
|---|---|
| Magnitudes across categories | Horizontal bars, sorted by value, labels left, values right |
| A range per category (min–max) | Range bars — a `--pb-track` rail with a `--pb-blue` span, endpoints labelled |
| Parts of one whole (2–5 parts) | A single stacked bar, labelled in place. Not a pie |
| Parts of one whole (1 share that matters) | One donut or meter with the number huge in the middle |
| A sequence of stages | A left-to-right or top-to-bottom flow, numbered, one line of copy per stage |
| A decision | A branch diagram — question, two or three outcomes, the rule on each edge |
| Two dimensions across options | A 2×2, or a small labelled grid. Never a scatter with unlabelled dots |
| A comparison across features | A matrix of ✓/✕/partial, features as rows, options as columns |
| A structure's parts | An annotated panel — the thing, with callouts naming each part |
| One striking number | A stat block: the number at 60–80px, one line saying what it means |

Never: 3D anything, a pie with more than five slices, a doughnut used as decoration, a
radar chart, a word cloud, a truncated axis that exaggerates a difference, or a chart whose
gridlines are louder than its data.

---

## 6. Building a rendered image

Write a **fragment** of HTML — no `<html>`, `<head>`, or `<body>`, and no `<style>` for
fonts or tokens. The renderer wraps it in `#pv-canvas` and injects everything brand-level.
Scope your own classes with a `pv-` prefix. Keep it fully self-contained: no CDN, no remote
font, no remote image. Inline any image you need as a `data:` URI.

### Canvas

Width is always 1200 logical px, rendered at 2× (the blog serves body images at ~800px, so
this downsamples crisply). Pick a height:

| Preset | Size | For |
|---|---|---|
| `strip` | 1200 × 420 | A timeline, a stat row, one meter |
| `wide` | 1200 × 675 | Hero, 16:9 — one chart, few categories |
| `standard` | 1200 × 800 | The default — a chart plus a note, or a 2-up |
| `tall` | 1200 × 1100 | Ranked bars with many rows, a stacked comparison |
| `square` | 1000 × 1000 | A single donut or meter, social-friendly |

**Prefer `--fit`** for a content-flow layout: the renderer measures the real content height
and crops the canvas to it, so the visual has no dead space. Use a fixed preset only when
your layout depends on a known height (`height:100%` flex fills). Never let content run off
the canvas — the renderer checks the edges and refuses to ship a clipped visual.

### Render, then upload

```bash
RV=~/.claude/factcheck-flow/bin/render_visual.py

# 1. Render and look at it. Iterate here, not after uploading.
python3 "$RV" --html /tmp/visual.html --fit --out /tmp/visual.webp

# 2. Upload once you're happy. Prints {"id":…, "source_url":…} for the block.
python3 "$RV" --html /tmp/visual.html --fit \
  --slug botox-units-by-treatment-area \
  --alt "Range bars showing typical Botox unit ranges: glabella 20 to 25 units, forehead 10 to 20, crow's feet 8 to 16 per side" \
  --upload
```

- `--slug` becomes the media filename: lowercase, hyphenated, descriptive of the *content*.
  Never `chart-1` or `visual-final`.
- `--alt` is mandatory with `--upload` and carries the figures (§3).
- Useful flags: `--pad N` (page-background margin around a full-bleed design),
  `--quality N` (default 88), `--width/--height`, `--max-height`, `--preset`.
- Keep it under ~400 KB. The renderer warns past that; lower `--quality` or shorten the
  canvas.

**Look at the rendered image before you upload it.** Read the file. An unexamined
generated chart is how a clipped label, an unlabelled axis, or a bar that overflows its
track ships to the live site.

### The block

A rendered visual is an ordinary core image block and must satisfy `WordPress-blocks.md`
§10 in full — caption, and exactly one 800 × 35 spacer after it. Use the `id` and
`source_url` the upload printed:

```
<!-- wp:image {"id":<media id>,"sizeSlug":"large"} -->
<figure class="wp-block-image size-large"><img src="<source_url>" alt="<the alt you uploaded>" class="wp-image-<media id>"/><figcaption class="wp-element-caption"><em>Full-sentence caption that says what the reader is looking at and names the source.</em></figcaption></figure>
<!-- /wp:image -->
<!-- wp:spacer {"width":"800px","height":"35px"} -->
<div style="height:35px;width:800px" aria-hidden="true" class="wp-block-spacer"></div>
<!-- /wp:spacer -->
```

The caption follows §10's contract — full sentence, ends with a period, italic via `<em>`
and never asterisks — plus, for a visual, it names the source and adds the reading the chart
supports. Don't restate the alt text.

- BAD: `<em>Botox units by area.</em>` — a label.
- GOOD: `<em>Glabellar lines take roughly twice the units of crow's feet, which is why
  per-area pricing rarely matches per-unit pricing. Ranges as reported by the
  manufacturer.</em>`

---

## 7. Building an interactive visualization

Ships as a single `wp:html` block containing one root `<div>`, one scoped `<style>`, and the
markup. **CSS-only — no JavaScript.** WP Rocket defers and delays JS on pabau.com, so an
inline script is not reliably executed on the live page; a CSS-only interaction cannot
break. Use the radio-and-`:checked` pattern for tabs, `:hover`/`:focus-within` for reveals,
or `<details>` for an accordion.

Hard requirements — all of them are checked by the linter:

1. **One namespaced root.** `<div class="pv-viz pv-viz-<slug>">`, and *every* selector in
   the `<style>` sits under `.pv-viz-<slug>`. Never style a bare element (`p`, `h3`, `li`,
   `table`) — it would leak into the whole article. Never a global class.
2. **Tokens declared on the root.** The renderer isn't involved here, so the block carries
   its own custom properties (copy the values from §4). Satoshi comes free — the theme
   already loads it, so `font-family:'Satoshi',…` just works.
3. **Self-contained.** No external URL of any kind, no `<script>`, no `on…=` handler.
4. **A mobile breakpoint.** Over half of blog traffic is mobile. Ship a
   `@media (max-width:640px)` rule that reflows to one column and drops the type a step.
5. **Keyboard and screen reader reachable.** Labels tied to inputs with `for`, real text in
   the DOM (never a number that exists only as a bar width), sensible reading order.
6. **A caption.** Close the block with a `.pv-note` line that does the caption's job —
   what this shows and where the figures came from.
7. **Valid CSS.** Quote attribute-selector values that are not bare identifiers:
   `[data-pv="1"]`, never `[data-pv=1]`. An unquoted numeric value makes the browser
   discard the whole rule, and the visual silently renders in its default state.

Lint it, then preview it, before it goes in the article:

```bash
RV=~/.claude/factcheck-flow/bin/render_visual.py
python3 "$RV" --lint-embed /tmp/embed.html                       # must exit 0
python3 "$RV" --html /tmp/embed.html --fit --width 900 --pad 24 \
  --out /tmp/embed-preview.webp                                  # then look at it
```

The preview renders the default state only — it will not exercise the tabs. Check the other
states by reading the CSS carefully: confirm each `:checked` rule targets a panel that
exists, and that exactly one panel is visible at a time.

Wrap the finished markup:

```
<!-- wp:html -->
<div class="pv-viz pv-viz-<slug>"> … </div>
<!-- /wp:html -->
```

No spacer is needed — give the root its own `margin:28px 0`. An interactive block is not an
image, so it is not counted by §10's caption audit and must not be given a `<figcaption>`.

A verified starting template lives in §10.

---

## 8. Where the visual goes

Inside the body, per `WordPress-blocks.md` §1 — a visual sits in the body section whose
point it makes, immediately after the paragraph that sets it up, so the reader meets the
claim and then sees it.

- **Never inside** the Key takeaways block, the download box, the Pabau section, the
  Conclusion, the FAQ, or the Continue your research block.
- **Never between** the Conclusion and the Continue your research block.
- **Never immediately adjacent to the YouTube embed** — the video already closes the intro
  run; do not stack a visual against it.
- **In a listicle**, the natural slots are a comparison visual right after the intro's
  comparison table, and at most one per provider review — placed inside the review's prose,
  never between the provider card and the review's first paragraph.
- **Introduce it in the prose.** One clause is enough ("the ranges below vary more by area
  than most price lists suggest"). A visual dropped in with no lead-in reads like an ad.

---

## 9. QA before you save

Run through this for every visual you added:

- [ ] Its one-sentence job is real, and the article couldn't do it faster in prose.
- [ ] Every figure traces to the article; pricing is first-party; nothing invented.
- [ ] Source named inside the visual, and in the caption.
- [ ] Alt text carries the figures.
- [ ] Tokens and Satoshi only — no off-brand colour, no substituted font.
- [ ] No meaning carried by hue alone; ✓/✕ glyphs where there's a yes/no.
- [ ] Nothing clipped, nothing overlapping, no dead space, values aligned.
- [ ] **You actually looked at the rendered file.**
- [ ] Rendered image: caption + exactly one 800 × 35 spacer, per §10.
- [ ] Interactive: `--lint-embed` exits 0, mobile rule present, one panel visible at a time.
- [ ] Under ~400 KB.

After the save, confirm it rendered on the front end without pulling the page into context:

```bash
URL="<article URL>"
curl -s "$URL" | grep -c 'wp-element-caption'        # captions, incl. your visual's
curl -s "$URL" | grep -o 'pv-viz' | wc -l            # interactive roots (0 or 1)
curl -s "$URL" | grep -o 'wp-content/uploads[^"]*\.webp' | wc -l
```

And check the uploaded media is actually reachable:

```bash
curl -sI -o /dev/null -w '%{http_code}\n' "<source_url>"   # want 200
```

---

## 10. Verified templates

Both of these were rendered and checked. Copy the structure; replace the content, the
`--slug`, and the source line. Never ship them with their placeholder figures.

### 10a. Ranked bars — rendered image

Render with `--fit`. Note the `pv-` prefixes, the token references, the accent on the single
top row, the tabular values in their own column, and the rule above the source line.

```html
<style>
.pv-wrap{padding:48px 60px;display:flex;flex-direction:column}
.pv-kicker{margin-bottom:10px}
.pv-h{font-size:30px;line-height:1.2}
.pv-sub{font-size:15px;color:var(--pb-muted);margin-top:9px}
.pv-rows{display:flex;flex-direction:column;gap:20px;margin-top:32px}
.pv-row{display:grid;grid-template-columns:210px 1fr 92px;align-items:center;gap:20px}
.pv-name{font-size:15px;font-weight:500;color:var(--pb-ink)}
.pv-track{height:32px;background:var(--pb-track);border-radius:8px;overflow:hidden}
.pv-bar{height:100%;border-radius:8px;background:var(--pb-series-1)}
.pv-row.pv-hi .pv-bar{background:var(--pb-series-2)}
.pv-val{font-size:20px;text-align:right}
.pv-foot{margin-top:30px;padding-top:16px;border-top:1px solid var(--pb-line);display:flex;justify-content:space-between;align-items:center}
</style>
<div class="pv-wrap">
  <div>
    <div class="pv-kicker">Minutes per patient, per visit</div>
    <h2 class="pv-h">Where the admin time actually goes</h2>
    <p class="pv-sub">One line saying what the reader should take from this.</p>
  </div>
  <div class="pv-rows">
    <div class="pv-row pv-hi"><div class="pv-name">Longest item</div><div class="pv-track"><div class="pv-bar" style="width:100%"></div></div><div class="pv-val pv-num">11.4</div></div>
    <div class="pv-row"><div class="pv-name">Second item</div><div class="pv-track"><div class="pv-bar" style="width:64%"></div></div><div class="pv-val pv-num">7.3</div></div>
    <div class="pv-row"><div class="pv-name">Third item</div><div class="pv-track"><div class="pv-bar" style="width:41%"></div></div><div class="pv-val pv-num">4.7</div></div>
  </div>
  <div class="pv-foot">
    <span class="pv-source">Source: &lt;who&gt;, &lt;when&gt;.</span>
    <span class="pv-kicker">pabau.com</span>
  </div>
</div>
```

`.pv-num`, `.pv-label`, `.pv-kicker`, `.pv-source` and `.pv-rule` are provided by the
renderer's base CSS — use them rather than redefining the same rules.

### 10b. CSS-only tabs — interactive visualization

Lints clean and works on tap and click. Three tabs, three panels, one visible at a time;
the token block, the mobile breakpoint, and the quoted attribute selectors are the parts
people get wrong.

```html
<div class="pv-viz pv-viz-stages">
<style>
.pv-viz-stages{--pv-ink:#121D36;--pv-body:#3D4757;--pv-muted:#8A94A6;--pv-blue:#037CD2;--pv-cyan:#24BEE1;--pv-line:#E3E8EF;--pv-track:#DDE3EC;--pv-surface:#F5F8FB;font-family:'Satoshi',-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,Arial,sans-serif;color:var(--pv-body);background:#fff;border:1px solid var(--pv-line);border-radius:14px;padding:26px 28px 22px;margin:28px 0;box-shadow:0 1px 2px rgba(18,29,54,.05),0 10px 28px -8px rgba(18,29,54,.16)}
.pv-viz-stages *{box-sizing:border-box}
.pv-viz-stages .pv-kicker{font-size:11px;font-weight:600;letter-spacing:.13em;text-transform:uppercase;color:var(--pv-muted);margin:0 0 8px}
.pv-viz-stages .pv-title{font-size:20px;font-weight:700;color:var(--pv-ink);letter-spacing:-.02em;margin:0 0 18px;line-height:1.25}
.pv-viz-stages .pv-tabs{display:flex;flex-wrap:wrap;gap:8px;margin:0 0 20px;padding:0;border:0}
.pv-viz-stages input.pv-radio{position:absolute;opacity:0;pointer-events:none}
.pv-viz-stages label.pv-tab{cursor:pointer;font-size:13.5px;font-weight:500;color:var(--pv-body);background:var(--pv-surface);border:1px solid var(--pv-line);border-radius:99px;padding:7px 15px;line-height:1.3;transition:background .15s,color .15s}
.pv-viz-stages label.pv-tab:hover{border-color:var(--pv-blue);color:var(--pv-blue)}
.pv-viz-stages .pv-panel{display:none}
.pv-viz-stages .pv-rows{display:flex;flex-direction:column;gap:14px}
.pv-viz-stages .pv-row{display:grid;grid-template-columns:minmax(120px,1.1fr) 2fr auto;align-items:center;gap:14px}
.pv-viz-stages .pv-name{font-size:14px;color:var(--pv-ink);font-weight:500;min-width:0}
.pv-viz-stages .pv-track{height:26px;background:var(--pv-track);border-radius:7px;overflow:hidden}
.pv-viz-stages .pv-bar{height:100%;border-radius:7px;background:var(--pv-blue);transition:width .3s ease}
.pv-viz-stages .pv-row.pv-hi .pv-bar{background:var(--pv-cyan)}
.pv-viz-stages .pv-val{font-size:16px;font-weight:700;color:var(--pv-ink);font-variant-numeric:tabular-nums;text-align:right;min-width:64px}
.pv-viz-stages .pv-note{font-size:12.5px;color:var(--pv-muted);margin:18px 0 0;padding-top:14px;border-top:1px solid var(--pv-line)}
.pv-viz-stages #pv-s1:checked~.pv-tabs label[for=pv-s1],.pv-viz-stages #pv-s2:checked~.pv-tabs label[for=pv-s2],.pv-viz-stages #pv-s3:checked~.pv-tabs label[for=pv-s3]{background:var(--pv-blue);border-color:var(--pv-blue);color:#fff;font-weight:600}
.pv-viz-stages #pv-s1:checked~.pv-body .pv-panel[data-pv="1"],.pv-viz-stages #pv-s2:checked~.pv-body .pv-panel[data-pv="2"],.pv-viz-stages #pv-s3:checked~.pv-body .pv-panel[data-pv="3"]{display:block}
@media (max-width:640px){
.pv-viz-stages{padding:20px 16px 18px;border-radius:12px}
.pv-viz-stages .pv-row{grid-template-columns:1fr auto;gap:6px 12px}
.pv-viz-stages .pv-track{grid-column:1/-1;height:22px}
.pv-viz-stages .pv-title{font-size:17px}
.pv-viz-stages label.pv-tab{font-size:12.5px;padding:6px 12px}
}
</style>
<p class="pv-kicker">Tap a stage</p>
<p class="pv-title">A title that names what the reader is choosing between</p>
<input class="pv-radio" type="radio" name="pv-stages" id="pv-s1" checked>
<input class="pv-radio" type="radio" name="pv-stages" id="pv-s2">
<input class="pv-radio" type="radio" name="pv-stages" id="pv-s3">
<div class="pv-tabs">
<label class="pv-tab" for="pv-s1">First view</label>
<label class="pv-tab" for="pv-s2">Second view</label>
<label class="pv-tab" for="pv-s3">Third view</label>
</div>
<div class="pv-body">
<div class="pv-panel" data-pv="1"><div class="pv-rows">
<div class="pv-row pv-hi"><span class="pv-name">Row label</span><span class="pv-track"><span class="pv-bar" style="width:100%;display:block"></span></span><span class="pv-val">9 min</span></div>
<div class="pv-row"><span class="pv-name">Row label</span><span class="pv-track"><span class="pv-bar" style="width:44%;display:block"></span></span><span class="pv-val">4 min</span></div>
</div></div>
<div class="pv-panel" data-pv="2"><div class="pv-rows">
<div class="pv-row pv-hi"><span class="pv-name">Row label</span><span class="pv-track"><span class="pv-bar" style="width:100%;display:block"></span></span><span class="pv-val">11 min</span></div>
</div></div>
<div class="pv-panel" data-pv="3"><div class="pv-rows">
<div class="pv-row pv-hi"><span class="pv-name">Row label</span><span class="pv-track"><span class="pv-bar" style="width:100%;display:block"></span></span><span class="pv-val">6 min</span></div>
</div></div>
</div>
<p class="pv-note">What this shows, and where the figures came from.</p>
</div>
```

Note the `display:block` on each `.pv-bar` — the bars are `<span>`s so the markup stays
inline-friendly, and a span needs it to take a width.

---

## 11. The blog featured image

A `/blog/` article whose featured image is empty gets one **built here** — same renderer,
different job. This is not the §1 visual and does not stand in for it: the in-body visual
carries information, the featured image is the card the article travels on (the blog index,
related-post rails, and the Open Graph thumbnail in Slack, LinkedIn and X). An article
missing both gets both.

### When it applies

- The article's URL contains `/blog/` **and** its `featured_media` is `0`.
- A draft's permalink is `?p=<id>`, so read the kind off the article instead. It is a blog
  article unless it is a template article (it hands the reader a downloadable form) or a code
  article (an ICD/CPT/HCPCS code is its subject) — those publish under `/templates/`,
  `/procedure-codes/` and `/diagnostic-codes/`.
- **Never replace a featured image that already exists**, however plain it looks. This fills
  an empty slot; it does not re-art-direct the blog.
- Other post types are out of scope. A template or code article with an empty slot is
  recorded, not filled.

### What it is

**1200 × 630**, rendered from the template in §11a and uploaded to the media library. That is
the size every other featured image on the site uses, and it is the OG card ratio, so nothing
crops it.

It is typographic, not a chart: title, one line of deck, the topic, the wordmark. This is the
one visual on the site that carries no data, because a card is read at thumbnail size in a
feed — §1's "earn its place" test does not apply to it. Everything else still does: tokens and
Satoshi only, nothing invented, no stock photo, no screenshot. If you do put a number on it, it
comes from the article and it is the number the article is about.

The copy on the card:

- **Title** — the article's own H1, sentence case, shortened to fit if it runs long. Aim under
  ~70 characters, three lines maximum on the canvas. Cut words, never truncate with an ellipsis,
  and never re-title the article here.
- **Deck** — one sentence, 14 words or fewer, the reader's payoff. Not a summary of the Key
  takeaways.
- **Kicker** — the topic area in two to four words, US English ("Insurance & billing",
  "Practice operations", "Aesthetic treatments"). Not the keyword, not a category slug.
- **Chip** — what kind of read it is ("Practice management guide", "Code reference"), or one
  first-party figure from the article. Optional: drop it rather than pad it.
- **Never** a product claim, a price, a competitor's name, or anything about a free trial.
  The card is brand surface, and it outlives the paragraph it was written from.

### Build, check, upload, attach

```bash
RV=~/.claude/factcheck-flow/bin/render_visual.py

# 1. Render at the featured-image size and LOOK at the file.
python3 "$RV" --html /tmp/hero.html --width 1200 --height 630 --out /tmp/hero.webp

# 2. Upload. Prints {"id":…, "source_url":…}; you need the id.
python3 "$RV" --html /tmp/hero.html --width 1200 --height 630 \
  --slug insurance-eligibility-verification-featured \
  --alt "Pabau blog card: how insurance eligibility verification works, from intake to a clean claim" \
  --upload
```

- `--width 1200 --height 630` is deliberate. 630 is not one of the presets, and `--fit` is
  wrong here — a card is a fixed frame, not a content flow.
- `--slug` is `<article-slug>-featured`, so the media library says what it belongs to.
- `--alt` names it as a Pabau blog card and repeats the title. It is decoration on the page it
  fronts, but it is the only text a screen reader gets in a share preview.
- **The image goes nowhere in the body.** No `wp:image` block, no caption, no spacer — §10 of
  `WordPress-blocks.md` does not apply to it. It is attached by field only, in the same single
  PUT as the body:

```json
{"featured_media": 186912}
```

- If Chrome can't render (`render_visual.py --check` fails), record it under "Skipped" with the
  reason. Never attach a stock photo instead, and never leave a half-uploaded id in the payload.

### QA before you attach

- [ ] The slot really was empty, and the article really is a blog article.
- [ ] You read the rendered file. Nothing clipped, no orphaned word, no third line of deck.
- [ ] Title matches the article's H1 in substance and in case.
- [ ] Tokens and Satoshi only; no hue carrying meaning; no invented figure.
- [ ] 1200 × 630, under ~200 KB (a card this simple renders around 50 KB).
- [ ] `featured_media` set in the PUT, and nothing added to the body.
- [ ] After the save: `curl -sI -o /dev/null -w '%{http_code}\n' "<source_url>"` returns 200.

### 11a. The card — verified template

Rendered and checked at 1200 × 630, in both variants. Replace the kicker, title, deck and
chip; leave the structure alone. The corner disc is the only decoration the edge-clipping check
tolerates at this size, so don't add more.

```html
<style>
.pv-hero{height:100%;display:flex;flex-direction:column;padding:60px 72px;
  background:var(--pb-wash-a);position:relative;overflow:hidden}
.pv-hero::after{content:"";position:absolute;right:-160px;top:-160px;width:540px;height:540px;
  border-radius:50%;background:var(--pb-tint);opacity:.7}
.pv-hero>*{position:relative;z-index:1}
.pv-eyebrow{display:flex;align-items:center;gap:12px}
.pv-eyebrow .pv-dot{width:9px;height:9px;border-radius:50%;background:var(--pb-cyan)}
.pv-mid{flex:1;display:flex;flex-direction:column;justify-content:center}
.pv-title{font-size:56px;line-height:1.07;letter-spacing:-.025em;max-width:17em}
.pv-deck{font-size:20px;line-height:1.45;color:var(--pb-body);max-width:34em;margin-top:20px}
.pv-foot{display:flex;align-items:center;justify-content:space-between;
  padding-top:22px;border-top:1px solid var(--pb-line)}
.pv-mark{font-size:17px;font-weight:700;color:var(--pb-ink);letter-spacing:-.01em}
.pv-chip{font-size:13px;font-weight:500;color:var(--pb-ink);background:var(--pb-page);
  border:1px solid var(--pb-line);border-radius:999px;padding:8px 16px}
</style>
<div class="pv-hero">
  <div class="pv-eyebrow"><span class="pv-dot"></span><span class="pv-kicker">Insurance &amp; billing</span></div>
  <div class="pv-mid">
    <h1 class="pv-title">How insurance eligibility verification works, from intake to a clean claim</h1>
    <p class="pv-deck">What to check before the visit, and the five denial codes it prevents.</p>
  </div>
  <div class="pv-foot"><span class="pv-mark">pabau.com</span><span class="pv-chip">Practice management guide</span></div>
</div>
```

For the **navy variant** — a stronger thumbnail in a feed, same layout — swap six values:
`background:var(--pb-wash-a)` → `var(--pb-navy)`; the disc's
`background:var(--pb-tint);opacity:.7` → `background:#1F2C45;opacity:1`; the title's colour →
`#FFFFFF`; the deck's `var(--pb-body)` → `#C6D2E4`; the footer rule → `rgba(255,255,255,.18)`;
and the chip to `color:#E8F6FB;background:rgba(255,255,255,.08);border:1px solid
rgba(255,255,255,.22)`. Add `style="color:var(--pb-cyan)"` to the kicker so it holds up on the
dark ground. Pick one variant per article and don't mix them mid-run.
