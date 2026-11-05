"""Shell command parsing and transcript reading shared by the hooks (pre-bash-guard, pre-design-gate, pre-skill-gate,
post-bash-register, stop-lint).
parse() reads a command with mvdan/sh, bash's syntax as shfmt parses it (hooks/requirements.txt, installed on first use into
~/.mergeworthy/pydeps): every simple command it runs, in substitutions, heredocs a shell reads, `bash -c` and `eval` too. A
command that doesn't parse, or a parser that can't be installed, yields the command's words split roughly, with the error,
so a hook checks what it can and blocks a guarded verb it can't check."""
import fnmatch, functools, glob, hashlib, itertools, json, os, re, subprocess, sys
import work_folder


def branch_record(d, kind, branch=None):
    """The pr-steps record kept once per repo and branch (preflight, approach; bin/pr-steps writes through it) of branch, by default the
    checked-out one; None outside git."""
    git = lambda *a: subprocess.run(['git', '-C', d, *a], capture_output=True, text=True).stdout.strip()
    common = git('rev-parse', '--git-common-dir')
    if not common:
        return None
    root = os.path.realpath(os.path.join(d, common))
    rec = lambda b: os.path.expanduser(f'~/.claude/pr-steps/{kind}.' + hashlib.sha256((root + '\n' + b).encode()).hexdigest()[:40])
    branch = branch or git('symbolic-ref', '--short', '-q', 'HEAD') or 'HEAD'
    # a worktree on its own local branch tracking the PR's branch, pushed (refs/remotes/<remote>/…) or local, shares that branch's records
    up = re.sub(r'^refs/(remotes/[^/]+|heads)/', '', git('for-each-ref', '--format=%(upstream)', f'refs/heads/{branch}'))
    return next((rec(b) for b in (branch, up) if b and os.path.exists(rec(b))), rec(branch))


def folder(path):
    """path when it is a folder, else its nearest existing parent (a new file's folder may not exist yet)."""
    return next(p for p in work_folder.ancestors(os.path.realpath(path)) if os.path.isdir(p))


def waits_for(path, kind):
    """Whether code in the repo and branch holding path waits for its kind of record (preflight, approach): not outside git, nor on a branch
    sharing no history with the remote's default branch, such as one holding a PR's screenshots, which holds no code of the product."""
    d = folder(path)
    rec = branch_record(d, kind)
    return bool(rec) and not os.path.exists(rec) and \
        subprocess.run(['git', '-C', d, 'merge-base', 'HEAD', 'refs/remotes/origin/HEAD'], capture_output=True).returncode != 1


def no_preflight(path):
    """Why code can't start yet in the repo and branch holding path for want of its preflight (pull-request step 2), or ''."""
    return waits_for(path, 'preflight') and ("no `pr-steps preflight` record for this repo and branch. Before any code, start the app, then run "
            "`pr-steps preflight <its URL> [Chrome flags]` (or `<PNG the session's browser MCP just took>`), "
            "or `pr-steps preflight 'none, because <why there is no UI or browser-run code>'`") or ''


def no_approach(path):
    """Why code can't start yet in the repo and branch holding path for want of its approach (pull-request step 5), or ''."""
    return waits_for(path, 'approach') and (
        "no `pr-steps approach` record for this repo and branch. Before any code, rate the approaches (mergeworthy:pull-request step 5), "
        "then `pr-steps approach <work folder>/approach.md`. A worktree on its own branch for a PR's work tracks that PR's branch "
        "(`git branch -u <its branch>`) and shares its record") or ''


SHELLS = ('bash', 'sh', 'zsh', 'dash', 'ksh', 'fish')
REQUIREMENTS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'requirements.txt')


def _deps():
    """The folder holding the pinned parser, installed on first use with uv, else pip, one install at a time. After a failed
    install its error is raised again at once for 5 minutes, then the install is retried."""
    import fcntl, shutil, tempfile, time
    base = os.environ.get('MERGEWORTHY_PYDEPS') or os.path.expanduser('~/.mergeworthy/pydeps')
    target = os.path.join(base, hashlib.sha256(open(REQUIREMENTS, 'rb').read()).hexdigest()[:16])
    if os.path.isdir(target):
        return target
    os.makedirs(base, exist_ok=True)
    with open(os.path.join(base, '.lock'), 'w') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        failed = target + '.failed'
        if os.path.isdir(target):
            return target
        if os.path.exists(failed) and time.time() - os.path.getmtime(failed) < 300:
            raise RuntimeError(open(failed).read())
        uv = shutil.which('uv') or next((p for p in map(os.path.expanduser, ('~/.local/bin/uv', '~/.cargo/bin/uv')) if os.access(p, os.X_OK)), None)
        tmp = tempfile.mkdtemp(dir=base)
        cmd = ([uv, 'pip', 'install', '--python', sys.executable] if uv else [sys.executable, '-m', 'pip', 'install']) + \
              ['--quiet', '--only-binary', ':all:', '--require-hashes', '--target', tmp, '-r', REQUIREMENTS]
        try: r = subprocess.run(cmd, capture_output=True, text=True, timeout=240)
        except (OSError, subprocess.TimeoutExpired) as e: r = subprocess.CompletedProcess(cmd, 1, '', str(e))
        if r.returncode:
            shutil.rmtree(tmp, ignore_errors=True)
            open(failed, 'w').write(f"its install failed ({(r.stderr or r.stdout).strip()[-300:]}); install uv (https://docs.astral.sh/uv/) "
                                    f"or pip, or run `{' '.join(cmd).replace(tmp, target)}`, then retry")
            raise RuntimeError(open(failed).read())
        os.rename(tmp, target)
    return target


def _src(n, src):
    return src[n['Pos']['Offset']:n['End']['Offset']].decode(errors='replace')


class Word(str):
    """A word as bash passes it (_word), with parts, each a tuple its kind leads: ('lit', text), ('var', name), ('exp', name, op, its word),
    ('repl', name, all, pattern, replacement), ('sub', each pipeline stage's argv, None when it's anything else), ('piece',), a number, or ('opaque',).
    bare: its literal text outside quotes, where bash reads braces and globs; splits: whether an expansion stands outside double quotes;
    quoted: whether a part is quoted or escaped, which bash doesn't split."""
    def __new__(cls, text, parts=(), bare='', splits=False, quoted=False):
        w = super().__new__(cls, text)
        w.parts, w.bare, w.splits, w.quoted = tuple(parts), bare, splits, quoted
        return w


def _stages(s, src):
    """The argv of each stage of the statement s, a plain pipeline with no redirect; None for anything else."""
    c = s.get('Cmd') or {}
    if s.get('Redirs') or s.get('Negated') or s.get('Background'):
        return None
    if c.get('Type') == 'CallExpr' and not c.get('Assigns'):
        return [[_word(a, src) for a in c.get('Args') or []]]
    if c.get('Type') != 'BinaryCmd' or c.get('Op') != '|':
        return None
    x, y = _stages(c['X'], src), _stages(c['Y'], src)
    return x + y if x and y else None


def _readers(tree, src):
    """The argv of the stages after the first, by the first's statement, of each plain pipeline (_stages) that is a statement of the line's own list or the last side of one's && or ||."""
    out = {}
    for s in tree.get('Stmts') or []:
        while (s.get('Cmd') or {}).get('Type') == 'BinaryCmd' and s['Cmd'].get('Op') in ('&&', '||'):
            s = s['Cmd']['Y']
        if stages := _stages(s, src):
            while (s.get('Cmd') or {}).get('Type') == 'BinaryCmd':
                s = s['Cmd']['X']
            out[id(s)] = stages[1:]
    return out


def _expansion(p, src):
    """The part (Word.parts) of an expansion's node."""
    t, name = p.get('Type'), (p.get('Param') or {}).get('Value')
    if t == 'ArithmExp' or t == 'ParamExp' and p.get('Length'):
        return ('piece',)
    if t == 'CmdSubst' and not p.get('Backquotes'):
        stmts = p.get('Stmts') or []
        return ('sub', _stages(stmts[0], src) if len(stmts) == 1 else None)
    if t != 'ParamExp' or not name or any(p.get(k) for k in ('Excl', 'Width', 'Index', 'Slice', 'Names')):
        return ('opaque',)
    if e := p.get('Exp'):
        return ('exp', name, e['Op'], _word(e.get('Word') or {}, src))
    if r := p.get('Repl'):
        return ('repl', name, bool(r.get('All')), _word(r.get('Orig') or {}, src), _word(r.get('With') or {}, src))
    return ('var', name)


