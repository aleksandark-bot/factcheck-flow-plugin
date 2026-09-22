#!/usr/bin/env python3
"""Move cluster assignments between this machine and the central store.

The central store is the `clusters-data` branch of the public repo
aleksandark-bot/factcheck-flow-plugin (see clusters/CONTRACT.md — that file is the
agreement, this script is one implementation of it). Nothing here ever decides WHAT a
cluster is; `cluster_lookup.py` reads, `cluster_store.py` merges, this moves bytes.

Commands
  pull     fetch the store into ~/.claude/factcheck-flow/clusters/ (gated on the branch sha)
  submit   append ONE reasoned assignment to the local queue, then try to push it
  push     drain the local queue into clusters/additions.jsonl on the data branch
  adopt    one-time export of this machine's workbook to clusters/snapshots/<user>.jsonl
  status   what a human runs when something looks off

Design rules, all of them load-bearing:
  * FAIL-SILENT. This runs inside a /fact run. A dead network, a rate limit, a missing
    token or a half-written file must never block or crash one. Everything exits 0 except
    a genuine agent error on `submit` (exit 2), which is a bug worth stopping for.
  * QUEUE FIRST. `submit` writes the durable local row BEFORE it touches the network.
    Nothing is ever lost to a missing token.
  * ATOMIC. Every local write is temp-file + os.replace, after validation, so a partial
    download can never truncate a good local file.
  * THE TOKEN IS NEVER PRINTED. The repo is public; the token is a fine-grained PAT with
    contents:write on it. It is read from the environment or a chmod-600 file, used as a
    header, and scrubbed out of every message this script emits.

Depends on `cluster_store.py` (same directory) for url normalization, the row schema, the
authority ladder and the merged read path. Without it this still queues and pushes, degraded,
and says so.

Data (override with env vars):
  $PABAU_CLUSTERS_TOKEN  else ~/.claude/factcheck-flow/.clusters-token   (contents:write PAT)
  $PABAU_CLUSTERS_XLSX   else ~/Desktop/pabau-content-clusters.xlsx      (adopt's input)
  $PABAU_CLUSTER_USER    else git config user.email's localpart, else $USER  (snapshot name)
  $PABAU_FACTCHECK_DIR   else ~/.claude/factcheck-flow                   (local store root)
  $PABAU_CLUSTERS_DIR    else <$PABAU_FACTCHECK_DIR>/clusters   (where pull writes)
  $PABAU_CLUSTERS_REPO   $PABAU_CLUSTERS_BRANCH
  $PABAU_CLUSTERS_API_BASE  $PABAU_CLUSTERS_RAW_BASE   (test seams; default GitHub)

Exit codes: 0 always, except 2 for a setup/usage error or a `submit` that re-litigates a
human assignment.
"""
import argparse
import base64
import hashlib
import json
import os
import random
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

# --------------------------------------------------------------------------- config

HOME = os.path.expanduser("~")
FF = os.environ.get("PABAU_FACTCHECK_DIR") or os.path.join(HOME, ".claude", "factcheck-flow")
DATA_DIR = os.environ.get("PABAU_CLUSTERS_DIR") or os.path.join(FF, "clusters")
QUEUE = os.path.join(FF, "cluster-queue.jsonl")
SHA_STATE = os.path.join(FF, ".last-clusters-sha")
ADOPT_STATE = os.path.join(FF, ".last-adopt.json")
TOKEN_FILE = os.path.join(FF, ".clusters-token")
XLSX = os.environ.get("PABAU_CLUSTERS_XLSX") or os.path.join(
    HOME, "Desktop", "pabau-content-clusters.xlsx")

REPO = os.environ.get("PABAU_CLUSTERS_REPO") or "aleksandark-bot/factcheck-flow-plugin"
BRANCH = os.environ.get("PABAU_CLUSTERS_BRANCH") or "clusters-data"
API_BASE = (os.environ.get("PABAU_CLUSTERS_API_BASE") or "https://api.github.com").rstrip("/")
RAW_BASE = (os.environ.get("PABAU_CLUSTERS_RAW_BASE")
            or "https://raw.githubusercontent.com").rstrip("/")

TIMEOUT = 8            # every network call. Non-negotiable: this runs inside /fact.
PULL_DEADLINE = 25     # whole-command budget for `pull`: six requests must not add up
MAX_RETRIES = 5        # 409/422 on PUT — somebody else pushed between our GET and PUT
UA = "factcheck-flow-cluster-sync/1.0"

# repo path, local name, required?  A missing optional file is normal: additions.jsonl only
# exists once somebody has pushed, snapshots/ is per-user.
PULL_FILES = [
    ("clusters/base.jsonl", "base.jsonl", True),
    ("clusters/clusters.json", "clusters.json", True),
    ("clusters/review-queue.json", "review-queue.json", False),
    ("clusters/additions.jsonl", "additions.jsonl", False),
    ("clusters/MANIFEST.json", "MANIFEST.json", False),
]

ADDITIONS_PATH = "clusters/additions.jsonl"

# CONTRACT.md "Row schema", in order. cluster_store.ROW_KEYS is the real list and is what
# actually orders a written row; this copy only feeds the degraded-mode guard below.
ROW_KEYS = [
    "url", "title", "cluster", "cluster_id", "tier", "subcluster", "published",
    "rule_applied", "secondary_tag", "flag", "note", "wp_categories", "source_sheet",
    "intent", "silo_source", "depth_target", "depth_current", "in_scope", "exclusion",
    "assigned_by", "assigned_at", "evidence",
]

