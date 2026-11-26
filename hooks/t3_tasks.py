#!/usr/bin/env python3
"""T3 Code: whether the session runs under it, and its delegated tasks as the session's transcript reports them: its tool calls
and results (delegate_task, task_status, t3_thread_send) and T3's notices. A thread is all its tasks: the first, each message sent
to it, each turn T3 continues on its own (provider-continuation)."""
import json, os, re

# T3's notice is `Delegated task <id>[ (<title>)][ in child thread <thread id>] [<status>]:` with its result, or
# `Delegated task <id> reached a terminal state` for a task it no longer knows (its formatter, delegatedCompletionWakeDetail)
NOTICE = re.compile(r'(?:\A|\n\n)Delegated task (\S+)(?: \(.*?\))?(?: in child thread \S+)? (?:reached a terminal state|\[(\w+)\]:?)')

def notices(text):
    """(task id, status or None, its result) for each notice of T3's message, which starts with one and holds one per finished task,
    each after a blank line: a result quoting a notice on a line of its own stays that task's result"""
    ms = list(NOTICE.finditer(text)) if NOTICE.match(text) else []
    for m, nxt in zip(ms, ms[1:] + [None]): yield m[1], m[2], text[m.end():nxt.start() if nxt else len(text)]

# What the harness, T3, a hook or the watcher writes into a session as a user message: a tag (`<task-notification>`), not an autolink (`<https://…>`)
TAG = re.compile(r'<[A-Za-z][\w-]*[\s>/]')
NOTICES = ('Stop hook feedback', 'Watcher events in ', 'Delegated task ', 'Skill /', 'Base directory for this skill',
           'This session is being continued', '[Your previous response had no visible output', '[T3 Code: ')


def typed(content):
    """The text a person typed in a user entry's content, or '' for a tool result or a machine's notice."""
    t = content if isinstance(content, str) else ' '.join(x.get('text', '') for x in content or [] if isinstance(x, dict) and x.get('type') == 'text')
    return '' if not t.strip() or t.lstrip().startswith(NOTICES) or TAG.match(t.lstrip()) else t


def under_t3():
    """The hook's session was opened by T3 Code, so T3's MCP tools (delegate_task) are its own: T3 sets T3CODE_THREAD_ID in the
    environment of every Claude session it opens, and passes its MCP server outside the command line."""
    return bool(os.environ.get('T3CODE_THREAD_ID'))


def driver(instance, kind=None):
    """The driver T3 Code runs provider instance `instance` with (claudeAgent, codex, antigravity), from its settings; else the driver
    `kind` the launch names, else the id itself, as a built-in instance's id is its driver's."""
    try: return json.load(open(os.path.expanduser('~/.t3/userdata/settings.json')))['providerInstances'][instance]['driver']
    except (OSError, ValueError, KeyError, TypeError): return kind or instance


def result(content):
    """A T3 tool's result, the JSON object in its text (alone, or in content blocks as a PostToolUse hook gets it), else None."""
    r = ''.join(x.get('text', '') for x in content if isinstance(x, dict)) if isinstance(content, list) else str(content or '')
    try: r = json.loads(r)
    except ValueError: return None
    return r if isinstance(r, dict) else None


class Observer:
    """Fed each entry of a session's transcript in turn, result() is (status, thread, seen, launched): each task's (status, title),
    in the order last heard of; the name of its thread; the tasks heard of since the user's last message; whether the session
    launched or messaged one (a read with task_status alone doesn't). json() is what it has seen, as Observer(j) takes it back."""
    def __init__(self, j=None):
        j = j or {}
        self.titles, self.status, self.thread = j.get('titles', {}), j.get('status', {}), j.get('thread', {})
        self.seen, self.launched = set(j.get('seen', ())), j.get('launched', False)

    def json(self):
        return {'titles': self.titles, 'status': self.status, 'thread': self.thread, 'seen': sorted(self.seen), 'launched': self.launched}

    def feed(self, e):
        titles, status, thread = self.titles, self.status, self.thread
        c = (e.get('message') or {}).get('content')
        if e.get('type') == 'user' and isinstance(c, str) and not c.startswith('<'):
            # T3's own completion notice isn't the user (typed): it marks its task terminal
            for task, st, res in notices(c):
                # a sub-agent whose turn ends while its own background work runs says so, and T3 continues it later: not finished
                waits = re.search(r"\b(?:still running|I'll (?:continue|wait|resume)|I will (?:continue|wait|resume)|I'm waiting|wakes? (?:me )?when)\b", res[:400], re.I)
                status[task] = ('waiting' if waits else st or 'completed', status.pop(task, ('', ''))[1])
        if e.get('type') == 'user' and typed(c): self.seen = set()
        for b in c if isinstance(c, list) else []:
            if not isinstance(b, dict): continue
            if b.get('type') == 'tool_use' and re.search(r'(delegate_task|task_status|thread_send)$', b.get('name', '')):
                titles[b['id']] = (b.get('name', '').endswith('task_status'), str((b.get('input') or {}).get('title') or ''))
                self.launched = self.launched or not titles[b['id']][0]
            elif b.get('type') == 'tool_result' and b.get('tool_use_id') in titles:
                r = result(b.get('content')) or {}
                if r.get('threadId') and not r.get('taskId'):  # a message sent to a task's thread runs it again
                    r = {'taskId': r['threadId'] + '#sent', 'childThreadId': r['threadId'], 'status': r.get('status') or 'running'}
                if r.get('taskId'):
                    is_read, title = titles[b['tool_use_id']]
                    old = status.pop(r['taskId'], ('', ''))
                    status[r['taskId']] = (str(r.get('status') or ''), title or old[1])
                    thread[r['taskId']] = str(r.get('childThreadId') or r.get('threadId') or thread.get(r['taskId']) or r['taskId'])  # a follow-up message is a new task of its thread
                    self.seen.add(r['taskId'])

    def result(self):
        def name_of(i):
            m = re.search(r'%25253A([^%]+)%3Aordinal', i)  # a continuation's id holds its thread's, encoded twice
            return (m[1] if m else self.thread.get(i, i).rsplit('%3A', 1)[-1]).lower()
        return {i: tuple(s) for i, s in self.status.items()}, {i: name_of(i) for i in self.status}, self.seen, self.launched
