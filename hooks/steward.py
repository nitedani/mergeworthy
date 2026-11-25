#!/usr/bin/env python3
"""The steward, declared in ~/.mergeworthy/steward as `<watch dir> <T3 thread id>`: the session that sorts follow-ups and owns
the mergeworthy repo. Without the file there is none, and each main session keeps both."""
import contextlib, datetime, os, re, shutil, sqlite3, time

def read():
    """(watch dir, T3 thread id), or None."""
    try: wd, tid = open(os.path.expanduser('~/.mergeworthy/steward')).read().split()[:2]
    except (OSError, ValueError): return None
    return os.path.expanduser(wd).rstrip('/'), tid

def folder():
    """The steward's folder: the first word of ~/.mergeworthy/steward, else ~/.mergeworthy/work/steward (mergeworthy:steward)."""
    return (read() or (os.path.expanduser('~/.mergeworthy/work/steward'),))[0]

def in_folder(path):
    """True for the steward's folder or a dir in it (<S>, <S>/live): disk-sweep's w-done keeps it, and its watchers don't stop when T3
    deletes the steward's thread, since T3 can settle and then delete that thread while the steward's PRs are open."""
    own, p = os.path.realpath(folder()), os.path.realpath(path)
    return p == own or p.startswith(own + os.sep)

def live():
    """The live dir, <folder>/live: the watcher a pass leaves on what it posted (mergeworthy:steward), which answers like any work folder's."""
    return os.path.join(folder(), 'live')

def quiet(d):
    """True for the steward's folder and the watch dirs inside it but live(): their watcher reacts to nothing, owes no reply and wakes
    its thread only for a new mergeworthy issue (gh-watch.py's WAKES); the rest of their events.log waits for the next pass."""
    s, d = os.path.realpath(folder()), os.path.realpath(d)
    return (d == s or d.startswith(s + '/')) and d != os.path.realpath(live())

def home(wf):
    """The watch dir a thread posted from work folder wf joins: live() for the steward's folder (its PR worktrees), else wf."""
    return live() if wf and os.path.realpath(wf) == os.path.realpath(folder()) else wf

def passed_by(wd):
    """The session whose watcher round in wd passed in the last day (gh-watch-start --round writes <wd>/passed), or None."""
    try:
        p = os.path.join(wd, 'passed')
        return open(p).read().split()[0] if time.time() - os.path.getmtime(p) < 86400 else None
    except (OSError, IndexError):
        return None

def sorted_verdicts(path):
    """{key: verdict} of a followups-sorted.txt's `<key> MISS|TASTE|DIRECTION|WORKED <link or reason>` lines (mergeworthy:rules step 6);
    a commit's URL is keyed by its sha."""
    try: text = open(path, errors='replace').read()
    except OSError: return {}
    return {re.sub(r'^https?://\S+/commit/(?=[0-9a-f]{7,40}$)', '', k): v
            for k, v in re.findall(r'^(\S+)\s+(MISS|TASTE|DIRECTION|WORKED)\s+\S', text, re.M)}

def sorted_as(ref, verdicts):
    """The verdict of a FOLLOW-UP or review ref: its exact key, or a sha prefix of 7+ characters either way; else None."""
    sha = lambda x: re.fullmatch(r'[0-9a-f]{7,40}', x)
    return next((v for k, v in verdicts.items() if k == ref or sha(k) and sha(ref) and (k.startswith(ref) or ref.startswith(k))), None)

def unsorted(wd, older=0):
    """(line, key, epoch) of each MAINTAINER REVIEW in wd's events.log more than older seconds old with no verdict in its
    followups-sorted.txt (mergeworthy:rules step 6)."""
    try: log = open(os.path.join(wd, 'events.log'), errors='replace').read()
    except OSError: return []
    done = sorted_verdicts(os.path.join(wd, 'followups-sorted.txt'))
    events = ((m[0], m[1], datetime.datetime.fromisoformat(m[2].replace('Z', '+00:00')).timestamp())
              for m in re.finditer(r'^### MAINTAINER REVIEW [^:\n]+: (\S+) by .*  at (\S+Z)$', log, re.M))
    return [e for e in dict.fromkeys(events) if time.time() - e[2] > older and not sorted_as(e[1], done)]

