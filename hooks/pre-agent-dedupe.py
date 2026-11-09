#!/usr/bin/env python3
"""Claude Code PreToolUse hook (matcher: Agent, Task, delegate_task, t3_thread_launch). Exit 2 blocks the launch; stderr goes to the agent.
With the argument `register` it runs as the PostToolUse hook: only a launch that ran is registered, so one another hook blocked leaves no job.
One agent per job: a launch is registered under its job key (the ticket files its prompt names, and its title), and a second
launch of the same job, or of a task that contains or is contained in an open job's (the text tells the agents' transcripts
apart, agent_jobs), is blocked until `agent-job done <key>` releases it. A turn that ended is not a finished agent: on T3 a
child wakes again when its background commands end, so only its terminal task status (read first) releases the job."""
import datetime, fcntl, glob, hashlib, json, os, re, shlex, sys, time
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import failclosed
import agent_jobs, memory_file, project_file, steward, subprocess, testpaths
from post_words import fence_spans
from shellcmd import branch_record, segments, prog, git_argv, rlines, transcript, Where
from work_folder import git_top, task_of
from t3_tasks import under_t3
register = sys.argv[1:] == ['register']
d = json.load(sys.stdin)
ti = d.get('tool_input', {}) or {}
# T3 opens no run for a turn Claude Code starts by itself (a finished background command, a Monitor event), and refuses
# launches from it (pingdotgg/t3code#16808): nothing ran, so no job, and the session keeps working instead of waiting
if register and 'parent_not_active' in json.dumps(d.get('tool_response') or ''):
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PostToolUse', 'additionalContext':
        "T3 refused this launch: a background event started this turn, and T3 opened no run for it, so it refuses agent "
        "launches and the user doesn't see this turn in the thread. The next user message, scheduled task or finished agent "
        "starts a run. Until then, do the step yourself wherever the main session may (gates, tests, probes, an implementer's "
        "edits, preparing the push or the body: delegate step 7); only an independent review and a post wait for a run. "
        "Keep the brief, launch it in the next run, and add no status line on each wake."}}))
    sys.exit(0)
# T3 starts a new Claude session for each turn, and Claude Code's background agents end with the session that launched them;
# the Agent tool runs in the background unless run_in_background is false
if not register and d.get('tool_name') in ('Agent', 'Task') and under_t3() and ti.get('run_in_background') is not False:
    sys.stderr.write("BLOCKED: under T3 Code a background Agent stops when this turn ends (T3 starts a new session for the next one). "
                     "Launch it with delegate_task (mergeworthy:delegate step 4), or with run_in_background: false for a child that finishes within this turn.\n")
    sys.exit(2)
# This hook runs only under Claude Code, so a review on claudeAgent, or naming no provider (it inherits), is on the main session's company
if not register and ti.get('role') == 'review' and under_t3():
    target = ti.get('target') or {}
    provider = {target.get('providerInstanceId'), target.get('driverKind')} - {None, ''}
    if (not provider or 'claudeAgent' in provider) and not re.search(r'^Fallback:[ \t]*\S', str(ti.get('task') or ''), re.M):
        sys.stderr.write("BLOCKED: an independent check starts on another company's model (mergeworthy:delegate §Reviewers): set target.providerInstanceId to codex. "
                         "Only when that call failed, launch on this company with a line `Fallback: <what failed>` in the task.\n")
        sys.exit(2)
# T3 answers a delegate_task whose clientRequestId it has seen with that earlier task's result, without running anything.
# Reuse is allowed only within 10 minutes (a retry of the same launch).
cid = str(ti.get('clientRequestId') or '')
if cid:
    ids = os.path.expanduser('~/.claude/agent-client-request-ids.json'); os.makedirs(os.path.dirname(ids), exist_ok=True)
    lock = open(ids + '.lock', 'a'); fcntl.flock(lock, fcntl.LOCK_EX)  # held until exit: launches register at once
    seen = json.load(open(ids)) if os.path.exists(ids) else {}
    if cid in seen and time.time() - seen[cid] > 600:
        sys.stderr.write(f"BLOCKED: clientRequestId '{cid}' was used before; T3 would return that earlier task's result instead of running this one. Use a new id (add the date or the head SHA).\n")
        sys.exit(2)
    if register:
        seen.setdefault(cid, time.time())
        with open(ids + '.tmp', 'w') as f: json.dump(seen, f)
        os.replace(ids + '.tmp', ids)
text = '\n'.join(str(ti.get(k) or '') for k in ('prompt', 'task', 'message', 'description', 'title', 'workspaceStrategy'))
# a ticket is the brief file the agent executes; a file under ~/.mergeworthy (project notes, an installed skill) is a reference
mw = os.path.abspath(os.path.expanduser('~/.mergeworthy')) + os.sep
MD = r'(?<![\w.~/-])(~?/[^\s`\'"]+\.md)\b'
tickets = sorted({t for t in (os.path.abspath(os.path.expanduser(m)) for m in re.findall(MD, text))
                  if not t.startswith(mw)})
