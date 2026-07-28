# /SEO — part 1: research & keyword selection (S0–S3)

> Executed by the `/SEO` command (`commands/SEO.md`), which asks "Is this a new article or a
> refresh?" as its first action and then runs the stages below. Part 2 —
> `prompts/seo-write.md` — carries S4–S9 and is read at the START OF S4, not now. This file
> is auto-synced from the factcheck-flow repo, so edits here propagate on the next session.

**Read `~/.claude/factcheck-flow/guides/core-rules.md` now, and nothing else yet.** It
carries the always-on rules plus the map of which full guide to open at which stage. The
writing guides (`Pabau-style-guide.md`, `2-editorial.md`, `WordPress-blocks.md`,
`Meta-title-best-practices.md`, `About-Pabau.md`, `Originality-and-search-intent.md`) are
read in part 2, where the writing happens. Loading them now would keep ~40k tokens resident
through every turn of the research stages, which is the single most expensive mistake in
this flow.

**Batch your tool calls.** Independent calls go in ONE message: the Stage-1 SERP fetch is
one call, Stage 2 is one script call, and Stage 5's page reads (part 2) fan out together.
Every extra round-trip re-reads the whole conversation.

---

## Two branches + selection routing

The FIRST thing /SEO does is ask, verbatim, **"Is this a new article or a refresh?"** with two
options in this exact order — **1. New article**, **2. Refresh** (Stage 0). That picks the branch:

- **New article → QUICK / AUTOMATIC** (is_draft = true). Everything runs automatically; Claude
  makes the keyword judgment calls itself using David's documented logic. No GSC list. Ends by
  saving and running **/fact**. (A post someone published by accident is still handled as
  new-article content — never change publish status.)
- **Refresh → MANUAL** (is_draft = false). Claude also pulls the **GSC** list and, for keyword
  selection, opens a clean keyword picker in the browser to choose from. (GSC is one of five
  lists; the Highly Relevant list appears in both branches.)

Selection routing at Stage 3 depends on how many keywords the data actually yields:
- **> 10 total:** draft = auto-select; published = browser picker.
- **≤ 10 total (or all lists empty):** override both paths with the Claude Code multiple-choice
  picker (AskUserQuestion), ending in a **"Do you want to proceed with optimization?"** gate
  that can cancel and skip straight to /fact.

Every path ends the same way: save → (delete the temp files) → run **/fact**. Human gates use
strict JSON contracts, so these prompts also drop into a future modal app with no rewrite.

Stages: **S0** draft-check + setup → **S1** SERP pick → **S2** build lists → **S3** keyword
selection (routing above) → *[read part 2]* → **S4** Outline → **S5** entities + SERP structure
→ **S6** group entities + structure refine → **S7** main-keyword swap → **S8** optimize + write
→ **S9** save, cleanup, hand off to /fact.

---

## CONFIG (tweak these; referenced by the prompts below)

```yaml
location_name: "United States"
language_code: "en"
search_engine: "google"

# Keyword thresholds (David's rules) — enforced in code by bin/dfs_lists.py
difficulty_soft_ceiling: 10 # PREFER ≤ 10; fill from here first. NOT a hard cap.
difficulty_priority: 5      # 0–5 difficulty takes priority
volume_ideal: 100           # prefer ≥ 100
volume_ok: 50               # acceptable ≥ 50
volume_floor: 20            # normal floor; only the Tier-3 last resort may go below

# List sizes
list_target_len: 20         # each list should reach 20 keywords if the data allows
competitor_top_n: 20        # top keywords per selected competitor page
serp_depth: 10              # organic results pulled for the SERP-pick gate

# Scarcity fallback (Stage 3 routing)
scarce_total_threshold: 10  # ≤ this many keywords TOTAL → Claude Code picker + proceed gate

site_domain: "pabau.com"    # used to identify our own result + our own ranked keywords

# Helpers (all ship with the command)
dfs_lists_script: "$HOME/.claude/factcheck-flow/bin/dfs_lists.py"
gsc_query_script: "$HOME/.claude/factcheck-flow/bin/gsc_query.py"
gsc_key: "$HOME/.claude/factcheck-flow/gsc-key.json"  # SECRET; not in repo. Override: $PABAU_GSC_KEY
gsc_property: "https://pabau.com/"   # URL-prefix property. Override: $PABAU_GSC_PROPERTY
gsc_window_days: 90                  # trailing window for the query pull
gsc_top_n: 20                        # candidate pool (top 20 by clicks); re-sorted by position asc
```

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
2. Load CONFIG above. You have already read core-rules.md; read NO other guide yet.
3. Resolve the article via the wordpress-access skill — ONE fetch, with `context=edit` and the
   `_fields=` list from that skill (without it the response carries the body twice plus Yoast's
   head blobs). Never WebFetch the public URL to read the article. Capture:
   - post ID, slug, full URL, status (draft/publish), categories, tags
   - H1, and the full heading tree (H2/H3/H4) in document order
   - the body blocks (so you can later place content precisely)
   - current Yoast focus keyphrase, SEO/meta title, and meta description
