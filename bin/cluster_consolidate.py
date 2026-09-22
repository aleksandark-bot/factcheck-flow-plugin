#!/usr/bin/env python3
"""Fold every version of the cluster store back into one canonical base.

This is the tool David runs to answer "consolidate the different versions we all have on
our individual devices". It reads the canonical store, the append-only additions queue,
every teammate snapshot and David's own local workbook, merges them under exactly the
precedence in `clusters/CONTRACT.md`, and writes:

    1. a new clusters/base.jsonl        additions folded in, snapshots reconciled
    2. a conflict report                conflict-report.json + conflict-report.md
    3. a regenerated workbook view      so David keeps editing a spreadsheet
    4. a summary on stdout              rows in, rows added, conflicts by type, no-ops

The conflict report is the product. Every url where sources disagree is shown with each
competing assignment, its provenance, who made it and when, the evidence behind any
reasoned one, which one won and WHICH PRECEDENCE RULE FIRED. Where two sources of equal
authority disagree it is marked UNRESOLVED and sorted to the top, because only David can
settle it.

Precedence (CONTRACT.md § PROVENANCE). `silo_source` is an OPEN vocabulary — the literal
string always passes through unchanged and what matters is the AUTHORITY it maps to:

    human          a human assignment made directly in the store        (highest)
    spreadsheet    a human assignment from the original workbook
    anything else  machine-assigned: the interlinking-v4 labels
                   ("assigned:high", "R3 nearest-neighbour vote") and any future label
                   nobody has taught the code about
    reasoned       an agent resolved it from `suggest` during a run     (lowest)

An unrecognized label ranks with the machine labels, never higher: a label nobody
anticipated can never outrank a human assignment.

Within `reasoned`, the earliest assigned_at wins. Within any other authority the
tie-break is by source stream — local workbook > base.jsonl > additions.jsonl — and that
tie-break settles NOTHING: every equal-authority disagreement is reported as a conflict
for David, because only he can decide it.

Hard rules this file enforces:

  * a `reasoned` row NEVER overwrites a row of higher authority — the collision is
    reported, not applied;
  * a teammate snapshot is ADVISORY ONLY. It is consolidation input and nothing else, and
    never reaches base.jsonl except through David's decision. That is the per-device drift
    this tool exists to surface;
  * nothing is ever deleted. A url that has vanished from every live source is marked
    (`absent_since`) and kept;
  * a row flagged NON-ENGLISH is frozen — no merge ever changes its assignment;
  * an empty `cluster` is legal (the regional /ae/, /au/ … pages, rule R0b). Those rows are
    kept, counted in MANIFEST.counts.unassigned, and never guessed at.

Usage
    python3 bin/cluster_consolidate.py [--dry-run] [--out DIR] [--skip-workbook]
                                       [--only-snapshots] [--clusters-dir DIR]

Data (override with env vars):
    $PABAU_CLUSTERS_DIR    else the installed/repo clusters dir
    $PABAU_CLUSTERS_XLSX   else ~/Desktop/pabau-content-clusters.xlsx

Exit codes: 0 ok; 2 setup/data error; 1 when conflicts need David (so a cron run can be
noticed). --dry-run always exits 0 unless setup failed.
"""
import argparse
import collections
import datetime
import hashlib
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
HOME = os.path.expanduser("~")
BACKUP_DIR = os.environ.get("PABAU_CLUSTERS_BACKUPS") or os.path.join(
    HOME, ".claude", "factcheck-flow", "backups")

TOOL = "cluster_consolidate.py"
TOOL_VERSION = "1.0"

# --------------------------------------------------------------- shared store helpers
# url normalization, the row schema and store loading live in bin/cluster_store.py and are
# imported, never reimplemented. The fallbacks below exist only so this module is testable
# on a checkout where cluster_store.py is missing; they must stay behaviour-compatible.
sys.path.insert(0, HERE)
try:
    import cluster_store as CS
    normalize_url = CS.normalize_url
    canonical_row = CS.canonical_row
    assignment_of = CS.assignment_of
    authority_of = CS.authority_of
    row_json = CS.row_json
    store_read_jsonl = CS.read_jsonl
    store_read_workbook = CS.read_workbook
    load_store = CS.load_store
    AUTHORITY = CS.AUTHORITY
    UNKNOWN_AUTHORITY = CS.UNKNOWN_AUTHORITY
    STREAM_RANK = CS.STREAM_RANK
    ROW_KEYS = CS.ROW_KEYS
    INT_KEYS = CS.INT_KEYS
    XLSX = CS.XLSX
    default_data_dir = CS.default_data_dir
except Exception:                               # pragma: no cover - fallback path
    CS = None
    XLSX = os.environ.get("PABAU_CLUSTERS_XLSX") or os.path.join(
        HOME, "Desktop", "pabau-content-clusters.xlsx")
    ROW_KEYS = [
        "url", "title", "cluster", "cluster_id", "tier", "subcluster", "published",
        "rule_applied", "secondary_tag", "flag", "note", "wp_categories", "source_sheet",
        "intent", "silo_source", "depth_target", "depth_current", "in_scope", "exclusion",
        "assigned_by", "assigned_at", "evidence",
    ]
    INT_KEYS = ("depth_target", "depth_current")
    AUTHORITY = {"human": 0, "spreadsheet": 1, "interlinking-v4": 2, "reasoned": 3}
    UNKNOWN_AUTHORITY = 2
    STREAM_RANK = {"xlsx": 0, "base": 1, "additions": 2, "snapshot": 3}
    load_store = None
    store_read_workbook = None

    def default_data_dir():
        return os.environ.get("PABAU_CLUSTERS_DIR") or os.path.join(REPO, "clusters")

    def normalize_url(u):
        if not u:
            return ""
        u = str(u).strip().split("#")[0].split("?")[0]
        u = re.sub(r"^https?://", "", u, flags=re.I)
        u = re.sub(r"^www\.", "", u, flags=re.I)
        u = u.rstrip("/")
        return "https://" + u.lower() + "/" if u else ""

    def canonical_row(d):
        out = {}
        for k in ROW_KEYS:
            if k not in d:
                continue
            v = d[k]
            if k in INT_KEYS:
                try:
                    out[k] = v if isinstance(v, int) or v is None else int(str(v).strip())
                except (TypeError, ValueError):
                    out[k] = None
            elif k == "evidence":
                out[k] = v
            else:
                out[k] = "" if v is None else str(v)
        for k in sorted(d):
            if k not in out and k not in ROW_KEYS:
                out[k] = d[k]
        return out

    def row_json(row):
        return json.dumps(canonical_row(row), ensure_ascii=False,
                          separators=(",", ":"), sort_keys=False)

    def assignment_of(row):
        return ((row.get("cluster_id") or "").strip().lower(),
                (row.get("cluster") or "").strip().lower(),
                (row.get("subcluster") or "").strip().lower())

    def authority_of(row):
        return AUTHORITY.get((row.get("silo_source") or "").strip().lower(),
                             UNKNOWN_AUTHORITY)

    def store_read_jsonl(path, warnings, label):
        rows = []
        if not os.path.exists(path):
            return rows
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
        return rows

CLUSTERS_DIR = default_data_dir()

