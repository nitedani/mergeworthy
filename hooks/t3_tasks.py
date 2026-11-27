#!/usr/bin/env python3
"""T3 Code: whether the session runs under it, and its delegated tasks as the session's transcript reports them: its tool calls
and results (delegate_task, task_status, t3_thread_send) and T3's notices. A thread is all its tasks: the first, each message sent
to it, each turn T3 continues on its own (provider-continuation)."""
import contextlib, functools, hashlib, json, os, pathlib, re, shlex, sqlite3

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


# T3's built-in drivers with a default instance, whose id is the driver's (src/provider/builtInDrivers.ts BUILT_IN_DRIVERS, all but
# acpRegistry), and those its default leaves off (packages/contracts/src/settings.ts DEFAULT_DISABLED_PROVIDER_DRIVERS)
BUILT_IN = ('codex', 'claudeAgent', 'cursor', 'grok', 'fx', 'opencode', 'antigravity', 'kiro', 'pi', 'muse')
OFF_BY_DEFAULT = {'cursor', 'grok', 'fx', 'kiro', 'muse', 'pi', 'opencode', 'antigravity'}


def t3_home():
    """T3 Code's data directory as its resolveBaseDir gives it: T3CODE_HOME trimmed, a leading `~` or `~/` for the home folder
    (expandHomePath), made absolute; else ~/.t3."""
    raw, home = (os.environ.get('T3CODE_HOME') or '').strip(), os.path.expanduser('~')
    if not raw: return os.path.join(home, '.t3')
    return os.path.abspath(home if raw == '~' else os.path.join(home, raw[2:]) if raw.startswith('~/') else raw)


def userdata(*path):
    """A path in T3 Code's state folder, `userdata` in its data directory."""
    return os.path.join(t3_home(), 'userdata', *path)


@functools.cache
def settings():
    """T3 Code's settings.json, or None when it can't be read."""
    try: d = json.load(open(userdata('settings.json')))
    except (OSError, ValueError): return None
    return d if isinstance(d, dict) else None


def instances():
    """T3 Code's provider instances by id as T3 runs them: its settings' own, and the default instance of each built-in driver they
    leave out (deriveProviderInstanceConfigMap); None without its settings."""
    if (s := settings()) is None: return None
    listed = s.get('providerInstances')
    known = {i: o for i, o in listed.items() if isinstance(o, dict)} if isinstance(listed, dict) else {}
    for d in BUILT_IN: known.setdefault(d, {'driver': d})
    return known


def here(environment):
    """Whether a launch naming T3 environment `environment` (or none) runs on this machine, whose id is its userdata's environment-id."""
    try: return not environment or environment == open(userdata('environment-id')).read().strip()
    except OSError: return False


def state_uri():
    """T3 Code's state database as a read-only SQLite URI."""
    return pathlib.Path(userdata('statev2.sqlite')).absolute().as_uri() + '?mode=ro'


@functools.cache
def project():
    """The T3 project of the hook's thread (T3CODE_THREAD_ID), from T3's state, or None."""
    try:
        with contextlib.closing(sqlite3.connect(state_uri(), uri=True, timeout=2)) as c:
            r = c.execute('select project_id from orchestration_v2_projection_threads where thread_id = ?', (os.environ.get('T3CODE_THREAD_ID'),)).fetchone()
    except sqlite3.Error: return None
    return r and r[0]


def enabled(instance, o):
    """Whether T3 runs instance `o` in the hook's project (resolveProjectProviderInstanceEnabled): the project's override, else (as
    resolveProviderInstanceEnabled) either explicit false disables the instance; otherwise the outer flag, inner flag, or driver
    default applies."""
    over = (((settings() or {}).get('projectSettingsOverrides') or {}).get(project()) or {}) if project() else {}
    over = ((over.get('providerInstances') or {}).get(instance) or {}).get('enabled') if isinstance(over, dict) else None
    if isinstance(over, bool): return over
    flag = (o.get('config') or {}).get('enabled') if isinstance(o.get('config'), dict) else None
    if o.get('enabled') is False or flag is False: return False
    return next((v for v in (o.get('enabled'), flag) if isinstance(v, bool)), o.get('driver') not in OFF_BY_DEFAULT)


def driver(instance, kind=None):
    """The driver T3 Code runs provider instance `instance` with (claudeAgent, codex, antigravity), from its settings; else the driver
    `kind` the launch names, else the id itself, as a built-in instance's id is its driver's."""
    try: return (instances() or {})[instance]['driver']
    except (KeyError, TypeError): return kind or instance


