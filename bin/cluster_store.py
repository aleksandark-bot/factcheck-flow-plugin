#!/usr/bin/env python3
"""The central cluster store — loading, merging and exporting cluster assignments.

This module owns the data layer described by `clusters/CONTRACT.md`. Everything that
needs to know which cluster a URL belongs to reads it through `load_store()`; nothing
else parses the workbook or the JSONL files by hand.

    from cluster_store import normalize_url, load_store, effective_cluster
    store = load_store()
    store["posts"]["https://pabau.com/blog/dermatology-marketing-ideas/"]["cluster_id"]

`normalize_url()` is THE url normalizer for the whole system. `cluster_lookup.py` keeps
its own `norm()` as a thin wrapper over it, so the two can never drift.

`load_store()` merges base.jsonl + additions.jsonl + the local workbook + this machine's
own unpushed submit queue, and NOTHING else.
`clusters/snapshots/*.jsonl` are consolidation input only — `load_snapshots()` is their one
entry point and only `cluster_consolidate.py` calls it (CONTRACT.md, "SNAPSHOTS").

Commands
  export   --out DIR [--xlsx F]    workbook -> base.jsonl, clusters.json,
                                   review-queue.json, MANIFEST.json
  resolve  --url URL               the effective merged row for one url
  stats    [--data DIR]            what loaded, what it merged, what collided
  verify   [--sample N]            compare this store against cluster_lookup.py `resolve`

Data (override with env vars):
  $PABAU_CLUSTERS_XLSX   else ~/Desktop/pabau-content-clusters.xlsx   (local workbook)
  $PABAU_FACTCHECK_DIR   else ~/.claude/factcheck-flow    (local install root: cache,
                         synced files and the submit queue all hang off it)
  $PABAU_CLUSTERS_DIR    else <$PABAU_FACTCHECK_DIR>/clusters,
                         else <repo>/clusters                          (synced data files)
  $PABAU_CLUSTER_QUEUE   else <$PABAU_FACTCHECK_DIR>/cluster-queue.jsonl  (submit queue)

Exit codes: 0 ok; 2 setup/data error; 1 only from `verify` when the comparison fails.
"""
import argparse
import hashlib
import json
import os
import re
import sys
import time

HOME = os.path.expanduser("~")
# $PABAU_FACTCHECK_DIR moves the WHOLE local install — cache, synced files and the write
# queue together. cluster_sync.py honours it; so does this module, or a sandboxed or
# relocated install reads one place and writes another.
FF_DIR = os.environ.get("PABAU_FACTCHECK_DIR") or os.path.join(
    HOME, ".claude", "factcheck-flow")
XLSX = os.environ.get("PABAU_CLUSTERS_XLSX") or os.path.join(
    HOME, "Desktop", "pabau-content-clusters.xlsx")
CACHE_DIR = os.path.join(FF_DIR, "cache")

# cluster_sync.py `submit` appends here BEFORE it touches the network, and rows sit here
# until a run with a working token drains them (CONTRACT.md "Write path" step 3). It is a
# read-path input for exactly that reason: on a token-less machine — the default teammate
# state — this is the only place the assignment exists, and the run that reasoned it must
# be able to see it. Merged at `reasoned` authority, below everything in the store.
QUEUE_PATH = os.environ.get("PABAU_CLUSTER_QUEUE") or os.path.join(
    FF_DIR, "cluster-queue.jsonl")

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_CLUSTERS = os.path.join(os.path.dirname(_HERE), "clusters")
_INSTALLED_CLUSTERS = os.path.join(FF_DIR, "clusters")

CODE_FOLDERS = ("/procedure-codes/", "/diagnostic-codes/")
BILLING_CLUSTER_ID = "billing-coding-claims"

STORE_VERSION = 1
# Bump when the shape of what gets cached changes, so stale cache files are ignored.
CACHE_EPOCH = 2

try:  # this output gets piped to head a lot; die quietly when it does
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (ImportError, AttributeError, ValueError):
    pass


class WorkbookUnavailable(Exception):
    """The local workbook exists but cannot be parsed — no openpyxl, corrupt file, bad
    permissions, anything.

    It is an exception and NOT a die(): on the read path an unreadable workbook degrades
    to the synced store, which is a complete copy of it. Killing every cluster command
    because one optional input is unreadable breaks the contract's non-negotiable —
    "Fail-silent on the read path ... must never block a /fact run". Only `export`, whose
    whole job IS the workbook, turns this back into a fatal error.
    """


def die(msg):
    sys.stderr.write("CLUSTER STORE ERROR: " + msg + "\n")
    sys.exit(2)


def warn(msg):
    sys.stderr.write("CLUSTER STORE WARN: " + msg + "\n")


# --------------------------------------------------------------------------- URLs

def normalize_url(u):
    """Canonical form: https://pabau.com/<folder>/<slug>/ — lowercased, no query, no
    fragment, no www, exactly one trailing slash.

    THE single implementation. Identical in behaviour to `cluster_lookup.norm()`; when
    that script is refactored onto this module the assignments must not move, so any
    change here is a change to the data contract and belongs in CONTRACT.md first.
    """
    if not u:
        return ""
    u = str(u).strip()
    u = u.split("#")[0].split("?")[0]
    u = re.sub(r"^https?://", "", u, flags=re.I)
    u = re.sub(r"^www\.", "", u, flags=re.I)
    u = u.rstrip("/")
    return "https://" + u.lower() + "/" if u else ""