# Consolidation-only extension key. Not in the typed schema on purpose; forward
# compatibility means every consumer already tolerates it.
#   absent_since  ISO date this url stopped appearing in every live source.
ABSENT_KEY = "absent_since"
ABSENT_PREFIX = "ABSENT since "
ABSENT_NOTE = "no live source holds this url"
ABSENT_RE = re.compile(r"^ABSENT since (\d{4}-\d{2}-\d{2}) — %s(?: — (.*))?$" % ABSENT_NOTE)

# REQUIRED on every row. `cluster` / `cluster_id` are deliberately NOT here: 60 rows (the
# regional /ae/, /au/ … pages, rule R0b) legitimately carry "" and are never guessed at.
REQUIRED = ("url", "silo_source")
REASONED_KEYS = ("assigned_by", "assigned_at", "evidence")

STREAM_LABEL = {"xlsx": "the local workbook", "base": "base.jsonl",
                "additions": "additions.jsonl", "snapshot": "a teammate snapshot"}

# Which precedence rule fired, and the sentence the report prints for it.
RULES = {
    "P0": "P0 sole-candidate — only one source held this url.",
    "P1": "P1 human-highest — a human assignment outranks every other provenance.",
    "P2": "P2 spreadsheet-over-machine — the sheet is a human assignment and the source of "
          "truth; it is never re-litigated (3-links.md §0) and no machine row can displace it.",
    "P3": "P3 machine-over-reasoned — an interlinking-v4 (or other machine) label outranks a "
          "reasoned one.",
    "P4": "P4 reasoned-earliest — between two reasoned rows the earliest assigned_at wins; "
          "the later one is recorded as an alternate. First writer wins keeps the store stable.",
    "P9": "P9 stream-tie-break — equal authority, so the deterministic order local workbook > "
          "base.jsonl > additions.jsonl decided which row is carried forward. It settles "
          "nothing: an equal-authority disagreement is a question for David.",
    "P6": "P6 snapshot-advisory — a snapshot is consolidation input only. It never reaches "
          "base.jsonl except through David's decision.",
    "P7": "P7 non-english-frozen — the row is flagged NON-ENGLISH. No merge may change it and "
          "no English-only work ever touches the page.",
    "P8": "P8 invalid-row-ignored — the row violates the required schema and was not allowed "
          "to win.",
}

# Conflict taxonomy. (severity, order, heading, blurb)
NEEDS = "needs_decision"
ATTN = "attention"
INFO = "informational"
CATEGORIES = collections.OrderedDict([
    ("unresolved_equal_authority", (NEEDS, 10,
     "Unresolved — two sources of equal authority disagree",
     "Nothing in the precedence rules can settle these. A deterministic tie-break picked which "
     "row is carried forward, but that is not a decision. Settle each one in the workbook (or "
     "by writing a `human` row) and re-run.")),
    ("snapshot_only_url", (NEEDS, 20,
     "On a teammate's device only — url the canonical store does not have",
     "This is the per-device divergence. A teammate's local sheet carries an assignment for a "
     "url the store has never seen. Nothing was applied. Adopt it by adding the row to the "
     "workbook, or ignore it.")),
    ("snapshot_only_assignment", (NEEDS, 30,
     "On a teammate's device only — assignment differs from canonical",
     "The store and a teammate's local copy disagree about a url both have. A snapshot is a "
     "possibly-stale, possibly-hand-edited workbook, so nothing was applied.")),
    ("workbook_edit_adopted", (NEEDS, 40,
     "The local workbook disagrees with the store at equal authority",
     "The tie-break carried the workbook's row forward, which is almost always what you want "
     "when the edit was yours. Listed because the contract requires every equal-authority "
     "disagreement to be asked about — confirm each one, and the next run is silent.")),
    ("non_english_frozen", (ATTN, 50, "NON-ENGLISH rows — competing assignment refused",
     "These rows are flagged NON-ENGLISH. They are frozen: no consolidation ever changes them, "
     "and no English-only pass ever edits or links the pages.")),
    ("reasoned_over_human_attempt", (ATTN, 60,
     "An agent reasoned a cluster a human had already set",
     "Resolved by precedence — the human assignment stands. Each of these means an agent ran "
     "`suggest` on a url that already had a row, which is a bug worth chasing upstream.")),
    ("duplicate_in_source", (ATTN, 70,
     "The same url appears twice in one source file, disagreeing",
     "A data-hygiene problem in the named file, not a cross-device conflict.")),
    ("invalid_row", (ATTN, 80, "Rows that violate the required schema",
     "Missing a REQUIRED key, or a reasoned row with no assigned_by / assigned_at / evidence. "
     "These rows were never allowed to win a merge.")),
    ("reasoned_alternate", (INFO, 90,
     "Two reasoned assignments — earliest kept, later recorded as an alternate",
     "Resolved by P4. Listed so the alternate is not lost.")),
    ("precedence_resolved", (INFO, 100, "Resolved by precedence — unequal authority",
     "Informational only, per CONTRACT.md: unequal authority resolves by precedence.")),
    ("subcluster_divergence", (INFO, 110, "Same cluster, different subcluster",
     "The cluster agrees. Only the subcluster differs.")),
    ("tier_mismatch", (INFO, 120, "Tier disagrees with clusters.json",
     "`tier` is derived from the cluster definitions; a sheet Tier column that disagrees is "
     "advisory and was overridden, not obeyed.")),
    ("absent_url", (INFO, 130, "Rows absent from every live source — marked, never dropped",
     "These urls are still in base and always will be. They now carry `absent_since`.")),
])


def die(msg):
    sys.stderr.write("CLUSTER CONSOLIDATE ERROR: " + msg + "\n")
    sys.exit(2)


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def stamp():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def today():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")


def _s(v):
    if v is None:
        return ""
    if isinstance(v, (datetime.datetime, datetime.date)):
        return v.strftime("%Y-%m-%d")
    return str(v).strip()


def _as_int(v):
    if v is None or v == "" or isinstance(v, bool):
        return None
    try:
        return int(str(v).strip())
    except (TypeError, ValueError):
        return None


def cluster_key(row):
    """What two rows must agree on to be the same CLUSTER (subcluster excluded)."""
    return assignment_of(row)[:2]


def row_problems(row, lenient=False):
    """Schema violations, as a list of human sentences. Empty list = valid.

    `lenient` is for rows read out of the workbook: the sheet is a VIEW of the store and has
    no columns for assigned_by / assigned_at / evidence, so a reasoned row read back from it
    is not malformed — its audit trail lives in base.jsonl.
    """
    bad = []
    for k in REQUIRED:
        if not _s(row.get(k)):
            bad.append("missing required key `%s`" % k)
    if _s(row.get("cluster")) and not _s(row.get("cluster_id")):
        bad.append("has a cluster name but no cluster_id")
    if (row.get("silo_source") or "").strip().lower() == "reasoned" and not lenient:
        for k in ("assigned_by", "assigned_at"):
            if not _s(row.get(k)):
                bad.append("reasoned row with no `%s`" % k)
        ev = row.get("evidence")
        if not isinstance(ev, dict) or not ev:
            bad.append("reasoned row with no `evidence`")
    return bad


def is_non_english(row):
    hay = (_s(row.get("flag")) + " " + _s(row.get("exclusion"))).lower()
    return "non-english" in hay or "non english" in hay


# ------------------------------------------------------------------------- candidates