def _word(w, src):
    """A word as bash passes it: quotes and escapes removed; expansions and substitutions as written."""
    out, parts, bare, splits, quoted = [], [], '', False, False
    def add(text, part=None):
        out.append(text)
        parts.append(part or ('lit', text))
    for p in w.get('Parts') or []:
        t, v = p.get('Type'), p.get('Value', '')
        if t == 'Lit':
            bare, quoted = bare + v, quoted or '\\' in v
            add(re.sub(r'\\(.)', r'\1', v.replace('\\\n', ''), flags=re.S))
        elif t == 'SglQuoted':
            quoted = True
            add(v.encode('latin-1', 'backslashreplace').decode('unicode_escape', 'replace') if p.get('Dollar') else v)
        elif t == 'DblQuoted':
            quoted = True
            for x in p.get('Parts') or []:
                if x.get('Type') == 'Lit': add(re.sub(r'\\([$`"\\])', r'\1', x.get('Value', '').replace('\\\n', '')))
                else: add(_src(x, src), _expansion(x, src))
        else:
            splits = True
            add(_src(p, src), _expansion(p, src))
    return Word(''.join(out), parts, bare, splits, quoted)


def _assign(a, src):
    if a.get('Naked'):
        return a['Name']['Value'] if a.get('Name') else _word(a['Value'], src)
    name = a['Name']['Value'] + '='
    if a.get('Array'):
        return Word(name + _src(a['Array'], src), [('lit', name), ('opaque',)])
    w = _word(a.get('Value') or {}, src)
    return Word(name + w, [('lit', name), *w.parts])


# The kinds of scope a command runs in (Seg.scopes): a cd in an isolating one never reaches what follows it (Where)
ISOLATING, CONDITIONAL, LOOP = 'isolating', 'conditional', 'loop'
_ids = itertools.count()
STDIN, CHILD = '<<', '-c'


def _scope(kind, name='', items=()):
    """A new scope of kind, for Seg.scopes; name: the function whose body it is, a for loop's variable, CHILD for the script a child
    shell runs (`bash -c`), which gets none of the line's unexported variables, so it starts with them unknown, or STDIN for the script
    a shell reads from a heredoc or <<<, which may run after later commands of the line moved, so it starts knowing nothing; items: the
    words the loop's variable takes."""
    return ((next(_ids), kind, name, items),)


class Seg(list):
    """A simple command's argv; scopes: the (id, kind, function name) of each scope it runs in, outermost first, for Where; loop: whether it
    runs inside a while or until loop; raw: each word's source as written, None when not known; unseen: the
    names its script, or a script running it, may set where Where can't follow (_unseen), whose values it never trusts; nested: whether
    it is in a script the line runs (`eval`'s included), where a plain walk loses the dir (Where); after: each statement that exited 0 if this
    one runs at all, being before it in a chain of && (_passed); stmt: the statement it runs as, for after to name; readers: the argv of each
    command its output is piped to, when nothing else takes its output or status (_readers), else None."""
    scopes, loop, raw, unseen, nested, after, stmt, readers = (), False, None, frozenset(), False, (), None, None


def _seg(argv, scopes=(), loop=False, raw=None, after=(), stmt=None):
    s = Seg(argv)
    s.scopes, s.loop, s.raw, s.after, s.stmt = scopes, loop, raw, after, stmt
    return s


def _kind(x, k):
    """The kind of scope node x's child k runs in of its own, or None when it runs in x's."""
    t = x.get('Type')
    if t in ('Subshell', 'CmdSubst', 'ProcSubst', 'CoprocClause') or k == 'Cmd' and x.get('Background') or t == 'BinaryCmd' and x.get('Op') in ('|', '|&'):
        return ISOLATING
    if t in ('WhileClause', 'ForClause'):
        return LOOP
    if t in ('IfClause', 'CaseClause', 'FuncDecl') or k == 'Cmd' and x.get('Negated') or t == 'BinaryCmd' and x.get('Op') == '||' and k == 'Y':
        return CONDITIONAL
    return None


class _Every:
    """Every name: what _unseen gives for a line that may set any variable."""
    def __contains__(self, name): return True


EVERY = _Every()


SETTERS = ('read', 'mapfile', 'readarray', 'unset', 'getopts', 'wait')  # builtins that set the variables they name (printf: -v's)
ASSIGNS = ('=', '+=', '-=', '*=', '/=', '%=', '<<=', '>>=', '&=', '^=', '|=', '++', '--')


def _name(w):
    """The variable a word names, its identifier prefix (`D=x`, `D[0]` -> D), or None for a word that names none (-r, 5)."""
    m = re.match(r'[A-Za-z_]\w*', w)
    return m and m[0]


def _unseen(tree, src):
    """The names a script may set where Where can't follow, read from its syntax: a name assigned other than by a command of only
    `NAME=value` words, or those after export, readonly, declare or a function's local (export -n D=x, typeset, D+=x, D[1]=x, D=x cmd), one a builtin sets (read, mapfile, printf -v, unset, getopts, wait -p),
    ${D:=x}, an arithmetic assignment ((( )), $(( )), let), and a for loop's variable assigned anywhere; EVERY when it runs eval,
    source, . or trap, which can set any. Heredoc bodies and quoted text are words, never read as commands."""
    names, assigned, loops, todo = set(), set(), set(), [(tree, False)]  # each node, and whether it is in a function's body
    while todo:
        y, body = todo.pop()
        if isinstance(y, list):
            todo += [(x, body) for x in y]
            continue
        if not isinstance(y, dict):
            continue
        cmd, t = y.get('Cmd') or {}, y.get('Type')
        plain = lambda assigns: not y.get('Redirs') and not any(a.get('Index') or a.get('Append') or a.get('Naked') for a in assigns)  # Where.step's: D=x, not D[1]=x, D+=x or D=x >f
        if cmd.get('Type') == 'CallExpr':
            assigns = cmd.get('Assigns') or []
            (assigned if not cmd.get('Args') and plain(assigns) else names).update(a['Name']['Value'] for a in assigns if a.get('Name'))
            argv = prog([_word(w, src) for w in cmd.get('Args') or []])
            name = os.path.basename(argv[0]) if argv else ''
            if name in ('eval', 'source', '.', 'trap'):
                return EVERY
            if name in SETTERS:
                names.update(map(_name, argv[1:]))
            elif name == 'printf':
                names.update(_name(argv[i + 1]) for i in range(1, len(argv) - 1) if argv[i] == '-v')
        elif cmd.get('Type') == 'DeclClause':
            args = cmd.get('Args') or []
            variant = cmd['Variant']['Value']
            taken = (variant in ('export', 'readonly', 'declare') or variant == 'local' and body) and plain(args)  # Where.step's: export D=x, not export -n D=x
            (assigned if taken else names).update(a['Name']['Value'] if a.get('Name') else _name(_word(a['Value'], src)) for a in args)
        if t == 'ParamExp' and (y.get('Exp') or {}).get('Op') in ('=', ':=') and y.get('Param'):
            names.add(y['Param']['Value'])
        if t in ('BinaryArithm', 'UnaryArithm') and y.get('Op') in ASSIGNS and (y.get('X') or {}).get('Type') == 'Word':
            names.add(_name(_word(y['X'], src)))
        if t == 'ForClause' and (y.get('Loop') or {}).get('Name'):
            loops.add(y['Loop']['Name']['Value'])
        todo += [(v, body or t == 'FuncDecl') for v in y.values() if isinstance(v, (dict, list))]
    return frozenset(names - {None} | assigned & loops)


def _passed(s, src):
    """Each plain command's statement that exited 0 when statement s did: s itself, or each side of a &&; none under a negation, pipe or ||."""
    c = s.get('Cmd') or {}
    if s.get('Negated'):
        return ()
    if c.get('Type') == 'CallExpr':
        return (s,)
    return _passed(c['X'], src) + _passed(c['Y'], src) if c.get('Type') == 'BinaryCmd' and c.get('Op') == '&&' else ()


def _calls(node, src):
    """(the argv of every simple command under node, in order, each a Seg; the statements each heredoc of them is read by:
    (redirect, top statement, whether it is in a loop))."""
    segs, docs, stack = [], [], [(node, None, (), False, ())]
    while stack:
        x, top, n, loop, after = stack.pop()
        if isinstance(x, list):
            stack += [(y, top, n, loop, after) for y in reversed(x)]
            continue
        if not isinstance(x, dict):
            continue
        loop = loop or x.get('Type') == 'WhileClause'  # shfmt's node for until too
        var = ((x.get('Loop') or {}).get('Name') or {}).get('Value', '') if x.get('Type') == 'ForClause' else ''
        items = tuple(_word(w, src) for w in x['Loop'].get('Items') or []) if var else ()
        name = x['Name']['Value'] if x.get('Type') == 'FuncDecl' else var
        inner = {k: n + _scope(kind, name, items) if (kind := _kind(x, k)) else n for k, v in x.items() if isinstance(v, (dict, list))}
        cmd, redirs = x.get('Cmd') or {}, x.get('Redirs') or []
        words = [w for r in redirs for w in ((r.get('N') or {}).get('Value', '') + r['Op'], _word(r.get('Word') or {}, src))]
        raws = [w for r in redirs for w in (r['Op'], _src(r['Word'], src) if r.get('Word') else '')]
        if cmd.get('Type') == 'CallExpr':
            segs.append(_seg([_assign(a, src) for a in cmd.get('Assigns') or []] + [_word(a, src) for a in cmd.get('Args') or []] + words, inner['Cmd'], loop,
                             [_src(a, src) for a in (cmd.get('Assigns') or []) + (cmd.get('Args') or [])] + raws, after, x))
        elif cmd.get('Type') == 'DeclClause':
            segs.append(_seg([cmd['Variant']['Value']] + [_assign(a, src) for a in cmd.get('Args') or []] + words, inner['Cmd'], loop,
                             [cmd['Variant']['Value']] + [_src(a, src) for a in cmd.get('Args') or []] + raws, after, x))
        docs += [(r, top or x, loop) for r in redirs if r.get('Hdoc')]
        chained = _passed(x['X'], src) if x.get('Type') == 'BinaryCmd' and x.get('Op') == '&&' else ()
        stack += [(v, None if k == 'Stmts' else (top or x) if 'Cmd' in x else top, inner[k], loop, after + chained if k == 'Y' else after)  # each statement of a list is a top statement
                  for k, v in reversed(x.items()) if isinstance(v, (dict, list)) and k not in ('Pos', 'End', 'Hdoc')]
    return segs, docs


