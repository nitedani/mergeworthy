#!/usr/bin/env python3
"""Claude Code PreToolUse hook (matcher: Bash). Exit 2 blocks the command; stderr goes to the agent.
Checks each simple command separately (shellcmd.parse: chains, substitutions, `bash -c`; heredoc bodies and quoted text are data).
It fails closed: a command it can't parse, a record it can't find or a state gh can't read blocks what it guards.
MERGEWORTHY_MERGE=reviewer blocks every `gh pr merge`."""
import glob, itertools, json, re, sys, os, hashlib, shlex, subprocess, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import failclosed
import shellcmd
from shellcmd import parse, segments, prog, script, opt, api_call, field_name, TEXT_FREE, discussion_post, discussion_thread_of, names_discussion_mutation, env_of, origin, plain_create, PLAIN, new_post_drafts, no_instructions_read, by_agent, written_files, git_argv, git_globals, operands, unquoted, GUARDED, _nested, Unseen, Where
from records import branch_record, commit_file, no_approach, no_preflight, STORE
import drift, own_actions, review_launch, steward, post_words, threads_file, work_folder
from t3_tasks import under_t3
def missing_steps(d, head=None):
    """(head, the converge steps it lacks): head is a push's pushed commit, else HEAD."""
    head = head or subprocess.run(['git', '-C', d, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
    rec = commit_file(head)
    # A maintainer's commits on top carry the last converged head's records, whatever their size: they get
    # reply §Maintainer commits' review, and the pipeline runs again only once the maintainer says they're done.
    # Only non-merge commits without the agent's Co-Authored-By: Claude trailer are skipped back over.
    for c in subprocess.run(['git', '-C', d, 'rev-list', '--first-parent', '--max-count=100', head or 'HEAD'], capture_output=True, text=True).stdout.split():
        if os.path.exists(commit_file(c)):
            rec = commit_file(c); break
        parents, _, body = subprocess.run(['git', '-C', d, 'log', '-1', '--format=%P%x00%B', c], capture_output=True, text=True).stdout.partition('\0')
        if len(parents.split()) != 1 or drift.AGENT_TRAILER.search(body): break
    kinds = {l.split()[0] for l in open(rec)} if head and os.path.exists(rec) else set()
    kinds |= {'fresh'} if 'review' in kinds else set()  # records made before the six steps
    kinds |= {'shape'} if {'loopb', 'refactor'} <= kinds else set()  # records made before the shape pass
    missing = [k for k in ('verify', 'shape', 'reverify', 'fresh', 'gates') if k not in kinds]
    # the approach is chosen once per PR: recorded per repo and branch
    if head and not os.path.exists(branch_record(d, 'approach')):
        missing.insert(0, 'approach')
    return head, missing

def check_union(d, repo, num, base=None, branch=None, head=None):
    """Two ready PRs (MRs) of ours that change one file can each pass alone and break their base merged (#188): each other open, non-draft
    one of the account on this one's base (PR num's, or the branch's) sharing a file needs a `pr-steps union`
    record on head (a push's pushed commit, else HEAD) naming its head. repo: owner/repo on GitHub, <host>/<path> on GitLab. A file list cut short
    shares every file; gh or glab not answering blocks."""
    lab = '.' in repo.split('/')[0]
    def ask(*args):
        try:
            r = subprocess.run(args, cwd=d, capture_output=True, text=True, timeout=30)
            return json.loads(r.stdout) if r.returncode == 0 else None
        except (OSError, subprocess.TimeoutExpired, ValueError): return None
    cli, kind = ('glab', 'MR') if lab else ('gh', 'PR')
    retry = lambda what: block(f"{cli} couldn't read {what} of {repo}, so whether one of your ready {kind}s changes this one's files can't be checked: retry once {cli} answers")
    if lab:
        import urllib.parse
        host, path = repo.split('/', 1)
        api = lambda ep: ask('glab', 'api', '--hostname', host, f"projects/{urllib.parse.quote(path, safe='')}{ep}")
        got = api('/merge_requests?state=opened&scope=created_by_me&per_page=100')
        prs = [{'number': m['iid'], 'isDraft': bool(m.get('draft') or m.get('work_in_progress')), 'baseRefName': m['target_branch'], 'headRefName': m['source_branch'],
                'headRefOid': m['sha']} for m in got] if isinstance(got, list) else None
    else:
        prs = ask('gh', 'pr', 'list', '-R', repo, '--author', '@me', '--state', 'open', '--limit', '100', '--json', 'number,isDraft,baseRefName,headRefName,headRefOid,files,changedFiles')
    if not isinstance(prs, list): retry(f'your open {kind}s')
    this = next((p for p in prs if str(p['number']) == str(num) or num is None and branch and p['headRefName'] == branch), None)
    if this is None: return  # not ours
    if not (others := [p for p in prs if p is not this and not p['isDraft']]): return
    base = base or this['baseRefName']
    head = head or git_head(d)
    done = {s for l in (open(RECORDS + head) if os.path.exists(RECORDS + head) else []) if l.split()[:1] == ['union'] for s in l.split()[3:]}  # pairs already checked
    if not (others := [p for p in others if p['baseRefName'] == base and p['headRefOid'] not in done]): return
    def paths(p):  # None: cut short
        if not lab: return {f['path'] for f in p['files']} if len(p['files']) >= p['changedFiles'] else None
        c = api(f"/merge_requests/{p['number']}/changes")
        if not isinstance(c, dict): retry(f"!{p['number']}'s changes")
        return None if c.get('overflow') else {f for x in c.get('changes') or [] for f in (x['old_path'], x['new_path'])}
    git = lambda *a: subprocess.run(['git', '-C', d, *a], capture_output=True, text=True).stdout.strip()
    ref = next(iter(git('for-each-ref', '--format=%(refname)', f'refs/remotes/*/{base}').split()), '')
    local = set(git('diff', '--name-only', f'{ref}...{head}').splitlines()) if ref else None  # with what this head adds to it
    listed = paths(this)
    mine = None if listed is None else listed | (local or set())
    for p in others:
        theirs = paths(p)
        shared = sorted(mine & theirs) if mine is not None and theirs is not None else None
        if shared == []: continue
        n, sha, mark = p['number'], p['headRefOid'], '!' if lab else '#'
        what = ', '.join(shared) if shared else 'files listed only in part'
        fetch = f"git fetch https://{repo} merge-requests/{n}/head" if lab else f"git fetch https://github.com/{repo} pull/{n}/head"
        block(f"{repo}{mark}{n}, also yours and ready, changes {what} too: merged together the two can break {base} without a conflict. Check them merged first: "
              f"`git worktree add --detach <work folder>/union origin/{base}`; there fetch and merge this head and {mark}{n}'s (`{fetch}`), run the quick gates (code §Gates) "
              f"into a log whose first line is `Union: {repo}#{num or '<N>'}@{head[:10]} + #{n}@{sha[:10]} on {base}@<its sha>`, then `pr-steps union <log>`; when they conflict, "
              f"`pr-steps union --conflict {sha}` here. A red union: change this one until it is green or conflicts, or stack it (mergeworthy:converge §Stacked PRs); "
              f"tell {mark}{n}'s session only if {mark}{n} must change")

def flag(a, *names):
    """A boolean flag's value in argv a, names its long and short spellings: the last occurrence wins, a bare `--x` or `-x` is true and
    `--x=<v>` false for v false, f or 0 (any case); False when absent. Bundled short flags (`-df`) aren't read."""
    on = False
    for n, eq, v in (x.partition('=') for x in a):
        if n in names: on = not eq or v.lower() not in ('false', 'f', '0')
    return on

def pr_ready(a):
    """Whether `gh <a>` is a `gh pr ready` taking the PR out of draft: --undo not in effect, no -h or --help."""
    return a[:2] == ['pr', 'ready'] and not flag(a, '--undo') and not {'-h', '--help'} & set(a)

DRAFT_TITLE = re.compile(r'\s*(\[draft\]|\(draft\)|draft:|draft\b|\[wip\]|wip:)', re.I)  # GitLab's draft prefixes
def goes_ready(p, a, env, run_dir):
    """(repo, number, base, branch) of the PR or MR this command takes out of draft, with the base it ends on (None: its own),
    for the records check and check_union alike; None for any other command. A push to a ready PR is gated where pushes are.
    A create opening its PR or MR ready blocks: which commit it publishes (a tracking ref, another repo's branch of that name, a source GitLab
    picks or makes) can't be told here."""
    if '--help' in a or '-h' in a: return None
    if (p, *a[:2]) in (('gh', 'pr', 'create'), ('glab', 'mr', 'create')) and not flag(a, '--draft', '-d' if p == 'gh' else '--wip'):
        block(f"`{p} {a[0]} create` opens it ready, and which commit it opens can't be told from this checkout: "
              f"open it with --draft, then `{'gh pr ready <N>' if p == 'gh' else 'glab mr update <N> --ready'}` from its checkout")
    if p == 'gh' and pr_ready(a):
        return (*post_target('pr', a[2:], env, run_dir), None, None)
    if p == 'gh' and a[:2] == ['pr', 'edit'] and (base := opt(a[2:], ['--base', '-B'])):  # a retarget of a ready PR
        repo, n = post_target('pr', a[2:], env, run_dir)
        if not isinstance(pr := gh_json(f'repos/{repo}/pulls/{n}'), dict):
            block(f"gh couldn't read {repo}#{n}, so whether this retarget puts a ready PR on {base[-1]} can't be checked: retry once gh answers")
        return None if pr.get('draft') else (repo, n, base[-1], None)
    if p == 'glab' and a[:2] == ['mr', 'update'] and not flag(a, '--draft', '--wip'):
        repo, iid, branch = mr_target(operands(a[2:]), run_dir)
        base, title = (opt(a[2:], ['--target-branch']) or [None])[-1], (opt(a[2:], ['--title', '-t']) or [None])[-1]
        if flag(a, '--ready', '-r') or repo and mr_ready_on(repo, iid, branch, base, title):
            return repo, iid, base, branch
        return None
    if p == 'glab' and a[:1] == ['api'] and (call := api_call(a[1:]))[0] == 'PUT' and \
            (m := re.fullmatch(r'(.*/merge_requests)/(\d+)(\?.*)?', call[1])) and (opens := api_opens(m[1], a[1:], env, run_dir)):
        if call[3] or any(x.partition('=')[2].startswith('@') for x in call[2]):
            block("this `glab api` PUT to an MR takes fields from a file or stdin (--input, a value starting with @), so whether it leaves the MR ready on a branch "
                  "can't be checked: pass them literally with -f <field>=<value>, or use `glab mr update`")
        f = dict(x.split('=', 1) for x in call[2] if '=' in x)
        if not {'title', 'draft', 'target_branch'} & set(f): return None
        if not opens[0]:
            block("can't tell which project this `glab api` call acts on (a numeric id), so whether it leaves an MR ready on a branch can't be checked: name the project by its path")
        return (opens[0], m[2], f.get('target_branch'), None) if mr_ready_on(opens[0], m[2], None, f.get('target_branch'), f.get('title'), f.get('draft')) else None
    return None

def mr_ready_on(repo, iid, branch, base, title=None, draft=None):
    """Whether an update setting these values (None: unchanged) leaves the MR ready where it was a draft, or moves a ready MR to base."""
    if title is None and draft is None and not base: return False
    now = mr_draft(repo, iid, branch)
    after = str(draft).lower() == 'false' if draft is not None else not DRAFT_TITLE.match(title) if isinstance(title, str) else not now
    return after and (now or bool(base))

def mr_draft(repo, iid, branch):
    """Whether the MR iid (else the open one from branch) of repo (<host>/<path>) is a draft now; one glab can't read blocks."""
    import urllib.parse
    host, path = repo.split('/', 1)
    ep = f"projects/{urllib.parse.quote(path, safe='')}/merge_requests" + (f'/{iid}' if iid else f"?state=opened&source_branch={urllib.parse.quote(branch or '')}")
    try: mr = json.loads(subprocess.run(['glab', 'api', '--hostname', host, ep], capture_output=True, text=True, timeout=30, check=True).stdout)
    except (OSError, subprocess.SubprocessError, ValueError): mr = None
    mr = mr[0] if isinstance(mr, list) and mr else mr
    if not isinstance(mr, dict):
        block(f"glab couldn't read the MR of {repo} this command changes, so whether it leaves draft can't be checked: retry once glab answers")
    return bool(mr.get('draft') or mr.get('work_in_progress'))

def push_before_gates(url):
    """The PR's project file has the `## Gates` line `Push: before gates`, bulleted or not: its maintainers take a ready PR's pushes before converge (merging step 1)."""
    m = re.match(r'https://(?:github\.com/(.+)/pull|gitlab\.com/(.+)/-/merge_requests)/\d+$', url or '')
    f = os.path.expanduser(f'~/.mergeworthy/projects/{m[1] or m[2]}.md') if m else ''
    sec = re.search(r'^## Gates\b[^\n]*\n(.*?)(?=^## |\Z)', open(f, errors='replace').read(), re.M | re.S) if os.path.isfile(f) else None
    return bool(sec and re.search(r'^(?:[-*] +)?Push: *before gates *$', sec[1], re.M))

def setting(name, default):
    """MERGEWORTHY_<name> from the environment, else from ~/.mergeworthy/settings.env (written at session start from the plugin's options)."""
    f = os.path.expanduser('~/.mergeworthy/settings.env')
    saved = dict(l.strip().split('=', 1) for l in open(f) if '=' in l) if os.path.exists(f) else {}
    return os.environ.get(f'MERGEWORTHY_{name}') or saved.get(f'MERGEWORTHY_{name}', default)
d = json.load(sys.stdin)
cmd = d.get('tool_input', {}).get('command', '')
cwd = d.get('cwd') or os.getcwd()
where = Where(cwd)  # where each of the command's simple commands runs (walk), with the variables it set

def block(msg):
    print(f"BLOCKED by pre-bash-guard: {msg}", file=sys.stderr); sys.exit(2)

def known(d, word=None):
    """d, what a check reads of where the command runs, or of where its written file word lands (from Where); one Where can't tell (None, or an Unknown saying why) blocks."""
    if d is None or isinstance(d, shellcmd.Unknown):
        if err:
            why, fix = err, '' if 'shell parser' in err else ": backticks or `$(` in an unquoted heredoc usually cause it, so quote its delimiter (`<<'EOF'`) or escape them"
        elif d in (None, ''):
            why, fix = "after a cd to an expansion it can't resolve, `cd -`, popd, a cd in a branch, loop or function, or a relative cd in a loop", \
                ": cd to an absolute path first (`cd /abs/dir && <command>`), or pass absolute paths"
        else:
            why, fix = d, ''
        block(f"can't tell which dir {'this command runs in' if word is None else f'`{word}` lands in'} ({why}), so its checks can't run{fix}")
    return d

def short_has(t, letter):  # -f, -9f, -fu ...
    return re.match(r'^-[A-Za-z0-9]*' + letter + r'[A-Za-z0-9]*$', t) is not None

def gated_file(p, has_cd, create=False):
    p = os.path.expanduser(where.expand(p))
    if not os.path.isabs(p):
        if has_cd:
            block(f"relative draft path {p} after a cd: use an absolute path")
        p = os.path.join(cwd, p)
    gate = p + '.gate'
    if not os.path.exists(p) or not os.path.exists(gate):
        block(f"no gate record for {p}: run post-lint + the review (mergeworthy:post steps 2-3), then `gate-pass {p} <review-output>`")
    sha = hashlib.sha256(open(p, 'rb').read()).hexdigest()
    if sha != open(gate).read().split('\n')[0].strip():
        block(f"{p} changed after its gate: review it again and re-run gate-pass")
    if create:  # a new comment/issue/PR from this exact draft: only once (edits may repeat); post-bash-register writes .posted once it succeeded
        posted = p + '.posted'
        if os.path.exists(posted) and open(posted).read().strip() == sha:
            block(f"{p} was already posted: edit that post instead (PATCH / gh … edit)")

def local_login():
    """The account gh is logged in as, from its own config (no network); '' when gh can't say."""
    try: return subprocess.run(['gh', 'config', 'get', '-h', 'github.com', 'user'], capture_output=True, text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.TimeoutExpired): return ''

def gh_login():
    """[login, id] of the account gh pushes as: the id is read from GitHub once per login and kept in ~/.claude/gh-user.txt;
    None when neither gh nor the cache can say."""
    cache, login = os.path.expanduser('~/.claude/gh-user.txt'), local_login()
    try: cached = open(cache).read().split()[:2]
    except OSError: cached = []
    if cached and cached[0] == (login or cached[0]):
        return cached
    try:
        r = subprocess.run(['gh', 'api', 'user', '--jq', '.login + " " + (.id|tostring)'], capture_output=True, text=True, timeout=20)
        if r.returncode == 0 and len(r.stdout.split()) == 2:
            open(cache, 'w').write(r.stdout)
            return r.stdout.split()
    except (OSError, subprocess.TimeoutExpired):
        pass
    return None

def check_commit_identity(overrides, git_dir):
    """Commits are authored as the GitHub account that pushes them, never the global git identity (a user checkout's worktrees share its config).
    While gh can't name the account (offline, never read), or the command computes the identity, a commit passes: it stays local, and can be amended."""
    if 'github.com' not in subprocess.run(['git', '-C', git_dir, 'remote', '-v'], capture_output=True, text=True).stdout:
        return  # a checkout of no GitHub repo is pushed with another account (GitLab's), which gh doesn't name
    name = overrides.get('user.name') or subprocess.run(['git', '-C', git_dir, 'config', 'user.name'], capture_output=True, text=True).stdout.strip()
    who = gh_login()
    if not who:
        return
    login, uid = who
    email = overrides.get('user.email') or subprocess.run(['git', '-C', git_dir, 'config', 'user.email'], capture_output=True, text=True).stdout.strip()
    if re.search(r'[$`]', name + email):  # set when the command runs (`user.email=${id}+...`): a local commit, amendable
        return
    if name != login or email != f'{uid}+{login}@users.noreply.github.com':
        block(f"commit author would be {name!r} <{email}>: commit as the pushing account, `git -c user.name={login} -c user.email={uid}+{login}@users.noreply.github.com commit ...`")


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

def need_watch(repo, path, why=''):
    """A push, or opening an issue or PR outside a task's work folder (need_home), needs the live loop (mergeworthy:task step 5): a running
    watcher of the task's work folder holding path, or of this session, must cover the repo. A comment on an existing thread isn't blocked
    here: post-bash-register adds that thread, and stop-lint requires a watcher's Monitor after any post."""
    if setting('WATCHER', 'on') != 'on': return
    repos = [repo] if isinstance(repo, str) else [r for r in repo if r]
    if not repos:
        block("can't tell which repo this acts on, so the watcher check can't run: pass -R <owner/repo>")
    path = known(path)
    def lines(d, f):
        return [l.strip() for l in open(os.path.join(d, f))] if os.path.exists(os.path.join(d, f)) else []
    sid = d.get('session_id')
    covering = [w for w in work_folder.watched_by(watch_dirs(), sid, path)
                if any(l.split()[:1] in ([r] for r in repos) for l in lines(w, 'repos.txt'))
                or any(r in repos for r, _ in threads_file.read(os.path.join(w, 'threads.txt'))[0])]
    if not covering:
        start = f"`gh-watch-start {steward.home(work_folder.task_of(path)) or '<your work folder>'} {repos[0]}`"
        block(f"no running watcher of this task or session covers {' or '.join(repos)} (another session's watcher wakes that session, not this one{'; ' + why if why else ''}): "
              + (f"a subagent starts none: end your turn asking the main session to run {start}" if by_agent(d)
                 else f"{start}, arm the Monitor it prints if any, then retry (mergeworthy:task step 5)"))

def need_home(repo, path):
    """Opening an issue or PR: a plain create (shellcmd.plain_create), whose thread post-bash-register adds to its work folder's
    watcher, starting or reviving it, passes; any other command needs need_watch's running watcher."""
    if not plain_create(cmd, cwd):
        need_watch(repo, path, PLAIN)

def check_turn(repo, num, args=()):
    """post §Thread rules: at most two comments in a row: while your last two comments on a thread have no reply after them and the last
    is under 3 hours old, a third stacks on them: edit the last one instead. After 3 hours, the third is the wait ping. The agent and the user may
    share one login, so a comment is the agent's only when its body was gated (gate-pass writes ~/.claude/gated-posts.txt).
    A discussion's comments and their replies count as one row, in time order."""
    if '--help' in args or '-h' in args:
        return
    def api(path, jq, issue_404=False):
        """gh's answer; an issue's 404 (on a pulls endpoint, or for a discussion's number) is None. Anything else gh can't read blocks: the rule can't be checked."""
        try: r = subprocess.run(['gh', 'api', path, '--jq', jq], capture_output=True, text=True, timeout=20)
        except (OSError, subprocess.TimeoutExpired) as e: r = subprocess.CompletedProcess([], 1, '', str(e))
        if r.returncode == 0: return r.stdout
        if issue_404 and 'HTTP 404' in r.stderr: return None
        block(f"gh couldn't read {repo}#{num} ({path}: {r.stderr.strip()[:160]}), so post §Thread rules (two comments in a row) can't be checked: retry once gh answers")
    n = api(f'repos/{repo}/issues/{num}', '.comments', issue_404=True)
    if n is None:  # a discussion: every comment and reply, as thread-context reads it, in time order
        try: r = subprocess.run([TC, '--items', f'{repo}#{num}'], capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as e: r = subprocess.CompletedProcess([], 1, '', str(e))
        if r.returncode: block(f"{r.stderr.strip()[:200]}, so post §Thread rules (two comments in a row) can't be checked: retry once gh answers")
        last = [{'body': x['body'], 'created': x['at'], 'url': x['url'], 'user': x['author']} for x in json.loads(r.stdout) if x['kind'] != 'body'][-2:]
        reviews = []
    elif int(n.strip() or 0) < 2: return
    else:
        page = lambda p: json.loads(api(f'repos/{repo}/issues/{num}/comments?per_page=100&page={p}', '[.[] | {body, created: .created_at, url: .html_url, user: .user.login}]') or '[]')
        p = (int(n.strip()) - 1) // 100 + 1
        last = page(p)
        if len(last) < 2 and p > 1: last = page(p - 1) + last
        last = last[-2:]
        reviews = (api(f'repos/{repo}/pulls/{num}/reviews?per_page=100', '.[].submitted_at', issue_404=True) or '').split()
    me = api('user', '.login').strip()
    # a maintainer's push after your comments answers them too (their commits deserve a review comment)
    reviews += [d for l in (api(f'repos/{repo}/pulls/{num}/commits?per_page=100', '.[] | "\\(.author.login) \\(.commit.committer.date)"', issue_404=True) or '').splitlines()
                for who, d in [l.split(' ', 1)] if who != me and who != 'null']
    f = os.path.expanduser(os.environ.get('GATED_POSTS', '~/.claude/gated-posts.txt'))
    gated = set(open(f).read().split()) if os.path.exists(f) else set()
    norm = lambda b: hashlib.sha256((b or '').replace('\r\n', '\n').strip().encode()).hexdigest()
    # someone else's comment is a reply, even when its text matches a gated draft (e.g. a quoted parent)
    if len(last) < 2 or not all(c.get('user') == me and norm(c['body']) in gated for c in last):
        return
    import datetime
    when = lambda t: datetime.datetime.fromisoformat(t.replace('Z', '+00:00'))
    if (datetime.datetime.now(datetime.timezone.utc) - when(last[-1]['created'])).total_seconds() >= 3 * 3600 or any(when(r) > when(last[-1]['created']) for r in reviews if r != 'null'):
        return
    block(f"your last two comments on {repo}#{num} have no reply yet ({last[-1]['url']}): edit the last one instead of posting a third; "
          "at most two comments in a row; after 3 hours without a reply, the wait ping may follow (mergeworthy:post §Thread rules)")


def check_finality(repo, num, files):
    """A design thread that has had two proposal rounds needs the finality pass's thread map before the third (mergeworthy:finality).
    post-bash-register counts posted `--kind proposal` drafts per thread in ~/.claude/proposal-rounds.txt; the map is
    <work folder>/maps/<owner>-<repo>-<number>.md (the root holds drafts/), and must be newer than the last proposal."""
    if not repo or not str(num).isdigit(): return
    log = os.path.expanduser('~/.claude/proposal-rounds.txt')
    rounds = [int(l.split()[1]) for l in open(log) if l.split()[:1] == [f'{repo}#{num}']] if os.path.exists(log) else []
    if len(rounds) < 2: return
    for f in files:
        f = os.path.expanduser(where.expand(f[5:] if f.startswith('body=') else f)).lstrip('@')
        f = f if os.path.isabs(f) else os.path.join(cwd, f)
        try: flags = open(f + '.lint').read().split()
        except OSError: continue
        if flags[flags.index('--kind') + 1:][:1] != ['proposal']: continue
        root = next((os.path.dirname(p) for p in work_folder.ancestors(f) if os.path.basename(p) == 'drafts'), os.path.dirname(os.path.dirname(f)))
        m = os.path.join(root, 'maps', f"{repo.replace('/', '-')}-{num}.md")
        if os.path.exists(m) and os.path.getmtime(m) > rounds[-1]: continue
        block(f"{repo}#{num} has had {len(rounds)} proposal rounds: run the finality pass (mergeworthy:finality step 1, a drifted design thread) before this reply, "
              f"write its thread map with the invariants list to {m} (newer than your last proposal), update the thread's WIP comment (Agreed with permalinks, Open; mergeworthy:design §WIP comment) from it, and let this reply say 'I updated the [WIP comment](link)' instead of restating the design")

def comment_discussion(node_id):
    """owner/repo#N of the GitHub Discussion holding the comment with that node id; None when gh can't name it."""
    q = 'query($id: ID!) { node(id: $id) { ... on DiscussionComment { discussion { number repository { nameWithOwner } } } } }'
    try: r = subprocess.run(['gh', 'api', 'graphql', '-f', f'query={q}', '-f', f'id={node_id}'], capture_output=True, text=True, timeout=20)
    except (OSError, subprocess.TimeoutExpired): return None
    try: d = json.loads(r.stdout)['data']['node']['discussion'] if r.returncode == 0 else None
    except (ValueError, KeyError, TypeError): d = None
    return f"{d['repository']['nameWithOwner']}#{d['number']}" if d and d.get('number') else None

def check_discussion_post(kind, ref, draft, has_cd):
    """discussion-post, checked as `gh issue comment --body-file` (a new comment) or a comment edit."""
    if not draft:
        block("discussion-post takes <discussion URL | owner/repo#N> <abs draft>, or --edit <comment node id> <abs draft>")
    thread = discussion_thread_of(ref) if kind == 'add' else comment_discussion(ref)
    if not thread:
        block(f"gh can't name the discussion {'at ' + ref if kind == 'add' else 'holding comment ' + ref}, so this post's checks can't run: retry once gh answers, "
              "or check the reference")
    repo, num = thread.split('#')
    if kind == 'add':
        check_turn(repo, num); check_finality(repo, num, [draft])
    check_context(thread, [draft])
    gated_file(draft, has_cd, create=kind == 'add')

def thread_of_ref(repo, ref):
    """owner/repo#N from a gh issue/pr argument (number or URL) or None."""
    m = re.search(r'github\.com/([\w.-]+/[\w.-]+)/(?:issues|pull)/(\d+)', ref or '')
    if m: return f'{m.group(1)}#{m.group(2)}'
    return f'{repo}#{ref}' if repo and str(ref).isdigit() else None

# gh issue/pr options that take a value: the word after one is not the command's target
VALUED = {'-R', '--repo', '-F', '--body-file', '-b', '--body', '-t', '--title', '-B', '--base', '-H', '--head', '-l', '--label', '-a', '--assignee',
          '-r', '--reviewer', '-p', '--project', '-m', '--milestone', '-c', '--comment', '-T', '--template', '-s', '--state', '-q', '--jq',
          '--add-label', '--remove-label', '--add-assignee', '--remove-assignee', '--add-reviewer', '--remove-reviewer', '--add-project', '--remove-project'}
def post_target(group, rest, env, run_dir):
    """(owner/repo, N) a `gh issue|pr <sub> <rest>` command acts on: its number or URL argument, or for gh pr its branch argument or the current
    branch's PR (`gh pr view`). Every check of a post on a thread reads its target here; one it can't tell blocks, as no check could run."""
    repo = gh_repo(rest, env, run_dir)
    ref = next((x for i, x in enumerate(rest) if not x.startswith('-') and (i == 0 or rest[i - 1] not in VALUED)), None)
    if t := thread_of_ref(repo, ref): return tuple(t.split('#'))
    n = ''
    if group == 'pr':
        try:
            r = subprocess.run(['gh', 'pr', 'view', *([ref] if ref else []), *(['-R', repo] if ref and repo else []), '--json', 'number', '--jq', '.number'],
                               cwd=run_dir if ref and repo else known(run_dir), env={**os.environ, **env}, capture_output=True, text=True, timeout=20)
            n = r.stdout.strip() if r.returncode == 0 else ''
        except (OSError, subprocess.TimeoutExpired): pass
    if not (repo and n.isdigit()):
        block(f"can't tell which thread this `gh {group}` command acts on, so its checks can't run: pass the number or URL, and -R <owner/repo>")
    return repo, n

TC = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'bin', 'thread-context')

def check_context(thread, files):
    """post step 1: a post on a thread is drafted from its whole record: <draft dir>/thread-context.md, made by `thread-context <repo#N> --out <dir>/thread-context.md`,
    for this thread and recording its latest human comment (the tool's --verify). Tracker drafts are exempt; a thread gh can't read blocks."""
    if not thread: return
    for f in files:
        f = os.path.expanduser(where.expand(f[5:] if f.startswith('body=') else f)).lstrip('@')
        f = f if os.path.isabs(f) else os.path.join(cwd, f)
        try: flags = open(f + '.lint').read().split()
        except OSError: flags = []
        if '--kind' in flags and flags[flags.index('--kind') + 1:][:1] == ['tracker']: continue
        parent = re.sub(r'\.md$', '', f) + '.parent.md'
        tcf = os.path.join(os.path.dirname(f), 'thread-context.md')
        # the gate record names the thread context the draft was written and reviewed from (gate-pass); one made later is not it
        recorded = [l[3:].strip() for l in (open(f + '.gate').read().splitlines() if os.path.exists(f + '.gate') else []) if l.startswith('tc ')]
        if os.path.exists(tcf) and recorded != [hashlib.sha256(open(tcf, 'rb').read()).hexdigest()]:
            block(f"{tcf} isn't the one {f} was gated with: draft from thread-context.md before the review, then gate-pass (mergeworthy:post step 1)")
        cmd = [TC, '--verify', tcf, '--target', thread] + (['--parent', parent] if os.path.exists(parent) else [])
        try: r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as e: r = subprocess.CompletedProcess(cmd, 1, '', f"thread-context --verify couldn't run: {e}")
        if r.returncode != 0:
            block(f"{r.stderr.strip() or f'thread-context --verify exited {r.returncode}'} (mergeworthy:post step 1: draft from thread-context.md, give the reviewer the same file)")

def gh_json(path):
    """`gh api <path>` parsed, or None when gh can't read it."""
    try:
        r = subprocess.run(['gh', 'api', path], capture_output=True, text=True, timeout=20)
        return json.loads(r.stdout) if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, ValueError): return None

def promised(repo, num, drafts):
    """An open `PROMISED <repo>#<num>: …refactor…` line in proposals-open.md of this session's watch dir (gh-watch-dirs.txt, its `session`
    file), or above a draft's folder, as gate-pass finds it. It proves only that the line exists: not that a holding reply was posted, nor
    its time; stop-lint holds the session to a time the line names."""
    sid = d.get('session_id') or os.environ.get('CLAUDE_CODE_SESSION_ID')
    reg = os.path.expanduser('~/.claude/gh-watch-dirs.txt')
    dirs = [w for w in (l.strip() for l in (open(reg) if os.path.exists(reg) else [])) if w and sid and (open(os.path.join(w, 'session')).read().strip()
            if os.path.isfile(os.path.join(w, 'session')) else '') == sid]
    dirs += [os.path.dirname(os.path.dirname(os.path.realpath(os.path.join(cwd, os.path.expanduser(f))))) for f in drafts]
    line = re.compile(rf'^PROMISED\s+(?:{re.escape(repo)})?#{num}\b.*\brefactor', re.I | re.M)
    return any(os.path.isfile(po := os.path.join(w, 'proposals-open.md')) and line.search(open(po).read()) for w in dirs)

ASKS = os.path.expanduser('~/.claude/refactor-asks.txt')  # the watcher's: <time> <PR head the scan saw> <owner/repo#N> <comment URL>
def check_refactor_ask(repo, num, comment, drafts=()):
    """A maintainer's refactor ask (the newest entry for this PR in refactor-asks.txt) is answered by a pass: a non-carry shape record with a
    later time, on the PR's head or a commit on the first page of its commits. Until one exists, a comment goes out only with the session's
    PROMISED line for the result (promised()); `gh pr ready` and a body edit wait for the pass. Only the record is checked: whether the post
    shows that pass's result is the post review's (delegate/post-review.md). A PR gh can't read blocks."""
    if not repo or not str(num).isdigit(): return
    asks = sorted(l.split() for l in (open(ASKS) if os.path.exists(ASKS) else []) if l.split()[2:3] == [f'{repo}#{num}'])
    if not asks: return
    pr = gh_json(f'repos/{repo}/pulls/{num}')
    if not isinstance(pr, dict):
        block(f"gh couldn't read {repo}#{num}, so whether its refactor ask ({asks[-1][3]}) was answered by a pass can't be checked: retry once gh answers")
    t, _, _, url = asks[-1][:4]
    commits = gh_json(f'repos/{repo}/pulls/{num}/commits?per_page=100')
    shas = {c.get('sha') for c in commits if isinstance(c, dict)} if isinstance(commits, list) else set()
    if any(at > t for sha in shas | {(pr.get('head') or {}).get('sha')} for _, _, at in real_passes(sha)): return
    if comment and promised(repo, num, drafts): return  # the post review checks the comment says the result is still to come
    block(f"{url} asks for a refactor pass ({t}) and no pass on this PR was recorded after it: fetch the PR's head, run the pass on it "
          "(converge step 2, delegate/shape.md), then record its report there with `pr-steps shape <report>`, on the unchanged head when the pass changes nothing. " +
          (f"To comment before it (a holding reply, a commit review), first add 'PROMISED {repo}#{num}: the refactor pass's result by <time> (<draft>)' "
           "to proposals-open.md in your watch dir" if comment else "`gh pr ready` and a body edit wait for the recorded pass"))

def real_passes(sha):
    """The (step, report, time) shape records of sha whose report is a pass, not a carry."""
    rec = commit_file(sha)
    rows = [l.split()[:3] for l in open(rec) if len(l.split()) >= 3] if sha and os.path.isfile(rec) else []
    return [r for r in rows if r[0] == 'shape' and os.path.isfile(r[1]) and 'carries the pass of' not in open(r[1], errors='replace').read()]

def gh_repo(args, env, run_dir):
    return shellcmd.gh_repo(args, env, lambda: origin(known(run_dir)))

def gitlab_repo(a, run_dir):
    return shellcmd.gitlab_repo(a, lambda: origin(known(run_dir)))

def api_opens(ep, rest, env, d):
    return shellcmd.api_opens(ep, rest, env, lambda: origin(known(d)))

def check_compose(env, t):
    """delegate/agent.md §Machine, own ports: a compose stack you start publishes no fixed host port and pins no container name;
    netns-run doesn't isolate what the Docker daemon publishes. A config that can't be read blocks (the stack wouldn't start either).
    Then an `up` starts only while the machine's memory holds it (check_stack_memory)."""
    n = 2 if os.path.basename(t[0]) == 'docker' else 1
    if t[1:n] not in ([], ['compose']) or env.get('MERGEWORTHY_HOST_PORTS') == 'user-asked': return
    keep, paths = ('-f', '--file', '-p', '--project-name', '--profile', '--project-directory', '--env-file'), ('-f', '--file', '--project-directory', '--env-file')
    a, glob, files = t[n:], [], []
    while a and a[0].startswith('-'):
        k = 2 if a[0] in keep + ('--ansi', '--parallel', '--progress') else 1
        if a[0].split('=')[0] in keep: glob += a[:k]
        a = a[k:]
    if not (a[:1] == ['up'] or a[:1] == ['run'] and '--service-ports' in a): return
    for i, x in enumerate(glob):  # compose gets the paths, not the words: ~ and the variables the line set put in
        o, eq, _ = x.partition('=') if x.startswith('--') else ('', '', x)
        v = x[len(o) + 1:] if eq else x
        if eq and o in paths or not o and i and glob[i - 1] in paths:
            if (f := where.path(v)) is None:
                block(f"can't tell the path `{v}` this compose command reads, so its ports can't be checked: write it out, or set its variable on this line")
            files += [f] if (o or glob[i - 1]) in ('-f', '--file') else []
            glob[i] = o + eq + f
    listed, sep = (env.get(k, os.environ.get(k, default)) for k, default in (('COMPOSE_FILE', ''), ('COMPOSE_PATH_SEPARATOR', ':')))
    files = {os.path.normpath(f) for f in files or map(where.path, listed.split(sep) if listed else []) if f}
    # without -f or COMPOSE_FILE, compose finds a default name in the project dir or a parent, wherever that is
    defaults = () if files or listed else {f'{b}{o}.{e}' for b in ('compose', 'docker-compose') for o in ('', '.override') for e in ('yaml', 'yml')}
    if f := next((f for f in sorted(where.wrote - {None}) if f in files or os.path.basename(f) in defaults), None):
        block(f"{f} is written by this same command, so its ports can't be checked yet: write it in one command, then start the stack in the next")
    try:
        r = subprocess.run(t[:n] + glob + ['config', '--format', 'json'], cwd=known(run_dir), env={**os.environ, **env}, capture_output=True, text=True, timeout=30)
        cfg = json.loads(r.stdout) if r.returncode == 0 else {'services': {}}
        svcs = cfg['services']
    except (OSError, ValueError, KeyError, subprocess.TimeoutExpired) as e:
        block(f"`{' '.join(t[:n] + glob)} config` couldn't be read ({e}), so its ports can't be checked: fix the config, then start it")
    if r.returncode != 0:
        block(f"`{' '.join(t[:n] + glob)} config` failed ({r.stderr.strip()[:200]}), so its ports can't be checked: fix the config, then start it")
    bad = [f"{s} container_name {c['container_name']}" for s, c in svcs.items() if c.get('container_name')] + \
          [f"{s} host port {p['published']}" for s, c in svcs.items() for p in c.get('ports') or [] if p.get('published')]
    if bad:
        block(f"this stack takes what another session's stack needs ({', '.join(bad)}), and netns-run doesn't isolate ports Docker publishes. "
              "Start it with a unique project name (-p or COMPOSE_PROJECT_NAME) and the override the project file's Running the app → Start names "
              "(`ports: !override [\"<container port>\"]` for Docker-assigned ports, found with `docker compose port <svc> <port>`; `ports: !reset []` where the host needs none; "
              "`container_name: !reset null`) (mergeworthy delegate/agent.md, Machine). Only when the user asked for the stack on its usual ports: prefix MERGEWORTHY_HOST_PORTS=user-asked")
    if a[:1] == ['up'] and env.get('MERGEWORTHY_STACK_MEMORY') != 'user-asked':
        pd = next((x.partition('=')[2] or glob[i + 1] for i, x in enumerate(glob) if x.split('=')[0] == '--project-directory'), None)
        check_stack_memory(env, files or compose_defaults(pd or known(run_dir)), cfg.get('name'))

def compose_defaults(d):
    """The files compose reads without -f or COMPOSE_FILE: the first default name in d or its nearest parent holding one, with that dir's override."""
    while True:
        found = [[f for f in (f'{b}{o}.{e}' for b in ('compose', 'docker-compose') for e in ('yaml', 'yml')) if os.path.isfile(os.path.join(d, f))][:1]
                 for o in ('', '.override')]
        if found[0]: return {os.path.join(d, f) for f in found[0] + found[1]}
        if d == (d := os.path.dirname(d)): return set()

def check_stack_memory(env, files, name):
    """delegate/agent.md §Machine, compute memory: MemAvailable less the stack's expected peak keeps 10% of MemTotal. The peak is the largest running
    compose project started from the same files, other than this one (`name`); swap is no condition, as it stays used after memory frees.
    A docker that fails or hangs counts no peak."""
    try: mem = {k: int(v.split()[0]) * 1024 for k, v in (l.split(':', 1) for l in open(os.environ.get('MERGEWORTHY_MEMINFO') or '/proc/meminfo'))}
    except (OSError, ValueError, IndexError): return
    def docker(*a):
        try: r = subprocess.run(['docker', *a], env={**os.environ, **env}, capture_output=True, text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired): return []
        return [l.split('\t') for l in r.stdout.splitlines()] if r.returncode == 0 else []
    ps = [c for c in docker('ps', '--filter', 'label=com.docker.compose.project', '--format',
                            '{{.Names}}\t{{.Label "com.docker.compose.project"}}\t{{.Label "com.docker.compose.project.config_files"}}') if len(c) == 3]
    used = {c[0]: c[1] for c in docker('stats', '--no-stream', '--format', '{{.Name}}\t{{.MemUsage}}') if len(c) == 2} if ps else {}
    size = lambda u: float(m[1]) * 1024 ** 'BKMGT'.index(m[2].upper() or 'B') if (m := re.match(r'([\d.]+)\s*([kKMGT]?)i?B', u)) else 0
    projects, same = {}, set()
    for c, p, cf in ps:
        projects[p] = projects.get(p, 0) + size(used.get(c, ''))
        if p != name and {os.path.normpath(f) for f in cf.split(',')} == files: same.add(p)
    src = max(same, key=projects.get, default=None)
    peak, room = projects.get(src, 0), mem['MemTotal'] / 10
    if mem['MemAvailable'] - peak >= room: return
    gb = lambda b: f'{b / 2 ** 30:.1f} GB'
    block(f"the machine can't hold this stack: MemAvailable {gb(mem['MemAvailable'])} less its expected peak {gb(peak)}{f' (running {src}, from the same files)' if src else ''} "
          f"leaves under the headroom {gb(room)} (10% of MemTotal). Running compose projects: {', '.join(f'{p} {gb(m)}' for p, m in sorted(projects.items(), key=lambda x: -x[1])) or 'none'}. "
          "Bring down a stack whose run ended (`docker compose -p <name> down`), yours first, or wait for one to end (mergeworthy delegate/agent.md, Machine). "
          "Only when the user asked for this stack anyway: prefix MERGEWORTHY_STACK_MEMORY=user-asked")

def check_steward(repo):
    """A declared steward owns the mergeworthy repo: other sessions report a problem to it instead of committing."""
    st = steward.read()
    if st and re.search(r'github\.com[:/]nitedani/mergeworthy(\.git)?$', subprocess.run(['git', '-C', repo, 'remote', 'get-url', 'origin'],
            capture_output=True, text=True).stdout.strip()) and not steward.is_steward(d.get('session_id'), d.get('cwd')):
        block(f"only the steward session (named in ~/.mergeworthy/steward; mergeworthy:rules step 2) commits to mergeworthy: open an issue on nitedani/mergeworthy with the fault and the fix you'd make: it wakes the steward")

def title_setter(repo, num):
    """(login, when) of whoever else retitled the PR last, from its timeline; None when it's ours or nobody's. A timeline or
    login gh can't read blocks: whose title it is can't be told."""
    def api(path):
        try:
            r = subprocess.run(['gh', 'api', path, '--paginate'], capture_output=True, text=True, timeout=20)
            return json.loads(r.stdout) if r.returncode == 0 else None
        except (subprocess.TimeoutExpired, ValueError, OSError): return None
    me = os.environ.get('GH_WATCH_ME') or (api('user') or {}).get('login')
    events = api(f'repos/{repo}/issues/{num}/timeline?per_page=100')
    if not me or not isinstance(events, list):
        block(f"gh couldn't read {repo}#{num}'s timeline or your login, so who set its title can't be told: retry once gh answers (mergeworthy:pull-request step 7)")
    renames = [e for e in events if e.get('event') == 'renamed']
    last = renames[-1] if renames else None
    login = ((last or {}).get('actor') or {}).get('login')
    return (login, last.get('created_at')) if login and login != me else None

RECORDS = os.path.realpath(STORE) + os.sep
push_urls = []  # where this command's pushes go (pushed()), for the watcher check
# what this command does on GitHub (own_actions), recorded once it passed every check: the watcher logs these changes without waking the session
own = {'PUSHED_HEADS': [], 'CLOSED_THREADS': []}  # the heads it pushes; `owner/repo#N merged|closed`

indexes = {}  # a checkout's index file: its copy for this command, removed when the hook ends
def index_copy(d):
    """The copy of checkout d's index that this command's `git add`s stage into and its commits' dry-runs read, so the real index stays as it is."""
    real = subprocess.run(['git', '-C', d, 'rev-parse', '--path-format=absolute', '--git-path', 'index'], capture_output=True, text=True).stdout.strip()
    if real not in indexes:
        import atexit, shutil, tempfile  # here, not at import: they cost every hook call ~2 ms
        indexes[real] = os.path.join(tempfile.mkdtemp(), 'index'); atexit.register(shutil.rmtree, os.path.dirname(indexes[real]), True)
        if os.path.exists(real): shutil.copy2(real, indexes[real])  # with its mtime, which git's check of a file changed in the same second reads
    return indexes[real]

def git_head(d):
    return subprocess.run(['git', '-C', d, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()

def block_drift(hot, pushed=None):
    """Blocks on the files drift.over found ({file: its count}); pushed: the branch or commit a push publishes, None for a commit."""
    if not hot: return
    (first, n), *rest = hot.items()
    block(f"{first} {'got' if pushed else 'would get'} a {n}th change{''.join(f', {f} a {c}th' for f, c in rest)} on {pushed or 'this branch'}: "
          "patch after patch in one place is drift. Run the finality pass (mergeworthy:finality steps 2-3) on it and record its plan with "
          f"`pr-steps finality <the plan>` {f'with {pushed} checked out' if pushed else 'on this head'} before Phase C's commits")

def repo_of(url):
    """(host, repo path) of a remote URL in each form git takes (scheme://[user@]host[:port]/path, [user@]host:path); an ssh host
    alias is resolved to its HostName. None for a local path."""
    m = re.match(r'[a-z][\w+.-]*://(?:[^@/]*@)?([^/:]+)(?::\d*)?/(.+?)(?:\.git)?/*$', url, re.I) or re.match(r'(?:[^@/:]+@)?([^/:]+):(.+?)(?:\.git)?/*$', url)
    if not m or url.startswith('file:'): return None
    host = m[1].lower()
    if not url.lower().startswith(('http://', 'https://')):
        try: host = re.search(r'^hostname (\S+)', subprocess.run(['ssh', '-G', host], capture_output=True, text=True, timeout=10).stdout, re.M)[1].lower()
        except (OSError, subprocess.TimeoutExpired, TypeError): pass
    return host, m[2]

def pushed(git_dir, opts, env, rest):
    """([remote URLs], [(commit, branch it updates, local branch it publishes)]) of a `git push <rest>` run in git_dir with the command's other global options
    (opts) and env: the remote's push URLs (pushurl, pushInsteadOf), or the URL given; no commits for a delete, tags only, or
    a local path."""
    if '--delete' in rest or '-d' in rest: return [], []
    if {'--all', '--branches', '--mirror'} & set(rest):
        block("push one branch, named (`git push <remote URL> <branch>`): each pushed head's records are checked (mergeworthy:merging step 1)")
    pos, skip = [], False
    for x in operands(rest):
        if skip: skip = False
        elif x in ('-o', '--push-option', '--repo', '--receive-pack', '--exec'): skip = True
        elif not x.startswith('-'): pos.append(x)
    run = lambda *a: subprocess.run(['git', '-C', git_dir, *opts, *a], env=env, capture_output=True, text=True)
    git = lambda *a: run(*a).stdout.strip()
    to = git('rev-parse', '--abbrev-ref', '@{push}').split('/', 1)  # where a bare `git push` goes: remote/branch
    head = git('symbolic-ref', '--short', '-q', 'HEAD')
    if len(to) < 2:  # a branch with no upstream yet: the remote git picks, the branch of the same name
        to = [next((r for r in (git('config', f'branch.{head}.pushRemote'), git('config', 'remote.pushDefault'), git('config', f'branch.{head}.remote')) if r), 'origin'), head]
    remote = pos[0] if pos else (opt(rest, ['--repo']) or [to[0]])[-1]
    vals = where.values(remote)
    if not vals or len(vals) > 1 or shellcmd.PIECE in vals[0]:
        block(f"where this push goes ({remote}) is computed when it runs, so it can't be checked: push to a remote name or URL written out, or one the line assigns")
    remote = vals[0]
    urls = git('remote', 'get-url', '--push', '--all', remote).split()
    if not urls:  # a URL, rewritten as git does: the longest url.<base>.pushInsteadOf, else insteadOf, prefix
        rules = [l.split(' ', 1) for l in git('config', '--get-regexp', r'^url\..*\.(push)?insteadof$').splitlines() if ' ' in l]
        best = max((r for r in rules if remote.startswith(r[1])), key=lambda r: (r[0].endswith('pushinsteadof'), len(r[1])), default=None)
        urls = [best[0][4:best[0].rindex('.')] + remote[len(best[1]):] if best else remote]
        if not best and not re.search(r'[/:]', remote) and not os.path.exists(os.path.join(git_dir, remote)):  # a bare name git can't resolve
            block(f"`{remote}` is neither a remote of this checkout nor a URL or path, so where this push goes can't be told")
    push_urls.extend(urls)
    if all(repo_of(u) is None for u in urls):
        return urls, []  # a local path publishes nothing a reviewer or CI sees
    out = []
    for spec in pos[1:] or ([] if '--tags' in rest else ['HEAD']):
        src, _, dst = spec.lstrip('+').partition(':')
        if not src or src.startswith('refs/tags/') or run('show-ref', '--verify', '-q', f'refs/tags/{src}').returncode == 0:
            continue  # a delete (:dst), or a tag
        sha = git('rev-parse', '--verify', '-q', f'{src}^{{commit}}')
        if not sha and not re.search(r'[$`]', src):  # a commit computed when it runs is checked only if the push is collaboration
            block(f"`{src}` in this push names no commit here, so what it publishes can't be checked: push a branch or commit of this checkout")
        branch = dst or (to[1] if not pos[1:] else head if src == 'HEAD' else src)
        if re.search(r'[$`]', branch):
            block(f"the branch this push updates ({branch}) is computed when it runs, so whether it is a PR's can't be told: write it out")
        local = re.sub(r'^refs/heads/', '', src)
        if src == 'HEAD': local = head or 'HEAD'
        elif run('show-ref', '--verify', '-q', f'refs/heads/{local}').returncode: local = branch  # a commit, not a branch: the one it updates
        out.append((sha, re.sub(r'^refs/heads/', '', branch), re.sub(r'^refs/heads/', '', local)))
    return urls, out

def collaboration(d, url, heads):
    """([why this push is collaboration work], [{url, isDraft, sha: the commit pushed to it} of each open PR or MR it updates]): it updates an open PR's (MR's)
    head, or goes to a repo the pushing account doesn't own, or to a host that is neither GitHub nor GitLab. A push of its own (no
    PR, its own repo) or to a gist has no why. When GitHub or GitLab can't answer, a push to the account's own repo from a checkout of no one
    else's repo is its own; anything else blocks."""
    if not heads or not (r := repo_of(url)): return [], []
    host, repo = r
    if host == 'gist.github.com': return [], []
    hub = host == 'github.com'
    if not hub and 'gitlab' not in host: return [f"{host} is neither GitHub nor GitLab, so whether it updates a PR can't be told"], []
    owner = repo.rsplit('/', 1)[0]
    cli = ['gh', 'config', 'get', '-h', host, 'user'] if hub else ['glab', 'config', 'get', 'user', '--host', host]
    try: login = subprocess.run(cli, capture_output=True, text=True, timeout=20).stdout.strip()
    except (OSError, subprocess.TimeoutExpired): login = ''
    def ask(args):
        try:
            r = subprocess.run(args, capture_output=True, text=True, timeout=30)
            return (json.loads(r.stdout) if r.returncode == 0 else None), r.stderr.strip()
        except (OSError, subprocess.TimeoutExpired, ValueError) as e: return None, str(e)
    if hub:
        q = 'query($o:String!,$n:String!' + ''.join(f',$b{i}:String!' for i in range(len(heads))) + '){viewer{login} repository(owner:$o,name:$n){owner{login} ' + \
            ' '.join(f'b{i}:ref(qualifiedName:$b{i}){{associatedPullRequests(states:OPEN,first:5){{nodes{{url isDraft}}}}}}' for i in range(len(heads))) + '}}'
        data, err = ask(['gh', 'api', 'graphql', '-f', f'query={q}', '-f', f'o={owner}', '-f', f'n={repo.split("/")[1]}',
                         *[x for i, (_, b) in enumerate(heads) for x in ('-f', f'b{i}=refs/heads/{b}')]])
        data = (data.get('data') or {}).get('repository') and data['data'] if isinstance(data, dict) else None
    else:  # a group's project too: whether the push updates an MR decides its approach check
        import urllib.parse
        answers = [ask(['glab', 'api', '--hostname', host, f"projects/{urllib.parse.quote(repo, safe='')}/merge_requests?state=opened&source_branch={urllib.parse.quote(b)}"]) for _, b in heads]
        data = [{**x, 'sha': sha} for (a, _), (sha, _) in zip(answers, heads) for x in a if isinstance(x, dict)] if all(isinstance(a, list) for a, _ in answers) else None
        err = next((e for a, e in answers if not isinstance(a, list)), '')
    if data is None:
        others = {o[1].split('/')[0] for u in set(subprocess.run(['git', '-C', d, 'remote', '-v'], capture_output=True, text=True).stdout.split()[1::3])
                  if (o := repo_of(u))} - {login}
        if login and login == owner and not others: return [], []
        block(f"{'gh' if hub else 'glab'} couldn't tell whether this push to {repo} updates a {'PR' if hub else 'MR'} ({err[:160]}), so its push gates can't be checked: retry once it answers")
    if not hub:
        mrs = [{'url': x.get('web_url'), 'isDraft': bool(x.get('draft')), 'sha': x['sha']} for x in data]
        return [f"it updates {', '.join(p['url'] for p in mrs)}"] * bool(mrs) + [f"{repo} isn't {login}'s"] * bool(login and owner != login), mrs
    prs = [{**p, 'sha': heads[i][0]} for i in range(len(heads)) for p in ((data['repository'].get(f'b{i}') or {}).get('associatedPullRequests') or {}).get('nodes') or []]
    why = [f"it updates {', '.join(p['url'] for p in prs)}"] * bool(prs) + \
          [f"{repo} isn't {data['viewer']['login']}'s"] * (data['repository']['owner']['login'] != data['viewer']['login'])
    return why, prs

def failing_jobs(urls):
    """{job name: PR URL} of every failing CI job on these PRs' (MRs') heads: gh reads a PR's checks, glab an MR's head pipeline
    on the MR's own host; a PR or MR whose CI can't be read blocks."""
    import urllib.parse
    def api(host, path, *flags):
        return subprocess.run(['glab', 'api', '--hostname', host, path, *flags], capture_output=True, text=True, timeout=30, check=True).stdout
    def pages(out):  # glab api --paginate prints each page's array as it came, back to back: [...][...]
        jobs, at = [], 0
        while not at or out[at:].strip():  # an empty answer is no page: it blocks like any unreadable one
            page, at = json.JSONDecoder().raw_decode(out, len(out) - len(out[at:].lstrip()))
            jobs += page
        return jobs
    out = {}
    for u in urls:
        mr = re.match(r'https?://([^/]+)/(.+?)/-/merge_requests/(\d+)', u)
        try:
            if mr:
                project = f"projects/{urllib.parse.quote(mr[2], safe='')}"
                pipeline = (json.loads(api(mr[1], f'{project}/merge_requests/{mr[3]}')).get('head_pipeline') or {}).get('id')
                failed = [x.get('name') for x in pages(api(mr[1], f'{project}/pipelines/{pipeline}/jobs?scope[]=failed&scope[]=canceled&per_page=100', '--paginate'))
                          if isinstance(x, dict) and not x.get('allow_failure')] if pipeline else []
            else:
                r = subprocess.run(['gh', 'pr', 'checks', u, '--json', 'name,bucket'], capture_output=True, text=True, timeout=30)
                failed = [x.get('name') for x in ([] if 'no checks reported' in r.stderr else json.loads(r.stdout)) if isinstance(x, dict) and x.get('bucket') in ('fail', 'cancel')]
        except (OSError, subprocess.SubprocessError, ValueError, AttributeError, TypeError):
            cli = 'glab' if mr else 'gh'
            block(f"{cli} couldn't read the CI of {u}, so whether this head reproduces its failing jobs can't be checked: retry once {cli} answers")
        out.update(dict.fromkeys(failed, u))
    return out

def check_workflow(what, d, commits, updates=()):
    """task steps 2-3 and pull-request steps 1 and 6 by their records, before a collaboration push (collaboration()) and every
    `gh pr create`, draft or not, whichever skills the session opened: the checkout is in the task's work folder, its scope.md
    opens with the Tier line and lists the asks as checkboxes, and each pushed head has a passing `pr-steps quick` (or `gates`)
    log whose lines name every failing CI job of the PRs it updates, so a CI fix is reproduced here first."""
    top = subprocess.run(['git', '-C', d, 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip()
    if not top:
        if what.startswith('this push'): return  # outside a work tree git itself refuses the push
        block(f"{what} runs from the PR branch's checkout (mergeworthy:pull-request step 7), so its records can be checked")
    wf = work_folder.task_of(top)
    if not wf:
        block(f"{top} isn't in a task's work folder: {what} runs from a worktree in ~/.mergeworthy/work/<task>/ (mergeworthy:task §Files, pull-request step 1)")
    scope = os.path.join(wf, 'scope.md')
    text = open(scope, errors='replace').read() if os.path.isfile(scope) else ''
    if not re.match(r'\s*Tier:\s*[0SML]\b', text) or not re.search(r'^\s*[-*] \[[ xX]\] ', text, re.M):
        block(f"{scope} needs line 1 `Tier: <0|S|M|L>, because <signals>` and a checkbox per ask, with its link (mergeworthy:task steps 2-3), before {what}")
    jobs = failing_jobs(dict.fromkeys(updates))
    if what.startswith('this push'):  # the PR this push updates is answered by a watcher on its repo (task step 5): upstream, origin or the fork pushed to
        urls = subprocess.run(['git', '-C', top, 'remote', '-v'], capture_output=True, text=True).stdout + ' ' + ' '.join(push_urls)
        repos = sorted({m[0] or 'gitlab.com/' + m[1] for m in re.findall(r'github\.com[:/]([\w.-]+/[\w.-]+?)(?:\.git)?(?:\s|$)|gitlab\.com[:/]([\w./-]+?)(?:\.git)?(?:\s|$)', urls)})
        if repos: need_watch(repos, top)  # a host no watcher reads (neither GitHub nor GitLab) has nothing to arm
    for sha in commits:
        rec = commit_file(sha)
        logs = [l.split()[1] for l in (open(rec) if os.path.isfile(rec) else []) if l.split()[:1] in (['quick'], ['gates']) and len(l.split()) > 1]
        if not logs:
            block(f"{sha[:10]} has no passing gate record: run the quick gates on it (format, type-check, units, and each failing CI job's command: "
                  f"code §Gates), installing whatever they need, then `pr-steps quick <log>`, before {what}. CI is not where a change is first checked")
        ran = '\n'.join(open(l, errors='replace').read() for l in logs if os.path.isfile(l)).lower()
        missed = [j for j in jobs if not re.search(re.escape(j.lower()) + r'.* -> exit 0\b', ran)]
        if missed:
            block(f"these CI jobs fail ({', '.join(sorted(set(jobs[j] for j in missed)))}) and {sha[:10]}'s gate log has no passing line naming them: "
                  + '; '.join(f'"{j}"' for j in missed) + ". Run each job's command here on this head (its workflow file names it; install what it needs), "
                  "add `<job name>: <command> -> exit 0` to the log, and `pr-steps quick <log>` again (code §Gates)")

def unproven_trailers(body, commits):
    """The squash body's lines that aren't a Co-authored-by trailer for a human author of the PR's commits (gh lists their co-authors as authors)."""
    authors = {f"{a['name']} <{a['email']}>".lower() for c in commits for a in c['authors']
               if a['email'] != 'noreply@anthropic.com' and not re.match(r'Claude\b', a['name'])}  # the agent's trailer is no contributor credit
    return [l for l in body.strip().split('\n') if not ((m := re.fullmatch(r'Co-authored-by: (.+ <[^<>]+>)', l.strip(), re.I)) and m[1].lower() in authors)]

def need_approach(d, what, branch=None):
    """pull-request step 5 comes before the build and the draft PR: the branch's approach record, before it opens a PR or MR (draft or not)
    or updates an open one; branch defaults to the checked-out one."""
    rec = branch_record(d, 'approach', branch)
    if not rec:
        block(f"{what} runs from the branch's checkout, so its approach record can be checked")
    if not os.path.exists(rec):
        block(f"{branch or 'this branch'} has no approach record: rate the approaches before building it and opening its PR or MR (mergeworthy:pull-request step 5), "
              f"then `pr-steps approach <work folder>/approach.md`, before {what}")

def opened_branch(a, options=(), fields=()):
    """The branch a PR or MR create with arguments a opens from, as it names it (the last of options, or a head= or source_branch= field
    among fields; owner:branch gives branch); None when it names none, for the checked-out one."""
    named = opt(a, list(options)) + [v[v.index('=') + 1:] for v in opt(a, list(fields)) if v.split('=', 1)[0] in ('head', 'source_branch')]
    return where.expand(named[-1]).split(':')[-1] if named else None

def thread_of_pr(url):
    """`owner/repo#N` of a GitHub PR's URL, `<host>/<path>!N` of a GitLab MR's (defects-open.md's form); None for any other."""
    if m := re.match(r'https://github\.com/([\w.-]+/[\w.-]+)/pull/(\d+)/?$', url or ''): return f'{m[1]}#{m[2]}'.lower()
    if m := re.match(r'https?://([^/]+)/(.+?)/-/merge_requests/(\d+)/?$', url or ''): return f'{m[1]}/{m[2]}!{m[3]}'.lower()

def all_defects():
    """Every work folder's open defects-open.md lines (work_folder.open_defects): a line names its PR, whichever session wrote it."""
    return work_folder.open_defects(glob.glob(os.path.join(work_folder.ROOT, '*')) + glob.glob(os.path.expanduser('~/*-work')))

def glab_get(repo, ep):
    """`glab api <ep>` on repo's (<host>/<path>) project, parsed; None when glab can't read it."""
    host, path = repo.split('/', 1)
    try:
        r = subprocess.run(['glab', 'api', '--hostname', host, f"projects/{urllib.parse.quote(path, safe='')}/{ep}"], capture_output=True, text=True, timeout=30)
        return json.loads(r.stdout) if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, ValueError): return None

def check_defects(thread, what):
    """A known defect in an open PR's own diff, not yet fixed, is in its body before the next push or ready (task §Dispositions): each open
    line of a work folder's defects-open.md naming thread (work_folder.open_defects) needs a row of the live body's notes table with Kind bug
    and Blocks merge yes, in the repo's language (post_words), whose Note holds the line's words, case and spacing aside (cells split on unescaped pipes). A body gh or glab can't read blocks."""
    lines = [x for x in all_defects() if x[1] == thread]
    if not lines: return
    repo, sep, num = re.match(r'(.+)([#!])(\d+)$', thread).groups()
    pr = gh_json(f'repos/{repo}/pulls/{num}') if sep == '#' else glab_get(repo, f'merge_requests/{num}')
    body = pr.get('body' if sep == '#' else 'description') if isinstance(pr, dict) else None
    if not isinstance(body, str):
        block(f"{'gh' if sep == '#' else 'glab'} couldn't read {thread}'s body, so whether it shows its open defects-open.md lines ({lines[0][3][:120]}) can't be checked: retry once it answers")
    norm = lambda x: ' '.join(x.lower().split())
    w = post_words.words(repo)  # the notes table in the repo's language (writing §Forms)
    bug, yes = w['kinds'][0], w['yes']
    rows = [[c.strip().replace('\\|', '|') for c in re.split(r'(?<!\\)\|', l.strip())[1:]] for l in body.splitlines() if l.strip().startswith('|')]
    notes = [norm(c[0]) for c in rows if len(c) >= 4 and c[1].lower() == bug and c[2].lower() == yes]
    unshown = [x for x in lines if not any(norm(x[2]) in n for n in notes)]
    if unshown:
        f, _, defect, line = unshown[0]
        block(f"{f} has the open line `{line[:160]}`, and {thread}'s body has no notes-table row for it: before {what}, fix it in its own commit and clear the line "
              f"as `fixed in <sha>: …`, or add the row `| {defect[:120].replace('|', chr(92) + '|')} | {bug} | {yes} | <Next> |` to the body (mergeworthy:task §Dispositions, writing §Forms)")

def ready_defects(p, repo, num, _base, branch, what):
    """check_defects for a PR or MR goes_ready finds this command taking out of draft (or retargeting while ready): its number, else the open
    MR of branch (a `glab mr update` naming none), read only when a line names an MR of its project, and one glab can't find blocks there."""
    if not repo: return
    if p == 'gh': return check_defects(f'{repo}#{num}'.lower(), what)
    if not num:
        if not any((t or '').startswith(f'{repo}!'.lower()) for _, t, _, _ in all_defects()): return
        mrs = glab_get(repo, f"merge_requests?state=opened&source_branch={urllib.parse.quote(branch or '')}")
        if not (isinstance(mrs, list) and mrs and isinstance(mrs[0], dict) and str(mrs[0].get('iid', '')).isdigit()):
            block(f"a defects-open.md line names an MR of {repo}, and glab finds no open MR from {branch or 'this checkout'}, so whether this is it can't be checked: pass the MR's number")
        num = str(mrs[0]['iid'])
    check_defects(f'{repo}!{num}'.lower(), what)

def ready_head(p, repo, num, run_dir, a, env):
    """The commit goes_ready's command makes ready, which its records are judged on: the head of the PR or MR it names, as `gh pr view` or
    `glab mr view` resolve it with the command's own target, env and dir (an API PUT: the project and MR its path names).
    A checkout whose HEAD is another commit blocks, naming both and the command aimed at the PR's URL; a head the CLI can't read blocks."""
    rest, keep = a[2:], None
    if a[0] == 'api':
        view = ['glab', 'mr', 'view', num, '-R', f'https://{repo}', '--output', 'json']
    else:
        at = next((i for i, x in enumerate(rest) if not x.startswith('-') and not (i and rest[i - 1] in (VALUED if p == 'gh' else GLAB_UPDATE_VALUED))), None)
        if p == 'glab' and at is not None and not re.fullmatch(r'\d+|https?://.+/-/merge_requests/\d+/?', rest[at]):
            block("`glab mr update <branch>` picks its MR by filters (state, owner) this check can't follow: pass the MR number (`glab mr update <N> --ready`)")
        view = [p, a[0], 'view', *rest[at:at + 1 if at is not None else 0], *(['-R', r[-1]] if (r := opt(rest, ['-R', '--repo'])) else []),
                *(['--json', 'headRefOid,url'] if p == 'gh' else ['--output', 'json'])]
        keep = [x for i, x in enumerate(rest) if i != at and not re.match(r'-R|--repo(=|$)', x) and not (i and rest[i - 1] in ('-R', '--repo'))]
    try:
        r = subprocess.run(view, cwd=known(run_dir), env={**os.environ, **env}, capture_output=True, text=True, timeout=30)
        pr = json.loads(r.stdout) if r.returncode == 0 else None
    except (OSError, subprocess.TimeoutExpired, ValueError): r, pr = None, None
    kind = 'PR' if p == 'gh' else 'MR'
    if r and r.returncode and re.search(r'Could not resolve to a (PullRequest|Repository)|no (pull|merge) requests? found|\b404\b', r.stderr, re.I):
        block(f"`{shlex.join(view)}` finds no {kind} ({r.stderr.strip().splitlines()[0][:200]}): the repository and the number or URL name no {kind} this account can see, so check them")
    sha, url = (pr.get(k) for k in (('headRefOid', 'url') if p == 'gh' else ('sha', 'web_url'))) if isinstance(pr, dict) else (None, None)
    if not (sha and url):
        block(f"`{shlex.join(view)}` couldn't read the head this command makes ready, so it can't be checked: retry once {p} answers")
    if sha != (here := git_head(known(run_dir))):
        retry = shlex.join([p, *a[:2], url, *keep] if keep is not None else [p, *a])
        block(f"`{shlex.join([p, *a])}` makes {url}'s head {sha[:10]} ready, and this checkout's HEAD is {here[:10] or '(no git repo in cwd)'}: "
              f"run it from that checkout with that head pushed (`cd <its checkout> && {retry}`)")
    return sha

GLAB_UPDATE_VALUED = {'-a', '--assignee', '--attach', '-d', '--description', '--description-file', '-l', '--label', '-m', '--milestone',
                      '--reviewer', '--state', '--target-branch', '-t', '--title', '-u', '--unlabel', '-R', '--repo'}  # docs.gitlab.com/cli/mr/update
def mr_target(a, run_dir):
    """(repo, iid, branch) of the MR `glab mr update <a>` acts on, for goes_ready: its positional iid, MR URL
    (whose project it is, whatever -R says) or branch, else the checked-out branch; never an option's value. repo is `<host>/<path>`, as
    gitlab_repo gives it; None when it can't be told."""
    ref = next((x for i, x in enumerate(a) if not x.startswith('-') and not (i and a[i - 1] in GLAB_UPDATE_VALUED)), '')
    if m := re.match(r'https?://([^/]+)/(.+?)/-/merge_requests/(\d+)', ref): return f'{m[1]}/{m[2]}', m[3], None  # gitlab_repo's form
    repo = gitlab_repo(a, run_dir)
    if ref.isdigit(): return repo, ref, None
    return repo, None, ref or subprocess.run(['git', '-C', known(run_dir), 'symbolic-ref', '--short', '-q', 'HEAD'], capture_output=True, text=True).stdout.strip()

NEED_DRAFT ="post from a draft file (--body-file /abs/drafts/<name>.md, -F body=@/abs/drafts/<name>.md or --input) that passed the gate"

def recorded(step, after, repo):
    """Whether a `pr-steps <step> ...` this command ran and && proved passed (Seg.after) wrote that record of repo's branch."""
    rec = branch_record(repo, step)
    return any(records.get(id(a)) == rec for a in after)

def ps_by_pid(a):
    """Whether ps arguments a select only by PID or parent PID (-p, -q, --pid, --ppid, --quick-pid, p, q, a bare PID list). ps(1) adds the processes of
    every other selector (-e, -A, a, x, -C, -u, -g, -t, ...) to theirs, and a number that is another selector's value is no PID."""
    pid = other = False
    a = list(a)
    while a:
        x = a.pop(0)
        if x.startswith('--'):
            name, eq, _ = x[2:].partition('=')
            pids, others = ('pid', 'ppid', 'quick-pid'), ('Group', 'group', 'sid', 'tty', 'user', 'User')
            pid, other = pid or name in pids, other or name in others or name == 'deselect'
            if not eq and name in pids + others + ('format', 'sort', 'cols', 'columns', 'width', 'rows', 'lines', 'date-format'):
                a = a[1:]
        elif re.fullmatch(r'[\d,]+', x):
            pid = True
        elif re.fullmatch(r'[-+]\d[\d,]*', x):  # a process group, a session
            other = True
        elif re.fullmatch(r'-?[A-Za-z].*', x):  # a cluster of options, standard (-ef, -p1) or BSD (aux, p 1); its value ends it
            dash = x.startswith('-')
            selects, takes = ('AaedNCGgstuU', 'CGgpqstuUoOD') if dash else ('agTrxtU', 'pqUoOk')
            for i, c in enumerate(x[dash:]):
                pid, other = pid or c in 'pq', other or c in selects
                if c in takes:
                    a = a if x[dash + i + 1:] else a[1:]
                    break
    return pid and not other

def picks(t):
    """Whether argv t picks processes by what they look like (a name, a text, all of them), not by a PID it names or that PID's children."""
    t = operands(prog(t))
    p, a = (os.path.basename(t[0]), t[1:]) if t else ('', [])
    if p in ('pgrep', 'pidof', 'pkill', 'killall'):
        return not any(x.startswith(('-P', '--parent')) for x in a) and not (p == 'killall' and a in (['-l'], ['--list']))  # killall -l lists signals
    if p == 'ps':
        return not ps_by_pid(a)
    return any(re.search(r'/proc/[*\[]', x) for x in a)

def kill_targets(a):
    """What the kill arguments a signal (PIDs, jobs, process groups): the words past its one signal (-9, -KILL, -s <sig>) and a --; none for signal 0 and -l/-L, which send nothing."""
    if a[:1] in (['-0'], ['-l'], ['-L']) or a[:2] in (['-s', '0'], ['-n', '0']): return []
    a = a[2:] if a[:1] in (['-s'], ['-n']) else a[1:] if a[:1] and a[0].startswith('-') and a[0] != '--' else a
    return a[1:] if a[:1] == ['--'] else a

def assignment_words(segs):
    """The `NAME=value` words of every command, after export, readonly, declare, typeset or local too."""
    return [x for s in segs for x in itertools.takewhile(lambda x: re.match(r'\w+=', x) and not x.quoted, s[1:] if s[:1] and s[0] in shellcmd.DECLARING else s)]

def started_pids(segs):
    """The variables holding a PID this command started: assigned `NAME=$!` by an assignment word, and NAME written nowhere else in it."""
    words = assignment_words(segs)
    names = [x.split('=', 1)[0] for x in words]
    others = {n for s in segs for n in s.sets} | {c[2] for s in segs for c in s.scopes}  # read, printf -v, a for loop's variable, ...
    return set() if any(s.sets_any for s in segs) else {n for x, n in zip(words, names) if x == n + '=$!' and names.count(n) == 1 and n not in others}

def search_writes(segs):
    """Whether a picking search writes its output to a file: by a redirect of its own or a later stage of its pipeline (`| tee f`)."""
    for i, s in enumerate(segs):
        for x in segs[i:] if picks(s) else ():
            if written_files(prog(x)): return True
            if not x.piped: break
    return False

def picked_vars(segs):
    """The variables that may hold PIDs a search picked: set by read, mapfile, printf -v, a for loop and the like, or assigned by an assignment
    word whose value runs a picking search or names a picked variable (`C=$B`); None when a command may set any or a search writes a file
    (a redirect, or a tee down its pipeline), which a later read brings back."""
    if any(s.sets_any for s in segs) or search_writes(segs): return None
    assigned = [(n, v, set(re.findall(r'\$\{?(\w+)', v))) for n, v in (x.split('=', 1) for x in assignment_words(segs))]
    picked = {n for s in segs for n in s.sets} | {c[2] for s in segs for c in s.scopes} | {n for n, v, _ in assigned if any(map(picks, segments(v)))}
    while grown := {n for n, _, refs in assigned if refs & picked} - picked:
        picked |= grown
    return picked

def check_processes(segs):
    """Refuses the two harms of a process search: a loop waiting on one, and a signal to processes one picked."""
    searched = any(map(picks, segs))
    if any(s.loop and picks(s) for s in segs) or err and searched and re.search(r'\b(while|until)\b', cmd):  # rough segments know no loop
        block("a loop on a process search (pgrep, pidof, ps, /proc/*) may never end: the search matches this command itself and other sessions' processes. "
              "Wait on the PID you started: `<cmd> & pid=$!; wait $pid`, or `while kill -0 $pid; do sleep 5; done` in the background, or its port. One search, to look, passes")
    picked, started = picked_vars(segs), started_pids(segs)
    for s in segs:
        t = prog(s)
        p = os.path.basename(t[0]) if t else ''
        targets = kill_targets(operands(t[1:])) if p == 'kill' else []
        if p in ('pkill', 'killall') and picks(t) or '-1' in targets or searched and (
                p == 'kill' and 'xargs' in map(os.path.basename, s[:len(s) - len(t)])
                or any(not re.fullmatch(r'-?(\d+|%.*|\$!)', x) and not ((m := re.fullmatch(r'-?\$\{?([A-Za-z_]\w*)\}?', x)) and (m[1] in started or picked is not None and m[1] not in picked)) for x in targets)
                or re.fullmatch(r'[gmn]?awk|perl|python[\d.]*|nodejs|node|ruby|lua|php|deno|bun', p) and any(re.search(r'\bkill\b', x) for x in t[1:])):  # a program text can signal; a word kill elsewhere only looks
            block("this signals processes a search picked (pkill, killall, or a kill of PIDs from pgrep, pidof, ps or /proc in this command, or -1, every process): they can be other sessions'. "
                  "Kill the PID you started (`<cmd> & pid=$!` … `kill $pid`), its children (`pkill -P $pid`), or a PID you looked up and checked in an earlier command (`kill 1234`)")

def check(t, has_cd):
    after = getattr(t, 'after', ())
    env = env_of(t)
    t = prog(t)
    if not t: return
    p, a = os.path.basename(t[0]), t[1:]
    if p == 'codex' and ('exec' in a or a[:1] == ['e']) and under_t3():
        block("under T3 Code, start Codex through T3, where the user sees it: delegate_task with target {providerInstanceId: codex, "
              "model: <the review model from orchestrator_capabilities>}, the prompt file's path in the task, a new delegate_task per review round (mergeworthy:delegate §Reviewers)")
    if p in ('docker', 'docker-compose'):
        check_compose(env, t)
    # a watcher wakes the session that started it, and a subagent's result is its last message: the main session owns the PR and its watcher
    if p == 'gh-watch-start' and '--round' not in a and by_agent(d):
        block("a subagent never starts a watcher: it would wake you, not the main session that owns the PR. End your turn with your result; "
              "the main session watches (mergeworthy:reply step 1)")
    # A credential file printed to the tool output lands in the transcript (an npm token, 2026-10-14)
    CRED = r'(?:^|/)(?:\.npmrc|\.netrc|\.pypirc|\.git-credentials|hosts\.yml|credentials(?:\.json)?|id_(?:rsa|ed25519|ecdsa)|\.config/pnpm/(?:config\.yaml|rc))$'
    if p in ('cat', 'head', 'tail', 'less', 'more', 'bat', 'sed', 'awk', 'grep', 'rg', 'cut', 'strings', 'xxd', 'od', 'base64', 'jq', 'yq', 'python3', 'node') and any(
            re.search(CRED, os.path.expanduser(x)) and os.path.isfile(os.path.expanduser(x)) for x in a if not x.startswith('-')) and not (
            p in ('grep', 'rg') and any(re.fullmatch(r'-\w*[clqL]\w*|--count|--quiet|--files-with-matches', x) for x in a)):
        block("that file holds credentials, and printing it puts them in the transcript. Check a setting without its value "
              "(`grep -c '^//registry' <file>`, `npm config get registry`), or ask the user")
    # thread-context --verify compares the thread record's time with the parent's: setting a time makes a stale record pass
    if p == 'touch' and any(x in ('-d', '-t', '-r') or x.startswith(('--date', '--reference')) or (re.fullmatch(r'-[a-z]+', x) and set(x[1:]) & set('dtr')) for x in a) \
            and ('drafts/' in cmd or any('drafts/' in os.path.abspath(os.path.expanduser(x)) for x in a if not x.startswith('-'))):
        block("never set a draft's file times: the posting gate reads them. Rebuild the record instead (`thread-context <owner/repo#N> --out <its folder>/thread-context.md`), "
              "re-save the draft, and run its review again (mergeworthy:post steps 1-4)")
    if p == 'kill':
        for x in a:
            if x.isdigit():
                try: argv = open(f'/proc/{x}/cmdline', 'rb').read().split(b'\0')
                except OSError: continue
                if any(os.path.basename(v.decode(errors='replace')) == 'claude' for v in argv[:2]) and b'stream-json' in b' '.join(argv):
                    block(f"PID {x} is a running agent (a claude session), not a command: never kill it. Read its task status and latest runs; "
                          "a turn that ended or 'waiting_for_children' is alive. Stop it through its task (interrupt) only after that, "
                          "and when two run the same job keep the one with the most progress")
    if p == 'git':
        repo, overrides, sub, rest = git_argv(t, where)
        if sub in ('commit', 'push') and repo is not None:
            check_steward(repo)
        if sub == 'commit' and repo is not None and os.path.isdir(repo):  # in a folder this hook can't resolve (`cd "$(mktemp -d)"`), a commit stays local
            for step, missing in (('preflight', no_preflight), ('approach', no_approach)):
                if not recorded(step, after, repo) and (why := missing(repo)):
                    block(why + (f" This check runs before the line does, so the line's own `pr-steps {step}` counts only when the commit needs it to pass: "
                                 "join them with `&&`, with no `;`, `||` or pipe on the record" if branch_record(repo, step) in records.values() else ''))
            check_commit_identity(overrides, repo)
            out = iter(subprocess.run(['git', '-C', repo, 'commit', '--dry-run', '--porcelain', '-z', '--untracked-files=no', *operands(rest)], capture_output=True,
                                      text=True, stdin=subprocess.DEVNULL, env={**os.environ, 'GIT_INDEX_FILE': index_copy(repo)}).stdout.split('\0'))
            taken = set()
            for x in out:  # `XY path`, X the index side the commit takes; a rename's next entry is its old path
                if x[:1] not in ('', ' ', '?'): taken |= {x[3:], *([next(out, '')] if x[0] == 'R' else [])}
            block_drift(drift.over(repo, pending=sorted(taken), amend='--amend' in rest))
        if sub == 'add' and repo is not None and os.path.isdir(repo):  # what a `git commit` later in this command reads
            subprocess.run(['git', '-C', repo, 'add', *operands(rest)], capture_output=True, stdin=subprocess.DEVNULL, env={**os.environ, 'GIT_INDEX_FILE': index_copy(repo)})
        if sub == 'push' and {'--dry-run', '-n'} & set(rest):
            sub = 'push --dry-run'  # publishes nothing
        if sub == 'push' and (repo is None or not os.path.isdir(repo)) and '--help' not in rest:
            # a checkout the command makes first (`git clone ../o.git d && cd d`): a push to a local path, or to the local repo it was cloned from, publishes nothing
            to, made = next((x for x in operands(rest) if not x.startswith('-')), 'origin'), repo and os.path.normpath(repo)
            if repo_of(to if to != 'origin' else clones.get(made, to)) is None and (to != 'origin' or made in clones):
                return
            block(f"can't tell which checkout this push runs in ({'a cd to ' + repo if repo else 'a dir change it can' + chr(39) + 't follow'}), so what it publishes can't be checked: cd to an absolute path first")
        if sub == 'stash':
            first = rest[0] if rest else ''
            ok = first in ('list', 'show', 'apply', 'branch', 'create', 'store') or \
                 (first == 'drop' and len(rest) > 1) or \
                 (first in ('push', 'save', '') or first.startswith('-')) and bool(opt(rest, ['-m', '--message']) or (first == 'save' and len(rest) > 1))
            if not ok:
                block("never bare git stash / pop / drop / clear: use a WIP commit, or `git stash push -u -m <tag>` + apply <sha>, then drop that entry by its ref")
        if sub == 'push' and '--help' not in rest and '-h' not in rest:
            leases = [x for x in rest if x.startswith('--force-with-lease')]
            force = any(x in ('--force', '--mirror') or (not x.startswith('--') and x.startswith('-') and short_has(x, 'f'))
                        or (x.startswith('+') and len(x) > 1) for x in rest)
            if force or any(not re.match(r'^--force-with-lease=[^:\s]+:.+$', x, re.S) for x in leases):  # the sha may be computed
                block("force-push only with --force-with-lease=<branch>:<sha you last pushed>, after checking others' commits")
            if {'--git-dir', '--work-tree'} & {x.split('=')[0] for x in git_globals(t)} or {'GIT_DIR', 'GIT_WORK_TREE'} & set(env):
                block("push from the checkout itself (cd or -C, without --git-dir, --work-tree, GIT_DIR or GIT_WORK_TREE), so what it publishes can be checked")
            g = git_globals(t)
            urls, heads = pushed(repo, [x for i, x in enumerate(g) if x != '-C' and g[i - 1:i] != ['-C']], {**os.environ, **env}, rest)
            why, prs = [sum(x, []) for x in zip(*[collaboration(repo, u, [h[:2] for h in heads]) for u in urls])] or ([], [])
            if why and not all(sha for sha, _, _ in heads):
                block(f"this push ({'; '.join(why)}) publishes a commit computed when it runs, so its records can't be checked: push a branch or a sha written out")
            if why:  # a push of its own (no PR, its own repo) is free; collaboration runs the task's records first
                check_workflow(f"this push ({'; '.join(why)})", repo, [sha for sha, _, _ in heads], [p['url'] for p in prs])
                for sha, branch, local in heads:  # named by what it publishes: its branch when that branch is the commit pushed, else the commit
                    if branch.startswith('refs/tags/'): continue  # a tag it makes is no branch's drift
                    tip = subprocess.run(['git', '-C', repo, 'rev-parse', '-q', '--verify', f'refs/heads/{local}'], capture_output=True, text=True).stdout.strip()
                    block_drift(drift.over(repo, sha), local if tip == sha else sha)
                if prs:  # each branch it publishes, whichever is checked out
                    for _, _, local in heads: need_approach(repo, f"this push ({'; '.join(why)})", local)
                for pr in prs: check_defects(thread_of_pr(pr['url']), 'this push')
                for pr in prs:
                    if pr['isDraft'] or push_before_gates(pr['url']): continue
                    sha = pr['sha'] or block(f"this push's commit for {pr['url']} can't be told, so its records can't be checked: push a branch or a sha written out")
                    if (missing := missing_steps(repo, sha)[1]):
                        block(f"{pr['url']} is out of draft and its pushed commit {sha[:10]} has no pr-steps {', '.join(missing)} record (approach: pull-request step 5, once per branch): run converge's pipeline on it first (each step ends with its `pr-steps <step> <output>`), or `gh pr ready --undo` while it converges")
                    if m := re.match(r'https://(?:github\.com/(.+)/pull|([^/]+/.+?)/-/merge_requests)/(\d+)$', pr['url'] or ''):
                        check_union(repo, m[1] or m[2], m[3], head=sha)
            own['PUSHED_HEADS'] += [sha for sha, _, _ in heads if sha]
    if p in ('curl', 'wget', 'http', 'https', 'xh') and any(re.search(r'\bapi\.github\.com\b|github\.com/api/', x) for x in a) and \
            any(re.fullmatch(r'-X|--request|-d|--data[\w-]*|-F|--form|--json|-T|--upload-file|--method|POST|PATCH|PUT|DELETE|-\w*[dXFT]', x) or re.match(r'--(?:request|method)=', x) for x in a):
        block("a GitHub write goes through gh, where the posting gate checks it (mergeworthy:post): use `gh api` with the draft file")
    if p == 'gh' and a[:1] == ['pr'] and a[1:2] in (['create'], ['edit']) and '--help' not in a and '-h' not in a:
        # a title typed inline skips every reviewed file: it is drafted in a file, like the body
        if any(not re.fullmatch(r'\$\(cat \S+\)', v) for v in opt(a[2:], ['--title', '-t'])):
            block('the PR title is typed inline: write it to <work folder>/drafts/title.md in the repo\'s form (its last 10 merged titles) '
                  'and pass --title "$(cat <that file>)" (mergeworthy:pull-request step 7)')
        if a[1] == 'edit' and opt(a[2:], ['--title', '-t']) and (who := title_setter(*post_target('pr', a[2:], env, run_dir))):
            block(f"{who[0]} set this PR's title ({who[1]}): it is their decision. Keep it, or ask them on the PR first (mergeworthy:pull-request step 7)")
    # A review's verdict is the reviewer's final message, which it writes itself (`codex exec -o`, an agent's output file); an agent's stdout is it too.
    # The launch records the text the reviewer is handed (review_launch); a Bash write of that record or the verdict it set aside is refused,
    # a workflow check of the writes this hook sees, not proof of who wrote them
    targets = written_files(t)
    files = [where.files(x) for x in targets]
    names = [*map(where.expand, targets), *(f for c in files for f in c or [])]
    if p not in ('claude', 'codex') and any(review_launch.REVIEW_OUT.fullmatch(f) for f in names) and not by_agent(d):
        block("a review's output is the reviewer's final message, written by the reviewer: `codex exec -o <out>`, or the agent writes <out> itself. "
              "Never write a verdict yourself (mergeworthy:delegate §Reviewers, post step 3)")
    if any(review_launch.REVIEW_OUT.fullmatch(re.sub(r'\.(launch|prev)$', '', f)) and f.endswith(('.launch', '.prev')) for f in names):
        block("a review output's .launch and .prev are written by the hook that starts its reviewer, which records the text the reviewer is handed: "
              "launch the review again (mergeworthy:post step 3)")
    if p in ('claude', 'codex'):
        # the verdict is codex's -o file, or claude's stdout: another descriptor's file is a plain write
        stdout = [t[i + 1] for i, x in enumerate(t[:-1]) if re.fullmatch(r'1?>>?|1?>\||&>>?', x) and not t[i + 1].startswith('/dev/')]
        for w in (opt(a, ['-o', '--output-last-message']) if p == 'codex' else []) + (stdout if p == 'claude' and ('-p' in a or '--print' in a) else []):
            # only an output that is one fully known path is recorded or name-checked; any other that may land in drafts/ is refused
            vals, paths = where.values(w), where.files(w)
            if isinstance(vals, shellcmd.Unknown) or isinstance(paths, shellcmd.Unknown) or len(vals) != 1 or len(paths) != 1 or shellcmd.PIECE in vals[0]:
                seen = [where.expand(w), *([] if isinstance(vals, shellcmd.Unknown) else vals), *([] if isinstance(paths, shellcmd.Unknown) else paths)]
                if any(re.search(r'(^|/)drafts/', x) for x in seen):
                    block(f"the review output {w} can't be placed: pass its absolute path, written out or assigned once")
                continue
            out = paths[0]
            if why := review_launch.misnamed(out):
                block(why)
            if review_launch.draft_of(out):
                if why := review_launch.unlinted(out): block(why)
                launches.append(out)  # recorded once every segment of the command passed
    written = [f for x, c in zip(targets, files) for f in known(c, x)]
    for x in dict.fromkeys(map(shellcmd.folder, written)):  # the instructions check runs git, once per folder
        if why := no_instructions_read(x, d):
            block(why)
    if any(os.path.realpath(x).startswith(RECORDS) for x in written):
        block("the step records in ~/.claude/pr-steps are written by `pr-steps <step> <its output>` alone, which checks the output first")
    if p == 'gh' and pr_ready(a):
        check_refactor_ask(*post_target('pr', a[2:], env, run_dir), comment=False)
    if p == 'gh' and a[:2] == ['pr', 'create'] and '--help' not in a and '-h' not in a:
        check_workflow('`gh pr create`', known(run_dir), [git_head(run_dir)])
        need_approach(run_dir, '`gh pr create`', opened_branch(a[2:], ['--head', '-H']))
    if ready := goes_ready(p, a, env, run_dir):
        ready_defects(p, *ready, f"`{p} {'api' if a[:1] == ['api'] else ' '.join(a[:2])}`")
        head, missing = missing_steps(known(run_dir), ready_head(p, ready[0], ready[1], run_dir, a, env))
        if missing:
            block(f"HEAD {head[:10]} has no pr-steps {', '.join(missing)} record: run those steps of mergeworthy:converge's pipeline on the final HEAD, each ending with `pr-steps <step> <its output>` (again after a base merge)")
        if ready[0]:  # no GitLab project: nothing to list
            check_union(run_dir, *ready, head=head)
    if p == 'glab' and len(a) >= 2 and a[0] in ('issue', 'mr') and a[1] == 'create' and '--help' not in a and '-h' not in a:
        need_home(gitlab_repo(a[2:], run_dir), run_dir)
        if a[0] == 'mr': need_approach(run_dir, '`glab mr create`', opened_branch(a[2:], ['--source-branch', '-s']))
    if p == 'glab' and a[:1] == ['api'] and (call := api_call(a[1:]))[0] == 'POST' and (opens := api_opens(call[1], a[1:], env, run_dir)):
        need_home([opens[0]], run_dir)
        if opens[1] == 'pr': need_approach(run_dir, '`glab api` creating an MR', opened_branch(a[1:], fields=['-f', '--raw-field', '-F', '--field']))
    if p == 'gh' and len(a) >= 2 and a[0] == 'pr' and a[1] == 'merge':
        if setting('MERGE', 'on-request-squash') == 'reviewer':
            block('never merge: the reviewer merges this repo\'s PRs (MERGEWORTHY_MERGE=reviewer)')
        rest = a[2:]
        subj, body = opt(rest, ['--subject', '-t']), opt(rest, ['--body', '-b'])
        # the PR the merge names (a number, a URL or a branch), else the current branch's
        sel = next((x for i, x in enumerate(rest) if not x.startswith('-') and (i == 0 or rest[i - 1] not in ('-t', '--subject', '-b', '--body', '-F', '--body-file', '-A', '--author-email', '--match-head-commit', '-R', '--repo'))), '')
        num = m.group(1) if (m := re.fullmatch(r'(?:\S*/pull/)?(\d+)(?:/\S*)?', sel)) else ''
        if not ('--squash' in rest or '-s' in rest) or not subj or not re.search(r' \(#' + (num or r'\d+') + r'\)$', subj[-1]) or len(body) != 1:
            block('squash-merge as the repo asks, by default `gh pr merge <N> --squash --delete-branch --subject "<exact PR title> (#<N>)" --body ""`; re-read the repo\'s AGENTS.md first')
        if '--admin' in rest:
            block("never `gh pr merge --admin`: it bypasses the base's branch protection. Merge once the PR meets it")
        repo = opt(rest, ['-R', '--repo'])
        def gh(*args):  # in the dir and with the env the merge runs in
            r = subprocess.run(['gh', *args], cwd=known(run_dir), env={**os.environ, **env}, capture_output=True, text=True, timeout=20)
            return json.loads(r.stdout) if r.returncode == 0 else None
        try:
            pr = gh('pr', 'view', *([sel] if sel else []), *(['-R', repo[-1]] if repo else []), '--json', 'url,headRefName,headRefOid,baseRefName,mergeStateStatus,changedFiles,files,statusCheckRollup,commits')
            slug, commits = '/'.join(pr['url'].split('/')[3:5]), pr['commits']
            # the head's last check run tested the base as it was then: later base commits touching the PR's files are untested with it
            green = max((c.get('completedAt') or c.get('createdAt') or '' for c in pr['statusCheckRollup']), default='')
            moved = gh('api', f"repos/{slug}/compare/{pr['headRefOid']}...{pr['baseRefName']}")
            newer = [gh('api', f"repos/{slug}/commits/{c['sha']}")['files'] for c in moved['commits'] if c['commit']['committer']['date'] > green]
        except (OSError, subprocess.TimeoutExpired, ValueError, KeyError, TypeError) as e:
            block(f"gh couldn't read this PR's merge state ({type(e).__name__}: {e}), so whether its base moved can't be checked: retry once gh answers")
        if body[0].strip() and (bad := unproven_trailers(body[0], commits)):
            block(f"the squash body holds only `Co-authored-by: <name> <email>` lines naming human authors of the PR's commits, copied from `gh pr view <N> --json commits` "
                  f"(mergeworthy:merging step 4); not one: {bad[0]!r}")
        if len(moved['commits']) < moved['total_commits'] or any(len(f) >= 300 for f in newer) or newer and len(pr['files']) < pr['changedFiles']:
            block(f"{pr['baseRefName']} moved past one page of GitHub's lists (100 files a PR, 250 commits a compare, 300 files a commit), so which of this PR's files it touched can't be checked: merge or rebase {pr['baseRefName']} into it, push, and merge once CI is green on that head")
        touched = sorted({f['path'] for f in pr['files']} & {f['filename'] for files in newer for f in files})
        if pr['mergeStateStatus'] in ('BEHIND', 'DIRTY') or touched:
            why = f"its base {pr['baseRefName']} got commits touching {', '.join(touched)} after its last CI run" if touched else f"GitHub reports it {pr['mergeStateStatus']} against {pr['baseRefName']}"
            block(f"{why}: merge or rebase {pr['baseRefName']} into it (after a rebase, `git range-diff` shows nothing changed beyond the conflict resolution), push, and merge once CI is green on that head (mergeworthy:merging step 4)")
        # Deleting a branch other open PRs are based on closes them (GitHub doesn't retarget them)
        if '--delete-branch' in rest or '-d' in rest:
            head = pr['headRefName']
            try:
                deps = subprocess.run(['gh', 'pr', 'list', '-R', slug, '--base', head, '--json', 'number', '-q', '[.[].number] | join(",")'],
                                      cwd=known(run_dir), env={**os.environ, **env}, capture_output=True, text=True, timeout=20).stdout.strip() if head else ''
            except Exception:
                deps = ''
            if deps:
                block(f"open PRs #{deps} are based on {head}: retarget them first (`gh pr edit <N> --base <new base>`), or merge without --delete-branch; deleting it closes them")
        own['CLOSED_THREADS'].append(f"{slug}#{pr['url'].rstrip('/').rsplit('/', 1)[1]} merged")
    if dp := discussion_post(t):
        check_discussion_post(*dp, has_cd)
    if p == 'gh' and len(a) >= 2 and a[0] in ('issue', 'pr'):
        sub, rest = a[1], a[2:]
        if '--help' in rest or '-h' in rest:
            return  # reading gh's help posts nothing
        files = opt(rest, ['--body-file', '-F'])
        texts = [] if sub == 'merge' else [v for v in opt(rest, ['--body', '-b']) + (opt(rest, ['--comment', '-c']) if sub == 'close' else []) if v.strip()]
        if sub in ('comment', 'create', 'review') or (sub in ('edit', 'close', 'merge') and (files or texts)):
            if texts or not files:
                if sub == 'review' and not texts and not files and '--approve' in rest:
                    return  # an approval without a body posts no text
                block(NEED_DRAFT)
            if sub == 'create':
                need_home(gh_repo(rest, env, run_dir), run_dir)
            if a[0] == 'pr' and sub == 'create':  # a draft's body says why on its State line (pull-request step 7); goes_ready refused a ready create
                w = post_words.words(gh_repo(rest, env, run_dir))
                for f in files:
                    f = os.path.join(cwd, os.path.expanduser(where.expand(f)))
                    lines = [l.strip() for l in open(f).read().split('\n') if l.strip()] if os.path.exists(f) else []
                    lead = lines[1:2] if lines[:1] and lines[0].startswith('<img') else lines[:1]  # under the badge
                    if lines and not post_words.state_line(w).match((lead or [''])[0]):
                        block(f"{f}: a draft PR's body starts, right under the badge, with '**{w['state'][0]}: {w['state'][1]}** (<why it's a draft, in plain words>)' (post-lint --kind pr --draft)")
            # a comment or body edit on a PR with a refactor ask: the target post_target resolves (gh issue too: an issue number that is a PR)
            target = post_target(a[0], rest, env, run_dir) if sub != 'create' else (None, None)
            if sub in ('comment', 'edit') and files:
                check_refactor_ask(*target, comment=sub == 'comment', drafts=files)
            if sub == 'comment' and '--edit-last' not in rest:
                check_turn(*target, rest)
            if sub in ('comment', 'review'):
                check_finality(*target, files)
            if sub != 'create':
                check_context(f'{target[0]}#{target[1]}' if all(target) else None, files)
            for f in files: gated_file(f, has_cd, create=f in new_post_drafts(t))
    if p == 'gh' and a[:2] in (['pr', 'close'], ['issue', 'close']) and '--help' not in a and '-h' not in a:  # one it can't tell wakes as before
        ref = next((x for i, x in enumerate(a[2:]) if not x.startswith('-') and (i == 0 or a[1 + i] not in VALUED)), None)
        if t_ := thread_of_ref(gh_repo(a[2:], env, run_dir) if run_dir is not None or opt(a[2:], ['--repo', '-R']) else None, ref):
            own['CLOSED_THREADS'].append(f"{t_} closed")
    if p == 'gh' and a and a[0] == 'api':
        rest = a[1:]
        method, ep, fields, inputs, posts = api_call(rest, run_dir)
        if shellcmd.graphql_endpoint(ep) and (named := names_discussion_mutation(rest, run_dir)) is not False:
            block("post to a GitHub Discussion, or edit a comment there, with `discussion-post <discussion URL | owner/repo#N> <abs draft>` or "
                  "`discussion-post --edit <comment node id> <abs draft>`: it posts the gated draft as the comment's text, which a GraphQL call can't be checked for"
                  if named else "can't read a file this GraphQL call reads, so whether it posts to a GitHub Discussion can't be told: pass the query inline")
        if not posts:
            return
        if re.search(r'\{(owner|repo)\}', ep) and (here := gh_repo(rest, env, run_dir)):  # what gh fills them from
            ep = ep.replace('{owner}', here.split('/')[0]).replace('{repo}', here.split('/')[1])
        bodies = [v[len('body=@'):] for v in opt(rest, ['-F', '--field']) if v.startswith('body=@')]
        literal = [v for v in fields if re.match(r'^(body|query)=', v) and not v.startswith('body=@') and not (ep == 'graphql' and v.startswith('query='))]
        if literal or not (bodies or inputs):
            unknown = sorted({field_name(v) for v in fields} - TEXT_FREE) if not shellcmd.graphql_endpoint(ep) else []
            block(NEED_DRAFT + (f"; fields not known to post no text (shellcmd.TEXT_FREE): {', '.join(unknown)}" if unknown else ''))
        if method == 'POST' and (opens := api_opens(ep, rest, env, run_dir)):
            need_home([opens[0]], run_dir)
            if opens[1] == 'pr': need_approach(run_dir, '`gh api` creating a PR', opened_branch(rest, fields=['-f', '--raw-field', '-F', '--field']))
        c = re.fullmatch(r'/?repos/([\w.-]+/[\w.-]+)/issues/(\d+)/comments', ep)
        if c and method == 'POST': check_turn(c.group(1), c.group(2), rest); check_finality(c.group(1), c.group(2), bodies + inputs)
        thread = None
        t_ = re.fullmatch(r'/?repos/([\w.-]+/[\w.-]+)/(?:issues|pulls)/(\d+)(?:/.*)?', ep)
        if t_: thread = f'{t_.group(1)}#{t_.group(2)}'
        else:  # an edit of a comment by id: ask which thread it is on
            c_ = re.fullmatch(r'/?repos/([\w.-]+/[\w.-]+)/(?:issues|pulls)/comments/\d+', ep)
            if c_:
                r_ = subprocess.run(['gh', 'api', ep.lstrip('/'), '--jq', '.issue_url // .pull_request_url'], capture_output=True, text=True, timeout=20)
                n_ = re.search(r'/(\d+)\s*$', r_.stdout) if r_.returncode == 0 else None
                thread = f'{c_.group(1)}#{n_.group(1)}' if n_ else None
        # a comment on a PR, or an edit of its body, as `gh pr comment` and `gh pr edit` are checked
        if thread and method in ('POST', 'PATCH') and re.search(r'/issues/(?:\d+/comments|comments/\d+)$|/(?:issues|pulls)/\d+$', ep):
            check_refactor_ask(*thread.split('#'), comment=not re.search(r'/(?:issues|pulls)/\d+$', ep), drafts=bodies + inputs)
        check_context(thread, bodies + inputs)
        for f in bodies + inputs: gated_file(f, has_cd, create=f in new_post_drafts(t))

segs, err = parse(cmd)
if err and (m := GUARDED.search(unquoted(cmd))):  # its words are still checked below, but what they don't show can't be
    verb = ' '.join(m.group(0).split()[:2])
    block(f"{err}, so this command's `{verb}` can't be checked" if 'shell parser' in err else f"this command doesn't parse ({err}), so its `{verb}` "
          "can't be checked: split it into simple commands, a message or body in a file (`git commit -F <file>`, `--body-file`)")
check_processes(segs)
waits = re.search(r'\b(until|while)\b[^\n]*\bsleep\b', cmd) if err else any(s.loop and prog(s)[:1] and os.path.basename(prog(s)[0]) == 'sleep' for s in segs)
# a subagent's result is its last message, so waiting for its own run is its job
if waits and not d.get('tool_input', {}).get('run_in_background') and not by_agent(d):
    block('never wait in the foreground: the main session keeps working while agents and builds run. Rely on the task-completion notification, '
          'or run the wait with run_in_background (one notification when it ends)')
# a Playwright install prunes the browser builds other sessions use from the shared ~/.cache/ms-playwright (agent.md §Machine),
# and a browser the machine already has needs none
if any(re.fullmatch(r'(?:.*/)?playwright(?:-core)?(?:@[^/]*)?(?:/cli\.js)?', w) and prog(x)[i + 1:i + 2] == ['install'] for x in segs for i, w in enumerate(prog(x))) and 'PLAYWRIGHT_BROWSERS_PATH=' not in cmd:
    block("a Playwright install deletes the browser builds other sessions use from the shared ~/.cache/ms-playwright: "
          "Run on a browser the machine already has first: an installed Google Chrome or Edge through Playwright's `channel: 'chrome'` (or `'msedge'`), "
          "set in a config of your own in the work folder that extends the repo's. Only when the tests need a build no installed browser gives "
          "(Firefox, WebKit, a pinned Chromium): install into a folder of your own, `PLAYWRIGHT_BROWSERS_PATH=<work folder>/.pw <the same command>`, "
          "and run the tests with the same variable")
# gate-pass is read on its own: this hook checks the gate record before the command runs, so a post in the same command
# goes out on the old record even when gate-pass then refuses the draft (and a pipe hides that refusal)
if any(prog(x)[:1] and os.path.basename(prog(x)[0]) == 'gate-pass' for x in segs) and \
        any(prog(x)[:1] == ['gh'] and (prog(x)[1:3] and prog(x)[1] in ('issue', 'pr') and prog(x)[2:3] and prog(x)[2] in ('comment', 'create', 'edit', 'review', 'close', 'merge')
                                        or prog(x)[1:2] == ['api'] and any(w.startswith('body=') or w in ('--input',) for w in prog(x))) or discussion_post(x) for x in segs):
    block("run gate-pass as its own command and read its exit code, then post in the next command: this check reads the gate record before the command runs (mergeworthy:post step 4)")
clones = {}  # folder: the repo it was cloned from, for a `git clone` in this command
launches = []  # the review outputs of the reviewers this command starts (check)
records = {}  # each `pr-steps approach|preflight ...` walked so far, by its statement (Seg.stmt): the record it writes
for s in where.walk(segs):
    run_dir, has_cd = where.dir, where.moved
    if run_dir is not None and (a := script(prog(s)))[:1] and os.path.basename(a[0]) == 'pr-steps' and a[1:2] in (['approach'], ['preflight']) and a[2:]:
        records[id(s.stmt)] = branch_record(run_dir, a[1])
    if run_dir is not None and prog(s)[:2] == ['git', 'clone'] and (ops := [where.expand(x) for x in operands(prog(s)[2:]) if not x.startswith('-')]):
        src = ops[0] if repo_of(ops[0]) else os.path.join(run_dir, os.path.expanduser(ops[0]))
        clones[os.path.normpath(os.path.join(run_dir, ops[1] if ops[1:] else re.sub(r'(\.git)?/*$', '', ops[0]).rsplit('/', 1)[-1]))] = src
    # a command named by a variable this command set (`G="git -C x"; $G commit`) is checked as what it runs
    if prog(s)[:1] and (v := re.fullmatch(r'\$\{?(\w+)\}?', prog(s)[0])) and (x := where.vars.get(v[1])) is not None and not isinstance(x, Unseen):
        s = ((segments(where.vars[v[1]]) or [[]])[0]) + prog(s)[1:]
    # a command named by an expansion (`"${a[@]}"`, `$GIT push`), or a shell running a computed script (`sh -c "$(...)"`), runs what this
    # hook can't see: it blocks when its arguments, or the variables it names, hold a guarded verb
    named = prog(s)[0] if prog(s)[:1] and prog(s)[0][:1] in '$`' else (_nested(s) or '') if (_nested(s) or '')[:1] in '$`' else ''
    if named:
        words = [x for x in prog(s)[1:] if ' ' not in x] + re.findall(r'[\w-]+', named) + [w for v in re.findall(r'\w+', named) for w in re.split(r'[\s()]+', where.vars.get(v, ''))]
        w = {x.lower() for x in words}
        if w & {'git', 'gh', 'glab'} and w & {'push', 'commit', 'pr', 'issue', 'api', 'release', 'mr'} or 'git' not in w and w & {'push', 'commit'}:
            block(f"`{named}` runs a command named only when it runs, with `{' '.join(words)[:80]}`: write the command out, so it can be checked")
    check(s, has_cd)
for out in launches:
    review_launch.launch(out)
try:  # pending until post-bash-register sees how the command ended
    own_actions.intend(own_actions.key(d), own)
except OSError:
    pass
sys.exit(0)
