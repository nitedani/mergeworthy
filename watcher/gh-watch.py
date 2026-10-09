#!/usr/bin/env python3
"""Robust GitHub watch for the tracked threads. One line on stdout per event.

- The comments the agent answers (mergeworthy:github-threads), new or edited, each with an :eyes: reaction: a maintainer's
  (write access) on a thread in threads.txt, the threads the agent opened or posted in; and yours with /ai or /agent, on any thread
  (your events feed; one watch dir gets each, see main_dir). Nothing else.
- Your "/agent ..." comments on threads no watch dir lists, found in the watched repos' recent comments (search as a backup) and sent to one dir (see agent_command): `### AGENT COMMAND`.
- FOLLOW-UP: later commits by others to the lines of your merged PRs, and PRs that reference them (see follow_ups), for 60 days after the merge.
- Maintainers' commits pushed to a tracked PR, and 👍/👎 from GH_WATCH_EYES on the agent's comments.
- WAIT PING DUE: your account's comment is the last on an open thread and has had no reply for WAIT_PING_HOURS (3).
- PR head/state changes (pushes, merges, closes), CI turning red or green on open PRs, and your PR's code (tests excluded) changing by more than ~80 lines since its last refactor pass (REFACTOR STALE).
State lives in gh-watch-state.json: every seen (id, updated_at) pair, so nothing is skipped or repeated,
and scans overlap by 10 minutes. A failed API call prints WATCH ERROR and that thread's scan position isn't advanced.
"""
import json, os, re, subprocess, sys, time, datetime, fcntl, http.client, threading
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, 'gh-watch-state.json')
THREADS = os.path.join(HERE, 'threads.txt')  # one "owner/repo number" per line
ME = os.environ.get('GH_WATCH_ME') or subprocess.run(['gh', 'api', 'user', '--jq', '.login'], capture_output=True, text=True).stdout.strip()
if not ME:
    sys.exit("WATCH ERROR could not read your login (gh api user); set GH_WATCH_ME")  # else your own comments become events
ONCE = '--once' in sys.argv  # a manual check: prints events but doesn't consume them or react, so the daemon still logs them
WAIT_PING_HOURS = float(os.environ.get('WAIT_PING_HOURS') or 3)  # mergeworthy:github-threads: a wait ping may follow after this long
EYES_FOR = set(filter(None, os.environ.get('GH_WATCH_EYES', '').split(',')))  # maintainers: their commits on your PRs and 👍/👎 are reported


def gh(args):
    r = subprocess.run(['gh'] + args, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"gh {' '.join(args)}: {r.stderr.strip()[:200]}")
    return r.stdout


def gh_json(path):
    out = gh(['api', '--paginate', '--slurp', path])
    pages = json.loads(out)
    items = []
    for p in pages:
        items.extend(p if isinstance(p, list) else [p])
    return items


def load_state():
    try:
        s = json.load(open(STATE))
        s.setdefault('since_by', {})
        return s
    except Exception:
        now = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        return {'since': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'seen': {}, 'prs': {}, 'ci': {}, 'is_pr': {}, 'since_by': {}}


def save_state(s):
    if ONCE:
        return
    tmp = STATE + '.tmp'
    json.dump(s, open(tmp, 'w'))
    os.replace(tmp, STATE)


# The agent and the user may post as the same account (ME). The agent posts only gated drafts
# (gate-pass registers each one's hash), so a comment by ME whose text matches no gated post is the user's.
GATED_POSTS = os.path.expanduser(os.environ.get('GATED_POSTS', '~/.claude/gated-posts.txt'))  # written by gate-pass


def _norm(text):
    import hashlib
    return hashlib.sha256((text or '').replace('\r\n', '\n').strip().encode()).hexdigest()


def agent_post_hashes():
    try:
        return set(open(GATED_POSTS).read().split())
    except OSError:
        return set()


MAINTAINER = ('OWNER', 'MEMBER', 'COLLABORATOR')
AI_CALL = re.compile(r'(^|\s)/(ai|agent)\b', re.I)


def answerable(u, body, agent_hashes, kind='comment', own=False):
    """mergeworthy:github-threads. On a thread the agent opened (own), what a person would answer on their own PR:
    every human's comment, and a review bot's inline finding (its summaries ask nothing). On a thread it only posted
    in: a maintainer's comment or the user's. The user's /ai calls elsewhere go through ai_call_elsewhere."""
    if own and kind == 'review-comment' and is_bot(u):
        return True
    if not is_human(u, body, agent_hashes):
        return False
    return own or u.get('login') == ME or u.get('assoc') in MAINTAINER


def is_bot(u):
    return bool(u) and (u.get('type') == 'Bot' or u.get('login', '').endswith('[bot]'))


def is_human(u, body=None, agent_hashes=frozenset()):
    if not u or is_bot(u):
        return False
    if u.get('login') != ME:
        return True
    return _norm(body) not in agent_hashes  # ME: the user's own comment unless it's an agent post


def append_owed(entry, d=None):
    """replies-owed.md (mergeworthy:github-threads): the daemon records each human comment as an owed reply; the session
    clears the line with "done: <reply url> <what changed>" when it is answered. The Stop hook
    blocks a turn while a line is still owed, so an unposted reply cannot end the session unseen."""
    path = os.path.join(d or HERE, 'replies-owed.md')
    owed = open(path).read().splitlines() if os.path.exists(path) else []
    if any(f' {entry.split()[2]} ' in l for l in owed):
        return  # already recorded
    with open(path, 'a') as f:
        if not owed:
            f.write('# replies owed (mergeworthy:github-threads): clear each line with "done: <reply url> <what changed>"\n')
        f.write(entry + '\n')


