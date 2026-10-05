#!/usr/bin/env python3
"""Claude Code Stop hook. Blocks ending a turn with an offer or permission question the agent should just act on,
or after posting on GitHub with no live Monitor on a watcher's events.log in this session (the session is what answers
the events; nothing else wakes it), or with a line still owed in a live watcher's replies-owed.md (mergeworthy:github-threads)."""
import json, os, re, sys
d = json.load(sys.stdin)
if d.get('stop_hook_active'):
    sys.exit(0)
last = ''
posted, monitor_ids, monitors, dead, commands, monitor_cmds = False, {}, set(), set(), [], []
last_user = ''  # the user's own last message (not a tool result or a hook's feedback)
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
        typed = c if isinstance(c, str) else ' '.join(x.get('text', '') for x in c or [] if isinstance(x, dict) and x.get('type') == 'text')
        if typed.strip() and not typed.lstrip().startswith(('<', 'Stop hook feedback')):
            last_user = typed
        for t in texts:
            for tid in re.findall(r'<task-id>(\w+)</task-id>[\s\S]*?Monitor expired', t or ''): dead.add(tid)
    if e.get('type') == 'assistant':
        for x in c if isinstance(c, list) else []:
            if not isinstance(x, dict) or x.get('type') != 'tool_use': continue
            i = x.get('input') or {}
            if x.get('name') == 'Bash' and POST.search(i.get('command', '')): posted = True
            if x.get('name') == 'Bash': commands.append(i.get('command', ''))
            if x.get('name') == 'Monitor' and 'events.log' in i.get('command', ''):
                monitor_ids[x.get('id')] = 1
                monitor_cmds.append(i.get('command', ''))
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
own_dirs = set()
reg = os.path.expanduser('~/.claude/gh-watch-dirs.txt')
cwd_d = d.get('cwd') or ''
for wd in (l.strip() for l in open(reg)) if os.path.exists(reg) else ():
    # or a watch dir this session works through from elsewhere (its cwd is a repo, the watch dir an artifact root):
    # it watches its events.log, starts its watcher or gates a draft in it. Only reading another session's files
    # (its state, its log) doesn't make that session's owed replies this one's.
    home_wd = wd.replace(os.path.expanduser('~'), '~', 1)
    def mentions(c): return wd in c or home_wd in c
    if wd and (cwd_d == wd or cwd_d.startswith(wd.rstrip('/') + '/') or any(map(mentions, monitor_cmds))
               or any(mentions(c) and re.search(r'\b(gh-watch-start|gate-pass)\b', c) for c in commands)): own_dirs.add(wd)
_env = os.path.expanduser('~/.mergeworthy/settings.env')
# MERGEWORTHY_WATCHER in the environment wins over the plugin option, as for every script
watcher_on = (os.environ.get('MERGEWORTHY_WATCHER') or ('off' if 'MERGEWORTHY_WATCHER=off' in (open(_env).read() if os.path.exists(_env) else '') else 'on')) != 'off'
# A headless run (`claude -p`, entrypoint sdk-cli) has no Monitor tool: its caller watches
headless = any('"entrypoint":"sdk-cli"' in l for l in lines[-20:])
# The user paused the work: nothing is to be watched or answered until they resume
paused = re.search(r'\bpause\b', last_user, re.I) is not None
if posted and watcher_on and not headless and not paused and not (monitors - dead):
    print("You posted on GitHub in this session and no Monitor in it watches a watcher's events.log, so replies go unseen: "
          "nothing else answers them. Run `gh-watch-start <your artifact root> <owner/repo> <N>` and arm the Monitor it "
          "prints, with the longest timeout; re-arm it whenever it expires (mergeworthy:github-threads).", file=sys.stderr)
    sys.exit(2)
# The owed-reply list: the daemon records each human comment in the live watcher's replies-owed.md; a turn
# cannot end with a line still owed.
if watcher_on and not paused:
    for wd in sorted(own_dirs):
        try:
            os.kill(int(open(os.path.join(wd, 'gh-watch.pid')).read().strip()), 0)
        except (OSError, ValueError):
            continue  # no live daemon in this dir
        f = os.path.join(wd, 'replies-owed.md')
        owed = [l.strip() for l in open(f) if l.strip() and not l.startswith('#')] if os.path.exists(f) else []
        import datetime
        def holding(l):  # `holding: <reply url> <ETA as ISO time>`: a holding reply was posted and its answer isn't due yet
            m = re.match(r'holding:\s+\S+\s+(\S+)', l, re.I)
            try:
                return bool(m) and datetime.datetime.fromisoformat(m.group(1).replace('Z', '+00:00')) > datetime.datetime.now(datetime.timezone.utc)
            except ValueError:
                return False
        open_owed = [l for l in owed if not l.lower().startswith('done:') and not holding(l)]
        if open_owed:
            print(f"replies-owed.md in {wd} still has an owed reply ({open_owed[0][:120]}). Answer it through the gate and clear the "
                  "line with 'done: <reply url> <what changed>' (mergeworthy:github-threads), or clear it with the reason no reply is owed.",
                  file=sys.stderr)
            sys.exit(2)
sys.exit(0)
