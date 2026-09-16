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

**Before anything else, run the truncation / repetition check (see "Truncation or
repetition" below).** If it trips, reply with the single line
`REWRITE_REQUIRED: <one-line reason>` and nothing else — no findings, no other text.
That signal makes the orchestrator rewrite the article and re-run the entire /fact
process on it, with no human triage.

Otherwise, return your findings in **two buckets**. Almost every finding is applied
automatically without a human ever reading it, so only the small "needs a human" bucket
gets the full seven-field form. Writing the long form for every finding costs the
orchestrator a large context for no decision.

### Bucket 1 — `AUTO` (applied without asking)

Everything of type `factual`, `Pabau-fact`, `link`, `publishing`, `missing-section`, or
`code-state`, plus any `listicle-rank` change that does NOT move Pabau's own position.
**One line each**, numbered, in this exact shape:

```
AUTO 1. <type> | <location> | <what is wrong> → <the correct value / the change to make>
```

Keep each line to about 30 words. No labelled sub-lines, no evidence, no reasoning — the
editor applies these as written.

### Bucket 2 — `ASK` (the human decides)

Only two kinds of finding reach a human, and they are the only ones that get the long
form. For EACH, include these labelled lines:

- `LOCATION:` where in the article the fix applies (section heading / paragraph / link anchor)
- `TYPE:` `factual` or `listicle-rank`
- `ISSUE:` exactly what is wrong
- `CORRECT:` the correct information / value
- `FIX:` the specific change to make
- `EVIDENCE:` what you checked and what it showed (an independent verifier reads this)
- `NEEDS_USER_VALUE:` `true` if this needs a value only the human can supply
  (e.g. correct Capterra/G2/Trustpilot score); otherwise `false`.
- `CONFIRM:` `true` if this fix must get the human's explicit sign-off before it is
  applied. Set it `true` in only two cases: (1) a **grave factual error** whose correction
  cannot be a simple in-place edit because it would require a full rewrite or rewriting
  large parts of the article (e.g. the central ICD/CPT code the whole article is built
  around is wrong) — report it as a `factual` finding with `CONFIRM: true`, and do NOT emit
  a bare `REWRITE_REQUIRED` for it; (2) a `listicle-rank` change that moves **Pabau's own
  position** up or down.

A finding belongs in bucket 2 only if `CONFIRM: true` or `NEEDS_USER_VALUE: true`.
Everything else goes in bucket 1, however important it feels.

If the article is entirely fine, reply with exactly: `CORRECT: No fix needed`.
If one bucket is empty, write the header and `(none)`.

## Blocks — do NOT audit them here

**You do not check the block contract.** The article-editor's final pass (Pass D) enforces
all of it unconditionally at the end of Stage 3 — Key takeaways, the template download box,
the Pabau section and its CTA block, the Conclusion, Continue your research, the Yoast FAQ
block, listicle pricing segments, and image captions. It locates and re-derives each one
from the raw markup regardless of what you say, so a block audit here is work that gets
redone twice and read by nobody. Skip it, and do not read `WordPress-blocks.md`.

**The exceptions — and these three are the ONLY absences you ever report,** each as a
`missing-section` line in bucket 1:

1. **A wholly missing FAQ**, where the article's type calls for one. Pass D deliberately never
   invents a missing FAQ — it only converts one that exists — so that gap has to be caught
   here or it ships. A malformed or non-Yoast FAQ is NOT your problem; Pass D converts it.
2. **Missing documentation requirements**, where the topic calls for them.
3. **The empty required `pdc_*` fields on a Broken templated code page** — see "The structural
   states you REPORT and do not fix" below.

Nothing else that is absent is reported: Pass D adds every other block-contract section
unconditionally in Stage 3.

Separately, any pricing figure you can trace to a third party (Capterra, G2, GetApp,
Software Advice, Trustpilot, a review round-up, another blog) instead of the provider's own
website is a `factual` finding with `CONFIRM: false` — give the provider's published figure
as `CORRECT`, or "Contact sales / no published pricing" when the vendor publishes none. For
Pabau's own pricing, pabau.com is the only acceptable source.

## Code pages — the `pdc_*` meta is in scope, and it is a FACTUAL check

On a **templated code page**, the whole area between the H1 and the first H2 — badge, H1,
flag line, **Code Definition**, **Related Information** — is rendered by a WordPress page
template from `pdc_*` post meta. **None of it lives in `post_content`**, so none of it is
visible in the WordPress editor and none of it comes back in `content.raw`. It is
page-visible, fact-checkable content, and checking it is yours.

**This does not reopen the block audit.** The section above still stands in full: you do not
check the block contract, and you do not read `WordPress-blocks.md`. The `pdc_*` values are
factual claims on a live page, verified exactly the way body claims are verified. That they
live in post meta rather than in the body changes only *how the editor applies the fix* —
not whose pass it belongs to. Nothing here asks you to judge document order, block presence,
or placement; the two checks do not overlap. (The contract itself is
`WordPress-blocks.md` §13, which the editor reads — you do not.)

**Detection:**

```
renders the code top area  ==  post.template is the code template
fully Templated            ==  that, AND all eight required pdc_* fields non-empty
```

The template alone decides whether the top area renders. The eight required fields then decide
whether it renders complete (**Templated**) or with blanks (**Broken**) — so a page missing
even `pdc_code` is Broken, not "not a code page", and everything in this section still applies
to it.

There is one code template, **`template-diagnostic-code.php`**, and it serves
`/diagnostic-codes/` and `/procedure-codes/` pages alike. The name is awkward on a procedure
page; it is still the only code template, so do not "correct" it. Key the check on `template` +
meta presence, **never on the URL folder** — the route never decides the state. Work through the
four states before concluding that a page is out of scope — only state 4 (no `template`, no
meta) leaves nothing in this section to do.

### The four states

Every code page is in exactly one of these, on either code route.

| # | `template` | `pdc_*` meta | State | What you do |
|---|---|---|---|---|
| 1 | `template-diagnostic-code.php` | all eight required fields present | **Templated** | Check the `pdc_*` values as factual claims, below. |
| 2 | `template-diagnostic-code.php` | one or more of the eight required fields empty | **Broken** | Check the values as above, and report the empty required fields as one `missing-section` line. |
| 3 | empty | any `pdc_*` set | **Half-migrated** | A defect. Check the body as a normal old-shape article and report it with a `code-state` line, below. |
| 4 | empty | none set | **Old shape** | Nothing in this section applies. |

Most procedure-code pages you meet are still old shape; nearly every diagnostic-code page is
templated.

A page whose `template` is set but is **not** the code template (`elementor_canvas`,
`elementor_header_footer`, `elementor_theme`,
`wp-templates/p-medical-certificate-generator.php`) does not render the code top area at all.
Check the body as old shape, report the `template` value, and do not try to fix it.

### The fields, and what "correct" means

**Eight are ALWAYS REQUIRED** — a templated page must carry all eight, and an empty one is a gap
to report: `pdc_code_type`, `pdc_code`, `pdc_descriptor`, `pdc_h1_descriptor`, `pdc_definition`,
`pdc_chapter`, `pdc_category`, `pdc_group`.

**Two are CONDITIONAL:** `pdc_billable` and `pdc_specific`. They are required, `yes` or `no`, on
an **ICD-10-CM** page. They are **left empty** where the code system has no billable/specific
distinction to report — the live HCPCS page J8650 has both empty, and empty is correct there,
never a gap. Empty values hide the "Billable Code • Specific Code" flag line under the H1 **and**
the "Billable" row in Related Information. Never propose `yes`/`no` for either one just to make a
page look complete.

**Five are OPTIONAL, and an empty one is never a finding.** `pdc_h1_prefix` is always left empty
— the template supplies the H1 prefix ("ICD code", "HCPCS code"). `pdc_also_known` is written
only when the authority names a genuine synonym for the code; empty is its normal, correct
state. `pdc_label_1`, `pdc_label_2` and `pdc_label_3` relabel the three Related Information rows
and stay empty unless a default label would be wrong (see below). Never propose a value for any
of the five to satisfy a completeness check.

| Field | What it feeds | Correct means |
|---|---|---|
| `pdc_code_type` | the badge | the right code system — `ICD-10-CM Code`, `CPT Code`, `HCPCS Code`, … |
| `pdc_code` | the H1 and the CTA mock | the code itself, dotted (`S65.419A`), and it is the code the article is actually about |
| `pdc_descriptor` | data behind the top area (not rendered directly) | the **official** descriptor, verbatim, including the 7th-character clause |
| `pdc_h1_descriptor` | the H1 after the dash, the CTA mock | a short plain-language descriptor — deliberately *not* the official text |
| `pdc_h1_prefix` | the H1 before the code | empty on every live page; the template supplies the prefix ("ICD code", "HCPCS code"). **Leave it alone.** |
| `pdc_billable` | flag line + a Related Information row | `yes` / `no`, matching the code's official billable status — or empty where the code system has no billable status to report |
| `pdc_specific` | flag line | `yes` / `no` — or empty where the code system has no specific/unspecified distinction |
| `pdc_definition` | the **Code Definition** block (this is the article's intro) | plain text, no HTML and no links, 1–2 paragraphs split by `\n\n`, and every claim in it true |
| `pdc_chapter` | Related Information row 1 | the first reference fact for this code system, true and official — `<range> <official chapter title>` on ICD |
| `pdc_category` | Related Information row 2 | the second reference fact, true and official — `<code> <official category title>` on ICD |
| `pdc_group` | Related Information row 3 | the third reference fact, true and official — `<code> <official group title>` on ICD |
| `pdc_label_1` / `_2` / `_3` | the labels on those three rows | empty (the template's default label for this code type), or an override that correctly describes the value beside it |
| `pdc_also_known` | an optional Related Information row | a genuine synonym for the code; the row is hidden when empty, and empty is fine |

**The three labelled rows are generic slots**, not literally "the chapter", "the category" and
"the group". They carry the three most useful reference facts for that code system: on the HCPCS
page J8650 they hold `Level II`, `J — Drugs administered other than oral method` and
`Deleted, effective 31 December 2025`. Their contents are factual claims and you check them like
any other.

`pdc_label_1/2/3` relabel those rows in that order — 1 → chapter, 2 → category, 3 → group. Empty
means "use the template's default label for this code type", which is right for the common cases:
an ICD-10-CM page with all three empty renders Chapter / Category / Group, and the HCPCS page
renders **Level** for row 1 with `pdc_label_1` empty. A label is set only to override a default
that would be wrong — J8650 sets `pdc_label_3` to `Status` because its `pdc_group` carries
"Deleted, effective 31 December 2025" rather than a code group. **Where a label IS set, check
it:** it is a claim about how to read that row, and it is wrong if it does not describe the value
beside it. Never propose blanking a label that is set, and never propose setting one to the value
the default would produce anyway.

**Verify against the official source, as you would any body claim:** the CDC/NCHS ICD-10-CM
tabular list for ICD codes, the AMA for CPT, CMS for HCPCS.

### How to report a meta finding

Use a `meta:<field>` location prefix, so the editor knows the fix is a meta write and not a
body edit:

```
AUTO 3. factual | meta:pdc_category | reads "S65 Injury of blood vessels at hand level" → "S65 Injury of blood vessels at wrist and hand level"
```

Severity:

- A wrong **`pdc_code`** is the grave-error case: the whole page is built on it. Report it as
  `factual` with `CONFIRM: true`, in the `ASK` bucket's long form (do **not** emit a bare
  `REWRITE_REQUIRED`).
- `pdc_descriptor`, `pdc_chapter`, `pdc_category`, `pdc_group`, `pdc_code_type`,
  `pdc_billable`, `pdc_specific`, and any `pdc_label_1/2/3` that is set — ordinary `factual`
  findings in the `AUTO` bucket.
- `pdc_definition` is prose: check its claims exactly like body prose.
- `pdc_h1_descriptor` and `pdc_also_known` are editorial, not official text — flag them only
  when they **contradict** the code.

Never propose deleting or blanking a `pdc_*` field or the `template` value. A blanked field
silently empties a section of the live page that nobody can see in the editor.

### The structural states you REPORT and do not fix

The later passes cannot infer these from the body, so they have to be caught here.

1. **Broken page** (state 2) — the code template is set and one or more of the eight required
   fields is empty, so the top area renders with blanks. Report it as a single
   `missing-section` line in the `AUTO` bucket, naming every **required** field that is empty
   and giving the value each should hold, e.g.
   `AUTO 4. missing-section | meta:pdc_chapter, meta:pdc_group | templated code page renders blank rows → set pdc_chapter "S00-T88 …", pdc_group "S65.419 …"`.
   An empty conditional field (`pdc_billable`, `pdc_specific`) or optional field
   (`pdc_h1_prefix`, `pdc_also_known`, `pdc_label_1/2/3`) is never part of that line and is
   never a finding.
2. **Half-migrated page** (state 3) — `pdc_*` meta is set and `template` is empty, on either
   code route. The meta is dead: the page renders the OLD
   layout and the values never reach a reader. Report it as an ordinary numbered `AUTO` line of
   type `code-state`, carrying the exact token `CODE_PAGE_HALF_MIGRATED` and the slug, e.g.
   `AUTO 5. code-state | meta | template empty but pdc_* populated (icd-10-code-t86859) → report CODE_PAGE_HALF_MIGRATED; do not fix`.
   It belongs inside the `AUTO` bucket like any other finding — **never as a bare token on its
   own line, and never outside the report.** **This is NOT to be fixed by the flow** — do not
   propose setting `template`, do not treat the meta as page content, and check the body as a
   normal old-shape article. It needs a separate migration process.

Equally, **never migrate an old-shape page**: do not propose setting `template`, do not
invent `pdc_*` values for a page that has none, and do not propose stripping a body intro
from a page that still needs one.

## Truncation or repetition → automatic rewrite (check this first)

Check whether the article is **truncated or broken** (the body cuts off mid-section or
mid-sentence, or so much is absent that the piece can't stand on its own) OR **repeats
itself** (duplicated sentences, paragraphs, or whole sections). Either problem means the
article can't be QA'd as-is; it needs a rewrite, not findings. When you detect it, reply
with exactly one line: `REWRITE_REQUIRED: <one-line reason>` (e.g. `REWRITE_REQUIRED:
body cuts off mid-sentence under the "Documentation requirements" H2`). Do not list any
other findings — a fresh /fact run happens automatically after the rewrite.

A single expected section merely being **absent** from an otherwise-complete article
(no intro, no FAQ, no conclusion, etc.) is NOT a rewrite. Pass D adds the block-contract
sections automatically in Stage 3, so the only absences you report are the three listed under
"Blocks — do NOT audit them here".

---

## Review instructions

Review the content of this article carefully for factual and medical/coding accuracy. Also check the link status: whether the internal/external links are broken or not (this is the one link check that lives in this pass — the editorial/link stage handles redirects, nofollow, anchor text, counts, and replacements). Do NOT audit the block contract (see the section above); the only structural gaps you report are the three `missing-section` cases listed under "Blocks — do NOT audit them here". Do NOT flag Healthcode references that appear in images or image captions — the editorial step replaces those automatically, so there is no need to report them. If something is wrong, report the correction (do NOT apply it in this pass; if the article is a draft, note it should be saved as a draft; if it's published, note the change targets the published article). If the article is a listicle, then ensure everyone is ranked fairly (do additional research, be completely objective (do not be fooled by the original framing of the article!), be completely unbiased, and then place every service in its appropriate order. If your fair re-ranking moves **Pabau itself** up or down from where the article currently ranks it, flag that specific finding with `CONFIRM: true` — the human signs off on Pabau's own position, while the re-ordering of every other service applies automatically. For listicles, you can't actually access Capterra/G2/Trustpilot to fact check if the scores are correct, so always ask for the correct score for each service (flag each as NEEDS_USER_VALUE: true). For listicles DO NOT base your entire opinion around Capterra/G2/Trustpilot scores, as these are overall scores, whereas the listicle will always have a specific theme (the ranking must reflect the best fit for the purpose of the reader, not overall best for any purpose). [year] and %%currentyear%% are modifiers and apply the correct year on the front end (not a placeholder). Tell me if the content is correct or not. If the article is correct, just say "CORRECT: No fix needed" — this is a perfectly good answer. If it is not correct, give me a report on what you found, listing all issues in a numbered list. The report should specify exactly what is wrong, what the correct information is, and where in the article the fix needs to be applied.

Note: This is a newly published article or draft that may not yet be indexed by search engines, so don't rely on a search index to read it.

**Fetch it ONCE, via the REST API, using the `wordpress-access` skill (SKILL.md)** — with `context=edit` and that skill's `_fields=` list, which already carries `template` and `meta`; use it as-is rather than typing your own field list, and confirm both came back. Without them the code-page check above silently reads as "not templated". Do NOT WebFetch the public URL: the site's navigation and footer are very large and would eat most of the response before the body appears, which is why older versions of this prompt told you to raise the token limit. The REST response has no nav in it, so the workaround is unnecessary. In this pass you only READ — no PUT, no POST.