4. Write two small files Stage 2's helper needs (this costs nothing and saves a large
   keyword-matching pass later):
   - /tmp/seo-<slug>-headings.txt : one heading per line, exactly as written
   - /tmp/seo-<slug>-body.txt     : the article's visible body text (strip block comments/HTML)
5. Determine the CURRENT MAIN KEYWORD: use the Yoast focus keyphrase if present; else infer
   from the H1 + slug. State it explicitly.
6. Classify the ARTICLE TYPE (affects editorial + meta-title rules): listicle, code article
   (diagnostic/procedure code), template article, or standard guide.
7. Emit a short setup summary: main keyword, type, status, is_draft, heading count. No changes.
```

---

# STAGE 1 — SERP fetch → competitor pick  ⟨HUMAN GATE #1⟩

```
Goal: let the user choose which SERP results to mine for Competitor Keywords. These SAME
URLs are reused for entity NLP in Stage 5, so choose once.

1. Call serp_organic_live_advanced:
     keyword = CURRENT MAIN KEYWORD, location_name/language_code/search_engine from CONFIG,
     depth = serp_depth.
2. Keep ORGANIC results only. Drop: our own domain (site_domain), pure aggregators/SERP
   features, and anything paywalled/login-gated you can't open. Keep the ranked order.
   ASSESS INTENT using the two-bar summary and the query-pattern mapping in core-rules.md —
   the full Originality-and-search-intent.md is read in part 2 at S4, where the outline and
   the originality nugget are planned. FIRST read the focus keyphrase as a literal question
   and confirm what answer it demands (a "how to…" wants a procedure; "best…" a ranked list;
   "what is…" a definition; "X vs Y" a comparison; "…cost" pricing). Then from the kept top
   results note the SERP-DOMINANT FORMAT (how-to / listicle / comparison / definition /
   template / tool / case study) and the depth the SERP rewards. Record this in ONE short
   paragraph — it is the intent "floor" every later stage must match, and it is what you
   carry into part 2. If our current article answers a DIFFERENT question than the query, or
   uses the wrong format (e.g. keyphrase "how to become an aesthetic practitioner in the UK"
   but our article is a list of qualifications rather than a step-by-step route), say so now:
   on the published path the user can spell out the fix in the Structural-changes box; on the
   auto/draft path YOU own the restructure in Stage 4.
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

# STAGE 2 — Build the five keyword lists (ONE script call)

