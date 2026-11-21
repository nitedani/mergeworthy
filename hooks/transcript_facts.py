#!/usr/bin/env python3
"""What a Claude Code session's transcript says so far, for stop-lint: read(path) -> Facts. The facts of the lines a stop read are
kept per transcript (~/.claude/mergeworthy-folds), so the next stop reads only the lines written since (Claude Code only appends);
when the kept facts may not match the file (another version of this code, a replaced or shrunk file, one whose first 4 KiB or the
64 KiB before the kept offset changed, an unreadable keep), every line is read again."""
import collections, datetime, hashlib, json, os, re, time
import report, t3_tasks

_DIR = os.path.expanduser('~/.claude/mergeworthy-folds')
POST = re.compile(r'\bgh\b[^\n]*(body-file|body=@|--input|\s-F\s)')
READ = re.compile(r'\bgh\s+api\s+graphql\b|\bgh\s+api\b[^\n]*\s(?:-X\s*|--method[\s=])GET\b')  # a field makes `gh api` a POST, but these read
RUN_GH = re.compile(r'(?:^|[;&|(]|\s--)\s*gh\s')  # gh where the shell runs it: a line's start, after ; & | ( or mw post's --
QUOTED = re.compile(r"'[^'\n]*'|\"(?:[^\"\\\n]|\\.)*\"|`[^`\n]*`")  # text in quotes or backticks is data, not a command


def run_lines(cmd):  # the command's lines minus heredoc bodies, which are a file's text
    end = None
    for l in cmd.split('\n'):
        if end is not None:
            if l.strip() == end: end = None
            continue
        doc = re.search(r'<<-?\s*[\'"]?(\w+)', l)
        end = doc and doc.group(1)
        yield l


def posts(cmd):
    return any(POST.search(l) and RUN_GH.search(QUOTED.sub("''", l)) and not (READ.search(l) and 'mutation' not in cmd) for l in run_lines(cmd))


def opening(l):  # a user line's typed text ('' for a tool result's list, or a line that isn't JSON)
    try: c = (json.loads(l).get('message') or {}).get('content')
    except (ValueError, AttributeError): return ''
    return c if isinstance(c, str) else ''


class Facts:
    """The session's facts so far, fed one transcript line at a time. Every field is plain JSON (a set kept as a dict), so json()
    saves it and Facts(j) takes it back."""
    def __init__(self, j=None):
        j = j or {}
        self.posted, self.posted_at = j.get('posted', False), j.get('posted_at', '')  # posted_at: the time of the session's last post
        # the background commands and Monitors this session started, and the ones that ended
        self.monitor_ids, self.monitors, self.dead, self.wakers = (j.get(k, {}) for k in ('monitor_ids', 'monitors', 'dead', 'wakers'))
        self.commands, self.monitor_cmds = j.get('commands', []), j.get('monitor_cmds', [])
        self.opened_task, self.delegated = j.get('opened_task', False), j.get('delegated', False)
        self.last, self.last_user = j.get('last', ''), j.get('last_user', '')  # the agent's last text; the user's own last message (t3_tasks.typed)
        self.forks_before_last = j.get('forks_before_last', {})  # the GENUINE-FORK lines of every text the agent wrote but the last
        self.child_opening, self.head_lines = j.get('child_opening', False), j.get('head_lines', 0)  # the first 20 lines open a sub-agent's brief
        self.models = j.get('models', {})  # each Claude model id the session ran on or launched an agent on: the time of its last line
        self.at = j.get('at', '')  # the time of the transcript's latest line
        self.tail_sdk = collections.deque(j.get('tail_sdk', []), maxlen=20)  # for each of the last 20 lines: the SDK CLI wrote it
        self.tasks = t3_tasks.Observer(j.get('tasks'))

    def json(self):
        return {**{k: v for k, v in vars(self).items() if k not in ('tail_sdk', 'tasks')}, 'tail_sdk': list(self.tail_sdk), 'tasks': self.tasks.json()}

    def said(self, fin=None):
        """(the GENUINE-FORK lines of every text but the last, the last text), the final message fin from the hook's input counted
        as the last text: the transcript may not hold it yet."""
        before, last = set(self.forks_before_last), self.last
        if isinstance(fin, str) and fin.strip():
            if last.strip() and last.strip() != fin.strip(): before |= report.forks(last)
            last = fin
        return before, last

    def ran(self, model, at):
        if isinstance(model, str) and model.startswith('claude-'): self.models[model] = at

    def recent_models(self, hours=24):
        """The ids of self.models last seen in the hours before the transcript's latest line; one with no time counts."""
        since = datetime.datetime.fromisoformat(self.at) - datetime.timedelta(hours=hours) if self.at else None
        return {m for m, at in self.models.items() if not (since and at) or datetime.datetime.fromisoformat(at) >= since}

    def feed(self, line):
        if self.head_lines < 20:
            self.head_lines += 1
            if '"type":"user"' in line.replace(' ', '') and 'sub-agent for this task' in line and re.match(r'Act as the [\w-]+ sub-agent for this task', opening(line)):
                self.child_opening = True
        self.tail_sdk.append('"entrypoint":"sdk-cli"' in line)
        try:
            e = json.loads(line)
        except ValueError:
            return  # one bad or half-written line must not disable the check
        if not isinstance(e, dict): return
        self.tasks.feed(e)
        self.at = e.get('timestamp') or self.at
        c = (e.get('message') or {}).get('content')
        if e.get('type') == 'user':
            texts = [c] if isinstance(c, str) else [x.get('text', '') if x.get('type') == 'text' else json.dumps(x.get('content')) for x in c or [] if isinstance(x, dict)]
            for x in c if isinstance(c, list) else []:
                if isinstance(x, dict) and x.get('tool_use_id') in self.monitor_ids:
                    m = re.search(r'Monitor started \(task (\w+)', json.dumps(x.get('content')))
                    if m: self.monitors[m.group(1)] = 1
            typed = c if isinstance(c, str) else ' '.join(x.get('text', '') for x in c or [] if isinstance(x, dict) and x.get('type') == 'text')
            self.last_user = t3_tasks.typed(typed) or self.last_user
            for t in texts:
                for tid in re.findall(r'<task-id>(\w+)</task-id>[\s\S]*?Monitor expired', t or ''): self.dead[tid] = 1
                for tid, st in re.findall(r'<task-id>(\w+)</task-id>[\s\S]*?<status>(\w+)</status>', t or ''):
                    if st in ('completed', 'failed', 'killed', 'stopped', 'cancelled', 'canceled', 'error'): self.dead[tid] = 1
                for tid in re.findall(r'Command running in background with ID: (\w+)|Monitor started \(task (\w+)', t or ''):
                    self.wakers[tid[0] or tid[1]] = 1
            self.opened_task = self.opened_task or '<command-name>/mergeworthy:task</command-name>' in typed
        if e.get('type') == 'assistant':
            at = e.get('timestamp') or ''
            self.ran((e.get('message') or {}).get('model'), at)
            for x in c if isinstance(c, list) else []:
                if not isinstance(x, dict) or x.get('type') != 'tool_use': continue
                i = x.get('input') or {}
                if x.get('name') in ('Agent', 'Task'): self.ran(f"claude-{i['model']}" if i.get('model') in ('opus', 'sonnet', 'haiku', 'fable') else i.get('model'), at)  # an alias: the family, any version
                if x.get('name', '').endswith('delegate_task'): self.ran((i.get('target') or {}).get('model'), at)
                if x.get('name') == 'Bash' and posts(i.get('command', '')): self.posted, self.posted_at = True, e.get('timestamp') or ''
                if x.get('name') == 'Bash': self.commands.append(i.get('command', ''))
                if x.get('name') == 'Skill' and str(i.get('skill', '')) in ('task', 'mergeworthy:task'): self.opened_task = True
                if x.get('name') == 'Monitor' and 'events.log' in i.get('command', ''):
                    self.monitor_ids[x.get('id')] = 1
                    self.monitor_cmds.append(i.get('command', ''))
                if x.get('name') in ('Agent', 'Task') or re.search(r'(delegate_task|t3_thread_launch)$', x.get('name', '')): self.delegated = True
                if x.get('name') == 'TaskStop': self.dead[i.get('task_id') or i.get('shell_id') or ''] = 1
            if isinstance(c, list):
                t = ''.join(x.get('text', '') for x in c if isinstance(x, dict) and x.get('type') == 'text')
                if t.strip():
                    if self.last.strip(): self.forks_before_last.update(dict.fromkeys(report.forks(self.last), 1))
                    self.last = t


