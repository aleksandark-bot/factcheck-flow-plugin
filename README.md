# factcheck-flow

A Claude Code plugin that batch-QAs WordPress articles. You give it a set of article
URLs (or post IDs); it runs three passes over each, with **one** human checkpoint in
the middle:

1. **Fact-check (parallel, read-only)** — one agent per article reviews accuracy,
   categories/tags, links, and structure, and returns a findings report. Nothing is
   written yet.
2. **Triage (you)** — you approve / reject / edit **each** finding individually, and
   supply any values only you can know (e.g. correct Capterra/G2/Trustpilot scores).
3. **Apply + editorial + links (parallel, automated)** — one agent per article applies
   the approved fixes, then the editorial pass, then the link-audit pass, writing
   changes back over the WordPress REST API.

Your only manual actions are handing over the URLs and doing the triage. Everything
else runs automatically.

## Install

In Claude Code:

```
/plugin marketplace add <this-repo-or-local-path>
/plugin install factcheck-flow@factcheck-tools
```

(You can also `/plugin marketplace add /absolute/path/to/factcheck-flow-plugin` for
local testing before pushing to a git host.)

## One-time setup: WordPress credentials

Credentials are **not** stored in this plugin. The `wordpress-access` skill carries only
the resolution order, which is the same on every install — that's what lets the skill be
auto-synced along with the prompts. Pick whichever of the three sources suits you:

1. In WordPress, create an **Application Password**: Users → Profile → Application
   Passwords.
2. Then either:

**a) The installer's file (simplest).** `install.sh` prompts for the three values and
writes them to `~/.claude/factcheck-flow/wp-credentials` (mode 600, never in the repo).
Nothing else to configure — the skill looks there by default.

**b) Point at a credentials file you already have.** Set `WP_CREDENTIALS_FILE` to its
path in `~/.claude/settings.json`:

```json
{
  "env": {
    "WP_CREDENTIALS_FILE": "/path/to/your/wp-credentials"
  }
}
```

The file may be `KEY=VALUE` lines (`WP_BASE_URL=…`, `WP_USER=…`, `WP_APP_PASSWORD=…`) or
a plain document with `Site URL:`, `Username:`, and `Application Password:` labels.
Only the *path* goes in settings — the secret stays in the file.

**c) Environment variables**, if you prefer them, in `.claude/settings.local.json`:

```json
{
  "env": {
    "WP_BASE_URL": "https://your-site.com",
    "WP_USER": "your-wordpress-username",
    "WP_APP_PASSWORD": "xxxx xxxx xxxx xxxx xxxx xxxx"
  }
}
```

Env vars win over `$WP_CREDENTIALS_FILE`, which wins over the default path.
`settings.local.json` is git-ignored — never commit real credentials. Restart the
session after any of these so the settings load.

## Use

```
/factcheck-flow https://your-site.com/blog/article-one/ https://your-site.com/blog/article-two/ 12345
```

Accepts full URLs or bare post IDs, whitespace-separated, up to ~5 at a time.

Two single-article commands sit alongside it: `/SEO <url-or-id>` optimizes an article that
already exists, and `/generate <topic>` writes a new one as a draft. Both finish by handing off
to `/fact`.

## /SEO — single-article optimization

`/SEO <url-or-id>` optimizes ONE article end to end: it researches keywords (DataForSEO +
Google Search Console), lets you choose which to target, rewrites/adds headings and content
around them, updates the main keyword / meta description / SEO title when you promote a new
main keyword, and then automatically runs `/fact` on the same article.

Its first question is always **"Is this a draft?"**

- **Draft** → fully automatic keyword selection, then it saves and runs `/fact`.
- **Published** → it also pulls the queries the page already ranks for from GSC, and opens a
  clean keyword picker in your browser; you choose keywords, click Save, and it continues.
- If very few keywords are found, it falls back to an in-chat multiple-choice picker and asks
  whether to optimize at all before proceeding.

