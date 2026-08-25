# /SEO — part 1: research & keyword selection (S0–S3)

> Executed by the `/SEO` command (`commands/SEO.md`), which asks "Is this a new article or a
> refresh?" as its first action and then runs the stages below. Part 2 —
> `prompts/seo-write.md` — carries S4–S9 and is read at the START OF S4, not now. This file
> is auto-synced from the factcheck-flow repo, so edits here propagate on the next session.

**Read `~/.claude/factcheck-flow/guides/core-rules.md` now, and nothing else yet.** It
carries the always-on rules plus the map of which full guide to open at which stage. The
writing guides (`Pabau-style-guide.md`, `2-editorial.md`, `WordPress-blocks.md`,
`Meta-title-best-practices.md`, `About-Pabau.md`, `Visuals.md`) are read by the `seo-writer`
subagent at S8 — never in this conversation. Part 2 reads exactly one of them,
`Originality-and-search-intent.md`, because the outline depends on it. Loading the rest here
would keep ~40k tokens resident through every remaining turn, which is the single most
expensive mistake in this flow.

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

Stages: **S0** draft-check + setup → **S1** SERP pick + answer surface → **S1B** ownership
pre-flight → **S2** build lists → **S3** keyword selection (routing above) → *[read part 2]* →
**S4** Outline → **S5** entities + SERP structure → **S6** group entities + structure refine →
**S7** write the brief → **S8** dispatch the `seo-writer` subagent (it writes and saves) →
**S9** cleanup, baseline, hand off to /fact.

Note the shape: this conversation RESEARCHES and PLANS; a subagent WRITES. The writing guides
(~40k tokens) and the article body are never loaded here — they live in the writer's context
and are discarded when it returns.

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
serp_fetch_script: "$HOME/.claude/factcheck-flow/bin/serp_fetch.py"
dfs_lists_script: "$HOME/.claude/factcheck-flow/bin/dfs_lists.py"
gsc_query_script: "$HOME/.claude/factcheck-flow/bin/gsc_query.py"
gsc_key: "$HOME/.claude/factcheck-flow/gsc-key.json"  # SECRET; not in repo. Override: $PABAU_GSC_KEY
gsc_property: "https://pabau.com/"   # URL-prefix property. Override: $PABAU_GSC_PROPERTY
gsc_windows: "28,90"                 # TWO windows. A single 90-day average cannot tell a
                                     # growing page from a dying one, and its average position
                                     # is dragged down by every day the page spent being
                                     # tested. The pair gives trend + an honest best position.
gsc_top_n: 25                        # candidate pool; re-sorted STRIKING DISTANCE FIRST
striking_band: [11, 20]              # positions 11-20 — one pass here beats a net-new target
page_one_push: [4, 10]               # already on page one, not yet top 3 — the second priority
cannibal_days: 28                    # ownership window (short on purpose: position testing
                                     # over 90 days reads as a fight that isn't there)

# Helpers (all ship with the command)
cannibal_script: "$HOME/.claude/factcheck-flow/bin/gsc_cannibal.py"
index_ping_script: "$HOME/.claude/factcheck-flow/bin/index_ping.py"
baseline_dir: "$HOME/.claude/factcheck-flow/cache/seo-baselines"   # per-slug run baseline
indexing_key: "$HOME/.claude/factcheck-flow/indexing-key.json"     # SECRET; not in repo
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

1. Fetch the SERP IN CODE, not in context. The raw `serp_organic_live_advanced` response is
   deeply nested — SERP features, rich-snippet sub-objects, per-result metadata — and this
   stage keeps four fields per result. Loaded here it would sit in context for the whole run,
   the same mistake Stage 2 already avoids. Run:
     python3 "$HOME/.claude/factcheck-flow/bin/serp_fetch.py" \
             --keyword "<CURRENT MAIN KEYWORD>" \
             --location "United States" --language en --depth 10 \
             --exclude-domain pabau.com \
             --out /tmp/seo-<slug>-serp.json
   It prints one summary line — {"out","kept","dropped_own","keyword","snippet","aio","paa",
   "title_gap","our_position"} — and writes the Gate #1 payload, already in the shape step 3
   describes and `serp_picker.py --in` expects. Paid results are dropped; our own domain is
   flagged `own_domain: true` (kept, not removed, so you can see where we rank).
   On a non-zero exit read the stderr message and fix it (usually credentials); do NOT fall
   back to calling the DataForSEO MCP tool by hand — that reintroduces the cost this avoids.

