#!/usr/bin/env bash
#
# factcheck-flow installer (no plugin system required)
# Installs the /fact command, its two agents, the WordPress skill,
# and the three prompt files into ~/.claude/ — works in Claude Code setups
# where the plugin system is disabled.
#
# Run it with:
# While the repo is public:
#   bash <(curl -fsSL https://raw.githubusercontent.com/aleksandark-bot/factcheck-flow-plugin/main/install.sh)
# Once it is private (token from David) — download first, then run, so a refused token
# stops with curl's error instead of handing bash an empty script:
#   export PABAU_REPO_TOKEN=<token>
#   curl -fsSL -H "Authorization: Bearer $PABAU_REPO_TOKEN" -H "Accept: application/vnd.github.raw" https://api.github.com/repos/aleksandark-bot/factcheck-flow-plugin/contents/install.sh -o /tmp/ff-install.sh && bash /tmp/ff-install.sh
#
# Either form keeps the terminal on stdin, which the installer's questions need. Never
# `curl ... | bash`: a piped script has no terminal to ask them on.
#
set -euo pipefail

REPO_RAW="https://raw.githubusercontent.com/aleksandark-bot/factcheck-flow-plugin/main"
CLAUDE="$HOME/.claude"
FF="$CLAUDE/factcheck-flow"
PROMPTS="$FF/prompts"
GUIDES="$FF/guides"
CREDS="$FF/wp-credentials"

# --- interactive prompts, safe on a pipe ----------------------------------
# Every prompt below is optional ("blank to skip"). Under `set -e` a bare `read` that hits
# EOF — a piped install, CI, `bash <(curl ...) < /dev/null` — returns non-zero and kills the
# installer at the FIRST prompt, so the cluster-store token and, worse, the first
# `cluster_sync.py pull` never run and the machine ends up with no cluster data at all.
# These two helpers answer "" on a non-interactive run instead, so the install takes every
# skip branch and still reaches the steps that need no input.
INTERACTIVE=1
[ -t 0 ] || INTERACTIVE=0

ask() {          # ask VAR "prompt text"
  local __var="$1" __prompt="$2" __ans=""
  if [ "$INTERACTIVE" = 1 ]; then
    read -r -p "$__prompt" __ans || __ans=""
  else
    printf '%s(no terminal — skipped)\n' "$__prompt"
  fi
  printf -v "$__var" '%s' "$__ans"
}

ask_secret() {   # ask_secret VAR "prompt text"  — never echoes what is typed
  local __var="$1" __prompt="$2" __ans=""
  if [ "$INTERACTIVE" = 1 ]; then
    read -r -s -p "$__prompt" __ans || __ans=""
    echo ""
  else
    printf '%s(no terminal — skipped)\n' "$__prompt"
  fi
  printf -v "$__var" '%s' "$__ans"
}

# A real python3 on PATH. On macOS /usr/bin/python3 is an installer stub until the Command
# Line Tools are there — running it pops an "install developer tools" dialog and fails — so
# on a Mac that one path counts only once xcode-select points at a developer dir holding a
# real python3. Homebrew / python.org pythons live elsewhere and are used as is.
py_ok() {
  local p dev
  p="$(command -v python3 2>/dev/null || true)"
  [ -n "$p" ] || return 1
  if [ "$(uname -s 2>/dev/null)" = Darwin ] && [ "$p" = /usr/bin/python3 ]; then
    dev="$(xcode-select -p 2>/dev/null || true)"
    [ -n "$dev" ] && [ -x "$dev/usr/bin/python3" ] || return 1
  fi
  return 0
}
py_stub_note() { # $1 = what was skipped. Only says something when python3 is the Mac stub
  if command -v python3 >/dev/null 2>&1 && ! py_ok; then
    echo "  NOTE: $1 skipped — python3 needs the Mac developer tools. Run  xcode-select --install ,"
    echo "        then re-run this installer."
  fi
}

echo ""
echo "  Installing factcheck-flow into $CLAUDE ..."
echo ""

mkdir -p "$CLAUDE/commands" "$CLAUDE/agents" "$CLAUDE/skills/wordpress-access" "$PROMPTS" "$GUIDES" "$FF/bin"

# --- 0. The repo token (read-only; optional while the repo is public) -----
# Once the repo is private, every download below and every auto-update needs it. Looked up
# in the same order the updater uses: $PABAU_REPO_TOKEN, then an existing $FF/.repo-token,
# then the cluster write token ($PABAU_CLUSTERS_TOKEN, then $FF/.clusters-token —
# contents:write can read too). A token typed here or passed in $PABAU_REPO_TOKEN is saved
# to $FF/.repo-token (mode 600, covered by .gitignore) so the auto-updater finds it — but
# only once GitHub has accepted it. It is never echoed or printed.
_tok() { printf '%s' "${1:-}" | tr -d '[:space:]'; }
REPO_TOKEN="$(_tok "${PABAU_REPO_TOKEN:-}")"
TOKEN_SRC=""
SAVE_REPO_TOKEN=0
if [ -n "$REPO_TOKEN" ]; then
  TOKEN_SRC="the PABAU_REPO_TOKEN environment variable"; SAVE_REPO_TOKEN=1
fi
if [ -z "$REPO_TOKEN" ]; then
  REPO_TOKEN="$(_tok "$(cat "$FF/.repo-token" 2>/dev/null || true)")"
  [ -n "$REPO_TOKEN" ] && TOKEN_SRC="$FF/.repo-token"
fi
if [ -z "$REPO_TOKEN" ]; then
  REPO_TOKEN="$(_tok "${PABAU_CLUSTERS_TOKEN:-}")"
  [ -n "$REPO_TOKEN" ] && TOKEN_SRC="the PABAU_CLUSTERS_TOKEN environment variable (the cluster write token)"
fi
if [ -z "$REPO_TOKEN" ]; then
  REPO_TOKEN="$(_tok "$(cat "$FF/.clusters-token" 2>/dev/null || true)")"
  [ -n "$REPO_TOKEN" ] && TOKEN_SRC="$FF/.clusters-token (the cluster write token)"
fi
if [ -z "$REPO_TOKEN" ] && [ "$INTERACTIVE" = 1 ]; then
  echo "  The repo token David sent lets this machine download the tool and its updates."
  ask_secret REPO_TOKEN_IN "  Repo token (blank is fine while the repo is still public): "
  REPO_TOKEN="$(_tok "${REPO_TOKEN_IN:-}")"
  unset REPO_TOKEN_IN
  if [ -n "$REPO_TOKEN" ]; then
    TOKEN_SRC="the token you typed"; SAVE_REPO_TOKEN=1
  fi
fi

# How the downloads below reach the repo — the same rule the auto-updater follows:
#   * With a token, ONE up-front probe of the commits API decides. Accepted (200): every
#     download goes through the Contents API raw type with the token, pinned to the commit
#     the probe returned. Refused (401/403/404): the probe is retried without the token; if
#     the repo still answers (it is public), the install warns once and carries on through
#     raw.githubusercontent unauthenticated, and the refused token is not saved. If it does
#     not answer either, the install stops and says where the refused token came from.
#   * Without a token: raw.githubusercontent unauthenticated, exactly as before, with no
#     probe — it costs no API quota, and the office IP's 60/hour unauthenticated allowance
#     is often used up.
# A token is never sent to raw.githubusercontent: it answers a refused token with 404 even
# on a public repo, which is what used to abort this installer over a stale token.
REPO="aleksandark-bot/factcheck-flow-plugin"
REPO_API="https://api.github.com/repos/$REPO"
DL_MODE=raw
DL_SHA=""

PROBE_CODE="" PROBE_BODY=""
probe() { # probe [token] — sets PROBE_CODE ("000" = never completed) and PROBE_BODY
  local resp=""
  if [ -n "${1:-}" ]; then
    resp="$(curl -sSL --max-time 15 -H 'Accept: application/vnd.github+json' \
      -H "Authorization: Bearer $1" -w '\n%{http_code}' "$REPO_API/commits/main" 2>/dev/null)" || true
  else
    resp="$(curl -sSL --max-time 15 -H 'Accept: application/vnd.github+json' \
      -w '\n%{http_code}' "$REPO_API/commits/main" 2>/dev/null)" || true
  fi
  PROBE_CODE="${resp##*$'\n'}"
  PROBE_BODY="${resp%$'\n'*}"
  case "$PROBE_CODE" in [0-9][0-9][0-9]) ;; *) PROBE_CODE=000 ;; esac
}
is_rate_limited() { case "$PROBE_BODY" in *[Rr]ate\ limit*) return 0 ;; esac; return 1; }
probe_sha() {
  printf '%s\n' "$PROBE_BODY" | grep -m1 '"sha"' \
    | sed -E 's/.*"sha"[[:space:]]*:[[:space:]]*"([^"]+)".*/\1/' || true
}
# Can the repo be read with no token at all? The unauthenticated commits API first; if the
# office IP has used up its API allowance, raw.githubusercontent decides instead (it costs
# no quota and, unauthenticated, only answers 200 on a public repo).
repo_is_public() {
  probe
  [ "$PROBE_CODE" = 200 ] && return 0
  if [ "$PROBE_CODE" = 403 ] && is_rate_limited; then
    curl -fsSL --max-time 15 -o /dev/null \
      "https://raw.githubusercontent.com/$REPO/main/install.sh" 2>/dev/null && return 0
  fi
  return 1
}
token_refused_stop() { # $1 = the HTTP code the token got
  echo "" >&2
  echo "  ERROR: GitHub refused the repo token (HTTP $1), and the repo cannot be read without" >&2
  echo "         one. The token has probably expired or been revoked. It came from" >&2
  echo "         $TOKEN_SRC." >&2
  echo "         Ask David for a new one, then re-run the install command from his message." >&2
  exit 1
}

if [ -n "$REPO_TOKEN" ]; then
  probe "$REPO_TOKEN"
  case "$PROBE_CODE" in
    200)
      DL_SHA="$(probe_sha)"
      case "$DL_SHA" in
        ""|*[!0-9a-f]*)
          echo "  ERROR: GitHub answered the repo check with something unexpected. Re-run the" >&2
          echo "         install command in a minute." >&2
          exit 1 ;;
      esac
      DL_MODE=api ;;
    401|403|404)
      if [ "$PROBE_CODE" = 403 ] && is_rate_limited; then
        # The token was accepted but its hourly API allowance is used up. Not a refusal:
        # keep (and save) the token, and download without it if the repo allows that.
        if repo_is_public; then
          echo "  NOTE: GitHub's hourly limit for the repo token is used up — downloading without"
          echo "        it (the repo is still public). The token is kept for the auto-updater."
        else
          echo "  ERROR: GitHub's hourly limit for the repo token is used up. Re-run the install" >&2
          echo "         command in an hour." >&2
          exit 1
        fi
      else
        refused="$PROBE_CODE"
        if repo_is_public; then
          echo "  WARNING: GitHub refused the token this machine has — continuing without it;"
          echo "           ask David for a new one and re-run the install command from his message."
          echo "           It came from $TOKEN_SRC."
          SAVE_REPO_TOKEN=0
          REPO_TOKEN=""
        else
          token_refused_stop "$refused"
        fi
      fi ;;
    *)
      echo "  ERROR: could not reach GitHub to check the repo token (HTTP $PROBE_CODE). Check your" >&2
      echo "         internet connection, then re-run the install command." >&2
      exit 1 ;;
  esac
