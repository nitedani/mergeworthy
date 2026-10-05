#!/usr/bin/env python3
"""Claude Code PreToolUse hook (matcher: Bash). Exit 2 blocks the command; stderr goes to the agent.
Checks each simple command separately (split at ; && || | & and newlines, heredoc bodies and quoted text ignored).
MERGEWORTHY_MERGE=reviewer blocks every `gh pr merge`."""
import json, re, sys, os, hashlib, shlex, subprocess
def setting(name, default):
    """MERGEWORTHY_<name> from the environment, else from ~/.mergeworthy/settings.env (written at session start from the plugin's options)."""
    f = os.path.expanduser('~/.mergeworthy/settings.env')
    saved = dict(l.strip().split('=', 1) for l in open(f) if '=' in l) if os.path.exists(f) else {}
    return os.environ.get(f'MERGEWORTHY_{name}') or saved.get(f'MERGEWORTHY_{name}', default)
d = json.load(sys.stdin)
cmd = d.get('tool_input', {}).get('command', '')
cwd = d.get('cwd') or os.getcwd()
def block(msg):
    print(f"BLOCKED by pre-bash-guard: {msg}", file=sys.stderr); sys.exit(2)

def segments(cmd):
    """Token lists of the simple commands in cmd. Heredoc bodies are dropped; quotes are resolved by shlex."""
    cmd = re.sub(r'\\\n', ' ', cmd)
    lines, out, term = cmd.split('\n'), [], None
    for l in lines:
        if term is not None:
            if l.strip() == term: term = None
            continue
        h = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", l)
        if h: term = h.group(1)
        out.append(l)
    segs = []
    for l in out:
        lx = shlex.shlex(l, posix=True, punctuation_chars=';&|<>()')
        lx.whitespace_split = True
        cur = []
        for tok in lx:  # raises ValueError on unbalanced quotes
            if tok and set(tok) <= set(';&|()'):
                if cur: segs.append(cur)
                cur = []
            else:
                cur.append(tok)
        if cur: segs.append(cur)
    return segs

def prog(t):
    """Drop env assignments and wrappers; return the command's argv."""
    while t and (re.match(r'^\w+=', t[0]) or t[0] in ('sudo', 'env', 'command', 'time', 'exec', 'nohup')):
        t = t[1:]
    return t

def short_has(t, letter):  # -f, -9f, -fu ...
    return re.match(r'^-[A-Za-z0-9]*' + letter + r'[A-Za-z0-9]*$', t) is not None

def gated_file(p, has_cd, create=False):
    p = os.path.expandvars(os.path.expanduser(p))
    if not os.path.isabs(p):
        if has_cd:
            block(f"relative draft path {p} after a cd: use an absolute path")
        p = os.path.join(cwd, p)
    gate = p + '.gate'
    if not os.path.exists(p) or not os.path.exists(gate):
        block(f"no gate record for {p}: run post-lint + the review until CLEAN, then `gate-pass {p} <review-output>`")
    sha = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    if sha != open(gate).read().strip():
        block(f"{p} changed after its gate: review it again and re-run gate-pass")
    if create:  # a new comment/issue/PR from this exact draft: only once (edits may repeat)
        posted = p + '.posted'
        if os.path.exists(posted) and open(posted).read().strip() == sha:
            block(f"{p} was already posted: edit that post instead (PATCH / gh … edit); if the earlier post failed, delete {posted}")
        open(posted, 'w').write(sha)

def check_commit_identity(overrides, git_dir):
    """Commits are authored as the GitHub account that pushes them, never the global git identity (a user checkout's worktrees share its config)."""
    import subprocess
    name = overrides.get('user.name') or subprocess.run(['git', '-C', git_dir, 'config', 'user.name'], capture_output=True, text=True).stdout.strip()
    r = subprocess.run(['gh', 'api', 'user', '--jq', '.login + " " + (.id|tostring)'], capture_output=True, text=True)
    if r.returncode != 0 or not r.stdout.strip():
        return  # offline: nothing to compare with
    login, uid = r.stdout.split()
    if name != login:
        block(f"commit author would be {name!r}: commit as the pushing account, `git -c user.name={login} -c user.email={uid}+{login}@users.noreply.github.com commit ...`")


