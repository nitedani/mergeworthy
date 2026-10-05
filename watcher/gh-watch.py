#!/usr/bin/env python3
"""Robust GitHub watch for the tracked threads. One line on stdout per event.

- The comments the agent answers (mergeworthy:github-threads), new or edited, each with an :eyes: reaction: a maintainer's
  (write access) on a thread in threads.txt, the threads the agent opened or posted in; and yours with /ai or /agent, on any thread
  (your events feed; one watch dir gets each, see main_dir). Nothing else.
- Maintainers' commits pushed to a tracked PR, and 👍/👎 from GH_WATCH_EYES on the agent's comments.
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


def answerable(u, body, agent_hashes):
    """mergeworthy:github-threads, for a thread the agent opened or posted in: a maintainer's comment or the user's.
    The user's /ai calls on other threads go through ai_call_elsewhere."""
    if not is_human(u, body, agent_hashes):
        return False
    return u.get('login') == ME or u.get('assoc') in MAINTAINER


def is_human(u, body=None, agent_hashes=frozenset()):
    if not u or u.get('type') == 'Bot' or u.get('login', '').endswith('[bot]'):
        return False
    if u.get('login') != ME:
        return True
    return _norm(body) not in agent_hashes  # ME: the user's own comment unless it's an agent post


def append_owed(entry):
    """replies-owed.md (mergeworthy:github-threads): the daemon records each human comment as an owed reply; the session
    clears the line with "done: <reply url> <what changed>" when it is answered. The Stop hook
    blocks a turn while a line is still owed, so an unposted reply cannot end the session unseen."""
    path = os.path.join(HERE, 'replies-owed.md')
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
    emit(f"### {key} {kind}{' (edited)' if edited else ''} {cid} by {login} {upd} {extra} {url}\n{body}\n")
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


def emit_dependents(key):
    # waiting-on.txt: "<owner/repo#N> -> <dependent thread>: <what to do>", one per line
    path = os.path.join(HERE, 'waiting-on.txt')
    lines = [l.strip() for l in open(path)] if os.path.exists(path) else []
    for l in lines:
        if l.split(' -> ')[0].strip() == key:
            emit(f"### DEPENDENT of merged {key}: {l.split(' -> ', 1)[1]}: do it now and post the progress on that PR (mergeworthy:github-threads)")


def emit_tracker_stale(key, ended):
    """umbrella.txt ("owner/repo N"): the program's umbrella issue (methodology 1.2). When a PR merges or closes, its
    checkbox there must be ticked and say how it ended; a tracker updated "in the same step" from memory went stale for days."""
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
    elif not any(l.lstrip().startswith('- [x]') and re.search(rf'{num}(~~)? \((merged|closed|released)', l) for l in items):
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


def fetch_thread(repo, num, since, is_pr_known):
    """Network only (runs in a worker thread). Returns (is_pr, events, pr_state, red_checks)."""
    is_pr = is_pr_known
    if is_pr is None:
        is_pr = 'pull_request' in json.loads(gh(['api', f"repos/{repo}/issues/{num}"]))
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
    return is_pr, events, pr_state, red


def scan(state, only=None):
    """Scan all tracked threads (or only the given keys) in parallel; apply results in this thread."""
    from concurrent.futures import ThreadPoolExecutor
    def since(key):  # each thread keeps its own position, so one failing thread doesn't hold back the others
        dt = datetime.datetime.strptime(state['since_by'].get(key, state['since']), '%Y-%m-%dT%H:%M:%SZ') - datetime.timedelta(minutes=10)
        return dt.strftime('%Y-%m-%dT%H:%M:%SZ')
    started = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    threads = read_threads()
    if only is not None:
        threads = [t for t in threads if f"{t[0]}#{t[1]}" in only]
    else:
        threads = scan_set(state, threads)
    ok = True
    with ThreadPoolExecutor(max_workers=8) as ex:
        futs = {ex.submit(fetch_thread, repo, num, since(f"{repo}#{num}"), state['is_pr'].get(f"{repo}#{num}")): (repo, num) for repo, num in threads}
        for fut, (repo, num) in futs.items():
            key = f"{repo}#{num}"
            try:
                is_pr, events, pr_state, red = fut.result()
            except Exception as e:
                ok = False
                emit(f"WATCH ERROR {key}: {e}")
                continue
            state['is_pr'][key] = is_pr
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
                if answerable(user, body, agent_hashes):
                    handle_comment(state, repo, key, kind, cid, upd, user['login'], url, body, extra)
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


# kept across rounds: a new TLS connection per request made a round of ~22 polls take ~7 s instead of ~2
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


def ai_call_elsewhere(state, repo, num, etype, c):
    """Your /ai or /agent comment on a thread no live watcher watches goes to main_dir's watcher, so one session gets it."""
    key, body = f"{repo}#{num}", c.get('body') or ''
    if not c.get('id') or not AI_CALL.search(body) or _norm(body) in agent_post_hashes() or main_dir() != HERE:
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


def locked():
    """One scan at a time across processes (daemon and manual runs), so state updates aren't lost."""
    f = open(STATE + '.lock', 'w')
    fcntl.flock(f, fcntl.LOCK_EX)
    return f


def run_scan():
    with locked():
        state = load_state()
        scan(state)
        save_state(state)
    with locked():
        state = load_state()
        scan_reactions(state, scan_set(state, read_threads()))
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
        prs = load_state()['prs']
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
    script on the new code. Without it a watcher ran the version it started on until someone restarted it."""
    root = installed_root()
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
            retire_if_done()
            last_full = time.time()
        time.sleep(10)


if __name__ == '__main__':
    main()