fi
if [ "$SAVE_REPO_TOKEN" = 1 ]; then
  # Subshell, so the umask never leaks into the rest of the installer.
  ( umask 077; printf '%s\n' "$REPO_TOKEN" > "$FF/.repo-token" )
  chmod 600 "$FF/.repo-token"
  echo "  - repo token saved (readable only by you) to $FF/.repo-token"
fi

# percent-encode a repo path, keeping "/" and the RFC 3986 unreserved set — the same
# function as the auto-updater's (bash-3.2-safe).
urlpath() {
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

# Every download from the repo goes through this: gh_get <repo-relative path> <output file>.
# No array, so it is safe under `set -u` on macOS's bash 3.2. A Contents-API answer typed
# application/json is GitHub's JSON wrapper, never the file (the raw type comes back as
# application/vnd.github.raw), so it counts as a failed download and is not left on disk.
gh_get() {
  local ct=""
  if [ "$DL_MODE" = api ]; then
    ct="$(curl -fsSL -H "Authorization: Bearer $REPO_TOKEN" -H 'Accept: application/vnd.github.raw' \
      -w '%{content_type}' "$REPO_API/contents/$(urlpath "$1")?ref=$DL_SHA" -o "$2")" || return 1
    ct="$(printf '%s' "$ct" | tr '[:upper:]' '[:lower:]')"
    case "$ct" in
      application/json|application/json\;*|application/json\ *) rm -f "$2"; return 1 ;;
    esac
    return 0
  fi
  curl -fsSL "$REPO_RAW/$1" -o "$2"
}

# Why a required download failed, for the ERROR lines below.
dl_fail_hint() {
  if [ "$DL_MODE" = api ]; then
    echo "         Check your internet connection and re-run the install command." >&2
  elif [ -n "$TOKEN_SRC" ] && [ -z "$REPO_TOKEN" ]; then
    echo "         Check your internet connection. If the repo has just gone private, the" >&2
    echo "         token from $TOKEN_SRC no longer works:" >&2
    echo "         ask David for a new one, then re-run the install command from his message." >&2
  else
    echo "         Check your internet connection. If the repo is now private, rerun with the" >&2
    echo "         repo token David sent:" >&2
    echo '           export PABAU_REPO_TOKEN=<token>' >&2
    echo '           curl -fsSL -H "Authorization: Bearer $PABAU_REPO_TOKEN" -H "Accept: application/vnd.github.raw" https://api.github.com/repos/aleksandark-bot/factcheck-flow-plugin/contents/install.sh -o /tmp/ff-install.sh && bash /tmp/ff-install.sh' >&2
  fi
}

# --- 1. Download the editable prompt files from the repo -------------------
for p in 1-factcheck 2-editorial 3-links seo-research seo-write generate-research generate-write; do
  if ! gh_get "prompts/$p.md" "$PROMPTS/$p.md"; then
    echo "  ERROR: could not download prompts/$p.md." >&2
    dl_fail_hint
    exit 1
  fi
done
echo "  - prompts installed"

# --- 1a. The GSC query helper (used by /SEO on published articles) --------
if gh_get "bin/gsc_query.py" "$FF/bin/gsc_query.py"; then
  chmod +x "$FF/bin/gsc_query.py" 2>/dev/null || true
  echo "  - GSC helper installed"
else
  echo "  NOTE: could not download bin/gsc_query.py — /SEO's GSC step will be unavailable." >&2
fi
if gh_get "bin/keyword_picker.py" "$FF/bin/keyword_picker.py"; then
  chmod +x "$FF/bin/keyword_picker.py" 2>/dev/null || true
  echo "  - keyword picker installed"
else
  echo "  NOTE: could not download bin/keyword_picker.py — /SEO will use the in-chat picker." >&2
fi
if gh_get "bin/serp_picker.py" "$FF/bin/serp_picker.py"; then
  chmod +x "$FF/bin/serp_picker.py" 2>/dev/null || true
  echo "  - SERP picker installed"
else
  echo "  NOTE: could not download bin/serp_picker.py — /SEO will use the in-chat SERP list." >&2
fi
if gh_get "bin/dfs_lists.py" "$FF/bin/dfs_lists.py"; then
  chmod +x "$FF/bin/dfs_lists.py" 2>/dev/null || true
  echo "  - keyword-list builder installed"
else
  echo "  NOTE: could not download bin/dfs_lists.py — /SEO Stage 2 will have no helper." >&2
fi
if gh_get "bin/sentence_check.py" "$FF/bin/sentence_check.py"; then
  chmod +x "$FF/bin/sentence_check.py" 2>/dev/null || true
  echo "  - sentence checker installed"
else
  echo "  NOTE: could not download bin/sentence_check.py — the /fact sentence gate will be unavailable." >&2
fi
if gh_get "bin/serp_fetch.py" "$FF/bin/serp_fetch.py"; then
  chmod +x "$FF/bin/serp_fetch.py" 2>/dev/null || true
  echo "  - SERP fetcher installed"
else
  echo "  NOTE: could not download bin/serp_fetch.py — /SEO Stage 1 will have no helper." >&2
fi
if gh_get "bin/render_visual.py" "$FF/bin/render_visual.py"; then
  chmod +x "$FF/bin/render_visual.py" 2>/dev/null || true
  echo "  - visual renderer installed"
else
  echo "  NOTE: could not download bin/render_visual.py — /fact cannot build article visuals." >&2
fi
if gh_get "bin/cluster_lookup.py" "$FF/bin/cluster_lookup.py"; then
  chmod +x "$FF/bin/cluster_lookup.py" 2>/dev/null || true
  echo "  - cluster lookup installed"
else
  echo "  NOTE: could not download bin/cluster_lookup.py — /fact's link pass will be blocked." >&2
fi
# The central cluster store (clusters/CONTRACT.md). cluster_lookup.py IMPORTS
# cluster_store.py, so without these three the link pass has no data layer at all: no
# base.jsonl reader, no way to sync the branch, no way to write a reasoned assignment back.
for b in cluster_store cluster_sync cluster_consolidate; do
  if gh_get "bin/$b.py" "$FF/bin/$b.py"; then
    chmod +x "$FF/bin/$b.py" 2>/dev/null || true
  else
    echo "  NOTE: could not download bin/$b.py — /fact's link pass will be blocked." >&2
  fi
done
echo "  - cluster store installed"
if gh_get "bin/elementor_guard.py" "$FF/bin/elementor_guard.py"; then
  chmod +x "$FF/bin/elementor_guard.py" 2>/dev/null || true
  echo "  - Elementor guard installed"
else
  echo "  NOTE: could not download bin/elementor_guard.py — engine detection falls back to REST." >&2
fi
if gh_get "bin/gsc_cannibal.py" "$FF/bin/gsc_cannibal.py"; then
  chmod +x "$FF/bin/gsc_cannibal.py" 2>/dev/null || true
  echo "  - Keyword-ownership pre-flight installed"
else
  echo "  NOTE: could not download bin/gsc_cannibal.py — /SEO cannot check for cannibalization." >&2
fi
if gh_get "bin/index_ping.py" "$FF/bin/index_ping.py"; then
  chmod +x "$FF/bin/index_ping.py" 2>/dev/null || true
  echo "  - Re-crawl request helper installed"
else
  echo "  NOTE: could not download bin/index_ping.py — /SEO will skip the re-crawl request." >&2
fi

