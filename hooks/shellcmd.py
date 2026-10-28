"""Shell command parsing and transcript reading shared by the hooks (pre-bash-guard, pre-design-gate, pre-skill-gate,
post-bash-register, stop-lint).
parse() reads a command with mvdan/sh, bash's syntax as shfmt parses it (hooks/requirements.txt, installed on first use into
~/.mergeworthy/pydeps): every simple command it runs, in substitutions, heredocs a shell reads, `bash -c` and `eval` too. A
command that doesn't parse, or a parser that can't be installed, yields the command's words split roughly, with the error,
so a hook checks what it can and blocks a guarded verb it can't check."""
import hashlib, itertools, json, os, re, subprocess, sys


def branch_record(d, kind):
    """The pr-steps record kept once per repo and branch (preflight, approach; same key as bin/pr-steps), None outside git."""
    git = lambda *a: subprocess.run(['git', '-C', d, *a], capture_output=True, text=True).stdout.strip()
    common = git('rev-parse', '--git-common-dir')
    if not common:
        return None
    root = os.path.realpath(os.path.join(d, common))
    rec = lambda b: os.path.expanduser(f'~/.claude/pr-steps/{kind}.' + hashlib.sha256((root + '\n' + b).encode()).hexdigest()[:40])
    branch = git('symbolic-ref', '--short', '-q', 'HEAD') or 'HEAD'
    # a worktree on its own local branch tracking the PR's branch shares that branch's records
    up = git('rev-parse', '--abbrev-ref', '--symbolic-full-name', '@{u}').split('/', 1)[-1]
    return next((rec(b) for b in (branch, up) if b and os.path.exists(rec(b))), rec(branch))


def folder(path):
    """path when it is a folder, else its nearest existing parent (a new file's folder may not exist yet)."""
    path = os.path.realpath(path)
    while not os.path.isdir(path): path = os.path.dirname(path)
    return path


def no_preflight(path):
    """Why code can't start yet in the repo and branch holding path, or '' (outside git, nothing to check; a branch sharing no history with
    the remote's default branch, such as one holding a PR's screenshots, holds no code of the product)."""
    d = folder(path)
    rec = branch_record(d, 'preflight')
    if not rec or os.path.exists(rec):
        return ''
    if subprocess.run(['git', '-C', d, 'merge-base', 'HEAD', 'refs/remotes/origin/HEAD'], capture_output=True).returncode == 1:
        return ''
    return ("no `pr-steps preflight` record for this repo and branch. Before any code, start the app, then run "
            "`pr-steps preflight <its URL> [Chrome flags]` (or `<PNG the session's browser MCP just took>`), "
            "or `pr-steps preflight 'none, because <why there is no UI or browser-run code>'`")


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
    """A word as bash passes it (_word), with script: the text a shell that reads it as a script gets, the parent having expanded it
    first, each of the parent's expansions made _parent's placeholder; splits: whether it holds an unquoted expansion, which bash
    splits, globs and drops when empty; tilde: whether it starts with an unquoted ~, which bash expands (a value's, in an assignment);
    literal: the word with each $ and ` bash keeps as it is (quoted or escaped) marked (_LITERAL), when it has one."""
    script, splits, tilde, literal = None, False, None, None


_LITERAL = str.maketrans('$`', '\0\1')  # a literal $ and `, which Where.expand leaves alone


def _plain(w):
    """A Word.literal (or any text) with its literal $ and ` back."""
    return w.replace('\0', '$').replace('\1', '`')


def _script(w):
    return w if getattr(w, 'script', None) is None else w.script


PARENT = '__mwp_'  # a placeholder's prefix: ${__mwp_7_D} holds the value $D had in the parent shell
_pids = itertools.count()


def _parent(p):
    """The placeholder for the parent's expansion p in a script it hands on: ${__mwp_<n>_D} for $D or ${D}, whose value Where takes in
    the parent, n telling it from one a script nested in it carries on; ${__mwp_}, never set, for any other (`${D:-x}`, `$(...)`,
    whose commands are the parent's own)."""
    n = (p.get('Param') or {}).get('Value', '')
    simple = p.get('Type') == 'ParamExp' and re.fullmatch(r'[A-Za-z_]\w*', n) and not any(p.get(k) for k in ('Exp', 'Repl', 'Index', 'Slice', 'Length', 'Excl', 'Names', 'Width'))
    return '${' + PARENT + (f'{next(_pids)}_{n}' if simple else '') + '}'


