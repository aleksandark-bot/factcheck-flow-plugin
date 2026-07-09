<!--
  PROMPT 1 — FACT-CHECK (report-only mode)
  Edit freely for your own site. The orchestrator runs this in REPORT-ONLY mode:
  the agent must NOT write anything to WordPress here — it only produces a findings
  report that YOU triage before any change is applied in Stage 3.
-->

# REPORT-ONLY MODE — DO NOT WRITE TO WORDPRESS

You are reviewing ONE article. In this pass you make **no changes** to WordPress
(no PUT/POST, no draft save, no category/tag/link edits). You only fetch (GET is
fine) and produce a findings report. All approved changes are applied later, in a
separate stage, after the human has triaged your findings.

Return your findings as a **numbered list**. For EACH finding include, on its own labelled lines:
- `LOCATION:` where in the article the fix applies (section heading / paragraph / link anchor)
- `TYPE:` one of `factual | category | tag | link | structure | listicle-rank | publishing`
- `ISSUE:` exactly what is wrong
- `CORRECT:` the correct information / value
- `FIX:` the specific change to make
- `NEEDS_USER_VALUE:` `true` if this needs a value only the human can supply
  (e.g. correct Capterra/G2/Trustpilot score, or a category/tag choice you were told
  to ask about); otherwise `false`.

If the article is entirely fine, reply with exactly: `CORRECT: No fix needed`.

---

## Review instructions

Review the content of this article carefully for factual and medical/coding accuracy. Check whether this article has a proper topical category set, and if it's missing one, add the right category — do not replace existing categories, only append if needed from the existing categories in wordpress. If no suitable existing category exists, or the topic is ambiguous, don't guess, tell me and ask if you should apply it (flag as NEEDS_USER_VALUE: true). Apply tags in the same manner as categories. Also check if the internal/external links are broken or not. If something is wrong, report the correction (do NOT apply it in this pass; if the article is a draft, note it should be saved as a draft; if it's published, note the change targets the published article). If the article appears truncated or incomplete (missing sections like intro, FAQ, conclusion, documentation requirements, etc. compared to the full structure of similar articles on the same site), flag that as a publishing issue. Intro must exist. The proper structure is H1 > Key Takeaways > Intro > H2 > rest of the article. The only exception are template articles, where it's H1 > Key Takeaways > Download box (with built-in H2) > intro > H2 > rest of the article. If the article is a listicle, then ensure everyone is ranked fairly (do additional research, be completely objective (do not be fooled by the original framing of the article!), be completely unbiased, and then place every service in its appropriate order. For listicles, you can't actually access Capterra/G2/Trustpilot to fact check if the scores are correct, so always ask for the correct score for each service (flag each as NEEDS_USER_VALUE: true). For listicles DO NOT base your entire opinion around Capterra/G2/Trustpilot scores, as these are overall scores, whereas the listicle will always have a specific theme (the ranking must reflect the best fit for the purpose of the reader, not overall best for any purpose). [year] and %%currentyear%% are modifiers and apply the correct year on the front end (not a placeholder). Tell me if the content is correct or not. If the article is correct, just say "CORRECT: No fix needed" — this is a perfectly good answer. If it is not correct, give me a report on what you found, listing all issues in a numbered list. The report should specify exactly what is wrong, what the correct information is, and where in the article the fix needs to be applied.

Note: This is a newly published article or draft that may not yet be indexed by search engines. Fetch the URL directly and review the full article body content. Use a high token limit when fetching because the site has very large navigation menus that consume token space before the article body appears. You have full WordPress read access via the `wordpress-access` skill (SKILL.md) — but remember, in this pass you only READ.
