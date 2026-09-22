# /generate — part 1: route, commission, keywords & source harvest (G0–G4)

> Executed by the `/generate` command (`commands/generate.md`), which asks "Is this a locked
> target keyword, or a topic to research?" as its first action and then runs the stages below.
> Part 2 — `prompts/generate-write.md` — carries G5–G10 and is read at the START OF G5, not
> now. This file is auto-synced from the factcheck-flow repo, so edits here propagate on the
> next session.

**Read `~/.claude/factcheck-flow/guides/core-rules.md` now, and nothing else yet.** It carries
the always-on rules plus the map of which full guide to open at which stage. The writing guides
(`Pabau-style-guide.md`, `2-editorial.md`, `WordPress-blocks.md`, `Meta-title-best-practices.md`,
`About-Pabau.md`, `Visuals.md`) are read by the `article-generator` subagent at G9 — never in
this conversation. Part 2 reads exactly one of them, `Originality-and-search-intent.md`, because
the outline depends on it. Loading the rest here would keep ~40k tokens resident through every
remaining turn, which is the single most expensive mistake in this flow.

**Batch your tool calls.** Independent calls go in ONE message: the G1 SERP fetch is one call,
G3 is one script call, and G4's page reads fan out together. Every extra round-trip re-reads
the whole conversation.

---

## What makes this different from `/SEO`

`/SEO` improves a page that already exists. `/generate` creates one that does not. Four things
change because of that, and they shape every stage below.

1. **There is no GSC data for this page, and there never was.** No striking-distance list, no
   page diagnosis, no CTR gap, no baseline to write. The keyword priority order is therefore
   rebuilt around what a zero-authority page can actually win.
2. **There is no body to improve, so the source material has to come from somewhere.** What
   currently ranks IS Google's own statement of what a good answer looks like for the query, so
   G4 harvests it as a constraint set — the facts, figures, steps and structure the page has to
   match — instead of letting the writer fill the gaps from model memory.
3. **The page's biggest risk is that it should not exist.** Refreshing a declining page beats
   publishing a new one, and publishing onto a topic another page already owns adds a third
   competitor instead of fixing anything. G2 is the stage that catches both, and it runs before
   a single word is planned.
4. **The outline is the quality gate, not the draft.** A model that writes structure and prose
   in one pass anchors every later edit to a structure nobody chose. So the outline is planned,
   shown, and approved BEFORE any prose exists — which is also the cheapest place to fix it.

Stages: **G0** intake + route → **G1** SERP + answer surface → **G2** commission check
⟨GATE⟩ → **G3** keyword lists + selection → **G4** source harvest + entity/structure profile →
*[read part 2]* → **G5** searcher-intent note → **G6** outline + nugget → **G7** outline gate
⟨GATE⟩ → **G8** write the brief → **G9** dispatch the `article-generator` → **G10** route
verification, corner-stone links, commission record, hand off to /fact.

Note the shape: this conversation RESEARCHES and PLANS; a subagent WRITES. The writing guides
(~40k tokens) and the harvested source reports are never loaded here — they live in the
writer's context and are discarded when it returns.

---

## CONFIG (tweak these; referenced by the prompts below)

```yaml
location_name: "United States"
language_code: "en"
search_engine: "google"

# Keyword thresholds — enforced in code by bin/dfs_lists.py
difficulty_soft_ceiling: 10 # PREFER <= 10; fill from here first. NOT a hard cap.
difficulty_priority: 5      # 0-5 difficulty takes priority
volume_ideal: 100           # prefer >= 100
volume_ok: 50               # acceptable >= 50
volume_floor: 20            # normal floor; only the Tier-3 last resort may go below

# List sizes
list_target_len: 20         # each list should reach 20 keywords if the data allows
competitor_top_n: 25        # top keywords per selected competitor page
serp_depth: 10              # organic results pulled for the SERP gate

site_domain: "pabau.com"    # used to identify our own result + our own ranked keywords
status: "draft"             # NEVER anything else. /generate does not publish.

# Commission thresholds (G2)
duplicate_serp_position: 20   # we already rank here for the seed -> refresh, don't write new
duplicate_search_hits: 5      # WP search results to inspect for an existing page
cannibal_days: 28             # ownership window

# Helpers (all ship with the command)
serp_fetch_script:  "$HOME/.claude/factcheck-flow/bin/serp_fetch.py"
dfs_lists_script:   "$HOME/.claude/factcheck-flow/bin/dfs_lists.py"
cannibal_script:    "$HOME/.claude/factcheck-flow/bin/gsc_cannibal.py"
cluster_script:     "$HOME/.claude/factcheck-flow/bin/cluster_lookup.py"
sentence_script:    "$HOME/.claude/factcheck-flow/bin/sentence_check.py"
gsc_key: "$HOME/.claude/factcheck-flow/gsc-key.json"  # SECRET; not in repo. Override: $PABAU_GSC_KEY
gsc_property: "https://pabau.com/"                    # Override: $PABAU_GSC_PROPERTY
commission_dir: "$HOME/.claude/factcheck-flow/cache/generated"  # per-article commission record
```

---

## THE ROUTE TABLE (memorize this — G0 applies it and G10 verifies it)

The published URL prefix is decided by the TAXONOMY TERMS on the post, not by the slug and not
by the folder name. A draft's `link` field is only `https://pabau.com/?p=<id>`, so the route
cannot be read back from it — it is asserted from the terms.