def _placeholders(script, word=''):
    """The frame entries giving the placeholders script got from its word (those not in the word itself) their parent's values: env-argument
    ones, expanded before the prefix applies. One the word holds already came from further out, and keeps its value."""
    names = [m for m in dict.fromkeys(re.findall(r'\$\{(' + PARENT + r'\d+_(\w+))\}', script)) if '${' + m[0] + '}' not in word]
    return tuple((f'{m}=${{{n}}}', False) for m, n in names)


def _word(w, src):
    """A word as bash passes it: quotes and escapes removed; expansions and substitutions as written (a Word)."""
    out, sc, lt = [], [], []  # the word, its script, its literal
    for p in w.get('Parts') or []:
        t, v = p.get('Type'), p.get('Value', '')
        if t == 'Lit':
            out.append(re.sub(r'\\(.)', r'\1', v.replace('\\\n', ''), flags=re.S))
        elif t == 'SglQuoted':
            out.append(v.encode('latin-1', 'backslashreplace').decode('unicode_escape', 'replace') if p.get('Dollar') else v)
        elif t == 'DblQuoted':
            for x in p.get('Parts') or []:
                out.append(re.sub(r'\\([$`"\\])', r'\1', x.get('Value', '').replace('\\\n', '')) if x.get('Type') == 'Lit' else _src(x, src))
                sc.append(out[-1] if x.get('Type') == 'Lit' else _parent(x))
                lt.append(out[-1].translate(_LITERAL) if x.get('Type') == 'Lit' else out[-1])
            continue
        else:
            out.append(_src(p, src))
            sc.append(_parent(p))
            lt.append(out[-1])
            continue
        sc.append(out[-1])
        lt.append(out[-1].translate(_LITERAL))
    word = Word(''.join(out))
    literal = ''.join(lt)
    word.literal = literal if literal != word else None
    parts = w.get('Parts') or []
    word.script, word.splits = ''.join(sc), any(p.get('Type') not in ('Lit', 'SglQuoted', 'DblQuoted') for p in parts)
    word.tilde = bool(parts) and parts[0].get('Type') == 'Lit' and parts[0].get('Value', '')[:1] == '~'
    return word


def _heredoc(r, src):
    """The text a shell reading heredoc r gets: as written under a quoted delimiter, else with the parent's expansions done (_parent)."""
    parts = r['Hdoc'].get('Parts') or []
    if re.search(r'[\'"\\]', _src(r['Word'], src)):
        return ''.join(_src(p, src) for p in parts)
    return ''.join(re.sub(r'\\([$`\\])', r'\1', p.get('Value', '').replace('\\\n', '')) if p.get('Type') == 'Lit' else _parent(p) for p in parts)


def _assign(a, src):
    if a.get('Naked'):
        return a['Name']['Value'] if a.get('Name') else _word(a['Value'], src)
    v = _word(a['Value'], src) if a.get('Value') else _src(a['Array'], src) if a.get('Array') else ''
    word = Word(a['Name']['Value'] + '+' * bool(a.get('Append')) + '=' + v)
    word.tilde = getattr(v, 'tilde', False)
    word.literal = getattr(v, 'literal', None) and word[:len(word) - len(v)] + v.literal
    return word


_ids = itertools.count()