def _segments(tree, src, depth):
    """(every simple command the tree runs, with each heredoc's commands: its substitutions, or all of it when a shell
    without a script reads it (`bash <<EOF`, `cat <<EOF | sh`); the error of a heredoc script that doesn't parse)."""
    (segs, docs), err = _calls(tree, src), ''
    for r, top, loop in docs:
        if any(reads_stdin(a) for a in _calls(top, src)[0]) and depth < 4:
            s, e = parse(''.join(_src(p, src) for p in r['Hdoc'].get('Parts') or []), depth + 1, _scope(ISOLATING, STDIN), loop)
        else:
            s, e = _segments(r['Hdoc'], src, depth)
        segs, err = segs + s, err or e
    return segs, err


def reads_stdin(t):
    """Whether argv t is a shell that runs what its stdin carries: no script operand, `-s`, or the script /dev/stdin."""
    t = prog(t)
    if not t or os.path.basename(t[0]) not in SHELLS or _nested(t) is not None: return False
    ops = [x for x in operands(t[1:]) if not x.startswith(('-', '+'))]
    return not ops or ops[0] in ('/dev/stdin', '-') or any(re.fullmatch(r'-[a-zA-Z]*s[a-zA-Z]*', x) for x in t[1:])


REDIR = re.compile(r'\d*(?:&>>?|<<<|<<-?|<>|<&|>&|>>|>\||<|>)')


def operands(a):
    """An argv's words minus its redirections and their targets."""
    out, skip = [], False
    for w in a:
        if skip: skip = False
        elif REDIR.fullmatch(w): skip = True
        else: out.append(w)
    return out


def _rough(cmd):
    """Words of a command that doesn't parse: quotes dropped, split at every separator; a guarded verb still shows."""
    return [p.split() for p in re.split(r'[;&|()\n`]+', unquoted(cmd)) if p.split()]


def unquoted(cmd):
    """cmd with its quote characters and escapes dropped: `"g"it push` reads git push."""
    return re.sub(r'[\'"\\]', '', cmd)


def _nested(t):
    """The script a segment runs as a further command: `bash -c '<script>'`, `eval <words>`; else None."""
    t = prog(t)
    name, a = (os.path.basename(t[0]), t[1:]) if t else ('', [])
    if name == 'eval' or t[:1] and ' ' in t[0]:  # eval's words, or a script handed to a wrapper as one word
        return ' '.join(t if ' ' in t[0] else a)
    if name in ('su', 'runuser', 'script'):  # -c <command>, also in a flag group (`script -qc`)
        return next((a[i + 1] for i in range(len(a) - 1) if re.fullmatch(r'-[a-zA-Z]*c|--command', a[i])), None)
    if name in SHELLS:
        i, c = 0, False
        while i < len(a) and a[i][:1] in '-+' and a[i] != '-':
            if a[i] == '--': i += 1; break
            c = c or re.fullmatch(r'-[a-zA-Z]*c[a-zA-Z]*', a[i]) is not None
            i += 2 if a[i] in ('-o', '+o', '-O', '+O') else 1
        return a[i] if c and i < len(a) else None
    return None


def parse(cmd, depth=0, scopes=(), loop=False):
    """(segments, error): the argv of every simple command cmd runs, each a Seg (in scopes, loop: all of them), command substitutions and
    the scripts of `bash -c` and `eval` included; error is '' when it parsed, else why not (the segments are then _rough's, each in a
    conditional scope of its own)."""
    try:
        r = subprocess.run([os.path.join(_deps(), 'bin', 'shfmt'), '--to-json', '-ln', 'bash'], input=cmd.encode(), capture_output=True, timeout=60)
        if r.returncode:
            raise ValueError('bash syntax error at ' + r.stderr.decode(errors='replace').strip().replace('<standard input>:', ''))
        tree = json.loads(r.stdout)
        (segs, err), unseen = _segments(tree, cmd.encode(), depth), _unseen(tree, cmd.encode())
        if not depth:  # a script's own list may be what a substitution reads
            readers = _readers(tree, cmd.encode())
            for x in segs: x.readers = readers.get(id(x.stmt))
    except ValueError as e:  # also a JSON error
        segs, err, unseen = [_seg(x, _scope(CONDITIONAL)) for x in _rough(cmd)], str(e), EVERY
    except Exception as e:  # no parser: nothing is checked as parsed, and a guarded verb blocks
        segs, err, unseen = [_seg(x, _scope(CONDITIONAL)) for x in _rough(cmd)], f"mergeworthy's shell parser (shfmt, {REQUIREMENTS}) can't run: {e}", EVERY
    for x in segs: x.scopes, x.loop = scopes + x.scopes, x.loop or loop
    out = []
    for s in segs:  # each command, then what it runs: find's -exec commands, a script
        out.append(s)
        t = prog(s)
        if t[:1] and os.path.basename(t[0]) == 'find':  # find -exec <command> ;
            out += [_seg(x.split('\0'), s.scopes + _scope(ISOLATING), s.loop) for x in re.findall(r'\0-(?:exec|execdir|ok|okdir)\0(.+?)\0(?:;|\+)(?=\0|$)', '\0' + '\0'.join(t))]
        here = [s[i + 1] for i in range(len(s) - 1) if s[i] == '<<<']  # `bash <<< '<script>'`
        script = _nested(s) if depth < 4 else None
        stdin = not script and depth < 4 and here and reads_stdin(s)
        script = here[0] if stdin else script
        if script:
            same = t[:1] and os.path.basename(t[0]) == 'eval'  # eval runs its words in this shell; a child shell, in its own
            # a script word with no quote or escape (`bash -c "cd $W"`) had every expansion done by this shell; else the child does its own
            child = s.raw is None or script not in s or re.search(r"['\\]", s.raw[s.index(script)])
            inner, e = parse(script, depth + 1, s.scopes + (() if same else _scope(ISOLATING, STDIN if stdin else CHILD if child else '')), s.loop)
            for x in inner: x.nested = True
            out += inner
            err = err or e
    # a script's names hold for its own commands and the scripts it runs, never for its shell's: a child shell sets none of them (eval is EVERY)
    for x in out: x.unseen = EVERY if EVERY in (x.unseen, unseen) else x.unseen | unseen
    return out, err


def segments(cmd):
    """parse()'s segments."""
    return parse(cmd)[0]


# The verbs the hooks check: a command holding one that doesn't parse is blocked (pre-bash-guard), never let through unchecked
GUARDED = re.compile(r'\b(?:git\b.*?\b(?:push|commit)|gh\s+(?:pr|issue|api|release)|discussion-post|glab\s+(?:issue|mr)|(?:curl|wget|xh|https?)\b.*?\bapi\.github\.com)\b', re.S)

# Wrappers that run the command after them, with the options each takes a value for (`timeout 200`, `nice -n 19`, `env -u X`)
WRAPPERS = {'sudo': ('-u', '-g', '-h', '-p', '-C', '-D', '-r', '-t', '-U'), 'env': ('-u', '-C', '--unset', '--chdir'), 'command': (),
            'time': (), 'exec': (), 'nohup': (), 'setsid': (), 'netns-run': (), 'builtin': (),
            'nice': ('-n',), 'ionice': ('-c', '-n'), 'stdbuf': (), 'timeout': ('-s', '-k', '--signal', '--kill-after'),
            'watch': ('-n', '-d', '--interval'), 'parallel': ('-j', '--jobs'), 'xargs': ('-I', '-n', '-P', '-L', '-d', '-a', '-E', '-s', '--max-args', '--max-procs', '--delimiter', '--arg-file')}
