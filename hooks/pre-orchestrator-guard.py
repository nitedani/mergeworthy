#!/usr/bin/env python3
"""Claude Code PreToolUse hook (matcher: Write, Edit, MultiEdit, NotebookEdit, Bash). Exit 2 blocks; stderr goes to the agent.
The orchestrator plans, briefs and decides; it never edits, writes or formats repo files, commits, or runs build/test work (core 1.1.14).
This blocks those calls in the orchestrator session, so the work goes to a briefed implementer.

Who is the orchestrator? Not a delegated agent. A session is delegated when either
  - the hook input carries agent_id or agent_type (a Claude Code subagent), or
  - the first user message in its transcript starts "Act as the <role> sub-agent for this task" (a T3 Code delegate_task child,
    which runs as its own session; stop-lint recognises children the same way).
Everything else is the orchestrator. Limits: a delegated agent whose brief does not open with that sentence, and a subagent runtime that
sends neither field, look like the orchestrator and are blocked (brief delegated work with the standard opening). The Bash check is a
pattern match on the command text, not a parse: a script that writes files from inside (python3 build.py) passes, and a rare lookup that
matches a pattern is blocked. Set MERGEWORTHY_ORCHESTRATOR_WRITES=allow (environment or ~/.mergeworthy/settings.env) to turn it off.
Allowed to the orchestrator: files under an artifact root (<name>-work/), ~/.claude, ~/.mergeworthy, any file outside a git worktree,
and read-only commands."""
import json, os, re, subprocess, sys

d = json.load(sys.stdin)
ti = d.get('tool_input', {}) or {}
tool = d.get('tool_name', '')
cwd = d.get('cwd') or os.getcwd()
home = os.path.expanduser('~')

def setting():
    f = os.path.join(home, '.mergeworthy', 'settings.env')
    saved = dict(l.strip().split('=', 1) for l in open(f) if '=' in l) if os.path.exists(f) else {}
    return os.environ.get('MERGEWORTHY_ORCHESTRATOR_WRITES') or saved.get('MERGEWORTHY_ORCHESTRATOR_WRITES', '')

def delegated():
    if d.get('agent_id') or d.get('agent_type'):
        return True
    try:
        for l in open(d['transcript_path']).readlines()[:20]:
            if '"type":"user"' not in l.replace(' ', ''):
                continue
            c = (json.loads(l).get('message') or {}).get('content') or ''
            if isinstance(c, list):
                c = ' '.join(b.get('text', '') for b in c if isinstance(b, dict))
            return re.match(r'\s*Act as the [\w-]+ sub-agent for this task', c) is not None
    except (OSError, KeyError, ValueError):
        pass
    return False

def allowed_path(p):
    p = os.path.realpath(os.path.join(cwd, os.path.expanduser(p)))
    if any(part.endswith('-work') for part in p.split(os.sep)):
        return True
    if any(p == r or p.startswith(r + os.sep) for r in (os.path.join(home, '.claude'), os.path.join(home, '.mergeworthy'))):
        return True
    top = subprocess.run(['git', '-C', os.path.dirname(p) if os.path.isdir(os.path.dirname(p)) else cwd, 'rev-parse', '--show-toplevel'],
                         capture_output=True, text=True).stdout.strip()
    return not top  # outside any git worktree

MSG = ("BLOCKED by pre-orchestrator-guard: {what}. The orchestrator decides and briefs; it does not edit, write or format repo files, "
       "commit, or run build/test/browser work (core 1.1.14). Brief an implementer: open mergeworthy:delegating, write the brief "
       "(goal, verified facts, steps, acceptance) under the artifact root, and delegate it. Files under <name>-work/ and memory are yours.\n")

def block(what):
    sys.stderr.write(MSG.format(what=what)); sys.exit(2)

if setting() == 'allow' or delegated():
    sys.exit(0)

if tool != 'Bash':
    p = str(ti.get('file_path') or ti.get('notebook_path') or '')
    if p and not allowed_path(p):
        block(f"{tool} on {p}")
    sys.exit(0)

cmd = str(ti.get('command') or '')
# Drop heredoc bodies and quoted text so words inside a message or argument are not read as commands
cmd = re.sub(r'\\\n', ' ', cmd)
lines, term = [], None
for l in cmd.split('\n'):
    if term is not None:
        if l.strip() == term:
            term = None
        continue
    h = re.search(r"<<-?\s*['\"]?(\w+)['\"]?", l)
    if h:
        term = h.group(1)
    lines.append(l)
bare = re.sub(r"'[^']*'|\"(?:[^\"\\]|\\.)*\"", "''", ' '.join(lines))
WRITE = [
    (r'\bgit\s+(?:-\S+\s+\S+\s+)*(commit|add|apply|am|cherry-pick|rebase|merge|restore|revert|mv|rm)\b', 'git {0}'),
    (r'\b(?:sed|perl)\s+(?:-\S+\s+)*-[A-Za-z]*i', 'in-place edit'),
    (r'\b(?:prettier|eslint|biome|ruff|black|gofmt|rustfmt)\b[^|;&]*\s(?:--write|--fix|-w|format)\b', 'formatter'),
    (r'\b(?:npm|pnpm|yarn|bun)\s+(?:run\s+)?(?:build|test|lint|typecheck|check|format|e2e)\b', 'build/test run'),
    (r'(?<![\w/.-])(?:tsc|vitest|jest|playwright|pytest|cargo\s+(?:build|test|clippy)|go\s+(?:build|test)|make)\b', 'build/test run'),
]
for rx, label in WRITE:
    m = re.search(rx, bare)
    if m:
        block(f"`{(label or '').format(*m.groups()) or m.group(0)}` in Bash")
# File writes: redirects, tee, cp/mv/install, and scripts that open a file for writing; allowed when every target is allowed
targets = [t for t in re.findall(r'(?<![<>&\d])>>?\s*([^\s|;&<>()]+)', bare) if not t.startswith('&')]
for m in re.finditer(r'\b(?:tee(?:\s+-a)?|cp|mv|install)\s+([^|;&<>]*)', bare):
    args = [a for a in m.group(1).split() if not a.startswith('-')]
    targets += args if m.group(0).startswith('tee') else args[-1:]  # cp/mv/install: the destination is last
for t in targets:
    t = t.strip("'\"")
    if t and t != '/dev/null' and not t.startswith('/dev/') and not allowed_path(t):
        block(f"Bash writes {t}")
if re.search(r"\b(?:python3?|node|ruby)\b[^|;&]*(?:open\([^)]*['\"][wa]|write_?[Ff]ile|\.write_text|fs\.write)", ' '.join(lines)):
    block("a script that writes files, run from Bash")
sys.exit(0)
