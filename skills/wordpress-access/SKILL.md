---
name: wordpress-access
description: Read and update WordPress articles via the REST API using HTTP Basic Auth. Provides the site URL, credentials, and rules for fetching and saving posts. Used by /fact and /SEO.
---

# WordPress access

## Credentials

No secret is committed to the shared plugin — this file carries only the *resolution
order*, which is identical on every install, so it can be auto-synced like the prompts.

Resolve credentials in this order and stop at the first that yields all three values:

1. **Environment variables** `WP_BASE_URL`, `WP_USER`, `WP_APP_PASSWORD`.
2. **The file named by `$WP_CREDENTIALS_FILE`**, if that variable is set.
3. **`~/.claude/factcheck-flow/wp-credentials`** — the conventional path the installer
   writes to (mode 600, gitignored, never in the repo).

Both file forms are accepted, so an existing credentials file usually works as-is:

```
WP_BASE_URL=https://example.com
WP_USER=someone
WP_APP_PASSWORD=xxxx xxxx xxxx xxxx
```

or a plain document containing lines like `Site URL:`, `Username:`, and
`Application Password:` (the labels are matched case-insensitively).

Load them without echoing the values, e.g.:

```bash
CREDS="${WP_CREDENTIALS_FILE:-$HOME/.claude/factcheck-flow/wp-credentials}"
[ -n "$WP_APP_PASSWORD" ] || { set -a; . "$CREDS" 2>/dev/null; set +a; }
```

(That `.` form only works for the `KEY=VALUE` shape; for the labelled-document shape,
parse the three labels instead. Either way, never print a password to stdout, never
paste it into a URL you log, and never write it into a file inside the repo.)

The values you need:

- Site base URL, e.g. `https://pabau.com` (used as `$WP_BASE_URL`; no trailing `/wp-json`)
- WordPress username (`$WP_USER`)
- WordPress Application Password (`$WP_APP_PASSWORD`) — from WordPress → your Profile →
  Application Passwords. This is NOT the normal login password.

If none of the three sources yields credentials, stop and ask the user to run the
installer or set `$WP_CREDENTIALS_FILE`. Never guess, and never proceed unauthenticated.

## What you do

Given a post ID or URL plus instructions, fetch and/or update that article via the
WordPress REST API at `$WP_BASE_URL/wp-json/wp/v2/posts/`.

**The REST API is the only way you read article content.** Never `WebFetch` a public
article URL to read its body — see "Never fetch the front end for content" below.

## Fetching (read)

Two rules keep the payload small. Both matter: an article you fetch early stays in
context for the rest of the job, so every wasted kilobyte is re-read on every later turn.

**1. Always pass `_fields=`.** Without it, `context=edit` returns `content.rendered`
AND `content.raw` (the whole body twice) plus Yoast's `yoast_head` and
`yoast_head_json` blobs and a `_links` map — several times the size of what you need.

```bash
FIELDS='id,slug,link,status,type,title,content,excerpt,categories,tags,meta,featured_media'

curl -s -u "$WP_USER:$WP_APP_PASSWORD" \
  "$WP_BASE_URL/wp-json/wp/v2/posts/<POST_ID>?context=edit&_fields=$FIELDS"
```

Some installs honour nested selection, which drops `content.rendered` — a second full
copy of the body. Test it once per site:

```bash
curl -s -u "$WP_USER:$WP_APP_PASSWORD" \
  "$WP_BASE_URL/wp-json/wp/v2/posts/<POST_ID>?context=edit&_fields=content.raw" | head -c 300
```

If that returns `{"content":{"raw":"…"}}`, use `content.raw` in `FIELDS`. If it returns
the whole content object anyway, keep plain `content`.

**2. Fetch once per article, per job.** You keep the body you fetched; re-fetching it
between editing passes re-reads something you already hold.

To resolve a URL to a post ID, query by slug:

```bash
curl -s -u "$WP_USER:$WP_APP_PASSWORD" \
  "$WP_BASE_URL/wp-json/wp/v2/posts?slug=<SLUG>&context=edit&_fields=$FIELDS"
```

Other endpoints — always scoped with `_fields`, which typically cuts them by ~90%
(the defaults carry description, count, link, taxonomy and a `_links` map per term):

```bash
# categories / tags (use existing terms; do not invent)
curl -s -u "$WP_USER:$WP_APP_PASSWORD" "$WP_BASE_URL/wp-json/wp/v2/categories?per_page=100&_fields=id,name,slug"
curl -s -u "$WP_USER:$WP_APP_PASSWORD" "$WP_BASE_URL/wp-json/wp/v2/tags?per_page=100&_fields=id,name,slug"

# media library search (for sourcing images)
curl -s -u "$WP_USER:$WP_APP_PASSWORD" "$WP_BASE_URL/wp-json/wp/v2/media?search=<term>&per_page=20&_fields=id,source_url,alt_text,title"
```

## Never fetch the front end for content

The site's navigation and footer are very large. A `WebFetch` of a public article URL
spends most of its budget on that chrome before it reaches the body — which is why older
versions of these prompts told you to raise the token limit. The REST response above has
no chrome in it at all, so the workaround is unnecessary: **read via REST, always.**

To verify that a save rendered correctly, do not pull the page into context either.
Assert against it in Bash and print only the answer:

```bash
URL="<article URL>"

# how many captions rendered?
curl -s "$URL" | grep -c 'wp-element-caption'

# did a custom block render, or ship as an empty shell?
curl -s "$URL" | grep -c 'wp-block-yoast-faq-block'
curl -s "$URL" | grep -o '<table[^>]*>' | wc -l

# did any literal asterisk-italics leak to the front end?
curl -s "$URL" | grep -o '>\*[^<]\{0,80\}\*<' | head -5
```

Each of these returns a number or a couple of short lines instead of a whole page. Only
pull a real excerpt (`grep -o … -A2 -B2`) when an assertion fails and you need to see why.

## Saving (write)

**One save per article, per job.** Apply every change to the body you already hold in
memory, then PUT once at the end. Saving between passes costs a full extra copy of the
article in context each time and buys nothing.

Write the payload to a file with the Write tool, then send it by reference:

```bash
curl -s -u "$WP_USER:$WP_APP_PASSWORD" \
  -X POST "$WP_BASE_URL/wp-json/wp/v2/posts/<POST_ID>" \
  -H "Content-Type: application/json" \
  -d @payload.json \
  -o /dev/null -w '%{http_code}\n'
```

Never paste the article body inline into the shell command: the quoting breaks on real
content, and it puts a second full copy of the body into context. Discard the response
body with `-o /dev/null` — you already know what you sent, so the status code is the
entire signal you need. On a non-2xx code, re-run without `-o /dev/null` to read the error.

## Rules

- Update ONLY the fields you intend to change (`content`, `title`, `slug`, `status`,
  `categories`, `tags`, `author`, `meta`, `excerpt`/meta description as needed).
- A draft (`status: draft`) stays a draft; a published post (`status: publish`) stays
  published. Never change publication status unless explicitly instructed.
- Keep all existing HTML/Gutenberg block structure intact unless an instruction says
  to change it.
- Do not replace existing categories/tags — append only, using terms that already
  exist in WordPress.
- Fetch once, save once, and verify with a `grep` assertion rather than a page fetch.
- After saving, confirm what changed and remind the user to purge the site cache
  (e.g. WP Rocket → Purge this URL).
