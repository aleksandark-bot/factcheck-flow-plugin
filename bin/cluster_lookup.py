#!/usr/bin/env python3
"""Resolve a Pabau URL to its content cluster and its legal link targets.

Cluster assignment comes from the CENTRAL STORE (`clusters/CONTRACT.md`), loaded through
`cluster_store.load_store()`: the `clusters-data` branch files that `update.sh` syncs to
every machine (`base.jsonl` + `additions.jsonl`), merged with the local workbook where one
exists. The workbook is no longer the sole source of truth — it is ONE input, and still the
highest-authority one, so David's authoring workflow is unchanged and a sheet row always
beats anything reasoned. What changed is that a machine without the workbook now reads the
branch copy instead of blocking, and a cluster reasoned during a run is written back
(`submit`) rather than thrown away. This script still never re-derives or re-litigates an
assignment the store already holds.

Every command below answers a question the internal-linking rulebook asks
(`~/.claude/factcheck-flow/prompts/3-links.md`), so the link pass never has to load
5,000 spreadsheet rows into context.

Commands
  resolve   --url URL [--title T]      cluster, tier, pillar, budget, code family, directives
  suggest   --title T [--terms "..."]  nearest posts + cluster tally (for URLs not in the sheet)
  targets   --cluster ID [filters]     candidate in-cluster link targets, with inbound counts
  classify  --urls U [U ...]           per-URL cluster/folder verdict (the disposition sweep)
  clusters                             all clusters: tier, pillar, supporting hubs
  subhubs   [--verify]                 the billing ADD_SUBHUB target set
  verify    --url URL --plan plan.json mechanical gate over a finished link plan
  submit    --url URL --cluster-id ID  write a reasoned assignment back to the store
                                       (a thin alias — the implementation is cluster_sync.py)

Data (override with env vars):
  $PABAU_CLUSTERS_XLSX   else ~/Desktop/pabau-content-clusters.xlsx   (local workbook)
  $PABAU_CLUSTERS_DIR    else ~/.claude/factcheck-flow/clusters       (the synced store)
  $PABAU_LINKMAP_GRAPH   else ~/Desktop/linkmap/graph.json            (current link graph)

Exit codes: 0 ok; 2 setup/data error; 1 only from `verify` when the plan fails a check.
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import unicodedata

BIN_DIR = os.path.dirname(os.path.abspath(__file__))
if BIN_DIR not in sys.path:
    sys.path.insert(0, BIN_DIR)

# The data layer. A checkout that predates it still runs: every command falls back to the
# local workbook alone, which is exactly the behaviour this script had before the store.
try:
    import cluster_store as CS
except Exception:  # pragma: no cover - only on a partial install
    CS = None

HOME = os.path.expanduser("~")
XLSX = os.environ.get("PABAU_CLUSTERS_XLSX") or os.path.join(
    HOME, "Desktop", "pabau-content-clusters.xlsx")
GRAPH = os.environ.get("PABAU_LINKMAP_GRAPH") or os.path.join(
    HOME, "Desktop", "linkmap", "graph.json")
CACHE_DIR = os.path.join(HOME, ".claude", "factcheck-flow", "cache")

CODE_FOLDERS = ("/procedure-codes/", "/diagnostic-codes/")
IN_SCOPE_FOLDERS = ("/blog/", "/templates/") + CODE_FOLDERS

BILLING_CLUSTER_ID = "billing-coding-claims"
BILLING_PILLAR = "https://pabau.com/features/claims-management-software/"

# The billing subhub families named in the Clusters sheet's supporting-pages cell,
# resolved to the live URL that returns 200. Verified 2026-08-21; re-check with
# `subhubs --verify`. Families with no archive page resolve to the family's guide page,
# which is inside the billing cluster and therefore a legal target either way.
SUBHUBS = [
    ("cpt-codes", "https://pabau.com/procedure-codes/cpt-codes/", "archive"),
    ("icd-10-cm", "https://pabau.com/diagnostic-codes/icd-10-cm/", "archive"),
    ("hcpcs", "https://pabau.com/procedure-codes/hcpcs/", "archive"),
    ("ccsd-codes", "https://pabau.com/procedure-codes/ccsd-codes/", "archive"),
    ("diagnostic-codes", "https://pabau.com/diagnostic-codes/", "archive"),
    ("procedure-codes", "https://pabau.com/procedure-codes/", "archive"),
    ("denial-codes", "https://pabau.com/procedure-codes/denial-codes-in-medical-billing/",
     "guide page — no archive hub exists"),
    ("mbs", "https://pabau.com/blog/mbs-item-numbers/",
     "guide page — /procedure-codes/mbs/ 301s here"),
    ("medicare", "https://pabau.com/blog/medicare-billing/",
     "guide page — no archive hub exists"),
]

# Which subhubs a code page rotates through, by its own family. Its own family's archive
# is listed last: a CPT page linking the CPT archive spreads no new equity.
SIBLING_ORDER = {
    "CPT": ["icd-10-cm", "denial-codes", "hcpcs", "ccsd-codes", "cpt-codes"],
    "ICD-10": ["cpt-codes", "denial-codes", "hcpcs", "diagnostic-codes", "icd-10-cm"],
    "HCPCS": ["cpt-codes", "icd-10-cm", "denial-codes", "ccsd-codes", "hcpcs"],
    "CCSD": ["cpt-codes", "icd-10-cm", "denial-codes", "hcpcs", "ccsd-codes"],
    "denial": ["cpt-codes", "icd-10-cm", "hcpcs", "diagnostic-codes"],
    "MBS": ["cpt-codes", "icd-10-cm", "medicare", "denial-codes"],
    "Medicare": ["cpt-codes", "icd-10-cm", "mbs", "denial-codes"],
    "other": ["cpt-codes", "icd-10-cm", "hcpcs", "denial-codes", "ccsd-codes"],
}

# Anchor-variant rotation. Not a table of strings — a rotation of PATTERNS, so the corpus
# never carries one sitewide exact-match anchor for a pillar or hub. Pick the pattern the
# seed names, then write it in this article's own words.
ANCHOR_PATTERNS = [
    "the target's exact primary keyword, lower case",
    "a descriptive phrase naming the audience (\"software built for med spas\")",
    "the target page's own H1, trimmed to fit the sentence",
    "a benefit-framed phrase that still contains the head noun",
]

# Pillar exceptions the rulebook names. Keyed by cluster id.
PILLAR_NOTES = {
    "comparisons-alternatives": (
        "PILLAR_EXCEPTION — the listed pillar is an /lp/ page and is banned. Up-link the most "
        "relevant non-LP /compare/ page instead and verify it returns 200 "
        "(https://pabau.com/compare/ is the index). If none fits, log BLOCKED_PILLAR."),
    "optometry-eye-care": (
        "BLOCKED_PILLAR — pillar is /lp/-only and the cluster is on the watch-list. Plan no "
        "pillar up-link; log the cluster as BLOCKED_PILLAR pending a real /industry/ page."),
    "ai-in-healthcare": (
        "Interim pillar — use /features/ai-medical-scribe/ as-is."),
    "pabau-product-updates": (
        "HOUSE CATEGORY — not a silo. No added editorial links and no pillar rule. Only "
        "REMOVE/REROUTE (/lp/, cross-cluster) and the /book-demo/ CTA contract apply."),
    "retire-review": (
        "RETIREMENT BUCKET — no link actions at all. Log and skip the link pass."),
}


try:  # this output gets piped to head a lot; die quietly when it does
    import signal
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)
except (ImportError, AttributeError, ValueError):
    pass


def die(msg):
    sys.stderr.write("CLUSTER LOOKUP ERROR: " + msg + "\n")
    sys.exit(2)


# --------------------------------------------------------------------------- URLs

def _norm_fallback(u):
    """Normalize a URL for matching: scheme/host lowercased, no query, one trailing slash."""
    if not u:
        return ""
    u = str(u).strip()
    u = u.split("#")[0].split("?")[0]
    u = re.sub(r"^https?://", "", u, flags=re.I)
    u = re.sub(r"^www\.", "", u, flags=re.I)
    u = u.rstrip("/")
    return "https://" + u.lower() + "/" if u else ""


# One normalizer for the whole system. `cluster_store.normalize_url` is byte-for-byte the
# function above; binding the name to it means the two can never drift apart, and a url
# cannot mean one thing to the store and another to this script. `_norm_fallback` only runs
# on a checkout with no cluster_store.py.
norm = CS.normalize_url if CS is not None else _norm_fallback


def folder_of(u):
    m = re.match(r"^https://[^/]+(/[^/]+/)", norm(u))
    return m.group(1) if m else "/"


def slug_of(u):
    p = norm(u).rstrip("/").split("/")
    return p[-1] if p else ""


def is_lp(u):
    return "/lp/" in norm(u)


def seed_of(u, mod):
    """Stable rotation seed from the article slug — same article, same choice, every run."""
    s = slug_of(u) or norm(u)
    h = 0
    for ch in s:
        h = (h * 131 + ord(ch)) & 0xFFFFFFFF
    return h % mod if mod else 0


def code_family(url, title=""):
    t = (norm(url) + " " + (title or "")).lower()
    if re.search(r"\bccsd", t):
        return "CCSD"
    if re.search(r"\bhcpcs", t):
        return "HCPCS"
    if re.search(r"icd[- ]?1[01]", t):
        return "ICD-10"
    if re.search(r"\bcpt\b|cpt-code", t):
        return "CPT"
    if "denial" in t:
        return "denial"
    if re.search(r"\bmbs\b", t):
        return "MBS"
    if "medicare" in t or "medicaid" in t:
        return "Medicare"
    return "other"


BOFU_RE = re.compile(
    r"\b(best|top \d|vs\.?|versus|alternative|alternatives|compare|comparison|pricing|price|"
    r"cost|software options|reviews?|which|choosing|buyer)\b", re.I)


def stage_guess(url, title):
    """Heuristic funnel stage. G says classify from the target query and title — this is the
    title half; the link pass owns the final call."""
    f = folder_of(url)
    if f in CODE_FOLDERS:
        return "TOFU"
    if BOFU_RE.search(title or "") or f == "/compare/":
        return "BOFU"
    if f == "/templates/":
        return "BOFU"
    return "TOFU"


# ------------------------------------------------------------------- cluster store

def _cache_path(src, tag):
    try:
        st = os.stat(src)
        key = "%s-%d-%d" % (tag, int(st.st_mtime), st.st_size)
    except OSError:
        key = tag
    return os.path.join(CACHE_DIR, key + ".json")


def _load_cached(src, tag, build):
    path = _cache_path(src, tag)
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


def load_sheet():
    """The merged cluster index, in the shape every command below already consumes.

    The store does the work (`cluster_store.load_store`): base.jsonl + additions.jsonl from
    the synced `clusters-data` files, merged with the local workbook where one exists, under
    the precedence in CONTRACT.md. The workbook still wins — it is the highest-authority
    input — so a machine that has one behaves exactly as it always did, and a machine that
    does not now reads the branch copy instead of blocking the link pass.

    Caching is the store's, keyed on the (mtime, size) of every input, so a refreshed
    workbook or a fresh `cluster_sync.py pull` invalidates it automatically.
    """
    if CS is None:
        die("bin/cluster_store.py is missing, so the cluster store cannot be read. "
            "Run the factcheck-flow updater (~/.claude/factcheck-flow/update.sh) or "
            "reinstall — the link pass cannot run without it.")

    store = CS.load_store(xlsx_path=XLSX)
    sheet = CS.legacy_sheet(store)

    meta = store.get("meta") or {}
    xlsx_rows = (meta.get("counts") or {}).get("xlsx") or 0
    if not sheet["posts"] and not sheet["clusters"]:
        # Neither the workbook nor the synced files gave us anything. This is the only
        # hard stop: guessing a cluster is worse than doing nothing (3-links.md §0).
        die("no cluster store is readable — neither the local workbook (%s) nor the synced "
            "files (%s). Run `cluster_sync.py pull`, or set $PABAU_CLUSTERS_XLSX. Report "
            "LINKPLAN_BLOCKED and change no links." % (XLSX, meta.get("data_dir", "?")))

    # What `resolve` prints on its last line. The workbook, when present, is still the
    # authority and still what David edits, so the label does not move for him.
    sheet["source"] = XLSX if xlsx_rows else (meta.get("data_dir") or XLSX)
    built = meta.get("built") or ""
    sheet["built"] = built.replace("T", " ")[:16] if built else ""
    sheet["store_warnings"] = meta.get("warnings") or []
    return sheet


def cluster_by_name(sheet, name):
    for c in sheet["clusters"]:
        if c["name"].lower() == (name or "").lower():
            return c
    return None


def cluster_by_key(sheet, key):
    key = (key or "").strip().lower()
    for c in sheet["clusters"]:
        if c["id"].lower() == key or c["name"].lower() == key:
            return c
    for c in sheet["clusters"]:
        if key and (key in c["id"].lower() or key in c["name"].lower()):
            return c
    return None


# ---------------------------------------------------------------------- link graph

def load_graph_index():
    """url -> {in, out, pr, date, folder}. Cached; the 8 MB graph is only parsed when the
    cache is cold or the file changed."""
    if not os.path.exists(GRAPH):
        return {"nodes": {}, "stale_hours": None, "missing": True}

    def build():
        with open(GRAPH) as fh:
            g = json.load(fh)
        nodes = {}
        for n in g.get("nodes", []):
            nodes[norm(n.get("url"))] = {
                "in": n.get("in", 0), "out": n.get("out", 0),
                "pr": n.get("pr", 0.0), "date": n.get("date") or "",
                "folder": n.get("folder") or "", "title": n.get("title") or "",
            }
        return {"nodes": nodes, "missing": False}

    idx = _load_cached(GRAPH, "graph-index", build)
    try:
        idx["stale_hours"] = round((time.time() - os.stat(GRAPH).st_mtime) / 3600.0, 1)
    except OSError:
        idx["stale_hours"] = None
    return idx


def load_graph_edges():
    if not os.path.exists(GRAPH):
        return []
    with open(GRAPH) as fh:
        return json.load(fh).get("edges", [])


def graph_note(gi):
    if gi.get("missing"):
        return ("link graph not found at %s — inbound counts unavailable; "
                "fall back to REST search counts" % GRAPH)
    if gi.get("stale_hours") is not None and gi["stale_hours"] > 48:
        return ("link graph is %.0fh old — refresh it: cd ~/Desktop/linkmap && ./refresh.sh"
                % gi["stale_hours"])
    return ""


# ------------------------------------------------------------------------ resolve

def resolve_record(sheet, url, title=""):
    u = norm(url)
    post = sheet["posts"].get(u)
    review = sheet["review"].get(u)
    cl = None
    if post:
        cl = cluster_by_name(sheet, post["cluster_name"])
    if review and not cl:
        cl = cluster_by_name(sheet, review["cluster_as_assigned"])
    if not cl and folder_of(u) in CODE_FOLDERS:
        # The sheet is a fixed snapshot; a code page published after it was built is still
        # billing — "essentially all of /procedure-codes/ and /diagnostic-codes/" (rule A).
        cl = cluster_by_key(sheet, BILLING_CLUSTER_ID)
    return u, post, review, cl


def print_resolve(a):
    sheet = load_sheet()
    gi = load_graph_index()
    u, post, review, cl = resolve_record(sheet, a.url, a.title)
    fold = folder_of(u)
    title = a.title or (post or {}).get("title", "")

    print("URL              : %s" % u)
    print("Folder           : %s%s" % (fold, "" if fold in IN_SCOPE_FOLDERS
                                       else "   << OUTSIDE the four editable folders"))
    print("In spreadsheet   : %s" % ("yes" if post else "NO — published after the snapshot; infer the cluster"))
    if post:
        print("Title            : %s" % post["title"])
        print("Cluster          : %s" % post["cluster_name"])
        print("Tier             : %s" % post["tier"])
        print("Subcluster       : %s" % post["subcluster"])
        print("Published        : %s" % post["published"])
        if post["flag"]:
            print("Sheet flag       : %s  (do not re-litigate)" % post["flag"])
        if post["note"]:
            print("Sheet note       : %s" % post["note"])
    if review:
        print("REVIEW QUEUE     : %s | %s" % (review["decision"], review["rule"]))
        if "retire" in (review["decision"] + review["cluster_as_assigned"]).lower():
            print("DIRECTIVE        : retirement/reassign bucket — no link actions at all; "
                  "log and skip.")

    if cl:
        print("")
        print("Cluster id       : %s" % cl["id"])
        print("Pillar           : %s -> %s" % (cl["pillar_name"], cl["pillar_url"] or "—"))
        print("Pillar status    : %s" % cl["pillar_status"])
        print("Supporting hubs  : %s" % (" · ".join(cl["supporting"]) or "—"))
        print("Subclusters      : %s" % (" · ".join(cl["subclusters"]) or "—"))
        note = PILLAR_NOTES.get(cl["id"])
        if note:
            print("DIRECTIVE        : %s" % note)
        if is_lp(cl["pillar_url"]):
            print("DIRECTIVE        : the sheet's pillar URL is an /lp/ page — banned as a "
                  "target. See the exception above.")
    elif not post:
        print("")
        print("No cluster resolved. Run `suggest --title \"<article title>\"` and reason from "
              "the nearest posts, then re-run resolve with --cluster on `targets`.")

    budget = 3 if fold in CODE_FOLDERS else 5
    print("")
    print("In-body budget   : %d editorial links (house blocks, Continue-your-research picks "
          "and /book-demo/ CTA links excluded)" % budget)
    print("Funnel stage     : %s (heuristic from title/folder — confirm from the target query)"
          % stage_guess(u, title))
    print("Anchor rotation  : seed %d -> %s"
          % (seed_of(u, len(ANCHOR_PATTERNS)), ANCHOR_PATTERNS[seed_of(u, len(ANCHOR_PATTERNS))]))

    if cl and cl["id"] == BILLING_CLUSTER_ID or fold in CODE_FOLDERS:
        fam = code_family(u, title)
        print("")
        print("BILLING WALL     : link only inside the billing cluster and its own hubs. No "
              "other cluster's pillar. /book-demo/ CTA links are the only exception.")
        print("Code family      : %s" % fam)
        print("Required pillar  : %s" % BILLING_PILLAR)
        order = SIBLING_ORDER.get(fam, SIBLING_ORDER["other"])
        byfam = {k: (v, w) for k, v, w in SUBHUBS}
        pick = order[seed_of(u, len(order))]
        print("Subhub (rotation): %s -> %s" % (pick, byfam[pick][0]))
        print("Subhub siblings  : %s" % ", ".join(
            "%s=%s" % (k, byfam[k][0]) for k in order if k in byfam))
        print("                   Override the rotation when the article points somewhere "
              "specific (medical necessity -> icd-10-cm, denial-prone -> denial-codes).")
        print("Pattern          : 1 pillar up-link + 1 subhub + at most 1 next-step "
              "(CPT<->ICD-10 pair, or a billing template/guide). Nothing outside billing.")
        print("Funnel exemption : code pages are exempt from the TOFU->BOFU funnel mandate.")

    g = gi["nodes"].get(u)
    if g:
        print("")
        print("Link graph       : inbound %d | outbound %d | pr %.6f | crawled %s"
              % (g["in"], g["out"], g["pr"], g["date"]))
    warn = graph_note(gi)
    if warn:
        print("NOTE             : %s" % warn)
    print("")
    print("Source of truth  : %s (built %s)"
          % (sheet.get("source") or XLSX, sheet.get("built", "")))


# ------------------------------------------------------------------------ suggest

STOP = set("""a an the and or of for to in on with without your you my our their its it is are
be how what why when which who whom that this these those from at by as vs versus best top new
guide complete ultimate free template templates checklist form forms 2024 2025 2026 pabau""".split())


def toks(s):
    s = unicodedata.normalize("NFKD", str(s or "")).lower()
    return [w for w in re.findall(r"[a-z0-9]+", s) if w not in STOP and len(w) > 2]


def print_suggest(a):
    sheet = load_sheet()
    want = set(toks(a.title) + toks(a.terms or ""))
    if not want:
        die("give --title (and optionally --terms) with some words in it")
    scored = []
    for u, p in sheet["posts"].items():
        t = set(toks(p["title"]) + toks(slug_of(u).replace("-", " ")))
        if not t:
            continue
        inter = len(want & t)
        if not inter:
            continue
        scored.append((inter / float(len(want | t)) + 0.01 * inter, inter, u, p))
    scored.sort(reverse=True)
    top = scored[: a.limit]
    tally = {}
    for _, _, _, p in scored[: max(a.limit * 4, 40)]:
        key = (p["cluster_name"], p["subcluster"])
        tally[key] = tally.get(key, 0) + 1

    if getattr(a, "json", False):
        # Exactly the `evidence` object CONTRACT.md specifies, ready to hand to
        # `submit --evidence-json`. Hand-copying this out of the text below is how an
        # audit trail quietly stops matching the assignment it is supposed to justify.
        ranked = sorted(tally.items(), key=lambda kv: -kv[1])
        print(json.dumps({
            "top_matches": [{"url": u, "cluster": p["cluster_name"],
                             "subcluster": p["subcluster"], "score": round(sc, 4)}
                            for sc, _inter, u, p in top[:8]],
            "tally": [{"cluster": c, "subcluster": s, "n": n} for (c, s), n in ranked[:5]],
            "top_score": round(top[0][0], 4) if top else 0.0,
            "title_used": a.title,
            "terms_used": a.terms or "",
        }, ensure_ascii=False))
        return

    print("Nearest posts in the spreadsheet (semantic shortlist — YOU make the call):")
    for sc, inter, u, p in top:
        print("  %.3f  %-42s | %-26s | %s" % (sc, p["cluster_name"][:42],
                                              p["subcluster"][:26], u))
    print("")
    print("Cluster / subcluster tally over the shortlist:")
    for (c, s), n in sorted(tally.items(), key=lambda kv: -kv[1])[:10]:
        print("  %3d  %s  ->  %s" % (n, c, s))
    print("")
    print("Then confirm the pillar and hubs with: cluster_lookup.py clusters")


# ------------------------------------------------------------------------ targets

def print_targets(a):
    sheet = load_sheet()
    gi = load_graph_index()
    cl = cluster_by_key(sheet, a.cluster)
    if not cl:
        die("no cluster matches %r — run `clusters` for the list" % a.cluster)
    exclude = {norm(x) for x in (a.exclude or [])}
    rows = []
    for u, p in sheet["posts"].items():
        if p["cluster_name"] != cl["name"] or u in exclude:
            continue
        if a.folder and folder_of(u) != a.folder:
            continue
        if a.subcluster and a.subcluster.lower() not in p["subcluster"].lower():
            continue
        if is_lp(u):
            continue
        if a.terms:
            want = set(toks(a.terms))
            have = set(toks(p["title"]) + toks(slug_of(u).replace("-", " ")))
            if not (want & have):
                continue
        stage = stage_guess(u, p["title"])
        if a.bofu and stage != "BOFU":
            continue
        g = gi["nodes"].get(u, {})
        rows.append({
            "url": u, "title": p["title"], "sub": p["subcluster"], "stage": stage,
            "in": g.get("in", 0), "pr": g.get("pr", 0.0), "date": p["published"],
        })
    # Deterministic tie-break. All three sorts below are stable, so without this the order
    # of equally-ranked rows would follow the merge order of the store's inputs — which
    # differs between a machine that has the workbook and one that reads the branch alone.
    # Sorting by url first pins it: same cluster, same graph, same list, everywhere.
    rows.sort(key=lambda r: r["url"])
    key = {"inbound": lambda r: (r["in"], -r["pr"]),
           "pr": lambda r: (-r["pr"], r["in"]),
           "recent": lambda r: (r["date"] < "0", ),
           }.get(a.sort, lambda r: (r["in"], -r["pr"]))
    if a.sort == "recent":
        rows.sort(key=lambda r: r["date"], reverse=True)
    else:
        rows.sort(key=key)
    print("Cluster: %s (%s) | pillar %s" % (cl["name"], cl["tier"], cl["pillar_url"] or "—"))
    hint = {"inbound": "lowest inbound first = most equity-hungry",
            "pr": "highest PageRank first = strongest sources",
            "recent": "newest first"}[a.sort]
    print("%d candidates%s. Sorted by %s (%s)."
          % (len(rows), " (showing %d)" % a.limit if len(rows) > a.limit else "", a.sort, hint))
    print("%-4s %-5s %-9s %-10s %s" % ("in", "stage", "pr", "published", "url"))
    for r in rows[: a.limit]:
        print("%-4d %-5s %-9.6f %-10s %s" % (r["in"], r["stage"], r["pr"], r["date"], r["url"]))
    warn = graph_note(gi)
    if warn:
        print("NOTE: %s" % warn)


# -------------------------------------------------------------- target legality (A)

def abs_url(s):
    return norm("https://pabau.com" + s) if str(s).startswith("/") else norm(s)


def hub_maps(sheet):
    """Every target rule A allows, keyed by normalized URL."""
    pillars, tier2_hubs = {}, {}
    for c in sheet["clusters"]:
        if c["pillar_url"] and not is_lp(c["pillar_url"]):
            pillars[norm(c["pillar_url"])] = c
        if c["tier"].startswith("Tier 2"):
            for s in c["supporting"]:
                if str(s).startswith(("/", "http")):
                    tier2_hubs[abs_url(s)] = c
    return pillars, tier2_hubs


# LEGAL_* codes are targets rule A permits; the rest are dispositions.
LEGAL = ("LEGAL_SAME_CLUSTER", "LEGAL_OWN_PILLAR", "LEGAL_OWN_HUB", "LEGAL_OTHER_PILLAR",
         "LEGAL_TIER2_HUB", "LEGAL_BILLING_PILLAR", "LEGAL_BILLING_SUBHUB", "CTA")


def judge_target(sheet, from_cl, url):
    """One place decides whether a target is legal for this source — classify reports it,
    verify enforces it. Returns (code, explanation)."""
    u = norm(url)
    fold = folder_of(u)
    p = sheet["posts"].get(u)
    cl = cluster_by_name(sheet, p["cluster_name"]) if p else None
    if not cl and fold in CODE_FOLDERS:
        cl = cluster_by_key(sheet, BILLING_CLUSTER_ID)
    pillars, tier2_hubs = hub_maps(sheet)
    own_hubs = {abs_url(s) for s in (from_cl or {}).get("supporting", [])
                if str(s).startswith(("/", "http"))}
    subhub_urls = {norm(v) for _, v, _ in SUBHUBS}

    if is_lp(u):
        return "LP_TARGET", "never a target, in body or in a pick — REMOVE"
    if "/book-demo/" in u:
        return "CTA", "CTA link — never removed or rerouted"
    if u not in subhub_urls and (
            re.search(r"^https://[^/]+/(blog|templates|procedure-codes|diagnostic-codes)/$", u)
            or re.search(r"/(author|page|category|tag)/", u)):
        return ("ARCHIVE", "an index or archive page, not an article — never an editorial "
                           "target; REMOVE")
    if from_cl and from_cl["id"] == BILLING_CLUSTER_ID:
        # The strictest wall: billing links only inside billing and its own hubs.
        if u == norm(BILLING_PILLAR):
            return "LEGAL_BILLING_PILLAR", "the billing pillar up-link (exactly one per page)"
        if u in subhub_urls:
            return "LEGAL_BILLING_SUBHUB", "billing subhub (exactly one per code page)"
        if cl and cl["id"] == BILLING_CLUSTER_ID:
            return "LEGAL_SAME_CLUSTER", "legal next-step inside billing"
        return ("BILLING_WALL_BREACH", "billing pages link nothing outside billing, "
                                       "not even another cluster's pillar — REMOVE")
    if u in subhub_urls and from_cl:
        return ("CROSS_CLUSTER", "a billing subhub — inbound, non-billing pages may link the "
                                 "billing pillar only; REROUTE or REMOVE")
    if from_cl and cl and cl["name"] == from_cl["name"]:
        return "LEGAL_SAME_CLUSTER", "same cluster — legal target"
    if from_cl and norm(from_cl["pillar_url"]) == u:
        return "LEGAL_OWN_PILLAR", "own pillar up-link (exactly one per page)"
    if u in own_hubs:
        return "LEGAL_OWN_HUB", "own cluster's supporting hub"
    if u in pillars:
        return ("LEGAL_OTHER_PILLAR", "another cluster's PILLAR — legal cross-cluster link (A), "
                                      "but only where the prose genuinely discusses that topic")
    if u in tier2_hubs:
        return ("LEGAL_TIER2_HUB", "Tier-2 cross-industry hub (%s) — legal where the prose "
                                   "genuinely discusses that operational function"
                % tier2_hubs[u]["id"])
    if p and from_cl:
        return ("CROSS_CLUSTER", "another cluster's post — REMOVE, or REROUTE to that cluster's "
                                 "pillar if the mention survives naturally")
    if fold not in IN_SCOPE_FOLDERS:
        return ("CROSS_CLUSTER", "not a pillar, listed hub or in-cluster post — A allows no "
                                 "such target; default REMOVE")
    return ("UNRESOLVED", "published after the sheet snapshot — resolve its cluster with "
                          "`suggest` before keeping")


# ----------------------------------------------------------------------- classify

def print_classify(a):
    sheet = load_sheet()
    gi = load_graph_index()
    from_cl = None
    if a.from_url:
        _, _, _, from_cl = resolve_record(sheet, a.from_url)
    urls = list(a.urls or [])
    if a.urls_file:
        with open(a.urls_file) as fh:
            urls += [l.strip() for l in fh if l.strip()]
    if not urls:
        die("give --urls or --urls-file")
    if from_cl:
        print("Source cluster: %s (%s) | pillar %s"
              % (from_cl["name"], from_cl["tier"], from_cl["pillar_url"] or "—"))
    else:
        print("Source cluster unresolved — pass --from-url, or resolve it with `suggest` first. "
              "Cross-cluster verdicts below are unreliable without it.")
    print("")
    for raw in urls:
        u = norm(raw)
        p = sheet["posts"].get(u)
        g = gi["nodes"].get(u, {})
        code, why = judge_target(sheet, from_cl, u)
        print("%s" % u)
        print("   folder %-18s inbound %-4s cluster %s"
              % (folder_of(u), g.get("in", "?"), (p or {}).get("cluster_name", "—")))
        if p and p["subcluster"]:
            print("   subcluster %s | stage %s" % (p["subcluster"], stage_guess(u, p["title"])))
        print("   -> %-22s %s" % (code, why))
        if g.get("in", 0) == 1:
            print("   -> ANTI-ORPHAN WATCH: only one inbound link in the graph. Removing it "
                  "orphans the page — see rule B.")


# ----------------------------------------------------------------------- clusters

def print_clusters(a):
    sheet = load_sheet()
    for c in sheet["clusters"]:
        print("%-2s %-32s %-24s %s" % (c["n"], c["id"], c["tier"], c["pillar_url"] or "—"))
        print("     name        : %s  (%s posts)" % (c["name"], c["posts"]))
        print("     supporting  : %s" % (" · ".join(c["supporting"]) or "—"))
        print("     subclusters : %s" % (" · ".join(c["subclusters"]) or "—"))
        if PILLAR_NOTES.get(c["id"]):
            print("     DIRECTIVE   : %s" % PILLAR_NOTES[c["id"]])


# ------------------------------------------------------------------------ subhubs

def http_code(url):
    try:
        out = subprocess.run(
            ["curl", "-sI", "-o", "/dev/null", "-w", "%{http_code}", "-A", "Mozilla/5.0",
             "--max-time", "15", url], capture_output=True, text=True, timeout=25)
        return out.stdout.strip()
    except Exception:
        return "???"


def print_subhubs(a):
    print("Billing ADD_SUBHUB target set (families named in the Clusters sheet):")
    for fam, url, kind in SUBHUBS:
        code = " [%s]" % http_code(url) if a.verify else ""
        print("  %-17s %s%s   (%s)" % (fam, url, code, kind))
    print("")
    print("Pillar: %s" % BILLING_PILLAR)
    print("Rotate the subhub across pages so equity spreads; `resolve --url` prints the "
          "rotation pick for one page.")
    if not a.verify:
        print("Re-verify with --verify before shipping a link to any of them.")


# ------------------------------------------------------------------------- verify

COUNTING_TYPES = {"KEEP", "KEEP_ANTI_ORPHAN", "REWRITE_ANCHOR", "REROUTE", "ADD_PILLAR",
                  "ADD_SUBHUB", "ADD_BOOST", "ADD_NEXTSTEP", "ADD_FUNNEL"}
ALL_TYPES = COUNTING_TYPES | {"REMOVE", "ADD_CTA", "REPLACE_PICK"}


def print_verify(a):
    sheet = load_sheet()
    gi = load_graph_index()
    u, post, review, cl = resolve_record(sheet, a.url)
    try:
        with open(a.plan) as fh:
            plan = json.load(fh)
    except Exception as e:
        die("could not read plan %s: %s" % (a.plan, e))

    links = plan.get("links", []) or []
    picks = [norm(p if isinstance(p, str) else p.get("target")) for p in plan.get("picks", [])]
    fold = folder_of(u)
    budget = 3 if fold in CODE_FOLDERS else 5
    fails, warns = [], []

    def bad(msg):
        fails.append(msg)

    # An article published after the snapshot has no sheet row — the link pass resolves its
    # cluster by reasoning (§0) and declares it here. The sheet always wins where it has a row.
    declared = cluster_by_key(sheet, plan.get("cluster", "")) if plan.get("cluster") else None
    if declared and post and cl and declared["name"] != cl["name"]:
        bad("plan declares cluster %s but the spreadsheet assigns %s — the sheet is the source "
            "of truth; do not re-litigate it" % (declared["id"], cl["id"]))
    if declared and not cl:
        cl = declared
    if not cl:
        warns.append("no cluster resolved for this article — declare it in the plan as "
                     "\"cluster\": \"<cluster id>\" so the wall checks can run")

    for l in links:
        t = (l.get("type") or "").upper()
        if t not in ALL_TYPES:
            bad("unknown action type %r on %s" % (l.get("type"), l.get("target")))

    final = [l for l in links if (l.get("type") or "").upper() in COUNTING_TYPES]

    # 1. /lp/ and folder scope
    for l in links + [{"target": p, "type": "REPLACE_PICK"} for p in picks]:
        if is_lp(l.get("target")) and (l.get("type") or "").upper() != "REMOVE":
            bad("LP_TARGET survives: %s" % l.get("target"))
    if fold not in IN_SCOPE_FOLDERS:
        bad("the edited page is outside the four editable folders (%s)" % fold)

    # 2. budget
    if len(final) > budget:
        bad("budget: %d in-body editorial links, limit %d" % (len(final), budget))

    # 3. pillar up-link
    pillars = [l for l in final if (l.get("type") or "").upper() == "ADD_PILLAR"
               or l.get("role") == "pillar"]
    exempt = bool(cl and cl["id"] in ("pabau-product-updates", "retire-review",
                                      "optometry-eye-care"))
    if not exempt:
        if len(pillars) != 1:
            bad("pillar up-link: found %d, need exactly 1" % len(pillars))
        elif cl and cl["pillar_url"] and not is_lp(cl["pillar_url"]):
            want = norm(cl["pillar_url"])
            if cl["id"] == BILLING_CLUSTER_ID:
                want = norm(BILLING_PILLAR)
            if norm(pillars[0].get("target")) != want:
                bad("pillar up-link points at %s; this cluster's pillar is %s"
                    % (pillars[0].get("target"), want))

    # 4. target legality — the same judge `classify` prints, enforced
    for l in final:
        code, why = judge_target(sheet, cl, l.get("target"))
        if code in LEGAL:
            continue
        if code == "UNRESOLVED" and l.get("cluster_confirmed"):
            # Target is newer than the snapshot and the pass resolved its cluster by hand.
            warns.append("target newer than the snapshot, cluster confirmed by the pass: %s"
                         % l.get("target"))
            continue
        bad("%s: %s (%s)" % (code, l.get("target"), why))

    # 5. code-page pattern
    if fold in CODE_FOLDERS:
        subs = {norm(v) for _, v, _ in SUBHUBS}
        got = [l for l in final if norm(l.get("target")) in subs
               or (l.get("type") or "").upper() == "ADD_SUBHUB"]
        if len(got) != 1:
            bad("code page: %d subhub links, need exactly 1 (see `subhubs`)" % len(got))

    # 6. the absolute page ceiling
    total = plan.get("total_outbound")
    if isinstance(total, int) and total > 50:
        bad("page carries %d outbound links, ceiling 50 (CTA links excluded)" % total)
    elif total is None:
        warns.append("record total_outbound (every outbound link on the page, CTA links "
                     "excluded) so the 50-link ceiling can be checked")

    # 7. anchors
    seen = {}
    for l in final:
        a_txt = (l.get("anchor") or "").strip().lower()
        if not a_txt:
            bad("no anchor recorded for %s" % l.get("target"))
            continue
        seen[a_txt] = seen.get(a_txt, 0) + 1
    for txt, n in seen.items():
        if n > 3:
            bad("anchor %r used %d times (max 3 per article)" % (txt, n))
        if txt in ("click here", "read more", "here", "this article", "learn more"):
            bad("BAD_ANCHOR: %r" % txt)
        if txt.startswith("http"):
            bad("BAD_ANCHOR: bare URL %r" % txt)

    # 8. picks stay inside the cluster
    for p in picks:
        pp = sheet["posts"].get(p)
        if is_lp(p):
            bad("pick is an /lp/ URL: %s" % p)
        elif not pp:
            warns.append("pick not in the sheet, confirm its cluster by hand: %s" % p)
        elif cl and pp["cluster_name"] != cl["name"]:
            bad("pick outside the cluster (%s): %s" % (pp["cluster_name"], p))
    if len(picks) > 5:
        bad("Continue your research: %d picks, max 5" % len(picks))

    # 9. CTA contract
    cta = [l for l in links if "/book-demo/" in norm(l.get("target"))]
    if plan.get("cta_promotional") is not True or plan.get("cta_conclusion") is not True:
        if len(cta) < 2:
            warns.append("record cta_promotional/cta_conclusion true in the plan once both "
                         "/book-demo/ placements exist (G)")
    for l in links:
        if "/book-demo/" in norm(l.get("target")) and \
                (l.get("type") or "").upper() in ("REMOVE", "REROUTE"):
            bad("a /book-demo/ link is never removed or rerouted: %s" % l.get("target"))

    # 10. anti-orphan on removals
    for l in links:
        if (l.get("type") or "").upper() in ("REMOVE", "REROUTE"):
            g = gi["nodes"].get(norm(l.get("target")), {})
            if g.get("in", 99) <= 1 and not is_lp(l.get("target")):
                warns.append("removing %s may orphan it (inbound=%s) — rule B wants a "
                             "compliant same-cluster ADD or KEEP_ANTI_ORPHAN"
                             % (l.get("target"), g.get("in")))

    # 11. funnel mandate
    stage = (plan.get("stage") or stage_guess(u, (post or {}).get("title", ""))).upper()
    if stage == "TOFU" and fold in ("/blog/", "/templates/") and not exempt:
        fun = [l for l in final if (l.get("type") or "").upper() == "ADD_FUNNEL"
               or l.get("role") == "funnel"]
        if not fun and not plan.get("no_bofu_in_cluster"):
            bad("TOFU post with no same-cluster BOFU funnel link (G) — add one or set "
                "no_bofu_in_cluster true and log NO_BOFU_IN_CLUSTER")

    # 12. engine recorded
    if (plan.get("engine") or "").lower() not in ("gutenberg", "classic", "elementor"):
        bad("record engine: gutenberg | classic | elementor (rule F)")

    print("PLAN: %s" % u)
    print("cluster %s | folder %s | stage %s | budget %d | in-body links %d | picks %d"
          % ((cl or {}).get("name", "—"), fold, stage, budget, len(final), len(picks)))
    for w in warns:
        print("WARN  %s" % w)
    for f in fails:
        print("FAIL  %s" % f)
    print("%s | %d checks failed, %d warnings" % ("FAIL" if fails else "PASS",
                                                  len(fails), len(warns)))
    sys.exit(1 if fails else 0)


# -------------------------------------------------------------------------- submit

def delegate_submit(argv):
    """`cluster_lookup.py submit ...` -> `cluster_sync.py submit ...`, unchanged.

    The link pass reads and writes through one entry point, but the write path has exactly
    one implementation (CONTRACT.md, "Write path" step 2). Every flag, every exit code and
    every refusal is cluster_sync's — nothing is re-parsed or re-interpreted here, so the
    alias cannot drift away from the thing it aliases.
    """
    try:
        import cluster_sync
    except Exception as e:
        die("bin/cluster_sync.py is missing or unimportable (%s), so a reasoned assignment "
            "cannot be written back. Run the factcheck-flow updater "
            "(~/.claude/factcheck-flow/update.sh)." % e)
    sys.argv = [os.path.join(BIN_DIR, "cluster_sync.py"), "submit"] + list(argv)
    cluster_sync.main()


# --------------------------------------------------------------------------- main

def main():
    # Delegated before argparse sees it: a thin alias must not re-declare, re-order or
    # swallow a single one of cluster_sync's flags.
    if len(sys.argv) > 1 and sys.argv[1] == "submit":
        delegate_submit(sys.argv[2:])
        return

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd")

    p = sub.add_parser("resolve", help="cluster, pillar, budget and directives for one URL")
    p.add_argument("--url", required=True)
    p.add_argument("--title", default="")
    p.set_defaults(fn=print_resolve)

    p = sub.add_parser("suggest", help="nearest posts for a URL that is not in the sheet")
    p.add_argument("--title", required=True)
    p.add_argument("--terms", default="")
    p.add_argument("--limit", type=int, default=12)
    p.add_argument("--json", action="store_true",
                   help="emit the CONTRACT.md `evidence` object instead of the text "
                        "shortlist, ready for `submit --evidence-json`")
    p.set_defaults(fn=print_suggest)

    p = sub.add_parser("targets", help="candidate in-cluster link targets")
    p.add_argument("--cluster", required=True, help="cluster id or name")
    p.add_argument("--subcluster", default="")
    p.add_argument("--folder", default="", help="/blog/ | /templates/ | /procedure-codes/ ...")
    p.add_argument("--terms", default="", help="keep only titles sharing a word with these")
    p.add_argument("--bofu", action="store_true", help="BOFU candidates only (heuristic)")
    p.add_argument("--sort", default="inbound", choices=["inbound", "pr", "recent"])
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--exclude", nargs="*", default=[])
    p.set_defaults(fn=print_targets)

    p = sub.add_parser("classify", help="verdict for each link currently in the body")
    p.add_argument("--urls", nargs="*", default=[])
    p.add_argument("--urls-file", default="")
    p.add_argument("--from-url", default="", help="the article being edited")
    p.set_defaults(fn=print_classify)

    p = sub.add_parser("clusters", help="all clusters, tiers, pillars and hubs")
    p.set_defaults(fn=print_clusters)

    p = sub.add_parser("subhubs", help="the billing subhub target set")
    p.add_argument("--verify", action="store_true", help="curl each one for its status code")
    p.set_defaults(fn=print_subhubs)

    p = sub.add_parser("verify", help="mechanical gate over a finished link plan")
    p.add_argument("--url", required=True)
    p.add_argument("--plan", required=True, help="JSON: {engine, stage, links[], picks[]}")
    p.set_defaults(fn=print_verify)

    # Registered so `-h` lists it; the real handling happens above, before argparse runs.
    sub.add_parser("submit", add_help=False,
                   help="write a reasoned assignment back to the store "
                        "(alias for cluster_sync.py submit — see its --help)")

    a = ap.parse_args()
    if not getattr(a, "fn", None):
        ap.print_help()
        sys.exit(2)
    a.fn(a)


if __name__ == "__main__":
    main()
