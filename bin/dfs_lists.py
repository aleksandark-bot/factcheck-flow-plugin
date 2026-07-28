#!/usr/bin/env python3
"""Build the /SEO keyword lists (Stage 2) entirely in code.

Replaces ~26k tokens of raw DataForSEO JSON in the model's context with one compact
payload, and makes the thresholds deterministic instead of model-judged. Emits exactly
the shape `keyword_picker.py --in` expects, so Stage 3 can hand it straight over.

Usage:
  dfs_lists.py --main-keyword "<kw>" --out /tmp/seo-<slug>-kw.json \\
               [--article-title "<title>"] [--article-url "<url>"] \\
               [--competitor-url <url>]...            # repeatable; list C \\
               [--gsc /tmp/gsc.json]                  # gsc_query.py output; list D \\
               [--article-text /tmp/article.txt]      # headings + body, for present_on_page \\
               [--location "United States"] [--language en] \\
               [--list-len 20] [--competitor-top-n 20]

Auth, resolved in this order (nothing secret lives in this repo):
  1. $DATAFORSEO_AUTH                     base64 of "login:password"
  2. $DATAFORSEO_LOGIN + $DATAFORSEO_PASSWORD
  3. ~/.claude/factcheck-flow/dataforseo-key.json   {"login":..,"password":..} or {"auth":".."}
  4. the `dataforseo` MCP server entry in ~/.claude.json (its Authorization header)

Output: the picker payload on --out, plus a one-line summary on stdout. All five lists
are deduped across each other (priority gsc > competitor > related > variations >
highly_relevant), tier-filled toward --list-len, and ranked per David's rules.

What this script deliberately does NOT do: judge topical relevance. Off-topic, off-intent
and brand terms that don't fit Pabau still need a human/model eye — but they are struck
from ~100 short rows, not from raw API JSON.

Exit codes: 0 ok; 2 on a setup/auth/API error, with a clear message on stderr.
"""
import os, sys, json, re, base64, argparse, itertools
import urllib.request, urllib.error

API = "https://api.dataforseo.com"


def die(msg):
    sys.stderr.write("DFS ERROR: " + msg + "\n")
    sys.exit(2)


# ---------------------------------------------------------------- auth

def resolve_auth():
    a = os.environ.get("DATAFORSEO_AUTH")
    if a:
        return a.strip()
    lo, pw = os.environ.get("DATAFORSEO_LOGIN"), os.environ.get("DATAFORSEO_PASSWORD")
    if lo and pw:
        return base64.b64encode(("%s:%s" % (lo, pw)).encode()).decode()

    kf = os.path.expanduser("~/.claude/factcheck-flow/dataforseo-key.json")
    if os.path.exists(kf):
        try:
            d = json.load(open(kf))
        except Exception as e:
            die("could not read %s: %s" % (kf, e))
        if d.get("auth"):
            return d["auth"]
        if d.get("login") and d.get("password"):
            return base64.b64encode(("%s:%s" % (d["login"], d["password"])).encode()).decode()

    cj = os.path.expanduser("~/.claude.json")
    if os.path.exists(cj):
        try:
            hdr = json.load(open(cj))["mcpServers"]["dataforseo"]["headers"]["Authorization"]
            if hdr.lower().startswith("basic "):
                return hdr.split(None, 1)[1].strip()
        except Exception:
            pass

    die("no DataForSEO credentials. Set $DATAFORSEO_LOGIN and $DATAFORSEO_PASSWORD, or "
        "put {\"login\":..,\"password\":..} in ~/.claude/factcheck-flow/dataforseo-key.json")


AUTH = None


