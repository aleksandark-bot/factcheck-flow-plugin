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
#     contents:write token can read too). With a token, files come through the Contents
#     API pinned to the commit just checked; without one, from raw.githubusercontent
#     unauthenticated, exactly as before, which works for as long as the repo is public.
#     A token is never printed.
#   - Also keeps the SEO-knowledge skill's git clone (~/.claude/skills/SEO-knowledge)
#     fast-forwarded, backgrounded and at most hourly — see step 0b.
#   - Says ONE line only when the user has to act (SessionStart stdout reaches the session,
#     so Claude can pass it on): updates paused by a 401/403/404 — no token on this machine,
#     or GitHub refused the one it has — or a token GitHub refused while the repo is still
#     public, so updates carry on unauthenticated for now. A tokenless machine that can
#     reach the repo, and a machine with a working token, both stay silent.
#
set -uo pipefail   # deliberately NOT -e

REPO="aleksandark-bot/factcheck-flow-plugin"
BRANCH="main"
RAW="https://raw.githubusercontent.com/$REPO/$BRANCH"
API="https://api.github.com/repos/$REPO/commits/$BRANCH"
CONTENTS="https://api.github.com/repos/$REPO/contents"
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
# Set by step 1 below when GitHub refused this machine's token but the repo still answered
# without one, and carried across the self-update re-exec so that run neither re-sends the
# refused token nor repeats the line about it.
[ -n "${FF_TOKEN_REFUSED:-}" ] && TOKEN=""
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

