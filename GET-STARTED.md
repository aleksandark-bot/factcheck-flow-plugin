# Get started (no tech knowledge needed)

This tool checks your WordPress articles for you inside Claude Code: it fact-checks
them, shows you each suggested change so **you** decide yes/no, and then makes the
approved edits plus an editorial and link cleanup.

You do **not** need to know coding or Ubuntu. If you can copy and paste, you can do
this. Follow the steps in order.

---

## Before you start

You need **Claude Code** already open and working (the chat window where you talk to
Claude). If you don't have it, ask whoever set this up for you to get it running first.

You'll also use the **Terminal** once, for the install. On Ubuntu you open it by
pressing **Ctrl + Alt + T** (or search "Terminal" in your apps).

---

## Step 1 — Install it (one copy-paste)

Open the Terminal and paste this **one line**, then press Enter:

```
bash <(curl -fsSL https://raw.githubusercontent.com/aleksandark-bot/factcheck-flow-plugin/main/install.sh)
```

It will set everything up and then ask you three questions:

1. **Site URL** — your WordPress address, e.g. `https://pabau.com`
2. **WordPress username** — your login name
3. **Application password** — see the next step for where to get this

### Where the Application Password comes from

This is a special password just for apps (not your normal login). To get it:

1. Log into your WordPress admin (usually `yoursite.com/wp-admin`).
2. Top-right, click your name → **Edit Profile** (or left menu: **Users → Profile**).
3. Scroll to **Application Passwords**.
4. Type a name like `Claude`, click **Add New Application Password**.
5. Copy the code it shows (like `abcd efgh ijkl mnop qrst uvwx`) and paste it into the
   Terminal when it asks. (You won't see it again — if you lose it, just make a new one.)

When it finishes, you'll see a green **✅ Done!** message.

## Step 2 — Restart Claude Code

Fully **close and reopen** Claude Code. This makes it notice the new `/factcheck-flow`
command. (Just closing the chat isn't enough — quit the whole app and open it again.)

## Step 3 — Use it

In the Claude Code chat box, type `/factcheck-flow` followed by the article web
addresses (or their post ID numbers), separated by spaces. Example:

```
/factcheck-flow https://yoursite.com/blog/first-article/ https://yoursite.com/blog/second-article/
```

You can do up to about 5 at a time.

### What happens next

1. **It reads the articles and finds possible issues.** It does **not** change anything
   yet.
2. **It asks you about each issue**, one at a time, with buttons to pick from — usually
   **Apply the fix**, **Reject**, or **Edit it yourself**. Some ask you to type a value
   (like a review score it can't look up). Just pick or type for each one.
3. **Once you've answered them all, it does the rest automatically** — applies what you
   approved, tidies the writing, and fixes the links. Then it tells you what it did.

Your only jobs are handing it the articles and answering the yes/no questions.

---

## Good to know

- **Nothing changes without your OK.** The first pass only *suggests*; you approve each
  change before anything is written.
- **Try one article first.** Before a big batch, run it on a single **draft** post.
- **Published stays published, drafts stay drafts.** It never publishes for you.
- **After it finishes**, clear your site cache so changes show up (WP Rocket →
  **Purge this URL**).

## If something goes wrong

- **`curl: command not found`** in the Terminal: paste
  `sudo apt-get install -y curl` first, then redo Step 1.
- **`/factcheck-flow` doesn't appear** in Claude Code: make sure you fully quit and
  reopened the app (Step 2).
- **Login / credentials errors:** the usual cause is a typo in the site address or
  application password. Re-run the Step 1 install line — it lets you enter them again
  (delete the file `~/.claude/factcheck-flow/wp-credentials` first if you want a clean
  reset).
- **Still stuck?** Tell Claude in the chat what you typed and what it said back — it can
  walk you through the fix.

---

## Optimizing one article (/SEO)

Besides checking articles, you can **optimize** one for search. In the chat, type:

```
/SEO https://yoursite.com/blog/your-article/
```

The first thing it asks is **"Is this a draft?"**

- **Draft** → it does everything automatically: researches keywords, improves the headings and
  text, then runs the fact-check.
- **A published article you're updating** → it builds keyword lists (including what the page
  already ranks for on Google) and opens a **keyword picker in your browser**. Tick the
  keywords you want and click **Save** — it continues automatically, optimizes the article,
  and runs the fact-check.

**Two extra bits for published articles:**

1. It uses Google Search Console data, which needs a key file from whoever set this up. Ask
   them for the **GSC service-account JSON**, then either let the installer copy it in when it
   asks, or save it to `~/.claude/factcheck-flow/gsc-key.json`. (Draft optimization works
   without it.)
2. The keyword picker opens in your default web browser — nothing extra to install.

---

## Updating later

If the prompts or the tool are improved, just re-run the same one-line install command
from Step 1. It refreshes everything and keeps your saved WordPress login.

---

<sub>Note: there is also a `/plugin` install method (see README) for Claude Code setups
that have the plugin system enabled. If your Claude Code says plugins aren't available,
use the Terminal installer above — it works everywhere.</sub>
