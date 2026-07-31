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
for p in 1-factcheck 2-editorial 3-links seo-research seo-write; do
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
if curl -fsSL "$REPO_RAW/bin/dfs_lists.py" -o "$FF/bin/dfs_lists.py"; then
  chmod +x "$FF/bin/dfs_lists.py" 2>/dev/null || true
  echo "  - keyword-list builder installed"
else
  echo "  NOTE: could not download bin/dfs_lists.py — /SEO Stage 2 will have no helper." >&2
fi
if curl -fsSL "$REPO_RAW/bin/sentence_check.py" -o "$FF/bin/sentence_check.py"; then
  chmod +x "$FF/bin/sentence_check.py" 2>/dev/null || true
  echo "  - sentence checker installed"
else
  echo "  NOTE: could not download bin/sentence_check.py — the /fact sentence gate will be unavailable." >&2
fi
if curl -fsSL "$REPO_RAW/bin/serp_fetch.py" -o "$FF/bin/serp_fetch.py"; then
  chmod +x "$FF/bin/serp_fetch.py" 2>/dev/null || true
  echo "  - SERP fetcher installed"
else
  echo "  NOTE: could not download bin/serp_fetch.py — /SEO Stage 1 will have no helper." >&2
fi

# --- 1b. Download the Pabau reference guides from the repo -----------------
# These define voice/terminology (Pabau-style-guide), product/positioning
# context (About-Pabau), and SERP title optimization (Meta-title-best-practices).
# The editorial prompt and factcheck-reporter read them.
for g in core-rules Pabau-style-guide About-Pabau Meta-title-best-practices Originality-and-search-intent WordPress-blocks; do
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
# Pulls the latest editable /fact files (prompts, guides, commands, agents) from the repo, but
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

mkdir -p "$FF/prompts" "$FF/guides" "$FF/bin" "$HOME/.claude/commands" "$HOME/.claude/agents" "$HOME/.claude/skills/wordpress-access" 2>/dev/null || true

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

for p in 1-factcheck 2-editorial 3-links seo-research seo-write; do
  fetch "prompts/$p.md" "$FF/prompts/$p.md"
done
for g in core-rules Pabau-style-guide About-Pabau Meta-title-best-practices Originality-and-search-intent WordPress-blocks; do
  fetch "guides/$g.md" "$FF/guides/$g.md"
done

# Retired files. seo.md was split into seo-research.md + seo-write.md; leaving the old copy
# behind means a stale 63 KB prompt can still be read by mistake. Only remove it once its
# replacements are actually on disk, so a failed download never leaves the install broken.
if [ -s "$FF/prompts/seo-research.md" ] && [ -s "$FF/prompts/seo-write.md" ]; then
  rm -f "$FF/prompts/seo.md" 2>/dev/null || true
fi

# /fact command + its two subagents. These live outside $FF (Claude Code loads commands
# from ~/.claude/commands and agents from ~/.claude/agents), and they carry rules that
# change alongside the prompts — e.g. the article-editor's block-guarantee passes — so a
# repo change to either has to reach existing installs, not just fresh ones.
fetch "commands/factcheck-flow.md" "$HOME/.claude/commands/fact.md"
fetch "agents/article-editor.md" "$HOME/.claude/agents/article-editor.md"
fetch "agents/factcheck-reporter.md" "$HOME/.claude/agents/factcheck-reporter.md"
fetch "agents/seo-writer.md" "$HOME/.claude/agents/seo-writer.md"

# The wordpress-access skill. Safe to sync: it holds only the credential RESOLUTION ORDER
# (env vars → $WP_CREDENTIALS_FILE → ~/.claude/factcheck-flow/wp-credentials), never a
# secret and never an install-specific path, so every install wants the same copy.
fetch "skills/wordpress-access/SKILL.md" "$HOME/.claude/skills/wordpress-access/SKILL.md"

# /SEO command + helpers (the seo-research/seo-write prompts are fetched in the loop above)
fetch "commands/SEO.md" "$HOME/.claude/commands/SEO.md"
for b in gsc_query keyword_picker serp_picker dfs_lists sentence_check serp_fetch; do
  fetch "bin/$b.py" "$FF/bin/$b.py"; chmod +x "$FF/bin/$b.py" 2>/dev/null || true
done

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
below — do NOT treat it as a finding); or a two-bucket findings report.

The two buckets are the reporter's own split, and they map straight onto what you do next:

- **`AUTO`** — one line per finding, already in the shape
  `<type> | <location> | <what is wrong> → <the fix>`. These are applied without asking.
  Do NOT expand, re-derive, or re-verify them; pass each line through to Stage 3 verbatim,
  tagged with its article.
- **`ASK`** — the long seven-field form, and the only findings Stage 2 looks at.

Articles that returned `CORRECT: No fix needed` contribute zero findings but still go
through Stage 3.

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

**The whole `AUTO` bucket is applied automatically** — route it straight to Stage 3
without inspection. (`publishing`: a draft stays a draft and a published article stays
published — the editor already targets the right one, so never ask. Categories and tags
are owned by the editorial pass, which also strips "Uncategorized" — nothing to ask here.
Block-contract gaps are not reported at all now: the editor's Pass D enforces the contract
unconditionally, so there is nothing to triage.)

Only the `ASK` bucket reaches this stage, via the `AskUserQuestion` tool (batch up to 4
per call; label each with its article + location). If the `ASK` bucket is empty across
every article, skip the questions entirely and go straight to Stage 3. Case 3 is special:
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
   fresh, read-only fact-checker subagent (a `general-purpose` agent **pinned to
   `model: opus`** — this verdict decides whether a whole article gets rewritten, and it is
   rare enough that the stronger model costs almost nothing; do not let it inherit a cheaper
   session model; run all such
   verifications together in a single message when more than one grave error was caught)
   and hand it only what it needs to judge the claim from scratch: the article's exact
   statement, the reporter's proposed `CORRECT` value, and the reporter's `EVIDENCE`
   line. Do not send it the article or any other finding. Tell
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
- its article URL/ID,
- that article's `AUTO` lines verbatim, and
- the **approved** `ASK` decisions for that article from Stage 2 (include any
  user-supplied values/edits; omit rejected findings).

Each subagent fetches its article ONCE, runs its four sequential passes (approved
fact-check fixes → editorial → link audit → block guarantees) in memory, and writes
everything back in a SINGLE save via the `wordpress-access` skill. They do not ask
further questions.

The block-guarantee pass ALWAYS runs last and enforces the contract in
`~/.claude/factcheck-flow/guides/WordPress-blocks.md` — required document order plus the
eight always-on guarantees (Key takeaways, template download box, Pabau section + CTA
block, Conclusion, Continue your research, Yoast FAQ, listicle pricing segments, image
captions). That file and the article-editor's own Pass D own the detail; you are the
orchestrator and never perform this work, so do not restate the contract to the subagents
— they read it themselves.

After that, and before the single save, each editor must clear the **sentence gate** (Pass E):
`bin/sentence_check.py` counts every sentence in the body and the editor rewrites until the
script exits 0 — nothing over 30 words ships, and 26–30 needs a per-sentence justification.
Sentence length is measured by script precisely because it cannot be eyeballed. Every editor
reports the checker's final summary line verbatim; an article whose change-log has no
`Sentence gate:` line did not run it, and that is a failed job worth flagging in your report.

## Final report

Once all Stage 3 subagents return, compile a single consolidated summary for the user.
Each editor returns a compact change-log; relay it, don't re-derive it. Per article:
fact-check fixes applied, editorial highlights, link changes, the one-line block-contract
status the editor reported for each of the eight guarantees, the sentence gate's summary line
(longest sentence + how many were rewritten), and anything skipped. Note
any article whose grave error was flagged but dropped after independent verification, and
any article that hit the two-rewrite ceiling and needs manual attention. End with the
reminder to purge the WP Rocket cache for each edited URL.
EOF
echo "  - /fact command installed"

# --- 2b. The /SEO command -------------------------------------------------
if curl -fsSL "$REPO_RAW/commands/SEO.md" -o "$CLAUDE/commands/SEO.md"; then
  echo "  - /SEO command installed"
  if curl -fsSL "$REPO_RAW/agents/seo-writer.md" -o "$CLAUDE/agents/seo-writer.md"; then
    echo "  - seo-writer agent installed"
  else
    echo "  NOTE: could not download agents/seo-writer.md — /SEO cannot write without it." >&2
  fi
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
exactly, including the two-bucket output format (a one-line `AUTO` bucket, and an `ASK`
bucket in the long labelled form). **Fetch the article ONCE**, via the `wordpress-access`
skill — REST, `context=edit`, with that skill's `_fields=` list. Never WebFetch the public
URL; the site's nav would consume most of the response. Read only.

