#!/usr/bin/env python3
"""Claude Code PostToolUse and PostToolUseFailure hook (matcher: Bash). It settles the pushes, merges and closes pre-bash-guard
recorded as pending for the command (own_actions): its own once it succeeded, gone once it failed. A thread you just posted in (a new issue or PR, a comment, a review)
joins the threads.txt of a watcher whose events reach the posting session, so maintainer comments on it are answered (mergeworthy:reply):
the task's work folder holding the command's dir, whose watcher it starts or revives when it isn't running (gh-watch-start), else
the session's own, the one covering its repo first. Another session's watcher wakes that session alone, so it never gets the thread. A thread whose watcher would be a guess (posting
commands leading to different watchers, or one in a dir shellcmd.Where can't tell) joins none, and the hook says so (exit 2).
A gated draft it posted as new gets its .posted marker, which pre-bash-guard reads to refuse posting it as new again."""
import hashlib, json, os, re, shlex, sys, time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import failclosed
from shellcmd import segments, prog, new_post_drafts, Where, opened, plain_create
import own_actions, steward, work_folder
d = json.load(sys.stdin)
# the pushes, merges and closes pre-bash-guard let this command make are its own once it succeeded; a failed command's go
own_actions.settle(own_actions.key(d), d.get('hook_event_name') != 'PostToolUseFailure')
if d.get('hook_event_name') == 'PostToolUseFailure':
    sys.exit(0)
cmd = d.get('tool_input', {}).get('command', '')
r = d.get('tool_response') or {}
out = r.get('stdout', '') if isinstance(r, dict) else str(r)

def threads(text):
    """The threads text's URLs name, in order, each (repo, number, gh-watch-start's line): `owner/repo N`, or `gitlab.com/<path> N`
    for an issue and `gitlab.com/<path> !N` for an MR. The line names the thread whole: its repo, kind and number."""
    return [(m[1], m[2], f'{m[1]} {m[2]}') if m[1] else ('gitlab.com/' + m[3], m[5], f"gitlab.com/{m[3]} {'!' if m[4] == 'merge_requests' else ''}{m[5]}")
            for m in re.finditer(r'github\.com/([\w.-]+/[\w.-]+)/(?:issues|pull)/(\d+)|gitlab\.com/([\w.-]+(?:/[\w.-]+)+?)/-/(issues|work_items|merge_requests)/(\d+)', text)]  # glab prints new issues as work_items

def created(out):
    """The thread (as threads() names it) an API create's JSON response is, by its top-level html_url or web_url; None when the
    output isn't one such response (filtered, or several)."""
    try: v = json.loads(out)
    except ValueError: return None
    t = threads((v.get('html_url') or v.get('web_url') or '') if isinstance(v, dict) else '')
    return t[0] if len(t) == 1 else None

def target(t, d):
    """(repo or None, number or None[, the thread]) a posting gh argv, run in d, writes to; None when the argv doesn't post.
    Only a real `gh` argv counts: text that merely mentions one (an echo, a grep, a fixture) posts nothing.
    An issue, PR or MR an API call opens is told as pre-bash-guard tells it (shellcmd.opened), the thread by the response's own
    URL (created): a URL in the new thread's body isn't the thread."""
    if prog(t)[1:2] == ['api'] and (o := opened(t, d)):
        return (o[0], None, c) if (c := created(out)) else (o[0], None)
    t = prog(t)
    if t and os.path.basename(t[0]) == 'glab' and t[2:3] in (['create'], ['note']) and t[1] in ('issue', 'mr') and '--help' not in t and '-h' not in t:
        return None, None  # glab prints the thread's URL: that names it
    if not t or os.path.basename(t[0]) != 'gh' or len(t) < 2 or '--help' in t or '-h' in t:
        return None
    a = t[1:]
    if a[0] in ('issue', 'pr') and a[1:2] and a[1] in ('create', 'comment', 'review'):
        repo = next((x.split('=', 1)[1] for x in a if x.startswith('--repo=')), None) or \
            next((a[i + 1] for i in range(len(a) - 1) if a[i] in ('--repo', '-R')), None)
        arg = a[2] if a[2:3] and not a[2].startswith('-') else ''
        m = re.search(r'github\.com/([\w.-]+/[\w.-]+)/(?:issues|pull)/(\d+)', arg)
        if m: return m.group(1), m.group(2)
        return repo, (arg if arg.isdigit() else None)
    if a[0] == 'api':
        m = next((re.match(r'/?repos/([\w.-]+/[\w.-]+)/(?:issues|pulls)\b(?:/(\d+))?', x) for x in a[1:]
                  if re.match(r'/?repos/[\w.-]+/[\w.-]+/(issues|pulls)\b', x)), None)
        method = next((x[2:] for x in a if x.startswith('-X') and len(x) > 2), None) or \
            next((a[i + 1] for i in range(len(a) - 1) if a[i] in ('-X', '--method')), None)
        body = any(x in ('-f', '-F', '--field', '--raw-field', '--input') or re.match(r'^--(field|raw-field|input)=', x) for x in a)
        if m and (method.upper() == 'POST' if method else body):
            return m.group(1), m.group(2)
    return None