The flow is split in two so the writing instructions and writing guides stay out of context
during the research stages: `prompts/seo-research.md` (S0–S3, read at the start) and
`prompts/seo-write.md` (S4–S9, read only once you pass the proceed gate). Both are auto-synced
like the other prompts. The command is `commands/SEO.md`. Helpers: `bin/gsc_query.py` (GSC),
`bin/gsc_cannibal.py` (keyword-ownership pre-flight), `bin/dfs_lists.py` (builds all five
keyword lists in code), `bin/keyword_picker.py` and `bin/serp_picker.py` (the browser pickers),
`bin/serp_fetch.py` (the SERP + its answer surface), `bin/index_ping.py` (the re-crawl request).

### What the flow decides on, beyond volume and difficulty

- **The whole answer surface, not ten blue links.** `bin/serp_fetch.py` also summarizes the
  featured snippet (holder + FORMAT, because winning it means matching the format), whether an
  AI Overview sits on top and which domains it cites, the People-also-ask and related-search
  queries, every other SERP block present, and a **title-gap** verdict — how many ranking pages
  actually put the exact keyword in their title. A phrase none of them claimed is far cheaper
  to win than its difficulty score suggests.
- **Who already owns the keyword.** `bin/gsc_cannibal.py` (Stage 1B, both branches) asks GSC
  which page on the site holds each candidate keyword. Two of our own pages competing for one
  query halves both their chances, so a blocker is a question on the refresh path and a stated
  decision on the new-article path — never a silent overlap.
- **Striking distance first.** The GSC pull runs two windows (28 + 90 days), so every query
  carries a trend, an honest `best_position` (a long average is dragged down by every day the
  page was being tested), a band, and a CTR gap. Positions 11–20 outrank every net-new keyword:
  the relevance is already there and what it needs is information gain.
- **Title/query mismatch and CTR repair.** A page collecting many one-off queries with no
  coherent bucket has a title problem no body copy fixes, and a page that ranks but gets no
  clicks needs a title rewrite rather than a new section. Both are detected and routed.
- **Commercial intent.** Every keyword carries CPC — advertisers bidding is evidence somebody
  converts; "no advertisers" is a caution flag, never a blue ocean. A tiebreak, never a filter.
- **Fan-out coverage.** The outline has to answer 3–6 named sub-question branches, built from
  the SERP's own PAA and related searches plus a decomposition by audience, constraint and use
  case — the branches an answer engine splits the query into before it assembles an answer.
- **Information gain, not word count.** The competitor pass returns an information-gain ledger
  (what the SERP shares, what only one page has, what none has), and the brief carries a closed
  GAIN IN / GAIN OUT pair. GAIN OUT is the originality nugget stated as information.
- **Capsules.** Roughly 60–70% of sections open with a 20–25 word self-contained answer that
  makes sense quoted alone — the form a snippet and an answer engine can lift.

### What it reports instead of doing

`/SEO` edits ONE article. Three things it finds are edits elsewhere, so it names them precisely
and stops: **ownership findings** (the competing URL for a vetoed keyword), **corner-stone
links** (3–5 already-ranking pages that should link INTO this article, with anchors), and
**slug findings on a published post**. It never changes a live URL or publish status.

On a published article it also writes a dated **baseline** to
`~/.claude/factcheck-flow/cache/seo-baselines/` and requests a re-crawl of the already-public
URL. Google tests a changed page for roughly two weeks, so the baseline plus a named review
date is what lets the next run tell improvement from noise.

`bin/dfs_lists.py` needs DataForSEO credentials. It resolves them from `$DATAFORSEO_LOGIN` +
`$DATAFORSEO_PASSWORD`, or `$DATAFORSEO_AUTH` (base64 `login:password`), or
`~/.claude/factcheck-flow/dataforseo-key.json`, and finally falls back to the `dataforseo` MCP
server entry in `~/.claude.json` — so if you already have that MCP server configured, it works
with no extra setup.

