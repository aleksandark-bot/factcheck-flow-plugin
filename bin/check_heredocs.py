#!/usr/bin/env python3
"""install.sh embeds copies of files that also exist in this repo. Prove they still match.

THE TRAP THIS EXISTS TO CLOSE
-----------------------------
`install.sh` is a single self-contained script: a fresh machine runs it straight off a curl
with nothing checked out, so it cannot `cp` from a repo it does not have. Several files are
therefore written out of it as heredocs — `update.sh`, the `/fact` command, two agents and
the wordpress-access skill — while the SAME files also live in the repo as the canonical
copies the auto-updater fetches.

Edit the canonical file and nothing tells you the heredoc still holds the old bytes. The
repo keeps building, every test keeps passing, and the only symptom is that a teammate who
installs fresh silently gets the previous version — until their first session, when the
updater overwrites it and the bug evaporates before anyone can see it. It has bitten before.

So: after touching any file listed in EMBEDDED below, run

    python3 bin/check_heredocs.py            # report
    python3 bin/check_heredocs.py --fix      # rewrite the heredocs from the canonical files

Exit 0 when every heredoc matches its file, 1 when any differs, 2 on a structural problem
(a marker that moved, a heredoc that is no longer where this script expects it). All three
are meaningful in CI: 2 means this checker needs updating, not that the files are wrong.

HOW A BLOCK IS FOUND
--------------------
By its opening line, verbatim — `cat > "$DEST" <<'MARKER'` — and then to the first line
that is exactly MARKER. Quoted markers (<<'EOF') mean the shell does no expansion inside,
so the bytes between are the file's bytes and a byte comparison is the right comparison.
An UNQUOTED marker (<<EOF) would interpolate `$var` and backticks, so this script refuses
to treat such a block as a copy of a file — the CLAUDE.md block near the end of install.sh
is one of those, is not a copy of any repo file, and is deliberately not listed here.
"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)

# (opening line in install.sh, marker, canonical file relative to the repo root)
EMBEDDED = [
    ('cat > "$FF/update.sh" <<\'UPDATESH\'', "UPDATESH", "update.sh"),
    ('cat > "$CLAUDE/commands/fact.md" <<\'EOF\'', "EOF", "commands/factcheck-flow.md"),
    ('cat > "$CLAUDE/agents/factcheck-reporter.md" <<\'EOF\'', "EOF",
     "agents/factcheck-reporter.md"),
    ('cat > "$CLAUDE/agents/article-editor.md" <<\'EOF\'', "EOF", "agents/article-editor.md"),
    ('cat > "$CLAUDE/skills/wordpress-access/SKILL.md" <<\'EOF\'', "EOF",
     "skills/wordpress-access/SKILL.md"),
]

INSTALL = os.path.join(REPO, "install.sh")


class Structural(Exception):
    pass


def find_block(lines, opener, marker):
    """-> (start, end): the heredoc body is lines[start:end], marker line is lines[end]."""
    hits = [i for i, l in enumerate(lines) if l.rstrip("\n") == opener]
    if not hits:
        raise Structural("no line in install.sh reads exactly:\n    %s" % opener)
    if len(hits) > 1:
        raise Structural("%d lines in install.sh read exactly %r — this checker cannot tell "
                         "which heredoc is which" % (len(hits), opener))
    start = hits[0] + 1
    for j in range(start, len(lines)):
        if lines[j].rstrip("\n") == marker:
            return start, j
    raise Structural("heredoc opened at line %d by %r is never closed by a line reading "
                     "exactly %r" % (hits[0] + 1, opener, marker))


def check(fix=False):
    with open(INSTALL, encoding="utf-8") as fh:
        lines = fh.readlines()

    results = []
    edits = []
    for opener, marker, rel in EMBEDDED:
        path = os.path.join(REPO, rel)
        try:
            start, end = find_block(lines, opener, marker)
        except Structural as e:
            results.append((rel, "STRUCTURE", str(e), None))
            continue
        if not os.path.exists(path):
            results.append((rel, "STRUCTURE", "canonical file is missing: %s" % path, None))
            continue
        with open(path, encoding="utf-8") as fh:
            want = fh.readlines()
        have = lines[start:end]
        if have == want:
            results.append((rel, "OK", "%d lines, byte-identical" % len(want),
                            (start, end)))
        else:
            results.append((rel, "DIFFERS", _summary(have, want), (start, end)))
            edits.append((start, end, want))

    if fix and edits:
        # Apply back to front so earlier offsets stay valid.
        for start, end, want in sorted(edits, reverse=True):
            lines[start:end] = want
        with open(INSTALL, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
    return results, edits


def _summary(have, want):
    import difflib
    sm = difflib.SequenceMatcher(None, have, want)
    add = rem = 0
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag in ("replace", "delete"):
            rem += i2 - i1
        if tag in ("replace", "insert"):
            add += j2 - j1
    first = next((i for i, (a, b) in enumerate(zip(have, want)) if a != b), min(len(have),
                                                                               len(want)))
    return ("embedded %d lines, file has %d; %d removed / %d added; first difference at "
            "body line %d" % (len(have), len(want), rem, add, first + 1))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--fix", action="store_true",
                    help="rewrite every stale heredoc from its canonical file")
    a = ap.parse_args()

    results, edits = check(fix=a.fix)
    if a.fix and edits:
        results, edits = check(fix=False)  # re-verify what we just wrote

    width = max(len(r[0]) for r in results)
    bad = struct = 0
    for rel, verdict, detail, _span in results:
        print("%-8s %-*s  %s" % (verdict, width, rel, detail))
        if verdict == "DIFFERS":
            bad += 1
        elif verdict == "STRUCTURE":
            struct += 1

    print("")
    if struct:
        print("%d heredoc(s) could not be located in install.sh. Fix bin/check_heredocs.py "
              "(or the markers) before trusting this result." % struct)
        return 2
    if bad:
        print("%d heredoc(s) in install.sh are STALE. A fresh install would ship the old "
              "file. Run:  python3 bin/check_heredocs.py --fix" % bad)
        return 1
    print("All %d embedded heredocs match their canonical files." % len(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