segs = segments(cmd)  # a command that doesn't lex still yields its words: a post in it is still registered
# the drafts posted as new, and each posting segment's target with the dir it ran in, resolved as pre-bash-guard resolves them
cwd = d.get('cwd') or os.getcwd()
where, drafts, posts = Where(cwd), [], []
for s in where.walk(segs):
    drafts += [os.path.join(cwd, os.path.expanduser(where.expand(f))) for f in new_post_drafts(s)]
    if tg := target(s, where.dir): posts.append((tg[0], tg[1], where.dir, tg[2] if len(tg) > 2 else None))
# Written here, not in pre-bash-guard: PostToolUse runs only after the command succeeded, so a post another hook blocked, or one that failed, can be retried
if isinstance(r, dict) and not r.get('interrupted'):
    for f in drafts:
        try:
            sha = hashlib.sha256(open(f, 'rb').read()).hexdigest()
            if open(f + '.gate').read().split('\n')[0].strip() == sha:
                open(f + '.posted', 'w').write(sha)
        except OSError:
            pass  # a draft with no gate record wasn't posted (pre-bash-guard refuses it); one gone since can't be posted again
if not posts:
    sys.exit(0)
def wrote(post, th):  # whether that posting segment can have written the thread th (threads()'s); one that names its thread, only that one
    return post[3] == th if post[3] else (post[0] is None or post[0] == th[0]) and (post[1] is None or post[1] == th[1])
def posted(th):  # a URL in stdout counts only when it is the thread a posting segment wrote to
    return any(wrote(p, th) for p in posts)
# The agent and the user may share one login, so the watcher knows a comment is the agent's by its body's hash.
# `gh --attach` rewrites the body as it posts, so register the body that was actually posted, not only the draft's.
import subprocess
def register_posted(out):
    gated = os.path.expanduser(os.environ.get('GATED_POSTS', '~/.claude/gated-posts.txt'))
    for repo, num, kind, cid in re.findall(r'github\.com/([\w.-]+/[\w.-]+)/(?:issues|pull)/(\d+)(?:#(issuecomment|discussion_r)-?(\d+))?', out):
        if not posted((repo, num, f'{repo} {num}')):
            continue
        path = {'issuecomment': f'repos/{repo}/issues/comments/{cid}', 'discussion_r': f'repos/{repo}/pulls/comments/{cid}'}.get(kind, f'repos/{repo}/issues/{num}')
        try:
            r = subprocess.run(['gh', 'api', path, '--jq', '.body'], capture_output=True, text=True, timeout=20)
        except Exception:
            continue
        if r.returncode == 0 and r.stdout.strip():
            body = r.stdout[:-1] if r.stdout.endswith('\n') else r.stdout
            open(gated, 'a').write(hashlib.sha256(body.replace('\r\n', '\n').strip().encode()).hexdigest() + '\n')
register_posted(out)
# Count a posted design proposal per thread (pre-bash-guard asks for a finality map from the third on)
def body_files(t):
    a = prog(t)
    return [a[i + 1] for i in range(len(a) - 1) if a[i] in ('--body-file', '-F', '--field', '--input')] + \
        [x.split('=', 1)[1] for x in a if x.startswith('--body-file=')]
for s in segs:
    tg = target(s, None)
    if not tg or not tg[0] or not tg[1]:
        continue
    for f in body_files(s):
        f = os.path.expanduser(f[len('body='):] if f.startswith('body=') else f)
        f = f[1:] if f.startswith('@') else f
        try:
            flags = open(f + '.lint').read().split()
        except OSError:
            continue
        if flags[flags.index('--kind') + 1:][:1] == ['proposal'] and os.path.exists(f + '.posted'):
            open(os.path.expanduser('~/.claude/proposal-rounds.txt'), 'a').write(f'{tg[0]}#{tg[1]} {int(time.time())}\n')
reg = os.path.expanduser('~/.claude/gh-watch-dirs.txt')
dirs = [l.strip() for l in open(reg)] if os.path.exists(reg) else []
def lines(dr, f):
    p = os.path.join(dr, f)
    return [l.strip() for l in open(p)] if os.path.exists(p) else []