WRAPPERS.update({'npx': (), 'pnpx': (), 'bunx': (), 'chronic': (), 'taskset': (), 'flock': ('-w', '-E'), 'direnv': (), 'runuser': ('-u', '-g')})
POSITIONAL = {'timeout': 1, 'taskset': 1, 'flock': 1, 'direnv': 2}  # `timeout 20`, `taskset 0x1`, `flock <file>`, `direnv exec <dir>`
RUNNERS = {'pnpm': ('exec', 'dlx'), 'npm': ('exec',), 'yarn': ('exec', 'dlx'), 'bun': ('x',), 'uv': ('run',), 'uvx': ()}  # `pnpm exec git ...`
KEYWORDS = ('!', '{', 'if', 'then', 'else', 'elif', 'do', 'while', 'until')  # a command after these still runs


def script(t):
    """The argv of the script an interpreter runs (`python3 -u /x/gate-pass a b` -> `/x/gate-pass a b`), so a mergeworthy command run through
    one is that command; t itself for any other argv, and for code or a module an interpreter runs (-c, -m)."""
    if not t or not re.fullmatch(r'python[\d.]*|bash|sh', os.path.basename(t[0])):
        return t
    i = 1
    while i < len(t) and t[i].startswith('-'):
        if t[i] in ('-c', '-m'): return t
        i += 2 if t[i] in ('-X', '-W') else 1
    return t[i:] or t

def prog(t):
    """Drop env assignments, shell keywords and wrappers (with their options, and timeout's duration); return the command's argv."""
    while t:
        if re.match(r'^(\w+|\$\{?\w+\}?)=', t[0]) or t[0] in KEYWORDS:  # `env "$v=x" cmd` assigns too
            t = t[1:]
            continue
        w = os.path.basename(t[0])
        if w in RUNNERS and (not RUNNERS[w] or t[1:2] and t[1] in RUNNERS[w]):
            t = t[1 + bool(RUNNERS[w]):]
            while t and t[0].startswith('-'): t = t[1:]
            continue
        if w not in WRAPPERS:
            return t
        t = t[1:]
        while t and t[0].startswith('-'):
            t = t[2:] if t[0] in WRAPPERS[w] else t[1:]
        t = t[POSITIONAL.get(w, 0):]
    return t


_git_builtins = None


def _builtins():
    """git's own commands, which no alias can replace (git ignores one that would)."""
    global _git_builtins
    if _git_builtins is None:
        _git_builtins = set(subprocess.run(['git', '--list-cmds=builtins'], capture_output=True, text=True).stdout.split())
    return _git_builtins


def git_globals(t):
    """The global options of a git argv, before its subcommand (-C dir, -c k=v, --git-dir ...)."""
    a, out = t[1:], []
    while a and a[0].startswith('-'):
        n = 2 if a[0] in ('-C', '-c', '--git-dir', '--work-tree', '--namespace', '--config-env') else 1
        out, a = out + a[:n], a[n:]
    return out


TOPLEVEL = '$(git rev-parse --show-toplevel)'  # the one substitution Where runs itself, in `cd $(git rev-parse --show-toplevel)`


class Maybe(str):
    """A value a variable may hold or not (set in a branch or loop): Where.expand leaves the variable as written."""


class Unknown(str):
    """What Where.values and Where.files give for a word the line doesn't list the values of; its text says why, when there is more to say."""
    def __bool__(self): return False


PIECE = '\0'  # in a value, a part known only to hold no /: it may stand in a file's name, which can't change the file's folder
SPECIALS = ('$', '!', '?', '#', 'RANDOM', 'SECONDS')  # the shell's variables that only ever hold a number
HASHES = ('md5sum', 'sha1sum', 'sha256sum', 'sha512sum', 'b2sum', 'cksum')
CAP = 64  # a word's values and a file's candidates: the check runs git for each folder
UNKNOWN, CAPPED = Unknown(), Unknown(f'its word may hold more than {CAP} values: name the files, or run a command per folder')


class Many(Maybe):
    """A variable's value that Where.values alone reads: the values it may hold here (vals), or Unknown. As a str it is the text as written, so
    each other reader of a Maybe sees what it saw."""
    def __new__(cls, text, vals):
        m = super().__new__(cls, text)
        m.vals = vals
        return m


