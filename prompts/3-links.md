<!--
  PROMPT 3 — LINK PASS (applied automatically in Stage 3, inside the article-editor)

  This file implements the Pabau internal-linking rulebook for ONE article. The rulebook is
  corpus-wide, so some of its rules are adapted to a single article here; the parts that cannot
  be done one article at a time are listed under "Out of scope for /fact" at the end — you
  report those, you never fake them.

  The EXTERNAL-link rules in §12 are unchanged from the previous version of this pass.
-->

# The link pass, in one paragraph

Links are an expense, not free authority. This article gets **at most five in-body editorial
links** (three if it is a code page), every one of them inside its own content cluster, exactly
one of them pointing up at the cluster's pillar, each one the reader's genuine next step. The
cluster comes from the cluster store, never from your judgment about what feels related. Every
existing link gets a disposition. Then a script checks the plan before you save.

Work from the copy of the article you already hold — this pass runs inside the article-editor,
which fetched the article once at the start. Do not re-fetch it, and hold every edit for the
single save at the end of the run.

---

## §0 — Resolve the cluster first (nothing else happens before this)

**The cluster store is the source of truth for cluster assignment. Use it as-is. Never
re-derive it, never re-litigate an assignment** — including the conflict resolutions and the
Rule-2 flags. The store is `clusters/base.jsonl` on the repo's `clusters-data` branch, which
the updater pulls onto every machine, merged with `~/Desktop/pabau-content-clusters.xlsx`
where the machine has one — the local workbook outranks the network, so David's edits still
win. An assignment either one already carries is settled, and re-reasoning it is how a URL
quietly changes cluster and drags its links across a wall with it.

The store is live, not a snapshot, so it grows as articles are assigned; an article published
this morning still will not be in it. For those, and only those, you reason the cluster from
`suggest` — and then you write that reasoning back, so the next run inherits it instead of
guessing at it again.

You never read the store by hand. `~/.claude/factcheck-flow/bin/cluster_lookup.py` reads it at
runtime and answers exactly the questions this pass asks:

```bash
CL=~/.claude/factcheck-flow/bin/cluster_lookup.py

# 1. The article: cluster, tier, subcluster, pillar, supporting hubs, budget, directives
python3 $CL resolve --url "<article URL>"

# 2. Only if it is NOT in the store — the nearest posts, so you can reason to a cluster
python3 $CL suggest --title "<the article's H1>" --terms "<3-6 topic words>"

# 2b. Then always — write that reasoning back, so this URL is never reasoned twice.
#     Re-run suggest with --json and hand the file straight to submit: the evidence object is
#     the shortlist you actually decided from, not a retyping of it.
python3 $CL suggest --title "<the article's H1>" --terms "<3-6 topic words>" --json > /tmp/ev.json
python3 $CL submit --url "<article URL>" --title "<the article's H1>" \
    --cluster-id <cluster-id> --subcluster "<subcluster>" --intent <TOFU|MOFU|BOFU|JTBD> \
    --evidence-file /tmp/ev.json

# 3. Candidate targets inside that cluster (lowest inbound first = most equity-hungry)
python3 $CL targets --cluster <cluster-id> --subcluster "<subcluster>" --limit 20
python3 $CL targets --cluster <cluster-id> --bofu --sort pr --limit 10   # funnel candidates

# 4. Every link already in the body, judged against rule A
python3 $CL classify --from-url "<article URL>" --urls <every internal href in the body>

# 5. Billing only: the subhub target set
python3 $CL subhubs
```

`resolve` prints the tier, the pillar URL, the listed supporting hub pages, the in-body budget,
the funnel stage, an anchor-rotation seed, and any directive that applies (pillar exceptions,
the billing wall, the house category, the retirement bucket). Read its output as instructions,
not as suggestions.

