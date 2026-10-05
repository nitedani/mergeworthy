#!/usr/bin/env python3
"""stop-lint's watch check: after a GitHub post, a turn ends only with a live Monitor on a watcher's events.log.
Run: python3 tests/test_stop_lint.py (exit 0 = all pass)."""
import json, os, subprocess, sys, tempfile
HOOK = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'hooks', 'stop-lint.py')
def tool(name, inp, id): return {'type': 'assistant', 'message': {'content': [{'type': 'tool_use', 'name': name, 'id': id, 'input': inp}]}}
def result(id, text): return {'type': 'user', 'message': {'content': [{'type': 'tool_result', 'tool_use_id': id, 'content': text}]}}
def note(text): return {'type': 'user', 'message': {'content': text}}
SAY = {'type': 'assistant', 'message': {'content': [{'type': 'text', 'text': 'Posted the reply.'}]}}
POST = tool('Bash', {'command': 'gh api repos/o/r/issues/1/comments -F body=@/abs/drafts/x.md'}, 'p1')
MON = [tool('Monitor', {'command': 'tail -n 0 -F /w/events.log'}, 'm1'), result('m1', 'Monitor started (task abc123, expires in 3600s)')]
EXPIRED = note('<task-notification>\n<task-id>abc123</task-id>\n<event>[Monitor expired after 3600s with 0 events delivered.]</event>\n</task-notification>')
cases = [('post, no monitor', [POST, SAY], 2), ('post, live monitor', [POST] + MON + [SAY], 0),
         ('post, expired monitor', [POST] + MON + [EXPIRED, SAY], 2), ('no post', [SAY], 0)]
fails = 0
for name, events, want in cases:
    with tempfile.TemporaryDirectory() as home:
        t = os.path.join(home, 't.jsonl'); open(t, 'w').write(''.join(json.dumps(e) + '\n' for e in events))
        env = {**os.environ, 'HOME': home}; env.pop('CLAUDE_CODE_SUBAGENT_MODEL', None)
        got = subprocess.run([sys.executable, HOOK], input=json.dumps({'transcript_path': t, 'cwd': home}), text=True, capture_output=True, env=env).returncode
    if got != want: fails += 1; print(f'FAIL {name}: exit {got}, want {want}')
print(f'{len(cases) - fails}/{len(cases)} passed'); sys.exit(1 if fails else 0)
