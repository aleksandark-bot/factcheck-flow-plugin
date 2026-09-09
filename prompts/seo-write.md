# /SEO — part 2: outline, entities & the writing brief (S4–S9)

> Read at the START OF S4, after `prompts/seo-research.md` has produced the Gate #2 selection.
> If the Stage-3 proceed gate was skipped, this file is never read.
> The actual writing happens in the `seo-writer` subagent (S8), not in this conversation.

## You PLAN here. You do not write.

This half of the flow ends with a brief, not with copy. S4–S6 produce the outline; S7–S8 are
executed by the **`seo-writer` subagent**, which reads the writing guides and the article body
in ITS context and saves the result. You never load them.

That split is deliberate and it is the main cost control in this flow. The writing guides are
roughly 40k tokens; the article body is thousands more. Held here they would sit in context
through S4, S5, S6, the whole of the writing stage, and the /fact hand-off — re-read on every
turn. Held by the writer, they are read once and discarded when it returns.

**So: read NO writing guide here.** Not `Pabau-style-guide.md`, not `WordPress-blocks.md`, not
`2-editorial.md`, not `About-Pabau.md`, not `Visuals.md`, not `Meta-title-best-practices.md`.
The one guide this half does need is:

- `~/.claude/factcheck-flow/guides/Originality-and-search-intent.md` — the two-bar rule in
  full, the mirage battery, and the specificity tests. **Read it now.** S4's outline lives or
  dies on it, and the originality nugget has to be named at planning time or it never happens.

You have already read `core-rules.md` in part 1; its non-negotiables still bind everything you
plan (introduce Pabau on first mention; qualify product names once; never "Pabau Connect"
externally; no feature gating; no free trial; lead with outcomes; headings read naturally;
25-word sentence ceiling). The writer enforces them in the prose — you make sure the outline
doesn't require breaking them.

Planning-time structure rules, so you don't need `2-editorial.md` to lay out a heading tree:
keep a valid hierarchy (no H2 → H4 jumps), headings must read naturally rather than as
keyword fragments, and one section covers one concrete idea. Anything finer-grained than that
is the writer's call, not yours.

## Optimization stance (governs S4 and S6 — and is passed to the writer)

Six principles that override any "leave it as-is" instinct elsewhere in this file. When a
default below says "preserve" or "only if it improves," these win. The writer carries its own
copy of these — plus a seventh that is purely a writing mechanic (name the entity, skip the
pronoun) and needs nothing from you. Yours is what shapes the outline it receives.

1. **Be only as conservative as you NEED to be.** The job is to optimize, not to protect the
   existing draft. Overwriting, rewriting, and resequencing existing copy to work in the target
   keywords/entities and match the SERP is the DEFAULT, not the exception. Do not tiptoe: if
   rewriting a paragraph, merging two weak sections, or replacing a whole section lands the
   entities and intent better than a light touch, do it. The only things you must NOT change are
   the guardrails (facts, Pabau positioning/non-negotiables, publish status, and — on a
   published post — the URL/slug). Everything else is fair game. A timid pass that "preserves"
   the article but fails to insert the entities or answer the query is a FAILED pass.
2. **Every question-heading is answered in its FIRST sentence — as a self-contained
   capsule.** Any heading phrased as a question (or that plainly implies one — "How to…",
   "What is…", "…cost", "…vs…") MUST be answered directly and completely in the first sentence
   of that section — no throat-clearing, no "There are several factors to consider," no
   restating the question. Give the answer, then elaborate. Applies to FAQ answers too.

   The sharpened version, and the one to PLAN for: that opening answer is a CAPSULE. It runs
   20-25 words, up to 50 only if it is still tightly answering the question, and it has to make
   complete sense QUOTED ON ITS OWN — with the heading gone and nothing before or after it.
   That is the test, because that is exactly how a featured snippet and an answer engine will
   use it. Aim for roughly 60-70% of the article's sections opening this way; the rest stays
   ordinary explanatory or procedural prose. All capsules and no prose reads mechanical, which
   is why the target is two-thirds and not everything. No inline links inside a capsule
   sentence — put them in the elaboration that follows.
