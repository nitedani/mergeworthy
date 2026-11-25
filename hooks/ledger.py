#!/usr/bin/env python3
"""ledger.py [--post] <ledger> [<checkout>]: exits 0 when a review loop's ledger (delegate §Review rounds: `<id> <label> <outcome>`, ids
R<round>.<n> from a finding's first round, and a line `Round: <N>` naming the last completed round) closes a round 2 or later whose
verdict wasn't clean: the completed round is the larger of `Round: <N>` and the highest id round, each finding of every round is
`fixed in <sha>` with the sha in the checkout's HEAD history, `declined: <why>` or `listed: <where>`, and no blocker of any round
is listed or open; a row whose id (a word starting with a letter, with a digit) isn't R<round>.<n> stands too. With --post
(gate-pass) `fixed in r<N>`, a later round up to the completed one that confirmed the fix, closes a finding too. Without it,
`fixed in <draft>.md` (ledger-relative) closes a finding while <draft>.md.gate's first line is its current sha256.
`fixed in`'s word, less trailing `.,;:)`, is one form: .md, else sha, else r<N>. Used by pr-steps and gate-pass (`--ledger`);
else it prints what stands and exits 1."""
import hashlib, os, re, subprocess, sys

LINE = re.compile(r'^[\s>*-]*`?(?:R(\d+)\.\d+|[a-z][^\s`]*\d[^\s`]*)`?\s+`?(blocker|should|nit)`?:?(?=\s|$)\s*(.*?)\s*$', re.I)
ROUND = re.compile(r'^[\s>*-]*`?Round:\s*(\d+)', re.I | re.M)


def gated(draft):
    try: return hashlib.sha256(open(draft, 'rb').read()).hexdigest() == open(draft + '.gate').read().split('\n')[0].strip()
    except OSError: return False


def problems(path, checkout='.', post=False):
    fix = 'fixed in r<N>' if post else 'fixed in <sha>'
    try: text = open(path, errors='replace').read()
    except OSError as e: return [f'{path}: {e.strerror}']
    lines = [m for m in map(LINE.match, text.splitlines()) if m]
    rows = [m for m in lines if m[1]]
    misnamed = [f'{m[0].strip()}  <- its id is not R<round>.<n>' for m in lines if not m[1]]
    if not rows: return misnamed + [f"{path} has no '<id> <label> <outcome>' lines (R<round>.<n> blocker|should|nit {fix}|declined: <why>|listed: <where>)"]
    last = max(int(n) for n in [m[1] for m in rows] + ROUND.findall(text))
    out = misnamed + ([] if last >= 2 else [f'{path} closes round {last}: a verdict that is not clean gets round 2 first'])
    for m in rows:
        op = (o := re.match(r'fixed in (\S+)', m[3])) and o[1].rstrip('.,;:)')
        body = fixed = confirmed = None
        if op and op.endswith('.md'): body = not post and os.path.join(os.path.dirname(path), op)
        elif op and re.fullmatch(r'[0-9a-f]{7,40}', op): fixed = op
        elif op and post and (r := re.fullmatch(r'r(\d+)', op)): confirmed = int(m[1]) < int(r[1]) <= last
        closed = confirmed or body and gated(body) or fixed and subprocess.run(['git', '-C', checkout, 'merge-base', '--is-ancestor', fixed, 'HEAD'], capture_output=True).returncode == 0
        if body and not closed:
            out.append(f'{m[0].strip()}  <- {op} has no gate-pass record of its current text')
        elif fixed and not closed:
            out.append(f'{m[0].strip()}  <- {fixed} is not in HEAD\'s history')
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