def opt(t, names):
    """Values of options in names, in --x v, --x=v and -Xv forms."""
    vals = []
    for i, a in enumerate(t):
        for n in names:
            if a == n and i + 1 < len(t): vals.append(t[i + 1])
            elif n.startswith('--') and a.startswith(n + '='): vals.append(a[len(n) + 1:])
            elif not n.startswith('--') and a.startswith(n) and len(a) > len(n): vals.append(a[len(n):])
    return vals

def watch_dirs():
    """Watch dirs (gh-watch-start) whose daemon is alive."""
    reg = os.path.expanduser('~/.claude/gh-watch-dirs.txt')
    live = []
    for d in (l.strip() for l in open(reg)) if os.path.exists(reg) else ():
        try:
            pid = open(os.path.join(d, 'gh-watch.pid')).read().strip()
            if 'gh-watch-daemon' in subprocess.run(['ps', '-p', pid, '-o', 'command='], capture_output=True, text=True).stdout: live.append(d)
        except (OSError, ValueError):
            pass
    return live

def need_watch(repo):
    """Opening an issue or PR starts the live loop (mergeworthy:github-threads): a running watcher must cover the repo (post-bash-register adds
    the new thread). A comment on an existing thread isn't blocked here: post-bash-register adds that thread, and stop-lint requires a watcher's Monitor after any post."""
    if setting('WATCHER', 'on') != 'on' or not repo: return
    def lines(d, f):
        return [l.strip() for l in open(os.path.join(d, f))] if os.path.exists(os.path.join(d, f)) else []
    covering = [d for d in watch_dirs() if repo in lines(d, 'repos.txt') or any(l.split()[:1] == [repo] for l in lines(d, 'threads.txt'))]
    if not covering:
        block(f"no running watcher covers {repo}: `gh-watch-start <your artifact root> {repo}`, arm the Monitor it prints, then open it")

def check_turn(repo, num, args=()):
    """1.6 at most two comments in a row: while your last two comments on a thread have no reply after them and the last
    is under 3 hours old, a third stacks on them: edit the last one instead. After 3 hours, the third is the wait ping. The agent and the user may
    share one login, so a comment is the agent's only when its body was gated (gate-pass writes ~/.claude/gated-posts.txt)."""
    if '--help' in args or '-h' in args or not repo or not str(num).isdigit():
        return
    def api(path, jq):
        r = subprocess.run(['gh', 'api', path, '--jq', jq], capture_output=True, text=True, timeout=20)
        return r.stdout if r.returncode == 0 else ''
    try:
        n = int(api(f'repos/{repo}/issues/{num}', '.comments').strip() or 0)
        if n < 2: return
        page = lambda p: json.loads(api(f'repos/{repo}/issues/{num}/comments?per_page=100&page={p}', '[.[] | {body, created: .created_at, url: .html_url}]') or '[]')
        p = (n - 1) // 100 + 1
        last = page(p)
        if len(last) < 2 and p > 1: last = page(p - 1) + last
        last = last[-2:]
        reviews = api(f'repos/{repo}/pulls/{num}/reviews?per_page=100', '.[].submitted_at').split()  # 404 on an issue: none
        me = api('user', '.login').strip()
        # a maintainer's push after your comments answers them too (their commits deserve a review comment)
        reviews += [d for l in api(f'repos/{repo}/pulls/{num}/commits?per_page=100', '.[] | "\\(.author.login) \\(.commit.committer.date)"').splitlines()
                    for who, d in [l.split(' ', 1)] if who != me and who != 'null']
    except Exception:
        return
    f = os.path.expanduser(os.environ.get('GATED_POSTS', '~/.claude/gated-posts.txt'))
    gated = set(open(f).read().split()) if os.path.exists(f) else set()
    norm = lambda b: hashlib.sha256((b or '').replace('\r\n', '\n').strip().encode()).hexdigest()
    if len(last) < 2 or not all(norm(c['body']) in gated for c in last):
        return
    import datetime
    when = lambda t: datetime.datetime.fromisoformat(t.replace('Z', '+00:00'))
    if (datetime.datetime.now(datetime.timezone.utc) - when(last[-1]['created'])).total_seconds() >= 3 * 3600 or any(when(r) > when(last[-1]['created']) for r in reviews if r != 'null'):
        return
    block(f"your last two comments on {repo}#{num} have no reply yet ({last[-1]['url']}): edit the last one instead of posting a third; "
          "at most two comments in a row; after 3 hours without a reply, the wait ping may follow (mergeworthy:github-threads 1.6)")