| Destination | Set this | Term IDs |
|---|---|---|
| `/templates/` | tag `template` | **1382** |
| `/diagnostic-codes/` | category `diagnostic-codes` + one subcategory | **1549** + `icd-10-cm` 1550 / `icd11` 1551 / `snomed-ct` 1553 |
| `/procedure-codes/` | category `billing-codes` + one subcategory | **1433** + `cpt-codes` 1546 / `hcpcs` 1548 / `ccsd-codes` 1547 |
| `/blog/` | nothing — this is the default | — |

Three rules that are easy to get wrong:

- **The `templates` CATEGORY (4138) does not route anything.** Only the `template` TAG does.
  Four posts carry the category without the tag and they all sit under `/blog/`. Set the tag.
- **`diagnostic-codes` beats `billing-codes`** when a post somehow carries both. Never set both.
- A `/blog/` article is `/blog/` by having none of the routing terms. Do not invent a "blog"
  category to force it.

Topic categories are chosen SEPARATELY and additionally, from terms that already exist in
WordPress (`GET /wp-json/wp/v2/categories?per_page=100&_fields=id,name,slug`). Never create a
new category or tag, and never leave a post in `Uncategorized` (1).

---

# STAGE G0 — Intake, article type & route

```
You are running the /generate flow for ONE new article. The argument is $ARGUMENTS — a topic
or a target keyword. If none was given, ask for it and stop.

1. LOCKED-VS-TOPIC CHECK — the /generate command asks this as its VERY FIRST action, verbatim:
   "Is this a locked target keyword, or a topic to research?" -> 1. Locked keyword, 2. Topic.
   Map it: Locked keyword -> keyword_locked = true; Topic -> keyword_locked = false. If somehow
   unset, ask it now before any data work.
2. Load CONFIG and the ROUTE TABLE above. You have already read core-rules.md; read NO other
   guide yet.
3. CLASSIFY THE ARTICLE TYPE. This decides the block contract, the link budget and the meta
   title rules, so get it right before anything else:
   - CODE ARTICLE — the subject is a single billing or diagnostic code, or a small code family.
   - TEMPLATE ARTICLE — the subject is a downloadable form, worksheet, care plan, checklist,
     assessment or report the reader will fill in. The test is whether the page's payoff is a
     document the reader takes away, not whether the word "template" appears in the keyword.
   - LISTICLE — "best X", "top N", "X alternatives", a ranked or compared set of providers.
   - STANDARD GUIDE — everything else: how-to, definition, comparison, cost breakdown.
4. RESOLVE THE ROUTE from the type, and state it in one line:
   - CODE ARTICLE, ICD-9 / ICD-10 / ICD-10-CM / ICD-11 / SNOMED CT -> /diagnostic-codes/,
     category 1549 + the matching subcategory (1550 ICD-10-CM, 1551 ICD-11, 1553 SNOMED CT).
   - CODE ARTICLE, CPT / HCPCS / CCSD / any other procedure, service or billing code
     -> /procedure-codes/, category 1433 + the matching subcategory (1546 CPT, 1548 HCPCS,
     1547 CCSD). A code that fits no listed subcategory gets 1433 alone; say so.
   - TEMPLATE ARTICLE -> /templates/, tag 1382. Also add the `templates` category (4138) for
     the archive, but never rely on it to route.
   - Everything else -> /blog/, no routing term.
   If the type is genuinely ambiguous — a nursing care plan article that could be a guide about
   care plans OR a downloadable care-plan template — pick the one the SEARCH INTENT supports
   after G1, and say which way you went and why. Do not stall on it here.
5. PROPOSE THE SLUG. A draft has no live URL, no inbound links and no index entry, so the slug
   is fully in scope and it is one of the five keyword placements.
   - State the main keyword ONCE. Never repeat a word the folder already carries: it is
     `/templates/consultation-form`, not `/templates/consultation-form-template`.
   - CODE ARTICLES follow the existing conventions EXACTLY, or the page will not sit with its
     siblings: `cpt-code-<code>`, `hcpcs-code-<code>`, `ccsd-code-<code>`, `icd-10-code-<code>`
     (no dot: S99.141S -> `icd-10-code-s99141s`), and ICD-11 as
     `icd-11-<code>-<condition>-<qualifier>` (e.g. `icd-11-6a02-autism-spectrum-disorder-
     diagnosis-coding-guide`). Check a live sibling before you commit: 
     `GET /wp-json/wp/v2/posts?search=<code family>&per_page=3&_fields=slug,link`.
   - Lowercase kebab-case, no stop-word padding, no year.
   The slug is provisional until G3 fixes the main keyword; restate it there.
6. FIX THE RUN TOKEN. Every temp file in this flow is named `/tmp/gen-<run>-…`, where `<run>`
   is a short kebab-case token derived from the SEED, truncated to about 40 characters —
   `no-shows-med-spa`, `cpt-code-99213`. Fix it HERE and never change it: the slug is still
   provisional and may change at G3, so naming files after the slug would orphan half of them
   mid-run. State the token once, in the setup summary, and use it verbatim from now on.
7. Emit a short setup summary: topic, keyword_locked, article type, route, the term IDs you
   will set, the run token, the provisional slug, and the URL the post will have once someone
   publishes it (`https://pabau.com/<prefix>/<slug>/`). No writing, no fetching yet.
