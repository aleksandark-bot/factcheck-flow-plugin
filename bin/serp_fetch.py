#!/usr/bin/env python3
"""Fetch the Stage-1 SERP for /SEO and emit only the rows the flow actually uses.

`serp_organic_live_advanced` returns deeply nested JSON — SERP features, rich-snippet
sub-objects, rating blocks, per-result metadata — and Stage 1 keeps exactly four fields
per organic result. Loaded into the conversation the raw response sits in context for
the whole run; this script keeps it out entirely, the same trade dfs_lists.py makes for
Stage 2.

Usage:
  serp_fetch.py --keyword "<main keyword>" --out /tmp/seo-<slug>-serp.json \\
                [--location "United States"] [--language en] [--depth 10] \\
                [--exclude-domain pabau.com]        # repeatable
                [--no-extras]                       # skip the answer_surface summary

Auth, resolved in this order (nothing secret lives in this repo):
  1. $DATAFORSEO_AUTH                     base64 of "login:password"
  2. $DATAFORSEO_LOGIN + $DATAFORSEO_PASSWORD
  3. ~/.claude/factcheck-flow/dataforseo-key.json   {"login":..,"password":..} or {"auth":".."}
  4. the `dataforseo` MCP server entry in ~/.claude.json (its Authorization header)

Output: the Gate #1 payload on --out, in exactly the shape serp_picker.py --in expects:

  {"main_keyword": "...",
   "serp": [{"rank": 1, "title": "...", "url": "...", "domain": "...",
             "description": "...", "own_domain": false, "kw_in_title": false}, ...],
   "answer_surface": {
     "featured_snippet": {"domain","url","title","format"} | null,
     "ai_overview": {"present": bool, "cited_domains": [...], "we_are_cited": bool},
     "paa": ["question", ...],
     "related_searches": ["query", ...],
     "features": {"<serp item type>": count, ...},
     "our_position": <int|null>,
     "title_gap": {"exact_in_title": n, "of": m, "verdict": "wide-open|contested|claimed"}
   }}

plus a one-line summary on stdout:
{"out","kept","dropped_own","keyword","snippet","aio","paa","title_gap"}.

The `serp` array is organic results only — paid results are dropped. But the rest of the
SERP is where the click now goes, so it is SUMMARIZED into `answer_surface` instead of
being thrown away:

  * featured_snippet — who holds it and in what FORMAT, because winning it means matching
    that format (paragraph / list / table), not just writing a better page.
  * ai_overview — whether an AI Overview sits above the organic results and which domains
    it cites. An AIO explains a weak CTR at a strong position, and its cited domains are
    the rank-stack to join.
  * paa + related_searches — the SERP's own visible query fan-out. These are the sub-questions
    the page has to answer to be the complete answer, and the best FAQ candidates.
  * features — every other block present (video, discussions_and_forums, images, local_pack…),
    counted. What the SERP rewards is a format decision, and this is the evidence for it.
  * title_gap — how many of the ranking pages actually put the exact keyword in their TITLE.
    A keyword nobody has claimed in their title is far cheaper to win than its difficulty
    score implies; one every page has claimed is a fight. `wide-open` = 0 titles carry it,
    `contested` = 1-2, `claimed` = 3+.

Results on an --exclude-domain are kept in the file but flagged `own_domain: true`, so
Stage 1 can see where we currently rank without mining ourselves for competitor keywords;
`our_position` reports that rank directly.

What this script deliberately does NOT do: judge which results are worth mining, or read
searcher intent. Those are the two Stage-1 judgments that need a model.

Exit codes: 0 ok; 2 on a setup/auth/API error, with a clear message on stderr.
"""
import os, sys, json, base64, argparse
import urllib.request, urllib.error

API = "https://api.dataforseo.com"
PATH = "/v3/serp/google/organic/live/advanced"


def die(msg):
    sys.stderr.write("SERP ERROR: " + msg + "\n")
    sys.exit(2)


# ---------------------------------------------------------------- auth
# Kept byte-compatible with dfs_lists.py: one credential setup serves both scripts.

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


def post(auth, task):
    req = urllib.request.Request(API + PATH, data=json.dumps([task]).encode(), method="POST")
    req.add_header("Authorization", "Basic " + auth)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=180) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        die("HTTP %s: %s" % (e.code, e.read().decode("utf-8", "ignore")[:300]))
    except Exception as e:
        die("request failed: %s" % e)
    if resp.get("status_code") not in (20000, None):
        die(str(resp.get("status_message")))
    tasks = resp.get("tasks") or []
    if not tasks:
        die("no tasks in response")
    t = tasks[0]
    if t.get("status_code") not in (20000, None):
        die(str(t.get("status_message")))
    res = t.get("result") or []
    return res[0] if res else {}


def host_of(url):
    u = (url or "").split("://", 1)[-1]
    return u.split("/", 1)[0].lower().lstrip("www.")


# ---------------------------------------------------------------- answer surface
# Everything on the SERP that is not an organic result. Summarized here so the model
# never has to hold the raw nested response to see what the SERP actually rewards.

def _words(txt):
    return [w for w in "".join(c.lower() if (c.isalnum() or c.isspace()) else " "
                              for c in (txt or "")).split() if w]