1b. READ THE ANSWER SURFACE — the ten blue links are no longer the whole SERP. The script also
   writes an `answer_surface` object beside them, and it is cheap to read (a few dozen lines).
   Record it as the ANSWER-SURFACE PROFILE — six facts, each with a consequence:

   · `featured_snippet` — who holds it and in what FORMAT (paragraph / list / table). Winning
     a snippet means MATCHING ITS FORMAT, not just writing a better page. If a competitor
     holds it, that format becomes a requirement on our target section, and part 2 plans it.
   · `ai_overview` — whether an AI Overview sits above the results, and which domains it
     cites. Two consequences: (a) an AIO suppresses organic CTR by itself, so a weak CTR at a
     strong position is the AIO, not our title; (b) its cited domains are the rank-stack to
     join — answer engines read roughly the first two or three pages of the SERP, so ranking
     on page one for this query IS the AI-visibility play. Note whether pabau.com is cited.
   · `paa` + `related_searches` — the SERP's own visible query fan-out. Keep every line: S4
     turns them into the fan-out branches the outline must cover, and they are the strongest
     FAQ candidates because they are Google's own phrasing of the follow-up question.
   · `features` — every other block present. `discussions_and_forums`, or a Reddit/forum
     result in the top 10, says this SERP wants lived experience — a hard pull toward the
     practitioner-angle nugget. A `video` block says the SERP rewards video; note it, but
     never plan a new one (the video rule is placement-only, never addition).
   · `title_gap` — how many ranking pages actually put the exact keyword in their TITLE.
     `wide-open` (none) means the page-one results rank for this phrase INCIDENTALLY rather
     than because they targeted it: the cheapest kind of keyword to take, and no difficulty
     score can see it. `claimed` (3+) is a real fight — expect to need the nugget and the
     structure to win it, not on-page placement alone.
   · `our_position` — where we rank right now, if at all. Positions 4-20 are the whole game
     for this run (see Stage 3); a page already at 11-20 moves on INFORMATION GAIN, not on
     more mentions of the phrase.

   Write the profile as six short lines. It travels to part 2 and into the brief.
