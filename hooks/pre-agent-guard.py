#!/usr/bin/env python3
"""Claude Code PreToolUse hook (matcher: Agent). mergeworthy:delegate: while the local model is available, read-only exploration goes to
the local model (a T3 Code child on Local Claude), not to a Claude subagent. Exit 2 blocks; stderr goes to the agent.
Blocks an Agent call that explores read-only (an Explore agent, or a prompt that says read-only / find / list every / where…)
when: local_model=on, `claude-local` is installed, `claude-usage --mode` isn't `off`, and `serve.sh` doesn't see the GPU taken.
Reviews that gate a post (the prompt asks for a final `CLEAN`) go to the local model the same way. A prompt with a
`NEEDS-CLAUDE:` line saying why the local model can't do it (judgment, design) passes. A Haiku subagent is always blocked.
Inert in a session that runs on the local model itself (CLAUDE_CODE_SUBAGENT_MODEL=local): its subagents are already
the local model, so there is nothing to delegate to."""
import json, os, re, shutil, subprocess, sys

d = json.load(sys.stdin)
i = d.get('tool_input') or {}
prompt = i.get('prompt') or ''
f = os.path.expanduser('~/.mergeworthy/settings.env')
saved = dict(l.strip().split('=', 1) for l in open(f) if '=' in l) if os.path.exists(f) else {}
if (os.environ.get('MERGEWORTHY_LOCAL_MODEL') or saved.get('MERGEWORTHY_LOCAL_MODEL', 'off')) != 'on': sys.exit(0)
if (os.environ.get('CLAUDE_CODE_SUBAGENT_MODEL') or '').lower() == 'local': sys.exit(0)  # the session is the local model; its subagents already are
if (i.get('model') or '').lower() == 'haiku':
    print("No Haiku subagents: pair with the local model instead (it works and you review, or you write and it reviews: "
          "a gate review), or use the session's own model.", file=sys.stderr); sys.exit(2)
if not shutil.which('claude-local') or 'NEEDS-CLAUDE:' in prompt: sys.exit(0)
review = re.search(r'\bCLEAN\b', prompt)
explore = review or i.get('subagent_type') == 'Explore' or re.search(
    r'\bread-only\b|\b(find|list) (every|all)\b|\bwhere (is|are|does)\b|\bwhich files\b|\bexplore\b|\bmap (the|every)\b', prompt, re.I)
if not explore: sys.exit(0)
def run(*a):
    try: return subprocess.run(a, capture_output=True, text=True, timeout=20)
    except Exception: return None
mode = run('claude-usage', '--mode')
if mode is None or mode.returncode != 0 or mode.stdout.strip() == 'off': sys.exit(0)
serve = os.path.expanduser('~/local-llm/serve.sh')
if os.path.exists(os.path.expanduser('~/local-llm/.disabled')): sys.exit(0)
# the server already up is ours (the model is loaded); otherwise ask serve.sh whether another program has the GPU
busy = run('bash', '-c', f'source <(sed -n "/^up()/,/^processing()/p" {serve}); DIR=~/local-llm; URL=http://127.0.0.1:${{LLM_PORT:-8080}}; ! up && gpu_taken')
if busy is not None and busy.returncode == 0: sys.exit(0)  # a game or another program has the GPU: Claude does it
if review:
    print("Gate reviews go to the local model while it's available: a ticket with `## File` = the draft (plus Facts and Scope), "
          "a T3 Code `delegate_task` child on the Local Claude instance (model `local`, runtimeMode full-access); "
          "check each finding yourself, and write its final CLEAN to the review output for gate-pass.", file=sys.stderr); sys.exit(2)
print("Read-only exploration goes to the local model while it's available (mergeworthy:delegate): "
      "give the brief to a T3 Code `delegate_task` child on the Local Claude instance (model `local`, "
      "runtimeMode full-access), then check two or three of its path:line citations. If this needs Claude (judgment, design, "
      "maintainer-facing wording), add a line `NEEDS-CLAUDE: <why>` to the prompt.", file=sys.stderr)
sys.exit(2)
