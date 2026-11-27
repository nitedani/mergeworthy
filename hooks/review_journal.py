"""The review journal (delegate §Review rounds): one append-only file per change, a branch of one repo, holding a `round` event for
each review round that ran, written only by the hooks that register rounds. rounds() reads it back as the loops' records."""
import fcntl, glob, hashlib, json, os, subprocess, time

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


def events(change):
    """The events in the journal file change, oldest first."""
    try: return [json.loads(l) for l in open(change).read().splitlines() if l.strip()]
    except OSError: return []


def post_of(draft):
    """The journal file of a post's review loops on draft: each seat's launches (`post`) and the verdicts a new round set aside (`verdict`)."""
    return os.path.join(JOURNAL, 'posts', hashlib.sha256(os.path.realpath(draft).encode()).hexdigest()[:16] + '.jsonl')


def rounds(change=None, handle=None, keep=lambda e: True):
    """{loop: its round events, oldest first} in the journal file change, or, for the reviewer handle (a T3 thread, a Claude
    agent), the rounds that ran in it in every change's; only the events keep accepts."""
    found = {}
    for f in [change] if handle is None else sorted(glob.glob(os.path.join(JOURNAL, '*', '*.jsonl'))) if handle else ():
        for e in events(f) if f else ():
            if (handle is None or e.get('thread') == handle) and keep(e): found.setdefault(e['loop'], []).append(e)
    return found