norm = normalize_url  # the name cluster_lookup.py uses


def folder_of(u):
    m = re.match(r"^https://[^/]+(/[^/]+/)", normalize_url(u))
    return m.group(1) if m else "/"


def slug_of(u):
    p = normalize_url(u).rstrip("/").split("/")
    return p[-1] if p else ""


# ---------------------------------------------------------------------- row schema

# CONTRACT.md "Row schema", in the order the contract lists them. base.jsonl writes the
# keys in exactly this order so a diff of two exports is readable.
ROW_KEYS = [
    "url", "title", "cluster", "cluster_id", "tier", "subcluster", "published",
    "rule_applied", "secondary_tag", "flag", "note", "wp_categories", "source_sheet",
    "intent", "silo_source", "depth_target", "depth_current", "in_scope", "exclusion",
    "assigned_by", "assigned_at", "evidence",
]
INT_KEYS = ("depth_target", "depth_current")
REASONED_KEYS = ("assigned_by", "assigned_at", "evidence")

# CONTRACT.md "PROVENANCE": lowest number wins. An unrecognised silo_source ranks with
# interlinking-v4 — every non-enum value in the workbook today ("assigned:high",
# "R3 nearest-neighbour vote", "R0a excluded (/lp/)") is one of that project's own
# labels, and a machine label must never outrank a human one.
AUTHORITY = {"human": 0, "spreadsheet": 1, "interlinking-v4": 2, "reasoned": 3}
UNKNOWN_AUTHORITY = 2

# Tie-break at equal authority: which input stream the row came from. Lower wins. The
# contract's read path puts the local workbook above everything, and base above the
# append-only streams. The local queue ranks last: it is this machine's own unpushed
# scratch, so at equal authority anything already in the store beats it.
QUEUE_STREAM = "local-queue (unpushed)"
STREAM_RANK = {"xlsx": 0, "base": 1, "additions": 2, "snapshot": 3, QUEUE_STREAM: 4}


def authority_of(row):
    return AUTHORITY.get((row.get("silo_source") or "").strip().lower(),
                         UNKNOWN_AUTHORITY)


def _s(v):
    """Sheet cell -> contract string. openpyxl hands back None for an empty cell."""
    if v is None:
        return ""
    return str(v).strip()


def _i(v):
    """Sheet cell -> contract int|null. Non-numeric text ("no path") becomes null; the
    caller keeps the original in an extra key so nothing is dropped."""
    if v is None or v == "":
        return None
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def canonical_row(d):
    """Order the keys per the contract, coerce the typed ones, keep unknown keys.

    Forward compatibility is a contract requirement: a key this version has never heard
    of is preserved (sorted, after the known ones) rather than dropped.
    """
    out = {}
    for k in ROW_KEYS:
        if k not in d:
            continue
        v = d[k]
        if k in INT_KEYS:
            out[k] = v if isinstance(v, int) or v is None else _i(v)
        elif k == "evidence":
            out[k] = v
        else:
            out[k] = "" if v is None else str(v)
    for k in sorted(d):
        if k not in out and k not in ROW_KEYS:
            out[k] = d[k]
    return out


def row_json(row):
    """One base.jsonl line. Deterministic: contract key order, no spaces after the
    separators, UTF-8 kept as UTF-8 so the file is greppable."""
    return json.dumps(canonical_row(row), ensure_ascii=False,
                      separators=(",", ":"), sort_keys=False)


def assignment_of(row):
    """What two rows have to agree on before we call them the same assignment."""
    return ((row.get("cluster_id") or "").strip().lower(),
            (row.get("cluster") or "").strip().lower(),
            (row.get("subcluster") or "").strip().lower())


# -------------------------------------------------------------------------- caching

def _stat_key(paths):
    """(mtime, size) of every input, hashed. A refreshed input invalidates the cache
    automatically — the same rule `cluster_lookup._cache_path` uses, widened from one
    file to the whole input set."""
    parts = []
    for p in paths:
        try:
            st = os.stat(p)
            parts.append("%s:%d:%d" % (p, int(st.st_mtime), st.st_size))
        except OSError:
            parts.append("%s:missing" % p)
    return hashlib.sha256("|".join(parts).encode("utf-8")).hexdigest()[:20]


def _cache_path(paths, tag):
    return os.path.join(CACHE_DIR, "%s-v%d-%s.json" % (tag, CACHE_EPOCH, _stat_key(paths)))


def _load_cached(paths, tag, build):
    path = _cache_path(paths, tag)
    try:
        with open(path) as fh:
            return json.load(fh)
    except Exception:
        pass
    data = build()
    try:
        os.makedirs(CACHE_DIR, exist_ok=True)
        tmp = path + ".tmp%d" % os.getpid()
        with open(tmp, "w") as fh:
            json.dump(data, fh)
        os.replace(tmp, path)
    except Exception:
        pass
    return data


# ---------------------------------------------------------------------- data dir

def default_data_dir():
    """The synced data files: the installed copy first (that is what a teammate has),
    the repo working copy second (that is what David has)."""
    env = os.environ.get("PABAU_CLUSTERS_DIR")
    if env:
        return env
    if os.path.isdir(_INSTALLED_CLUSTERS):
        return _INSTALLED_CLUSTERS
    return _REPO_CLUSTERS


