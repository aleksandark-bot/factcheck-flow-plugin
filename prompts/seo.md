# /SEO — Article Optimization flow

> Executed by the `/SEO` command (`commands/SEO.md`), which asks "Is this a new article or a
> refresh?" as its first action and then runs the stages below. This file is auto-synced from
> the factcheck-flow repo, so edits here propagate to everyone on their next session.

---

## Two branches + selection routing

The FIRST thing /SEO does is ask, verbatim, **"Is this a new article or a refresh?"** with two
options in this exact order — **1. New article**, **2. Refresh** (Stage 0). That picks the branch:

- **New article → QUICK / AUTOMATIC** (is_draft = true). Everything runs automatically; Claude
  makes the keyword judgment calls itself using David's documented logic (this brief + the video
  transcript). No GSC list. Ends by saving and running **/fact**. (A post someone published by
  accident is still handled as new-article content — never change publish status.)
- **Refresh → MANUAL** (is_draft = false). Claude also pulls the **GSC** list and, for keyword
  selection, opens a clean keyword picker in the browser to choose from. (GSC is one of five
  lists; the Highly Relevant list appears in both branches.)

Selection routing at Stage 3 depends on how many keywords the data actually yields:
- **> 10 total:** draft = auto-select; published = Desktop document.
- **≤ 10 total (or all lists empty):** override both paths with the Claude Code multiple-choice
  picker (AskUserQuestion), ending in a **"Do you want to proceed with optimization?"** gate
  that can cancel and skip straight to /fact.

Every path ends the same way: save → (delete the temp doc if one was made) → run **/fact**.
Human gates use strict JSON contracts (below), so these prompts also drop into a future modal
app with no rewrite.

Stages: **S0** draft-check + setup → **S1** SERP pick → **S2** build lists → **S3** keyword
selection (routing above) → **S4** Outline → **S5** entities + SERP structure analysis →
**S6** group entities + structure refine → **S7** main-keyword swap → **S8** optimize + write →
**S9** save, cleanup, hand off to /fact.

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
gsc_top_n: 20                        # candidate pool the helper pulls (top 20 by clicks); the GSC list is then re-sorted by position asc for display
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
- `~/.claude/factcheck-flow/guides/Originality-and-search-intent.md` — the TWO-BAR rule: every
  article must fit searcher intent (judge from the SERP) AND carry an originality nugget (a
  unique angle no top-10 result has). Governs new content AND restructuring decisions; drives
  the Structural-changes box, Stage 4 outline, and Stage 8 writing. Originality is the priority.
- `~/.claude/skills/wordpress-access/SKILL.md` — how to read/write the article (REST API,
  `context=edit`, PUT only changed fields, draft stays draft, append-only categories/tags,
  Yoast focus keyphrase via the post `meta` field).