# The statuses T3 Code counts as active: a run's (its orchestration_v2_projection_runs_recovery_idx) and a delegated task's (its binary's widest set)
ACTIVE_RUNS = ('queued', 'preparing', 'starting', 'running', 'waiting')
ACTIVE_TASKS = ('pending', 'starting', 'running', 'waiting')

def _db(ask, default):
    """ask(read-only connection to T3 Code's state), or default on an error. The connection is closed after: an unclosed one stays
    open until the cycle collector runs, so a watcher that asks for days runs out of file handles."""
    try: c = sqlite3.connect(f"file:{os.path.expanduser('~/.t3/userdata/statev2.sqlite')}?mode=ro", uri=True, timeout=2)
    except sqlite3.Error: return default
    try:
        return ask(c)
    except sqlite3.Error:
        return default
    finally:
        c.close()

def _ask(session_id, ask, default):
    """ask(connection, the T3 thread a Claude session runs in), or default without that thread or on an error."""
    def run(c):
        r = c.execute("select thread_id from orchestration_v2_projection_provider_threads where json_extract(payload_json, '$.nativeThreadRef.nativeId') = ?",
                      (session_id,)).fetchone()
        return ask(c, r[0]) if r else default
    return _db(run, default)

def queued(tid, text):
    """The run on T3 thread tid still queued for a message starting with text, or None."""
    r = _db(lambda c: c.execute(
        "select r.run_id from orchestration_v2_projection_runs r join orchestration_v2_projection_messages m on m.message_id = json_extract(r.payload_json, '$.userMessageId') "
        "where r.thread_id = ? and r.status = 'queued' and substr(json_extract(m.payload_json, '$.text'), 1, ?) = ?", (tid, len(text), text)).fetchone(), None)
    return r and r[0]

def received(tid, text, since):
    """True when T3 thread tid holds a message with exactly this text, created at or after since (UTC, ISO)."""
    return bool(_db(lambda c: c.execute("select 1 from orchestration_v2_projection_messages where thread_id = ? and created_at >= ? "
                                        "and json_extract(payload_json, '$.text') = ? limit 1", (tid, since, text)).fetchone(), None))

# A message that opens by asking to stop or pause the work itself ("can you stop work please", "Stooooppoopp", "állj", "stop the work
# now", "pause until I say continue") or ends with it ("…, then pause"); not "don't stop", "stop-lint …", "stop the dev server" or
# "stop /tmp/server", and not a stop said mid-sentence
STOP = re.compile(r"^\W*(?:(?:please|pls|ok(?:ay)?|hey|(?:can|could|would) you)[\s,]+)*(?:st+o+p+[op]*|pause|áll(?:j|jál|jatok|jon)(?:\s+(?:meg|le))?)"
                  r"(?:\s+(?:the work|work(?:ing)?|(?:right |for )?now|it|that|this|everything|all|here|immediately|what you['’]?re doing|doing (?:that|this|it)))*"
                  r"(?:\s+(?:please|pls|until|and (?:wait|hold))\b|\s+for (?:a (?:bit|moment|while|minute|second)|\d+ (?:minutes?|hours?))\b|\s*(?:[.!?,;:…。！？]+(?=\s|$)|[^\w/\\.:-]*$))"
                  r"|\bthen\s+(?:stop|pause)\W*$", re.I)

def asks_stop(text):
    return bool(STOP.search(text or ''))

def stopped(tid):
    """True while the user has T3 thread tid stopped: its latest run is one someone stopped (status interrupted: the stop button or
    t3_thread_interrupt; a T3 restart leaves none), or the latest message a person wrote in it asks to stop. A wake would restart work
    the user stopped; their next message ends it."""
    def ask(c):
        r = c.execute("select status from orchestration_v2_projection_runs where thread_id = ? "
                      "order by json_extract(payload_json, '$.ordinal') desc limit 1", (tid,)).fetchone()
        m = c.execute("select json_extract(payload_json, '$.text') from orchestration_v2_projection_messages where thread_id = ? and role = 'user' "
                      "and coalesce(json_extract(payload_json, '$.createdBy'), 'user') = 'user' order by created_at desc limit 1", (tid,)).fetchone()
        return bool(r) and r[0] == 'interrupted' or bool(m) and asks_stop(m[0])
    return _db(ask, False)