Also read `~/.claude/factcheck-flow/guides/About-Pabau.md` and flag any statement that
contradicts it as a factual finding — e.g. claiming Pabau has a free trial, calling
online booking "Pabau Connect" (an internal name), implying features are gated to
higher tiers, misstating the product family (Pabau GO, Pabau Pay, Pabau Scribe),
or naming a specific customer/competitor relationship that the guide flags as
verify-first. Treat these as TYPE: Pabau-fact findings.

**Do NOT read `WordPress-blocks.md`, and do not audit the block contract.** The
article-editor's final pass enforces all of it unconditionally later in the run, so a block
audit here is redone twice and read by nobody. The single exception — a wholly missing FAQ —
is spelled out in the fact-check instructions.

Your entire returned message IS the findings report (it is parsed by the
orchestrator, not shown to a human as chat). Begin your reply with the exact line:

`ARTICLE: <the url or post id you reviewed>`

then one of: `CORRECT: No fix needed`; the single line `REWRITE_REQUIRED: <reason>`
(when the article is truncated/incomplete or repeats itself — see the fact-check
instructions, and emit nothing else); or the two buckets, each under its own header,
with `(none)` where a bucket is empty. Do not add preamble, sign-off, or commentary
outside the report.
EOF

cat > "$CLAUDE/agents/article-editor.md" <<'EOF'
---
name: article-editor
description: Stage 3 worker for /fact. Owns ONE WordPress article end-to-end — applies the human-approved fact-check fixes, then the editorial pass, then the link-audit pass, writing all changes via the WordPress REST API. Can also run in rewrite mode to fix a truncated/self-repeating article before /fact re-runs.
tools: Read, Write, WebFetch, WebSearch, Bash, Glob, Grep
model: opus
---

You own ONE WordPress article from start to finish for the automated edit stage.
This runs AFTER the human has triaged fact-check findings, so there are **no more
questions** — apply the approved work and write the changes to WordPress via the
`wordpress-access` skill (SKILL.md).

You will be given:
- the article URL or post ID,
- that article's `AUTO` findings (one line each — apply them as written), and
- the approved `ASK` decisions, if any (each Apply / Apply-with-edit / Reject, plus any
  human-supplied values such as listicle scores). Apply only the approved ones.

## Fetch once, save once

This is the rule that governs the whole job.

1. **Fetch the article ONCE**, at the very start, via the `wordpress-access` skill — REST,
   `context=edit`, with that skill's `_fields=` list. Never WebFetch the public URL to read
   the article: the site's nav and footer would consume most of the response.
2. **Run all four passes against the copy you hold**, in memory, in order. Do not re-fetch
   between passes — you already have the body, including every edit you just made to it.
3. **Clear the sentence gate BEFORE you save** (Pass E below). The article does not go out
   over the ceiling.
4. **Save ONCE**, at the end, with a single PUT. Write `payload.json` with the Write tool and
   send it with `-d @payload.json -o /dev/null -w '%{http_code}\n'`. A draft stays a draft;
   a published post stays published.
5. **Verify with grep assertions, not page fetches** (see "Verifying the save" below).

The old four-fetch / four-save shape cost six full copies of the article per run and bought
nothing. If a pass genuinely cannot proceed without re-reading something, re-read that one
thing, not the article.

## Guides — read on trigger

- `~/.claude/factcheck-flow/guides/core-rules.md` — **read first, always.** The Pabau
  non-negotiables, voice and mechanics, AI tells, and the required document order.
- `~/.claude/factcheck-flow/prompts/2-editorial.md` — at Pass B.
- `~/.claude/factcheck-flow/prompts/3-links.md` — at Pass C.
- `~/.claude/factcheck-flow/guides/WordPress-blocks.md` — at Pass D, and any earlier moment
  you need block markup. **It is the single source of truth for the block contract**; the
  D-steps below tell you what to DO, that file tells you what the markup IS. Never
  reconstruct a block from memory or from a summary.
- `Pabau-style-guide.md`, `About-Pabau.md`, `Meta-title-best-practices.md` — when
  `2-editorial.md` sends you to them (writing prose, writing Pabau copy, writing a SERP
  title). Not up front.

**Rewrite mode.** If the orchestrator dispatched you in rewrite mode (it will say so
and hand you a `REWRITE_REQUIRED` reason), do ONLY this: fetch the article, then
complete or rewrite it so it matches the full structure of similar articles on the
same site — fill in any missing sections (intro, FAQ, conclusion, documentation
requirements, etc.) and remove any duplicated or self-repeating content — then save
(a draft stays a draft; a published post stays published). Do NOT run the four passes
below: /fact re-runs in full on the rewritten article afterward, which is where
editorial and links get handled. Return a short change-log of what you completed and
de-duplicated, plus the cache-purge reminder, and stop.