```

---

# STAGE G1 — SERP fetch → answer surface → competitor pick

```
Goal: read the SERP for the seed, and pick the results to mine. These SAME URLs are reused for
the source harvest and the entity profile in G4, so choose once.

1. Fetch the SERP IN CODE, not in context. Run:
     python3 "$HOME/.claude/factcheck-flow/bin/serp_fetch.py" \
             --keyword "<SEED KEYWORD>" \
             --location "United States" --language en --depth 10 \
             --exclude-domain pabau.com \
             --out /tmp/gen-<run>-serp.json
   It prints one summary line — {"out","kept","dropped_own","keyword","snippet","aio","paa",
   "title_gap","our_position"} — and writes the payload. Paid results are dropped; our own
   domain is flagged `own_domain: true` (kept, not removed, so you can see whether we already
   rank — which G2 needs).
   On a non-zero exit read the stderr message and fix it (usually credentials); do NOT fall back
   to calling the DataForSEO MCP tool by hand.

1b. READ THE ANSWER SURFACE. The script writes an `answer_surface` object beside the results and
   it is cheap to read. Record it as the ANSWER-SURFACE PROFILE — six short lines:

   · `featured_snippet` — who holds it and in what FORMAT (paragraph / list / table). For a NEW
     page the snippet is the most winnable SERP real estate there is, because winning it is
     mostly a matter of matching the format, and a new page is free to be built in that format
     from the first draft. Name the format as a requirement on our target section.
   · `ai_overview` — whether an AI Overview sits above the results and which domains it cites.
     Those domains are the rank-stack to join: answer engines read roughly the first two or
     three pages of the SERP, so ranking on page one for this query IS the AI-visibility play.
     Note whether pabau.com is cited.
   · `paa` + `related_searches` — the SERP's own visible query fan-out. Keep every line
     verbatim. G6 turns them into the branches the outline must cover, and they are the
     strongest FAQ candidates because they are Google's own phrasing of the follow-up question.
   · `features` — every other block present. A `discussions_and_forums` block or a Reddit result
     in the top 10 says this SERP wants lived experience, which pulls hard toward a
     practitioner-angle nugget. A `video` block is a note only: /generate never adds a video.
   · `title_gap` — how many ranking pages put the exact keyword in their TITLE. This is THE
     signal for a new page. `wide-open` (none) means the page-one results rank for this phrase
     incidentally rather than because they targeted it, which is the cheapest kind of keyword to
     take and the only kind a zero-authority page reliably takes. `claimed` (3+) means a real
     fight, and a new page usually loses it — say so, and prefer a different target at G3.
   · `our_position` — where pabau.com ranks for the seed today, if at all. This is a COMMISSION
     input, not a note: it goes straight into G2.

   Write the profile as six short lines. It travels to part 2 and into the brief.

2. Read that file (it is a short list) and apply the two judgments the script cannot make.
   First, drop pure aggregators and anything paywalled or login-gated you cannot open, and
   ignore rows flagged `own_domain`. Keep the ranked order.
   Then ASSESS INTENT using the two-bar summary and the query-pattern mapping in core-rules.md.
   Read the seed as a literal question and confirm what answer it demands ("how to…" wants a
   procedure; "best…" a ranked list; "what is…" a definition; "X vs Y" a comparison; "…cost"
   pricing; a bare code wants the code's meaning, its billing rules and its documentation
   requirements). Then from the kept results note the SERP-DOMINANT FORMAT and the depth the
   SERP rewards. Record this in ONE short paragraph — it is the intent floor every later stage
   must match, and it is what you carry into part 2.
   If the SERP-dominant format contradicts the ARTICLE TYPE you set in G0, the SERP wins:
   re-set the type and the route now, and say you did.

3. SELECT the results to mine, automatically — there is no human step here. Keep results that
   are GENUINE WRITTEN ARTICLES topically similar to the planned piece. EXCLUDE software
   directories and review aggregators (Capterra, G2, GetApp, Trustpilot, Software Advice and
   similar), homepages, product / pricing / category / landing pages, and thin listing pages
   with no real prose. Prefer the closest-matching, article-style pages. Aim for 3-6.
   If NONE qualify, fall back to every result with usable written content (exclude only pure
   link shells), and if there is truly nothing, note it and continue — G4's harvest is simply
   thinner and the originality bar goes UP, not down.
   Log which URLs you kept and why, as clickable markdown links, then CONTINUE.

4. Record the G1 SELECTION: { "selected_competitor_urls": ["<url>", ...] }
```

---

# STAGE G2 — Commission check: should this article exist?  ⟨HUMAN GATE #1, conditional⟩

```
The most expensive mistake /generate can make is writing a page the site already has. Two of
our own pages competing for one query does not double our chances, it halves them: Google
alternates which page it thinks is the better answer and neither settles. And a declining page
that already carries topical authority and ranking history will out-perform a brand-new page on
the same topic, usually by a wide margin — the bounce-back a refresh gets is not available to a
page with no history to bounce back on.

So: before a single word is planned, establish that this page has a reason to exist. FOUR
checks, run together in ONE message.

CHECK 1 — DO WE ALREADY RANK? Read `our_position` from the G1 SERP profile.
  · Position 1-20 for the seed -> a page already exists and already ranks. This is a REFRESH,
    not a new article. Blocker.
  · Position 21+ -> a page exists but is not competing. Usually still a refresh; carry it to
    the gate as a blocker so the human decides.
  · Absent -> no signal either way. Continue to check 2; absence here proves nothing.