# 0b. The SEO-knowledge skill (github.com/aleksandark-bot/seo-knowledge-skill), a git clone
#     at ~/.claude/skills/SEO-knowledge. Same reasoning as step 0: it has its own history,
#     so it cannot wait behind main's gate, and it runs backgrounded and silenced. It only
#     ever FAST-FORWARDS, and only when every one of these holds — otherwise it does nothing:
#       - the directory is a git checkout whose origin is that repo (https, with or without .git);
#       - git is really there. On macOS /usr/bin/git is a stub that pops an "install developer
#         tools" dialog when the Command Line Tools are missing, so on a Mac that stub is only
#         run once xcode-select points at a developer dir that holds a real git;
#       - at most once an hour ($FF/.last-skill-pull), since sessions start often;
#       - no git operation in progress (index.lock, rebase, merge, cherry-pick), no maintainer
#         rebuild running, branch `main`, working tree clean, and the local branch not ahead of
#         the remote. David's machine publishes the skill FROM this checkout, so a rebuild's
#         half-written files or an unpushed commit must never be pulled over.
#     The token (when there is one) travels as a one-off http.extraheader scoped to
#     https://github.com/ — never written to .git/config, never in the remote URL. If the
#     tokened fetch fails, one unauthenticated retry (a still-public repo, a stale token).
SK_DIR="$HOME/.claude/skills/SEO-knowledge"
SK_STAMP="$FF/.last-skill-pull"
SK_LOCK="$FF/.skill-pull.lock"
sk_git_ok() { # a real git on PATH — never the macOS installer stub
  local g dev
  g="$(command -v git 2>/dev/null)" || return 1
  [ -n "$g" ] || return 1
  if [ "$(uname -s 2>/dev/null)" = Darwin ] && [ "$g" = /usr/bin/git ]; then
    dev="$(xcode-select -p 2>/dev/null)" || return 1
    [ -n "$dev" ] && [ -x "$dev/usr/bin/git" ] || return 1
  fi
  return 0
}
sk_origin_ok() {
  case "$(git -C "$SK_DIR" config --get remote.origin.url 2>/dev/null)" in
    https://github.com/aleksandark-bot/seo-knowledge-skill|https://github.com/aleksandark-bot/seo-knowledge-skill.git) return 0 ;;
  esac
  return 1
}
sk_safe() { # nothing in flight, nothing local that a pull could touch
  local gd="$SK_DIR/.git" f
  for f in index.lock rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD BISECT_LOG; do
    [ -e "$gd/$f" ] && return 1
  done
  if command -v pgrep >/dev/null 2>&1 \
     && pgrep -f 'seo-universal/(rebuild-all|publish-skill)|doctrine-update\.sh' >/dev/null 2>&1; then
    return 1
  fi
  [ "$(git -C "$SK_DIR" symbolic-ref -q --short HEAD 2>/dev/null)" = main ] || return 1
  [ -z "$(git -C "$SK_DIR" status --porcelain 2>/dev/null)" ] || return 1
  git -C "$SK_DIR" rev-parse -q --verify HEAD >/dev/null 2>&1 || return 1
  return 0
}
sk_fetch() { # $1 = token or empty. `git fetch origin main`, killed after 120 s
  local hdr="" pid rc=0 n=0
  if [ -n "${1:-}" ]; then
    hdr="$(printf 'x-access-token:%s' "$1" | base64 2>/dev/null | tr -d '\n\r')"
    [ -n "$hdr" ] || return 1
  fi
  (
    # Never prompt: no terminal, no askpass, no credential helper (Git Credential Manager
    # would open a browser window for a private repo it has no login for).
    export GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never GIT_ASKPASS=true SSH_ASKPASS=true \
           GIT_HTTP_LOW_SPEED_LIMIT=1000 GIT_HTTP_LOW_SPEED_TIME=30
    if [ -n "$hdr" ]; then
      exec git -C "$SK_DIR" -c credential.helper= \
        -c "http.https://github.com/.extraheader=AUTHORIZATION: basic $hdr" \
        fetch -q --no-tags origin main
    else
      exec git -C "$SK_DIR" -c credential.helper= fetch -q --no-tags origin main
    fi
  ) &
  pid=$!
  while kill -0 "$pid" 2>/dev/null; do
    n=$((n + 1))
    if [ "$n" -gt 120 ]; then kill "$pid" 2>/dev/null; break; fi
    sleep 1
  done
  wait "$pid" 2>/dev/null || rc=$?
  return "$rc"
}
sk_pull() {
  local now last new
  sk_git_ok || return 0
  now="$(date +%s 2>/dev/null)"
  case "$now" in ''|*[!0-9]*) return 0 ;; esac
  last="$(cat "$SK_STAMP" 2>/dev/null)"
  case "$last" in ''|*[!0-9]*) last=0 ;; esac
  # Throttle; a stamp from the future (clock moved back) counts as due.
  if [ "$last" -le "$now" ] && [ $((now - last)) -lt 3600 ]; then return 0; fi
  # One puller at a time (two sessions opening together); a lock older than 10 min is stale.
  if ! mkdir "$SK_LOCK" 2>/dev/null; then
    [ -n "$(find "$SK_LOCK" -maxdepth 0 -mmin +10 2>/dev/null)" ] || return 0
    rmdir "$SK_LOCK" 2>/dev/null; mkdir "$SK_LOCK" 2>/dev/null || return 0
  fi
  trap 'rmdir "$SK_LOCK" 2>/dev/null' EXIT
  printf '%s\n' "$now" > "$SK_STAMP" 2>/dev/null || true
  sk_origin_ok || return 0
  sk_safe || return 0
  if [ -n "$TOKEN" ] && sk_fetch "$TOKEN"; then :
  elif sk_fetch ""; then :
  else return 0
  fi
  new="$(git -C "$SK_DIR" rev-parse -q --verify FETCH_HEAD 2>/dev/null)" || return 0
  [ -n "$new" ] || return 0
  [ "$new" = "$(git -C "$SK_DIR" rev-parse -q --verify HEAD 2>/dev/null)" ] && return 0
  sk_safe || return 0   # re-check: the fetch took time
  # Behind, not ahead or diverged: HEAD must be an ancestor of what was fetched.
  git -C "$SK_DIR" merge-base --is-ancestor HEAD "$new" 2>/dev/null || return 0
  git -C "$SK_DIR" merge -q --ff-only "$new" 2>/dev/null || return 0
  return 0
}
if [ -z "${FF_SELFUPDATED:-}" ] && [ -d "$SK_DIR/.git" ]; then
  ( sk_pull ) </dev/null >/dev/null 2>&1 &
fi