def post(path, task):
    """POST one task to a DataForSEO live endpoint; return result[0] (or {})."""
    req = urllib.request.Request(API + path, data=json.dumps([task]).encode(), method="POST")
    req.add_header("Authorization", "Basic " + AUTH)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        die("%s HTTP %s: %s" % (path, e.code, e.read().decode("utf-8", "ignore")[:300]))
    except Exception as e:
        die("%s failed: %s" % (path, e))
    if resp.get("status_code") not in (20000, None):
        die("%s: %s" % (path, resp.get("status_message")))
    tasks = resp.get("tasks") or []
    if not tasks:
        return {}
    t = tasks[0]
    if t.get("status_code") not in (20000, None):
        sys.stderr.write("DFS WARN %s: %s\n" % (path, t.get("status_message")))
        return {}
    res = t.get("result") or []
    return res[0] if res else {}


# ---------------------------------------------------------------- parsing

def unwrap(item):
    """Discovery endpoints nest the payload under keyword_data; others don't."""
    return item.get("keyword_data", item) if isinstance(item, dict) else {}


def row_from(item):
    kd = unwrap(item)
    kw = kd.get("keyword")
    if not kw:
        return None
    info = kd.get("keyword_info") or {}
    props = kd.get("keyword_properties") or {}
    intent = (kd.get("search_intent_info") or {}).get("main_intent")
    diff = props.get("keyword_difficulty")
    r = {
        "keyword": str(kw).strip().lower(),
        "volume": info.get("search_volume"),
        "difficulty": diff if isinstance(diff, int) else None,
        "intent": intent,
    }
    # ranked_keywords carries the competitor's SERP position alongside the keyword
    se = (item.get("ranked_serp_element") or {}).get("serp_item") or {}
    if se:
        r["_etv"] = se.get("etv") or 0
        r["_rank"] = se.get("rank_group")
    return r


def items_of(result):
    return (result or {}).get("items") or []


# ---------------------------------------------------------------- text utils

STOP = set("a an and or the of for to in on at by with from is are be as vs versus your "
           "you my our their it its how what when where which who why do does can".split())