## /generate — create a new article as a draft

`/generate <topic-or-keyword>` writes ONE brand-new article and creates it in WordPress as a
**draft**. It never publishes, and it never touches an existing post.

Its first question is always **"Is this a locked target keyword, or a topic to research?"**

- **Locked keyword** → the phrase you gave IS the main keyword; research decides everything else.
- **Topic** → the argument is a seed, and the flow picks the main keyword from the data.

The flow is split in two, like `/SEO`: `prompts/generate-research.md` (G0–G4) and
`prompts/generate-write.md` (G5–G10, read only after the research is done). The writing itself
happens in the `article-generator` subagent, which loads the writing guides and the harvested
source material in its own context and creates the post. The command is `commands/generate.md`.

### The route table — where the article lands

The published URL prefix is decided by the **taxonomy terms**, not by the slug. A draft's `link`
is only `https://pabau.com/?p=<id>`, so the route is asserted from the terms, at creation and
again at G10.

| Destination | What puts it there |
|---|---|
| `/templates/` | the **tag** `template` (ID 1382) |
| `/diagnostic-codes/` | the **category** `diagnostic-codes` (1549) + a subcategory (1550 ICD-10-CM / 1551 ICD-11 / 1553 SNOMED CT) |
| `/procedure-codes/` | the **category** `billing-codes` (1433) + a subcategory (1546 CPT / 1548 HCPCS / 1547 CCSD) |
| `/blog/` | none of the above — the default for everything else |

The `templates` **category** (4138) does not route anything; only the tag does. Four posts on
the site carry that category without the tag and they all sit under `/blog/`.

### What it adds on top of /SEO's research

`/SEO` improves a page that exists. `/generate` creates one that does not, and four stages exist
only because of that difference.

- **A commission check before anything is planned (G2).** Four signals — do we already rank for
  the seed, does a page (published *or* draft) already cover the question, who owns the keyword
  in GSC, and does the topic sit inside our cluster footprint. A hit is a blocking question with
  **[Refresh that page instead]** as the usual answer: a declining page with ranking history
  out-performs a brand-new page on the same topic, and a second page on an owned keyword adds a
  third competitor rather than fixing anything. Ending in "run /SEO on that URL" is a successful
  outcome for this command.
- **A source harvest, not just an entity pass (G4).** One subagent per ranking page returns the
  substantive FACTS — figures, rates, requirements, step sequences — each with the source the
  page credits or marked UNSOURCED, alongside the usual entities, headings, formats and
  information-gain ledger. Merged, they are the material the article is written from. A model
  writing a new page from memory fills the gaps itself, and the gaps are where the errors are.
  Code articles get an extra **authority pass** (CMS/CDC, WHO, AMA, CCSD, MBS) that wins over
  every ranking page it contradicts.
- **A written searcher-intent note before any structure exists (G5).** Four questions: who is
  typing this, what would insult them to be told, what they need in hand when they leave, and
  what would send them back to the SERP. It is the shortest stage in the flow and the outline is
  tested against it.
- **A mandatory outline gate (G7).** Always asked, never skipped. A model that writes structure
  and prose in one pass anchors every later edit to a shape nobody chose — the human reviewing
  the finished draft is only ever editing *within* it. Reviewing the outline costs a sentence;
  reviewing an anchored article costs a rewrite that usually does not happen.

Keyword selection is rebuilt for a page with no authority: **title gap first** (a phrase none of
the ranking pages put in their title, H1, slug and opening sentence is one they rank for
incidentally — the only kind a zero-authority page reliably takes), then long-tail and
bottom-of-funnel before the head term, then the ownership veto, with CPC as the tiebreak. Exactly
one primary keyword per URL: everything else is either a variant on this page or a **deferred**
keyword that gets its own page later.

### What it reports instead of doing

- **Corner-stone inbound links** — 3–5 already-ranking pages in the same cluster that should link
  INTO the new article, with anchors. A page that ranks generates authority by ranking, with no
  backlink involved, and a new page has none of its own; an orphan starts from zero and stays
  there. Named, never edited.
