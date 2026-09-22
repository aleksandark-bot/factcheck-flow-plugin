# `clusters-data` — the central cluster store

This branch is **data, not code**. It carries one file tree and nothing else:

    clusters/base.jsonl         the canonical snapshot, one JSON object per post, sorted by url
    clusters/clusters.json      the cluster definitions (id, name, tier, pillar, hubs, subclusters)
    clusters/review-queue.json  the retirement / reassign bucket
    clusters/additions.jsonl    append-only assignments made since the last consolidation
    clusters/snapshots/         one <user>.jsonl per teammate, their local sheet normalized
    clusters/MANIFEST.json      version, built date, row counts, sha256 of base.jsonl
    clusters/CONTRACT.md        the binding data contract — read this first

It is an **orphan** branch: its history shares no commit with `main`. That is deliberate.
`update.sh` gates its fetch of prompts, guides and `bin/*.py` on main's commit SHA, so if
assignment pushes landed on main the updater would fire on every push and clobber a
teammate's uncommitted local edits. Data syncs gate on this branch's SHA instead, recorded
in `~/.claude/factcheck-flow/.last-clusters-sha`, independently of main.

## Reading it

Never parse these files by hand. `bin/cluster_store.py` on `main` owns the read path:

```python
from cluster_store import normalize_url, load_store, effective_cluster
store = load_store()                       # merges base + additions + snapshots + local xlsx
store["posts"][normalize_url(url)]["cluster_id"]
```

`load_store()` applies the precedence in CONTRACT.md (human > spreadsheet > interlinking-v4 >
reasoned; between two reasoned rows the earliest `assigned_at` wins), records every
disagreement in `meta["collisions"]` rather than dropping it, caches the merge on the
(mtime, size) of every input, and never raises — a missing or corrupt file degrades to
whatever else is on disk and says so in `meta["warnings"]`.

## Writing to it

Assignments are appended to `clusters/additions.jsonl` by `bin/cluster_sync.py push`, which
drains the local queue at `~/.claude/factcheck-flow/cluster-queue.jsonl` through the GitHub
Contents API. The queue is written before the network is touched, so a dead token costs
nothing. Never hand-edit `base.jsonl`: David's workbook
(`~/Desktop/pabau-content-clusters.xlsx`) is the authoring surface, and
`python3 bin/cluster_store.py export --out clusters/` regenerates the snapshot from it.

`base.jsonl` is deterministic — sorted by url, contract key order — so two exports of the
same workbook diff to nothing and a real assignment change is visible in the diff.

## Provenance of this seed

Built from `pabau-content-clusters.xlsx` by `bin/cluster_store.py export`. Every one of the
Posts sheet's 18 columns is mapped into the row schema; nothing is dropped. Rows whose
`Silo source` cell was empty are recorded as `spreadsheet`; the rest keep the sheet's own
value. `MANIFEST.json` carries the row counts, the sha256 of `base.jsonl` and the sha256 of
the workbook it came from.