def norm(s):
    s = re.sub(r"[^a-z0-9\s]", " ", (s or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def singular(w):
    if len(w) > 3 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("es") and not w.endswith("ses"):
        return w[:-2]
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def content_words(s):
    return [singular(w) for w in norm(s).split() if w not in STOP]


def same_keyword(a, b):
    return content_words(a) == content_words(b)


QUALIFIER_HINTS = set("for beginners women men small large solo new startup private group "
                      "clinic clinics practice practices spa spas uk us usa nhs".split())


def classify(cand, main_words):
    """VARIATION keeps the main keyword's head terms; RELATED drops them."""
    cw = content_words(cand)
    if not main_words:
        return "related", False
    kept = sum(1 for w in main_words if w in cw)
    frac = kept / float(len(main_words))
    extra = [w for w in cw if w not in main_words]
    qualifier = bool(extra) and bool(set(extra) & QUALIFIER_HINTS)
    if frac > 0.5:
        return "variation", qualifier
    return "related", False


# ---------------------------------------------------------------- ranking

def bands(r):
    d, v = r.get("difficulty"), r.get("volume") or 0
    kd_band = 0 if (isinstance(d, int) and d <= 5) else (1 if isinstance(d, int) and d <= 10 else 2)
    vol_band = 0 if v >= 100 else (1 if v >= 50 else (2 if v >= 20 else 3))
    return kd_band, vol_band


def tier_of(r, floor=20):
    d, v = r.get("difficulty"), r.get("volume") or 0
    if isinstance(d, int) and d <= 10 and v >= floor:
        return 1
    if isinstance(d, int) and d > 10 and v >= floor:
        return 2
    return 3


def sort_key(r):
    t = r["_tier"]
    kd_band, vol_band = bands(r)
    d = r.get("difficulty")
    v = r.get("volume") or 0
    if t == 1:
        return (1, kd_band, vol_band, -v)
    if t == 2:
        return (2, d if isinstance(d, int) else 999, -v)
    # tier 3: known difficulty first, N/A at the bottom, both by volume desc
    return (3, 0 if isinstance(d, int) else 1, -v)


def fill(pool, target, exclude_exact):
    """Apply hygiene, tier, sort, and cut to target."""
    seen, out = set(), []
    for r in pool:
        k = " ".join(content_words(r["keyword"]))
        if not k or k in seen or k in exclude_exact:
            continue
        seen.add(k)
        r["_tier"] = tier_of(r)
        out.append(r)
    out.sort(key=sort_key)
    return out[:target]


def why_for(r, list_name):
    d = r.get("difficulty")
    ds = d if isinstance(d, int) else "N/A"
    v = r.get("volume")
    vs = v if isinstance(v, int) else "?"
    if list_name == "competitor" and r.get("_rank"):
        return "competitor ranks #%s, diff %s / vol %s" % (r["_rank"], ds, vs)
    if list_name == "variations" and r.get("_qualifier"):
        return "qualifier variation, diff %s / vol %s" % (ds, vs)
    if list_name == "related":
        return "distinct entity, diff %s / vol %s" % (ds, vs)
    return "diff %s / vol %s" % (ds, vs)


# ---------------------------------------------------------------- enrichment

def chunks(seq, n):
    it = iter(seq)
    while True:
        c = list(itertools.islice(it, n))
        if not c:
            return
        yield c


def enrich(rows, loc, lang):
    """Fill missing difficulty / volume / intent with batch calls."""
    by_kw = {}
    for r in rows:
        by_kw.setdefault(r["keyword"], []).append(r)
    kws = list(by_kw)
    if not kws:
        return

    need_d = [k for k in kws if not isinstance(by_kw[k][0].get("difficulty"), int)]
    for batch in chunks(need_d, 700):
        res = post("/v3/dataforseo_labs/google/bulk_keyword_difficulty/live",
                   {"keywords": batch, "location_name": loc, "language_code": lang})
        for it in items_of(res):
            kw, d = (it.get("keyword") or "").lower(), it.get("keyword_difficulty")
            if kw in by_kw and isinstance(d, int):
                for r in by_kw[kw]:
                    r["difficulty"] = d

    need_v = [k for k in kws if by_kw[k][0].get("volume") is None]
    for batch in chunks(need_v, 700):
        res = post("/v3/dataforseo_labs/google/keyword_overview/live",
                   {"keywords": batch, "location_name": loc, "language_code": lang})
        for it in items_of(res):
            kd = unwrap(it)
            kw = (kd.get("keyword") or "").lower()
            info = kd.get("keyword_info") or {}
            if kw in by_kw:
                for r in by_kw[kw]:
                    if r.get("volume") is None:
                        r["volume"] = info.get("search_volume")
                    if not r.get("intent"):
                        r["intent"] = (kd.get("search_intent_info") or {}).get("main_intent")

    need_i = [k for k in kws if not by_kw[k][0].get("intent")]
    for batch in chunks(need_i, 900):
        res = post("/v3/dataforseo_labs/google/search_intent/live",
                   {"keywords": batch, "language_code": lang})
        for it in items_of(res):
            kw = (it.get("keyword") or "").lower()
            lab = (it.get("keyword_intent") or {}).get("label")
            if kw in by_kw and lab:
                for r in by_kw[kw]:
                    r["intent"] = lab


def out_row(r, list_name):
    d = r.get("difficulty")
    return {
        "keyword": r["keyword"],
        "difficulty": d if isinstance(d, int) else "N/A",
        "volume": r.get("volume"),
        "intent": r.get("intent") or "",
        "why": why_for(r, list_name),
        "new_main_candidate": bool(r.get("_new_main")),
    }


# ---------------------------------------------------------------- main

def main():
    global AUTH
    ap = argparse.ArgumentParser()
    ap.add_argument("--main-keyword", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--article-title", default="")
    ap.add_argument("--article-url", default="")
    ap.add_argument("--competitor-url", action="append", default=[])
    ap.add_argument("--gsc", default=None, help="gsc_query.py JSON output (published only)")
    ap.add_argument("--article-text", default=None, help="headings + body text file")
    ap.add_argument("--headings", default=None, help="one exact heading per line")
    ap.add_argument("--location", default="United States")
    ap.add_argument("--language", default="en")
    ap.add_argument("--list-len", type=int, default=20)
    ap.add_argument("--competitor-top-n", type=int, default=20)
    a = ap.parse_args()

    AUTH = resolve_auth()
    main_kw = a.main_keyword.strip().lower()
    main_words = content_words(main_kw)
    loc, lang, N = a.location, a.language, a.list_len

    body_text = ""
    if a.article_text and os.path.exists(a.article_text):
        body_text = norm(open(a.article_text, errors="replace").read())
    exact_headings = set()
    if a.headings and os.path.exists(a.headings):
        for line in open(a.headings, errors="replace"):
            if line.strip():
                exact_headings.add(" ".join(content_words(line)))

    # ---- A/E: keyword_ideas (one call, used for both Related and Highly relevant)
    ideas = items_of(post("/v3/dataforseo_labs/google/keyword_ideas/live",
                          {"keywords": [main_kw], "location_name": loc, "language_code": lang,
                           "limit": 200, "include_serp_info": False}))
    ideas_rows = [r for r in (row_from(i) for i in ideas) if r]

    # ---- A: related_keywords (depth 2)
    rel = items_of(post("/v3/dataforseo_labs/google/related_keywords/live",
                        {"keyword": main_kw, "location_name": loc, "language_code": lang,
                         "depth": 2, "limit": 200, "include_serp_info": False}))
    rel_rows = [r for r in (row_from(i) for i in rel) if r]

    # ---- B: keyword_suggestions
    sug = items_of(post("/v3/dataforseo_labs/google/keyword_suggestions/live",
                        {"keyword": main_kw, "location_name": loc, "language_code": lang,
                         "limit": 200, "include_serp_info": False}))
    sug_rows = [r for r in (row_from(i) for i in sug) if r]

    # ---- C: ranked_keywords per selected competitor URL
    comp_rows = []
    for url in a.competitor_url:
        res = post("/v3/dataforseo_labs/google/ranked_keywords/live",
                   {"target": url, "location_name": loc, "language_code": lang,
                    "limit": a.competitor_top_n,
                    "order_by": ["ranked_serp_element.serp_item.etv,desc"]})
        comp_rows += [r for r in (row_from(i) for i in items_of(res)) if r]

    # ---- classify A+B into related vs variations
    related_pool, variations_pool = [], []
    for r in rel_rows + ideas_rows + sug_rows:
        if same_keyword(r["keyword"], main_kw):
            continue                                   # the bare main keyword has no value
        kind, qualifier = classify(r["keyword"], main_words)
        r["_qualifier"] = qualifier
        (variations_pool if kind == "variation" else related_pool).append(r)
    # qualifier variations are high value — surface them near the top of their tier
    variations_pool.sort(key=lambda r: 0 if r.get("_qualifier") else 1)

    # ---- enrich everything in batch before filtering
    all_rows = related_pool + variations_pool + comp_rows + ideas_rows
    enrich(all_rows, loc, lang)

    # current main keyword, for the picker's comparison line
    cm = {"keyword": main_kw, "difficulty": "N/A", "volume": None}
    cm_rows = [{"keyword": main_kw, "volume": None, "difficulty": None, "intent": None}]
    enrich(cm_rows, loc, lang)
    if isinstance(cm_rows[0].get("difficulty"), int):
        cm["difficulty"] = cm_rows[0]["difficulty"]
    cm["volume"] = cm_rows[0].get("volume")

    lists = {
        "related": fill(related_pool, N, exact_headings),
        "variations": fill(variations_pool, N, exact_headings),
        "competitor": fill(comp_rows, N, exact_headings),
    }
    # E: raw relevance order, no tier filtering, hygiene only
    hr, seen_hr = [], set()
    for r in ideas_rows:
        k = " ".join(content_words(r["keyword"]))
        if not k or k in seen_hr or k in exact_headings or same_keyword(r["keyword"], main_kw):
            continue
        seen_hr.add(k)
        hr.append(r)
    lists["highly_relevant"] = hr[:N]

    # ---- D: GSC (published only)
    gsc = []
    if a.gsc and os.path.exists(a.gsc):
        gq = json.load(open(a.gsc)).get("queries", [])
        for q in gq:
            gsc.append({"keyword": q["query"].strip().lower(), "position": q.get("position"),
                        "clicks": q.get("clicks", 0), "impressions": q.get("impressions", 0),
                        "difficulty": None, "volume": None, "intent": None})
        enrich(gsc, loc, lang)
        for r in gsc:
            k_norm = " ".join(content_words(r["keyword"]))
            present = bool(k_norm) and (norm(r["keyword"]) in body_text or k_norm in body_text)
            r["present_on_page"] = present
            pos = r.get("position") or 999
            if present:
                r["opportunity"] = ""
            elif pos <= 10:
                r["opportunity"] = "ranking, not on-page — add to a heading/body"
            else:
                r["opportunity"] = "not top 10 — target with a new heading + content"
        gsc.sort(key=lambda r: r.get("position") or 999)   # best rank first

    # ---- cross-list dedupe: keep the highest-priority list, note the overlap
    priority = ["gsc_ranking", "competitor", "related", "variations", "highly_relevant"]
    bucket = dict(lists)
    bucket["gsc_ranking"] = gsc
    kept = {}
    for name in priority:
        survivors = []
        for r in bucket.get(name, []):
            k = " ".join(content_words(r["keyword"]))
            if k in kept:
                kept[k].setdefault("_also", []).append(name)
                continue
            kept[k] = r
            survivors.append(r)
        bucket[name] = survivors

    # ---- new-main candidate: bigger volume than the current main, and supersedes it
    cur_v = cm.get("volume") or 0
    for name in ("variations", "competitor"):
        for r in bucket.get(name, []):
            v = r.get("volume") or 0
            cw = content_words(r["keyword"])
            if v > max(cur_v * 1.5, cur_v + 50) and all(w in cw for w in main_words):
                r["_new_main"] = True

    payload = {
        "article_title": a.article_title,
        "article_url": a.article_url,
        "current_main": cm,
        "lists": {},
    }
    for name in ("related", "variations", "competitor", "highly_relevant"):
        rows = []
        for r in bucket.get(name, []):
            o = out_row(r, name)
            if r.get("_also"):
                o["why"] += " (also in %s)" % ", ".join(sorted(set(r["_also"])))
            if name == "highly_relevant":
                o.pop("why", None)
                o.pop("new_main_candidate", None)
                o["relevance_rank"] = len(rows) + 1
            rows.append(o)
        payload["lists"][name] = rows
    if gsc:
        payload["lists"]["gsc_ranking"] = [{
            "keyword": r["keyword"],
            "position": round(r["position"], 1) if isinstance(r.get("position"), (int, float)) else None,
            "clicks": r.get("clicks", 0), "impressions": r.get("impressions", 0),
            "difficulty": r["difficulty"] if isinstance(r.get("difficulty"), int) else "N/A",
            "volume": r.get("volume"), "intent": r.get("intent") or "",
            "present_on_page": r.get("present_on_page", False),
            "opportunity": r.get("opportunity", ""),
        } for r in bucket.get("gsc_ranking", [])]

    with open(a.out, "w") as f:
        json.dump(payload, f, indent=2)

    counts = {k: len(v) for k, v in payload["lists"].items()}
    total = sum(counts.values())
    print(json.dumps({"out": a.out, "total_kw": total, "counts": counts,
                      "current_main": cm}))


if __name__ == "__main__":
    main()
