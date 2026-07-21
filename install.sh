#!/usr/bin/env bash
#
# factcheck-flow installer (no plugin system required)
# Installs the /fact command, its two agents, the WordPress skill,
# and the three prompt files into ~/.claude/ — works in Claude Code setups
# where the plugin system is disabled.
#
# Run it with:
#   bash <(curl -fsSL https://raw.githubusercontent.com/aleksandark-bot/factcheck-flow-plugin/main/install.sh)
#
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/aleksandark-bot/factcheck-flow-plugin/main"
CLAUDE="$HOME/.claude"
FF="$CLAUDE/factcheck-flow"
PROMPTS="$FF/prompts"
GUIDES="$FF/guides"
CREDS="$FF/wp-credentials"

echo ""
echo "  Installing factcheck-flow into $CLAUDE ..."
echo ""

mkdir -p "$CLAUDE/commands" "$CLAUDE/agents" "$CLAUDE/skills/wordpress-access" "$PROMPTS" "$GUIDES" "$FF/bin"

# --- 1. Download the editable prompt files from the repo -------------------
for p in 1-factcheck 2-editorial 3-links seo; do
  if ! curl -fsSL "$REPO_RAW/prompts/$p.md" -o "$PROMPTS/$p.md"; then
    echo "  ERROR: could not download prompts/$p.md — check your internet connection." >&2
    exit 1
  fi
done
echo "  - prompts installed"

# --- 1a. The GSC query helper (used by /SEO on published articles) --------
if curl -fsSL "$REPO_RAW/bin/gsc_query.py" -o "$FF/bin/gsc_query.py"; then
  chmod +x "$FF/bin/gsc_query.py" 2>/dev/null || true
  echo "  - GSC helper installed"
else
  echo "  NOTE: could not download bin/gsc_query.py — /SEO's GSC step will be unavailable." >&2
fi
if curl -fsSL "$REPO_RAW/bin/keyword_picker.py" -o "$FF/bin/keyword_picker.py"; then
  chmod +x "$FF/bin/keyword_picker.py" 2>/dev/null || true
  echo "  - keyword picker installed"
else
  echo "  NOTE: could not download bin/keyword_picker.py — /SEO will use the in-chat picker." >&2
fi
if curl -fsSL "$REPO_RAW/bin/serp_picker.py" -o "$FF/bin/serp_picker.py"; then
  chmod +x "$FF/bin/serp_picker.py" 2>/dev/null || true
  echo "  - SERP picker installed"
else
  echo "  NOTE: could not download bin/serp_picker.py — /SEO will use the in-chat SERP list." >&2
fi

# --- 1b. Download the Pabau reference guides from the repo -----------------
# These define voice/terminology (Pabau-style-guide), product/positioning
# context (About-Pabau), and SERP title optimization (Meta-title-best-practices).
# The editorial prompt and factcheck-reporter read them.
for g in Pabau-style-guide About-Pabau Meta-title-best-practices Originality-and-search-intent; do
  if ! curl -fsSL "$REPO_RAW/guides/$g.md" -o "$GUIDES/$g.md"; then
    echo "  ERROR: could not download guides/$g.md — check your internet connection." >&2
    exit 1
  fi
done
echo "  - guides installed"

# --- 1c. The auto-updater script ------------------------------------------
# Pulled by a SessionStart hook (installed in section 4c). Re-downloads the
# editable prompts + guides whenever the repo has advanced since the last sync.
cat > "$FF/update.sh" <<'UPDATESH'
#!/usr/bin/env bash
#
# factcheck-flow auto-updater (runs from a SessionStart hook)
# Pulls the latest editable /fact files (prompts + guides) from the repo, but
# ONLY when the repo has advanced since the last sync. Design goals:
#   - Fail-silent: a network hiccup, offline laptop, or API rate-limit must never
#     block or slow a Claude Code session. Every failure path exits 0 quietly.
#   - Author-safe: gated on the remote commit SHA. If nobody has pushed since the
#     last sync, this is a no-op — so uncommitted local edits are never clobbered.
#   - Quiet: prints nothing on success so it doesn't pollute session context.
#
set -uo pipefail   # deliberately NOT -e

REPO="aleksandark-bot/factcheck-flow-plugin"
BRANCH="main"
RAW="https://raw.githubusercontent.com/$REPO/$BRANCH"
API="https://api.github.com/repos/$REPO/commits/$BRANCH"
FF="$HOME/.claude/factcheck-flow"
STATE="$FF/.last-sync-sha"