# A gate review (names a review output `.out` and CLEAN) starts only on drafts that passed post-lint in their current form.
# Reference files (project notes, installed skills) are read by the agent, not part of its brief: their history SHAs pin nothing
gate_text = text + '\n' + '\n'.join(open(t).read() for t in tickets if os.path.isfile(t))
if not register and re.search(r'\.out\b', gate_text) and 'CLEAN' in gate_text:
    # The gate names a review's output after its draft (`<name>.review.out` for `<name>.md`): when it does, that draft is
    # the one reviewed, and the files beside it (thread record, brief, parent) are not drafts
    named = {re.sub(r'(\.review)?\.out$', '.md', o) for o in re.findall(r'(/[^\s`\'"()]*/drafts/[^\s`\'"()]+\.out)\b', gate_text)}
    named = {p for p in named if os.path.isfile(p)}
    for draft in sorted(named or set(re.findall(r'(/[^\s`\'"()]*/drafts/[^\s`\'"()]+\.md)\b', gate_text))):
        base = os.path.basename(draft)
        if not named and (base.endswith(('.parent.md', '.current.md', '.report.md')) or re.search(r'ticket|brief|prompt|research|context', base) or re.search(r'\.v\d+\.md$', base)) or not os.path.isfile(draft):
            continue
        try: ok = open(draft + '.lint.sha').read().strip() == hashlib.sha256(open(draft, 'rb').read()).hexdigest()
        except OSError: ok = False
        if not ok:
            sys.stderr.write(f"BLOCKED: {draft} has no passing post-lint for its current text: run post-lint first, then the review.\n")
            sys.exit(2)
# a brief the launch follows from the work folder counts here, though the tickets above skip all of ~/.mergeworthy
brief_files = {os.path.abspath(os.path.expanduser(m)) for m in re.findall(MD, text)}
briefs = gate_text + '\n' + '\n'.join(open(t).read() for t in brief_files if t.startswith(mw + 'work' + os.sep) and os.path.isfile(t))
# A template's slot left unfilled (`<the slice's risky edges>`) reaches the agent as a rule it never got. A slot in backticks is
# the agent's own output form, the paste-in rules (agent.md) carry slots of their own, and an HTML tag a brief quotes is no slot.
if not register:
    tdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'skills', 'delegate')
    pasted = {l.strip() for l in open(os.path.join(tdir, 'agent.md'))} if os.path.isfile(os.path.join(tdir, 'agent.md')) else set()
    # only the brief itself: the task text and the brief files it executes, not the input files it names (memory.md quotes `<sha>`)
    own = [t for t in tickets if re.search(r'brief|prompt|ticket', os.path.basename(t))] or tickets[:1]
    brief_text = text + '\n' + '\n'.join(open(t).read() for t in own if os.path.isfile(t))
    brief = '\n'.join(l for l in brief_text.splitlines() if l.strip() not in pasted)
    brief = re.sub(r'`[^`\n]*`', '', brief)  # a form the brief quotes in backticks (`PROMISED <thread>: …`) is a format, not a slot
    HTML = set('a b base body br code div em footer form h1 h2 h3 head header html i img input li link main meta nav ol p path pre script section span strong style svg table td template title tr ul'.split())
    unfilled = {}
    for t in sorted(glob.glob(os.path.join(tdir, '*.md'))):
        for line in '\n'.join(inner for _, _, inner in fence_spans(open(t).read())).splitlines():
            code = [m.span() for m in re.finditer(r'`[^`]*`', line)]
            for m in re.finditer(r'<([^<>\n]+)>', line):
                if m[1] not in HTML and m[0] in brief and not any(a <= m.start() and m.end() <= b for a, b in code):
                    unfilled.setdefault(m[0], []).append(os.path.basename(t))
    if unfilled:
        sys.stderr.write("BLOCKED: the brief still has a template's placeholder; fill it with the specifics (mergeworthy:delegate §Brief):\n"
                         + '\n'.join(f"{p} (delegate/{', delegate/'.join(dict.fromkeys(fs))})" for p, fs in sorted(unfilled.items())) + '\n')
        sys.exit(2)
# A project file's `## Agents` line `Effort: <effort>`, bulleted or not, is the effort every agent for its repo runs at: a launch whose brief names
# that file sets it (the Agent tool's `effort`, delegate_task's target.options or t3_thread_launch's modelSelection.options
# `effort` or `reasoningEffort`); with no option the harness's default runs, which is not the repo's choice.
if not register:
    opts = (ti.get('target') or ti.get('modelSelection') or {}).get('options') or {}
    opts = {o.get('id'): o.get('value') for o in opts if isinstance(o, dict)} if isinstance(opts, list) else opts
    effort = ti.get('effort') or opts.get('effort') or opts.get('reasoningEffort')
    for f in sorted({os.path.expanduser('~/.mergeworthy/projects/' + r + '.md') for r in re.findall(r'\.mergeworthy/projects/([\w.-]+/[\w.-]+)\.md', briefs)}):
        sec = re.search(r'^## Agents\n(.*?)(?=^## |\Z)', open(f, errors='replace').read(), re.M | re.S) if os.path.isfile(f) else None
        want = re.search(r'^(?:[-*] +)?Effort: *(\w+)', sec[1], re.M) if sec else None
        if want and str(effort or '').lower() != want[1].lower():
            sys.stderr.write(f"BLOCKED: {f}'s `## Agents` says `Effort: {want[1]}`: launch with effort {want[1]} (the Agent tool's `effort`, "
                             f"delegate_task's target.options `effort` for Claude or `reasoningEffort` for Codex), not "
                             + (f"{effort}.\n" if effort else "the harness's default.\n"))
            sys.exit(2)
