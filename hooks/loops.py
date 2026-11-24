"""Review loops (delegate §Review rounds): pre-agent-dedupe asks admit() whether round `<loop>-r<N>` of a code review may run, and
records a round that ran with register(); pr-steps and gate-pass ask close() whether a loop's ledger closes it. A round is refused once the heads its brief pins show the branch hasn't moved since four
earlier rounds of its loop, and, after an earlier one there, when the ledger its brief names doesn't show the last round brought a
fixed blocker or should."""
import fcntl, itertools, json, os, re, subprocess, sys
import ledger, testpaths

LOOPS = os.path.expanduser('~/.claude/review-loops.json')  # {loop: {'rounds': [[n, the heads its brief pinned]], 'threads': the T3 threads its rounds ran in}}
# what a loop recorded before review-loops.json: rounds {loop: [[n, heads]]}, threads {loop: [thread]}
OLD = {'rounds': os.path.expanduser('~/.claude/review-rounds.json'), 'threads': os.path.expanduser('~/.claude/review-threads.json')}


def round_of(name):
    """A review round `<loop>-r<N>`, maybe followed by the date or head SHA a reused clientRequestId needs: the match, loop and N."""
    return re.fullmatch(r'(.+)-r(\d+)', re.sub(r'(-\d{4}-\d{2}-\d{2}|-[0-9a-f]{7,40})+$', '', name.strip()))


def locked_update(path, change):
    """Applies change to the JSON object in path (an empty one while it is missing) and writes it back, under path's lock:
    concurrent launches update it one at a time."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path + '.lock', 'a') as held:
        if not (_lock and path == LOOPS): fcntl.flock(held, fcntl.LOCK_EX)  # a shell round admitted in this process holds it already
        data = json.load(open(path)) if os.path.exists(path) else {}
        change(data)
        with open(path + '.tmp', 'w') as o: json.dump(data, o)
        os.replace(path + '.tmp', path)


def _json(path):
    try: data = json.load(open(path))
    except (OSError, ValueError): return {}
    return data if isinstance(data, dict) else {}


def record(loop, loops=None):
    """loop's record in loops (default: review-loops.json), else what the files before it hold for loop."""
    r = (_json(LOOPS) if loops is None else loops).get(loop)
    if isinstance(r, dict): return r
    return {k: _json(path).get(loop, []) for k, path in OLD.items()}


def threads(loop):
    """The T3 threads an earlier review round of loop ran in."""
    return record(loop)['threads']


FANOUT = r'^Fan-out: converge §Running the agents$'  # a round 1 seating a step's reviewers at once (delegate §Reviewers)


def register(loop, n, heads, thread=None, post=False, outs=(), seated=False):
    """Records round n of loop that ran: the thread it ran in, and, for a code review, the heads its brief pinned, the reports it
    writes (outs) and whether it is one of its step's seats (seated: its round 1 brief's FANOUT line)."""
    def ran(loops):
        r = loops[loop] = record(loop, loops)
        if thread and thread not in r['threads']: r['threads'].append(thread)
        if not post:
            r['rounds'].append([n, heads])
            r['outs'] = sorted(set(r.get('outs', [])) | {os.path.realpath(o) for o in outs})
            r['seated'] = r.get('seated') or seated
    if thread or not post: locked_update(LOOPS, ran)


def open_seats(report, recorded):
    """The other seats of report's step, loops `<step-or-slice>-<provider>` seated with its loop, none of whose reports is in
    recorded (the outputs pr-steps recorded on the head): a step closes only once every seat's loop did."""
    loops, report = _json(LOOPS), os.path.realpath(report)
    stems = {l.rsplit('-', 1)[0] for l, r in loops.items() if isinstance(r, dict) and r.get('seated') and report in r.get('outs', [])}
    return sorted(l for l, r in loops.items() if isinstance(r, dict) and r.get('seated') and l.rsplit('-', 1)[0] in stems
                  and report not in r.get('outs', []) and not set(r.get('outs', [])) & set(recorded))