class Where:
    """Where each simple command of one command line runs, walk() taking them in order, with the variables the line set
    (`D=~/x; cd "$D"`). It follows the forms agents write: a cd or pushd to a path (`cd /abs/dir && ...`, or relative to a dir it
    knows), `cd $(git rev-parse --show-toplevel)` and `git -C <dir>`. A cd holds for the later commands of its scope (Seg.scopes) and
    the scopes inside it; leaving an isolating scope restores the dir and the line's variables from before it, leaving a branch or
    loop makes each variable set in it a Maybe. After any other dir change (a cd in a scope that may run it or not, once the scope
    is left; a call to a function the line defines, when one of their bodies changes dir; a relative one in a loop; a target
    holding an expansion it can't resolve; `cd -`, popd or a stack rotation) the dir is None until a cd to an absolute path, and a
    check that needs it blocks.
    That following is trust a plain walk doesn't give, so it is spent only where its variables are proven (strict expansion: Maybe,
    Word.parts' quoting, Seg.unseen): a cd nested in a scope or once the plain walk lost the dir, and a written file (files). The
    plain walk (main_dir, main_vars: every NAME=value the line runs, but an isolating scope's once it is left, then the environment's)
    decides each other cd, at the top level while it knows the dir, and every other expansion, as it did before scopes: a nested cd,
    `cd -` or popd loses its dir for good.
    spots: the dirs a relative write may start from, a written file's only read of where it runs: the dir when it is known, else each
    target a cd the dir can't follow has listed (_spots), and None where a target or the dir before it can't be told."""
    def __init__(self, cwd):
        self.funcs, self.func_vars, self.func_moves = set(), set(), False  # the functions the line defines, the variables their bodies set, whether one changes dir
        self.main_dir, self.main_vars = cwd, {'PWD': cwd}
        self.dir, self.moved, self.vars, self.scopes, self.quoted, self.unseen, self.spots = cwd, False, {'PWD': cwd}, [], set(), frozenset(), (cwd,)  # each scope entered: [(id, kind, name), dir before it, whether a cd ran in it, variables before it, variables set in it, main_vars before it, spots before it]

    def expand(self, p, strict=False):
        """p with the plain walk's variables ($D, ${D}: main_vars), then the environment's, put in. strict: the scoped ones (vars)
        instead, and every $ of a word the current command quoted or escaped (Word.parts), which is literal, and every variable the
        line may set unseen (Seg.unseen) stay as written. A value it can't tell (a Maybe) stays as written."""
        def value(m):
            n = m[1] or m[2]
            v = (self.vars if strict else self.main_vars).get(n, os.environ.get(n, m[0]))
            return m[0] if isinstance(v, Maybe) or strict and n in self.unseen else v
        return p if strict and p in self.quoted else re.sub(r'\$(?:(\w+)|\{(\w+)\})', value, p)

    def path(self, p, base='', strict=False):
        """p resolved from base (default: the dir), or None when it can't be told (an expansion left, or no base)."""
        p = os.path.expanduser(self.expand(p, strict))
        base = self.dir if base == '' else base
        return None if re.search(r'[$`]', p) else p if os.path.isabs(p) else None if base is None else os.path.join(base, p)

    def files(self, w):
        """The paths a file the current command names, word w, may be, each resolved from each of spots. An Unknown when one's folder can't be told:
        no spots for a relative one, a piece in its folder, or a value the line doesn't list."""
        vals = self.values(w)
        if isinstance(vals, Unknown):
            return vals
        out = []
        for v in map(os.path.expanduser, vals):
            if PIECE in os.path.dirname(v) or getattr(w, 'splits', False) and re.search(r'[\s*?[]', v):  # bash would split or match it: other paths
                return UNKNOWN
            v = v.replace(PIECE, '_')
            if os.path.isabs(v):
                out.append(v)
            elif self.spots is None:
                return UNKNOWN
            else:
                out += [os.path.join(x, v) for x in self.spots]
        return CAPPED if len(out) > CAP else out

    def values(self, w):
        """The values word w may hold here, what the line itself gives it, a PIECE for each part known only to hold no /; an Unknown when it
        doesn't list them or holds more than CAP."""
        if not isinstance(w, Word):
            v = self.expand(w, True)
            return UNKNOWN if re.search(r'[$`]', v) else (v,)
        out = ('',)
        for p in w.parts:
            vals = self._part(*p)
            if isinstance(vals, Unknown):
                return vals
            if len(out) * len(vals) > CAP:
                return CAPPED
            out = tuple(a + b for a in out for b in vals)
        return tuple(dict.fromkeys(out))

    def _part(self, kind, *a):
        """The values a part of a word (Word.parts) may hold."""
        if kind == 'lit': return UNKNOWN if re.search(r'[$`]', a[0]) else (a[0],)
        if kind == 'piece': return (PIECE,)
        if kind == 'var': return self._var(a[0])
        if kind == 'exp': return self._exp(*a)
        if kind == 'repl': return self._repl(*a)
        if kind == 'sub' and a[0]: return self._sub(a[0])
        return UNKNOWN

    def _exp(self, n, op, word):
        """${n<op><word>}: its default, or what a pattern leaves of each value; of a value it can't tell, only ${n##*/} and ${n%%/*} are known."""
        vals = self._var(n)
        lost = isinstance(vals, Unknown)
        if op in ('-', ':-') and lost and n.isidentifier() and n not in self.vars and n not in os.environ and n not in self.unseen:
            return self.values(word)
        if op in ('-', ':-', '?', ':?'):
            if lost or op != ':-' or '' not in vals:
                return vals
            other = self.values(word)
            return other if isinstance(other, Unknown) else (*(v for v in vals if v), *other)
        pat = self.values(word)
        if op not in ('#', '##', '%', '%%') or isinstance(pat, Unknown) or len(pat) != 1:
            return UNKNOWN
        if lost:
            return (PIECE,) if (op, pat[0]) in (('##', '*/'), ('%%', '/*')) else vals
        return tuple(_trim(v, op, pat[0]) for v in vals)

    def _repl(self, n, every, pattern, new):
        """${n/pattern/new} or ${n//pattern/new}; of a value it can't tell, only one replacing every / with no / is known."""
        vals, pat, to = self._var(n), self.values(pattern), self.values(new)
        if isinstance(pat, Unknown) or isinstance(to, Unknown) or len(pat) != 1 or len(to) != 1 or pat[0][:1] in ('#', '%'):
            return UNKNOWN
        if isinstance(vals, Unknown):
            return (PIECE,) if every and fnmatch.fnmatchcase('/', pat[0]) and '/' not in to[0] else vals
        return tuple(_replaced(v, pat[0], to[0], every) for v in vals)

    def _sub(self, stages):
        """A substitution's values: basename and dirname per value; a piece for what can't print a /; else unknown, as any other command's output."""
        t, names = stages[0], [os.path.basename(x[0]) if x else '' for x in stages]
        if names in (['basename'], ['dirname']):
            vals = self.values(t[1]) if len(t) == 2 and not t[1].startswith('-') else UNKNOWN
            if names == ['basename']:
                return (PIECE,) if isinstance(vals, Unknown) else tuple(os.path.basename(v.rstrip('/')) or v[:1] for v in vals)
            return vals if isinstance(vals, Unknown) else tuple(os.path.dirname(v.rstrip('/')) or ('/' if v[:1] == '/' else '.') for v in vals)
        if names == ['date']:
            fmt = [x for x in t[1:] if x not in ('-u', '--utc')]
            return (PIECE,) if not fmt or len(fmt) == 1 and re.fullmatch(r'\+[^/$`]*', fmt[0]) and not re.search(r'%[-_0^#]*\d*[Dxc]', fmt[0]) else UNKNOWN
        if names == ['git']:
            a = t[1 + len(git_globals(t)):]
            return (PIECE,) if a[:1] == ['rev-parse'] and a[-1:] == ['HEAD'] and (len(a) == 2 or len(a) == 3 and re.fullmatch(r'--short(=\d+)?', a[1])) else UNKNOWN
        hash_at = next((i for i, x in enumerate(names) if x in HASHES and len(stages[i]) == 1), None)
        if hash_at is not None and set(names[hash_at + 1:]) <= {'cut', 'head'}:
            return (PIECE,)
        return self._tr(stages) if names == ['echo', 'tr'] else UNKNOWN

    def _tr(self, stages):
        """$(echo <words> | tr <sets>): a piece when it can't print a /: tr adds none, and the words hold none or tr removes it."""
        said = [self.values(x) for x in stages[0][1:] if x != '-n']
        flag = lambda x: re.fullmatch(r'-[sd]+', x)
        flags, sets = ''.join(filter(flag, stages[1][1:])), [x for x in stages[1][1:] if not flag(x)]
        if not sets or len(sets) > 2 or re.search(r'[$`]', ''.join(sets)) or 'd' not in flags and '/' in ''.join(sets[1:]):
            return UNKNOWN
        gone = '/' in sets[0] and ('d' in flags or len(sets) == 2)
        return (PIECE,) if gone or not any(isinstance(v, Unknown) or any('/' in y for y in v) for v in said) else UNKNOWN

    def _var(self, n):
        """The values variable n holds here (Seg.unseen: none it may hold unseen)."""
        if n in SPECIALS and n not in self.vars:
            return (PIECE,)
        v = self.vars.get(n, os.environ.get(n))
        if n in self.unseen or v is None:
            return UNKNOWN
        return v.vals if isinstance(v, Many) else UNKNOWN if isinstance(v, Maybe) or re.search(r'[$`]', v) else (v,)

    def _listed(self, words):
        """What a for loop's variable holds over words: each word's values, split and matched on disk as bash does."""
        out = []
        for w in words:
            vals = UNKNOWN if '{' in w.bare else self.values(w)
            if isinstance(vals, Unknown):
                return Many('', vals)
            if w.splits and ('IFS' in self.vars or w.quoted and any(re.search(r'\s', v) for v in vals)):  # where bash splits it can't be told from the value
                return Many('', UNKNOWN)
            for v in (y for x in vals for y in (x.split() if w.splits else [x])):
                if (w.splits or re.search(r'[*?[]', w.bare)) and re.search(r'[*?[]', v) and PIECE not in v:
                    if not os.path.isabs(os.path.expanduser(v)) and self.dir is None:
                        return Many('', UNKNOWN)
                    out += glob.glob(os.path.expanduser(v), root_dir=self.dir) or [v]
                else:
                    out.append(v)
        return Many('', tuple(dict.fromkeys(out)) if words else UNKNOWN)

    def walk(self, segs):
        """Each of segs (parse()'s), with self moved to where it runs; self takes it once the caller is done with it."""
        for t in segs:
            self.unseen = t.unseen
            self.enter(t.scopes)
            self.quoted = {w for w in t if '$' in w and (not isinstance(w, Word) or any(x[0] == 'lit' and '$' in x[1] for x in w.parts))}
            yield t
            self.step(t)

    def enter(self, scopes):
        """Leave the scopes not in scopes, innermost first, and enter the new ones."""
        n = 0
        while n < min(len(self.scopes), len(scopes)) and self.scopes[n][0] == scopes[n]: n += 1
        for (_, kind, *_), before, moved, vars, set_in, main_vars, spots in reversed(self.scopes[n:]):
            self.dir = before if kind == ISOLATING else None if moved else self.dir
            self.spots = spots if kind == ISOLATING else None if moved else self.spots
            self.vars = vars if kind == ISOLATING else {**self.vars, **{v: Maybe(self.vars.get(v, '')) for v in set_in}}
            self.main_vars = main_vars if kind == ISOLATING else self.main_vars
        self.funcs |= {x[2] for x in scopes[n:] if x[2] and x[1] == CONDITIONAL}
        self.scopes = self.scopes[:n]
        for x in scopes[n:]:
            self.scopes.append([x, self.dir, False, dict(self.vars), set(), dict(self.main_vars), self.spots])
            if x[1] == LOOP and x[2]: self.vars[x[2]] = self._listed(x[3]); self.changed(x[2])  # each pass gives it another of its words
            if x[2] == STDIN: self.dir, self.spots = None, None
            if x[2] in (STDIN, CHILD): self.vars = {k: Maybe(v) for k, v in self.vars.items()} | {'PWD': _dir(self.dir)}  # a shell's PWD is where it starts

    def changed(self, var=None):
        """Record a cd (var None) or an assignment of var here in the scopes it changes what they leave behind, up to the innermost
        isolating one."""
        for x in reversed(self.scopes):
            if var is None: x[2] = True
            else: x[4].add(var)
            if x[0][1] == ISOLATING: return

    def in_body(self):
        """Whether the current command is in a function's body."""
        return any(x[0][2] and x[0][1] == CONDITIONAL for x in self.scopes)

    def step(self, t):
        words = t[1:] if t[:1] in (['export'], ['readonly'], ['declare']) or t[:1] == ['local'] and self.in_body() else t  # local fails outside a function
        if words and all(re.match(r'^\w+=', x) for x in words):
            for x in words:  # each value expanded as it is assigned, but one whose $ the command quoted or escaped
                n, v = x.split('=', 1)
                text, vals = v if x in self.quoted else self.expand(v, True), self.values(x)
                vals = vals if isinstance(vals, Unknown) else tuple(y[len(n) + 1:] for y in vals)
                self.vars[n], self.main_vars[n] = text if vals == (text,) else Many(text, vals), v if x in self.quoted else self.expand(v)
                self.changed(n)
            if self.in_body(): self.func_vars.update(x.split('=', 1)[0] for x in words)
            return
        p = prog(t)
        if p[:1] and p[0] in self.funcs:  # a call runs a body here, maybe calling another: what any of them changes can't be told
            if self.func_moves:
                self.dir, self.moved, self.spots = None, True, None
                self.changed()
            for v in self.func_vars: self.vars[v] = Maybe(self.vars.get(v, '')); self.changed(v)
            return
        if p[:1] not in (['cd'], ['pushd'], ['popd']):
            return
        self.moved, self.func_moves = True, self.func_moves or self.in_body()
        a = [x for x in operands(p[1:]) if x not in ('-P', '-L', '-e', '--')]
        to = a[0] if a else '~' if p[0] == 'cd' else '-'
        kinds = [x[0][1] for x in self.scopes if x[0][1] != CONDITIONAL]
        self.changed()
        old = self.dir, self.main_dir
        nested = t.nested or bool(t.scopes)
        main = None if nested or p[0] == 'popd' or to[:1] in '-+' or self.main_dir is None else \
            _toplevel(self.main_dir) if to == TOPLEVEL else self.path(to, self.main_dir) and os.path.normpath(self.path(to, self.main_dir))
        if not nested and self.main_dir is not None:
            self.dir = main
        elif p[0] == 'popd' or to[:1] in '-+' or to == TOPLEVEL and self.dir is None or kinds[-1:] == [LOOP] and not os.path.isabs(os.path.expanduser(self.expand(to, True))):
            self.dir = None
        elif to == TOPLEVEL:
            self.dir = _toplevel(self.dir)
        else:
            self.dir = self.path(to, strict=True) and os.path.normpath(self.path(to, strict=True))
        self.main_dir, self.spots = main, (self.dir,) if self.dir is not None else self._spots(p[0], to, kinds)
        for n, dirs in (('OLDPWD', old), ('PWD', (self.dir, self.main_dir))):
            self.vars[n], self.main_vars[n] = map(_dir, dirs)
            self.changed(n)
        if self.in_body(): self.func_vars.update(('PWD', 'OLDPWD'))

    def _spots(self, verb, to, kinds):
        """Where a cd the dir can't follow may have gone, verb to word to, in scopes of kinds (no conditional's): each value it lists, from each
        spot; None for a target the line doesn't list or a piece may name, and a relative one in a plain loop's body, whose each pass starts where the last ended."""
        vals = None if verb == 'popd' or to[:1] in '-+' or to == TOPLEVEL else self.values(to)
        if vals is None or isinstance(vals, Unknown):
            return None
        out = []
        for v in map(os.path.expanduser, vals):
            if PIECE in v or not os.path.isabs(v) and (self.spots is None or kinds[-1:] == [LOOP]):
                return None
            out += [os.path.normpath(os.path.join(x, v)) for x in ((v,) if os.path.isabs(v) else self.spots)]
        return tuple(dict.fromkeys(out))