def data_files(data_dir):
    """Every file load_store reads out of the data dir, in stream order."""
    snaps = []
    snap_dir = os.path.join(data_dir, "snapshots")
    try:
        snaps = sorted(os.path.join(snap_dir, f) for f in os.listdir(snap_dir)
                       if f.endswith(".jsonl"))
    except OSError:
        pass
    return {
        "base": os.path.join(data_dir, "base.jsonl"),
        "additions": os.path.join(data_dir, "additions.jsonl"),
        "clusters": os.path.join(data_dir, "clusters.json"),
        "review": os.path.join(data_dir, "review-queue.json"),
        "manifest": os.path.join(data_dir, "MANIFEST.json"),
        "snapshots": snaps,
    }


# -------------------------------------------------------------------- the workbook

def _sheet_rows(wb, name):
    if name not in wb.sheetnames:
        return []
    ws = wb[name]
    it = ws.iter_rows(values_only=True)
    try:
        hdr = [str(h).strip() if h is not None else "" for h in next(it)]
    except StopIteration:
        return []
    rows = []
    for r in it:
        if all(c is None for c in r):
            continue
        rows.append(dict(zip(hdr, r)))
    return rows


def _split_pages(cell):
    """The Clusters sheet packs several URLs into one cell. Same splitter
    `cluster_lookup._split_pages` uses, so the cluster records match."""
    if not cell:
        return []
    s = re.sub(r"^\s*Existing children:\s*", "", str(cell), flags=re.I)
    out = []
    for part in re.split(r"[·|,\n]", s):
        p = part.strip()
        if not p or p in ("—", "-", "— (none)", "(none)"):
            continue
        out.append(p)
    return out


# Posts sheet header -> contract row key. Every one of the 18 columns is mapped; the
# exporter fails loudly if the sheet grows a column this table does not know.
POSTS_COLUMNS = {
    "URL": "url",
    "Post title": "title",
    "Cluster": "cluster",
    "Tier": "tier",
    "Subcluster": "subcluster",
    "Published": "published",
    "Rule applied": "rule_applied",
    "Secondary tag": "secondary_tag",
    "Flag / needs review": "flag",
    "Note": "note",
    "Current WP categories": "wp_categories",
    "Source sheet (old cluster)": "source_sheet",
    "Intent": "intent",
    "Silo source": "silo_source",
    "Depth target": "depth_target",
    "Depth (current)": "depth_current",
    "In scope": "in_scope",
    "Exclusion": "exclusion",
}


def read_workbook(xlsx_path=None):
    """Parse the workbook into {clusters, posts, review, unmapped_columns, warnings}.

    Posts rows come back as contract rows (canonical key order, cluster_id and tier
    resolved off the Clusters sheet). Cached on (mtime, size) of the workbook.
    """
    path = xlsx_path or XLSX
    if not os.path.exists(path):
        return None

    def build():
        try:
            import openpyxl
        except Exception as e:
            raise WorkbookUnavailable(
                "openpyxl is not installed (%s), so %s cannot be read. Install it with "
                "`python3 -m pip install --user openpyxl` to edit assignments in the "
                "workbook; the synced store is used until then." % (e, path))
        try:
            wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        except Exception as e:
            raise WorkbookUnavailable("could not open %s (%s)" % (path, e))
        warnings = []

        clusters = []
        for r in _sheet_rows(wb, "Clusters"):
            cid = _s(r.get("Cluster ID"))
            if not cid:
                continue
            clusters.append({
                "n": r.get("#"),
                "id": cid,
                "name": _s(r.get("Cluster name")),
                "tier": _s(r.get("Tier")),
                "pillar_name": _s(r.get("PILLAR PAGE (name)")),
                "pillar_url": _s(r.get("Pillar page URL")),
                "pillar_status": _s(r.get("Pillar status / action")),
                "supporting": _split_pages(r.get("Supporting pages")),
                "subclusters": _split_pages(r.get("Subclusters covered")),
                "posts": r.get("Posts"),
                "md_count": r.get(".md count"),
            })
        by_name = {c["name"].lower(): c for c in clusters if c["name"]}

        posts, unmapped, seen = [], set(), {}
        for r in _sheet_rows(wb, "Posts"):
            for col in r:
                if col and col not in POSTS_COLUMNS:
                    unmapped.add(col)
            u = normalize_url(r.get("URL"))
            if not u:
                continue
            row = {"url": u}
            for col, key in POSTS_COLUMNS.items():
                if key == "url":
                    continue
                if key in INT_KEYS:
                    raw = r.get(col)
                    row[key] = _i(raw)
                    if row[key] is None and _s(raw):
                        # "no path" and friends: the contract types this int|null, so the
                        # original text rides along in an extra key rather than vanishing.
                        row[key + "_raw"] = _s(raw)
                elif key == "published":
                    row[key] = _s(r.get(col))[:10]
                else:
                    row[key] = _s(r.get(col))
            cl = by_name.get(row["cluster"].lower())
            row["cluster_id"] = cl["id"] if cl else ""
            if cl:
                # "Derived from clusters.json; never authored independently."
                if row["tier"] and row["tier"] != cl["tier"]:
                    warnings.append(
                        "tier mismatch on %s: sheet %r vs cluster %r — using the cluster's"
                        % (u, row["tier"], cl["tier"]))
                row["tier"] = cl["tier"]
            elif row["cluster"]:
                warnings.append("unknown cluster name %r on %s" % (row["cluster"], u))
            if not row.get("silo_source"):
                row["silo_source"] = "spreadsheet"
            if u in seen:
                warnings.append("duplicate url after normalization: %s" % u)
            seen[u] = True
            posts.append(canonical_row(row))

        review = []
        for r in _sheet_rows(wb, "Review queue"):
            u = normalize_url(r.get("URL"))
            decision = _s(r.get("Decision needed"))
            assigned = _s(r.get("Cluster as assigned"))
            shifted = False
            if not u and decision.lower().startswith("http"):
                # Eight rows in the sheet are shifted one column left: the url sits in
                # "Decision needed" and the decision in "Cluster as assigned". They are
                # the non-English exclusions. Recover them rather than dropping them.
                u, decision, assigned, shifted = normalize_url(decision), assigned, "", True
            if not u:
                continue
            entry = {
                "url": u,
                "title": _s(r.get("Post title")),
                "decision": decision,
                "cluster_as_assigned": assigned,
                "rule": _s(r.get("Rule applied")),
                "note": _s(r.get("Note")),
            }
            if shifted:
                entry["sheet_row_shifted"] = True
                warnings.append("Review queue row for %s is column-shifted in the sheet "
                                "— recovered" % u)
            review.append(entry)

        if unmapped:
            warnings.append("Posts sheet has unmapped columns: %s"
                            % ", ".join(sorted(unmapped)))
        posts.sort(key=lambda p: p["url"])
        review.sort(key=lambda p: p["url"])
        return {"clusters": clusters, "posts": posts, "review": review,
                "unmapped_columns": sorted(unmapped), "warnings": warnings,
                "built": time.strftime("%Y-%m-%d %H:%M")}

    return _load_cached([path], "cluster-store-xlsx", build)


