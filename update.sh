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

mkdir -p "$FF/prompts" "$FF/guides" 2>/dev/null || true

# 1. Latest commit on main. Bail quietly if we can't reach GitHub.
remote_sha="$(curl -fsSL --max-time 8 -H 'Accept: application/vnd.github+json' "$API" 2>/dev/null \
  | grep -m1 '"sha"' | sed -E 's/.*"sha"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')"
[ -n "${remote_sha:-}" ] || exit 0

# 2. Nothing new since last sync? Do nothing (this is what protects unpushed edits).
if [ -f "$STATE" ] && [ "$(cat "$STATE" 2>/dev/null)" = "$remote_sha" ]; then
  exit 0
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

for p in 1-factcheck 2-editorial 3-links; do
  fetch "prompts/$p.md" "$FF/prompts/$p.md"
done
for g in Pabau-style-guide About-Pabau Meta-title-best-practices; do
  fetch "guides/$g.md" "$FF/guides/$g.md"
done

# 4. Remember the commit we're now in sync with.
printf '%s\n' "$remote_sha" > "$STATE" 2>/dev/null || true
exit 0