3. **Answer the reader's problem NEAR THE TOP.** The core payoff must be reachable by a skim
   reader without scrolling deep. The MAIN KEYWORD goes in the article's FIRST SENTENCE, and the
   intro answers the keyword's main query COMPLETELY — a listicle names the best pick and who
   it's for, an informational article defines the subject in the first paragraph. Key takeaways
   sits directly below the intro and reflects that answer. For a LISTICLE specifically: Key
   takeaways IS the ranked shortlist — one item per provider, in body order, `#. [Provider] —
   Short reason why they're on the list.` (`WordPress-blocks.md` §2a) — then a comparison TABLE,
   then the provider/pick segments. Do not bury the list behind long "what to look for / why it matters"
   preamble; move that below the picks or trim it.
4. **Pull in images where they help.** Add relevant images anywhere a visual materially aids
   comprehension or matches what the SERP rewards — a comparison/product screenshot per listicle
   entry, a process diagram for a how-to, a UI screenshot, an "at a glance" visual near the top.
   Plan WHERE images belong and what each depicts; the writer sources them and owns the block,
   alt-text, and caption contract. Every image needs a caption, including ones already in the
   article. Missing obvious images is an incomplete optimization. Separately, the article ships
   at least one ORIGINAL VISUAL WE BUILT — plan which node carries it and what it plots, from
   figures that are already in the article. The writer builds it against `Visuals.md`.

5. **Cover the whole fan-out, not just the head query.** A compound query gets broken into
   narrower sub-queries before an answer is assembled, and the page that appears across several
   branches is the one that gets used. The Stage-1 answer surface already handed you the SERP's
   own visible branches (`paa` + `related_searches`); S4 turns them into a named branch list and
   the outline must answer each one, or say why a branch is out of scope for this article.
   Answer each branch in its own place, in a capsule, so it can be lifted whole.

6. **Information gain beats more words.** For a page already ranking at 4-20, the thing standing
   between it and the top is not length — it is something the top results contain and we don't,
   plus something we contain that none of them do. Name BOTH sides in the outline. Adding a
   thousand words of the same information the SERP already has is the failure mode this
   principle exists to prevent, and a longer article that says nothing new usually loses ground.

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
wins (still obeying the planning-time structure rules above — valid hierarchy, natural headings).
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
is ALSO woven into that section's body text by the writer — plan each section's content intent so both
the heading and its text carry the keyword naturally.