path_set = lambda t: {q for p in re.findall(r'(~?/[^\s`\'"()<>,;]+)', t) if (q := os.path.expanduser(p.rstrip('/.,:')))}
paths = path_set(gate_text)
# A brief names a worktree in its launch text or its brief file (a ticket it says to follow, or named so), not in a reference it names
# or an installed skill (~/.mergeworthy/current may link to a worktree of mergeworthy)
said_in = lambda s: {os.path.abspath(os.path.expanduser(m)) for x in re.split(r'(?<=[.!?])\s+|\n', s)
                     if re.search(r'\b(follow|execute|exactly|what it says)\b', x, re.I) for m in re.findall(MD, x)}
# the brief the launch executes: its own text, and each file it says to follow or names as a brief, under the work folder too
# (`Follow ~/.mergeworthy/work/<task>/brief.md exactly`); never a reference it names, nor an installed skill or a project file
executed_in = lambda s: [t for t in sorted({os.path.abspath(os.path.expanduser(m)) for m in re.findall(MD, s)})
                         if os.path.isfile(t) and not t.startswith((mw + 'current' + os.sep, mw + 'projects' + os.sep))
                         and (t in said_in(s) or re.search(r'brief|ticket|prompt', os.path.basename(t)))]
worktree_paths_in = lambda s: {p for p in path_set(s + '\n' + '\n'.join(open(t, errors='replace').read() for t in executed_in(s)))
                               if not (os.path.abspath(p) + os.sep).startswith(mw + 'current' + os.sep)}
worktree_paths = worktree_paths_in(text)
def linked(p):
    top = git_top(p)
    return top if top and os.path.isfile(os.path.join(top, '.git')) else None
worktrees_in = lambda s: sorted({w for w in (linked(os.path.realpath(p)) for p in worktree_paths_in(s)) if w})
# A brief pinned to an older commit of a worktree it names (a linked one: the user's own checkouts are read at any
# commit) re-runs work on code that has moved on.
shas = set(re.findall(r'\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b', gate_text))
git = lambda wt, *a: subprocess.run(['git', '-C', wt, *a], capture_output=True, text=True)
if not register:
    for wt in sorted(worktree_paths if shas else ()):
        head = git(wt, 'rev-parse', 'HEAD').stdout.strip() if os.path.isfile(os.path.join(wt, '.git')) else ''
        if head and not any(head.startswith(x) for x in shas):
            old = [x for x in shas if git(wt, 'merge-base', '--is-ancestor', x, head).returncode == 0]
            if old:
                root = memory_file.for_cwd(d.get('cwd') or '')
                ruled = memory_file.section(open(memory_file.path(root)).read(), 'Ruled out') if root and os.path.isfile(memory_file.path(root)) else ''
                sys.stderr.write(f"BLOCKED: the brief pins {', '.join(sorted(old))} in {wt}, which has moved on to {head[:12]}. "
                                 "Pin the live head (and check the work isn't already done there)." + (f" Ruled out:\n{ruled}\n" if ruled else "\n"))
                sys.exit(2)
