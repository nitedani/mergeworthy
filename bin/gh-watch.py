#!/usr/bin/env python3
"""Robust GitHub watch for the tracked threads. One line on stdout per event.

- Comments, review comments and reviews by anyone except you (GH_WATCH_ME) and bots (new or edited).
- Comments by the logins in GH_WATCH_EYES get an :eyes: reaction (held while every subscription is used up).
- Maintainers' commits pushed to a tracked PR, and 👍/👎 from GH_WATCH_EYES on the agent's comments.
- PR head/state changes (pushes, merges, closes), CI turning red or green on open PRs, and your PR's code (tests excluded) changing by more than ~80 lines since its last refactor pass (REFACTOR STALE).
- Tracker drift (tracker-check, next to this script).
State lives in gh-watch-state.json: every seen (id, updated_at) pair, so nothing is skipped or repeated,
and scans overlap by 10 minutes. A failed API call prints WATCH ERROR and that thread's scan position isn't advanced.
"""
import json, os, re, subprocess, sys, time, datetime, fcntl

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, 'gh-watch-state.json')
THREADS = os.path.join(HERE, 'threads.txt')  # one "owner/repo number" per line
ME = os.environ.get('GH_WATCH_ME') or subprocess.run(['gh', 'api', 'user', '--jq', '.login'], capture_output=True, text=True).stdout.strip()
if not ME:
    sys.exit("WATCH ERROR could not read your login (gh api user); set GH_WATCH_ME")  # else your own comments become events
ONCE = '--once' in sys.argv  # a manual check: prints events but doesn't consume them or react, so the daemon still logs them
EYES_FOR = set(filter(None, os.environ.get('GH_WATCH_EYES', '').split(',')))  # maintainers whose comments get :eyes:


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
        s.setdefault('since_by', {}); s.setdefault('stale', [])
        return s
    except Exception:
        now = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        return {'since': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'seen': {}, 'prs': {}, 'ci': {}, 'is_pr': {}, 'since_by': {}, 'stale': []}


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


def is_human(u, body=None, agent_hashes=frozenset()):
    if not u or u.get('type') == 'Bot' or u.get('login', '').endswith('[bot]'):
        return False
    if u.get('login') != ME:
        return True
    return _norm(body) not in agent_hashes  # ME: the user's own comment unless it's an agent post


def wake_agent(event):
    """The wake layer, harness-independent: launch the configured agent (command from <dir>/agent, e.g.
    `claude -p` or `codex exec`) to handle the new event from events.cursor. It is the only handler:
    a live session never acts on an event it hasn't checked against events.cursor and wake.pid (1.5),
    so the woken agent is never raced. One wake agent per dir at a time; the next event re-launches it
    once the previous one exits. Deduplication is the shared cursor: an event already handled
    (cursor past it) is skipped."""
    if ONCE:
        return
    agent = os.path.join(HERE, 'agent')
    if not os.path.exists(agent):
        # plain print, not emit: the line starts with ###, so emit would re-trigger wake_agent
        print(f"### WAKE: no agent configured for {HERE}: write the agent command (e.g. claude -p) to {agent}", flush=True)
        return
    pid_file = os.path.join(HERE, 'wake.pid')
    try:
        if int(open(pid_file).read().strip()) > 1:
            os.kill(int(open(pid_file).read().strip()), 0)
            return  # a wake agent is already running and will catch this event from events.log
    except (OSError, ValueError):
        pass
    import shlex
    cursor = os.path.join(HERE, 'events.cursor')
    prompt = f"""New GitHub watch event for this directory. Work in {HERE}.
Read {HERE}/events.log from the byte offset in {HERE}/events.cursor (from the start if it is missing).
Handle each new '###' event per methodology 1.5 (a comment by the account owner is the owner in chat: answer it
at once, every post through the gate); clear each comment line you answered in {HERE}/replies-owed.md with
'done: <reply url> <what changed>'. After each batch, re-read the rest of events.log and repeat until caught up.
Advance {HERE}/events.cursor to the end of what you handled; an event whose offset is already before the cursor is
handled: skip it."""
    log = open(os.path.join(HERE, 'wake.log'), 'a')
    proc = subprocess.Popen(shlex.split(open(agent).read().strip()) + [prompt], stdin=subprocess.DEVNULL, stdout=log,
                            stderr=subprocess.STDOUT, cwd=HERE, start_new_session=True)
    open(pid_file, 'w').write(str(proc.pid))
    if open(agent).read().strip() != 'true':  # `true`: a live session claimed the dir and handles the events itself
        open(os.path.join(HERE, 'wake.launch'), 'w').write(str(os.path.getsize(os.path.join(HERE, 'events.log'))))


