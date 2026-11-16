#!/usr/bin/env python3
"""Whether main's having a defect excuses it, decided by where the defect comes from (converge step 1, evidence step 4): a ruling
or a layout-check.md line that says main has it names the `path:line` (or `path:a-b`) it comes from, a file HEAD tracks, outside
every function the branch changes since the PR's base (`git diff -W`), else it excuses nothing. pr-steps reads it.
`main_too.py task <file the step records> <base>`: prints each layout-check.md line and each other file's RULED line that fails, in
the task's work folder holding the file (all of it) or else the layout-check.md beside it, and exits 1 when one does."""
import os, re, subprocess, sys
import work_folder

MAIN = re.compile(r"not a regression|pre-?existing|already exist(s|ed)?\b|\b(default|base) branch\b|\bbaseline\b|not caused by (this|the) (pr|change)|masteren is|same as (on )?(main|master)"
                  r"|\b(on|in) (main|master)\b(?! session| thread)|\b(main|master)('s\b| (too|as well|does|has|had|shows))", re.I)
PLACE = re.compile(r'(?<![\w./@~+-])([\w./@~+-]*[\w@~+-]):(\d+)(?:-(\d+))?')  # src/panel.tsx:12, ./panel.tsx:5-6, /abs/path.ts:3, Makefile:2
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


def ruled(line, why, base):
    """None when a RULED line's ruling (why, after its candidate) is a bug or another reason, or says main has it from a right place; else why not."""
    if re.search(r'earn every line|no realistic usage|contrived|staged race', line, re.I) or re.match(r'\s*(a bug|bug|fix(ed)?\b)', why.lstrip(': '), re.I): return None
    return misplaced(line, base) if MAIN.search(why) else None


def misplaced(text, base):
    """None when text names a place the defect comes from, each outside the functions the branch changes; else why not."""
    top = git('rev-parse', '--show-toplevel').strip()
    tracked, places = git('-C', top, 'ls-files').splitlines(), []
    for p, a, b in PLACE.findall(text):
        q = os.path.relpath(p, top) if os.path.isabs(p) else os.path.normpath(p)  # ./x and /<repo>/x are x
        files = [f for f in tracked if f == q or f.endswith('/' + q)]
        # a path or a file name with an extension is a citation; a bare word (`Makefile`) only when HEAD tracks it, so `10:30` is none
        if files or '/' in p or re.search(r'\w\.\w+$', p): places.append((p, files, int(a), int(b or a)))
    if not places: return 'it names no `path:line` the defect comes from'
    if not base: return "there is no merge-base with the PR's base branch to check its place against"
    funcs = changed(base)
    for p, files, a, b in places:
        if not files: return f'it names {p}, which HEAD does not track'
        if all(b > len(git('show', f'HEAD:{f}').splitlines()) for f in files): return f'it names {p}:{b}, past the end of the file'
        for f in files:
            if any(a <= z and x <= b for x, z in funcs.get(f, ())):
                return f'{p}:{a} is inside a function this branch changes, so the defect is this change\'s to fix'
    return None


def checks(record):
    """The .md files of the task's work folder holding record, past its checkouts and node_modules; outside one, the layout-check.md beside it."""
    if not (root := work_folder.task_of(record)):
        yield from (f for f in [os.path.join(os.path.dirname(os.path.abspath(record)), 'layout-check.md')] if os.path.isfile(f))
        return
    for d, sub, names in os.walk(root):
        sub[:] = [s for s in sub if s != 'node_modules' and not os.path.exists(os.path.join(d, s, '.git'))]
        yield from (os.path.join(d, n) for n in names if n.endswith('.md'))


def task(record, base):
    """Each failing line of the layout-check.md files the task holds, and of the RULED lines of its other files but record (pr-steps
    verify reads those), '<path>: <line>  <- <why>'."""
    bad = []
    for f in checks(record):
        lay, own = os.path.basename(f) == 'layout-check.md', os.path.samefile(f, record)
        for l in open(f, errors='replace').read().splitlines():
            if not lay:  # 'RULED: <candidate>: <ruling>', a walk's too
                if not own and l.startswith('RULED:') and (why := ruled(l, l[6:].strip().partition(': ')[2], base)):
                    bad.append(f'{f}: {l}  <- main having it excuses nothing here: {why}')
            elif (m := OK.match(l.strip())) and m[2].strip(' .'):
                bad.append(f"{f}: {l}  <- a screenshot with anything after OK: write it `{m[1]} — OK`, or each defect it shows as its own line `{m[1]} — <the defect>`")
            elif not m and (why := why_not(l, base)):
                bad.append(f'{f}: {l}  <- main having it excuses nothing here: {why}')
    return bad


if __name__ == '__main__' and sys.argv[1:2] == ['task']:
    bad = task(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '')
    for b in bad: print(b)
    sys.exit(1 if bad else 0)
