#!/usr/bin/env python3
"""shellcmd.Where against bash: a generated corpus of command lines (assignments, cd forms, the dir stack, git -C, subshells, child
shells, heredocs, eval, env, &&, ||, pipes, if, for, while, case, functions, nested two deep; a script word single-, double- or
unquoted, a heredoc quoted or not, a here-string single- or double-quoted, env-prefixed, crossed with cd targets that exist, are
missing, hold a space, are two words, are relative under a CDPATH, or are ~ and - after HOME and OLDPWD are assigned; a $ bash keeps
literal in every quoting that keeps it), each run in real bash from dir A
with stub glab and git that print the dir they run in, and walked by Where. Every posting command Where calls known must have run
in that dir; None (unknown) is always allowed. Usage: tests/where-diff.py [repo root]"""
import os, re, shlex, shutil, subprocess, sys, tempfile

R = os.path.abspath(sys.argv[1] if sys.argv[1:] else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ.setdefault('MERGEWORTHY_PYDEPS', os.path.expanduser('~/.mergeworthy/pydeps'))
T = os.path.realpath(tempfile.mkdtemp(prefix='where-diff-'))
A, B, C, H, BIN, S = (os.path.join(T, n) for n in ('A', 'B', 'C', 'home', 'bin', 'my dir'))
for d in (A, B, C, H, BIN, S, f'{A}/B', f'{A}/$D'):  # A/B: where a relative `cd B` goes without the CDPATH bash searches first; A/$D: a cd to a literal $D
    os.makedirs(d)
for v in ('D', 'E', 'CDPATH', 'OLDPWD', 'BASH_ENV', 'ENV'):
    os.environ.pop(v, None)
os.environ['HOME'] = H  # `cd ~` in bash and in Where
open(f'{BIN}/glab', 'w').write('#!/bin/sh\nfor a; do case "$a" in t[0-9]*) echo "$a $PWD";; esac; done\n')
open(f'{BIN}/git', 'w').write('#!/bin/sh\nwhile [ "$1" = -C ]; do cd "$2" || exit 0; shift 2; done\necho "$1 $PWD"\n')  # git -C, as git applies it
for s in ('glab', 'git'):
    os.chmod(f'{BIN}/{s}', 0o755)
BASH_ENV = {**os.environ, 'PATH': BIN + ':' + os.environ['PATH']}  # Where's own git calls stay the real git
sys.path.insert(0, os.path.join(R, 'hooks'))
import shellcmd

PRELUDES = ['', 'D={B}', 'export D={B}', 'D={B}; E=$D', 'D={T}; D+=/B', 'cd {C}', 'cd {C}; cd {B}', 'declare -x D={B}', 'read D <<< {B}']
MOVERS = ['cd {B}', 'cd "$D"', 'cd $D', 'cd ../B', 'cd ~', 'cd', 'cd -', 'pushd {B} >/dev/null', 'pushd {B} >/dev/null; popd >/dev/null',
          'popd >/dev/null 2>&1', 'cd "$E"', 'declare D={B}; cd "$D"', 'cd {C}; cd -',
          'pushd {B} >/dev/null; cd {C}; popd >/dev/null', 'git -C ../C {G}', ':']
WRAPS = ['{X}', '( {X} )', '{{ {X}; }}', 'bash -c {q}', 'sh -c {q}', "bash <<'{H}'\n{X}\n{H}", 'bash <<< {q}', 'eval {q}',
         'D={C} bash -c {q}', 'D={C} E="$D" bash -c {q}', 'env D={C} E="$D" bash -c {q}', 'env -u D bash -c {q}', 'D={C} eval {q}',
         'true && {X}', 'false || {X}', 'false && {X}', '{X} | cat', 'if true; then {X}; fi', 'if false; then :; else {X}; fi',
         'for i in 1 2; do {X}; done', 'while false; do {X}; done', 'case a in a) {X};; esac', 'f() {{ {X}; }}; f; f',
         'bash -c {dq}', 'bash -c {uq}', 'bash <<{H}\n{X}\n{H}', 'bash <<< {dq}', 'D={C} bash -c {dq}', 'env D={C} bash -c {dq}',
         'D={C} bash <<{H}\n{X}\n{H}', 'D={C} bash <<< {dq}', 'eval {dq}', 'sh -c {dq}']
SCRIPTS = ['{X}', '( {X} )', 'bash -c {q}', "bash <<'{H}'\n{X}\n{H}", 'bash <<< {q}', 'eval {q}'] + WRAPS[23:]  # every way a script word is quoted
TARGETS = [('', '{B}'), ('', '{B}/nope'), ('', '{S}'), ('', '{B} {C}'), ('CDPATH={T}', 'B'), ('', '~'), ('cd {C}; HOME={B}', '~'),
           ('cd {C}; HOME={B}', ''), ('cd {B}; OLDPWD={C}', '-')]  # (what the line sets first, a cd target)
LITS = ["cd '$D'", "cd '${{D}}'", 'cd "\\$D"', 'cd \\$D', "cd $'$D'", "E='$D'; cd \"$E\"", 'E="\\$D"; cd $E', "E=$'\\x24D'; cd \"$E\""]  # a $ bash keeps
PATHS = ['cd {t}', "cd '{t}'", 'cd "{t}"', "D='{t}'; cd $D", "D='{t}'; cd \"$D\""]  # every way a path word is quoted
SUDO = ['sudo bash -c {q}', 'sudo -u nobody sh -c {q}', 'su -c {q} nobody']  # not run: their environment and dir, so Where must call them unknown


def lines():
    """(command line, run it, its environment's additions): every wrapper around every mover after a rotating prelude, pairs of
    wrappers two deep, every script quoting around every cd target, every path quoting of each target, alone, before && and in a chain of
    &&, and every script quoting around every literal $;
    statements on lines of their own (a heredoc's end line holds nothing else)."""
    n = iter(range(1, 10 ** 6))
    def post(): return f'glab mr create --title t{next(n)}'
    def fill(w, x, depth):
        dq = '"' + re.sub(r'([\\"`])', r'\\\1', x) + '"'  # the parent expands its $D
        uq = re.sub(r'([^\w$/.,:=+@%-])', r'\\\1', x.replace('\n', ';'))  # ... and splits what it expands
        return w.format(X=x, q=shlex.quote(x), dq=dq, uq=uq, H=f'EOF{depth}', B=B, C=C, T=T)
    def body(m, sep='\n'): return m.format(B=B, C=C, T=T, S=S, G=f't{next(n)}') + sep + post()
    def line(*xs): return '\n'.join(x for x in xs if x)
    i = 0
    for w in WRAPS:
        for m in MOVERS:
            pre = PRELUDES[i % len(PRELUDES)].format(B=B, C=C, T=T); i += 1
            yield line(pre, fill(w, body(m), 1), post(), f'git -C ../C t{next(n)}'), True, {}
    for j, outer in enumerate(WRAPS[1:12]):
        for k, inner in enumerate(WRAPS[1:12]):
            m = MOVERS[(j + k) % len(MOVERS)]
            yield fill(outer, fill(inner, body(m), 2) + '\n' + post(), 1) + '\n' + post(), True, {}
    for pre, t in TARGETS:
        pre = line(pre, 'export D={C}').format(B=B, C=C, T=T)
        paths = [p.format(t=t) for p in PATHS]
        for k, w in enumerate(SCRIPTS):
            yield line(pre, fill(w, body(paths[k % len(paths)]), 1), post()), True, {}
        for p in paths:
            for w in ('{X}', 'D={C} bash -c {dq}'):
                yield line(pre, fill(w, body(p), 1), post()), True, {}
            yield line(pre, body(p, ' && ')), True, {}
            yield line(pre, body('cd {C} && ' + p, ' && ')), True, {}  # a chain of &&
    for m in LITS:  # with D an existing dir, so expanding the literal $D lands somewhere
        for w in SCRIPTS:
            yield line(f'export D={B}', fill(w, body(m), 1), post()), True, {}
        yield line(f'export D={B}', body(m, ' && ')), True, {}
    for p in PATHS:  # a CDPATH in the environment
        for w in ('{X}', 'bash -c {q}'):
            yield line(fill(w, body(p.format(t='B')), 1), post()), True, {'CDPATH': T}
    for w in SUDO:
        for m in (':', 'cd "$D"', 'cd ../B'):
            yield 'export D={B}\n'.format(B=B) + fill(w, body(m), 1), False, {}


def predicted(cmd):
    """{tag: [the dir Where gives each posting command with that tag]}."""
    out, w = {}, shellcmd.Where(A)
    for t in w.walk(shellcmd.parse(cmd)[0]):
        p = shellcmd.prog(t)
        tag = next((x for x in p if re.fullmatch(r't\d+', x)), None)
        if tag and os.path.basename(p[0]) in ('glab', 'git'):
            out.setdefault(tag, []).append(w.dir if os.path.basename(p[0]) == 'glab' else shellcmd.git_argv(p, w)[0])
    return out


cases = ran = known = 0
bad = []
for cmd, run, extra in lines():
    cases += 1
    os.environ.update(extra)  # Where reads the environment bash gets
    want = predicted(cmd)
    for v in extra: del os.environ[v]
    if not run:
        bad += [(cmd, tag, d, 'unrun: must be unknown') for tag, ds in want.items() for d in ds if d is not None]
        continue
    r = subprocess.run(['bash', '-c', cmd], cwd=A, env={**BASH_ENV, **extra}, stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=20)
    actual = {}
    for l in r.stdout.splitlines():
        tag, _, d = l.partition(' ')
        actual.setdefault(tag, set()).add(os.path.realpath(d))
    for tag, ds in want.items():
        ran += tag in actual
        for d in ds:
            if d is None or tag not in actual:
                continue
            known += 1
            if actual[tag] != {os.path.realpath(d)}:
                bad.append((cmd, tag, d, sorted(actual[tag])))
shutil.rmtree(T)
for cmd, tag, d, got in bad:
    print(f'MISMATCH {tag}: Where says {d}, bash ran it in {got}\n  {cmd!r}')
print(f'where-diff: {cases} command lines, {ran} posting commands run, {known} called known by Where, {len(bad)} mismatches')
sys.exit(1 if bad or not known else 0)
