#!/usr/bin/env python3
"""Antigravity (agy) hook event argv[1], from the plugin in agy/: runs the hooks hooks/hooks.json gives Claude Code for that event and
tool, and prints their verdict as agy's JSON on stdout, always (agy lets a tool through on an empty stdout). Each hook reads what it
would under Claude Code: agy's tools under their Claude names and arguments, and agy's transcript rewritten as a Claude Code
transcript, ~/.mergeworthy/agy/<conversation>.jsonl, kept until the conversation's files are untouched for 14 days. A tool's
result reaches agy's transcript only after its PostToolUse, so a PostToolUse hook runs at the conversation's next event, which shows its
message by refusing that event's tool (or, at Stop, by continuing). agy's own subagents (swarm) run no hooks, so they are refused."""
import datetime, json, os, re, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import session_catalog
HERE = os.path.dirname(os.path.realpath(__file__))
ROOT = os.path.dirname(HERE)
TOOLS = {'run_command': 'Bash', 'read_file': 'Read', 'write_file': 'Write', 'edit_file': 'Edit'}
OWN_AGENTS = ('swarm',)
KEEP = 14 * 86400
LIVE = 600  # a step first seen within this many seconds of agy's time for it is timed when seen; an older one keeps agy's time
DIR = os.path.expanduser('~/.mergeworthy/agy')  # each conversation's Claude Code transcript (.jsonl), queued checks (.post), step times (.seen)
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


def conversation(agy_id):
    """agy's conversation id as the name of its files and its session id."""
    return re.sub(r'[^\w-]', '', agy_id or '') or 'none'


def call_id(session, step):
    """A tool call's id in both records, unique across conversations. The hook input names the call (toolCall.id) but agy's log
    doesn't, so the key both have is its result's step: the hook's stepIdx."""
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


def outcome(name, step):
    """How call name ended, from its result step (or agy's message that its task finished): whether it failed, its output, agy's error."""
    return {'failed': failed(name, step), 'output': output(step), 'error': step.get('error') or ''}


def started(step):
    """The task id of a background command's result step (agy's RUNNING step naming its task), else None."""
    return m[1] if step.get('status') == 'RUNNING' and (m := STARTED.search(step.get('content') or '')) else None


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


def stamp(us):
    """Microseconds since the epoch as Claude Code writes a time: UTC, with its fraction."""
    s, f = divmod(us, 10 ** 6)
    return time.strftime('%Y-%m-%dT%H:%M:%S', time.gmtime(s)) + f'.{f:06d}Z'


def first_seen(step, now):
    """The time to record for a step an event shows for the first time (microseconds): now, when that is within LIVE of agy's own
    time for it; else agy's time, so a reopened or migrated conversation's old steps keep their age for every reader of the times."""
    try: own = int(datetime.datetime.fromisoformat(step['created_at'].replace('Z', '+00:00')).timestamp() * 10 ** 6)
    except (KeyError, AttributeError, TypeError, ValueError): return now
    return now if now - own <= LIVE * 10 ** 6 else own