- **Deferred keywords** — the secondary topics that need their own article. These are the next
  `/generate` runs, not sections of this one.
- **Ownership findings** — keywords another pabau.com page holds, with the competing URL.

It never publishes, never calls the indexing API (the URL does not exist yet), and never edits
another page. The durable output is a **commission record** in
`~/.claude/factcheck-flow/cache/generated/` — the route, the keyword, the verdict, the cluster
and the deferred keywords — which is what stops a later run from writing the same page twice.
Every run ends by handing off to `/fact`, which is the human-reviewed pass that verifies the
finished prose against its sources.

### Cluster data (the link pass)

`/fact`'s link pass resolves every article's content cluster before it touches a link, and
refuses to guess when it can't. That assignment comes from the **central cluster store**, which
the installer and `update.sh` pull for you — nothing to download by hand:

    clusters/base.jsonl         every assigned page, one JSON row each
    clusters/clusters.json      the cluster definitions (pillar, hubs, subclusters, tier)
    clusters/review-queue.json  the retirement / reassign bucket
    clusters/additions.jsonl    assignments made since the last consolidation

The store lives on the **`clusters-data` branch** of this repo, not on `main`. The two are
fetched independently: an assignment pushed to the data branch must never make the updater
re-fetch `main` and overwrite someone's local prompt edits. `clusters/CONTRACT.md` on that
branch is the binding description of the format and the precedence rules.

Where a machine also has the **`~/Desktop/pabau-content-clusters.xlsx` workbook** (or
`$PABAU_CLUSTERS_XLSX`), it is read as well and it outranks the network, so editing the
workbook still beats anything the branch says. Most machines have no workbook, and that is a
normal setup, not a broken one — reading `openpyxl` (`python3 -m pip install --user openpyxl`)
matters only where the workbook exists.

Optional but recommended: **`~/Desktop/linkmap/graph.json`** (or `$PABAU_LINKMAP_GRAPH`) — the
current internal-link graph, which supplies inbound counts for the anti-orphan and
equity-spreading rules. Without it the pass still runs; inbound counts show as `?`.

The link pass reports `LINKPLAN_BLOCKED` and changes no links only when it has neither the
store nor a workbook; the rest of `/fact` runs normally.

#### Reasoned assignments are written back

The store is live, not a fixed snapshot, but an article published this morning is still in
no source yet. The link pass reasons its cluster from `cluster_lookup.py suggest`, then
**submits that assignment back to the
store** with the evidence behind it — the shortlist, the tally, the top score, who decided and
when. The next person to run `/fact` on that URL inherits the answer instead of reasoning their
own, which is what stops one URL sitting in two clusters on two machines.

A machine assignment never overwrites a human one, and among competing reasoned rows the
earliest wins, so the store stays stable no matter who runs what.

#### The write token (optional)

Writing to the data branch needs a fine-grained GitHub token with `contents:write` on this
repo. It is never embedded here — the repo is public. The installer asks for it and stores it
at `~/.claude/factcheck-flow/.clusters-token` (chmod 600); `$PABAU_CLUSTERS_TOKEN` overrides.

**Skipping it costs you nothing you'll notice.** Reads work: the store is public and pulls
without any token. Writes queue instead — every submitted assignment is appended to
`~/.claude/factcheck-flow/cluster-queue.jsonl` *before* the network is touched, and the whole
queue goes up on the first run that has a token. A missing token is a no-op, never an error,
and never blocks a `/fact` run.

#### The sync commands

`bin/cluster_sync.py` is the one entry point; run it from
`~/.claude/factcheck-flow/bin/cluster_sync.py`.

    pull     fetch the store from the data branch (gated on the branch SHA, so a no-op is cheap)
    submit   queue ONE reasoned assignment, with its evidence, then try to push it
    push     drain the local queue into clusters/additions.jsonl
    adopt    export this machine's workbook to clusters/snapshots/<user>.jsonl and push it once
    status   token present or not, local vs remote SHA, queue depth, row counts

