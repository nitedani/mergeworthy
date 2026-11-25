#!/usr/bin/env python3
"""The work folders (mergeworthy:task §Files): ~/.mergeworthy/work/<task>/, the task's checkouts inside it; before that layout,
<checkout>-work/ beside a checkout. disk-sweep's w-done rule deletes a finished one."""
import os, re, subprocess
import steward

ROOT = os.path.join(os.path.expanduser('~'), '.mergeworthy', 'work')
GITHUB = re.compile(r'(?:https://github\.com/|git@github\.com:|ssh://git@github\.com/)([\w.-]+/[\w.-]+?)(?:\.git)?/?$')


def git(repo, *args, **kw):
    """git in repo, captured; --no-optional-locks: a refreshed index would reset disk-sweep's idle check; no fsmonitor: a repo's
    own config (an extracted archive's) would run it; no lazy fetch: a partial clone would download each object it lacks."""
    return subprocess.run(['git', '--no-optional-locks', '-c', 'core.fsmonitor=false', '-C', repo, *args], capture_output=True, text=True,
                          env={**os.environ, 'GIT_NO_LAZY_FETCH': '1'}, **kw)


def ancestors(path):
    """path made absolute, then each folder above it, the root last: a walk up that ends on any input, '//' too (its own parent)."""
    p = os.path.abspath(path)
    while True:
        yield p
        if (up := os.path.dirname(p)) == p: return
        p = up


def git_top(path):
    """The nearest folder at or above path holding a .git (a checkout's top), or None."""
    return next((p for p in ancestors(path) if os.path.exists(os.path.join(p, '.git'))), None)


def real(path):
    """path's real path, a leading ~, $HOME or ${HOME} made the home folder."""
    return os.path.realpath(os.path.expanduser(re.sub(r'^\$(?:HOME|\{HOME\})(?=/|$)', '~', path)))


def of(path):
    """The work folder holding path: its ancestor directly under ROOT, else None."""
    p, root = real(path), os.path.realpath(ROOT)
    return os.path.join(root, p[len(root) + 1:].split('/')[0]) if p.startswith(root + '/') else None


def task_of(path):
    """The task's work folder holding path: ~/.mergeworthy/work/<task>/; before that layout, the nearest <name>-work/ above it, or
    the <prefix>-work/ beside the checkout it is in (`fu185-work/` beside `fu185-gps-fix/`); None when there is none."""
    if wf := of(path): return wf
    home = os.path.realpath(os.path.expanduser('~'))
    for p in ancestors(real(path)):
        if p in (home, '/'): return None
        if p.endswith('-work') and os.path.isdir(p): return p
        name = os.path.basename(p)
        for i in [len(name)] + [m.start() for m in re.finditer('-', name)][::-1]:
            if os.path.isdir(beside := os.path.join(os.path.dirname(p), name[:i] + '-work')): return beside


def watched_by(dirs, session_id, path):
    """The watch dirs (gh-watch-start) among dirs whose events reach the session acting at path: the task's work folder holding path
    (the steward's: its live dir, steward.home); outside one, the dirs whose `session` file names session_id, but the steward's (steward.quiet: it wakes only for a new mergeworthy issue).
    Another session's watcher wakes that session alone."""
    if wf := task_of(path):
        return [w for w in dirs if os.path.realpath(w) == os.path.realpath(steward.home(wf))]
    def session(w):
        try: return open(os.path.join(w, 'session')).read().strip()
        except OSError: return ''
    return [w for w in dirs if session_id and session(w) == session_id and not steward.quiet(w)]


def inside(p, top):
    return p == top or p.startswith(top + '/')


def trees(folder):
    """Every git work tree under folder, nested and ignored ones too, without following a symlink or leaving its filesystem."""
    dev, found, stack = os.lstat(folder).st_dev, [], [folder]
    while stack:
        try:
            entries = list(os.scandir(stack.pop()))
        except OSError:
            continue
        for e in entries:
            if e.is_symlink() or e.stat(follow_symlinks=False).st_dev != dev:
                continue
            if e.name == '.git':
                found.append(os.path.dirname(e.path))
            elif e.is_dir():
                stack.append(e.path)
    return found


def common_dir(top):
    """The real path of top's git common dir (its repo's git data), or None."""
    c = git(top, 'rev-parse', '--path-format=absolute', '--git-common-dir').stdout.strip()
    return os.path.realpath(c) if c else None


def outside_repos(folder):
    """The git common dirs outside folder whose repos have a worktree under it."""
    folder = os.path.realpath(folder)
    return sorted({c for c in map(common_dir, trees(folder)) if c and not inside(c, folder)})


def worktrees(top):
    """[(path, HEAD sha, detached)] of each worktree of top's repo."""
    out = []
    for block in git(top, 'worktree', 'list', '--porcelain').stdout.split('\n\n'):
        f = dict(l.partition(' ')[::2] for l in block.splitlines())
        if 'worktree' in f:
            out.append((f['worktree'], f.get('HEAD', ''), 'detached' in f))
    return out


def has_open_line(path, cleared):
    """Whether the file path has a line that isn't blank, a # comment or cleared (it starts with cleared, in any case, after a `- ` or
    `* ` list marker if it has one)."""
    return os.path.isfile(path) and any((l := s.strip()) and not l.startswith('#') and not re.sub(r'^[-*] ', '', l).lower().startswith(cleared)
                                        for s in open(path, errors='replace'))


def open_defects(folders):
    """(file, PR, defect, line) of each open line in the folders' defects-open.md (mergeworthy:task §Files): `<owner/repo#N>: <the defect>`,
    a GitLab MR's `gitlab.com/<path>!N: …` (`<path>!N` is on gitlab.com), after a `- ` or `* ` marker too; PR is None on a line of no such form. A blank line, a # comment
    or one cleared as `fixed in <sha>: …` isn't open."""
    out = []
    for f in (os.path.join(x, 'defects-open.md') for x in folders):
        for l in (s.strip() for s in (open(f, errors='replace') if os.path.isfile(f) else ())):
            body = re.sub(r'^[-*] ', '', l)
            if not l or l.startswith('#') or body.lower().startswith('fixed in '): continue
            m = re.match(r'([\w./-]+(?:#|!)\d+):\s+(\S.*)', body)
            pr = m and m[1].lower()
            out.append((f, 'gitlab.com/' + pr if pr and '!' in pr and not pr.startswith('gitlab.com/') else pr, m[2] if m else body, l))
    return out


def lent(folder):
    """One reason for each worktree outside folder of a repo whose git data is inside it: deleting folder would take that checkout's repo."""
    folder, repos = os.path.realpath(folder), {}
    for top in sorted(trees(folder)):
        if (c := common_dir(top)) and inside(c, folder):
            repos.setdefault(c, top)
    return [f'{top}: its worktree {p} is outside the folder' for top in repos.values() for p, _, _ in worktrees(top)
            if not inside(os.path.realpath(p), folder) and os.path.exists(p)]
