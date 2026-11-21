"""The drift count behind pre-bash-guard's finality trigger (`finality` step 1 as a mechanism): which code files (not
testpaths.NOT_CODE, not build output: testpaths.generated) the branch's own commits changed more than 5 times since its first
review (a verify, small, shape, reverify or fresh record); a `pr-steps finality` record on a commit, HEAD too, starts the counts
over after it. Building before any review counts nothing. Only the branch's own commits count (first parent): a merge commit,
made or being made, is no change, nor are the commits it brings in, nor is a maintainer's (AGENT_TRAILER): the drift is the agent's.
pr-steps notes each record in the repo's drift log, which every branch and worktree of the repo shares, by its commit's SHA and
identity (identities). A record anchors its own commit; once that SHA has left the branch, it anchors the one commit on the branch
with its identity, and none when two share it."""
import hashlib, os, re, subprocess
import testpaths
from records import STORE

AGENT_TRAILER = re.compile(r'^Co-Authored-By: Claude', re.M | re.I)  # a commit without it is a maintainer's


def identities(d, *revs):
    """{sha: identity} of the commits `git log revs` lists in checkout d that change something: the sha256 of the lines it
    changes, whitespace included, with their files but not their positions or the lines around them. An amend of the message
    alone, a cherry-pick and a rebase that leaves those lines alone keep it; any change to them, a squash or a whitespace fixup
    too, doesn't. A commit missing from it (a merge, an empty commit) is its own SHA."""
    log = subprocess.run(['git', '-C', d, 'log', '-p', '-U0', '--no-color', '--full-index', '--binary', '--no-renames', '--no-textconv',
                          '--no-diff-merges', '--no-show-signature', '--format=%x00%H', *revs], capture_output=True).stdout
    ids = {}
    for commit in log.split(b'\0')[1:]:
        sha, _, diff = commit.partition(b'\n')
        # a hunk header's positions and an index line's blob ids change with lines the commit doesn't change
        lines = [b'@@' if l.startswith(b'@@') else l for l in diff.split(b'\n') if not l.startswith(b'index ')]
        if diff.strip(): ids[sha.decode()] = hashlib.sha256(b'\n'.join(lines)).hexdigest()
    return ids


def log_path(d):
    """The drift log of the repo holding checkout d, one for all its worktrees."""
    common = subprocess.run(['git', '-C', d, 'rev-parse', '--path-format=absolute', '--git-common-dir'], capture_output=True, text=True).stdout.strip()
    return os.path.join(STORE, 'drift.' + hashlib.sha256(os.path.realpath(common).encode()).hexdigest()[:40])


def note(d, kind, sha):
    """Notes a kind of record (review, finality) that bin/pr-steps accepted on commit sha of checkout d, once: a retry of the same
    record notes it after a failed write, its row whole on a line of its own."""
    row = f'{kind} {sha} {identities(d, "-1", sha).get(sha, sha)}'
    with open(log_path(d), 'a+') as f:
        f.seek(0); rows = f.read()
        if row not in rows.splitlines(): f.write(('\n' if rows and not rows.endswith('\n') else '') + row + '\n')


def over(d, head='HEAD', pending=None, amend=False):
    """{code file: its count} of checkout d's files past 5 changes on the branch at head. pending: the files the commit being made
    changes, which alone are judged, each counted once more; None for a push, which judges the commits alone. amend: that commit
    replaces HEAD."""
    notes = []  # (kind, sha, identity) of each record
    if os.path.exists(path := log_path(d)):
        notes = [row for l in open(path) if len(row := l.split()) == 3]  # a row a failed write tore is skipped
    if not notes: return {}
    g = lambda *a: subprocess.run(['git', '-C', d, *a], capture_output=True, encoding='utf-8', errors='surrogateescape').stdout  # any filename's bytes
    base = g('symbolic-ref', '-q', '--short', 'refs/remotes/origin/HEAD').strip() or 'origin/main'
    if pending is not None and g('rev-parse', '-q', '--verify', 'MERGE_HEAD').strip(): pending = []
    # git prints `\0<sha>\n<message>\0` per commit, then `\n` and `<file>\0` for each file it changed (none for a merge): `\0\0` is where a commit ends
    log = g('log', '--first-parent', '--reverse', '--no-diff-merges', '--no-renames', '--no-show-signature', '--encoding=UTF-8', '--name-only', '-z',
            '--format=%x00%H%n%B', head, '--not', base)
    commits = [c.partition('\0\n') for c in log[1:-1].split('\0\0')] if log else []
    shas = [message[:message.find('\n')] for message, _, _ in commits]; on = set(shas)
    noted = {}  # {sha: its records' kinds}: a record's own commit, or the one commit rewritten from it once its SHA left the branch
    for kind, sha, _ in notes:
        if sha in on: noted.setdefault(sha, set()).add(kind)
    if gone := [n for n in notes if n[1] not in on]:
        ids = identities(d, '--first-parent', head, '--not', base)
        twins = {}
        for sha in shas: twins.setdefault(ids.get(sha, sha), []).append(sha)
        for kind, _, ident in gone:
            if len(match := twins.get(ident, [])) == 1: noted.setdefault(match[0], set()).add(kind)
    start = None  # the index of the commit the counts start after
    for i, sha in enumerate(shas):
        kinds = noted.get(sha, set())
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