`status` is the one to run when something looks wrong: it says in five lines whether you have a
token, whether your copy is current, and how many assignments are waiting to go up.

#### If you already have a cluster workbook

Before the central store existed, the workbook was copied from machine to machine by hand, so
every copy has drifted a little from every other one. Run **`adopt` once** and your copy stops
drifting:

    python3 ~/.claude/factcheck-flow/bin/cluster_sync.py adopt

It writes your workbook to `clusters/snapshots/<your-user>.jsonl` on the data branch — one file
per person, so two people adopting at the same moment can't collide. Nothing in your snapshot
changes anyone's assignment on its own: consolidation diffs it against the canonical store and
surfaces the differences for David to accept or reject. Your local workbook keeps working
exactly as before, and keeps outranking the network on your machine.

#### Consolidation and publishing (David only)

Everything above is a one-way street until somebody folds it back in. `additions.jsonl` grows
with every reasoned assignment, teammate snapshots pile up in `clusters/snapshots/`, and
David's workbook keeps moving. **Consolidation** merges all of it into one new `base.jsonl`;
**publishing** puts that base back on the branch so everyone actually gets it.

This is David's job, and the natural cadence is **monthly, or after any large batch of `/fact`
runs** — whenever `cluster_sync.py status` shows the additions file getting long, or somebody
has run `adopt`.

    # 1. see what would change, decide nothing yet
    python3 bin/cluster_consolidate.py --dry-run

    # 2. really merge: writes a new base.jsonl, a conflict report, and a regenerated workbook
    python3 bin/cluster_consolidate.py

    # 3. read the conflict report and settle anything marked UNRESOLVED
    open clusters/conflict-report.md

    # 4. push the result to the data branch
    python3 bin/cluster_consolidate.py publish --dry-run
    python3 bin/cluster_consolidate.py publish

Step 2 exits 1 when a url needs a human decision, so a cron run can be noticed. It never
resolves an equal-authority disagreement on its own and it never deletes a row — a url that
has vanished from every source is marked `absent_since` and kept.

**What `publish` does**, in this order, and the order is the safety property:

1. pushes `base.jsonl`, `clusters.json` and `review-queue.json`;
2. pushes `MANIFEST.json` last — it is the seal every reader verifies against;
3. re-reads the published `base.jsonl` and checks its sha256;
4. only then rewrites `additions.jsonl`, dropping the rows this consolidation folded in and
   **keeping** any row whose url is not in the new base (somebody pushed it after the merge
   ran, so it belongs to the next consolidation).

If it fails part-way, nothing is lost: until the manifest lands, every teammate's `pull` sees
a digest mismatch and leaves their local files untouched, and `additions.jsonl` is not touched
at all. Re-running `publish` closes the gap. It refuses outright if the local manifest does not
match the local files, if the new base is more than 10% smaller than the upstream one, or if
there is no write token, and it asks you to type `PUBLISH` unless you pass `--yes`.

Teammates need to do nothing: `update.sh` runs `cluster_sync.py pull` at the start of every
session, so the new base arrives on its own.

### GSC access (required for published articles)

The "already ranking" list reads Google Search Console via a **service-account key** — a
secret that is **not** in this repo. Each user needs:

1. The service-account **JSON key** (ask your admin) at `~/.claude/factcheck-flow/gsc-key.json`
   (the installer offers to copy it there), or pointed to via `$PABAU_GSC_KEY`.
2. That service account granted **read access** to the Search Console property
   (`https://pabau.com/`) — the admin adds its `client_email` as a user in GSC.
3. **PyJWT** (`python3 -m pip install --user pyjwt`) — the installer does this when it can.

Without it, draft-mode `/SEO` still works; published-mode stops with a clear message until the
key is set up.