# --- 1b. Download the Pabau reference guides from the repo -----------------
# These define voice/terminology (Pabau-style-guide), product/positioning
# context (About-Pabau), and SERP title optimization (Meta-title-best-practices).
# The editorial prompt and factcheck-reporter read them.
for g in core-rules Pabau-style-guide About-Pabau Meta-title-best-practices Originality-and-search-intent WordPress-blocks Visuals; do
  if ! gh_get "guides/$g.md" "$GUIDES/$g.md"; then
    echo "  ERROR: could not download guides/$g.md." >&2
    dl_fail_hint
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
#     reach the repo, and a machine with a working token, both stay silent. Likewise one
#     line when GitHub refused the last SEO-knowledge skill fetch (step 0b).
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
#
#    On macOS /usr/bin/python3 is an installer stub until the Command Line Tools are there:
#    running it pops an "install developer tools" dialog, which here would be every session.
#    So on a Mac that one path is only run once xcode-select points at a developer dir that
#    holds a real python3. Homebrew / python.org pythons live elsewhere and are used as is.
ff_py_ok() { # a real python3 on PATH — never the macOS installer stub
  local p dev
  p="$(command -v python3 2>/dev/null)" || return 1
  [ -n "$p" ] || return 1
  if [ "$(uname -s 2>/dev/null)" = Darwin ] && [ "$p" = /usr/bin/python3 ]; then
    dev="$(xcode-select -p 2>/dev/null)" || return 1
    [ -n "$dev" ] && [ -x "$dev/usr/bin/python3" ] || return 1
  fi
  return 0
}
if [ -z "${FF_SELFUPDATED:-}" ] && ff_py_ok && [ -f "$FF/bin/cluster_sync.py" ]; then
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
#       - not the maintainer's machine. David publishes the skill FROM his checkout
#         (seo-universal/publish-skill.sh), so where that script exists this step does
#         nothing at all: no fetch racing his rebuilds or his own fetch/push;
#       - the directory is a git checkout whose origin is that repo (https, with or without .git);
#       - git is really there. On macOS /usr/bin/git is a stub that pops an "install developer
#         tools" dialog when the Command Line Tools are missing, so on a Mac that stub is only
#         run once xcode-select points at a developer dir that holds a real git;
#       - at most once an hour ($FF/.last-skill-pull), since sessions start often;
#       - no git operation in progress (index.lock, rebase, merge, cherry-pick), no maintainer
#         rebuild running, branch `main`, working tree clean, and the local branch not ahead of
#         the remote.
#     The token (when there is one) travels as a one-off http.extraheader scoped to
#     https://github.com/ — never written to .git/config, never in the remote URL, and on
#     git 2.31+ passed through the environment (GIT_CONFIG_COUNT) so it is not in `ps`
#     either. If the tokened fetch fails, one unauthenticated retry (a still-public repo, a
#     stale token). A user url.<ssh>.insteadOf rule is overridden for this one repo, so the
#     fetch stays on HTTPS with the token instead of going over SSH and maybe prompting.
#     When GitHub refuses access on every attempt, $FF/.skill-pull-status says `auth`, and
#     the next session prints one line about it (cleared by the next good fetch). Offline,
#     timeouts and other failures stay silent.
SK_DIR="$HOME/.claude/skills/SEO-knowledge"
SK_STAMP="$FF/.last-skill-pull"
SK_LOCK="$FF/.skill-pull.lock"
SK_STATUS="$FF/.skill-pull-status"
SK_PUBLISHER="$HOME/Desktop/temp/seo-universal/publish-skill.sh"
SK_PIN="url.https://github.com/aleksandark-bot/seo-knowledge-skill.insteadOf=https://github.com/aleksandark-bot/seo-knowledge-skill"
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
sk_git_ge() { # sk_git_ge MAJOR MINOR — the installed git is at least that version
  local v maj min
  v="$(git --version 2>/dev/null)"
  v="${v#git version }"
  maj="${v%%.*}"
  min="${v#*.}"; min="${min%%[!0-9]*}"
  case "$maj" in ''|*[!0-9]*) return 1 ;; esac
  [ -n "$min" ] || min=0
  [ "$maj" -gt "$1" ] && return 0
  [ "$maj" -eq "$1" ] && [ "$min" -ge "$2" ]
}
sk_origin_ok() {
  case "$(git -C "$SK_DIR" config --get remote.origin.url 2>/dev/null)" in
    https://github.com/aleksandark-bot/seo-knowledge-skill|https://github.com/aleksandark-bot/seo-knowledge-skill.git) return 0 ;;
  esac
  return 1
}
sk_safe() { # nothing in flight, nothing local that a pull could touch
  local gd="$SK_DIR/.git" f st
  for f in index.lock rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD BISECT_LOG; do
    [ -e "$gd/$f" ] && return 1
  done
  if command -v pgrep >/dev/null 2>&1 \
     && pgrep -f 'seo-universal/(rebuild-all|publish-skill)|doctrine-update\.sh' >/dev/null 2>&1; then
    return 1
  fi
  [ "$(git -C "$SK_DIR" symbolic-ref -q --short HEAD 2>/dev/null)" = main ] || return 1
  # GIT_OPTIONAL_LOCKS=0 is `git --no-optional-locks`: status must not take index.lock
  # (refreshing the index) under whatever else is using this checkout.
  st="$(GIT_OPTIONAL_LOCKS=0 git -C "$SK_DIR" status --porcelain 2>/dev/null)" || return 1
  [ -z "$st" ] || return 1
  git -C "$SK_DIR" rev-parse -q --verify HEAD >/dev/null 2>&1 || return 1
  return 0
}
sk_auth_err() { # $1 = a failed git's stderr. 0 when it says GitHub refused access
  [ -s "$1" ] || return 1
  grep -Eiq "authentication failed|repository '[^']*' not found|repository not found|could not read (username|password)|terminal prompts disabled|invalid username or (password|token)|returned error: 40[134]|HTTP 40[134]|permission denied \(publickey" "$1"
}
sk_fetch() { # $1 = token or empty, $2 = stderr file. Killed (whole process group) after 120 s
  local hdr="" pid rc=0 n=0 env=0 i
  if [ -n "${1:-}" ]; then
    hdr="$(printf 'x-access-token:%s' "$1" | base64 2>/dev/null | tr -d '\n\r')"
    [ -n "$hdr" ] || return 1
    sk_git_ge 2 31 && env=1
  fi
  # `set -m` puts the job in its own process group (pgid = its pid), so the watchdog can
  # kill git AND its git-remote-https child, not just the parent.
  set -m
  (
    # Never prompt: no terminal, no askpass, no credential helper (Git Credential Manager
    # would open a browser window for a private repo it has no login for), no SSH prompt.
    export GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never GIT_ASKPASS=true SSH_ASKPASS=true \
           GIT_SSH_COMMAND='ssh -oBatchMode=yes' \
           GIT_HTTP_LOW_SPEED_LIMIT=1000 GIT_HTTP_LOW_SPEED_TIME=30
    set -- -C "$SK_DIR" -c credential.helper= -c "$SK_PIN" -c gc.auto=0 -c maintenance.auto=false \
      fetch -q --no-tags
    sk_git_ge 2 29 && set -- "$@" --no-write-fetch-head
    set -- "$@" origin +refs/heads/main:refs/remotes/origin/main
    if [ -n "$hdr" ] && [ "$env" = 1 ]; then
      # Off argv: config from the environment (git 2.31+), appended to any the user has.
      i="${GIT_CONFIG_COUNT:-0}"
      case "$i" in ''|*[!0-9]*) i=0 ;; esac
      export "GIT_CONFIG_KEY_$i=http.https://github.com/.extraheader" \
             "GIT_CONFIG_VALUE_$i=AUTHORIZATION: basic $hdr" "GIT_CONFIG_COUNT=$((i + 1))"
      exec git "$@"
    elif [ -n "$hdr" ]; then
      exec git -c "http.https://github.com/.extraheader=AUTHORIZATION: basic $hdr" "$@"
    else
      exec git "$@"
    fi
  ) </dev/null >/dev/null 2>"$2" &
  pid=$!
  set +m
  trap 'kill -TERM -- "-$pid" 2>/dev/null; exit 1' INT TERM HUP   # our own group goes with us
  while kill -0 "$pid" 2>/dev/null; do
    n=$((n + 1))
    if [ "$n" -gt 120 ]; then
      kill -TERM -- "-$pid" 2>/dev/null
      n=0
      while kill -0 "$pid" 2>/dev/null && [ "$n" -lt 5 ]; do sleep 1; n=$((n + 1)); done
      kill -KILL -- "-$pid" 2>/dev/null
      break
    fi
    sleep 1
  done
  { wait "$pid"; } 2>/dev/null || rc=$?
  trap - INT TERM HUP
  return "$rc"
}
sk_pull() {
  local now last new err ok=0 tauth=1
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
    rm -rf "$SK_LOCK" 2>/dev/null; mkdir "$SK_LOCK" 2>/dev/null || return 0
  fi
  trap 'rm -rf "$SK_LOCK" 2>/dev/null' EXIT
  printf '%s\n' "$now" > "$SK_STAMP" 2>/dev/null || true
  sk_origin_ok || return 0
  sk_safe || return 0
  err="$SK_LOCK/err"
  if [ -n "$TOKEN" ]; then
    if sk_fetch "$TOKEN" "$err"; then ok=1
    else sk_auth_err "$err" || tauth=0
    fi
  fi
  if [ "$ok" = 0 ]; then
    if sk_fetch "" "$err"; then ok=1
    else
      # Refused on every attempt → tell the next session. Anything else stays silent.
      if [ "$tauth" = 1 ] && sk_auth_err "$err"; then
        printf 'auth\n' > "$SK_STATUS" 2>/dev/null || true
      fi
      return 0
    fi
  fi
  rm -f "$SK_STATUS" 2>/dev/null
  new="$(git -C "$SK_DIR" rev-parse -q --verify refs/remotes/origin/main 2>/dev/null)" || return 0
  [ -n "$new" ] || return 0
  [ "$new" = "$(git -C "$SK_DIR" rev-parse -q --verify HEAD 2>/dev/null)" ] && return 0
  sk_safe || return 0   # re-check: the fetch took time
  # Behind, not ahead or diverged: HEAD must be an ancestor of what was fetched.
  git -C "$SK_DIR" merge-base --is-ancestor HEAD "$new" 2>/dev/null || return 0
  git -C "$SK_DIR" -c gc.auto=0 -c maintenance.auto=false merge -q --ff-only "$new" 2>/dev/null || return 0
  return 0
}
if [ -z "${FF_SELFUPDATED:-}" ] && [ -d "$SK_DIR/.git" ] && [ ! -e "$SK_PUBLISHER" ]; then
  if [ "$(cat "$SK_STATUS" 2>/dev/null)" = auth ]; then
    echo "factcheck-flow: SEO-knowledge updates paused — GitHub refused access. Re-run the install command from David's message."
  fi
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
  tagged with its article. One `AUTO` type is a signal rather than a fix: a `code-state` line
  (it carries `CODE_PAGE_HALF_MIGRATED`) names a page the flow deliberately leaves alone. Pass
  it through verbatim like the rest, and note its article for the once-per-run list in the
  final report.
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
fact-check fixes → editorial → link pass → block guarantees) in memory, and writes
everything back in a SINGLE save via the `wordpress-access` skill. They do not ask
further questions.

The link pass (`3-links.md`) resolves each article's content cluster from the central
cluster store — read at runtime by `bin/cluster_lookup.py`, which merges the synced
`clusters-data` files with the local workbook where one exists — and links only inside that
cluster, at most five in-body editorial links (three on a code page). It ends in its own
mechanical gate, so expect the gate's `PASS | 0 checks failed` line back on every `Links:`
line, the same way Pass E reports the sentence gate. An editor that reports
`LINKPLAN_BLOCKED — no cluster store` could reach neither the synced files nor a local
workbook: that is a setup problem to relay, not a reason to re-run the article with links
improvised. A missing workbook on its own is normal and blocks nothing.

The block-guarantee pass ALWAYS runs last and enforces the contract in
`~/.claude/factcheck-flow/guides/WordPress-blocks.md` — required document order plus the
always-on guarantees (an original visual, a featured image on a blog article that has none,
Key takeaways, template download box, Pabau section + CTA block, Conclusion, Continue your
research, Yoast FAQ, listicle pricing segments, image captions). That file, `Visuals.md`, and
the article-editor's own Pass D own the detail; you are the orchestrator and never perform this work, so do not restate the
contract to the subagents — they read it themselves.

That pass opens with **D0 — visuals**: every article gets at least one original
visualization we built, either a rendered image (HTML → WebP, uploaded to the media library)
or one CSS-only interactive block. The contract is
`~/.claude/factcheck-flow/guides/Visuals.md` and the editor reads it itself. You never pick
the visual, never design it, and never ask the user about it — it is unconditional, like the
other guarantees. Expect a `Visuals:` line back from every editor.

**D0b — featured image** follows it, and only on a blog article whose featured image slot is
empty: the editor renders a 1200 × 630 brand card from the same guide (§11), uploads it, and
attaches it with `featured_media` in the one save. It never replaces an existing featured
image, never touches a template or code article, and never puts the card in the body. Same
standing as D0 — you don't design it, don't second-guess which article qualifies, and don't
ask the user. Expect a `Featured image:` line back from every editor, including the
"already had one" and "not a blog article" cases.

After that, and before the single save, each editor must clear the **sentence gate** (Pass E):
`bin/sentence_check.py` counts every sentence in the body and the editor rewrites until the
script exits 0 — nothing over 30 words ships, and 26–30 needs a per-sentence justification.
Sentence length is measured by script precisely because it cannot be eyeballed. Every editor
reports the checker's final summary line verbatim; an article whose change-log has no
`Sentence gate:` line did not run it, and that is a failed job worth flagging in your report.

## Final report

Once all Stage 3 subagents return, compile a single consolidated summary for the user.
Each editor returns a compact change-log; relay it, don't re-derive it. Per article:
fact-check fixes applied, editorial highlights, link changes, a `Code page:` line (one of the
four states — templated, broken (with the `pdc_*` fields that were filled), half-migrated, or old
shape — plus any `pdc_*` values corrected; "not a code page" where it isn't one; the
half-migrated articles themselves go in the once-per-run block below, not per article), the visual that was built
(route, what it shows, media id or `pv-viz` class), whether a featured image was built,
already there, or not applicable, the one-line block-contract status the
editor reported for each of the other guarantees, the sentence gate's summary line
(longest sentence + how many were rewritten), and anything skipped. Note
any article whose grave error was flagged but dropped after independent verification, and
any article that hit the two-rewrite ceiling and needs manual attention. Collect the
link-pass findings that are about OTHER pages and list them once for the user rather than per
article: merge candidates from close-variant pairs, BOFU articles that need inbound boosts,
`NO_BOFU_IN_CLUSTER` clusters, and any `BLOCKED_PILLAR` or `BLOCKED_ELEMENTOR` article. List
every `CODE_PAGE_HALF_MIGRATED` article in that same once-per-run block — sourced from a
Stage 1 `code-state` line, an editor's `Code page:` line, or both, listed once each rather than
per article: the flow deliberately leaves those alone — they need David's migration process,
not an edit. End with
the reminder to purge the WP Rocket cache for each edited URL, plus — once for the whole run,
not per article — refreshing the link atlas (`cd ~/Desktop/linkmap && ./refresh.sh`) so the next
run's inbound counts include what this one changed.
EOF
echo "  - /fact command installed"