CHECK 2 — DOES A PAGE ALREADY EXIST, RANKING OR NOT? The SERP cannot see a page that ranks
  nowhere, and those are exactly the pages a duplicate would collide with. Search WordPress
  directly, via the wordpress-access skill:
      GET /wp-json/wp/v2/posts?search=<seed>&per_page=5&status=publish,draft&_fields=id,link,title,status
  Read the titles. A page covering the same QUESTION is a blocker even when its wording differs;
  a page covering an adjacent question is not. Also check for an existing DRAFT — a half-written
  piece on the same topic is the same collision, and finishing it beats starting again.

CHECK 3 — WHO OWNS THE KEYWORD IN GSC? One call, on the URL this page WILL have:
      python3 "$HOME/.claude/factcheck-flow/bin/gsc_cannibal.py" \
              --page "https://pabau.com/<prefix>/<proposed-slug>/" \
              --keyword "<SEED KEYWORD>" \
              --head-term "<the seed's HEAD TERM — its 1-2 core words>" \
              --days 28 \
              --out /tmp/gen-<run>-cannibal.json
  Read the SUMMARY LINE, not the file; G3 passes the file to `dfs_lists.py`, which stamps the
  verdicts onto the keyword rows for you.
  The page does not exist in GSC and that is the point: every verdict comes back `unclaimed`
  (nobody holds it — free to target) or `owned-elsewhere` / `split` (a live page holds it — the
  finding). `owned-elsewhere` here is never an error, it is the answer.
  The `--head-term` pass is the one that catches what exact-match misses: it asks how the whole
  term FAMILY is distributed across the site. Pick the head term by dropping every qualifier.
  A non-zero exit means NO DATA, never "no cannibalization". Note that the check could not run,
  say so at the gate, and let the human decide with one fewer signal.

CHECK 4 — IS THIS TOPIC ACTUALLY OURS? Google's topical relevance is linear and literal, not
  associative: content adjacent to the core topic does not read as related just because a human
  can see the connection, and enough of it drags the whole site's focus down with it. The
  precedent is a CRM that chased informational keywords away from its product until its topical
  authority broke. Pabau's core topic is practice management software for aesthetic, medical and
  healthcare practices, and the clinical / billing / operational work those practices do.
      python3 "$HOME/.claude/factcheck-flow/bin/cluster_lookup.py" suggest \
              --title "<the working title>" --limit 8
  It returns the nearest posts and a cluster tally. Read the top similarity score and the tally:
  · A clear cluster with decent scores -> the topic sits inside our footprint. Fine.
  · Nothing above a weak score, or a tally scattered across unrelated clusters -> this topic is
    outside our footprint. That is a blocker, and "it gets search volume" is not an answer to
    it — volume is exactly what makes topical overreach tempting.
  Record the cluster and its pillar; G10 needs them for the corner-stone links, and part 2 needs
  the cluster for the link budget.
  The page is new, so the cluster store holds nothing for it and the cluster you just reasoned
  is the only assignment it has. Write it back once G3 locks the slug and the URL is real —
  that makes it canonical for everyone and stops /fact reasoning the same page again later.
  Re-run `suggest` with THE SAME FLAGS plus `--json`: `--limit` changes both the shortlist and
  the tally, so a bare `--json` run records evidence for a shortlist you never saw, and the
  audit trail then justifies a different decision from the one you made.
      python3 "$HOME/.claude/factcheck-flow/bin/cluster_lookup.py" suggest \
              --title "<the working title>" --limit 8 --json > /tmp/ev.json
      python3 "$HOME/.claude/factcheck-flow/bin/cluster_lookup.py" submit \
              --url "https://pabau.com/<prefix>/<slug>/" --title "<the working title>" \
              --cluster-id <cluster-id> --subcluster "<subcluster>" \
              --evidence-file /tmp/ev.json
  The evidence is required — an assignment nobody can audit is one David has to re-derive. With
  no write token the row queues on disk and goes up on the next run that has one, which is not
  a failure and never blocks this gate.

── THE VERDICT ──
Combine the four into ONE of three:

  COMMISSION — no existing page, keyword unclaimed or ours, topic inside the footprint.
               State it in two lines and CONTINUE. No question, no pause.

  REFRESH INSTEAD — a live page already covers this question or already ranks for the seed.
               BLOCKER.

  RETARGET — the topic is ours and uncovered, but the seed keyword is owned elsewhere or split.
               BLOCKER.

── THE GATE (blockers only) ──
On a blocker, ask ONE AskUserQuestion naming the specific competing URL and what it holds:

    "GSC / the site says <competing URL> already covers <keyword> (<evidence>).
     How should I handle it?"
    [Refresh that page instead]   — I stop here and you run /SEO <url> (usually the right call)
    [Retarget to a different keyword] — I pick the strongest unblocked candidate at G3
    [Write it anyway]             — a deliberate second page; I will say which URL it competes with

  On [Refresh that page instead]: STOP. Do not read part 2, do not create anything. Report the
  URL and tell the user to run `/SEO <url>` in a NEW session. That is a successful outcome for
  this command, not a failure — the flow found the cheaper win.
  On [Retarget]: carry the veto into G3, where the blocked keyword is struck from selection.
  On [Write it anyway]: continue, and carry the competing URL into the final report so the
  deliberate overlap is on the record.

  Never silently retarget, never silently proceed, and never resolve a blocker by deciding the
  existing page "isn't very good". Whether a weak page gets replaced or rewritten is a
  content-strategy decision with a redirect attached, not a keyword-tool one.