def check_wake():
    """A wake agent that exits with the cursor short of where events.log ended at its launch left events unhandled
    (refused permissions, a crash, a usage limit): say so once, with no ###, so it doesn't wake a second agent
    into the same failure. The owed lines stay in replies-owed.md, where the Stop hook holds every live session."""
    launch = os.path.join(HERE, 'wake.launch')
    try:
        target = int(open(launch).read())
        os.kill(int(open(os.path.join(HERE, 'wake.pid')).read().strip()), 0)
        return  # still running
    except (OSError, ValueError):
        if not os.path.exists(launch):
            return
    try:
        cursor = int(open(os.path.join(HERE, 'events.cursor')).read().strip() or 0)
    except (OSError, ValueError):
        cursor = 0
    os.remove(launch)
    if cursor < target:
        print(f"WAKE FAILED at {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}: the agent exited at cursor {cursor} "
              f"of {target}; see {HERE}/wake.log. A live session handles the events from the cursor (1.5).", flush=True)


def append_owed(entry):
    """1.5's replies-owed.md: the daemon records each human comment as an owed reply; the agent
    clears the line with "done: <reply url> <what changed>" when it is answered. The Stop hook
    blocks a turn while a line is still owed, so an unposted reply cannot end the session unseen."""
    path = os.path.join(HERE, 'replies-owed.md')
    owed = open(path).read().splitlines() if os.path.exists(path) else []
    if any(f' {entry.split()[2]} ' in l for l in owed):
        return  # already recorded
    with open(path, 'a') as f:
        if not owed:
            f.write('# replies owed (1.5): clear each line with "done: <reply url> <what changed>"\n')
        f.write(entry + '\n')


def emit(line):
    print(line, flush=True)
    if line.startswith('###') and not ONCE:
        wake_agent(line)


def emit_dependents(key):
    # waiting-on.txt: "<owner/repo#N> -> <dependent thread>: <what to do>", one per line
    path = os.path.join(HERE, 'waiting-on.txt')
    lines = [l.strip() for l in open(path)] if os.path.exists(path) else []
    for l in lines:
        if l.split(' -> ')[0].strip() == key:
            emit(f"### DEPENDENT of merged {key}: {l.split(' -> ', 1)[1]}: do it now and post the progress on that PR (1.5)")


PROFILES = os.path.expanduser('~/.claude/profiles')  # claude-swap's accounts and limited.json


def all_limited():
    """True when every claude-swap account is used up: then no agent can reply, so the :eyes: would promise nothing."""
    try:
        names = [n for n in os.listdir(PROFILES) if os.path.exists(os.path.join(PROFILES, n, 'credentials.json'))]
        lim = json.load(open(os.path.join(PROFILES, 'limited.json')))
    except Exception:
        return False
    until = lambda v: v.get('until', 0) if isinstance(v, dict) else v + 5 * 3600
    return bool(names) and all(until(lim[n]) > time.time() for n in names if n in lim) and all(n in lim for n in names)


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
        emit(f"### MAINTAINER COMMITS {key}: {' '.join(theirs)}: review each one in a table (| Commit | What it does, and the idea behind it | Rating |, one short sentence each; rated N/10 with a short reason next to anything below 10, e.g. 9/10 (Vite's built-ins differ); an emoji only where it's funny; 10/10 only when nothing could be better), as requested (1.5)")


def emit_refactor_stale(repo, key, new):
    """Your PR changed by more than ~80 lines since its last refactor pass (`pr-steps refactor`): the ratings describe old code."""
    num = key.split('#')[1]
    try:
        pr = json.loads(gh(['api', f"repos/{repo}/pulls/{num}", '--jq', '{author: .user.login, base: .base.ref}']))
        if pr['author'] != ME: return
        shas = json.loads(gh(['api', f"repos/{repo}/compare/{pr['base']}...{new}", '--jq', '[.commits[].sha]']))
        rec = os.path.expanduser('~/.claude/pr-steps')
        last = next((s for s in reversed(shas) if os.path.exists(f'{rec}/{s}') and any(l.startswith('refactor ') for l in open(f'{rec}/{s}'))), None)
        if last == new: return
        lines = int(gh(['api', f"repos/{repo}/compare/{last or pr['base']}...{new}", '--jq', '[.files[] | select(.filename | test("\\\\.(spec|test)\\\\.|(^|/)tests?/") | not) | .additions + .deletions] | add // 0']))  # tests aren't refactored
    except Exception as e:
        emit(f"WATCH ERROR refactor check {key}: {e}")
        return
    if lines > 80:
        emit(f"### REFACTOR STALE {key}: {lines} changed lines since the last refactor pass ({last[:10] if last else 'never'}): re-run `convergence` §11.2 on the whole PR diff, then `pr-steps refactor` and replace the PR's Ratings")


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
    """A 👍 or 👎 from GH_WATCH_EYES on one of the agent's comments is feedback on that comment (methodology 1.5)."""
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
                        emit(f"### THUMBS DOWN {repo}#{num} by {who} on {c['html_url']} (reaction {r['id']}): work out why and fix the rule behind it; if the thread is still on that point, post a new reply with the fix that @-mentions {who}; if it has moved past it or it's resolved, instead edit that comment to add how you'll do better. Leave the 👎 (1.5)")
                    else:
                        emit(f"### THUMBS UP {repo}#{num} by {who} on {c['html_url']}: note what they liked and reinforce the rule that produced it (1.5)")


