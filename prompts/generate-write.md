# /generate — part 2: intent, outline, the gate & the brief (G5–G10)

> Read at the START OF G5, after `prompts/generate-research.md` has produced the G3 selection
> and the G4 source profile. If the G2 commission gate ended in "Refresh that page instead",
> this file is never read.
> The actual writing happens in the `article-generator` subagent (G9), not in this conversation.

## You PLAN here. You do not write.

This half ends with a brief, not with copy. G5–G8 produce the outline and the brief; G9 is
executed by the **`article-generator` subagent**, which reads the writing guides and the
harvested source files in ITS context and creates the post. You never load them.

That split is the main cost control in this flow. The writing guides are roughly 40k tokens and
the source reports several thousand more. Held here they would sit in context through G6, G7,
the whole writing stage and the /fact hand-off, re-read on every turn. Held by the writer, they
are read once and discarded when it returns.

**So: read NO writing guide here.** Not `Pabau-style-guide.md`, not `WordPress-blocks.md`, not
`2-editorial.md`, not `About-Pabau.md`, not `Visuals.md`, not `Meta-title-best-practices.md`.
The one guide this half needs is:

- `~/.claude/factcheck-flow/guides/Originality-and-search-intent.md` — the two-bar rule in
  full, the mirage battery and the specificity tests. **Read it now.** G6's outline lives or
  dies on it, and the originality nugget has to be named at planning time or it never happens.

You have already read `core-rules.md` in part 1; its non-negotiables still bind everything you
plan. Planning-time structure rules, so you do not need `2-editorial.md` to lay out a heading
tree: keep a valid hierarchy (no H2 → H4 jumps), headings read naturally rather than as keyword
fragments, and one section covers one concrete idea. Anything finer is the writer's call.

## Generation stance (governs G6 — and is passed to the writer)

Eight principles. The first four are the ones that separate a new article that ranks from one
that reads well and does nothing.

1. **Write from the harvested material, not from memory.** Every substantive claim in the
   outline traces to a fact in the G4 SOURCE FACTS list, to the code authority, or to Pabau's
   own knowledge. A number with no source does not go in the plan, so it cannot end up in the
   copy. This is not a citation formality: a model asked for a page with no supplied material
   fills the gaps itself, and those gaps are where the errors live.
2. **Answer the query in the first sentence, above the fold.** A reader who has to scroll to
   find out whether the page answers their question goes back to the SERP, and that bounce is
   what kills a new page before it ever gets a fair test. The intro states the answer outright;
   Key takeaways carries it; the H1 and the SERP title front-load the exact keyword.
3. **The page must be hard to reproduce.** Ask the durability question about the plan: what
   would it take for a competitor with a writer and public sources to produce this page? If the
   answer is "an afternoon", the plan is a rewritten explainer, and no amount of length,
   structure or freshness fixes that — the same summary is what an answer engine produces for
   free. Fix it at the outline with one of: first-hand practitioner detail, original data, a
   named framework, a decision rule, a built visual carrying real figures, or a genuinely
   useful interactive element. Name which one, in the outline.
4. **Narrow beats broad.** Answer engines slice documents into passages and reassemble them, so
   a tightly-scoped page about one thing is easier to lift and cite than a broad page about
   three. If the outline is growing a second subject, that subject is a DEFERRED article, not a
   section. Say so and move it to the report.
5. **Cover the whole fan-out.** A compound query gets broken into narrower sub-queries before
   an answer is assembled, and the page that appears across several branches is the one that
   gets used. G1's answer surface already handed you the SERP's own branches (`paa` +
   `related_searches`); G6 turns them into a named branch list and every branch gets a node or
   an explicit out-of-scope reason.
6. **Capsules, at roughly two-thirds.** Any heading that is or implies a question opens with a
   self-contained 20-25 word answer that makes complete sense quoted alone, with the heading
   removed. That is exactly how a featured snippet and an answer engine use it. Aim for 60-70%
   of body sections, not all of them: wall-to-wall Q&A reads mechanical, and the remaining
   third carries the explanation and the procedure that make the piece worth reading.
