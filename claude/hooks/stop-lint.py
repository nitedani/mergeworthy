#!/usr/bin/env python3
"""Claude Code Stop hook. Blocks ending a turn with an offer or permission question the agent should just act on,
or after posting on GitHub with no armed tail of a watcher's events.log — a Monitor, or a live `tail` process
where the harness has no Monitor tool (1.5), or with a line still owed in a live watcher's replies-owed.md (1.5)."""
import glob, json, os, re, sys
d = json.load(sys.stdin)
if d.get('stop_hook_active'):
    sys.exit(0)
last = ''
posted, monitor_ids, monitors, dead = False, {}, set(), set()
POST = re.compile(r'\bgh\b[^\n]*(body-file|body=@|--input|\s-F\s)')
try:
    lines = open(d['transcript_path']).readlines()
except Exception:
    sys.exit(0)
for line in lines:
    try:
        e = json.loads(line)
    except ValueError:
        continue  # one bad or half-written line must not disable the check
    if not isinstance(e, dict): continue
    c = (e.get('message') or {}).get('content')
    if e.get('type') == 'user':
        texts = [c] if isinstance(c, str) else [x.get('text', '') if x.get('type') == 'text' else json.dumps(x.get('content')) for x in c or [] if isinstance(x, dict)]
        for x in c if isinstance(c, list) else []:
            if isinstance(x, dict) and x.get('tool_use_id') in monitor_ids:
                m = re.search(r'Monitor started \(task (\w+)', json.dumps(x.get('content')))
                if m: monitors.add(m.group(1))
        for t in texts:
            for tid in re.findall(r'<task-id>(\w+)</task-id>[\s\S]*?Monitor expired', t or ''): dead.add(tid)
    if e.get('type') == 'assistant':
        for x in c if isinstance(c, list) else []:
            if not isinstance(x, dict) or x.get('type') != 'tool_use': continue
            i = x.get('input') or {}
            if x.get('name') == 'Bash' and POST.search(i.get('command', '')): posted = True
            if x.get('name') == 'Monitor' and 'events.log' in i.get('command', ''): monitor_ids[x.get('id')] = 1
            if x.get('name') == 'TaskStop': dead.add(i.get('task_id') or i.get('shell_id') or '')
        if isinstance(c, list):
            t = ''.join(x.get('text', '') for x in c if isinstance(x, dict) and x.get('type') == 'text')
            if t.strip(): last = t
# quoted words are someone else's (a user's "should I ...?", a banned phrase being discussed): not an offer
own = re.sub(r'```.*?```|`[^`\n]*`|"[^"\n]*"|“[^”\n]*”|^>.*$', ' ', last, flags=re.S | re.M)
tail = own.strip()[-400:]
OFFER = r"(when you say (go|so)|say the word|want me to|shall I|should I\b|if you want|if you'd rather|your call|is yours to|or would you rather|which do you (want|prefer)|let me know if)"
if re.search(OFFER, tail, re.I) and 'GENUINE-FORK' not in last:
    print("Your last message ends with an offer or a permission question. If it is your own recommendation or in scope, "
          "do it now. Ask only for (a) irreversible actions on shared state you didn't create, (b) money, credentials "
          "or the user's global config, (c) an external maintainer's product decision or a fork you can't rank; then "
          "include a line starting 'GENUINE-FORK:' with your recommended default.", file=sys.stderr)
    sys.exit(2)
# A live `tail` of a watcher's events.log arms the watch too: harnesses without a Monitor tool (a local claude) run
# the printed tail as a background task, whose expiry the transcript doesn't report — the process is the monitor.
own_dirs = set()
reg = os.path.expanduser('~/.claude/gh-watch-dirs.txt')
cwd_d = d.get('cwd') or ''
for wd in (l.strip() for l in open(reg)) if os.path.exists(reg) else ():
    if wd and (cwd_d.startswith(wd) or wd.startswith(cwd_d or '/nonexistent')): own_dirs.add(wd)
def watched_by_service():
    """A watch dir whose daemon runs and whose agent the daemon wakes (the systemd service, 1.5): it handles the events."""
    for wd in own_dirs:
        try:
            pid = open(os.path.join(wd, 'gh-watch.pid')).read().strip()
            if b'gh-watch-daemon' in open(f'/proc/{pid}/cmdline', 'rb').read() and open(os.path.join(wd, 'agent')).read().strip() not in ('', 'true'):
                return True
        except OSError:
            continue
    return False

def armed_tail():
    for proc in glob.glob('/proc/[0-9]*'):
        try:
            cmd = open(proc + '/cmdline', 'rb').read().split(b'\0')
        except OSError:
            continue
        # this session's own watcher: a tail of the events.log in a watch dir this session's posts registered
        if b'tail' in cmd and any(c.endswith(b'events.log') and os.path.dirname(c.decode(errors='replace')) in own_dirs for c in cmd):
            return True
    return False

watcher_on = 'METHODOLOGY_WATCHER=off' not in (open(os.path.expanduser('~/.claude/mechanisms/settings.env')).read() if os.path.exists(os.path.expanduser('~/.claude/mechanisms/settings.env')) else '')
# A headless run (`claude -p`, entrypoint sdk-cli) has no Monitor tool: its caller watches, so don't ask it for one
headless = any('"entrypoint":"sdk-cli"' in l for l in lines[-20:])
if posted and watcher_on and not headless and not (monitors - dead or armed_tail() or watched_by_service()):
    print("You posted on GitHub in this session and no armed tail watches a watcher's events.log, so replies go unseen. "
          "Run `gh-watch-start <your artifact root> <owner/repo> <N>` for each thread: it runs the watcher as a service "
          "that wakes the agent on each event (methodology 1.5).", file=sys.stderr)
    sys.exit(2)
# 1.5's owed-debt list: the daemon records each human comment in the live watcher's replies-owed.md; a turn
# cannot end with a line still owed.
if watcher_on:
    for wd in sorted(own_dirs):
        try:
            os.kill(int(open(os.path.join(wd, 'gh-watch.pid')).read().strip()), 0)
        except (OSError, ValueError):
            continue  # no live daemon in this dir
        f = os.path.join(wd, 'replies-owed.md')
        owed = [l.strip() for l in open(f) if l.strip() and not l.startswith('#')] if os.path.exists(f) else []
        open_owed = [l for l in owed if not l.lower().startswith('done:')]
        if not os.path.exists(f) or open_owed:
            item = open_owed[0][:120] if open_owed else 'missing file'
            print(f"replies-owed.md in {wd} still has an owed reply ({item}). Answer it through the gate and clear the "
                  "line with 'done: <reply url> <what changed>' (1.5), or clear it with the reason no reply is owed.",
                  file=sys.stderr)
            sys.exit(2)
sys.exit(0)