def live(dr):
    try:
        os.kill(int(lines(dr, 'gh-watch.pid')[0]), 0)
        return True
    except (IndexError, OSError, ValueError):
        return False
sid = d.get('session_id')
# only a running daemon wakes anyone on the thread: a dir a steward pass read (gh-watch-start --round) has none
live_dirs = [dr for dr in dirs if live(dr)]
def home_of(repo, post_dir):
    """The watcher a new thread of repo posted from post_dir joins: the task's work folder holding post_dir, though its watcher isn't
    running (started below); elsewhere, of those reaching the session from there, one covering repo first."""
    if wf := work_folder.task_of(post_dir):
        return wf
    mine = work_folder.watched_by(live_dirs, sid, post_dir)
    covering = [dr for dr in mine if any(l.split()[:1] == [repo] for l in lines(dr, 'repos.txt') + lines(dr, 'threads.txt'))]
    return (covering + mine + [None])[0]
_env = os.path.expanduser('~/.mergeworthy/settings.env')  # MERGEWORTHY_WATCHER as stop-lint reads it
watcher_on = (os.environ.get('MERGEWORTHY_WATCHER') or ('off' if 'MERGEWORTHY_WATCHER=off' in (open(_env).read() if os.path.exists(_env) else '') else 'on')) != 'off'
START = os.environ.get('GH_WATCH_START') or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'bin', 'gh-watch-start')
told = []  # what the session must do after a start: arm the Monitor, or start it by hand
def start(home, line):
    """Starts or revives home's watcher with the thread, as this session's (its T3 thread, else the Monitor it prints)."""
    r = subprocess.run([START, home, *line.split()], capture_output=True, text=True, timeout=120, stdin=subprocess.DEVNULL,
                       env={**os.environ, 'CLAUDE_CODE_SESSION_ID': sid or ''})
    if r.returncode:
        told.append(f"`gh-watch-start {home} {line}` failed ({r.returncode}): {(r.stderr or r.stdout).strip()[-300:]}; run it yourself")
    elif 'Arm a Monitor' in r.stdout:
        told.append(f"started the watcher of {home} for {line}. " + r.stdout[r.stdout.index('Arm a Monitor'):].strip())
# each thread in stdout joins the one watcher every posting segment it fits leads to; one whose watcher would be a guess joins
# none, and the agent is told
found = [f for f in dict.fromkeys(threads(out)) if posted(f)]
pairs, lost = [], []
for repo, num, line in found:
    fits = [p for p in posts if wrote(p, (repo, num, line))]
    homes = {home_of(repo, p[2]) for p in fits} if all(p[2] for p in fits) else set()  # a dir Where can't tell picks no watcher
    if len(homes) == 1: pairs.append((repo, line, homes.pop()))
    else: lost.append(line)
for repo, line, home in pairs:
    if watched := next((dr for dr in live_dirs if line in lines(dr, 'threads.txt') and not steward.quiet(dr)), None):  # the steward's dirs wake no one on it
        home = watched
    elif home and os.path.realpath(home) in map(os.path.realpath, live_dirs):
        open(os.path.join(home, 'threads.txt'), 'a').write(line + '\n')
    elif home and watcher_on and home == plain_create(cmd, cwd):  # what pre-bash-guard let through without a running watcher
        start(home, line)
    elif home and watcher_on:
        told.append(f"the watcher of {home} isn't running, so {line} joined none: run `gh-watch-start {home} {line}`, arm the Monitor it prints if any")
    # the thread now covers its repo there: its bare repo line says nothing more
    if home and repo in lines(home, 'repos.txt'):
        p = os.path.join(home, 'repos.txt')
        keep = [l for l in open(p) if l.split('#', 1)[0].strip() != repo]
        with open(p + '.tmp', 'w') as f:
            f.writelines(keep)
        os.replace(p + '.tmp', p)
if told:
    print('post-bash-register: ' + '\n'.join(told), file=sys.stderr)
if lost:
    why = ("which dir a posting command ran in can't be told (shellcmd.Where: cd to an absolute path first)"
           if any(p[2] is None for p in posts) else "posting commands ran in folders with different watchers, so which one posted these can't be told")
    ran = ', '.join(dict.fromkeys(p[2] for p in posts if p[2]))
    print(f"post-bash-register: {why}, and they joined no watcher. Add each to the watcher of the work folder its command ran in{f' ({ran})' if ran else ''}: "
          + '; '.join(f"`gh-watch-start <work folder> {' '.join(shlex.quote(x) for x in line.split())}`" for line in lost), file=sys.stderr)
    sys.exit(2)
sys.exit(2 if told else 0)