try:  # output gets piped to head; die quietly when it does
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (ImportError, AttributeError, ValueError):
    pass


def die(msg):
    sys.stderr.write("CLUSTER SYNC ERROR: " + scrub(msg) + "\n")
    sys.exit(2)


def warn(msg):
    sys.stderr.write("cluster-sync: " + scrub(msg) + "\n")


def say(msg):
    sys.stdout.write(scrub(msg) + "\n")


# ------------------------------------------------------------------ the shared store

# cluster_store.py owns url normalization, the row schema, the authority ladder and the
# merged read path. This module moves bytes; it never forms a second opinion about any of
# that. The guard below exists for one case only — a half-finished install where
# cluster_store.py has not landed yet — and it degrades loudly rather than guessing.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
STORE_OK = True
try:
    from cluster_store import (AUTHORITY, assignment_of, authority_of, canonical_row,
                               cluster_by_key, load_store, normalize_url,
                               read_workbook, row_json)
except Exception as _store_err:  # degraded mode
    STORE_OK = False
    _STORE_ERR = str(_store_err)

    def normalize_url(u):
        """GUARD ONLY. cluster_store.normalize_url is the real one; this exists so a
        half-installed machine still queues a usable row instead of crashing a /fact run."""
        if not u:
            return ""
        u = str(u).strip().split("#")[0].split("?")[0]
        u = re.sub(r"^https?://", "", u, flags=re.I)
        u = re.sub(r"^www\.", "", u, flags=re.I).rstrip("/")
        return "https://" + u.lower() + "/" if u else ""

    AUTHORITY = {"human": 0, "spreadsheet": 1, "interlinking-v4": 2, "reasoned": 3}

    def authority_of(row):
        return AUTHORITY.get((row.get("silo_source") or "").strip().lower(), 2)

    def assignment_of(row):
        return ((row.get("cluster_id") or "").strip().lower(),
                (row.get("cluster") or "").strip().lower(),
                (row.get("subcluster") or "").strip().lower())

    def canonical_row(d):
        out = {k: d[k] for k in ROW_KEYS if k in d}
        out.update({k: v for k, v in d.items() if k not in out})
        return out

    def row_json(row):
        return json.dumps(canonical_row(row), ensure_ascii=False,
                          separators=(",", ":"), sort_keys=False)

    def load_store(xlsx_path=None, data_dir=None):
        return {"posts": {}, "clusters": {"list": [], "by_id": {}, "by_name": {}},
                "review": {}, "meta": {"warnings": ["cluster_store.py is missing"]}}

    def cluster_by_key(store, key):
        return None

    def read_workbook(xlsx_path=None):
        return None


def store_guard():
    """One warning, once, when we are running without cluster_store.py."""
    if not STORE_OK:
        warn("cluster_store.py could not be imported (%s) — running degraded: rows are "
             "still queued and pushed, but the local store is not consulted. Re-run "
             "`update.sh` or reinstall." % _STORE_ERR)
    return STORE_OK


def store():
    """The merged read path, pinned to THIS module's data dir and workbook."""
    try:
        return load_store(xlsx_path=XLSX, data_dir=DATA_DIR)
    except SystemExit:
        raise
    except Exception as e:
        warn("could not load the local store (%s) — continuing without it" % e)
        return {"posts": {}, "clusters": {"list": [], "by_id": {}, "by_name": {}},
                "review": {}, "meta": {}}


def dumps_row(row):
    return row_json(row)


# ----------------------------------------------------------------------------- token

_TOKEN_CACHE = []


def read_token():
    """The PAT, or "". Env first, then the chmod-600 file. Cached so scrub() can redact it."""
    if _TOKEN_CACHE:
        return _TOKEN_CACHE[0]
    tok = (os.environ.get("PABAU_CLUSTERS_TOKEN") or "").strip()
    src = "env" if tok else ""
    if not tok:
        try:
            with open(TOKEN_FILE) as fh:
                tok = fh.read().strip()
            src = "file" if tok else ""
        except Exception:
            tok = ""
    _TOKEN_CACHE.append(tok)
    _TOKEN_CACHE.append(src)
    return tok


def token_source():
    read_token()
    return _TOKEN_CACHE[1] if len(_TOKEN_CACHE) > 1 else ""


def scrub(msg):
    """Belt and braces: even an accidental interpolation can't leak the token to a log."""
    s = str(msg)
    tok = _TOKEN_CACHE[0] if _TOKEN_CACHE else (os.environ.get("PABAU_CLUSTERS_TOKEN") or "")
    if tok and len(tok) > 6 and tok in s:
        s = s.replace(tok, "***redacted***")
    return s


# ------------------------------------------------------------------------------ http

def http(url, method="GET", data=None, headers=None, auth=True, timeout=TIMEOUT):
    """(status, body_bytes, error) — never raises, never blocks longer than `timeout`.

    status 0 means the request never completed (DNS, TLS, timeout, refused).
    """
    hdrs = {"User-Agent": UA, "Accept": "application/vnd.github+json"}
    if headers:
        hdrs.update(headers)
    if auth:
        tok = read_token()
        if tok:
            hdrs["Authorization"] = "Bearer " + tok
    if isinstance(data, str):
        data = data.encode("utf-8")
    req = urllib.request.Request(url, data=data, method=method, headers=hdrs)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.getcode(), r.read(), None
    except urllib.error.HTTPError as e:
        try:
            body = e.read()
        except Exception:
            body = b""
        return e.code, body, "HTTP %d" % e.code
    except Exception as e:  # URLError, socket.timeout, ssl, anything
        return 0, b"", type(e).__name__ + ": " + str(e)


