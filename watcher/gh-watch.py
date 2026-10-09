#!/usr/bin/env python3
"""Robust GitHub watch for the tracked threads. One line on stdout per event.

- The comments the agent answers (mergeworthy:github-threads), new or edited, each with an :eyes: reaction: a maintainer's
  (write access) on a thread in threads.txt, the threads the agent opened or posted in; and yours with /ai or /agent, on any thread
  (your events feed; one watch dir gets each, see main_dir). Nothing else.
- Your "/agent ..." comments on threads no watch dir lists, found in the watched repos' recent comments (search as a backup) and sent to one dir (see agent_command): `### AGENT COMMAND`.
- FOLLOW-UP: later commits by others to the lines of your merged PRs, and PRs that reference them (see follow_ups), for 60 days after the merge.
- Machine-wide work (those two) runs in one daemon at a time (shared_pass). Every call goes through request(), which keeps the
  hour's budget (see "The GitHub API budget") and sends ETags; a rate-limit pause prints one WATCH ERROR per daemon.
- Maintainers' commits pushed to a tracked PR, and 👍/👎 from GH_WATCH_EYES on the agent's comments.
- WAIT PING DUE: your account's comment is the last on an open thread and has had no reply for WAIT_PING_HOURS (3).
- PR head/state changes (pushes, merges, closes), CI turning red or green on open PRs, and your PR's code (tests excluded) changing by more than ~80 lines since its last refactor pass (REFACTOR STALE).
State lives in gh-watch-state.json: every seen (id, updated_at) pair, so nothing is skipped or repeated,
and scans overlap by 10 minutes. A failed API call prints WATCH ERROR and that thread's scan position isn't advanced.
"""
import contextlib, datetime, fcntl, hashlib, http.client, json, os, re, subprocess, sys, threading, time, urllib.parse
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
STATE = os.path.join(HERE, 'gh-watch-state.json')
THREADS = os.path.join(HERE, 'threads.txt')  # one "owner/repo number" per line
ONCE = '--once' in sys.argv  # a manual check: prints events but doesn't consume them or react, so the daemon still logs them
WAIT_PING_HOURS = float(os.environ.get('WAIT_PING_HOURS') or 3)  # mergeworthy:github-threads: a wait ping may follow after this long
EYES_FOR = set(filter(None, os.environ.get('GH_WATCH_EYES', '').split(',')))  # maintainers: their commits on your PRs and 👍/👎 are reported


# ---------- The GitHub API budget ----------
# Every watcher on the machine shares one account's 5,000 calls an hour. All of them go through request() below, and what
# is machine-wide lives in ~/.mergeworthy/shared-watch.json: the rate limit as GitHub last reported it, the pause after a
# rate-limit answer, when each shared job last ran, the follow-up cursors and the commit details already read.
# Machine-wide jobs (shared_pass) run in one daemon at a time, the one holding the lease.

class Budget(Exception):
    """The machine-wide pause is on, or a rate-limit answer just started it. Not reported per call (see announce_pause)."""


class PassSpent(Exception):
    """A shared job used its calls for this pass (PASS_CALLS); it carries over to the next one."""


OK, RESERVE, LOW, PAUSED = range(4)  # level(): how much budget is left
RESERVE_AT, LOW_AT = 1500, 500  # remaining calls: below RESERVE_AT only the daemons' own threads are scanned; below LOW_AT only the notifications fast path
PASS_CALLS, STABLE = 40, 86400  # calls one shared job may make per pass; seconds a polled URL's `since` stays the same, so its ETag still matches
_pass = {'left': None}


def shared_path(name='shared-watch.json'):
    return os.path.expanduser('~/.mergeworthy/' + name)


def shared_default():
    return {'rate': {}, 'pause_until': 0, 'jobs': {}, 'etags': {}, 'commits': {}, 'followups': {}, 'backlog': {}, 'agent_since': None, 'me': None}


_read, _once_state = {}, {}


def shared_read():
    """The shared state, read without the lock: every write replaces the file whole, so a read sees one version. Don't mutate."""
    if ONCE and _once_state:
        return _once_state
    try:
        st = os.stat(shared_path())
        if _read.get('key') != (st.st_mtime_ns, st.st_size):
            with open(shared_path()) as f:
                _read.update(key=(st.st_mtime_ns, st.st_size), val={**shared_default(), **json.load(f)})
        return _read['val']
    except (OSError, ValueError):
        return shared_default()