# Two rounds per loop on one head (delegate §Review rounds): a review round `<loop>-r<N>`, maybe followed by the date or head SHA
# the reuse block above asks for, once two earlier rounds of its loop pinned its head or one within SHAPE STALE's count of it, is refused
rnd = re.fullmatch(r'(.+)-r(\d+)', re.sub(r'(-\d{4}-\d{2}-\d{2}|-[0-9a-f]{7,40})+$', '', (cid or str(ti.get('description') or '')).strip()))
if rnd and (ti.get('role') == 'review' or not ti.get('role') and re.search(r'\bexactly (CLEAN|NO BUGS)\b', briefs)):
    tops = sorted({t for t in map(git_top, worktree_paths) if t})
    heads = sorted({h for t in tops if (h := git(t, 'rev-parse', 'HEAD').stdout.strip()) and any(h.startswith(x) for x in shas)})
    rf = os.path.expanduser('~/.claude/review-rounds.json')
    rlock = open(rf + '.lock', 'a'); fcntl.flock(rlock, fcntl.LOCK_EX)  # held until exit
    rounds = json.load(open(rf)) if os.path.exists(rf) else {}
    loop, n = rnd[1], int(rnd[2])
    if register:
        rounds.setdefault(loop, []).append([n, heads])
        with open(rf + '.tmp', 'w') as f: json.dump(rounds, f)
        os.replace(rf + '.tmp', rf)
    elif n >= 3:
        # first-parent and no merges: what a merge of the base brought in isn't the PR's own, as SHAPE STALE's compare leaves it out; no renames: each row names a real path
        own_lines = lambda t, o, h: sum(int(a) + int(b) for a, b, p in re.findall(r'^(\d+)\t(\d+)\t(.*)$', git(t, '-c', 'core.quotePath=false', 'log', '--first-parent', '--no-merges', '--no-renames', '--numstat', '--format=', f'{o}..{h}').stdout, re.M) if not re.search(testpaths.NOT_SHAPE, p))
        fixes = lambda t, o, h: git(t, 'merge-base', '--is-ancestor', o, h).returncode == 0 and own_lines(t, o, h) <= testpaths.STALE_LINES
        built_on = lambda old: not old and not heads or any(fixes(t, o, h) for t in tops for o in old for h in heads)
        earlier = sorted({m for m, old in rounds.get(loop, []) if m < n and built_on(old)})
        if len(earlier) >= 2:
            sys.stderr.write(f"BLOCKED: {loop} already ran {', '.join(f'r{m}' for m in earlier)} on this head or one within {testpaths.STALE_LINES} changed lines of it "
                             f"({', '.join(h[:12] for h in heads) or 'no head pinned'}): a loop gets two rounds per head, and a head past those lines is a new one (mergeworthy:delegate §Review rounds). "
                             "List what is still open in the report or the PR body's notes and go on (push, ready, the next step) without waiting for an answer; "
                             "only an open blocker keeps the PR in draft. A maintainer's ask on a new head starts a new loop name. "
                             "Close a round 2 that isn't clean with `pr-steps <step> <file> --ledger <ledger>` or `gate-pass ... --ledger <ledger>` on the last report: the agent's own report is the record, never one the main session writes."
                             + ("" if heads else " An independent update of a body no Git head pins (a tracker's status lines), and not a fix to the text these rounds reviewed, is its own loop: `<loop>-u<N>-r1`, `-r2`.") + "\n")
            sys.exit(2)