class Seg(list):
    """A simple command's argv. frames: the scopes it runs in, outermost first, each (id, kind, the variables set on entering it: a
    loop's own, unknown; a child shell's, (word, whether it sees the ones before it) of its command's prefix or env's arguments,
    `D=x bash -c`, and its script's placeholders, _parent). Kinds: 'sub' (a copy of the shell: a subshell, substitution, pipeline
    part or background job), 'proc' (a child bash: `bash -c`, a heredoc bash reads), 'sh' (a child shell that isn't bash: no dir
    stack or `declare`), 'user' (a shell whose environment can't be told: another user's, `sudo bash -c`, `su -c`, fish, or one
    `env` with options starts), 'cond' (it may not run: after ||, an if or case branch), 'and' (after &&: it runs once what &&
    follows succeeded), 'loop' (a loop's body, run again and again), 'opaque' (run where it can't be told: a function's body,
    `D=x eval`, a command that doesn't parse) or 'eval' (eval's script, in this shell, with its placeholders). negated: run as `! cmd`."""
    frames, negated = (), False


def _seg(argv, frames):
    s = Seg(argv)
    s.frames = frames
    return s


def _kind(x, k):
    """The kind of frame node x's child k runs in, or None for x's own."""
    t = x.get('Type')
    if t in ('Subshell', 'CmdSubst', 'ProcSubst', 'CoprocClause') or k == 'Cmd' and x.get('Background'):
        return 'sub'
    if t == 'BinaryCmd':
        return 'sub' if x.get('Op') in ('|', '|&') else ('and' if x.get('Op') == '&&' else 'cond') if k == 'Y' else None
    if t in ('IfClause', 'CaseClause') and k in ('Then', 'Else', 'Items'):
        return 'cond'
    return {'WhileClause': 'loop', 'ForClause': 'loop', 'FuncDecl': 'opaque'}.get(t)


def _calls(node, src, depth, frames):
    """(the argv of every simple command under node, in the order they run, each a Seg; the error of a script in it that doesn't
    parse). The script a command runs (`bash -c`, `eval`, find's -exec) follows it, as does a heredoc a shell without a script reads
    (`bash <<EOF`, `cat <<EOF | sh`); another heredoc's substitutions follow its statement."""
    segs, err, docs, stack = [], '', {}, [(node, None, frames)]
    while stack:
        x, top, fr = stack.pop()
        if top == 'end':  # x: (a top statement, the index of its first command): what its heredocs run
            stmt, start = x
            shell = next((i for i in range(start, len(segs)) if reads_stdin(segs[i])), None) if depth < 4 else None
            for r, rfr in docs.pop(id(stmt), []):
                if shell is not None:  # the parent's own substitutions in it, then the shell's script
                    text, (ps, e) = _heredoc(r, src), _calls(r['Hdoc'], src, depth, rfr)
                    raw = ''.join(_src(p, src) for p in r['Hdoc'].get('Parts') or [])
                    s, e2 = parse(text, depth + 1, segs[shell].frames + (_child(segs[shell], text, raw),))
                    segs[shell + 1:shell + 1], shell, e = ps + s, shell + len(ps) + len(s), e or e2
                else:
                    s, e = _calls(r['Hdoc'], src, depth, rfr)
                    segs += s
                err = err or e
            continue
        if isinstance(x, list):
            stack += [(y, top, fr) for y in reversed(x)]
            continue
        if not isinstance(x, dict):
            continue
        if 'Cmd' in x and top is None:  # each statement of a list is a top statement
            stack.append(((x, len(segs)), 'end', fr))
            top = x
        ids = {}  # the frame each child runs in: one per pipeline part or branch, one for a whole loop or function
        loop = tuple(n['Value'] for n in [(x.get('Loop') or {}).get('Name')] if n) if x.get('Type') == 'ForClause' else ()
        kids = {k: fr + ((ids.setdefault(k if kind in ('sub', 'cond', 'and') else '', next(_ids)), kind, loop),) if (kind := _kind(x, k)) else fr for k in x}
        cmd, redirs = x.get('Cmd') or {}, x.get('Redirs') or []
        words = [w for r in redirs for w in ((r.get('N') or {}).get('Value', '') + r['Op'], _word(r.get('Word') or {}, src))]
        if cmd.get('Type') == 'CallExpr':
            argv = [_assign(a, src) for a in cmd.get('Assigns') or []] + [_word(a, src) for a in cmd.get('Args') or []] + words
        elif cmd.get('Type') == 'DeclClause':
            argv = [cmd['Variant']['Value']] + [_assign(a, src) for a in cmd.get('Args') or []] + words
        if cmd.get('Type') in ('CallExpr', 'DeclClause'):
            segs.append(_seg(argv, kids.get('Cmd', fr)))
            segs[-1].negated = bool(x.get('Negated'))
            s, e = _inner(segs[-1], depth)
            segs += s
            err = err or e
        if redirs and any(r.get('Hdoc') for r in redirs):
            docs.setdefault(id(top), []).extend((r, kids.get('Cmd', fr)) for r in redirs if r.get('Hdoc'))
        stack += [(v, None if k == 'Stmts' else top, kids[k])
                  for k, v in reversed(x.items()) if isinstance(v, (dict, list)) and k not in ('Pos', 'End', 'Hdoc')]
    return segs, err