Non-negotiables carried over from `/fact`: introduce Pabau on first mention; qualify product
names once; never "Pabau Connect" externally (say "online booking"); no feature gating; no
free trial; lead with outcomes; headings must read naturally (no keyword stuffing).

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
   Takeaways). For a LISTICLE specifically: name the actual providers/picks in the Key Takeaways
   block, and start the provider/pick segments IMMEDIATELY after the intro — preceded by a
   comparison TABLE (the skim-reader's answer) so someone who reads nothing else still gets the
   ranked shortlist. Do not bury the list behind long "what to look for / why it matters"
   preamble; move that below the picks or trim it.
4. **Pull in images where they help.** Add relevant images anywhere a visual materially aids
   comprehension or matches what the SERP rewards — a comparison/product screenshot per listicle
   entry, a process diagram for a how-to, a UI screenshot, an "at a glance" visual near the top.
   See the image rule in Stage 8 for sourcing (site media library first) and the exact block +
   alt-text format. Missing obvious images is an incomplete optimization.

---

# STAGE 0 — Draft check, setup & fetch

```
You are running the /SEO optimization flow for a single article: $ARGUMENTS
(one WordPress URL or post ID). If none was given, ask for it and stop.

1. NEW-VS-REFRESH CHECK — the /SEO command asks this as its VERY FIRST action, before any file
   reads, verbatim and in this exact order: "Is this a new article or a refresh?" →
   1. New article, 2. Refresh. Map it: New article → is_draft = true; Refresh → is_draft = false
   (if somehow unset, ask it now before any data work). It gates the GSC list (Stage 2, list D):
     - is_draft = true (New article)  → do NOT run GSC (no search history yet); only 4 lists.
     - is_draft = false (Refresh)     → build the GSC "already-ranking" list (list D) in Stage 2.
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
   ASSESS INTENT (per Originality-and-search-intent.md): intent is not just info/commercial —
   FIRST read the focus keyphrase as a literal question and confirm what answer it demands (a
   "how to…" wants a procedure; "best…" a ranked list; "what is…" a definition; "X vs Y" a
   comparison; "…cost" pricing). Then from the kept top results note the SERP-DOMINANT FORMAT
   (how-to / listicle / comparison / definition / template / tool / case study) and the depth
   the SERP rewards. Record this — it is the intent "floor" every later stage must match. If our
   current article answers a DIFFERENT question than the query, or uses the wrong format (e.g.
   keyphrase "how to become an aesthetic practitioner in the UK" but our article is a list of
   qualifications rather than a step-by-step route), say so now: on the published path the user
   can spell out the fix in the Structural-changes box; on the auto/draft path YOU own the
   restructure in Stage 4.
3. Build the SERP-pick JSON (Gate #1 OUTPUT):

   {
     "main_keyword": "<string>",
     "serp": [
       {"rank": 1, "title": "<title>", "url": "<full exact live page URL, incl https://>"},
       ...
     ]
   }

4. SELECT which results to mine (Competitor Keywords + Stage 5 entity NLP). The METHOD
   depends on is_draft:

   4a. is_draft == true  (AUTO — NO human step): Claude chooses them itself. Keep results that
       are GENUINE WRITTEN ARTICLES / editorial content topically similar to the draft. EXCLUDE
       non-article pages — software directories / review aggregators (Capterra, G2, GetApp,
       Trustpilot, Software Advice, and similar), homepages, product / pricing / category /
       landing pages, and thin listing pages with no real prose. Prefer the closest-matching,
       article-style pages. If NONE qualify, fall back to selecting EVERY result that has any
       usable written content you can mine (exclude only pure link/directory shells). Briefly
       log which URLs you kept and why — as clickable markdown links — then CONTINUE without
       asking the user.

   4b. is_draft == false (MANUAL): launch the browser SERP picker — a clean page listing every
       ranking result as a checkbox row whose title is a CLICKABLE live link (opens in a new
       tab), with Select all / Select none. It writes the chosen URLs back automatically.
       1. Write the SERP JSON (from step 3) to /tmp/seo-<slug>-serp.json:
            { "main_keyword": "<kw>", "serp": [ {"rank","title","url"}, ... ] }
       2. Run (this BLOCKS until the user clicks Save):
            python3 "$HOME/.claude/factcheck-flow/bin/serp_picker.py" \
                    --in /tmp/seo-<slug>-serp.json --out /tmp/seo-<slug>-serp-sel.json
          It opens in the browser automatically. Tell the user: "I've opened a SERP picker in
          your browser — check the results to use, and optionally add any Structural changes at the
          bottom (I'll do those AND add my own; leave it blank to let me decide the structure).
          There's no time limit — take as long as you need, then click Save."
       3. On exit 0, read /tmp/seo-<slug>-serp-sel.json →
          { "selected_urls": [...], "structural_changes": "<text or empty>" }. Capture BOTH:
          the URLs AND the free-text structural_changes box (may be ""). Delete both temp files
          afterward.
       FALLBACK (headless machine, or picker exits non-zero): present a NUMBERED LIST where
       every line is a CLICKABLE MARKDOWN LINK to the exact live ranking page (never a table,
       never the domain, never a bare URL) — `1. [<title>](<full https:// URL>)` … one per
       result — then ask: "Which should I use for competitor keywords + entity analysis?
       (e.g. 1,2,5)". THEN also ask, as a second question: "Any structural changes? (custom
       instructions for larger format/rewrite updates — I'll do those AND add my own; leave blank
       to let me decide the structure)" and capture the reply as structural_changes.
5. Record the Gate #1 SELECTION (auto-chosen in 4a for drafts, user-chosen in 4b for published):

   { "selected_competitor_urls": ["<url>", "<url>", ...], "structural_changes": "<text or "">" }

   Aim for at least 1 URL. For drafts, never pause — if truly nothing usable ranks, note it and
   continue (Stage 2's Competitor list is simply empty); drafts have NO structural_changes box
   (Claude decides format itself), so structural_changes = "" on the auto path. For published,
   wait for the pick and carry structural_changes forward — in Stages 4 and 8 it is a FLOOR, not
   an on/off switch: you ALWAYS restructure (box text = do it in full THEN add your own ideas;
   empty box = carte blanche to restructure as the SERP/intent/originality require).
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
   sorted by clicks desc (top gsc_top_n). This is the candidate POOL.
   HARD REQUIREMENT: GSC is mandatory on the PUBLISHED path. If the helper exits non-zero
   (missing key, PyJWT not installed, or an API error), STOP and tell the user GSC isn't set up
   — do NOT silently continue without this list. Fix path: place the key at gsc_key or set
   $PABAU_GSC_KEY, and install PyJWT (`python3 -m pip install --user pyjwt`). Drafts never call it.

   ENRICH each GSC query with DIFFICULTY + SEARCH VOLUME from DataForSEO — fold the queries into
   the batch bulk_keyword_difficulty + keyword_overview calls in the Enrichment section below
   (same no-data rule: difficulty is an int or "N/A", never blank). These are DISPLAY/context
   columns only. Do NOT apply the difficulty/volume Tier filters to GSC — we surface these terms
   because we already have first-party ranking signal for them, not because they clear a bar.

   ORDER FOR DISPLAY — sort the GSC list by AVERAGE POSITION ASCENDING (best ranking first:
   position 1 is the greatest, larger numbers are worse). This is the order the keyword picker
   renders them in. Clicks, impressions, difficulty and volume ride along as columns.

   PRESENCE CHECK — for each query, check whether it appears (exact or near-exact match) in ANY
   article HEADING **or** anywhere in the BODY TEXT, using the heading tree + body blocks captured
   in Stage 0. Record present_on_page = true/false.

   SELECTION LOGIC — flag the two TARGET categories via the "opportunity" field (this becomes the
   reason text the picker shows, so the user knows which to pick). Both require present_on_page ==
   false (a term already in a heading or the body is already targeted — leave it unflagged):
     · Category 1 — RANKING, NOT ON-PAGE (quick win): present_on_page == false AND position ≤ 10.
       We already rank for it, but it is absent from every heading and the body text. Just weave
       it into the relevant section's body — and into a heading where it maps to a topic.
       opportunity = "ranking, not on-page — add to a heading/body".
     · Category 2 — WINNABLE, NEEDS CONTENT: present_on_page == false AND position > 10. We are NOT
       in the top 10, but the term is relevant enough to win by giving it a dedicated HEADING and
       creating content built for it. opportunity = "not top 10 — target with a new heading + content".
   A query already in the top 10 AND already present on-page is info-only (opportunity = "");
   still show it (ordered by position), just don't flag it as an opportunity.
E. HIGHLY RELEVANT KEYWORDS → dataforseo_labs_google_keyword_ideas (seed = main keyword),
   using DataForSEO's DEFAULT relevance ordering. Take the top list_target_len (20) purely BY
   RELEVANCE. This list has NO difficulty/volume filtering and NO fill tiers — just the 20 most
   relevant terms (show difficulty/volume as info only). Only the always-on hygiene applies
   (drop the bare main keyword, drop terms already used as an exact-match heading, dedupe, stay
   on-topic). Cross-list overlap is resolved in the "Deduplicate across ALL lists" final pass —
   highly_relevant is LOWEST priority, so any term it shares with another list moves there and this
   list may end up shorter than 20. Present for BOTH drafts and published.

── Enrichment ────────────────────────────────────────────────────────────────
- Difficulty: dataforseo_labs_bulk_keyword_difficulty (batch).
  NO-DATA RULE: DataForSEO computes KD from the current top-10 ranking pages, so for
  long-tail / near-zero-volume keywords it returns the keyword with the keyword_difficulty
  field ABSENT (not null, not 0 — the key is simply missing). The discovery endpoints
  (keyword_ideas / related_keywords / ranked_keywords) omit it the same way. Whenever KD is
  absent or null after this batch call, record difficulty as the string "N/A" — NEVER leave it
  blank and NEVER fabricate a number. Every keyword in every list must carry a difficulty value
  that is either an integer or "N/A"; a blank difficulty cell is a bug.
- Volume + CPC + trend: dataforseo_labs_google_keyword_overview.
- Intent: dataforseo_labs_search_intent. Flag intent that mismatches the article's intent.
- ALSO enrich the CURRENT MAIN KEYWORD (Stage 0) for difficulty + volume in these same batch
  calls — it is not a candidate, but Stage 3 displays it (current_main) above the new-main
  selector so the user can compare. Same no-data rule: difficulty is an int or "N/A".
- ALSO enrich the GSC list keywords (list D) for difficulty + volume in these same batch calls
  so the picker can show Diff. + Vol. columns for them. GSC keeps its own no-filter rule — these
  are display/context only, never a reason to drop a GSC query.

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
           best available first. Keywords with "N/A" difficulty belong here (their difficulty
           is unknown, so they can never satisfy the Tier 1 ≤10 or Tier 2 >10 bands); place
           them at the BOTTOM of the tier, sorted by volume desc.
If even Tier 3 yields few, KEEP WHAT YOU HAVE — a short/empty list is valid and drives the
Stage 3 routing. Do not invent keywords.
Always applied (every tier): drop keywords the article already targets as an exact-match
heading; dedupe WITHIN each list here (cross-list duplicates are removed later in the "Deduplicate
across ALL lists" final pass — note the overlap on the keeper); drop off-topic/off-intent/brand
terms that don't fit Pabau (borderline → keep, tag "review"). Relevance is NEVER relaxed, even in Tier 3.

── Ranking within each list ─────────────────────────────────────────────────────
Primary: difficulty band (0–5 first, then 6–10, then the Tier 2/3 fill in that order).
Secondary: volume desc. Target list_target_len (20). For each kept keyword, record a one-line
"why" (e.g. "distinct entity, diff 3 / vol 210", "qualifier variation: women", "competitor
rank 4 also targets this").

── Deduplicate across ALL lists (final pass — run AFTER every list is built) ──────
Once all lists exist, remove DUPLICATE entries so no keyword appears more than once across the
whole payload. Normalize for comparison: lowercase, trim, collapse internal whitespace, and treat
a trivial plural/stopword-only difference as the SAME keyword. When a keyword lands in more than
one list, KEEP it in the single highest-priority list and DELETE it from the others:
    gsc_ranking > competitor > related > variations > highly_relevant
(GSC wins because it carries first-party ranking data and its own selection logic; highly_relevant
is the raw relevance dump, so shared terms move to their more specific list.) When you keep a row,
note the overlap in its "why" (e.g. "also in variations"). Lists may end up shorter than
list_target_len after this pass — that is expected; do NOT backfill or re-invent keywords to refill
them. The result is five (published) or four (draft) lists with ZERO repeated keywords.

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
  // "difficulty" is ALWAYS present on every row: an integer 0–100, or the string "N/A" when
  // DataForSEO has no KD for that keyword (Stage 2 no-data rule). Never blank, never fabricated.
  "lists": {
    "related":       [ {"keyword": "...", "difficulty": 3, "volume": 210, "intent": "informational", "why": "...", "new_main_candidate": false}, ... ],
    "variations":    [ {"keyword": "...", "difficulty": 5, "volume": 140, "intent": "...", "why": "qualifier: women", "new_main_candidate": false}, ... ],
    "competitor":     [ {"keyword": "...", "difficulty": 2, "volume": 300, "intent": "...", "why": "ranks #4 for competitorX", "new_main_candidate": true}, ... ],
    "highly_relevant":[ {"keyword": "...", "difficulty": 12, "volume": 40, "intent": "...", "relevance_rank": 1}, ... ],
    "gsc_ranking":    [ {"keyword": "...", "position": 8.0, "clicks": 2077, "impressions": 26170, "difficulty": 12, "volume": 40, "intent": "informational", "present_on_page": false, "opportunity": "ranking, not on-page — add to a heading/body"}, ... ]  // ordered by position ASC (best rank first)
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
  keywords. Present each keyword as its OWN multi-select question with exactly four options:
  [use in text] / [use in heading] / [use as FAQ] / [set as NEW MAIN]. There is NO skip —
  leaving all four unchecked means the keyword is NOT used. If ANY box is checked the keyword IS
  used: "use in heading" = heading AND text; "use as FAQ" = an FAQ question (see the FAQ rule in
  Selection semantics); "set as NEW MAIN" = H1 + intro + meta description + SEO title (Stage 7).
  At most ONE new main across all keywords. This OVERRIDES both the auto and document
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
  • is_draft == false → PICKER PATH: launch the local web picker (see below), which opens a
    clean page in the browser with a per-keyword role dropdown and a free-text "new main" keyword
    box. STOP until the user clicks Save; then read the selection JSON it writes.

── PROCEED GATE (Cases A and B only) ──
Final question of this step, via AskUserQuestion:
    "Do you want to proceed with optimization?"  → [Proceed] / [Skip to /fact]
If Skip (or Case A with nothing selected): do NOT optimize — jump straight to Stage 9 (/fact
handoff). This is the escape hatch for when there aren't enough keywords to matter.

── BROWSER PICKER (Case C, published) ──
Do NOT write a markdown/Obsidian file. Launch the shipped local web picker: it renders the
lists as a clean page with clickable controls (a per-keyword "Use as" dropdown — skip / Text /
Heading / FAQ — plus one free-text "New main keyword" box with type-ahead suggestions, NOT a
dropdown) and writes the selection back automatically.

1. Write the five lists to a temp JSON at /tmp/seo-<slug>-kw.json, shaped as:
     { "article_title": "<title>", "article_url": "<url>",
       "current_main": { "keyword": "<current Yoast focus keyphrase / main keyword>",
                         "difficulty": <int|"N/A">, "volume": <int|null> },
       "lists": { "related":[...], "variations":[...], "competitor":[...],
                  "highly_relevant":[...], "gsc_ranking":[...] } }
   Row fields: keyword, difficulty, volume, intent, why — or for gsc_ranking: keyword, position,
   clicks, impressions, difficulty, volume, intent, opportunity — with the gsc_ranking rows
   ORDERED BY POSITION ASC (best ranking first). Omit gsc_ranking on drafts.
   current_main is the CURRENT MAIN KEYWORD determined in Stage 0 (Yoast focus keyphrase, else
   inferred). Enrich its difficulty + volume in Stage 2 alongside the candidates (same no-data
   rule: difficulty is an int or "N/A", never blank). The picker shows it directly above the
   "New main keyword" box so the user can compare before promoting a replacement.
2. Run (this BLOCKS until the user clicks Save in the browser):
     python3 "$HOME/.claude/factcheck-flow/bin/keyword_picker.py" \
             --in /tmp/seo-<slug>-kw.json --out /tmp/seo-<slug>-sel.json
   It opens the page in the user's browser automatically. Tell the user: "I've opened a keyword
   picker in your browser — choose your keywords and click Save."
3. When it exits 0, read /tmp/seo-<slug>-sel.json — it already IS the SELECTION JSON below
   ({selected:[{keyword,list,use_in_heading,use_as_faq}], new_main_keyword}). Delete temp files after.
   If the picker exits non-zero / can't open a browser (headless), FALL BACK to the Case B
   AskUserQuestion picker.

── Gate #2 SELECTION (produced by whichever path ran) ──
{
  "selected": [ {"keyword": "...", "list": "related|variation|competitor|highly_relevant|gsc_ranking|custom",
                 "use_in_heading": true, "use_as_faq": false, "new_main_keyword": false}, ... ],
  "new_main_keyword": "<the one keyword flagged new main, or null>"
}
Note: the picker's "New main keyword" control is a FREE-TEXT box, so new_main_keyword may be a
keyword the user typed that is NOT in any of the five lists — in that case its "selected" entry
carries list = "custom". Stage 7 applies it (H1/intro/meta/title) regardless of its list.
Selection semantics (apply in EVERY path — auto, document, picker):
- selected, use_in_heading = false and use_as_faq = false → weave the keyword into BODY TEXT only.
- selected, use_in_heading = true  → place it as an EXACT-MATCH heading AND weave it into that
  section's body text (a heading keyword ALWAYS also appears in text).
- selected, use_as_faq = true → add the keyword VERBATIM as an FAQ QUESTION in the article's FAQ
  block (use proper Yoast FAQ schema; create the FAQ block if none exists). For its ANSWER:
  FIRST check whether ANY OTHER selected keyword is similar/related to this FAQ question — if so,
  work THAT keyword naturally into the answer. If none is related, write the answer using a
  sensible VARIATION of the FAQ keyword that fits the sentence — do NOT duplicate the question
  keyword or echo a near-identical phrase. use_as_faq is mutually exclusive with use_in_heading,
  and a new main keyword is never an FAQ.
- new_main_keyword → apply in the H1, intro text, meta description, and SEO title (Stage 7);
  implies use_in_heading. At most ONE new_main_keyword.
- a keyword with nothing selected is NOT used.
```

---

# STAGE 4 — Outline planning  (your step 4 — PLANNING ONLY, no writing)

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
wins (still obeying 2-editorial.md structure rules — H1 > Key Takeaways > Intro > H2, valid
hierarchy, natural headings). Note in the outline which nodes exist BECAUSE of structural changes,
and whether each came from the user's box or your own judgment.

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
   non-duplicative variation). If the article has no FAQ block, plan to create one (Yoast FAQ
   schema).
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
  Key Takeaways to carry it. If the current article buries the payoff behind long preamble,
  reorder now so the answer surfaces early (this is a structural change you are authorized to make).
- LISTICLE type: the outline MUST (a) name the actual picks/providers in Key Takeaways;
  (b) place a comparison [TABLE] node immediately after the intro, before the first pick; and
  (c) start the per-pick segments right after that table. Push any long "how we chose / what to
  look for" material BELOW the picks (or trim it). Plan the table's columns now (name + the 2–4
  axes that actually decide the pick).

IMAGE PLANNING (Optimization stance #4): mark outline nodes that should carry an image with an
[IMG] note — what the image should show and why it helps (e.g. "product screenshot for pick #1",
"booking-flow screenshot", "comparison visual near the top"). Sourcing + block format are handled
in S8; here just decide WHERE images belong and what each depicts.

If new_main_keyword is set: plan the new H1 (exact-match, grammatical) and note that S7 will
also update meta/intro/SEO title/focus keyphrase.

TWO-BAR CHECK (per Originality-and-search-intent.md) — the outline must clear both before you
proceed to writing:
- INTENT (floor): the outline ANSWERS THE QUERY'S ACTUAL QUESTION (not an adjacent one) in the
  SERP-dominant format + depth assessed in Stage 1. If the current article answers a different
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

Structure compliance (per 2-editorial.md): keep H1 > Key Takeaways > Intro > H2 order; valid
hierarchy H1>H2>H3>H4; headings must read naturally; no keyword stuffing.

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

# STAGE 5 — Entity extraction + SERP structure analysis (NLP over selected SERP pages)  (your step 5)

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

── SERP STRUCTURE ANALYSIS (same open pages) ────────────────────────────────────
While each page is open, ALSO analyze its STRUCTURE. Do this for EVERY SERP page you opened (the
more of the ranking set the better) so the profile reflects the whole SERP, not one page:
- HEADING OUTLINE: capture each page's full H1–H4 tree in document order.
- HEADING KEYWORD/ENTITY USE: for each heading, note which target keywords and which Stage-5
  entities appear in it, and the heading PATTERN (question, "how to", "X vs Y", number + noun,
  benefit-led, etc.). Which subtopics/entities does nearly every competitor give a dedicated
  heading? Which does none of them?
- STRUCTURED-DATA FORMATS: record every structured presentation and what it holds —
  comparison/pricing/spec TABLES, ordered (step) and unordered LISTS, FAQ blocks, definition
  boxes, pros/cons, checklists, "at a glance" summary boxes, how-to/FAQ schema. Note where a
  format is competing for a FEATURED SNIPPET (short answer + list/table).

SERP STRUCTURE PROFILE output:
- consensus heading map: the subtopics/entities the SERP consistently gives headings to, with the
  dominant heading pattern for each (this is the structural "floor" the article must match);
- format inventory: which structured formats dominate (e.g. "5/6 pages use a comparison table";
  "all use a numbered step list"), plus any featured-snippet opportunity;
- WEAKNESSES TO BEAT: vague or keyword-stuffed competitor headings, missing/thin tables or lists,
  disorganized flow, obvious subtopics with no heading — and, most important, what NEW useful data
  we could present as a table/list that none of the ranking pages offer.
This profile is consumed by S6 (outline structure refinement) and S8 (writing).
```

---

# STAGE 6 — Group entities + refine outline structure  (your step 6)

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
  addressing the WEAKNESSES TO BEAT. Any Stage-1 structural_changes still win, and keep 2-editorial
  structure rules (H1 > Key Takeaways > Intro > H2, valid hierarchy, natural headings).

Output: the FINAL OUTLINE S8 writes from — the heading tree with any S6 structure revisions and
planned [TABLE]/[LIST] nodes, each node carrying its grouped entities plus table-column / list-item
notes beneath it. Still no prose written.
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

STRUCTURAL CHANGES: EXECUTE the Stage 4 structural plan here in full — it is already baked into
the Stage 4 outline, so write to that restructured outline. On the manual (Refresh) branch there
is ALWAYS a structural plan to execute: whatever the user put in the box (do it in full) PLUS your
own structural improvements, or — if the box was empty — the changes you decided under carte
blanche. This may mean a LARGER REWRITE than a normal optimization pass: reformatting the article,
re-sequencing or replacing whole sections, or rewriting substantial copy to match the format the
SERPs reward. Never half-apply a change to "preserve" the old structure. Keep the SEO keyword work
intact on top of the new structure. If the changes imply the article's TYPE changed, re-check the
meta title per Meta-title-best-practices.md. Summarize the structural changes made in the S9
change-log (noting which came from the user's box vs your own judgment).

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
- [IMG] node → insert the planned image here as a real WordPress image block (see the image
  rule in Hard rules for sourcing + format).
- IN-TEXT keywords → insert into the most relevant existing sentence/section naturally.
- FAQ keywords (use_as_faq) → add each as a new Q in the FAQ block (verbatim question, proper
  Yoast FAQ schema; create the block if missing). Write the ANSWER per Selection semantics:
  reuse a related SELECTED keyword in the answer if one exists; otherwise use a sensible
  variation of the FAQ keyword — never duplicate the question phrase or a near-identical one.

Hard rules:
- Keywords placed in headings are EXACT match; headings still read naturally (reword fully).
- A keyword placed in a heading MUST also appear in that section's body text (heading + text).
- A new main keyword must land in the H1, intro, meta description, and SEO title (via S7).
- No keyword stuffing in body or headings; every sentence must carry information (no fluff).
- ANSWER-FIRST HEADINGS (Optimization stance #2): any heading that is or implies a question is
  answered directly and completely in the FIRST sentence of its section — no preamble, no
  restating the question, no "it depends" hedge before the answer. Answer, then elaborate. Same
  for every FAQ answer. This is non-negotiable.
- ANSWER NEAR THE TOP (Optimization stance #3): the intro states the reader's core answer and
  Key Takeaways reflects it. For a LISTICLE: name the real picks/providers in Key Takeaways, put
  a comparison TABLE right after the intro, and begin the per-pick segments immediately after
  that table — never bury the picks behind long preamble (move "how we chose / what to look for"
  below the picks or trim it).
- OVERWRITE FREELY (Optimization stance #1): rewrite, resequence, merge, or replace existing copy
  and blocks whenever that optimizes better than a light edit — do NOT preserve the old structure
  for its own sake. Keep only the guardrails fixed (facts, Pabau positioning, publish status,
  published-post URL/slug). Fix malformed HTML/FAQ blocks per editorial rules. Respect paragraph
  (≤4 lines/≤60 words) and sentence-length limits; convert 3+ clause lists to WordPress list blocks.
- If the SERP shows a featured-snippet opportunity, format the relevant answer as both a
  short paragraph and a list to compete for it (from the transcript's snippet tactic).
- EMULATE + IMPROVE ON THE SERP STRUCTURE (S5 profile / S6 final outline): write the planned novel
  headings (clearer and more natural than the ranking pages', never mirrored or keyword-stuffed);
  build every planned [TABLE]/[LIST] node as a real WordPress table/list block that delivers NEW
  useful information (a new column or comparison axis, real numbers or steps competitors omit) —
  never a decorative rehash of a competitor's table; and organize each section more logically than
  the SERP, fixing the WEAKNESSES TO BEAT. Match the structural formats the SERP rewards, then go
  one better in clarity and usefulness.
- ORIGINALITY + ANTI-MIRAGE (per Originality-and-search-intent.md): actually DELIVER the nugget
  planned in Stage 4 (don't let it evaporate into generic copy), and run every new/rewritten
  section through the mirage battery — reader's-shoes ("no shit" vs "no one told me this"),
  real-examples, and customer-fit (write for a practice owner/manager who already knows the
  basics, not "anyone"). Cut platitudes, obvious tips, and generic intros. Keep the piece
  matched to the SERP intent throughout.
- IMAGES (Optimization stance #4): build every [IMG] node planned in S4, and add an image
  anywhere else a visual clearly helps or the SERP rewards one. Sourcing, in order:
    1. The site's OWN media library first — query it and reuse a relevant asset already hosted:
         curl -s -u "$WP_USER:$WP_APP_PASSWORD" \
           "$WP_BASE_URL/wp-json/wp/v2/media?search=<term>&per_page=20&context=edit"
       Use the returned `source_url` and note the media `id`.
    2. If nothing fits and the section genuinely needs one (e.g. a per-provider screenshot/logo
       in a listicle), use the provider's OWN official image URL. VERIFY the URL resolves (HTTP
       200, image content-type) before inserting — never insert an unverified or guessed URL,
       and never hotlink something that will 404.
  Insert as a proper Gutenberg image block, e.g.:
       <!-- wp:image {"id":<id>,"sizeSlug":"large"} -->
       <figure class="wp-block-image size-large"><img src="<source_url>" alt="<descriptive alt>"/>
       <figcaption class="wp-block-image">…optional caption…</figcaption></figure>
       <!-- /wp:image -->
  Alt text is REQUIRED and descriptive — work the relevant entity/keyword in only where it reads
  naturally (never stuffed). Don't overload a section with images; one purposeful image beats
  three decorative ones. If the post has NO featured image and a good candidate exists, set it
  via `featured_media: <id>` in the save. Log every image added (and its source) in the change-log.

Save via wordpress-access: PUT only changed fields (content, title, excerpt/meta description,
Yoast focus keyphrase meta, categories/tags — append-only, remove "Uncategorized"). Draft
stays draft; published stays published.

CHANGE-LOG (hold for the S9 combined report): main keyword (old→new if changed), structural
changes applied (from the Stage 1 box, if any), headings added/optimized, keywords placed
(heading vs in-text), entity themes woven in, meta/title/description changes, categories/tags
added, images added (with source) + featured image set, and any answer-first/top-of-article
reordering done.
```

---

# STAGE 9 — Save, cleanup, hand off to /fact

```
1. Ensure all S7/S8 changes are saved to WordPress. Draft stays draft; a post someone
   accidentally published is still handled as draft content — NEVER change publish status.
2. If the browser picker was used (Case C, published), delete its temp files now
   (/tmp/seo-<slug>-kw.json and /tmp/seo-<slug>-sel.json).
3. Run /fact on the SAME article (its URL/ID). /SEO ALWAYS finishes by handing off to /fact —
   including when the PROCEED GATE was skipped and no optimization happened.
4. Produce ONE combined report covering the /SEO change-log (if any) + the /fact results,
   ending with the reminder to purge the WP Rocket cache for the URL.
```

---

## Notes / defaults (resolved)

- Competitor keywords: pooled into ONE deduped list, tagged with which competitor(s) rank.
- SERP structure analysis (S5): reuses the SAME pages opened for entity NLP — headings, heading
  keyword/entity use, and structured-data formats (tables/lists/FAQ/step blocks) → a SERP structure
  profile that S6 turns into novel headings + [TABLE]/[LIST] nodes + reorganization, and S8 writes
  and improves on. No extra fetches beyond the entity pass.
- GSC list: pull top 20 by clicks (trailing 90-day window), enrich each with difficulty + volume
  (DataForSEO; display only — no filtering), then DISPLAY ordered by position ASC (best ranking
  first). "opportunity" flags the two target categories, both requiring the term to be absent from
  every heading AND the body text (present_on_page == false): (1) RANKING, NOT ON-PAGE — position
  ≤ 10, a quick win to weave into a heading/body; (2) WINNABLE, NEEDS CONTENT — position > 10, win
  it with a new dedicated heading + content. Terms already in the top 10 and already on-page are
  shown but not flagged.
- Save cadence: single save in S8 (S7 changes are held and saved together).
- After the keyword gate, S4–S8 run straight through to the /fact handoff (S9).
