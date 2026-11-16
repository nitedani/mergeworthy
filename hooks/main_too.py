#!/usr/bin/env python3
"""Whether main's having a defect excuses it, decided by where the defect comes from (converge step 1, evidence step 4): a ruling
or a layout-check.md line that says main has it names the `path:line` (or `path:a-b`) it comes from, a file HEAD tracks, outside
every function the branch changes since base (`git diff -W`), else it excuses nothing. pr-steps reads it.
`main_too.py layout <file the step records> <base>`: prints each layout-check.md line that fails, in the task's work folder holding
the file (all of it) or else beside it, and exits 1 when one does."""
import os, re, subprocess, sys
import work_folder

MAIN = re.compile(r"not a regression|\bexisting\b|already exists?\b|\b(default|base) branch\b|\bbaseline\b|not caused by (this|the) (pr|change)|masteren is|same as (on )?(main|master)"
                  r"|\b(on|in) (main|master)\b(?! session| thread)|\b(main|master)('s\b| (too|as well|does|has|had|shows))", re.I)
PLACE = re.compile(r'([\w./@~+-]*[\w@~+-]\.\w+):(\d+)(?:-(\d+))?')  # src/panel.tsx:12, panel.tsx:5-6
OK = re.compile(r'^(.+?)\s[—–-]\s+OK\b(.*)$')


def git(*a):
    return subprocess.run(['git', '-c', 'core.quotePath=false', *a], capture_output=True, text=True).stdout


def changed(base):
    """{path: [(first, last)]}: HEAD's lines of each function the branch changes since base, a hunk of `git diff -W` each."""
    out, path = {}, None
    for l in git('-c', 'diff.noprefix=false', 'diff', '-U0', '-W', '--no-color', '--no-ext-diff', f'{base}...HEAD').splitlines():
        if l.startswith('+++ '): path = l[6:] if l.startswith('+++ b/') else None
        elif path and (m := re.match(r'@@ -\S+ \+(\d+)(?:,(\d+))? @@', l)):
            a, n = int(m[1]), int(m[2] or 1)
            out.setdefault(path, []).append((a, a + max(n, 1) - 1))
    return out


def why_not(text, base):
    """None when text says nothing of main, or names a place outside the changed functions; else why it excuses nothing."""
    return misplaced(text, base) if MAIN.search(text) else None


def misplaced(text, base):
    """None when text names a place the defect comes from, each outside the functions the branch changes; else why not."""
    places = PLACE.findall(text)
    if not places: return 'it names no `path:line` the defect comes from'
    if not base: return "there is no merge-base with origin's default branch to check its place against"
    funcs, tracked = changed(base), git('ls-files').splitlines()
    for p, a, b in places:
        a, b = int(a), int(b or a)
        files = [f for f in tracked if f == p or f.endswith('/' + p)]
        if not files: return f'it names {p}, which HEAD does not track'
        if all(b > len(git('show', f'HEAD:{f}').splitlines()) for f in files): return f'it names {p}:{b}, past the end of the file'
        for f in files:
            if any(a <= z and x <= b for x, z in funcs.get(f, ())):
                return f'{p}:{a} is inside a function this branch changes, so the defect is this change\'s to fix'
    return None


def checks(record):
    """The layout-check.md files of the task's work folder holding record, past its checkouts and node_modules; outside one, the one beside it."""
    if not (root := work_folder.task_of(record)):
        yield from (f for f in [os.path.join(os.path.dirname(os.path.abspath(record)), 'layout-check.md')] if os.path.isfile(f))
        return
    for d, sub, names in os.walk(root):
        sub[:] = [s for s in sub if s != 'node_modules' and not os.path.exists(os.path.join(d, s, '.git'))]
        if 'layout-check.md' in names: yield os.path.join(d, 'layout-check.md')


def layout(record, base):
    """Each failing line of the layout-check.md files the task holds, '<path>: <line>  <- <why>'."""
    bad = []
    for f in checks(record):
        for l in open(f, errors='replace').read().splitlines():
            if (m := OK.match(l.strip())) and m[2].strip(' .'):
                bad.append(f"{f}: {l}  <- a screenshot with anything after OK: write it `{m[1]} — OK`, or each defect it shows as its own line `{m[1]} — <the defect>`")
            elif not m and (why := why_not(l, base)):
                bad.append(f'{f}: {l}  <- main having it excuses nothing here: {why}')
    return bad


if __name__ == '__main__' and sys.argv[1:2] == ['layout']:
    bad = layout(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '')
    for b in bad: print(b)
    sys.exit(1 if bad else 0)
