<!--
  PROMPT 3 — LINK AUDIT PASS (applied automatically in Stage 3)
  Edit the site paths, minimum link count, replacement-source blog, and the
  banned-link list below for your own site.
-->

For this article, check internal links (NOT redirects, NOT nofollow, anchor text makes sense with the content and searcher intent). No duplicate links, unless they're in the "Expert Picks" or "Continue your research" (the box at the bottom that lists other articles to visit). If you remove links for any reason, find appropriate Pabau blogs to replace them with. Aim for internal links to /blog/, /diagnostic-codes/, /procedure-codes/, or /templates/ pages that scale with the article's length — roughly **one internal link per 200 words** (so ~15 for a 3,000-word article). This is an ideal target, not a hard floor: get close to it with links that fit naturally, but never stuff or pad to reach the number — a shorter or link-sparse article that reads well is better than a padded one.

Linking must be organic. Place every link inside a sentence that already earns its place in the article — **never write a new paragraph or sentence whose purpose is to carry a link, and never pad the article to hit the link count**. Allow **no more than 2 internal links in any single paragraph**; spread links across the article rather than clustering them. If hitting the minimum would force stuffing, prefer fewer, well-placed links over cramming.

Every article must link to **exactly two /industry/ pages**. Prefer the /industry/ pages that are currently the **least linked to** from the rest of the site, so link equity is spread rather than concentrated — from those, pick the two that best fit the article's topic and can be worked in naturally. To find the least-linked candidates, list the site's /industry/ pages and check how many internal links already point to each (via the `wordpress-access` skill or a site search); if that genuinely can't be determined, choose the two most topically relevant /industry/ pages instead. These two links **count toward the internal-link target above** (they are not extra), and they are still bound by the max-2-links-per-paragraph and organic-placement rules.

Where it fits naturally, link to **at most one /case-studies/ page** — this is preferred but **not mandatory**: include it only where a case study genuinely supports the surrounding sentence, and never add one if there's no natural home for it. **No more than one /case-studies/ link per article.** Prefer the /case-studies/ pages that are currently the **least linked to** from the rest of the site, so link equity is spread rather than concentrated — from those, pick the one that best fits the article's topic. To find the least-linked candidates, list the site's /case-studies/ pages and check how many internal links already point to each (via the `wordpress-access` skill or a site search); if that genuinely can't be determined, choose the most topically relevant /case-studies/ page instead. If included, this link **counts toward the internal-link target above** (it is not extra), and it is still bound by the max-2-links-per-paragraph and organic-placement rules.

For duplicate links, always remove the second link, then rephrase the sentence containing it so it makes sense without the link. If the removed link was in a sentence solely directing the reader to read the linked article, delete the sentence entirely. If the removed link was in an Expert picks / continue your research block, then replace the entire sentence with another one, linking to a different article that satisfies the Expert picks rules below.

**Expert picks / Continue your research block.** This is the box at the bottom that lists other articles to visit. It must contain **5 links AT MOST** — if it currently has more, trim it down to the 5 strongest, most topically relevant ones and delete the rest. Every article linked from this block must be an **orphan, near-orphan, or "lonely" page** — one with **fewer than 5 internal links already pointing to it** from the rest of the site. The entire purpose of this block is to spread link equity to under-linked pages, so never fill it with already-well-linked articles. To choose targets, use the `wordpress-access` skill or a site search to count how many internal links already point to each candidate; keep/add only those under 5, prioritizing true orphans (0 inbound links) first, then near-orphans (1–2), then lonely pages (3–4). If an article already sitting in the block turns out to be well-linked (5+ inbound links), replace it with a lonely one that still fits the article's topic. If you genuinely cannot determine inbound-link counts, prefer the most recently published articles (which are the least likely to have accumulated links yet).

Check today's date. Find all articles published the past day in /blog/, /diagnostic-codes/, /procedure-codes/, or /templates/. Link to at least 3 of those articles (choose them at random, do not go in order).

Check for any 3xx redirects or 4xx errors; all links must return a clean 200.

External links must be nofollow, open in new tab.

Internal links open in the same tab and are NOT nofollow.

Keep up to 5 external links ONLY. Choose the ones with the greatest impact, keep those, and remove the rest, while fixing the context around them to make sense without the link.

Remove any links to these articles and replace them with something else:
- …/intraparenchymal-hemorrhage-icd-10-codes/
- …/blog/acne-face-mapping/
- …/icd-10-code-for-autistic-disorder/
- …/situational-anxiety-icd-10-code/
- …/blog/ index

When you link to articles from the /diagnostic-codes/ or /procedure-codes/ subfolders, the anchor text should be just the procedural or diagnostic code itself, and the sentence should not contain any parentheticals describing what the code refers to (as this makes sentences extremely clunky).

Anchor text should be no longer than 4 words. Reduce anchor text that is too long.

When you have finished ALL link changes, read the whole article through once more for flow — this is the last thing you do in the link step. Make sure the interlinking hasn't interrupted the flow of the article, its sections, or any individual paragraph. Watch for link-cluttered paragraphs, awkwardly inserted anchors, and sentences that now exist only to hold a link. Fix anything that blocks flow automatically — rephrase, merge, or cut — without asking.

Note: This is a newly published article or draft that may not yet be indexed by search engines. Fetch the URL directly and review the full article body content. Use a high token limit when fetching because the site has very large navigation menus that consume token space before the article body appears. You have full WordPress access and login via the `wordpress-access` skill (SKILL.md).