# 1. Latest commit on main. Bail quietly if we can't reach GitHub at all. No -f: the HTTP
#    status is what tells "no access" apart from "offline", so it is captured on the last
#    line of the output and the body is everything above it.
check() { # sets $code and $body; "$@" = extra curl args (the auth header, or nothing)
  local resp
  resp="$(curl -sSL --max-time 8 -H 'Accept: application/vnd.github+json' "$@" \
    -w '\n%{http_code}' "$API" 2>/dev/null)" || return 1
  code="${resp##*$'\n'}"
  body="${resp%$'\n'*}"
}
code="" body=""
check ${AUTH[@]+"${AUTH[@]}"} || exit 0
if [ -n "$TOKEN" ]; then
  case "$code" in
    401|403|404)
      # A rate limit is also a 403. That is not an access problem and passes on its own, so
      # it stays silent like any other transient failure.
      case "$body" in *[Rr]ate\ limit*) exit 0 ;; esac
      # Otherwise GitHub refused the token: 401 when it is expired or revoked, 403 or 404
      # when it no longer covers this repo. While the repo is public it still answers
      # without one, so a stale token must not stop updates: retry once unauthenticated
      # and, if that works, carry on without the token for the rest of this run (files
      # then come from raw, as before).
      refused="$code"
      if check && [ "$code" = 200 ]; then
        echo "factcheck-flow: GitHub refused the token this machine uses (HTTP $refused) — it has probably expired. Updates still work for now, but ask David for a new one, then re-run the install command from his message."
        TOKEN=""
        AUTH=()
        export FF_TOKEN_REFUSED=1
      else
        # Refused with the token and not readable without it: that is the paused case,
        # whatever the retry itself answered (the refusal is the part the user can act on).
        echo "factcheck-flow: updates paused — GitHub refused the token this machine uses (HTTP $refused). Ask David for a new one, then re-run the install command from his message."
        exit 0
      fi ;;
  esac
fi
case "$code" in
  200) ;;
  401|403|404)
    # Only a tokenless machine gets here: every tokened refusal was handled above.
    case "$body" in *[Rr]ate\ limit*) exit 0 ;; esac
    echo "factcheck-flow: updates paused — this machine has no repo token. Re-run the install command from David's message (it includes the token)."
    exit 0 ;;
  *) exit 0 ;;
esac
remote_sha="$(printf '%s\n' "$body" | grep -m1 '"sha"' \
  | sed -E 's/.*"sha"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/')"
[ -n "${remote_sha:-}" ] || exit 0
case "$remote_sha" in *[!0-9a-f]*) exit 0 ;; esac

# Download one repo file ($1, repo-relative) to $2. With a token: the Contents API's raw
# media type, pinned to $remote_sha — documented to take a fine-grained token on a private
# repo, answers a refused one with 401 rather than raw.githubusercontent's ambiguous 404,
# serves files up to 100 MB, and gives one consistent snapshot with no branch cache.
# Without a token: raw.githubusercontent, unauthenticated, exactly as before — it costs no
# API quota, and the unauthenticated API allowance (60/hour) is shared by the whole office IP.
urlpath() { # percent-encode a repo path, keeping "/" and the RFC 3986 unreserved set
  local LC_ALL=C s="$1" out="" c   # C locale: one byte per step, so UTF-8 encodes right
  while [ -n "$s" ]; do
    c="${s%"${s#?}"}"; s="${s#?}"
    case "$c" in
      [A-Za-z0-9._~/-]) out="$out$c" ;;
      *) out="$out$(printf '%%%02X' $(( $(printf '%d' "'$c") & 255 )))" ;;   # & 255: 3.2 sign-extends
    esac
  done
  printf '%s' "$out"
}
# curl runs without -f so the status code can be read, which means a non-zero exit is a
# transport failure — most often --max-time firing mid-body AFTER a 200 header. The write-out
# still says 200 then, so the exit status is the only thing that catches a truncated file.
RAW_PIN="https://raw.githubusercontent.com/$REPO/$remote_sha"
# get() sets GET_CODE to the HTTP status (000 when the request never completed), so fetch()
# can tell "this file is not in the repo" (404) apart from a failed download.
GET_CODE=""
get() { # $1 = repo-relative path, $2 = output file; 0 only for a clean 200
  local w ct
  if [ -n "$TOKEN" ]; then
    w="$(curl -sSL --max-time 8 ${AUTH[@]+"${AUTH[@]}"} -H 'Accept: application/vnd.github.raw' \
      -w '%{http_code} %{content_type}' "$CONTENTS/$(urlpath "$1")?ref=$remote_sha" \
      -o "$2" 2>/dev/null)" || { GET_CODE=000; return 1; }
  else
    # Pinned to the commit, not the branch: raw's CDN caches branch refs for minutes, and a
    # sync that records $remote_sha must have fetched $remote_sha's files.
    w="$(curl -sSL --max-time 8 -w '%{http_code} %{content_type}' "$RAW_PIN/$1" -o "$2" \
      2>/dev/null)" || { GET_CODE=000; return 1; }
  fi
  GET_CODE="${w%% *}"
  [ -n "$GET_CODE" ] || GET_CODE=000
  [ "$GET_CODE" = 200 ] || return 1
  if [ -n "$TOKEN" ]; then
    # The raw media type comes back as application/vnd.github.raw. application/json is
    # GitHub's JSON wrapper (metadata + base64) — never the file itself, so a failed fetch.
    ct="$(printf '%s' "${w#* }" | tr '[:upper:]' '[:lower:]')"
    case "$ct" in application/json|application/json\;*|application/json\ *) return 1 ;; esac
  fi
  return 0
}