class Candidate(object):
    __slots__ = ("row", "stream", "label", "file", "problems")

    def __init__(self, row, stream, label, path):
        self.row = row
        self.stream = stream        # xlsx | base | additions | snapshot
        self.label = label          # "snapshots/alex.jsonl" etc
        self.file = path
        self.problems = row_problems(row, lenient=(stream == "xlsx"))

    @property
    def silo(self):
        return _s(self.row.get("silo_source")) or "(none)"

    @property
    def auth(self):
        return authority_of(self.row)

    @property
    def valid(self):
        return not self.problems

    def sort_key(self):
        # authority, then validity, then (reasoned) earliest assigned_at, then stream.
        at = _s(self.row.get("assigned_at")) or "~"
        return (self.auth, 0 if self.valid else 1, at,
                STREAM_RANK.get(self.stream, 9), self.label)

    def brief(self):
        return collections.OrderedDict([
            ("cluster", _s(self.row.get("cluster")) or "(unassigned)"),
            ("cluster_id", _s(self.row.get("cluster_id"))),
            ("subcluster", _s(self.row.get("subcluster"))),
            ("tier", _s(self.row.get("tier"))),
            ("silo_source", self.silo),
            ("authority", self.auth),
            ("assigned_by", _s(self.row.get("assigned_by"))),
            ("assigned_at", _s(self.row.get("assigned_at"))),
            ("rule_applied", _s(self.row.get("rule_applied"))),
            ("stream", self.stream),
            ("source", self.label),
            ("source_file", self.file),
            ("schema_problems", self.problems),
            ("evidence", self.row.get("evidence")),
        ])


def pick_winner(cands):
    """-> (winner, rule_id, unresolved). `cands` never contains a snapshot."""
    ordered = sorted(cands, key=lambda c: c.sort_key())
    win = ordered[0]
    if len(ordered) == 1:
        return win, "P0", False
    rival = next((c for c in ordered[1:] if assignment_of(c.row) != assignment_of(win.row)),
                 None)
    if rival is None:
        return win, "P0", False
    if win.auth != rival.auth:
        rule = {0: "P1", 1: "P2", 2: "P3"}.get(win.auth, "P1")
        return win, rule, False
    if win.auth == AUTHORITY["reasoned"]:
        if _s(win.row.get("assigned_at")) and \
                _s(win.row.get("assigned_at")) != _s(rival.row.get("assigned_at")):
            return win, "P4", False
    if not win.valid and rival.valid:
        return rival, "P8", False
    # Equal authority: the stream order is deterministic, not decisive.
    return win, "P9", True


def classify(winner, losers, unresolved):
    # Checked first, including at equal authority: when the CLUSTER agrees, nothing a
    # reader resolves changes, so this is a lesser disagreement than a cluster one.
    if all(cluster_key(l.row) == cluster_key(winner.row) for l in losers):
        return "subcluster_divergence"
    if unresolved:
        if winner.stream == "xlsx":
            return "workbook_edit_adopted"
        return "unresolved_equal_authority"
    if winner.auth <= AUTHORITY["spreadsheet"] and \
            any(l.auth == AUTHORITY["reasoned"] for l in losers):
        return "reasoned_over_human_attempt"
    if winner.auth == AUTHORITY["reasoned"]:
        return "reasoned_alternate"
    return "precedence_resolved"


def why_text(ctype, winner, losers, rule):
    if ctype == "unresolved_equal_authority":
        return ("Both sides carry the same authority (%d — `%s` vs `%s`), so no precedence "
                "rule can decide. The stream order carried %s forward; that is bookkeeping, "
                "not a decision."
                % (winner.auth, winner.silo, losers[0].silo,
                   STREAM_LABEL.get(winner.stream, winner.stream)))
    if ctype == "workbook_edit_adopted":
        return ("The live workbook and the stored row disagree at equal authority. The "
                "workbook was carried forward, which is right if this edit was yours — "
                "confirm it and the next run says nothing.")
    if ctype == "reasoned_over_human_attempt":
        return ("An agent reasoned a cluster for a url that already carried a `%s` "
                "assignment. The human assignment stands; the reasoned one is recorded here "
                "and was NOT applied. The agent should have found the existing row."
                % winner.silo)
    if ctype == "reasoned_alternate":
        return ("Two reasoned assignments. The earliest assigned_at (%s) wins; the later one "
                "is kept here as an alternate." % (_s(winner.row.get("assigned_at")) or "—"))
    if ctype == "subcluster_divergence":
        return "The cluster agrees. Only the subcluster differs, so the winning row's is kept."
    return "Resolved by precedence: authority %d beat authority %d." % (
        winner.auth, min(l.auth for l in losers))


def make_conflict(url, ctype, winner, others, rule, note):
    sev, order, _h, _b = CATEGORIES[ctype]
    title = ""
    for c in ([winner] if winner else []) + list(others):
        if c is not None and _s(c.row.get("title")):
            title = _s(c.row.get("title"))
            break
    cands = []
    if winner is not None:
        b = winner.brief()
        b["won"] = True
        cands.append(b)
    for c in others:
        b = c.brief()
        b["won"] = False
        cands.append(b)
    return collections.OrderedDict([
        ("url", url),
        ("title", title),
        ("type", ctype),
        ("severity", sev),
        ("needs_human", sev == NEEDS),
        ("sort", order),
        ("winner", (winner.brief() if winner else None)),
        ("rule_fired", rule),
        ("rule", RULES.get(rule, "")),
        ("why", note),
        ("candidates", cands),
    ])


def sha256_of(path):
    if not os.path.exists(path):
        return ""
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


# ------------------------------------------------------------------------- the merge