```
Stage 2 runs in code, not in context. `bin/dfs_lists.py` makes every DataForSEO call, applies
the CONFIG thresholds, classifies related vs variation, fills the tiers, dedupes across all
five lists, and writes the picker payload. Raw API JSON never enters the conversation — it is
~26k tokens of nested objects to keep 100 short rows.

1. GSC first, PUBLISHED ARTICLES ONLY (skip entirely when is_draft == true):
     python3 "$HOME/.claude/factcheck-flow/bin/gsc_query.py" \
             --page "<full article URL>" --days 90 --limit 20 > /tmp/seo-<slug>-gsc.json
   HARD REQUIREMENT on the published path. If it exits non-zero (missing key, PyJWT not
   installed, API error), STOP and tell the user GSC isn't set up — do NOT silently continue
   without this list. Fix path: place the key at gsc_key or set $PABAU_GSC_KEY, and install
   PyJWT (`python3 -m pip install --user pyjwt`). Drafts never call it.

2. Build every list in one call (add --gsc only on the published path):
     python3 "$HOME/.claude/factcheck-flow/bin/dfs_lists.py" \
       --main-keyword "<CURRENT MAIN KEYWORD>" \
       --article-title "<title>" --article-url "<url>" \
       --competitor-url "<url1>" --competitor-url "<url2>"   … one per Gate #1 URL \
       --gsc /tmp/seo-<slug>-gsc.json \
       --article-text /tmp/seo-<slug>-body.txt \
       --headings /tmp/seo-<slug>-headings.txt \
       --location "United States" --language en \
       --list-len 20 --competitor-top-n 20 \
       --out /tmp/seo-<slug>-kw.json
   It prints one summary line — {"out","total_kw","counts","current_main"} — and writes the
   full payload to --out. On a non-zero exit, read the stderr message and fix it (usually
   credentials); do not fall back to calling the DataForSEO MCP tools by hand.

   What the script has already done for you (do NOT redo any of it by hand):
     · list A RELATED — keyword_ideas + related_keywords, terms that DROP the main keyword's
       head term and name a distinct entity/subtopic;
     · list B VARIATIONS — keyword_suggestions, terms that KEEP the head term (reorder, synonym
       swap, plural, or main keyword + qualifier); qualifier variations (user group / use case)
       are surfaced at the top;
     · list C COMPETITOR — ranked_keywords for each selected URL, top competitor_top_n by
       traffic, pooled and deduped, each tagged with the competitor's rank;
     · list D GSC — the queries from step 1, enriched with difficulty + volume (display only,
       never filtered), `present_on_page` computed against your headings + body files, the two
       opportunity categories flagged, and the whole list ordered by position ascending;
     · list E HIGHLY RELEVANT — the raw top-20 by DataForSEO relevance, no tier filtering;
     · difficulty / volume / intent enrichment for every row, with absent KD recorded as the
       string "N/A" (never blank, never fabricated);
     · the tier fill (Tier 1 ≤10 difficulty and ≥20 volume, Tier 2 above the ceiling, Tier 3
       last resort with N/A difficulty at the bottom), the ranking, and the cross-list dedupe
       (priority gsc > competitor > related > variations > highly_relevant, overlap noted in
       the row's "why"). Lists shorter than 20 after dedupe are expected — never backfill.

3. THE ONE JUDGMENT THE SCRIPT CANNOT MAKE: topical relevance. Read the payload (it is ~100
   short rows) and STRIKE any row that is off-topic, off-intent, or a brand term that doesn't
   fit Pabau — the discovery endpoints happily return things like "minute clinic" or "the
   patient" for a clinic-software seed. Borderline stays, tagged "review". Relevance is never
   relaxed, not even in Tier 3. Rewrite the JSON file with the survivors before Stage 3, and
   say how many rows you struck.

4. Report the per-list counts and total_kw. That total drives the Stage 3 routing.
```

---

# STAGE 3 — Keyword selection  ⟨HUMAN GATE #2⟩

