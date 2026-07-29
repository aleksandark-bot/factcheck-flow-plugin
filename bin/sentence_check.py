#!/usr/bin/env python3
"""
sentence_check.py — find every sentence in a WordPress article that breaks the
sentence-length ceiling (25 words, 30 absolute max).

Models cannot count words reliably while writing prose, so /fact and /SEO do not
ask them to. They run this instead, fix what it lists, and re-run until it exits 0.

Usage
  sentence_check.py --post 151170            # fetch raw block markup via the WP REST API
  sentence_check.py --url https://site/slug/ # resolve the slug, then fetch
  sentence_check.py --file article.html      # check a local file
  cat article.html | sentence_check.py       # check stdin

Options
  --max N     soft ceiling, the number to write to   (default 25)
  --hard N    absolute ceiling, never acceptable     (default 30)
  --json      machine-readable output
  --all       list every sentence with its count, not just violations
  --top N     show at most N violations (default: all)

Exit codes
  0  clean — every sentence is within --max
  1  at least one sentence is over --max
  2  usage / fetch error

WP credentials come from the same place as the wordpress-access skill:
WP_BASE_URL, WP_USER, WP_APP_PASSWORD in the environment, or a
$WP_CREDENTIALS_FILE / ~/.claude/factcheck-flow/wp-credentials shell file.
"""

import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

# ── credentials ────────────────────────────────────────────────────────────────

CRED_KEYS = ("WP_BASE_URL", "WP_USER", "WP_APP_PASSWORD")


def load_credentials():
    creds = {k: os.environ.get(k, "") for k in CRED_KEYS}
    if all(creds.values()):
        return creds
    path = os.environ.get("WP_CREDENTIALS_FILE") or os.path.expanduser(
        "~/.claude/factcheck-flow/wp-credentials"
    )
    if os.path.exists(path):
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                line = re.sub(r"^export\s+", "", line)
                if "=" not in line:
                    continue
                key, val = line.split("=", 1)
                key = key.strip()
                if key in CRED_KEYS and not creds.get(key):
                    creds[key] = val.strip().strip("'\"")
    return creds


def wp_get(path, creds):
    url = creds["WP_BASE_URL"].rstrip("/") + path
    req = urllib.request.Request(url, headers={"User-Agent": "sentence_check/1.0"})
    token = f"{creds['WP_USER']}:{creds['WP_APP_PASSWORD']}".encode()
    import base64

    req.add_header("Authorization", "Basic " + base64.b64encode(token).decode())
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8", "replace"))


def fetch_post_content(post_id=None, url=None):
    creds = load_credentials()
    missing = [k for k in CRED_KEYS if not creds.get(k)]
    if missing:
        die(
            "missing WP credentials: "
            + ", ".join(missing)
            + " (set them in the environment or ~/.claude/factcheck-flow/wp-credentials)"
        )
    if url and not post_id:
        slug = [s for s in urllib.parse.urlparse(url).path.split("/") if s]
        if not slug:
            die(f"could not read a slug out of {url}")
        found = wp_get(f"/wp-json/wp/v2/posts?slug={slug[-1]}&context=edit", creds)
        if not found:
            for ptype in ("pages",):
                found = wp_get(
                    f"/wp-json/wp/v2/{ptype}?slug={slug[-1]}&context=edit", creds
                )
                if found:
                    break
        if not found:
            die(f"no post found for slug '{slug[-1]}'")
        return found[0].get("content", {}).get("raw", "")
    post = wp_get(f"/wp-json/wp/v2/posts/{post_id}?context=edit", creds)
    return post.get("content", {}).get("raw", "")


def die(msg):
    sys.stderr.write(f"sentence_check: {msg}\n")
    sys.exit(2)


# ── extracting text units ──────────────────────────────────────────────────────
#
# A "unit" is a span of prose whose sentences cannot run into another span: one
# paragraph, one list item, one table cell, one caption, one block attribute
# string. Splitting into units first is what stops a heading (no terminal
# punctuation) from being glued onto the paragraph beneath it and reported as one
# enormous sentence.

# Block-level containers whose text is prose we check.
UNIT_TAGS = ("p", "li", "td", "th", "figcaption", "dd", "dt", "blockquote", "caption")
# Skipped: headings are labels, not sentences; code/pre is not prose.
SKIP_TAGS = ("h1", "h2", "h3", "h4", "h5", "h6", "pre", "code", "script", "style")

