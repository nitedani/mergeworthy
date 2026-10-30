#!/usr/bin/env python3
"""The jobs pre-agent-dedupe registered (~/.claude/agent-jobs, one JSON file each: key, started, and the brief, the launcher's
session and transcript) and whether each one's agent has finished. T3's notices miss a run that ended interrupted or failed
and was revived, or that wrote its report without a final message, so the agent's own transcript decides: the one under
~/.claude/projects or ~/.codex/sessions whose first prompt carries the brief (or, for a job an older hook registered with only its
key and start, every ticket path in the key). A transcript belongs to one job, kept in CLAIMS: the open jobs on one brief, in launch
order, each claim the earliest-started unclaimed one that started at or after their launch, so a release, a later round or another
process never moves it. It has finished when that transcript has been quiet for QUIET
seconds with no tool call pending, or for LONG seconds whatever it was doing (no foreground tool call runs ten minutes),
while T3 Code shows no active run or background command of its thread and no agent it launched is still at work."""
import datetime, fcntl, glob, hashlib, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import steward

JOBS = os.path.expanduser('~/.claude/agent-jobs')
REPORTED = os.path.expanduser('~/.claude/agent-jobs-reported')  # <job file>-<transcript mtime>: reported once per finish
LAUNCHED = os.path.expanduser('~/.claude/agent-jobs-launch')  # <job file>: the time pre-agent-dedupe let its launch through
CLAIMS = os.path.expanduser('~/.claude/agent-jobs-claims')  # <claim time>\t<job id>\t<transcript>, one line per claim
LAUNCH = re.compile(rb'"name": ?"(Agent|Task|mcp__[^"]*(delegate_task|t3_thread_launch))"')  # pre-agent-dedupe's matcher
QUIET, LONG, OPEN = 180, 660, 24 * 3600
CODEX = '~/.codex/sessions/*/*/*/rollout-*.jsonl'  # T3 Code's Codex agents  # OPEN: pre-agent-dedupe's window, after which a job no longer counts

def jobs(now=None):
    """(file name, job) for each open job: registered in the last day and not released."""
    now, out = now or time.time(), []
    for f in sorted(os.listdir(JOBS)) if os.path.isdir(JOBS) else ():
        try: j = json.load(open(os.path.join(JOBS, f)))
        except (OSError, ValueError): continue
        if isinstance(j, dict) and j.get('key') and now - j.get('started', 0) < OPEN:
            out.append((f, j))
    return out

_head = {}
def head(path):
    """(first prompt, start time) of a transcript, None for a start it doesn't record: the first entry's `timestamp` (a Codex
    rollout's session_meta, a Claude transcript's first queued prompt). Neither ever changes, so each file is read once."""
    if path not in _head:
        prompt, start = '', None
        with open(path, errors='replace') as fh:
            for i, line in zip(range(50), fh):
                try: o = json.loads(line)
                except ValueError: continue
                if not isinstance(o, dict): continue
                if start is None and isinstance(o.get('timestamp'), str):
                    start = datetime.datetime.fromisoformat(o['timestamp'].replace('Z', '+00:00')).timestamp()
                if o.get('type') == 'response_item' and (o.get('payload') or {}).get('role') == 'user':
                    prompt += ' '.join(b.get('text', '') for b in o['payload'].get('content') or [] if isinstance(b, dict)) + '\n'
                    continue
                if o.get('type') == 'user' and not o.get('isMeta'):
                    c = (o.get('message') or {}).get('content')
                    t = c if isinstance(c, str) else ' '.join(b.get('text', '') for b in c or [] if isinstance(b, dict) and b.get('type') == 'text')
                    if t.strip():
                        prompt = t
                        break
        _head[path] = (prompt, start)
    return _head[path]

def needles(job):
    """What the agent's first prompt carries: the brief, else the ticket paths the key lists (a title-only key has none)."""
    return [job['brief'].strip()[:500]] if job.get('brief') else [w for w in job['key'].split() if w.startswith('/')]

def launched(job):
    """When the job's launch began (pre-agent-dedupe's PreToolUse); its registration for a job recorded without it."""
    return job.get('launched') or job['started']

def job_id(job):
    return hashlib.sha256(f"{job['key']}\0{launched(job)}".encode()).hexdigest()[:16]

