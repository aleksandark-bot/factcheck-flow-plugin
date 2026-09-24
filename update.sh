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
#   - Private-repo ready: every GitHub read carries a read-only "repo token" when this
#     machine has one (env $PABAU_REPO_TOKEN, then ~/.claude/factcheck-flow/.repo-token,
#     then the cluster write token — $PABAU_CLUSTERS_TOKEN or .clusters-token — since a
#     contents:write token can read too). No token means unauthenticated requests, exactly
#     as before, which works for as long as the repo is public. A token is never printed.
#   - Says ONE line when it matters, and only then (SessionStart stdout reaches the session,
#     so Claude can pass it on): a 401/403/404 from GitHub pauses updates with a line saying
#     why — no token on this machine, or GitHub refused the one it has — and a machine that
#     still updates without a token gets a heads-up to save one before the repo goes
#     private. A machine with a working token stays silent.
#
set -uo pipefail   # deliberately NOT -e

REPO="aleksandark-bot/factcheck-flow-plugin"
BRANCH="main"
RAW="https://raw.githubusercontent.com/$REPO/$BRANCH"
API="https://api.github.com/repos/$REPO/commits/$BRANCH"
FF="$HOME/.claude/factcheck-flow"
STATE="$FF/.last-sync-sha"

mkdir -p "$FF/prompts" "$FF/guides" "$FF/bin" "$FF/clusters" "$HOME/.claude/commands" "$HOME/.claude/agents" "$HOME/.claude/skills/wordpress-access" 2>/dev/null || true

# Read-only repo token, optional (see the header). Whitespace is stripped so a pasted
# trailing newline or space never corrupts the header. AUTH is expanded everywhere as
# ${AUTH[@]+"${AUTH[@]}"}: macOS ships bash 3.2, where `set -u` treats an empty
# "${AUTH[@]}" as an unbound variable and would kill the script on a tokenless machine.
_tok() { printf '%s' "${1:-}" | tr -d '[:space:]'; }
TOKEN="$(_tok "${PABAU_REPO_TOKEN:-}")"
[ -n "$TOKEN" ] || TOKEN="$(_tok "$(cat "$FF/.repo-token" 2>/dev/null)")"
[ -n "$TOKEN" ] || TOKEN="$(_tok "${PABAU_CLUSTERS_TOKEN:-}")"
[ -n "$TOKEN" ] || TOKEN="$(_tok "$(cat "$FF/.clusters-token" 2>/dev/null)")"
AUTH=()
[ -n "$TOKEN" ] && AUTH=(-H "Authorization: Bearer $TOKEN")

# 0. The central cluster store (clusters/CONTRACT.md). It lives on its OWN branch,
#    `clusters-data`, and syncs on that branch's head sha — recorded by cluster_sync.py in
#    $FF/.last-clusters-sha, deliberately separate from main's sha below. This runs BEFORE
#    main's gate on purpose: that gate exits this script the moment nobody has pushed a
#    prompt change, and a cluster assignment somebody submitted last week would then never
#    reach anyone. Assignment data has to sync on its own schedule or it does not sync.
#
#    Backgrounded and silenced, because this fires on SessionStart: the session must never
#    wait on GitHub. cluster_sync.py is fail-silent by contract — no network, a rate limit
#    or a missing token leaves whatever is already on disk exactly as it was.
#
#    `push` drains assignments that earlier runs queued locally. Without a token it is a
#    no-op that leaves the queue intact, so nothing is ever lost to a machine that has no
#    write access yet.
#    Skipped on the self-update re-exec below (FF_SELFUPDATED set), which is the one path
#    that runs this script twice in a session: two concurrent pulls would race over the
#    same 4.6 MB base.jsonl.
if [ -z "${FF_SELFUPDATED:-}" ] && command -v python3 >/dev/null 2>&1 \
   && [ -f "$FF/bin/cluster_sync.py" ]; then
  (
    python3 "$FF/bin/cluster_sync.py" pull --quiet
    if [ -n "${PABAU_CLUSTERS_TOKEN:-}" ] || [ -s "$FF/.clusters-token" ]; then
      python3 "$FF/bin/cluster_sync.py" push
    fi
  ) </dev/null >/dev/null 2>&1 &