def handle_comment(state, repo, key, kind, cid, upd, login, url, body, extra=''):
    """An answerable comment (mergeworthy:github-threads): an event, an owed reply and an :eyes: reaction, each once."""
    sk = f"{kind}:{cid}"
    if state['seen'].get(sk) == upd:
        return
    edited = sk in state['seen']
    state['seen'][sk] = upd
    indented = '\n'.join('    ' + l for l in body.splitlines())  # no body line can start with ### and pass as an event
    emit(f"### {key} {kind}{' (edited)' if edited else ''} {cid} by {login} {upd} {extra} {url}\n{indented}\n")
    if edited:
        return
    append_owed(f"{key} {kind} {cid} by {login} {url} — {body.strip().splitlines()[0][:80]}" if body.strip() else f"{key} {kind} {cid} by {login} {url}")
    if re.fullmatch(r"\W*(ok(ay)?|good|great|lgtm|yes|sure|agreed|sounds good|👍|nice)\W*", body.strip().lower()):
        emit(f"### ACK {key} {cid}: an acknowledgement answers your last open proposal in that thread or PR; apply it now (mergeworthy:github-threads)")
    if not ONCE and kind != 'review':  # GitHub has no reactions on a review
        react_eyes(repo, kind, cid)


def watch_dirs():
    reg = os.path.expanduser('~/.claude/gh-watch-dirs.txt')
    return [l.strip() for l in open(reg)] if os.path.exists(reg) else []


def live(d):
    try:
        os.kill(int(open(os.path.join(d, 'gh-watch.pid')).read().strip()), 0)
        return True
    except (OSError, ValueError):
        return False


def main_dir():
    """The watch dir that gets /ai calls on threads no live watcher watches: ~/.mergeworthy/main-watch
    (gh-watch-start --main) while its watcher runs, else the first live dir in gh-watch-dirs.txt."""
    try:
        m = open(os.path.expanduser('~/.mergeworthy/main-watch')).read().strip()
    except OSError:
        m = ''
    if m and live(m):
        return m
    return next((d for d in watch_dirs() if live(d)), None)


def emit(line):
    print(line, flush=True)  # into events.log, where the session's Monitor delivers it (mergeworthy:github-threads)


def waiting_keys():
    """waiting-on.txt: "<owner/repo#N> -> <dependent thread>: <what to do>", one per line. Yields (line, "owner/repo#N"):
    the key is the left side's start, so a trailing note such as "(Version Packages, releases #390)" doesn't hide it."""
    path = os.path.join(HERE, 'waiting-on.txt')
    if not os.path.exists(path):
        return
    for l in (l.strip() for l in open(path)):
        if not l or l.startswith('#') or l.lower().startswith('done:') or ' -> ' not in l:
            continue
        m = re.match(r'([\w.-]+/[\w.-]+)#(\d+)', l.split(' -> ')[0].strip())  # only a PR key; other waits stay unwatched
        if m:
            yield l, f"{m[1]}#{m[2]}"


def emit_dependents(key):
    for l, k in waiting_keys():
        if k == key:
            emit(f"### DEPENDENT of merged {key}: {l.split(' -> ', 1)[1]}: do it now and post the progress on that PR (mergeworthy:github-threads)")


def emit_tracker_stale(key, ended):
    """umbrella.txt ("owner/repo N"): the program's umbrella issue (methodology 1.2). When a PR merges or closes, its
    checkbox there must be ticked and say how it ended."""
    path = os.path.join(HERE, 'umbrella.txt')
    w = open(path).read().split() if os.path.exists(path) else []
    if len(w) < 2 or f"{w[0]}#{w[1]}" == key:
        return
    try:
        body = json.loads(gh(['api', f"repos/{w[0]}/issues/{w[1]}"]))['body'] or ''
    except Exception as e:
        emit(f"WATCH ERROR tracker check {key}: {e}")
        return
    repo, num = key.split('#')
    ref = re.compile(rf'(?<![\w/.-])(?:{re.escape(repo)}#|{"#" if repo == w[0] else "(?!)"}){num}(?!\d)')
    items = [l for l in body.splitlines() if re.match(r'\s*- \[[ x]\] ', l) and ref.search(l)]
    if not items:
        emit(f"### TRACKER STALE {w[0]}#{w[1]}: {key} {ended} and has no checkbox there: add it with its state, through the gate (mergeworthy:core 1.2)")
    elif not any(l.lstrip().startswith('- [x]') and re.search(r'\((merged|closed|released)', l) for l in items):
        emit(f"### TRACKER STALE {w[0]}#{w[1]}: {key} {ended}: tick its checkbox and write '({ended}…)' after it, through the gate (mergeworthy:core 1.2)")


def emit_maintainer_commits(repo, key, old, new):
    """A maintainer's commits pushed to a tracked PR: reviewing them was requested ("Review each of my commit as I push them")."""
    try:
        commits = json.loads(gh(['api', f"repos/{repo}/compare/{old}...{new}", '--jq', '[.commits[] | {sha: .sha[0:10], login: (.author.login // "")}]']))
    except Exception as e:
        emit(f"WATCH ERROR compare {key} {old}...{new}: {e}")
        return
    try:  # commits that came from merging the base branch aren't the PR's
        base = gh(['api', f"repos/{repo}/pulls/{key.split('#')[1]}", '--jq', '.base.ref']).strip()
        on_pr = set(json.loads(gh(['api', f"repos/{repo}/compare/{base}...{new}", '--jq', '[.commits[].sha[0:10]]'])))
    except Exception as e:
        emit(f"WATCH ERROR compare {key} base...{new}: {e}")
        return
    theirs = [c['sha'] for c in commits if c['login'] in EYES_FOR and c['login'] != ME and c['sha'] in on_pr]
    if theirs:
        emit(f"### MAINTAINER COMMITS {key}: {' '.join(theirs)}: review each one in a table (| Commit | What it does, and the idea behind it | Rating |, one short sentence each; rated N/10 with a short reason next to anything below 10, e.g. 9/10 (Vite's built-ins differ); an emoji only where it's funny; 10/10 only when nothing could be better), as requested (mergeworthy:github-threads)")


