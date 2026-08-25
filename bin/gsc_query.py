#!/usr/bin/env python3
"""Fetch Google Search Console query data for ONE page, across several time windows.

Used by the /SEO command's "already ranking" list (published articles only) and by its
refresh diagnosis. The point of the multi-window pull is that a single 90-day average
hides the two things that decide what to do with a page:

  * TREND — a 90-day average cannot tell a page that is growing from one that is dying.
    The recent window's daily rate against the long window's daily rate can. Refreshing a
    declining page beats writing a new one, so the flow needs to know which it has.
  * BEST POSITION — a 90-day average position is dragged down by every day the page was
    being tested. The best average position across the windows is the honest read on what
    the page can reach, and it is what decides whether a query is in striking distance.

Usage:
  gsc_query.py --page <URL> [--windows 28,90] [--limit 25] [--end YYYY-MM-DD]
  gsc_query.py --page <URL> --days 90 --limit 20        # legacy form, still supported

Config (resolved from the environment, with safe defaults):
  service-account key : $PABAU_GSC_KEY        else ~/.claude/factcheck-flow/gsc-key.json
  GSC property        : $PABAU_GSC_PROPERTY    else https://pabau.com/

Output: JSON on stdout —
  {"page","end","windows":[28,90],"primary":90,
   "queries":[{"query","clicks","impressions","position","ctr",   <- primary window
               "by_window":{"28":{...},"90":{...}},
               "best_position", "band", "trend", "ctr_gap"}, ...],
   "page_totals":{"28":{...},"90":{...}},
   "verdict":"growing|flat|declining|no-data",
   "query_spread":{"total_queries","one_off_share","top5_click_share"},
   "title_mismatch_signal": bool,
   "striking_distance":["query", ...],
   "start","days"}                              <- start/days mirror the primary window

The legacy keys (`queries[].query/clicks/impressions/position`, `start`, `end`) are
unchanged and hold the PRIMARY (longest) window, so anything already reading this file
keeps working.

`band`  top3 (<=3) · page1 (<=10) · striking (<=20) · longtail (>20), from best_position.
`trend` compares the shortest window's daily click rate against the longest window's.
        The short window is a subset of the long one, so this reads "recent rate vs the
        whole-period average" — directional, not a strict period-over-period delta.
`ctr_gap` flags a query whose CTR falls far below the rough curve for its position, on
        enough impressions to mean something. That points at the TITLE, not the content —
        but an AI Overview on the SERP suppresses CTR on its own, so check `serp_fetch.py`'s
        answer_surface before blaming the title.
`title_mismatch_signal` fires when a page collects many one-off queries and no query
        bucket holds a real share of its clicks — the signature of a title/slug that
        doesn't match any coherent query Google could rank it for.

Exit codes: 0 ok; 2 on a setup/auth/API error, with a clear message on stderr. The /SEO
published path treats a non-zero exit as "GSC not set up" and stops rather than continuing
without the list.
"""
import os, sys, json, time, argparse, datetime
import urllib.request, urllib.parse, urllib.error


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

# A rough organic CTR-by-position curve. Deliberately coarse: it exists only to catch a
# SEVERE shortfall (actual CTR under half the expected band) on enough impressions to be
# real. Never treat a near-band number as a finding.
CTR_CURVE = {1: 0.28, 2: 0.15, 3: 0.11, 4: 0.08, 5: 0.06,
             6: 0.05, 7: 0.04, 8: 0.032, 9: 0.028, 10: 0.025}
CTR_CURVE_TAIL = 0.012          # positions 11-20
CTR_MIN_IMPRESSIONS = 100       # below this, CTR is noise

try:
    _sa = json.load(open(KEY))
except Exception as e:
    die("could not read service-account key %s: %s" % (KEY, e))

_token_cache = {}


