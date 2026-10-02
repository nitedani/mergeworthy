#!/usr/bin/env python3
"""Claude Code PostToolUse hook (matcher: Bash). A thread you just created (`gh issue create`, `gh pr create`, `gh api` POST)
joins the threads.txt of the running watcher that covers its repo (gh-watch-start), so its replies are seen."""
import json, os, re, sys
d = json.load(sys.stdin)
cmd = d.get('tool_input', {}).get('command', '')
r = d.get('tool_response') or {}
out = r.get('stdout', '') if isinstance(r, dict) else str(r)
if not re.search(r'\bgh\b.*\b(create|POST)\b|\bgh api\b.*\b(issues|pulls)\b', cmd):
    sys.exit(0)
reg = os.path.expanduser('~/.claude/gh-watch-dirs.txt')
dirs = [l.strip() for l in open(reg)] if os.path.exists(reg) else []
def lines(dr, f):
    p = os.path.join(dr, f)
    return [l.strip() for l in open(p)] if os.path.exists(p) else []
for repo, num in set(re.findall(r'github\.com/([\w.-]+/[\w.-]+)/(?:issues|pull)/(\d+)', out)):
    line = f'{repo} {num}'
    covering = [dr for dr in dirs if repo in lines(dr, 'repos.txt') or any(l.split()[:1] == [repo] for l in lines(dr, 'threads.txt'))]
    if covering and not any(line in lines(dr, 'threads.txt') for dr in covering):
        open(os.path.join(covering[0], 'threads.txt'), 'a').write(line + '\n')
sys.exit(0)
