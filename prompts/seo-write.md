# /SEO — part 2: outline, entities & writing (S4–S9)

> Read at the START OF S4, after `prompts/seo-research.md` has produced the Gate #2 selection.
> If the Stage-3 proceed gate was skipped, this file is never read.

## Read these NOW — the writing guides

You are about to change headings, titles, meta, and body copy. These are the source of truth
and override anything below on voice and structure. Read all of them before S4:

- `~/.claude/factcheck-flow/prompts/2-editorial.md` — editorial standards: fluff/AI-tell
  removal, US English, structure, paragraph and sentence limits, image captions, meta
  description, capitalization, Yoast, categories/tags.
- `~/.claude/factcheck-flow/guides/Pabau-style-guide.md` — voice, benefit framing, US/UK
  terminology, formatting mechanics, glossary.
- `~/.claude/factcheck-flow/guides/WordPress-blocks.md` — **the block contract and the exact
  markup for every block.** It is the single source of truth: whatever /SEO saves must already
  comply. /fact enforces it afterward, but shipping it right the first time avoids a rewrite.
- `~/.claude/factcheck-flow/guides/Originality-and-search-intent.md` — the two-bar rule in
  full, the mirage battery, and the specificity tests. Drives S4's outline and S8's writing.
- `~/.claude/factcheck-flow/guides/About-Pabau.md` — product family, naming rules, pricing,
  competitors. Needed the moment you write Pabau copy.

Read `Meta-title-best-practices.md` when you reach the SERP title (S7 step 3, or the S8 meta
work) — not before; it is about titles and nothing else.

Non-negotiables carried over from `core-rules.md` and `/fact`: introduce Pabau on first
mention; qualify product names once; never "Pabau Connect" externally (say "online booking");
no feature gating; no free trial; lead with outcomes; headings read naturally; 25-word
sentence ceiling everywhere.

## Optimization stance (governs S4, S6, S8 — read before writing anything)

Four principles that override any "leave it as-is" instinct elsewhere in this file. When a
default below says "preserve" or "only if it improves," these win.

1. **Be only as conservative as you NEED to be.** The job is to optimize, not to protect the
   existing draft. Overwriting, rewriting, and resequencing existing copy to work in the target
   keywords/entities and match the SERP is the DEFAULT, not the exception. Do not tiptoe: if
   rewriting a paragraph, merging two weak sections, or replacing a whole section lands the
   entities and intent better than a light touch, do it. The only things you must NOT change are
   the guardrails (facts, Pabau positioning/non-negotiables, publish status, and — on a
   published post — the URL/slug). Everything else is fair game. A timid pass that "preserves"
   the article but fails to insert the entities or answer the query is a FAILED pass.
2. **Every question-heading is answered in its FIRST sentence.** Any heading phrased as a
   question (or that plainly implies one — "How to…", "What is…", "…cost", "…vs…") MUST be
   answered directly and completely in the first sentence of that section — no throat-clearing,
   no "There are several factors to consider," no restating the question. Give the answer, then
   elaborate. This is a hard rule (it also wins featured snippets). Applies to FAQ answers too.