def _inner(s, depth):
    """The commands segment s runs as further commands, with the error of a script among them that doesn't parse: find's -exec
    commands, and the script of `bash -c`, `eval` or a here-string a shell reads (`bash <<< '<script>'`)."""
    t, out, err = prog(s), [], ''
    fr = getattr(s, 'frames', ())
    if t[:1] and os.path.basename(t[0]) == 'find':  # find -exec <command> ;
        out += [_seg(x.split('\0'), fr + ((next(_ids), 'proc', ()),)) for x in re.findall(r'\0-(?:exec|execdir|ok|okdir)\0(.+?)\0(?:;|\+)(?=\0|$)', '\0' + '\0'.join(t))]
    here = [s[i + 1] for i in range(len(s) - 1) if s[i] == '<<<']
    script = (_nested(s) or (here[0] if here and reads_stdin(s) else None)) if depth < 4 else None
    if script:
        eval_ = t and os.path.basename(t[0]) == 'eval'  # in this shell; with a prefix (`D=x eval ...`), only for its duration
        text = _script(script)
        frame = _child(s, text, script) if not eval_ else (next(_ids), 'opaque', ()) if len(t) < len(s) else (next(_ids), 'eval', _placeholders(text, script))
        inner, err = parse(text, depth + 1, fr + (frame,))
        out += inner
    return out, err


def _child(s, script='', word=''):
    """The frame of the child shell segment s starts to run script (from word): 'proc' (bash) or 'sh' (another shell), with the assignments that
    set its environment, each (word, whether it sees the ones before it: true for the command's prefix, false for env's arguments
    and the script's placeholders), or 'user' (another user's shell, fish, `env` with options, a prefix appending to a variable)."""
    t = prog(s)
    pre = s[:len(s) - len(t)]
    names = [os.path.basename(w) for w in pre + t[:1]]
    if {'sudo', 'su', 'runuser', 'fish'} & set(names) or 'env' in names and any(w.startswith('-') for w in pre[names.index('env'):]) or \
            any(re.match(r'\w+\+=', w) for w in pre):
        return next(_ids), 'user', ()
    kind = 'proc' if not t or os.path.basename(t[0]) == 'bash' else 'sh'
    lead = next((i for i, w in enumerate(pre) if not re.match(r'\w+=', w)), len(pre))
    return next(_ids), kind, tuple((w, i < lead) for i, w in enumerate(pre) if re.match(r'\w+=', w)) + _placeholders(script, word)


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
        words = t if ' ' in t[0] else a
        script = Word(' '.join(words))
        script.script = ' '.join(map(_script, words))
        return script
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


def parse(cmd, depth=0, frames=()):
    """(segments, error): the argv of every simple command cmd runs, in the order they run, each a Seg run in frames and its own,
    command substitutions and the scripts of `bash -c` and `eval` included; error is '' when it parsed, else why not (the segments
    are then _rough's, run where Where can't tell)."""
    try:
        r = subprocess.run([os.path.join(_deps(), 'bin', 'shfmt'), '--to-json', '-ln', 'bash'], input=cmd.encode(), capture_output=True, timeout=60)
        if r.returncode:
            raise ValueError('bash syntax error at ' + r.stderr.decode(errors='replace').strip().replace('<standard input>:', ''))
        return _calls(json.loads(r.stdout), cmd.encode(), depth, frames)
    except ValueError as e:  # also a JSON error
        err = str(e)
    except Exception as e:  # no parser: nothing is checked as parsed, and a guarded verb blocks
        err = f"mergeworthy's shell parser (shfmt, {REQUIREMENTS}) can't run: {e}"
    segs, fr = [], frames + ((next(_ids), 'opaque', ()),)
    for s in (_seg(x, fr) for x in _rough(cmd)):
        inner, e = _inner(s, depth)
        segs += [s, *inner]
        err = err or e
    return segs, err


