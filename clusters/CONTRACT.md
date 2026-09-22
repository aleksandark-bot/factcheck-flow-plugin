# The central cluster store — data contract

Status: v1, 2026-09-22. This file is the agreement every piece of the system builds against.
Change it here first, then change the code.

## Why this exists

Cluster assignment used to live in exactly one place: `~/Desktop/pabau-content-clusters.xlsx`
on David's Desktop. It was never shipped to the team — `update.sh` fetches prompts, guides,
commands, agents and `bin/*.py`, but never the workbook. So a teammate's link pass either
blocked on `LINKPLAN_BLOCKED — cluster spreadsheet not found` or ran off a hand-copied sheet
that drifted from the day they copied it. And when an agent reasoned a cluster for an article
published after the snapshot, that reasoning was thrown away at the end of the run.

This store fixes both: one canonical copy everyone reads, and reasoned assignments written
back so nobody re-guesses the same article twice.

## Where it lives

Repo `aleksandark-bot/factcheck-flow-plugin`, branch **`clusters-data`** (NOT `main`).

    clusters/base.jsonl         the canonical snapshot, one JSON object per post, sorted by url
    clusters/clusters.json      the cluster definitions (id, name, tier, pillar, hubs, subclusters)
    clusters/review-queue.json  the retirement / reassign bucket
    clusters/additions.jsonl    append-only new assignments since the last consolidation
    clusters/snapshots/<user>.jsonl   one per teammate, their local sheet normalized (for consolidation)
    clusters/MANIFEST.json      version, built date, row counts, and digests — see MANIFEST below

The data branch is separate from `main` on purpose. `update.sh` gates its main-branch fetch on
main's commit SHA; if assignment pushes advanced main, the updater would fire on every push and
clobber anyone's uncommitted local prompt edits. Data syncs gate on the `clusters-data` SHA
recorded in `~/.claude/factcheck-flow/.last-clusters-sha`, independently.

## Row schema (base.jsonl, additions.jsonl, snapshots/*.jsonl)

One JSON object per line, no trailing commas, UTF-8, `\n` endings. Keys, in this order:

    url              string   REQUIRED. Canonical form: https://pabau.com/<folder>/<slug>/ with
                              trailing slash, lowercased host+path, no query, no fragment.
                              This is the primary key. Normalize before comparing, always.
    title            string
    cluster          string   REQUIRED except on a deliberately unassigned row. The cluster
                              NAME as it appears in clusters.json ("Med Spa & Aesthetics"),
                              not the id. 60 rows (the regional /ae/, /au/ … pages, rule R0b)
                              legitimately carry "". They are kept, counted in
                              MANIFEST.counts.unassigned, and never guessed at.
    cluster_id       string   REQUIRED on the same terms. The slug id ("med-spa-aesthetics").
    tier             string   "Tier 1 — Industry" etc. DERIVED from clusters.json via the
                              cluster. The workbook's own Tier column is advisory: it agrees
                              on all 7,600 rows today, and a mismatch is a warning, not an
                              override.
    subcluster       string
    published        string   ISO date "2026-04-16" or "".
    rule_applied     string   the rule that produced the assignment ("R4 industry")
    secondary_tag    string
    flag             string   "Rule-2 candidate — vendor roundup" etc. Never re-litigated.
    note             string
    wp_categories    string   semicolon-separated, as the sheet holds it
    source_sheet     string   the old cluster name, for provenance
    intent           string   TOFU | MOFU | BOFU | JTBD | ""
    silo_source      string   REQUIRED. See PROVENANCE below.
    depth_target     int|null
    depth_current    int|null  the workbook holds the string "no path" on 1,169 rows. Emit null
                              and preserve the original in `depth_current_raw`.
    in_scope         string   "yes" | "no" | ""
    exclusion        string   why not in scope. Also carries the absence marker: a url no live
                              source holds is stamped
                              "ABSENT since <ISO date> — no live source holds this url"
                              so a workbook round-trip cannot silently clear it.
    absent_since     string   ISO date, set when a url stops appearing in every live source.
                              Rows are marked, never deleted.
    assigned_by      string   REQUIRED on reasoned rows: the $USER or configured handle
    assigned_at      string   REQUIRED on reasoned rows: ISO 8601 UTC "2026-09-22T11:46:00Z"
    evidence         object   REQUIRED on reasoned rows. See EVIDENCE below.

Rows read from the workbook carry the sheet's own values and omit the last three keys.
Absent optional keys are equivalent to "" (or null for the int fields). Consumers must not
crash on an unknown key — forward compatibility is a requirement, not a nicety.

## PROVENANCE — `silo_source`