def get_token():
    if "t" in _token_cache:
        return _token_cache["t"]
    now = int(time.time())
    payload = {
        "iss": _sa["client_email"], "scope": SCOPE, "aud": _sa["token_uri"],
        "iat": now, "exp": now + 3600,
    }
    assertion = jwt.encode(payload, _sa["private_key"], algorithm="RS256")
    data = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion,
    }).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(_sa["token_uri"], data=data), timeout=60) as r:
            _token_cache["t"] = json.load(r)["access_token"]
            return _token_cache["t"]
    except urllib.error.HTTPError as e:
        die("token request failed (HTTP %s): %s" % (e.code, e.read().decode("utf-8", "ignore")[:300]))


def query_api(body):
    site = ("https://www.googleapis.com/webmasters/v3/sites/"
            + urllib.parse.quote(PROPERTY, safe="") + "/searchAnalytics/query")
    req = urllib.request.Request(site, data=json.dumps(body).encode(), method="POST")
    req.add_header("Authorization", "Bearer " + get_token())
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        die("Search Analytics API HTTP %s: %s" % (e.code, e.read().decode("utf-8", "ignore")[:300]))


def page_filter(page):
    return [{"filters": [{"dimension": "page", "operator": "equals", "expression": page}]}]


def fetch_window(page, start, end, limit):
    """Query rows for one window, keyed by query string."""
    resp = query_api({
        "startDate": start, "endDate": end,
        "dimensions": ["query"],
        "dimensionFilterGroups": page_filter(page),
        "rowLimit": limit, "dataState": "final",
    })
    out = {}
    for row in resp.get("rows", []):
        out[row["keys"][0]] = {
            "clicks": row.get("clicks", 0),
            "impressions": row.get("impressions", 0),
            "position": round(row.get("position", 0), 1),
            "ctr": round(row.get("ctr", 0), 4),
        }
    return out


def band_of(pos):
    if pos is None:
        return "unranked"
    if pos <= 3:
        return "top3"
    if pos <= 10:
        return "page1"
    if pos <= 20:
        return "striking"
    return "longtail"


def trend_of(short, long_, short_days, long_days):
    """Recent daily rate vs the whole-period daily rate. Clicks first, impressions as
    the fallback when the page gets impressions but no clicks."""
    if not long_ and not short:
        return "none"
    if not long_:
        return "new"

    def rate(row, days, field):
        return (row.get(field, 0) / float(days)) if row else 0.0

    for field in ("clicks", "impressions"):
        if (long_ or {}).get(field, 0) <= 0:
            continue
        s, l = rate(short, short_days, field), rate(long_, long_days, field)
        if l <= 0:
            return "new"
        ratio = s / l
        if ratio >= 1.2:
            return "rising"
        if ratio <= 0.8:
            return "declining"
        return "flat"
    return "none"


def ctr_gap_of(row):
    """severe / mild / none / n-a — only meaningful with enough impressions."""
    if not row or row.get("impressions", 0) < CTR_MIN_IMPRESSIONS:
        return "n/a"
    pos = row.get("position") or 999
    if pos > 20:
        return "n/a"
    expected = CTR_CURVE.get(int(round(pos)), CTR_CURVE_TAIL)
    actual = row.get("ctr", 0)
    if actual < expected * 0.5:
        return "severe"
    if actual < expected * 0.75:
        return "mild"
    return "none"