7. **Match the SERP's format, then beat its structure.** The consensus heading map from G4 is
   the floor: every subtopic the SERP consistently gives a heading, this page covers. Then word
   the headings better, add the table or list the format inventory says wins, and fix the
   pooled weaknesses. Emulate the shape; never mirror the phrasing.
8. **Plan the visual and the images at outline time.** Every article ships at least one ORIGINAL
   VISUAL we built, from figures that are already in the article. A `/blog/` article also needs
   a 1200 × 630 featured-image card, because a brand-new post has no featured image at all.
   Decide which node carries the visual and what it plots here; the writer builds both.

---

# STAGE G5 — The searcher-intent note  (two minutes, and it is not optional)

```
Before any structure exists, write down — in the conversation, in three to five sentences —
who is searching this keyword and what they are trying to achieve. Not a persona, not a funnel
label: the specific person and the specific job.

Answer these four:
  · WHO is typing this? (a practice owner comparing systems? a biller looking up a code mid-
    claim? a therapist looking for a form to use this afternoon?)
  · WHAT do they already know, and what would insult them to be told?
  · WHAT do they need in hand when they leave the page — a decision, a number, a document, a
    procedure, a code they can bill with confidence?
  · WHAT would make them go back to the search results? Name the specific failure.

Writing this down before drafting measurably improves the piece, and it is the shortest step in
the flow. It is also what the "customer fit" test in Originality-and-search-intent.md checks
against later, so keep it: G6 tests the outline against it and it goes into the brief verbatim.

For a TEMPLATE article the fourth answer is almost always "the template wasn't actually
usable". For a CODE article it is almost always "it didn't tell me what documentation the payer
wants". Say the specific version for THIS article.
```

---

# STAGE G6 — Outline planning  (PLANNING ONLY, no writing)

