# /SEO — Article Optimization flow

> Executed by the `/SEO` command (`commands/SEO.md`), which asks "Is this a draft?" as its
> first action and then runs the stages below. This file is auto-synced from the
> factcheck-flow repo, so edits here propagate to everyone on their next session.

---

## Two branches + selection routing

The FIRST thing /SEO does is ask **"Is this a draft?"** (Stage 0), which picks the branch:

- **Draft → QUICK / AUTOMATIC.** After "Yes", everything runs automatically; Claude makes the
  keyword judgment calls itself using David's documented logic (this brief + the video
  transcript). No GSC list. Ends by saving and running **/fact**. (A post someone published
  by accident is still treated as a draft here — content only; never change publish status.)
- **Published update → MANUAL.** After "No", Claude also pulls the **GSC** 4th list and, for
  keyword selection, writes an Obsidian checklist to the Desktop for David to tick. (GSC is one
  of five lists; the Highly Relevant list appears in both branches.)

Selection routing at Stage 3 depends on how many keywords the data actually yields:
- **> 10 total:** draft = auto-select; published = Desktop document.
- **≤ 10 total (or all lists empty):** override both paths with the Claude Code multiple-choice
  picker (AskUserQuestion), ending in a **"Do you want to proceed with optimization?"** gate
  that can cancel and skip straight to /fact.

Every path ends the same way: save → (delete the temp doc if one was made) → run **/fact**.
Human gates use strict JSON contracts (below), so these prompts also drop into a future modal
app with no rewrite.

Stages: **S0** draft-check + setup → **S1** SERP pick → **S2** build lists → **S3** keyword
selection (routing above) → **S4** Outline → **S5** entities → **S6** group entities →
**S7** main-keyword swap → **S8** optimize + write → **S9** save, cleanup, hand off to /fact.

---

## CONFIG (tweak these; referenced by the prompts below)

```yaml
location_name: "United States"
language_code: "en"
search_engine: "google"

# Keyword thresholds (David's rules)
difficulty_soft_ceiling: 10 # PREFER ≤ 10; fill from here first. NOT a hard cap — see Stage 2.
difficulty_priority: 5      # 0–5 difficulty takes priority
volume_ideal: 100           # prefer ≥ 100
volume_ok: 50               # acceptable ≥ 50
volume_floor: 20            # normal floor; only the Tier-3 last resort may go below (Stage 2)

# List sizes
list_target_len: 20         # each list should reach 20 keywords if the data allows
competitor_top_n: 20        # top keywords per selected competitor page
serp_depth: 10              # organic results pulled for the SERP-pick gate

# Scarcity fallback (Stage 3 routing)
scarce_total_threshold: 10  # ≤ this many keywords TOTAL → Claude Code picker + proceed gate

site_domain: "pabau.com"    # used to identify our own result + our own ranked keywords

# Google Search Console (LIVE — published articles only; see Stage 0 draft check)
gsc_query_script: "$HOME/.claude/factcheck-flow/bin/gsc_query.py"  # portable helper (ships with command)
gsc_key: "$HOME/.claude/factcheck-flow/gsc-key.json"  # service-account JSON (SECRET; not in repo). Override: $PABAU_GSC_KEY
gsc_property: "https://pabau.com/"   # URL-prefix property. Override: $PABAU_GSC_PROPERTY
gsc_window_days: 90                  # trailing window for the query pull
gsc_top_n: 20                        # queries to pull, ordered by clicks desc
```

---

## Guides every writing/optimizing stage MUST obey

Before any stage that changes headings, titles, meta, or body text (S4, S7, S8), read and
comply with — these are the source of truth and override anything below on voice/structure:

- `~/.claude/factcheck-flow/prompts/2-editorial.md` — editorial standards (fluff/AI-tell
  removal, US English, structure H1 > Key Takeaways > Intro > H2, paragraph/sentence
  limits, meta description ≤140 chars, capitalization, Yoast, categories/tags).
