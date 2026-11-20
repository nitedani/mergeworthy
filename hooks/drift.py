"""The drift count behind pre-bash-guard's finality trigger (`finality` step 1 as a mechanism): which code files (not
testpaths.NOT_CODE, not build output: testpaths.generated) the branch's own commits changed more than 5 times since its first
review (a verify, small, shape, reverify or fresh record); a `pr-steps finality` record on a commit, HEAD too, starts the counts
over after it. Building before any review counts nothing. Only the branch's own commits count (first parent): a merge commit,
made or being made, is no change, nor are the commits it brings in, nor is a maintainer's (AGENT_TRAILER): the drift is the agent's."""
import os, re, subprocess
import testpaths
from records import commit_file

AGENT_TRAILER = re.compile(r'^Co-Authored-By: Claude', re.M | re.I)  # a commit without it is a maintainer's


def over(d, head='HEAD', pending=None, amend=False):
    """{code file: its count} of checkout d's files past 5 changes on the branch at head. pending: the files the commit being made
    changes, which alone are judged, each counted once more; None for a push, which judges the commits alone. amend: that commit
    replaces HEAD."""
    g = lambda *a: subprocess.run(['git', '-C', d, *a], capture_output=True, text=True).stdout
    base = g('symbolic-ref', '-q', '--short', 'refs/remotes/origin/HEAD').strip() or 'origin/main'
    if pending is not None and g('rev-parse', '-q', '--verify', 'MERGE_HEAD').strip(): pending = []
    commits = g('rev-list', '--reverse', '--first-parent', head, '--not', base).split()
    start = None  # the commit the counts start after
    for c in commits:
        steps = {l.split()[0] for l in open(commit_file(c)) if l.split()} if os.path.exists(commit_file(c)) else set()
        if 'finality' in steps or not start and steps & {'verify', 'small', 'shape', 'reverify', 'fresh'}: start = c
    if not start: return {}
    count = {}
    # per commit `\0<sha>\n<message>\0`, then `\n<file>\0<file>\0` (none for a merge commit): no part is empty, so `\0\0` is only where a commit ends
    log = g('log', '--first-parent', '--reverse', '--no-diff-merges', '--no-renames', '--name-only', '-z', '--format=%x00%H%n%B', f'{start}..{head}')
    for commit in log[1:-1].split('\0\0'):
        message, _, names = commit.partition('\0\n')
        files = names.split('\0') if names and AGENT_TRAILER.search(message) else []
        if amend and message.startswith(commits[-1]): pending, files = sorted(set(pending or []) | set(files)), []  # the amended commit is the pending one
        for f in files: count[f] = count.get(f, 0) + 1
    for f in pending or []: count[f] = count.get(f, 0) + 1
    hot = [f for f in (count if pending is None else pending) if count.get(f, 0) > 5 and not re.search(testpaths.NOT_CODE, f)]
    gen = testpaths.generated(d, hot, head if pending is None else None) if hot else set()  # a push's own attributes, a commit's checkout
    return {f: count[f] for f in hot if f not in gen}
