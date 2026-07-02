---
name: wordpress-access
description: Read and update WordPress articles via the REST API using HTTP Basic Auth. Provides the site URL, credentials, and rules for fetching and saving posts. Used by /factcheck-flow.
---

# WordPress access

## Credentials

This skill reads credentials from environment variables so no secret is committed to
the shared plugin. Set these once in your own `.claude/settings.local.json` (which is
gitignored) — see the plugin README:

- `WP_BASE_URL`   — e.g. `https://example.com` (no trailing `/wp-json`)
- `WP_USER`       — your WordPress username
- `WP_APP_PASSWORD` — a WordPress Application Password (Users → Profile → Application Passwords)

If those variables are not set, stop and tell the user to configure them per the
README rather than guessing.

## What you do

Given a post ID or URL plus instructions, fetch and/or update that article via the
WordPress REST API at `$WP_BASE_URL/wp-json/wp/v2/posts/`.

## Fetching (read)

Always fetch the current article first, with edit context so you see raw block markup:

```bash
curl -s -u "$WP_USER:$WP_APP_PASSWORD" \
  "$WP_BASE_URL/wp-json/wp/v2/posts/<POST_ID>?context=edit"
```

To resolve a URL to a post ID, query by slug:

```bash
curl -s -u "$WP_USER:$WP_APP_PASSWORD" \
  "$WP_BASE_URL/wp-json/wp/v2/posts?slug=<SLUG>&context=edit"
```

Categories/tags list endpoints (use existing terms; do not invent):

```bash
curl -s -u "$WP_USER:$WP_APP_PASSWORD" "$WP_BASE_URL/wp-json/wp/v2/categories?per_page=100"
curl -s -u "$WP_USER:$WP_APP_PASSWORD" "$WP_BASE_URL/wp-json/wp/v2/tags?per_page=100"
```

## Saving (write)

Apply changes to the fetched body/fields, then PUT them back. Send only the fields you
are changing:

```bash
curl -s -u "$WP_USER:$WP_APP_PASSWORD" \
  -X POST "$WP_BASE_URL/wp-json/wp/v2/posts/<POST_ID>" \
  -H "Content-Type: application/json" \
  -d @payload.json
```

## Rules

- Update ONLY the fields you intend to change (`content`, `title`, `slug`, `status`,
  `categories`, `tags`, `author`, `meta`, `excerpt`/meta description as needed).
- A draft (`status: draft`) stays a draft; a published post (`status: publish`) stays
  published. Never change publication status unless explicitly instructed.
- Keep all existing HTML/Gutenberg block structure intact unless an instruction says
  to change it.
- Do not replace existing categories/tags — append only, using terms that already
  exist in WordPress.
- After saving, confirm what changed and remind the user to purge the site cache
  (e.g. WP Rocket → Purge this URL).