_hit = {}
def transcript(job):
    """The agent's transcript, the one claimed for the job (CLAIMS); None until it starts."""
    ns = needles(job)
    if not ns: return None
    if os.path.exists(_hit.get(job_id(job)) or '/nonexistent'):
        return _hit[job_id(job)]
    os.makedirs(os.path.dirname(CLAIMS), exist_ok=True)
    with open(CLAIMS, 'a+') as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)  # every hook and watcher claims through this file, one at a time
        fh.seek(0)
        lines = fh.readlines()
        rows = [l.rstrip('\n').split('\t') for l in lines if l.count('\t') == 2 and time.time() - float(l.split('\t')[0]) < 2 * OPEN]
        if len(rows) < len(lines):  # a claim is kept two days, a day past the longest its job stays open (OPEN)
            fh.truncate(0); fh.writelines('\t'.join(r) + '\n' for r in rows)
        owner = {r[1]: r[2] for r in rows}
        if job_id(job) not in owner:
            same = sorted({job_id(j): j for j in [job] + [j for _, j in jobs()] if needles(j) == ns}.values(), key=launched)
            wait = [j for j in same if job_id(j) not in owner]
            root, taken, found = os.path.expanduser('~/.claude/projects'), set(owner.values()), []
            for p in glob.glob(f'{root}/*/*.jsonl') + glob.glob(f'{root}/*/*/subagents/*.jsonl') + glob.glob(os.path.expanduser(CODEX)):
                try:
                    if p in taken or p in (j.get('transcript') for j in same) or os.path.getmtime(p) < launched(wait[0]): continue
                    prompt, start = head(p)
                    if start is not None and all(n in prompt for n in ns): found.append((start, p))
                except OSError: pass
            found.sort()
            for j in wait:
                p = next((p for s, p in found if s >= launched(j) and p not in taken), None)
                if p is None: continue
                taken.add(p); owner[job_id(j)] = p
                fh.write(f"{time.time()}\t{job_id(j)}\t{p}\n")
    if p := owner.get(job_id(job)):
        _hit[job_id(job)] = p
    return p

def launchers(items):
    """{file name: launcher transcript} for (file name, job, agent transcript) items whose job recorded no launcher: the
    session transcript written since the launch, not the agent's, with a launch call naming every needle (a transcript
    that only lists the job doesn't count). Each transcript is read once."""
    out, todo = {}, [(f, j, c, [n.encode() for n in needles(j)]) for f, j, c in items if needles(j)]
    for p in glob.glob(os.path.expanduser('~/.claude/projects/*/*.jsonl')) if todo else ():
        try:
            m = os.path.getmtime(p)
            want = [t for t in todo if t[0] not in out and m >= t[1]['started'] - 60 and p != t[2]]
            calls = [l for l in open(p, 'rb') if b'"tool_use"' in l and LAUNCH.search(l)] if want else []
        except OSError: continue
        for f, j, c, ns in want:
            if any(all(n in l for n in ns) for l in calls): out[f] = p
    return out

def session_id(path):
    """The provider's id of the session a transcript records, the one T3 Code names it by: a Codex rollout's session_meta id,
    else (Claude) the file's name."""
    try:
        with open(path) as fh: o = json.loads(fh.readline())
        if isinstance(o, dict) and o.get('type') == 'session_meta': return str((o.get('payload') or {}).get('id') or '')
    except (OSError, ValueError): pass
    return os.path.basename(path)[:-len('.jsonl')]

def pending(path):
    """The transcript's last turn is a tool call still running (or cut off by a crash: LONG covers that)."""
    with open(path, 'rb') as fh:
        fh.seek(max(0, os.path.getsize(path) - 65536))
        for line in reversed(fh.read().splitlines()):
            try: o = json.loads(line)
            except ValueError: continue
            if isinstance(o, dict) and o.get('type') == 'event_msg':
                return (o.get('payload') or {}).get('type') not in ('task_complete', 'turn_aborted')
            if isinstance(o, dict) and o.get('type') in ('user', 'assistant'):
                c = (o.get('message') or {}).get('content')
                return o['type'] == 'assistant' and any(isinstance(b, dict) and b.get('type') == 'tool_use' for b in c or [] if not isinstance(c, str))
    return False

def finished(job, now=None, _seen=()):
    """(transcript, its mtime) when the job's agent has finished, else None. An agent whose T3 thread has an active run
    (waiting on an approval) or background command still running, or that launched agents of its own, hasn't finished."""
    p = transcript(job)
    if not p: return None
    m = os.path.getmtime(p); quiet = (now or time.time()) - m
    if not (quiet >= LONG or (quiet >= QUIET and not pending(p))): return None
    sid = session_id(p)
    if steward.busy(sid) or sid not in _seen and any(j.get('session') == sid and not finished(j, now, _seen + (sid,)) for _, j in jobs(now)):
        return None
    return (p, m)

def reported(f, mtime):
    return os.path.exists(os.path.join(REPORTED, f'{f}-{int(mtime)}'))

def claim(f, mtime):
    """True once per job and finish: the first caller reports it."""
    os.makedirs(REPORTED, exist_ok=True)
    try: os.close(os.open(os.path.join(REPORTED, f'{f}-{int(mtime)}'), os.O_CREAT | os.O_EXCL)); return True
    except FileExistsError: return False