```
Produce the OUTLINE. Write NO article copy — short content-intent notes only.

FAN-OUT BRANCHES — do this FIRST, because it decides which nodes exist. Build the branch list
from three sources, in this order:
  1. `answer_surface.paa` — Google's own follow-up questions for this query. Highest value:
     these are not guesses, they are what the SERP is already asking.
  2. `answer_surface.related_searches` — the adjacent queries the same searcher runs next.
  3. Your own decomposition — read the main keyword as a compound question and split it the way
     an answer engine would: by AUDIENCE (solo practice vs multi-location), by CONSTRAINT
     (price, time, regulation, country), and by USE CASE.
Dedupe into a NAMED BRANCH LIST of 3-6 items. Branches that overlap across several sources
matter most. Do not turn every branch into an H2 — a branch can be answered inside a section, as
a capsule, or as an FAQ entry. What matters is that the answer is present and liftable.

STRUCTURE — build the tree in this order:
  1. Start from the G4 CONSENSUS HEADING MAP. Every subtopic the SERP consistently gives a
     heading gets a node here. That is the completeness floor; missing one is how a new page
     reads as thin next to the incumbents.
  2. Add a node for every GAIN IN item — the ledger's HAVE entries our plan does not yet cover.
     Each becomes a specific node, a figure inside a node, or a table column. Not "more detail".
  3. Add the GAIN OUT nodes — the ledger's ABSENT list, filtered to what we can supply honestly.
     This is REQUIRED CONTENT, not a bonus.
  4. Reorganize so the flow is more logical than the SERP's, directly addressing the WEAKNESSES
     TO BEAT. Word every heading better than the ranking pages did: clearer, more natural, never
     mirrored and never keyword-stuffed.
  5. Place the selected keywords. A keyword in a heading is an EXACT MATCH and the whole heading
     is reworded around it so it reads naturally — that is mandatory, not optional. A heading
     keyword is ALSO woven into that section's body text, so plan the content intent for both.
     use_as_faq keywords go into the FAQ block verbatim as questions.
  6. Walk the branch list against the final tree. Every branch has a node answering it, or a
     one-line reason it is out of scope. Do this LAST — merging and splitting nodes is what
     orphans a branch.

STRUCTURED DATA — where the G4 format inventory shows a table or list dominates, or a snippet is
up for grabs, plan a [TABLE] or [LIST] node and make it carry NEW useful information: an extra
column, a fresh comparison axis, real numbers competitors omit. Add the intended columns or list
items as short notes on the node. A table that restates a competitor's table is decoration.

SNIPPET TARGET — if `answer_surface.featured_snippet` exists, name the node competing for it and
REQUIRE ITS FORMAT to match the snippet's: a table snippet needs a [TABLE] node, a list snippet
a [LIST] node, a paragraph snippet a capsule. Matching the format is most of winning it, and a
page being written from scratch can be built in that format at no cost.

TITLE + H1 — plan both now. The exact main keyword goes at or near the START of each, and the H1
adds the concrete benefit the reader gets rather than stopping at the bare subject. The writer
owns the final wording and reads the meta-title guide for it; you name the query bucket the
title must own and the benefit the H1 must promise.

ANSWER-FIRST — for EVERY node whose heading is a question or implies one, note "answer in first
sentence" and WHAT that one-sentence answer is, so the writer leads with it rather than
inventing a preamble. Plan the intro to state the direct answer, and Key takeaways to carry it.

TYPE-SPECIFIC REQUIREMENTS — apply the one that matches the G0 article type:

  · LISTICLE — the outline MUST (a) name the actual picks/providers in Key takeaways;
    (b) place a comparison [TABLE] node immediately after the intro, before the first pick;
    (c) start the per-pick segments right after that table; (d) give every provider review a
    `Pricing` node at its end. Push any "how we chose / what to look for" material BELOW the
    picks or trim it. Plan the table's columns now — name plus the 2-4 axes that decide the
    pick. Comparison listicles are also the format answer engines cite most, so the table and
    the per-provider structure are the SEO work here, not decoration.
  · TEMPLATE ARTICLE — the download box is a required node with its own H2, placed per the
    document order. Plan what the template actually CONTAINS, field by field, because the
    failure mode for this type is a page that describes a template nobody can use. Plan a node
    that explains how to fill it in, and one that says when to use it.
  · CODE ARTICLE — the authority record from G4 is the spine: the official descriptor, status,
    effective dates, parent/child codes and the payer's documentation requirements each get a
    node or a table row. Plan a [TABLE] for the code's key facts. Code pages carry a link budget
    of 3 in-body links, all inside billing — the pillar, one subhub, at most one next step — so
    plan fewer link opportunities, not more. Never plan a price or a reimbursement figure that
    the authority does not state.
  · STANDARD GUIDE — no extra requirements beyond the branch list and the block contract.

REQUIRED BLOCKS — plan them as outline nodes NOW; do not leave them to be discovered during
writing. **Do not open `WordPress-blocks.md` to do this.** You decide WHICH block nodes exist
and roughly where; the writer owns their exact markup and reconciles your ordering against the
required document order in that file's §1. Plan by name: Key takeaways, the template download
box (template articles only), the Pabau section + its CTA block, Conclusion, Continue your
research, FAQ, and (listicles) a Pricing node per provider. Note for each:
- **Pabau section** — the topic-specific H2 (never "Why choose Pabau") and which Pabau workflow
  it covers for THIS article's purpose.
- **Conclusion** — the judgment it lands, plus its closing inline `/book-demo/` CTA link.
- **Continue your research** — max 5 targets, no wrapper H2, all inside the G2 cluster.
- **No video.** /generate never plans a YouTube embed. Adding one is a separate editorial call.

IMAGE PLANNING: mark nodes that should carry an image with an [IMG] note — what it shows and why
it helps. Then mark exactly ONE node [VISUAL]: the original visual we build, what it plots, and
which figures from THIS article it uses. Both come with the caption contract, which the writer
owns. A `/blog/` article also gets a featured-image card; note it, it is not a body node.

TWO-BAR CHECK — the outline must clear both before you proceed:
- INTENT (floor): the outline ANSWERS THE QUERY'S ACTUAL QUESTION, in the SERP-dominant format
  and depth you recorded in G1, and it satisfies the G5 searcher-intent note. Read the note back
  and check the four answers against the tree — especially "what would make them go back to the
  search results".
- ORIGINALITY NUGGET (priority): name at least one nugget no top-10 result has. Cross-check it
  against the G4 ledger: if a competitor already has it, it is not a nugget — pick another angle
  NOW, at planning time. Light→Medium is fine: a distinctive sort or framing, a practitioner
  angle, a proprietary checklist, real Pabau workflows.

  Two things make a nugget worth more, at no extra effort:
  · NAME IT. A nugget with an ownable two-to-four-word name — a named checklist, framework or
    sequence — is repeatable, and repeated across articles in the same words it becomes the term
    people and answer engines associate with us. If a previous Pabau article already named this
    framework, REUSE THAT NAME rather than inventing a synonym; the consistency is the whole
    mechanism.
  · MAKE IT THE GAIN OUT. The nugget and the information-gain GAIN OUT line are the same thing
    said two ways — the angle, and the concrete information the angle produces. State it as
    information: a number, a sequence, a real example, a decision rule. That is the form a
    competitor cannot paraphrase and an answer engine can quote.
  A nugget that survives as a claim in the intro and nowhere else is decoration. It has to be
  the substance of at least one section.

DURABILITY CHECK (stance #3): in one line, answer "what would it take to reproduce this page?"
If the honest answer is "a writer and the same five sources", go back and fix the plan before
the gate. Do not take this to the gate unfixed.

OUTLINE OUTPUT — the full heading tree in final document order, each node tagged:
  [NEW]        every body node (this is a new article; there is nothing else it can be)
  [IMG]        an image at/under this node (+ what it shows + why)
  [VISUAL]     the original visual we build (exactly one node; + what it plots + its figures)
  [CAPSULE]    opens with a 20-25 word self-contained answer (+ that answer, in one line)
  [SNIPPET]    the node competing for the featured snippet (+ the required format)
  [TABLE]      (+ the intended columns)
  [LIST]       (+ the intended items)
  [BLOCK]      a required block node (Key takeaways, download box, Pabau + CTA, Conclusion,
               Continue your research, FAQ, Pricing)
Tag roughly 60-70% of the body nodes [CAPSULE] — not all of them. Under the tree, list: the
keywords routed to IN-TEXT with their target section, the fan-out branch each node answers, the
GAIN IN / GAIN OUT lines, the nugget and its name, and the durability answer.
```