- `~/.claude/factcheck-flow/guides/Meta-title-best-practices.md` — SERP title rules.
- `~/.claude/factcheck-flow/guides/Pabau-style-guide.md` — voice, US/UK terms, glossary.
- `~/.claude/factcheck-flow/guides/About-Pabau.md` — product family, naming rules, pricing.
- `~/.claude/skills/wordpress-access/SKILL.md` — how to read/write the article (REST API,
  `context=edit`, PUT only changed fields, draft stays draft, append-only categories/tags,
  Yoast focus keyphrase via the post `meta` field).

Non-negotiables carried over from `/fact`: introduce Pabau on first mention; qualify product
names once; never "Pabau Connect" externally (say "online booking"); no feature gating; no
free trial; lead with outcomes; headings must read naturally (no keyword stuffing).

---

# STAGE 0 — Draft check, setup & fetch

```
You are running the /SEO optimization flow for a single article: $ARGUMENTS
(one WordPress URL or post ID). If none was given, ask for it and stop.

1. DRAFT CHECK — the /SEO command asks this as its VERY FIRST action, before any file reads:
     "Is this a draft, or a published article being updated?"
   Use that answer as is_draft (true/false); if it is somehow unset, ask it now before any
   data work. It gates the GSC list (Stage 2, list D):
     - is_draft = true  → do NOT run GSC (a draft has no search history yet); only 3 lists.
     - is_draft = false → build the GSC "already-ranking" list (list D) in Stage 2.
   When you fetch in step 3, cross-check the WordPress `status` field. If the human's answer
   and the WP status disagree, flag it and trust the human's answer.
2. Load CONFIG and read all guides listed in "Guides every writing stage MUST obey".
3. Resolve the article via the wordpress-access skill. Fetch it with context=edit so you
   get raw Gutenberg block markup. Capture:
   - post ID, slug, full URL, status (draft/publish), categories, tags
   - H1, and the full heading tree (H2/H3/H4) in document order
   - the body blocks (so you can later place content precisely)
   - current Yoast focus keyphrase, SEO/meta title, and meta description
4. Determine the CURRENT MAIN KEYWORD: use the Yoast focus keyphrase if present; else infer
   from the H1 + slug. State it explicitly.
5. Classify the ARTICLE TYPE (affects editorial + meta-title rules): listicle, code article
   (diagnostic/procedure code), template article, or standard guide.
6. Emit a short setup summary: main keyword, type, status, is_draft, heading count. No changes.
```

---

# STAGE 1 — SERP fetch → competitor pick  ⟨HUMAN GATE #1⟩  (your step 2)

```
Goal: let the user choose which SERP results to mine for Competitor Keywords. These SAME
URLs are reused for entity NLP in Stage 5, so choose once.

1. Call serp_organic_live_advanced:
     keyword = CURRENT MAIN KEYWORD, location_name/language_code/search_engine from CONFIG,
     depth = serp_depth.
2. Keep ORGANIC results only. Drop: our own domain (site_domain), pure aggregators/SERP
   features, and anything paywalled/login-gated you can't open. Keep the ranked order.
3. Build the SERP-pick JSON (Gate #1 OUTPUT):

   {
     "main_keyword": "<string>",
     "serp": [
       {"rank": 1, "title": "<title>", "url": "<full exact live page URL, incl https://>"},
       ...
     ]
   }

4. PRESENT for selection — THIS EXACT FORMAT, no exceptions:
   Output a NUMBERED LIST where EVERY line is a CLICKABLE MARKDOWN LINK to the exact live
   ranking page. One clickable link per SERP result — all of them (however many rank).
   - DO NOT render a table.
   - DO NOT show the domain, ever.
   - DO NOT print a bare/plain URL — it MUST be markdown link syntax so it is clickable.
   - The link target MUST be the exact ranking page URL (the organic item's `url`), never the
     homepage or the domain root.

   Format each line exactly like this:

       1. [<page title>](<full exact live https:// URL>)
       2. [<page title>](<full exact live https:// URL>)
       … continue for every ranking result …

   Then ask:
     "Which of these should I use for competitor keywords + entity analysis? (e.g. 1,2,5)".
5. Record the Gate #1 SELECTION:

   { "selected_competitor_urls": ["<url>", "<url>", ...] }

   Require at least 1. Do not proceed until selection is received.
```