def emit_refactor_stale(repo, key, new):
    """Your PR's own commits changed more than ~80 lines since its last refactor pass (`pr-steps refactor`): the ratings
    describe old code. Merges of the base branch, tests and lockfiles don't count: they aren't the PR's code to rate."""
    num = key.split('#')[1]
    try:
        pr = json.loads(gh(['api', f"repos/{repo}/pulls/{num}", '--jq', '{author: .user.login, base: .base.ref}']))
        if pr['author'] != ME: return
        commits = json.loads(gh(['api', f"repos/{repo}/compare/{pr['base']}...{new}", '--jq', '[.commits[] | {sha, merge: (.parents | length > 1)}]']))
        rec = os.path.expanduser('~/.claude/pr-steps')
        idx = max((i for i, c in enumerate(commits) if os.path.exists(f"{rec}/{c['sha']}") and any(l.startswith('refactor ') for l in open(f"{rec}/{c['sha']}"))), default=-1)
        since = [c['sha'] for c in commits[idx + 1:] if not c['merge']]
        skip = re.compile(r'\.(spec|test)\.|(^|/)tests?/|(^|/)(pnpm-lock\.yaml|package-lock\.json|yarn\.lock)$')
        lines = sum(f['n'] for sha in since for f in json.loads(gh(['api', f"repos/{repo}/commits/{sha}", '--jq', '[.files[] | {filename, n: (.additions + .deletions)}]'])) if not skip.search(f['filename']))
    except Exception as e:
        emit(f"WATCH ERROR refactor check {key}: {e}")
        return
    if lines > 80:
        last = commits[idx]['sha'][:10] if idx >= 0 else 'never'
        emit(f"### REFACTOR STALE {key}: {lines} changed lines since the last refactor pass ({last}): re-run it on the whole PR diff (mergeworthy:refactor), then `pr-steps refactor`")


def read_threads():
    threads = []
    for l in open(THREADS):
        w = l.split('#', 1)[0].split() if not l.lstrip().startswith('#') else []
        if len(w) == 2 and w[1].isdigit():
            threads.append(w)
        elif w:
            emit(f"WATCH ERROR threads.txt: bad line {l.strip()!r} (want 'owner/repo number')")
    for _, key in waiting_keys():  # a PR you wait on is watched too, so its merge emits DEPENDENT
        repo, num = key.rsplit('#', 1)
        if [repo, num] not in threads:
            threads.append([repo, num])
    return threads


def scan_reactions(state, threads):
    """A 👍 or 👎 from GH_WATCH_EYES on one of the agent's comments is feedback on that comment (mergeworthy:github-threads)."""
    agent_hashes = agent_post_hashes()
    seen = state.setdefault('reactions', {})  # "<kind>:<id>" -> ["<login>:<content>", ...]
    for repo, num in threads:
        for kind, path in (('body', 'issues'), ('comment', 'issues'), ('review-comment', 'pulls')):
            try:
                if kind == 'body':  # the PR or issue description itself
                    comments = gh_json(f"repos/{repo}/issues/{num}")
                else:
                    comments = gh_json(f"repos/{repo}/{path}/{num}/comments?per_page=100")
            except Exception as e:
                if path == 'issues':
                    emit(f"WATCH ERROR reactions {repo}#{num}: {e}")
                continue  # an issue has no review comments
            for c in comments:
                counts = c.get('reactions') or {}
                if c['user'].get('login') != ME or _norm(c.get('body')) not in agent_hashes or not (counts.get('+1') or counts.get('-1')):
                    continue
                sk = f"{kind}:{c['id']}"
                try:
                    url = f"repos/{repo}/issues/{num}/reactions" if kind == 'body' else f"repos/{repo}/{path}/comments/{c['id']}/reactions"
                    reactions = gh_json(f"{url}?per_page=100")
                except Exception as e:
                    emit(f"WATCH ERROR reactions {sk}: {e}")
                    continue
                for r in reactions:
                    who, content = r['user']['login'], r['content']
                    if content not in ('+1', '-1') or who not in EYES_FOR or f"{who}:{content}" in seen.get(sk, []):
                        continue
                    seen.setdefault(sk, []).append(f"{who}:{content}")
                    if content == '-1':
                        emit(f"### THUMBS DOWN {repo}#{num} by {who} on {c['html_url']} (reaction {r['id']}): work out why and fix the rule behind it; if the thread is still on that point, post a new reply with the fix that @-mentions {who}; if it has moved past it or it's resolved, instead edit that comment to add how you'll do better. Leave the 👎 (mergeworthy:github-threads)")
                    else:
                        emit(f"### THUMBS UP {repo}#{num} by {who} on {c['html_url']}: note what they liked and reinforce the rule that produced it (mergeworthy:github-threads)")


def react_eyes(repo, kind, cid):
    path = f"repos/{repo}/issues/comments/{cid}/reactions" if kind == 'comment' else f"repos/{repo}/pulls/comments/{cid}/reactions"
    try:
        gh(['api', '-X', 'POST', path, '-f', 'content=eyes'])
    except Exception as e:
        emit(f"WATCH ERROR eyes {repo} {kind} {cid}: {e}")


def fetch_thread(repo, num, since, is_pr_known, author_known=None):
    """Network only (runs in a worker thread). Returns (is_pr, author, events, pr_state, red_checks, last_comment)."""
    is_pr, author = is_pr_known, author_known
    if is_pr is None or author is None:
        issue = json.loads(gh(['api', f"repos/{repo}/issues/{num}"]))
        is_pr, author = 'pull_request' in issue, (issue.get('user') or {}).get('login')
    events = []
    for c in gh_json(f"repos/{repo}/issues/{num}/comments?since={since}&per_page=100"):
        events.append(('comment', c['id'], c['updated_at'], {**c['user'], 'assoc': c.get('author_association')}, c['html_url'], c.get('body') or '', ''))
    pr_state = red = None
    if is_pr:
        for c in gh_json(f"repos/{repo}/pulls/{num}/comments?since={since}&per_page=100"):
            events.append(('review-comment', c['id'], c['updated_at'], {**c['user'], 'assoc': c.get('author_association')}, c['html_url'], c.get('body') or '', f"{c.get('path')}:{c.get('line') or c.get('original_line')}"))
        for r in gh_json(f"repos/{repo}/pulls/{num}/reviews?per_page=100"):
            if (r.get('submitted_at') or '') >= since and (r.get('body') or r.get('state') in ('APPROVED', 'CHANGES_REQUESTED')):
                events.append(('review', r['id'], r['submitted_at'], {**r['user'], 'assoc': r.get('author_association')}, r['html_url'], r.get('body') or '', r.get('state')))
        pr = json.loads(gh(['api', f"repos/{repo}/pulls/{num}"]))
        # 'conflict': GitHub runs no CI on a PR that conflicts with its base, so a conflict must be reported like red CI
        pr_state = {'head': pr['head']['sha'][:10], 'state': 'merged' if pr.get('merged') else pr['state'], 'conflict': pr.get('mergeable_state') == 'dirty'}
        if pr_state['state'] == 'open':
            r = subprocess.run(['gh', 'pr', 'checks', num, '-R', repo], capture_output=True, text=True)
            if r.returncode not in (0, 1, 8) and 'no checks reported' not in r.stderr:  # 1 = some failed, 8 = some pending
                raise RuntimeError(f"gh pr checks {num} -R {repo}: {r.stderr.strip()[:200]}")
            checks = r.stdout
            red = sorted(l.split('\t')[0] for l in checks.splitlines() if '\tfail\t' in l)
    return is_pr, author, events, pr_state, red, fetch_last_comment(repo, num)