FAN-OUT BRANCHES (Optimization stance #5) — do this BEFORE placing keywords, because it
changes which nodes exist. Build the branch list from three sources, in this order:
  1. `answer_surface.paa` — Google's own follow-up questions for this query. Highest value:
     these are not guesses, they are what the SERP is already asking.
  2. `answer_surface.related_searches` — the adjacent queries the same searcher runs next.
  3. Your own decomposition — read the main keyword as a compound question and split it the way
     an answer engine would: by AUDIENCE (solo practice vs multi-location), by CONSTRAINT
     (price, time, regulation, country), and by USE CASE. Three to five branches is right.
Then dedupe them into a NAMED BRANCH LIST of 3-6 items, and for each one write which outline
node answers it. A branch with no node is either a new node or an explicit out-of-scope note
with a reason — never silently dropped. Branches that overlap across several sources matter
most; a page that answers all of them is the one that survives being fanned out.
Do not turn every branch into an H2. A branch can be answered inside a section, as a capsule,
or as an FAQ entry — what matters is that the answer is present and liftable.

INFORMATION GAIN (Optimization stance #6) — REQUIRED whenever the page already ranks at 4-20
for the target query (`page_diagnosis` / `answer_surface.our_position` tells you), and good
practice otherwise. Name both sides in one line each:
  · GAIN IN: what the top results cover that we don't — a subtopic with no heading here, a
    number we never give, a step we skip. S5's competitor pass is what fills this in, so leave
    the line open now and complete it at S6.
  · GAIN OUT: what we will carry that none of them do. This is the originality nugget, stated
    as information rather than as an angle. If GAIN OUT is empty the run has nothing to win on.
A striking-distance page gets no credit for more words. Plan the delta, not the length.

TITLE MANDATE — if part 1 handed you `title_mismatch_signal: true`, the SERP title and the H1
must be re-pointed at ONE winnable query bucket this run, whether or not the main keyword
changed. Name that bucket in the outline and note it for S7; the writer owns the wording. Same
mandate when a target query carries `ctr_gap: severe` at position 10 or better AND no AI
Overview is present — it ranks and nobody clicks, so the title is the deliverable, not copy.

SNIPPET TARGET — if `answer_surface.featured_snippet` exists, name the node that will compete
for it and REQUIRE ITS FORMAT to match the snippet's: a table snippet needs a [TABLE] node, a
list snippet a [LIST] node, a paragraph snippet a capsule. Matching the format is most of
winning it. If we already hold the snippet, note that too — and don't restructure that section
out from under ourselves.

ANSWER-FIRST & TOP-OF-ARTICLE PLACEMENT (Optimization stance #2 + #3 — bake into the outline):
- For EVERY node whose heading is a question or implies one, note "answer in first sentence" and
  what that one-sentence answer is, so S8 leads the section with it (not preamble).
- Put the reader's core answer near the top. Plan the intro to state the direct answer, and plan
  Key takeaways to carry it. If the current article buries the payoff behind long preamble,
  reorder now so the answer surfaces early (this is a structural change you are authorized to make).
- LISTICLE type: the outline MUST (a) name the actual picks/providers in Key takeaways;
  (b) place a comparison [TABLE] node immediately after the Key takeaways block that follows
  the intro, before the first pick; plan Key takeaways as the ranked `#. [Provider] — reason`
  list (§2a); and
  (c) start the per-pick segments right after that table. Push any long "how we chose / what to
  look for" material BELOW the picks (or trim it). Plan the table's columns now (name + the 2–4
  axes that actually decide the pick).

REQUIRED BLOCKS — plan them as outline nodes now, don't leave them to be discovered during
writing. **Do not open `WordPress-blocks.md` to do this.** You are deciding WHICH block nodes
exist and roughly where they sit; the writer owns their exact markup and reconciles your
ordering against the required document order in that file's §1. Plan these nodes by name —
Key takeaways, template download box (template articles only), the Pabau section + its CTA
block, Conclusion, Continue your research, FAQ, and (listicles) a Pricing node per provider —
tag each [UNCHANGED]/[OPTIMIZED]/[NEW] like any other node, and note:
- **Pabau section** (§5) — the topic-specific H2 (never "Why choose Pabau") and which Pabau
  workflow it covers for THIS article's purpose. If the article's Pabau material currently
  lives elsewhere, plan the move.
- **Conclusion** (§6) — plan the rename if the article says "The bottom line" or similar, and
  note the judgment it will land plus its closing inline CTA link.
- **Continue your research** (§7) — plan the block (max 5 under-linked targets, no wrapper H2).
- **LISTICLE** (§9) — plan a `Pricing` node at the END of every provider review.
- **Video** (§11) — if the article already carries a YouTube embed, its only slot is the last
  block before the first body heading, after the intro and the Key takeaways block. Never plan
  a video between paragraphs, above the intro, in the intro/takeaways seam, or inside a body
  section. If it currently sits in one of
  those places, plan the move; never plan a new video.

IMAGE PLANNING (Optimization stance #4): mark outline nodes that should carry an image with an
[IMG] note — what the image should show and why it helps (e.g. "product screenshot for pick #1",
"booking-flow screenshot", "comparison visual near the top"). The writer sources the image and
owns the block markup and caption contract. Here just decide WHERE images belong and what each
depicts.

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

  Two things make a nugget worth more, at no extra effort — apply them when they fit, and never
  in place of the nugget itself:
  · NAME IT. A nugget with an ownable two-to-four-word name — a named checklist, a named
    framework, a named sequence — is repeatable. Repeated across articles in the same words, it
    becomes the term people and answer engines associate with us, which is exactly what a
    generic phrasing of the same idea never earns. If a previous Pabau article already named
    this framework, REUSE THE SAME NAME rather than inventing a synonym; consistency is the
    whole mechanism. `Originality-and-search-intent.md` already puts named frameworks in the
    Medium tier — this is how to get the compounding out of them.
  · MAKE IT THE GAIN OUT. The nugget and the information-gain "GAIN OUT" line are the same
    thing said two ways: the angle, and the concrete information that angle produces. State it
    as information — a number, a sequence, a real example, a decision rule — because that is
    the form a competitor can't paraphrase and an answer engine can quote.
  A nugget that survives as a claim in the intro and nowhere else is decoration. It has to be
  the substance of at least one section.
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
  [VISUAL]     the original visual we build (exactly one node carries it; + what it plots)
  [CAPSULE]    this node opens with a 20-25 word self-contained answer (+ the answer, in one
               line, so S8 leads with it instead of inventing a preamble)
  [SNIPPET]    the node competing for the featured snippet (+ the required format)
Tag roughly 60-70% of the body nodes [CAPSULE] — not all of them. Also list keywords routed to
IN-TEXT with their target section, the fan-out branch each node answers, and flag every
question-heading that S8 must answer in its first sentence.
This OUTLINE is the reference object for S6 (entity grouping) and for the S7 brief.
```

---

# STAGE 5 — Entity extraction + SERP structure analysis  (FAN OUT — one subagent per URL)

```
Do NOT open the competitor pages in this conversation. A parsed article page is 15–25k tokens
and there are several of them; loaded here they stay resident for every remaining turn of the
run. Instead, dispatch one `general-purpose` subagent PER selected_competitor_url — ALL IN A
SINGLE MESSAGE so they run concurrently.

**The reports go to disk, not into this conversation.** Each is ~600 words, there are up to
ten of them, and the merge below is the only thing that ever needs the full text. Have each
subagent write its report to a file and return one short line; then a single merge subagent
reads the files. That way the raw reports never enter this context at all.

Give each subagent exactly one URL, its index `<n>`, and these instructions:

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

    UNIQUE DATA: the specific things THIS page has that a generic article on the topic would
    not — a real number with its source, a named framework, a first-hand account, a price, a
    dated benchmark, an original screenshot, a quoted practitioner. List up to 6, each in one
    line, and mark any figure with the source the page credits. This is the information-gain
    ledger: it is what we have to match or beat, and it is the most useful thing in this report.

    ANSWER SHAPE: does the page open each section with a short self-contained answer, or bury
    it under preamble? One sentence. If it does answer up front, quote ONE example capsule
    verbatim (under 30 words) so we can see the bar.

    Total under 700 words. Write it to /tmp/seo-<slug>-entity-<n>.md and write nothing else
    there — no preamble, no commentary, no page text. Then return ONE line and nothing else:
    DONE: <n> | <url> | entities=<count> headings=<count> formats=<short comma list>

Then dispatch ONE `general-purpose` merge subagent, pinned to **`model: sonnet`** — merging
already-structured reports into a fixed output shape does not need a stronger model, and this
runs on every /SEO. Give it the file paths (not the contents) and these instructions:

    Read every /tmp/seo-<slug>-entity-*.md file listed below. They are competitor analyses of
    the <N> pages currently ranking for "<CURRENT MAIN KEYWORD>". Merge them into ONE profile
    and return it as your entire reply. Do not quote the source files.

    ENTITY LIST — keep a term only if it appears on ALL pages, or at minimum on ≥ 2 of them.
    Match SEMANTICALLY, not by exact string: group synonyms and paraphrases that mean the same
    thing into one entity and record the variants. Output per entity: canonical label, variants
    seen, and page coverage count (e.g. "3/3 pages"). Order by coverage desc, then salience.

    SERP STRUCTURE PROFILE:
    - consensus heading map: the subtopics/entities the SERP consistently gives headings to,
      with the dominant heading pattern for each (the structural "floor" we must match);
    - format inventory: which structured formats dominate (e.g. "5/6 pages use a comparison
      table"; "all use a numbered step list"), plus any featured-snippet opportunity;
    - WEAKNESSES TO BEAT: the pooled weaknesses — and, most important, what NEW useful data we
      could present as a table/list that none of the ranking pages offer.

    INFORMATION-GAIN LEDGER — the deliverable that decides whether a striking-distance page
    moves, so give it real space:
    - HAVE: the unique data points that appear on 2+ pages, i.e. the SERP's shared baseline.
      Anything here that our article lacks is a gap we must close to be a complete answer.
    - RARE: unique data points that appear on exactly ONE page. These are the differentiators
      currently in play — note which page holds each.
    - ABSENT: what NONE of them has, that this topic obviously calls for and we could
      credibly supply (a real number, a decision rule, a worked example, a practitioner
      account, a country-specific detail). Be concrete; "more depth" is not an entry.
    - ANSWER SHAPE: how many of the pages open their sections with a short self-contained
      answer, and how good the best example was. That sets the bar for our capsules.

    Keep the whole reply under 1000 words. It is the only thing that survives this stage.

What that subagent returns IS the profile. Keep it — S6 turns it into structure revisions and
the writer receives it in the brief. Delete the /tmp/seo-<slug>-entity-*.md files at S9.
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
  planning-time structure rules; the writer reconciles final block ordering against §1.

CLOSE THE INFORMATION-GAIN LINES (S4 left GAIN IN open on purpose):
- GAIN IN ← the ledger's HAVE entries our article lacks. Each one becomes a specific outline
  change: a node, a figure inside a node, or a table column. Not "add more detail".
- GAIN OUT ← the ledger's ABSENT list, filtered to what we can supply honestly. Cross-check it
  against the nugget from S4: if the ledger shows a competitor already has our nugget, the
  nugget is not one — pick a different angle now, at planning time, not after it is written.
- Any RARE entry we can beat outright is worth a node of its own. Note who currently holds it.

FAN-OUT CHECK — walk the branch list from S4 against the final tree. Every branch either has a
node answering it, or an explicit one-line reason it is out of scope. Do this last, after the
reorganization, because merging and splitting nodes is what usually orphans a branch.

SNIPPET FORMAT — if a [SNIPPET] node exists, confirm its planned format still matches the
snippet holder's (table / list / capsule) after the reorganization above.

Output: the FINAL OUTLINE the writer works from — the heading tree with any S6 revisions and
planned [TABLE]/[LIST]/[CAPSULE]/[SNIPPET]/[VISUAL] nodes, each node carrying its grouped
entities plus table-column / list-item notes beneath it, and the closed GAIN IN / GAIN OUT
lines. Still no prose written.
```

---

# STAGE 7 — Write the brief

```
The outline is final. Serialize everything the writer needs into ONE file and stop planning.

Write /tmp/seo-<slug>-brief.md with the Write tool. It must be self-contained: the writer
starts with an empty context and cannot see this conversation. Include, in this order:

1. ARTICLE — URL, post ID, slug, status, is_draft, article type (listicle / code article /
   template article / standard guide).
2. MAIN KEYWORD — the current one, and the new one if the selection set a new_main_keyword
   (state "unchanged" if not). If it changed, say explicitly that the writer must land it in
   the SEO title, the H1, the FIRST SENTENCE of the body, and the meta description, as an exact
   match reading naturally in each. Then the fifth spot, the SLUG: on a DRAFT give the
   `proposed_slug` from the selection and tell the writer to set it; on a REFRESH write
   "SLUG: DO NOT TOUCH (published)" in those words. Never leave this line ambiguous.
3. SEARCH INTENT — your one-paragraph Stage-1 note: the question the query actually asks, the
   SERP-dominant format, and the depth the SERP rewards.
4. ANSWER SURFACE — the six lines from Stage 1 step 1b: featured snippet (holder + FORMAT), AI
   Overview (present? cited domains? are we cited?), the PAA and related-search lines verbatim,
   the other SERP features present, the title-gap verdict, and our current position. The writer
   uses the format requirement and the AIO read directly.
5. FAN-OUT BRANCHES — the named branch list from S4, each with the node that answers it, and
   each out-of-scope branch with its reason. Tell the writer every listed branch must be
   answered in its node, in a capsule, and that skipping one is a Skipped-line item.
6. PAGE DIAGNOSIS (published only) — the GSC verdict (growing / flat / declining), the
   striking-distance queries with `best_position`, any `ctr_gap: severe` query, and the
   `title_mismatch_signal` with the ONE query bucket the title and H1 must own if it fired.
   State plainly whether this run is a rescue, a push, or a defence.
7. OWNERSHIP — the Stage-1B verdicts in one block: which keywords are ours, which were vetoed
   as owned elsewhere or split, the competing URL for each, and the decision taken. Add:
   "never edit the competing page" — it is a finding for David, not work for this run.
8. INFORMATION GAIN — the closed GAIN IN and GAIN OUT lines from S6, plus the ledger's ABSENT
   list. Mark GAIN OUT as REQUIRED CONTENT, not as background.
9. ORIGINALITY NUGGET — the nugget you named in S4, its NAME if it has an ownable one, and
   which node delivers it. Mark it as REQUIRED: the writer must not let it evaporate into
   generic copy, and must use the same name throughout rather than paraphrasing it.
10. SERP STRUCTURE PROFILE — the merge subagent's output from S5: consensus heading map, format
   inventory, featured-snippet opportunity, the WEAKNESSES TO BEAT, and the ANSWER SHAPE bar.
11. FINAL OUTLINE — the S6 heading tree in document order, every node carrying its tag
   ([UNCHANGED]/[OPTIMIZED]/[NEW]/[H1-NEW]/[IMG]/[VISUAL]/[CAPSULE]/[SNIPPET]/[TABLE]/[LIST]),
   its grouped entities, its content intent, the fan-out branch it answers, and — for
   [OPTIMIZED] nodes — the old heading text so the writer can find the section. For every
   [CAPSULE] node give the one-line answer it opens with. Flag every question-heading that
   must be answered in its first sentence.
12. KEYWORD PLACEMENT — every selected keyword with its role (heading / in-text / FAQ) and its
   target node. Exact-match rule stated. Note that a heading keyword also goes in that
   section's body text.
13. BLOCK NODES — which required blocks you planned as [NEW] vs [UNCHANGED], and the note that
   the writer owns their markup and final ordering per WordPress-blocks.md §1.

Keep it dense and factual — it is instructions, not prose. Do NOT paste the article body into
it; the writer fetches that itself. Do NOT restate block markup; the writer reads the contract.

Then stop. The next stage dispatches the writer; you write no article copy at any point.
```

---

# STAGE 8 — Dispatch the writer

```
Spawn ONE `seo-writer` subagent. It performs the main-keyword swap, writes every section,
enforces the block contract, sources images, clears the sentence gate, and saves the article
in a single PUT. You do none of that yourself and you never see the article body.

Pass it exactly this — paths and short facts, nothing bulky:
- the brief path: /tmp/seo-<slug>-brief.md   (tell it to read this FIRST)
- the selection path: /tmp/seo-<slug>-sel.json
- the article URL or post ID, its status, and is_draft

Then wait. The writer reads its own guides, fetches the article itself, and returns a
change-log. Do NOT re-explain the block contract, the style guide, the sentence gate, or the
optimization stance in the dispatch message — the agent carries all of it, and restating it
here would pull into this context the very material the split exists to keep out.

If the writer reports it could not complete something under "Skipped", relay that verbatim in
S9. Do not try to fix it here by loading the guides and editing the article yourself — that
undoes the whole arrangement. If a genuine re-run is needed, dispatch a fresh seo-writer with
the same brief plus a note on what to correct.

Keep the returned change-log. It is the /SEO half of the S9 report.
```

---

# STAGE 9 — Cleanup, hand off to /fact

```
1. Confirm the writer reported a 2xx save, and that it preserved status. Draft stays draft; a
   post someone accidentally published is still handled as draft content — NEVER change publish
   status. SLUG: on a published post confirm the slug is unchanged; on a draft confirm it
   matches the brief's `proposed_slug` if one was given.

1b. WRITE THE RUN BASELINE (published articles only — a draft has nothing to measure yet).
   Google actively tests a changed page for roughly two weeks before its position settles, so
   the position a week from now proves nothing on its own. What makes the next run able to tell
   improvement from noise is a dated before-picture, and this is the only moment it exists.

     mkdir -p "$HOME/.claude/factcheck-flow/cache/seo-baselines"
     cp /tmp/seo-<slug>-gsc.json \
        "$HOME/.claude/factcheck-flow/cache/seo-baselines/<slug>-<YYYY-MM-DD>.json"

   Then write a short sibling file `<slug>-<YYYY-MM-DD>.md` with the Write tool holding: the
   date, the main keyword before and after, the GSC verdict, the striking-distance queries with
   their `best_position`, the fan-out branches covered, the nugget delivered, and the REVIEW
   DATE (today + 14 days). Keep it under 20 lines. Name the review date in the final report.

2. Delete the run's temp files: /tmp/seo-<slug>-kw.json, -sel.json, -gsc.json, -serp.json,
   -serp-sel.json, -cannibal.json, -cannibal-main.json, -headings.txt, -body.txt, -brief.md,
   and every -entity-*.md. Copy the GSC file to the baseline directory BEFORE deleting it.

2b. REQUEST A RE-CRAWL — published articles ONLY, and only after a confirmed 2xx save:

     python3 "$HOME/.claude/factcheck-flow/bin/index_ping.py" --url "<full article URL>"

   A refresh Google hasn't re-crawled is a refresh that hasn't happened yet, and a sitemap is a
   crawl-priority hint rather than a request. This is the direct one. It notifies Google that a
   URL that is ALREADY PUBLIC has changed: it publishes nothing, changes nothing on the site,
   and cannot expose a draft.
   · NEVER run it on a draft. The script refuses a non-200 URL, but do not rely on that.
   · Exit 3 is a SKIP, not a failure (no key installed, quota exhausted, URL unreachable).
     Report the reason in one line and move on.
   · One URL per run. This is not a bulk submitter, and the daily quota is shared.

2c. NAME THE CORNER-STONE LINKS — a REPORT-ONLY deliverable, and one of the highest-value
   things this run produces. A page that already ranks and earns clicks generates authority by
   ranking, with no backlink involved, and an in-body link from it into this article channels
   some of that authority here. That is what moves a page the last few positions when the
   content is already right.

   Produce a shortlist of 3-5 SOURCE pages that should link INTO this article:
     python3 "$HOME/.claude/factcheck-flow/bin/cluster_lookup.py" resolve --url "<url>"
     python3 "$HOME/.claude/factcheck-flow/bin/cluster_lookup.py" targets --cluster <id> --sort pr
   Keep only pages that are (a) in the SAME cluster — the cluster wall binds link planning as
   much as link writing, (b) already ranking and earning clicks, not just published, and (c)
   not already carrying a heavy load of outbound links (a page past roughly 50 in-body links is
   passing very little to any single destination, and overloading one strong page can cost it
   its own ranking). For each, give the source URL, the section the link would sit in, and a
   proposed anchor. Vary the anchors — the same anchor repeated across a site stops adding
   information — and never propose more than one new link per source page.

   **Never edit those pages.** /SEO optimizes ONE article; inbound boost links are edits to
   other pages and belong to David or to the interlinking project. Name them and stop.

3. HAND OFF TO /fact — IN A FRESH SUBAGENT, NOT IN THIS CONVERSATION.
   /SEO ALWAYS finishes by handing off to /fact, including when the PROCEED GATE was skipped
   and no optimization happened. /fact re-runs the editorial and block passes independently;
   that duplication is deliberate.

   Do NOT run /fact inline here. By this point this context holds the research, the keyword
   work, the entity profile, the outline, and the writer's change-log — and /fact is itself a
   multi-stage orchestration with its own subagent fan-outs and human gates. Running it on top
   of this context re-reads all of the above on every one of its turns, for no benefit: the two
   flows share nothing but the article ID.

   Instead spawn ONE `general-purpose` subagent, pinned to **`model: sonnet`** — it is
   routing and relaying, and every agent it spawns carries its own model pin, so its own
   model barely touches output quality. Tell it, in substance:

       Run the /fact flow on <article URL or post ID> by following
       ~/.claude/commands/fact.md exactly, as the orchestrator. That file is your
       instructions. Return its final consolidated report and nothing else.

   ONE EXCEPTION — the triage gate. /fact Stage 2 asks the human about listicle review scores,
   Pabau's own ranking position, and verified grave factual errors. A subagent cannot run that
   gate. So:
     - If you expect findings that need triage, prefer telling the user plainly: "/SEO is done
       and saved. Run `/fact <url>` next — in a NEW session, so it starts with a clean
       context." That is the cheapest and most correct hand-off, and it keeps the human in the
       loop where the design puts them.
     - Only dispatch the subagent version when running unattended, and have it treat an empty
       ASK bucket as the normal case and surface any ASK findings in its report instead of
       deciding them itself.
4. Produce ONE combined report: the writer's change-log + the /fact results (or the instruction
   to run /fact next, if you took that route). Add these five lines, which are the /SEO half of
   the value and exist nowhere else:
   - `Page diagnosis:` growing / flat / declining, and whether this run was a rescue, a push or
     a defence. Say plainly that a fresh position means nothing for about two weeks.
   - `Review date:` the date from step 1b, and the one thing to check on it (the striking-
     distance queries' positions, not total traffic).
   - `Ownership findings:` every keyword vetoed as owned elsewhere or split, with the competing
     URL. These are edits to OTHER pages — name them, never make them.
   - `Corner-stone links:` the 3-5 source pages from step 2c with their proposed anchors, marked
     clearly as not-yet-done.
   - `Re-crawl:` submitted, or the skip reason.
   End with the reminder to purge the WP Rocket cache for the URL.
```

---

## Notes / defaults (resolved)

- Competitor keywords: pooled into ONE deduped list, tagged with which competitor(s) rank.
- SERP structure analysis (S5): reuses the SAME pages opened for entity NLP, via one subagent
  per page writing to /tmp, then ONE merge subagent → a SERP structure profile that S6 turns
  into novel headings + [TABLE]/[LIST] nodes + reorganization, and the writer improves on. No
  extra fetches beyond the entity pass, and neither the page text nor the per-page reports ever
  enter the main context.
- GSC list: built by `dfs_lists.py` — top 20 by clicks over a trailing 90-day window, enriched
  with difficulty + volume (display only, never filtered), displayed by position ascending.
  "opportunity" flags the two target categories, both requiring `present_on_page == false`:
  (1) RANKING, NOT ON-PAGE — position ≤ 10, weave into a heading/body; (2) WINNABLE, NEEDS
  CONTENT — position > 10, win it with a new dedicated heading + content.
- Save cadence: exactly one save, made by the `seo-writer` subagent (the main-keyword swap
  rides along with it). This conversation never PUTs to WordPress.
- Division of labour: S4–S7 PLAN (this context, no writing guides loaded); S8 WRITES (the
  `seo-writer` subagent, which loads the guides and the body); S9 hands off. The writing guides
  are ~40k tokens and the body thousands more — kept out of here, they are read once by an
  agent that then discards them, instead of being re-read on every remaining turn.
- After the keyword gate, S4–S8 run straight through to the /fact handoff (S9).
- What /SEO deliberately does NOT do, and reports instead: edit any page other than this one
  (corner-stone inbound links, the competing page in a cannibalization finding), change a
  published URL or slug, merge or redirect anything. Those are corpus-level decisions with
  their own sign-off, and naming them precisely is worth more than half-doing them.
- The baseline files in `cache/seo-baselines/` are the only durable output of a run. They are
  what makes the NEXT run able to say whether this one worked, so writing one is not optional
  book-keeping — it is the measurement half of the loop.