# A brief that writes or reviews code, docs or a post (any role but research or test) for a repo whose maintainers' notes exist
# (delegate step 3) names the project file, so the agent reads them: by owner/repo, or by a path in that repo's checkout. A memory-refresh
# brief reads only the session log.
if not register and ti.get('role') not in ('research', 'test') and 'memory-refresh' not in gate_text:
    notes = {os.path.relpath(f, os.path.expanduser('~/.mergeworthy/projects'))[:-3].lower(): f
             for f in glob.glob(os.path.expanduser('~/.mergeworthy/projects/*/*.md'))}
    named = {r for r in notes if re.search(r'(?<![\w.-])' + re.escape(r) + r'(?!\.md)(?:\.git)?(?![\w.-])', gate_text, re.I)}
    tops = set()
    for p in paths if notes else ():
        if p.startswith('//'): continue  # the //host/… of a URL, not a path
        tops.add(git_top(p))
    for top in tops - {None}:
        url = subprocess.run(['git', '-C', top, 'remote', 'get-url', 'origin'], capture_output=True, text=True).stdout.strip()
        m = re.search(r'[:/]([\w.-]+/[\w.-]+?)(?:\.git)?$', url)
        named |= {m.group(1).lower()} & set(notes) if m else set()
    missing = [notes[r] for r in sorted(named) if f'projects/{r}.md' not in gate_text.lower()]
    if missing:
        sys.stderr.write("BLOCKED: the brief works on a repo with a project file; name each project file in it so the agent reads "
                         "and applies them (mergeworthy:delegate step 3):\n" + '\n'.join(missing) + '\n')
        sys.exit(2)
    # every agent reads the project file whole: one over its cap is condensed before the next agent starts
    # the learning thread condensing it is waited for while it runs; its own agents, which do the condensing, pass
    over = []
    for r in sorted(named):
        n = project_file.words(notes[r])
        if n > project_file.CAP:
            t = project_file.learning_thread(r)
            if t and t[0] in steward.threads(d.get('session_id')) + steward.delegators(os.environ.get('T3CODE_THREAD_ID', '')):
                continue
            live = t and steward.active(t[0])
            over.append(f"{notes[r]}: {n} words" + (f"; the learning thread {t[0]} started {t[1]} condenses it: wait for it (`t3 thread show`), don't condense alongside it" if live else ''))
    if over:
        sys.stderr.write(f"BLOCKED: a project file the brief names is over its {project_file.CAP}-word cap: condense it first (mergeworthy:task "
                         "§Project file), its quotes into the study, unless a learning thread already does:\n" + '\n'.join(over) + '\n')
        sys.exit(2)
    # The producer reads the standard its checker uses, by path (delegate step 3): code for an implementer, writing for a drafter.
    need = [f for f, applies in (('skills/code/SKILL.md', named and ti.get('role') == 'implementation'),
                                 ('skills/writing/SKILL.md', 'thread-context.md' in gate_text)) if applies and f not in gate_text]
    if need:
        sys.stderr.write("BLOCKED: name the standard the agent writes to by its path, so it reads it before producing "
                         "(mergeworthy:delegate step 3): " + ', '.join('~/.mergeworthy/current/' + f for f in need) + '\n')
        sys.exit(2)
    # The main session decides on code it read itself, not on an agent's summary: an implementation brief for a repo needs a file
    # tracked in that repo read by this session in the last three hours (Read, Grep, a cat/sed/head/grep/git show on it, gh pr diff,
    # gh api .../contents, or a WebFetch of its github.com page); a report an agent wrote inside a checkout is untracked and doesn't count
    if ti.get('role') == 'implementation' and named and d.get('transcript_path') and os.path.isfile(d['transcript_path']):
        origin = {}
        def repo_of(p):
            top = git_top(p)
            if not top: return '', top
            if top not in origin:
                u = subprocess.run(['git', '-C', top, 'remote', 'get-url', 'origin'], capture_output=True, text=True).stdout.strip()
                m = re.search(r'[:/]([\w.-]+/[\w.-]+?)(?:\.git)?$', u); origin[top] = m.group(1).lower() if m else ''
            return origin[top], top
        def code_read(q):
            q = os.path.expanduser(q.split(':')[0])
            if not os.path.exists(q): return False
            r, top = repo_of(q)
            if r not in named: return False
            return os.path.isdir(q) or subprocess.run(['git', '-C', top, 'ls-files', '--error-unmatch', q], capture_output=True).returncode == 0
        def bash_reads(cmd, cwd):
            out, where = [], Where(cwd)
            for t in where.walk(segments(cmd)):
                w = prog(t)
                if w[:1] == ['git'] and 'show' in w and (g := git_argv(w, where))[2] == 'show' and g[0] and \
                        not {'--stat', '--name-only', '--name-status', '--no-patch', '-s', '--oneline'} & set(g[3]):
                    out += [os.path.join(g[0], a.split(':', 1)[1]) for a in g[3] if re.match(r'^[\w./~^-]+:[^/]', a)] or [g[0]]
                elif w[:1] and w[0] in ('cat', 'sed', 'head', 'tail', 'grep', 'rg', 'less', 'nl'):
                    out += [p for a in w[1:] if not a.startswith('-') and (os.sep in a or '.' in a) and (p := where.path(a))]
            return out
        since, seen = time.time() - 3 * 3600, False
        for l in reversed(open(d['transcript_path'], errors='replace').readlines()[-4000:]):
            if seen or '"tool_use"' not in l: continue
            try: e = json.loads(l)
            except ValueError: continue
            try: t = datetime.datetime.fromisoformat(e.get('timestamp', '').replace('Z', '+00:00')).timestamp()
            except ValueError: continue
            if t < since: break
            for x in (e.get('message') or {}).get('content') or []:
                if not isinstance(x, dict) or x.get('type') != 'tool_use': continue
                i, n = x.get('input') or {}, x.get('name')
                if n == 'Bash' and re.search(r'\bgh (pr diff|api repos/\S+/(contents|commits))', i.get('command', '')) and any(r in i['command'].lower() for r in named) \
                        or n == 'WebFetch' and any('github.com/' + r + '/' in i.get('url', '').lower() for r in named):
                    seen = True; break
                cands = [i.get('file_path', '')] if n == 'Read' else [i.get('path', '')] if n == 'Grep' else \
                        bash_reads(i.get('command', ''), e.get('cwd') or '/') if n == 'Bash' else []
                if any(q and code_read(q) for q in cands):
                    seen = True; break
        if not seen:
            sys.stderr.write(f"BLOCKED: read the code this change is about yourself before briefing it ({', '.join(sorted(named))}): open the files "
                             "(no checkout: clone it, or gh pr diff / gh api), the feature's docs page and its JSDoc, and decide from them, not from an agent's report (always-on: the main session)\n")
            sys.exit(2)
    # An author or the fresh reader works from the repo study (task step 4): the project file's ## Who decides links one dated within 30 days
    authors = ti.get('role') == 'implementation' or 'thread-context.md' in gate_text or 'MERGE AS IS' in gate_text
    stale = []
    for r in sorted(named) if authors else ():
        sec = re.search(r'^## Who decides\n(.*?)(?=^## |\Z)', open(notes[r], errors='replace').read(), re.M | re.S)
        # a link relative to the project file counts too (`[r.study.md](r.study.md)`)
        cands = [os.path.join(os.path.dirname(notes[r]), os.path.expanduser(c)) for c in re.findall(r'[^\s()\[\]`]+\.study\.md', sec[1])] if sec else []
        study = next((c for c in cands if os.path.isfile(c)), None)
        first = open(study, errors='replace').readline() if study else ''
        dated = re.match(r'Studied:\s*(\d{4}-\d{2}-\d{2})', first)
        if not dated or (datetime.date.today() - datetime.date.fromisoformat(dated[1])).days > 30:
            stale.append(notes[r])
    if stale:
        sys.stderr.write("BLOCKED: write the repo study first (mergeworthy:task step 4, §Repo study): each project file's `## Who decides` links "
                         "~/.mergeworthy/projects/<owner>/<repo>.study.md whose first line is `Studied: <date>` within 30 days, so the author writes "
                         "what the maintainer merges:\n" + '\n'.join(stale) + '\n')
        sys.exit(2)
    # A drafter (reads the thread record, isn't a review) lists each scope-word claim beside its proof: the template's line
    if 'thread-context.md' in gate_text and 'CLEAN' not in gate_text and not re.search(r'scope word', gate_text, re.I):
        sys.stderr.write("BLOCKED: a drafter brief carries the template's scope-word check: paste "
                         "~/.mergeworthy/current/skills/delegate/drafter.md, filled in (mergeworthy:delegate step 3)\n")
        sys.exit(2)