_F = 'state comments(last:1){nodes{databaseId url createdAt author{login}}}'
LAST_COMMENT = ('query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){issueOrPullRequest(number:$n){'
                '... on Issue{F} ... on PullRequest{F}}}}').replace('F', _F)


def fetch_last_comment(repo, num):
    """The thread's latest issue or PR conversation comment and whether the thread is open: one GraphQL call."""
    o, r = repo.split('/')
    t = json.loads(gh(['api', 'graphql', '-f', f'query={LAST_COMMENT}', '-f', f'o={o}', '-f', f'r={r}', '-F', f'n={num}']))['data']['repository']['issueOrPullRequest']
    nodes = t['comments']['nodes']
    return {'open': t['state'] == 'OPEN', 'last': nodes[0] if nodes else None}


def emit_wait_ping(state, key, last, events):
    """mergeworthy:github-threads, the wait ping: your account's comment is the thread's last, and nobody has replied since
    WAIT_PING_HOURS. Once per comment id; a newer comment by anyone makes a different comment the last, so it starts over."""
    if not last or not last['open'] or not last['last'] or (last['last'].get('author') or {}).get('login') != ME:
        return
    c = last['last']
    posted = datetime.datetime.strptime(c['createdAt'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc)
    if any(user.get('login') != ME and upd > c['createdAt'] for _, _, upd, user, *_ in events):
        return  # a review comment or review from someone else, newer than ours (the call above sees only conversation comments)
    hours = (datetime.datetime.now(datetime.timezone.utc) - posted).total_seconds() / 3600
    done = state.setdefault('wait_ping', {}).setdefault(key, [])
    if hours < WAIT_PING_HOURS or c['databaseId'] in done:
        return
    done[:] = [c['databaseId']]  # only the latest comment matters
    emit(f"### WAIT PING DUE {key}: no reply for {int(hours)} h since {c['url']}; nudge whoever it waits on with the open question (mergeworthy:github-threads)")
    append_owed(f"{key} wait-ping {c['databaseId']} since {c['url']}: no reply for {int(hours)} h; nudge whoever it waits on")  # the Stop hook holds the turn until it's done


def scan(state, only=None, threads=None):
    """Scan all tracked threads (or only the given keys, or the given threads) in parallel; apply results in this thread."""
    from concurrent.futures import ThreadPoolExecutor
    def since(key):  # each thread keeps its own position, so one failing thread doesn't hold back the others
        dt = datetime.datetime.strptime(state['since_by'].get(key, state['since']), '%Y-%m-%dT%H:%M:%SZ') - datetime.timedelta(minutes=10)
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    started = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    if threads is None:
        threads = read_threads()
        if only is not None:
            threads = [t for t in threads if f"{t[0]}#{t[1]}" in only]
        else:
            threads = scan_set(state, threads)
    ok = True
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_thread, repo, num, since(f"{repo}#{num}"), state['is_pr'].get(f"{repo}#{num}"), state.setdefault('author', {}).get(f"{repo}#{num}")): (repo, num) for repo, num in threads}
        for fut, (repo, num) in futs.items():
            key = f"{repo}#{num}"
            try:
                is_pr, author, events, pr_state, red, last = fut.result()
            except Exception as e:
                ok = False
                emit(f"WATCH ERROR {key}: {e}")
                continue
            state['is_pr'][key] = is_pr
            state['author'][key] = author
            state['since_by'][key] = started
            if pr_state:
                prev = state['prs'].get(key)
                if prev and prev != pr_state:
                    emit(f"### PR CHANGED {key}: {prev} -> {pr_state}")
                    if pr_state['state'] == 'merged' and prev.get('state') != 'merged':
                        emit_dependents(key)
                    if pr_state['state'] in ('merged', 'closed') and prev.get('state') != pr_state['state']:
                        emit_tracker_stale(key, pr_state['state'])
                    if prev.get('head') != pr_state['head']:
                        emit_maintainer_commits(repo, key, prev['head'], pr_state['head'])
                        emit_refactor_stale(repo, key, pr_state['head'])
                state['prs'][key] = pr_state
            if red is not None:
                if red != state['ci'].get(key, []):
                    emit(f"### CI {key}: red={red}: fix it, or if it is not this PR's doing, say why on the PR now with the evidence (mergeworthy:github-threads)" if red else f"### CI {key}: no longer red")
                state['ci'][key] = red
            agent_hashes = agent_post_hashes()  # read after the fetch: a post gated while it ran is the agent's
            for kind, cid, upd, user, url, body, extra in events:
                if answerable(user, body, agent_hashes, kind, own=author == ME):
                    handle_comment(state, repo, key, kind, cid, upd, user['login'], url, body, extra)
            emit_wait_ping(state, key, last, events)
    if only is None:
        state['since'] = started  # only the default for threads added to threads.txt later
    return ok


def scan_set(state, threads):
    """The threads a full scan reads: the open ones, and once an hour the merged and closed ones too. A full scan costs
    about 7 API calls a thread; reading every closed thread every 3 minutes ran through GitHub's 5,000 calls an hour.
    A comment on a closed thread still arrives sooner through the notifications fast path (your own threads notify you)."""
    if time.time() - state.get('closed_scan', 0) > 3600:
        state['closed_scan'] = time.time()
        return threads
    return [t for t in threads if state['prs'].get(f"{t[0]}#{t[1]}", {}).get('state') not in ('merged', 'closed')]