mkdir -p "$FF/prompts" "$FF/guides" "$FF/bin" "$HOME/.claude/commands" 2>/dev/null || true

# 1. Latest commit on main. Bail quietly if we can't reach GitHub.
remote_sha="$(curl -fsSL --max-time 8 -H 'Accept: application/vnd.github+json' "$API" 2>/dev/null \
  | grep -m1 '"sha"' | sed -E 's/.*"sha"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')"
[ -n "${remote_sha:-}" ] || exit 0

# 2. Nothing new since last sync? Do nothing (this is what protects unpushed edits).
if [ -f "$STATE" ] && [ "$(cat "$STATE" 2>/dev/null)" = "$remote_sha" ]; then
  exit 0
fi

# 2b. Self-update: pull the latest copy of THIS script first, so changes to the
#     updater itself — including new files added to the fetch lists below (e.g. a
#     newly added guide) — propagate without a manual reinstall. Safe by design:
#       - Guarded by FF_SELFUPDATED so the re-exec can't loop.
#       - Only acts on a validated download (non-empty, has a shebang, is actually
#         our updater), and only re-execs when the copy genuinely changed.
#       - On any failure it falls through to run the current copy unchanged.
SELF="$FF/update.sh"
if [ -z "${FF_SELFUPDATED:-}" ]; then
  tmp_self="$(mktemp 2>/dev/null || true)"
  if [ -n "${tmp_self:-}" ] \
     && curl -fsSL --max-time 8 "$RAW/update.sh" -o "$tmp_self" 2>/dev/null \
     && [ -s "$tmp_self" ] \
     && head -1 "$tmp_self" 2>/dev/null | grep -q '^#!' \
     && grep -q 'factcheck-flow auto-updater' "$tmp_self" \
     && ! cmp -s "$tmp_self" "$SELF" 2>/dev/null; then
    if mv "$tmp_self" "$SELF" 2>/dev/null; then
      chmod +x "$SELF" 2>/dev/null || true
      export FF_SELFUPDATED=1
      exec bash "$SELF" || exit 0
    fi
  fi
  rm -f "${tmp_self:-}" 2>/dev/null || true
fi

# 3. Download each file to a temp path; only replace the real file on a clean,
#    non-empty download so a partial fetch never truncates a good local file.
fetch() { # $1 = repo-relative path, $2 = local destination
  local tmp
  tmp="$(mktemp 2>/dev/null)" || return 0
  if curl -fsSL --max-time 8 "$RAW/$1" -o "$tmp" 2>/dev/null && [ -s "$tmp" ]; then
    mkdir -p "$(dirname "$2")" 2>/dev/null || true
    mv "$tmp" "$2" 2>/dev/null || rm -f "$tmp" 2>/dev/null || true
  else
    rm -f "$tmp" 2>/dev/null || true
  fi
}

for p in 1-factcheck 2-editorial 3-links seo; do
  fetch "prompts/$p.md" "$FF/prompts/$p.md"
done
for g in Pabau-style-guide About-Pabau Meta-title-best-practices Originality-and-search-intent; do
  fetch "guides/$g.md" "$FF/guides/$g.md"
done

# /SEO command + GSC helper (seo.md prompt is fetched in the prompts loop above)
fetch "commands/SEO.md" "$HOME/.claude/commands/SEO.md"
fetch "bin/gsc_query.py" "$FF/bin/gsc_query.py"; chmod +x "$FF/bin/gsc_query.py" 2>/dev/null || true
fetch "bin/keyword_picker.py" "$FF/bin/keyword_picker.py"; chmod +x "$FF/bin/keyword_picker.py" 2>/dev/null || true
fetch "bin/serp_picker.py" "$FF/bin/serp_picker.py"; chmod +x "$FF/bin/serp_picker.py" 2>/dev/null || true

# 4. Remember the commit we're now in sync with.
printf '%s\n' "$remote_sha" > "$STATE" 2>/dev/null || true
exit 0
UPDATESH
chmod +x "$FF/update.sh"
echo "  - auto-updater script installed"