def settled(tid):
    """True while T3 thread tid is settled, by the user or by T3 after a week idle, or archived (thread_state): any message it receives
    brings it back."""
    return thread_state(tid) == 'settled'

def thread_of(wd):
    """The T3 thread a watch dir is bound to: its t3-thread, else the t3-gone T3 once reported not found; '' without either."""
    return first(os.path.join(wd, 't3-thread')) or first(os.path.join(wd, 't3-gone'))

def thread_state(tid):
    """What T3's database says of thread tid, the one reader of it for the watcher's tick and disk-sweep's w-done: 'deleted' once its
    row holds a deleted_at or T3 has no row for it, 'settled' while it is settled as T3 counts it (settledOverride 'settled' or a
    settledAt, ThreadPullRequestService) or archived (archived_at), else 'live'; None without a thread or when the database can't be read."""
    if not tid:
        return None
    row = _db(lambda c: [c.execute("select deleted_at, archived_at, json_extract(payload_json, '$.settledOverride'), json_extract(payload_json, '$.settledAt')"
                                   " from orchestration_v2_projection_threads where thread_id = ?", (tid,)).fetchone()], None)
    if row is None:
        return None
    if row[0] is None or row[0][0] is not None:
        return 'deleted'
    _, archived, override, settled_at = row[0]
    return 'settled' if archived is not None or override == 'settled' or settled_at is not None else 'live'

def started(run_id):
    """True once T3 started the run, False while it can still start, None when it ended without starting, is gone or can't be read."""
    def ask(c):
        r = c.execute("select status, json_extract(payload_json, '$.startedAt') from orchestration_v2_projection_runs where run_id = ?", (run_id,)).fetchone()
        return None if not r else True if r[1] else False if r[0] in ACTIVE_RUNS else None
    return _db(ask, None)

def _in(values):
    return f"({','.join('?' * len(values))})"

def _chain(c, tid):
    out = []
    try:
        while tid and tid not in out and len(out) < 8:
            out.append(tid)
            r = c.execute('select thread_id from orchestration_v2_projection_subagents where child_thread_id = ?', (tid,)).fetchone()
            tid = r and r[0]
    except sqlite3.Error:
        pass
    return out

def native(tid):
    """The provider's id of the session T3 thread tid runs in (a Claude session's, a Codex rollout's), one for all its runs; None before
    its first run starts or without T3's database."""
    return _db(lambda c: (c.execute("select json_extract(payload_json, '$.nativeThreadRef.nativeId') from orchestration_v2_projection_provider_threads "
                                    "where thread_id = ?", (tid,)).fetchone() or (None,))[0], None)

def threads(session_id):
    """The T3 thread a Claude session runs in, then the threads that delegated it, read from T3 Code's state."""
    return _ask(session_id, _chain, [])

def bind_watcher(wd):
    """Under T3 Code <wd>/t3-thread names the main session's thread (the last of the threads that delegated the session in
    <wd>/session), then t3's full path, for gh-watch.py's wake_thread. t3-wake.cursor starts at events.log's end when there is none
    or the thread replaces another, else it stays, so what came while t3 was missing still goes. Without t3, t3-thread goes; without
    a thread, or for the one wake_thread found deleted (<wd>/t3-gone), the cursor too."""
    s = first(os.path.join(wd, 'session'))
    tid, t3 = s and (threads(s) or [''])[-1], shutil.which('t3')  # its full path: cron revives the daemon with a PATH that may not hold it
    cursor, bound = os.path.join(wd, 't3-wake.cursor'), first(os.path.join(wd, 't3-thread'))
    drop = not tid or tid == first(os.path.join(wd, 't3-gone'))
    if drop or not t3:
        for f in ['t3-thread', 't3-wake.cursor'][:1 + drop]:
            with contextlib.suppress(FileNotFoundError): os.remove(os.path.join(wd, f))
        return
    if bound and bound != tid or not os.path.exists(cursor):
        with open(cursor, 'w') as f: f.write(f"{os.path.getsize(os.path.join(wd, 'events.log'))}\n")
    with open(os.path.join(wd, 't3-thread'), 'w') as f: f.write(f"{tid}\n{t3}\n")