def consolidate(args):
    cdir = args.clusters_dir
    base_path = os.path.join(cdir, "base.jsonl")
    add_path = os.path.join(cdir, "additions.jsonl")
    snap_dir = os.path.join(cdir, "snapshots")

    warnings = []
    stats = collections.Counter()
    inputs = collections.OrderedDict()

    def load(path, label):
        rows = [canonical_row(r) for r in store_read_jsonl(path, warnings, label)]
        return rows

    base_rows = load(base_path, "base.jsonl")
    inputs["base.jsonl"] = {"path": base_path, "rows": len(base_rows),
                            "sha256": sha256_of(base_path)}
    add_rows = load(add_path, "additions.jsonl")
    inputs["additions.jsonl"] = {"path": add_path, "rows": len(add_rows)}

    snaps = collections.OrderedDict()
    if os.path.isdir(snap_dir):
        for fn in sorted(os.listdir(snap_dir)):
            if not fn.endswith(".jsonl"):
                continue
            p = os.path.join(snap_dir, fn)
            label = "snapshots/" + fn
            snaps[label] = (p, load(p, label))
            inputs[label] = {"path": p, "rows": len(snaps[label][1])}

    # The workbook, the cluster definitions and the review queue all come from the store
    # module so this tool and every reader see exactly the same parse.
    sheet = None
    wb_present = os.path.exists(args.xlsx)
    if wb_present and store_read_workbook is None:
        # No cluster_store.py on this checkout. The workbook is the live census for the
        # absent check, so pretending it is empty would mark the whole store absent.
        warnings.append("bin/cluster_store.py is not importable, so the workbook cannot be "
                        "read. Consolidating the synced files only, and NOT regenerating "
                        "the workbook.")
        wb_present = False
    if wb_present:
        try:
            sheet = store_read_workbook(args.xlsx)
        except SystemExit:
            raise
        except Exception as e:
            warnings.append("could not read the workbook %s (%s) — it will NOT be "
                            "regenerated" % (args.xlsx, e))
            wb_present = False
    wb_rows = [canonical_row(r) for r in (sheet or {}).get("posts", [])]
    for r in wb_rows:
        # The absent marker rides in the Exclusion column so it survives the round trip
        # through our own regenerated sheet. Read it back off and restore the cell's
        # original text, so only David clearing it by hand can clear it.
        m = ABSENT_RE.match(_s(r.get("exclusion")))
        if m:
            r[ABSENT_KEY] = m.group(1)
            r["exclusion"] = _s(m.group(2))
    warnings.extend((sheet or {}).get("warnings") or [])
    inputs["workbook"] = {"path": args.xlsx, "rows": len(wb_rows), "present": wb_present}

    cl_list = (sheet or {}).get("clusters") or []
    if not cl_list and load_store is not None:
        try:
            cl_list = load_store(xlsx_path=args.xlsx, data_dir=cdir)["clusters"]["list"]
        except Exception:
            cl_list = []
    cl_by_name = {_s(c.get("name")).lower(): c for c in cl_list if _s(c.get("name"))}
    cl_order = {_s(c.get("name")).lower(): i for i, c in enumerate(cl_list)}

    # -------------------------------------------------- candidates, grouped by url
    cands = collections.defaultdict(list)
    snap_cands = collections.defaultdict(list)
    dupes = []

    def add_stream(rows, stream, label, path, bucket):
        seen = {}
        for r in rows:
            u = r.get("url")
            if not u:
                continue
            prev = seen.get(u)
            if prev is not None:
                if assignment_of(prev) != assignment_of(r):
                    dupes.append((u, label, path, prev, r))
                else:
                    stats["no_op_duplicate"] += 1
                    continue
            seen[u] = r
            bucket[u].append(Candidate(r, stream, label, path))

    add_stream(base_rows, "base", "base.jsonl", base_path, cands)
    if not args.only_snapshots:
        add_stream(add_rows, "additions", "additions.jsonl", add_path, cands)
        if wb_present:
            add_stream(wb_rows, "xlsx", "workbook", args.xlsx, cands)
    for label, (p, rws) in snaps.items():
        add_stream(rws, "snapshot", label, p, snap_cands)

    live_urls = set()
    if not args.only_snapshots:
        live_urls |= set(r["url"] for r in add_rows if r.get("url"))
        if wb_present:
            live_urls |= set(r["url"] for r in wb_rows if r.get("url"))
    for _lbl, (_p, rws) in snaps.items():
        live_urls |= set(r["url"] for r in rws if r.get("url"))

    conflicts = []
    merged = {}
    base_index = {r["url"]: r for r in base_rows if r.get("url")}

    # A sheet that has lost a tenth of its rows is a corrupt input, not a thousand
    # deletions. Marking every one of them absent would be technically correct and
    # practically useless, so the whole pass is skipped and said out loud instead.
    gone = [u for u in base_index if u not in live_urls] if (
        wb_present and not args.only_snapshots) else []
    mark_absent = len(gone) <= max(50, 0.1 * len(base_index))
    if gone and not mark_absent:
        warnings.append(
            "%d of %d base rows are missing from the workbook, the additions queue and "
            "every snapshot. That is a corrupt or partial input, not that many deletions, "
            "so NOTHING was marked absent this run. Fix the input and re-run."
            % (len(gone), len(base_index)))

    for url in sorted(set(cands) | set(snap_cands)):
        canon = cands.get(url) or []
        snapc = snap_cands.get(url) or []

        if not canon:
            # url exists ONLY on a teammate's device. Never auto-applied.
            for c in snapc:
                conflicts.append(make_conflict(
                    url, "snapshot_only_url", None, [c], "P6",
                    "The canonical store has no row for this url; %s holds one. Nothing was "
                    "written — adopt it by adding the row to the workbook, or ignore it."
                    % c.label))
            continue

        winner, rule, unresolved = pick_winner(canon)

        # NON-ENGLISH freeze: the stored row stands, whatever anyone else says.
        frozen = any(is_non_english(c.row) for c in canon)
        if frozen:
            inc = next((c for c in canon if c.stream == "base" and is_non_english(c.row)),
                       None) or next((c for c in canon if is_non_english(c.row)), canon[0])
            dissent = [c for c in canon + snapc
                       if c is not inc and assignment_of(c.row) != assignment_of(inc.row)]
            if dissent:
                conflicts.append(make_conflict(
                    url, "non_english_frozen", inc, dissent, "P7",
                    "This row is flagged NON-ENGLISH. Consolidation never changes it, whatever "
                    "another source says, and no English-only pass touches the page."))
            winner, rule, unresolved, snapc = inc, "P7", False, []

        losers = [c for c in canon
                  if c is not winner and assignment_of(c.row) != assignment_of(winner.row)]
        stats["no_op_agreement"] += len(canon) - 1 - len(losers)

        if losers and not frozen:
            ctype = classify(winner, losers, unresolved)
            conflicts.append(make_conflict(url, ctype, winner, losers, rule,
                                           why_text(ctype, winner, losers, rule)))

        for c in canon:
            if c.problems:
                conflicts.append(make_conflict(
                    url, "invalid_row", winner if c is not winner else None, [c], "P8",
                    "%s: %s." % (c.label, "; ".join(c.problems))))

        # Snapshots: consolidation input only. Compare, report, never apply.
        for c in snapc:
            if assignment_of(c.row) == assignment_of(winner.row):
                stats["no_op_snapshot_agrees"] += 1
                continue
            conflicts.append(make_conflict(
                url, "snapshot_only_assignment", winner, [c], "P6",
                "%s has a different assignment for a url the store already holds. A snapshot "
                "is one teammate's possibly-stale workbook and never reaches base on its own "
                "— this is the per-device divergence, for your decision." % c.label))

        row = dict(winner.row)
        # Nothing is ever dropped: fill blanks, and carry forward every key a losing row
        # still has. Never an assignment field — that is what the precedence just decided.
        assignment_fields = ("cluster", "cluster_id", "subcluster")
        for c in canon:
            for k, v in c.row.items():
                if k in assignment_fields:
                    continue
                if k == "evidence":
                    if not row.get("evidence") and v and \
                            assignment_of(c.row) == assignment_of(row):
                        row["evidence"] = v
                    continue
                if k in INT_KEYS and row.get(k + "_raw"):
                    # The winner holds the sheet's own sentinel ("no path"). A number from
                    # another row is not the same fact, so it does not fill this blank.
                    continue
                if row.get(k) in (None, "") and v not in (None, ""):
                    row[k] = v

        # tier is DERIVED from the cluster definitions. A sheet Tier that disagrees is
        # advisory: overridden, and reported as a warning.
        cl = cl_by_name.get(_s(row.get("cluster")).lower())
        if cl and _s(cl.get("tier")):
            if _s(row.get("tier")) and _s(row.get("tier")) != _s(cl.get("tier")):
                conflicts.append(make_conflict(
                    url, "tier_mismatch", winner, [], "P0",
                    "tier %r does not match %r from the cluster definitions. The cluster "
                    "definition wins." % (_s(row.get("tier")), _s(cl.get("tier")))))
            row["tier"] = cl["tier"]
        if not _s(row.get("cluster")):
            stats["unassigned"] += 1

        # Absent from every live source -> marked, never dropped. The marker round-trips
        # through the workbook's Exclusion column, so our own regenerated sheet cannot
        # silently clear it; only David removing it can.
        wb_cand = next((c for c in canon if c.stream == "xlsx"), None)
        if wb_present and not args.only_snapshots:
            if url not in live_urls and not mark_absent:
                stats["absent_skipped"] += 1
            elif url not in live_urls:
                if not _s(row.get(ABSENT_KEY)):
                    row[ABSENT_KEY] = today()
                    conflicts.append(make_conflict(
                        url, "absent_url", winner, [], "P0",
                        "Present in base, absent from the workbook, the additions queue and "
                        "every snapshot. Marked `absent_since %s` and kept — nothing is ever "
                        "deleted." % today()))
                stats["absent"] += 1
            elif wb_cand is not None and _s(wb_cand.row.get(ABSENT_KEY)):
                row[ABSENT_KEY] = _s(wb_cand.row.get(ABSENT_KEY))
                stats["absent"] += 1
            elif _s(row.get(ABSENT_KEY)):
                row.pop(ABSENT_KEY, None)
                stats["absent_cleared"] += 1

        merged[url] = canonical_row(row)

    for (u, label, path, a, b) in dupes:
        conflicts.append(make_conflict(
            u, "duplicate_in_source", None,
            [Candidate(a, "base", label, path), Candidate(b, "base", label, path)], "P8",
            "%s holds this url twice with different assignments. Deduplicate that file."
            % label))

    return {
        "merged": merged, "conflicts": conflicts, "inputs": inputs, "stats": stats,
        "base_index": base_index, "warnings": warnings, "cluster_order": cl_order,
        "clusters": cl_list, "review": (sheet or {}).get("review") or [],
        "wb_present": wb_present, "add_rows": add_rows, "snaps": snaps,
    }


