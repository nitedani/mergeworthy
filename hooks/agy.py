#!/usr/bin/env python3
"""Antigravity (agy) hook event argv[1], from the plugin in agy/: runs the hooks hooks/hooks.json gives Claude Code for that event and
tool, and prints their verdict as agy's JSON on stdout, always (agy lets a tool through on an empty stdout). Each hook reads what it
would under Claude Code: agy's tools under their Claude names and arguments, and agy's transcript rewritten as a Claude Code
transcript, ~/.mergeworthy/agy/<conversation>.jsonl, kept until the conversation's files are untouched for 14 days. A tool's
result reaches agy's transcript only after its PostToolUse, so a PostToolUse hook runs at the conversation's next event, which shows its
message by refusing that event's tool (or, at Stop, by continuing). agy's own subagents (swarm) run no hooks, so they are refused."""
import json, os, re, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import session_catalog
HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
TOOLS = {'run_command': 'Bash', 'read_file': 'Read', 'write_file': 'Write', 'edit_file': 'Edit'}
OWN_AGENTS = ('swarm',)
KEEP = 14 * 86400
HEADER = re.compile(r'\A(?:(?:Created|Completed) At: .*\n)*')
STARTED = re.compile(r'^Tool is running as a background task with task id: (\S+)$', re.M)
FINISHED = re.compile(r'content=Task id "([^"]+)" finished with \w+:\n(.*?)(?:\n\nLog: \S+)?\n</SYSTEM_MESSAGE>', re.S)


def claude_name(name):
    """agy's tool name as Claude Code's: mcp_<server>_<tool> as mcp__<server>_<tool>, which hooks.json's mcp__.*<tool> matchers take."""
    return TOOLS.get(name) or (f'mcp__{name[4:]}' if name.startswith('mcp_') else name)


def claude_input(name, args):
    a = args if isinstance(args, dict) else {}
    if name == 'run_command': return {'command': a.get('CommandLine', ''), 'description': a.get('toolSummary', '')}
    if name == 'read_file': return {'file_path': a.get('Path', '')}
    if name == 'write_file': return {'file_path': a.get('Path', ''), 'content': a.get('Content', '')}
    if name == 'edit_file': return {'file_path': a.get('Path', ''), 'old_string': a.get('Target', ''), 'new_string': a.get('Replacement', '')}
    return {k: v for k, v in a.items() if k != 'toolSummary'}


def call_id(session, step):
    """A tool call's id in both records, unique across conversations: agy's transcript names no call ids, but its call's result is the
    step the hooks' stepIdx names."""
    return f'agy-{session}-{step}'


def failed(name, step):
    """Whether the result step of a call failed: agy's error, or a command's non-zero exit, which Claude Code also reports as an error.
    The exit is agy's line above the command's output, which may hold such a line of its own."""
    head = (step.get('content') or '').split('\nCommand output:\n', 1)[0]
    return step.get('status') == 'ERROR' or name == 'run_command' and not re.search(r'^Command exited with code 0\.$', head, re.M)


def output(step):
    """A result step's text without agy's timestamps; a command's, its output alone."""
    text = HEADER.sub('', step.get('content') or '')
    return m[1] if (m := re.search(r'\nCommand output:\n(.*)\Z', text, re.S)) else '' if text.startswith('Command exited with code') else text


def finished(agy_steps):
    """Each ended background task's result text, by task id, from agy's message that it finished."""
    return {m[1]: m[2] for s in agy_steps if s.get('type') == 'SYSTEM_MESSAGE' and (m := FINISHED.search(s.get('content') or ''))}


def started(step):
    """The task id of a background command's result step (agy's RUNNING step naming its task), else None."""
    return m[1] if step.get('status') == 'RUNNING' and (m := STARTED.search(step.get('content') or '')) else None


def ended(step, ends):
    """A call's result step once the call ended: a background command's from ends, else None."""
    return step if not (t := started(step)) else {'status': 'DONE', 'content': ends[t]} if t in ends else None


def task_id(agy_id):
    """agy's task id as Claude Code's, a word."""
    return re.sub(r'\W', '', agy_id)


def whole(step):
    """Whether a read_file result shows the whole file: agy's "Showing lines 1-N of N" (a line range or a long file shows fewer)."""
    return bool(re.match(r'Showing lines 1-(\d+) of \1\n', output(step) + '\n'))


def skill_of(path):
    """The mergeworthy skill whose SKILL.md path is, else None: agy opens a skill by reading it."""
    m = re.search(r'/skills/([\w-]+)/SKILL\.md$', path or '')
    return m[1] if m and os.path.realpath(path) == os.path.realpath(os.path.join(ROOT, 'skills', m[1], 'SKILL.md')) else None


def steps(path):
    out = []
    for l in open(path, errors='replace'):
        try: s = json.loads(l)
        except ValueError: continue  # a line still being written
        if isinstance(s, dict) and isinstance(s.get('step_index'), int): out.append(s)
    return out


