#!/usr/bin/env python3
"""Ask Search Console which page on the site actually OWNS a keyword.

The /SEO pre-flight guard. Optimizing an article for a keyword another page on the same
site already owns does not win the keyword — it splits it, and a split keyword halves both
pages' chances instead of merely diluting them. So before /SEO commits a keyword to an
article, this script checks who holds it today.

It is deliberately narrow: a few named keywords for ONE article, not a corpus-wide
cannibalization sweep (that belongs to the bulk interlinking project). It reads GSC and
writes nothing.

Usage:
  gsc_cannibal.py --page <URL> --keyword "kw" [--keyword "kw2" ...] \\
                  [--head-term "clinic software"] [--days 28] [--out FILE]

  --page       the article /SEO is about to optimize (the candidate owner)
  --keyword    repeatable, up to 12. The main keyword and any new-main candidate first.
  --head-term  optional; runs one extra "query containing <term>" pass to show how the
               whole term FAMILY is distributed across the site, which is the check that
               catches cannibalization the exact-match pass misses.
  --days       trailing window (default 28 — short on purpose, so normal position
               testing doesn't read as a settled ownership fight)
  --out        write the JSON here as well as printing the summary line

Config (same resolution as gsc_query.py):
  service-account key : $PABAU_GSC_KEY        else ~/.claude/factcheck-flow/gsc-key.json
  GSC property        : $PABAU_GSC_PROPERTY    else https://pabau.com/

Verdicts, per keyword:
  unclaimed        no page on the site gets impressions for it — free to target
  ours             our page holds the large majority; `ours-clear` at >=90%
  owned-elsewhere  another single page holds the large majority — targeting it here
                   creates the split. Retarget, or decide deliberately to move the
                   keyword to this page and strip it from the other one.
  split            no page holds a majority and two or more compete — already
                   cannibalized. Pick the primary before adding a third contender.

Share is measured on clicks when the keyword has any real clicks (>=5 across the site),
on impressions otherwise, because a keyword with two clicks total has no click signal.

Exit codes: 0 ok; 2 on a setup/auth/API error. A non-zero exit means "no cannibalization
data", not "no cannibalization" — treat it as unknown, never as a pass.
"""
import os, sys, json, time, argparse, datetime
import urllib.request, urllib.parse, urllib.error

MAX_KEYWORDS = 12
MAJORITY = 0.70          # a page holding this share owns the keyword
CLEAR = 0.90             # ...and at this share there is nothing to fix
PRESENT = 0.20           # below this share a page isn't really a contender
CLICK_SIGNAL_MIN = 5     # fewer clicks than this site-wide -> judge on impressions


def die(msg):
    sys.stderr.write("GSC ERROR: " + msg + "\n")
    sys.exit(2)


try:
    import jwt  # PyJWT
except ImportError:
    die("PyJWT is not installed. Run: python3 -m pip install --user pyjwt")

KEY = os.environ.get("PABAU_GSC_KEY") or os.path.expanduser("~/.claude/factcheck-flow/gsc-key.json")
if not os.path.exists(KEY):
    die("service-account key not found at %s "
        "(place the JSON there or set $PABAU_GSC_KEY)." % KEY)

PROPERTY = os.environ.get("PABAU_GSC_PROPERTY", "https://pabau.com/")
SCOPE = "https://www.googleapis.com/auth/webmasters.readonly"

try:
    _sa = json.load(open(KEY))
except Exception as e:
    die("could not read service-account key %s: %s" % (KEY, e))

_tok = {}


def get_token():
    if "t" in _tok:
        return _tok["t"]
    now = int(time.time())
    assertion = jwt.encode({
        "iss": _sa["client_email"], "scope": SCOPE, "aud": _sa["token_uri"],
        "iat": now, "exp": now + 3600,
    }, _sa["private_key"], algorithm="RS256")
    data = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
    }).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(_sa["token_uri"], data=data), timeout=60) as r:
            _tok["t"] = json.load(r)["access_token"]
            return _tok["t"]
    except urllib.error.HTTPError as e:
        die("token request failed (HTTP %s): %s" % (e.code, e.read().decode("utf-8", "ignore")[:300]))