# ------------------------------------------------------------------------- reporting

def render_markdown(res, args, added):
    conflicts = res["conflicts"]
    by_type = collections.defaultdict(list)
    for c in conflicts:
        by_type[c["type"]].append(c)
    L = []
    A = L.append
    A("# Cluster consolidation — conflict report")
    A("")
    A("Generated %s by `bin/%s` v%s." % (utcnow(), TOOL, TOOL_VERSION))
    if args.dry_run:
        A("")
        A("**DRY RUN — nothing was written.** This is what a real run would do.")
    if args.only_snapshots:
        A("")
        A("**--only-snapshots** — snapshots reconciled against base. additions.jsonl, "
          "base.jsonl and the workbook were not touched.")
    A("")
    A("## Inputs")
    A("")
    A("| source | rows | path |")
    A("| --- | ---: | --- |")
    for name, meta in res["inputs"].items():
        A("| %s | %s | `%s`%s |" % (name, meta.get("rows", 0), meta.get("path", ""),
                                    "" if meta.get("present", True) else " *(not found)*"))
    A("")
    A("## What changed")
    A("")
    A("- rows in canonical base before: **%d**" % len(res["base_index"]))
    A("- rows in the new base: **%d**" % len(res["merged"]))
    A("- urls added: **%d**" % added)
    A("- rows with no cluster (legitimately unassigned): **%d**" % res["stats"]["unassigned"])
    A("- rows marked absent (kept, never dropped): **%d**" % res["stats"]["absent"])
    A("- no-ops (a source repeated an assignment already held): **%d**"
      % (res["stats"]["no_op_agreement"] + res["stats"]["no_op_snapshot_agrees"]
         + res["stats"]["no_op_duplicate"]))
    A("")
    A("## Conflicts by type")
    A("")
    A("| needs you? | type | count | what it is |")
    A("| --- | --- | ---: | --- |")
    for ctype, (sev, _o, heading, _b) in CATEGORIES.items():
        n = len(by_type.get(ctype, []))
        mark = {NEEDS: "**YES**", ATTN: "look", INFO: "—"}[sev]
        A("| %s | `%s` | %d | %s |" % (mark, ctype, n, heading))
    A("")
    need = sum(1 for c in conflicts if c["needs_human"])
    if need:
        A("**%d url(s) need your decision.** They are first below." % need)
    else:
        A("No url needs a decision from you. Everything resolved by precedence.")
    A("")
    if res["warnings"]:
        A("## Warnings from the store loader (nothing lost)")
        A("")
        for w in res["warnings"]:
            A("- %s" % w)
        A("")

    for ctype, (sev, _o, heading, blurb) in CATEGORIES.items():
        items = by_type.get(ctype) or []
        if not items:
            continue
        badge = {NEEDS: "NEEDS YOUR DECISION", ATTN: "WORTH A LOOK", INFO: "INFORMATIONAL"}[sev]
        A("---")
        A("")
        A("## %s — %s (%d)" % (badge, heading, len(items)))
        A("")
        A(blurb)
        A("")
        for c in sorted(items, key=lambda x: x["url"]):
            A("### %s" % c["url"])
            A("")
            if c["title"]:
                A("*%s*" % c["title"])
                A("")
            A("| | cluster | subcluster | silo_source | auth | by | at | source |")
            A("| --- | --- | --- | --- | ---: | --- | --- | --- |")
            for cand in c["candidates"]:
                A("| %s | %s | %s | `%s` | %d | %s | %s | `%s` |" % (
                    "**WON**" if cand.get("won") else "lost",
                    cand["cluster"], cand["subcluster"] or "—", cand["silo_source"],
                    cand["authority"], cand["assigned_by"] or "—",
                    cand["assigned_at"] or "—", cand["source"]))
            A("")
            for cand in c["candidates"]:
                if cand.get("evidence"):
                    A(render_evidence(cand))
            if c["winner"]:
                A("**Winner:** %s — `%s` from `%s`." % (
                    c["winner"]["cluster"], c["winner"]["silo_source"], c["winner"]["source"]))
                A("")
            A("**Rule that fired:** %s" % (c["rule"] or c["rule_fired"]))
            A("")
            A("**Why:** %s" % c["why"])
            if c["needs_human"]:
                A("")
                A("> **UNRESOLVED — needs David.** No assignment was adopted from the losing "
                  "side; the store is unchanged apart from the deterministic tie-break.")
            A("")
    A("---")
    A("")
    A("Precedence reference (CONTRACT.md § PROVENANCE): authority `human` > `spreadsheet` > "
      "any machine label > `reasoned` (earliest `assigned_at` wins). `silo_source` is an open "
      "vocabulary: an unrecognized label ranks with the machine labels, never higher.")
    A("")
    return "\n".join(L)


def render_evidence(cand):
    ev = cand.get("evidence") or {}
    L = ["<details><summary>evidence behind the reasoned assignment from %s</summary>"
         % cand["source"], ""]
    L.append("- title used: `%s`" % _s(ev.get("title_used")))
    L.append("- terms used: `%s`" % _s(ev.get("terms_used")))
    L.append("- top score: %s" % _s(ev.get("top_score")))
    if ev.get("top_matches"):
        L.append("- nearest posts:")
    for m in (ev.get("top_matches") or [])[:8]:
        L.append("  - %s → %s / %s (%s)" % (_s(m.get("url")), _s(m.get("cluster")),
                                            _s(m.get("subcluster")), _s(m.get("score"))))
    ta = ev.get("tally") or []
    if ta:
        L.append("- cluster tally: " + ", ".join(
            "%s/%s ×%s" % (_s(t.get("cluster")), _s(t.get("subcluster")), _s(t.get("n")))
            for t in ta[:5]))
    L += ["", "</details>", ""]
    return "\n".join(L)


