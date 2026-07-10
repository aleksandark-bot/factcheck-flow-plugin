#!/usr/bin/env python3
"""Fetch the top Google Search Console queries (by clicks) for ONE page.

Used by the /SEO command's "already ranking" list (published articles only).

Usage:
  gsc_query.py --page <URL> [--days 90] [--limit 20] [--end YYYY-MM-DD]

Config (resolved from the environment, with safe defaults):
  service-account key : $PABAU_GSC_KEY        else ~/.claude/factcheck-flow/gsc-key.json
  GSC property        : $PABAU_GSC_PROPERTY    else https://pabau.com/

Output: JSON on stdout —
  {"page":..., "start":..., "end":..., "queries":[{"query","clicks","impressions","position"}, ...]}
Sorted by clicks desc (the API's default order).

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

try:
    _sa = json.load(open(KEY))
except Exception as e:
    die("could not read service-account key %s: %s" % (KEY, e))


def get_token():
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
            return json.load(r)["access_token"]
    except urllib.error.HTTPError as e:
        die("token request failed (HTTP %s): %s" % (e.code, e.read().decode("utf-8", "ignore")[:300]))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", required=True, help="full article URL")
    ap.add_argument("--days", type=int, default=90)
    ap.add_argument("--limit", type=int, default=20)
    ap.add_argument("--end", default=None, help="end date YYYY-MM-DD (default: today)")
    a = ap.parse_args()

    end = a.end or datetime.date.today().isoformat()
    start = (datetime.date.fromisoformat(end) - datetime.timedelta(days=a.days)).isoformat()

    site = ("https://www.googleapis.com/webmasters/v3/sites/"
            + urllib.parse.quote(PROPERTY, safe="") + "/searchAnalytics/query")
    body = {
        "startDate": start, "endDate": end,
        "dimensions": ["query"],
        "dimensionFilterGroups": [{"filters": [
            {"dimension": "page", "operator": "equals", "expression": a.page}]}],
        "rowLimit": a.limit, "dataState": "final",
    }
    req = urllib.request.Request(site, data=json.dumps(body).encode(), method="POST")
    req.add_header("Authorization", "Bearer " + get_token())
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        die("Search Analytics API HTTP %s: %s" % (e.code, e.read().decode("utf-8", "ignore")[:300]))

    queries = [{
        "query": row["keys"][0],
        "clicks": row.get("clicks", 0),
        "impressions": row.get("impressions", 0),
        "position": round(row.get("position", 0), 1),
    } for row in resp.get("rows", [])]

    json.dump({"page": a.page, "start": start, "end": end, "queries": queries},
              sys.stdout, indent=2)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