git = lambda wt, *a: subprocess.run(['git', '-C', wt, *a], capture_output=True, text=True)
SHA = r'\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b'


def pinned(L):
    """(the checkouts launch L's brief names, their heads that its pinned SHAs equal)."""
    shas = set(re.findall(SHA, L.brief))
    return L.checkouts, sorted({h for t in L.checkouts if (h := git(t, 'rev-parse', 'HEAD').stdout.strip()) and any(h.startswith(x) for x in shas)})


def ledger_named(brief):
    """The ledger path a round's brief names, else None."""
    m = re.search(r'(/[^\s`\'"()]+\.ledger\.md)\b', brief)
    return m and m[1]
_lock = None


def admit(loop, n, tops, heads, led):
    """Why round n (2 or later) of code review loop is refused, '' when it may run: tops are the checkouts its brief names, heads
    their heads its pins equal, led the ledger path it names (None). Holds the rounds' lock until the process exits."""
    global _lock
    if re.fullmatch(r'fresh(-[^-]+)?', loop):
        return f"{loop}-r{n}: the fresh reader runs once (mergeworthy:converge step 4); its findings go back to the loops that own them, `<slice>-fresh` (mergeworthy:delegate §Review rounds).\n"
    _lock = open(LOOPS + '.lock', 'a'); fcntl.flock(_lock, fcntl.LOCK_EX)
    # first-parent and no merges: what a merge of the base brought in isn't the PR's own, as SHAPE STALE's compare leaves it out; no renames: each row names a real path
    def own_lines(t, o, h):
        rows = re.findall(r'^(\d+)\t(\d+)\t(.*)$', git(t, '-c', 'core.quotePath=false', 'log', '--first-parent', '--no-merges', '--no-renames', '--numstat', '--format=', f'{o}..{h}').stdout, re.M)
        gen = testpaths.generated(t, [p for _, _, p in rows])
        return testpaths.moved([r for r in rows if r[2] not in gen])
    desc = lambda t, o, h: git(t, 'merge-base', '--is-ancestor', o, h).returncode == 0
    def built_on(old):
        # each new head built on the round's heads counts, so a pin that never moves can't stand for a branch that did
        if not old: return not heads
        moved = False
        for h in heads:
            if h in old: moved = True; continue
            on = ((t, o) for t in tops for o in old if desc(t, o, h))
            if (first := next(on, None)) is None: continue
            moved = True
            if not any(own_lines(t, o, h) <= testpaths.STALE_LINES for t, o in itertools.chain([first], on)): return False
        return moved
    earlier = sorted({m for m, old, *_ in record(loop)['rounds'] if m < n and built_on(old)})
    try: last, kept = ledger.last_round(led) if led and os.path.isfile(led) else (0, False)
    except OSError as e: return f"the ledger {led} can't be read ({e.strerror}), so no round of {loop} is admitted: fix it, or name the loop's ledger (mergeworthy:delegate §Review rounds).\n"
    close = f"Close the loop with `pr-steps <step> <file> --ledger {led or '<ledger>'}` on r{earlier[-1]}'s report when it isn't clean: the agent's own report is the record, never one the main session writes.\n" if earlier else ''
    if len(earlier) >= 4:
        return (f"{loop} already ran {', '.join(f'r{m}' for m in earlier)} on this head or one within {testpaths.STALE_LINES} changed lines of it "
                f"({', '.join(h[:12] for h in heads) or 'no head pinned'}): a loop gets four rounds per head, and a head past those lines is a new one "
                "(mergeworthy:delegate §Review rounds). "
                + (f"The ledger {led} shows round {last} still brought a blocker or should fixed in a commit: the area keeps taking patches, so its next step is "
                   "the finality pass (mergeworthy:finality step 1, recorded by `pr-steps finality <file>`), not another round. " if kept else "")
                + "List what is still open in the report or the PR body's notes and go on (push, ready, the next step) without waiting for an answer; "
                "only an open blocker keeps the PR in draft. A maintainer's ask on a new head starts a new loop name. " + close)
    if earlier and not kept:
        return (f"{loop}-r{n} follows r{earlier[-1]} on this head or one within {testpaths.STALE_LINES} changed lines of it, and a loop gets its next round only "
                "while its last round brought a blocker or should you kept and fixed (mergeworthy:delegate §Review rounds), but "
                + ("the brief names no `<work folder>/drafts/<review>.ledger.md` to show it: name the loop's ledger in the brief, or end the loop. " if not led else
                   f"{led} doesn't exist: name the loop's ledger, or end the loop. " if not os.path.isfile(led) else
                   f"the ledger {led} shows round {last} brought none `fixed in <sha>`: the loop ends there. ")
                + close)
    return ''