---

# STAGE G7 — The outline gate  ⟨HUMAN GATE #2 — always⟩

```
This gate is the cheapest quality control in the whole flow, and it is the reason the outline
exists before the prose. A model that writes structure and copy in one pass anchors every later
edit to a structure nobody chose: the human reviewing the finished draft is only ever editing
WITHIN the shape the model picked, which is not the same as choosing the shape. Fixing an
outline costs a sentence. Fixing an anchored article costs a rewrite that usually does not
happen.

PRESENT, in this order, and keep it SHORT — this is a decision aid, not a document:
  1. Route + the URL the post will have: `https://pabau.com/<prefix>/<slug>/`, and the term IDs.
  2. Main keyword, and whether it was locked or selected. One line on why, naming the title-gap
     verdict.
  3. The commission verdict from G2, in one line.
  4. The searcher-intent note from G5, in full — it is four short sentences.
  5. The heading tree, headings only, with the [BLOCK] / [TABLE] / [LIST] / [VISUAL] / [SNIPPET]
     tags. No content-intent notes, no entities.
  6. The originality nugget, its name, and the node that delivers it.
  7. The durability answer, in one line.
  8. The DEFERRED keywords — the secondary topics that need their own page later.

Then ONE AskUserQuestion:

    "Ready to write this article?"
    [Write it]          — I dispatch the writer and create the draft
    [Revise the outline] — tell me what to change and I'll re-plan, then ask again
    [Cancel]            — nothing gets created

On [Revise the outline]: take the user's instruction as a mandatory FLOOR — do everything it
asks, then add any further improvement it implies — re-run the affected parts of G6, present the
revised tree, and ask again. There is no cap on rounds.
On [Cancel]: delete the temp files (G10 step 2), report what the research found, and stop. The
research is not wasted: the commission verdict, the keyword and the ledger all go in the report.
On [Write it]: continue to G8.

Do not skip this gate because the outline looks obviously right. It is always asked.
```

---

# STAGE G8 — Write the brief

```
The outline is approved. Serialize everything the writer needs into ONE file and stop planning.

Write /tmp/gen-<run>-brief.md with the Write tool. It must be self-contained: the writer starts
with an empty context and cannot see this conversation. Include, in this order:

1. ARTICLE — the working title, the article TYPE, `status: draft`, and the ROUTE: the
   destination prefix, the exact category IDs and tag IDs to set, and the URL the post will have
   when published. State plainly: "CREATE a new post (POST), never update an existing one" and
   "status is draft and never changes".
2. SLUG — the `proposed_slug`, and the instruction to set it on creation. For a code article,
   repeat the naming convention and the sibling slug you checked it against.
3. MAIN KEYWORD — the one primary keyword, and the FIVE-SPOT placement: SERP title, H1, the
   FIRST SENTENCE of the body, the meta description, and the slug — exact match, reading
   naturally in each. Name the benefit the H1 must promise alongside it.
4. SEARCHER INTENT — the G5 note, verbatim, all four answers. Then the one-paragraph G1 note:
   the question the query actually asks, the SERP-dominant format, and the depth it rewards.
5. ANSWER SURFACE — the six lines from G1 step 1b: featured snippet (holder + FORMAT), AI
   Overview (present? cited domains? are we cited?), the PAA and related-search lines verbatim,
   the other SERP features, the title-gap verdict, and our current position.
6. FAN-OUT BRANCHES — the named list, each with the node that answers it, and each out-of-scope
   branch with its reason. Tell the writer every listed branch must be answered in its node, in
   a capsule, and that skipping one is a Skipped-line item.
7. SOURCE MATERIAL — the merged G4 SOURCE FACTS list, grouped by subtopic, with the
   CONFIRMED / CONTESTED / SINGLE marks and the credited source on every figure. Then the PATHS
   of the per-page files (`/tmp/gen-<run>-src-*.md`) and the authority file if one exists, and
   this instruction, in these terms: "Write from this material. Read the per-page files for
   detail the merge compressed. A figure with no source does not ship — trace it to its
   primary source and cite THAT at the point of claim, never the competitor page you found it
   on. Where the authority file contradicts a ranking page, the authority wins."
8. ENTITIES — the G4 entity list, grouped per outline node, with the variants for each.
9. SERP STRUCTURE PROFILE — the consensus heading map, the format inventory, the
   featured-snippet opportunity, the WEAKNESSES TO BEAT and the ANSWER SHAPE bar.
10. INFORMATION GAIN — the closed GAIN IN and GAIN OUT lines and the ledger's ABSENT list. Mark
   GAIN OUT as REQUIRED CONTENT, not background.
11. ORIGINALITY NUGGET — the nugget, its NAME if it has an ownable one, and which node delivers
   it. Mark it REQUIRED: the writer must not let it evaporate into generic copy, and must use
   the same name throughout rather than paraphrasing it. Add the durability answer beneath it.
12. FINAL OUTLINE — the approved heading tree in document order, every node with its tags, its
   grouped entities, its content intent, the fan-out branch it answers, and — for [CAPSULE]
   nodes — the one-line answer it opens with. Flag every question-heading that must be answered
   in its first sentence.
13. KEYWORD PLACEMENT — every selected keyword with its role (heading / in-text / FAQ) and its
   target node. Exact-match rule stated. Note that a heading keyword also goes in that section's
   body text.
14. BLOCK NODES — which required blocks you planned and where, and the note that the writer owns
   their markup and final ordering per WordPress-blocks.md §1.
15. LINKS — the CLUSTER and PILLAR from G2 check 4, and the link budget: at most 5 in-body
   editorial links (3 on a code page), exactly one of them the cluster's pillar, all inside the
   cluster. Tell the writer to resolve targets with `cluster_lookup.py targets --cluster <id>`
   and to read `3-links.md` before placing any link.
16. VISUALS — the [VISUAL] node, what it plots and which of the article's figures it uses; every
   [IMG] node; and, for a `/blog/` article, that the post has NO featured image and needs a
   1200 × 630 brand card built and attached via `featured_media`.

Keep it dense and factual — it is instructions, not prose. Do NOT restate block markup; the
writer reads the contract. Then stop. G9 dispatches the writer; you write no article copy at any
point.
```

---

# STAGE G9 — Dispatch the writer

```
Spawn ONE `article-generator` subagent. It writes every section, enforces the block contract,
builds the visual and the featured image, clears the sentence gate, and CREATES the post as a
draft in a single POST. You do none of that and you never see the article body.

