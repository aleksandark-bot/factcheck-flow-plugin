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

Auth, resolved in this order (nothing secret lives in this repo):
  1. $DATAFORSEO_AUTH                     base64 of "login:password"
  2. $DATAFORSEO_LOGIN + $DATAFORSEO_PASSWORD
  3. ~/.claude/factcheck-flow/dataforseo-key.json   {"login":..,"password":..} or {"auth":".."}
  4. the `dataforseo` MCP server entry in ~/.claude.json (its Authorization header)

Output: the Gate #1 payload on --out, in exactly the shape serp_picker.py --in expects:

  {"main_keyword": "...",
   "serp": [{"rank": 1, "title": "...", "url": "...", "domain": "...",
             "description": "...", "own_domain": false}, ...]}

plus a one-line summary on stdout: {"out","kept","dropped_own","keyword"}.

Organic results only. Paid, People-also-ask, video carousels and other SERP features are
dropped here rather than in the model's head. Results on an --exclude-domain are kept in
the file but flagged `own_domain: true`, so Stage 1 can see where we currently rank
without mining ourselves for competitor keywords.

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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keyword", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--location", default="United States")
    ap.add_argument("--language", default="en")
    ap.add_argument("--depth", type=int, default=10)
    ap.add_argument("--exclude-domain", action="append", default=[],
                    help="repeatable; matching results are flagged own_domain, not removed")
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
        })
        if rank >= a.depth:
            break

    payload = {"main_keyword": a.keyword, "serp": serp}
    with open(a.out, "w") as f:
        json.dump(payload, f, indent=2)

    print(json.dumps({"out": a.out, "kept": len(serp),
                      "dropped_own": dropped_own, "keyword": a.keyword}))


if __name__ == "__main__":
    main()