def react_eyes(repo, kind, cid, state):
    if all_limited():
        state.setdefault('eyes_pending', []).append([repo, kind, cid])  # flush_eyes adds it once an account is free
        return
    path = f"repos/{repo}/issues/comments/{cid}/reactions" if kind == 'comment' else f"repos/{repo}/pulls/comments/{cid}/reactions"
    try:
        gh(['api', '-X', 'POST', path, '-f', 'content=eyes'])
    except Exception as e:
        emit(f"WATCH ERROR eyes {repo} {kind} {cid}: {e}")


def flush_eyes(state):
    pending = state.pop('eyes_pending', [])
    for repo, kind, cid in pending:
        react_eyes(repo, kind, cid, state)  # re-queues itself if the limit is still on


def fetch_thread(repo, num, since, is_pr_known):
    """Network only (runs in a worker thread). Returns (is_pr, events, pr_state, red_checks)."""
    is_pr = is_pr_known
    if is_pr is None:
        is_pr = 'pull_request' in json.loads(gh(['api', f"repos/{repo}/issues/{num}"]))
    events = []
    for c in gh_json(f"repos/{repo}/issues/{num}/comments?since={since}&per_page=100"):
        events.append(('comment', c['id'], c['updated_at'], c['user'], c['html_url'], c.get('body') or '', ''))
    pr_state = red = None
    if is_pr:
        for c in gh_json(f"repos/{repo}/pulls/{num}/comments?since={since}&per_page=100"):
            events.append(('review-comment', c['id'], c['updated_at'], c['user'], c['html_url'], c.get('body') or '', f"{c.get('path')}:{c.get('line') or c.get('original_line')}"))
        for r in gh_json(f"repos/{repo}/pulls/{num}/reviews?per_page=100"):
            if (r.get('submitted_at') or '') >= since and (r.get('body') or r.get('state') in ('APPROVED', 'CHANGES_REQUESTED')):
                events.append(('review', r['id'], r['submitted_at'], r['user'], r['html_url'], r.get('body') or '', r.get('state')))
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
                    if prev.get('head') != pr_state['head']:
                        emit_maintainer_commits(repo, key, prev['head'], pr_state['head'])
                        emit_refactor_stale(repo, key, pr_state['head'])
                state['prs'][key] = pr_state
            if red is not None:
                if red != state['ci'].get(key, []):
                    emit(f"### CI {key}: red={red}: fix it, or if it is not this PR's doing, say why on the PR now with the evidence (1.5)" if red else f"### CI {key}: no longer red")
                state['ci'][key] = red
            agent_hashes = agent_post_hashes()  # read after the fetch: a post gated while it ran is the agent's
            for kind, cid, upd, user, url, body, extra in events:
                if not is_human(user, body, agent_hashes):
                    continue
                sk = f"{kind}:{cid}"
                if state['seen'].get(sk) == upd:
                    continue
                edited = sk in state['seen']
                state['seen'][sk] = upd
                emit(f"### {key} {kind}{' (edited)' if edited else ''} {cid} by {user['login']} {upd} {extra} {url}\n{body}\n")
                if not edited and kind in ('comment', 'review-comment'):
                    append_owed(f"{key} {kind} {cid} by {user['login']} {url} — {body.strip().splitlines()[0][:80]}" if body.strip() else f"{key} {kind} {cid} by {user['login']} {url}")
                if re.fullmatch(r"\W*(ok(ay)?|good|great|lgtm|yes|sure|agreed|sounds good|👍|nice)\W*", body.strip().lower()):
                    emit(f"### ACK {key} {cid}: an acknowledgement answers your last open proposal in that thread or PR; apply it now (1.5)")
                if user['login'] in EYES_FOR and not edited and not ONCE and kind in ('comment', 'review-comment'):
                    react_eyes(repo, kind, cid, state)
    if only is None:
        state['since'] = started  # only the default for threads added to threads.txt later
    return ok


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
        scan_reactions(state, read_threads())
        save_state(state)
    r = subprocess.run(['bash', os.path.join(os.path.dirname(os.path.realpath(__file__)), 'tracker-check')], capture_output=True, text=True)
    stale = [l for l in r.stdout.splitlines() if 'STALE' in l]
    with locked():
        state = load_state()
        for l in stale:
            if l not in state['stale']:  # report each drift once, not every scan
                emit(l)
        state['stale'] = stale
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
    # plain print, not emit: a ### line would wake the agent
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


def main():
    if ONCE:
        run_scan()
        return
    last_full = 0
    while True:
        with locked():
            state = load_state()
            changed = (notifications_changed(state) or set()) | own_events_changed(state)
            if changed:
                scan(state, only=changed)
            if state.get('eyes_pending'):
                flush_eyes(state)
            save_state(state)
        if time.time() - last_full > 180:
            run_scan()
            check_wake()
            retire_if_done()
            last_full = time.time()
        time.sleep(10)


if __name__ == '__main__':
    main()