def render_json(res, args, added):
    by_type = collections.Counter(c["type"] for c in res["conflicts"])
    return collections.OrderedDict([
        ("tool", TOOL),
        ("tool_version", TOOL_VERSION),
        ("generated_at", utcnow()),
        ("dry_run", bool(args.dry_run)),
        ("only_snapshots", bool(args.only_snapshots)),
        ("inputs", res["inputs"]),
        ("counts", collections.OrderedDict([
            ("base_rows_in", len(res["base_index"])),
            ("base_rows_out", len(res["merged"])),
            ("urls_added", added),
            ("unassigned", res["stats"]["unassigned"]),
            ("marked_absent", res["stats"]["absent"]),
            ("absent_cleared", res["stats"]["absent_cleared"]),
            ("no_op_agreement", res["stats"]["no_op_agreement"]),
            ("no_op_snapshot_agrees", res["stats"]["no_op_snapshot_agrees"]),
            ("no_op_duplicate_rows", res["stats"]["no_op_duplicate"]),
            ("conflicts_total", len(res["conflicts"])),
            ("conflicts_needing_human", sum(1 for c in res["conflicts"] if c["needs_human"])),
        ])),
        ("conflicts_by_type", collections.OrderedDict(
            (t, by_type.get(t, 0)) for t in CATEGORIES)),
        ("precedence_rules", RULES),
        ("warnings", res["warnings"]),
        ("conflicts", sorted(res["conflicts"], key=lambda c: (c["sort"], c["url"]))),
    ])


# ------------------------------------------------------------------- workbook out

POSTS_COLS = collections.OrderedDict([
    ("Cluster", "cluster"), ("Tier", "tier"), ("Subcluster", "subcluster"),
    ("Post title", "title"), ("URL", "url"), ("Published", "published"),
    ("Rule applied", "rule_applied"), ("Secondary tag", "secondary_tag"),
    ("Flag / needs review", "flag"), ("Note", "note"),
    ("Current WP categories", "wp_categories"), ("Source sheet (old cluster)", "source_sheet"),
    ("Intent", "intent"), ("Silo source", "silo_source"), ("Depth target", "depth_target"),
    ("Depth (current)", "depth_current"), ("In scope", "in_scope"), ("Exclusion", "exclusion"),
])


