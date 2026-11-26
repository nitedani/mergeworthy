#!/usr/bin/env python3
"""A review loop's ledger (delegate §Review rounds): `<id> <label> <outcome>` lines, ids R<round>.<n> from a finding's first round,
and a line `Round: <N>` naming the last completed round, the larger of it and the highest id round. loops.close says whether it
closes its loop; loops.admit asks owed whether a code round may follow."""
import hashlib, re
from typing import NamedTuple

LINE = re.compile(r'^[\s>*-]*`?(?:((?:[a-z][\w-]*:)?R(\d+)\.\d+)|[a-z][^\s`]*\d[^\s`]*)`?\s+`?(blocker|should|nit)`?:?(?=\s|$)\s*(.*?)\s*$', re.I)
ROUND = re.compile(r'^[\s>*-]*`?Round:\s*(\d+)', re.I | re.M)


class Row(NamedTuple):
    """A finding line: the line, its id R<round>.<n>, a post's second seat's first (`<seat>:R<round>.<n>`; None for an id of another
    form), its round, label and outcome."""
    line: str
    id: str
    round: int
    label: str
    outcome: str

    @property
    def fix(self):
        """`fixed in <word>`'s word less trailing `.,;:)`, one form: a draft's <path>.md, else a sha, else a post's r<N>; else None."""
        return (m := re.match(r'fixed in (\S+)', self.outcome)) and m[1].rstrip('.,;:)')

    @property
    def fixed(self):
        """The sha of `fixed in <sha>`, else None."""
        return (f := self.fix) and re.fullmatch(r'[0-9a-f]{7,40}', f) and f

    @property
    def confirmed(self):
        """The round N of a post's `fixed in r<N>`, else None."""
        return (f := self.fix) and (m := re.fullmatch(r'r(\d+)', f)) and int(m[1])

    @property
    def draft(self):
        """The path, relative to the ledger, of `fixed in <draft>.md`, else None."""
        return (f := self.fix) and f.endswith('.md') and f

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
    """Whether round n earns a code loop its next round: it brought a blocker or should `fixed in <sha>` with on_head(sha); a
    round whose findings were all declined, blockers included, ends the loop (delegate §Review rounds)."""
    return any(r.round == n and r.label != 'nit' and r.fixed and on_head(r.fixed) for r in rows)


def gated(draft):
    """Whether the first line of draft's gate-pass record (<draft>.gate) is the sha256 of its current text."""
    try: return hashlib.sha256(open(draft, 'rb').read()).hexdigest() == open(draft + '.gate').read().split('\n')[0].strip()
    except OSError: return False