2. Read that file (it is a short list) and apply the two judgments the script cannot make.
   First, drop from consideration any pure aggregator or anything paywalled/login-gated you
   can't open, and ignore rows flagged `own_domain`. Keep the ranked order.
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
3. The SERP-pick JSON (Gate #1 OUTPUT) already exists at /tmp/seo-<slug>-serp.json — step 1's
   script wrote it. Do not rebuild it by hand. Its shape is:

   {
     "main_keyword": "<string>",
     "serp": [
       {"rank": 1, "title": "<title>", "url": "<full exact live page URL, incl https://>",
        "domain": "<host>", "description": "<snippet>", "own_domain": false},
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
       1. The input file already exists: /tmp/seo-<slug>-serp.json, written by step 1's script.
          Nothing to build here.
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

# STAGE 1B — Ownership pre-flight: who already holds this keyword?  ⟨runs on BOTH branches⟩

```
Before committing a keyword to this article, find out whether another page on pabau.com
already owns it. This is the cheapest high-value check in the flow and it runs every time.

WHY IT MATTERS. Two of our own pages competing for one query does not double our chances —
it halves them: Google alternates which page it thinks is the better answer, and neither
settles. That is why the fix comes BEFORE the content work, not after. It is also why this
runs on the NEW-ARTICLE path too: a draft is the cheapest possible moment to discover that a
live page already owns the keyword, because nothing has been written to the wrong target yet.

RUN IT (one call, both branches):
  python3 "$HOME/.claude/factcheck-flow/bin/gsc_cannibal.py" \
          --page "<full article URL>" \
          --keyword "<CURRENT MAIN KEYWORD>" \
          --head-term "<the main keyword's HEAD TERM — its 1-2 core words>" \
          --days 28 \
          --out /tmp/seo-<slug>-cannibal.json

It prints one line — {"out","checked","verdicts","family","blockers","dropped_keywords"} —
and writes the per-keyword verdicts. Read the SUMMARY LINE, not the file; Stage 2 passes the
file to `dfs_lists.py`, which stamps the verdicts onto the keyword rows for you.

The `--head-term` pass is the one that catches what exact-match misses: it asks how the whole
term FAMILY is distributed across the site. Pick the head term by dropping every qualifier —
"how to reduce no-shows in aesthetic clinics" → "no-shows".

VERDICTS and what each one means for this run:
  unclaimed        no page on the site gets impressions for it. Free to target.
  ours / ours-clear this page already holds it. Nothing to settle — proceed.
  owned-elsewhere  another single page holds the large majority. Targeting it HERE creates
                   the split. This is a DECISION, not a warning (see below).
  split            two or more of our pages already compete and none has won. Already
                   cannibalized; adding a third contender makes it worse.

WHAT TO DO WITH A BLOCKER (`owned-elsewhere` or `split` on the CURRENT MAIN KEYWORD, or on
the family, or later on a proposed new main):

- is_draft == false (Refresh) → carry it to Gate #2 and ASK. Add ONE AskUserQuestion, only
  when there is a blocker, naming the competing URL and its share:
      "GSC says <competing URL> holds <keyword> (<share>% of impressions, position <n>).
       How should I handle it?"
      [Retarget this article to a different keyword]  (default — the picker's other lists stay open)
      [Make THIS page the owner]  (I optimize for it here; you strip it from the other page later —
                                  I will name that page in the final report, and never edit it)
      [Proceed anyway and accept the overlap]
  Never silently retarget, and never silently proceed — a keyword owner is a content-strategy
  decision, not a keyword-tool one.
- is_draft == true (New article) → decide it yourself and SAY SO in the setup summary. Prefer
  retargeting: pick the strongest non-blocked candidate from Stage 2 as the main keyword and
  leave the owned keyword to its owner. Only keep a blocked keyword when nothing else fits the
  draft's actual subject, and then say plainly that the split is deliberate and which URL it
  competes with.

A DRAFT'S URL WILL NOT BE IN GSC AT ALL. That is expected and it is exactly what makes the
check useful: on a draft, every verdict is `unclaimed` (nobody holds it — good) or
`owned-elsewhere` (a live page holds it — the finding). Do not read `owned-elsewhere` on a
draft as an error.

NON-ZERO EXIT means NO DATA, never "no cannibalization". On the published path treat it the
same way as the Stage-2 GSC failure: stop and say GSC isn't set up. On the draft path, note
that the check couldn't run and continue — a draft has nothing to lose by proceeding.
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
             --page "<full article URL>" --windows 28,90 --limit 25 > /tmp/seo-<slug>-gsc.json
   HARD REQUIREMENT on the published path. If it exits non-zero (missing key, PyJWT not
   installed, API error), STOP and tell the user GSC isn't set up — do NOT silently continue
   without this list. Fix path: place the key at gsc_key or set $PABAU_GSC_KEY, and install
   PyJWT (`python3 -m pip install --user pyjwt`). Drafts never call it.

   TWO windows, not one. A 90-day average cannot tell a page that is growing from one that is
   dying, and its average position is dragged down by every day the page spent being tested.
   The pull therefore also returns, per query, `best_position` (the honest ceiling), a `band`
   (top3 / page1 / striking / longtail), a `trend`, and a `ctr_gap`; and per PAGE, a `verdict`
   (growing / flat / declining) plus a `title_mismatch_signal`.

   READ THE PAGE-LEVEL BLOCK NOW — three lines, and they set the stance for the whole run:
     · verdict `declining` → this is a RESCUE. Refreshing a declining page beats writing a new
       one, and the decline is the reason the run exists. Say so; part 2 plans against it.
     · verdict `growing` → don't fight the trend. Optimize, but preserve what is working: the
       sections already earning the clicks are evidence, not scaffolding to rip out.
     · `title_mismatch_signal: true` → the page collects many one-off queries and no query
       bucket holds a real share of its clicks. That is the signature of a title targeting
       nothing coherent, and no amount of body copy fixes it. The SERP title and the H1 must
       be re-pointed at ONE winnable query bucket this run, whether or not the main keyword
       changes. Carry this flag to part 2 — it is a mandate, not a note.

2. Build every list in one call (add --gsc only on the published path):
     python3 "$HOME/.claude/factcheck-flow/bin/dfs_lists.py" \
       --main-keyword "<CURRENT MAIN KEYWORD>" \
       --article-title "<title>" --article-url "<url>" \
       --competitor-url "<url1>" --competitor-url "<url2>"   … one per Gate #1 URL \
       --gsc /tmp/seo-<slug>-gsc.json \
       --article-text /tmp/seo-<slug>-body.txt \
       --headings /tmp/seo-<slug>-headings.txt \
       --serp /tmp/seo-<slug>-serp.json \
       --cannibal /tmp/seo-<slug>-cannibal.json \
       --location "United States" --language en \
       --list-len 20 --competitor-top-n 25 \
       --out /tmp/seo-<slug>-kw.json
   It prints one summary line — {"out","total_kw","counts","current_main"} plus, when the data
   supports them, "striking_distance", "title_gap_keywords", "cannibal_flags",
   "page_verdict" and "title_mismatch_signal" — and writes the full payload to --out. On a
   non-zero exit, read the stderr message and fix it (usually credentials); do not fall back
   to calling the DataForSEO MCP tools by hand.

   `--serp` and `--cannibal` are what turn a keyword list into a decision list. Pass them on
   BOTH branches (the cannibal file exists on both — Stage 1B always runs).

   What the script has already done for you (do NOT redo any of it by hand):
     · list A RELATED — keyword_ideas + related_keywords, terms that DROP the main keyword's
       head term and name a distinct entity/subtopic;
     · list B VARIATIONS — keyword_suggestions, terms that KEEP the head term (reorder, synonym
       swap, plural, or main keyword + qualifier); qualifier variations (user group / use case)
       are surfaced at the top;
     · list C COMPETITOR — ranked_keywords for each selected URL, top competitor_top_n by
       traffic, pooled and deduped, each tagged with the competitor's rank;
     · list D GSC — the queries from step 1, enriched with difficulty + volume + CPC (display
       only, never filtered), `present_on_page` computed against your headings + body files,
       and each row carrying `best_position`, `band`, `trend`, `ctr_gap` and an
       `opportunities` list. The list is ordered STRIKING DISTANCE FIRST (11-20), then page
       one, then the top three — because a query already in striking distance is worth more
       than any net-new target, and one pass of information gain moves it;
     · list E HIGHLY RELEVANT — the raw top-20 by DataForSEO relevance, no tier filtering;
     · difficulty / volume / intent enrichment for every row, with absent KD recorded as the
       string "N/A" (never blank, never fabricated);
     · CPC on every row, as a COMMERCIAL-INTENT read and never an ad-relevance one. Advertisers
       bidding on a term is evidence somebody converts on it. The inverse is the trap: "no
       advertisers" is far more often informational intent, or a term advertisers already
       tested and abandoned, than an untapped opening. Treat zero CPC as a caution flag, never
       as a blue ocean, and never as a hard filter either way;
     · `title_gap: true` on every keyword that appears in NONE of the top-10 titles for the
       head term (from --serp). Those keywords are ranked for incidentally rather than
       targeted, and they are the cheapest to take — a signal difficulty scores cannot see;
     · `owns: <verdict>` on every keyword the Stage-1B pre-flight covered (from --cannibal),
       so a keyword another Pabau page holds is visible AT SELECTION TIME rather than after
       the article is written;
     · the tier fill (Tier 1 ≤10 difficulty and ≥20 volume, Tier 2 above the ceiling, Tier 3
       last resort with N/A difficulty at the bottom), the ranking, and the cross-list dedupe
       (priority gsc > competitor > related > variations > highly_relevant, overlap noted in
       the row's "why"). Lists shorter than 20 after dedupe are expected — never backfill.

3. THE ONE JUDGMENT THE SCRIPT CANNOT MAKE: topical relevance. **Delegate it — do NOT read the
   payload yourself.** It is ~100 rows, and once the picker has run the only keywords that
   matter are the handful the user selects; reading all 100 here would keep them resident for
   the rest of the run for nothing.

   Spawn ONE `general-purpose` subagent and give it exactly this job:

       Read /tmp/seo-<slug>-kw.json. It holds five keyword lists for an article about
       <one-line topic>, whose main keyword is "<CURRENT MAIN KEYWORD>". The site is
       pabau.com — practice management software for aesthetic and healthcare practices.

       STRIKE any row that is off-topic, off-intent, or a brand term that doesn't fit Pabau.
       The discovery endpoints happily return things like "minute clinic" or "the patient"
       for a clinic-software seed. Borderline rows STAY, with "review" appended to their
       "why" field. Relevance is never relaxed, not even in Tier 3.

       Rewrite /tmp/seo-<slug>-kw.json in place with the survivors, preserving the file's
       exact schema and every remaining row's fields verbatim — including `cpc`,
       `title_gap`, `owns`, `band`, `trend`, `best_position`, `opportunities`, and the
       top-level `answer_surface`, `cannibalization` and `page_diagnosis` objects. Do not
       reorder, re-rank, re-score, or backfill — only remove rows and tag borderline ones.

       Judge RELEVANCE ONLY. A row is not off-topic because its CPC is zero, because it is
       flagged `owns: owned-elsewhere`, or because its difficulty is high — those are
       selection inputs for later, and striking them here destroys the signal.

       Return ONE line and nothing else:
       STRUCK: <n> | REMAINING: <total> | LISTS: related=<n> variations=<n> competitor=<n> highly_relevant=<n> gsc_ranking=<n>

   Take the returned counts at face value; the picker reads the pruned file from disk, so you
   never need the rows themselves.

4. Report the per-list counts and total_kw from the subagent's line. That total drives the
   Stage 3 routing (recount from REMAINING, not from the pre-strike summary).
```

---

# STAGE 3 — Keyword selection  ⟨HUMAN GATE #2⟩

```
The payload written by Stage 2 IS the Gate #2 payload; its shape is:

{
  "article_title": "...", "article_url": "...",
  "current_main": {"keyword": "...", "difficulty": <int|"N/A">, "volume": <int|null>},
  "answer_surface": { ... },        // from --serp; the Stage-1 profile, verbatim
  "cannibalization": { ... },       // from --cannibal; the Stage-1B verdicts, verbatim
  "page_diagnosis": {"verdict","windows","page_totals","title_mismatch_signal",
                     "query_spread"},                       // published only
  "lists": {
    "related":        [ {"keyword","difficulty","volume","cpc","intent","why","title_gap",
                         "owns","new_main_candidate"}, ... ],
    "variations":     [ {...same...}, ... ],
    "competitor":     [ {...same...}, ... ],
    "highly_relevant":[ {"keyword","difficulty","volume","cpc","intent","title_gap","owns",
                         "relevance_rank"}, ... ],
    "gsc_ranking":    [ {"keyword","position","best_position","band","trend","ctr","ctr_gap",
                         "clicks","impressions","difficulty","volume","cpc","intent",
                         "present_on_page","title_gap","owns","opportunity","opportunities"},
                        ... ]   // STRIKING DISTANCE FIRST, then page one, then top 3
  }
}

"difficulty" is ALWAYS present on every row: an integer 0–100, or the string "N/A".
"highly_relevant" is ALWAYS present. "gsc_ranking" and "page_diagnosis" are present ONLY for
published articles (is_draft == false). Drafts show four lists; published shows five.

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
      - set use_in_heading = true where the keyword maps cleanly to a heading topic;
      - then apply the PRIORITY ORDER below, which overrides "strongest per list".
    Continue to Stage 4 (no proceed gate — there is plenty to do).
  • is_draft == false → PICKER PATH: launch the local web picker (below), which opens a
    clean page in the browser with a per-keyword role dropdown and a free-text "new main"
    keyword box. STOP until the user clicks Save; then read the selection JSON it writes.

── PRIORITY ORDER (applies to EVERY path — auto, scarce picker, browser picker) ──
This is the ranking the data now supports, and it beats "biggest volume wins" every time.
On the auto path it decides the selection. On a picker path it decides what you RECOMMEND:
say in one short paragraph which rows you would take and why, before opening the picker, so
the user is choosing against a read rather than a raw table.

1. STRIKING DISTANCE FIRST (published only). Any `gsc_ranking` row with `band: striking`
   (positions 11-20) outranks every net-new keyword in the payload. The page already has the
   relevance and the impressions; it needs the information gain. `band: page1` rows above
   position 3 come next. Chasing a fresh keyword while a query sits at 14 is the single most
   common waste in this flow.
2. TITLE/QUERY MISMATCH, if `page_diagnosis.title_mismatch_signal` is true. Then the FIRST
   job of this run is picking the one query bucket the title and H1 will own. Choose it here,
   explicitly, and prefer the bucket with real repeat impressions over the biggest volume.
3. OWNERSHIP VETO. Never select a keyword whose `owns` is `owned-elsewhere` or `split` unless
   Stage 1B's decision explicitly authorized it. It is not a scoring penalty — it is a veto.
   Log every keyword you dropped for this reason; those are findings for David, because the
   other page is where the fix lives.
4. TITLE-GAP BONUS. Among keywords of similar difficulty and volume, `title_gap: true` wins.
   Nobody on page one has claimed the phrase in a title, so placing it in ours — title, H1,
   first sentence — is often the whole job. This is the one signal that beats difficulty.
5. COMMERCIAL INTENT as the tiebreak, not the filter. A real CPC means advertisers pay for
   the click, so someone converts on it. "No advertisers" is a caution flag, not an
   opportunity. Never drop an otherwise strong informational keyword for a zero CPC — the
   article needs to answer the question either way.
6. CTR REPAIR. A `ctr_gap: severe` row at `band: top3`/`page1` is not a content job at all:
   it ranks and nobody clicks. Route it to the SERP-title rewrite instead of to a new
   section — UNLESS `answer_surface.ai_overview.present` is true, which explains the missing
   clicks on its own and means the title is probably fine.
7. FAN-OUT COVERAGE. Prefer keywords that also appear in `answer_surface.paa` or
   `related_searches`. Those are the sub-questions the SERP itself is asking, and part 2
   requires the outline to cover the branches.

── FIVE-SPOT PLACEMENT (the main keyword's non-negotiable placement) ──
Whichever keyword ends up as the main keyword goes in the SERP title, the H1, the FIRST
SENTENCE of the body, and the meta description, as an exact match, each one reading naturally.
That is four of the five classic spots. The fifth is the URL slug, and it is branch-dependent:

- is_draft == true (New article): the slug IS in scope. A draft has no live URL, no links
  pointing at it and no index entry, so aligning the slug to the main keyword costs nothing.
  Record the proposed slug in the selection and let the writer set it. Skip it when the
  existing slug already carries the keyword.
- is_draft == false (Refresh): the slug is NEVER touched. Not this run, not as a suggestion
  the writer might act on. If the slug is genuinely the problem, say so in the final report as
  a finding for David; changing a live URL is a separate, explicitly-requested job.

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
  "new_main_keyword": "<the one keyword flagged new main, or null>",
  "proposed_slug": "<kebab-case slug, DRAFTS ONLY — null on a refresh, always>"
}
The browser picker does not collect `proposed_slug`; you add it yourself on the draft path
per FIVE-SPOT PLACEMENT above. On a refresh it is `null`, with no exceptions.

IF A NEW MAIN KEYWORD WAS CHOSEN, re-run the ownership pre-flight on it before you leave this
stage — one extra call, and it is the keyword the whole article will be pointed at:
  python3 "$HOME/.claude/factcheck-flow/bin/gsc_cannibal.py" --page "<url>" \
          --keyword "<new main>" --days 28 --out /tmp/seo-<slug>-cannibal-main.json
A blocker here follows Stage 1B's rules: ask on the published path, decide and say so on the
draft path. Do not carry an unchecked new main keyword into part 2.
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
- the **ANSWER-SURFACE PROFILE** (S1 step 1b) — the six lines, including the PAA and
  related-search lines verbatim, because S4 turns them into the fan-out branches
- the **OWNERSHIP verdicts** (S1B): the summary line, any blocker, and the decision taken
- the **PAGE DIAGNOSIS** (published only): verdict, `title_mismatch_signal`, and the striking-
  distance queries with their `best_position`
- the Gate #2 SELECTION JSON, including `proposed_slug`
- the keywords you DROPPED for ownership, and which URL owns each — they go in the final report

The only exception is the PROCEED GATE skip above, which goes straight to /fact without
reading part 2.
