#!/usr/bin/env python3
"""A review loop's ledger (delegate §Review rounds): `<id> <label> <outcome>` lines, ids R<round>.<n> from a finding's first round,
and a line `Round: <N>` naming the last completed round, the larger of it and the highest id round. loops.close says whether it
closes its loop; loops.admit asks last_round whether a code round may follow."""
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


def fixed_in(rows, n):
    """Whether round n brought a blocker or should `fixed in <sha>`: only such a round earns a code loop its next round."""
    return any(int(m[1]) == n and m[2].lower() != 'nit' and FIXED.match(m[3]) for m in rows)


def last_round(path):
    """(the ledger's completed round, whether it brought a blocker or should `fixed in <sha>`)."""
    rows, _, last = read(path)
    return last, fixed_in(rows, last)