def spread_of(page, start, end):
    """The title-mismatch signal: a wide scatter of one-off queries with no query bucket
    holding a real share of the clicks means the title/slug matches nothing coherent."""
    resp = query_api({
        "startDate": start, "endDate": end,
        "dimensions": ["query"],
        "dimensionFilterGroups": page_filter(page),
        "rowLimit": 1000, "dataState": "final",
    })
    rows = resp.get("rows", [])
    total = len(rows)
    if not total:
        return {"total_queries": 0, "one_off_share": None, "top5_click_share": None}, False
    one_off = sum(1 for r in rows if r.get("impressions", 0) <= 2)
    clicks = sorted((r.get("clicks", 0) for r in rows), reverse=True)
    all_clicks = sum(clicks)
    top5 = (sum(clicks[:5]) / all_clicks) if all_clicks else None
    spread = {
        "total_queries": total,
        "one_off_share": round(one_off / float(total), 3),
        "top5_click_share": round(top5, 3) if top5 is not None else None,
    }
    signal = bool(total >= 25 and spread["one_off_share"] >= 0.6
                  and (top5 is None or top5 < 0.5))
    return spread, signal


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", required=True, help="full article URL")
    ap.add_argument("--windows", default=None,
                    help="comma-separated trailing day counts, e.g. 28,90 (default 28,90)")
    ap.add_argument("--days", type=int, default=None,
                    help="legacy single-window form; equivalent to --windows <days>")
    ap.add_argument("--limit", type=int, default=25)
    ap.add_argument("--end", default=None, help="end date YYYY-MM-DD (default: today)")
    ap.add_argument("--no-spread", action="store_true",
                    help="skip the extra full-query-list call used for the title-mismatch signal")
    a = ap.parse_args()

    if a.windows:
        windows = sorted({int(w) for w in a.windows.split(",") if w.strip()})
    elif a.days:
        windows = [a.days]
    else:
        windows = [28, 90]
    if not windows:
        die("no windows given")

    end = a.end or datetime.date.today().isoformat()
    end_d = datetime.date.fromisoformat(end)

    per_window, page_totals = {}, {}
    for w in windows:
        start = (end_d - datetime.timedelta(days=w)).isoformat()
        rows = fetch_window(a.page, start, end, max(a.limit, 100))
        per_window[w] = rows
        page_totals[str(w)] = {
            "start": start,
            "clicks": sum(r["clicks"] for r in rows.values()),
            "impressions": sum(r["impressions"] for r in rows.values()),
            "queries": len(rows),
        }

    primary, shortest = windows[-1], windows[0]
    prim_rows = per_window[primary]
    prim_start = page_totals[str(primary)]["start"]

    # rank the primary window's queries by clicks, then impressions — the old behaviour
    ordered = sorted(prim_rows.items(),
                     key=lambda kv: (-kv[1]["clicks"], -kv[1]["impressions"]))[:a.limit]

    queries = []
    for kw, row in ordered:
        by_window = {str(w): per_window[w].get(kw) for w in windows}
        positions = [v["position"] for v in by_window.values() if v and v.get("position")]
        best = min(positions) if positions else None
        queries.append({
            "query": kw,
            "clicks": row["clicks"],
            "impressions": row["impressions"],
            "position": row["position"],
            "ctr": row["ctr"],
            "by_window": by_window,
            "best_position": best,
            "band": band_of(best),
            "trend": trend_of(by_window.get(str(shortest)), by_window.get(str(primary)),
                              shortest, primary) if len(windows) > 1 else "n/a",
            "ctr_gap": ctr_gap_of(row),
        })

    # page-level verdict from the same rate comparison, on page totals
    if len(windows) > 1:
        verdict = trend_of(
            {"clicks": page_totals[str(shortest)]["clicks"],
             "impressions": page_totals[str(shortest)]["impressions"]},
            {"clicks": page_totals[str(primary)]["clicks"],
             "impressions": page_totals[str(primary)]["impressions"]},
            shortest, primary)
        verdict = {"rising": "growing", "none": "no-data"}.get(verdict, verdict)
    else:
        verdict = "n/a"

    spread, mismatch = ({"total_queries": None}, False)
    if not a.no_spread:
        spread, mismatch = spread_of(a.page, prim_start, end)

    striking = [q["query"] for q in queries
                if q["band"] in ("striking", "page1") and (q["best_position"] or 99) > 3]

    json.dump({
        "page": a.page,
        "start": prim_start, "end": end, "days": primary,
        "windows": windows, "primary": primary,
        "queries": queries,
        "page_totals": page_totals,
        "verdict": verdict,
        "query_spread": spread,
        "title_mismatch_signal": mismatch,
        "striking_distance": striking,
    }, sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