def cwd_repo(run_dir):
    import subprocess
    url = subprocess.run(['git', '-C', run_dir, 'remote', 'get-url', 'origin'], capture_output=True, text=True).stdout.strip()
    m = re.search(r'github\.com[:/]([\w.-]+/[\w.-]+?)(\.git)?$', url)
    return m.group(1) if m else None

NEED_DRAFT = "post from a draft file (--body-file /abs/drafts/<name>.md, -F body=@/abs/drafts/<name>.md or --input) that passed the gate"

def check(t, has_cd):
    t = prog(t)
    if not t: return
    p, a = os.path.basename(t[0]), t[1:]
    if p == 'killall' or (p == 'pkill' and any(x == '--full' or (not x.startswith('--') and short_has(x, 'f')) for x in a)):
        block("never pkill -f / killall: kill your own processes by PID or port")
    if p == 'git':
        overrides = dict(a[i + 1].split('=', 1) for i in range(len(a) - 1) if a[i] == '-c' and '=' in a[i + 1])
        git_dir = next((a[i + 1] for i in range(len(a) - 1) if a[i] == '-C'), run_dir)
        while a and a[0].startswith('-'):  # global options: -C dir, -c k=v, --git-dir=...
            a = a[2:] if a[0] in ('-C', '-c') else a[1:]
        if not a: return
        sub, rest = a[0], a[1:]
        if sub == 'commit':
            check_commit_identity(overrides, os.path.join(run_dir, os.path.expanduser(git_dir)))
        if sub == 'stash':
            first = rest[0] if rest else ''
            ok = first in ('list', 'show', 'apply', 'branch', 'create', 'store') or \
                 (first == 'drop' and len(rest) > 1) or \
                 (first in ('push', 'save', '') or first.startswith('-')) and bool(opt(rest, ['-m', '--message']) or (first == 'save' and len(rest) > 1))
            if not ok:
                block("never bare git stash / pop / drop / clear: use a WIP commit, or `git stash push -u -m <tag>` + apply <sha>, then drop that entry by its ref")
        if sub == 'push':
            leases = [x for x in rest if x.startswith('--force-with-lease')]
            force = any(x in ('--force', '--mirror') or (not x.startswith('--') and x.startswith('-') and short_has(x, 'f'))
                        or (x.startswith('+') and len(x) > 1) for x in rest)
            if force or any(not re.match(r'^--force-with-lease=\S+:\S+$', x) for x in leases):
                block("force-push only with --force-with-lease=<branch>:<sha you last pushed>, after checking others' commits")
    if p == 'gh' and len(a) >= 2 and a[0] == 'pr' and ((a[1] == 'create' and '--draft' not in a and '-d' not in a) or (a[1] == 'ready' and '--undo' not in a)):
        head = subprocess.run(['git', '-C', run_dir, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
        rec = os.path.expanduser(f'~/.claude/pr-steps/{head}')
        kinds = {l.split()[0] for l in open(rec)} if head and os.path.exists(rec) else set()
        missing = [k for k in ('review', 'refactor') if k not in kinds]
        if missing:
            block(f"HEAD {head[:10] or '(no git repo in cwd)'} has no {' and no '.join(missing)} record: finish mergeworthy:converge's pipeline, then run `pr-steps review <fresh reader's output>` and `pr-steps refactor <Loop B's last re-rating>` on the final HEAD (again after a base merge); or open it with --draft")
    if p == 'gh' and len(a) >= 2 and a[0] == 'pr' and a[1] == 'merge':
        if setting('MERGE', 'on-request-squash') == 'reviewer':
            block('never merge: the reviewer merges this repo\'s PRs (MERGEWORTHY_MERGE=reviewer)')
        rest = a[2:]
        subj, body = opt(rest, ['--subject', '-t']), opt(rest, ['--body', '-b'])
        num = next((x for i, x in enumerate(rest) if re.fullmatch(r'\d+', x) and (i == 0 or not rest[i - 1].startswith('-'))), '')
        if not ('--squash' in rest or '-s' in rest) or not subj or not re.search(r' \(#' + (num or r'\d+') + r'\)$', subj[-1]) or body != ['']:
            block('squash-merge as the repo asks, by default `gh pr merge <N> --squash --subject "<exact PR title> (#<N>)" --body ""`; re-read the repo\'s AGENTS.md first')
        # Deleting a branch other open PRs are based on closes them (GitHub doesn't retarget them)
        if num and ('--delete-branch' in rest or '-d' in rest):
            repo = opt(rest, ['-R', '--repo'])
            rargs = ['-R', repo[-1]] if repo else []
            try:
                head = subprocess.run(['gh', 'pr', 'view', num, *rargs, '--json', 'headRefName', '-q', '.headRefName'],
                                      capture_output=True, text=True, timeout=20).stdout.strip()
                deps = subprocess.run(['gh', 'pr', 'list', *rargs, '--base', head, '--json', 'number', '-q', '[.[].number] | join(",")'],
                                      capture_output=True, text=True, timeout=20).stdout.strip() if head else ''
            except Exception:
                deps = ''
            if deps:
                block(f"open PRs #{deps} are based on {head}: retarget them first (`gh pr edit <N> --base <new base>`), or merge without --delete-branch; deleting it closes them")
    if p == 'gh' and len(a) >= 2 and a[0] in ('issue', 'pr'):
        sub, rest = a[1], a[2:]
        if '--help' in rest or '-h' in rest:
            return  # reading gh's help posts nothing
        files = opt(rest, ['--body-file', '-F'])
        texts = [v for v in opt(rest, ['--body', '-b']) + (opt(rest, ['--comment', '-c']) if sub == 'close' else []) if v.strip()]
        if sub in ('comment', 'create', 'review') or (sub in ('edit', 'close', 'merge') and (files or texts)):
            if texts or not files:
                if sub == 'review' and not texts and not files and '--approve' in rest:
                    return  # an approval without a body posts no text
                block(NEED_DRAFT)
            if sub == 'create':
                need_watch((opt(rest, ['--repo', '-R']) or [None])[-1] or cwd_repo(run_dir))
            if sub == 'comment' and '--edit-last' not in rest:
                num = next((x for x in rest if x.isdigit()), None)
                check_turn((opt(rest, ['--repo', '-R']) or [None])[-1] or cwd_repo(run_dir), num, rest)
            for f in files: gated_file(f, has_cd, create=sub in ('comment', 'create', 'review'))
    if p == 'gh' and a and a[0] == 'api':
        rest = a[1:]
        method = (opt(rest, ['-X', '--method']) or [''])[-1].upper()
        fields = opt(rest, ['-f', '--raw-field', '-F', '--field'])
        inputs = opt(rest, ['--input'])
        if not method: method = 'POST' if fields or inputs else 'GET'
        pos = [x for i, x in enumerate(rest) if not x.startswith('-') and (i == 0 or rest[i - 1] not in
               ('-X', '--method', '-f', '--raw-field', '-F', '--field', '--input', '-H', '--header', '-q', '--jq', '-t', '--template', '--hostname', '--cache', '-p', '--preview'))]
        ep = pos[0] if pos else ''
        if ep == 'graphql':
            if not any(re.search(r'\bmutation\b', v) for v in fields): return
        elif method not in ('POST', 'PATCH', 'PUT') or re.search(r'/(reactions|rerun[\w-]*|dispatches|labels|assignees|requested_reviewers)(/|$|\?)', ep):
            return
        bodies = [v[len('body=@'):] for v in opt(rest, ['-F', '--field']) if v.startswith('body=@')]
        literal = [v for v in fields if re.match(r'^(body|query)=', v) and not v.startswith('body=@') and not (ep == 'graphql' and v.startswith('query='))]
        if literal or not (bodies or inputs):
            block(NEED_DRAFT)
        m = re.fullmatch(r'/?repos/([\w.-]+/[\w.-]+)/(?:issues|pulls)', ep)
        if m and method == 'POST': need_watch(m.group(1))
        c = re.fullmatch(r'/?repos/([\w.-]+/[\w.-]+)/issues/(\d+)/comments', ep)
        if c and method == 'POST': check_turn(c.group(1), c.group(2), rest)
        for f in bodies + inputs: gated_file(f, has_cd, create=method == 'POST')

try:
    segs = segments(cmd)
except ValueError:
    segs = [cmd.split()]  # unbalanced quotes: check the raw words
has_cd = False
run_dir = cwd  # where the command's git calls run: follows `cd <dir>` within the command
for s in segs:
    check(s, has_cd)
    if prog(s)[:1] in (['cd'], ['pushd']):
        has_cd = True
        if len(prog(s)) > 1: run_dir = os.path.join(run_dir, os.path.expanduser(prog(s)[1]))
sys.exit(0)