# per kind of loop: the fix outcome that closes a finding, why the completed round leaves the loop open ('' when it doesn't), and
# whether a later round confirming the fix closes it (a post's draft has no sha)
KINDS = {
    'code': ('fixed in <sha>', lambda rows, last, p: f'{p} closes round {last}, which brought a blocker or should fixed in a commit: the loop gets its next round first'
             if last < 4 and ledger.fixed_in(rows, last) else '', False),
    'post': ('fixed in r<N>', lambda rows, last, p: '' if last >= 2 else f'{p} closes round {last}: a verdict that is not clean gets round 2 first', True),
}


def close(path, kind='code', checkout='.'):
    """What leaves the loop of the ledger at path open, [] when it closes: each finding of every round is the kind's fix (a code
    fix's sha in checkout's HEAD history), `declined: <why>` or `listed: <where>`, no blocker is listed or open, the completed round
    leaves the loop closed by the kind's rule, and every row's id (a word starting with a letter, with a digit) is R<round>.<n>."""
    fix, still_open, confirms = KINDS[kind]
    try: rows, lines, last = ledger.read(path)
    except OSError as e: return [f'{path}: {e.strerror}']
    misnamed = [f'{m[0].strip()}  <- its id is not R<round>.<n>' for m in lines if not m[1]]
    if not rows: return misnamed + [f"{path} has no '<id> <label> <outcome>' lines (R<round>.<n> blocker|should|nit {fix}|declined: <why>|listed: <where>)"]
    out = misnamed + [w for w in [still_open(rows, last, path)] if w]
    for m in rows:
        fixed = ledger.FIXED.match(m[3])
        confirmed = confirms and (r := re.match(r'fixed in r(\d+)\b', m[3])) and int(m[1]) < int(r[1]) <= last
        closed = confirmed or fixed and subprocess.run(['git', '-C', checkout, 'merge-base', '--is-ancestor', fixed[1], 'HEAD'], capture_output=True).returncode == 0
        if fixed and not closed:
            out.append(f'{m[0].strip()}  <- {fixed[1]} is not in HEAD\'s history')
        elif m[2].lower() == 'blocker' and not closed and not m[3].startswith('declined:'):
            out.append(f'{m[0].strip()}  <- an open blocker keeps the PR in draft')
        elif not closed and not re.match(r'(declined|listed):\s*\S', m[3]):
            out.append(f'{m[0].strip()}  <- not {fix}, declined: <why> or listed: <where>')
    return out


if __name__ == '__main__' and sys.argv[1:2] == ['seats']:  # loops.py seats <report> <record file>: open_seats, a line each
    print(*open_seats(sys.argv[2], [l.split()[1] for l in open(sys.argv[3]) if len(l.split()) > 1] if os.path.isfile(sys.argv[3]) else []), sep='\n')
elif __name__ == '__main__':  # loops.py close [--post] <ledger> [<checkout>]: exits 0 when the ledger closes its loop, else prints what stands
    post = sys.argv[2:3] == ['--post']
    found = close(*sys.argv[2 + post:3 + post], kind='post' if post else 'code', checkout=(sys.argv[3 + post:4 + post] or ['.'])[0])
    if found:
        print('the ledger leaves this round open (mergeworthy:delegate §Review rounds):\n' + '\n'.join(found), file=sys.stderr)
    sys.exit(1 if found else 0)