---

# STAGE 2 — Build the four keyword lists (automated)

```
Produce FIVE candidate lists (four discovery lists + GSC). For every candidate keyword attach
difficulty, search volume, and search intent — EXCEPT the Highly Relevant list (raw top-20 by
relevance, unfiltered) and the GSC list (its own click/impression/position metrics). Then
filter and rank per David's rules. Do NOT ask anything yet.

── Data sources ──────────────────────────────────────────────────────────────
A. RELATED KEYWORDS  → dataforseo_labs_google_keyword_ideas (seed = main keyword) AND
   dataforseo_labs_google_related_keywords (seed = main keyword, depth 2).
   Purpose: topically relevant terms that are CONCEPTUALLY DIFFERENT from the main keyword.
B. MAIN KEYWORD VARIATIONS → dataforseo_labs_google_keyword_suggestions (seed = main keyword).
   Purpose: terms that rephrase/extend the main keyword.
C. COMPETITOR KEYWORDS → dataforseo_labs_google_ranked_keywords for EACH selected competitor
   URL; take that page's top competitor_top_n by organic traffic/position; pool + dedupe.
D. ALREADY-RANKING — GSC, PUBLISHED ARTICLES ONLY (this is the 4th list).
   SKIP ENTIRELY if is_draft == true (Stage 0). Otherwise pull the queries the LIVE article
   already ranks for from Google Search Console (first-party data) by RUNNING the shipped
   helper (it handles service-account auth via gsc_key, scope webmasters.readonly, property
   gsc_property):
       python3 "$HOME/.claude/factcheck-flow/bin/gsc_query.py" \
               --page "<full article URL>" --days 90 --limit 20
   It prints JSON — { page, start, end, queries: [{query, clicks, impressions, position}, …] } —
   already sorted by clicks desc (top gsc_top_n).
   HARD REQUIREMENT: GSC is mandatory on the PUBLISHED path. If the helper exits non-zero
   (missing key, PyJWT not installed, or an API error), STOP and tell the user GSC isn't set up
   — do NOT silently continue without this list. Fix path: place the key at gsc_key or set
   $PABAU_GSC_KEY, and install PyJWT (`python3 -m pip install --user pyjwt`). Drafts never call it.
   CLICKS + IMPRESSIONS + AVERAGE POSITION are the primary columns ("how many clicks each keyword
   gets"). Do NOT apply the difficulty/volume filters here — we already rank for these. Instead
   FLAG optimization opportunities:
     · queries with high impressions but weak position (≈ pos 4–15), and/or
     · queries NOT currently reflected in any article heading (exact-match gap).
E. HIGHLY RELEVANT KEYWORDS → dataforseo_labs_google_keyword_ideas (seed = main keyword),
   using DataForSEO's DEFAULT relevance ordering. Take the top list_target_len (20) purely BY
   RELEVANCE. This list has NO difficulty/volume filtering and NO fill tiers — just the 20 most
   relevant terms (show difficulty/volume as info only). Only the always-on hygiene applies
   (drop the bare main keyword, drop terms already used as an exact-match heading, dedupe, stay
   on-topic). Overlap with other lists is fine — tag it. Present for BOTH drafts and published.

── Enrichment ────────────────────────────────────────────────────────────────
- Difficulty: dataforseo_labs_bulk_keyword_difficulty (batch).
- Volume + CPC + trend: dataforseo_labs_google_keyword_overview.
- Intent: dataforseo_labs_search_intent. Flag intent that mismatches the article's intent.

── Classification rule (RELATED vs VARIATION) ───────────────────────────────────
Tokenize the main keyword into content words (ignore stopwords). For a candidate:
- It is a **VARIATION** if it keeps the main keyword's core head term(s) — a reorder, a
  synonym swap, a plural, or the main keyword PLUS a qualifier.
    · sub-flag "qualifier_variation" when the extra words name a USER GROUP or USE CASE
      (e.g. "…for women", "…for beginners", "…for small practices"). These are HIGH VALUE —
      surface them near the top of the Variations list.
    · a "reorder/synonym" variation (e.g. main "best VPN for china" → "best china vpn") is
      kept so headings can vary wording without spamming the exact main keyword.
- It is **RELATED** only if it DROPS the main keyword's core head term and names a distinct
  entity/subtopic in the same domain (main "best cloud storage" → "google drive"). Prefer
  low lexical overlap + high topical relevance ("completely different" = gold).
- If a candidate is essentially the exact main keyword (or a trivial stopword/plural diff),
  DISCARD it — no value.

── Filtering & fill-to-20 (DataForSEO lists A/B/C; lists D (GSC) and E (Highly Relevant) keep their own rules) ──
Goal: each list should reach list_target_len (20). Volume preference ALWAYS holds: ≥ 100
ideal > 50–99 acceptable > 20–49 usable only when nothing better exists. Fill via escalating
tiers, stopping the moment a list hits 20:
  Tier 1 — difficulty ≤ difficulty_soft_ceiling (10), sorted 0–5 first then 6–10; apply the
           volume preference above; volume ≥ volume_floor (20).
  Tier 2 — if still < 20: the ceiling is NOT a hard cap — add the best remaining candidates
           with difficulty ABOVE 10 (lowest difficulty first, then volume desc), volume ≥ 20.
  Tier 3 — if STILL < 20 (or the list is empty): LAST RESORT — add relevant keywords that do
           NOT meet the difficulty/volume criteria, including volume < 20 and any difficulty,
           best available first.
If even Tier 3 yields few, KEEP WHAT YOU HAVE — a short/empty list is valid and drives the
Stage 3 routing. Do not invent keywords.
Always applied (every tier): drop keywords the article already targets as an exact-match
heading; dedupe within and across lists (cross-list dupes stay in the most useful list —
Related > Variation — note the overlap); drop off-topic/off-intent/brand terms that don't fit
Pabau (borderline → keep, tag "review"). Relevance is NEVER relaxed, even in Tier 3.

── Ranking within each list ─────────────────────────────────────────────────────
Primary: difficulty band (0–5 first, then 6–10, then the Tier 2/3 fill in that order).
Secondary: volume desc. Target list_target_len (20). For each kept keyword, record a one-line
"why" (e.g. "distinct entity, diff 3 / vol 210", "qualifier variation: women", "competitor
rank 4 also targets this").

── New-main-keyword candidate detection ─────────────────────────────────────────
If any candidate (usually a Variation or Competitor keyword) has notably higher volume than
the current main keyword AND semantically contains/supersedes it, tag it
"new_main_candidate": true so the user sees it as a promotion option at the gate.

Output the four enriched, filtered, ranked lists as the Gate #2 payload (next stage).
```