# pull-request step 5 is the build's input: an implementer brief names `Approach: <path>`, the newest approach record of a checkout it names
# (pr-steps approach). A later build of that record's PR names a newer record, or the same one marked `(unchanged: <why>)`.
BUILT = os.path.expanduser('~/.claude/approach-builds')  # per approach record: the time of the record the PR's last build was briefed on
exec_text = text + '\n' + '\n'.join(open(t, errors='replace').read() for t in executed_in(text))
def brief_approach():
    """(record file, its newest line's time, the unchanged reason or '') of an implementer brief's Approach line; blocks when it has none."""
    m = re.search(r'^[ \t>*-]*Approach:\s*(\S+\.md)\b(.*)$', exec_text, re.M)
    if not m:
        sys.stderr.write("BLOCKED: an implementer brief names the approach it builds (mergeworthy:pull-request step 5, delegate/implementer.md): "
                         "a line `Approach: <abs path of approach.md>`, recorded first by `pr-steps approach` in the PR branch's checkout the brief names\n")
        sys.exit(2)
    named, recs = os.path.realpath(os.path.expanduser(m[1])), set()
    for p in (p for p in path_set(exec_text) if not p.startswith('//')):  # the //host/… of a URL, not a path
        if (top := git_top(p)) and (r := branch_record(top, 'approach')) and os.path.isfile(r): recs.add(r)
    for r in sorted(recs):
        rows = [l.split() for l in open(r) if len(l.split()) >= 3]
        if rows and os.path.realpath(rows[-1][1]) == named:
            why = re.search(r'\(unchanged:\s*([^)]*\S)\s*\)', m[2])
            return r, rows[-1][2], why[1] if why else ''
    sys.stderr.write(f"BLOCKED: {m[1]} is not the newest `pr-steps approach` record of a checkout this brief names: record it in the PR branch's "
                     "checkout (mergeworthy:pull-request step 5) and name that checkout in the brief\n")
    sys.exit(2)
approach = brief_approach() if ti.get('role') == 'implementation' or re.search(r'^\s*You implement\b', exec_text, re.M) else None
if approach and not register and not approach[2]:
    built = os.path.join(BUILT, os.path.basename(approach[0]))
    last = open(built).read().strip() if os.path.isfile(built) else ''
    if last >= approach[1]:
        sys.stderr.write(f"BLOCKED: this PR's last build was briefed on the approach recorded {last}, and this brief names no newer one. A changed "
                         "approach is rated and recorded first (mergeworthy:pull-request step 5); the same approach says so: "
                         "`Approach: <path> (unchanged: <why, in one line>)`\n")
        sys.exit(2)
if approach and register:
    os.makedirs(BUILT, exist_ok=True)
    open(os.path.join(BUILT, os.path.basename(approach[0])), 'w').write(approach[1])
# Research the program already wrote up (memory.md, the notes) is read, not redone.
root = None if register else memory_file.for_cwd(d.get('cwd') or '')
if root and (ti.get('role') == 'research' or re.search(r'\bresearch', f"{ti.get('title') or ''} {ti.get('description') or ''}", re.I)):
    topic = re.search(r'^\s*Topic:\s*(.+?)\s*$', gate_text, re.M)
    if not topic:
        sys.stderr.write("BLOCKED: a research brief names its topic in a `Topic: <key words>` line, so the hook can search the work folder's files for research already done (mergeworthy:delegate §Brief).\n")
        sys.exit(2)
    words = [w.lower() for w in re.findall(r'[\w.-]{3,}', topic.group(1))]
    checked = ' '.join(re.findall(r'^\s*Checked:\s*(.+)$', gate_text, re.M))
    # covered = one paragraph holds every topic word: a long design doc that mentions them apart covers nothing
    covers = lambda p: any(all(w in para for w in words) for para in re.split(r'\n\s*\n', open(p, errors='replace').read().lower()))
    hits = [p for p in memory_file.notes(root) if p not in checked and os.path.abspath(p) not in tickets and covers(p)]
    if hits:
        sys.stderr.write("BLOCKED: these files already cover the topic; read them first. If one answers it, use it; "
                         "if not, add `Checked: <file>` to the brief for each:\n" + '\n'.join(hits) + '\n')
        sys.exit(2)
