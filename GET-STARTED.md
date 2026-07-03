# Get started (no tech knowledge needed)

This plugin checks your WordPress articles for you: it fact-checks them, shows you
each suggested change so **you** decide yes/no, and then makes the approved edits
plus an editorial and link cleanup — all inside Claude Code.

You do **not** need to know Ubuntu, coding, or the command line. If you can copy and
paste, you can do this. Follow the steps in order.

---

## Before you start

You need **Claude Code** open and working (the chat window where you talk to Claude).
If you don't have it yet, ask whoever set this up for you to get it running first.
Everything below is typed into that same Claude Code chat box.

---

## Step 1 — Add the plugin (copy, paste, press Enter)

Click into the Claude Code chat box and paste this exactly, then press Enter:

```
/plugin marketplace add aleksandark-bot/factcheck-flow-plugin
```

You should see a message saying a marketplace called **factcheck-tools** was added.

## Step 2 — Install it (copy, paste, press Enter)

Now paste this and press Enter:

```
/plugin install factcheck-flow@factcheck-tools
```

You should see that **factcheck-flow** is now installed. That's the plugin in. ✅

---

## Step 3 — Give it your WordPress login (one time only)

The plugin needs to log into your WordPress site to read and edit articles. You give
it a special "Application Password" — this is **not** your normal password, it's a
safe one just for apps, and you can delete it anytime.

**3a. Get the Application Password from WordPress:**

1. Log into your WordPress admin (usually `yoursite.com/wp-admin`).
2. Top-right, click your name → **Edit Profile** (or left menu: **Users → Profile**).
3. Scroll down to the section called **Application Passwords**.
4. In the box, type a name so you remember it, e.g. `Claude`, then click
   **Add New Application Password**.
5. WordPress shows you a code like `abcd efgh ijkl mnop qrst uvwx`. **Copy it now** —
   you won't be able to see it again (if you lose it, just make a new one).

**3b. Tell Claude your login — just type it in the chat, in plain English:**

Paste a message like this into Claude Code (fill in your own details):

```
Set my WordPress credentials for the factcheck-flow plugin.
Site: https://yoursite.com
Username: your-wordpress-username
Application password: abcd efgh ijkl mnop qrst uvwx
```

Claude will save these safely on your computer. You only do this once.

---

## Step 4 — Use it

Whenever you want to check articles, paste `/factcheck-flow` followed by the article
web addresses (or their post ID numbers), separated by spaces. Example:

```
/factcheck-flow https://yoursite.com/blog/first-article/ https://yoursite.com/blog/second-article/
```

You can do up to about 5 at a time.

### What happens next

1. **It reads the articles and finds possible issues.** It does **not** change anything
   yet.
2. **It asks you about each issue**, one at a time, with buttons to pick from — usually
   **Apply the fix**, **Reject**, or **Edit it yourself**. Some questions ask you to type
   in a value (like a review score it can't look up). Just pick or type for each one.
3. **Once you've gone through them, it does the rest automatically** — applies the changes
   you approved, tidies up the writing, and fixes the links. Then it tells you what it did.

That's it. Your only jobs are handing it the articles and answering the yes/no questions.

---

## Good to know

- **Nothing gets changed without your OK.** The first pass only *suggests*; you approve
  each change before anything is written.
- **Try one article first.** Before doing a big batch, run it on a single **draft** post
  to see how it feels.
- **Published stays published, drafts stay drafts.** It never publishes something for you.
- **After it finishes**, it will remind you to clear your site cache (if you use WP
  Rocket: **WP Rocket → Purge this URL**) so the changes show up for visitors.

## If something goes wrong

- **"marketplace not found" / "command not found":** re-check Step 1 and 2 were typed
  exactly, then close and reopen Claude Code and try again.
- **"credentials not set" or login errors:** redo Step 3 — the most common cause is a
  typo in the site address or the application password. Make a fresh Application Password
  in WordPress and set it again.
- **Still stuck?** Just tell Claude in the chat what you typed and what it said back — it
  can walk you through the fix.