---

# STAGE 3 — Keyword selection  ⟨HUMAN GATE #2⟩  (your step 3)

```
Gate #2 OUTPUT payload (what the UI/table is built from):

{
  "main_keyword": "<current>",
  "lists": {
    "related":       [ {"keyword": "...", "difficulty": 3, "volume": 210, "intent": "informational", "why": "...", "new_main_candidate": false}, ... ],
    "variations":    [ {"keyword": "...", "difficulty": 5, "volume": 140, "intent": "...", "why": "qualifier: women", "new_main_candidate": false}, ... ],
    "competitor":     [ {"keyword": "...", "difficulty": 2, "volume": 300, "intent": "...", "why": "ranks #4 for competitorX", "new_main_candidate": true}, ... ],
    "highly_relevant":[ {"keyword": "...", "difficulty": 12, "volume": 40, "intent": "...", "relevance_rank": 1}, ... ],
    "gsc_ranking":    [ {"keyword": "...", "clicks": 2077, "impressions": 26170, "position": 8.0, "opportunity": "high impr / weak pos", "in_heading_already": false}, ... ]
  }
}

Note: "highly_relevant" is ALWAYS present. "gsc_ranking" is present ONLY for published articles
(is_draft == false). Drafts show four lists (related / variations / competitor /
highly_relevant); published shows five.

── ROUTING: how selection happens (by keyword count × draft flag) ──
Compute total_kw = keywords across ALL lists.

CASE A — total_kw == 0 (all lists empty):
  Nothing to optimize. Skip selection; go straight to the PROCEED GATE.

CASE B — total_kw ≤ scarce_total_threshold (10):
  Too few to justify a document. Use the Claude Code picker (AskUserQuestion), batches of ≤4
  keywords. Present each keyword as its OWN multi-select question with exactly three options:
  [use in text] / [use in heading] / [set as NEW MAIN]. There is NO skip — leaving all three
  unchecked means the keyword is NOT used. If ANY box is checked the keyword IS used: "use in
  heading" = heading AND text; "set as NEW MAIN" = H1 + intro + meta description + SEO title
  (Stage 7). At most ONE new main across all keywords. This OVERRIDES both the auto and document
  paths — it runs even for drafts. Then the PROCEED GATE.

CASE C — total_kw > 10:
  • is_draft == true  → AUTOMATIC SELECTION (no human). Apply David's logic:
      - take the strongest keywords per list in Stage 2 priority order;
      - keep RELATED only if conceptually distinct from the main keyword;
      - favor qualifier variations (user-group / use-case) in Variations;
      - if a new_main_candidate clearly beats the current main keyword on volume AND
        supersedes it, set new_main_keyword; otherwise keep the current main keyword;
      - set use_in_heading = true where the keyword maps cleanly to a heading topic.
    Continue to Stage 4 (no proceed gate — there is plenty to do).
  • is_draft == false → DOCUMENT PATH: write the Obsidian checklist to the Desktop, post the
    bold link block as the LAST thing in the reply, and STOP until David saves. Then read the
    file and parse ticked boxes into the SELECTION JSON.

── PROCEED GATE (Cases A and B only) ──
Final question of this step, via AskUserQuestion:
    "Do you want to proceed with optimization?"  → [Proceed] / [Skip to /fact]
If Skip (or Case A with nothing selected): do NOT optimize — jump straight to Stage 9 (/fact
handoff). This is the escape hatch for when there aren't enough keywords to matter.

── DESKTOP DOCUMENT (Case C, published) ──
Write an Obsidian-compatible Markdown file to:  ~/Desktop/SEO-<slug>-keywords.md
One section per list; each keyword is a clickable checkbox with two nested flag checkboxes,
metrics shown inline:

    ## Related keywords
    - [ ] **google drive**  ·  diff 3 · vol 210 · informational
        - [ ] use in heading
        - [ ] set as NEW MAIN keyword
    ## Highly relevant keywords
    - [ ] **appointment reminders**  ·  relevance #1 · diff 12 · vol 40
        - [ ] use in heading
        - [ ] set as NEW MAIN keyword
    ## Already ranking (GSC)
    - [ ] **medical certificate generator**  ·  2077 clicks · 26170 impr · pos 8.0
        - [ ] use in heading
        - [ ] set as NEW MAIN keyword

Read-back parse: top box ticked = selected; nested "use in heading" = use_in_heading; nested
"NEW MAIN" = new_main_keyword (enforce at most ONE across the whole file).
The bold link block MUST be the very LAST thing in the reply, exactly:

    **Article title:** <title>
    **Article link:** <url>
    **Keyword lists:** <file:// path to the .md on the Desktop>

── Gate #2 SELECTION (produced by whichever path ran) ──
{
  "selected": [ {"keyword": "...", "list": "related|variation|competitor|highly_relevant|gsc_ranking",
                 "use_in_heading": true, "new_main_keyword": false}, ... ],
  "new_main_keyword": "<the one keyword flagged new main, or null>"
}
Selection semantics (apply in EVERY path — auto, document, picker):
- selected, use_in_heading = false → weave the keyword into BODY TEXT only.
- selected, use_in_heading = true  → place it as an EXACT-MATCH heading AND weave it into that
  section's body text (a heading keyword ALWAYS also appears in text).
- new_main_keyword → apply in the H1, intro text, meta description, and SEO title (Stage 7);
  implies use_in_heading. At most ONE new_main_keyword.
- a keyword with nothing selected is NOT used.
```