def regenerate_workbook(res, args, report_path):
    """Rewrite the Posts sheet from the merged store and refresh the derived sheets.

    Built by EDITING the existing workbook, never from scratch: that is what preserves the
    Read me / Clusters / Open decisions sheets, the column widths and every style already in
    the file. Formatting follows Pabau-Interlinking-v4's 05_update_spreadsheets.py and the
    top-up script: 10pt body, wrapped titles, bold navy cluster column, sand fill on flagged
    rows, an autofilter across the header.
    """
    import openpyxl
    from openpyxl.styles import Font, PatternFill, Alignment

    NAVY, SAND = "1F3864", "FFF2CC"
    merged = res["merged"]
    order = res["cluster_order"]

    wb = openpyxl.load_workbook(args.xlsx)
    ps = wb["Posts"]
    hdr = [_s(c.value) for c in ps[1]]
    for col in POSTS_COLS:
        if col not in hdr:
            hdr.append(col)
            ps.cell(row=1, column=len(hdr), value=col)
    idx = {h: i for i, h in enumerate(hdr)}
    before = ps.max_row - 1

    parsed = res["inputs"]["workbook"].get("rows", 0)
    if before > 0 and parsed == 0 and not args.allow_shrink:
        sys.stderr.write(
            "REFUSING to rewrite the workbook: its Posts sheet has %d rows but not one of "
            "them parsed into a store row. That means a column this tool relies on (URL "
            "above all) has been renamed or moved. Fix the sheet, or re-run with "
            "--allow-shrink.\n" % before)
        return None
    if len(merged) < before * 0.9 and not args.allow_shrink:
        sys.stderr.write(
            "REFUSING to rewrite the workbook: it has %d Posts rows and the merged store has "
            "only %d. That is a >10%% shrink and almost certainly a bad input. Re-run with "
            "--allow-shrink if you really mean it.\n" % (before, len(merged)))
        return None

    def sort_key(r):
        nm = _s(r.get("cluster")).lower()
        return (order.get(nm, 999), _s(r.get("cluster")), _s(r.get("subcluster")),
                _s(r.get("title")).lower(), r.get("url"))

    rows = sorted(merged.values(), key=sort_key)
    body = []
    for r in rows:
        line = [None] * len(hdr)
        for col, key in POSTS_COLS.items():
            v = r.get(key)
            if key in INT_KEYS and v is None:
                # "no path" and friends: write the sheet's own original string back.
                v = r.get(key + "_raw") or None
            if key == "exclusion" and _s(r.get(ABSENT_KEY)):
                # The absent marker rides in Exclusion so it survives the round trip.
                v = "%s%s — %s%s" % (
                    ABSENT_PREFIX, _s(r[ABSENT_KEY]), ABSENT_NOTE,
                    (" — " + _s(v)) if _s(v) and not _s(v).startswith(ABSENT_PREFIX) else "")
            line[idx[col]] = v if v not in ("",) else None
        body.append(line)

    if ps.max_row > 1:
        ps.delete_rows(2, ps.max_row)
    flag_ix, title_ix = idx["Flag / needs review"], idx["Post title"]
    for line in body:
        ps.append(line)
    for row in ps.iter_rows(min_row=2, max_row=ps.max_row):
        for c in row:
            c.font = Font(size=10)
            c.alignment = Alignment(vertical="top")
        row[title_ix].alignment = Alignment(vertical="top", wrap_text=True)
        if row[flag_ix].value:
            for c in row:
                c.fill = PatternFill("solid", fgColor=SAND)
            row[flag_ix].font = Font(size=10, bold=True, color="7F6000")
        row[0].font = Font(size=10, bold=True, color=NAVY)
    last_col = openpyxl.utils.get_column_letter(len(hdr))
    ps.auto_filter.ref = "A1:%s%d" % (last_col, ps.max_row)

    counts = collections.Counter(_s(r.get("cluster")) for r in rows)
    rule2 = collections.Counter(_s(r.get("cluster")) for r in rows
                                if _s(r.get("flag")).startswith("Rule-2"))
    total = len(rows)

    if "Clusters" in wb.sheetnames:
        cl = wb["Clusters"]
        chdr = [_s(c.value) for c in cl[1]]
        if "Cluster name" in chdr and "Posts" in chdr:
            ni, pi = chdr.index("Cluster name"), chdr.index("Posts")
            for row in cl.iter_rows(min_row=2):
                nm = _s(row[ni].value)
                if nm in counts:
                    row[pi].value = counts[nm]

    if "Cluster summary" in wb.sheetnames:
        sm = wb["Cluster summary"]
        shdr = [_s(c.value) for c in sm[1]]

        def col(name):
            return shdr.index(name) if name in shdr else None

        ci, pi = col("Cluster"), col("Posts")
        r2i, shi = col("Rule-2 candidates inside"), col("Share of blog")
        if ci is not None and pi is not None:
            for row in sm.iter_rows(min_row=2):
                nm = _s(row[ci].value)
                if nm == "TOTAL":
                    row[pi].value = total
                    if shi is not None:
                        row[shi].value = 1
                    continue
                if nm in counts:
                    row[pi].value = counts[nm]
                    if r2i is not None:
                        row[r2i].value = rule2.get(nm) or ""
                    if shi is not None:
                        row[shi].value = (counts[nm] / total) if total else 0

    # Review queue: never rebuilt from scratch — it carries triage decisions this tool does
    # not own. Existing rows are repaired and refreshed in place; conflicts that need a human
    # are appended so the decision is visible in the sheet David actually opens.
    added_q = repaired_q = 0
    if "Review queue" in wb.sheetnames:
        rq = wb["Review queue"]
        qhdr = [_s(c.value) for c in rq[1]]
        qi = {h: i for i, h in enumerate(qhdr)}
        have = set()
        for row in rq.iter_rows(min_row=2):
            if "URL" not in qi or "Decision needed" not in qi:
                break
            u = normalize_url(row[qi["URL"]].value)
            if not u and _s(row[qi["Decision needed"]].value).lower().startswith("http"):
                # Eight rows in the sheet sit one column left: the url is in "Decision
                # needed" and the decision in "Cluster as assigned". Put them right.
                u = normalize_url(row[qi["Decision needed"]].value)
                decision = _s(row[qi["Cluster as assigned"]].value) \
                    if "Cluster as assigned" in qi else ""
                row[qi["URL"]].value = u
                row[qi["Decision needed"]].value = decision
                if "Cluster as assigned" in qi:
                    row[qi["Cluster as assigned"]].value = None
                repaired_q += 1
            if not u:
                continue
            have.add(u)
            r = merged.get(u)
            if not r:
                continue
            if "Post title" in qi and _s(r.get("title")):
                row[qi["Post title"]].value = r["title"]
            if "Cluster as assigned" in qi and _s(r.get("cluster")) \
                    and _s(row[qi["Cluster as assigned"]].value):
                row[qi["Cluster as assigned"]].value = r["cluster"]
        for c in sorted(res["conflicts"], key=lambda x: (x["sort"], x["url"])):
            if not c["needs_human"] or c["url"] in have:
                continue
            line = [None] * len(qhdr)
            for name, val in (("Decision needed", "Consolidation — %s" % c["type"]),
                              ("Cluster as assigned", (c["winner"] or {}).get("cluster") or ""),
                              ("Post title", c["title"]), ("URL", c["url"]),
                              ("Rule applied", c["rule_fired"]), ("Note", c["why"][:480])):
                if name in qi:
                    line[qi[name]] = val
            rq.append(line)
            have.add(c["url"])
            added_q += 1
        if added_q:
            for row in rq.iter_rows(min_row=rq.max_row - added_q + 1, max_row=rq.max_row):
                for c in row:
                    c.font = Font(size=10)
                    c.alignment = Alignment(vertical="top")
                    c.fill = PatternFill("solid", fgColor=SAND)
                row[0].font = Font(size=10, bold=True, color="7F6000")
        if rq.max_row > 1:
            rq.auto_filter.ref = "A1:%s%d" % (
                openpyxl.utils.get_column_letter(len(qhdr)), rq.max_row)

    if "Read me" in wb.sheetnames:
        rm = wb["Read me"]
        line = ("· Consolidated %s by bin/cluster_consolidate.py: %s rows, %s added, "
                "%s conflicts (%s need a decision). Report: %s"
                % (today(), format(total, ","), format(res["added"], ","),
                   format(len(res["conflicts"]), ","),
                   sum(1 for c in res["conflicts"] if c["needs_human"]), report_path))
        hit = None
        for row in rm.iter_rows():
            v = row[0].value
            if isinstance(v, str) and v.startswith("· Consolidated "):
                hit = row[0]
                break
        cell = hit or rm.cell(rm.max_row + 1, 1)
        cell.value = line
        cell.font = Font(size=10)
        cell.alignment = Alignment(vertical="top")

    # Backup convention follows the v4 script: one BEFORE- copy written once and never
    # overwritten (the pre-tool state), plus a dated copy per run. Named after the workbook
    # actually being written, so a test run can never shadow the real one.
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stem = os.path.splitext(os.path.basename(args.xlsx))[0]
    first = os.path.join(BACKUP_DIR, "%s.BEFORE-consolidate.xlsx" % stem)
    if not os.path.exists(first):
        shutil.copy2(args.xlsx, first)
    dated = os.path.join(BACKUP_DIR, "%s.%s.xlsx" % (stem, stamp()))
    shutil.copy2(args.xlsx, dated)
    wb.save(args.xlsx)
    return {"path": args.xlsx, "rows": total, "backup_first": first, "backup_run": dated,
            "review_queue_added": added_q, "review_queue_repaired": repaired_q}


# ------------------------------------------------------------------------------ main

