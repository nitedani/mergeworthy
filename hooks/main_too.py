#!/usr/bin/env python3
"""Whether main's having a defect excuses it, decided by where the defect comes from (converge step 1, evidence step 4): a ruling
that says main has it, and a defect line left in a layout check, names the `path:line` (or `path:a-b`) it comes from, a file HEAD
tracks, outside every function the branch changes since the PR's base (`git diff -W`), else it excuses nothing. pr-steps reads it,
in the file a step is given and no other.
`main_too.py layout <a layout check> <base>`: prints each line of it that fails, and exits 1 when one does."""
import os, re, subprocess, sys

MAIN = re.compile(r"not a regression|pre-?existing|already exist(s|ed)?\b|\b(default|base) branch\b|\bbaseline\b|not caused by (this|the) (pr|change)|masteren is|same as (on )?(main|master)"
                  r"|\b(on|in) (main|master)\b(?! session| thread)|\b(main|master)('s\b| (too|as well|does|has|had|shows))", re.I)
PLACE = re.compile(r'(?<![\w./@~+-])([\w./@~+-]*[\w@~+-]):(\d+)(?:-(\d+))?')  # src/panel.tsx:12, ./panel.tsx:5-6, /abs/path.ts:3, Makefile:2


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


def excuse(why, base):
    """None when a ruling's text, after its candidate, is a bug, a reason no user meets it, or says nothing of main; else why it excuses nothing."""
    if re.search(r'earn every line|no realistic usage|contrived|staged race', why, re.I) or re.match(r'\s*(a bug|bug|fix(ed)?\b)', why, re.I): return None
    return place(why, base) if MAIN.search(why) else None


def place(text, base):
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


def layout(file, base):
    """Each failing line of a layout check, '<line>  <- <why>': a line is `<file name> — OK`, or `<file name> — <the defect>` naming
    the place the defect comes from, outside the functions the branch changes; a heading or a blank line is neither."""
    bad = []
    for l in open(file, errors='replace').read().splitlines():
        if not l.strip() or l.startswith('#'): continue
        m = re.match(r'(.+?)\s[—–-]\s+(OK\b)?(.*)$', l.strip())
        if not m: why = 'no layout line: write `<file name> — OK` or `<file name> — <the defect>`'
        elif m[2]: why = m[3].strip(' .') and f'a screenshot with anything after OK: write it `{m[1]} — OK`, or each defect it shows as its own line `{m[1]} — <the defect>`'
        else: why = (w := place(m[3], base)) and f'a defect left in the check names the place it comes from, `{m[1]} — <the defect>, from <path:line>`: {w}'
        if why: bad.append(f'{l}  <- {why}')
    return bad


if __name__ == '__main__' and sys.argv[1:2] == ['layout']:
    bad = layout(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '')
    for b in bad: print(b)
    sys.exit(1 if bad else 0)
