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

Credentials are **not** stored in this plugin. Each user provides their own via
environment variables in their local, gitignored settings file.

1. In WordPress, create an **Application Password**: Users → Profile → Application
   Passwords.
2. In your project's `.claude/settings.local.json` (create it if needed), add:

```json
{
  "env": {
    "WP_BASE_URL": "https://your-site.com",
    "WP_USER": "your-wordpress-username",
    "WP_APP_PASSWORD": "xxxx xxxx xxxx xxxx xxxx xxxx"
  }
}
```

`settings.local.json` is git-ignored — never commit real credentials. Restart the
session so the env vars load.

## Use

```
/factcheck-flow https://your-site.com/blog/article-one/ https://your-site.com/blog/article-two/ 12345
```

Accepts full URLs or bare post IDs, whitespace-separated, up to ~5 at a time.

## Customizing for your site

The three passes are plain editable files under `prompts/`:

- `prompts/1-factcheck.md` — accuracy / category / tag / link / structure review.
- `prompts/2-editorial.md` — your house style guide (fluff, US English, structure,
  meta descriptions, etc.).
- `prompts/3-links.md` — internal/external link rules. **Edit the site paths, the
  minimum internal-link count, the replacement blog source, and the banned-link list**
  to match your own site (the defaults are specific to one site).

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