# --------------------------------------------------------------------- JSONL files

def read_jsonl(path, warnings, label):
    """Fail-soft: a corrupt line is skipped with a warning, a missing file is empty."""
    rows = []
    if not os.path.exists(path):
        return rows
    try:
        with open(path, encoding="utf-8") as fh:
            for n, line in enumerate(fh, 1):
                line = line.strip()
                if not line or line.startswith("//"):
                    continue
                try:
                    d = json.loads(line)
                except ValueError as e:
                    warnings.append("%s line %d is not valid JSON (%s) — skipped"
                                    % (label, n, e))
                    continue
                if not isinstance(d, dict):
                    warnings.append("%s line %d is not an object — skipped" % (label, n))
                    continue
                u = normalize_url(d.get("url"))
                if not u:
                    warnings.append("%s line %d has no url — skipped" % (label, n))
                    continue
                d["url"] = u
                rows.append(d)
    except Exception as e:  # unreadable file, bad encoding, anything
        warnings.append("could not read %s (%s) — continuing without it" % (label, e))
    return rows


def read_json(path, warnings, label, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception as e:
        warnings.append("could not read %s (%s) — continuing without it" % (label, e))
        return default


# ----------------------------------------------------------------------- the merge

def _better(a, b):
    """Is candidate `a` the row that should win over the incumbent `b`?

    CONTRACT.md precedence: human > spreadsheet > interlinking-v4 > reasoned; between two
    reasoned rows the earliest assigned_at wins (first writer wins keeps the store stable);
    otherwise the higher-priority input stream wins, and a true tie keeps the incumbent.
    """
    ra, rb = authority_of(a), authority_of(b)
    if ra != rb:
        return ra < rb
    if ra == AUTHORITY["reasoned"]:
        ta = (a.get("assigned_at") or "~")
        tb = (b.get("assigned_at") or "~")
        if ta != tb:
            return ta < tb
    sa = STREAM_RANK.get(a.get("_stream"), 9)
    sb = STREAM_RANK.get(b.get("_stream"), 9)
    return sa < sb


def _merge_rows(streams, meta):
    """streams: [(stream_name, [row, ...]), ...] in any order. Returns {url: row}.

    Every url where two sources disagree about the assignment lands in meta["collisions"]
    — resolved by precedence, never dropped.
    """
    posts, origin = {}, {}
    for stream, rows in streams:
        for raw in rows:
            row = canonical_row(raw)
            row["_stream"] = stream
            u = row["url"]
            cur = posts.get(u)
            if cur is None:
                posts[u] = row
                origin[u] = stream
                continue
            if assignment_of(row) != assignment_of(cur):
                ra, rb = authority_of(row), authority_of(cur)
                winner = row if _better(row, cur) else cur
                loser = cur if winner is row else row
                meta["collisions"].append({
                    "url": u,
                    "severity": "conflict" if ra == rb else "informational",
                    "winner": {
                        "stream": winner.get("_stream"),
                        "silo_source": winner.get("silo_source", ""),
                        "cluster": winner.get("cluster", ""),
                        "cluster_id": winner.get("cluster_id", ""),
                        "subcluster": winner.get("subcluster", ""),
                        "assigned_by": winner.get("assigned_by", ""),
                        "assigned_at": winner.get("assigned_at", ""),
                    },
                    "loser": {
                        "stream": loser.get("_stream"),
                        "silo_source": loser.get("silo_source", ""),
                        "cluster": loser.get("cluster", ""),
                        "cluster_id": loser.get("cluster_id", ""),
                        "subcluster": loser.get("subcluster", ""),
                        "assigned_by": loser.get("assigned_by", ""),
                        "assigned_at": loser.get("assigned_at", ""),
                        "evidence": loser.get("evidence"),
                    },
                })
            if _better(row, posts[u]):
                posts[u] = row
                origin[u] = stream
    for u, row in posts.items():
        row.pop("_stream", None)
        row["_source_stream"] = origin[u]
    return posts


def read_queue(path, warnings):
    """The local, not-yet-pushed submit queue as `reasoned` rows. Never raises.

    Every row is forced to `reasoned` authority whatever its silo_source says. The queue
    is a local file an agent appends to during a run; it must never be able to outrank a
    human assignment just because somebody edited a line in it.
    """
    rows = []
    for r in read_jsonl(path, warnings, "cluster-queue.jsonl"):
        if not (r.get("cluster") or r.get("cluster_id")):
            warnings.append("cluster-queue.jsonl row for %s has no cluster — skipped"
                            % r.get("url"))
            continue
        if authority_of(r) != AUTHORITY["reasoned"]:
            warnings.append("cluster-queue.jsonl row for %s claims silo_source %r — a "
                            "queued row is always read as `reasoned`"
                            % (r.get("url"), r.get("silo_source")))
            r["silo_source"] = "reasoned"
        rows.append(r)
    return rows


def load_store(xlsx_path=None, data_dir=None, queue_path=None):
    """The merged index every consumer reads.

    Returns {"posts": {url: row}, "clusters": {...}, "review": {...}, "meta": {...}}.

      posts     url -> the effective contract row, precedence already applied
      clusters  {"by_id": {...}, "by_name": {...}, "list": [...]}
      review    url -> the review-queue entry
      meta      inputs, counts, warnings, collisions, built

    Inputs: base.jsonl, additions.jsonl, the local workbook, and this machine's own
    unpushed submit queue (`reasoned` authority, ranked last, labelled
    `_source_stream: local-queue (unpushed)`).

    Never raises. A missing or corrupt input — including a workbook this machine cannot
    parse — degrades to whatever else is available and says so in meta["warnings"]. The
    read path must never block a /fact run; the only hard stop is nothing being readable
    at all, and that one belongs to the caller (`cluster_lookup.load_sheet`).
    """
    data_dir = data_dir or default_data_dir()
    xlsx_path = xlsx_path or XLSX
    queue_path = queue_path or QUEUE_PATH
    files = data_files(data_dir)
    # Snapshots are deliberately NOT here. They are not read, so they must not invalidate
    # the cache either — a teammate dropping a snapshot in must not rebuild every index.
    # The queue IS here: a `submit` during a run has to be visible to the rest of it.
    inputs = [files["base"], files["additions"], files["clusters"], files["review"],
              files["manifest"], xlsx_path, queue_path]

    def build():
        meta = {
            "version": STORE_VERSION,
            "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "data_dir": data_dir,
            "xlsx": xlsx_path,
            "inputs": {},
            "counts": {},
            "warnings": [],
            "collisions": [],
        }
        warnings = meta["warnings"]

        base_rows = read_jsonl(files["base"], warnings, "base.jsonl")
        add_rows = read_jsonl(files["additions"], warnings, "additions.jsonl")
        queue_rows = read_queue(queue_path, warnings)
        # clusters/snapshots/*.jsonl are NOT read here. See load_snapshots() below and
        # CONTRACT.md "SNAPSHOTS — consolidation input only, never a read-path source".

        cl_doc = read_json(files["clusters"], warnings, "clusters.json", None)
        rq_doc = read_json(files["review"], warnings, "review-queue.json", None)
        manifest = read_json(files["manifest"], warnings, "MANIFEST.json", None)

        sheet = None
        try:
            sheet = read_workbook(xlsx_path)
        except (WorkbookUnavailable, SystemExit, Exception) as e:
            # An unreadable workbook is a DEGRADATION, never a stop. base.jsonl is an
            # export of that same workbook, so the run keeps every assignment it had —
            # it just cannot see edits made in the sheet since the last export. Dying
            # here (which is what a missing openpyxl used to do) blocked every cluster
            # command on a machine holding the whole store, and reported LINKPLAN_BLOCKED.
            warnings.append("could not read the workbook %s (%s) — continuing on the "
                            "synced files alone" % (xlsx_path, e))
        xlsx_rows = []
        if sheet:
            xlsx_rows = sheet["posts"]
            warnings.extend(sheet.get("warnings") or [])
        elif not os.path.exists(xlsx_path):
            warnings.append("no local workbook at %s — reading the synced files only"
                            % xlsx_path)

        # Clusters: the workbook is the authoring surface, clusters.json the synced copy.
        clusters = []
        if sheet and sheet["clusters"]:
            clusters = sheet["clusters"]
        elif isinstance(cl_doc, dict) and isinstance(cl_doc.get("clusters"), list):
            clusters = cl_doc["clusters"]
        elif isinstance(cl_doc, list):
            clusters = cl_doc
        else:
            warnings.append("no cluster definitions available (neither the workbook nor "
                            "clusters.json) — tier and pillar lookups will be empty")

        review = {}
        rq_rows = []
        if isinstance(rq_doc, dict) and isinstance(rq_doc.get("rows"), list):
            rq_rows = rq_doc["rows"]
        elif isinstance(rq_doc, list):
            rq_rows = rq_doc
        if sheet and sheet["review"]:
            rq_rows = sheet["review"]
        for r in rq_rows:
            if not isinstance(r, dict):
                continue
            u = normalize_url(r.get("url"))
            if u:
                review[u] = r

        # Stream order only matters for tie-breaks; _better() does the deciding.
        # No "snapshot" stream: a snapshot is one teammate's possibly-stale local workbook,
        # and merging it here would let their drift win at equal authority and propagate to
        # everyone. Snapshots reach base.jsonl only through cluster_consolidate.py.
        # The queue is merged LAST and ranks last: a locally queued row fills a gap, it
        # never displaces a row the store already holds. It is `reasoned`, so it cannot
        # reach a human or spreadsheet assignment at all, and a url that also arrives from
        # the branch is deduped by url like any other — the branch copy wins the tie.
        posts = _merge_rows([
            ("base", base_rows),
            ("additions", add_rows),
            (QUEUE_STREAM, queue_rows),
            ("xlsx", xlsx_rows),
        ], meta)

        for label, path in (("base", files["base"]), ("additions", files["additions"]),
                            ("clusters", files["clusters"]), ("review", files["review"]),
                            ("manifest", files["manifest"]), ("xlsx", xlsx_path),
                            ("queue", queue_path)):
            try:
                st = os.stat(path)
                meta["inputs"][label] = {"path": path, "present": True,
                                         "mtime": int(st.st_mtime), "size": st.st_size}
            except OSError:
                meta["inputs"][label] = {"path": path, "present": False}
        # Listed for visibility only — present on disk, never merged (see load_snapshots).
        meta["inputs"]["snapshots"] = [os.path.basename(p) for p in files["snapshots"]]
        meta["inputs"]["snapshots_merged"] = False
        meta["counts"] = {
            "posts": len(posts),
            "base": len(base_rows),
            "additions": len(add_rows),
            "queue": len(queue_rows),
            "snapshots": 0,
            "xlsx": len(xlsx_rows),
            "clusters": len(clusters),
            "review": len(review),
            "collisions": len(meta["collisions"]),
            "conflicts": sum(1 for c in meta["collisions"]
                             if c["severity"] == "conflict"),
        }
        meta["manifest"] = manifest if isinstance(manifest, dict) else None

        by_id, by_name = {}, {}
        for c in clusters:
            if c.get("id"):
                by_id[str(c["id"]).lower()] = c
            if c.get("name"):
                by_name[str(c["name"]).lower()] = c
        return {"posts": posts,
                "clusters": {"list": clusters, "by_id": by_id, "by_name": by_name},
                "review": review, "meta": meta}

    try:
        return _load_cached(inputs, "cluster-store-index", build)
    except (SystemExit, Exception) as e:  # last-ditch: never raise on the read path
        return {"posts": {}, "clusters": {"list": [], "by_id": {}, "by_name": {}},
                "review": {},
                "meta": {"version": STORE_VERSION, "counts": {}, "collisions": [],
                         "warnings": ["load_store failed entirely (%s) — empty store" % e]}}


def load_snapshots(data_dir=None, warnings=None):
    """Every `clusters/snapshots/*.jsonl` row, grouped by file. CONSOLIDATION ONLY.

    Returns [(label, path, [row, ...]), ...] sorted by filename — never a merged index,
    because merging is exactly what a snapshot must not get. A snapshot is one teammate's
    possibly-stale, possibly-hand-edited workbook; `load_store()` does not read it, and no
    agent's `resolve` may ever see it. Its claims reach base.jsonl only by passing through
    `cluster_consolidate.py` and David's judgment (CONTRACT.md, "SNAPSHOTS").

    `warnings` is an optional list that malformed-line notes are appended to. Never raises.
    """
    data_dir = data_dir or default_data_dir()
    if warnings is None:
        warnings = []
    out = []
    for p in data_files(data_dir)["snapshots"]:
        label = "snapshots/" + os.path.basename(p)
        out.append((label, p, read_jsonl(p, warnings, label)))
    return out


# ------------------------------------------------------------------ read helpers

def cluster_by_name(store, name):
    return store["clusters"]["by_name"].get((name or "").strip().lower())


def cluster_by_key(store, key):
    key = (key or "").strip().lower()
    c = store["clusters"]["by_id"].get(key) or store["clusters"]["by_name"].get(key)
    if c:
        return c
    for c in store["clusters"]["list"]:
        if key and (key in str(c.get("id", "")).lower()
                    or key in str(c.get("name", "")).lower()):
            return c
    return None


def effective_cluster(store, url):
    """The cluster record for a url, by the same three steps `cluster_lookup.resolve`
    takes: the row, then the review queue, then the code-folder fallback (a code page
    published after the snapshot is still billing — rule A)."""
    u = normalize_url(url)
    row = store["posts"].get(u)
    cl = cluster_by_name(store, row["cluster"]) if row and row.get("cluster") else None
    if not cl:
        rq = store["review"].get(u)
        if rq:
            cl = cluster_by_name(store, rq.get("cluster_as_assigned"))
    if not cl and folder_of(u) in CODE_FOLDERS:
        cl = cluster_by_key(store, BILLING_CLUSTER_ID)
    return cl


# The shape `cluster_lookup.load_sheet()` returns today. Phase 2 refactors that script
# onto this module and its seven commands must keep byte-identical output, so the store
# hands back the legacy record shape rather than making the caller rename keys.
LEGACY_CLUSTER_KEYS = ("n", "id", "name", "tier", "pillar_name", "pillar_url",
                       "pillar_status", "supporting", "subclusters", "posts")


def legacy_sheet(store):
    """`load_store()` output re-shaped as `cluster_lookup.load_sheet()` returns it."""
    posts = {}
    for u, r in store["posts"].items():
        posts[u] = {
            "url": u,
            "cluster_name": r.get("cluster", ""),
            "tier": r.get("tier", ""),
            "subcluster": r.get("subcluster", ""),
            "title": r.get("title", ""),
            "published": r.get("published", ""),
            "rule": r.get("rule_applied", ""),
            "flag": r.get("flag", ""),
            "note": r.get("note", ""),
            "categories": r.get("wp_categories", ""),
        }
    review = {}
    for u, r in store["review"].items():
        review[u] = {
            "decision": r.get("decision", ""),
            "cluster_as_assigned": r.get("cluster_as_assigned", ""),
            "rule": r.get("rule", ""),
            "note": r.get("note", ""),
        }
    # Every legacy key is always present: `cluster_lookup.py` subscripts these records
    # directly (c["pillar_name"]), so a cluster definition that happens to omit a key —
    # a hand-written or older clusters.json — would crash the link pass rather than
    # degrade. The list-valued keys default to [], the rest to "".
    clusters = [dict({k: ([] if k in ("supporting", "subclusters") else "")
                      for k in LEGACY_CLUSTER_KEYS},
                     **{k: c[k] for k in LEGACY_CLUSTER_KEYS if k in c})
                for c in store["clusters"]["list"]]
    return {"clusters": clusters, "posts": posts, "review": review,
            "built": store["meta"].get("built", "")}


# -------------------------------------------------------------------- the exporter

def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _write(path, text):
    tmp = path + ".tmp%d" % os.getpid()
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    os.replace(tmp, path)


def export(xlsx_path, out_dir):
    """Workbook -> the four canonical files. Deterministic: base.jsonl sorted by url with
    the contract's key order, so two exports of the same workbook diff to nothing.

    This is the one place an unreadable workbook is still fatal: export IS the workbook.
    """
    try:
        sheet = read_workbook(xlsx_path)
    except WorkbookUnavailable as e:
        die(str(e))
    if sheet is None:
        die("workbook not found at %s (set $PABAU_CLUSTERS_XLSX)" % xlsx_path)
    if sheet.get("unmapped_columns"):
        die("the Posts sheet has columns this exporter does not map: %s — add them to "
            "POSTS_COLUMNS and to CONTRACT.md before exporting, so nothing is dropped"
            % ", ".join(sheet["unmapped_columns"]))

    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(os.path.join(out_dir, "snapshots"), exist_ok=True)
    gitkeep = os.path.join(out_dir, "snapshots", ".gitkeep")
    if not os.path.exists(gitkeep):
        _write(gitkeep, "")

    rows = sorted(sheet["posts"], key=lambda r: r["url"])
    base_path = os.path.join(out_dir, "base.jsonl")
    _write(base_path, "".join(row_json(r) + "\n" for r in rows))

    clusters_path = os.path.join(out_dir, "clusters.json")
    _write(clusters_path, json.dumps(
        {"version": STORE_VERSION, "built": sheet["built"], "clusters": sheet["clusters"]},
        ensure_ascii=False, indent=2, sort_keys=False) + "\n")

    review_path = os.path.join(out_dir, "review-queue.json")
    _write(review_path, json.dumps(
        {"version": STORE_VERSION, "built": sheet["built"], "rows": sheet["review"]},
        ensure_ascii=False, indent=2, sort_keys=False) + "\n")

    additions_path = os.path.join(out_dir, "additions.jsonl")
    if not os.path.exists(additions_path):
        _write(additions_path, "")

    unassigned = sum(1 for r in rows if not r.get("cluster_id"))
    by_silo = {}
    for r in rows:
        k = r.get("silo_source") or ""
        by_silo[k] = by_silo.get(k, 0) + 1
    # CONTRACT.md "MANIFEST.json — pinned shape". Readers verify downloads against this,
    # so the shape is part of the contract: counts is {posts, clusters, review,
    # unassigned}, and `sha256` is the authoritative MAP. It is recomputed here in full,
    # from the files this call just wrote — a manifest that names base.jsonl with the
    # PREVIOUS digest makes every teammate's `pull` refuse the snapshot, silently, forever.
    # additions.jsonl is deliberately NOT in the map: `push` rewrites it without touching
    # the manifest, so a digest for it would go stale on the first assignment and freeze
    # the store exactly the same way.
    manifest = {
        "version": STORE_VERSION,
        "built": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "source": os.path.basename(xlsx_path),
        "source_sha256": sha256_of(xlsx_path),
        "counts": {
            "posts": len(rows),
            "clusters": len(sheet["clusters"]),
            "review": len(sheet["review"]),
            "unassigned": unassigned,
        },
        "by_silo_source": dict(sorted(by_silo.items())),
        "base_sha256": sha256_of(base_path),
        "sha256": {
            "base.jsonl": sha256_of(base_path),
            "clusters.json": sha256_of(clusters_path),
            "review-queue.json": sha256_of(review_path),
        },
    }
    manifest_path = os.path.join(out_dir, "MANIFEST.json")
    _write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    return manifest, sheet


def cmd_export(a):
    manifest, sheet = export(a.xlsx or XLSX, a.out)
    print("Exported %s -> %s" % (a.xlsx or XLSX, a.out))
    for k, v in manifest["counts"].items():
        print("  %-12s %d" % (k, v))
    print("  base sha256  %s" % manifest["base_sha256"])
    for w in sheet.get("warnings") or []:
        print("  WARN %s" % w)


# ------------------------------------------------------------------- other commands

def cmd_resolve(a):
    store = load_store(a.xlsx, a.data)
    u = normalize_url(a.url)
    row = store["posts"].get(u)
    print("URL            : %s" % u)
    print("In store       : %s" % ("yes" if row else "no"))
    if row:
        for k in ROW_KEYS:
            if k in row and row[k] not in ("", None):
                print("%-15s: %s" % (k, row[k]))
        print("%-15s: %s" % ("_source_stream", row.get("_source_stream")))
    cl = effective_cluster(store, u)
    if cl:
        print("")
        print("Cluster id     : %s" % cl.get("id"))
        print("Cluster name   : %s" % cl.get("name"))
        print("Tier           : %s" % cl.get("tier"))
        print("Pillar         : %s" % (cl.get("pillar_url") or "—"))
    rq = store["review"].get(u)
    if rq:
        print("REVIEW QUEUE   : %s | %s" % (rq.get("decision"), rq.get("rule")))
    for c in store["meta"]["collisions"]:
        if c["url"] == u:
            print("COLLISION      : %s %s beat %s" % (
                c["severity"], c["winner"]["silo_source"], c["loser"]["silo_source"]))


def cmd_stats(a):
    store = load_store(a.xlsx, a.data)
    m = store["meta"]
    print("data dir : %s" % m.get("data_dir"))
    print("workbook : %s" % m.get("xlsx"))
    print("built    : %s" % m.get("built"))
    for label, info in sorted((m.get("inputs") or {}).items()):
        if isinstance(info, dict):
            print("  %-10s %s %s" % (label, "ok  " if info.get("present") else "MISS",
                                     info.get("path")))
    print("")
    for k, v in sorted((m.get("counts") or {}).items()):
        print("  %-12s %s" % (k, v))
    for w in (m.get("warnings") or [])[:20]:
        print("  WARN %s" % w)
    for c in (m.get("collisions") or [])[:20]:
        print("  COLLISION %-13s %s : %s (%s) beat %s (%s)"
              % (c["severity"], c["url"], c["winner"]["cluster_id"],
                 c["winner"]["silo_source"], c["loser"]["cluster_id"],
                 c["loser"]["silo_source"]))


def cmd_verify(a):
    """Compare this store against cluster_lookup.py's own `resolve` over a url sample.

    The store is a refactor of a working system; the only acceptable outcome is that it
    assigns exactly what the live script assigns today.
    """
    sys.path.insert(0, _HERE)
    try:
        import cluster_lookup as cl_mod
    except Exception as e:
        die("could not import cluster_lookup.py for the comparison (%s)" % e)

    import random
    random.seed(a.seed)
    store = load_store(a.xlsx, a.data)
    sheet = cl_mod.load_sheet()

    pool = sorted(set(list(store["posts"].keys()) + list(sheet["posts"].keys())))
    if not pool:
        die("nothing to compare — the store and the sheet are both empty")
    sample = random.sample(pool, min(a.sample, len(pool)))
    # Plus a few urls that are in neither, to exercise the code-folder fallback.
    sample += ["https://pabau.com/procedure-codes/cpt-99999-not-in-the-sheet/",
               "https://pabau.com/diagnostic-codes/z99-999-not-in-the-sheet/",
               "https://pabau.com/blog/a-post-published-after-the-snapshot/"]

    same = diff = 0
    misses = []
    for u in sample:
        _, _, _, want = cl_mod.resolve_record(sheet, u)
        got = effective_cluster(store, u)
        wid = (want or {}).get("id", "")
        gid = (got or {}).get("id", "")
        if wid == gid:
            same += 1
        else:
            diff += 1
            misses.append((u, wid, gid))
        if a.strict and store["posts"].get(normalize_url(u)):
            w = sheet["posts"].get(normalize_url(u)) or {}
            s = store["posts"][normalize_url(u)]
            for skey, wkey in (("subcluster", "subcluster"), ("title", "title"),
                               ("published", "published"), ("flag", "flag"),
                               ("note", "note")):
                if (s.get(skey) or "") != (w.get(wkey) or ""):
                    misses.append((u + " [" + skey + "]", w.get(wkey), s.get(skey)))
                    diff += 1
                    same -= 1
                    break

    print("compared %d urls (seed %d)" % (len(sample), a.seed))
    print("  identical cluster : %d" % same)
    print("  different         : %d" % diff)
    for u, w, g in misses[:25]:
        print("  MISMATCH %s: cluster_lookup=%r store=%r" % (u, w, g))
    print("%s" % ("PASS" if diff == 0 else "FAIL"))
    sys.exit(0 if diff == 0 else 1)


# --------------------------------------------------------------------------- main

def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--xlsx", default=None, help="override $PABAU_CLUSTERS_XLSX")
    ap.add_argument("--data", default=None, help="override $PABAU_CLUSTERS_DIR")
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("export", help="workbook -> the four canonical files")
    p.add_argument("--out", required=True)
    p.set_defaults(fn=cmd_export)

    p = sub.add_parser("resolve", help="the effective merged row for one url")
    p.add_argument("--url", required=True)
    p.set_defaults(fn=cmd_resolve)

    p = sub.add_parser("stats", help="what loaded, what merged, what collided")
    p.set_defaults(fn=cmd_stats)

    p = sub.add_parser("verify", help="compare against cluster_lookup.py `resolve`")
    p.add_argument("--sample", type=int, default=200)
    p.add_argument("--seed", type=int, default=20260922)
    p.add_argument("--strict", action="store_true",
                   help="also compare title/subcluster/published/flag/note")
    p.set_defaults(fn=cmd_verify)

    a = ap.parse_args()
    if not getattr(a, "fn", None):
        ap.print_help()
        sys.exit(2)
    a.fn(a)


if __name__ == "__main__":
    main()