# --- 2. The command -------------------------------------------------------
# Remove the old command name if a previous version installed it.
rm -f "$CLAUDE/commands/factcheck-flow.md"
cat > "$CLAUDE/commands/fact.md" <<'EOF'
---
description: Batch-QA WordPress articles — parallel fact-check, per-finding human triage, then automated editorial + link passes.
argument-hint: "<url-or-id> <url-or-id> ... (up to ~5)"
---

You are orchestrating a three-stage WordPress article QA run over the articles the
user passed as arguments.

Articles to process: **$ARGUMENTS**

If no arguments were given, ask the user for the list of article URLs or post IDs and
stop until they provide them. Otherwise parse them into a list (whitespace- or
newline-separated). Treat each token as one article. Proceed through the stages below
in order. Do NOT skip the triage gate.

---

## Stage 1 — Fact-check (report-only, parallel)

Spawn one **factcheck-reporter** subagent per article, **all in a single message**
(so they run concurrently). Give each subagent exactly one article (its URL or ID)
and tell it to produce its findings report per its instructions. These agents are
read-only — nothing is written to WordPress in this stage.

Collect every subagent's returned report. A report is one of: `CORRECT: No fix
needed`; a single `REWRITE_REQUIRED: <reason>` line (handle via the Rewrite gate
below — do NOT treat it as a finding); or a numbered findings list. Parse the findings
lists into a flat list, tagging each with its article. Keep the `NEEDS_USER_VALUE` and `CONFIRM`
flags, `TYPE`, `LOCATION`, `ISSUE`, `CORRECT`, and `FIX` for each. Articles that
returned `CORRECT: No fix needed` contribute zero findings but still go through Stage 3.

Briefly tell the user how many findings came back per article, then go to Stage 2.
If there are zero findings across all articles (and none needs a rewrite), tell the
user and skip directly to Stage 3.

### Rewrite gate

An article enters the rewrite path in one of two ways: (a) its Stage 1 report is a bare
`REWRITE_REQUIRED: <reason>` — truncated/incomplete or self-repeating; this is fully
automatic with no user input and runs before Stage 2; or (b) a grave factual error was
**independently verified and then approved by the user** during Stage 2 triage (case 3
below). For each such article:

1. Spawn an **article-editor** subagent in **rewrite mode**: pass the article URL/ID and
   the reason — the `REWRITE_REQUIRED` reason, or, for a verified-and-approved grave
   factual error, that correction — and tell it to complete/rewrite the article so it matches
   the full structure of similar articles on the same site (fill missing sections, remove
   any duplicated/repeated content, correct the confirmed error) and save via
   `wordpress-access`. In rewrite mode it runs no triage, editorial, or link pass.
2. When the rewrite is saved, **re-run the entire /fact pipeline on that article from
   Stage 1** (fresh fact-check → triage → editorial + links).

A truncation/repetition rewrite is never asked about — it happens automatically on
detection. A grave factual error is the one case where a rewrite follows independent
verification plus the user's approval (Stage 2, case 3). Guard against loops: rewrite a given article at most
**twice**. If it still returns `REWRITE_REQUIRED` after the second rewrite, stop looping
it and flag it for manual attention in the final report. Articles that did not trigger a
rewrite proceed through Stage 2 as normal (they do not wait on rewriting articles).

## Stage 2 — Triage gate (mostly automatic — the human is asked in only three cases)

Almost every finding is **applied automatically** — do NOT put it in an `AskUserQuestion`
batch. Silently mark as Apply and route straight to Stage 3 all findings of type
`factual`, `Pabau-fact`, `link`, `publishing`, and `missing-section`, plus any
`listicle-rank` finding that does **not** move Pabau's own position. (`publishing`: a
draft stays a draft and a published article stays published — the editor already targets
the right one, so never ask. Categories and tags are owned by the editorial pass, which
also strips "Uncategorized" — nothing to ask here.)

The human is asked **only** in the three cases below, via the `AskUserQuestion` tool
(batch up to 4 per call; label each with its article + location). If no finding matches
these three, skip the questions entirely and go straight to Stage 3. Case 3 is special:
a flagged grave error reaches the human **only after an independent agent verifies it**.
Run those verifications first (see case 3) so that a confirmed error joins cases 1–2 in
the same `AskUserQuestion` batch, while an unconfirmed one is dropped and never asked.

1. **Listicle review scores** — any finding with `NEEDS_USER_VALUE: true`. The reporter
   can't reach Capterra/G2/Trustpilot, so ask the user for the correct current score for
   each service; offer sensible options plus the free-text "Other" field. Apply the
   supplied value in Stage 3.

2. **Pabau's own ranking position** — a `listicle-rank` finding flagged `CONFIRM: true`,
   i.e. one that would move Pabau up or down from where the article currently places it.
   Show the proposed position vs. current and ask **Apply / Reject**. Re-ranking of every
   other service is automatic and is never asked.

3. **Grave factual error (rewrite-scale)** — a `factual` finding flagged `CONFIRM: true`:
   one whose correction would require a full rewrite or rewriting large parts of the
   article (e.g. the central ICD/CPT code the article is built on is wrong). **Do not ask
   the human about it yet — first verify the error with an independent agent.** Spawn a
   fresh, read-only fact-checker subagent (a `general-purpose` agent; run all such
   verifications together in a single message when more than one grave error was caught)
   and hand it only what it needs to judge the claim from scratch: the article's exact
   statement, the reporter's proposed `CORRECT` value, and the reporter's evidence. Tell
   it to research the point independently — actively trying to establish whether the
   article could in fact be right — to write nothing anywhere, and to return **exactly one
   verdict line**:
   `VERIFIED_ERROR: <why the article is genuinely wrong>` **or**
   `NOT_AN_ERROR: <why the article's statement is actually fine>`.
   - **Verifier returns `NOT_AN_ERROR`** → the flagged error is not real. **Drop the
     finding, leave the article unchanged on that point, and do NOT contact the human.**
     Record it as "grave error flagged but not confirmed on verification" for the summary.
   - **Verifier returns `VERIFIED_ERROR`** → the error is real, so **contact the human for
     input** via `AskUserQuestion`: show the article's statement, the verified correction,
     and that an independent check confirmed it, then ask **Apply (rewrite) / Reject**.
     - **Apply** → do not apply it as a normal in-place fix; route the article into the
       Rewrite gate path above (article-editor rewrite mode, then re-run /fact from
       Stage 1), passing the verified correction as the basis for the rewrite.
     - **Reject** → drop the finding and leave the article unchanged on that point.