def http_json(url, method="GET", payload=None, auth=True, timeout=TIMEOUT):
    """(status, parsed_or_None, error)."""
    data = None
    headers = None
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers = {"Content-Type": "application/json"}
    code, body, err = http(url, method=method, data=data, headers=headers, auth=auth,
                           timeout=timeout)
    obj = None
    if body:
        try:
            obj = json.loads(body.decode("utf-8", "replace"))
        except Exception:
            obj = None
    if err is None and obj is None and body:
        err = "unparseable response"
    return code, obj, err


def api_error(code, obj):
    """A short, safe explanation of a GitHub API failure."""
    msg = ""
    if isinstance(obj, dict):
        msg = str(obj.get("message") or "")
    if code == 401:
        return "401 — the token was rejected (expired, revoked, or not a token)"
    if code == 403:
        return "403 — forbidden or rate-limited%s" % (": " + msg if msg else "")
    if code == 404:
        return ("404 — branch %s or the path is missing, or the token cannot see the repo"
                % BRANCH)
    return "HTTP %s%s" % (code, ": " + msg if msg else "")


def head_sha():
    """Head commit of the data branch, or "". Works unauthenticated — the repo is public."""
    url = "%s/repos/%s/commits/%s" % (API_BASE, REPO, urllib.parse.quote(BRANCH))
    code, obj, err = http_json(url)
    if code == 200 and isinstance(obj, dict) and obj.get("sha"):
        return str(obj["sha"])
    return ""


def raw_get(commit, repo_path, timeout=TIMEOUT):
    """(status, bytes, error) for a file, pinned to a COMMIT sha.

    Pinning matters twice: raw.githubusercontent caches branch refs for minutes, and a
    multi-file pull must see one consistent snapshot, not a moving branch.
    """
    url = "%s/%s/%s/%s" % (RAW_BASE, REPO, commit, repo_path)
    return http(url, auth=bool(read_token()), timeout=timeout)


def dir_listing(repo_dir):
    """{name: {"sha":..., "size":...}} for a directory on the data branch, or None.

    Deliberately a DIRECTORY listing, not a file GET: the Contents API refuses to return
    content for files over 1 MB, but a listing still carries every blob sha — and the blob
    sha is the only thing a PUT actually needs.
    """
    url = "%s/repos/%s/contents/%s?ref=%s" % (API_BASE, REPO, repo_dir,
                                              urllib.parse.quote(BRANCH))
    code, obj, err = http_json(url)
    if code == 404:
        return {}          # directory doesn't exist yet — same as empty
    if code != 200 or not isinstance(obj, list):
        return None        # unknown: caller must not treat this as "file absent"
    out = {}
    for e in obj:
        if isinstance(e, dict) and e.get("name"):
            out[e["name"]] = {"sha": e.get("sha"), "size": e.get("size")}
    return out


def put_file(repo_path, content_text, blob_sha, message):
    """PUT one file. (ok, status, error). Caller owns the retry loop."""
    url = "%s/repos/%s/contents/%s" % (API_BASE, REPO, repo_path)
    payload = {
        "message": message,
        "branch": BRANCH,
        "content": base64.b64encode(content_text.encode("utf-8")).decode("ascii"),
    }
    if blob_sha:
        payload["sha"] = blob_sha
    code, obj, err = http_json(url, method="PUT", payload=payload, timeout=max(TIMEOUT, 15))
    if code in (200, 201):
        return True, code, None
    return False, code, api_error(code, obj)


def backoff(attempt):
    time.sleep(min(0.4 * (2 ** attempt), 3.0) + random.uniform(0, 0.25))


# ------------------------------------------------------------------- local file paths

def local(name):
    return os.path.join(DATA_DIR, name)


def ensure_dirs():
    for d in (FF, DATA_DIR):
        try:
            os.makedirs(d, exist_ok=True)
        except OSError:
            pass


def atomic_write(path, text):
    """Write via temp + rename. Returns True on success; never leaves a partial file."""
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp = "%s.tmp%d" % (path, os.getpid())
        with open(tmp, "w", encoding="utf-8") as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        return True
    except Exception as e:
        warn("could not write %s: %s" % (path, e))
        try:
            os.unlink(tmp)
        except Exception:
            pass
        return False


def read_jsonl(path):
    """[rows]. A malformed line is skipped, never fatal — a bad line must not cost the run."""
    rows = []
    try:
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                if isinstance(o, dict):
                    rows.append(o)
    except Exception:
        return []
    return rows