# a fan-out runs several agents on one brief, each under its own title and naming its part in its task: the title is part of the job
key = ' '.join([*tickets, str(ti.get('title') or ti.get('description') or '').strip()]).strip()
jobs = os.path.expanduser('~/.claude/agent-jobs'); os.makedirs(jobs, exist_ok=True)
# one launch at a time checks the open jobs and leaves its record, so launches in one message see each other; held until exit
lock = open(jobs + '.lock', 'a'); fcntl.flock(lock, fcntl.LOCK_EX)
def returned(path, use_id):
    """The launcher's transcript holds the call's tool_result: another hook blocked it, or it returned (then it registers)."""
    try:
        for l in rlines(path):  # last first: the result comes after the call
            if use_id.encode() not in l: continue
            try: e = json.loads(l)
            except ValueError: continue
            content = (e.get('message') or {}).get('content') if isinstance(e.get('message'), dict) else None
            for b in content if isinstance(content, list) else ():
                if isinstance(b, dict) and b.get('type') == 'tool_result' and b.get('tool_use_id') == use_id: return True
                if isinstance(b, dict) and b.get('type') == 'tool_use' and b.get('id') == use_id: return False
    except OSError: return True
    return False
if not register:
    pending = []  # a launch let through whose call is still running, not registered yet
    for n in os.listdir(agent_jobs.LAUNCHED) if os.path.isdir(agent_jobs.LAUNCHED) else ():
        try: r = json.load(open(os.path.join(agent_jobs.LAUNCHED, n)))
        except (OSError, ValueError): continue
        if isinstance(r, dict) and r.get('tool_use_id') and r.get('transcript') and not returned(r['transcript'], r['tool_use_id']):
            pending.append({'key': r.get('key', ''), 'brief': r.get('task', ''), 'started': r.get('launched', 0), 'launched': r.get('launched', 0),
                            'role': r.get('role'), 'worktrees': r.get('worktrees', []), 'transcript': r['transcript']})
# One writer per worktree: a writer (any role but review or research) waits for a linked worktree its brief names (not the launcher's
# own) that holds another session's process, or that a live writer job or outstanding writer call names, whose agent isn't the launcher. T3 can show that
# agent interrupted or cancelled while it runs, so agent_jobs.finished decides.
READERS = ('review', 'research')
if not register and ti.get('role') not in READERS:
    own, sid = linked(os.path.realpath(d.get('cwd') or '/')), d.get('session_id')
    wts = [w for w in worktrees_in(text) if w != own]
    anc, p = set(), os.getpid()
    while wts and p > 1:
        anc.add(p)
        try: p = int(open(f'/proc/{p}/stat').read().rsplit(')', 1)[1].split()[1])
        except (OSError, IndexError, ValueError): break
    procs = []
    for e in os.listdir('/proc') if wts else ():
        try:
            if e.isdigit() and int(e) not in anc:
                procs.append((e, os.readlink(f'/proc/{e}/cwd'), open(f'/proc/{e}/comm').read().strip()))
        except OSError: pass
    def launchers_own(pid):
        try: return bool(sid) and f'CLAUDE_CODE_SESSION_ID={sid}'.encode() in open(f'/proc/{pid}/environ', 'rb').read().split(b'\0')
        except OSError: return False
    me, busy = os.path.realpath(transcript(d) or '/'), []
    # a call still outstanding counts as its job will, its own key's aside (one_per_job's); one whose agent never started stops counting after LONG
    calls = [j for j in pending if j['key'] != key and set(j['worktrees']) & set(wts) and (agent_jobs.transcript(j) or time.time() - j['started'] < agent_jobs.LONG)]
    writers = [j for j in [j for _, j in agent_jobs.jobs()] + calls if j.get('role') not in READERS] if wts else []
    for j in writers:
        if 'worktrees' not in j: j['worktrees'] = worktrees_in(j.get('brief', ''))  # registered before jobs recorded theirs
    for w in wts:
        pids = [f'{e} ({c})' for e, cwd, c in procs if (cwd == w or cwd.startswith(w + '/')) and not launchers_own(e)]
        held = []
        for j in writers:
            if w in j['worktrees'] and not agent_jobs.finished(j):
                a = agent_jobs.transcript(j)
                if not a or os.path.realpath(a) != me:
                    held.append(f"{j['key'][:160]} (started {int((time.time() - j['started']) / 60)} min ago, its transcript: {a or 'not started'})")
        if pids or held:
            busy.append(f"{w}: " + '; '.join((['processes with their cwd there: ' + ', '.join(pids)] if pids else []) + (['live writer jobs: ' + ', '.join(held)] if held else [])))
    if busy:
        sys.stderr.write("BLOCKED: another writer is working in a worktree this brief names (T3's interrupted or cancelled status doesn't mean it stopped):\n"
                         + '\n'.join(busy) + "\nContinue that agent with a message, or wait for it to finish; a replacement goes in a fresh worktree. "
                         "A job whose agent has ended and whose result you read: `agent-job done <key>`.\n")
        sys.exit(2)
if not key:
    sys.exit(0)  # nothing names the job (no ticket, title or description), so no second launch of it can be told apart
