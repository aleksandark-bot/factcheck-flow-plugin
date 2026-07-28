# factcheck-flow

A Claude Code plugin that batch-QAs WordPress articles. You give it a set of article
URLs (or post IDs); it runs three passes over each, with **one** human checkpoint in
the middle:

1. **Fact-check (parallel, read-only)** — one agent per article reviews accuracy,
   categories/tags, links, and structure, and returns a findings report. Nothing is
   written yet.
2. **Triage (you)** — you approve / reject / edit **each** finding individually, and
   supply any values only you can know (e.g. correct Capterra/G2/Trustpilot scores).
3. **Apply + editorial + links (parallel, automated)** — one agent per article applies
   the approved fixes, then the editorial pass, then the link-audit pass, writing
   changes back over the WordPress REST API.

Your only manual actions are handing over the URLs and doing the triage. Everything
else runs automatically.

## Install

In Claude Code:

```
/plugin marketplace add <this-repo-or-local-path>
/plugin install factcheck-flow@factcheck-tools
```

(You can also `/plugin marketplace add /absolute/path/to/factcheck-flow-plugin` for
local testing before pushing to a git host.)

## One-time setup: WordPress credentials

Credentials are **not** stored in this plugin. The `wordpress-access` skill carries only
the resolution order, which is the same on every install — that's what lets the skill be
auto-synced along with the prompts. Pick whichever of the three sources suits you:

1. In WordPress, create an **Application Password**: Users → Profile → Application
   Passwords.
2. Then either:

**a) The installer's file (simplest).** `install.sh` prompts for the three values and
writes them to `~/.claude/factcheck-flow/wp-credentials` (mode 600, never in the repo).
Nothing else to configure — the skill looks there by default.

**b) Point at a credentials file you already have.** Set `WP_CREDENTIALS_FILE` to its
path in `~/.claude/settings.json`:

```json
{
  "env": {
    "WP_CREDENTIALS_FILE": "/path/to/your/wp-credentials"
  }
}
```

The file may be `KEY=VALUE` lines (`WP_BASE_URL=…`, `WP_USER=…`, `WP_APP_PASSWORD=…`) or
a plain document with `Site URL:`, `Username:`, and `Application Password:` labels.
Only the *path* goes in settings — the secret stays in the file.

**c) Environment variables**, if you prefer them, in `.claude/settings.local.json`:

```json
{
  "env": {
    "WP_BASE_URL": "https://your-site.com",
    "WP_USER": "your-wordpress-username",
    "WP_APP_PASSWORD": "xxxx xxxx xxxx xxxx xxxx xxxx"
  }
}
```

Env vars win over `$WP_CREDENTIALS_FILE`, which wins over the default path.
`settings.local.json` is git-ignored — never commit real credentials. Restart the
session after any of these so the settings load.

## Use

```
/factcheck-flow https://your-site.com/blog/article-one/ https://your-site.com/blog/article-two/ 12345
```

Accepts full URLs or bare post IDs, whitespace-separated, up to ~5 at a time.

## /SEO — single-article optimization

`/SEO <url-or-id>` optimizes ONE article end to end: it researches keywords (DataForSEO +
Google Search Console), lets you choose which to target, rewrites/adds headings and content
around them, updates the main keyword / meta description / SEO title when you promote a new
main keyword, and then automatically runs `/fact` on the same article.

Its first question is always **"Is this a draft?"**

- **Draft** → fully automatic keyword selection, then it saves and runs `/fact`.
- **Published** → it also pulls the queries the page already ranks for from GSC, and opens a
  clean keyword picker in your browser; you choose keywords, click Save, and it continues.
- If very few keywords are found, it falls back to an in-chat multiple-choice picker and asks
  whether to optimize at all before proceeding.

