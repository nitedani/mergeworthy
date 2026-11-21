"""The drift count behind pre-bash-guard's finality trigger (`finality` step 1 as a mechanism): which code files (not
testpaths.NOT_CODE, not build output: testpaths.generated) the branch's own commits changed more than 5 times since its first
review (a verify, small, shape, reverify or fresh record); a `pr-steps finality` record on a commit, HEAD too, starts the counts
over after it. Building before any review counts nothing. Only the branch's own commits count (first parent): a merge commit,
made or being made, is no change, nor are the commits it brings in, nor is a maintainer's (AGENT_TRAILER): the drift is the agent's.
A record is the commit's pr-steps record, or the note pr-steps adds beside it under refs/notes/drift, which every worktree of the
repo reads. pr-steps puts refs/notes/drift in the repo's notes.rewriteRef, so git copies the note onto the commit an amend or a
rebase makes (a rebase with conflicts too), and onto the commit a squash or fixup in a rebase joins it into. A cherry-pick, or a
squash made by a reset and a new commit, carries no note: that commit has no record until its next review."""
import os, re, subprocess
import testpaths
from records import commit_file

AGENT_TRAILER = re.compile(r'^Co-Authored-By: Claude', re.M | re.I)  # a commit without it is a maintainer's
REVIEW = {'verify', 'small', 'shape', 'reverify', 'fresh', 'review'}  # the record steps, and the note kind, that are a review


def log(d, *args):
    """`git log args` in checkout d, with signature display, which would add its own lines to any format, pinned off, read as any
    filename's bytes: every history read of the count goes through it."""
    return subprocess.run(['git', '-C', d, '-c', 'log.showSignature=false', 'log', *args], capture_output=True, encoding='utf-8',
                          errors='surrogateescape').stdout


def steps(sha, note):
    """What is recorded on commit sha: the kinds its drift note holds and the steps its pr-steps record holds."""
    rec = commit_file(sha)
    return set(note.split()) | ({l.split()[0] for l in open(rec) if l.split()} if os.path.exists(rec) else set())


def anchor(commits):
    """The commit the count starts after, of the branch's (sha, drift note) pairs oldest first: the last finality, else the first review;
    None for neither. Any first-parent commit's note counts, a merge's or an empty commit's too, as git log prints it with no diff."""
    start = None
    for c, note in commits:
        recorded = steps(c, note)
        if 'finality' in recorded or (start is None and recorded & REVIEW): start = c
    return start


def over(d, head='HEAD', pending=None, amend=False):
    """{code file: its count} of checkout d's files past 5 changes on the branch at head. pending: the files the commit being made
    changes, which alone are judged, each counted once more; None for a push, which judges the commits alone. amend: that commit
    replaces HEAD."""
    g = lambda *a: subprocess.run(['git', '-C', d, *a], capture_output=True, text=True).stdout
    base = g('symbolic-ref', '-q', '--short', 'refs/remotes/origin/HEAD').strip() or 'origin/main'
    if pending is not None and g('rev-parse', '-q', '--verify', 'MERGE_HEAD').strip(): pending = []
    # git prints `\0<sha>\n<its drift note>` per commit: the kinds pr-steps noted on it, one a line
    commits = [c.split('\n', 1) for c in log(d, '--first-parent', '--reverse', '--no-notes', '--notes=drift', '--format=%x00%H%n%N', head, '--not', base).split('\0')[1:]]
    start = anchor(commits)
    if not start: return {}
    count = {}
    # git prints `\0<sha>\n<message>\0` per commit, then `\n` and `<file>\0` for each file it changed (none for a merge): `\0\0` is where a commit ends
    changes = log(d, '--first-parent', '--reverse', '--no-diff-merges', '--no-renames', '--name-only', '-z', '--format=%x00%H%n%B', f'{start}..{head}')
    for commit in changes[1:-1].split('\0\0'):
        message, _, names = commit.partition('\0\n')
        files = names.split('\0') if names and AGENT_TRAILER.search(message) else []
        if amend and message.startswith(commits[-1][0]): pending, files = sorted(set(pending or []) | set(files)), []  # the amended commit is the pending one
        for f in files: count[f] = count.get(f, 0) + 1
    for f in pending or []: count[f] = count.get(f, 0) + 1
    hot = [f for f in (count if pending is None else pending) if count.get(f, 0) > 5 and not re.search(testpaths.NOT_CODE, f)]
    gen = testpaths.generated(d, hot, head if pending is None else None) if hot else set()  # a push's own attributes, a commit's checkout
    return {f: count[f] for f in hot if f not in gen}
