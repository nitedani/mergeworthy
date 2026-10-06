#!/usr/bin/env python3
"""Claude Code PreToolUse hook (matcher: Agent, Task, delegate_task). Exit 2 blocks the launch; stderr goes to the agent.
One agent per job: a launch is registered under its job key (the ticket files its prompt names, else its title), and a second
launch of the same job is blocked until `agent-job done <key>` releases it. A turn that ended is not a finished agent: on T3 a
child wakes again when its background commands end, so only its terminal task status (read first) releases the job."""
import hashlib, json, os, re, sys, time
d = json.load(sys.stdin)
ti = d.get('tool_input', {}) or {}
text = ' '.join(str(ti.get(k) or '') for k in ('prompt', 'task', 'description', 'title'))
tickets = sorted(set(re.findall(r'(/[^\s`\'"]+\.md)\b', text)))
key = ' '.join(tickets) or (str(ti.get('title') or ti.get('description') or '').strip())
if not key:
    sys.exit(0)
jobs = os.path.expanduser('~/.claude/agent-jobs'); os.makedirs(jobs, exist_ok=True)
f = os.path.join(jobs, hashlib.sha256(key.encode()).hexdigest()[:16])
if os.path.exists(f):
    j = json.load(open(f))
    if time.time() - j.get('started', 0) < 24 * 3600:
        age = int((time.time() - j['started']) / 60)
        sys.stderr.write(
            f"BLOCKED: an agent for this job is already registered ({key[:160]}, started {age} min ago). One agent per job: "
            "read its status first (task_status, its latest runs); a turn that ended or 'waiting_for_children' means it is still alive. "
            "Continue it with a message instead of starting another. Only when its task is terminal and you have read its result, "
            f"release the job with `agent-job done '{key[:200]}'`, then launch.\n")
        sys.exit(2)
json.dump({'key': key, 'started': time.time()}, open(f, 'w'))
sys.exit(0)