`silo_source` is an OPEN vocabulary, not an enum. The workbook already carries 13 distinct
values across its 7,600 rows (only 5,136 say `spreadsheet`; 1,955 say `assigned:high|medium|low`,
the rest are the interlinking-v4 script's own rule labels like `R3 nearest-neighbour vote`).
The literal string always passes through unchanged. What matters is the AUTHORITY it maps to:

    authority 3  "human"                    a human assignment made directly in the store
    authority 2  "spreadsheet"              a human assignment from the original workbook
    authority 1  anything else              machine-assigned: the interlinking-v4 labels, and
                                            any future label nobody has taught the code about
    authority 0  "reasoned"                 an agent resolved it from `suggest` during a run

An unrecognized label ranks at authority 1, never higher. That is the safe direction: a machine
label nobody anticipated can never outrank a human assignment.

Precedence when the same url appears more than once: highest authority wins. Within authority 0,
the earliest `assigned_at` wins. Within any other authority, where two rows genuinely disagree,
the tie-break is by SOURCE STREAM, in this order:

    local workbook  >  base.jsonl  >  additions.jsonl

and the disagreement is ALWAYS recorded as a `conflict` collision for the report. The tie-break
exists so the code is deterministic, not because it settles anything — an equal-authority
disagreement is a question for David, and the report is where it gets asked.

Snapshots are NOT in this list. See SNAPSHOTS below.

Rule: a `reasoned` row NEVER overwrites a row of higher authority. An agent that resolves a
cluster for a url already carrying a human or spreadsheet assignment has made an error —
the sheet is the source of truth and is never re-litigated (`3-links.md` §0). The store
records the collision in the conflict report instead of applying it.

First writer wins among reasoned rows keeps the store stable: a url does not flip cluster
because two people happened to run /fact on it in the same week.

## EVIDENCE — what a reasoned row must carry

    "evidence": {
      "top_matches": [ {"url": "...", "cluster": "...", "subcluster": "...", "score": 0.42}, ... ],
      "tally":       [ {"cluster": "...", "subcluster": "...", "n": 7}, ... ],
      "top_score":   0.42,
      "title_used":  "the H1 the agent passed to suggest",
      "terms_used":  "the --terms string, or ''"
    }

At most 8 matches and 5 tally entries — this is an audit trail, not a dataset. Evidence is
what lets David confirm or overturn an assignment months later without re-running anything.

## MANIFEST.json — pinned shape

Readers verify downloads against this, so its shape is part of the contract, not an
implementation detail:

    {
      "version":       1,
      "built":         "2026-09-22T11:46:00Z",
      "source":        "pabau-content-clusters.xlsx",
      "source_sha256": "<digest of the workbook the export came from>",
      "counts":        {"posts": 7600, "clusters": 21, "review": 125, "unassigned": 60},
      "by_silo_source": {"spreadsheet": 5136, "assigned:high": ..., ...},
      "sha256":        {"base.jsonl": "<digest>", "clusters.json": "<digest>", ...}
    }

MANIFEST.json is written by `cluster_store.py export` and by `cluster_consolidate.py`, and is
READ-ONLY to `cluster_sync.py` — sync verifies downloads against it and never rewrites it.
One writer per file, always.

`sha256` is a MAP of filename to digest, and it is the authoritative one. A reader verifies
every file the map names and refuses a torn download. `built` changes on every export, so an
export with no assignment change still produces a non-empty diff — accepted, since the digests
are what actually tell you whether anything moved.

## Authority is a RANK, and lower is stronger

`cluster_store.authority_of(row)` returns 0 for `human`, 1 for `spreadsheet`, 2 for any
unrecognized label, 3 for `reasoned`. Lower wins. The prose above talks about "highest
authority" in plain English; the code compares ranks with `<=`. Always call `authority_of()` —
never hard-code a number and never invert the comparison by hand. A sign error here silently
lets machine rows overwrite human ones, which is the one thing this system must never do.

## Read path

Effective assignment for a url =
    merge(base.jsonl, additions.jsonl, local xlsx if present) under the precedence above.

The local workbook, where one exists (`$PABAU_CLUSTERS_XLSX`, default
`~/Desktop/pabau-content-clusters.xlsx`), is treated as `spreadsheet`-authority rows and wins
over anything reasoned. This keeps David's authoring workflow exactly as it is: he edits the
workbook, and the workbook still beats the network.

Readers cache the merged index under `~/.claude/factcheck-flow/cache/`, keyed on the
(mtime, size) of every input, so a refreshed input invalidates the cache automatically. That
is the existing `cluster_lookup.py` cache behavior and it does not change.

## Write path

1. The link pass resolves a cluster by reasoning for a url with no row (`3-links.md` §0).
2. It calls `cluster_sync.py submit` with the url, cluster, subcluster and the `suggest`
   output that justified it. (`cluster_lookup.py submit` exists as a thin alias so the link
   pass has one entry point, but the implementation lives in cluster_sync.)
3. `submit` appends the row to `~/.claude/factcheck-flow/cluster-queue.jsonl` — always, first,
   before any network call. The queue is the durable record; the network is best-effort.
4. `cluster_sync.py push` drains the queue into `clusters/additions.jsonl` on the data branch.
   The naive "GET the file and its blob sha from the Contents API" does NOT work here: that
   endpoint refuses content above 1 MB and `base.jsonl` is already 4.6 MB. So:
     - the blob sha comes from the Contents API DIRECTORY listing (which carries a sha at any
       size),
     - the content comes from raw.githubusercontent PINNED TO THE HEAD COMMIT SHA, not to the
       branch ref — the branch ref is CDN-cached for minutes and will serve you a stale file,
     - the PUT carries the listing's sha.
   Append only rows not already present (dedupe on normalized url) and never overwrite an
   existing row. On a sha conflict, re-fetch and re-merge — never force — up to 5 times with
   backoff.
   Dedupe is against `additions.jsonl` only. A reasoned row whose url already has a
   lower-authority row in `base.jsonl` is still appended, on purpose: consolidation wants to
   see that collision and decide it.
5. Rows that make it up are removed from the local queue. Rows that don't stay queued and go
   up on the next run that has a working token. Nothing is ever lost to a missing token.

A push with no token is not an error. It is a no-op that leaves the queue intact and says so.

## Token

    $PABAU_CLUSTERS_TOKEN, else ~/.claude/factcheck-flow/.clusters-token (chmod 600)

A fine-grained PAT scoped to this repo with contents:write. It is NEVER embedded in
`install.sh` or any other file in this repo — the repo is public. `install.sh` prompts for it
and writes it to that path; `.gitignore` covers it.

## Consolidation

`bin/cluster_consolidate.py`, run by David, folds everything into a new base:

    inputs   base.jsonl + additions.jsonl + snapshots/*.jsonl + the local workbook
    outputs  a new base.jsonl (additions truncated, snapshots consumed)
             a conflict report: every url where two sources disagree, with both assignments,
             both provenances and the evidence behind any reasoned one
             a regenerated workbook view, so David keeps editing a spreadsheet

Conflicts are reported, never silently resolved, whenever two rows of EQUAL authority disagree.
Unequal authority resolves by precedence and is reported as informational only.

## SNAPSHOTS — consolidation input only, never a read-path source

`clusters/snapshots/*.jsonl` are NOT merged by `load_store` and never affect what an agent
resolves during a run. They are input to `cluster_consolidate.py` and nothing else.

The reason is the whole point of the snapshot: it is one teammate's possibly-stale,
possibly-hand-edited workbook. Merging it into the read path would let a stale local copy win
over canonical at equal authority and quietly propagate one person's drift to everyone — the
exact failure this system exists to end. A snapshot's claims reach `base.jsonl` only by passing
through consolidation and David's judgment.

## Snapshot adoption — consolidating what everyone already has

A teammate running the upgraded tooling for the first time with a local workbook that differs
from `base.jsonl` exports it to `clusters/snapshots/<user>.jsonl` and pushes it once. That is
how the divergent per-device copies get pulled back together: consolidation reads every
snapshot, diffs it against base, and surfaces any assignment a teammate has that the canonical
store does not — as a conflict-report row for David, not as an automatic write.

One file per user means two teammates adopting at the same moment touch different paths and
can never conflict.

A snapshot's rows keep the workbook's OWN `silo_source` values. They are never restamped as
`spreadsheet` wholesale: roughly 2,460 of them carry machine labels, and promoting those to
human authority because they happened to arrive in a human's workbook is exactly the
overwrite this contract forbids.

## Non-negotiables

- The url is the key, and it is normalized before every comparison. A trailing-slash mismatch
  silently forking a row is the single most likely way this system rots.
- Nothing ever deletes a row. Rows for dead urls are marked, never removed — the
  interlinking-v4 script already established this and consolidation keeps it.
- A human assignment is never overwritten by a machine one. Ever.
- Every write is append-then-push, never push-then-append: the local queue is written before
  the network is touched, so a crash or a dead token costs nothing.
- Fail-silent on the read path. A network failure, a rate limit or a missing token must never
  block a /fact run — it falls back to whatever is on disk and says so in the report.