def notifications_changed(state):
    """Cheap fast path: a conditional request GitHub answers with 304 (not rate-limited) until something changes.
    Returns None (no change) or the set of changed thread keys ("owner/repo#N")."""
    lm = state.get('notif_lm')
    args = ['gh', 'api', '-i', 'notifications?all=true&per_page=50']
    if lm:
        args[2:2] = ['-H', f'If-Modified-Since: {lm}']
    r = subprocess.run(args, capture_output=True, text=True)
    head = r.stdout.split('\n', 1)[0]
    if ' 304 ' in head or not head.startswith('HTTP/'):
        return None
    headers, _, body = r.stdout.partition('\r\n\r\n') if '\r\n\r\n' in r.stdout else r.stdout.partition('\n\n')
    for l in headers.splitlines():
        if l.lower().startswith('last-modified:'):
            state['notif_lm'] = l.split(':', 1)[1].strip()
    keys = set()
    prev = state.get('notif_upd', '')
    try:
        for n in json.loads(body):
            if n.get('updated_at', '') <= prev:
                continue
            state['notif_upd'] = max(state.get('notif_upd', ''), n.get('updated_at', ''))
            url = (n.get('subject') or {}).get('url') or ''
            parts = url.split('/repos/')[-1].split('/')
            if len(parts) >= 4:
                keys.add(f"{parts[0]}/{parts[1]}#{parts[3]}")
    except Exception:
        pass
    return keys


# kept across rounds: a new TLS connection per request makes a round several times slower
_pool, _conn = ThreadPoolExecutor(8), threading.local()


def repo_comments_changed(state):
    """The notifications fast path lags GitHub by 20-30 s. Each watched repo's newest issue and review comments, polled
    with If-None-Match (a 304 isn't rate-limited), catch a comment within one loop. Returns the changed thread keys."""
    threads = read_threads()
    watched = {f"{r}#{n}" for r, n in threads}
    etags, seen = state.setdefault('rc_etag', {}), state.setdefault('rc_seen', {})
    token = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True).stdout.strip()
    def poll(url):
        headers = {'Authorization': f'Bearer {token}', 'User-Agent': 'gh-watch', 'Accept': 'application/vnd.github+json'}
        if etags.get(url):
            headers['If-None-Match'] = etags[url]
        try:
            _conn.c = getattr(_conn, 'c', None) or http.client.HTTPSConnection('api.github.com', timeout=20)
            _conn.c.request('GET', '/' + url, headers=headers)
            r = _conn.c.getresponse()
            body = r.read()
            return url, r.headers.get('ETag'), body if r.status == 200 else None
        except Exception:  # a dropped connection: reconnect next round
            _conn.c = None
            return url, None, None
    urls = [f"repos/{r}/{k}/comments?sort=created&direction=desc&per_page=20" for r in sorted({r for r, _ in threads}) for k in ('issues', 'pulls')]
    keys = set()
    for url, etag, body in _pool.map(poll, urls):
        if body is None:
            continue
        if etag:
            etags[url] = etag
        try:
            comments = json.loads(body)
        except ValueError:
            continue
        prev = seen.get(url)
        seen[url] = max([prev or ''] + [c.get('created_at', '') for c in comments])
        if prev is None:  # the first poll only records where the feed stands
            continue
        for c in comments:
            num = (c.get('issue_url') or c.get('pull_request_url') or '').rsplit('/', 1)[-1]
            key = f"{url.split('/')[1]}/{url.split('/')[2]}#{num}"
            if c.get('created_at', '') > prev and key in watched:
                keys.add(key)
    return keys


AGENT_CMD = re.compile(r'\s*/agent\b(?:[ \t]+([\w.-]+))?', re.I)  # a comment that starts with /agent, then maybe a watch dir's name
THREAD_REF = re.compile(r'(?<![\w/.-])([\w.-]+/[\w.-]+)#(\d+)|github\.com/([\w.-]+/[\w.-]+)/(?:issues|pull)/(\d+)')
AGENT_CLAIMS = os.path.expanduser('~/.mergeworthy/agent-commands.seen')  # shared by every daemon: each command is emitted once


def live_dirs():
    return [d for d in dict.fromkeys(watch_dirs()) if live(d)]


def listed_threads(d):
    try:
        return {f"{w[0]}#{w[1]}" for w in (l.split('#', 1)[0].split() for l in open(os.path.join(d, 'threads.txt'))) if len(w) == 2}
    except OSError:
        return set()


def thread_links(repo, num):
    """Threads this one links to (its body and comments) or that link to it (GitHub's cross-references)."""
    links = set()
    def read(text):
        links.update(f"{m[1] or m[3]}#{m[2] or m[4]}" for m in THREAD_REF.finditer(text or ''))
    read(json.loads(gh(['api', f"repos/{repo}/issues/{num}"])).get('body'))
    for e in gh_json(f"repos/{repo}/issues/{num}/timeline?per_page=100"):
        if e.get('event') == 'commented':
            read(e.get('body'))
        elif e.get('event') == 'cross-referenced' and ((e.get('source') or {}).get('issue') or {}).get('number'):
            i = e['source']['issue']
            links.add(f"{i['repository_url'].split('/repos/')[-1]}#{i['number']}")
    links.discard(f"{repo}#{num}")
    return links


def route_agent_command(repo, num, name):
    """-> (watch dir, routed). The dir named `name` (its folder's name); else the dir listing most of the threads this one
    links to or is linked from (a tie goes to main_dir); else main_dir, unrouted."""
    dirs = live_dirs()
    for d in dirs:
        if name and os.path.basename(d.rstrip('/')).lower() == name.lower():
            return d, True
    links = thread_links(repo, num)
    score = {d: len(links & listed_threads(d)) for d in dirs}
    best = max(score.values(), default=0)
    if best:
        top = [d for d in dirs if score[d] == best]
        return (main_dir() if main_dir() in top else top[0]), True
    return main_dir(), False


def claim(sk, record=True):
    """True if no daemon has taken this command yet (and, with record, takes it): the claim file is locked, so two daemons can't both."""
    os.makedirs(os.path.dirname(AGENT_CLAIMS), exist_ok=True)
    with open(AGENT_CLAIMS, 'a+') as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        f.seek(0)
        if sk in f.read().split():
            return False
        if record:
            f.write(sk + '\n')
        return True