Otherwise (the normal case), perform four passes in this exact order, on the copy you fetched:

1. **Pass A — approved fact-check fixes.** Apply the `AUTO` lines exactly as written, plus
   the approved `ASK` decisions. Ignore rejected findings.
2. **Pass B — editorial.** Read `~/.claude/factcheck-flow/prompts/2-editorial.md` and follow
   it in full.
3. **Pass C — link audit.** Read `~/.claude/factcheck-flow/prompts/3-links.md` and follow it
   in full.
4. **Pass D — block guarantees (ALWAYS run this LAST).** Read
   `~/.claude/factcheck-flow/guides/WordPress-blocks.md` — the contract, with the exact
   markup for every block (reference article: https://pabau.com/templates/accutite/, post
   151170; fetch it with `context=edit` if you want to see the real thing). Then enforce all
   nine guarantees below, in order, against the block markup you hold: Key takeaways →
   download box (templates) → Pabau section + CTA block → Conclusion → Continue your
   research → FAQ → listicle pricing → image captions → video placement.

   In D1, D5, D6 and D9 you are only changing wrapper markup, letter case, placeholder items,
   and block position — never the copy. D2, D3, D4, D7 and D8 may require writing new content
   (a download box, a Pabau section, a proper conclusion, a pricing segment, an image caption);
   write it in the article's voice per `2-editorial.md` and the Pabau guides.

   The required document order you are enforcing is `WordPress-blocks.md` §1. Never leave a
   heading above a block that renders its own heading (Key takeaways, Continue your research).

   **D1 — Key takeaways (ALWAYS).** Contract: §2. Locate the Key takeaways section near the
   top of the article, however it is currently marked up: the proper custom block, a plain
   `<h2>`/`<h3>` "Key takeaways" heading followed by a `<ul>`/paragraphs, a pasted raw
   `<div id="key_takeaways">` (that is the block's *rendered* output, not real block markup),
   an Elementor blue panel, or any other HTML. Then:
   - **Already the proper self-closing block** → change only two things: add
     `"title":"Key takeaways"` if the attribute is absent, and fix the letter case of any
     `items[].text` that is not sentence case. If both are already right, change nothing.
   - **Any non-block form** → convert it to the block in §2. Pull each takeaway's text into
     one `items` entry, preserving wording and inline links, and drop the old heading/list
     markup (the block renders its own header).
   - **Still absent** → add it. Pass B should already have written the section, since it is
     a required one; if it somehow didn't, write it here.

   **D2 — Download box (TEMPLATE ARTICLES ONLY).** Contract: §3. A template article is one
   with a `/templates/` URL, or one whose job is to hand the reader a downloadable
   form/chart/worksheet. Ensure the box sits directly below Key takeaways and above the
   intro. The wrapper is fixed and copied byte-for-byte from §3; the H2 text, the
   description, and the `href` are written fresh for THIS article — never carry AccuTite's
   (or any other post's) heading, description, or PDF URL across. Verify the download URL
   before saving:
   `curl -sI -o /dev/null -w '%{http_code}' "<url>"` — ship only a 200. If nothing resolves,
   keep the box, leave the best candidate URL in place, and record the missing asset under
   "Skipped". A non-template article gets no download box; remove one that's there by mistake.

   **D3 — Pabau section + CTA block (ALWAYS).** Contract: §4 (the block) and §5 (the
   section). The article must have an H2 section immediately before the Conclusion that
   promotes Pabau for this article's specific purpose and contains the CTA block. Decide by
   what you find:
   - Section exists, no CTA block → insert the block at the end of it.
   - CTA block exists but sits loose elsewhere → write the section around it in that slot.
   - A Pabau section exists elsewhere in the body → move or rework it into the pre-Conclusion
     slot rather than writing a second one.
   - Neither exists → write the section (2–4 paragraphs: what the practice does today, what
     Pabau does instead, the outcome) plus the block.

   **D4 — Conclusion (ALWAYS).** Contract: §6. The body must end with an H2 headed exactly
   `Conclusion`.
   - Rename any variant — "The bottom line", "The bottom line on X", "Final thoughts",
     "Wrapping up", "Key points", "Getting started with…", or any topic-specific sign-off.
     Keep the section's content; change the heading text and its `id`/anchor to `h-conclusion`.
   - If the existing conclusion summarizes rather than concludes, rewrite it. If there is no
     conclusion at all, write one.
   - Ensure it ends with the inline `/book-demo/` CTA sentence. The `book-demo` CTA *block*
     stays in D3's section; do not put it here.

   **D5 — FAQ (ALWAYS).** Contract: §8, which carries the canonical markup and the full
   conversion rules. Locate the FAQ however it is marked up, then apply §8: leave a proper
   Yoast block alone, convert any other form, and — this is the one case where you do
   nothing — if the article has **no FAQ section at all**, leave it. This pass never invents
   one; a genuinely missing FAQ is written earlier, in Pass B.

   **D6 — Continue your research (ALWAYS).** Contract: §7. Locate the "Expert picks" /
   "Continue your research" box however it is marked up (the `expert-picks` block, a list
   block, a styled panel, a plain `<ul>`).
   - No block at all → build one from the up-to-5 qualifying under-linked articles chosen per
     `3-links.md` in Pass C. Non-block form → convert it, preserving the real links.
   - Scan for placeholder, empty, or dead items and remove them: a literal "list item #1" /
     "list item #2", a bare "list item", "Article title", "Lorem ipsum", an empty `<li>`, or
     a link whose href is "#", empty, or a stub like "example.com". Pass C should have filled
     the block with genuine links already; replace any survivor with a real link to a
     qualifying under-linked article (per `3-links.md`) or delete that item.
   - If **no genuine link items remain and you cannot source any**, remove the whole block
     rather than ship an empty shell or stubs. This is the one case where the article may end
     up without it; note it under "Skipped".

   **D7 — Listicle pricing segments (LISTICLES ONLY).** Contract: §9. Every provider review
   must END with a pricing segment — a `Pricing` heading at the level matching the article's
   provider hierarchy, a pricing table, then one sentence of context — placed after the
   shines/falls-short material and before the next provider. Prefer the site's
   `pricing-table` block using the provider's exact stored name; after saving, confirm it
   rendered real rows (see below) and fall back to a `wp:table` if it came back empty. Every
   figure comes from the provider's own website; never a third-party listing. Also check the
   listicle carries its top-of-page comparison table right after the intro, and add it if
   missing — it does not replace the per-provider tables.

   **D8 — Image captions (ALWAYS).** Contract: §10, which carries the caption rules, the
   block markup, and the required 800 × 35 spacer. Walk EVERY image in the article — core
   `wp:image` blocks, images inside `wp:html`, images in a gallery — and bring each one up to
   §10:
   - Any image with no `<figcaption>` gets one written for it. No image ships bare, and never
     ask about it. Look at what the image actually shows (fetch the `src` if the alt text and
     surrounding copy don't tell you) and write the caption for *that* image in *that*
     section — never one that would fit any image on any article.
   - Rewrite labels and fragments into full sentences; add the missing period.
   - Strip asterisk italics and wrap the text in `<em>` — asterisks render literally on the
     front end. Also strip a stray single leading or trailing `*`.
   - Pabau feature screenshots get the extra treatment in §10: name the feature AND say how
     it helps the reader do the specific thing this article is about.
   - Keep alt text present and separate. Ensure exactly one spacer follows each image.

   **D9 — Video placement (ONLY IF the article has a video).** Contract: §11. A YouTube embed
   belongs at the END of the intro — after every intro paragraph, immediately before the first
   H2. It must never break up a prose section: not between two paragraphs, not between a
   heading and its first paragraph, not inside the Pabau section, Conclusion, or FAQ, and not
   after the Conclusion. Find every embed in the body and move any that is misplaced, block
   markup unchanged. If a paragraph was split around it, rejoin the halves, and drop any
   "watch the video below" line left pointing at nothing. Ensure one 800 × 35 spacer follows
   the embed. No video in the article → nothing to do; never add one.

## Pass E — sentence-length gate (MANDATORY, blocks the save)

Sentence length is not checked by eye. You cannot count words reliably while writing, so a
script does it. Run it, fix what it lists, run it again. **This gate is not optional and not
negotiable: while it exits non-zero, the article is not finished and you may not PUT it.**

After Pass D, before you write `payload.json`:

```bash
# 1. Dump the body you are about to save (write it with the Write tool, never echo/heredoc).
#    Then check it:
python3 ~/.claude/factcheck-flow/bin/sentence_check.py --file /tmp/body.html
```

It prints one line per offending sentence — word count, where it lives, and the sentence
itself — then a summary and PASS/FAIL. Exit 0 means clean; exit 1 means you have rewriting to
do. Rewrite every sentence it lists **in the body you hold**, then re-run. Repeat until it
exits 0. Splitting one long sentence into two is almost always the fix.

Rules for clearing the gate:

- **Nothing over 30 words ships. Ever.** There is no judgment call here — split it.
- **26–30 is a justified exception, not a second budget.** A sentence may stay in that band
  only where splitting genuinely breaks the meaning. For each one you keep, name it and say
  why in your change-log. If you cannot articulate why, it does not qualify — split it.
- **Never buy the word count with damage:** no dropped subjects, no telegraphic fragments, no
  clause welded on with a semicolon or an em dash to make one sentence read as two. The
  checker counts words; you still own the prose. A gate-passing article that reads like a
  telegram has failed Pass B, and the style guide's "vary your sentence length" still holds.
- The gate covers everything the checker sees: body paragraphs, list items, table cells, image
  captions, Key takeaways items, CTA and download-box copy, FAQ answers.
- If the script is missing (an older install), fetch it once:
  `curl -fsSL https://raw.githubusercontent.com/aleksandark-bot/factcheck-flow-plugin/main/bin/sentence_check.py -o ~/.claude/factcheck-flow/bin/sentence_check.py`

After the save lands, re-run it against what actually shipped and paste that summary line
into your change-log verbatim:

```bash
python3 ~/.claude/factcheck-flow/bin/sentence_check.py --post <POST_ID>
```

## Verifying the save

After the single PUT returns a 2xx, confirm the blocks rendered — **without pulling the page
into context.** Assert against the front end in Bash and read only the numbers:

```bash
URL="<article URL>"
curl -s "$URL" | grep -c 'wp-element-caption'            # captions rendered
curl -s "$URL" | grep -c 'wp-block-yoast-faq-block'      # FAQ block rendered
curl -s "$URL" | grep -o '<table[^>]*>' | wc -l          # pricing/comparison tables rendered
curl -s "$URL" | grep -o '>\*[^<]\{0,80\}\*<' | head -5  # leaked asterisk italics (want none)
```

Compare each count against what you expect to have written. Only when an assertion fails do
you pull a small excerpt (`grep -o … -A2 -B2`) to see why. For D7 specifically, an empty
`pricing-table` block means that provider isn't in the site's dataset — swap it for a
`wp:table` and save that correction.

## Rules

- Preserve existing HTML/Gutenberg block structure unless an instruction changes it.
- Do NOT pause to ask questions. If a specific item genuinely cannot be completed
  (e.g. a required value is missing, an external check is impossible), skip that one
  item, keep going, and record it under "Skipped" in your final report.
- Never paste the article body inline into a shell command — write it to a file and send it
  with `-d @payload.json`.

## Your report

Your returned message is a concise change-log for this article, not chat, and the
orchestrator relays it rather than re-deriving it. Keep each line short. Start with:

`ARTICLE: <url or post id>`

then these sections, one line each:

- `Fact-check applied:` — count plus anything notable
- `Editorial:` — the highlights, not an inventory
- `Links:` — added / removed / replaced counts, industry + case-study links, external count
- `Key takeaways block:` already correct / converted / title attribute added / casing fixed / added
- `Download box:` already correct / added / URL fixed / not a template article
- `Pabau section + CTA block:` already correct / CTA block added / section written / section moved
- `Conclusion:` already correct / renamed from "<old heading>" / rewritten to conclude / written / CTA link added
- `FAQ block:` already a Yoast block / converted / no FAQ present
- `Continue your research block:` already correct / converted / added / placeholders replaced / placeholders removed / trimmed to 5 / wrapper H2 removed / empty block removed
- `Pricing segments:` all first-party / N added / N figures corrected / comparison table added / not a listicle
- `Image captions:` N images, all captioned / N written / N rewritten / N asterisk fixes / no images
- `Video:` already at end of intro / moved to end of intro from "<old location>" / spacer added / no video
- `Sentence gate:` the checker's final summary line, pasted verbatim (e.g. `175 sentences |
  longest 24w | 0 over 25`), then `N rewritten`. If any sentence sits in the 26–30 band, list
  each one and why it can't be split. An empty or absent line means the gate was not run,
  which is a failed job — run it.
- `Verified:` the assertion counts you got back
- `Skipped:` anything you couldn't complete, and why

End with the reminder to purge the site cache (WP Rocket → Purge this URL) for the edited URL.
EOF
echo "  - agents installed"

# --- 4. The WordPress access skill ---------------------------------------
cat > "$CLAUDE/skills/wordpress-access/SKILL.md" <<'EOF'
---
name: wordpress-access
description: Read and update WordPress articles via the REST API using HTTP Basic Auth. Provides the site URL, credentials, and rules for fetching and saving posts. Used by /fact and /SEO.
---

# WordPress access

## Credentials

No secret is committed to the shared plugin — this file carries only the *resolution
order*, which is identical on every install, so it can be auto-synced like the prompts.

Resolve credentials in this order and stop at the first that yields all three values:

1. **Environment variables** `WP_BASE_URL`, `WP_USER`, `WP_APP_PASSWORD`.
2. **The file named by `$WP_CREDENTIALS_FILE`**, if that variable is set.
3. **`~/.claude/factcheck-flow/wp-credentials`** — the conventional path the installer
   writes to (mode 600, gitignored, never in the repo).

Both file forms are accepted, so an existing credentials file usually works as-is:

```
WP_BASE_URL=https://example.com
WP_USER=someone
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

or a plain document containing lines like `Site URL:`, `Username:`, and
`Application Password:` (the labels are matched case-insensitively).

Load them without echoing the values, e.g.:

```bash
CREDS="${WP_CREDENTIALS_FILE:-$HOME/.claude/factcheck-flow/wp-credentials}"
[ -n "$WP_APP_PASSWORD" ] || { set -a; . "$CREDS" 2>/dev/null; set +a; }
```

(That `.` form only works for the `KEY=VALUE` shape; for the labelled-document shape,
parse the three labels instead. Either way, never print a password to stdout, never
paste it into a URL you log, and never write it into a file inside the repo.)

The values you need:

- Site base URL, e.g. `https://pabau.com` (used as `$WP_BASE_URL`; no trailing `/wp-json`)
- WordPress username (`$WP_USER`)
- WordPress Application Password (`$WP_APP_PASSWORD`) — from WordPress → your Profile →
  Application Passwords. This is NOT the normal login password.

If none of the three sources yields credentials, stop and ask the user to run the
installer or set `$WP_CREDENTIALS_FILE`. Never guess, and never proceed unauthenticated.

## What you do

Given a post ID or URL plus instructions, fetch and/or update that article via the
WordPress REST API at `$WP_BASE_URL/wp-json/wp/v2/posts/`.

**The REST API is the only way you read article content.** Never `WebFetch` a public
article URL to read its body — see "Never fetch the front end for content" below.

## Fetching (read)

Two rules keep the payload small. Both matter: an article you fetch early stays in
context for the rest of the job, so every wasted kilobyte is re-read on every later turn.

**1. Always pass `_fields=`.** Without it, `context=edit` returns `content.rendered`
AND `content.raw` (the whole body twice) plus Yoast's `yoast_head` and
`yoast_head_json` blobs and a `_links` map — several times the size of what you need.

```bash
FIELDS='id,slug,link,status,type,title,content,excerpt,categories,tags,meta,featured_media'

curl -s -u "$WP_USER:$WP_APP_PASSWORD" \
  "$WP_BASE_URL/wp-json/wp/v2/posts/<POST_ID>?context=edit&_fields=$FIELDS"
```

Some installs honour nested selection, which drops `content.rendered` — a second full
copy of the body. Test it once per site:

```bash
curl -s -u "$WP_USER:$WP_APP_PASSWORD" \
  "$WP_BASE_URL/wp-json/wp/v2/posts/<POST_ID>?context=edit&_fields=content.raw" | head -c 300
```

If that returns `{"content":{"raw":"…"}}`, use `content.raw` in `FIELDS`. If it returns
the whole content object anyway, keep plain `content`.

**2. Fetch once per article, per job.** You keep the body you fetched; re-fetching it
between editing passes re-reads something you already hold.

To resolve a URL to a post ID, query by slug:

```bash
curl -s -u "$WP_USER:$WP_APP_PASSWORD" \
  "$WP_BASE_URL/wp-json/wp/v2/posts?slug=<SLUG>&context=edit&_fields=$FIELDS"
```

Other endpoints — always scoped with `_fields`, which typically cuts them by ~90%
(the defaults carry description, count, link, taxonomy and a `_links` map per term):

```bash
# categories / tags (use existing terms; do not invent)
curl -s -u "$WP_USER:$WP_APP_PASSWORD" "$WP_BASE_URL/wp-json/wp/v2/categories?per_page=100&_fields=id,name,slug"
curl -s -u "$WP_USER:$WP_APP_PASSWORD" "$WP_BASE_URL/wp-json/wp/v2/tags?per_page=100&_fields=id,name,slug"

# media library search (for sourcing images)
curl -s -u "$WP_USER:$WP_APP_PASSWORD" "$WP_BASE_URL/wp-json/wp/v2/media?search=<term>&per_page=20&_fields=id,source_url,alt_text,title"
```

## Never fetch the front end for content

The site's navigation and footer are very large. A `WebFetch` of a public article URL
spends most of its budget on that chrome before it reaches the body — which is why older
versions of these prompts told you to raise the token limit. The REST response above has
no chrome in it at all, so the workaround is unnecessary: **read via REST, always.**

To verify that a save rendered correctly, do not pull the page into context either.
Assert against it in Bash and print only the answer:

```bash
URL="<article URL>"

# how many captions rendered?
curl -s "$URL" | grep -c 'wp-element-caption'

# did a custom block render, or ship as an empty shell?
curl -s "$URL" | grep -c 'wp-block-yoast-faq-block'
curl -s "$URL" | grep -o '<table[^>]*>' | wc -l

# did any literal asterisk-italics leak to the front end?
curl -s "$URL" | grep -o '>\*[^<]\{0,80\}\*<' | head -5
```

Each of these returns a number or a couple of short lines instead of a whole page. Only
pull a real excerpt (`grep -o … -A2 -B2`) when an assertion fails and you need to see why.

## Saving (write)

**One save per article, per job.** Apply every change to the body you already hold in
memory, then PUT once at the end. Saving between passes costs a full extra copy of the
article in context each time and buys nothing.

Write the payload to a file with the Write tool, then send it by reference:

```bash
curl -s -u "$WP_USER:$WP_APP_PASSWORD" \
  -X POST "$WP_BASE_URL/wp-json/wp/v2/posts/<POST_ID>" \
  -H "Content-Type: application/json" \
  -d @payload.json \
  -o /dev/null -w '%{http_code}\n'
```

Never paste the article body inline into the shell command: the quoting breaks on real
content, and it puts a second full copy of the body into context. Discard the response
body with `-o /dev/null` — you already know what you sent, so the status code is the
entire signal you need. On a non-2xx code, re-run without `-o /dev/null` to read the error.

## Rules

- Update ONLY the fields you intend to change (`content`, `title`, `slug`, `status`,
  `categories`, `tags`, `author`, `meta`, `excerpt`/meta description as needed).
- A draft (`status: draft`) stays a draft; a published post (`status: publish`) stays
  published. Never change publication status unless explicitly instructed.
- Keep all existing HTML/Gutenberg block structure intact unless an instruction says
  to change it.
- Do not replace existing categories/tags — append only, using terms that already
  exist in WordPress.
- Fetch once, save once, and verify with a `grep` assertion rather than a page fetch.
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
- \`~/.claude/factcheck-flow/guides/WordPress-blocks.md\` — the block contract + exact markup: document order, Key takeaways block (mandatory \`"title":"Key takeaways"\`), template download box, Pabau CTA (\`book-demo\`) block and the Pabau section before the Conclusion, the \`Conclusion\` heading + its \`/book-demo/\` link, Continue your research (\`expert-picks\`), Yoast FAQ, listicle pricing tables, image captions. Reference article: https://pabau.com/templates/accutite/.

Block rules every article must satisfy: "Key takeaways" (capital K only, via the block's \`title\` attribute); an H2 Pabau section with the CTA block immediately before an H2 headed exactly "Conclusion" that concludes (not summarizes) and ends with a \`/book-demo/\` CTA link; a Continue your research block; a download box on template articles; a caption on every image (full sentence, ends with a period, italic via \`<em>\` — and if it shows a Pabau feature, it says how that feature helps the reader do what the article is about); any YouTube video placed at the end of the intro (after all intro paragraphs, before the first H2) and never breaking up a prose section; and in listicles a \`Pricing\` heading + pricing table closing every provider review, with figures from the provider's own website only.

Quick rules: keep sentences to 25 words max (30 only where a split would break the meaning); US English (say "practice", not "clinic"); introduce Pabau on first mention ("practice management software like Pabau"); qualify product names once ("Pabau GO, our iOS app"); never say "Pabau Connect" externally (say "online booking"); no free trial (structured onboarding); every subscription includes every feature (no gating); don't undermine the core product when describing Plus add-ons. Every article must fit searcher intent AND have a unique angle (originality nugget) — never publish generic, me-too content.
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
