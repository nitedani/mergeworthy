#!/usr/bin/env python3
"""ledger.py [--post] <ledger> [<checkout>]: exits 0 when a review loop's ledger (delegate §Review rounds: `<id> <label> <outcome>`, ids
R<round>.<n> from a finding's first round, and a line `Round: <N>` naming the last completed round) closes its loop: the completed
round is the larger of `Round: <N>` and the highest id round, each finding of every round is `fixed in <sha>` with the sha in the
checkout's HEAD history, `declined: <why>` or `listed: <where>`, no blocker of any round is listed or open, and the completed round
brought no blocker or should `fixed in <sha>` or is round 4 or later; a row whose id (a word starting with a letter, with a digit)
isn't R<round>.<n> stands too. With --post (gate-pass: a post's draft has no sha) the completed round is round 2 or later instead,
and `fixed in r<N>`, a later round up to the completed one that confirmed the fix, closes a finding too. Used by pr-steps and
gate-pass (`--ledger`), and by loops.admit to refuse a code round after the last one (last_round); else it prints what stands
and exits 1."""
import re, subprocess, sys

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


def problems(path, checkout='.', post=False):
    fix = 'fixed in r<N>' if post else 'fixed in <sha>'
    try: rows, lines, last = read(path)
    except OSError as e: return [f'{path}: {e.strerror}']
    misnamed = [f'{m[0].strip()}  <- its id is not R<round>.<n>' for m in lines if not m[1]]
    if not rows: return misnamed + [f"{path} has no '<id> <label> <outcome>' lines (R<round>.<n> blocker|should|nit {fix}|declined: <why>|listed: <where>)"]
    if post: out = misnamed + ([] if last >= 2 else [f'{path} closes round {last}: a verdict that is not clean gets round 2 first'])
    else: out = misnamed + ([f'{path} closes round {last}, which brought a blocker or should fixed in a commit: the loop gets its next round first']
                            if last < 4 and fixed_in(rows, last) else [])
    for m in rows:
        fixed = FIXED.match(m[3])
        confirmed = post and (r := re.match(r'fixed in r(\d+)\b', m[3])) and int(m[1]) < int(r[1]) <= last
        closed = confirmed or fixed and subprocess.run(['git', '-C', checkout, 'merge-base', '--is-ancestor', fixed[1], 'HEAD'], capture_output=True).returncode == 0
        if fixed and not closed:
            out.append(f'{m[0].strip()}  <- {fixed[1]} is not in HEAD\'s history')
        elif m[2].lower() == 'blocker' and not closed and not m[3].startswith('declined:'):
            out.append(f'{m[0].strip()}  <- an open blocker keeps the PR in draft')
        elif not closed and not re.match(r'(declined|listed):\s*\S', m[3]):
            out.append(f'{m[0].strip()}  <- not {fix}, declined: <why> or listed: <where>')
    return out


if __name__ == '__main__':
    post = sys.argv[1:2] == ['--post']
    found = problems(*sys.argv[1 + post:3 + post], post=post)
    if found:
        print('the ledger leaves this round open (mergeworthy:delegate §Review rounds):\n' + '\n'.join(found), file=sys.stderr)
    sys.exit(1 if found else 0)