def claude_transcript(agy_steps, cwd, session):
    """agy's transcript steps as Claude Code transcript entries: a typed request, each model text and tool call, each call's result, a
    Stop hook's continuation reason, and a compaction (agy's CHECKPOINT step) as compact_boundary. A background command's result
    and its end are Claude Code's: a started task, then a <task-notification>."""
    calls, out = {}, []
    for s in agy_steps:
        at, n = s.get('created_at'), s['step_index']
        if s.get('type') == 'USER_INPUT':
            m = re.search(r'<USER_REQUEST>\n?(.*?)\n?</USER_REQUEST>', s.get('content') or '', re.S)
            out.append({'type': 'user', 'timestamp': at, 'cwd': cwd, 'message': {'role': 'user', 'content': m[1] if m else s.get('content') or ''}})
        elif s.get('type') == 'CHECKPOINT':
            out.append({'type': 'system', 'subtype': 'compact_boundary', 'timestamp': at})
        elif s.get('type') == 'SYSTEM_MESSAGE' and (m := FINISHED.search(s.get('content') or '')):
            status = 'failed' if failed('run_command', {'content': m[2]}) else 'completed'
            out.append({'type': 'user', 'timestamp': at, 'message': {'role': 'user', 'content': (
                f"<task-notification>\n<task-id>{task_id(m[1])}</task-id>\n<status>{status}</status>\n<summary>{output({'content': m[2]})}</summary>\n</task-notification>")}})
        elif s.get('type') == 'SYSTEM_MESSAGE':
            out.append({'type': 'user', 'timestamp': at, 'message': {'role': 'user', 'content': f"Stop hook feedback:\n{s.get('content') or ''}"}})
        elif s.get('type') == 'PLANNER_RESPONSE':
            text = [{'type': 'text', 'text': s['content']}] if s.get('content') else []
            for i, c in enumerate(s.get('tool_calls') or []):
                calls[n + 1 + i] = c
                text.append({'type': 'tool_use', 'id': call_id(session, n + 1 + i), 'name': claude_name(c.get('name', '')), 'input': claude_input(c.get('name'), c.get('args'))})
            out.append({'type': 'assistant', 'timestamp': at, 'cwd': cwd, 'message': {'role': 'assistant', 'model': s.get('model'), 'content': text}})
        elif n in calls:
            c = calls.pop(n)
            bad = not (bg := started(s)) and failed(c.get('name'), s)
            text = f'Command running in background with ID: {task_id(bg)}' if bg else s.get('error') or output(s)
            out.append({'type': 'user', 'timestamp': at, 'message': {'role': 'user', 'content': [
                {'type': 'tool_result', 'tool_use_id': call_id(session, n), 'is_error': bad, 'content': text}]}})
            if c.get('name') == 'read_file' and not bad and whole(s) and (k := skill_of((c.get('args') or {}).get('Path'))):
                out.append({'type': 'assistant', 'timestamp': at, 'cwd': cwd, 'message': {'role': 'assistant', 'content': [
                    {'type': 'tool_use', 'id': f'{call_id(session, n)}-skill', 'name': 'Skill', 'input': {'skill': f'mergeworthy:{k}'}}]}})
    return out


class Event:
    """One agy hook call: its input, the conversation's agy steps so far, and the Claude Code transcript written from them."""
    def __init__(self, d):
        self.d = d
        self.session = re.sub(r'[^\w-]', '', d.get('conversationId') or '') or 'none'
        self.dir = os.path.expanduser('~/.mergeworthy/agy')
        self.transcript = os.path.join(self.dir, f'{self.session}.jsonl')
        self.pending = os.path.join(self.dir, f'{self.session}.post')
        self.steps = steps(d['transcriptPath']) if os.path.isfile(d.get('transcriptPath') or '') else []
        os.makedirs(self.dir, exist_ok=True)
        tmp = f'{self.transcript}.{os.getpid()}'
        with open(tmp, 'w') as f:
            f.writelines(json.dumps(e) + '\n' for e in claude_transcript(self.steps, d.get('cwd'), self.session))
        os.replace(tmp, self.transcript)

    def base(self, event):
        return {'session_id': self.session, 'transcript_path': self.transcript, 'cwd': self.d.get('cwd'), 'hook_event_name': event}

    def call(self, name, args, step):
        return {'tool_name': claude_name(name), 'tool_input': claude_input(name, args), 'tool_use_id': call_id(self.session, step)}


def matched(event, tool):
    """The hooks/run commands hooks.json gives event for tool (any, for an event without matchers), in order."""
    groups = json.load(open(os.path.join(HERE, 'hooks.json')))['hooks'].get(event, [])
    return [h['command'].split('/hooks/run ', 1)[1].split() for g in groups if not g.get('matcher') or re.search(g['matcher'], tool or '')
            for h in g['hooks'] if '/hooks/run ' in h['command']]