def kw_in_text(keyword, text):
    """Is the keyword present in `text` as a phrase, ignoring case and punctuation?"""
    kw = " ".join(_words(keyword))
    return bool(kw) and kw in " ".join(_words(text))


def snippet_format(item):
    """paragraph / list / table — the shape a featured snippet has to be written in."""
    if item.get("table"):
        return "table"
    desc = item.get("description") or ""
    lines = [ln.strip(" \u2022-\u2013\u2014*\t") for ln in desc.splitlines() if ln.strip()]
    if len(lines) >= 3 and sum(len(ln) < 120 for ln in lines) >= 3:
        return "list"
    return "paragraph"


def collect_domains(node, out):
    """Pull every referenced domain out of an ai_overview item, whatever its shape."""
    if isinstance(node, dict):
        for key in ("domain", "source_domain"):
            v = node.get(key)
            if isinstance(v, str) and v:
                out.add(v.lower().lstrip("www."))
        if not node.get("domain") and isinstance(node.get("url"), str):
            out.add(host_of(node["url"]))
        for v in node.values():
            collect_domains(v, out)
    elif isinstance(node, list):
        for v in node:
            collect_domains(v, out)


def answer_surface(items, keyword, own, serp):
    """Summarize the non-organic SERP + the title-gap test over the organic titles."""
    features, paa, related = {}, [], []
    snippet, aio_domains, aio_present = None, set(), False

    for it in items:
        if not isinstance(it, dict):
            continue
        t = it.get("type") or "unknown"
        features[t] = features.get(t, 0) + 1

        if t == "featured_snippet" and snippet is None:
            snippet = {
                "domain": (it.get("domain") or host_of(it.get("url"))) or "",
                "url": it.get("url") or "",
                "title": (it.get("title") or "").strip()[:200],
                "format": snippet_format(it),
            }
        elif t == "people_also_ask":
            for q in (it.get("items") or []):
                title = (q or {}).get("title") if isinstance(q, dict) else None
                if title and title not in paa:
                    paa.append(title.strip())
        elif t == "related_searches":
            for q in (it.get("items") or []):
                q = q if isinstance(q, str) else (q or {}).get("title")
                if q and q not in related:
                    related.append(q.strip())
        elif t == "ai_overview":
            aio_present = True
            collect_domains(it, aio_domains)

    # title gap: how many ranking pages claimed the exact phrase in their title
    in_title = sum(1 for r in serp if r["kw_in_title"])
    verdict = "wide-open" if in_title == 0 else ("contested" if in_title <= 2 else "claimed")

    ours = next((r["rank"] for r in serp if r["own_domain"]), None)
    return {
        "featured_snippet": snippet,
        "ai_overview": {
            "present": aio_present,
            "cited_domains": sorted(aio_domains)[:20],
            "we_are_cited": any(d in aio_domains for d in own) if own else False,
        },
        "paa": paa[:12],
        "related_searches": related[:12],
        "features": features,
        "our_position": ours,
        "title_gap": {"exact_in_title": in_title, "of": len(serp), "verdict": verdict},
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--location", default="United States")
    ap.add_argument("--language", default="en")
    ap.add_argument("--depth", type=int, default=10)
    ap.add_argument("--exclude-domain", action="append", default=[],
                    help="repeatable; matching results are flagged own_domain, not removed")
    ap.add_argument("--no-extras", action="store_true",
                    help="omit the answer_surface summary (organic rows only)")
    a = ap.parse_args()

    auth = resolve_auth()
    result = post(auth, {
        "keyword": a.keyword,
        "location_name": a.location,
        "language_code": a.language,
        "depth": a.depth,
        "device": "desktop",
    })

    own = set()
    for d in a.exclude_domain:
        own.add(d.lower().lstrip("www."))

    serp, rank, dropped_own = [], 0, 0
    for item in (result.get("items") or []):
        if not isinstance(item, dict) or item.get("type") != "organic":
            continue
        url = item.get("url")
        if not url:
            continue
        rank += 1
        h = host_of(url)
        is_own = any(h == o or h.endswith("." + o) for o in own)
        if is_own:
            dropped_own += 1
        serp.append({
            "rank": rank,
            "title": (item.get("title") or "").strip(),
            "url": url,
            "domain": h,
            "description": (item.get("description") or "").strip()[:200],
            "own_domain": is_own,
            "kw_in_title": kw_in_text(a.keyword, item.get("title") or ""),
        })
        if rank >= a.depth:
            break

    payload = {"main_keyword": a.keyword, "serp": serp}
    summary = {"out": a.out, "kept": len(serp),
               "dropped_own": dropped_own, "keyword": a.keyword}

    if not a.no_extras:
        surf = answer_surface(result.get("items") or [], a.keyword, own, serp)
        payload["answer_surface"] = surf
        fs = surf["featured_snippet"]
        summary["snippet"] = ("%s (%s)" % (fs["domain"], fs["format"])) if fs else None
        summary["aio"] = surf["ai_overview"]["present"]
        summary["paa"] = len(surf["paa"])
        summary["title_gap"] = surf["title_gap"]["verdict"]
        summary["our_position"] = surf["our_position"]

    with open(a.out, "w") as f:
        json.dump(payload, f, indent=2)

    print(json.dumps(summary))


if __name__ == "__main__":
    main()