# 2. Nothing new since last sync? Do nothing (this is what protects unpushed edits).
if [ -f "$STATE" ] && [ "$(cat "$STATE" 2>/dev/null)" = "$remote_sha" ]; then
  exit 0
fi

# 2b. Self-update: pull the latest copy of THIS script first, so changes to the
#     updater itself — including new files added to the fetch lists below (e.g. a
#     newly added guide) — propagate without a manual reinstall. Safe by design:
#       - Guarded by FF_SELFUPDATED so the re-exec can't loop.
#       - Only acts on a validated download (non-empty, has a shebang, is actually
#         our updater, ends on its final `exit 0` so a truncated copy is refused), and
#         only re-execs when the copy genuinely changed.
#       - On any failure it falls through to run the current copy unchanged.
SELF="$FF/update.sh"
if [ -z "${FF_SELFUPDATED:-}" ]; then
  tmp_self="$(mktemp 2>/dev/null || true)"
  if [ -n "${tmp_self:-}" ] \
     && get update.sh "$tmp_self" \
     && [ -s "$tmp_self" ] \
     && head -1 "$tmp_self" 2>/dev/null | grep -q '^#!' \
     && grep -q 'factcheck-flow auto-updater' "$tmp_self" \
     && [ "$(tail -n 1 "$tmp_self" 2>/dev/null)" = "exit 0" ] \
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
#    non-empty download so a partial fetch never truncates a good local file. FAILS counts
#    every file that did not land: step 4 records the sync only when it is zero, so a run
#    that lost a file (network blip, refused token) is retried next session instead of
#    being marked done and skipped until the next push. A 404 is not a loss: the file is
#    simply not in the repo at this commit.
FAILS=0
fetch() { # $1 = repo-relative path, $2 = local destination
  local tmp
  tmp="$(mktemp 2>/dev/null)" || { FAILS=$((FAILS + 1)); return 0; }
  if get "$1" "$tmp" && [ -s "$tmp" ]; then
    mkdir -p "$(dirname "$2")" 2>/dev/null || true
    if ! mv "$tmp" "$2" 2>/dev/null; then
      rm -f "$tmp" 2>/dev/null || true
      FAILS=$((FAILS + 1))
    fi
  else
    rm -f "$tmp" 2>/dev/null || true
    # A 404 on a run whose commit check succeeded means the file is not in the repo at this
    # commit (retired, or not added yet): nothing to download, so not a failure. Counting it
    # would block STATE forever and re-download every file every session.
    [ "$GET_CODE" = 404 ] || FAILS=$((FAILS + 1))
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

# 4. Remember the commit we're now in sync with — but only if every file above arrived.
#    Otherwise leave STATE alone so the next session tries again.
if [ "$FAILS" -eq 0 ]; then
  printf '%s\n' "$remote_sha" > "$STATE" 2>/dev/null || true
fi
exit 0
