#!/usr/bin/env python3
"""shellcmd.Where against bash: a generated corpus of command lines (assignments, cd forms, the dir stack, git -C, subshells, child
shells, heredocs, eval, env, &&, ||, pipes, if, for, while, case, functions, nested two deep; a script word single-, double- or
unquoted, a heredoc quoted or not, a here-string single- or double-quoted, env-prefixed, crossed with cd targets that exist, are
missing, hold a space, are two words, are relative under a CDPATH, or are ~ and - after HOME and OLDPWD are assigned; a $ bash keeps
literal in every quoting that keeps it; child shells nested three deep; redirects on cd, pushd and popd; cd to $(...) and `...`; a
negated cd; a line redefining cd, pushd or popd; cd through a symlink, logically and physically; prefix assignments on cd, pushd
and popd; and a fixed list of everyday lines agents type), each run in real bash from dir A
with stub glab, gh and git that print the dir they run in, and walked by Where. Every posting command Where calls known must have run
in that dir; None (unknown) is always allowed. Usage: tests/where-diff.py [repo root]"""
import os, re, shlex, shutil, subprocess, sys, tempfile

R = os.path.abspath(sys.argv[1] if sys.argv[1:] else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
os.environ.setdefault('MERGEWORTHY_PYDEPS', os.path.expanduser('~/.mergeworthy/pydeps'))
T = os.path.realpath(tempfile.mkdtemp(prefix='where-diff-'))
A, B, C, H, BIN, S, G = (os.path.join(T, n) for n in ('A', 'B', 'C', 'home', 'bin', 'my dir', 'repo'))
for d in (A, B, C, H, BIN, S, f'{A}/B', f'{A}/$D', f'{G}/sub', f'{C}/repo', f'{C}/x'):  # A/B: where a relative `cd B` goes without the CDPATH bash searches first; A/$D: a cd to a literal $D
    os.makedirs(d)
os.symlink(f'{C}/repo', f'{A}/link')  # a folder linked into another: cd follows it logically, cd -P physically
GIT = shutil.which('git')
subprocess.run([GIT, 'init', '-q', G], check=True)  # for cd $(git rev-parse --show-toplevel)
open(f'{T}/in.txt', 'w').close()  # an input a redirect can read
for v in ('D', 'E', 'F', 'CDPATH', 'OLDPWD', 'BASH_ENV', 'ENV'):
    os.environ.pop(v, None)
os.environ['HOME'] = H  # `cd ~` in bash and in Where
TAGS = 'for a; do case "$a" in t[0-9]*) echo "$a $PWD";; esac; done\n'  # each tag among its arguments, and the dir
for s in ('glab', 'gh'):
    open(f'{BIN}/{s}', 'w').write('#!/bin/sh\n' + TAGS)
open(f'{BIN}/git', 'w').write('#!/bin/sh\nwhile [ "$1" = -C ]; do cd "$2" || exit 0; shift 2; done\n'  # git -C, as git applies it
                              f'[ "$1" = rev-parse ] && exec {GIT} "$@"\n' + TAGS)
for s in ('glab', 'gh', 'git'):
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
NEST = ['bash -c {q}', 'bash -c {dq}', 'sh -c {q}', 'sh -c {dq}', 'eval {q}', 'eval {dq}', 'bash <<< {q}', 'bash <<< {dq}',
        "bash <<'{H}'\n{X}\n{H}", 'bash <<{H}\n{X}\n{H}', 'D={C} bash -c {dq}', 'D={C} bash -c {q}', 'env D={C} bash -c {dq}', '( {X} )']  # child shells
R = ['>/dev/null', '2>/dev/null', '&>/dev/null', '>&2', '>/dev/null 2>&1']
ODD = [f'cd {{B}} {r}' for r in R] + [f'pushd {{B}} {r}' for r in R] + [f'pushd {{B}} {r}; popd {r}' for r in R] + [f'cd $D {r}' for r in R] + [
    '>/dev/null cd {B}', '2>/dev/null pushd {B}', 'cd $(echo {B})', 'cd "$(echo {B})"', 'cd `echo {B}`', 'cd {G}/sub; cd $(git rev-parse --show-toplevel)',
    'cd {G}/sub; cd "$(git rev-parse --show-toplevel)"', 'cd {G}/sub; cd `git rev-parse --show-toplevel`', '! cd {B}', '! cd {B}/nope',
    'cd() {{ :; }}; cd {B}', 'function cd {{ builtin cd {C}; }}; cd {B}', 'pushd() {{ :; }}; pushd {B}', 'popd() {{ builtin cd {C}; }}; pushd {B}; popd',
    "shopt -s expand_aliases\nalias cd='builtin cd {C}'\ncd {B}"] + [
    f'{c} {r}' for c in ('cd {B}', 'pushd {B}', 'pushd {B} >/dev/null; popd') for r in (
        '>$F', '>"$F"', '>/nonexistent/x', '2>{T}/nodir/x', '<{T}/missing', '>{B}', '>{T}/out.txt', '>>{T}/out.txt', '<{T}/in.txt')] + [
    '! {{ cd {B}/nope; }}', '! {{ cd {B}; }}', "! eval 'cd {B}/nope'", "! eval 'cd {B}'", '! ( cd {B}/nope )', 'f() {{ cd {B}/nope; }}; ! f',
    '! {{ true && cd {B}/nope; }}'] + [  # redirects, substitutions, negation, a redefined cd; redirects that fail, negated groups
    'cd {A}/link; cd ..', 'cd {A}/link/..', 'cd -L {A}/link/..', 'cd -P {A}/link/..', 'cd -P {A}/link; cd ..', 'cd {A}/link; cd -P ..',
    'cd {A}/link/../x', 'cd -P {A}/link/../x', 'cd {A}/link; cd ..; cd -', 'cd {A}/link && cd .. && :', 'pushd {A}/link >/dev/null; cd ..',
    'pushd {A}/link/.. >/dev/null', 'cd {A}/link; pushd .. >/dev/null', 'pushd {A}/link >/dev/null; pushd {B} >/dev/null; popd >/dev/null',
    'set -P; cd {A}/link; cd ..', 'set -o physical; cd {A}/link/..'] + [  # symlinks
    'CDPATH={C} cd repo', 'CDPATH= cd B', 'HOME={C} cd', 'HOME={C} cd ~', 'cd {B}; OLDPWD={C} cd -', 'CDPATH={C} pushd repo >/dev/null',
    'cd {B} && pushd {C} >/dev/null && HOME={B} popd >/dev/null', 'env CDPATH={C} cd repo', 'env cd {B}', 'nice cd {B}', 'command cd {B}',
    'CDPATH={C} builtin cd repo', 'CDPATH={C} cd repo; cd repo', 'X=1 cd {B}', 'PWD={C} cd ..', 'CDPATH={C} command cd repo'] + [  # prefixes
    f'D={{B}}; {v}={{C}} {c} {w}' for v in ('D', 'HOME', 'CDPATH', 'OLDPWD', 'PWD') for c in ('cd', 'pushd')
    for w in (f'${v}', f'${{{{{v}}}}}', f'"${v}"', f'{{B}} >"${v}/out.txt"', f'{{B}} 2>${{{{{v}}}}}/err.txt')] + [
    'HOME={C} cd ~', 'HOME={C} cd ~/x', 'HOME={C} pushd ~ >/dev/null', 'D={B}; D={C} cd "$D" && :', 'cd {B}; OLDPWD={C} cd "$OLDPWD"',
    'D={B}; pushd {C} >/dev/null; D={T} popd >"$D/out.txt"']  # a prefix's variable in the words and redirects, which see the line's
EVERYDAY = [  # lines agents typed (Claude Code transcripts on this machine, 2026-10), their paths made the corpus's and other commands harmless ones
    'cd {B} && git push -u origin {G} 2>&1 | tail -6; git rev-parse HEAD',
    'cd {B}; glab issue view 1 --comments 2>&1 | head -40; glab mr create --title {G}',
    'cd {B} && glab mr create --title {G} 2>&1 | sed -n 1,20p',
    'cd {T} && rm -f nothing.yml; cd B && git push -u origin {G} 2>&1 | tail -5; git log --oneline -1',
    'cd {B} && D={C} && glab mr update 1 --description "$(cat $D/none 2>/dev/null)" --title {G} 2>&1 | tail -1',
    'cd {B} && git fetch -q origin && git merge-base --is-ancestor origin/x HEAD && echo on-top && git push https://example.invalid/r.git {G} 2>&1 | tail -3',
    'cd {B} && U=$(git remote get-url origin 2>/dev/null); echo "$U"; git push -q "$U" {G} 2>&1 | tail -3',
    'cd {B}; for n in 1 2; do glab mr view $n --comments > /dev/null 2>&1 & done; wait; glab mr create --title {G}',
    'cd {B} && gh pr create --draft --base main --title {G} --body x 2>&1 | tail -3',
    'cd {B} && gh pr checks 16 2>&1 | head; gh pr comment 1 --body {G}',
    'cd {B} && cat <<< "x" > /dev/null; echo "exit $?"; git push https://example.invalid/r.git {G} 2>&1 | tail -5',
    "cd {B} && git log -1 --format='%an <%ae>' && git push https://example.invalid/r.git {G} 2>&1 | tail -4",
    'cd {B} && git status --short; git log --oneline -3; git push -u origin {G} 2>&1 | tail -4; git rev-parse HEAD',
    'cd {B} && true 2>&1 | tail -2 && git push -u origin {G} 2>&1 | tail -4',
    'pushd {B} >/dev/null && gh pr create --title {G}; popd >/dev/null',
    'cd {G}/sub && cd "$(git rev-parse --show-toplevel)" && gh pr create --title {G}',
    'cd {G}/sub && cd $(git rev-parse --show-toplevel) && gh pr create --title {G}',
    'cd {B} 2>/dev/null && glab mr create --title {G}',
    'mkdir -p ~/w && cd ~/w && gh pr create --title {G}',
    'W={B}; cd $W && git push origin {G}',
    'cd {B} && git add -A && git commit -qm x && git push origin {G} && gh pr create --title {G}',
    'cd {B} || exit 1; gh pr create --title {G}',
    'set -e; cd {B}; glab mr create --title {G}',
    'cd {B} && git -C {C} push origin {G} 2>&1 | tail -2',
    'cd {B} D={C} glab mr create --draft --title {G}',  # from here on, Where may say unknown: cd gets three arguments and fails,
    'mkdir -p {T}/new && cd {T}/new && cd {B} && for n in 1 2; do glab issue view $n > /dev/null 2>&1; done; glab mr create --title {G}']  # the cds may not run
SUDO = ['sudo bash -c {q}', 'sudo -u nobody sh -c {q}', 'su -c {q} nobody']  # not run: their environment and dir, so Where must call them unknown


def lines():
    """(command line, run it, its environment's additions, whether each posting command must be called known): every wrapper around every mover after a rotating prelude, pairs of
    child shells two and three deep, odd cd forms, the everyday lines, every script quoting around every cd target, every path quoting of each target, alone, before && and in a chain of
    &&, and every script quoting around every literal $;
    statements on lines of their own (a heredoc's end line holds nothing else)."""
    n = iter(range(1, 10 ** 6))
    def post(): return f'glab mr create --title t{next(n)}'
    def fill(w, x, depth):
        dq = '"' + re.sub(r'([\\"`])', r'\\\1', x) + '"'  # the parent expands its $D
        uq = re.sub(r'([^\w$/.,:=+@%-])', r'\\\1', x.replace('\n', ';'))  # ... and splits what it expands
        return w.format(X=x, q=shlex.quote(x), dq=dq, uq=uq, H=f'EOF{depth}', B=B, C=C, T=T)
    def body(m, sep='\n'): return m.replace('{G}/', G + '/').format(A=A, B=B, C=C, T=T, S=S, G=f't{next(n)}') + sep + post()
    def line(*xs): return '\n'.join(x for x in xs if x)
    i = 0
    for w in WRAPS:
        for m in MOVERS:
            pre = PRELUDES[i % len(PRELUDES)].format(B=B, C=C, T=T); i += 1
            yield line(pre, fill(w, body(m), 1), post(), f'git -C ../C t{next(n)}'), True, {}, False
    for j, outer in enumerate(NEST):  # two and three deep, the parent's D differing from the prefix's
        for k, inner in enumerate(NEST):
            m = MOVERS[(j + k) % len(MOVERS)]
            yield line('export D={B}'.format(B=B), fill(outer, fill(inner, body(m), 2) + '\n' + post(), 1), post()), True, {}, False
            third = NEST[(j * 5 + k) % len(NEST)]
            yield line('export D={B}'.format(B=B), fill(outer, fill(inner, fill(third, body(m), 3) + '\n' + post(), 2) + '\n' + post(), 1), post()), True, {}, False
    for k, m in enumerate(ODD):
        for w in ('{X}', 'bash -c {q}', 'bash -c {dq}', 'eval {q}', '( {X} )'):
            yield line('export D={B}'.format(B=B), fill(w, body(m), 1), post()), True, {}, False
        yield line('export D={B}'.format(B=B), body(m, ' && ')), True, {}, False
    for k, m in enumerate(EVERYDAY):
        yield m.replace('{G}/', G + '/').format(B=B, C=C, T=T, G=f't{next(n)}'), True, {}, k < len(EVERYDAY) - 2
    for pre, t in TARGETS:
        pre = line(pre, 'export D={C}').format(B=B, C=C, T=T)
        paths = [p.format(t=t) for p in PATHS]
        for k, w in enumerate(SCRIPTS):
            yield line(pre, fill(w, body(paths[k % len(paths)]), 1), post()), True, {}, False
        for p in paths:
            for w in ('{X}', 'D={C} bash -c {dq}'):
                yield line(pre, fill(w, body(p), 1), post()), True, {}, False
            yield line(pre, body(p, ' && ')), True, {}, False
            yield line(pre, body('cd {C} && ' + p, ' && ')), True, {}, False  # a chain of &&
    for m in LITS:  # with D an existing dir, so expanding the literal $D lands somewhere
        for w in SCRIPTS:
            yield line(f'export D={B}', fill(w, body(m), 1), post()), True, {}, False
        yield line(f'export D={B}', body(m, ' && ')), True, {}, False
    for p in PATHS:  # a CDPATH in the environment
        for w in ('{X}', 'bash -c {q}'):
            yield line(fill(w, body(p.format(t='B')), 1), post()), True, {'CDPATH': T}, False
    for w in SUDO:
        for m in (':', 'cd "$D"', 'cd ../B'):
            yield 'export D={B}\n'.format(B=B) + fill(w, body(m), 1), False, {}, False


def predicted(cmd):
    """{tag: [the dir Where gives each posting command with that tag]}."""
    out, w = {}, shellcmd.Where(A)
    for t in w.walk(shellcmd.parse(cmd)[0]):
        p = shellcmd.prog(t)
        tag = next((x for x in p if re.fullmatch(r't\d+', x)), None)
        if tag and os.path.basename(p[0]) in ('glab', 'gh', 'git'):
            out.setdefault(tag, []).append(shellcmd.git_argv(p, w)[0] if os.path.basename(p[0]) == 'git' else w.dir)
    return out


cases = ran = known = 0
bad = []
for cmd, run, extra, must in lines():
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
        if re.fullmatch(r't\d+', tag): actual.setdefault(tag, set()).add(os.path.realpath(d))
    bad += [(cmd, tag, None, 'everyday: must be known') for tag in actual if must and None in want.get(tag, [None])]
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
