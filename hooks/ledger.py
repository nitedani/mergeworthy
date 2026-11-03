#!/usr/bin/env python3
"""ledger.py <ledger> [<checkout>]: exits 0 when a review loop's ledger (delegate §Review rounds: `<id> <label> <outcome>`, ids
R<round>.<n> from a finding's first round, and a line `Round: <N>` naming the last completed round) closes a round 2 or later whose
verdict wasn't clean: the completed round is the larger of `Round: <N>` and the highest id round, each finding of every round is
`fixed in <sha>` with the sha in the checkout's HEAD history, `declined: <why>` or `listed: <where>`, and no blocker of any round
is listed or open. Used by pr-steps and gate-pass (`--ledger`); else it prints what stands and exits 1."""
import re, subprocess, sys

LINE = re.compile(r'^[\s>*-]*`?R(\d+)\.\d+`?\s+`?(blocker|should|nit)`?\s+(.*?)\s*$', re.I)
ROUND = re.compile(r'^[\s>*-]*`?Round:\s*(\d+)', re.I | re.M)


def problems(path, checkout='.'):
    try: text = open(path, errors='replace').read()
    except OSError as e: return [f'{path}: {e.strerror}']
    rows = [m for m in map(LINE.match, text.splitlines()) if m]
    if not rows: return [f"{path} has no '<id> <label> <outcome>' lines (R<round>.<n> blocker|should|nit fixed in <sha>|declined: <why>|listed: <where>)"]
    last = max(int(n) for n in [m[1] for m in rows] + ROUND.findall(text))
    out = [] if last >= 2 else [f'{path} closes round {last}: a verdict that is not clean gets round 2 first']
    for m in rows:
        fixed = re.match(r'fixed in ([0-9a-f]{7,40})\b', m[3])
        on_head = fixed and subprocess.run(['git', '-C', checkout, 'merge-base', '--is-ancestor', fixed[1], 'HEAD'], capture_output=True).returncode == 0
        if fixed and not on_head:
            out.append(f'{m[0].strip()}  <- {fixed[1]} is not in HEAD\'s history')
        elif m[2].lower() == 'blocker' and not on_head and not m[3].startswith('declined:'):
            out.append(f'{m[0].strip()}  <- an open blocker keeps the PR in draft')
        elif not fixed and not re.match(r'(declined|listed):\s*\S', m[3]):
            out.append(f'{m[0].strip()}  <- not fixed in <sha>, declined: <why> or listed: <where>')
    return out


if __name__ == '__main__':
    found = problems(*sys.argv[1:3])
    if found:
        print('the ledger leaves this round open (mergeworthy:delegate §Review rounds):\n' + '\n'.join(found), file=sys.stderr)
    sys.exit(1 if found else 0)
