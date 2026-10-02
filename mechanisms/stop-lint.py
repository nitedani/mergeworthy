#!/usr/bin/env python3
"""Claude Code Stop hook. Blocks ending a turn with an offer or permission question the agent should just act on,
or after posting on GitHub with no Monitor tailing a watcher's events.log (1.5)."""
import json, os, re, sys
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
watcher_on = 'METHODOLOGY_WATCHER=off' not in (open(os.path.expanduser('~/.claude/mechanisms/settings.env')).read() if os.path.exists(os.path.expanduser('~/.claude/mechanisms/settings.env')) else '')
if posted and watcher_on and not (monitors - dead):
    print("You posted on GitHub in this session and no Monitor tails a watcher's events.log, so replies go unseen. "
          "Run `gh-watch-start <your artifact root> <owner/repo> <N>` for each thread, arm the Monitor command it prints "
          "(timeout_ms 1800000), handle events.log from your cursor, and re-arm on every expiry (methodology 1.5).", file=sys.stderr)
    sys.exit(2)
sys.exit(0)
