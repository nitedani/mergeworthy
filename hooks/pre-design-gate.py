#!/usr/bin/env python3
"""Claude Code PreToolUse hook (matcher: Write, Edit, MultiEdit, NotebookEdit, delegate_task). Exit 2 blocks; stderr goes to the agent.
An edit inside a git work tree waits until this session read the AGENTS.md and CLAUDE.md at its root (pre-bash-guard checks the files a
command writes the same way), then for its repo and branch's `pr-steps preflight` and `pr-steps approach` records.
At Tier M or L (first line of scope.md in the work folder: ~/.mergeworthy/work/<task>/ holding the checkout, or <repo>-work/ beside it),
code waits for prior art (task step 6) and the design (design step 4): the work folder's prior-art.md and a decisions/*.md must exist
before an edit inside the repo, or an implementation agent briefed to work in a checkout of it (the session's own when the brief says none).
In a task's work folder, code waits for scope.md's Tier line (task step 2).
The step records under ~/.claude/pr-steps are pr-steps' to write."""
import glob, json, os, re, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import failclosed
from shellcmd import folder, no_approach, no_preflight, no_instructions_read
import launch, work_folder
d = json.load(sys.stdin)
ti = d.get('tool_input', {}) or {}
tool = d.get('tool_name', '')
cwd = d.get('cwd') or os.getcwd()
near = cwd
if 'delegate_task' not in tool:
    target = os.path.realpath(os.path.join(cwd, os.path.expanduser(str(ti.get('file_path') or ti.get('notebook_path') or ''))))
    if target.startswith(os.path.realpath(os.path.expanduser('~/.claude/pr-steps')) + os.sep):
        sys.stderr.write("BLOCKED: the step records in ~/.claude/pr-steps are written by `pr-steps <step> <its output>` alone, which checks the output first\n")
        sys.exit(2)
    near = folder(target)  # a new file's folder may not exist yet
    if why := no_instructions_read(target, d) or no_preflight(near) or no_approach(near):
        sys.stderr.write(f"BLOCKED: {why}\n")
        sys.exit(2)
def waits(near, code):
    """Why a change at near waits for its task's triage or design, or None; code(top) says whether the change is code in that repo."""
    # the edited file's repo, else the session's: an edit outside any repo is no code change (the push gate checks what leaves)
    top = subprocess.run(['git', '-C', near, 'rev-parse', '--show-toplevel'], capture_output=True, text=True).stdout.strip()
    if not top:
        return None
    work = work_folder.of(top) or work_folder.of(cwd) or top + '-work'
    try:
        tier = open(os.path.join(work, 'scope.md')).readline()
    except OSError:
        tier = ''
    if not re.match(r'\s*Tier:\s*[0SML]\b', tier):
        # a checkout in a task's work folder: the task is triaged before its code (outside one, nothing tells the task)
        return f"{work}/scope.md has no line 1 `Tier: <0|S|M|L>, because <signals>`: triage and scope the task first (mergeworthy:task steps 2-3)" if work_folder.of(top) else None
    if not re.match(r'\s*Tier:\s*[ML]\b', tier) or not code(top):
        return None
    missing = [n for n, ok in (('prior-art.md', os.path.isfile(os.path.join(work, 'prior-art.md'))),
                              ('decisions/*.md', bool(glob.glob(os.path.join(work, 'decisions', '*.md'))))) if not ok]
    return missing and (f"{tier.strip()} and {work} has no {' or '.join(missing)}. Before code: prior art (mergeworthy:task step 6: the web, "
                        "every project the user names, peers) into prior-art.md, then design it twice (mergeworthy:design step 4) "
                        "into decisions/<name>.md.")
if 'delegate_task' in tool:
    impl = str(ti.get('role') or '') == 'implementation'
    # an implementer works in the checkouts its brief says it works in; the session's own when it says none
    nears, code = (launch.parse(ti).targets if impl else []) or [cwd], lambda top: impl
else:
    path = os.path.realpath(str(ti.get('file_path') or ti.get('notebook_path') or ''))
    nears, code = [near], lambda top: path.startswith(os.path.realpath(top) + os.sep)
for n in nears:
    if why := waits(n, code):
        sys.stderr.write(f"BLOCKED: {why}\n")
        sys.exit(2)
sys.exit(0)