def shared_update(fn):
    """Read-modify-write the shared state under its lock, written atomically. A manual --once run changes memory only."""
    if ONCE:
        if not _once_state:
            _once_state.update(json.loads(json.dumps(shared_read())))
        fn(_once_state)
        return
    os.makedirs(os.path.dirname(shared_path()), exist_ok=True)
    with open(shared_path('shared-watch.json.lock'), 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            with open(shared_path()) as f:
                s = {**shared_default(), **json.load(f)}
        except (OSError, ValueError):
            s = shared_default()
        fn(s)
        prune(s['etags'])
        tmp = shared_path() + '.tmp'
        with open(tmp, 'w') as f:
            json.dump(s, f)
        os.replace(tmp, shared_path())


@contextlib.contextmanager
def lease():
    """The machine-wide runner: the daemon holding this lock for a pass runs the shared jobs for every live watch dir; one that
    doesn't get it skips them (it never waits). The kernel drops the lock if the holder dies."""
    os.makedirs(os.path.dirname(shared_path()), exist_ok=True)
    f = open(shared_path('shared-watch.lease'), 'a')
    try:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError:
            yield False
            return
        yield True
    finally:
        f.close()


def level():
    """OK, RESERVE (below RESERVE_AT calls left), LOW (below LOW_AT) or PAUSED, from the rate limits any daemon last saw."""
    s, now, lvl = shared_read(), time.time(), OK
    if s['pause_until'] > now:
        return PAUSED
    for r in s['rate'].values():
        if r['reset'] > now:
            lvl = max(lvl, LOW if r['remaining'] < LOW_AT else RESERVE if r['remaining'] < RESERVE_AT else OK)
    return lvl


_noted = {}


def note_rate(h):
    """Record GitHub's x-ratelimit headers (core and graphql) in the shared state. A write every call would be a lock per
    call, so a change under 25 calls is skipped while the budget is healthy."""
    res = h.get('x-ratelimit-resource')
    if res not in ('core', 'graphql') or 'x-ratelimit-remaining' not in h:
        return
    left, reset = int(h['x-ratelimit-remaining']), int(h['x-ratelimit-reset'])
    last = _noted.get(res)
    if last and last[1] == reset and abs(last[0] - left) < 25 and left >= RESERVE_AT + 100:
        return
    def put(s):
        cur = s['rate'].get(res)
        if not cur or reset > cur['reset'] or (reset == cur['reset'] and left < cur['remaining']):
            s['rate'][res] = {'remaining': left, 'reset': reset}
    shared_update(put)
    _noted[res] = (left, reset)


def pause_until(t):
    shared_update(lambda s: s.__setitem__('pause_until', max(s['pause_until'], t)))


def iso(t):
    return datetime.datetime.fromtimestamp(t, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def iso_epoch(t):
    return datetime.datetime.strptime(t, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=datetime.timezone.utc).timestamp()


def announce_pause(state):
    """One `WATCH ERROR` per pause per daemon, however many calls it stopped."""
    until = shared_read()['pause_until']
    if until > time.time() and state.get('pause_notified') != until:
        state['pause_notified'] = until
        emit(f"WATCH ERROR API budget: paused until {iso(until)}")


def prune(etags, keep=2 * 86400):
    for k in [k for k, v in etags.items() if v['t'] < time.time() - keep]:
        del etags[k]


class Resp:
    def __init__(self, status, headers, body):
        self.status, self.headers, self.body = status, headers, body

    def json(self):
        return json.loads(self.body)

    def next(self):
        m = re.search(r'<([^>]+)>;\s*rel="next"', self.headers.get('link', ''))
        return m and m[1].split('api.github.com/', 1)[-1]


_token, _conn = [None], threading.local()  # kept across calls: a new TLS connection per request makes a round several times slower


def http_get(path, headers):
    """A GET over a kept-alive connection (a `gh` process per poll costs ~50 ms of CPU, and the feeds are polled every 10 s)."""
    for attempt in (0, 1):
        if not _token[0]:
            _token[0] = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True).stdout.strip()
        h = {'Authorization': f'Bearer {_token[0]}', 'User-Agent': 'gh-watch', 'Accept': 'application/vnd.github+json', **headers}
        try:
            _conn.c = getattr(_conn, 'c', None) or http.client.HTTPSConnection('api.github.com', timeout=20)
            _conn.c.request('GET', '/' + path, headers=h)
            r = _conn.c.getresponse()
            resp = Resp(r.status, {k.lower(): v for k, v in r.getheaders()}, r.read().decode('utf-8', 'replace'))
        except (http.client.HTTPException, OSError):  # a dropped keep-alive connection: reconnect once
            _conn.c = None
            if attempt:
                raise
            continue
        if resp.status == 401 and not attempt:  # `gh auth login` replaced the token this process had read
            _token[0] = None
            continue
        return resp


def gh_send(method, path, headers, args):
    """`gh api -i`: the status line and headers come first. gh exits 1 on a 304 or an error status and still prints them."""
    argv = ['gh', 'api', '-i', '-X', method] + [x for k, v in headers.items() for x in ('-H', f'{k}: {v}')] + list(args) + [path]
    r = subprocess.run(argv, capture_output=True, text=True)
    if not r.stdout.startswith('HTTP/'):
        raise RuntimeError(f"gh api {path}: {r.stderr.strip()[:200]}")
    head, _, body = r.stdout.partition('\r\n\r\n') if '\r\n\r\n' in r.stdout else r.stdout.partition('\n\n')
    lines = head.splitlines()
    return Resp(int(lines[0].split()[1]), {k.strip().lower(): v.strip() for k, _, v in (l.partition(':') for l in lines[1:])}, body)


def limit_pause(resp):
    """-> when a rate-limit answer (429, or 403 naming a limit) lets calls resume, else None."""
    h = resp.headers
    if resp.status not in (403, 429) or not (resp.status == 429 or h.get('x-ratelimit-remaining') == '0' or 'retry-after' in h or 'rate limit' in resp.body.lower()):
        return None
    if 'retry-after' in h:
        return time.time() + int(h['retry-after'])
    return int(h['x-ratelimit-reset']) if h.get('x-ratelimit-remaining') == '0' else time.time() + 60


def spend():
    if _pass['left'] is not None:
        if _pass['left'] <= 0:
            raise PassSpent()
        _pass['left'] -= 1


def request(path, method='GET', args=(), store=None, pending=None, fresh=False, newest_first=False):
    """The one place the watcher calls GitHub: pause check, rate-limit bookkeeping, conditional requests.
    - store: a dict of validators by path. A request sends If-None-Match for its path; a 304 (not counted against the limit)
      comes back as status 304 with no body, for the caller to read as "nothing new since I last read it".
      The new validators go to `pending` if given (the caller commits them once it has used the answer), else straight to store.
      A first page with more pages after it is cached only if the list is newest first: otherwise a change on a later page hides.
    - fresh: send no validators (the caller can't use a 304, e.g. a new PR it has never read).
    - GETs go over the kept-alive connection; the rest through `gh api -i`."""
    if shared_read()['pause_until'] > time.time():
        raise Budget('paused')
    spend()
    seen = store.get(path) if store is not None and not fresh else None
    headers = {'If-None-Match': seen['e']} if seen and seen.get('e') else {'If-Modified-Since': seen['lm']} if seen and seen.get('lm') else {}
    if method == 'GET' and not os.environ.get('GH_HOST'):
        resp = http_get(path, headers)
    else:
        resp = gh_send(method, path, headers, args)
    note_rate(resp.headers)
    until = limit_pause(resp)
    if until:
        pause_until(until)
        raise Budget(f"rate limited until {iso(until)}")
    if resp.status == 304:
        if _pass['left'] is not None:
            _pass['left'] += 1  # a 304 isn't a call against the limit, so it doesn't use up the pass either
        return resp
    if resp.status >= 400:
        raise RuntimeError(f"gh api {path}: HTTP {resp.status} {resp.body.strip()[:150]}")
    if store is not None and (resp.headers.get('etag') or resp.headers.get('last-modified')) and (newest_first or not resp.next()):
        (store if pending is None else pending)[path] = {'e': resp.headers.get('etag'), 'lm': resp.headers.get('last-modified'), 't': time.time()}
    return resp


def paged(path, store=None, pending=None, fresh=False, newest_first=False, until=None):
    """Every item of a list. -> [] on a 304. `until(page)`: stop once a page of a newest-first list reaches what was already read."""
    resp = request(path, store=store, pending=pending, fresh=fresh, newest_first=newest_first)
    items = []
    while resp.status != 304:
        page = resp.json()
        items.extend(page if isinstance(page, list) else [page])
        if not resp.next() or (until and page and until(page)):
            break
        resp = request(resp.next())
    return items


def run_gh(argv):
    """A gh command that isn't `gh api` (`gh pr checks` is GraphQL and shows no headers), under the same pause and pass limits."""
    if shared_read()['pause_until'] > time.time():
        raise Budget('paused')
    spend()
    r = subprocess.run(['gh'] + argv, capture_output=True, text=True)
    if r.returncode and 'rate limit' in r.stderr.lower():
        pause_until(time.time() + 600)
        raise Budget('rate limited')
    return r


def fail(what, e):
    """`WATCH ERROR` for a failed call, except when the pause stopped it: that is announced once (announce_pause)."""
    if not isinstance(e, Budget):
        emit(f"WATCH ERROR {what}: {e}")


def stable_since(since):
    """A polled URL must stay the same for its ETag to match, so `since` is rounded down to the start of its day. The
    answer holds a little more than was asked for; seen/claims drop what was handled."""
    return iso(iso_epoch(since) // STABLE * STABLE)


def login():
    if os.environ.get('GH_WATCH_ME'):
        return os.environ['GH_WATCH_ME']
    token = subprocess.run(['gh', 'auth', 'token'], capture_output=True, text=True).stdout.strip()
    fp, cached = hashlib.sha256(token.encode()).hexdigest()[:12], shared_read()['me'] or {}
    if cached.get('token') == fp:  # read once per account, not on every restart
        return cached['login']
    try:
        name = request('user').json().get('login') or ''
    except Exception:
        return ''
    shared_update(lambda s: s.__setitem__('me', {'token': fp, 'login': name}))
    return name


ME = login()
if not ME:
    sys.exit("WATCH ERROR could not read your login (gh api user); set GH_WATCH_ME")  # else your own comments become events


def load_state():
    try:
        s = json.load(open(STATE))
        s.setdefault('since_by', {})
        s.setdefault('etag', {})
        return s
    except Exception:
        now = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=1)
        return {'since': now.strftime('%Y-%m-%dT%H:%M:%SZ'), 'seen': {}, 'prs': {}, 'ci': {}, 'is_pr': {}, 'since_by': {}, 'etag': {}}


def save_state(s):
    if ONCE:
        return
    prune(s.setdefault('etag', {}))
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
        body = request(f"repos/{w[0]}/issues/{w[1]}").json()['body'] or ''
    except Exception as e:
        fail(f"tracker check {key}", e)
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
        commits = [{'sha': c['sha'][:10], 'login': (c.get('author') or {}).get('login') or ''} for c in request(f"repos/{repo}/compare/{old}...{new}").json()['commits']]
    except Exception as e:
        fail(f"compare {key} {old}...{new}", e)
        return
    try:  # commits that came from merging the base branch aren't the PR's
        base = request(f"repos/{repo}/pulls/{key.split('#')[1]}").json()['base']['ref']
        on_pr = {c['sha'][:10] for c in request(f"repos/{repo}/compare/{base}...{new}").json()['commits']}
    except Exception as e:
        fail(f"compare {key} base...{new}", e)
        return
    theirs = [c['sha'] for c in commits if c['login'] in EYES_FOR and c['login'] != ME and c['sha'] in on_pr]
    if theirs:
        emit(f"### MAINTAINER COMMITS {key}: {' '.join(theirs)}: review each one in a table (| Commit | What it does, and the idea behind it | Rating |, one short sentence each; rated N/10 with a short reason next to anything below 10, e.g. 9/10 (Vite's built-ins differ); an emoji only where it's funny; 10/10 only when nothing could be better), as requested (mergeworthy:github-threads)")


def emit_refactor_stale(repo, key, new):
    """Your PR's own commits changed more than ~80 lines since its last refactor pass (`pr-steps refactor`): the ratings
    describe old code. Merges of the base branch, tests and lockfiles don't count: they aren't the PR's code to rate."""
    num = key.split('#')[1]
    try:
        pr = request(f"repos/{repo}/pulls/{num}").json()
        if pr['user']['login'] != ME: return
        commits = [{'sha': c['sha'], 'merge': len(c['parents']) > 1} for c in request(f"repos/{repo}/compare/{pr['base']['ref']}...{new}").json()['commits']]
        rec = os.path.expanduser('~/.claude/pr-steps')
        idx = max((i for i, c in enumerate(commits) if os.path.exists(f"{rec}/{c['sha']}") and any(l.startswith('refactor ') for l in open(f"{rec}/{c['sha']}"))), default=-1)
        since = [c['sha'] for c in commits[idx + 1:] if not c['merge']]
        skip = re.compile(r'\.(spec|test)\.|(^|/)tests?/|(^|/)(pnpm-lock\.yaml|package-lock\.json|yarn\.lock)$')
        lines = sum(f['additions'] + f['deletions'] for sha in since for f in (request(f"repos/{repo}/commits/{sha}").json().get('files') or []) if not skip.search(f['filename']))
    except Exception as e:
        fail(f"refactor check {key}", e)
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
    seen, etags = state.setdefault('reactions', {}), state['etag']  # seen: "<kind>:<id>" -> ["<login>:<content>", ...]
    for repo, num in threads:
        pending, clean = {}, True  # an answer's ETag is kept only once everything in it was handled: a 304 later means "nothing new"
        for kind, path in (('body', 'issues'), ('comment', 'issues'), ('review-comment', 'pulls')):
            try:
                if kind == 'body':  # the PR or issue description itself
                    comments = paged(f"repos/{repo}/issues/{num}", etags, pending)
                else:
                    comments = paged(f"repos/{repo}/{path}/{num}/comments?per_page=100", etags, pending)
            except Exception as e:
                if path == 'issues':
                    clean = False
                    fail(f"reactions {repo}#{num}", e)
                continue  # an issue has no review comments
            for c in comments:
                counts = c.get('reactions') or {}
                if c['user'].get('login') != ME or _norm(c.get('body')) not in agent_hashes or not (counts.get('+1') or counts.get('-1')):
                    continue
                sk = f"{kind}:{c['id']}"
                try:
                    url = f"repos/{repo}/issues/{num}/reactions" if kind == 'body' else f"repos/{repo}/{path}/comments/{c['id']}/reactions"
                    reactions = paged(f"{url}?per_page=100", etags, pending)
                except Exception as e:
                    clean = False
                    fail(f"reactions {sk}", e)
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
        if clean:
            etags.update(pending)


def react_eyes(repo, kind, cid):
    path = f"repos/{repo}/issues/comments/{cid}/reactions" if kind == 'comment' else f"repos/{repo}/pulls/comments/{cid}/reactions"
    try:
        request(path, 'POST', ['-f', 'content=eyes'])
    except Exception as e:
        fail(f"eyes {repo} {kind} {cid}", e)


def fetch_thread(repo, num, since, is_pr_known, author_known, prev_pr, etags):
    """Network only (runs in a worker thread). Returns (is_pr, author, events, pr_state, red_checks, last_comment, validators):
    validators are the ETags to keep once the caller has used the answers. A list that answers 304 has nothing new
    (comments, reviews), and an unchanged PR keeps its previous state."""
    is_pr, author, pending = is_pr_known, author_known, {}
    if is_pr is None or author is None:
        issue = request(f"repos/{repo}/issues/{num}").json()
        is_pr, author = 'pull_request' in issue, (issue.get('user') or {}).get('login')
    events = []
    for c in paged(f"repos/{repo}/issues/{num}/comments?since={stable_since(since)}&per_page=100", etags, pending):
        events.append(('comment', c['id'], c['updated_at'], {**c['user'], 'assoc': c.get('author_association')}, c['html_url'], c.get('body') or '', ''))
    pr_state = red = None
    if is_pr:
        for c in paged(f"repos/{repo}/pulls/{num}/comments?since={stable_since(since)}&per_page=100", etags, pending):
            events.append(('review-comment', c['id'], c['updated_at'], {**c['user'], 'assoc': c.get('author_association')}, c['html_url'], c.get('body') or '', f"{c.get('path')}:{c.get('line') or c.get('original_line')}"))
        for r in paged(f"repos/{repo}/pulls/{num}/reviews?per_page=100", etags, pending):
            if (r.get('submitted_at') or '') >= since and (r.get('body') or r.get('state') in ('APPROVED', 'CHANGES_REQUESTED')):
                events.append(('review', r['id'], r['submitted_at'], {**r['user'], 'assoc': r.get('author_association')}, r['html_url'], r.get('body') or '', r.get('state')))
        resp = request(f"repos/{repo}/pulls/{num}", store=etags, pending=pending, fresh=not prev_pr)
        if resp.status == 304:
            pr_state = prev_pr
        else:
            pr = resp.json()
            # 'conflict': GitHub runs no CI on a PR that conflicts with its base, so a conflict must be reported like red CI
            pr_state = {'head': pr['head']['sha'][:10], 'state': 'merged' if pr.get('merged') else pr['state'], 'conflict': pr.get('mergeable_state') == 'dirty'}
        if pr_state['state'] == 'open':
            r = run_gh(['pr', 'checks', num, '-R', repo])
            if r.returncode not in (0, 1, 8) and 'no checks reported' not in r.stderr:  # 1 = some failed, 8 = some pending
                raise RuntimeError(f"gh pr checks {num} -R {repo}: {r.stderr.strip()[:200]}")
            checks = r.stdout
            red = sorted(l.split('\t')[0] for l in checks.splitlines() if '\tfail\t' in l)
    return is_pr, author, events, pr_state, red, fetch_last_comment(repo, num), pending


_F = 'state comments(last:1){nodes{databaseId url createdAt author{login}}}'
LAST_COMMENT = ('query($o:String!,$r:String!,$n:Int!){repository(owner:$o,name:$r){issueOrPullRequest(number:$n){'
                '... on Issue{F} ... on PullRequest{F}}}}').replace('F', _F)


def fetch_last_comment(repo, num):
    """The thread's latest issue or PR conversation comment and whether the thread is open: one GraphQL call."""
    o, r = repo.split('/')
    t = request('graphql', 'POST', ['-f', f'query={LAST_COMMENT}', '-f', f'o={o}', '-f', f'r={r}', '-F', f'n={num}']).json()['data']['repository']['issueOrPullRequest']
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
        futs = {ex.submit(fetch_thread, repo, num, since(f"{repo}#{num}"), state['is_pr'].get(f"{repo}#{num}"), state.setdefault('author', {}).get(f"{repo}#{num}"), state['prs'].get(f"{repo}#{num}"), state['etag']): (repo, num) for repo, num in threads}
        for fut, (repo, num) in futs.items():
            key = f"{repo}#{num}"
            try:
                is_pr, author, events, pr_state, red, last, validators = fut.result()
            except Exception as e:
                ok = False
                fail(key, e)
                continue
            state['etag'].update(validators)
            state['is_pr'][key] = is_pr
            state['author'][key] = author
            if last:
                state.setdefault('open', {})[key] = last['open']
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
    try:
        resp = request('notifications?all=true&per_page=50', store=state['etag'])
    except Budget:
        raise
    except Exception:
        return None
    if resp.status == 304:
        return None
    body = resp.body
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


_pool = ThreadPoolExecutor(8)


def repo_comments_changed(state):
    """The notifications fast path lags GitHub by 20-30 s. Each watched repo's newest issue and review comments, polled
    with If-None-Match (a 304 isn't rate-limited), catch a comment within one loop. Returns the changed thread keys."""
    threads = read_threads()
    watched = {f"{r}#{n}" for r, n in threads}
    seen = state.setdefault('rc_seen', {})
    def poll(url):
        try:
            resp = request(url, store=state['etag'])
            return url, resp.body if resp.status == 200 else None
        except Budget:
            raise
        except Exception:  # a failed poll: the next round tries again
            return url, None
    urls = [f"repos/{r}/{k}/comments?sort=created&direction=desc&per_page=20" for r in sorted({r for r, _ in threads}) for k in ('issues', 'pulls')]
    keys = set()
    for url, body in _pool.map(poll, urls):
        if body is None:
            continue
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
    read(request(f"repos/{repo}/issues/{num}").json().get('body'))
    for e in paged(f"repos/{repo}/issues/{num}/timeline?per_page=100"):
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


def discover_agent_commands():
    """Your /agent comments on threads no watcher lists reach no one: you comment as the agent's own account, which GitHub
    doesn't notify you of, and the search and events indexes lag by many minutes. So each pass lists the recent issue
    and review comments of every watched repo (the comments feeds are live) and hands each /agent comment to agent_command.
    A search of the threads you commented on, minus those repos, backs it up for repos no one lists. A feed is read with its
    ETag, newest first, only back to where the last pass stopped. A failed call leaves the position, so it is retried."""
    started = iso(time.time())
    cursor = shared_read()['agent_since'] or iso(time.time() - 3600)
    since = iso(iso_epoch(cursor) - 600)  # passes overlap by 10 minutes
    day = stable_since(since)
    etags, ok = shared_read()['etags'], True
    old = lambda page: page[-1].get('updated_at', '') < since
    repos = watched_repos()
    for repo in sorted(repos):
        pending = {}
        try:
            for kind, path in (('comment', 'issues'), ('review-comment', 'pulls')):
                for c in paged(f"repos/{repo}/{path}/comments?since={day}&sort=updated&direction=desc&per_page=100", etags, pending, newest_first=True, until=old):
                    agent_command(repo, (c.get('issue_url') or c.get('pull_request_url') or '').rsplit('/', 1)[-1], kind, c)
            keep_etags(pending)
        except (Budget, PassSpent):
            raise
        except Exception as e:
            ok = False
            fail(f"agent commands {repo}", e)
    try:
        pending = {}
        query = urllib.parse.quote(f'commenter:{ME} updated:>={day}', safe='')
        found = request(f"search/issues?q={query}&sort=updated&order=desc&per_page=50", store=etags, pending=pending, newest_first=True)
        for i in ([] if found.status == 304 else found.json()['items']):
            repo, num = i['repository_url'].split('/repos/')[-1], i['number']
            if repo in repos:
                continue
            try:
                found = [('comment', c) for c in paged(f"repos/{repo}/issues/{num}/comments?since={day}&per_page=100", etags, pending)]
                if 'pull_request' in i:
                    found += [('review-comment', c) for c in paged(f"repos/{repo}/pulls/{num}/comments?since={day}&per_page=100", etags, pending)]
                for kind, c in found:
                    agent_command(repo, num, kind, c)
            except (Budget, PassSpent):
                raise
            except Exception as e:
                ok = False
                fail(f"agent commands {repo}#{num}", e)
        if ok:
            keep_etags(pending)
    except (Budget, PassSpent):
        raise
    except Exception as e:
        ok = False
        fail("agent command search", e)
    if ok:
        shared_update(lambda s: s.__setitem__('agent_since', started))


def keep_etags(pending):
    shared_update(lambda s: s['etags'].update(pending))


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
    try:
        resp = request(f'users/{ME}/events?per_page=30', store=state['etag'])
    except Budget:
        raise
    except Exception:
        return set()
    if resp.status == 304:
        return set()
    body = resp.body
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


FOLLOWUP_DAYS, SLACK = 60, 3  # how long a merged PR is followed; lines of slack around its lines
LOCKFILES = ('pnpm-lock.yaml', 'package-lock.json', 'yarn.lock')
# a package.json line that only gives a dependency (or the package) a version; in a lockfile, semver numbers and integrity hashes
DEP_LINE = re.compile(r'^\s*"([^"]+)":\s*"(?:[\^~<>=v ]*\d[^"]*|\*|latest|(?:workspace|npm|catalog|link|file):[^"]*)"(,?)\s*$')
SEMVER = re.compile(r'\d+\.\d+\.\d+[\w.+-]*|(?:sha\d+|md5)-[\w+/=]+|\b[0-9a-f]{40}\b')


def version_only(base, lines):
    """A hunk of package.json or a lockfile whose removed lines equal its added lines once versions are blanked: a dependency
    bump, which says nothing about your PR's lines (the dependency PRs of the repo are the noise in a follow-up report)."""
    if base != 'package.json' and base not in LOCKFILES:
        return False
    def norm(l):
        m = DEP_LINE.match(l[1:])
        return f'"{m[1]}"{m[2]}' if m else SEMVER.sub('V', l[1:]).strip()
    return sorted(norm(l) for l in lines if l[0] == '-') == sorted(norm(l) for l in lines if l[0] == '+')


def patch_lines(patch, path=''):
    """-> (old-side, new-side) line numbers a unified-diff patch changes; a pure insertion or deletion counts at its position.
    Hunks that only bump dependency versions (version_only) are left out."""
    old, new = [], []
    for hunk in re.split(r'(?m)^(?=@@)', patch or ''):
        lines = hunk.splitlines()
        if not lines or not lines[0].startswith('@@') or version_only(path.rsplit('/', 1)[-1], [l for l in lines[1:] if l[:1] in ('+', '-')]):
            continue
        m = re.match(r'@@ -(\d+)(?:,\d+)? \+(\d+)', lines[0])
        o, n = int(m[1]), int(m[2])
        for l in lines[1:]:
            if l.startswith('-'):
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


def follow_record(key):
    """A merged PR of yours: its merge commit and the lines it changed, to compare later commits against."""
    repo, num = key.rsplit('#', 1)
    pr = request(f"repos/{repo}/pulls/{num}").json()
    files = {f['filename']: spans(patch_lines(f['patch'])[1]) if f.get('patch') else [[1, 10**9]]  # no patch: the whole file
             for f in paged(f"repos/{repo}/pulls/{num}/files?per_page=100") if f.get('status') != 'removed'}
    until = iso_epoch(pr['merged_at']) + FOLLOWUP_DAYS * 86400
    return {'merge_sha': pr['merge_commit_sha'], 'base': pr['base']['ref'], 'merged': pr['merged_at'], 'scanned': pr['merged_at'], 'checked': 0,
            'until': until, 'files': files if until > time.time() else {}}


def summarize(files):
    """What a commit did to each file, small enough to keep for good: the old-side line spans it changed, or None when
    GitHub shows no patch. A file that changed no line that counts (a dependency bump) is left out."""
    out = []
    for f in files:
        base = f['filename'].rsplit('/', 1)[-1]
        if f.get('status') == 'modified' and not f.get('patch') and base in LOCKFILES:
            continue  # a lockfile too large for GitHub to show: a dependency change, not your lines
        e = {'f': f['filename'], 's': f.get('status'), 'o': spans(patch_lines(f['patch'], f['filename'])[0]) if f.get('patch') else None}
        if f.get('previous_filename'):
            e['p'] = f['previous_filename']
        if e['o'] != [] or e['s'] in ('removed', 'renamed') or e.get('p'):
            out.append(e)
    return out


def touches(e, files):
    """Does a commit's summary (see summarize) change lines of the PR (within SLACK lines), or rename or remove one of its files? A rename is followed."""
    hit, renames = False, []
    for f in files:
        old = f.get('p') or f['f']
        ranges = e['files'].get(old)
        if ranges is None:
            continue
        if old != f['f']:
            renames.append((old, f['f']))
        if old != f['f'] or f['s'] == 'removed' or f['o'] is None:
            hit = True
        else:
            hit = hit or any(a <= hi + SLACK and b >= lo - SLACK for a, b in f['o'] for lo, hi in ranges)
    for old, new in renames:
        e['files'][new] = e['files'].pop(old)
    return hit


def commit_files(repo, sha):
    """A commit's summary, read from GitHub once ever: the answer is the same every time, so it is kept in the shared state."""
    k = f"{repo}@{sha}"
    if k not in shared_read()['commits']:
        files = summarize(request(f"repos/{repo}/commits/{sha}").json().get('files') or [])
        shared_update(lambda s: s['commits'].__setitem__(k, files))
    return shared_read()['commits'][k]


def emit_to(d, line):
    """An event for the session that owns watch dir d: its events.log, which that dir's daemon also writes to."""
    if ONCE:
        return emit(line)
    with open(os.path.join(d, 'events.log'), 'a') as f:
        f.write(line + '\n')


def follow_emit(sk, dirs, line):
    if claim(sk, record=not ONCE):  # once across restarts and daemons; a manual --once check records nothing
        for d in dirs:
            emit_to(d, line)


def followed_prs():
    """-> {key: [watch dirs]}: your merged PRs in the threads of every live watch dir (and this one)."""
    out = {}
    for d in dict.fromkeys(live_dirs() + [HERE]):
        try:
            st = json.load(open(os.path.join(d, 'gh-watch-state.json')))
        except (OSError, ValueError):
            continue
        for key in listed_threads(d):
            if st.get('prs', {}).get(key, {}).get('state') == 'merged' and st.get('author', {}).get(key) == ME:
                out.setdefault(key, []).append(d)
                old = st.get('followups', {}).get(key)  # kept by a watcher from before the shared state: its cursors save the backfill
                if old and key not in shared_read()['followups']:
                    old.setdefault('merged', iso(old['until'] - FOLLOWUP_DAYS * 86400))
                    shared_update(lambda s: s['followups'].setdefault(key, old))
    return out


def follow_ups():
    """After a PR of yours merges, later commits to its lines by others and PRs that reference it are a review you didn't get
    (mergeworthy:core, Learning from follow-ups). A shared job (shared_pass): each merged PR of yours in any live watch dir is
    followed for FOLLOWUP_DAYS. `### FOLLOW-UP` goes once, to the dirs that list the PR, per commit (not yours, not a bot's,
    not a merge) that touches its recorded lines, and once per other person's PR that references it.
    The commits of a repo are listed once per pass, newest first and with an ETag, and read oldest first, so a pass that
    runs out of calls (PASS_CALLS) resumes where it stopped, a list of more pages than a pass included (the backlog in the shared state);
    PRs not checked for longest go first."""
    prs, now = followed_prs(), time.time()
    fu = shared_read()['followups']
    for key in sorted(prs.keys() - fu.keys()):
        try:
            record = follow_record(key)
        except (Budget, PassSpent):
            raise
        except Exception as e:
            fail(f"follow-up record {key}", e)
            continue
        shared_update(lambda s: s['followups'].__setitem__(key, record))
    fu = shared_read()['followups']
    groups = {}
    for key in sorted((k for k in prs if k in fu and fu[k]['until'] > now), key=lambda k: fu[k]['checked']):
        groups.setdefault((key.rsplit('#', 1)[0], fu[key]['base']), []).append(key)
    for k in prs:
        if k in fu and fu[k]['until'] <= now and fu[k]['files']:
            shared_update(lambda s: s['followups'][k].update(files={}))  # past the window: kept as a marker so the PR isn't recorded again
    for (repo, base), keys in groups.items():
        entries = {k: json.loads(json.dumps(fu[k])) for k in keys}  # worked on here, written back when the group is done or stops
        gk, pending, done = f"{repo}@{base}", {}, False
        floor, since = min(e['scanned'] for e in entries.values()), min(e['merged'] for e in entries.values())
        url = f"repos/{repo}/commits?sha={base}&since={since}&per_page=100"
        bk = shared_read()['backlog'].get(gk)  # a commit list longer than a pass, kept page by page: this pass continues it
        if not bk or bk['since'] > since or bk['floor'] > floor:
            bk = {'since': since, 'floor': floor, 'started': iso(now - 600), 'next': url, 'queue': [],  # overlap: claims dedupe
                  'fresh': any(e['checked'] == 0 for e in entries.values())}  # a PR never read can't use a 304 for a list others have read
        try:
            while bk['next']:  # newest first, down to what was already read
                first = bk['next'] == url
                resp = request(bk['next'], store=shared_read()['etags'] if first else None, pending=pending if first else None, fresh=bk['fresh'], newest_first=True)
                page = [] if resp.status == 304 else resp.json()
                bk['queue'] += [{'sha': c['sha'], 'html_url': c['html_url'], 'parents': [0] * len(c.get('parents') or []), 'author': c.get('author') and {k: c['author'].get(k) for k in ('login', 'type')},
                                 'commit': {'committer': {'date': c['commit']['committer']['date']}, 'author': {k: c['commit']['author'].get(k) for k in ('name', 'email')}}} for c in page]
                bk['next'] = None if not page or not resp.next() or page[-1]['commit']['committer']['date'] < bk['floor'] else resp.next()
            while bk['queue']:  # oldest first
                c = bk['queue'][-1]
                sha, author, when = c['sha'], c.get('author') or {}, c['commit']['committer']['date']
                who = author.get('login') or c['commit']['author'].get('name')  # no GitHub account is linked to the commit's email: its git name
                mine = author.get('login') == ME or re.fullmatch(rf"(\d+\+)?{re.escape(ME)}@users\.noreply\.github\.com", c['commit']['author'].get('email') or '', re.I)
                if not is_bot({**author, 'login': who}) and not mine and len(c.get('parents') or []) <= 1:
                    wanted = [k for k, e in entries.items() if when >= e['scanned'] and sha != e['merge_sha'] and claim(f"followup:{k}:{sha}", record=False)]
                    if wanted:
                        files = commit_files(repo, sha)
                        for k in wanted:
                            if touches(entries[k], files):
                                follow_emit(f"followup:{k}:{sha}", prs[k], f"### FOLLOW-UP {k}: {sha[:10]} by {who} changes lines from your PR  {c['html_url']}")
                for e in entries.values():
                    e['scanned'] = max(e['scanned'], when)
                bk['queue'].pop()
            for k, e in entries.items():
                tpending = {}
                for t in paged(f"repos/{repo}/issues/{k.rsplit('#', 1)[1]}/timeline?per_page=100", shared_read()['etags'], tpending, fresh=bk['fresh']):
                    i = (t.get('source') or {}).get('issue') or {}
                    if t.get('event') == 'cross-referenced' and 'pull_request' in i and not is_bot(i.get('user')) and (i.get('user') or {}).get('login') != ME:
                        follow_emit(f"followup-ref:{k}:{i['html_url']}", prs[k], f"### FOLLOW-UP {k}: {i['html_url']} by {i['user']['login']} references your PR")
                pending.update(tpending)
                e['scanned'] = bk['started']
            done = True
        except (Budget, PassSpent):
            raise
        except Exception as ex:
            fail(f"follow-up {repo}", ex)
        finally:
            for e in entries.values():
                e['checked'] = now  # done or not, the group goes to the back of the line: a long backlog doesn't hold up the other repos
            shared_update(lambda s: (s['followups'].update(entries), s['etags'].update(pending if done else {}), s['backlog'].pop(gk, None) if done else s['backlog'].__setitem__(gk, bk)))


def locked():
    """One scan at a time across processes (daemon and manual runs), so state updates aren't lost."""
    f = open(STATE + '.lock', 'w')
    fcntl.flock(f, fcntl.LOCK_EX)
    return f


def run_scan():
    with locked():
        state = load_state()
        state['last_full'] = time.time()
        threads = scan_set(state, read_threads())  # once: it opens the hourly closed-thread window for both scans
        scan(state, threads=threads)
        save_state(state)
    with locked():
        state = load_state()
        scan_reactions(state, threads)
        save_state(state)


JOBS = (('discovery', 300, discover_agent_commands), ('followups', 600, follow_ups))  # machine-wide work: name, seconds between passes, job


def shared_pass(force=False):
    """The machine-wide jobs, for every live watch dir, by the one daemon that holds the lease; the others skip them. Each job
    is due every so many seconds across all daemons (its last_run is in the shared state, so a restart doesn't make it due
    again), makes at most PASS_CALLS calls per pass, and runs only while the budget is healthy."""
    if level() != OK and not force:
        return
    with lease() as mine:
        if not mine:
            return
        for name, every, job in JOBS:
            if level() != OK and not force:
                return
            if not force and time.time() - (shared_read()['jobs'].get(name) or {}).get('last_run', 0) < every:
                continue
            shared_update(lambda s: s['jobs'].__setitem__(name, {'last_run': time.time()}))  # at the start: a failing job waits its turn too
            _pass['left'] = PASS_CALLS
            try:
                job()
            except PassSpent:
                pass  # the rest waits for the next pass
            except Budget:
                return
            except Exception as e:
                fail(name, e)
            finally:
                _pass['left'] = None


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
    fu = shared_read()['followups']  # a merged PR of yours still being followed, or not yet recorded by the shared job, keeps the watcher
    if any(state['prs'].get(k, {}).get('state') == 'merged' and state.get('author', {}).get(k) == ME and fu.get(k, {'until': float('inf')})['until'] > time.time()
           for k in (f"{r}#{n}" for r, n in threads)):
        return
    prs = state['prs']
    for repo, num in threads:
        key = f"{repo}#{num}"
        if key in prs:
            done = prs[key].get('state') in ('merged', 'closed')
        elif key in state.get('open', {}):  # an issue: as the last scan found it
            done = not state['open'][key]
        else:
            try:
                done = request(f"repos/{repo}/issues/{num}").json()['state'] == 'closed'
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


def announce():
    """Tell this daemon's log about a pause that began since it last did (see announce_pause)."""
    if shared_read()['pause_until'] > time.time():
        with locked():
            state = load_state()
            announce_pause(state)
            save_state(state)


def tick():
    """One round of a daemon. What each budget level allows: OK everything; RESERVE (below RESERVE_AT calls left) not the shared
    jobs; LOW (below LOW_AT) only the notifications fast path and the threads it reports; PAUSED nothing."""
    follow_update()
    lvl = level()
    if lvl < PAUSED:
        try:
            with locked():
                state = load_state()
                changed = notifications_changed(state) or set()
                if lvl <= RESERVE:
                    changed |= own_events_changed(state) | repo_comments_changed(state)
                if changed:
                    scan(state, only=changed)
                save_state(state)
                full = lvl <= RESERVE and time.time() - state.get('last_full', 0) > 300  # the backstop; the repo comment feeds catch comments within ~10 s
            if full:
                run_scan()
                retire_if_done()
            shared_pass()
        except Budget:
            pass
    announce()


def main():
    if ONCE:
        run_scan()
        shared_pass(force=True)
        return
    while True:
        tick()
        time.sleep(10)


if __name__ == '__main__':
    main()