Record a decision for every finding that was asked; everything else is already marked
Apply. Nothing has been written to WordPress yet. After the last batch, show a short
summary of what will be applied / rewritten / rejected / dropped-after-verification per
article, then proceed to Stage 3 automatically (no further prompts).

## Stage 3 — Apply + editorial + links (parallel, automated)

Spawn one **article-editor** subagent per article, **all in a single message** (so
articles process concurrently). To each subagent pass:
- its article URL/ID, and
- the list of **approved** decisions for that article from Stage 2 (include any
  user-supplied values/edits; omit rejected findings).

Each subagent runs its four sequential passes (approved fact-check fixes → editorial
→ link audit → FAQ block guarantee) on its own article and writes changes via the
`wordpress-access` skill. They do not ask further questions. The final pass ALWAYS
runs last: it ensures the article's FAQ is a proper Yoast FAQ block (not plain HTML),
converting it if it isn't. Articles with no FAQ are left untouched by that pass.

## Final report

Once all Stage 3 subagents return, compile a single consolidated summary for the user:
per article — what fact-check fixes were applied, editorial highlights, link changes,
the FAQ block result (already a Yoast block / converted to Yoast block / no FAQ present),
and anything skipped. End with the reminder to purge the WP Rocket cache for each
edited URL.
EOF
echo "  - /fact command installed"

# --- 2b. The /SEO command -------------------------------------------------
if curl -fsSL "$REPO_RAW/commands/SEO.md" -o "$CLAUDE/commands/SEO.md"; then
  echo "  - /SEO command installed"
else
  echo "  ERROR: could not download commands/SEO.md — check your internet connection." >&2
  exit 1
fi

# --- 3. The agents --------------------------------------------------------
cat > "$CLAUDE/agents/factcheck-reporter.md" <<'EOF'
---
name: factcheck-reporter
description: Stage 1 worker for /fact. Reviews ONE WordPress article for factual/coding accuracy, link status, and listicle ranking, and returns a numbered findings report (or a single REWRITE_REQUIRED line if the article is truncated or repeats itself). READ-ONLY — never writes to WordPress.
tools: Read, WebFetch, WebSearch, Bash, Glob, Grep
model: sonnet
---

