#!/usr/bin/env python3
"""A review loop's ledger (delegate §Review rounds): `<id> <label> <outcome>` lines, ids R<round>.<n> from a finding's first round,
and a line `Round: <N>` naming the last completed round, the larger of it and the highest id round. loops.close says whether it
closes its loop; loops.admit asks owed whether a code round may follow."""
import re
from typing import NamedTuple

LINE = re.compile(r'^[\s>*-]*`?(?:((?:[a-z][\w-]*:)?R(\d+)\.\d+)|[a-z][^\s`]*\d[^\s`]*)`?\s+`?(blocker|should|nit)`?:?(?=\s|$)\s*(.*?)\s*$', re.I)
ROUND = re.compile(r'^[\s>*-]*`?Round:\s*(\d+)', re.I | re.M)
FIXED = re.compile(r'fixed in ([0-9a-f]{7,40})\b')


class Row(NamedTuple):
    """A finding line: the line, its id R<round>.<n>, a post's second seat's first (`<seat>:R<round>.<n>`; None for an id of another
    form), its round, label and outcome."""
    line: str
    id: str
    round: int
    label: str
    outcome: str

    @property
    def fixed(self):
        """The sha of `fixed in <sha>`, else None."""
        return (m := FIXED.match(self.outcome)) and m[1]

    @property
    def confirmed(self):
        """The round N of a post's `fixed in r<N>`, else None."""
        return (m := re.match(r'fixed in r(\d+)\b', self.outcome)) and int(m[1])

    @property
    def declined(self):
        return bool(re.match(r'declined:\s*\S', self.outcome))

    @property
    def listed(self):
        return bool(re.match(r'listed:\s*\S', self.outcome))


def rows(text):
    """Every finding line of text, as Rows."""
    return [Row(m[0].strip(), m[1], m[2] and int(m[2]), m[3].lower(), m[4]) for m in map(LINE.match, text.splitlines()) if m]


def read(path):
    """(its rows with an id R<round>.<n>, its finding lines with an id of another form, its completed round) of the ledger at path;
    raises OSError when it can't be read."""
    text = open(path, errors='replace').read()
    found = rows(text)
    named = [r for r in found if r.id]
    return named, [r.line for r in found if not r.id], max([r.round for r in named] + [int(n) for n in ROUND.findall(text)], default=0)


def owed(rows, n, on_head):
    """What earns a code loop its next round after round n: 'fixed' when it brought a blocker or should `fixed in <sha>` with
    on_head(sha), else 'declined' when it brought a blocker `declined: <why>` and isn't itself the round a declined blocker went
    back in: a declined blocker goes back to its seat once, and one the round after still holds is Stuck (delegate §Review rounds), else ''."""
    sends = lambda m: m >= 1 and any(r.round == m and r.label == 'blocker' and r.declined for r in rows) and not sends(m - 1)
    return 'fixed' if any(r.round == n and r.label != 'nit' and r.fixed and on_head(r.fixed) for r in rows) else 'declined' if sends(n) else ''