def _version():  # the code whose output a kept fold holds
    h = hashlib.sha256()
    for m in (__file__, t3_tasks.__file__, report.__file__):
        with open(m, 'rb') as f: h.update(f.read())
    return h.hexdigest()


def _marks(f, off):  # the bytes a kept offset stands on: the file's start and the 64 KiB before it (all of a small file)
    f.seek(0); head = f.read(min(off, 4096))
    f.seek(max(0, off - 65536)); before = f.read(off - max(0, off - 65536))
    return hashlib.sha256(head + b'\0' + before).hexdigest()


def read(path):
    """The facts of every line of the transcript at path. Raises OSError when it can't be read."""
    with open(path, 'rb') as f:
        st = os.fstat(f.fileno())
        kept = os.path.join(_DIR, hashlib.sha256(os.path.realpath(path).encode()).hexdigest()[:32] + '.json')
        ver, facts, off = _version(), None, 0
        try:
            with open(kept) as kf: k = json.load(kf)
            if k['version'] == ver and k['ino'] == [st.st_dev, st.st_ino] and k['offset'] <= st.st_size and k['marks'] == _marks(f, k['offset']):
                facts, off = Facts(k['facts']), k['offset']
        except (OSError, ValueError, KeyError, TypeError): pass
        facts = facts or Facts()
        f.seek(off)
        pos, tail = off, b''
        for raw in f:  # b'\n' alone ends a line, as readlines() splits a transcript (its JSON escapes every \r)
            if not raw.endswith(b'\n'): tail = raw; break
            facts.feed(raw.decode(errors='replace')); pos += len(raw)
        if pos > off:
            try:
                os.makedirs(_DIR, exist_ok=True)
                [os.remove(os.path.join(_DIR, n)) for n in os.listdir(_DIR) if os.path.getmtime(os.path.join(_DIR, n)) < time.time() - 30 * 86400]
                tmp = f'{kept}.{os.getpid()}'
                with open(tmp, 'w') as kf: json.dump({'version': ver, 'ino': [st.st_dev, st.st_ino], 'offset': pos, 'marks': _marks(f, pos), 'facts': facts.json()}, kf)
                os.replace(tmp, kept)
            except OSError: pass  # the facts still hold for this stop
    if tail: facts.feed(tail.decode(errors='replace'))  # a last line not yet ended is read for this stop alone, and again on the next
    return facts