def archive_previous(path):
    if not os.path.exists(path):
        return
    d = os.path.join(os.path.dirname(path), "reports")
    os.makedirs(d, exist_ok=True)
    stem, ext = os.path.splitext(os.path.basename(path))
    try:
        ts = datetime.datetime.fromtimestamp(
            os.path.getmtime(path), datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    except OSError:
        ts = stamp()
    shutil.move(path, os.path.join(d, "%s.%s%s" % (stem, ts, ext)))


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Fold base + additions + snapshots + the local workbook into one "
                    "canonical base, and report every conflict.")
    ap.add_argument("--dry-run", action="store_true",
                    help="read-only: compute everything, write nothing, print the summary")
    ap.add_argument("--out", metavar="DIR",
                    help="where to write base.jsonl and the conflict report "
                         "(default: the clusters dir)")
    ap.add_argument("--skip-workbook", action="store_true",
                    help="do not regenerate the xlsx view")
    ap.add_argument("--only-snapshots", action="store_true",
                    help="reconcile snapshots against base only: additions are not folded "
                         "in, base and the workbook are left alone (report-only)")
    ap.add_argument("--clusters-dir", metavar="DIR", default=CLUSTERS_DIR,
                    help="input store directory (default %s)" % CLUSTERS_DIR)
    ap.add_argument("--xlsx", metavar="PATH", default=XLSX,
                    help="the local workbook (default %s)" % XLSX)
    ap.add_argument("--allow-shrink", action="store_true",
                    help="permit a workbook rewrite that loses more than 10%% of its rows")
    args = ap.parse_args(argv)

    args.clusters_dir = os.path.abspath(os.path.expanduser(args.clusters_dir))
    args.xlsx = os.path.abspath(os.path.expanduser(args.xlsx))
    out_dir = os.path.abspath(os.path.expanduser(args.out or args.clusters_dir))
    if not os.path.isdir(args.clusters_dir):
        die("clusters dir not found: %s" % args.clusters_dir)
    read_only = args.dry_run or args.only_snapshots

    res = consolidate(args)
    base_before = set(res["base_index"])
    added = len(set(res["merged"]) - base_before)
    res["added"] = added

    md = render_markdown(res, args, added)
    js = render_json(res, args, added)

    wrote = []
    mp = os.path.join(out_dir, "conflict-report.md")
    if not args.dry_run:
        os.makedirs(out_dir, exist_ok=True)
        jp = os.path.join(out_dir, "conflict-report.json")
        archive_previous(jp)
        archive_previous(mp)
        with open(jp, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(js, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        with open(mp, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(md)
        wrote += [jp, mp]

    base_out = os.path.join(out_dir, "base.jsonl")
    if not read_only and base_before and len(res["merged"]) < len(base_before) * 0.9 \
            and not args.allow_shrink:
        # Nothing ever deletes a row, so the merge can only shrink if an input was read
        # badly. Refuse rather than write a truncated canonical store.
        sys.stderr.write(
            "REFUSING to write base.jsonl: it had %d rows and the merge produced only %d. "
            "Rows are never deleted, so an input must have been read badly. Nothing was "
            "written except the conflict report. Re-run with --allow-shrink if you really "
            "mean it.\n" % (len(base_before), len(res["merged"])))
        read_only = True
    if not read_only:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        # A non-default store (a test fixture) is tagged so its backups can never be
        # mistaken for the real store's.
        tag = "" if args.clusters_dir == os.path.abspath(CLUSTERS_DIR) else \
            os.path.basename(os.path.dirname(args.clusters_dir)) + "-"
        src = os.path.join(args.clusters_dir, "base.jsonl")
        if os.path.exists(src):
            shutil.copy2(src, os.path.join(BACKUP_DIR, "%sbase.%s.jsonl" % (tag, stamp())))
        tmp = base_out + ".tmp%d" % os.getpid()
        with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
            for u in sorted(res["merged"]):
                fh.write(row_json(res["merged"][u]) + "\n")
        os.replace(tmp, base_out)
        wrote.append(base_out)

        # additions are consumed: kept as a dated copy, then truncated.
        ap_path = os.path.join(args.clusters_dir, "additions.jsonl")
        if os.path.exists(ap_path) and res["add_rows"]:
            shutil.copy2(ap_path,
                         os.path.join(BACKUP_DIR, "%sadditions.%s.jsonl" % (tag, stamp())))
            with open(ap_path, "w", encoding="utf-8"):
                pass

        man_path = os.path.join(out_dir, "MANIFEST.json")
        try:
            man = json.load(open(man_path, encoding="utf-8"))
            if not isinstance(man, dict):
                man = {}
        except Exception:
            man = {}
        man.update({
            "version": (_as_int(man.get("version")) or 0) + 1,
            "built": utcnow(),
            "built_by": TOOL,
            "rows": len(res["merged"]),
            "base_sha256": sha256_of(base_out),
            "counts": {
                "posts": len(res["merged"]),
                "unassigned": res["stats"]["unassigned"],
                "absent": res["stats"]["absent"],
                "conflicts": len(res["conflicts"]),
                "conflicts_needing_human": sum(1 for c in res["conflicts"]
                                               if c["needs_human"]),
            },
        })
        with open(man_path, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(man, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        wrote.append(man_path)

    wbinfo = None
    if not read_only and not args.skip_workbook and res["wb_present"]:
        try:
            wbinfo = regenerate_workbook(res, args, mp)
            if wbinfo:
                wrote.append(wbinfo["path"])
        except Exception as e:
            sys.stderr.write("WARNING: workbook regeneration failed (%s). The new base.jsonl "
                             "and the conflict report were still written.\n" % e)

    # ------------------------------------------------------------------ stdout summary
    by_type = collections.Counter(c["type"] for c in res["conflicts"])
    need = sum(1 for c in res["conflicts"] if c["needs_human"])
    P = print
    P("")
    P("cluster consolidation — %s%s" % (utcnow(), "  [DRY RUN]" if args.dry_run else ""))
    P("=" * 72)
    P("ROWS IN")
    for name, meta in res["inputs"].items():
        note = "" if meta.get("present", True) else "   (not found)"
        P("  %-28s %7s  %s%s" % (name, meta.get("rows", 0), meta.get("path", ""), note))
    P("")
    P("ROWS OUT")
    P("  base rows before             %7d" % len(base_before))
    P("  base rows after              %7d" % len(res["merged"]))
    P("  urls added                   %7d" % added)
    P("  unassigned (no cluster)      %7d" % res["stats"]["unassigned"])
    P("  marked absent (kept)         %7d" % res["stats"]["absent"])
    if res["stats"]["absent_skipped"]:
        P("  absent marking SKIPPED        %7d  (see the warning)"
          % res["stats"]["absent_skipped"])
    P("  absent flag cleared          %7d" % res["stats"]["absent_cleared"])
    P("")
    P("NO-OPS (a source repeated an assignment already held)")
    P("  sources agreeing             %7d" % res["stats"]["no_op_agreement"])
    P("  snapshots agreeing           %7d" % res["stats"]["no_op_snapshot_agrees"])
    P("  duplicate identical rows     %7d" % res["stats"]["no_op_duplicate"])
    P("")
    P("CONFLICTS BY TYPE  (%d total, %d need you)" % (len(res["conflicts"]), need))
    shown = False
    for ctype, (sev, _o, _h, _b) in CATEGORIES.items():
        n = by_type.get(ctype, 0)
        if not n:
            continue
        shown = True
        P("  %-7s %-34s %5d" % ("[YOU]" if sev == NEEDS else
                                ("[look]" if sev == ATTN else "[info]"), ctype, n))
    if not shown:
        P("  none")
    if res["warnings"]:
        P("")
        P("STORE WARNINGS                 %5d  (listed in the report)" % len(res["warnings"]))
    P("")
    if args.dry_run:
        P("DRY RUN — nothing written. A real run would write:")
        P("  %s" % base_out)
        P("  %s" % os.path.join(out_dir, "conflict-report.json"))
        P("  %s" % mp)
        if not args.skip_workbook and res["wb_present"]:
            P("  %s  (backed up to %s first)" % (args.xlsx, BACKUP_DIR))
        if need:
            P("")
            P("TOP OF THE REPORT — %d url(s) would need your decision:" % need)
            for c in sorted(res["conflicts"], key=lambda x: (x["sort"], x["url"])):
                if c["needs_human"]:
                    P("  %-28s %s" % (c["type"], c["url"]))
    else:
        if args.only_snapshots:
            P("--only-snapshots: base, additions and the workbook were left untouched.")
        P("WROTE")
        for p in wrote:
            P("  %s" % p)
        if wbinfo:
            P("  workbook backup (first run) %s" % wbinfo["backup_first"])
            P("  workbook backup (this run)  %s" % wbinfo["backup_run"])
            if wbinfo.get("review_queue_repaired"):
                P("  %d column-shifted Review queue row(s) put back in the right columns"
                  % wbinfo["review_queue_repaired"])
            if wbinfo.get("review_queue_added"):
                P("  %d conflict row(s) appended to the Review queue sheet"
                  % wbinfo["review_queue_added"])
            P("  NOTE the four folder splits (pabau-content-clusters-blog.xlsx etc) are now")
            P("       stale. Re-derive with Pabau-Interlinking-v4/bin/05_update_spreadsheets.py")
        elif not args.skip_workbook and res["wb_present"]:
            P("  (workbook NOT rewritten — see the warning above)")
    P("")
    if need:
        P("%d url(s) need your decision. Open the report: %s" % (need, mp))
    else:
        P("Nothing needs a decision from you.")
    P("")
    return 1 if (need and not args.dry_run) else 0


if __name__ == "__main__":
    sys.exit(main())
