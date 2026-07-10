---
description: Optimize ONE WordPress article — GSC + DataForSEO keyword research, keyword selection (auto for drafts, checklist for published), on-page optimization, then hand off to /fact.
argument-hint: "<url-or-id>   (one article)"
---

Article: **$ARGUMENTS**

STOP — your VERY FIRST action, before reading any file, fetching anything, calling any tool,
or reasoning about the article, is to ask the user exactly this one question and wait:

> **Is this a draft, or a published article being updated?**  →  **[Draft]** / **[Published update]**

Ask it immediately (use AskUserQuestion). Do not run tools first. Do not think for long. Just ask.

Once answered, set `is_draft` (Draft → true, Published → false) and then read the full flow and
execute it end to end:

- Read `~/.claude/factcheck-flow/prompts/seo.md` and perform stages **S0 → S9 in order**,
  passing your `is_draft` answer into S0 (do not ask the draft question again).
- Branch per that file: **draft → quick/automatic** (no GSC list); **published → manual**
  (GSC list + Obsidian checklist on the Desktop). Honor the scarcity fallback and the
  "Do you want to proceed with optimization?" gate.
- If no article argument was given, ask for the URL/ID first (after the draft question).

Follow `seo.md` exactly, including its CONFIG, keyword-selection logic, and the final `/fact`
hand-off in S9.
