#!/usr/bin/env python3
"""Claude Code PreToolUse hook (matcher: Monitor). Exit 2 blocks; stderr goes to the agent.
A Monitor on the events.log of a watch dir bound to a T3 thread (<dir>/t3-thread, steward.bind_watcher) is refused: that watcher
sends each event to the thread itself (gh-watch.py's wake_thread), so the Monitor would only wake the session when it expires."""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import failclosed
import steward
d = json.load(sys.stdin)
cmd = str((d.get('tool_input') or {}).get('command') or '')
cwd = d.get('cwd') or os.getcwd()
for p in re.findall(r'''([^\s'"|;&<>]*)/events\.log\b''', cmd):
    wd = os.path.join(cwd, os.path.expanduser(re.sub(r'^\$(HOME\b|\{HOME\})', '~', p)))
    if tid := steward.first(os.path.join(wd, 't3-thread')):
        sys.stderr.write(f"BLOCKED: the watcher in {wd} sends each event to T3 thread {tid} itself (gh-watch.py's wake_thread): "
                         "arm no Monitor on its events.log, and re-arm none when one expires\n")
        sys.exit(2)
sys.exit(0)
