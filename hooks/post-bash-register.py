#!/usr/bin/env python3
"""Claude Code PostToolUse hook (matcher: Bash). A thread you just opened (`gh issue create`, `gh pr create`, a `gh api`
POST to repos/<o>/<r>/issues or /pulls) joins the threads.txt of the running watcher that covers its repo, so maintainer
comments on it are answered (mergeworthy:github-event). A comment on an existing thread registers nothing."""
import json, os, re, sys
d = json.load(sys.stdin)
cmd = d.get('tool_input', {}).get('command', '')
r = d.get('tool_response') or {}
out = r.get('stdout', '') if isinstance(r, dict) else str(r)
if not re.search(r'\bgh\s+(issue|pr)\s+create\b|\bgh\s+api\b.*\brepos/[\w.-]+/[\w.-]+/(issues|pulls)(\s|$|[\'"])', cmd):
    sys.exit(0)
reg = os.path.expanduser('~/.claude/gh-watch-dirs.txt')
dirs = [l.strip() for l in open(reg)] if os.path.exists(reg) else []
def lines(dr, f):
    p = os.path.join(dr, f)
    return [l.strip() for l in open(p)] if os.path.exists(p) else []
for repo, num in set(re.findall(r'github\.com/([\w.-]+/[\w.-]+)/(?:issues|pull)/(\d+)(?![\w#/-])', out)):
    line = f'{repo} {num}'
    covering = [dr for dr in dirs if repo in lines(dr, 'repos.txt') or any(l.split()[:1] == [repo] for l in lines(dr, 'threads.txt'))]
    if covering and not any(line in lines(dr, 'threads.txt') for dr in covering):
        open(os.path.join(covering[0], 'threads.txt'), 'a').write(line + '\n')
sys.exit(0)
