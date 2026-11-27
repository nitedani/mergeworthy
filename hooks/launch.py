#!/usr/bin/env python3
"""A launch (Agent, Task, delegate_task, t3_thread_launch) parsed once: what the hook reads of its input (Request), and its
brief, what the agent is told (the launch's own text plus each file it executes: one it says to follow, execute or do, or whose
path names it a brief, ticket or prompt; never an installed skill or a project file), the other .md files it names, the
checkouts its brief names, and those it says it works in."""
import os, re
from shellcmd import transcript
from t3_tasks import driver, under_t3
from work_folder import git_top, task_of

MW = os.path.abspath(os.path.expanduser('~/.mergeworthy')) + os.sep
READ_ONLY = (MW + 'current' + os.sep, MW + 'projects' + os.sep)
MD = r'(?<![\w.~/-])(~?/[^\s`\'"]+\.md)\b'
PATH = r'~?/[^\s`\'"()<>,;]+'


def text_of(ti):
    """The launch's own text: every field of the tool input an agent reads."""
    return '\n'.join(str(ti.get(k) or '') for k in ('prompt', 'task', 'message', 'description', 'title', 'workspaceStrategy'))


def path_set(t):
    return {q for p in re.findall(f'({PATH})', t) if (q := os.path.expanduser(p.rstrip('/.,:')))}


def bound(text, verbs):
    """The first path after one of verbs in the same clause, at most four words between them, quoted or not
    (`Follow <p> exactly`, `Read and do the brief at <p>`), or the path the clause says to read and then to <verb> (`Read <p>
    and follow it`, `read <p> and follow its steps`); a verb elsewhere in the sentence, or one a negation comes right before,
    a word between allowed (`Do not edit <p>`, `never ever follow <p>`, `Read <p> and don't follow it`), binds nothing."""
    quote, neg = '[`\'"(<]*', r"\b(?:not|never|no|don['’]t|doesn['’]t)\s+(?:\S+\s+)?$"
    lead = lambda v: rf'\b(?:{v})\b(?!\s+not\b)(?:\s+(?!{quote}~?/)\S+){{0,4}}\s+{quote}({PATH})'
    said = set()
    for c in re.split(r'[.;!?,]\s+|\n', text):
        said |= {m[1] for m in re.finditer(rf'(?={lead(verbs)})', c, re.I) if not re.search(neg, c[:m.start()], re.I)}
        for m in re.finditer(lead('read'), c, re.I):
            then = re.search(rf'\b(?:{verbs})\s+(?:it|its steps|them)\b', c[m.end():], re.I)
            if then and not re.search(neg, c[:m.start()], re.I) and not re.search(neg, c[m.end():m.end() + then.start()], re.I):
                said.add(m[1])
    return {os.path.abspath(os.path.expanduser(p.rstrip('/.,:'))) for p in said}


def checkouts(paths):
    """The checkouts holding paths, outside the installed plugin."""
    return sorted({git_top(os.path.realpath(p)) for p in paths
                   if not p.startswith('//') and not (os.path.abspath(p) + os.sep).startswith(MW + 'current' + os.sep)} - {None})


def own_path(f):
    """f below the checkout or work folder holding it, else its name: a checkout's own files are no brief by their folder's name."""
    base = git_top(f) or task_of(f)
    return os.path.relpath(f, base) if base else os.path.basename(f)


class Request:
    """What the hook reads of a launch's hook input, whichever tool made it (its PostToolUse call's adds the response)."""
    def __init__(self, d):
        ti = d.get('tool_input', {}) or {}
        self.tool, self.t3, self.text = d.get('tool_name'), under_t3(), text_of(ti)
        self.task = str(ti.get('task') or ti.get('prompt') or '')  # delegate_task's task, the Agent tool's prompt
        self.description = str(ti.get('description') or '')
        self.title = str(ti.get('title') or self.description).strip()  # the Agent tool names its launch by its description
        self.client_id = str(ti.get('clientRequestId') or '')
        self.round_name = (self.client_id or self.description).strip()
        self.role, self.background = ti.get('role'), ti.get('run_in_background') is not False
        target = ti.get('target') or {}
        self.providers = {target.get('providerInstanceId'), target.get('driverKind')} - {None, ''}
        # the T3 provider instance it names: delegate_task's target, t3_thread_launch's modelSelection
        self.instance = str(target.get('providerInstanceId') or (ti.get('modelSelection') or {}).get('instanceId') or '')
        # the drivers it runs on, as T3 Code picks them: the named instance's, else any instance of the driver it names
        k = target.get('driverKind')
        self.drivers = {driver(i, k)} if (i := target.get('providerInstanceId')) else {k} if k else set()
        # the Agent tool's `effort`, delegate_task's target.options or t3_thread_launch's modelSelection.options, as a list of
        # {id, value} or an object, `effort`, `reasoningEffort` or Antigravity's `thought_level`
        opts = (ti.get('target') or ti.get('modelSelection') or {}).get('options') or {}
        opts = {o.get('id'): o.get('value') for o in opts if isinstance(o, dict)} if isinstance(opts, list) else opts
        self.effort = ti.get('effort') or opts.get('effort') or opts.get('reasoningEffort') or opts.get('thought_level')
        self.session, self.transcript, self.cwd = d.get('session_id'), d.get('transcript_path'), d.get('cwd') or ''
        self.caller = transcript(d)  # the transcript of the session or subagent making the call
        # a call that failed (PostToolUseFailure, as T3 returns a refused launch: an MCP error) has its error instead of a response
        self.tool_use_id, self.response = d.get('tool_use_id'), d.get('tool_response') or d.get('error')
        self.failed = d.get('hook_event_name') == 'PostToolUseFailure'


class Brief:
    def __init__(self, text):
        self.text = text
        md = lambda s: {os.path.abspath(os.path.expanduser(m)) for m in re.findall(MD, s)}
        said = bound(text, 'follow|execute|do')
        named = sorted(md(text))
        self.files = [f for f in named if os.path.isfile(f) and not f.startswith(READ_ONLY)
                      and (f in said or re.search(r'brief|ticket|prompt', own_path(f)))]
        self.refs = [f for f in named if f not in self.files]
        # the job's key: the files it names outside ~/.mergeworthy (no project file, installed skill or work folder file is a ticket)
        self.tickets = [f for f in named if not f.startswith(MW)]
        self.brief = text + '\n' + '\n'.join(open(f, errors='replace').read() for f in self.files)
        self.paths = path_set(self.brief)
        self.checkouts = checkouts(self.paths)
        # where the change goes (`work only in <p>`, `implement the fix in <p>`), not a checkout it names for reference
        self.targets = checkouts(bound(self.brief, r'implement|work|edit|build|fix|in the checkout'))
        self.worktrees = [c for c in self.checkouts if os.path.isfile(os.path.join(c, '.git'))]


def parse(ti):
    return Brief(text_of(ti))