3. **Answer the reader's problem NEAR THE TOP.** The core payoff must be reachable by a skim
   reader without scrolling deep. Put the direct answer in the intro (and reflect it in Key
   takeaways). For a LISTICLE specifically: name the actual providers/picks in the Key takeaways
   block, and start the provider/pick segments IMMEDIATELY after the intro — preceded by a
   comparison TABLE (the skim-reader's answer) so someone who reads nothing else still gets the
   ranked shortlist. Do not bury the list behind long "what to look for / why it matters"
   preamble; move that below the picks or trim it.
4. **Pull in images where they help.** Add relevant images anywhere a visual materially aids
   comprehension or matches what the SERP rewards — a comparison/product screenshot per listicle
   entry, a process diagram for a how-to, a UI screenshot, an "at a glance" visual near the top.
   See the image rule in Stage 8 for sourcing; the block, alt-text, and caption format live in
   `WordPress-blocks.md` §10. Every image needs a caption, including ones already in the
   article. Missing obvious images is an incomplete optimization.

---

# STAGE 4 — Outline planning  (PLANNING ONLY, no writing)

```
Using the Gate #2 selection + the existing heading tree, decide placement for EACH selected
keyword. Produce an OUTLINE; write NO article copy yet (only short content-intent notes).

STRUCTURAL CHANGES (Stage 1) — read FIRST and let them shape the whole outline. On the manual
(Refresh) branch you ALWAYS make structural changes — NEVER fall back to "preserve the existing
structure and only place keywords." There are two cases, and in BOTH you end up restructuring:
- The user ENTERED structural_changes text → treat it as a mandatory, high-priority FLOOR: do
  everything it asks (reorder, merge, split, add/remove sections, change the article TYPE/format
  entirely — e.g. listicle → how-to guide — or a substantial rewrite the SERPs imply), THEN add
  your OWN further structural improvements on top (driven by the SERP structure profile, searcher
  intent, and the originality nugget below). The user's instruction is the minimum, not the ceiling.
- The box is EMPTY → you have CARTE BLANCHE: decide the structure yourself and make the changes the
  SERP-dominant format, searcher intent, and originality nugget call for. An empty box NEVER means
  "leave the structure alone" — it means the structural decisions are entirely yours.
Bake all of this into the OUTLINE now (new/removed/reordered nodes), then layer keyword placement
on top. Where a structural change conflicts with a keyword-placement default, the structural change
wins (still obeying 2-editorial.md structure rules — valid hierarchy, natural headings).
Note in the outline which nodes exist BECAUSE of structural changes, and whether each came from
the user's box or your own judgment.

Placement decision per selected keyword:
1. TOPIC ALREADY COVERED, heading not an exact match → reword that heading so it contains
   the keyword as an EXACT MATCH, rewritten to be fully grammatical and natural (never a
   shoehorned exact-match fragment). Record old → new heading.
2. TOPIC NOT COVERED → add a NEW H2 or H3 (pick the level that respects hierarchy and fits
   the surrounding structure) whose text is the keyword as an EXACT MATCH, grammatical.
   Note the content intent (what the section will cover) — no prose yet.
3. use_in_heading = true but no sensible heading placement exists → mark the keyword for
   IN-TEXT insertion instead, and note the target section.
4. use_as_faq = true → plan it into the FAQ block as a new FAQ QUESTION (exact match); note the
   answer source per Selection semantics (reuse a related selected keyword if one exists, else a
   non-duplicative variation). If the article has no FAQ block, plan to create one.
5. use_in_heading = false and use_as_faq = false → mark for in-text insertion in the most
   relevant section.

Exact-match rule: any keyword placed in a heading must appear verbatim; you MUST reword the
whole heading around it for grammar/sense (this is mandatory, not optional). A heading keyword
is ALSO woven into that section's body text in S8 — plan each section's content intent so both
the heading and its text carry the keyword naturally.

ANSWER-FIRST & TOP-OF-ARTICLE PLACEMENT (Optimization stance #2 + #3 — bake into the outline):
- For EVERY node whose heading is a question or implies one, note "answer in first sentence" and
  what that one-sentence answer is, so S8 leads the section with it (not preamble).
- Put the reader's core answer near the top. Plan the intro to state the direct answer, and plan
  Key takeaways to carry it. If the current article buries the payoff behind long preamble,
  reorder now so the answer surfaces early (this is a structural change you are authorized to make).
- LISTICLE type: the outline MUST (a) name the actual picks/providers in Key takeaways;
  (b) place a comparison [TABLE] node immediately after the intro, before the first pick; and
  (c) start the per-pick segments right after that table. Push any long "how we chose / what to
  look for" material BELOW the picks (or trim it). Plan the table's columns now (name + the 2–4
  axes that actually decide the pick).

REQUIRED BLOCKS — plan them as outline nodes now, don't discover them in S8. The required
document order and the markup for every block are in `WordPress-blocks.md` (§1 for the order,
§2–§10 for each block). Do not restate the contract here; open that file and plan to the shape
it defines. Tag each block node [UNCHANGED]/[OPTIMIZED]/[NEW] like any other node, and note:
- **Pabau section** (§5) — the topic-specific H2 (never "Why choose Pabau") and which Pabau
  workflow it covers for THIS article's purpose. If the article's Pabau material currently
  lives elsewhere, plan the move.
- **Conclusion** (§6) — plan the rename if the article says "The bottom line" or similar, and
  note the judgment it will land plus its closing inline CTA link.
- **Continue your research** (§7) — plan the block (max 5 under-linked targets, no wrapper H2).
- **LISTICLE** (§9) — plan a `Pricing` node at the END of every provider review.

IMAGE PLANNING (Optimization stance #4): mark outline nodes that should carry an image with an
[IMG] note — what the image should show and why it helps (e.g. "product screenshot for pick #1",
"booking-flow screenshot", "comparison visual near the top"). Sourcing is in S8; the block format
and caption contract are in `WordPress-blocks.md` §10. Here just decide WHERE images belong and
what each depicts.

If new_main_keyword is set: plan the new H1 (exact-match, grammatical) and note that S7 will
also update meta/intro/SEO title/focus keyphrase.

TWO-BAR CHECK (per Originality-and-search-intent.md) — the outline must clear both before you
proceed to writing:
- INTENT (floor): the outline ANSWERS THE QUERY'S ACTUAL QUESTION (not an adjacent one) in the
  SERP-dominant format + depth you recorded in Stage 1. If the current article answers a different
  question or uses the wrong format, restructure it here (reorder/merge/split/replace sections,
  or change the article type) — you are ALWAYS authorized to make this change: on the manual path
  it's part of the structural work you always do (box or no box), and on the auto/draft path you
  do it on your own judgment. Originality never excuses answering the wrong question — the nugget
  must live INSIDE the correct answer.
- ORIGINALITY NUGGET (priority): name at least one nugget the outline will deliver that no
  top-10 result has (Light→Medium is fine — a distinctive sort/framing, a practitioner angle, a
  proprietary checklist, real Pabau workflows/customer examples). This is REQUIRED on EVERY run,
  independent of the structural-changes box — an empty box does not lower the bar. Plan where it
  lives. If you can't name one, the article isn't ready — find an angle before writing. Apply the
  intro litmus test to the planned intro (no generic "When it comes to…" opener).
Also apply specificity: each section is a concrete pain point; flag any section so broad it
"could be its own blog" to either go deep or split (respect what the SERP rewards).

SERP STRUCTURE (deferred to S5→S6): the deep competitor analysis — every ranking page's heading
tree, which keywords/entities they put in headings, and their structured-data formats (tables,
lists, FAQ/step blocks) — runs in S5 and is applied to THIS outline in S6 (novel headings,
[TABLE]/[LIST] nodes, reorganization to beat the SERP). Plan keyword placement now; leave room for
those structural improvements rather than locking the format here.

OUTLINE output — the full heading tree in final document order, each node tagged:
  [UNCHANGED]  existing heading kept as-is
  [OPTIMIZED]  existing heading, shown in its NEW exact-match form (+ old form)
  [NEW]        new heading (+ target keyword + one-line content intent)
  [H1-NEW]     new H1 (only if main keyword changed)
  [IMG]        an image to add at/under this node (+ what it shows + why)
Also list keywords routed to IN-TEXT with their target section, and flag every question-heading
that S8 must answer in its first sentence.
This OUTLINE is the reference object for S6 (entity grouping) and S8 (writing).
```

---

# STAGE 5 — Entity extraction + SERP structure analysis  (FAN OUT — one subagent per URL)

```
Do NOT open the competitor pages in this conversation. A parsed article page is 15–25k tokens
and there are several of them; loaded here they stay resident for every remaining turn of the
run. Instead, dispatch one `general-purpose` subagent PER selected_competitor_url — ALL IN A
SINGLE MESSAGE so they run concurrently — and keep only what they return.

Give each subagent exactly one URL and these instructions:

    Open <URL> (use on_page_content_parsing, or WebFetch with a high token limit) and read the
    MAIN CONTENT only — ignore nav, footer, cookie banners, and CTA boilerplate. Return a
    COMPACT report and nothing else, in this shape. Do not include the page text.

    ENTITIES: the salient recurring words/phrases — domain nouns, named concepts, features,
    sub-topics, multi-word phrases. Ignore stopwords, generic connectives, and site-brand
    chrome. For each: canonical label + the variant spellings/synonyms used on this page.
    Cap at 30, ordered by salience.

    HEADINGS: the full H1–H4 tree in document order, one per line, each tagged with the
    heading PATTERN (question / how-to / X-vs-Y / number+noun / benefit-led / plain).

    FORMATS: every structured presentation and what it holds — comparison/pricing/spec TABLES
    (with their columns), ordered (step) and unordered LISTS, FAQ blocks, definition boxes,
    pros/cons, checklists, "at a glance" boxes, how-to/FAQ schema. Note any place the page is
    plainly competing for a FEATURED SNIPPET (short answer + list/table).

    WEAKNESSES: vague or keyword-stuffed headings, missing or thin tables/lists, disorganized
    flow, obvious subtopics with no heading of their own.

    Total under 600 words. Your reply IS the data — no preamble, no commentary.

When the reports come back, merge them yourself:

ENTITY LIST — keep a term only if it appears on ALL pages, or at minimum on ≥ 2 of them. Match
SEMANTICALLY, not by exact string: group synonyms and paraphrases that mean the same thing into
one entity and record the variants. Output per entity: canonical label, variants seen, and page
coverage count (e.g. "3/3 pages"). Order by coverage desc, then salience.

SERP STRUCTURE PROFILE — built from the merged HEADINGS/FORMATS/WEAKNESSES:
- consensus heading map: the subtopics/entities the SERP consistently gives headings to, with the
  dominant heading pattern for each (this is the structural "floor" the article must match);
- format inventory: which structured formats dominate (e.g. "5/6 pages use a comparison table";
  "all use a numbered step list"), plus any featured-snippet opportunity;
- WEAKNESSES TO BEAT: the pooled weaknesses — and, most important, what NEW useful data we could
  present as a table/list that none of the ranking pages offer.

This profile is consumed by S6 (outline structure refinement) and S8 (writing).
```

---

# STAGE 6 — Group entities + refine outline structure

```
Map each ENTITY to the OUTLINE heading it is most semantically relevant to. An entity may
map to more than one heading if genuinely relevant to each.

- Attach entities to headings ([UNCHANGED], [OPTIMIZED], [NEW] alike).
- Entities that fit no specific heading but are on-topic → pool under "Intro / general".
- Entities that don't fit the article's scope at all → drop (note them under "unused").

STRUCTURE REFINEMENT (from the S5 SERP STRUCTURE PROFILE) — now improve the outline's SHAPE, not
just its entity coverage. Emulate what works on the SERP and beat it; never copy competitors:
- HEADINGS: make sure every consensus-map subtopic the article should cover has a heading (respect
  hierarchy + editorial rules), but word them as NOVEL, clearer, more natural headings than the
  SERP's — don't mirror a competitor's phrasing or stuff keywords. Keep the exact-match keyword
  placements from S4 intact; only improve the wording around them.
- STRUCTURED DATA: where the format inventory shows a table or list wins (or a snippet is up for
  grabs), plan a [TABLE] or [LIST] node — and make it carry NEW useful information (an extra
  column, a fresh comparison axis, real numbers/steps competitors omit), not a rehash. Add the
  intended columns/list items as short notes on the relevant node.
- ORGANIZATION: reorder / merge / split nodes so the flow is more logical than the SERP's, directly
  addressing the WEAKNESSES TO BEAT. Any Stage-1 structural_changes still win, and keep the
  2-editorial structure rules and the document order in `WordPress-blocks.md` §1.

Output: the FINAL OUTLINE S8 writes from — the heading tree with any S6 structure revisions and
planned [TABLE]/[LIST] nodes, each node carrying its grouped entities plus table-column / list-item
notes beneath it. Still no prose written.
```

---

# STAGE 7 — Main-keyword swap (only if new_main_keyword is set)

```
Skip this stage entirely if new_main_keyword is null.

Otherwise update, in line with the guides (editorial + style + About-Pabau):
1. H1 → the new main keyword as an exact match, reworded to be natural/grammatical.
2. Yoast focus keyphrase (post meta) → the new main keyword.
3. SEO/meta title → NOW read `~/.claude/factcheck-flow/guides/Meta-title-best-practices.md`
   and re-optimize per it (listicle number if applicable, current year if time-sensitive,
   match micro-intent, differentiate in SERP, lead with the pain point). Don't just mirror
   the H1 if a stronger SERP title exists.
4. Meta description → rewrite to answer the searcher query as an article excerpt, ≤140 chars.
5. Intro text → rework so the new main keyword appears naturally in the first paragraph;
   keep the OLD main keyword nearby as a secondary keyword if still valuable (don't shoehorn).

Do NOT write to WordPress here — hold these changes for the single save in S8.
```

---

# STAGE 8 — Optimize & write to WordPress

```
Now produce and apply the actual copy, using the OUTLINE + grouped entities + S7 changes.
EVERYTHING written here must comply with 2-editorial.md, the style guide, About-Pabau, and
`WordPress-blocks.md`.

STRUCTURAL CHANGES: EXECUTE the Stage 4 structural plan here in full — it is already baked into
the Stage 4 outline, so write to that restructured outline. On the manual (Refresh) branch there
is ALWAYS a structural plan to execute: whatever the user put in the box (do it in full) PLUS your
own structural improvements, or — if the box was empty — the changes you decided under carte
blanche. This may mean a LARGER REWRITE than a normal optimization pass: reformatting the article,
re-sequencing or replacing whole sections, or rewriting substantial copy to match the format the
SERPs reward. Never half-apply a change to "preserve" the old structure. Keep the SEO keyword work
intact on top of the new structure. If the changes imply the article's TYPE changed, re-check the
meta title per Meta-title-best-practices.md. Summarize the structural changes in the S9 change-log
(noting which came from the user's box vs your own judgment).

For each OUTLINE node:
- [OPTIMIZED] heading → apply the new heading text; then rewrite that section's existing
  copy to naturally weave in the grouped entities (don't just append; integrate).
- [NEW] heading → write new section copy from scratch covering the content intent, using the
  grouped entities. Match article voice; lead with the outcome; introduce/qualify Pabau
  correctly on first mention.
- [UNCHANGED] heading → still rewrite the body wherever that lands the grouped entities, an
  answer-first opening, or clearer copy — don't wave a section through untouched just because
  its heading didn't change. Only genuinely strong, on-target copy should survive verbatim
  (Optimization stance #1: be only as conservative as you need to be).
- [IMG] node → insert the planned image here as a real WordPress image block (sourcing below;
  markup, alt text and caption contract in `WordPress-blocks.md` §10).
- IN-TEXT keywords → insert into the most relevant existing sentence/section naturally.
- FAQ keywords (use_as_faq) → add each as a new Q in the FAQ block (verbatim question, proper
  Yoast FAQ schema; create the block if missing). Write the ANSWER per Selection semantics:
  reuse a related SELECTED keyword in the answer if one exists; otherwise use a sensible
  variation of the FAQ keyword — never duplicate the question phrase or a near-identical one.

Hard rules:
- BLOCK CONTRACT — the saved article MUST satisfy `WordPress-blocks.md` in full: the required
  document order (§1) and the exact markup for the Key takeaways block (§2), the template
  download box (§3), the `book-demo` CTA block (§4) inside the required Pabau section (§5), the
  `Conclusion` heading and its inline CTA link (§6), the `expert-picks` Continue your research
  block (§7), the Yoast FAQ block (§8), listicle pricing segments (§9), and image captions +
  spacers (§10). Copy the markup from that file — do not reconstruct it from memory, and do not
  rely on a summary. Rename any "The bottom line"/"Final thoughts" heading to `Conclusion` while
  you are in there.
- LISTICLE PRICING (§9): every figure comes from the PROVIDER'S OWN WEBSITE; never Capterra, G2,
  GetApp, Software Advice, Trustpilot, or another blog, and pabau.com only for Pabau. No
  published prices → "Contact sales / no published pricing" plus a sentence saying so.
- Keywords placed in headings are EXACT match; headings still read naturally (reword fully).
- A keyword placed in a heading MUST also appear in that section's body text.
- A new main keyword must land in the H1, intro, meta description, and SEO title (via S7).
- No keyword stuffing in body or headings; every sentence must carry information (no fluff).
- ANSWER-FIRST HEADINGS (stance #2): any heading that is or implies a question is answered
  directly and completely in the FIRST sentence of its section. Same for every FAQ answer.
- ANSWER NEAR THE TOP (stance #3): the intro states the reader's core answer and Key takeaways
  reflects it. For a LISTICLE: name the real picks in Key takeaways, put a comparison TABLE right
  after the intro, and begin the per-pick segments immediately after that table.
- OVERWRITE FREELY (stance #1): rewrite, resequence, merge, or replace existing copy and blocks
  whenever that optimizes better than a light edit. Keep only the guardrails fixed (facts, Pabau
  positioning, publish status, published-post URL/slug). Fix malformed HTML/FAQ blocks. Respect
  the paragraph (≤4 lines/≤60 words) and sentence (≤25 words; 30 only where a split would break
  the meaning) limits in every piece of prose you write or leave standing, captions and FAQ
  answers included; convert 3+ clause lists to WordPress list blocks.
- If the SERP shows a featured-snippet opportunity, format the relevant answer as both a
  short paragraph and a list to compete for it.
- EMULATE + IMPROVE ON THE SERP STRUCTURE (S5 profile / S6 final outline): write the planned novel
  headings (clearer and more natural than the ranking pages', never mirrored or keyword-stuffed);
  build every planned [TABLE]/[LIST] node as a real WordPress table/list block that delivers NEW
  useful information — never a decorative rehash of a competitor's table; and organize each
  section more logically than the SERP, fixing the WEAKNESSES TO BEAT.
- ORIGINALITY + ANTI-MIRAGE: actually DELIVER the nugget planned in Stage 4 (don't let it
  evaporate into generic copy), and run every new/rewritten section through the mirage battery
  in Originality-and-search-intent.md — reader's-shoes ("no shit" vs "no one told me this"),
  real-examples, and customer-fit (write for a practice owner/manager who already knows the
  basics, not "anyone"). Cut platitudes, obvious tips, and generic intros.
- IMAGES (stance #4): build every [IMG] node planned in S4, and add an image anywhere else a
  visual clearly helps or the SERP rewards one. Sourcing, in order:
    1. The site's OWN media library first — reuse a relevant asset already hosted:
         curl -s -u "$WP_USER:$WP_APP_PASSWORD" \
           "$WP_BASE_URL/wp-json/wp/v2/media?search=<term>&per_page=20&_fields=id,source_url,alt_text,title"
       Use the returned `source_url` and note the media `id`.
    2. If nothing fits and the section genuinely needs one (e.g. a per-provider screenshot/logo
       in a listicle), use the provider's OWN official image URL. VERIFY it resolves before
       inserting: `curl -sI -o /dev/null -w '%{http_code}' "<url>"` — ship only a 200. Never
       insert a guessed URL, and never hotlink something that will 404.
  The image block markup, the mandatory `<figcaption>` rules, and the required 800 × 35 spacer
  are all in `WordPress-blocks.md` §10 — including the rule that a caption on a PABAU FEATURE
  screenshot must name the feature and say how it helps the reader do what this article is about.
  Alt text is required, descriptive, and separate from the caption. Don't overload a section with
  images; one purposeful image beats three decorative ones. If the post has NO featured image and
  a good candidate exists, set it via `featured_media: <id>`. Log every image added (and its
  source) in the change-log.

SENTENCE GATE — run BEFORE the save, and do not save while it fails. You cannot count words by
eye, so a script does it. Dump the body you are about to PUT to a file, then:
  python3 ~/.claude/factcheck-flow/bin/sentence_check.py --file /tmp/body.html
Rewrite every sentence it lists, re-run, repeat until it exits 0. Nothing over 30 words ships;
26–30 is a per-sentence exception you must be able to justify, not a second budget. Don't buy the
count with fragments or semicolon-welded clauses. Paste the final summary line into the
change-log. If the script is missing, fetch it from the repo's `bin/` once.

SAVE — ONE save for the whole run. Hold S7's changes and all of S8's edits in memory and PUT
them together, per the wordpress-access skill: write payload.json with the Write tool, send it
with `-d @payload.json -o /dev/null -w '%{http_code}\n'`, and change only the fields you touched
(content, title, excerpt/meta description, Yoast focus keyphrase meta, categories/tags —
append-only, remove "Uncategorized", featured_media if you set one). Draft stays draft; published
stays published. Verify the save with a grep assertion, not a page fetch.

CHANGE-LOG (hold for the S9 combined report): main keyword (old→new if changed), structural
changes applied (from the Stage 1 box vs your own judgment), headings added/optimized, keywords
placed (heading vs in-text), entity themes woven in, meta/title/description changes,
categories/tags added, images added (with source) + featured image set + captions written or
fixed, any answer-first/top-of-article reordering done, the block-contract work, and the sentence
gate's final summary line (verbatim) plus how many sentences you rewrote to clear it.
```

---

# STAGE 9 — Save, cleanup, hand off to /fact

```
1. Confirm the S8 save returned a 2xx. Draft stays draft; a post someone accidentally
   published is still handled as draft content — NEVER change publish status.
2. Delete the run's temp files: /tmp/seo-<slug>-kw.json, -sel.json, -gsc.json,
   -headings.txt, -body.txt (and the SERP picker's files if they still exist).
3. Run /fact on the SAME article (its URL/ID). /SEO ALWAYS finishes by handing off to /fact —
   including when the PROCEED GATE was skipped and no optimization happened. /fact re-runs the
   editorial and block passes independently; that duplication is deliberate.
4. Produce ONE combined report covering the /SEO change-log (if any) + the /fact results,
   ending with the reminder to purge the WP Rocket cache for the URL.
```

---

## Notes / defaults (resolved)

- Competitor keywords: pooled into ONE deduped list, tagged with which competitor(s) rank.
- SERP structure analysis (S5): reuses the SAME pages opened for entity NLP, via one subagent
  per page — headings, heading keyword/entity use, and structured-data formats → a SERP
  structure profile that S6 turns into novel headings + [TABLE]/[LIST] nodes + reorganization,
  and S8 writes and improves on. No extra fetches beyond the entity pass, and no page text in
  the main context.
- GSC list: built by `dfs_lists.py` — top 20 by clicks over a trailing 90-day window, enriched
  with difficulty + volume (display only, never filtered), displayed by position ascending.
  "opportunity" flags the two target categories, both requiring `present_on_page == false`:
  (1) RANKING, NOT ON-PAGE — position ≤ 10, weave into a heading/body; (2) WINNABLE, NEEDS
  CONTENT — position > 10, win it with a new dedicated heading + content.
- Save cadence: exactly one save, in S8 (S7's changes ride along with it).
- After the keyword gate, S4–S8 run straight through to the /fact handoff (S9).