Pass it exactly this — paths and short facts, nothing bulky:
- the brief path: /tmp/gen-<run>-brief.md   (tell it to read this FIRST)
- the source file paths: /tmp/gen-<run>-src-*.md and /tmp/gen-<run>-authority.md if it exists
- the article type, the route prefix, and the term IDs to set
- the proposed slug

Then wait. The writer reads its own guides, writes from the harvested material, and returns a
change-log with the new post ID. Do NOT re-explain the block contract, the style guide, the
sentence gate or the generation stance in the dispatch message — the agent carries all of it,
and restating it here pulls into this context the very material the split exists to keep out.

If the writer reports it could not complete something under "Skipped", relay that verbatim in
G10. Do not fix it here by loading the guides and editing the article yourself — that undoes the
whole arrangement. If a genuine re-run is needed, dispatch a fresh `article-generator` with the
same brief, the existing post ID, and a note on what to correct.

Keep the returned change-log. It is the /generate half of the G10 report.
```

---

# STAGE G10 — Verify the route, name the inbound links, hand off to /fact

```
1. CONFIRM THE CREATE. The writer reports the new post ID and a 2xx. Verify three things
   yourself, in one call — the route is the one thing a reader will notice and the one thing the
   writer cannot see, because a draft's `link` is only `https://pabau.com/?p=<id>`:

     GET /wp-json/wp/v2/posts/<ID>?context=edit&_fields=id,slug,status,categories,tags,featured_media

   Assert, and say each result in one line:
   · `status == "draft"`. If it is anything else, say so LOUDLY — that is the one failure in
     this flow that puts content in front of the public, and it needs fixing before anything
     else. Set it back to draft immediately.
   · The ROUTE terms are present and correct for the destination: tag 1382 for `/templates/`;
     category 1549 + a subcategory for `/diagnostic-codes/`; category 1433 + a subcategory for
     `/procedure-codes/`; NONE of those for `/blog/`. A `/blog/` article carrying a stray
     routing term will publish to the wrong folder — check for that specifically.
   · Category 1 (`Uncategorized`) is absent, and at least one real topic category is present.
   · `slug` matches the brief's `proposed_slug`.
   · For a `/blog/` article, `featured_media` is a non-zero ID.
   Then state the URL the post will have when published: `https://pabau.com/<prefix>/<slug>/`.

2. NO INDEXING PING, EVER. `bin/index_ping.py` submits an ALREADY-PUBLIC URL to Google. This URL
   does not exist and will 404. The script refuses a non-200 URL, but do not rely on that — do
   not call it. There is likewise no GSC baseline to write: the page has no history to measure
   against. Its equivalent is step 3.

3. WRITE THE COMMISSION RECORD. This is the durable output of a /generate run, and it is what
   stops the NEXT run from writing this page again.

     mkdir -p "$HOME/.claude/factcheck-flow/cache/generated"

   Write `<slug>-<YYYY-MM-DD>.md` there (the final slug, not the run token) with the Write tool, under 20 lines, holding: the date,
   the post ID, the route and the future URL, the main keyword and how it was chosen (locked or
   selected, plus the title-gap verdict), the commission verdict from G2 and any competing URL,
   the cluster and pillar, the nugget and its name, the DEFERRED keywords, and the corner-stone
   links from step 4. Add a REVIEW line: "not published — publishing is a human decision".

4. NAME THE CORNER-STONE INBOUND LINKS — report-only, and for a new page it is the single
   highest-value thing this run produces. A page that already ranks and earns clicks generates
   authority by ranking, with no backlink involved, and an in-body link from it into this
   article channels some of that authority here. A brand-new page has none of its own, so this
   is what moves it from crawled-but-not-indexed to actually ranking. Every new page should have
   at least one inbound internal link from the moment it publishes — an orphan page starts from
   zero and stays there.

     python3 "$HOME/.claude/factcheck-flow/bin/cluster_lookup.py" targets \
             --cluster <the G2 cluster id> --folder "/<prefix>/" --sort pr --limit 25

   Keep 3-5 pages that are (a) in the SAME cluster — the cluster wall binds link planning as
   much as link writing, (b) already ranking and earning clicks, not merely published, and
   (c) not already carrying a heavy load of outbound links (a page past roughly 50 in-body links
   passes very little to any single destination, and overloading one strong page can cost it its
   own ranking). For each: the source URL, the section the link would sit in, and a proposed
   anchor. Vary the anchors, and never propose more than one new link per source page.

   **Never edit those pages.** /generate creates ONE article; inbound links are edits to other
   pages and belong to David or the interlinking project. Name them and stop.