---

# STAGE 4 — Outline planning  (your step 4 — PLANNING ONLY, no writing)

```
Using the Gate #2 selection + the existing heading tree, decide placement for EACH selected
keyword. Produce an OUTLINE; write NO article copy yet (only short content-intent notes).

Placement decision per selected keyword:
1. TOPIC ALREADY COVERED, heading not an exact match → reword that heading so it contains
   the keyword as an EXACT MATCH, rewritten to be fully grammatical and natural (never a
   shoehorned exact-match fragment). Record old → new heading.
2. TOPIC NOT COVERED → add a NEW H2 or H3 (pick the level that respects hierarchy and fits
   the surrounding structure) whose text is the keyword as an EXACT MATCH, grammatical.
   Note the content intent (what the section will cover) — no prose yet.
3. use_in_heading = true but no sensible heading placement exists → mark the keyword for
   IN-TEXT insertion instead, and note the target section.
4. use_in_heading = false → mark for in-text insertion in the most relevant section.

Exact-match rule: any keyword placed in a heading must appear verbatim; you MUST reword the
whole heading around it for grammar/sense (this is mandatory, not optional). A heading keyword
is ALSO woven into that section's body text in S8 — plan each section's content intent so both
the heading and its text carry the keyword naturally.

If new_main_keyword is set: plan the new H1 (exact-match, grammatical) and note that S7 will
also update meta/intro/SEO title/focus keyphrase.

Structure compliance (per 2-editorial.md): keep H1 > Key Takeaways > Intro > H2 order; valid
hierarchy H1>H2>H3>H4; headings must read naturally; no keyword stuffing.

OUTLINE output — the full heading tree in final document order, each node tagged:
  [UNCHANGED]  existing heading kept as-is
  [OPTIMIZED]  existing heading, shown in its NEW exact-match form (+ old form)
  [NEW]        new heading (+ target keyword + one-line content intent)
  [H1-NEW]     new H1 (only if main keyword changed)
Also list keywords routed to IN-TEXT with their target section.
This OUTLINE is the reference object for S6 (entity grouping) and S8 (writing).
```