def segments(cmd):
    """parse()'s segments."""
    return parse(cmd)[0]


# The verbs the hooks check: a command holding one that doesn't parse is blocked (pre-bash-guard), never let through unchecked
GUARDED = re.compile(r'\b(?:git\b.*?\b(?:push|commit)|gh\s+(?:pr|issue|api|release)|glab\s+(?:issue|mr)|(?:curl|wget|xh|https?)\b.*?\bapi\.github\.com)\b', re.S)

# Wrappers that run the command after them, with the options each takes a value for (`timeout 200`, `nice -n 19`, `env -u X`)
WRAPPERS = {'sudo': ('-u', '-g', '-h', '-p', '-C', '-D', '-r', '-t', '-U'), 'env': ('-u', '-C', '--unset', '--chdir'), 'command': (),
            'time': (), 'exec': (), 'nohup': (), 'setsid': (), 'netns-run': (), 'builtin': (),
            'nice': ('-n',), 'ionice': ('-c', '-n'), 'stdbuf': (), 'timeout': ('-s', '-k', '--signal', '--kill-after'),
            'watch': ('-n', '-d', '--interval'), 'parallel': ('-j', '--jobs'), 'xargs': ('-I', '-n', '-P', '-L', '-d', '-a', '-E', '-s', '--max-args', '--max-procs', '--delimiter', '--arg-file')}
WRAPPERS.update({'npx': (), 'pnpx': (), 'bunx': (), 'chronic': (), 'taskset': (), 'flock': ('-w', '-E'), 'direnv': (), 'runuser': ('-u', '-g')})
POSITIONAL = {'timeout': 1, 'taskset': 1, 'flock': 1, 'direnv': 2}  # `timeout 20`, `taskset 0x1`, `flock <file>`, `direnv exec <dir>`
RUNNERS = {'pnpm': ('exec', 'dlx'), 'npm': ('exec',), 'yarn': ('exec', 'dlx'), 'bun': ('x',), 'uv': ('run',), 'uvx': ()}  # `pnpm exec git ...`
KEYWORDS = ('!', '{', 'if', 'then', 'else', 'elif', 'do', 'while', 'until')  # a command after these still runs


def prog(t):
    """Drop env assignments, shell keywords and wrappers (with their options, and timeout's duration); return the command's argv."""
    while t:
        if re.match(r'^\w+\+?=', t[0]) or t[0] in KEYWORDS:
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