f = os.path.join(jobs, hashlib.sha256(key.encode()).hexdigest()[:16])
# when the launch this registers began (its transcript starts after it): one record per key, as one_per_job lets one call of a key
# pend at a time, and the key's next launch overwrites the record of a call another hook blocked
pre = os.path.join(agent_jobs.LAUNCHED, os.path.basename(f))
task = str(ti.get('task') or ti.get('prompt') or '')
if register:
    try: launched = json.load(open(pre))['launched']; os.remove(pre)
    except (OSError, ValueError, KeyError, TypeError): launched = time.time()
    json.dump({'key': key, 'started': time.time(), 'launched': launched, 'brief': task, 'role': ti.get('role'), 'worktrees': worktrees_in(text),
               'session': d.get('session_id'), 'transcript': d.get('transcript_path')}, open(f, 'w'))
    # an agent now runs memory-prep's brief: stop-lint's hourly repeat of the refresh order waits an hour
    for t in tickets:
        if os.path.basename(t).startswith('memory-brief-') and os.path.isfile(os.path.join(os.path.dirname(t), 'memory.source')):
            open(os.path.join(os.path.dirname(t), '.memory-order-repeated'), 'w').close()
def one_per_job(started):
    """Blocks a second agent for this key: a key is one job, so two job files never share one."""
    sys.stderr.write(
        f"BLOCKED: an agent for this job is already launched ({key[:160]}, started {int((time.time() - started) / 60)} min ago). One agent per job: "
        "read its status first (task_status, its latest runs); a turn that ended or 'waiting_for_children' means it is still alive. "
        "Continue it with a message instead of starting another. Only when its task is terminal and you have read its result, "
        f"release the job with `agent-job done {shlex.quote(key[:200])}`, then launch.\n")
    sys.exit(2)
if not register and os.path.exists(f):
    j = json.load(open(f))
    if time.time() - j.get('started', 0) < 24 * 3600: one_per_job(j['started'])
if not register:
    for j in pending:
        if j['key'] == key: one_per_job(j['started'])
    for j in [j for _, j in agent_jobs.jobs()] + pending if task.strip() else ():
        if (other := j.get('brief', '').strip()) and (other in task.strip() or task.strip() in other):
            sys.stderr.write(
                f"BLOCKED: this task contains, or is contained in, an open job's task ({j['key'][:160]}, started {int((time.time() - j['started']) / 60)} min ago), "
                "and an agent's transcript is told apart from another's by its task text. An agent of a fan-out names its part in its task "
                "(its slice, subsystem, frames or topic). A new round on the same task releases the earlier job first, once its agent "
                f"is done and you have read its result: `agent-job done {shlex.quote(j['key'][:200])}`.\n")
            sys.exit(2)
# At most 3 agents at a time per session (delegate step 1), or the number the user gave, quoted in the task's scope.md (the work folder
# of the session's cwd, else the one the briefs it launches are in): a job is open until released or its agent finished; a memory refresh doesn't count
# A fan-out a step names (finality steps 2-3, converge's per-slice verifiers) says so on a `Fan-out:` line, in the task or its brief, and passes
fanout = ti.get('role') != 'implementation' and re.search(r'^Fan-out: (finality step [23]|converge §Running the agents)$', briefs, re.M)
def users_words(quote):
    """Whether a prompt the user typed in this session (its transcript) holds quote verbatim: a tool result, hook message or
    assistant turn doesn't count."""
    try:
        for l in open(d.get('transcript_path') or '', errors='replace'):
            try: o = json.loads(l)
            except ValueError: continue
            if isinstance(o, dict) and memory_file.prompt(o) and any(quote in t for t in memory_file.texts(o)): return True
    except OSError: pass
    return False
if not register and d.get('session_id') and 'memory-refresh' not in gate_text and not fanout:
    live = [j for _, j in agent_jobs.jobs() if j.get('session') == d['session_id'] and '/memory-brief-' not in j['key']
            and 'memory-refresh' not in j.get('brief', '') and not agent_jobs.finished(j)]
    folders = {f for t in brief_files if (f := task_of(t))}
    scope = os.path.join(task_of(d.get('cwd') or '/') or (folders.pop() if len(folders) == 1 else '<your work folder>'), 'scope.md')
    raised = re.search(r'^Agents: ([1-9]\d*) \(user \d{4}-\d{2}-\d{2}: "(.+)"\)$', open(scope, errors='replace').read() if os.path.isfile(scope) else '', re.M)
    limit = int(raised[1]) if raised and len(live) >= 3 and users_words(raised[2]) else 3  # a transcript is read only at the cap
    if len(live) >= limit:
        sys.stderr.write(f"BLOCKED: this session already has {len(live)} agents open, and the limit is {limit} at a time (mergeworthy:delegate step 1):\n"
                         + '\n'.join(f"{j['key'][:160]} (started {int((time.time() - j['started']) / 60)} min ago)" for j in live)
                         + "\nContinue one with a message, or wait for one to finish, read its result and release it with `agent-job done <key>`. "
                         f"A higher limit the user gave for this task goes in {scope} as a line `Agents: <N> (user <YYYY-MM-DD>: \"<their words>\")`, quoting the user's own words from this session.\n")
        sys.exit(2)
if not register:
    os.makedirs(agent_jobs.LAUNCHED, exist_ok=True); json.dump({'launched': time.time(), 'key': key, 'task': task, 'role': ti.get('role'), 'worktrees': worktrees_in(text), 'tool_use_id': d.get('tool_use_id'),
                                                           'transcript': d.get('transcript_path')}, open(pre, 'w'))
sys.exit(0)