---

# STAGE 5 — Entity extraction (NLP over selected SERP pages)  (your step 5)

```
Open EACH Gate #1 selected_competitor_url (use on_page_content_parsing, or WebFetch with a
high token limit). Extract the MAIN CONTENT text (ignore nav, footer, cookie/CTA boilerplate).

Build an ENTITY LIST of the salient words and phrases that recur ACROSS PAGES:
- Keep a term only if it appears on ALL selected pages, or at minimum on ≥ 2 of them.
- Match SEMANTICALLY, not by exact string — group synonyms/paraphrases that mean the same
  thing into one entity (record the variants).
- Prefer domain nouns, named concepts, features, sub-topics, and multi-word phrases.
- IGNORE stopwords and generic connective/common speech ("and", "the", "however", etc.) and
  site-brand chrome.

ENTITY LIST output — for each entity: canonical label, the variant spellings/synonyms seen,
and page coverage count (e.g. "3/3 pages"). Order by coverage desc, then salience.
```

---

# STAGE 6 — Group entities under the Outline  (your step 6)

```
Map each ENTITY to the OUTLINE heading it is most semantically relevant to. An entity may
map to more than one heading if genuinely relevant to each.

- Attach entities to headings ([UNCHANGED], [OPTIMIZED], [NEW] alike).
- Entities that fit no specific heading but are on-topic → pool under "Intro / general".
- Entities that don't fit the article's scope at all → drop (note them under "unused").

Output: the OUTLINE, now with a bullet list of grouped entities beneath each heading. These
grouped entities are the raw material S8 uses to write new sections and to enrich existing
copy. Still no prose written.
```

---

# STAGE 7 — Main-keyword swap (only if new_main_keyword is set)  (your step 7)