@functools.cache
def t3_claude_config_dir():
    """CLAUDE_CONFIG_DIR in T3 Code's own environment, which it passes to each Claude it starts: read in /proc from the server its
    server-runtime.json names, when that process runs T3's binary from its data directory; None when that can't be read."""
    try:
        pid = int(json.load(open(userdata('server-runtime.json')))['pid'])
        if not os.path.realpath(f'/proc/{pid}/exe').startswith(os.path.realpath(t3_home()) + os.sep): return None
        env = open(f'/proc/{pid}/environ', 'rb').read().split(b'\0')
    except (OSError, ValueError, KeyError, TypeError): return None
    return next((v.split(b'=', 1)[1].decode(errors='replace') for v in env if v.startswith(b'CLAUDE_CONFIG_DIR=')), None)


def loads_mergeworthy(instance, config):
    """Whether T3 Code's provider instance `instance` (its settings entry `config`) loads mergeworthy, as its driver loads plugins:
    Claude Code with the plugin in a `--plugin-dir` of its launchArgs, or enabled in its config dir's settings.json (its homePath,
    else CLAUDE_CONFIG_DIR in its environment, else in T3's own, else ~/.claude) and not disabled by a `--settings` file or JSON
    there (which override it); Antigravity with a `mergeworthy` plugin in the instance's own profile (where hooks/agy-link links
    it). Any other driver: True, as nothing here can tell."""
    c = config.get('config') if isinstance(config.get('config'), dict) else {}
    if config.get('driver') == 'claudeAgent':
        # its config dir as T3 gives it (resolveClaudeConfigDirPath, mergeClaudeProcessEnvironment)
        env = config.get('environment') if isinstance(config.get('environment'), list) else []
        home = (c.get('homePath') or next((e.get('value') for e in env if isinstance(e, dict) and e.get('name') == 'CLAUDE_CONFIG_DIR'), None)
                or t3_claude_config_dir())
        layers = [os.path.join(os.path.expanduser(home or '~/.claude'), 'settings.json')]
        args = c.get('launchArgs') or []
        try: args = shlex.split(args) if isinstance(args, str) else [str(a) for a in args]
        except ValueError: args = []
        flag = lambda name: [a.split('=', 1)[1] if a.startswith(name + '=') else b for a, b in zip(args, args[1:] + ['']) if a == name or a.startswith(name + '=')]
        # a --plugin-dir T3 passes on (claudeLaunchArgPluginDirectories) loads the plugin it holds
        for d in filter(None, flag('--plugin-dir')):
            try:
                if json.load(open(os.path.join(os.path.expanduser(d), '.claude-plugin', 'plugin.json'))).get('name') == 'mergeworthy': return True
            except (OSError, ValueError, AttributeError): pass
        layers += flag('--settings')
        on = False
        for layer in filter(None, layers):
            try: d = json.loads(layer) if layer.lstrip().startswith('{') else json.load(open(os.path.expanduser(layer)))
            except (OSError, ValueError): continue
            plugins = d.get('enabledPlugins') if isinstance(d, dict) else None
            for k, v in (plugins.items() if isinstance(plugins, dict) else ()):
                if k.split('@')[0] == 'mergeworthy': on = bool(v)
        return on
    if config.get('driver') == 'antigravity':
        profile = hashlib.sha256(instance.encode()).hexdigest()
        return os.path.exists(userdata('providers', 'antigravity', profile, 'config', 'plugins', 'mergeworthy'))
    return True


def _enabled(known, kind):
    """The ids of the instances in `known` of driver `kind` that T3 runs."""
    return [i for i, o in known.items() if o.get('driver') == kind and enabled(i, o)]


def mergeworthy_instances(kind):
    """The enabled instances of driver `kind` that load mergeworthy, as T3 Code runs them; [kind] without its settings, as a
    built-in instance's id is its driver's."""
    known = instances()
    return [kind] if known is None else [i for i in _enabled(known, kind) if loads_mergeworthy(i, known[i])]


def without_mergeworthy(instance, kind=None):
    """The instances a launch may run on that load no mergeworthy, or [] when it loads it or T3 Code's settings can't tell. It names
    an instance id, or a driverKind alone, for which T3 may pick any enabled instance of that driver (resolveTarget: the first
    healthy one when the parent's runs another driver)."""
    known = instances() or {}
    return [i for i in ([instance] if instance else _enabled(known, kind)) if i in known and not loads_mergeworthy(i, known[i])]


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
