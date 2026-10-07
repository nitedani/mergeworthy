#!/usr/bin/env python3
"""Claude Code PreToolUse hook (matcher: Write, Edit, MultiEdit, delegate_task). Exit 2 blocks; stderr goes to the agent.
At Tier M or L (first line of <repo>-work/scope.md), code waits for prior art (1.3) and the design loop (1.4):
<repo>-work/prior-art.md and a <repo>-work/decisions/*.md must exist before an edit inside the repo or an implementation agent."""
import glob, json, os, re, subprocess, sys
d = json.load(sys.stdin)
ti = d.get('tool_input', {}) or {}
tool = d.get('tool_name', '')
cwd = d.get('cwd') or os.getcwd()
try:
    top = subprocess.run(['git', '-C', cwd, 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip()
except OSError:
    top = ''
if not top:
    sys.exit(0)
work = top + '-work'
try:
    tier = open(os.path.join(work, 'scope.md')).readline()
except OSError:
    sys.exit(0)
if not re.match(r'\s*Tier:\s*[ML]\b', tier):
    sys.exit(0)
if 'delegate_task' in tool:
    if str(ti.get('role') or '') != 'implementation':
        sys.exit(0)
else:
    path = os.path.realpath(str(ti.get('file_path') or ti.get('notebook_path') or ''))
    if not path.startswith(os.path.realpath(top) + os.sep):
        sys.exit(0)
missing = [n for n, ok in (('prior-art.md', os.path.isfile(os.path.join(work, 'prior-art.md'))),
                          ('decisions/*.md', bool(glob.glob(os.path.join(work, 'decisions', '*.md'))))) if not ok]
if missing:
    sys.stderr.write(f"BLOCKED: {tier.strip()} and {work} has no {' or '.join(missing)}. Before code: prior art (core 1.3: the web, "
                     "every project the user names, peers) into prior-art.md, then the design loop (open mergeworthy:design-loop) "
                     "into decisions/<name>.md.\n")
    sys.exit(2)
sys.exit(0)
