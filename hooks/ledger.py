#!/usr/bin/env python3
"""A review loop's ledger (delegate §Review rounds): `<id> <label> <outcome>` lines, ids R<round>.<n> from a finding's first round,
and a line `Round: <N>` naming the last completed round, the larger of it and the highest id round. loops.close says whether it
closes its loop; loops.admit asks owed whether a code round may follow."""
import re

LINE = re.compile(r'^[\s>*-]*`?(?:R(\d+)\.\d+|[a-z][^\s`]*\d[^\s`]*)`?\s+`?(blocker|should|nit)`?:?(?=\s|$)\s*(.*?)\s*$', re.I)
ROUND = re.compile(r'^[\s>*-]*`?Round:\s*(\d+)', re.I | re.M)
FIXED = re.compile(r'fixed in ([0-9a-f]{7,40})\b')


def read(path):
    """(its rows, every finding line, its completed round) of the ledger at path; raises OSError when it can't be read."""
    text = open(path, errors='replace').read()
    lines = [m for m in map(LINE.match, text.splitlines()) if m]
    rows = [m for m in lines if m[1]]
    return rows, lines, max([int(m[1]) for m in rows] + [int(n) for n in ROUND.findall(text)], default=0)


def owed(rows, n, on_head):
    """What earns a code loop its next round after round n: 'fixed' when it brought a blocker or should `fixed in <sha>` with
    on_head(sha), else 'declined' when it brought a blocker `declined:`, which goes back to its seat once (delegate §Stuck), else ''."""
    of_n = [m for m in rows if int(m[1]) == n]
    return 'fixed' if any(m[2].lower() != 'nit' and (f := FIXED.match(m[3])) and on_head(f[1]) for m in of_n) else \
        'declined' if any(m[2].lower() == 'blocker' and m[3].startswith('declined:') for m in of_n) else ''