def _pending(c, tid):
    return bool(c.execute(f"select 1 from orchestration_v2_projection_subagents where ? in (thread_id, child_thread_id) and status in {_in(ACTIVE_TASKS)}",
                          (tid, *ACTIVE_TASKS)).fetchone()
                or c.execute("select 1 from orchestration_v2_projection_provider_threads where thread_id = ? and case when json_valid(payload_json) "
                             "then json_array_length(payload_json, '$.pendingBackgroundTasks') > 0 else 0 end", (tid,)).fetchone())

def _busy(c, tid):
    return bool(c.execute(f"select 1 from orchestration_v2_projection_runs where thread_id = ? and status in {_in(ACTIVE_RUNS)}", (tid, *ACTIVE_RUNS)).fetchone()) or _pending(c, tid)

def busy(session_id):
    """True when the Claude session's T3 thread has an active run, a task it delegated still active, a background command still
    running (T3's waiting_for_children), or, as a delegated task, is still active itself: T3 will act on it again."""
    return _ask(session_id, _busy, False)

def ended(session_id, at):
    """When the Claude session's T3 turn that had started and was running at epoch `at` ended (epoch seconds): T3 delivers a notice due then once
    that turn ends. None while it still runs; 0 without the thread, such a turn or T3's database. Later turns don't count."""
    def ask(c, tid):
        ts = lambda v: datetime.datetime.fromisoformat(v.replace('Z', '+00:00')).timestamp()
        for status, start, done in c.execute("select status, json_extract(payload_json, '$.startedAt'), completed_at from orchestration_v2_projection_runs "
                                             "where thread_id = ? and json_valid(payload_json)", (tid,)):
            if start and ts(start) <= at and (not done or ts(done) >= at):  # a run that started: a queued or cancelled one never held it
                return None if status in ACTIVE_RUNS else ts(done) if done else 0
        return 0
    return _ask(session_id, ask, 0)

def pending(session_id):
    """What busy() counts but the thread's runs: a Stop hook runs inside the session's own run, so busy() is true at every stop."""
    return _ask(session_id, _pending, False)

def active(tid):
    """True while T3 thread tid has what busy() counts as active; without T3's database, False: nothing can be waited for."""
    return _db(lambda c: _busy(c, tid), False)

def delegators(tid):
    """T3 thread tid, then the threads that delegated it, read from T3 Code's state."""
    return _db(lambda c: _chain(c, tid), [tid]) if tid else []

def tasks(session_id):
    """The ids of the delegated tasks T3 ran in the Claude or Codex session's thread: its launch, each message sent to it, each continuation."""
    return _ask(session_id, lambda c, tid: [r[0] for r in c.execute("select subagent_id from orchestration_v2_projection_subagents where child_thread_id = ?", (tid,))], [])

def first(path):
    try: return open(path).read().split()[0]
    except (OSError, IndexError): return ''

def is_steward(session_id, cwd):
    """True for the steward's session and the agents it delegated: by its T3 thread, a cwd in its watch dir, or, without
    T3's database, the session gh-watch-start recorded in its watch dir."""
    s = read()
    return bool(s) and (((cwd or '').rstrip('/') + '/').startswith(s[0] + '/') or bool(session_id) and
                        (first(os.path.join(s[0], 'session')) == session_id or s[1] in threads(session_id)))

def recipient(dirs):
    """Where a follow-up goes: the steward's watch dir while its watcher runs (someone reads it), else dirs."""
    s = read()
    try: os.kill(int(first(os.path.join(s[0], 'gh-watch.pid'))), 0)
    except (TypeError, ValueError, OSError): return dirs
    return [s[0]]