def agent_command(repo, num, kind, c):
    """Your comment starting with /agent on a thread no live watch dir lists (a listed thread's own scan reports it) goes to
    one dir's events.log, once: `/agent <name>` to the dir of that name, else the dir that lists a thread this one links to
    or is linked from, else main_dir (UNROUTED). You and the agent post as one account: a gated post is not a command."""
    key, body, cid = f"{repo}#{num}", c.get('body') or '', c.get('id')
    sk = f"{kind}:{cid}"
    if not cid or not AGENT_CMD.match(body) or (c.get('user') or {}).get('login', ME) != ME or _norm(body) in agent_post_hashes() \
            or any(key in listed_threads(d) for d in live_dirs()) or not claim(sk, record=False):
        return
    target, routed = route_agent_command(repo, num, AGENT_CMD.match(body)[1])
    upd, url = c.get('updated_at') or c.get('created_at', ''), c.get('html_url', '')
    indented = '\n'.join('    ' + l for l in body.splitlines())  # no body line can start with ### and pass as an event
    event = f"### {'AGENT COMMAND' if routed else 'UNROUTED /agent'} {key} {kind} {cid} by {ME} {upd}  {url}\n{indented}\n"
    if ONCE:
        return emit(event)
    if not target or not claim(sk):
        return
    line = key.replace('#', ' ')
    if routed and line not in open(os.path.join(target, 'threads.txt')).read().splitlines():
        open(os.path.join(target, 'threads.txt'), 'a').write(line + '\n')  # its follow-ups are watched
    append_owed(f"{key} {kind} {cid} by {ME} {url} — {body.strip().splitlines()[0][:80]}", target)
    react_eyes(repo, kind, cid)
    with open(os.path.join(target, 'events.log'), 'a') as f:  # last: the event wakes that session, which finds the rest in place
        f.write(event)


def watched_repos():
    """Every repo a live watch dir lists a thread or a whole-repo line for (and this dir's own)."""
    repos = set()
    for d in dict.fromkeys(live_dirs() + [HERE]):
        repos |= {t.rsplit('#', 1)[0] for t in listed_threads(d)}
        try:
            repos |= {l.split('#', 1)[0].strip() for l in open(os.path.join(d, 'repos.txt')) if l.split('#', 1)[0].strip()}
        except OSError:
            pass
    return repos


def discover_agent_commands(state):
    """Your /agent comments on threads no watcher lists reach no one: you comment as the agent's own account, which GitHub
    doesn't notify you of, and the search and events indexes lag by many minutes. So each full scan lists the recent issue
    and review comments of every watched repo (the comments feeds are live) and hands each /agent comment to agent_command.
    A search of the threads you commented on, minus those repos, backs it up for repos no one lists. Scans overlap by
    10 minutes; a failed call leaves the scan position, so it is retried."""
    started = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    since = (datetime.datetime.strptime(state.get('agent_since') or state['since'], '%Y-%m-%dT%H:%M:%SZ') - datetime.timedelta(minutes=10)).strftime('%Y-%m-%dT%H:%M:%SZ')
    ok = True
    repos = watched_repos()
    for repo in sorted(repos):
        try:
            for kind, path in (('comment', 'issues'), ('review-comment', 'pulls')):
                for c in gh_json(f"repos/{repo}/{path}/comments?since={since}&sort=updated&direction=desc&per_page=100"):
                    agent_command(repo, (c.get('issue_url') or c.get('pull_request_url') or '').rsplit('/', 1)[-1], kind, c)
        except Exception as e:
            ok = False
            emit(f"WATCH ERROR agent commands {repo}: {e}")
    try:
        items = json.loads(gh(['api', '-X', 'GET', 'search/issues', '-f', f'q=commenter:{ME} updated:>={since}', '-f', 'per_page=50']))['items']
        for i in items:
            repo, num = i['repository_url'].split('/repos/')[-1], i['number']
            if repo in repos:
                continue
            try:
                found = [('comment', c) for c in gh_json(f"repos/{repo}/issues/{num}/comments?since={since}&per_page=100")]
                if 'pull_request' in i:
                    found += [('review-comment', c) for c in gh_json(f"repos/{repo}/pulls/{num}/comments?since={since}&per_page=100")]
                for kind, c in found:
                    agent_command(repo, num, kind, c)
            except Exception as e:
                ok = False
                emit(f"WATCH ERROR agent commands {repo}#{num}: {e}")
    except Exception as e:
        ok = False
        emit(f"WATCH ERROR agent command search: {e}")
    if ok:
        state['agent_since'] = started


def ai_call_elsewhere(state, repo, num, etype, c):
    """Your /ai or /agent comment on a thread no live watcher watches goes to main_dir's watcher, so one session gets it."""
    key, body = f"{repo}#{num}", c.get('body') or ''
    if not c.get('id') or not AI_CALL.search(body) or _norm(body) in agent_post_hashes():
        return
    if AGENT_CMD.match(body):  # routed to the right dir, from any daemon
        kind = 'review-comment' if etype == 'PullRequestReviewCommentEvent' else 'comment'
        try:
            agent_command(repo, num, kind, {**c, 'user': c.get('user') or {'login': ME}})
        except Exception as e:
            emit(f"WATCH ERROR agent command {key}: {e}")
        return
    if main_dir() != HERE:
        return
    watched = any(f"{repo} {num}" in (l.strip() for l in open(os.path.join(d, 'threads.txt')))
                  for d in watch_dirs() if live(d) and os.path.exists(os.path.join(d, 'threads.txt')))
    if not watched:  # a watched thread's own scan handles it
        kind = 'review-comment' if etype == 'PullRequestReviewCommentEvent' else 'comment'
        handle_comment(state, repo, key, kind, c['id'], c.get('updated_at') or c.get('created_at', ''), ME, c.get('html_url', ''), body)