The flow is split in two so the writing instructions and writing guides stay out of context
during the research stages: `prompts/seo-research.md` (S0–S3, read at the start) and
`prompts/seo-write.md` (S4–S9, read only once you pass the proceed gate). Both are auto-synced
like the other prompts. The command is `commands/SEO.md`. Helpers: `bin/gsc_query.py` (GSC),
`bin/dfs_lists.py` (builds all five keyword lists in code), `bin/keyword_picker.py` and
`bin/serp_picker.py` (the browser pickers).

`bin/dfs_lists.py` needs DataForSEO credentials. It resolves them from `$DATAFORSEO_LOGIN` +
`$DATAFORSEO_PASSWORD`, or `$DATAFORSEO_AUTH` (base64 `login:password`), or
`~/.claude/factcheck-flow/dataforseo-key.json`, and finally falls back to the `dataforseo` MCP
server entry in `~/.claude.json` — so if you already have that MCP server configured, it works
with no extra setup.

### GSC access (required for published articles)

The "already ranking" list reads Google Search Console via a **service-account key** — a
secret that is **not** in this repo. Each user needs:

1. The service-account **JSON key** (ask your admin) at `~/.claude/factcheck-flow/gsc-key.json`
   (the installer offers to copy it there), or pointed to via `$PABAU_GSC_KEY`.
2. That service account granted **read access** to the Search Console property
   (`https://pabau.com/`) — the admin adds its `client_email` as a user in GSC.
3. **PyJWT** (`python3 -m pip install --user pyjwt`) — the installer does this when it can.

Without it, draft-mode `/SEO` still works; published-mode stops with a clear message until the
key is set up.

## Customizing for your site

The three passes are plain editable files under `prompts/`:

- `prompts/1-factcheck.md` — accuracy / category / tag / link / structure review.
- `prompts/2-editorial.md` — your house style guide (fluff, US English, structure,
  meta descriptions, etc.).
- `prompts/3-links.md` — internal/external link rules. **Edit the site paths, the
  minimum internal-link count, the replacement blog source, and the banned-link list**
  to match your own site (the defaults are specific to one site).

Reference guides under `guides/` define voice, product context, and the block contract, and
are read by the editorial pass and the fact-check reviewer:

- `guides/Pabau-style-guide.md` — tone of voice, benefit framing, US/UK terminology,
  formatting mechanics, and a treatments/regulation glossary.
- `guides/About-Pabau.md` — what the product is, its product family and naming rules,
  pricing model, competitors, and the customer journey.
- `guides/WordPress-blocks.md` — the block contract every article must satisfy, with exact
  markup: required document order, the Key takeaways block, the template download box, the
  Pabau CTA (`book-demo`) block and the section that carries it, the `Conclusion` heading and
  its CTA link, the Continue your research (`expert-picks`) block, the Yoast FAQ block,
  listicle pricing tables, and the image caption contract (every image captioned, full
  sentence, italic). **Site-specific — the custom block names and inline styles are
  Pabau's; swap them for your own theme's blocks.**

**These defaults are Pabau-specific — replace them with your own brand's voice and
product context** (keep the filenames, or update the references in `prompts/2-editorial.md`
and the `factcheck-reporter` agent if you rename them). The installer also adds a small
Pabau block to `~/.claude/CLAUDE.md` (between managed markers) so ad-hoc editing outside
`/fact` picks up the guides too.

Edit these freely; the workflow picks up your changes on the next run.

## How it's built

- `commands/factcheck-flow.md` — the orchestrator that drives the three stages and the
  triage gate (runs in the main conversation, since only it can ask you questions).
- `agents/factcheck-reporter.md` — Stage 1 worker (read-only).
- `agents/article-editor.md` — Stage 3 worker (applies all three passes to one
  article, end to end).
- `skills/wordpress-access/SKILL.md` — REST API read/write helper used by the agents.

## Safety notes

- Stage 1 never writes to WordPress — findings are reported for your approval first.
- Test on a **draft** post before running against live published articles.
- Drafts stay drafts and published posts stay published; publication status is never
  changed automatically.
