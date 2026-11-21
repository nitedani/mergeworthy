"""The drift count behind pre-bash-guard's finality trigger (`finality` step 1 as a mechanism): which code files (not
testpaths.NOT_CODE, not build output: testpaths.generated) the branch's own commits changed more than 5 times since its first
review (a verify, small, shape, reverify or fresh record); a `pr-steps finality` record on a commit, HEAD too, starts the counts
over after it. Building before any review counts nothing. Only the branch's own commits count (first parent): a merge commit,
made or being made, is no change, nor are the commits it brings in, nor is a maintainer's (AGENT_TRAILER): the drift is the agent's.
pr-steps notes each record in the repo's drift log by the commit's identity, which a rebase, a cherry-pick and an amend keep and
a squash doesn't, and which every branch and worktree of the repo shares: a squashed branch counts nothing until its next review."""
import hashlib, os, re, subprocess, sys
import testpaths
from records import STORE

AGENT_TRAILER = re.compile(r'^Co-Authored-By: Claude', re.M | re.I)  # a commit without it is a maintainer's
ID = '%at %s'  # the git format identity() reads


def identity(line):
    """The identity of the commit whose ID line is line: its author time and a hash of its subject."""
    at, _, subject = line.partition(' ')
    return f'{at}:{hashlib.sha256(subject.encode()).hexdigest()[:12]}'


def log_path(d):
    """The drift log of the repo holding checkout d, one for all its worktrees."""
    common = subprocess.run(['git', '-C', d, 'rev-parse', '--path-format=absolute', '--git-common-dir'], capture_output=True, text=True).stdout.strip()
    return os.path.join(STORE, 'drift.' + hashlib.sha256(os.path.realpath(common).encode()).hexdigest()[:40])


def note(d, kind, proof):
    """Notes a kind of record (review, finality) with its proof file on checkout d's HEAD."""
    line = subprocess.run(['git', '-C', d, 'log', '-1', f'--format={ID}'], capture_output=True, text=True).stdout.rstrip('\n')
    with open(log_path(d), 'a') as f: f.write(f'{kind} {identity(line)} {proof}\n')


def over(d, head='HEAD', pending=None, amend=False):
    """{code file: its count} of checkout d's files past 5 changes on the branch at head. pending: the files the commit being made
    changes, which alone are judged, each counted once more; None for a push, which judges the commits alone. amend: that commit
    replaces HEAD."""
    noted = {}
    if os.path.exists(path := log_path(d)):
        for l in open(path):
            kind, ident = l.split()[:2]
            noted.setdefault(ident, set()).add(kind)
    if not noted: return {}
    g = lambda *a: subprocess.run(['git', '-C', d, *a], capture_output=True, text=True).stdout
    base = g('symbolic-ref', '-q', '--short', 'refs/remotes/origin/HEAD').strip() or 'origin/main'
    if pending is not None and g('rev-parse', '-q', '--verify', 'MERGE_HEAD').strip(): pending = []
    # git prints `\0<sha>\n<ID line>\n<message>\0` per commit, then `\n` and `<file>\0` for each file it changed (none for a merge): `\0\0` is where a commit ends
    log = g('log', '--first-parent', '--reverse', '--no-diff-merges', '--no-renames', '--name-only', '-z', f'--format=%x00%H%n{ID}%n%B', head, '--not', base)
    commits = [c.partition('\0\n') for c in log[1:-1].split('\0\0')] if log else []
    start = None  # the index of the commit the counts start after
    for i, (message, _, _) in enumerate(commits):
        kinds = noted.get(identity(message.split('\n')[1]), set())
        if 'finality' in kinds or start is None and 'review' in kinds: start = i
    if start is None: return {}
    count = {}
    for i, (message, _, names) in enumerate(commits[start + 1:], start + 1):
        files = names.split('\0') if names and AGENT_TRAILER.search(message) else []
        if amend and i == len(commits) - 1: pending, files = sorted(set(pending or []) | set(files)), []  # the amended commit is the pending one
        for f in files: count[f] = count.get(f, 0) + 1
    for f in pending or []: count[f] = count.get(f, 0) + 1
    hot = [f for f in (count if pending is None else pending) if count.get(f, 0) > 5 and not re.search(testpaths.NOT_CODE, f)]
    gen = testpaths.generated(d, hot, head if pending is None else None) if hot else set()  # a push's own attributes, a commit's checkout
    return {f: count[f] for f in hot if f not in gen}


if __name__ == '__main__':  # bin/pr-steps: drift.py note <review|finality> <proof file>, on the checkout's HEAD
    note(os.getcwd(), *sys.argv[2:4])