```
The payload written by Stage 2 IS the Gate #2 payload; its shape is:

{
  "article_title": "...", "article_url": "...",
  "current_main": {"keyword": "...", "difficulty": <int|"N/A">, "volume": <int|null>},
  "lists": {
    "related":        [ {"keyword","difficulty","volume","intent","why","new_main_candidate"}, ... ],
    "variations":     [ {"keyword","difficulty","volume","intent","why","new_main_candidate"}, ... ],
    "competitor":     [ {"keyword","difficulty","volume","intent","why","new_main_candidate"}, ... ],
    "highly_relevant":[ {"keyword","difficulty","volume","intent","relevance_rank"}, ... ],
    "gsc_ranking":    [ {"keyword","position","clicks","impressions","difficulty","volume",
                         "intent","present_on_page","opportunity"}, ... ]   // position ASC
  }
}

"difficulty" is ALWAYS present on every row: an integer 0–100, or the string "N/A".
"highly_relevant" is ALWAYS present. "gsc_ranking" is present ONLY for published articles
(is_draft == false). Drafts show four lists; published shows five.

── ROUTING: how selection happens (by keyword count × draft flag) ──
total_kw = keywords across ALL lists (the script printed it; recount after your Stage-2 strike).

CASE A — total_kw == 0 (all lists empty):
  Nothing to optimize. Skip selection; go straight to the PROCEED GATE.

CASE B — total_kw ≤ scarce_total_threshold (10):
  Too few to justify a picker. Use the Claude Code picker (AskUserQuestion), batches of ≤4
  keywords. Present each keyword as its OWN multi-select question with exactly four options:
  [use in text] / [use in heading] / [use as FAQ] / [set as NEW MAIN]. There is NO skip —
  leaving all four unchecked means the keyword is NOT used. If ANY box is checked the keyword IS
  used: "use in heading" = heading AND text; "use as FAQ" = an FAQ question (see Selection
  semantics); "set as NEW MAIN" = H1 + intro + meta description + SEO title (Stage 7).
  At most ONE new main across all keywords. This OVERRIDES both the auto and picker
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
  • is_draft == false → PICKER PATH: launch the local web picker (below), which opens a
    clean page in the browser with a per-keyword role dropdown and a free-text "new main"
    keyword box. STOP until the user clicks Save; then read the selection JSON it writes.

── PROCEED GATE (Cases A and B only) ──
Final question of this step, via AskUserQuestion:
    "Do you want to proceed with optimization?"  → [Proceed] / [Skip to /fact]
If Skip (or Case A with nothing selected): do NOT optimize and do NOT read part 2 — jump
straight to the /fact handoff (Stage 9 below is reproduced here for that case: run /fact on
the same article and report). This is the escape hatch for when there aren't enough keywords
to matter, and it is the one path where seo-write.md is never loaded at all.

── BROWSER PICKER (Case C, published) ──
Do NOT write a markdown/Obsidian file. Launch the shipped local web picker: it renders the
lists as a clean page with clickable controls (a per-keyword "Use as" dropdown — skip / Text /
Heading / FAQ — plus one free-text "New main keyword" box with type-ahead suggestions, NOT a
dropdown) and writes the selection back automatically.

1. The input file already exists: /tmp/seo-<slug>-kw.json, written by Stage 2 and pruned by
   your relevance strike. The picker shows current_main directly above the "New main keyword"
   box so the user can compare before promoting a replacement.
2. Run (this BLOCKS until the user clicks Save in the browser):
     python3 "$HOME/.claude/factcheck-flow/bin/keyword_picker.py" \
             --in /tmp/seo-<slug>-kw.json --out /tmp/seo-<slug>-sel.json
   It opens the page in the user's browser automatically. Tell the user: "I've opened a keyword
   picker in your browser — choose your keywords and click Save."
3. When it exits 0, read /tmp/seo-<slug>-sel.json — it already IS the SELECTION JSON below
   ({selected:[{keyword,list,use_in_heading,use_as_faq}], new_main_keyword}). Delete temp files
   at Stage 9. If the picker exits non-zero / can't open a browser (headless), FALL BACK to the
   Case B AskUserQuestion picker.

── Gate #2 SELECTION (produced by whichever path ran) ──
{
  "selected": [ {"keyword": "...", "list": "related|variation|competitor|highly_relevant|gsc_ranking|custom",
                 "use_in_heading": true, "use_as_faq": false, "new_main_keyword": false}, ... ],
  "new_main_keyword": "<the one keyword flagged new main, or null>"
}
Note: the picker's "New main keyword" control is a FREE-TEXT box, so new_main_keyword may be a
keyword the user typed that is NOT in any of the five lists — in that case its "selected" entry
carries list = "custom". Stage 7 applies it (H1/intro/meta/title) regardless of its list.
Note: the picker also has an "Additional keywords" section — free-text rows (each with a
Text/Heading/FAQ selector, and a + button to add more) where the user can type keywords that are
in NO list. Each filled row arrives as a normal "selected" entry with list = "custom" and the
usual use_in_heading / use_as_faq flags, handled exactly like any other selected keyword.

Selection semantics (apply in EVERY path — auto, scarce, picker):
- selected, use_in_heading = false and use_as_faq = false → weave the keyword into BODY TEXT only.
- selected, use_in_heading = true  → place it as an EXACT-MATCH heading AND weave it into that
  section's body text (a heading keyword ALWAYS also appears in text).
- selected, use_as_faq = true → add the keyword VERBATIM as an FAQ QUESTION in the article's FAQ
  block (proper Yoast FAQ schema; create the block if none exists). For its ANSWER: FIRST check
  whether ANY OTHER selected keyword is similar/related to this FAQ question — if so, work THAT
  keyword naturally into the answer. If none is related, write the answer using a sensible
  VARIATION of the FAQ keyword that fits the sentence — do NOT duplicate the question keyword or
  echo a near-identical phrase. use_as_faq is mutually exclusive with use_in_heading, and a new
  main keyword is never an FAQ.
- new_main_keyword → apply in the H1, intro text, meta description, and SEO title (Stage 7);
  implies use_in_heading. At most ONE new_main_keyword.
- a keyword with nothing selected is NOT used.
```

---

# → CONTINUE IN PART 2

Selection is done. **Now read `~/.claude/factcheck-flow/prompts/seo-write.md`** and run
S4 → S9 from it. Carry forward, and nothing else:

- is_draft, article type, post ID / slug / URL, status
- the CURRENT MAIN KEYWORD, and the heading tree
- the Stage 1 record: `selected_competitor_urls`, `structural_changes`, and your one-paragraph
  SERP-dominant-format / intent note
- the Gate #2 SELECTION JSON

The only exception is the PROCEED GATE skip above, which goes straight to /fact without
reading part 2.
