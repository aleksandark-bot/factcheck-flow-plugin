#!/usr/bin/env python3
"""Tell Google one already-published URL has changed, so it re-crawls sooner.

A refresh that Google hasn't re-crawled is a refresh that hasn't happened yet. Sitemaps
are a crawl-PRIORITY signal, not a control list, and they never force anything — the
Indexing API's `URL_UPDATED` notification is the direct request. It is the last step of a
/SEO run on a PUBLISHED article.

Scope, deliberately narrow:
  * Published URLs only. Never a draft — a draft has no public URL to crawl.
  * One URL per call. This is not a bulk submitter.
  * The URL must already return 200 on the live site, and must sit on the configured
    property host. Submitting a 404 or someone else's URL is never useful.
  * It requests a re-crawl of a page WE just edited. It publishes nothing, changes nothing
    on the site, and cannot make a private page public.

Usage:
  index_ping.py --url https://pabau.com/blog/... [--dry-run] [--no-status-check]

Key (this is NOT the GSC read key):
  $PABAU_INDEXING_KEY  else ~/.claude/factcheck-flow/indexing-key.json

  The service account behind it needs to be an OWNER of the Search Console property, and
  the project needs the Web Search Indexing API enabled. A read-only GSC service account
  returns `403 PERMISSION_DENIED — Failed to verify the URL ownership`, so pointing this
  at the GSC key will simply fail. Daily quota is ~200 notifications.

Exit codes:
  0  submitted (or --dry-run passed every check)
  3  SKIPPED for a benign reason — no key installed, or the URL isn't reachable/on-property.
     The /SEO flow reports this and moves on; it is not a failure.
  2  a real error (auth, API, malformed key).
"""
import os, sys, json, time, argparse
import urllib.request, urllib.parse, urllib.error

ENDPOINT = "https://indexing.googleapis.com/v3/urlNotifications:publish"
SCOPE = "https://www.googleapis.com/auth/indexing"
PROPERTY = os.environ.get("PABAU_GSC_PROPERTY", "https://pabau.com/")


def out(status, **kw):
    kw["status"] = status
    print(json.dumps(kw))


def skip(reason, **kw):
    out("skipped", reason=reason, **kw)
    sys.exit(3)


def die(msg):
    sys.stderr.write("INDEX PING ERROR: " + msg + "\n")
    sys.exit(2)


def host_of(url):
    return urllib.parse.urlparse(url).netloc.lower().lstrip("www.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-status-check", action="store_true",
                    help="skip the live 200 check (only for a URL you already verified)")
    a = ap.parse_args()

    if not a.url.startswith("https://"):
        skip("not an https URL", url=a.url)
    if host_of(a.url) != host_of(PROPERTY):
        skip("URL is not on the configured property (%s)" % PROPERTY, url=a.url)

    key = (os.environ.get("PABAU_INDEXING_KEY")
           or os.path.expanduser("~/.claude/factcheck-flow/indexing-key.json"))
    if not os.path.exists(key):
        skip("no indexing key at %s — install it or set $PABAU_INDEXING_KEY" % key, url=a.url)

    try:
        sa = json.load(open(key))
        sa["client_email"], sa["private_key"], sa["token_uri"]
    except Exception as e:
        die("could not read the indexing key %s: %s" % (key, e))

    if not a.no_status_check:
        req = urllib.request.Request(a.url, method="HEAD")
        req.add_header("User-Agent", "Mozilla/5.0 (compatible; factcheck-flow/index_ping)")
        try:
            with urllib.request.urlopen(req, timeout=45) as r:
                code = r.status
        except urllib.error.HTTPError as e:
            code = e.code
        except Exception as e:
            skip("could not reach the URL: %s" % e, url=a.url)
        if code != 200:
            skip("live URL returned HTTP %s — nothing to re-crawl" % code, url=a.url)

    try:
        import jwt  # PyJWT
    except ImportError:
        skip("PyJWT is not installed (python3 -m pip install --user pyjwt)", url=a.url)

    if a.dry_run:
        out("dry-run", url=a.url, key=key)
        return

    now = int(time.time())
    assertion = jwt.encode({"iss": sa["client_email"], "scope": SCOPE,
                            "aud": sa["token_uri"], "iat": now, "exp": now + 3600},
                           sa["private_key"], algorithm="RS256")
    data = urllib.parse.urlencode({
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": assertion}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(sa["token_uri"], data=data), timeout=60) as r:
            token = json.load(r)["access_token"]
    except urllib.error.HTTPError as e:
        die("token request failed (HTTP %s): %s" % (e.code, e.read().decode("utf-8", "ignore")[:300]))

    body = json.dumps({"url": a.url, "type": "URL_UPDATED"}).encode()
    req = urllib.request.Request(ENDPOINT, data=body, method="POST")
    req.add_header("Authorization", "Bearer " + token)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            resp = json.load(r)
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "ignore")[:300]
        if e.code == 429:
            skip("daily indexing quota exhausted (HTTP 429)", url=a.url)
        if e.code == 403:
            skip("403 from the Indexing API — the service account is not an OWNER of %s "
                 "(%s)" % (PROPERTY, detail), url=a.url)
        die("Indexing API HTTP %s: %s" % (e.code, detail))
    except Exception as e:
        die("request failed: %s" % e)

    notified = ((resp.get("urlNotificationMetadata") or {}).get("latestUpdate") or {})
    out("submitted", url=a.url, type=notified.get("type", "URL_UPDATED"),
        notified_at=notified.get("notifyTime"))


if __name__ == "__main__":
    main()