5. CLEAN UP the run's temp files — everything matching `/tmp/gen-<run>-*`: -serp.json,
   -kw.json, -cannibal.json, -cannibal-main.json, -brief.md, every -src-*.md, -authority.md,
   and the body file the writer left behind.

6. HAND OFF TO /fact — IN A FRESH SUBAGENT, NOT IN THIS CONVERSATION. /generate always finishes
   by handing off to /fact, including after a Cancel at G7 produced nothing (in which case there
   is nothing to hand off — say so and stop). /fact re-runs the fact-check, editorial and block
   passes independently, and on a brand-new article that independent check matters more than it
   does on a refresh: nothing in this flow has verified the finished prose against its sources.

   Do NOT run /fact inline here. By this point this context holds the research, the keyword work,
   the source profile, the outline and the writer's change-log — and /fact is itself a
   multi-stage orchestration with its own fan-outs and human gates. Running it on top of this
   context re-reads all of the above on every one of its turns, for no benefit.

   The cheapest and most correct hand-off is to tell the user plainly: "The draft is created and
   saved at post <ID>. Run `/fact <id>` next — in a NEW session, so it starts with a clean
   context." /fact's Stage 2 triage gate asks the human about factual errors, and a subagent
   cannot run that gate. Only dispatch a subagent version when running unattended, and have it
   surface any ASK findings in its report rather than deciding them itself.

7. PRODUCE ONE COMBINED REPORT: the writer's change-log plus these six lines, which are the
   /generate half of the value and exist nowhere else:
   - `Created:` post ID, status draft, and the URL it will have when published.
   - `Route:` the destination and the exact terms set, with the assertion result from step 1.
   - `Commission:` the G2 verdict, and the competing URL if one was found.
   - `Corner-stone links:` the 3-5 source pages from step 4 with their proposed anchors, marked
     clearly as not-yet-done. Say that a new page with no inbound link starts from zero.
   - `Deferred keywords:` the secondary topics that need their own page later. These are the
     next /generate runs, not sections of this one.
   - `Ownership findings:` every keyword vetoed as owned elsewhere, with the competing URL.
     These are edits to OTHER pages — name them, never make them.
   End with two reminders: the article is a DRAFT and publishing is a human decision, and after
   publishing someone should purge the WP Rocket cache for the URL.
```

---

## Notes / defaults (resolved)

- Division of labour: G5–G8 PLAN (this context, no writing guides loaded); G9 WRITES (the
  `article-generator` subagent, which loads the guides and the source files); G10 verifies and
  hands off. The writing guides are ~40k tokens and the source reports several thousand more —
  kept out of here, they are read once by an agent that discards them.
- Save cadence: exactly one CREATE, made by the `article-generator`. This conversation never
  writes to WordPress; it only reads back the created post to verify the route.
- Two gates and no more: the G2 commission gate fires only on a blocker; the G7 outline gate
  fires always. Everything else is automatic, because a new article has no performance history
  for a human to weigh — only the decisions of whether to write it and what shape it takes.
- What /generate deliberately does NOT do, and reports instead: publish anything, edit any other
  page (corner-stone inbound links, the competing page in a commission finding), submit anything
  to the indexing API, or write the secondary keywords into this article rather than deferring
  them to their own pages.
- Volume discipline, at the program level rather than per run: sustained publishing above
  roughly 100 new articles a month reads as spam regardless of how carefully each one is
  written, and a human pass on each is what keeps the rest safe. /fact is that pass. If
  /generate is being run in a batch, the batch is the thing to size, not the article.
- The commission records in `cache/generated/` are the only durable output of a run. They are
  what makes the NEXT run able to see that this page already exists, so writing one is not
  book-keeping — it is the check that keeps the site from competing with itself.
