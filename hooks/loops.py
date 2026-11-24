"""Review loops (delegate §Review rounds): pre-agent-dedupe asks admit() whether round `<loop>-r<N>` of a code review may run, and
records a round that ran with register(). A round is refused once the heads its brief pins show the branch hasn't moved since four
earlier rounds of its loop, and, after an earlier one there, when the ledger its brief names doesn't show the last round brought a
fixed blocker or should."""
import fcntl, itertools, json, os, re, subprocess
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
        fcntl.flock(held, fcntl.LOCK_EX)
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


def register(loop, n, heads, thread=None, post=False):
    """Records round n of loop that ran: the thread it ran in, and, for a code review, the heads its brief pinned."""
    def ran(loops):
        r = loops[loop] = record(loop, loops)
        if thread and thread not in r['threads']: r['threads'].append(thread)
        if not post: r['rounds'].append([n, heads])
    if thread or not post: locked_update(LOOPS, ran)


git = lambda wt, *a: subprocess.run(['git', '-C', wt, *a], capture_output=True, text=True)
_lock = None


def admit(loop, n, tops, heads, led):
    """Why round n (2 or later) of code review loop is refused, '' when it may run: tops are the checkouts its brief names, heads
    their heads its pins equal, led the ledger path it names (None). Holds the rounds' lock until the process exits."""
    global _lock
    _lock = open(LOOPS + '.lock', 'a'); fcntl.flock(_lock, fcntl.LOCK_EX)
    # first-parent and no merges: what a merge of the base brought in isn't the PR's own, as SHAPE STALE's compare leaves it out; no renames: each row names a real path
    def own_lines(t, o, h):
        rows = re.findall(r'^(\d+)\t(\d+)\t(.*)$', git(t, '-c', 'core.quotePath=false', 'log', '--first-parent', '--no-merges', '--no-renames', '--numstat', '--format=', f'{o}..{h}').stdout, re.M)
        gen = testpaths.generated(t, [p for _, _, p in rows])
        return sum(int(a) + int(b) for a, b, p in rows if not re.search(testpaths.NOT_SHAPE, p) and p not in gen)
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
    last, kept = ledger.last_round(led) if led and os.path.isfile(led) else (0, False)
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