You review a single WordPress article and return a findings report. You are a
**read-only** reviewer: you may GET/fetch article content, but you must **never**
write to WordPress in this pass (no PUT, no POST, no draft save, no category/tag/
link edits). All approved fixes are applied later by a separate stage.

You will be given one article URL or post ID. Load the fact-check instructions from
`~/.claude/factcheck-flow/prompts/1-factcheck.md` (read that file) and follow them
exactly, including the required per-finding output format (LOCATION / TYPE / ISSUE /
CORRECT / FIX / NEEDS_USER_VALUE / CONFIRM). Use the `wordpress-access` skill only for reading
the article.

Also read `~/.claude/factcheck-flow/guides/About-Pabau.md` and flag any statement that
contradicts it as a factual finding — e.g. claiming Pabau has a free trial, calling
online booking "Pabau Connect" (an internal name), implying features are gated to
higher tiers, misstating the product family (Pabau GO, Pabau Pay, Pabau Scribe),
or naming a specific customer/competitor relationship that the guide flags as
verify-first. Treat these as TYPE: Pabau-fact findings.

Your entire returned message IS the findings report (it is parsed by the
orchestrator, not shown to a human as chat). Begin your reply with the exact line:

`ARTICLE: <the url or post id you reviewed>`

then one of: `CORRECT: No fix needed`; the single line `REWRITE_REQUIRED: <reason>`
(when the article is truncated/incomplete or repeats itself — see the fact-check
instructions, and emit nothing else); or the numbered list of findings. Do not add
preamble, sign-off, or commentary outside the report.
EOF

cat > "$CLAUDE/agents/article-editor.md" <<'EOF'
---
name: article-editor
description: Stage 3 worker for /fact. Owns ONE WordPress article end-to-end — applies the human-approved fact-check fixes, then the editorial pass, then the link-audit pass, writing all changes via the WordPress REST API. Can also run in rewrite mode to fix a truncated/self-repeating article before /fact re-runs.
tools: Read, WebFetch, WebSearch, Bash, Glob, Grep
model: sonnet
---

You own ONE WordPress article from start to finish for the automated edit stage.
This runs AFTER the human has triaged fact-check findings, so there are **no more
questions** — apply the approved work and write the changes to WordPress via the
`wordpress-access` skill (SKILL.md).

You will be given:
- the article URL or post ID, and
- the **approved fact-check decisions** for this article (each is Apply / Apply-with-
  edit / Reject, plus any human-supplied values such as listicle scores or category
  choices). Apply only the approved ones; ignore rejected findings.

**Rewrite mode.** If the orchestrator dispatched you in rewrite mode (it will say so
and hand you a `REWRITE_REQUIRED` reason), do ONLY this: fetch the article, then
complete or rewrite it so it matches the full structure of similar articles on the
same site — fill in any missing sections (intro, FAQ, conclusion, documentation
requirements, etc.) and remove any duplicated or self-repeating content — then save
(a draft stays a draft; a published post stays published). Do NOT run the four passes
below: /fact re-runs in full on the rewritten article afterward, which is where
editorial and links get handled. Return a short change-log of what you completed and
de-duplicated, plus the cache-purge reminder, and stop.

Otherwise (the normal case), perform four passes in this exact order, on this one article:

1. **Pass A — approved fact-check fixes.** Fetch the current article, apply exactly
   the approved decisions you were handed, and save (draft stays a draft; published
   stays published).
2. **Pass B — editorial.** Read `~/.claude/factcheck-flow/prompts/2-editorial.md` and
   follow it in full, then save your edits.
3. **Pass C — link audit.** Read `~/.claude/factcheck-flow/prompts/3-links.md` and
   follow it in full, then save your edits.