def own_events_changed(state):
    """GitHub doesn't notify you of your own comments, so the notifications fast path misses the user's (same account).
    Their public events feed, polled with If-None-Match (a 304 isn't rate-limited), catches them.
    Returns the set of thread keys ("owner/repo#N") with new comments or reviews."""
    etag = state.get('events_etag')
    args = ['gh', 'api', '-i', f'users/{ME}/events?per_page=30']
    if etag:
        args[2:2] = ['-H', f'If-None-Match: {etag}']
    r = subprocess.run(args, capture_output=True, text=True)
    head = r.stdout.split('\n', 1)[0]
    if ' 304 ' in head or not head.startswith('HTTP/'):
        return set()
    headers, _, body = r.stdout.partition('\r\n\r\n') if '\r\n\r\n' in r.stdout else r.stdout.partition('\n\n')
    for l in headers.splitlines():
        if l.lower().startswith('etag:'):
            state['events_etag'] = l.split(':', 1)[1].strip()
    keys = set()
    prev = state.get('events_seen', '')
    try:
        for e in json.loads(body):
            if e.get('created_at', '') <= prev or e.get('type') not in ('IssueCommentEvent', 'PullRequestReviewCommentEvent', 'PullRequestReviewEvent'):
                continue
            p = e.get('payload') or {}
            num = (p.get('issue') or p.get('pull_request') or {}).get('number')
            if num:
                keys.add(f"{e['repo']['name']}#{num}")
                ai_call_elsewhere(state, e['repo']['name'], num, e['type'], p.get('comment') or {})
        state['events_seen'] = max([prev] + [e.get('created_at', '') for e in json.loads(body)])
    except Exception:
        pass
    return keys


FOLLOWUP_DAYS, FOLLOWUP_EVERY, SLACK = 60, 3600, 3  # how long a merged PR is followed, how often, lines of slack around its lines


def patch_lines(patch):
    """-> (old-side, new-side) line numbers a unified-diff patch changes; a pure insertion or deletion counts at its position."""
    old, new, o, n = [], [], 0, 0
    for l in (patch or '').splitlines():
        if l.startswith('@@'):
            m = re.match(r'@@ -(\d+)(?:,\d+)? \+(\d+)', l)
            o, n = int(m[1]), int(m[2])
        elif l.startswith('-'):
            old.append(o); new.append(n); o += 1
        elif l.startswith('+'):
            old.append(o); new.append(n); n += 1
        elif not l.startswith('\\'):
            o += 1; n += 1
    return old, new


def spans(nums):
    out = []
    for x in sorted(set(nums)):
        if out and x <= out[-1][1] + 1:
            out[-1][1] = x
        else:
            out.append([x, x])
    return out


def iso_epoch(t):
    return datetime.datetime.strptime(t, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc).timestamp()


def follow_record(key):
    """A merged PR of yours: its merge commit and the lines it changed, to compare later commits against."""
    repo, num = key.rsplit('#', 1)
    pr = json.loads(gh(['api', f"repos/{repo}/pulls/{num}"]))
    files = {f['filename']: spans(patch_lines(f['patch'])[1]) if f.get('patch') else [[1, 10**9]]  # no patch: the whole file
             for f in gh_json(f"repos/{repo}/pulls/{num}/files?per_page=100") if f.get('status') != 'removed'}
    until = iso_epoch(pr['merged_at']) + FOLLOWUP_DAYS * 86400
    return {'merge_sha': pr['merge_commit_sha'], 'base': pr['base']['ref'], 'scanned': pr['merged_at'], 'checked': 0,
            'until': until, 'files': files if until > time.time() else {}}


def touches(e, files):
    """Does a commit's file list change lines of the PR (within SLACK lines), or rename or remove one of its files? A rename is followed."""
    hit, renames = False, []
    for f in files:
        old = f.get('previous_filename') or f['filename']
        ranges = e['files'].get(old)
        if ranges is None:
            continue
        if old != f['filename']:
            renames.append((old, f['filename']))
        if old != f['filename'] or f.get('status') == 'removed' or not f.get('patch'):
            hit = True
        else:
            hit = hit or any(lo - SLACK <= l <= hi + SLACK for l in patch_lines(f['patch'])[0] for lo, hi in ranges)
    for old, new in renames:
        e['files'][new] = e['files'].pop(old)
    return hit


def follow_emit(sk, line):
    if claim(sk, record=not ONCE):  # once across restarts; a manual --once check records nothing
        emit(line)