If the article is **not** in the store, run `suggest`, decide the cluster from the shortlist and
the cluster/subcluster tally, and record the id you chose — it goes in the plan you verify at
the end. Then `submit` it, carrying the shortlist, the tally and the top score you decided on —
`suggest --json` emits that object in exactly the shape `submit` wants, so pass the file rather
than retyping its contents. **That step is not optional.** An assignment you keep to yourself is one
the next person reasons from scratch, and two people reasoning separately is how one URL ends
up in two clusters; the evidence is what lets David confirm or overturn your call months later
without re-running anything. `submit` writes the row to a local queue before it touches the
network, so it costs nothing on a machine with no write token — the row goes up on the next run
that has one. If it refuses because the URL already carries a human assignment, you were
re-litigating the sheet: run `resolve` again and follow what it says.

If **neither** the local workbook nor the pulled store is readable, **stop the link pass**,
change no links, and report `LINKPLAN_BLOCKED — no cluster store`. A missing workbook on its
own is not that case and blocks nothing: most machines never have one and read the branch copy
instead. Guessing a cluster is worse than doing nothing.

Three §0 outcomes end the pass immediately:

- The article is in the **Review queue's retirement/reassign bucket** → no link actions at all.
  Log it and skip to §13.
- The article is in **`pabau-product-updates`** → house category, not a silo. No added editorial
  links, no pillar rule; only the §2 removals (/lp/, cross-cluster) and the §8 CTA contract.
- The article's URL is **outside `/blog/`, `/templates/`, `/procedure-codes/`,
  `/diagnostic-codes/`** → those four folders are the only pages that may ever be edited. Make
  no link changes, and say so in your report so David can decide whether /fact should have been
  pointed at it at all. (The rest of the /fact passes still run.)

---

## §1 — Hard scope gates

Violating any of these invalidates the whole plan.

1. **`/lp/` is radioactive.** No URL containing `/lp/` is ever a link target — not in the body,
   not in a Continue your research pick. Every existing link from this article to any `/lp/` URL
   is a REMOVE.
2. **Never plan a URL, slug, title, or status change.** This pass changes links and the prose
   hosting them, nothing else.
3. **House blocks and their links are untouchable** — Key takeaways, the Pabau CTA block, the
   Conclusion's `/book-demo/` link, download boxes, pricing tables, the FAQ. The only permitted
   block edit is REPLACE_PICK inside the Continue your research block (§7). Nav and footer are
   out of scope entirely.
4. **Every existing `/book-demo/` link stays** — block or inline, anywhere on the page. Never
   removed, never rerouted. §8 governs adding the missing required ones.

---

## §2 — The disposition sweep: every existing link gets exactly one verdict

List every internal href in the body you hold, then run `classify --from-url <article> --urls …`
and give each link exactly one of:

`KEEP` · `KEEP_ANTI_ORPHAN` · `REWRITE_ANCHOR` · `REROUTE` · `REMOVE`

with a reason code: `COMPLIANT` / `LP_TARGET` / `CROSS_CLUSTER` / `BILLING_WALL_BREACH` /
`OVER_CAP` / `BAD_ANCHOR` / `BAD_PLACEMENT` / `CANNIBAL_VARIANT`.

- **KEEP requires passing every rule**: legal target (§3), in-prose placement (§6), compliant
  anchor (§5), and inside the budget (§4).
- **Cross-cluster post-to-post links default to REMOVE.** REROUTE them to that cluster's pillar
  only when the mention survives naturally in the sentence.
- **Over budget?** Keep the pillar up-link first, then the highest reader-value links toward
  targets that need equity. REMOVE the rest with reason `OVER_CAP`.
- **Never orphan a page.** `classify` flags any target whose inbound count in the link graph is
  1 — removing that link orphans it. Fix it with a compliant same-cluster ADD elsewhere if one
  exists; if none does, keep the link and mark it `KEEP_ANTI_ORPHAN`. (`/lp/` removals are
  exempt: an /lp/ page is never protected from orphaning.)
- After a REMOVE, **rephrase the host sentence so it reads correctly without the link.** If the
  sentence existed only to send the reader to that page, delete the sentence. Removing a link
  does not obligate you to find a replacement — the budget, not the count, decides what is
  added.