def _trim(v, op, pat):
    """${v<op>pat}, op one of # ## % %%: v without the shortest or longest start or end that the glob pat matches."""
    start = op[0] == '#'
    for i in range(len(v) + 1) if op in ('#', '%%') else range(len(v), -1, -1):
        if fnmatch.fnmatchcase(v[:i] if start else v[i:], pat):
            return v[i:] if start else v[:i]
    return v


def _replaced(v, pat, new, every):
    """${v/pat/new}, or with every ${v//pat/new}: each longest match of the glob pat replaced, from the left."""
    out, i = '', 0
    while i < len(v):
        j = next((j for j in range(len(v), i, -1) if fnmatch.fnmatchcase(v[i:j], pat)), None)
        if j is None:
            out, i = out + v[i], i + 1
        else:
            out, i = out + new, j
            if not every:
                break
    return out + v[i:]


def _dir(d):
    """A dir as a variable's value: a Maybe when it can't be told (None)."""
    return Maybe('') if d is None else d


def _toplevel(d):
    return subprocess.run(['git', '-C', d, 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip() or None


def git_argv(t, where):
    """(git dir, -c overrides, subcommand, its arguments) of a git argv run at where (a Where), past its global options (each -C
    applies in turn; the dir is None when Where can't tell it); a configured alias (`git config alias.p push`, or `-c alias.p=push`)
    is expanded, so `git p` is checked as the push it runs."""
    g = git_globals(t)
    overrides = dict(g[i + 1].split('=', 1) for i in range(len(g) - 1) if g[i] == '-c' and '=' in g[i + 1])
    git_dir = where.dir
    for i in range(len(g) - 1):
        if g[i] == '-C': git_dir = where.path(g[i + 1], git_dir)
    a = t[1 + len(g):]
    if not a:
        return git_dir, overrides, '', []
    sub, rest = a[0], a[1:]
    alias = '' if sub in _builtins() else overrides.get(f'alias.{sub}') or \
        subprocess.run(['git', '-C', git_dir or '/', 'config', '--get', f'alias.{sub}'], capture_output=True, text=True).stdout.strip()
    if alias and not alias.startswith('!'):
        words = alias.split()
        sub, rest = words[0], words[1:] + rest
    elif alias:  # a shell alias: its first command's verb
        inner = prog((segments(alias[1:]) or [['']])[0])
        if inner[:1] == ['git']:
            return git_argv(inner + rest, where)
    return git_dir, overrides, sub, rest


def opt(t, names):
    """Values of options in names, in --x v, --x=v and -Xv forms."""
    vals = []
    for i, a in enumerate(t):
        for n in names:
            if a == n and i + 1 < len(t): vals.append(t[i + 1])
            elif n.startswith('--') and a.startswith(n + '='): vals.append(a[len(n) + 1:])
            elif not n.startswith('--') and a.startswith(n) and len(a) > len(n): vals.append(a[len(n):])
    return vals

NO_TEXT = re.compile(r'(?:repos/[^/]+/[^/]+/(?:.+/)?(?:reactions|rerun[\w-]*|dispatches|labels|assignees|requested_reviewers)(?:/[^/]+)?'
                     r'|repos/[^/]+/[^/]+/(?:collaborators|invitations)/[^/]+|user/repository_invitations/\d+)')

def graphql_posts(fields, inputs, cwd):
    """A GraphQL call posts text when its query, literal or read from a file (relative to cwd, the dir the command runs in), is a mutation other than
    adding or removing a reaction."""
    queries = [v for v in fields if not v.startswith('query=@')]
    try:
        path = lambda f: os.path.join(cwd or '', os.path.expanduser(f)) if cwd or os.path.isabs(os.path.expanduser(f)) else None
        queries += [open(path(v[len('query=@'):])).read() for v in fields if v.startswith('query=@')]
        queries += [str(json.load(open(path(f))).get('query', '')) for f in inputs]  # --input is a JSON request body
    except (OSError, ValueError, AttributeError, TypeError):
        return True  # stdin, an unreadable file or a body that isn't a JSON object: treated as a post
    for q in queries:
        if re.search(r'\bmutation\b', q):
            names = re.findall(r'\b([a-z]\w*)\s*\(\s*input\s*:', q)
            if not names or any(n not in ('addReaction', 'removeReaction') for n in names):
                return True
    return False

DISCUSSION_MUTATION = re.compile(r'\b(?:add|update)DiscussionComment\b')

def graphql_endpoint(ep):
    """Whether a `gh api` endpoint is GitHub's GraphQL one, in each form gh takes: graphql, /graphql, a full URL, GHES's api/graphql."""
    return bool(re.fullmatch(r'(?:https?://[^/]+)?/?(?:api/)?graphql', ep.split('?')[0]))

def names_discussion_mutation(rest, cwd):
    """Whether a `gh api` GraphQL request's query names a mutation that posts or edits a GitHub Discussion comment (discussion-post makes
    those) anywhere, as GitHub reads it: a query field's text, the file a -F query=@ field reads, or the --input body's query, JSON-decoded
    (files relative to cwd); None when a file can't be read, so it can't be told."""
    queries = [v[len('query='):] for v in opt(rest, ['-f', '--raw-field', '-F', '--field']) if v.startswith('query=')]
    try:
        path = lambda f: os.path.join(cwd or '', os.path.expanduser(f)) if cwd or os.path.isabs(os.path.expanduser(f)) else None
        queries += [open(path(v[len('query=@'):])).read() for v in opt(rest, ['-F', '--field']) if v.startswith('query=@')]
        for f in opt(rest, ['--input']):
            body = open(path(f)).read()
            try: body = json.loads(body)
            except ValueError: pass  # GitHub refuses a body that isn't JSON; its text is searched as it stands
            queries.append(str(body.get('query', '')) if isinstance(body, dict) else str(body))
    except (OSError, TypeError):
        return None
    return any(DISCUSSION_MUTATION.search(q) for q in queries)

def discussion_post(t):
    """('add', <discussion URL or owner/repo#N>, draft) or ('edit', <comment node id>, draft) of a `discussion-post` argv; None for any
    other argv, or its --help."""
    t = script(prog(t))
    if not t or os.path.basename(t[0]) != 'discussion-post' or '--help' in t or '-h' in t:
        return None
    a = t[1:]
    if a[:1] == ['--edit']:
        return ('edit', *a[1:3]) if len(a) == 3 else ('edit', '', '')
    return ('add', *a[:2]) if len(a) == 2 else ('add', '', '')

@functools.cache
def discussion_thread_of(ref):
    """owner/repo#N a discussion reference names (thread-context --ref: owner/repo#N or a discussion URL, an organization's too); None
    when it names none or can't be read."""
    tc = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bin', 'thread-context')
    try: r = subprocess.run([tc, '--ref', ref], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.TimeoutExpired): return None
    return r.stdout.strip() if r.returncode == 0 and re.fullmatch(r'[\w.-]+/[\w.-]+#\d+', r.stdout.strip()) else None

def api_call(rest, cwd=None):
    """(method, endpoint, fields, inputs, posts) of `gh api <rest>`. It posts text when it is a GraphQL mutation, or a POST,
    PATCH or PUT that isn't a reaction, rerun, dispatch, label, assignee, review request, collaborator or invitation. cwd: where the command
    runs, for the files a GraphQL query is read from; None when unknown, so a relative file counts as a post."""
    method = (opt(rest, ['-X', '--method']) or [''])[-1].upper()
    fields = opt(rest, ['-f', '--raw-field', '-F', '--field'])
    inputs = opt(rest, ['--input'])
    if not method: method = 'POST' if fields or inputs else 'GET'
    pos = [x for i, x in enumerate(rest) if not x.startswith('-') and (i == 0 or rest[i - 1] not in
           ('-X', '--method', '-f', '--raw-field', '-F', '--field', '--input', '-H', '--header', '-q', '--jq', '-t', '--template', '--hostname', '--cache', '-p', '--preview'))]
    ep = pos[0] if pos else ''
    if ep == 'graphql':
        posts = graphql_posts(fields, inputs, cwd)
    else:
        posts = method in ('POST', 'PATCH', 'PUT') and not NO_TEXT.fullmatch(re.sub(r'^(?:https?://[^/]+)?/?(?:api/v3/)?', '', ep).split('?')[0])
    return method, ep, fields, inputs, posts

def repo_name(r):
    """owner/repo a gh repository value names: [HOST/]OWNER/REPO or a URL."""
    return '/'.join(re.sub(r'(\.git)?/*$', '', r).split('/')[-2:])

def gh_repo(args, env, origin):
    """owner/repo a gh command with args acts on, as gh picks it: its -R, else GH_REPO set on the command or inherited (both
    [HOST/]OWNER/REPO or a URL), else the checkout's origin (origin(): its URL, read only then)."""
    if r := (opt(args, ['--repo', '-R']) or [None])[-1] or env.get('GH_REPO', os.environ.get('GH_REPO')):
        return repo_name(r)
    m = re.search(r'github\.com[:/]([\w.-]+/[\w.-]+?)(\.git)?$', origin())
    return m.group(1) if m else None

def gitlab_repo(a, origin):
    """`gitlab.com/<namespace>/<project>` a glab command acts on: its -R value (a path or URL), else the cwd's origin."""
    repo = (opt(a, ['--repo', '-R']) or [None])[-1]
    if repo:
        repo = re.sub(r'^(https://)?gitlab\.com/', '', repo)
    else:
        repo = (re.search(r'gitlab\.com[:/](.+?)(?:\.git)?$', origin()) or [None, None])[1]
    return 'gitlab.com/' + repo.strip('/') if repo and '://' not in repo else None

def api_opens(ep, rest, env, origin):
    """(repo, 'issue' or 'pr') a `gh api` or `glab api` POST to ep opens, in each form the CLIs take (a full URL, a leading slash, an api/v3/
    or api/v4/ prefix, a query, gh's {owner}/{repo} from GH_REPO or the checkout (origin, as gh_repo), glab's :fullpath or :id, a GitLab host from --hostname or GITLAB_HOST);
    None for any other endpoint, repo None when it can't be told (a project's numeric id)."""
    host, path = re.match(r'(?:https?://([^/]+))?/?(?:api/v[34]/)?([^?]*)', ep).groups()
    if (m := re.fullmatch(r'repos/([^/]+/[^/]+)/(issues|pulls)', path)):
        base = gh_repo(rest, env, origin) or ''
        repo = m[1].replace('{owner}', base.split('/')[0]).replace('{repo}', base.split('/')[-1]) if base else m[1]
        return (None if '{' in repo else repo if host in (None, 'api.github.com') else f'{host}/{repo}'), 'pr' if m[2] == 'pulls' else 'issue'
    if (m := re.fullmatch(r'projects/([^/]+)/(issues|merge_requests)', path)):
        import urllib.parse
        project = urllib.parse.unquote(m[1])
        host = host or (opt(rest, ['--hostname']) or [None])[-1] or env.get('GITLAB_HOST') or os.environ.get('GITLAB_HOST') or 'gitlab.com'
        repo = gitlab_repo(rest, origin) if project in (':fullpath', ':id') else f"{re.sub(r'^https?://|/+$', '', host)}/{project}" if '/' in project else None
        return repo, 'pr' if m[2] == 'merge_requests' else 'issue'
    return None

def env_of(t):
    """The variables a simple command sets for itself (`GH_REPO=o/r gh ...`)."""
    return dict(x.split('=', 1) for x in t[:len(t) - len(prog(t))] if re.match(r'^\w+=', x))

def origin(d):
    """The origin remote's URL of the checkout at d; '' without one."""
    return subprocess.run(['git', '-C', d, 'remote', 'get-url', 'origin'], capture_output=True, text=True).stdout.strip()

def _named_host(r, p):
    """The host a -R or GH_REPO value names (a URL, git@host:path, gh's HOST/OWNER/REPO, a glab path whose first part has a dot,
    which glab can't tell from a dotted group either); None when it names none, '' when it can't be read."""
    if m := re.match(r'(?:[a-z][\w+.-]*://)?[^@/]+@([^/:]+)[:/]|[a-z][\w+.-]*://([^/:]+)', r):
        return m[1] or m[2]
    if '://' in r or '@' in r: return ''
    parts = r.strip('/').split('/')
    return parts[0] if (len(parts) >= 3 if p == 'gh' else '.' in parts[0]) else None

def public_host(t):
    """Whether every host the gh or glab command t names is the CLI's public one (github.com, api.github.com; gitlab.com): an API
    endpoint's URL, each --hostname, a host in each -R or in GH_REPO, and GH_HOST (gh) or GITLAB_HOST and GL_HOST (glab), set on
    the command or in this environment. One naming another host, or one that can't be read, and it isn't; which of them the CLI
    would use isn't guessed."""
    env, a = env_of(t), prog(t)
    p, rest = os.path.basename(a[0]), a[1:]
    get = lambda k: env.get(k, os.environ.get(k))
    ep = api_call(rest[1:])[1] if rest[:1] == ['api'] else ''
    hosts = ([(re.match(r'https?://([^/]+)', ep) or [None, ''])[1]] if '://' in ep else []) + opt(rest, ['--hostname']) \
        + [h for r in opt(rest, ['--repo', '-R']) + ([get('GH_REPO')] if p == 'gh' and get('GH_REPO') else []) if (h := _named_host(r, p)) is not None] \
        + [v for k in (('GH_HOST',) if p == 'gh' else ('GITLAB_HOST', 'GL_HOST')) if (v := get(k))]
    public = ('github.com', 'api.github.com') if p == 'gh' else ('gitlab.com',)
    return all(re.sub(r'^https?://|/+$', '', h).lower() in public for h in hosts)

def watchable(repo):
    """True for a repo a watcher reads: owner/repo on github.com, or gitlab.com/<path>."""
    return bool(repo) and (repo.startswith('gitlab.com/') or bool(re.fullmatch(r'[\w.-]+/[\w.-]+', repo)))

def opened(t, d):
    """(repo, the options that keep its URL out of the output) of the issue, PR or MR the simple command t, run in d, opens (gh or
    glab create, or an API POST, as api_opens reads it); None when it opens none. repo is None when it can't be told."""
    env, a = env_of(t), prog(t)
    if not a or os.path.basename(a[0]) not in ('gh', 'glab') or '--help' in a or '-h' in a:
        return None
    p, a, here = os.path.basename(a[0]), a[1:], lambda: origin(d) if d else ''
    if a[:1] == ['api']:
        method, ep = api_call(a[1:])[:2]
        if method != 'POST' or not (o := api_opens(ep, a[1:], env, here)):
            return None
        return o[0], ('--jq', '-q', '--template', '-t', '--silent')
    if a[1:2] == ['create'] and a[0] in (('issue', 'pr') if p == 'gh' else ('issue', 'mr')):
        return gh_repo(a[2:], env, here) if p == 'gh' else gitlab_repo(a[2:], here), ('--web', '-w') if p == 'gh' else ('--web',)
    return None

PLAIN = ("only a plain create starts its work folder's watcher by itself: the command is exactly zero or more `cd /abs/dir && `, then "
         "gh or glab and its words (bare, '…', \"…\" without $, ` or \\, or \"$(cat <file>)\"), then at most one stderr redirect (2>&1, "
         "2>/dev/null, 2>/abs/file); no other $, `, >, <, ;, |, &, newline or parenthesis, and no output filter (--jq, -q, --silent, "
         "--template, --web); run in a task's work folder, on github.com or gitlab.com: every host it names (its URL, "
         "--hostname, -R, GH_REPO, GH_HOST, GITLAB_HOST, GL_HOST) is that one")
_BARE = r"[A-Za-z0-9_./:@=+,%-]"  # one character of a bare word
_ERR = rf"2>(?:&1|/dev/null|\s?/{_BARE}+)"
PLAIN_TEXT = re.compile(rf"""[ \t]*(?:cd[ \t]+/{_BARE}+(?:[ \t]+{_ERR})?[ \t]+&&[ \t]+)*(?:gh|glab)"""  # each piece of a word one way only: no backtracking blowup
                        rf"""(?:[ \t]+(?:{_BARE}|'[^'\n]*'|"[^"$`\\\n]*"|"\$\(cat {_BARE}+\)")+)*(?:[ \t]+{_ERR})?[ \t]*""")

def plain_create(cmd, cwd):
    """The task's work folder whose watcher post-bash-register adds the thread to, starting or reviving it, when the command text
    (run from cwd) is a plain create, the whole of it matching PLAIN_TEXT (PLAIN says which); None for any other command."""
    if not PLAIN_TEXT.fullmatch(cmd):
        return None
    where = Where(cwd)
    for t in where.walk(segments(cmd)):
        if t[:1] in (['gh'], ['glab']) and (o := opened(t, where.dir)):
            repo, filters = o
            ok = watchable(repo) and public_host(t) and not any(f in t or opt(t, [f]) for f in filters)
            return ok and where.dir and work_folder.task_of(where.dir) or None
    return None

def new_post_drafts(t):
    """Draft files a gh or discussion-post argv posts as something new (an issue, PR, comment or review): each draft is posted as new once, edits may repeat."""
    if (dp := discussion_post(t)) and dp[0] == 'add':
        return [dp[2]]
    t = prog(t)
    if not t or os.path.basename(t[0]) != 'gh' or '--help' in t or '-h' in t:
        return []
    a = t[1:]
    if a[:1] in (['issue'], ['pr']) and a[1:2] and a[1] in ('comment', 'create', 'review'):
        return opt(a[2:], ['--body-file', '-F'])
    if a[:1] == ['api']:
        method, _, _, inputs, posts = api_call(a[1:])
        if posts and method == 'POST':
            return [v[len('body=@'):] for v in opt(a[1:], ['-F', '--field']) if v.startswith('body=@')] + inputs
    return []


def rlines(path, chunk=1 << 20):
    """The file's lines, last first."""
    with open(path, 'rb') as f:
        f.seek(0, 2)
        pos, rest = f.tell(), b''
        while pos > 0:
            n = min(chunk, pos); pos -= n; f.seek(pos)
            lines = (f.read(n) + rest).split(b'\n')
            rest = lines.pop(0)
            yield from reversed(lines)
        yield rest


def transcript(d):
    path = d.get('transcript_path') or ''
    if d.get('agent_id'):  # a subagent's context holds only its own reads and skills
        path = d.get('agent_transcript_path') or os.path.join(os.path.dirname(path), d.get('session_id', ''), 'subagents', f"agent-{d['agent_id']}.jsonl")
    return path if path and os.path.isfile(path) else None


def in_place(a):
    """sed arguments a edit their files in place: -i, -i.bak, -ni, --in-place[=suffix]."""
    return any(re.fullmatch(r'-[A-Za-z]*i.*|--in-place(=.*)?', x) for x in a)


def sed_files(a):
    """sed's file operands in its arguments a: its script (each -e or -f value, else the first operand) is not one, nor
    BSD sed's empty suffix after -i (`sed -i '' ...`)."""
    files, script, it, prev = [], False, iter(a), ''
    for x in it:
        if x in ('-e', '-f', '--expression', '--file') or re.fullmatch(r'-[A-Za-z]*[ef]', x):
            script = next(it, None) is not None
        elif x.startswith(('--expression=', '--file=')) or re.fullmatch(r'-[A-Za-z]*[ef].+', x):
            script = True
        elif x == '' and re.fullmatch(r'-[A-Za-z]*i', prev):
            pass
        elif not x.startswith('-'):
            files.append(x)
        prev = x
    return files if script else files[1:]


def written_files(t):
    """The files a command (argv t, after prog) writes: its redirect targets, tee's files, an in-place sed's files, cp, mv
    and install's destination (-t <dir> included). Redirect operators and their targets are not operands; /dev/ and &N aren't files."""
    out, args, i = [], [], 1
    while i < len(t):
        x, nxt = t[i], t[i + 1] if i + 1 < len(t) else None
        if re.fullmatch(r'\d+', x) and nxt is not None and nxt[:1] in '<>&':  # the fd number of `2>`
            i += 1
        elif re.fullmatch(r'\d*(>>?|>\||&>>?|>&)', x):
            if nxt is not None and not nxt.startswith('/dev/') and not re.fullmatch(r'\d+|-', nxt):
                out.append(nxt)
            i += 2
        elif re.fullmatch(r'\d*(<<?<?|<&|<>)', x):
            i += 2
        else:
            args.append(x)
            i += 1
    p, files = os.path.basename(t[0]) if t else '', [x for x in args if not x.startswith('-')]
    if p == 'tee':
        out += files
    elif p == 'sed' and in_place(args):
        out += sed_files(args)
    elif p in ('cp', 'mv', 'install'):
        out += opt(args, ['-t', '--target-directory'])[-1:] or files[-1:]
    return out


def no_instructions_read(path, d):
    """Why path (a file, or a folder written into) can't change yet: the AGENTS.md and CLAUDE.md at its git repo's root that
    this session's transcript shows no successful Read, cat or sed of since its last compaction; '' outside git or when the
    root has neither."""
    root = subprocess.run(['git', '-C', folder(path), 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip()
    need = [f for f in (os.path.join(root, n) for n in ('AGENTS.md', 'CLAUDE.md')) if root and os.path.isfile(f)]
    if not need:
        return ''
    t = transcript(d)
    names = {os.path.basename(g).encode() for f in need for g in (f, os.path.realpath(f))}  # a symlink's target too
    seen = files_read(t, names) if t else set()
    unread = [f for f in need if os.path.realpath(f) not in seen]
    return f"read this repo's instructions first, with the Read tool, and follow them: {', '.join(unread)}" if unread else ''


def files_read(path, names):
    """Real paths the transcript's Read calls, and its Bash cat and sed (not sed -i), read since its last compaction, leaving
    out calls whose result is an error; only lines naming one of names, or holding an error, are parsed."""
    seen, failed = set(), set()
    for l in rlines(path):  # last first: a call's result comes before the call
        if not any(k in l for k in (b'compact_boundary', b'isCompactSummary', b'"is_error":true', *names)):
            continue
        try:
            e = json.loads(l)
        except ValueError:
            continue
        if e.get('subtype') == 'compact_boundary' or e.get('isCompactSummary'):
            break
        content = (e.get('message') or {}).get('content') if isinstance(e.get('message'), dict) else None
        if not isinstance(content, list):
            continue
        for b in content:
            if not isinstance(b, dict):
                continue
            if b.get('type') == 'tool_result' and b.get('is_error'):
                failed.add(b.get('tool_use_id'))
            if b.get('type') != 'tool_use' or e.get('type') != 'assistant' or b.get('id') in failed:
                continue
            i, cwd = b.get('input') or {}, e.get('cwd') or '/'
            at = lambda x: os.path.realpath(os.path.join(cwd, os.path.expanduser(re.sub(r'^\$(PWD\b|\{PWD\})', lambda _: cwd, x))))
            if b.get('name') == 'Read' and i.get('file_path'):
                seen.add(at(str(i['file_path'])))
            elif b.get('name') == 'Bash':
                try:
                    segs = segments(str(i.get('command') or ''))
                except ValueError:
                    continue
                for s in segs:  # `cd <dir>` moves where the later commands' relative paths point
                    t = prog(s)
                    p, a = (os.path.basename(t[0]), t[1:]) if t else ('', [])
                    if p in ('cd', 'pushd') and a:
                        cwd = at(a[0])
                    elif p == 'cat':
                        seen |= {at(x) for x in a if not x.startswith('-')}
                    elif p == 'sed' and not in_place(a):
                        seen |= {at(x) for x in sed_files(a)}
    return seen


if __name__ == '__main__':  # bin/pr-steps: the record path of the checked-out branch for kind sys.argv[1]
    print(branch_record(os.getcwd(), sys.argv[1]) or sys.exit(f'{os.getcwd()} is not in a git work tree'))
