#!/usr/bin/env python3
"""A launch (Agent, Task, delegate_task, t3_thread_launch) parsed once: its brief, what the agent is told (the launch's own text
plus each file it executes: one it says to follow, execute or do, or whose path names it a brief, ticket or prompt; never an
installed skill or a project file), the other .md files it names, and the checkouts its brief names."""
import os, re
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
    """The paths text puts after one of verbs in the same clause, at most four words and no other path between them
    (`Follow <p> exactly`, `Read and do the brief at <p>`); a verb elsewhere in the sentence binds nothing."""
    return {os.path.abspath(os.path.expanduser(m[1].rstrip('/.,:'))) for c in re.split(r'[.;!?,]\s+|\n', text)
            for m in re.finditer(rf'\b(?:{verbs})\b(?:\s+[^\s~/]\S*){{0,4}}\s+[`\'"]?({PATH})', c, re.I)}


def own_path(f):
    """f below the checkout or work folder holding it, else its name: a checkout's own files are no brief by their folder's name."""
    base = git_top(f) or task_of(f)
    return os.path.relpath(f, base) if base else os.path.basename(f)


class Launch:
    def __init__(self, text):
        self.text = text
        md = lambda s: {os.path.abspath(os.path.expanduser(m)) for m in re.findall(MD, s)}
        said = bound(text, 'follow|execute|do')
        named = sorted(md(text))
        self.files = [f for f in named if os.path.isfile(f) and not f.startswith(READ_ONLY)
                      and (f in said or re.search(r'brief|ticket|prompt', own_path(f)))]
        self.refs = [f for f in named if f not in self.files]
        # the job's key: a file outside ~/.mergeworthy it names (project notes and installed skills are read by every job)
        self.tickets = [f for f in named if not f.startswith(MW)]
        self.brief = text + '\n' + '\n'.join(open(f, errors='replace').read() for f in self.files)
        self.paths = path_set(self.brief)
        tops = {git_top(os.path.realpath(p)) for p in self.paths
                if not p.startswith('//') and not (os.path.abspath(p) + os.sep).startswith(MW + 'current' + os.sep)}
        self.checkouts = sorted(tops - {None})
        self.worktrees = [c for c in self.checkouts if os.path.isfile(os.path.join(c, '.git'))]


def parse(ti):
    return Launch(text_of(ti))
