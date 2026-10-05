#!/usr/bin/env python3
"""Claude Code PostToolUse hook (matcher: Bash). A thread you just posted in (a new issue or PR, a comment, a review)
joins the threads.txt of the watcher that covers its repo, else of the first live watcher, so maintainer comments on
it are answered (mergeworthy:github-event)."""
import json, os, re, sys
d = json.load(sys.stdin)
cmd = d.get('tool_input', {}).get('command', '')
r = d.get('tool_response') or {}
out = r.get('stdout', '') if isinstance(r, dict) else str(r)
# only a write: a read (`gh api …/issues/N/comments`) prints other threads' URLs, which aren't threads you posted in
api_write = re.search(r'\bgh\s+api\b.*\brepos/[\w.-]+/[\w.-]+/(issues|pulls)\b', cmd) and \
    re.search(r'(^|\s)(-X\s*POST|--method\s+POST|-f|-F|--field|--raw-field|--input)\b', cmd)
if not (re.search(r'\bgh\s+(issue|pr)\s+(create|comment|review)\b', cmd) or api_write):
    sys.exit(0)
reg = os.path.expanduser('~/.claude/gh-watch-dirs.txt')
dirs = [l.strip() for l in open(reg)] if os.path.exists(reg) else []
def lines(dr, f):
    p = os.path.join(dr, f)
    return [l.strip() for l in open(p)] if os.path.exists(p) else []
def live(dr):
    try:
        os.kill(int(lines(dr, 'gh-watch.pid')[0]), 0)
        return True
    except (IndexError, OSError, ValueError):
        return False
live_dirs = [dr for dr in dirs if live(dr)]
for repo, num in set(re.findall(r'github\.com/([\w.-]+/[\w.-]+)/(?:issues|pull)/(\d+)', out)):
    line = f'{repo} {num}'
    if any(line in lines(dr, 'threads.txt') for dr in live_dirs):
        continue
    covering = [dr for dr in live_dirs if repo in lines(dr, 'repos.txt') or any(l.split()[:1] == [repo] for l in lines(dr, 'threads.txt'))]
    target = (covering or live_dirs or [None])[0]
    if target:
        open(os.path.join(target, 'threads.txt'), 'a').write(line + '\n')
sys.exit(0)