- **Remove any link to these, and do not replace them:**
  - …/intraparenchymal-hemorrhage-icd-10-codes/
  - …/blog/acne-face-mapping/
  - …/icd-10-code-for-autistic-disorder/
  - …/situational-anxiety-icd-10-code/
  - the /blog/ index

---

## §3 — Where links may point (rule A)

**The wall is the cluster, not the folder.** Inside the article's own cluster you may link
freely across all four folders — blog ↔ template, CPT ↔ ICD-10 — plus the cluster's own pillar
and its listed supporting hub pages (targets only, never edited). Every link must be the
reader's next logical step. No link exists just to exist.

**Exactly one in-body pillar up-link. Not zero, not two.** If a compliant one already exists,
KEEP it (or REWRITE_ANCHOR). This is the highest-priority add class in the whole pass.

**Different cluster → only via a pillar or a shared Tier-2 hub. No lateral cross-cluster links,
ever.** The article may link another cluster's *pillar page*, or — where the topic is a shared
operational function — the pillar or a listed supporting hub of a `Tier 2 — Cross-industry`
cluster. Never another cluster's posts. Only where the prose genuinely discusses that topic.
`classify` labels each of these for you.

**Pillar exceptions** (`resolve` prints the one that applies):

- `comparisons-alternatives` — its listed pillar is an /lp/ page. Up-link the most relevant
  non-LP `/compare/` page instead and verify it returns 200. If none fits, log BLOCKED_PILLAR.
- `optometry-eye-care` — pillar is /lp/-only. No pillar up-link; log BLOCKED_PILLAR.
- `ai-in-healthcare` — use the interim pillar `/features/ai-medical-scribe/` as-is.
- Any listed supporting page that lives under /lp/ is never a target.

### The billing wall — strictest rule on the site

Articles in `billing-coding-claims` (essentially all of `/procedure-codes/` and
`/diagnostic-codes/`, plus billing-topic blog posts) link **only inside the billing cluster and
its own hubs**. Nothing outside billing — not even another cluster's pillar. The §8
`/book-demo/` CTA links are conversion links outside the cluster system and are the only
exception.

Every code page gets exactly this pattern, and nothing else:

1. **one up-link to `https://pabau.com/features/claims-management-software/`**;
2. **one link to a billing subhub** — `resolve` prints the rotation pick for this page, so
   equity spreads across the subhubs instead of piling on one. Override the rotation when the
   article points somewhere specific: a code whose medical-necessity codes live in ICD-10 links
   the ICD-10 hub, a denial-prone code links the denial-codes hub;
3. **at most one next-step** — the CPT ↔ ICD-10 counterpart, or the matching template/blog guide
   inside billing.

Pillar and subhub links are structural: they are exempt from the boost cap in §4. Inbound,
non-billing articles may link the billing pillar only.

---

## §4 — Budget (rule B)

- **At most 5 in-body editorial links** — **at most 3** on a `/procedure-codes/` or
  `/diagnostic-codes/` page. House blocks do not count, Continue your research picks do not
  count (§7), and `/book-demo/` CTA links do not count (§8).
- Final-state composition:
  - blog / template article = 1 pillar up-link + up to 4 discretionary (keeps, boosts,
    next-steps; on a TOFU article one of those slots is the §8 funnel link);
  - code page = 1 pillar + 1 subhub + at most 1 next-step.
- **Absolute ceiling of 50 outbound links on the page** (CTA links excluded). A page over it
  after your plan fails verification.
- **No duplicate in-body links** — one link per target. Picks may duplicate an in-body target
  (§7). Where a duplicate exists, remove the second and rephrase its sentence.
- **At most 2 internal links in any single paragraph**, and spread them across the article
  rather than clustering them.
- **Never pad to reach a number.** Five is a ceiling, not a target. Four well-placed links beat
  five with one that had to be invented a home.

---

## §5 — Anchors (rule C)

- The anchor describes the **target's** primary keyword, reads naturally mid-sentence, and is
  never "click here", "read more", "learn more", or a bare URL.
