# Core rules — the always-on baseline

The short list of rules that apply to **every sentence of every article**, plus a map of
when to open each full guide.

**Read this one always. Read the others when their trigger fires** — a guide you open at
the start of a job stays in context for the whole job, so loading all of them up front
costs far more than loading each one where it is actually used.

This file is a summary for triage and light edits. It never overrides a full guide: where
they differ, the full guide wins.

---

## When to read which guide

| Read this in full | When |
|---|---|
| `Pabau-style-guide.md` | **Before writing or rewriting any prose.** Voice, benefit framing, US/UK terms, glossary. Non-negotiable for /SEO's writing stages and the editorial pass. |
| `2-editorial.md` | **Before writing or rewriting any prose**, and for the whole editorial pass. Structure, AI-tell removal, meta description, capitalization, categories/tags. |
| `WordPress-blocks.md` | Whenever you touch block markup — the block-guarantee pass, or any stage that adds/converts/moves a block. **Sole source of truth for the block contract and its markup.** |
| `Visuals.md` | Before you build, audit, or place any chart, diagram, or interactive visualization — and before you build a blog featured image. **Sole source of truth for the visual contract** — what earns a visual, the brand tokens and font, the render/upload commands, the 1200 × 630 featured-image card (§11), and its verified templates. |
| `About-Pabau.md` | Writing new Pabau copy (the Pabau section, CTA text, Pabau feature captions), or fact-checking a Pabau claim. |
| `Originality-and-search-intent.md` | Judging intent from a SERP, planning an outline, or deciding a restructure. |
| `Meta-title-best-practices.md` | Writing or re-optimizing a SERP/meta title. Only then — it is about titles and nothing else. |
| `3-links.md` | **Any link work at all** — the internal-link pass, and choosing Continue-your-research targets. **Sole source of truth for interlinking:** the cluster wall, the ≤5 link budget, the pillar/subhub pattern, the funnel and CTA contract, and the gate that must pass before the save. |

---

## Pabau non-negotiables

These hold in every edit, with no exceptions.

- **Introduce Pabau on first mention** for cold search readers — "practice management
  software like Pabau", not a bare "Pabau".
- **Qualify product names on first mention:** "Pabau GO, our iOS app"; "Pabau Scribe, our
  AI scribe"; "Pabau Pay, our card terminals".
- **Never say "Pabau Connect" externally.** It is an internal name — say "online booking"
  or "our online booking portal".
- **No free trial.** Frame it as structured onboarding; never apologize for the absence.
- **No feature gating.** Every subscription includes every feature. Never imply lower
  tiers lock functionality.
- **Don't undermine the core product** when describing Plus add-ons — "additional" or
  "specialist", never "advanced", "basic marketing", or "limited reporting".
- **Lead with outcomes, not features.** Spell the benefit out ("so you can…").
- **Never name a specific customer** without the team's confirmation.
- **Every article ships at least one original visual we built** — a rendered chart or
  diagram, or one CSS-only interactive block. Never a stock photo and never invented
  numbers: every figure in a visual comes from the article, and the visual names its
  source. Full contract in `Visuals.md`.
- **A `/blog/` article with no featured image gets one built** — a 1200 × 630 brand card,
  rendered and uploaded like any other visual, attached by `featured_media` and never
  inserted into the body. It is a separate requirement from the visual above, and neither
  one covers for the other. An existing featured image is never replaced. Contract in
  `Visuals.md` §11.
- **Pricing comes from the provider's own website only** — never Capterra, G2, GetApp,
  Software Advice, Trustpilot, a round-up, or another blog. For Pabau, pabau.com only.
- **Never link to a competitor's pricing page.** Read it for the figures, but link their
  homepage instead — never `/pricing`, `/plans`, or a pricing anchor. Details in
  `3-links.md`.
- **Links stay inside the article's content cluster.** The cluster comes from
  `~/Desktop/pabau-content-clusters.xlsx` (source of truth, never re-derived) via
  `bin/cluster_lookup.py`. At most 5 in-body editorial links per article — 3 on a code page —
  exactly one of them the cluster's pillar. Cross-cluster links only via a pillar or a Tier-2
  hub, never post to post. Code pages link only inside billing: pillar + one subhub + at most
  one next-step. Full rulebook in `3-links.md`.
- **No URL containing `/lp/` is ever a link target** — not in the body, not in a Continue your
  research pick. Existing ones are removed.
- **Never remove or reroute a `/book-demo/` link.** Every article ends with two: one in the
  Pabau promotional section, one closing the Conclusion.

## Voice and mechanics

- **US English.** "Practice", not "clinic", in most cases. Convert UK medical terms. On a
  UK-specific article keep UK legislation and bodies, but still prefer "practice".
- **25 words per sentence, hard ceiling — measured, not eyeballed.** Never over 30. The
  26–30 band is a per-sentence exception you must justify, not a second budget. Applies to
  every piece of prose: intro, body, Key takeaways items, captions, FAQ answers, meta
  description, table cells. Don't count by eye — run the checker and fix what it lists:
  `python3 ~/.claude/factcheck-flow/bin/sentence_check.py --file <body>` (or `--post <id>`),
  and keep going until it exits 0. In `/fact` this is a gate that blocks the save.