# --- 2b. The /SEO command -------------------------------------------------
if gh_get "commands/SEO.md" "$CLAUDE/commands/SEO.md"; then
  echo "  - /SEO command installed"
  if gh_get "agents/seo-writer.md" "$CLAUDE/agents/seo-writer.md"; then
    echo "  - seo-writer agent installed"
  else
    echo "  NOTE: could not download agents/seo-writer.md — /SEO cannot write without it." >&2
  fi
else
  echo "  ERROR: could not download commands/SEO.md." >&2
  dl_fail_hint
  exit 1
fi

# --- 2c. The /generate command --------------------------------------------
if gh_get "commands/generate.md" "$CLAUDE/commands/generate.md"; then
  echo "  - /generate command installed"
  if gh_get "agents/article-generator.md" "$CLAUDE/agents/article-generator.md"; then
    echo "  - article-generator agent installed"
  else
    echo "  NOTE: could not download agents/article-generator.md — /generate cannot write without it." >&2
  fi
else
  echo "  ERROR: could not download commands/generate.md." >&2
  dl_fail_hint
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
skill — REST, `context=edit`, with that skill's `_fields=` list, which pulls `template` and
`meta` along with the body. Never WebFetch the public URL; the site's nav would consume most
of the response. Read only.

On a code page those two fields carry page-visible content that never appears in the body, so
check the `pdc_*` values per `1-factcheck.md` ("Code pages — the `pdc_*` meta is in scope").

Also read `~/.claude/factcheck-flow/guides/About-Pabau.md` and flag any statement that
contradicts it as a factual finding — e.g. claiming Pabau has a free trial, calling
online booking "Pabau Connect" (an internal name), implying features are gated to
higher tiers, misstating the product family (Pabau GO, Pabau Pay, Pabau Scribe),
or naming a specific customer/competitor relationship that the guide flags as
verify-first. Treat these as TYPE: Pabau-fact findings.

**Figures inside a visualization are yours to check.** A chart's numbers are baked into an
image, so nobody downstream re-reads them — but our visuals carry their figures in the alt
text and name their source in the caption, both of which are in the body you already hold.
Compare them against the prose and against the source they cite. A mismatch is a `factual`
finding like any other (say which figure, and which the article supports). Do not comment on
whether a visual exists, on its design, or on its placement — that is the editor's Pass D0.

**Do NOT read `WordPress-blocks.md` or `Visuals.md`, and do not audit the block contract.** The
article-editor's final pass enforces all of it unconditionally later in the run, so a block
audit here is redone twice and read by nobody. The exceptions — a wholly missing FAQ, missing
documentation requirements, and a Broken code page's empty required `pdc_*` fields — are
spelled out in the fact-check instructions. Those three are the only absences you report, and
each is a `missing-section` line in the `AUTO` bucket.

Your entire returned message IS the findings report (it is parsed by the
orchestrator, not shown to a human as chat). Begin your reply with the exact line:

`ARTICLE: <the url or post id you reviewed>`

then one of: `CORRECT: No fix needed`; the single line `REWRITE_REQUIRED: <reason>`
(when the article is truncated/incomplete or repeats itself — see the fact-check
instructions, and emit nothing else); or the two buckets, each under its own header,
with `(none)` where a bucket is empty. Do not add preamble, sign-off, or commentary
outside the report.

A code-page state signal is neither commentary nor a fourth shape: `CODE_PAGE_HALF_MIGRATED`
is reported as an ordinary numbered `AUTO` line of type `code-state`, inside the `AUTO`
bucket, per `1-factcheck.md`. Emit it there — never as a bare token on its own line, and never
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
   the article: the site's nav and footer would consume most of the response. That list carries
   `template` and `meta`, so the copy you hold already tells you whether this is a templated
   code page — D0c reads both from it and costs no extra request.
2. **Run all four passes against the copy you hold**, in memory, in order. Do not re-fetch
   between passes — you already have the body, including every edit you just made to it.
3. **Clear the sentence gate BEFORE you save** (Pass E below). The article does not go out
   over the ceiling.