```

---

# STAGE G3 — Keyword lists + selection (ONE script call, then automatic selection)

```
G3 runs in code, not in context. `bin/dfs_lists.py` makes every DataForSEO call, applies the
CONFIG thresholds, classifies related vs variation, fills the tiers, dedupes across the lists
and writes the payload. Raw API JSON never enters the conversation.

1. Build the lists in one call. There is NO --gsc flag and NO --article-text / --headings:
   this page has no search history and no body, so four lists are built, not five.
     python3 "$HOME/.claude/factcheck-flow/bin/dfs_lists.py" \
       --main-keyword "<SEED KEYWORD>" \
       --article-title "<the working title>" \
       --competitor-url "<url1>" --competitor-url "<url2>"   … one per G1 URL \
       --serp /tmp/gen-<run>-serp.json \
       --cannibal /tmp/gen-<run>-cannibal.json \
       --location "United States" --language en \
       --list-len 20 --competitor-top-n 25 \
       --out /tmp/gen-<run>-kw.json
   It prints one summary line and writes the full payload. `--serp` and `--cannibal` are what
   turn a keyword list into a decision list — pass both, always. On a non-zero exit read the
   stderr message and fix it; do not fall back to the DataForSEO MCP tools by hand.

   What the script has already done (do NOT redo any of it by hand): list A RELATED, list B
   VARIATIONS, list C COMPETITOR (ranked_keywords per selected URL, tagged with the
   competitor's rank), list E HIGHLY RELEVANT; difficulty / volume / intent / CPC enrichment on
   every row with absent KD recorded as the string "N/A"; `title_gap: true` on every keyword
   that appears in NONE of the top-10 titles; `owns: <verdict>` from the cannibal file; the tier
   fill, the ranking and the cross-list dedupe. Lists shorter than 20 after dedupe are expected —
   never backfill.

2. THE ONE JUDGMENT THE SCRIPT CANNOT MAKE: topical relevance. **Delegate it — do NOT read the
   payload yourself.** It is ~80 rows and only a handful survive selection.

   Spawn ONE `general-purpose` subagent with exactly this job:

       Read /tmp/gen-<run>-kw.json. It holds four keyword lists for a NEW article about
       <one-line topic>, whose seed keyword is "<SEED KEYWORD>". The site is pabau.com —
       practice management software for aesthetic and healthcare practices.

       STRIKE any row that is off-topic, off-intent, or a brand term that doesn't fit Pabau.
       The discovery endpoints happily return things like "minute clinic" or "the patient"
       for a clinic-software seed. Borderline rows STAY, with "review" appended to their
       "why" field. Relevance is never relaxed, not even in Tier 3.

       Rewrite /tmp/gen-<run>-kw.json in place with the survivors, preserving the file's
       exact schema and every remaining row's fields verbatim — including `cpc`, `title_gap`,
       `owns`, and the top-level `answer_surface` and `cannibalization` objects. Do not
       reorder, re-rank, re-score, or backfill — only remove rows and tag borderline ones.

       Judge RELEVANCE ONLY. A row is not off-topic because its CPC is zero, because it is
       flagged `owns: owned-elsewhere`, or because its difficulty is high — those are
       selection inputs for later, and striking them here destroys the signal.

       Return ONE line and nothing else:
       STRUCK: <n> | REMAINING: <total> | LISTS: related=<n> variations=<n> competitor=<n> highly_relevant=<n>

   Take the returned counts at face value.

3. SELECT, AUTOMATICALLY. There is no picker on this flow — a new article has no history for a
   human to weigh, so the judgment is documented rather than delegated. Apply this PRIORITY
   ORDER, which is the /SEO order rebuilt for a page with zero authority.

   0. LOCKED KEYWORD. If keyword_locked is true, the given phrase IS the main keyword and rules
      1-2 below do not apply to it. They still decide the SUPPORTING keywords. The ownership
      veto (rule 3) still applies to the locked keyword: a blocker goes to the G2 gate.

   1. TITLE GAP FIRST — the top signal for a new page, and the one no difficulty score can see.
      A keyword is genuinely easy when the pages ranking for it do NOT put the exact phrase in
      their title, H1, URL slug and opening sentence: they rank for it incidentally, not because
      they targeted it, so a page that DOES target all four takes it without a fight. That is
      exactly what `title_gap: true` measures. Among keywords of similar volume, title_gap wins,
      and it beats a lower difficulty score.
   2. LONG-TAIL AND BOTTOM-OF-FUNNEL BEFORE THE HEAD TERM. A new page cannot take a head term
      the incumbents already own, and it does not need to: the buyer-intent variants around it
      are less competitive and worth more per click. For software that means the patterns
      "X vs Y", "X alternatives", "best X for <audience>", "how to X", "<thing> cost", and the
      workflow terms around the product rather than the category word itself. Prefer these over
      a broad informational term with a bigger number next to it — a site that fills up with
      top-of-funnel explainers starts reading as an informational blog rather than a software
      company, and that costs the commercial rankings that pay for it.
   3. OWNERSHIP VETO. Never select a keyword whose `owns` is `owned-elsewhere` or `split` unless
      the G2 gate explicitly authorized it. It is a veto, not a scoring penalty. Log every
      keyword you dropped this way with the URL that owns it — those are findings for David.
   4. COMMERCIAL INTENT as the tiebreak, not the filter. A real CPC means advertisers pay for
      the click, so someone converts on it. "No advertisers" is a caution flag — far more often
      informational intent, or a term advertisers tested and abandoned, than an untapped
      opening. Never drop a strong informational keyword for a zero CPC; the article has to
      answer the question either way.
   5. FAN-OUT COVERAGE. Prefer keywords that also appear in `answer_surface.paa` or
      `related_searches`. Those are the sub-questions the SERP itself is asking, and part 2
      requires the outline to answer each branch.
   6. DEMAND IS NOT ONLY VOLUME. A question real practices ask proves demand at zero recorded
      volume, and a code page's demand is the code's own usage, not its search estimate. Never
      drop an obviously-real question because the tool shows "N/A". Say when you are selecting
      on this basis.

   ONE PRIMARY KEYWORD PER URL. Pick exactly one main keyword. Everything else is either a
   VARIANT (a close rewording that belongs on THIS page — a section, a heading, an FAQ) or a
   SECONDARY (a distinct topic that needs its OWN page later). Do not cram a secondary into this
   article to "cover" it: a narrow page beats a broad one both for ranking and for being lifted
   as a citation, because answer engines slice documents into passages and a page about two
   subjects has no clean passage about either. List the secondaries as DEFERRED — they are the
   next articles, and they go in the final report.

   THE FIVE-SPOT PLACEMENT, all five in scope because nothing is live yet: the SERP title, the
   H1, the FIRST SENTENCE of the body, the meta description, and the URL SLUG. On a
   code article, on either code route, that third spot is `pdc_definition`'s first sentence plus
   the opening H2 section — the body carries no intro (§13). Restate the slug
   now that the main keyword is fixed, per G0 step 5.

4. Record the G3 SELECTION:

   {
     "main_keyword": "<the one primary keyword>",
     "keyword_locked": true|false,
     "proposed_slug": "<kebab-case slug>",
     "selected": [ {"keyword": "...", "list": "related|variation|competitor|highly_relevant|custom",
                    "use_in_heading": true, "use_as_faq": false}, ... ],
     "deferred": [ {"keyword": "...", "why": "needs its own page"} , ... ],
     "vetoed":   [ {"keyword": "...", "owned_by": "<url>"} , ... ]
   }

   Selection semantics:
   - use_in_heading = false, use_as_faq = false -> weave into BODY TEXT only.
   - use_in_heading = true -> an EXACT-MATCH heading AND the keyword woven into that section's
     body text. A heading keyword always also appears in text.
   - use_as_faq = true -> the keyword VERBATIM as an FAQ question in the Yoast FAQ block. For
     the ANSWER, first check whether any OTHER selected keyword is related — if so, work THAT
     one into the answer; if none is, use a sensible VARIATION of the FAQ keyword. Never echo
     the question phrase back. use_as_faq and use_in_heading are mutually exclusive.

5. IF THE MAIN KEYWORD IS NOT THE SEED, re-run the ownership pre-flight on it before leaving
   this stage — it is the keyword the whole article will be pointed at:
     python3 "$HOME/.claude/factcheck-flow/bin/gsc_cannibal.py" \
             --page "https://pabau.com/<prefix>/<proposed-slug>/" \
             --keyword "<new main>" --days 28 --out /tmp/gen-<run>-cannibal-main.json
   A blocker here goes back through the G2 gate. Never carry an unchecked main keyword forward.
```

---

# STAGE G4 — Source harvest + entity & structure profile  (FAN OUT — one subagent per URL)

```
This stage does what /SEO does not have to: it gathers the MATERIAL the article will be written
from. A page with no body cannot be improved, only written, and a model writing from memory
produces the exact failure this stage exists to prevent — plausible prose, unsourced numbers,
and the consensus summary an answer engine can already generate without us.

What currently ranks is Google's own statement of what a good answer looks like for this query.
Harvested, it becomes a CONSTRAINT SET: the facts the page has to contain, the structure it has
to match, and the ledger of what every competitor has that we would otherwise miss. It is never
material to copy, and it is never the source cited — a figure found on a competitor's page is
traced to ITS source and verified there, or it does not ship.

Do NOT open the competitor pages in this conversation. A parsed article page is 15-25k tokens
and there are several. The reports go to DISK; only the merge ever reads them.

Dispatch one `general-purpose` subagent PER selected_competitor_url — ALL IN ONE MESSAGE so
they run concurrently. Give each its URL, its index <n>, and these instructions:

    Open <URL> (use on_page_content_parsing, or WebFetch with a high token limit) and read the
    MAIN CONTENT only — ignore nav, footer, cookie banners and CTA boilerplate. Return a
    COMPACT report and nothing else, in this shape. Do not include the page text.

    FACTS: the substantive, checkable claims this page makes about <topic> — definitions,
    figures, rates, prices, dates, eligibility rules, step sequences, requirements, code
    descriptors. Up to 15, one line each. For EVERY figure, name the source the page credits
    (an agency, a study, a vendor's own site) or write "UNSOURCED". This is the material the
    article gets written from, so be concrete: "documentation must include X, Y and Z" beats
    "covers documentation requirements".

    ENTITIES: the salient recurring words/phrases — domain nouns, named concepts, features,
    sub-topics. Ignore stopwords and site-brand chrome. For each: canonical label + the variant
    spellings/synonyms used on this page. Cap at 30, ordered by salience.

    HEADINGS: the full H1-H4 tree in document order, one per line, each tagged with the heading
    PATTERN (question / how-to / X-vs-Y / number+noun / benefit-led / plain).

    FORMATS: every structured presentation and what it holds — comparison/pricing/spec TABLES
    (with their columns), ordered (step) and unordered LISTS, FAQ blocks, definition boxes,
    pros/cons, checklists, "at a glance" boxes, how-to/FAQ schema. Note any place the page is
    plainly competing for a FEATURED SNIPPET (short answer + list/table).

    WEAKNESSES: vague or keyword-stuffed headings, missing or thin tables/lists, disorganized
    flow, obvious subtopics with no heading of their own, claims made with no source.

    UNIQUE DATA: the things THIS page has that a generic article on the topic would not — a
    real number with its source, a named framework, a first-hand account, a price, a dated
    benchmark, an original screenshot, a quoted practitioner. Up to 6, one line each. This is
    the information-gain ledger: what we have to match or beat.

    ANSWER SHAPE: does the page open each section with a short self-contained answer, or bury
    it under preamble? One sentence. If it does answer up front, quote ONE example capsule
    verbatim (under 30 words) so we can see the bar.

    Total under 900 words. Write it to /tmp/gen-<run>-src-<n>.md and write nothing else there.
    Then return ONE line and nothing else:
    DONE: <n> | <url> | facts=<count> entities=<count> headings=<count> formats=<short list>

FOR A CODE ARTICLE, add ONE MORE subagent alongside them — the AUTHORITY pass. A code page's
facts come from the code authority, never from the SERP, and the ranking pages are only a guide
to structure. Give it:

    Verify <CODE> against its issuing authority and return the primary record. Sources, in
    order: ICD-10-CM -> CMS and the CDC/NCHS tabular list; ICD-11 -> the WHO ICD-11 browser;
    CPT -> the AMA; HCPCS -> CMS; CCSD -> the CCSD schedule; MBS (Australia) -> the item pages
    at www9.health.gov.au. Note that health.gov.au and servicesaustralia.gov.au refuse
    connections from here; read a blocked page through the r.jina.ai text proxy instead.
    Return, each with the URL it came from: the exact official descriptor, the code's status
    and effective dates, its parent/child codes, any billing or documentation requirement
    stated by the authority, and anything the authority says that the ranking pages get wrong.

    THEN HARVEST THE CODE-PAGE FIELD VALUES. A code page renders its whole top area — badge, H1,
    flag line, Related Information card — out of post meta, not out of the body, so these values
    have to be sourced HERE or they cannot be written at all (`WordPress-blocks.md` §13). Return
    them as a labelled CODE FIELD RECORD, one per line, each with the URL it came from. The
    record has three parts — required, conditional and optional — and they are treated
    differently.

    REQUIRED — six of the eight ALWAYS-REQUIRED `pdc_*` fields are sourced here, and each one
    must carry a value or an explicit `NOT STATED`:
      · code_type   — `ICD-10-CM Code` / `CPT Code` / `HCPCS Code`, as the authority names it
      · code        — the code itself, dotted, exactly as the authority writes it
      · descriptor  — the OFFICIAL descriptor, VERBATIM, including any 7th-character clause
      · chapter     — the FIRST of three generic reference slots. `<range> <official chapter
                      title>` for ICD; for another code system, whichever top-level reference
                      fact is most useful (the live HCPCS page J8650 carries `Level II` here)
      · category    — the SECOND slot. `<code> <official category title>` for ICD; same idea
                      otherwise (J8650: `J — Drugs administered other than oral method`)
      · group       — the THIRD slot. `<code> <official group title>` for ICD; same idea
                      otherwise (J8650: `Deleted, effective 31 December 2025`)
    (The remaining two required fields — `h1_descriptor` and `definition` — are prose the writer
    composes from this record. Do NOT write them here.)

    CONDITIONAL — two fields, sourced here ONLY where the code system has the distinction:
      · billable    — yes / no, per the authority
      · specific    — yes / no (a specific code, or an unspecified / NOS one?)
                      Every ICD-10-CM code has both. Where the code system states no
                      billable/specific status at all — HCPCS J8650 is the live example — write
                      `NO SUCH DISTINCTION` on both lines. That leaves `pdc_billable` and
                      `pdc_specific` EMPTY, which hides the flag line under the H1 and the
                      Billable row in Related Information. It is correct, not a gap, and a
                      yes/no is never invented to fill it.

    OPTIONAL — never filled to make the record look complete:
      · also_known  — a genuine official synonym the authority itself gives for the code, or
                      `NOT STATED`. On this line `NOT STATED` means **leave `pdc_also_known`
                      empty**: empty is the normal, correct state, the Related Information row
                      hides when it is empty, and it is NOT a gap for anyone downstream to fill.
                      Never coin a synonym, never paraphrase the descriptor into one.
      · label_1/2/3 — the row LABELS for the three slots above, in that order (1 → chapter,
                      2 → category, 3 → group). Leave all three `NOT STATED` unless the
                      template's default label for this code type would be WRONG for the value
                      you harvested — J8650 needs `label_3 = Status` because its third slot
                      carries a deletion status rather than a code group. Never propose a label
                      that matches the default anyway.
    (`pdc_h1_prefix` is the remaining optional field. It is always left empty, so it is not part
    of this record at all — do not harvest a value for it.)

    Every value is the authority's own wording, not a paraphrase. Where the authority does not
    state one, write `NOT STATED` — never a guess. On a REQUIRED line that is a gap the writer
    reports under `Skipped`; on the `also_known`, `label_*`, `billable` and `specific` lines it
    simply means the field stays empty.
    These strings ship to the live page unedited, and an invented hierarchy label is invisible in
    the WordPress editor.

    Under 500 words plus the CODE FIELD RECORD, written to /tmp/gen-<run>-authority.md. Return
    ONE line: DONE: authority | <n> facts | <n> sources | required=<n stated>/6 |
    billable_specific=<stated|no-such-distinction> | also_known=<stated|empty>. Count only the
    six REQUIRED lines in the required tally — an empty `also_known`, `label_*`, `billable` or
    `specific` never counts as a miss.

Then dispatch ONE `general-purpose` merge subagent, pinned to **`model: sonnet`** — merging
already-structured reports into a fixed shape does not need a stronger model. Give it the file
PATHS, not the contents:

    Read every /tmp/gen-<run>-src-*.md file listed below (and /tmp/gen-<run>-authority.md if
    it exists). They are analyses of the <N> pages currently ranking for "<MAIN KEYWORD>".
    Merge them into ONE profile and return it as your entire reply. Do not quote the sources.

    SOURCE FACTS — the merged, deduped fact list, grouped by subtopic. Mark each fact CONFIRMED
    (2+ pages agree, or the authority states it), CONTESTED (pages disagree — say how), or
    SINGLE (one page only). Keep the credited source on every figure, and keep "UNSOURCED"
    where that is what it is. Where the authority file contradicts the ranking pages, the
    authority wins and you say so in one line. This section is the article's raw material —
    give it the most space.

    ENTITY LIST — keep a term only if it appears on ALL pages, or at minimum on >= 2. Match
    SEMANTICALLY, not by exact string: group synonyms into one entity and record the variants.
    Output per entity: canonical label, variants seen, page coverage count ("3/4 pages").
    Order by coverage desc, then salience.

    SERP STRUCTURE PROFILE:
    - consensus heading map: the subtopics the SERP consistently gives headings to, with the
      dominant heading pattern for each. This is the structural floor we must match.
    - format inventory: which structured formats dominate ("5/6 pages use a comparison table"),
      plus any featured-snippet opportunity.
    - WEAKNESSES TO BEAT: the pooled weaknesses, and — most important — what NEW useful data we
      could present as a table or list that none of the ranking pages offer.

    INFORMATION-GAIN LEDGER:
    - HAVE: unique data points appearing on 2+ pages — the SERP's shared baseline. Anything
      here that our article lacks is a gap that makes us an incomplete answer.
    - RARE: unique data points on exactly ONE page. The differentiators in play; name the page.
    - ABSENT: what NONE of them has, that this topic obviously calls for and we could credibly
      supply — a real number, a decision rule, a worked example, a practitioner account, a
      country-specific detail. Be concrete; "more depth" is not an entry.
    - ANSWER SHAPE: how many pages open sections with a short self-contained answer, and how
      good the best example was. That sets the bar for our capsules.

    CODE FIELD RECORD — if /tmp/gen-<run>-authority.md carries one, reproduce it VERBATIM, line
    for line, with each source URL and every `NOT STATED` intact. Do not summarize it, reword a
    descriptor or "tidy" a hierarchy label: these lines are written into post meta and rendered
    on the live page exactly as they arrive.

    Keep the whole reply under 1200 words; the CODE FIELD RECORD does not count toward that. It
    is the only thing that survives this stage.

What that subagent returns IS the profile. Keep it — part 2 turns it into the outline and the
writer receives it in the brief. Do NOT delete the /tmp/gen-<run>-src-*.md files yet: the
writer reads them directly for the detail the merge had to compress. They are deleted at G10.
```

---

# → CONTINUE IN PART 2

Research is done. **Now read `~/.claude/factcheck-flow/prompts/generate-write.md`** and run
G5 → G10 from it. Carry forward, and nothing else:

- the article TYPE, the ROUTE and its term IDs, and the URL the post will have when published
- `keyword_locked`, the MAIN KEYWORD and the `proposed_slug`
- the G1 record: `selected_competitor_urls` and your one-paragraph SERP-dominant-format /
  intent note
- the **ANSWER-SURFACE PROFILE** (G1 step 1b) — the six lines, with the PAA and related-search
  lines verbatim, because G6 turns them into the fan-out branches
- the **COMMISSION VERDICT** (G2): the verdict, any blocker, the answer given at the gate, and
  the CLUSTER + PILLAR from check 4
- the G3 SELECTION JSON, including `deferred` and `vetoed`
- the **SOURCE + STRUCTURE PROFILE** from G4, and the paths of the per-page source files
- on a CODE ARTICLE, the **CODE FIELD RECORD** from G4, verbatim — it is what populates six of
  the eight ALWAYS-REQUIRED `pdc_*` fields the code-page template renders
  (`WordPress-blocks.md` §13), plus the two CONDITIONAL fields `pdc_billable` and `pdc_specific`
  where the code system has them; the
  writer composes the other two required fields, `pdc_h1_descriptor` and `pdc_definition`, and
  leaves the five OPTIONAL fields (`pdc_h1_prefix`, `pdc_also_known`, `pdc_label_1/2/3`) empty
  unless the record names a genuine synonym or a default row label would be wrong
- the paths of every temp file, so G10 can clean up