def parse_jsonl_text(text):
    """(rows, error). Strict: this validates a DOWNLOAD before it replaces a good file."""
    rows = []
    for i, line in enumerate(text.splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            o = json.loads(line)
        except Exception as e:
            return None, "line %d is not JSON (%s)" % (i, e)
        if not isinstance(o, dict):
            return None, "line %d is not a JSON object" % i
        rows.append(o)
    return rows, None


def count_of(name, text):
    """"N rows" / "N clusters" — what a human wants to see next to a file name."""
    if name.endswith(".jsonl"):
        return "%d rows" % len([l for l in text.splitlines() if l.strip()])
    try:
        obj = json.loads(text)
    except Exception:
        return "unreadable"
    if isinstance(obj, list):
        return "%d entries" % len(obj)
    if isinstance(obj, dict):
        for k in ("clusters", "items", "rows", "queue", "urls"):
            if isinstance(obj.get(k), list):
                return "%d %s" % (len(obj[k]), k)
        return "%d keys" % len(obj)
    return "ok"


# ------------------------------------------------------------------------------ pull

def manifest_sha256(manifest_text):
    """{filename: digest} from a MANIFEST, whatever shape the writer chose.

    The contract says MANIFEST carries "sha256 of base.jsonl" without fixing the shape, and
    the consolidator writes all three: `sha256` as a {file: digest} map, `base_sha256`, and
    (defensively) `sha256` as a bare string. Read all of them, trust any of them.
    """
    try:
        man = json.loads(manifest_text) or {}
    except Exception:
        return {}
    if not isinstance(man, dict):
        return {}
    out = {}
    s = man.get("sha256")
    if isinstance(s, dict):
        for k, v in s.items():
            if isinstance(v, str):
                out[os.path.basename(str(k))] = v
    elif isinstance(s, str) and s:
        out["base.jsonl"] = s
    if isinstance(man.get("base_sha256"), str) and man["base_sha256"]:
        out.setdefault("base.jsonl", man["base_sha256"])
    return out


def manifest_mismatch(staged):
    """The staged files whose content contradicts the MANIFEST. Empty list = all good."""
    man = staged.get("MANIFEST.json")
    if not man:
        return []
    want = manifest_sha256(man)
    bad = []
    for name, digest in want.items():
        text = staged.get(name)
        if text is None:
            continue
        if hashlib.sha256(text.encode("utf-8")).hexdigest().lower() != str(digest).lower():
            bad.append(name)
    return bad


def cmd_pull(a):
    """Fetch the store. Gated on the branch head sha; fail-silent; exit 0 whatever happens."""
    ensure_dirs()
    deadline = time.time() + PULL_DEADLINE
    sha = head_sha()
    if not sha:
        say("pull: could not reach the data branch — using whatever is already on disk.")
        return 0

    last = ""
    try:
        with open(SHA_STATE) as fh:
            last = fh.read().strip()
    except Exception:
        last = ""

    have_required = all(os.path.exists(local(n)) for _, n, req in PULL_FILES if req)
    if last == sha and have_required and not a.force:
        if not a.quiet:
            say("pull: already at %s — nothing to do." % sha[:7])
        return 0

    # Phase 1: download and validate everything into memory. Nothing on disk is touched
    # until every file has proved itself.
    staged = {}          # local name -> text
    counts = {}
    missing_ok = []
    failed = []
    for repo_path, name, required in PULL_FILES:
        left = deadline - time.time()
        if left <= 0.5:
            # Six requests at 8s each could add up to a stall inside a /fact run. One
            # overall budget; whatever has not arrived by then waits for the next run.
            failed.append(name)
            continue
        code, body, err = raw_get(sha, repo_path, timeout=min(TIMEOUT, left))
        if code == 404:
            (failed if required else missing_ok).append(name)
            continue
        if code != 200 or err:
            failed.append(name)
            continue
        try:
            text = body.decode("utf-8")
        except Exception:
            failed.append(name)
            continue
        if name.endswith(".jsonl"):
            rows, perr = parse_jsonl_text(text)
            if perr is not None:
                warn("pull: %s is malformed (%s) — keeping the local copy" % (name, perr))
                failed.append(name)
                continue
            counts[name] = "%d rows" % len(rows)
        else:
            if not text.strip():
                failed.append(name)
                continue
            try:
                obj = json.loads(text)
            except Exception as e:
                warn("pull: %s is not valid JSON (%s) — keeping the local copy" % (name, e))
                failed.append(name)
                continue
            counts[name] = count_of(name, text)
        staged[name] = text

    if any(req and name not in staged for _, name, req in PULL_FILES):
        say("pull: incomplete download (%s) — local files left untouched."
            % (", ".join(sorted(set(failed))) or "unknown"))
        return 0

    # Integrity: MANIFEST.json carries the digests. A mismatch means we fetched a torn
    # snapshot (or somebody pushed mid-pull); take none of it rather than half of it.
    bad = manifest_mismatch(staged)
    if bad:
        say("pull: MANIFEST sha256 does not match %s — refusing this snapshot, local files "
            "left untouched." % ", ".join(bad))
        return 0

    # Phase 2: commit to disk.
    wrote = []
    for name, text in staged.items():
        if atomic_write(local(name), text):
            wrote.append(name)
    if len(wrote) != len(staged):
        say("pull: only %d of %d files could be written — not recording the sha, the next "
            "run will retry." % (len(wrote), len(staged)))
        return 0

    if not failed:
        atomic_write(SHA_STATE, sha + "\n")
    else:
        warn("pull: %s could not be fetched — not recording the sha so the next run retries."
             % ", ".join(sorted(set(failed))))

    say("pull: %s @ %s — %s" % (
        ", ".join("%s (%s)" % (n, counts.get(n, "?")) for n in sorted(wrote)),
        sha[:7],
        "complete" if not missing_ok else "not yet on the branch: " + ", ".join(missing_ok)))
    return 0


# ---------------------------------------------------------------------------- submit

def queued_row(url):
    """A row for this url already sitting in the local queue, or None."""
    u = normalize_url(url)
    for row in read_jsonl(QUEUE):
        if normalize_url(row.get("url")) == u:
            return row
    return None


def cluster_meta(st, cluster_id, cluster_name=""):
    """(name, tier) for a cluster id, off clusters.json. tier is DERIVED, never authored."""
    c = cluster_by_key(st, cluster_id or cluster_name)
    if c:
        return str(c.get("name") or ""), str(c.get("tier") or "")
    return (cluster_name or ""), ""


def load_evidence(a):
    """The `suggest` output that justified the assignment, trimmed to the contract's caps."""
    raw = None
    if a.evidence_json:
        raw = a.evidence_json
    elif a.evidence_file:
        try:
            if a.evidence_file == "-":
                raw = sys.stdin.read()
            else:
                with open(a.evidence_file, encoding="utf-8") as fh:
                    raw = fh.read()
        except Exception as e:
            die("could not read --evidence-file %s: %s" % (a.evidence_file, e))
    if raw is None:
        die("a reasoned row must carry its evidence (CONTRACT.md EVIDENCE). Pass "
            "--evidence-json '<json>' or --evidence-file <path> with the "
            "`cluster_lookup.py suggest` output that justified this assignment.")
    try:
        ev = json.loads(raw)
    except Exception as e:
        die("--evidence is not valid JSON: %s" % e)
    if not isinstance(ev, dict):
        die("--evidence must be a JSON object with top_matches / tally / top_score / "
            "title_used / terms_used")
    out = {
        "top_matches": [m for m in (ev.get("top_matches") or []) if isinstance(m, dict)][:8],
        "tally": [t for t in (ev.get("tally") or []) if isinstance(t, dict)][:5],
        "top_score": ev.get("top_score"),
        "title_used": str(ev.get("title_used") or ""),
        "terms_used": str(ev.get("terms_used") or ""),
    }
    if out["top_score"] is None and out["top_matches"]:
        try:
            out["top_score"] = out["top_matches"][0].get("score")
        except Exception:
            pass
    if not out["top_matches"] and not out["tally"]:
        die("--evidence carries neither top_matches nor tally — that is not an audit trail. "
            "Pass the real `suggest` output.")
    return out


def who_am_i():
    """The handle a row is signed with."""
    for env in ("PABAU_CLUSTER_USER", "USER", "LOGNAME"):
        v = (os.environ.get(env) or "").strip()
        if v:
            return v
    return "unknown"


def now_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def cmd_submit(a):
    url = normalize_url(a.url)
    if not url or not url.startswith("https://"):
        die("--url %r does not normalize to a canonical URL" % a.url)
    if not (a.cluster_id or "").strip():
        die("--cluster-id is required (the slug id, e.g. med-spa-aesthetics)")

    store_guard()
    st = store()
    prior = st["posts"].get(url)

    # silo_source is an OPEN vocabulary, so this keys on AUTHORITY, never on a string match.
    # "human" and "spreadsheet" are human assignments; everything unrecognized ranks as
    # machine-assigned, which a reasoned row may legitimately restate.
    if prior and authority_of(prior) <= AUTHORITY.get("spreadsheet", 1) and not a.force:
        die("%s already has a %s assignment (%s) in the local store. A human assignment is "
            "never re-litigated by an agent (CONTRACT.md PROVENANCE, 3-links.md §0) — run "
            "`cluster_lookup.py resolve --url %s` and follow it. Nothing was queued."
            % (url, prior.get("silo_source") or "?",
               prior.get("cluster") or prior.get("cluster_id") or "—", url))
    if prior:
        warn("%s already has a %s row (%s, authority %d). A reasoned row never outranks it "
             "— queuing anyway so consolidation sees both, but the link pass is only "
             "supposed to submit urls with NO row."
             % (url, prior.get("silo_source") or "?",
                prior.get("cluster") or "—", authority_of(prior)))
    dupe = queued_row(url)
    if dupe:
        warn("%s is already queued (%s). First writer wins — push will keep the earlier row."
             % (url, dupe.get("assigned_at")))

    evidence = load_evidence(a)
    name, tier = cluster_meta(st, a.cluster_id, a.cluster or "")
    row = canonical_row({
        "url": url,
        "title": a.title or "",
        "cluster": a.cluster or name,
        "cluster_id": a.cluster_id.strip(),
        "tier": tier,
        "subcluster": a.subcluster or "",
        "published": a.published or "",
        "rule_applied": a.rule or "",
        "intent": (a.intent or "").upper(),
        "silo_source": "reasoned",
        "in_scope": "yes",
        "assigned_by": a.assigned_by or who_am_i(),
        "assigned_at": now_iso(),
        "evidence": evidence,
    })
    if not row.get("cluster"):
        die("could not resolve a cluster NAME for id %r — pull the store (`cluster_sync.py "
            "pull`) or pass --cluster \"<Cluster name>\"" % a.cluster_id)

    # THE QUEUE WRITE HAPPENS FIRST, unconditionally, before any network call. Everything
    # after this point is best-effort; the row is already durable.
    ensure_dirs()
    try:
        with open(QUEUE, "a", encoding="utf-8") as fh:
            fh.write(dumps_row(row) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
    except Exception as e:
        die("could not write the queue at %s: %s" % (QUEUE, e))
    say("submit: queued %s -> %s / %s (%s)"
        % (url, row["cluster"], row.get("subcluster") or "—", row["assigned_at"]))

    if a.no_push:
        say("submit: --no-push, %d row(s) waiting in the queue." % len(read_jsonl(QUEUE)))
        return 0
    return do_push(quiet=False, dry_run=False)


# ------------------------------------------------------------------------------ push

def queue_key(row):
    """Identity of a queued row: url + when it was reasoned. Stable across a rewrite."""
    return (normalize_url(row.get("url")), str(row.get("assigned_at") or ""))


def prune_queue(done_keys):
    """Rewrite the queue without the rows that are now upstream. Re-reads first, so a submit
    that happened during the push is not lost."""
    if not done_keys:
        return 0
    rows = read_jsonl(QUEUE)
    keep = [r for r in rows if queue_key(r) not in done_keys]
    if len(keep) == len(rows):
        return 0
    text = "".join(dumps_row(r) + "\n" for r in keep)
    if atomic_write(QUEUE, text):
        return len(rows) - len(keep)
    return 0


def do_push(quiet=False, dry_run=False):
    """Drain the queue into clusters/additions.jsonl. Always returns 0 — never an error."""
    rows = read_jsonl(QUEUE)
    if not rows:
        if not quiet:
            say("push: the queue is empty.")
        return 0

    tok = read_token()
    if not tok:
        say("push: no token, so %d queued assignment(s) stay on disk and go up on the next "
            "run that has one ($PABAU_CLUSTERS_TOKEN or %s). Nothing was lost."
            % (len(rows), TOKEN_FILE))
        return 0

    if dry_run:
        say("push: --dry-run, %d queued row(s) for %s"
            % (len(rows), ", ".join(sorted({normalize_url(r.get("url")) for r in rows}))))
        return 0

    for attempt in range(MAX_RETRIES):
        sha = head_sha()
        if not sha:
            say("push: could not reach the data branch — %d row(s) stay queued." % len(rows))
            return 0
        listing = dir_listing("clusters")
        if listing is None:
            say("push: could not list the data branch — %d row(s) stay queued." % len(rows))
            return 0
        entry = listing.get("additions.jsonl")
        blob_sha = entry.get("sha") if entry else None

        existing_text = ""
        if entry:
            code, body, err = raw_get(sha, ADDITIONS_PATH)
            if code == 404:
                existing_text = ""
            elif code != 200 or err:
                say("push: could not read additions.jsonl (%s) — %d row(s) stay queued."
                    % (err or code, len(rows)))
                return 0
            else:
                try:
                    existing_text = body.decode("utf-8")
                except Exception:
                    say("push: additions.jsonl did not decode as UTF-8 — %d row(s) stay "
                        "queued." % len(rows))
                    return 0
        existing_rows, perr = parse_jsonl_text(existing_text)
        if perr is not None:
            say("push: additions.jsonl upstream is malformed (%s) — refusing to rewrite it. "
                "%d row(s) stay queued." % (perr, len(rows)))
            return 0

        # Dedupe on the NORMALIZED url, and never overwrite a row that is already there:
        # first writer wins (CONTRACT.md PROVENANCE).
        have = {normalize_url(r.get("url")) for r in existing_rows}
        new_rows, new_keys, dup_keys, seen = [], set(), set(), set()
        for r in rows:
            u = normalize_url(r.get("url"))
            if not u:
                continue
            if u in have:
                dup_keys.add(queue_key(r))     # already upstream: resolved, not lost
                continue
            if u in seen:
                dup_keys.add(queue_key(r))     # two queued rows, same url: earliest wins
                continue
            seen.add(u)
            new_rows.append(canonical_row(r))
            new_keys.add(queue_key(r))

        if not new_rows:
            n = prune_queue(dup_keys)
            say("push: nothing new — %d queued row(s) were already upstream and have been "
                "cleared." % n)
            return 0

        text = existing_text
        if text and not text.endswith("\n"):
            text += "\n"
        text += "".join(dumps_row(r) + "\n" for r in new_rows)

        msg = "clusters: +%d reasoned assignment%s (%s)" % (
            len(new_rows), "" if len(new_rows) == 1 else "s", who_am_i())
        ok, code, err = put_file(ADDITIONS_PATH, text, blob_sha, msg)
        if ok:
            cleared = prune_queue(new_keys | dup_keys)
            say("push: %d assignment(s) added to %s; %d queue row(s) cleared.%s"
                % (len(new_rows), ADDITIONS_PATH, cleared,
                   " %d were already upstream." % len(dup_keys) if dup_keys else ""))
            return 0
        if code in (409, 422):
            # Somebody pushed between our read and our write. Re-read and redo the merge —
            # never force, never overwrite their rows.
            if attempt < MAX_RETRIES - 1:
                backoff(attempt)
                continue
            say("push: the branch moved under us %d times — %d row(s) stay queued and go up "
                "next run." % (MAX_RETRIES, len(rows)))
            return 0
        say("push: %s — %d row(s) stay queued. Nothing was lost." % (err or code, len(rows)))
        return 0
    return 0


def cmd_push(a):
    return do_push(quiet=False, dry_run=a.dry_run)


# ----------------------------------------------------------------------------- adopt

def slug(s):
    """lower-kebab, or "" — never a placeholder. A fabricated id is worse than a blank one."""
    return re.sub(r"[^a-z0-9]+", "-", str(s or "").lower()).strip("-")


def snapshot_user():
    """$PABAU_CLUSTER_USER, else git config user.email's localpart, else $USER — slugified.

    One file per user is what makes adoption conflict-free: two teammates adopting at the
    same moment write different paths and can never race each other.
    """
    v = (os.environ.get("PABAU_CLUSTER_USER") or "").strip()
    if v:
        return slug(v) or "unknown"
    try:
        out = subprocess.run(["git", "config", "user.email"], capture_output=True, text=True,
                             timeout=5)
        email = (out.stdout or "").strip()
        if email:
            return slug(email.split("@", 1)[0] if "@" in email else email) or "unknown"
    except Exception:
        pass
    return slug(os.environ.get("USER") or os.environ.get("LOGNAME") or "") or "unknown"


def workbook_rows():
    """The workbook as contract rows, or (None, why-not).

    cluster_store.read_workbook is the ONLY workbook reader in this codebase: it owns the
    column map, tier derivation off clusters.json, the "no path" -> null + depth_current_raw
    rule, and the column-shifted Review-queue rows. Rows the sheet leaves deliberately
    unassigned (the 60 regional /ae/, /au/ pages under rule R0b) are exported exactly as
    they are — an empty cluster is a valid row, not a corrupt one, and adopt never guesses.
    """
    if not os.path.exists(XLSX):
        return None, ("no workbook at %s — nothing to adopt (set $PABAU_CLUSTERS_XLSX if it "
                      "lives elsewhere)" % XLSX)
    if not STORE_OK:
        return None, ("cluster_store.py is missing, and adopt will not hand-roll a second "
                      "workbook parser. Re-run update.sh and try again.")
    try:
        wb = read_workbook(XLSX)
    except SystemExit:
        return None, "openpyxl is not installed: python3 -m pip install --user openpyxl"
    except Exception as e:
        return None, "could not read %s: %s" % (XLSX, e)
    if not wb or not wb.get("posts"):
        return None, "no Posts rows with a URL in %s" % XLSX
    rows = [canonical_row(r) for r in wb["posts"]]
    rows.sort(key=lambda r: r.get("url", ""))
    return rows, None


def diff_against_base(rows):
    """(new_urls, changed_urls) — what this workbook claims that base.jsonl does not.

    "Same assignment" is cluster_store.assignment_of: cluster_id, cluster, subcluster. Notes,
    flags and categories drift between machines and are not worth a snapshot push; a
    different cluster is exactly what consolidation needs to see.
    """
    base = {}
    for r in read_jsonl(local("base.jsonl")):
        base[normalize_url(r.get("url"))] = r
    new, changed = [], []
    for r in rows:
        u = r.get("url")
        b = base.get(u)
        if b is None:
            new.append(u)
        elif assignment_of(r) != assignment_of(b):
            changed.append(u)
    return new, changed


def read_adopt_state():
    try:
        with open(ADOPT_STATE, encoding="utf-8") as fh:
            return json.load(fh) or {}
    except Exception:
        return {}


def cmd_adopt(a):
    """One-time (and idempotent) export of this machine's workbook for consolidation."""
    rows, err = workbook_rows()
    if err:
        say("adopt: %s" % err)
        return 0
    if not rows:
        say("adopt: the workbook has no rows with a URL — nothing to adopt.")
        return 0

    user = a.user or snapshot_user()
    text = "".join(dumps_row(r) + "\n" for r in rows)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    repo_path = "clusters/snapshots/%s.jsonl" % user

    state = read_adopt_state()
    if state.get("sha256") == digest and state.get("path") == repo_path and not a.force:
        say("adopt: this workbook (%d rows) was already exported to %s on %s — no-op."
            % (len(rows), repo_path, state.get("at", "?")))
        return 0

    new, changed = diff_against_base(rows)
    have_base = os.path.exists(local("base.jsonl"))
    if have_base and not new and not changed and not a.force:
        say("adopt: the workbook (%d rows) agrees with base.jsonl — nothing to consolidate."
            % len(rows))
        atomic_write(ADOPT_STATE, json.dumps(
            {"sha256": digest, "path": repo_path, "user": user, "at": now_iso(),
             "rows": len(rows), "pushed": False}) + "\n")
        return 0

    say("adopt: %d rows; %d not in base.jsonl, %d disagree with it.%s"
        % (len(rows), len(new), len(changed),
           "" if have_base else "  (no local base.jsonl — run `pull` first for a real diff)"))
    if a.dry_run:
        out = a.out or os.path.join(FF, "cluster-snapshot-%s.jsonl" % user)
        atomic_write(out, text)
        say("adopt: --dry-run, snapshot written to %s (nothing pushed)." % out)
        return 0

    if not read_token():
        say("adopt: no token, so nothing was pushed. Set $PABAU_CLUSTERS_TOKEN or write it "
            "to %s, then re-run — this command is idempotent." % TOKEN_FILE)
        return 0

    if len(text.encode("utf-8")) > 40 * 1024 * 1024:
        say("adopt: the snapshot is over 40 MB — too big for the Contents API. Tell David; "
            "this needs the Git Data API instead.")
        return 0

    for attempt in range(MAX_RETRIES):
        listing = dir_listing("clusters/snapshots")
        if listing is None:
            say("adopt: could not reach the data branch — nothing pushed, re-run later.")
            return 0
        entry = listing.get("%s.jsonl" % user)
        ok, code, err = put_file(
            repo_path, text, entry.get("sha") if entry else None,
            "clusters: snapshot from %s (%d rows)" % (user, len(rows)))
        if ok:
            atomic_write(ADOPT_STATE, json.dumps(
                {"sha256": digest, "path": repo_path, "user": user, "at": now_iso(),
                 "rows": len(rows), "pushed": True}) + "\n")
            say("adopt: pushed %d rows to %s. That file is CONSOLIDATION INPUT ONLY — it is "
                "never read at runtime and changes nothing anyone resolves. Consolidation "
                "diffs it against base and surfaces the gaps as a conflict report for David."
                % (len(rows), repo_path))
            return 0
        if code in (409, 422) and attempt < MAX_RETRIES - 1:
            backoff(attempt)
            continue
        say("adopt: %s — nothing pushed, re-run later." % (err or code))
        return 0
    return 0


# ---------------------------------------------------------------------------- status

def file_rows(name):
    path = local(name)
    if not os.path.exists(path):
        return "missing"
    try:
        with open(path, encoding="utf-8") as fh:
            return count_of(name, fh.read())
    except Exception:
        return "unreadable"


def cmd_status(a):
    tok_src = {"env": "yes ($PABAU_CLUSTERS_TOKEN)",
               "file": "yes (%s)" % TOKEN_FILE}.get(token_source(), "NO")
    local_sha = ""
    try:
        with open(SHA_STATE) as fh:
            local_sha = fh.read().strip()
    except Exception:
        local_sha = ""
    remote = "" if a.offline else head_sha()
    queued = read_jsonl(QUEUE)
    adopt = read_adopt_state()

    info = {
        "repo": REPO, "branch": BRANCH, "store": DATA_DIR,
        "token": tok_src,
        "cluster_store": "ok" if STORE_OK else "missing",
        "local_sha": local_sha or "(never pulled)",
        "remote_sha": remote or ("(not checked)" if a.offline else "(unreachable)"),
        "in_sync": bool(remote and local_sha == remote),
        "queued": len(queued),
        "queue_path": QUEUE,
        "adopt_last_run": adopt.get("at", "never"),
        "adopt_pushed": adopt.get("pushed", False),
        "adopt_path": adopt.get("path", ""),
        "workbook": XLSX if os.path.exists(XLSX) else "(none)",
        "files": {n: file_rows(n) for _, n, _ in PULL_FILES},
    }
    if a.json:
        say(json.dumps(info, indent=2))
        return 0

    say("repo            : %s @ %s" % (REPO, BRANCH))
    say("store           : %s" % DATA_DIR)
    say("token present   : %s" % tok_src)
    say("cluster_store   : %s" % ("ok" if STORE_OK else "MISSING — running degraded"))
    say("local data sha  : %s" % info["local_sha"])
    say("remote head sha : %s%s" % (info["remote_sha"],
                                    "   << behind, run `pull`" if remote and local_sha
                                    and local_sha != remote else ""))
    say("queued rows     : %d  (%s)" % (len(queued), QUEUE))
    for r in queued[:10]:
        say("   %s -> %s / %s  [%s]" % (r.get("url"), r.get("cluster"),
                                        r.get("subcluster") or "—", r.get("assigned_at")))
    if len(queued) > 10:
        say("   ... and %d more" % (len(queued) - 10))
    say("adopt last run  : %s%s" % (adopt.get("at", "never"),
                                    "" if not adopt else
                                    ("  -> %s (%s)" % (adopt.get("path", "?"),
                                                       "pushed" if adopt.get("pushed")
                                                       else "not pushed"))))
    if adopt.get("pushed"):
        say("                  (a snapshot is consolidation input only — never read at "
            "runtime)")
    say("local workbook  : %s" % info["workbook"])
    for _, n, _ in PULL_FILES:
        say("   %-18s %s" % (n, info["files"][n]))
    if not remote and not a.offline:
        say("NOTE: could not reach GitHub — every read fell back to what is on disk.")
    return 0


# ------------------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("pull", help="fetch the central store (gated on the branch sha)")
    p.add_argument("--force", action="store_true", help="refetch even if the sha is unchanged")
    p.add_argument("--quiet", action="store_true", help="say nothing when already in sync")
    p.set_defaults(fn=cmd_pull)

    p = sub.add_parser("submit", help="queue ONE reasoned assignment, then try to push it")
    p.add_argument("--url", required=True)
    p.add_argument("--cluster-id", required=True, help="the slug id, e.g. med-spa-aesthetics")
    p.add_argument("--subcluster", default="")
    p.add_argument("--cluster", default="", help="cluster NAME; derived from the store if omitted")
    p.add_argument("--title", default="")
    p.add_argument("--intent", default="", choices=["", "TOFU", "MOFU", "BOFU", "JTBD",
                                                    "tofu", "mofu", "bofu", "jtbd"])
    p.add_argument("--rule", default="", help="the rule that produced it, e.g. 'R4 industry'")
    p.add_argument("--published", default="")
    p.add_argument("--assigned-by", default="", help="defaults to $PABAU_CLUSTER_USER/$USER")
    p.add_argument("--evidence-json", default="", help="the `suggest` output as JSON")
    p.add_argument("--evidence-file", default="", help="same, from a file ('-' for stdin)")
    p.add_argument("--no-push", action="store_true", help="queue only, never touch the network")
    p.add_argument("--force", action="store_true",
                   help="DAVID ONLY: queue even though a human assignment exists")
    p.set_defaults(fn=cmd_submit)

    p = sub.add_parser("push", help="drain the queue into clusters/additions.jsonl")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(fn=cmd_push)

    p = sub.add_parser("adopt", help="export this machine's workbook to clusters/snapshots/")
    p.add_argument("--user", default="", help="override the snapshot name")
    p.add_argument("--dry-run", action="store_true", help="write the snapshot locally only")
    p.add_argument("--out", default="", help="where --dry-run writes it")
    p.add_argument("--force", action="store_true", help="push even if nothing changed")
    p.set_defaults(fn=cmd_adopt)

    p = sub.add_parser("status", help="token, shas, queue depth, row counts")
    p.add_argument("--json", action="store_true")
    p.add_argument("--offline", action="store_true", help="skip the remote sha check")
    p.set_defaults(fn=cmd_status)

    a = ap.parse_args()
    if not getattr(a, "fn", None):
        ap.print_help()
        sys.exit(2)
    try:
        sys.exit(a.fn(a) or 0)
    except SystemExit:
        raise
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as e:
        # Last line of defence. This runs inside a /fact run; it does not get to crash one.
        warn("unexpected failure (%s: %s) — nothing was lost, the queue is on disk."
             % (type(e).__name__, e))
        sys.exit(0)


if __name__ == "__main__":
    main()