def run(event, d):
    """Runs event's hooks on Claude Code input d: (the messages of those that blocked, their stdout)."""
    errs, outs = [], []
    env = {**os.environ, 'MERGEWORTHY_HOST': 'antigravity', 'CLAUDE_CODE_SESSION_ID': d['session_id']}
    for argv in matched(event, d.get('tool_name')):
        r = subprocess.run([os.path.join(HERE, 'run'), *argv], input=json.dumps(d), capture_output=True, text=True, env=env)
        if r.returncode == 2: errs.append(r.stderr.strip())
        if r.stdout.strip(): outs.append(r.stdout.strip())
    return errs, outs


def settle(ev):
    """Runs the PostToolUse hooks of each earlier call that ended in agy's transcript (a background command, once its task
    finished): their messages."""
    try: waiting = [json.loads(l) for l in open(ev.pending)]
    except OSError: return []
    ends, errs = finished(ev.steps), []
    done = {s['step_index']: r for s in ev.steps if (r := ended(s, ends))}
    for p in (p for p in waiting if p['step'] in done):
        s = done[p['step']]
        bad = failed(p['name'], s)
        d = {**ev.base('PostToolUseFailure' if bad else 'PostToolUse'), 'cwd': p['cwd'], **ev.call(p['name'], p['args'], p['step'])}
        d['tool_response'] = {'stdout': output(s), 'stderr': s.get('error') or '', 'interrupted': False} if p['name'] == 'run_command' else output(s)
        errs += [f"mergeworthy's check after your earlier call {p['name']} (step {p['step']}): {e}" for e in run(d['hook_event_name'], d)[0]]
    rest = [p for p in waiting if p['step'] not in done]
    with open(f'{ev.pending}.{os.getpid()}', 'w') as f: f.writelines(json.dumps(p) + '\n' for p in rest)
    os.replace(f'{ev.pending}.{os.getpid()}', ev.pending)
    return errs


def last_text(ev):
    return next((s.get('content') for s in reversed(ev.steps) if s.get('type') == 'PLANNER_RESPONSE' and s.get('content')), '')


def prune(folder):
    """Deletes the files of each conversation in folder (<conversation>.*) that are all untouched for KEEP."""
    convs = {}
    for f in os.scandir(folder): convs.setdefault(f.name.split('.')[0], []).append(f.path)
    for files in convs.values():
        try:
            if max(os.path.getmtime(f) for f in files) < time.time() - KEEP:
                for f in files: os.remove(f)
        except FileNotFoundError: pass  # another session's prune took it


def main(name, d):
    ev = Event(d)
    if name == 'SessionStart':
        prune(ev.dir)
        subprocess.run([os.path.join(HERE, 'bin-links')])
        session_catalog.record(ev.session, ROOT, 'startup')
        text = '\n'.join(run('SessionStart', {**ev.base('SessionStart'), 'source': 'startup'})[1])
        return {'injectSteps': [{'systemMessage': {'systemMessage': text}}] if text else []}
    c = d.get('toolCall') or {}
    if name == 'PostToolUse':
        if matched('PostToolUse', claude_name(c.get('name', ''))):
            with open(ev.pending, 'a') as f:
                f.write(json.dumps({'step': d.get('stepIdx'), 'name': c.get('name'), 'args': c.get('args'), 'cwd': d.get('cwd')}) + '\n')
        return {}
    after = settle(ev)  # at an event whose answer can carry their messages
    if name == 'PreToolUse':
        errs = (["mergeworthy: Antigravity's own subagents run without mergeworthy's checks: launch agents with T3's delegate_task "
                 "(mergeworthy:delegate step 4)."] if c.get('name') in OWN_AGENTS else
                run('PreToolUse', {**ev.base('PreToolUse'), **ev.call(c.get('name', ''), c.get('args'), d.get('stepIdx'))})[0])
        if after and not errs: after.append('This call was not run: run it again once you have acted on that.')
        return {'decision': 'deny', 'reason': '\n'.join(after + errs)} if after or errs else {'decision': 'allow'}
    errs = run('Stop', {**ev.base('Stop'), 'last_assistant_message': last_text(ev), 'stop_hook_active': (d.get('executionNum') or 0) > 0})[0]
    return {'decision': 'continue', 'reason': '\n'.join(after + errs)} if after or errs else {}


if __name__ == '__main__':
    event = sys.argv[1]
    try:
        verdict = main(event, json.load(sys.stdin))
    except Exception as e:  # a crash is a verdict too: agy lets a tool through on an empty stdout
        import traceback
        why = (f"mergeworthy's {event} check failed, so it can't tell whether this is allowed. Retry once; if it fails again, tell the "
               f"user, with this error:\n{''.join(traceback.format_exception(e))[-1500:]}")
        verdict = {'PreToolUse': {'decision': 'deny', 'reason': why}, 'Stop': {'decision': 'continue', 'reason': why},
                   'SessionStart': {'injectSteps': [{'systemMessage': {'systemMessage': why}}]}}.get(event, {})
    print(json.dumps(verdict))
