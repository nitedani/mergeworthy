"""The review journal (delegate §Review rounds): one append-only file per change, a branch of one repo, holding a `round` event for
each review round that ran, written only by the hooks that register rounds. fold() reads it back as the loops' records."""
import fcntl, hashlib, json, os, subprocess, time

JOURNAL = os.path.expanduser('~/.claude/review-journal')


def change_of(checkout):
    """The journal file of checkout's change: its repo's common git dir and its branch; None for a detached HEAD or no repo."""
    git = lambda *a: subprocess.run(['git', '-C', checkout, *a], capture_output=True, text=True).stdout.strip()
    common, branch = git('rev-parse', '--path-format=absolute', '--git-common-dir'), git('symbolic-ref', '-q', '--short', 'HEAD')
    if not (common and branch): return None
    repo = hashlib.sha256(os.path.realpath(common).encode()).hexdigest()[:12] + '-' + os.path.basename(os.path.dirname(os.path.realpath(common)))
    return os.path.join(JOURNAL, repo, branch.replace('/', '%') + '.jsonl')


def append(change, event):
    """Appends event to the journal file change, one JSON line, under its lock: several sessions register rounds at once."""
    os.makedirs(os.path.dirname(change), exist_ok=True)
    with open(change, 'a') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.write(json.dumps({'at': time.time(), **event}) + '\n')


def fold(change):
    """The loops change's journal holds: {loop: {'rounds': [[n, heads, outs]], 'threads': [...], 'outs': [...], 'seated': bool}}."""
    loops = {}
    try: lines = open(change).read().splitlines()
    except OSError: return loops
    for e in map(json.loads, filter(None, lines)):
        r = loops.setdefault(e['loop'], {'rounds': [], 'threads': [], 'outs': [], 'seated': False})
        if e.get('thread') and e['thread'] not in r['threads']: r['threads'].append(e['thread'])
        r['rounds'].append([e['n'], e['heads'], e['outs']])
        r['outs'] = sorted(set(r['outs']) | set(e['outs']))
        r['seated'] = r['seated'] or e['seated']
    return loops