# Block attribute keys that hold reader-facing prose.
TEXT_KEYS = (
    "text",
    "heading",
    "description",
    "title",
    "caption",
    "question",
    "answer",
    "content",
    "label",
    "subheading",
    "excerpt",
)
NON_PROSE = re.compile(
    r"^(https?://|/|#[0-9a-fA-F]{3,8}$|[\w-]+\.(png|jpe?g|webp|svg|gif|pdf)$)"
)


def strip_tags(fragment):
    fragment = re.sub(
        r"<(script|style)\b[^>]*>.*?</\1>", " ", fragment, flags=re.S | re.I
    )
    fragment = re.sub(r"<br\s*/?>", " ", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    text = html.unescape(fragment)
    text = text.replace(" ", " ").replace("​", "")
    return re.sub(r"\s+", " ", text).strip()


def walk_json(node, out, block, key=None):
    if isinstance(node, dict):
        for k, v in node.items():
            walk_json(v, out, block, k)
    elif isinstance(node, list):
        for item in node:
            walk_json(item, out, block, key)
    elif isinstance(node, str):
        val = node.strip()
        if not val or NON_PROSE.match(val):
            return
        # Only attributes that plausibly hold prose, and only if they read like it.
        if key not in TEXT_KEYS:
            return
        text = strip_tags(val)
        if text.count(" ") >= 2:
            out.append((f"{block}.{key}", text))


def extract_units(content):
    """Return [(location, text)] for every prose unit in raw block markup."""
    units = []

    # 1. Prose held in block attributes (Key takeaways items, CTA heading/description,
    #    FAQ questions/answers, download-box copy, …).
    for match in re.finditer(r"<!--\s*wp:([a-z0-9/-]+)\s*(\{.*?\})?\s*/?-->", content, re.S):
        block, raw_attrs = match.group(1), match.group(2)
        if not raw_attrs:
            continue
        try:
            attrs = json.loads(raw_attrs)
        except (ValueError, TypeError):
            continue
        walk_json(attrs, units, block)

    # 2. Prose in HTML. Drop block comments first so their JSON is not re-read as text.
    body = re.sub(r"<!--.*?-->", " ", content, flags=re.S)
    body = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", body, flags=re.S | re.I)
    for tag in SKIP_TAGS:
        body = re.sub(rf"<{tag}\b[^>]*>.*?</{tag}>", " ", body, flags=re.S | re.I)

    consumed = []
    for tag in UNIT_TAGS:
        for match in re.finditer(
            rf"<{tag}\b[^>]*>(.*?)</{tag}>", body, flags=re.S | re.I
        ):
            text = strip_tags(match.group(1))
            if text:
                units.append((tag, text))
            consumed.append((match.start(), match.end()))

    # 3. Anything left outside a recognized container (loose prose, stray markup).
    consumed.sort()
    cursor, leftovers = 0, []
    for start, end in consumed:
        if start > cursor:
            leftovers.append(body[cursor:start])
        cursor = max(cursor, end)
    leftovers.append(body[cursor:])
    for chunk in leftovers:
        text = strip_tags(chunk)
        if text and text.count(" ") >= 3:
            units.append(("loose", text))

    # De-duplicate: the same string can surface via both an attribute and the HTML.
    seen, unique = set(), []
    for loc, text in units:
        if text not in seen:
            seen.add(text)
            unique.append((loc, text))
    return unique


# ── sentence splitting ─────────────────────────────────────────────────────────

ABBREVIATIONS = (
    "e.g", "i.e", "etc", "vs", "approx", "est", "cf", "al", "ca",
    "Dr", "Mr", "Mrs", "Ms", "Prof", "Sr", "Jr", "St", "Inc", "Ltd", "Co", "Corp",
    "No", "Fig", "Vol", "Ch", "Sec", "min", "max", "avg", "hrs",
    "a.m", "p.m", "A.M", "P.M", "U.S", "U.K", "U.S.A", "Ph.D", "M.D", "R.N",
)
SENT_END = re.compile(r"(?<=[.!?])[\"')\]]*\s+")


def protect(text):
    """Mask periods that do not end a sentence, so the splitter ignores them."""
    marker = "\x00"
    for abbr in ABBREVIATIONS:
        text = re.sub(
            rf"(?<![\w.]){re.escape(abbr)}\.", abbr.replace(".", marker) + marker, text
        )
    # Decimals and dotted codes: 1.5, T86.298, ICD-10 codes, 3.4.1
    text = re.sub(r"(?<=\d)\.(?=\d)", marker, text)
    text = re.sub(r"(?<=[A-Z])\.(?=\d)", marker, text)
    # Single initials: J. Smith
    text = re.sub(r"(?<![\w.])([A-Z])\.(?=\s+[A-Z])", r"\1" + marker, text)
    # Ellipses
    text = text.replace("...", marker * 3)
    return text, marker


def split_sentences(text):
    masked, marker = protect(text)
    parts = []
    for piece in SENT_END.split(masked):
        piece = piece.replace(marker, ".").strip()
        if piece:
            parts.append(piece)
    return parts


WORD = re.compile(r"[0-9A-Za-zÀ-ɏ]")


def count_words(sentence):
    return sum(1 for tok in sentence.split() if WORD.search(tok))


# ── reporting ──────────────────────────────────────────────────────────────────


def analyze(content, max_words, hard_words):
    rows = []
    for loc, text in extract_units(content):
        for sentence in split_sentences(text):
            rows.append(
                {
                    "location": loc,
                    "words": count_words(sentence),
                    "sentence": sentence,
                }
            )
    violations = [r for r in rows if r["words"] > max_words]
    violations.sort(key=lambda r: -r["words"])
    return {
        "total_sentences": len(rows),
        "max_words": max(( r["words"] for r in rows), default=0),
        "over_max": len(violations),
        "over_hard": sum(1 for r in violations if r["words"] > hard_words),
        "in_grace": sum(1 for r in violations if r["words"] <= hard_words),
        "limit": max_words,
        "hard_limit": hard_words,
        "violations": violations,
        "all": rows,
    }


def main():
    ap = argparse.ArgumentParser(add_help=True, description=__doc__.split("\n")[1])
    src = ap.add_mutually_exclusive_group()
    src.add_argument("--post", help="WordPress post ID")
    src.add_argument("--url", help="article URL (slug is resolved to an ID)")
    src.add_argument("--file", help="local file of raw block markup / HTML")
    ap.add_argument("--max", type=int, default=25, help="soft ceiling (default 25)")
    ap.add_argument("--hard", type=int, default=30, help="absolute ceiling (default 30)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--all", action="store_true", help="list every sentence")
    ap.add_argument("--top", type=int, default=0, help="show at most N violations")
    args = ap.parse_args()

    if args.post or args.url:
        try:
            content = fetch_post_content(post_id=args.post, url=args.url)
        except urllib.error.HTTPError as exc:
            die(f"WP API returned HTTP {exc.code} — check the ID/URL and credentials")
        except urllib.error.URLError as exc:
            die(f"could not reach the WP API: {exc.reason}")
    elif args.file:
        with open(args.file, encoding="utf-8", errors="replace") as fh:
            content = fh.read()
    else:
        if sys.stdin.isatty():
            ap.print_help()
            return 2
        content = sys.stdin.read()

    if not content.strip():
        die("no content to check")

    result = analyze(content, args.max, args.hard)

    if args.json:
        print(json.dumps(result, indent=2))
        return 1 if result["over_max"] else 0

    rows = result["all"] if args.all else result["violations"]
    if args.top:
        rows = rows[: args.top]

    if args.all:
        for row in sorted(rows, key=lambda r: -r["words"]):
            mark = "OVER" if row["words"] > args.max else "ok  "
            print(f"{mark} {row['words']:3}w [{row['location']}] {row['sentence']}")
    else:
        for row in rows:
            severity = "TOO LONG" if row["words"] > args.hard else "over 25 "
            print(f"{severity} {row['words']:3}w [{row['location']}] {row['sentence']}")

    print(
        f"\n{result['total_sentences']} sentences | longest {result['max_words']}w | "
        f"{result['over_max']} over {args.max} "
        f"({result['in_grace']} in the 26–{args.hard} grace band, "
        f"{result['over_hard']} over {args.hard})"
    )
    if result["over_max"]:
        print(
            f"FAIL: rewrite the sentences above, then re-run. "
            f"Only sentences that genuinely cannot be split may sit in the "
            f"26–{args.hard} band; nothing may exceed {args.hard}."
        )
        return 1
    print("PASS: every sentence is within the ceiling.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