def pages_for(query, operator, start, end):
    """Every page on the property getting impressions for this query / query family."""
    site = ("https://www.googleapis.com/webmasters/v3/sites/"
            + urllib.parse.quote(PROPERTY, safe="") + "/searchAnalytics/query")
    body = {
        "startDate": start, "endDate": end,
        "dimensions": ["page"],
        "dimensionFilterGroups": [{"filters": [
            {"dimension": "query", "operator": operator, "expression": query}]}],
        "rowLimit": 50, "dataState": "final",
    }
    req = urllib.request.Request(site, data=json.dumps(body).encode(), method="POST")
    req.add_header("Authorization", "Bearer " + get_token())
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        die("Search Analytics API HTTP %s: %s" % (e.code, e.read().decode("utf-8", "ignore")[:300]))
    rows = []
    for row in resp.get("rows", []):
        url = row["keys"][0]
        rows.append({
            "page": url,
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "position": round(row.get("position", 0), 1),
            "lp": "/lp/" in url,
        })
    rows.sort(key=lambda r: (-r["impressions"], -r["clicks"]))
    return rows


def same_page(a, b):
    return a.rstrip("/").lower() == b.rstrip("/").lower()


def judge(rows, our_page, force_metric=None):
    """Who owns it, on what share, and who else is in the fight."""
    if not rows:
        return {"verdict": "unclaimed", "pages": 0, "metric": None,
                "our": None, "our_share": None, "leader": None, "competing": []}

    total_clicks = sum(r["clicks"] for r in rows)
    metric = force_metric or ("clicks" if total_clicks >= CLICK_SIGNAL_MIN else "impressions")
    total = float(sum(r[metric] for r in rows)) or 1.0

    for r in rows:
        r["share"] = round(r[metric] / total, 3)

    ours = next((r for r in rows if same_page(r["page"], our_page)), None)
    leader = max(rows, key=lambda r: r[metric])
    our_share = ours["share"] if ours else 0.0

    if ours and leader is ours and our_share >= CLEAR:
        verdict = "ours-clear"
    elif ours and leader is ours and our_share >= MAJORITY:
        verdict = "ours"
    elif leader["share"] >= MAJORITY and not (ours and leader is ours):
        verdict = "owned-elsewhere"
    elif len([r for r in rows if r["share"] >= PRESENT]) >= 2:
        verdict = "split"
    elif ours:
        verdict = "ours"
    else:
        verdict = "owned-elsewhere"

    return {
        "verdict": verdict,
        "pages": len(rows),
        "metric": metric,
        "our": {k: ours[k] for k in ("clicks", "impressions", "position", "share")} if ours else None,
        "our_share": our_share,
        "leader": {k: leader[k] for k in ("page", "clicks", "impressions", "position", "share", "lp")},
        "competing": [{k: r[k] for k in ("page", "clicks", "impressions", "position", "share", "lp")}
                      for r in rows
                      if not same_page(r["page"], our_page) and r["share"] >= PRESENT][:5],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", required=True)
    ap.add_argument("--keyword", action="append", default=[])
    ap.add_argument("--head-term", default="")
    ap.add_argument("--days", type=int, default=28)
    ap.add_argument("--end", default=None)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    kws = [k.strip() for k in a.keyword if k.strip()]
    if not kws and not a.head_term:
        die("give at least one --keyword or a --head-term")
    dropped = 0
    if len(kws) > MAX_KEYWORDS:
        dropped = len(kws) - MAX_KEYWORDS
        kws = kws[:MAX_KEYWORDS]

    end = a.end or datetime.date.today().isoformat()
    start = (datetime.date.fromisoformat(end) - datetime.timedelta(days=a.days)).isoformat()

    results = []
    for kw in kws:
        v = judge(pages_for(kw.lower(), "equals", start, end), a.page)
        v["keyword"] = kw
        results.append(v)

    family = None
    if a.head_term:
        rows = pages_for(a.head_term.lower(), "contains", start, end)
        # The family pass is about where the term family's ATTENTION goes, and a broad
        # "contains" match pulls in pages with real impressions and no clicks at all.
        # Judging it on clicks would score those pages at zero and hide the split.
        family = judge(rows, a.page, force_metric="impressions")
        family["head_term"] = a.head_term
        family["all_pages"] = rows[:10]

    payload = {
        "page": a.page, "start": start, "end": end, "days": a.days,
        "keywords": results, "family": family,
        "dropped_keywords": dropped,
    }
    if a.out:
        with open(a.out, "w") as f:
            json.dump(payload, f, indent=2)

    counts = {}
    for r in results:
        counts[r["verdict"]] = counts.get(r["verdict"], 0) + 1
    print(json.dumps({
        "out": a.out, "checked": len(results), "verdicts": counts,
        "family": (family or {}).get("verdict"),
        "blockers": [r["keyword"] for r in results
                     if r["verdict"] in ("owned-elsewhere", "split")],
        "dropped_keywords": dropped,
    }))


if __name__ == "__main__":
    main()