def claude_transcript(agy_steps, cwd, session, seen):
    """agy's transcript steps as Claude Code transcript entries: a typed request, each model text and tool call, each call's result, a
    Stop hook's continuation reason, and a compaction (agy's CHECKPOINT step) as compact_boundary. A background command's result
    and its end are Claude Code's: a started task, then a <task-notification>; the start's result is an error until the task ended with
    success, so a read through it (`sleep 5; cat AGENTS.md`) counts for shellcmd.files_read only then. A call agy logged no result for (declined, cancelled)
    failed with no result once a later step shows it ended, as Claude Code records one. Each entry's time is when an event first
    showed its step (seen, microseconds by step; first_seen), and at least a microsecond after the entry before it: agy's own times are whole
    seconds, which can't order a conversation's entries, nor a handoff's after the conversation it continues, for memory-prep's
    covered-until. Returns the entries and the outcome of each call that ended, by its step (a background command's once its task
    finished)."""
    calls, tasks, ends, out, last = {}, {}, {}, [], 0
    def at():
        nonlocal last
        last = max(seen[n], last + 1)
        return stamp(last)
    for s in agy_steps:
        n = s['step_index']
        for gone in sorted(k for k in calls if k < n):
            calls.pop(gone)
            o = ends[gone] = {'failed': True, 'output': '', 'error': 'The call ended with no result.'}
            out.append({'type': 'user', 'timestamp': at(), 'message': {'role': 'user', 'content': [
                {'type': 'tool_result', 'tool_use_id': call_id(session, gone), 'is_error': True, 'content': o['error']}]}})
        if s.get('type') == 'USER_INPUT':
            m = re.search(r'<USER_REQUEST>\n?(.*?)\n?</USER_REQUEST>', s.get('content') or '', re.S)
            out.append({'type': 'user', 'timestamp': at(), 'cwd': cwd, 'promptSource': 'typed',
                        'message': {'role': 'user', 'content': m[1] if m else s.get('content') or ''}})
        elif s.get('type') == 'CHECKPOINT':
            out.append({'type': 'system', 'subtype': 'compact_boundary', 'timestamp': at()})
        elif s.get('type') == 'SYSTEM_MESSAGE' and (m := FINISHED.search(s.get('content') or '')):
            o = outcome('run_command', {'content': m[2]})
            if m[1] in tasks:
                k, start = tasks.pop(m[1])
                ends[k], start['is_error'] = o, o['failed']
            out.append({'type': 'user', 'timestamp': at(), 'message': {'role': 'user', 'content': (
                f"<task-notification>\n<task-id>{task_id(m[1])}</task-id>\n<status>{'failed' if o['failed'] else 'completed'}</status>\n<summary>{o['output']}</summary>\n</task-notification>")}})
        elif s.get('type') == 'SYSTEM_MESSAGE':
            out.append({'type': 'user', 'timestamp': at(), 'message': {'role': 'user', 'content': f"Stop hook feedback:\n{s.get('content') or ''}"}})
        elif s.get('type') == 'PLANNER_RESPONSE':
            text = [{'type': 'text', 'text': s['content']}] if s.get('content') else []
            for i, c in enumerate(s.get('tool_calls') or []):
                calls[n + 1 + i] = c
                text.append({'type': 'tool_use', 'id': call_id(session, n + 1 + i), 'name': claude_name(c.get('name', '')), 'input': claude_input(c.get('name'), c.get('args'))})
            out.append({'type': 'assistant', 'timestamp': at(), 'cwd': cwd, 'message': {'role': 'assistant', 'model': s.get('model'), 'content': text}})
        elif n in calls:
            c = calls.pop(n)
            if bg := started(s):
                bad, text = True, f'Command running in background with ID: {task_id(bg)}'
            else:
                o = ends[n] = outcome(c.get('name'), s)
                bad, text = o['failed'], o['error'] or o['output']
            result = {'type': 'tool_result', 'tool_use_id': call_id(session, n), 'is_error': bad, 'content': text}
            if bg: tasks[bg] = n, result
            out.append({'type': 'user', 'timestamp': at(), 'message': {'role': 'user', 'content': [result]}})
            if c.get('name') == 'read_file' and not bad and whole(s) and (k := skill_of((c.get('args') or {}).get('Path'))):
                out.append({'type': 'assistant', 'timestamp': at(), 'cwd': cwd, 'message': {'role': 'assistant', 'content': [
                    {'type': 'tool_use', 'id': f'{call_id(session, n)}-skill', 'name': 'Skill', 'input': {'skill': f'mergeworthy:{k}'}}]}})
    return out, ends


def line(entry):
    """One transcript entry as Claude Code writes it, compact JSON on one line, which the hooks' byte filters ("is_error":true) match."""
    return json.dumps(entry, separators=(',', ':')) + '\n'


class Event:
    """One agy hook call: its input, the conversation's agy steps so far, and the Claude Code transcript written from them."""
    def __init__(self, d):
        self.d = d
        self.session = conversation(d.get('conversationId'))
        self.transcript = os.path.join(DIR, f'{self.session}.jsonl')
        self.pending = os.path.join(DIR, f'{self.session}.post')
        self.steps = steps(d['transcriptPath']) if os.path.isfile(d.get('transcriptPath') or '') else []
        os.makedirs(DIR, exist_ok=True)
        times = os.path.join(DIR, f'{self.session}.seen')
        try: seen = {int(k): v for k, v in json.load(open(times)).items()}
        except (OSError, ValueError, AttributeError): seen = {}  # a conversation from before step times: its steps are seen now
        now = time.time_ns() // 1000
        if new := {s['step_index']: first_seen(s, now) for s in self.steps if s['step_index'] not in seen}:
            seen.update(new)
            with open(f'{times}.{os.getpid()}', 'w') as f: json.dump(seen, f)
            os.replace(f'{times}.{os.getpid()}', times)
        entries, self.outcomes = claude_transcript(self.steps, d.get('cwd'), self.session, seen)
        tmp = f'{self.transcript}.{os.getpid()}'
        with open(tmp, 'w') as f:
            f.writelines(line(e) for e in entries)
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


def context(out):
    """What a hook's stdout gives the model as Claude Code reads it: its hookSpecificOutput.additionalContext, else the text itself."""
    try: return json.loads(out)['hookSpecificOutput']['additionalContext']
    except (ValueError, KeyError, TypeError): return out