- **The same anchor string appears at most 3 times in one article.**
- For a pillar, a Tier-2 hub, or a billing subhub, do not ship the same exact-match anchor the
  whole corpus uses — one sitewide anchor pattern is a footprint. `resolve` prints an
  **anchor-rotation seed** naming which pattern this article uses (exact keyword / audience
  phrase / the target's own H1 / benefit-framed phrase). Write that pattern in this article's
  own words, and record the anchor you used.
- **Anchors run to 4 words at most.** Trim anything longer.
- **Linking a `/procedure-codes/` or `/diagnostic-codes/` page: the anchor is the code itself**,
  and the sentence carries no parenthetical explaining what the code refers to — it makes
  sentences unreadable. (A billing page that is not about one specific code — the denial-codes
  page, a subhub archive — takes short descriptive anchor text instead.)
- CTA links are exempt from the target-keyword rule: the anchor is short CTA text ("Book a
  demo") inside a sentence naming the benefit for this article's reader.
- Anchors and all new prose follow `core-rules.md` and the style guide: US English, 25 words per
  sentence, no banned words.

---

## §6 — Placement and prose (rule E)

Links live in body prose paragraphs only — never in a heading, an image caption, or any house
block. Each added link uses one of three host types, and you decide which before you write:

- **EXISTING_SENTENCE (preferred).** Place the anchor inside a sentence that already earns its
  place in the article.
- **NEW_SENTENCE.** Where no natural host exists, **write 1–2 new sentences** that genuinely
  serve the reader on the target's topic, and insert them next to a specific existing sentence.
  They must read as native to the article, invent no facts, and pass every style rule. On
  templated corpora — the code pages especially — vary the structure and name the specific
  code or procedure. One boilerplate sentence cloned across pages is a footprint.
- **NEW_SECTION.** Only when the article contains nothing genuinely related **and** the link is
  structurally required (pillar or subhub): add a short new H2 of 2–4 sentences that creates
  real topical relevance, placed in the body run before the Pabau section, never disturbing the
  house block order. **Never for a discretionary boost** — if nothing related exists, the boost
  is dropped, not manufactured.

If honest supporting prose cannot exist for a link, the link shouldn't either: skip it with
reason `NOT_RELEVANT`.

This replaces the old blanket ban on writing prose to host a link. The ban on *padding* stands:
new prose must serve the reader on its own, and a sentence that only exists to hold an anchor
still fails.

**Genuine next-step links worth planning where budget allows:** blog article ↔ the same
procedure's template (the download is the conversion), CPT page ↔ the ICD-10 codes that support
its medical necessity, template → the blog guide that explains the procedure. Each must pass
the "would the reader want this next?" test. No systematic related-content meshes.

---

## §7 — Continue your research (the `expert-picks` block)

Markup and the 5-item ceiling belong to `WordPress-blocks.md` §7 — never rebuild the block from
memory. This pass owns only which articles it links.

- Picks **do not count** toward the in-body budget and **may duplicate** in-body link targets.
- **Every pick stays inside the article's own cluster.** Never outside it, never `/lp/`.
- Prefer, in order: same subcluster → same folder → posts over hub pages.
- Among compliant candidates, prefer the ones that need equity: `targets --sort inbound` lists
  the cluster's lowest-inbound pages first. This is a tiebreaker, never a reason to break the
  cluster wall.
- Any pick that violates the wall becomes a REPLACE_PICK with a compliant same-cluster
  replacement. Never delete the block, never change its structure.
- Every item must be a real, working link with descriptive anchor text naming the article. Never
  a placeholder — no "list item #1", "Article title", "Lorem ipsum", "#" or example.com hrefs,
  no empty items. Replace each one you find, or delete that item.

---

## §8 — Funnel and CTA (rule G)

**Classify this article TOFU / MOFU / BOFU** from its target query and title, and record the
stage. BOFU = purchase intent: comparisons, "alternative to", pricing, "best X software"
listicles, commercial decision guides; a template article defaults to BOFU (the download is the
conversion) unless it is purely educational. TOFU = educational, including every code page.
MOFU sits between them. `resolve` prints a heuristic guess — confirm it yourself.

**Every TOFU article in `/blog/` or `/templates/` links at least one same-cluster BOFU
article** — a post, not the pillar. This is the ADD_FUNNEL link. An existing compliant link may
serve as it, flagged on its KEEP row. It still has to pass the next-step test and live in honest
host prose. Route by subcluster relevance first. `targets --cluster <id> --bofu --sort pr` lists
the candidates; **spread across the cluster's BOFU inventory** rather than always picking the
strongest one. The funnel link counts against this article's budget. If the cluster has no BOFU
article at all, log `NO_BOFU_IN_CLUSTER` — that is a content-gap finding for David, not a
failure. **Code pages are exempt from this mandate**; where genuinely relevant their one
next-step may be a BOFU billing guide or template.

**The `/book-demo/` CTA contract.** Every in-scope, non-skipped article ends in final state with
both placements:

1. one in the **Pabau promotional section** — satisfied by the Pabau CTA (`book-demo`) block
   where it exists; where no block exists (Elementor articles), an inline CTA link in the
   Pabau-promotional prose. A code page — templated or old-shape — carries the `book-demo`
   block normally, so never substitute an inline CTA there;
2. one **inline CTA link closing the Conclusion** — short "Book a demo"-style anchor inside a
   closing sentence naming the benefit for this reader. `WordPress-blocks.md` owns the format.

Audit both, record the before-state, and add each missing one as an ADD_CTA — prose written via
§6, never a planned block addition. On a page with no Pabau section or Conclusion at all, put
the promotional CTA in a short passage before the closing content and the closing CTA as the
final body sentence. **Vary the benefit sentence per page.** CTA links are conversion links, not
editorial links: exempt from the cluster wall (billing included), from every budget and cap, and
from the §5 anchor rules. An article carrying more than the two placements is left alone.

(The block-guarantee pass D3/D4 enforces the same two placements from the block side. Where both
apply, they are the same two links — do not create a third.)

---

## §9 — Close variants and cannibalization (rule 1, per-article)

The corpus-wide cannibalization sweep is not this pass's job (see Out of scope). What is:

- **Never plan a boost, next-step, or funnel link at a page that is a close variant of another
  page competing on the same query** unless it is the primary. Close variants live mainly in the
  code corpus (neighboring or related codes) and in same-procedure blog/template pairs.
- When two candidate targets are genuine close variants of each other, pick the primary by best
  rank, then clicks. One GSC call each settles it, for the two or three shortlisted targets
  only:

  ```bash
  python3 ~/.claude/factcheck-flow/bin/gsc_query.py --page "<candidate URL>" --days 28 --limit 5
  ```

- An existing link pointing at a non-primary variant becomes REROUTE to the primary, reason
  `CANNIBAL_VARIANT`. Non-primary variants receive no boost, next-step or funnel links —
  structural pillar/subhub links and CTA links only — and variants never link each other
  laterally.
- Log any pair you find with heavy overlap as a merge candidate for David. **Never plan a merge
  or a 301** — out of scope.

**Does this article's own links pass equity?** A link from a page that does not itself rank
passes ~nothing. One call classifies this article:

```bash
python3 ~/.claude/factcheck-flow/bin/gsc_query.py --page "<article URL>" --days 28 --limit 10
```

Clicks > 0, or impressions at position ≤ 20 → RANKING. Otherwise INERT. Say which in your
report: on an INERT article the links you added are hygiene, not equity, and nobody should
credit them later for moving a pillar. A brand-new article is INERT by definition and that is
fine — it is not a reason to skip the pass.

---

## §10 — Elementor articles (rule F)

Detect the engine and **record it**: `gutenberg` / `classic` vs `elementor`. One call settles
it — exit 0 means `post_content` is safe to write, exit 3 means the page is builder-backed:

```bash
python3 ~/.claude/factcheck-flow/bin/elementor_guard.py <POST_ID>   # prints "<id> ok|BUILDER <url>"
```

Its fallback signals, if the script is unavailable: `content.raw` empty or a shell while
`content.rendered` is full, and/or `_elementor_data` / `_elementor_edit_mode` in meta.

**Elementor pages silently ignore `post_content` writes.** An edit written there reports success
and changes nothing. So on an Elementor article: quote host sentences and current anchors from
the `_elementor_data` widget text, edit that structure, preserve its JSON encoding exactly, and
regenerate/flush Elementor CSS after the save. If `_elementor_data` is not readable over REST,
change nothing and log **BLOCKED_ELEMENTOR** — never a blind edit. Elementor pages may carry no
Gutenberg house blocks at all; audit what actually exists and never plan adding blocks to one.

---

## §11 — Verify before you save (mechanical gate)

Link rules are counting rules, and counting is not done by eye. Write the finished plan to JSON
and run the gate. It must exit 0 before the article is saved.

```bash
# plan.json — write it with the Write tool, then:
python3 ~/.claude/factcheck-flow/bin/cluster_lookup.py verify \
  --url "<article URL>" --plan /tmp/plan.json
```

```json
{
  "engine": "gutenberg",
  "stage": "TOFU",
  "cluster": "med-spa-aesthetics",
  "cta_promotional": true,
  "cta_conclusion": true,
  "total_outbound": 23,
  "links": [
    {"type": "ADD_PILLAR",  "target": "https://pabau.com/industry/medical-spa-software/",
     "anchor": "software built for med spas", "host": "EXISTING_SENTENCE"},
    {"type": "ADD_FUNNEL",  "target": "https://pabau.com/blog/best-medical-spa-software/",
     "anchor": "best med spa software", "host": "NEW_SENTENCE"},
    {"type": "KEEP",        "target": "https://pabau.com/blog/dermatology-practice-marketing/",
     "anchor": "dermatology marketing"},
    {"type": "REMOVE",      "target": "https://pabau.com/lp/medical-spa-software/",
     "anchor": "med spa software", "reason": "LP_TARGET"},
    {"type": "ADD_CTA",     "target": "https://pabau.com/book-demo/", "anchor": "Book a demo"}
  ],
  "picks": ["https://pabau.com/blog/easi-score-calculator/"]
}
```

Every existing link needs a row, every added link needs a row. `cluster` is required only when
the article is not in the store. On a target the store does not hold, add
`"cluster_confirmed": true` to that row once you have resolved its cluster yourself.

`total_outbound` is every outbound link the saved page will carry, CTA links excluded — the
gate uses it for the 50-link ceiling.

The gate checks: no `/lp/` survivor; the edited page is in the four folders; the budget and the
50-link ceiling; exactly one pillar up-link and that it is the right pillar; every target legal under §3 (including the
billing wall); exactly one subhub on a code page; anchors — none banned, none over 3 uses; picks
inside the cluster and at most 5; no `/book-demo/` link removed or rerouted; the TOFU funnel
link; the engine recorded. It warns where a removal may orphan a page.

**A FAIL is not advisory.** Fix the plan, re-run, and only then continue. If the script is
missing, do not download it and do not improvise the counting — report
`LINKPLAN_GATE_UNAVAILABLE` and leave the links as they were.

Then check every link actually resolves — status codes only, never WebFetch a page for a
three-digit answer:

```bash
for u in <url1> <url2> <url3>; do
  printf '%s %s\n' "$(curl -sI -o /dev/null -w '%{http_code}' -L --max-time 15 "$u")" "$u"
done
```

Every link must return a clean 200 — no 3xx redirect, no 4xx. Drop `-L` when you specifically
want to catch a 3xx rather than follow it.

Finally, **read the whole article through once more for flow** — the last thing you do in this
pass. The interlinking must not have interrupted the article, a section, or a paragraph. Watch
for link-cluttered paragraphs, awkward anchors, and sentences that now exist only to hold a
link. Fix anything that blocks flow — rephrase, merge, or cut — without asking.

---

## §12 — External links (unchanged)

External links must be nofollow and open in a new tab. Internal links open in the same tab and
are NOT nofollow.

Keep up to **5 external links ONLY**. Choose the ones with the greatest impact, keep those, and
remove the rest, fixing the context around them so it makes sense without the link.

**NEVER link to a competitor's pricing page.** Reading a competitor's pricing page to source
their figures is still required — the link itself never ships. Check every external link for a
pricing destination: `/pricing`, `/pricing-plans`, `/plans`, `/packages`, `/cost`, a `#pricing`
anchor, or any page whose purpose is to sell their plans. Where you find one, **change the URL to
that competitor's homepage** (root domain, e.g. `https://www.zenoti.com/`) and keep it nofollow +
new tab. Then fix the anchor text and the surrounding sentence so both still make sense pointing
at a homepage — anchor text like "Zenoti's pricing page" becomes "Zenoti". If the sentence
existed only to send the reader to that pricing page, delete the sentence. If the homepage
version of the link then adds nothing, drop the link entirely rather than keep a hollow one.
This applies to every provider that isn't us, including in listicle pricing segments;
`pabau.com/pricing/` is our own page and is unaffected.

External links count toward nothing in §4 — that budget is internal editorial links only.

---

## §13 — What to report

The `Links:` line in your change-log carries, in this order:

- cluster + subcluster + tier, and whether it came from the store or from your reasoning — and
  when you reasoned it, what `submit` said: pushed, queued for the next run with a token, or
  refused (with the reason it gave);
- the funnel stage, and RANKING or INERT from §9;
- the engine (`gutenberg` / `classic` / `elementor`);
- final in-body editorial link count against the budget (e.g. `4/5`);
- the pillar up-link (target + anchor), or the BLOCKED_PILLAR reason;
- on a code page: the subhub you linked and why, plus the next-step if any;
- the funnel link (target), or `NO_BOFU_IN_CLUSTER`;
- dispositions as counts by code — `KEEP n · REWRITE_ANCHOR n · REROUTE n · REMOVE n` — with the
  reason codes for every REROUTE and REMOVE;
- picks: kept / replaced, and any REPLACE_PICK target;
- both CTA placements: already there or added;
- the gate's final line, verbatim (`PASS | 0 checks failed, N warnings`);
- external links: how many kept, any pricing-page URL you rewrote to a homepage;
- anything skipped, with its code: `NOT_RELEVANT`, `BLOCKED_PILLAR`, `BLOCKED_ELEMENTOR`,
  `NO_BOFU_IN_CLUSTER`, retirement bucket, product-updates, out-of-folder.

Also surface, for David rather than for the article: merge candidates from §9, and — when this
article is BOFU — that rule G wants 1–3 inbound boost links pointed **at** it from
high-PageRank, high-traffic same-cluster pages. That is an edit to other pages, so name it as a
finding here; never edit another page from this pass.

---

## Out of scope for /fact (report, never fake)

This pass edits ONE article. The rulebook's corpus-level work belongs to the bulk interlinking
project and is deliberately not attempted here:

- the 28-day corpus-wide cannibalization sweep and primary designation across all in-scope pages;
- inbound boost links to BOFU articles (they are edits to *other* pages);
- the post-removal orphan simulation over the whole graph — §2 uses the per-target inbound count
  from `graph.json` instead;
- cross-corpus rotation ledgers for subhub and funnel distribution — `resolve`'s per-article
  rotation seed is the stand-in;
- merges, 301s, URL and slug changes: never, under any circumstance.

The link graph behind the inbound counts is `~/Desktop/linkmap/graph.json`. If
`cluster_lookup.py` warns that it is more than 48 hours old, say so in your report; refreshing it
(`cd ~/Desktop/linkmap && ./refresh.sh`) is a wrap-up step for the /fact orchestrator, not
something to run per article.

Note: a newly published article or draft may not be indexed yet, so don't rely on a search index
to read it.