def follow_ups(state):
    """After a PR of yours merges, later commits to its lines by others and PRs that reference it are a review you didn't get
    (mergeworthy:core, Learning from follow-ups). Each merged PR in threads.txt is followed for FOLLOWUP_DAYS, one check an hour:
    `### FOLLOW-UP` once per commit (not yours, not a merge) that touches its recorded lines, and once per other person's PR
    that references it (GitHub's cross-referenced timeline events, which a mention in a PR body creates too)."""
    fu, now = state.setdefault('followups', {}), time.time()
    for key in {f"{r}#{n}" for r, n in read_threads()} - fu.keys():
        if state['prs'].get(key, {}).get('state') == 'merged' and state.get('author', {}).get(key) == ME:
            try:
                fu[key] = follow_record(key)
            except Exception as e:
                emit(f"WATCH ERROR follow-up record {key}: {e}")
    for e in fu.values():
        if e['until'] <= now:
            e['files'] = {}  # past the window: kept as a marker so the PR isn't recorded again
    due = {}
    for key, e in fu.items():
        if e['until'] > now and now - e['checked'] >= FOLLOWUP_EVERY:
            due.setdefault((key.rsplit('#', 1)[0], e['base']), []).append(key)
    details = {}
    for (repo, base), keys in due.items():
        started = datetime.datetime.fromtimestamp(now - 600, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')  # overlap: claims dedupe
        try:
            commits = gh_json(f"repos/{repo}/commits?sha={base}&since={min(fu[k]['scanned'] for k in keys)}&per_page=100")
        except Exception as ex:
            emit(f"WATCH ERROR follow-up commits {repo}: {ex}")
            continue
        for key in keys:
            e, num = fu[key], key.rsplit('#', 1)[1]
            try:
                for c in commits:
                    sha, author = c['sha'], (c.get('author') or {}).get('login')
                    sk = f"followup:{key}:{sha}"
                    if sha == e['merge_sha'] or author == ME or len(c.get('parents') or []) > 1 \
                            or c['commit']['committer']['date'] < e['scanned'] or not claim(sk, record=False):
                        continue
                    if sha not in details:
                        details[sha] = json.loads(gh(['api', f"repos/{repo}/commits/{sha}"])).get('files') or []
                    if touches(e, details[sha]):
                        follow_emit(sk, f"### FOLLOW-UP {key}: {sha[:10]} by {author or c['commit']['author']['name']} changes lines from your PR  {c['html_url']}")
                for t in gh_json(f"repos/{repo}/issues/{num}/timeline?per_page=100"):
                    i = (t.get('source') or {}).get('issue') or {}
                    if t.get('event') == 'cross-referenced' and 'pull_request' in i and not is_bot(i.get('user')) and (i.get('user') or {}).get('login') != ME:
                        follow_emit(f"followup-ref:{key}:{i['html_url']}", f"### FOLLOW-UP {key}: {i['html_url']} by {i['user']['login']} references your PR")
                e['scanned'], e['checked'] = started, now
            except Exception as ex:
                emit(f"WATCH ERROR follow-up {key}: {ex}")


def follow_up_scan():
    with locked():
        state = load_state()
        follow_ups(state)
        save_state(state)


def locked():
    """One scan at a time across processes (daemon and manual runs), so state updates aren't lost."""
    f = open(STATE + '.lock', 'w')
    fcntl.flock(f, fcntl.LOCK_EX)
    return f


def run_scan():
    with locked():
        state = load_state()
        threads = scan_set(state, read_threads())  # once: it opens the hourly closed-thread window for both scans
        scan(state, threads=threads)
        save_state(state)
    with locked():
        state = load_state()
        scan_reactions(state, threads)
        save_state(state)


def agent_command_scan():
    with locked():
        state = load_state()
        discover_agent_commands(state)
        save_state(state)


def retire_if_done():
    """A watcher whose every thread is merged or closed (and that covers no whole repo) has nothing left to watch: it
    disables its service, so it doesn't come back after a reboot, or stops its daemon."""
    repos = os.path.join(HERE, 'repos.txt')
    if os.path.exists(repos) and open(repos).read().strip():
        return
    threads = read_threads()
    if not threads:
        return
    with locked():
        state = load_state()
    if any(e['until'] > time.time() for e in state.get('followups', {}).values()):
        return  # a merged PR still being followed (follow_ups)
    prs = state['prs']
    for repo, num in threads:
        key = f"{repo}#{num}"
        if key in prs:
            done = prs[key].get('state') in ('merged', 'closed')
        else:
            try:
                done = json.loads(gh(['api', f"repos/{repo}/issues/{num}", '--jq', '{state}']))['state'] == 'closed'
            except Exception:
                return  # unknown: keep watching
        if not done:
            return
    print(f"WATCHER RETIRED at {datetime.datetime.now(datetime.timezone.utc):%Y-%m-%dT%H:%M:%SZ}: every watched thread is merged or closed", flush=True)
    # each supervisor gh-watch-start may have used, so the watcher doesn't come back after a reboot
    supervisor = os.environ.get('GH_WATCH_SUPERVISOR', '')  # set by the unit or the launchd agent gh-watch-start wrote
    if supervisor == 'systemd':
        unit = 'gh-watch@' + subprocess.run(['systemd-escape', '--path', HERE], capture_output=True, text=True).stdout.strip() + '.service'
        subprocess.run(['systemctl', '--user', 'disable', '--now', unit])
        return
    label = os.environ.get('XPC_SERVICE_NAME', '')
    if supervisor == 'launchd':
        subprocess.run(['rm', '-f', os.path.expanduser(f'~/Library/LaunchAgents/{label}.plist')])
        subprocess.run(['launchctl', 'bootout', f'gui/{os.getuid()}/{label}'])
        return
    tab = subprocess.run(['crontab', '-l'], capture_output=True, text=True)
    if tab.returncode == 0 and f'# gh-watch {HERE}' in tab.stdout:  # cron
        kept = ''.join(l + '\n' for l in tab.stdout.splitlines() if not l.endswith(f'# gh-watch {HERE}'))
        subprocess.run(['crontab', '-'], input=kept, text=True)
    try:
        os.kill(int(open(os.path.join(HERE, 'gh-watch.pid')).read().strip()), 15)  # the daemon's trap stops this watcher too
    except (OSError, ValueError):
        sys.exit(0)


# the version this process runs, resolved at start: ~/.mergeworthy/current may be repointed while it runs
RUNNING_ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))


def installed_root():
    """The plugin version Claude Code has installed now (it changes on every update), or None outside the plugin."""
    try:
        with open(os.path.expanduser('~/.claude/plugins/installed_plugins.json')) as f:
            root = json.load(f)['plugins']['mergeworthy@mergeworthy'][0]['installPath']
        return root if os.path.isdir(root) else None
    except Exception:
        return None


def follow_update():
    """After a plugin update, point ~/.mergeworthy/current at the new version and exit 75: the daemon restarts this
    script on the new code. A watcher run from a checkout (not the plugin's cache) never follows."""
    if '/plugins/cache/' not in RUNNING_ROOT:
        return
    root = installed_root()
    link = os.path.join(HERE, 'gh-watch.py')
    if root and os.path.islink(link) and '/plugins/cache/' in os.readlink(link):  # pinned to one version by an old gh-watch-start
        os.remove(link)
        os.symlink(os.path.expanduser('~/.mergeworthy/current/watcher/gh-watch.py'), link)
    if root and os.path.realpath(root) != RUNNING_ROOT:
        cur = os.path.expanduser('~/.mergeworthy/current')
        tmp = cur + '.tmp'
        if os.path.lexists(tmp): os.remove(tmp)
        os.symlink(root, tmp)
        os.replace(tmp, cur)
        sys.exit(75)


def main():
    if ONCE:
        run_scan()
        agent_command_scan()
        follow_up_scan()
        return
    last_full = 0
    while True:
        follow_update()
        with locked():
            state = load_state()
            changed = (notifications_changed(state) or set()) | own_events_changed(state) | repo_comments_changed(state)
            if changed:
                scan(state, only=changed)
            save_state(state)
        if time.time() - last_full > 300:  # a full scan is the backstop; the repo comment feeds catch comments within ~10 s
            run_scan()
            agent_command_scan()
            follow_up_scan()
            retire_if_done()
            last_full = time.time()
        time.sleep(10)


if __name__ == '__main__':
    main()
