"""The drift count behind pre-bash-guard's finality trigger (`finality` step 1 as a mechanism): which code files (not
testpaths.NOT_CODE, not build output: testpaths.generated) the branch's own commits changed more than 5 times since its first
review (a verify, small, shape, reverify or fresh record); a `pr-steps finality` record on a commit, HEAD too, starts the counts
over after it. Building before any review counts nothing. Only the branch's own commits count (first parent): a merge commit,
made or being made, is no change, nor are the commits it brings in, nor is a maintainer's (AGENT_TRAILER): the drift is the agent's.
pr-steps notes each record in the repo's drift log, which every branch and worktree of the repo shares, by its commit's SHA, author
time and email (KEY) and identity (identities). A record anchors its own commit; once that SHA has left the branch, it anchors the
one commit on the branch with its KEY and identity, and none when two share them. So a record follows its commit through an amend of
the message (a merge's and an empty commit's too), a cherry-pick and a rebase that leaves its changed lines and their function lines
alone, and stays behind on a squash and on any change to those lines or their function line, a whitespace fixup too."""
import hashlib, os, re, subprocess
import testpaths
from records import STORE

AGENT_TRAILER = re.compile(r'^Co-Authored-By: Claude', re.M | re.I)  # a commit without it is a maintainer's
KEY = '%at:%ae'  # a commit's author time and email, which an amend, a cherry-pick and a rebase keep
# the diff identities() hashes, the same in every checkout: no attributes (the empty tree's, none of the user's or the system's),
# no display settings, the default prefixes and algorithm
EMPTY_TREE = {40: '4b825dc642cb6eb9a060e54bf8d69288fbee4904', 64: '6ef19b41225c5369f1c104d45d8d85efa9b057b53b14b4b9b939dd74decc5321'}  # by SHA-1's and SHA-256's length
PATCH =['-p', '-U0', '--no-color', '--full-index', '--no-renames', '--no-relative', '--no-ext-diff', '--no-textconv', '--diff-algorithm=myers',
         '--indent-heuristic', '--src-prefix=a/', '--dst-prefix=b/', '--no-diff-merges', '--no-show-signature']


def identities(d, shas):
    """{sha: (KEY, identity)} of commits shas of checkout d, from one git call. The identity is the sha256 of each file's changed
    lines, whitespace included, under each hunk's function line (the line git names after its numbers) but not its numbers, a binary
    file by its old and new blob ids; for a commit with no patch (an empty commit, a merge), of its tree and its parents."""
    log = subprocess.run(['git', '-c', 'core.attributesFile=/dev/null', '-c', 'core.quotePath=true', f'--attr-source={EMPTY_TREE[len(shas[0])]}',
                          '-C', d, 'log', '--no-walk=unsorted', *PATCH, f'--format=%x00%H {KEY} %T %P', *shas],
                         capture_output=True, env={**os.environ, 'GIT_ATTR_NOSYSTEM': '1'}).stdout
    ids = {}
    for commit in log.split(b'\0')[1:]:
        head, _, patch = commit.partition(b'\n')
        sha, key, tree_parents = head.decode('utf-8', 'surrogateescape').split(' ', 2)
        hashed = b''.join(map(changed, re.split(rb'^(?=diff --git )', patch, flags=re.M))) if patch.strip() else tree_parents.encode()
        ids[sha] = (key, hashlib.sha256(hashed).hexdigest())
    return ids


def changed(file):
    """A file's part of a patch as identities() hashes it: a binary file whole, a text file without its blob ids and line numbers,
    which change with lines the commit doesn't change."""
    if b'\nBinary files ' in file: return file
    return b'\n'.join(b'@@' + l.split(b'@@', 2)[2] if l.startswith(b'@@') else l for l in file.split(b'\n') if not l.startswith(b'index '))


def log_path(d):
    """The drift log of the repo holding checkout d, one for all its worktrees."""
    common = subprocess.run(['git', '-C', d, 'rev-parse', '--path-format=absolute', '--git-common-dir'], capture_output=True, text=True).stdout.strip()
    return os.path.join(STORE, 'drift.' + hashlib.sha256(os.path.realpath(common).encode()).hexdigest()[:40])


def note(d, kind, sha):
    """Notes a kind of record (review, finality) that bin/pr-steps accepted on commit sha of checkout d, once: a retry of the same
    record notes it after a failed write, its row whole on a line of its own."""
    row = ' '.join((kind, sha, *identities(d, [sha])[sha]))
    with open(log_path(d), 'a+') as f:
        f.seek(0); rows = f.read()
        if row not in rows.splitlines(): f.write(('\n' if rows and not rows.endswith('\n') else '') + row + '\n')


def over(d, head='HEAD', pending=None, amend=False):
    """{code file: its count} of checkout d's files past 5 changes on the branch at head. pending: the files the commit being made
    changes, which alone are judged, each counted once more; None for a push, which judges the commits alone. amend: that commit
    replaces HEAD."""
    notes = []  # (kind, sha, KEY, identity) of each record
    if os.path.exists(path := log_path(d)):
        notes = [row for l in open(path) if len(row := l.split()) == 4]  # a row a failed write tore is skipped
    if not notes: return {}
    g = lambda *a: subprocess.run(['git', '-C', d, *a], capture_output=True, encoding='utf-8', errors='surrogateescape').stdout  # any filename's bytes
    base = g('symbolic-ref', '-q', '--short', 'refs/remotes/origin/HEAD').strip() or 'origin/main'
    if pending is not None and g('rev-parse', '-q', '--verify', 'MERGE_HEAD').strip(): pending = []
    # git prints `\0<sha> <KEY>\n<message>\0` per commit, then `\n` and `<file>\0` for each file it changed (none for a merge): `\0\0` is where a commit ends
    log = g('log', '--first-parent', '--reverse', '--no-diff-merges', '--no-renames', '--no-show-signature', '--encoding=UTF-8', '--name-only', '-z',
            f'--format=%x00%H {KEY}%n%B', head, '--not', base)
    commits = [c.partition('\0\n') for c in log[1:-1].split('\0\0')] if log else []
    keys = dict(message[:message.find('\n')].split(' ', 1) for message, _, _ in commits)  # {sha: KEY}, in branch order
    noted = {}  # {sha: its records' kinds}: a record's own commit, or the one commit rewritten from it once its SHA left the branch
    for kind, sha, _, _ in notes:
        if sha in keys: noted.setdefault(sha, set()).add(kind)
    gone = [n for n in notes if n[1] not in keys]; gone_keys = {n[2] for n in gone}
    if like := [sha for sha, key in keys.items() if key in gone_keys]:  # only the commits a rewrite can have made
        twins = {}
        for sha, key_ident in identities(d, like).items(): twins.setdefault(key_ident, []).append(sha)
        for kind, _, key, ident in gone:
            if len(match := twins.get((key, ident), [])) == 1: noted.setdefault(match[0], set()).add(kind)
    start = None  # the index of the commit the counts start after
    for i, sha in enumerate(keys):
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