- Short does not mean choppy. Vary sentence length; don't buy brevity with a dropped
  subject, a telegraphic fragment, or a clause welded on with a semicolon.
- **Don't force active voice.** Use passive voice where it reads better: when the actor
  is unknown, obvious, or irrelevant, or when the thing acted on is the point of the
  sentence ("The claim is denied if the modifier is missing"). Never rewrite a passive
  sentence to active just to make it active, and never invent an actor to do it.
- **Paragraphs: 4 lines / 60 words maximum.**
- Three or more clause-length list items in a sentence → make it a WordPress list block.
- Split clauses into their own sentences rather than joining them with em dashes, colons,
  or semicolons.
- **Headings are sentence case** (exceptions: a title starting with a number, and after a
  period, colon, semicolon, or em dash). Valid hierarchy H1 > H2 > H3 > H4.
- Headings must read naturally. No keyword stuffing, no stacked qualifiers, no heading
  that reads like a pasted search query.
- **Meta description ≤ 140 characters**, written as an excerpt that answers the query.

## AI tells to strip on sight

- No "gaps" unless it's a physical gap in a physical thing.
- No calling things "real", "true", or "actual" unless a fake version of that thing exists
  in the article ("…but it is real" → "…but it still affects the bottom line"; "scored
  against the practice's real records" → "scored against the practice's records").
- Cut "everything", "nothing", "anything", and bare "thing" down to a handful per article,
  and never pair "everything" against "nothing" as a contrast ("If everything is important,
  nothing is important" — don't write it in any form). Neither word can act: apart from
  "be"/"get", they never precede a verb. Name the actor or recast the sentence, passive
  included ("…and everything leaves a record of who did what" → "…and the whole process
  gets recorded").
- No "it's not X, it's Y" phrasing.
- No "most practices miss…" / "here's the part most clinics avoid" — or anything near it.
- No generic openers ("When it comes to…"), platitudes, or obvious advice.
- Every sentence carries information. Padding gets cut, not rewritten.

## The two-bar rule

Every article must clear both bars, on every run:

1. **Fit searcher intent (the floor).** Answer the query's actual question, in the format
   the SERP rewards — "how to" wants a procedure, "best" a ranked list, "what is" a
   definition, "X vs Y" a comparison, "…cost" pricing. Wrong format is a structural
   problem, not a copy tweak.
2. **Carry an originality nugget (the priority).** At least one angle no top-10 result
   has. If you can't name it, the article isn't ready.

Detail, worked examples, and the mirage tests are in `Originality-and-search-intent.md`.

## Answer-first

Any heading that is or implies a question is answered **directly and completely in the
first sentence** of its section — no preamble, no restating the question, no "it depends"
before the answer. Same for every FAQ answer.

**The intro carries the whole answer, and the main keyword is in the first sentence.**

- The **main keyword appears in the article's first sentence** — naturally, as part of a
  sentence a person would write, never bolted on.
- The intro **answers the keyword's main query completely**, not partially: a listicle says
  which provider is the best pick and for whom; an informational article defines the subject
  in the first paragraph; a "cost" query gives the number; a comparison says which one wins
  and when. A reader who stops at the intro has their answer.
- **Key takeaways sits directly below the intro** (order below), with nothing in the seam. On
  a listicle it is the ranked provider list — `#. [Provider] — short reason` per item,
  `WordPress-blocks.md` §2a.

## Required document order

Markup for every block below is in `WordPress-blocks.md` — that file is the contract, this
is only the shape:

```
H1
Intro                               ← main keyword in the FIRST sentence; answers the query in full
Key takeaways block                 ← directly below the intro, nothing in between
[Download box]                      ← template articles only; has its own H2
[YouTube embed]                     ← if there is a video: last block before the first body heading
H2 … body sections
H2 <Pabau-for-this-purpose section> ← contains the book-demo CTA block
H2 Conclusion                       ← exactly this word; concludes, links /book-demo/
Continue your research block        ← expert-picks; no wrapper H2
H2 Frequently asked questions
Yoast FAQ block
```

Never put a heading above a block that renders its own heading (Key takeaways, Continue
your research). Every image carries a `<figcaption>` and is followed by one 800 × 35
spacer block.

**In a listicle, every provider review opens with a `pabau/provider-card` block directly
below the provider's H2** (before any prose) and closes with a `Pricing` heading + table —
markup and card rules in `WordPress-blocks.md` §9a and §9.

**A YouTube video never breaks up a run of prose.** Its one slot is the last block before the
first body heading — after every intro paragraph and after the Key takeaways block, whether
the intro is headless or sits under an opening H2. Never between two paragraphs, never before
the intro, never in the intro/takeaways seam, never mid-body-section. Most articles have a `wp:embed` and about half have it in
the wrong place: move the block as-is, add no spacer, and never add a video that isn't there.