4. **Pass D — FAQ block guarantee (ALWAYS run this LAST).** This is the final thing you
   do, after Pass C is saved. Re-fetch the article's raw block markup
   (`context=edit`) and locate its FAQ section — the question-and-answer block, however
   it is currently marked up (a `## FAQ` / `<h2>Frequently asked questions</h2>` heading
   followed by questions as `<h3>`/`<strong>`/paragraphs, a plain `<div>`, an accordion,
   `wp:heading` + `wp:paragraph` pairs, or any other plain HTML).
   - If the article has **no FAQ section at all**, do nothing here — this pass never
     invents one (a genuinely missing FAQ is added earlier, in Pass B, only if that
     article type calls for it).
   - If the FAQ is **already a proper Yoast FAQ block** — `<!-- wp:yoast/faq-block -->`
     … `<!-- /wp:yoast/faq-block -->` wrapping `<div class="schema-faq
     wp-block-yoast-faq-block">` with `.schema-faq-section` / `.schema-faq-question` /
     `.schema-faq-answer` — leave it exactly as-is.
   - Otherwise the FAQ exists but is **plain HTML / headings / an accordion / a raw
     div** — **convert it into a proper Yoast FAQ block.** Keep any introductory FAQ
     H2 heading (e.g. "Frequently asked questions") above the block; the questions and
     answers themselves go inside the block. Preserve every question and answer's exact
     wording and any inline links or formatting inside the answers (links added in Pass
     C must survive) — you are only changing the wrapper markup, never rewriting copy.

   Canonical block to produce — one `.schema-faq-section` per Q&A pair, each with a
   unique `id`:

   ```
   <!-- wp:yoast/faq-block -->
   <div class="schema-faq wp-block-yoast-faq-block">
   <div class="schema-faq-section" id="faq-question-1700000000001"><strong class="schema-faq-question">Question one?</strong> <p class="schema-faq-answer">Answer one.</p></div>
   <div class="schema-faq-section" id="faq-question-1700000000002"><strong class="schema-faq-question">Question two?</strong> <p class="schema-faq-answer">Answer two.</p></div>
   </div>
   <!-- /wp:yoast/faq-block -->
   ```

   To stay robust against Yoast version differences in how the block stores its
   attributes, first fetch another **published article on the same site that already
   has a working Yoast FAQ block** (`context=edit`) and copy its exact delimiter and
   attribute format — matching the site's real output beats a hand-built guess. Save via
   `wordpress-access`, then confirm the FAQ now renders as a Yoast block.

Rules:
- Preserve existing HTML/Gutenberg block structure unless an instruction changes it.
- Do NOT pause to ask questions. If a specific item genuinely cannot be completed
  (e.g. a required value is missing, an external check is impossible), skip that one
  item, keep going, and record it under "Skipped" in your final report.

Your returned message is a concise change-log for this article, not chat. Start with:

`ARTICLE: <url or post id>`

then short sections: `Fact-check applied:`, `Editorial:`, `Links:`, `FAQ block:`
(state one of: already a Yoast block / converted to Yoast block / no FAQ present),
`Skipped:`. End with the reminder to purge the site cache (WP Rocket → Purge this URL)
for the edited URL.
EOF
echo "  - agents installed"

# --- 4. The WordPress access skill ---------------------------------------
cat > "$CLAUDE/skills/wordpress-access/SKILL.md" <<'EOF'
---
name: wordpress-access
description: Read and update WordPress articles via the REST API using HTTP Basic Auth. Provides the site URL, credentials, and rules for fetching and saving posts. Used by /fact.
---

# WordPress access

## Credentials

Before making any request, load the credentials. Prefer environment variables if they
are already set; otherwise source the local credentials file written by the installer:

```bash
set -a; . "$HOME/.claude/factcheck-flow/wp-credentials"; set +a
```

This provides `$WP_BASE_URL`, `$WP_USER`, and `$WP_APP_PASSWORD`. If none are
available, stop and ask the user for the site URL, username, and a WordPress
Application Password rather than guessing.

## What you do

Given a post ID or URL plus instructions, fetch and/or update that article via the
WordPress REST API at `$WP_BASE_URL/wp-json/wp/v2/posts/`.

## Fetching (read)

Always fetch the current article first, with edit context so you see raw block markup:

```bash
curl -s -u "$WP_USER:$WP_APP_PASSWORD" \
  "$WP_BASE_URL/wp-json/wp/v2/posts/<POST_ID>?context=edit"
```

To resolve a URL to a post ID, query by slug:

```bash
curl -s -u "$WP_USER:$WP_APP_PASSWORD" \
  "$WP_BASE_URL/wp-json/wp/v2/posts?slug=<SLUG>&context=edit"
```

Categories/tags list endpoints (use existing terms; do not invent):

```bash
curl -s -u "$WP_USER:$WP_APP_PASSWORD" "$WP_BASE_URL/wp-json/wp/v2/categories?per_page=100"
curl -s -u "$WP_USER:$WP_APP_PASSWORD" "$WP_BASE_URL/wp-json/wp/v2/tags?per_page=100"
```