```
Skip this stage entirely if new_main_keyword is null.

Otherwise update, in line with the guides (editorial + meta-title + style + About-Pabau):
1. H1 → the new main keyword as an exact match, reworded to be natural/grammatical.
2. Yoast focus keyphrase (post meta) → the new main keyword.
3. SEO/meta title → re-optimize per Meta-title-best-practices.md (listicle number if
   applicable, current year if time-sensitive, match micro-intent, differentiate in SERP,
   lead with the pain point). Don't just mirror the H1 if a stronger SERP title exists.
4. Meta description → rewrite to answer the searcher query as an article excerpt, ≤140 chars.
5. Intro text → rework so the new main keyword appears naturally in the first paragraph;
   keep the OLD main keyword nearby as a secondary keyword if still valuable (don't shoehorn).

Do not write to WordPress yet — hold changes for the single save in S8 (or save here and
again in S8; keep drafts as drafts, published as published either way).
```

---

# STAGE 8 — Optimize & write to WordPress  (your step 8)

```
Now produce and apply the actual copy, using the OUTLINE + grouped entities + S7 changes.
EVERYTHING written here must comply with 2-editorial.md, the style guide, About-Pabau, and
Meta-title-best-practices.md.

For each OUTLINE node:
- [OPTIMIZED] heading → apply the new heading text; then rewrite that section's existing
  copy to naturally weave in the grouped entities (don't just append; integrate).
- [NEW] heading → write new section copy from scratch covering the content intent, using the
  grouped entities. Match article voice; lead with the outcome; introduce/qualify Pabau
  correctly on first mention.
- [UNCHANGED] heading → only enrich the body with any grouped entities that clearly improve
  it; otherwise leave it.
- IN-TEXT keywords → insert into the most relevant existing sentence/section naturally.

Hard rules:
- Keywords placed in headings are EXACT match; headings still read naturally (reword fully).
- A keyword placed in a heading MUST also appear in that section's body text (heading + text).
- A new main keyword must land in the H1, intro, meta description, and SEO title (via S7).
- No keyword stuffing in body or headings; every sentence must carry information (no fluff).
- Preserve existing Gutenberg block structure unless a change requires otherwise; fix
  malformed HTML/FAQ blocks per editorial rules. Respect paragraph (≤4 lines/≤60 words) and
  sentence-length limits; convert 3+ clause lists to WordPress list blocks.
- If the SERP shows a featured-snippet opportunity, format the relevant answer as both a
  short paragraph and a list to compete for it (from the transcript's snippet tactic).

Save via wordpress-access: PUT only changed fields (content, title, excerpt/meta description,
Yoast focus keyphrase meta, categories/tags — append-only, remove "Uncategorized"). Draft
stays draft; published stays published.

CHANGE-LOG (hold for the S9 combined report): main keyword (old→new if changed), headings
added/optimized, keywords placed (heading vs in-text), entity themes woven in,
meta/title/description changes, categories/tags added.
```

---

# STAGE 9 — Save, cleanup, hand off to /fact

```
1. Ensure all S7/S8 changes are saved to WordPress. Draft stays draft; a post someone
   accidentally published is still handled as draft content — NEVER change publish status.
2. If a Desktop keyword document was created (Case C, published path), DELETE it now
   (~/Desktop/SEO-<slug>-keywords.md).
3. Run /fact on the SAME article (its URL/ID). /SEO ALWAYS finishes by handing off to /fact —
   including when the PROCEED GATE was skipped and no optimization happened.
4. Produce ONE combined report covering the /SEO change-log (if any) + the /fact results,
   ending with the reminder to purge the WP Rocket cache for the URL.
```

---

## Notes / defaults (resolved)

- Competitor keywords: pooled into ONE deduped list, tagged with which competitor(s) rank.
- GSC list: top 20 by clicks; "opportunity" = high impressions + weak position (≈ 4–15) or a
  heading gap; trailing 90-day window.
- Save cadence: single save in S8 (S7 changes are held and saved together).
- After the keyword gate, S4–S8 run straight through to the /fact handoff (S9).