fi

# 1. Latest commit on main. Bail quietly if we can't reach GitHub at all. No -f: the HTTP
#    status is what tells "no access" apart from "offline", so it is captured on the last
#    line of the output and the body is everything above it.
resp="$(curl -sSL --max-time 8 -H 'Accept: application/vnd.github+json' ${AUTH[@]+"${AUTH[@]}"} \
  -w '\n%{http_code}' "$API" 2>/dev/null)" || exit 0
code="${resp##*$'\n'}"
body="${resp%$'\n'*}"
case "$code" in
  200) ;;
  401|403|404)
    # A rate limit is also a 403. That is not an access problem and passes on its own, so
    # it stays silent like any other transient failure.
    case "$body" in *[Rr]ate\ limit*) exit 0 ;; esac
    if [ -z "$TOKEN" ]; then
      echo "factcheck-flow: updates paused — this machine has no repo token. Save the token David sent to ~/.claude/factcheck-flow/.repo-token (then restart Claude Code)."
    else
      echo "factcheck-flow: updates paused — GitHub refused the repo token (HTTP $code). It has probably expired; ask David for a new one."
    fi
    exit 0 ;;
  *) exit 0 ;;
esac
# Still public and this machine has no token: it works today and will stop the day the repo
# goes private, so say so. FF_HEADSUP_SHOWN keeps the self-update re-exec below from
# repeating the line in the same session.
if [ -z "$TOKEN" ] && [ -z "${FF_HEADSUP_SHOWN:-}" ]; then
  echo "factcheck-flow: heads-up — the tool's GitHub repo is going private soon. Save the repo token David sent to ~/.claude/factcheck-flow/.repo-token so your updates keep working."
  export FF_HEADSUP_SHOWN=1
fi
remote_sha="$(printf '%s\n' "$body" | grep -m1 '"sha"' \
  | sed -E 's/.*"sha"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')"
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
     && curl -fsSL --max-time 8 ${AUTH[@]+"${AUTH[@]}"} "$RAW/update.sh" -o "$tmp_self" 2>/dev/null \
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
  if curl -fsSL --max-time 8 ${AUTH[@]+"${AUTH[@]}"} "$RAW/$1" -o "$tmp" 2>/dev/null \
     && [ -s "$tmp" ]; then
    mkdir -p "$(dirname "$2")" 2>/dev/null || true
    mv "$tmp" "$2" 2>/dev/null || rm -f "$tmp" 2>/dev/null || true
  else
    rm -f "$tmp" 2>/dev/null || true
  fi
}

for p in 1-factcheck 2-editorial 3-links seo-research seo-write generate-research generate-write; do
  fetch "prompts/$p.md" "$FF/prompts/$p.md"
done
for g in core-rules Pabau-style-guide About-Pabau Meta-title-best-practices Originality-and-search-intent WordPress-blocks Visuals; do
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

# /generate command + its writer agent (the generate-* prompts are fetched in the loop above).
# /generate CREATES new drafts, so a stale copy of either is worse than none: the route table
# (which taxonomy term sends a post to /templates/, /diagnostic-codes/ or /procedure-codes/)
# lives in these files and changes with the site, not with the model.
fetch "commands/generate.md" "$HOME/.claude/commands/generate.md"
fetch "agents/article-generator.md" "$HOME/.claude/agents/article-generator.md"
# cluster_store/cluster_sync/cluster_consolidate are the central store (CONTRACT.md).
# cluster_lookup.py imports cluster_store, so the two must never be fetched apart.
for b in gsc_query gsc_cannibal keyword_picker serp_picker dfs_lists sentence_check serp_fetch index_ping render_visual cluster_lookup cluster_store cluster_sync cluster_consolidate elementor_guard; do
  fetch "bin/$b.py" "$FF/bin/$b.py"; chmod +x "$FF/bin/$b.py" 2>/dev/null || true
done

# 4. Remember the commit we're now in sync with.
printf '%s\n' "$remote_sha" > "$STATE" 2>/dev/null || true
exit 0