## Saving (write)

Apply changes to the fetched body/fields, then POST them back. Send only the fields you
are changing:

```bash
curl -s -u "$WP_USER:$WP_APP_PASSWORD" \
  -X POST "$WP_BASE_URL/wp-json/wp/v2/posts/<POST_ID>" \
  -H "Content-Type: application/json" \
  -d @payload.json
```

## Rules

- Update ONLY the fields you intend to change (`content`, `title`, `slug`, `status`,
  `categories`, `tags`, `author`, `meta`, `excerpt`/meta description as needed).
- A draft (`status: draft`) stays a draft; a published post (`status: publish`) stays
  published. Never change publication status unless explicitly instructed.
- Keep all existing HTML/Gutenberg block structure intact unless an instruction says
  to change it.
- Do not replace existing categories/tags — append only, using terms that already
  exist in WordPress.
- After saving, confirm what changed and remind the user to purge the site cache
  (e.g. WP Rocket → Purge this URL).
EOF
echo "  - wordpress-access skill installed"

# --- 4b. Global editing guidance in ~/.claude/CLAUDE.md -------------------
# The /fact flow reads the Pabau guides automatically. This block also points
# Claude at them for AD-HOC editing outside /fact. It is written between clearly
# marked sentinels so re-running the installer refreshes ONLY this block and
# never touches the rest of your CLAUDE.md.
CLAUDE_MD="$CLAUDE/CLAUDE.md"
GUIDE_START="<!-- factcheck-flow:pabau-guides START (managed by install.sh) -->"
GUIDE_END="<!-- factcheck-flow:pabau-guides END -->"
touch "$CLAUDE_MD"
if grep -qF "$GUIDE_START" "$CLAUDE_MD"; then
  awk -v s="$GUIDE_START" -v e="$GUIDE_END" '
    $0==s{skip=1}
    skip==0{print}
    $0==e{skip=0}
  ' "$CLAUDE_MD" > "$CLAUDE_MD.tmp" && mv "$CLAUDE_MD.tmp" "$CLAUDE_MD"
fi
# Drop trailing blank lines so repeated installs don't accumulate whitespace.
awk 'NF{last=NR} {line[NR]=$0} END{for(i=1;i<=last;i++) print line[i]}' \
  "$CLAUDE_MD" > "$CLAUDE_MD.tmp" && mv "$CLAUDE_MD.tmp" "$CLAUDE_MD"
cat >> "$CLAUDE_MD" <<EOF

$GUIDE_START
## Pabau content editing (factcheck-flow)

When writing, editing, or fact-checking Pabau content, read these guides first:

- \`~/.claude/factcheck-flow/guides/Pabau-style-guide.md\` — voice/tone, benefit framing, US vs UK terminology, formatting, glossary.
- \`~/.claude/factcheck-flow/guides/About-Pabau.md\` — what Pabau is, product family + naming rules, pricing model, competitors, customer journey.
- \`~/.claude/factcheck-flow/guides/Originality-and-search-intent.md\` — the two-bar rule for every article: fit searcher intent (answer the actual query, in the SERP-dominant format) AND carry an originality nugget (a unique angle no top-10 result has). Kill mirage/fluff; be specific.

Quick rules: US English (say "practice", not "clinic"); introduce Pabau on first mention ("practice management software like Pabau"); qualify product names once ("Pabau GO, our iOS app"); never say "Pabau Connect" externally (say "online booking"); no free trial (structured onboarding); every subscription includes every feature (no gating); don't undermine the core product when describing Plus add-ons. Every article must fit searcher intent AND have a unique angle (originality nugget) — never publish generic, me-too content.
$GUIDE_END
EOF
echo "  - CLAUDE.md editing guidance installed"

# --- 4c. Enable auto-update via a SessionStart hook -----------------------
# Registers a hook in ~/.claude/settings.json that runs update.sh whenever a new
# Claude Code session starts, so prompt/guide changes propagate without a manual
# reinstall. Idempotent, and it refuses to touch a settings.json it can't parse.
UPDATE_CMD='bash "$HOME/.claude/factcheck-flow/update.sh"'
if command -v python3 >/dev/null 2>&1; then
  SETTINGS="$CLAUDE/settings.json" python3 - "$UPDATE_CMD" <<'PY'
import json, os, sys
path = os.environ["SETTINGS"]
cmd = sys.argv[1]
try:
    with open(path) as f:
        cfg = json.load(f)
except FileNotFoundError:
    cfg = {}
except Exception:
    sys.exit(0)  # malformed settings.json — do NOT risk clobbering it; skip
if not isinstance(cfg, dict):
    sys.exit(0)
ss = cfg.setdefault("hooks", {}).setdefault("SessionStart", [])
already = any(
    h.get("command") == cmd
    for g in ss if isinstance(g, dict)
    for h in g.get("hooks", []) if isinstance(h, dict)
)
if not already:
    ss.append({"hooks": [{"type": "command", "command": cmd}]})
with open(path, "w") as f:
    json.dump(cfg, f, indent=2)
    f.write("\n")
PY
  echo "  - auto-update hook installed (SessionStart)"
else
  echo "  - NOTE: python3 not found — skipped auto-update hook (you'll need to re-run"
  echo "          this installer manually to get future prompt/guide changes)."
fi

# --- 4d. GSC access for /SEO (published-article keyword list) -------------
# /SEO's "already ranking" list reads Google Search Console via a service-account
# key. The key is a SECRET and is NOT in this repo — you supply it. PyJWT signs the
# short-lived token used to call the API.
if command -v python3 >/dev/null 2>&1; then
  if python3 -c 'import jwt' >/dev/null 2>&1; then
    echo "  - PyJWT present (GSC auth ready)"
  elif python3 -m pip install --user --quiet pyjwt >/dev/null 2>&1; then
    echo "  - PyJWT installed (GSC auth ready)"
  else
    echo "  NOTE: could not install PyJWT — if /SEO's GSC step fails, run:"
    echo "        python3 -m pip install --user pyjwt"
  fi
fi
GSC_KEY_DEST="$FF/gsc-key.json"
if [ -f "$GSC_KEY_DEST" ]; then
  echo "  - GSC key already present ($GSC_KEY_DEST) — keeping it"
else
  echo ""
  echo "  /SEO on PUBLISHED articles needs a Google Search Console service-account"
  echo "  key (JSON). Ask your admin for it. Leave blank to set up later (draft-only"
  echo "  /SEO still works without it)."
  read -r -p "  Path to your GSC service-account JSON (blank to skip): " GSC_SRC
  if [ -n "${GSC_SRC:-}" ] && [ -f "$GSC_SRC" ]; then
    umask 077; cp "$GSC_SRC" "$GSC_KEY_DEST"; chmod 600 "$GSC_KEY_DEST"
    echo "  - GSC key saved (readable only by you) to $GSC_KEY_DEST"
  else
    echo "  - skipped — set \$PABAU_GSC_KEY or place the JSON at $GSC_KEY_DEST later"
  fi
fi

# --- 5. WordPress credentials (interactive) -------------------------------
if [ -f "$CREDS" ]; then
  echo "  - credentials already present ($CREDS) — keeping them"
else
  echo ""
  echo "  Now enter your WordPress details (needed to read and edit articles)."
  echo "  Tip: the Application Password comes from WordPress → your Profile →"
  echo "       Application Passwords (it is NOT your normal login password)."
  echo ""
  read -r -p "  Site URL (e.g. https://pabau.com): " WP_URL
  read -r -p "  WordPress username: " WP_USR
  read -r -s -p "  Application password: " WP_PW; echo ""
  umask 077
  printf 'WP_BASE_URL=%s\nWP_USER=%s\nWP_APP_PASSWORD=%s\n' "$WP_URL" "$WP_USR" "$WP_PW" > "$CREDS"
  chmod 600 "$CREDS"
  echo "  - credentials saved (readable only by you) to $CREDS"
fi

echo ""
echo "  ✅ Done!"
echo ""
echo "  Next steps:"
echo "    1. Fully close and reopen Claude Code (so it loads the new command +"
echo "       the auto-update hook)."
echo "    2. Type:  /fact <article link or post ID>   (batch QA)"
echo "       or:    /SEO  <article link or post ID>   (optimize one article, then auto-runs /fact)"
echo "    3. Try one draft article first to see how it works."
echo ""
echo "  Auto-update is on: from now on, each time you open Claude Code it quietly"
echo "  pulls the latest prompts/guides when they've changed. Prompt/guide updates"
echo "  apply on your next /fact run; a rare command/agent change still needs a"
echo "  reinstall + restart."
echo ""