def run(event, d):
    """Runs event's hooks on Claude Code input d: what they said, (the messages of those that blocked, their context)."""
    errs, said = [], []
    env = {**os.environ, 'MERGEWORTHY_HOST': 'antigravity', 'CLAUDE_CODE_SESSION_ID': d['session_id']}
    for argv in matched(event, d.get('tool_name')):
        r = subprocess.run([os.path.join(HERE, 'run'), *argv], input=json.dumps(d), capture_output=True, text=True, env=env)
        if r.returncode == 2: errs.append(r.stderr.strip())
        if r.stdout.strip(): said.append(context(r.stdout.strip()))
    return errs, said


def settle(ev):
    """Runs the PostToolUse hooks of each earlier call that has an outcome (a background command, once its task finished): what
    they said, blocks and context alike, which the model gets in this event's answer."""
    try: waiting = [json.loads(l) for l in open(ev.pending)]
    except OSError: return []
    errs, done = [], ev.outcomes
    for p in (p for p in waiting if p['step'] in done):
        o = done[p['step']]
        d = {**ev.base('PostToolUseFailure' if o['failed'] else 'PostToolUse'), 'cwd': p['cwd'], **ev.call(p['name'], p['args'], p['step'])}
        d['tool_response'] = {'stdout': o['output'], 'stderr': o['error'], 'interrupted': False} if p['name'] == 'run_command' else o['output']
        blocks, said = run(d['hook_event_name'], d)
        errs += [f"mergeworthy's check after your earlier call {p['name']} (step {p['step']}): {e}" for e in blocks + said]
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


def answer(event, said):
    """agy's JSON for event from what the checks said: PreToolUse refuses the call with it, Stop continues the turn with it,
    SessionStart puts it in the conversation; with nothing said, each goes ahead, said so explicitly where agy reads silence as yes."""
    text = '\n'.join(said)
    if event == 'SessionStart': return {'injectSteps': [{'systemMessage': {'systemMessage': text}}] if text else []}
    if event == 'PreToolUse': return {'decision': 'deny', 'reason': text} if text else {'decision': 'allow'}
    if event == 'Stop': return {'decision': 'continue', 'reason': text} if text else {}
    return {}


def main(name, d):
    ev = Event(d)
    if name == 'SessionStart':
        # of Claude Code's SessionStart duties (hooks/session-start), the ones agy needs: old files pruned, the bin/ commands on
        # PATH, the catalog recorded, and the hooks hooks.json runs through hooks/run; session-start itself, which prints the
        # always-on rules agy loads from agy/rules, doesn't run
        prune(DIR)
        subprocess.run([os.path.join(HERE, 'bin-links')])
        session_catalog.record(ev.session, ROOT, 'startup')
        return answer(name, run('SessionStart', {**ev.base('SessionStart'), 'source': 'startup'})[1])
    if not os.path.exists(session_catalog.path(ev.session)):  # a conversation reopened (session/load, resume) after its record went
        session_catalog.record(ev.session, ROOT, 'resume')
    c = d.get('toolCall') or {}
    if name == 'PostToolUse':
        if matched('PostToolUse', claude_name(c.get('name', ''))):
            with open(ev.pending, 'a') as f:
                f.write(json.dumps({'step': d.get('stepIdx'), 'name': c.get('name'), 'args': c.get('args'), 'cwd': d.get('cwd')}) + '\n')
        return answer(name, [])
    after = settle(ev)  # at an event whose answer can carry their messages
    if name == 'PreToolUse':
        errs = (["mergeworthy: Antigravity's own subagents run without mergeworthy's checks: launch agents with T3's delegate_task "
                 "(mergeworthy:delegate step 4)."] if c.get('name') in OWN_AGENTS else
                run('PreToolUse', {**ev.base('PreToolUse'), **ev.call(c.get('name', ''), c.get('args'), d.get('stepIdx'))})[0])
        if after and not errs: after.append('This call was not run: run it again once you have acted on that.')
        return answer(name, after + errs)
    if name == 'Stop':
        return answer(name, after + run('Stop', {**ev.base('Stop'), 'last_assistant_message': last_text(ev), 'stop_hook_active': (d.get('executionNum') or 0) > 0})[0])
    raise ValueError(f'no such agy hook event: {name}')


if __name__ == '__main__':
    event = sys.argv[1]
    try:
        verdict = main(event, json.load(sys.stdin))
    except Exception as e:  # a crash is a verdict too: agy lets a tool through on an empty stdout
        import traceback
        verdict = answer(event, [f"mergeworthy's {event} check failed, so it can't tell whether this is allowed. Retry once; if it fails "
                                 f"again, tell the user, with this error:\n{''.join(traceback.format_exception(e))[-1500:]}"])
    print(json.dumps(verdict))