4. **Back the article up, then save ONCE**, at the end, with a single PUT. Before the first
   write, dump the JSON you fetched to `~/Desktop/temp/linkplan-backups/<post-id>.json` (create
   the directory if needed) — one file per article, so any edit of this run can be reversed.
   Then write `payload.json` with the Write tool and send it with
   `-d @payload.json -o /dev/null -w '%{http_code}\n'`. A draft stays a draft; a published post
   stays published. If D0b built a featured image, its `featured_media` id rides along in that
   same payload — it is a field on the post, not a second save. So does a `meta` object, if
   D0c or Pass B changed any `pdc_*` field on a code page: `{"content": …, "featured_media": …,
   "meta": {"pdc_definition": "…"}}` is one save, not three. **Send only the `pdc_*` keys you
   actually changed** — WordPress merges registered meta, so every key you leave out is left
   untouched (confirmed by test). **Never send `template` on an edit** — this agent only edits,
   so it never writes that field, in any state. (`/fact` and `/SEO` never write it; the one
   write that sets it is `/generate`'s create POST, which is not this agent.)
   After the PUT returns 2xx, read the meta straight back —
   `?context=edit&_fields=meta` — and assert every value you sent came back exactly as sent. A
   rejected meta write does not fail the request, so an unverified meta save is an unsaved one;
   report any value that did not stick rather than assuming it did.
   **An Elementor article is the exception:** `post_content` is silently ignored on a
   builder-backed page, so check with `bin/elementor_guard.py <post-id>` before you save. On a
   `BUILDER` verdict, edit the `_elementor_data` structure instead (preserving its JSON encoding
   exactly) and flush Elementor CSS after the save; where that data is not readable over REST,
   change nothing and report `BLOCKED_ELEMENTOR`.
5. **Verify with grep assertions, not page fetches** (see "Verifying the save" below).

The old four-fetch / four-save shape cost six full copies of the article per run and bought
nothing. If a pass genuinely cannot proceed without re-reading something, re-read that one
thing, not the article.

## Guides — read on trigger

- `~/.claude/factcheck-flow/guides/core-rules.md` — **read first, always.** The Pabau
  non-negotiables, voice and mechanics, AI tells, and the required document order.
- `~/.claude/factcheck-flow/prompts/2-editorial.md` — at Pass B.
- `~/.claude/factcheck-flow/prompts/3-links.md` — at Pass C. It is the single source of truth
  for internal linking: the cluster wall, the link budget, the pillar and subhub pattern, the
  funnel and CTA contract, and the mechanical gate that must pass before you save. Cluster
  assignment comes from the cluster store, read through `bin/cluster_lookup.py` — the
  `clusters-data` copy the updater pulls onto every machine, merged with
  `~/Desktop/pabau-content-clusters.xlsx` where the machine has one — never from your own
  sense of what is related. The store is live, not a snapshot, so an article too new to be in
  it gets reasoned from `suggest` and written straight back with `submit`; §0 walks through
  both. A machine with no workbook is the normal case and blocks nothing.
- `~/.claude/factcheck-flow/guides/Visuals.md` — at Pass D0, before you build anything
  visual. It owns the visual contract: what earns a visual, the brand tokens and font, the
  render/upload commands, the block markup, and two verified templates.
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
3. **Pass C — link pass.** Read `~/.claude/factcheck-flow/prompts/3-links.md` and follow it in
   full. It opens by resolving the article's content cluster from the cluster store — reasoning
   it from `suggest` and submitting it back when the article is too new to be in there — and ends with
   a mechanical gate (`cluster_lookup.py verify`) that must exit 0 — the link plan is not
   finished while it fails, exactly like the sentence gate in Pass E.
4. **Pass D — block guarantees (ALWAYS run this LAST).** Read
   `~/.claude/factcheck-flow/guides/WordPress-blocks.md` — the contract, with the exact
   markup for every block (reference article: https://pabau.com/templates/accutite/, post
   151170; fetch it with `context=edit` if you want to see the real thing). Then enforce all
   thirteen guarantees below, in order, against the block markup you hold: original visual →
   featured image (blog) → code-page top area (D0c) → Key takeaways (D1) → download box (D2,
   templates) → Pabau section + CTA block → Conclusion → Continue your research → FAQ →
   provider cards (listicles) →
   listicle pricing → image captions → video placement. The checks run in this order, but on a
   template article the **final document position** is download box, then Key takeaways
   directly below it — D1 and D2 both enforce that positioning regardless of check order.

   D0 runs FIRST inside this pass, so the visual it adds is then covered by D9's caption and
   spacer audit like any other image. D0b and D0c are the two steps that touch no block markup
   at all — D0b sets a field, D0c writes post meta. D0c still has to run **before** D1, because
   the state it detects decides where Key takeaways belongs.

   In D1, D5, D6 and D10 you are only changing wrapper markup, letter case, placeholder items,
   and block position — never the copy. D0, D0b, D0c, D2, D3, D4, D7, D8 and D9 may require writing
   new content (a visualization, a featured-image card, a missing `pdc_*` field, a download box,
   a Pabau section, a proper conclusion, a provider card's verdict and lists, a pricing segment,
   an image caption); write it in the article's voice per `2-editorial.md` and the Pabau guides.

   **D0 — original visual (ALWAYS, runs first in this pass).** Contract:
   `~/.claude/factcheck-flow/guides/Visuals.md` — read it now; it is the single source of
   truth for what to build, the brand tokens, the render commands, and the markup. Every
   article ships **at least one original visual we built**: either a rendered image (HTML →
   WebP via `bin/render_visual.py`, uploaded to the media library) or one CSS-only
   interactive visualization in a `wp:html` block. Default to the rendered image.
   - **Decide from the article's own substance.** Find the range, comparison, process,
     decision, or structure the prose already establishes, and name the visual's job in one
     sentence before you build. If you can't, you're about to build decoration — look
     harder, don't invent data. Every figure must come from the article; pricing is
     first-party only.
   - Build the HTML, render it, **read the rendered file to check it**, then upload with
     `--slug` and `--alt` (the alt carries the figures). Insert the `wp:image` block plus its
     single 800 × 35 spacer in the body section whose point it makes.
   - An interactive visual must pass `render_visual.py --lint-embed` (exit 0) before it goes
     in. No JavaScript — WP Rocket defers JS, so a script is not reliably executed.
   - Stock photos, re-crops of existing site images, and screenshots we didn't make do **not**
     satisfy this. An article that already carries a visual built to this contract does —
     audit it against the guide and leave it.
   - If the environment can't render (`render_visual.py --check` fails on Chrome), do not
     fake it and do not fall back to a decorative image: record it under "Skipped" with the
     reason and carry on with the rest of the pass.

   **D0b — featured image (BLOG ARTICLES WITH AN EMPTY SLOT).** Contract: `Visuals.md` §11 —
   read it before you build; it owns the size, the copy rules and the verified card template.
   The fetch you already did carries `link` and `featured_media`, so this costs no extra
   request.
   - **It applies when both are true:** the article is a blog article, and `featured_media` is
     `0`. A published blog article has `/blog/` in its `link`. A draft's `link` is `?p=<id>`,
     so judge the kind from the article itself: it is a blog article unless it is a template
     article (it hands the reader a downloadable form) or a code article (an ICD/CPT/HCPCS code
     is its subject).
   - **`featured_media` already set → do nothing.** Never replace, re-crop or "improve" an
     existing featured image, and never touch one on a template or code article. Say which
     case it was on the `Featured image:` line and move on.
   - Build the 1200 × 630 card from §11a with this article's own H1, a one-sentence deck, and a
     two-to-four-word topic kicker. **Read the rendered file before you upload it** — a clipped
     title on this card ships to every share preview the article ever gets.
   - Upload with `--slug <article-slug>-featured` and an `--alt` that names it as a Pabau blog
     card and repeats the title. Take the `id` from the upload's JSON.
   - **Attach it by field, in the same single PUT as the body:** add `"featured_media": <id>`
     to `payload.json`. It goes nowhere in the content — no `wp:image` block, no caption, no
     spacer. A card that is both attached and inserted is a failed step, not a bonus.
   - This is not the D0 visual and neither one covers for the other. An article that arrives
     with neither leaves with both.
   - Chrome can't render, or the upload fails? Leave `featured_media` out of the payload
     entirely, record it under "Skipped", and never substitute a stock photo or an existing
     media item.

   **D0c — code-page top area (CODE ARTICLES).** Contract: `WordPress-blocks.md` §13 — read it
   before you touch a `pdc_*` field. On a templated code page the whole area between the H1 and
   the first H2 is rendered by the page template out of post meta, so none of it is in
   `post_content` and none of it is visible in the editor. Run this before D1: what you find
   here decides where Key takeaways belongs.
   - **Detect the state** from the `template` and `meta` you already fetched. There is exactly
     one code template, **`template-diagnostic-code.php`**, and it serves `/diagnostic-codes/`
     and `/procedure-codes/` pages alike — the name is awkward on a procedure page, but it is
     the only one, so never "correct" it and never key any rule on the URL folder. Every code
     page is in exactly ONE of these four states, on either route; read the rows in order and
     stop at the first that matches:

     | # | `template` | `pdc_*` meta | State | What you do |
     |---|---|---|---|---|
     | 1 | `template-diagnostic-code.php` | all eight required fields present | **Templated** | The new contract: no body intro, Key takeaways first, meta is yours to check and fix. |
     | 2 | `template-diagnostic-code.php` | one or more of the eight required fields empty | **Broken** | Everything you do on a Templated page, plus fill the empty required fields. |
     | 3 | empty | any `pdc_*` set | **Half-migrated** | Nothing structural. Treat the body as old shape and report `CODE_PAGE_HALF_MIGRATED`. |
     | 4 | empty | none set | **Old shape** | Nothing. Old contract, body intro first. |

     Most procedure-code pages you meet are still old shape; nearly every diagnostic-code page
     is templated.

   - **The eight ALWAYS-REQUIRED fields** are `pdc_code_type`, `pdc_code`, `pdc_descriptor`,
     `pdc_h1_descriptor`, `pdc_definition`, `pdc_chapter`, `pdc_category`, `pdc_group`. An empty
     one of those eight is what makes a page Broken.
   - **Two fields are CONDITIONAL:** `pdc_billable` and `pdc_specific`. They are required,
     `yes` or `no`, on an **ICD-10-CM** page. They are **left empty** where the code system has
     no billable/specific distinction to report — the live HCPCS page J8650 has both empty, and
     empty is correct there, not a gap. Empty values hide the "Billable Code • Specific Code"
     flag line under the H1 **and** the "Billable" row in Related Information. Never write
     `yes`/`no` into either one just to make a page look complete; if the authority states no
     billable/specific status for that code system, they stay empty.
   - **Five fields are OPTIONAL and never count toward completeness:** `pdc_h1_prefix` is always
     left empty (the template supplies the prefix — "ICD code", "HCPCS code"); `pdc_also_known`
     is written only when the authority names a genuine synonym for the code; and
     `pdc_label_1`, `pdc_label_2`, `pdc_label_3` are written only to override a wrong default
     label (below). An empty one of those five is the correct state, never a gap — never fill
     one to satisfy a check, and never invent a synonym.
   - **`pdc_label_1/2/3` relabel the three Related Information rows** that `pdc_chapter`,
     `pdc_category` and `pdc_group` fill, in that order — 1 → chapter, 2 → category, 3 → group.
     **Empty means "use the template's default label for this code type"**, and the defaults are
     already right for the common cases: an ICD-10-CM page with all three empty renders
     Chapter / Category / Group, and the HCPCS page renders **Level** for row 1 with
     `pdc_label_1` empty. **Set one only to override a default that would be wrong for this
     code** — J8650 sets `pdc_label_3` to `Status` because its `pdc_group` carries
     "Deleted, effective 31 December 2025" rather than a code group. Never blank a label that is
     already set, and never set one to the value the default would produce anyway. This also
     means `pdc_chapter` / `pdc_category` / `pdc_group` are **generic slots**, not literally the
     chapter, the category and the group: they carry the three most useful reference facts for
     that code system, labelled accordingly.
   - **A `template` that is set but is NOT the code template** (`elementor_canvas`,
     `elementor_header_footer`, `elementor_theme`,
     `wp-templates/p-medical-certificate-generator.php`) renders no code top area at all. It is
     not one of the four rows: treat the body as **old shape**, report it as
     `old shape (non-code template: <value>)` on the `Code page:` line, and do not try to fix
     it.

   - **1. Templated** → verify each of the **eight required fields** is present and non-blank,
     and fill any that is empty from the article's own content. Verify `pdc_billable` and
     `pdc_specific` too, but as conditional fields: on an ICD-10-CM page they must read `yes` or
     `no`; on a code system with no such distinction they stay empty. **Leave `pdc_h1_prefix`,
     `pdc_also_known` and any empty `pdc_label_1/2/3` alone**: an empty one is correct, not a
     gap, and you never invent a synonym to fill `pdc_also_known` (write it only when a Stage 1
     finding hands you one). A `pdc_label_*` is yours to set only where the template's default
     label would be wrong for this code, and a label already set is never blanked.
     Apply every `meta:<field>` finding handed down from Stage 1 as a meta write, not a body
     edit. Hold `pdc_definition` and `pdc_h1_descriptor` to the Pass B prose rules (US English,
     AI tells, paragraph length, the 25/30-word ceiling); `pdc_definition` stays plain text, no
     HTML and no links, paragraphs separated by `\n\n`. Put the changed keys in the single PUT's
     `meta` object (see "Fetch once, save once") and verify the read-back.
   - **2. Broken** → the top area is rendering with blanks nobody can see in the editor. Handle
     this page **exactly as Templated** — same body rules (no body intro, Key takeaways first),
     same prose rules, same meta ownership, same read-back — with one addition: fill each empty
     **required** field from the article's own content, following the field table in §13 for the
     shape of each value (official descriptor verbatim, `<range> <chapter title>`,
     `<code> <category title>`, and so on). An empty conditional field (`pdc_billable`,
     `pdc_specific`) or optional field (`pdc_h1_prefix`, `pdc_also_known`, `pdc_label_1/2/3`) is
     not what makes a page Broken and is not filled here. Nothing else about
     the page is treated differently from a Templated one.
   - **3. Half-migrated** → the meta is dead; the page renders the OLD layout. Change nothing
     structural, treat the body as old shape for D1 and D10, and report
     `CODE_PAGE_HALF_MIGRATED` on the `Code page:` line.
   - **4. Old shape** → **do nothing at all.** Do not migrate it, do not invent `pdc_*` values, do
     not set `template`, and do not strip the body intro. The body keeps the old contract: intro
     first, then Key takeaways. Migration is a separate process and not this agent's job.
   - **Never delete or blank a `pdc_*` field, and never send `template` on an edit** — this agent
     only edits, so it never writes `template`, in any of the four states. A blanked field
     silently empties a section of the live page that no one can see in the editor.
   - The template's own "Automate coding with Pabau" CTA panel and "Why practices choose Pabau"
     trust panel are **fixed boilerplate**. Never write copy for them, never copy them into the
     body, and never count them toward the body's own Pabau-section/CTA requirements — D3 and D4
     are unchanged on a code page, and the body keeps its own Pabau section, CTA block and
     `Conclusion`.

   The required document order you are enforcing is `WordPress-blocks.md` §1. Never leave a
   heading above a block that renders its own heading (Key takeaways, Continue your research).

   **D1 — Key takeaways (ALWAYS).** Contract: §2, plus §2a for listicles. Locate the Key
   takeaways section near the
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
   - **Position (check every time).** On a non-template article the block belongs **directly
     below the intro**, not above it — that changed, and most live articles still carry the
     old order. Move the block down past every intro paragraph, and leave nothing in the seam
     between the last intro paragraph and the block: no image, no spacer, no embed, no
     comparison table. **On a template article, the block belongs directly below the download
     box instead (D2)** — the download box sits in the intro/Key-takeaways seam, not Key
     takeaways. **On a templated code page — state 1 Templated or state 2 Broken (D0c) — the block
     is the FIRST block in the body**,
     below only the optional schema `wp:html` and nothing else: the intro lives in
     `pdc_definition`, so there is no body intro for it to sit under. If a body intro is present
     on a templated page, that is the defect — fold its substance into the opening H2 section
     and move the block to the top. Do not delete the prose.
   - **Listicle → the items ARE the ranked provider list** (§2a): one entry per provider
     reviewed, in the body's order, each written `#. [Provider] — Short reason why they're on
     the list.` with the number and period inside the item text. Pass B should have written
     them this way; if the block still carries lesson-style takeaways, or an item count that
     doesn't match the providers reviewed, rewrite the items here — this is the one part of
     D1 where you do touch the copy.

   **D2 — Download box (TEMPLATE ARTICLES ONLY).** Contract: §3. A template article is one
   with a `/templates/` URL, or one whose job is to hand the reader a downloadable
   form/chart/worksheet. Ensure the box sits directly below the intro, **before** the Key
   takeaways block (D1) — Key takeaways now follows the download box, not the other way
   round. The wrapper is fixed and copied byte-for-byte from §3; the H2 text, the
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
   - No block at all → build one from the up-to-5 same-cluster picks chosen per `3-links.md` §7
     in Pass C. Non-block form → convert it, preserving the real links.
   - Scan for placeholder, empty, or dead items and remove them: a literal "list item #1" /
     "list item #2", a bare "list item", "Article title", "Lorem ipsum", an empty `<li>`, or
     a link whose href is "#", empty, or a stub like "example.com". Pass C should have filled
     the block with genuine links already; replace any survivor with a real link to a
     compliant same-cluster article (per `3-links.md` §7) or delete that item.
   - If **no genuine link items remain and you cannot source any**, remove the whole block
     rather than ship an empty shell or stubs. This is the one case where the article may end
     up without it; note it under "Skipped".

   **D7 — Provider cards (LISTICLES ONLY).** Contract: §9a. Every provider review must OPEN
   with a `pabau/provider-card` block placed **directly below the provider's H2** (or H3 if
   the hierarchy runs deeper), before any prose, followed by the standard 800 × 35 spacer.
   - No card under a provider heading → build one per §9a: rating consistent with the review,
     `topPick`/`pickLabel` on the #1 provider only, one-sentence `bottomLine`, newline-separated
     `who`/`works`/`doesnt` lists drawn from the review itself, `price` from the provider's own
     website (same sourcing rule as D8), `siteUrl` = competitor homepage (never their pricing
     page; `pabau.com/pricing/` allowed for Pabau).
   - A card that exists but sits below prose → move it up to directly under the heading.
   - A legacy raw `wp:html` `pb-card` → rebuild it as the `pabau/provider-card` block, carry
     the content over, and remove the per-article `<style>` block once no raw card remains.
   - Never add a logo, and never add a per-article `<style>` block — the plugin ships the CSS.
   - Card facts must agree with the review copy and the D8 pricing segment.

   **D8 — Listicle pricing segments (LISTICLES ONLY).** Contract: §9. Every provider review
   must END with a pricing segment — a `Pricing` heading at the level matching the article's
   provider hierarchy, a pricing table, then one sentence of context — placed after the
   shines/falls-short material and before the next provider. Prefer the site's
   `pricing-table` block using the provider's exact stored name; after saving, confirm it
   rendered real rows (see below) and fall back to a `wp:table` if it came back empty. Every
   figure comes from the provider's own website; never a third-party listing. Also check the
   listicle carries its top-of-page comparison table right after the intro, and add it if
   missing — it does not replace the per-provider tables.

   **D9 — Image captions (ALWAYS).** Contract: §10, which carries the caption rules, the
   block markup, and the required 800 × 35 spacer. Walk EVERY image in the article — core
   `wp:image` blocks, images inside `wp:html`, images in a gallery, **and the visual D0 just
   added** — and bring each one up to §10 (a visual's caption also names its data source, per
   `Visuals.md` §6; an interactive `pv-viz` block is not an image and takes no `<figcaption>`):
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

   **D10 — Video placement (ONLY IF the article has a video).** Contract: §11. Most articles
   carry one and about half have it misplaced, so check every time: search the body you hold
   for `<!-- wp:embed`. The embed's one legal slot is the **last block before the first body
   heading** — after every intro paragraph and after the Key takeaways block that follows
   them, whether the intro is headless or sits under an opening H2. Move it if it is anywhere
   else: between intro paragraphs, above the intro, in the intro/takeaways seam, mid body
   section, inside the Pabau section / Conclusion / FAQ, or after the Conclusion.
   - Move the block **byte-for-byte**. Don't rewrite its markup, don't normalize the
     `className` attribute (both forms are live), and don't add a spacer after it — no article
     has one.
   - Then repair the seam: rejoin any paragraph that was split around the video, and drop any
     "watch the video below" line left pointing at nothing.
   - A dead or private video is a broken block — remove it instead of moving it.
   - **On a templated code page (D0c)** the same rule lands one slot earlier: the embed sits
     directly beneath the Key takeaways block, which is itself the first block, and it is still
     the last block before the first body heading. Second content block, not fourth.
   - No embed in the article → nothing to do. **Never add a video.**

## Pass E — sentence-length gate (MANDATORY, blocks the save)

Sentence length is not checked by eye. You cannot count words reliably while writing, so a
script does it. Run it, fix what it lists, run it again. **This gate is not optional and not
negotiable: while it exits non-zero, the article is not finished and you may not PUT it.**

The checker is `~/.claude/factcheck-flow/bin/sentence_check.py` — a first-party factcheck-flow
script that the installer puts on disk. A healthy install already has it, so just run it.

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
- **Any Code Definition you are about to save is gated too.** If the `pdc_definition` value
  going into your payload is non-empty, it goes through the gate — whatever state the page is in
  (Templated or Broken) and whatever code route it sits on. It never reaches the checker
  through the body, so hand it over as its own unit: write the exact `pdc_definition` text you
  are about to save to a local plain-text file and pass it with `--defn` alongside the body in
  the same run —
  `python3 ~/.claude/factcheck-flow/bin/sentence_check.py --file /tmp/body.html --defn /tmp/defn.txt`.
  The gate is cleared only when that combined run exits 0. Rewrite the definition in the value
  you are going to PUT, not only in the file.
- **If the checker is missing, stop. Do not download it, and do not save the article.** The
  gate cannot be cleared by eye, so an install without the checker cannot ship an article.
  Abort and report `SENTENCE_GATE_UNAVAILABLE — ~/.claude/factcheck-flow/bin/sentence_check.py
  not found; re-run the factcheck-flow installer to restore it`. Fetching code off the network
  and running it mid-article is never part of this job: the installer and its SessionStart
  updater are the only things that install toolkit scripts.

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
curl -s "$URL" | grep -o 'class="pb-card' | wc -l        # provider cards rendered (listicles: one per provider)
curl -s "$URL" | grep -o '>\*[^<]\{0,80\}\*<' | head -5  # leaked asterisk italics (want none)
curl -s "$URL" | grep -o 'pv-viz' | wc -l                # interactive visual root (0 or 1)
curl -sI -o /dev/null -w '%{http_code}\n' "<visual source_url>"   # uploaded visual resolves (200)
curl -sI -o /dev/null -w '%{http_code}\n' "<card source_url>"     # featured card resolves (200)
```

If the payload carried a `meta` object, also read it back per "Fetch once, save once" —
`?context=edit&_fields=meta` — and check each `pdc_*` value you sent against what came back.
A dropped meta write returns 2xx and changes nothing, so this one is an assertion, not a
formality; report any mismatch on the `Code page:` line instead of re-sending blindly.

Compare each count against what you expect to have written. Only when an assertion fails do
you pull a small excerpt (`grep -o … -A2 -B2`) to see why. For D8 specifically, an empty
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
- `Links:` — the full line `3-links.md` §13 specifies: cluster + subcluster + tier (and whether
  it came from the store or your reasoning, and what `submit` said when you reasoned it),
  funnel stage, RANKING/INERT, engine, final
  in-body count against the budget (e.g. `4/5`), the pillar up-link, the subhub on a code
  article, the funnel link, disposition counts with reason codes, picks, both CTA placements,
  the gate's final line verbatim, external-link count, and anything skipped with its code
- `Key takeaways block:` already correct / converted / title attribute added / casing fixed / moved below the intro / moved below the download box / moved to the top (templated code page) / rewritten as the ranked provider list / added
- `Intro:` main keyword in the first sentence (yes/rewritten) + whether the intro now answers the query completely. On a templated code page this line reports `pdc_definition` — the Code Definition is the intro — plus whether the opening H2 section also answers the query; say "no body intro (templated code page)" so it is clear none was expected
- `Code page:` which ONE of the four states it was in (templated / broken / half-migrated / old shape), which `pdc_*` fields you corrected or filled and from what (name any `pdc_label_*` override and why), `CODE_PAGE_HALF_MIGRATED` on a half-migrated page, and the meta read-back result. `not a code page` / `old shape — untouched` where that is the answer
- `Download box:` already correct / added / URL fixed / not a template article
- `Pabau section + CTA block:` already correct / CTA block added / section written / section moved
- `Conclusion:` already correct / renamed from "<old heading>" / rewritten to conclude / written / CTA link added
- `FAQ block:` already a Yoast block / converted / no FAQ present
- `Continue your research block:` already correct / converted / added / placeholders replaced / placeholders removed / trimmed to 5 / wrapper H2 removed / empty block removed
- `Provider cards:` all present under provider headings / N added / N moved up / N converted from raw HTML (style block removed) / not a listicle
- `Pricing segments:` all first-party / N added / N figures corrected / comparison table added / not a listicle
- `Visuals:` what you built and its job in a few words, the route (rendered image / interactive),
  the media id + slug or the `pv-viz` class, and the canvas size. State the figures' source. If
  the article already had a conforming visual, say so. This line is mandatory; an empty one
  means D0 did not run.
- `Featured image:` built and attached (media id + slug) / already had one / not a blog
  article / skipped + why. This line is mandatory; an empty one means D0b did not run
- `Image captions:` N images, all captioned / N written / N rewritten / N asterisk fixes / no images
- `Video:` already in the right slot / moved to end of intro from "<old location>" / moved beneath Key takeaways (templated code page) from "<old location>" / dead video removed / no video
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
FIELDS='id,slug,link,status,type,title,content,excerpt,categories,tags,meta,template,featured_media'

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

**Why `template` is in the list.** On pabau.com, `template` together with the `pdc_*` keys
inside `meta` decides whether a code page renders its top area (badge, H1, flag line, Code
Definition, Related Information) from post meta instead of from `post_content`. That area is
page-visible and fact-checkable but never appears in `content.raw`. `template` is not
returned by default, so if it is missing from `_fields=`, every such check silently reads as
"not templated". Keep it in the list. See `WordPress-blocks.md` §13 for the contract.

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

**Writing meta.** A `meta` object may ride along in the same PUT as `content` — it does not
need a save of its own. WordPress *merges* registered meta, so send only the keys that
changed; keys you omit are left untouched (confirmed by test). After the save, read the meta
back and assert each value you sent came back as sent:

```bash
curl -s -u "$WP_USER:$WP_APP_PASSWORD" \
  "$WP_BASE_URL/wp-json/wp/v2/posts/<POST_ID>?context=edit&_fields=meta"
```

A rejected meta write does not fail the request — the PUT still returns 200 — so the read-back
is the only proof the value landed. Report a dropped meta write; never assume it applied.

## Rules

- Update ONLY the fields you intend to change (`content`, `title`, `slug`, `status`,
  `categories`, `tags`, `author`, `meta`, `excerpt`/meta description as needed).
- **Never send `template` on an edit.** `/fact` and `/SEO` never write it, in any state — a
  code page's `template` is set by the site's migration process, not by an editing pass. The
  only write that sets it is `/generate`'s **create POST**, and only on the
  `/diagnostic-codes/` route. Contract: `WordPress-blocks.md` §13.
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
- \`~/.claude/factcheck-flow/guides/Visuals.md\` — the visual contract: every article ships at least one original visual we built (a rendered chart/diagram, or one CSS-only interactive block), plus the 1200 × 630 featured-image card for a blog article that has none (§11). Brand tokens + Satoshi, the \`bin/render_visual.py\` render/upload commands, block markup, and the verified templates.

Block rules every article must satisfy: the intro comes FIRST, with the main keyword in its first sentence and a complete answer to the keyword's main query; "Key takeaways" directly below the intro with nothing in the seam (capital K only, via the block's \`title\` attribute) — except on a template article, where the download box sits in that seam instead and Key takeaways follows it — and on a listicle those takeaways ARE the ranked provider list, \`#. [Provider] — short reason why they're on the list.\`, one item per provider in body order; an H2 Pabau section with the CTA block immediately before an H2 headed exactly "Conclusion" that concludes (not summarizes) and ends with a \`/book-demo/\` CTA link; a Continue your research block; a download box on template articles, directly below the intro and before Key takeaways; a caption on every image (full sentence, ends with a period, italic via \`<em>\` — and if it shows a Pabau feature, it says how that feature helps the reader do what the article is about); any YouTube embed as the last block before the first body heading, after the intro and Key takeaways — never breaking up a run of prose, and moved byte-for-byte when it is misplaced (about half are); and in listicles a \`Pricing\` heading + pricing table closing every provider review, with figures from the provider's own website only.

Every article also ships at least one original visual we built — a rendered chart/diagram (HTML → WebP via \`bin/render_visual.py\`, uploaded to the media library) or one CSS-only interactive block. Never a stock photo, never invented numbers: every figure comes from the article and the visual names its source. Read \`Visuals.md\` before building one. And a \`/blog/\` article with an empty featured image gets a 1200 × 630 brand card built the same way, attached via \`featured_media\` and never inserted into the body — an existing featured image is never replaced (\`Visuals.md\` §11).

Quick rules: keep sentences to 25 words max (30 only where a split would break the meaning); US English (say "practice", not "clinic"); introduce Pabau on first mention ("practice management software like Pabau"); qualify product names once ("Pabau GO, our iOS app"); never say "Pabau Connect" externally (say "online booking"); no free trial (structured onboarding); every subscription includes every feature (no gating); don't undermine the core product when describing Plus add-ons; barely use "everything", "nothing", "anything" or "thing" (never contrast "everything" with "nothing", and neither can precede a verb other than "be"/"get"); no "real"/"true"/"actual" unless a fake version of that thing exists. Every article must fit searcher intent AND have a unique angle (originality nugget) — never publish generic, me-too content.
$GUIDE_END
EOF
echo "  - CLAUDE.md editing guidance installed"

# --- 4c. Enable auto-update via a SessionStart hook -----------------------
# Registers a hook in ~/.claude/settings.json that runs update.sh whenever a new
# Claude Code session starts, so prompt/guide changes propagate without a manual
# reinstall. Idempotent, and it refuses to touch a settings.json it can't parse.
UPDATE_CMD='bash "$HOME/.claude/factcheck-flow/update.sh"'
if py_ok; then
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
elif command -v python3 >/dev/null 2>&1; then
  py_stub_note "the auto-update hook"
else
  echo "  - NOTE: python3 not found — skipped auto-update hook (you'll need to re-run"
  echo "          this installer manually to get future prompt/guide changes)."
fi

# --- 4d. GSC access for /SEO (published-article keyword list) -------------
# /SEO's "already ranking" list reads Google Search Console via a service-account
# key. The key is a SECRET and is NOT in this repo — you supply it. PyJWT signs the
# short-lived token used to call the API.
if py_ok; then
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
  ask GSC_SRC "  Path to your GSC service-account JSON (blank to skip): "
  if [ -n "${GSC_SRC:-}" ] && [ -f "$GSC_SRC" ]; then
    umask 077; cp "$GSC_SRC" "$GSC_KEY_DEST"; chmod 600 "$GSC_KEY_DEST"
    echo "  - GSC key saved (readable only by you) to $GSC_KEY_DEST"
  else
    echo "  - skipped — set \$PABAU_GSC_KEY or place the JSON at $GSC_KEY_DEST later"
  fi
fi

# --- 4e. Indexing key for /SEO's re-crawl request (OPTIONAL) --------------
# After a refresh, /SEO asks Google to re-crawl the (already public) URL. That call needs a
# SEPARATE service account which is an OWNER of the Search Console property — the read-only
# GSC key above returns 403 for it, so the two keys are not interchangeable. Entirely
# optional: without it /SEO skips the step and says so.
INDEX_KEY_DEST="$FF/indexing-key.json"
if [ -f "$INDEX_KEY_DEST" ]; then
  echo "  - indexing key already present ($INDEX_KEY_DEST) — keeping it"
else
  echo ""
  echo "  OPTIONAL: /SEO can ask Google to re-crawl a refreshed article. That needs a"
  echo "  service-account key whose account is an OWNER of the Search Console property"
  echo "  (not the read-only GSC key above). Blank to skip — /SEO just skips the step."
  ask IDX_SRC "  Path to your Indexing API service-account JSON (blank to skip): "
  if [ -n "${IDX_SRC:-}" ] && [ -f "$IDX_SRC" ]; then
    umask 077; cp "$IDX_SRC" "$INDEX_KEY_DEST"; chmod 600 "$INDEX_KEY_DEST"
    echo "  - indexing key saved (readable only by you) to $INDEX_KEY_DEST"
  else
    echo "  - skipped — /SEO will report the re-crawl request as skipped"
  fi
fi

# --- 4f. Write access to the central cluster store (OPTIONAL) -------------
# Reading the store needs no write token: reads come off the `clusters-data` branch using
# the repo token from step 0 (or unauthenticated, while the repo is still public), and work
# for everybody who can install at all. This token only buys WRITE access, so a cluster you
# reason during a run reaches the branch immediately instead of sitting in a local queue.
#
# The token is NEVER in this file or anywhere in the repo. You paste it, it lands in
# $FF/.clusters-token with mode 600, and .gitignore covers that path.
CLUSTERS_TOKEN_DEST="$FF/.clusters-token"
if [ -s "$CLUSTERS_TOKEN_DEST" ]; then
  echo "  - cluster store token already present — keeping it"
else
  echo ""
  echo "  OPTIONAL: a write token for the shared cluster store."
  echo "  Skipping is fine and nothing breaks: reading cluster assignments needs only the repo"
  echo "  token (or none, while the repo is public), and any assignment you reason is queued"
  echo "  locally and goes up automatically on the first run that has a write token. Nothing"
  echo "  is ever lost by skipping this."
  echo "  Ask David for a fine-grained PAT (this repo, contents:write) when you want one."
  ask_secret CLUSTERS_TOKEN "  Cluster store write token (blank to skip): "
  if [ -n "${CLUSTERS_TOKEN:-}" ]; then
    umask 077
    printf '%s\n' "$CLUSTERS_TOKEN" > "$CLUSTERS_TOKEN_DEST"
    chmod 600 "$CLUSTERS_TOKEN_DEST"
    unset CLUSTERS_TOKEN
    echo "  - cluster store token saved (readable only by you) to $CLUSTERS_TOKEN_DEST"
  else
    echo "  - skipped — reads still work, writes queue locally until a write token exists"
  fi
fi

# --- 4g. First sync of the cluster store ----------------------------------
# Pull the branch copy now, so the very first /fact run has cluster assignments even on a
# machine that has never seen the workbook. Then `adopt`: if this machine DOES have a local
# workbook that differs from the canonical store, export it once to
# clusters/snapshots/<user>.jsonl so consolidation can reconcile the divergence. A snapshot
# is consolidation input only — it never overwrites anything and is never read at runtime.
# Both are fail-silent: no network, no token, no workbook are all fine.
if [ -f "$FF/bin/cluster_sync.py" ] && ! py_ok; then
  py_stub_note "the first cluster-store sync"
elif [ -f "$FF/bin/cluster_sync.py" ]; then
  if python3 "$FF/bin/cluster_sync.py" pull >/dev/null 2>&1; then
    echo "  - cluster store synced"
  else
    echo "  NOTE: could not sync the cluster store now — the updater retries every session."
  fi
  python3 "$FF/bin/cluster_sync.py" adopt >/dev/null 2>&1 || true

  # A local workbook outranks the synced store, but only if it can actually be READ.
  # openpyxl is what reads it, and nothing here installs it. Without openpyxl the store
  # still works (that path degrades with a warning rather than blocking a run), so this is
  # not fatal — but the machine would silently ignore its own spreadsheet, which is worse
  # than being told. Only worth saying to someone who actually has a workbook.
  if [ -f "$HOME/Desktop/pabau-content-clusters.xlsx" ] \
     && ! python3 -c "import openpyxl" >/dev/null 2>&1; then
    echo "  NOTE: you have pabau-content-clusters.xlsx but openpyxl is not installed, so it"
    echo "        cannot be read and the synced store will be used instead. To use your own"
    echo "        workbook:  python3 -m pip install --user openpyxl"
  fi
fi

# --- 4h. The SEO-knowledge skill -------------------------------------------
# The SEO knowledge base Claude queries for any SEO task (CLAUDE.md tells it to), shipped as
# its own repo and installed as a git clone at ~/.claude/skills/SEO-knowledge. From here on
# the auto-updater fast-forwards it at most hourly (update.sh step 0b). This step:
#   - the maintainer's machine (seo-universal/publish-skill.sh exists) → left alone: David
#     publishes the skill from that checkout;
#   - not there yet → clone it (into a temp dir first, so a failed clone leaves nothing);
#   - already that clone → the same safe fast-forward the updater does: only on branch main,
#     only with a clean tree, nothing in flight and nothing unpushed;
#   - something else at that path → left alone, with a note;
#   - no usable git → skipped with a note. None of this ever fails the install.
# The token travels as a one-off http.extraheader for https://github.com/ — never written
# to .git/config or into the remote URL, and on git 2.31+ passed through the environment so
# it is not in `ps` either — and a failed tokened try is retried once without. A user
# url.<ssh>.insteadOf rule is overridden for this one repo, so it stays on HTTPS.
SK_DIR="$CLAUDE/skills/SEO-knowledge"
SK_URL="https://github.com/aleksandark-bot/seo-knowledge-skill.git"
SK_STATUS="$FF/.skill-pull-status"
SK_PUBLISHER="$HOME/Desktop/temp/seo-universal/publish-skill.sh"
SK_PIN="url.https://github.com/aleksandark-bot/seo-knowledge-skill.insteadOf=https://github.com/aleksandark-bot/seo-knowledge-skill"
sk_git_ok() { # a real git on PATH — never the macOS stub that pops an installer dialog
  local g dev
  g="$(command -v git 2>/dev/null)" || return 1
  [ -n "$g" ] || return 1
  if [ "$(uname -s 2>/dev/null)" = Darwin ] && [ "$g" = /usr/bin/git ]; then
    dev="$(xcode-select -p 2>/dev/null)" || return 1
    [ -n "$dev" ] && [ -x "$dev/usr/bin/git" ] || return 1
  fi
  return 0
}
sk_git_ge() { # sk_git_ge MAJOR MINOR — the installed git is at least that version
  local v maj min
  v="$(git --version 2>/dev/null || true)"
  v="${v#git version }"
  maj="${v%%.*}"
  min="${v#*.}"; min="${min%%[!0-9]*}"
  case "$maj" in ''|*[!0-9]*) return 1 ;; esac
  [ -n "$min" ] || min=0
  [ "$maj" -gt "$1" ] && return 0
  [ "$maj" -eq "$1" ] && [ "$min" -ge "$2" ]
}
sk_origin_ok() {
  case "$(git -C "$SK_DIR" config --get remote.origin.url 2>/dev/null || true)" in
    https://github.com/aleksandark-bot/seo-knowledge-skill|https://github.com/aleksandark-bot/seo-knowledge-skill.git) return 0 ;;
  esac
  return 1
}
sk_safe() { # sets SK_WHY when it says no
  local gd="$SK_DIR/.git" f st
  SK_WHY=""
  for f in index.lock rebase-merge rebase-apply MERGE_HEAD CHERRY_PICK_HEAD REVERT_HEAD BISECT_LOG; do
    if [ -e "$gd/$f" ]; then SK_WHY="a git operation is in progress"; return 1; fi
  done
  if command -v pgrep >/dev/null 2>&1 \
     && pgrep -f 'seo-universal/(rebuild-all|publish-skill)|doctrine-update\.sh' >/dev/null 2>&1; then
    SK_WHY="a knowledge-base rebuild is running"; return 1
  fi
  if [ "$(git -C "$SK_DIR" symbolic-ref -q --short HEAD 2>/dev/null || true)" != main ]; then
    SK_WHY="not on branch main"; return 1
  fi
  # GIT_OPTIONAL_LOCKS=0 is `git --no-optional-locks`: status takes no index.lock.
  st="$(GIT_OPTIONAL_LOCKS=0 git -C "$SK_DIR" status --porcelain 2>/dev/null || echo x)"
  if [ -n "$st" ]; then
    SK_WHY="local changes"; return 1
  fi
  return 0
}
sk_auth_err() { # $1 = a failed git's stderr. 0 when it says GitHub refused access
  [ -s "$1" ] || return 1
  grep -Eiq "authentication failed|repository '[^']*' not found|repository not found|could not read (username|password)|terminal prompts disabled|invalid username or (password|token)|returned error: 40[134]|HTTP 40[134]|permission denied \(publickey" "$1"
}
sk_git() { # sk_git <token or ""> <timeout s> <git args...> — no prompts, no helpers, watchdog
  # git's stderr goes to $SK_ERR for sk_auth_err. The whole thing runs in a subshell so that
  # `set -m` (the job gets its own process group, pgid = its pid) never touches the
  # installer's shell; the watchdog then kills git AND its git-remote-https child.
  (
    tok="$1"; limit="$2"; hdr=""; env=0; rc=0; n=0
    shift 2
    if [ -n "$tok" ]; then
      hdr="$(printf 'x-access-token:%s' "$tok" | base64 2>/dev/null | tr -d '\n\r' || true)"
      [ -n "$hdr" ] || exit 1
      if sk_git_ge 2 31; then env=1; fi
    fi
    set -m
    (
      export GIT_TERMINAL_PROMPT=0 GCM_INTERACTIVE=never GIT_ASKPASS=true SSH_ASKPASS=true \
             GIT_SSH_COMMAND='ssh -oBatchMode=yes' \
             GIT_HTTP_LOW_SPEED_LIMIT=1000 GIT_HTTP_LOW_SPEED_TIME=30
      set -- -c credential.helper= -c "$SK_PIN" -c gc.auto=0 -c maintenance.auto=false "$@"
      if [ -n "$hdr" ] && [ "$env" = 1 ]; then
        i="${GIT_CONFIG_COUNT:-0}"
        case "$i" in ''|*[!0-9]*) i=0 ;; esac
        export "GIT_CONFIG_KEY_$i=http.https://github.com/.extraheader" \
               "GIT_CONFIG_VALUE_$i=AUTHORIZATION: basic $hdr" "GIT_CONFIG_COUNT=$((i + 1))"
        exec git "$@"
      elif [ -n "$hdr" ]; then
        exec git -c "http.https://github.com/.extraheader=AUTHORIZATION: basic $hdr" "$@"
      else
        exec git "$@"
      fi
    ) </dev/null >/dev/null 2>"${SK_ERR:-/dev/null}" &
    pid=$!
    set +m
    trap 'kill -TERM -- "-$pid" 2>/dev/null || true; exit 130' INT TERM HUP
    while kill -0 "$pid" 2>/dev/null; do
      n=$((n + 1))
      if [ "$n" -gt "$limit" ]; then
        kill -TERM -- "-$pid" 2>/dev/null || true
        n=0
        while kill -0 "$pid" 2>/dev/null && [ "$n" -lt 5 ]; do sleep 1; n=$((n + 1)); done
        kill -KILL -- "-$pid" 2>/dev/null || true
        break
      fi
      sleep 1
    done
    { wait "$pid"; } 2>/dev/null || rc=$?
    exit "$rc"
  )
}
sk_try() { # sk_try <timeout s> <git args...> — tokened first, then once without. On failure
           # SK_AUTH=1 when GitHub refused every attempt (not offline, not a timeout).
  local limit="$1" tauth=1
  shift
  SK_AUTH=0
  if [ -n "$SK_TOK" ]; then
    if sk_git "$SK_TOK" "$limit" "$@"; then return 0; fi
    sk_auth_err "${SK_ERR:-/dev/null}" || tauth=0
    if [ -n "${SK_TMP:-}" ]; then rm -rf "$SK_TMP/repo"; fi   # a clone's leftovers
  fi
  if sk_git "" "$limit" "$@"; then return 0; fi
  if [ "$tauth" = 1 ] && sk_auth_err "${SK_ERR:-/dev/null}"; then SK_AUTH=1; fi
  return 1
}
sk_status() { # $1 = ok | auth — what the updater's once-per-session line reads
  if [ "$1" = auth ]; then printf 'auth\n' > "$SK_STATUS" 2>/dev/null || true
  else rm -f "$SK_STATUS" 2>/dev/null || true
  fi
}
sk_refused() { # $1 = what it means for this machine
  echo "  NOTE: SEO-knowledge skill: GitHub refused access — this machine has no repo token, or"
  echo "        GitHub refused the one it has. $1"
  echo "        Ask David for a current install command (it includes the token), then run it."
}
sk_stamp() { date +%s > "$FF/.last-skill-pull" 2>/dev/null || true; }  # updater: no re-pull this hour
SK_TOK="${REPO_TOKEN:-}"
SK_DONE=0
SK_TMP=""
SK_ERR="$(mktemp "${TMPDIR:-/tmp}/ff-skill.XXXXXX" 2>/dev/null || true)"
if [ -e "$SK_PUBLISHER" ]; then
  echo "  - SEO-knowledge: maintainer checkout — left alone"
elif ! sk_git_ok; then
  if [ "$(uname -s 2>/dev/null)" = Darwin ]; then
    echo "  NOTE: SEO-knowledge skill skipped — git is not available (the Mac developer tools are"
    echo "        not installed). Run  xcode-select --install , then re-run this installer."
  else
    echo "  NOTE: SEO-knowledge skill skipped — git is not installed. Install git, then re-run"
    echo "        this installer."
  fi
elif [ -d "$SK_DIR/.git" ] && sk_origin_ok; then
  # Explicit refspec, so refs/remotes/origin/main is what gets updated and read whatever
  # the clone's own fetch config says. --no-write-fetch-head (git 2.29+) leaves FETCH_HEAD
  # alone; on an older git the slot repeats --no-tags, which is harmless.
  SK_NWFH="--no-tags"
  if sk_git_ge 2 29; then SK_NWFH="--no-write-fetch-head"; fi
  if ! sk_safe; then
    echo "  - SEO-knowledge skill: skipped: $SK_WHY in $SK_DIR"
  elif ! sk_try 180 -C "$SK_DIR" fetch -q --no-tags "$SK_NWFH" origin +refs/heads/main:refs/remotes/origin/main; then
    if [ "$SK_AUTH" = 1 ]; then
      sk_status auth
      sk_refused "Your copy stays as it is and stops updating until then."
    else
      echo "  NOTE: SEO-knowledge skill: could not reach GitHub — the updater retries hourly."
    fi
  else
    sk_status ok
    SK_NEW="$(git -C "$SK_DIR" rev-parse -q --verify refs/remotes/origin/main 2>/dev/null || true)"
    SK_HEAD="$(git -C "$SK_DIR" rev-parse -q --verify HEAD 2>/dev/null || true)"
    if [ -z "$SK_NEW" ] || [ "$SK_NEW" = "$SK_HEAD" ]; then
      echo "  - SEO-knowledge skill: already up to date"; SK_DONE=1; sk_stamp
    elif ! git -C "$SK_DIR" merge-base --is-ancestor HEAD "$SK_NEW" 2>/dev/null; then
      echo "  - SEO-knowledge skill: skipped: local commits not on GitHub in $SK_DIR"
    elif git -C "$SK_DIR" -c gc.auto=0 -c maintenance.auto=false merge -q --ff-only "$SK_NEW" >/dev/null 2>&1; then
      echo "  - SEO-knowledge skill: updated"; SK_DONE=1; sk_stamp
    else
      echo "  - SEO-knowledge skill: skipped: local changes in $SK_DIR"
    fi
  fi
elif [ -e "$SK_DIR" ]; then
  echo "  NOTE: $SK_DIR exists but is not a git clone of seo-knowledge-skill — left untouched."
  echo "        To have it installed and auto-updated, move it aside and re-run this installer."
else
  mkdir -p "$CLAUDE/skills"
  SK_TMP="$(mktemp -d "$CLAUDE/skills/.SEO-knowledge.tmp.XXXXXX" 2>/dev/null || true)"
  if [ -z "$SK_TMP" ]; then
    echo "  NOTE: SEO-knowledge skill skipped — could not create a temp dir in $CLAUDE/skills."
  else
    SK_OK=0
    if sk_try 300 clone -q "$SK_URL" "$SK_TMP/repo"; then SK_OK=1; sk_status ok
    elif [ "$SK_AUTH" = 1 ]; then sk_status auth
    fi
    if [ "$SK_OK" = 1 ] && [ -f "$SK_TMP/repo/SKILL.md" ] && [ ! -e "$SK_DIR" ] \
       && mv "$SK_TMP/repo" "$SK_DIR" 2>/dev/null; then
      echo "  - SEO-knowledge skill installed to $SK_DIR"; SK_DONE=1; sk_stamp
    elif [ "$SK_OK" = 0 ] && [ "$SK_AUTH" = 1 ]; then
      sk_refused "The skill is not installed yet."
    else
      echo "  NOTE: SEO-knowledge skill: could not download it now. Re-run this installer later;"
      echo "        until it is installed, it does not auto-update."
    fi
    rm -rf "$SK_TMP"
    SK_TMP=""
  fi
fi
if [ "$SK_DONE" = 1 ] && py_ok && [ -f "$SK_DIR/scripts/kb.py" ]; then
  SK_STATS="$(python3 "$SK_DIR/scripts/kb.py" stats 2>/dev/null | head -1 || true)"
  [ -n "$SK_STATS" ] && echo "    $SK_STATS"
fi
[ -n "$SK_ERR" ] && rm -f "$SK_ERR"
unset SK_TOK

# --- 5. WordPress credentials (interactive) -------------------------------
if [ -f "$CREDS" ]; then
  echo "  - credentials already present ($CREDS) — keeping them"
else
  echo ""
  echo "  Now enter your WordPress details (needed to read and edit articles)."
  echo "  Tip: the Application Password comes from WordPress → your Profile →"
  echo "       Application Passwords (it is NOT your normal login password)."
  echo ""
  ask WP_URL "  Site URL (e.g. https://pabau.com): "
  ask WP_USR "  WordPress username: "
  ask_secret WP_PW "  Application password: "
  if [ -n "${WP_URL:-}" ] && [ -n "${WP_USR:-}" ] && [ -n "${WP_PW:-}" ]; then
    umask 077
    printf 'WP_BASE_URL=%s\nWP_USER=%s\nWP_APP_PASSWORD=%s\n' "$WP_URL" "$WP_USR" "$WP_PW" > "$CREDS"
    chmod 600 "$CREDS"
    echo "  - credentials saved (readable only by you) to $CREDS"
  else
    # An empty credentials file looks configured and fails at the first REST call, so write
    # nothing. Everything else — prompts, guides, bin, the cluster store — is installed.
    echo "  - no WordPress credentials entered. Re-run this installer from a terminal, or"
    echo "    write $CREDS yourself with WP_BASE_URL / WP_USER / WP_APP_PASSWORD."
  fi
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
