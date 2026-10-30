#!/usr/bin/env python3
"""The jobs pre-agent-dedupe registered (~/.claude/agent-jobs, one JSON file each: key, started, and the task, the launcher's
session and transcript) and whether each one's agent has finished. T3's notices miss a run that ended interrupted or failed
and was revived, or that wrote its report without a final message, so the agent's own transcript decides: the earliest-started
one under ~/.claude/projects or ~/.codex/sessions that started at or after the launch and whose first prompt carries the job's
whole task (or, for a job an older hook registered with only its key and start, every ticket path in the key). pre-agent-dedupe
lets no open job's task contain another's, so that names the agent's own.
It has finished when that transcript has been quiet for QUIET
seconds with no tool call pending, or for LONG seconds whatever it was doing (no foreground tool call runs ten minutes),
while T3 Code shows no active run or background command of its thread and no agent it launched is still at work."""
import datetime, glob, hashlib, itertools, json, os, re, sys, time
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import steward

JOBS = os.path.expanduser('~/.claude/agent-jobs')
REPORTED = os.path.expanduser('~/.claude/agent-jobs-reported')  # <job file>-<transcript mtime>: reported once per finish
LAUNCHED = os.path.expanduser('~/.claude/agent-jobs-launch')  # <job file>: when pre-agent-dedupe let its launch through, its key and task
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
    rollout's session_meta, a Claude transcript's first queued prompt). Neither changes once the agent's first reply (Codex)
    or the first prompt (Claude) is written, so such a head is read once; one written before it is read again on the next call."""
    if path in _head: return _head[path]
    prompt, start, done, n = '', None, False, 0
    with open(path, errors='replace') as fh:
        for line in itertools.islice(fh, 50):
            if not line.endswith('\n'): break  # a line still being written
            n += 1
            try: o = json.loads(line)
            except ValueError: continue
            if not isinstance(o, dict): continue
            if start is None and isinstance(o.get('timestamp'), str):
                start = datetime.datetime.fromisoformat(o['timestamp'].replace('Z', '+00:00')).timestamp()
            p = o.get('payload') or {}
            if o.get('type') == 'response_item' and p.get('role') == 'user':
                prompt += ' '.join(b.get('text', '') for b in p.get('content') or [] if isinstance(b, dict)) + '\n'
                continue
            if o.get('type') == 'response_item' and (p.get('role') == 'assistant' or p.get('type') == 'reasoning' or str(p.get('type')).endswith('_call')):
                done = True
                break
            if o.get('type') == 'user' and not o.get('isMeta'):
                c = (o.get('message') or {}).get('content')
                t = c if isinstance(c, str) else ' '.join(b.get('text', '') for b in c or [] if isinstance(b, dict) and b.get('type') == 'text')
                if t.strip():
                    prompt, done = t, True
                    break
    if done or n == 50: _head[path] = (prompt, start)
    return prompt, start

def needles(job):
    """What the agent's first prompt carries: the whole task, else the ticket paths the key lists (a title-only key has none)."""
    return [job['brief'].strip()] if job.get('brief') else [w for w in job['key'].split() if w.startswith('/')]

def launched(job):
    """When the job's launch began (pre-agent-dedupe's PreToolUse); its registration for a job recorded without it."""
    return job.get('launched') or job['started']

def job_id(job):
    return hashlib.sha256(f"{job['key']}\0{launched(job)}".encode()).hexdigest()[:16]

_hit = {}
def transcript(job):
    """The agent's transcript; None until it starts."""
    ns, jid = needles(job), job_id(job)
    if not ns: return None
    if os.path.exists(_hit.get(jid) or '/nonexistent'):
        return _hit[jid]
    root, found = os.path.expanduser('~/.claude/projects'), []
    for p in glob.glob(f'{root}/*/*.jsonl') + glob.glob(f'{root}/*/*/subagents/*.jsonl') + glob.glob(os.path.expanduser(CODEX)):
        try:
            if os.path.getmtime(p) < launched(job): continue
            prompt, start = head(p)
            if start is not None and start >= launched(job) and all(n in prompt for n in ns): found.append((start, p))
        except OSError: pass
    if found:
        _hit[jid] = min(found)[1]
        return _hit[jid]
    return None

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