**Optional, separate key — the re-crawl request.** `bin/index_ping.py` asks Google to re-crawl
a refreshed (already public) URL. The Indexing API needs a service account that is an **OWNER**
of the property, so the read-only GSC key above returns 403 for it and the two are not
interchangeable. Put that key at `~/.claude/factcheck-flow/indexing-key.json` or point
`$PABAU_INDEXING_KEY` at it; the installer offers to copy it. Without it the step is skipped
with a one-line reason and nothing else changes.

## Customizing for your site

The three passes are plain editable files under `prompts/`:

- `prompts/1-factcheck.md` — accuracy / category / tag / link / structure review.
- `prompts/2-editorial.md` — your house style guide (fluff, US English, structure,
  meta descriptions, etc.).
- `prompts/3-links.md` — internal/external link rules. The internal half is cluster-based:
  **edit the site paths, the four editable folders, the link budgets, and the banned-link
  list**, and point `bin/cluster_lookup.py` at your own cluster workbook via
  `$PABAU_CLUSTERS_XLSX` (the defaults are specific to one site).

Reference guides under `guides/` define voice, product context, and the block contract, and
are read by the editorial pass and the fact-check reviewer:

- `guides/Pabau-style-guide.md` — tone of voice, benefit framing, US/UK terminology,
  formatting mechanics, and a treatments/regulation glossary.
- `guides/About-Pabau.md` — what the product is, its product family and naming rules,
  pricing model, competitors, and the customer journey.
- `guides/WordPress-blocks.md` — the block contract every article must satisfy, with exact
  markup: required document order, the Key takeaways block, the template download box, the
  Pabau CTA (`book-demo`) block and the section that carries it, the `Conclusion` heading and
  its CTA link, the Continue your research (`expert-picks`) block, the Yoast FAQ block,
  listicle pricing tables, and the image caption contract (every image captioned, full
  sentence, italic). **Site-specific — the custom block names and inline styles are
  Pabau's; swap them for your own theme's blocks.**

- `guides/Visuals.md` — the visual contract: every article ships at least one original
  visual the workflow builds, either a rendered image (HTML → WebP through
  `bin/render_visual.py`, uploaded to the media library) or one CSS-only interactive block.
  Covers what earns a visual, the brand tokens and webfont, chart-form selection, the render
  and upload commands, the block markup, and two verified templates. **Site-specific — the
  colour tokens and font are Pabau's; swap them for your own brand's in
  `bin/render_visual.py`.**

**These defaults are Pabau-specific — replace them with your own brand's voice and
product context** (keep the filenames, or update the references in `prompts/2-editorial.md`
and the `factcheck-reporter` agent if you rename them). The installer also adds a small
Pabau block to `~/.claude/CLAUDE.md` (between managed markers) so ad-hoc editing outside
`/fact` picks up the guides too.

Edit these freely; the workflow picks up your changes on the next run.

## How it's built

- `commands/factcheck-flow.md` — the orchestrator that drives the three stages and the
  triage gate (runs in the main conversation, since only it can ask you questions).
- `agents/factcheck-reporter.md` — Stage 1 worker (read-only).
- `agents/article-editor.md` — Stage 3 worker (applies all three passes to one
  article, end to end).
- `commands/SEO.md` + `prompts/seo-research.md` + `prompts/seo-write.md` + `agents/seo-writer.md`
  — the single-article optimization flow.
- `commands/generate.md` + `prompts/generate-research.md` + `prompts/generate-write.md` +
  `agents/article-generator.md` — the new-article flow. The command researches and plans; the
  agent writes and creates the draft.
- `skills/wordpress-access/SKILL.md` — REST API read/write helper used by the agents.

## Safety notes

- Stage 1 never writes to WordPress — findings are reported for your approval first.
- Test on a **draft** post before running against live published articles.
- Drafts stay drafts and published posts stay published; publication status is never
  changed automatically. `/generate` creates drafts only — it has no path to publishing at all.