class Where:
    """Where each simple command of one command line runs, walk() taking them in order: the dir a cd, pushd or popd moves (with
    `cd -` and the dir stack), and the variables the line set (`W=~/x; cd $W`, `export`, a value expanded when it is assigned, a
    command's prefix for the child shell it starts: `D=x bash -c`).
    What it can't tell is None, the dir included: after a cd to an expansion it can't resolve, a `source`, or a change where it
    may not run (after && or ||, in an if or case branch, a loop or a function); inside a function, and a loop that changes either.
    A subshell's or child shell's changes end with it."""
    def __init__(self, cwd):
        self.dir, self.old, self.stack, self.vars, self.exported, self.lost, self.moved = cwd, None, [], {}, set(), False, False
        self.pending = None  # (dir, old dir, stack) of the cd just run that may have failed: where a command after && runs
        self.carry = None  # the state an 'and' frame just left ended in, and what changed in it: where the next && in the chain goes on
        self.written = {}  # each variable's last value as written (`C="$(echo git) push"`), for words a command named by it may run
        self.open = []  # the frames (Seg.frames) entered: (frame, the state on entering it, what changed in it: 'dir', 'lost', variable names)

    def expand(self, p):
        """p with the line's variables ($D, ${D}; $PWD and $OLDPWD where it runs, unless the line assigns them), then the environment's,
        put in; one it can't tell stays as written."""
        p = getattr(p, 'literal', None) or p
        def value(m):
            n = m[1] or m[2]
            v = None if n in ('PWD', 'OLDPWD') and n in self.vars else self.dir if n == 'PWD' else self.old if n == 'OLDPWD' else self.vars[n] if n in self.vars else None if self.lost else os.environ.get(n)
            return m[0] if v is None else v
        return _plain(re.sub(r'\$(?:(\w+)|\{(\w+)\})', value, p))

    def path(self, p, base=''):
        """p resolved from base (default: the dir), or None when it can't be told (an expansion left, an unknown base, a ~ after the
        line assigns HOME)."""
        p = self._home(getattr(p, 'literal', None) or p, getattr(p, 'tilde', None))
        p = p and self.expand(p)
        if p is None: return None
        base = self.dir if base == '' else base
        return None if re.search(r'[$`]', p) else p if os.path.isabs(p) else None if base is None else os.path.join(base, p)

    def walk(self, segs):
        """Each of segs (parse()'s), with self moved to where it runs; self takes it once the caller is done with it."""
        changing = {f[0] for t in segs for i, f in enumerate(getattr(t, 'frames', ())) if f[1] == 'loop' and _changes(t)
                    and not any(g[1] in ('sub', 'proc', 'sh', 'user') for g in t.frames[i + 1:])}
        for t in segs:
            frames = getattr(t, 'frames', ())
            while [f[0] for f in self.open] != list(frames[:len(self.open)]):
                self._leave(*self.open.pop())
            for f in frames[len(self.open):]:
                self._enter(f, f[0] in changing)
            yield t
            self.step(t)

    def _state(self):
        return self.dir, self.old, self.stack and list(self.stack), dict(self.vars), set(self.exported), self.lost

    def _enter(self, f, changing):
        self.open.append((f, self._state(), set()))
        carry, self.carry = self.carry, None
        if f[1] == 'and' and carry:  # `a && b && c`: c runs as b left it
            (to, old, stack, vars, _, _), changed = carry
            if 'dir' in changed: self._move(to, old, stack)
            for n in changed - {'dir', 'lost'}: self._set(n, vars.get(n))
        elif f[1] == 'and' and self.pending:
            self._move(*self.pending)
        sets = [((getattr(w, 'literal', None) or w).partition('='), ordered, getattr(w, 'tilde', None)) for w, ordered in (x for x in f[2] if not isinstance(x, str))]
        argv = [(n, self._value(v, t)) for (n, _, v), ordered, t in sets if not ordered]  # env's and placeholders: expanded with the command's words
        argv = [(n, v if not n.startswith(PARENT) or v is None or re.fullmatch(r'[\w./+,:@%=-]*', v) else None) for n, v in argv]  # a value the script reparses
        given, parent = [], dict(self.vars)
        for (n, _, v), ordered, t in sets:  # the prefix's, in order: each sees the ones before it
            if ordered:
                given.append((n, self._value(v, t)))
                self.vars[n] = given[-1][1]
        self.vars, given = parent, given + argv
        if f[1] in ('proc', 'sh', 'user'):  # a child shell gets the exported variables alone, and no dir stack
            self.vars = {} if f[1] == 'user' else {n: v if n in self.exported or n in os.environ else None for n, v in self.vars.items()}
            self.old, self.stack = None, []
        if f[1] in ('user', 'opaque') or changing:
            self.dir = self.old = self.stack = None
            self.vars, self.lost = {}, True
        for n in f[2]:
            if isinstance(n, str): self._set(n, None)
        for n, v in given:
            self._set(n, v)
            self.exported.add(n)

    def _leave(self, f, state, changed):
        if f[1] == 'eval': return  # it ran in this shell
        if f[1] == 'and' and self.pending: self.dir, self.old, self.stack = self.pending  # a && after it runs once that cd succeeded
        carry = (self._state(), changed) if f[1] == 'and' else None
        self.dir, self.old, self.stack, self.vars, self.exported, self.lost = state
        self.pending = None
        if f[1] in ('cond', 'and', 'loop', 'opaque'):  # what changed in it may or may not hold after it
            if 'dir' in changed: self._move(None, None, None)
            if 'lost' in changed: self.lost = True; self._changed('lost')
            for n in changed - {'dir', 'lost'}: self._set(n, None)
        self.carry = carry

    def _changed(self, what):
        for f in reversed(self.open):  # up to the innermost subshell or child shell: its changes end with it
            f[2].add(what)
            if f[0][1] in ('sub', 'proc', 'sh', 'user'): break

    def _set(self, name, value):
        self.vars[name] = value
        self._changed(name)

    def _move(self, to, old, stack):
        self.dir, self.old, self.stack, self.moved = to, old, stack, True
        self._changed('dir')

    def step(self, t):
        """Take the simple command t, which ran: the variables it set, the dir it moved to."""
        self.pending = self.carry = None
        if t and all(re.match(r'^\w+\+?=', x) for x in t):
            for x in t: self._assign(x)
            return
        p = prog(t)
        name, a = (os.path.basename(p[0]), p[1:]) if p else ('', [])
        if name in ('declare', 'typeset', 'pushd', 'popd') and next((f[0][1] for f in reversed(self.open) if f[0][1] in ('proc', 'sh', 'user')), '') == 'sh':
            if name in ('pushd', 'popd'): self._move(None, self.dir, None)  # bash's own: in another shell they fail or differ
            for n in (re.match(r'\w+', x) for x in a if name in ('declare', 'typeset')):
                if n: self._set(n[0], None)
            return
        if name in ('export', 'declare', 'typeset', 'local', 'readonly'):
            flags = ''.join(x[1:] for x in a if x[:1] in '-+')
            for x in a:
                if x[:1] in '-+' or not (n := re.match(r'\w+', x)): continue
                if '=' in x: self._assign(x) if set(flags) <= set('xgr') else self._set(n[0], None)  # -a, -i, -n: a value it doesn't hold
                if name == 'export' or 'x' in flags: self.exported.add(n[0])
        elif name in ('read', 'mapfile', 'readarray', 'unset', 'getopts', 'let', 'printf'):  # set what they read or compute
            for x in opt(a, ['-v']) if name == 'printf' else [x for x in a if not x.startswith('-')]:
                if n := re.match(r'\w+', x): self._set(n[0], None)
        elif name in ('source', '.'):
            self._move(None, None, None)
            self.lost = True
            self._changed('lost')
        elif name in ('cd', 'pushd', 'popd') and getattr(t, 'negated', False):  # `! cd x && ...` goes on when it fails
            self._move(None, None, None)
        elif name in ('cd', 'pushd', 'popd'):
            a = [x for x in operands(a) if x not in ('-P', '-L', '-e', '-@', '--')]  # not its redirects (`pushd x >/dev/null`)
            here, stack = self.dir, self.stack
            arg = self.expand(a[0]) if a else ''
            if a and getattr(a[0], 'splits', False) and a[0] != TOPLEVEL and not re.fullmatch(r'[^\s*?[]+', arg):  # split, globbed or dropped: what cd gets can't be told
                self._move(None, None, None)
            elif name == 'cd':
                self._go((None if 'OLDPWD' in self.vars else self.old) if arg == '-' else self._to(a[0] if a else '~'), here, stack, len(a) < 2)
            elif name == 'pushd' and a and arg[:1] not in '+-':
                self._go(self._to(a[0]), here, None if stack is None else [here] + stack, len(a) < 2)
            elif not a and stack:  # pushd swaps the top two, popd goes to the top one
                self._go(stack[0], here, [here] + stack[1:] if name == 'pushd' else stack[1:], True)
            else:  # a rotation, -n, or an empty stack
                self._move(None, here, None)

    def _go(self, to, old, stack, one):
        """cd's move to `to`, when bash surely gets there: one argument, a dir it may enter. Else the dir can't be told, but a
        command after && runs there."""
        if one and to is not None and os.path.isdir(to) and os.access(to, os.X_OK):
            return self._move(to, old, stack)
        self._move(None, None, None)
        self.pending = (to, old, stack) if one and to is not None else None

    def _assign(self, x):
        n, plus, v = re.match(r'(\w+)(\+?)=(.*)', getattr(x, 'literal', None) or x, re.S).groups()
        self.written[n] = _plain(v)
        self._set(n, self._value('${' + n + '}' + v, False) if plus else self._value(v, getattr(x, 'tilde', None)))

    def _value(self, v, tilde=None):
        """An assignment's value v as the shell stores it, or None when it can't be told."""
        v = self._home(v, tilde)
        v = v and self.expand(v)
        return None if v is None or re.search(r'[$`]', v) else v

    def _home(self, p, tilde=None):
        """p with its leading ~ expanded when bash expands it (unquoted: tilde, else p's own, Word.tilde), or None for one once the line
        assigns HOME; a ~ an expansion puts in stays as it is."""
        tilde = getattr(p, 'tilde', None) if tilde is None else tilde
        if not (p[:1] == '~' if tilde is None else tilde):
            return p
        return None if 'HOME' in self.vars and re.match(r'~(/|$)', p) else os.path.expanduser(p)

    def _to(self, to):
        """Where cd or pushd goes for `to`, or None; a relative one under a CDPATH (the environment's or the line's) may go elsewhere."""
        if to == TOPLEVEL:  # unquoted, a top dir holding a space or a glob splits
            top = self.dir and subprocess.run(['git', '-C', self.dir, 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip() or None
            return None if top and getattr(to, 'splits', False) and re.search(r'\s|[*?[]', top) else top
        cdpath = self.vars['CDPATH'] if 'CDPATH' in self.vars else None if self.lost else os.environ.get('CDPATH', '')
        return None if (cdpath is None or cdpath) and not os.path.isabs(self.expand(self._home(to) or '/')) else self.path(to)


def _changes(t):
    """Whether the simple command t changes the dir or a variable."""
    w = Where('/')
    w.step(t)
    return w.moved or w.lost or bool(w.vars)


def git_argv(t, where):
    """(git dir, -c overrides, subcommand, its arguments) of a git argv run at where (a Where), past its global options (each -C
    applies in turn, with where's variables; the dir is None when it can't be told); a configured alias (`git config alias.p push`, or `-c alias.p=push`) is expanded,
    so `git p` is checked as the push it runs."""
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

def api_call(rest):
    """(method, endpoint, fields, inputs, posts) of `gh api <rest>`. It posts text when it is a GraphQL mutation, or a POST,
    PATCH or PUT that isn't a reaction, rerun, dispatch, label, assignee or review request."""
    method = (opt(rest, ['-X', '--method']) or [''])[-1].upper()
    fields = opt(rest, ['-f', '--raw-field', '-F', '--field'])
    inputs = opt(rest, ['--input'])
    if not method: method = 'POST' if fields or inputs else 'GET'
    pos = [x for i, x in enumerate(rest) if not x.startswith('-') and (i == 0 or rest[i - 1] not in
           ('-X', '--method', '-f', '--raw-field', '-F', '--field', '--input', '-H', '--header', '-q', '--jq', '-t', '--template', '--hostname', '--cache', '-p', '--preview'))]
    ep = pos[0] if pos else ''
    if ep == 'graphql':
        posts = any(re.search(r'\bmutation\b', v) and re.search(r'\b(?!(?:add|remove)Reaction\b)[a-z]\w*\s*\(input:', v) for v in fields)  # a reaction posts no text
    else:
        posts = method in ('POST', 'PATCH', 'PUT') and not re.search(r'/(reactions|rerun[\w-]*|dispatches|labels|assignees|requested_reviewers)(/|$|\?)', ep)
    return method, ep, fields, inputs, posts

def new_post_drafts(t):
    """Draft files a gh argv posts as something new (an issue, PR, comment or review): each draft is posted as new once, edits may repeat."""
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
