#!/usr/bin/env python3
"""Claude Code PreToolUse hook (matcher: Agent, Task, delegate_task, t3_thread_launch). Exit 2 blocks the launch; stderr goes to the agent.
With the argument `register` it runs as the PostToolUse hook: only a launch that ran is registered, so one another hook blocked leaves no job.
The PreToolUse call decides; the PostToolUse call only records what ran and makes no admission check (a failure writing its
records still fails it). An admitted launch leaves its decision as a pending record in agent_jobs.LAUNCHED (when it was let
through, its key, task, role, worktrees, tool_use_id, launcher transcript, session, `refresh` and the `memory` brief it
follows, an implementer's `approach` and a review round's `heads`), which the PostToolUse call turns into the job.
One agent per job: a launch is registered under its job key (the ticket files its prompt names, and its title). A second launch
of the same key is blocked until `agent-job done <key>` releases the job, or for OPEN (a day); a task that contains or is contained
in an open job's (the same work under another title: an agent already on the job gets a message, not a twin, mergeworthy:delegate
step 1) is blocked until that job's agent has finished (agent_jobs.finished). A turn that ended is not a finished agent: on T3 a
child wakes again when its background commands end."""
import datetime, fcntl, functools, glob, hashlib, itertools, json, os, re, shlex, subprocess, sys, time
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))
import failclosed
import agent_jobs, launch, memory_file, project_file, review_launch, testpaths
from post_words import fence_spans
from records import branch_record
from shellcmd import segments, prog, git_argv, rlines, Where
from work_folder import git_top, task_of
register = sys.argv[1:] == ['register']
req = launch.Request(json.load(sys.stdin))
blocked = False
def refused():
    """After a check wrote its refusal: the remaining checks still run, so the launch gets every refusal in one message."""
    global blocked
    blocked = True
# T3 opens no run for a turn Claude Code starts by itself (a finished background command, a Monitor event), and refuses
# launches from it (pingdotgg/t3code#16808): nothing ran, so no job, and the session keeps working instead of waiting
if register and 'parent_not_active' in json.dumps(req.response or ''):
    # Claude Code takes the context only from an answer naming the event it ran on
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PostToolUseFailure' if req.failed else 'PostToolUse', 'additionalContext':
        "T3 refused this launch: a background event started this turn, and T3 opened no run for it, so it refuses agent "
        "launches and the user doesn't see this turn in the thread. The next user message, scheduled task or finished agent "
        "starts a run. Until then, do the step yourself wherever the main session may (gates, tests, probes, an implementer's "
        "edits, preparing the push or the body: delegate step 7); only an independent review and a post wait for a run. "
        "Keep the brief, launch it in the next run, and add no status line on each wake."}}))
    sys.exit(0)
if register and req.failed:  # a launch that failed for another reason started nothing to register
    sys.exit(0)
L = launch.Brief(req.text)
brief = L.brief  # every rule below reads the brief; the files it only names (project notes, installed skills) are read, so their history SHAs pin nothing
paths = L.paths
# A gate review (names a review output `.out` and CLEAN) starts only with its output named after its draft and on drafts that passed post-lint in their current form, and once
# admitted records the text it is handed (review_launch, admit). Its outputs are the paths its task or prompt names after `output to` (delegate §Reviewers);
# a launch with no such clause: every drafts/ `.out` its brief names, the files it also names there (thread record, ledger, parent, report) not being drafts
said_outs = [p.rstrip('.,;:') for c in re.findall(r'\boutput to (/[^\s`\'"()]+(?: and /[^\s`\'"()]+)*)', req.task) for p in c.split(' and ')]
review_outs = lambda t: (sorted(set(said_outs)) or sorted(set(re.findall(r'(/[^\s`\'"()]*/drafts/[^\s`\'"()]+\.out)\b', t)))) if re.search(r'\.out\b', t) and 'CLEAN' in t else []
reviewed_drafts = lambda t: {p for o in review_outs(t) if (p := review_launch.draft_of(o)) and os.path.isfile(p)}
tdir = os.path.join(os.path.dirname(os.path.dirname(os.path.realpath(__file__))), 'skills', 'delegate')
pasted = {l.strip() for l in open(os.path.join(tdir, 'agent.md'))} if os.path.isfile(os.path.join(tdir, 'agent.md')) else set()
own_brief = '\n'.join(l for l in brief.splitlines() if l.strip() not in pasted)  # the brief without the rules pasted from agent.md
shas = set(re.findall(r'\b(?=[0-9a-f]*\d)(?=[0-9a-f]*[a-f])[0-9a-f]{7,40}\b', brief))
git = lambda wt, *a: subprocess.run(['git', '-C', wt, *a], capture_output=True, text=True)
@functools.cache  # computed once per call of the hook: the round check and the pending record share it
def round_heads():
    """The checkouts a round's brief names and their heads that its pins equal."""
    tops = L.checkouts
    return tops, sorted({h for t in tops if (h := git(t, 'rev-parse', 'HEAD').stdout.strip()) and any(h.startswith(x) for x in shas)})
# pull-request step 5 is the build's input: an implementer brief names `Approach: <path>`, the newest approach record of a checkout it names
# (pr-steps approach). A later build of that record's PR names a newer record, or the same one marked `(unchanged: <why>)`.
def brief_approach(strict=True):
    """(record file, its newest line's time, the unchanged reason or '') of an implementer brief's Approach line; when it has none,
    None, refusing first when strict (the PRE call)."""
    m = re.search(r'^[ \t>*-]*Approach:\s*(\S+\.md)\b(.*)$', brief, re.M)
    if not m:
        if strict:
            sys.stderr.write("BLOCKED: an implementer brief names the approach it builds (mergeworthy:pull-request step 5, delegate/implementer.md): "
                             "a line `Approach: <abs path of approach.md>`, recorded first by `pr-steps approach` in the PR branch's checkout the brief names\n")
            refused()
        return None
    named, recs, newest = os.path.realpath(os.path.expanduser(m[1])), {}, []
    for p in (p for p in paths if not p.startswith('//')):  # the //host/… of a URL, not a path
        if (top := git_top(p)) and (r := branch_record(top, 'approach')) and os.path.isfile(r): recs[r] = top
    for r, top in sorted(recs.items()):
        rows = [l.split() for l in open(r) if len(l.split()) >= 3]
        if rows and os.path.realpath(rows[-1][1]) == named:
            why = re.search(r'\(unchanged:\s*([^)]*\S)\s*\)', m[2])
            return r, rows[-1][2], why[1] if why else ''
        if rows: newest.append(f"{top}: {rows[-1][1]}")
    if strict:
        sys.stderr.write(f"BLOCKED: {m[1]} is not the newest `pr-steps approach` record of a checkout this brief names "
                         + (f"(newest: {'; '.join(newest)})" if newest else "(no checkout this brief names has a record)")
                         + ": name the newest one, or record this one in the PR branch's checkout (mergeworthy:pull-request step 5) and name that checkout in the brief\n")
        refused()
    return None
def memory_launch(task):
    """The file a memory-refresh launch runs, which the 3-agent cap leaves out, else None: its task or prompt (never its title)
    says to follow, execute or do (launch.bound: `Follow the brief at <path>`, not `Do not follow <path>`) the path of
    memory-prep's brief (an existing memory-brief-<N>.md beside memory.source, the session-memory order's launch; prep
    deletes the one it replaces) or of the installed memory-refresh template (the file
    ~/.mergeworthy/current/skills/delegate/memory-refresh.md or this hook's own copy resolves to). Any other file of that
    name, and a brief that cites one without such a verb, is other work."""
    templates = {os.path.realpath(os.path.expanduser('~/.mergeworthy/current/skills/delegate/memory-refresh.md')),
                 os.path.realpath(os.path.join(tdir, 'memory-refresh.md'))}
    for p in sorted(launch.bound(task, 'follow|execute|do')):
        if os.path.realpath(p) in templates or re.fullmatch(r'memory-brief-\d*\.md', os.path.basename(p)) \
                and os.path.isfile(p) and os.path.isfile(os.path.join(os.path.dirname(p), 'memory.source')):
            return p
    return None
READERS = ('review', 'research')
class Kinds:
    """What kind of launch this is, each guessed once from its role and its brief."""
    def __init__(self, req, brief):
        self.implementation = req.role == 'implementation'
        self.builds = bool(self.implementation or re.search(r'^\s*You implement\b', brief, re.M))  # what the Approach checks read
        # Two rounds per loop on one head (delegate §Review rounds): a review round `<loop>-r<N>`, maybe followed by the date or head SHA
        # the reuse block below asks for, once the heads its brief pins show the branch hasn't moved since two earlier rounds of its loop, is refused;
        # a post's review is refused only once gate-pass's own check (review_launch.answers) already passes every draft it reviews
        rnd = re.fullmatch(r'(.+)-r(\d+)', re.sub(r'(-\d{4}-\d{2}-\d{2}|-[0-9a-f]{7,40})+$', '', req.round_name))
        self.round = (rnd[1], int(rnd[2])) if rnd else None
        self.review = bool(rnd and (req.role == 'review' or not req.role and re.search(r'\bexactly (CLEAN|NO BUGS)\b', brief)))
        # a post's review: a gate review of a named draft whose brief asks for no code verdict (a small review's pr-body.review.out comes with one)
        self.post_review = self.review and bool(reviewed_drafts(brief)) and not re.search(r'\b(NO BUGS|MERGE AS IS)\b', own_brief)
        self.drafter = 'thread-context.md' in brief  # it reads the thread record
        self.author = self.implementation or self.drafter or 'MERGE AS IS' in brief
        self.research = req.role == 'research' or bool(re.search(r'\bresearch', f"{req.title} {req.description}", re.I))
        self.refresh = memory_launch(req.task)  # decided here, at admission, and stored on the pending call; `refresh` on the job too
        # A fan-out a step names (finality steps 2-3, converge's per-slice verifiers) says so on a `Fan-out:` line, in the task or its brief, and passes
        # the cap; the fan-out agents already open still count against an ordinary launch
        self.fanout = not self.implementation and bool(re.search(r'^Fan-out: (finality step [23]|converge §Running the agents)$', brief, re.M))
        self.writer = req.role not in READERS
k = Kinds(req, brief)
def is_refresh(r):
    """A pending call's or job's memory-refresh decision, as its admission recorded it; a job a hook before `refresh` registered,
    still open after an update, is classified from its task."""
    return r['refresh'] if 'refresh' in r else bool(memory_launch(r.get('task') or r.get('brief') or ''))
# a fan-out runs several agents on one brief, each under its own title and naming its part in its task: the title is part of the job
key = ' '.join([*L.tickets, req.title]).strip()
job_file = os.path.join(agent_jobs.JOBS, hashlib.sha256(key.encode()).hexdigest()[:16])
# when the launch this registers began (its transcript starts after it): one record per key, as one_per_job lets one call of a key
# pend at a time; the record of a call another hook blocked is overwritten by the key's next launch, or removed a day on by the
# next launch that reads it (the pending loop)
pre = os.path.join(agent_jobs.LAUNCHED, os.path.basename(job_file))
def register_launch():
    """The PostToolUse call: the launch ran, so it records what its admission decided (from its pending record, which becomes
    the job) and makes no admission check. A launch with no pending record (keyless, or one its admission didn't get to write)
    is read from its tool input now."""
    rec, ran_memory = {}, k.refresh
    if key:  # nothing names the job (no ticket, title or description) otherwise, so no second launch of it can be told apart
        os.makedirs(agent_jobs.JOBS, exist_ok=True)
        with open(agent_jobs.JOBS + '.lock', 'a') as jobs_lock:  # released before the files below take their own locks
            fcntl.flock(jobs_lock, fcntl.LOCK_EX)
            try: rec = json.load(open(pre)); launched = rec['launched']; ran_memory = rec.get('memory', k.refresh); os.remove(pre)
            except (OSError, ValueError, KeyError, TypeError): rec, launched = {}, time.time()
            json.dump({'key': key, 'started': time.time(), 'launched': launched, 'brief': req.task, 'role': req.role, 'worktrees': L.worktrees, 'refresh': bool(ran_memory),
                       'session': req.session, 'transcript': req.transcript, 'handle': agent_jobs.handle(req.response)}, open(job_file, 'w'))
    if req.client_id: agent_jobs.locked_update(agent_jobs.CIDS, lambda seen: seen.setdefault(req.client_id, time.time()))
    if k.review and not k.post_review:
        agent_jobs.locked_update(agent_jobs.ROUNDS, lambda rounds: rounds.setdefault(k.round[0], []).append([k.round[1], rec['heads'] if 'heads' in rec else round_heads()[1]]))
    if k.builds and (approach := rec['approach'] if 'approach' in rec else brief_approach(strict=False)):
        os.makedirs(agent_jobs.BUILT, exist_ok=True)
        open(os.path.join(agent_jobs.BUILT, os.path.basename(approach[0])), 'w').write(approach[1])
    # an agent now runs memory-prep's brief: stop-lint's hourly repeat of the refresh order waits an hour (its folder may be gone by now)
    if ran_memory and os.path.basename(ran_memory).startswith('memory-brief-') and os.path.isdir(os.path.dirname(ran_memory)):
        open(os.path.join(os.path.dirname(ran_memory), '.memory-order-repeated'), 'w').close()
if register:
    register_launch()
    sys.exit(0)
# T3 starts a new Claude session for each turn, and Claude Code's background agents end with the session that launched them;
# the Agent tool runs in the background unless run_in_background is false
if req.tool in ('Agent', 'Task') and req.t3 and req.background:
    sys.stderr.write("BLOCKED: under T3 Code a background Agent stops when this turn ends (T3 starts a new session for the next one). "
                     "Launch it with delegate_task (mergeworthy:delegate step 4), or with run_in_background: false for a child that finishes within this turn.\n")
    refused()
# T3 heads a delegated task with "the agent in T3 thread <id> sent this message, not the user"; under that line Haiku declined 8 of
# 86 memory refreshes launched with role general or none, and none of 17 with role research, which T3 opens with "Act as the
# research sub-agent for this task" (Claude transcripts on private, 2026-11-20 to 11-25)
if k.refresh and req.t3 and str(req.tool).endswith('delegate_task') and req.role != 'research':
    sys.stderr.write("BLOCKED: launch the memory refresh with role research: T3 then opens its task with \"Act as the research sub-agent\"; "
                     "without it the Haiku reads the task as another agent's message, not the user's, and declines it.\n")
    refused()
def codex_reset():
    """The soonest reset while claude-swap reads every saved Codex account as used up ($CODEX_HOME/profiles/limited.json), else None."""
    profiles = os.path.join(os.environ.get('CODEX_HOME') or os.path.expanduser('~/.codex'), 'profiles')
    try:
        limited = json.load(open(os.path.join(profiles, 'limited.json')))
        until = [float((limited.get(a) or {}).get('until') or 0) for a in os.listdir(profiles) if os.path.isfile(os.path.join(profiles, a, 'auth.json'))]
    except (OSError, ValueError, AttributeError, TypeError):
        return None
    return min(until) if until and min(until) > time.time() else None
# Delegated agents run on Claude, reviews first on Codex (mergeworthy:delegate §Model class, §Reviewers), whichever host the session runs
# on: a delegate_task with no target runs on the launching session's provider, Antigravity's under hooks/agy.py (MERGEWORTHY_HOST)
drivers = req.drivers or {'antigravity' if os.environ.get('MERGEWORTHY_HOST') == 'antigravity' else 'claudeAgent'}
if req.t3 and str(req.tool).endswith('delegate_task') and 'antigravity' in drivers:
    sys.stderr.write("BLOCKED: no delegated agent runs on Antigravity (mergeworthy:delegate §Model class, §Reviewers)"
                     + ("; with no target this launch would run on this session's Antigravity" if not req.providers else '')
                     + f": set target.providerInstanceId to {'codex' if req.role == 'review' else 'claudeAgent'}.\n")
    refused()
elif req.role == 'review' and req.t3:
    reset = codex_reset()
    if reset and 'codex' in req.providers:
        at = time.localtime(reset)
        sys.stderr.write(f"BLOCKED: claude-swap reads every saved Codex account as used up until {time.strftime('%H:%M' if at[:3] == time.localtime()[:3] else '%a %H:%M', at)}, so this launch would fail. "
                         "Launch the review on Claude (target.providerInstanceId claudeAgent); it needs no Fallback line while that holds.\n")
        refused()
    # the fallback keeps the first review's prompt, so its claim may sit in the brief file the task names; `<what failed>` is the form, no claim
    elif not reset and 'claudeAgent' in drivers and not re.search(r'\bFallback:[ \t]*[^\s<]', launch.Brief(req.task).brief):
        sys.stderr.write("BLOCKED: an independent check starts on another company's model (mergeworthy:delegate §Reviewers): set target.providerInstanceId to codex. "
                         "Only when that call failed, launch on Claude (claudeAgent) with `Fallback: <what failed>` in the task or the brief file it names.\n")
        refused()
# T3 answers a delegate_task whose clientRequestId it has seen with that earlier task's result, without running anything.
# Reuse is allowed only within 10 minutes (a retry of the same launch).
if req.client_id:
    seen = json.load(open(agent_jobs.CIDS)) if os.path.exists(agent_jobs.CIDS) else {}
    if req.client_id in seen and time.time() - seen[req.client_id] > 600:
        sys.stderr.write(f"BLOCKED: clientRequestId '{req.client_id}' was used before; T3 would return that earlier task's result instead of running this one. Use a new id (add the date or the head SHA).\n")
        refused()
for out in review_outs(brief):
    if why := review_launch.misnamed(out) or review_launch.unlinted(out):
        sys.stderr.write(f"BLOCKED: {why}\n")
        refused()
def admit():
    """The PRE call's end: a launch nothing refused records each review output its brief names, setting aside an earlier verdict."""
    if not blocked:
        for out in review_outs(brief): review_launch.launch(out)
# A template's slot left unfilled (`<the slice's risky edges>`) reaches the agent as a rule it never got. A slot in backticks is
# the agent's own output form, the paste-in rules (agent.md) carry slots of their own, and an HTML tag a brief quotes is no slot.
told = re.sub(r'`[^`\n]*`', '', own_brief)  # a form the brief quotes in backticks (`PROMISED <thread>: …`) is a format, not a slot
HTML = set('a b base body br code div em footer form h1 h2 h3 head header html i img input li link main meta nav ol p path pre script section span strong style svg table td template title tr ul'.split())
unfilled = {}
for t in sorted(glob.glob(os.path.join(tdir, '*.md'))):
    for line in '\n'.join(inner for _, _, inner in fence_spans(open(t).read())).splitlines():
        code = [m.span() for m in re.finditer(r'`[^`]*`', line)]
        for m in re.finditer(r'<([^<>\n]+)>', line):
            if m[1] not in HTML and m[0] in told and not any(a <= m.start() and m.end() <= b for a, b in code):
                unfilled.setdefault(m[0], []).append(os.path.basename(t))
if unfilled:
    sys.stderr.write("BLOCKED: the brief still has a template's placeholder; fill it with the specifics (mergeworthy:delegate §Brief):\n"
                     + '\n'.join(f"{p} (delegate/{', delegate/'.join(dict.fromkeys(fs))})" for p, fs in sorted(unfilled.items())) + '\n')
    refused()
# A brief pinned to an older commit of a worktree it names (a linked one: the user's own checkouts are read at any
# commit) re-runs work on code that has moved on.
for wt in sorted(paths if shas else ()):
    head = git(wt, 'rev-parse', 'HEAD').stdout.strip() if os.path.isfile(os.path.join(wt, '.git')) else ''
    if head and not any(head.startswith(x) for x in shas):
        old = [x for x in shas if git(wt, 'merge-base', '--is-ancestor', x, head).returncode == 0]
        if old:
            root = memory_file.for_cwd(req.cwd, req.session)
            ruled = memory_file.section(open(memory_file.path(root)).read(), 'Ruled out') if root and os.path.isfile(memory_file.path(root)) else ''
            sys.stderr.write(f"BLOCKED: the brief pins {', '.join(sorted(old))} in {wt}, which has moved on to {head[:12]}. "
                             "Pin the live head (and check the work isn't already done there)." + (f" Ruled out:\n{ruled}\n" if ruled else "\n"))
            refused()
if k.post_review:
    led = re.search(r'(/[^\s`\'"()]+\.ledger\.md)\b', brief)  # the ledger the brief names; answers() defaults to the one beside the draft
    passes = [(o, dr, led and led[1]) for o in review_outs(brief) if (dr := review_launch.draft_of(o)) in reviewed_drafts(brief)]
    if all(not review_launch.answers(o, dr, lg) for o, dr, lg in passes):
        sys.stderr.write("BLOCKED: gate-pass already passes every draft this post review reads, so a round on them reviews nothing new "
                         "(mergeworthy:delegate §Review rounds): post it, or edit the draft first. It passes with:\n"
                         + ''.join(f"gate-pass {dr} {o}{f' --ledger {lg}' if lg else ''}\n" for o, dr, lg in passes))
        refused()
elif k.review and k.round[1] >= 3:
    tops, heads = round_heads()
    rlock = open(agent_jobs.ROUNDS + '.lock', 'a'); fcntl.flock(rlock, fcntl.LOCK_EX)  # held until exit
    rounds = json.load(open(agent_jobs.ROUNDS)) if os.path.exists(agent_jobs.ROUNDS) else {}
    loop, n = k.round
    # first-parent and no merges: what a merge of the base brought in isn't the PR's own, as SHAPE STALE's compare leaves it out; no renames: each row names a real path
    def own_lines(t, o, h):
        rows = re.findall(r'^(\d+)\t(\d+)\t(.*)$', git(t, '-c', 'core.quotePath=false', 'log', '--first-parent', '--no-merges', '--no-renames', '--numstat', '--format=', f'{o}..{h}').stdout, re.M)
        gen = testpaths.generated(t, [p for _, _, p in rows])
        return sum(int(a) + int(b) for a, b, p in rows if not re.search(testpaths.NOT_SHAPE, p) and p not in gen)
    desc = lambda t, o, h: git(t, 'merge-base', '--is-ancestor', o, h).returncode == 0
    def built_on(old):
        # each new head built on the round's heads counts, so a pin that never moves can't stand for a branch that did
        if not old: return not heads
        moved = False
        for h in heads:
            if h in old: moved = True; continue
            on = ((t, o) for t in tops for o in old if desc(t, o, h))
            if (first := next(on, None)) is None: continue
            moved = True
            if not any(own_lines(t, o, h) <= testpaths.STALE_LINES for t, o in itertools.chain([first], on)): return False
        return moved
    earlier = sorted({m for m, old, *_ in rounds.get(loop, []) if m < n and built_on(old)})
    if len(earlier) >= 2:
        sys.stderr.write(f"BLOCKED: {loop} already ran {', '.join(f'r{m}' for m in earlier)} on this head or one within {testpaths.STALE_LINES} changed lines of it "
                         f"({', '.join(h[:12] for h in heads) or 'no head pinned'}): a loop gets two rounds per head, and a head past those lines is a new one "
                         "(mergeworthy:delegate §Review rounds). "
                         "List what is still open in the report or the PR body's notes and go on (push, ready, the next step) without waiting for an answer; "
                         "only an open blocker keeps the PR in draft. A maintainer's ask on a new head starts a new loop name. "
                         f"Close r{earlier[-1]}, the last round, when it isn't clean, with `pr-steps <step> <file> --ledger <ledger>` or `gate-pass ... --ledger <ledger>` on its report: the agent's own report is the record, never one the main session writes.\n")
        refused()
# A brief that writes or reviews code, docs or a post (any role but research or test) for a repo whose maintainers' notes exist
# (delegate step 3) names the project file, so the agent reads them: by owner/repo, or by a path in that repo's checkout. A memory-refresh
# launch (memory_launch) reads only the session log; a brief that only mentions the template is other work.
missing = []
if req.role not in ('research', 'test') and not k.refresh:
    notes = {os.path.relpath(f, os.path.expanduser('~/.mergeworthy/projects'))[:-3].lower(): f
             for f in glob.glob(os.path.expanduser('~/.mergeworthy/projects/*/*.md'))}
    named = {r for r in notes if re.search(r'(?<![\w.-])' + re.escape(r) + r'(?!\.md)(?:\.git)?(?![\w.-])', brief, re.I)}
    tops = set()
    for p in paths if notes else ():
        if p.startswith('//'): continue  # the //host/… of a URL, not a path
        tops.add(git_top(p))
    for top in tops - {None}:
        url = subprocess.run(['git', '-C', top, 'remote', 'get-url', 'origin'], capture_output=True, text=True).stdout.strip()
        m = re.search(r'[:/]([\w.-]+/[\w.-]+?)(?:\.git)?$', url)
        named |= {m.group(1).lower()} & set(notes) if m else set()
    missing = [notes[r] for r in sorted(named) if f'projects/{r}.md' not in brief.lower()]
    if missing:
        sys.stderr.write("BLOCKED: the brief works on a repo with a project file; name each project file in it so the agent reads "
                         "and applies them (mergeworthy:delegate step 3):\n" + '\n'.join(missing) + '\n')
        refused()
    # every agent reads the project file whole: one over its cap is condensed before the next agent starts, but by the learning sort,
    # whose brief (delegate/learn-sort.md) condenses it
    over = [] if 'delegate/learn-sort.md' in brief else [f"{notes[r]}: {n} words" for r in sorted(named) if (n := project_file.words(notes[r])) > project_file.CAP]
    if over:
        sys.stderr.write(f"BLOCKED: a project file the brief names is over its {project_file.CAP}-word cap: condense it first (mergeworthy:task "
                         "§Project file), its quotes into the study, or brief the learning sort (delegate/learn-sort.md):\n" + '\n'.join(over) + '\n')
        refused()
    # The producer reads the standard its checker uses, by path (delegate step 3): code for an implementer, writing for a drafter.
    need = [f for f, applies in (('skills/code/SKILL.md', named and k.implementation),
                                 ('skills/writing/SKILL.md', k.drafter)) if applies and f not in brief]
    if need:
        sys.stderr.write("BLOCKED: name the standard the agent writes to by its path, so it reads it before producing "
                         "(mergeworthy:delegate step 3): " + ', '.join('~/.mergeworthy/current/' + f for f in need) + '\n')
        refused()
    # The main session decides on code it read itself, not on an agent's summary: an implementation brief for a repo needs a file
    # tracked in that repo read by this session in the last three hours (Read, Grep, a cat/sed/head/grep/git show on it, gh pr diff,
    # gh api .../contents, or a WebFetch of its github.com page); a report an agent wrote inside a checkout is untracked and doesn't count
    if k.implementation and named and req.transcript and os.path.isfile(req.transcript):
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
        for l in itertools.islice(rlines(req.transcript), 4001):  # the last 4,000 lines: rlines yields b'' first after a final newline
            if seen: break
            if b'"tool_use"' not in l: continue
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
            refused()
    # An author or the fresh reader works from the repo study (task step 4): the project file's ## Who decides links one dated within 30 days
    stale = []
    for r in sorted(named) if k.author else ():
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
        refused()
    # A drafter (reads the thread record, isn't a review) lists each scope-word claim beside its proof: the template's line.
    # A launch in the review, research or design role reads the record without drafting.
    if k.drafter and 'CLEAN' not in brief and req.role not in ('review', 'research', 'design') \
            and not re.search(r'scope word', brief, re.I):
        sys.stderr.write("BLOCKED: a drafter brief carries the template's scope-word check: paste "
                         "~/.mergeworthy/current/skills/delegate/drafter.md, filled in (mergeworthy:delegate step 3)\n")
        refused()
# A project file's `## Agents` line `Effort: <effort>`, bulleted or not, is the effort every agent for its repo runs at: a launch whose brief names
# that file, or should name it (missing above), sets it; with no option the harness's default runs, which is not the repo's choice.
for pf in sorted({os.path.expanduser('~/.mergeworthy/projects/' + r + '.md') for r in re.findall(r'\.mergeworthy/projects/([\w.-]+/[\w.-]+)\.md', brief)} | set(missing)):
    sec = re.search(r'^## Agents\n(.*?)(?=^## |\Z)', open(pf, errors='replace').read(), re.M | re.S) if os.path.isfile(pf) else None
    want = re.search(r'^(?:[-*] +)?Effort: *(\w+)', sec[1], re.M) if sec else None
    if want and str(req.effort or '').lower() != want[1].lower():
        sys.stderr.write(f"BLOCKED: {pf}'s `## Agents` says `Effort: {want[1]}`: launch with effort {want[1]} (the Agent tool's `effort`, "
                         f"delegate_task's target.options `effort` for Claude or `reasoningEffort` for Codex), not "
                         + (f"{req.effort}.\n" if req.effort else "the harness's default.\n"))
        refused()
approach = brief_approach() if k.builds else None
if approach and not approach[2]:
    built = os.path.join(agent_jobs.BUILT, os.path.basename(approach[0]))
    last = open(built).read().strip() if os.path.isfile(built) else ''
    if last >= approach[1]:
        sys.stderr.write(f"BLOCKED: this PR's last build was briefed on the approach recorded {last}, and this brief names no newer one. A changed "
                         "approach is rated and recorded first (mergeworthy:pull-request step 5); the same approach says so: "
                         "`Approach: <path> (unchanged: <why, in one line>)`\n")
        refused()
# Research the program already wrote up (memory.md, the notes) is read, not redone; a memory refresh, launched as research, writes them
root = memory_file.for_cwd(req.cwd, req.session)
if root and k.research and not k.refresh:
    topic = re.search(r'^\s*Topic:\s*(.+?)\s*$', brief, re.M)
    if not topic:
        sys.stderr.write("BLOCKED: a research brief names its topic in a `Topic: <key words>` line, so the hook can search the work folder's files for research already done (mergeworthy:delegate §Brief).\n")
        refused()
    else:
        words = [w.lower() for w in re.findall(r'[\w.-]{3,}', topic.group(1))]
        checked = ' '.join(re.findall(r'^\s*Checked:\s*(.+)$', brief, re.M))
        # covered = one paragraph holds every topic word: a long design doc that mentions them apart covers nothing
        covers = lambda p: any(all(w in para for w in words) for para in re.split(r'\n\s*\n', open(p, errors='replace').read().lower()))
        hits = [p for p in memory_file.notes(root) if p not in checked and os.path.abspath(p) not in {os.path.abspath(x) for x in L.paths} and covers(p)]
        if hits:
            sys.stderr.write("BLOCKED: these files already cover the topic; read them first. If one answers it, use it; "
                             "if not, add `Checked: <file>` to the brief for each:\n" + '\n'.join(hits) + '\n')
            refused()
os.makedirs(agent_jobs.JOBS, exist_ok=True)
# one launch at a time checks the open jobs and leaves its record, so launches in one message see each other; held until exit
jobs_lock = open(agent_jobs.JOBS + '.lock', 'a'); fcntl.flock(jobs_lock, fcntl.LOCK_EX)
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
capped = bool(req.session) and not k.refresh and not k.fanout  # the 3-agent cap applies to this launch
def bears_on(r):
    """Whether a pending record can change this launch's verdict, from its stored fields alone: the union of what the checks
    below read (one agent per job: its key, or a task containing or contained in this one; the cap: this session's calls but
    memory refreshes; one writer per worktree: a shared worktree). It only keeps returned() and the transcript searches off the
    rest: another session's other calls are read by that session's launches, and each check still applies its own test."""
    rt, mine = str(r.get('task') or '').strip(), req.task.strip()
    return (r.get('key') == key or bool(rt and mine and (rt in mine or mine in rt))
            or capped and r.get('session') == req.session and not is_refresh(r)
            or k.writer and bool(set(r.get('worktrees') or []) & set(L.worktrees)))
calls_out = []  # the launches let through whose call hasn't returned, not registered yet
for n in os.listdir(agent_jobs.LAUNCHED) if os.path.isdir(agent_jobs.LAUNCHED) else ():
    try: r = json.load(open(os.path.join(agent_jobs.LAUNCHED, n)))
    except (OSError, ValueError): continue
    if not isinstance(r, dict) or not bears_on(r): continue
    if r.get('tool_use_id') and r.get('transcript') and not returned(r['transcript'], r['tool_use_id']):
        call = {'key': r.get('key', ''), 'brief': r.get('task', ''), 'started': r.get('launched', 0), 'launched': r.get('launched', 0),
                'role': r.get('role'), 'worktrees': r.get('worktrees', []), 'transcript': r['transcript'], 'session': r.get('session'),
                'refresh': is_refresh(r)}
        # past LONG with no result in the launcher's transcript, a call whose agent never started (a crash mid-call) or has
        # finished (its launcher lost) is over: its record goes, so the launches after this one don't search the transcripts for it again
        if time.time() - call['started'] >= agent_jobs.LONG and (not agent_jobs.transcript(call) or agent_jobs.finished(call)):
            agent_jobs.remove(os.path.join(agent_jobs.LAUNCHED, n)); continue
        calls_out.append(call)
    # a call that returned (another hook blocked it, or no PostToolUse call matched it) or that names no call counts for nothing:
    # a day on, past any call's PostToolUse, its record goes, so no later launch searches its launcher's transcript again
    elif time.time() - r.get('launched', 0) >= agent_jobs.OPEN:
        agent_jobs.remove(os.path.join(agent_jobs.LAUNCHED, n))
registered = [j for _, j in agent_jobs.jobs()]  # the open jobs, read once for the checks below
# One writer per worktree: a writer (any role but review or research) waits for a linked worktree its brief names (not the launcher's
# own) that holds another session's process, or that a live writer job or outstanding writer call names, whose agent isn't the launcher. T3 can show that
# agent interrupted or cancelled while it runs, so agent_jobs.finished decides.
if k.writer:
    own, sid = git_top(os.path.realpath(req.cwd or '/')), req.session
    wts = [w for w in L.worktrees if w != own]
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
    me, busy = os.path.realpath(req.caller or '/'), []
    # a call still outstanding counts as its job will, its own key's aside (one_per_job's)
    writer_calls = [c for c in calls_out if c['key'] != key and set(c['worktrees']) & set(wts)]
    writers = [j for j in registered + writer_calls if j.get('role') not in READERS] if wts else []
    for j in writers:
        if 'worktrees' not in j: j['worktrees'] = launch.Brief(j.get('brief', '')).worktrees  # registered before jobs recorded theirs
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
        refused()
if not key:
    admit()
    sys.exit(2 if blocked else 0)  # nothing names the job (no ticket, title or description), so no second launch of it can be told apart
def one_per_job(started):
    """Blocks a second agent for this key: a key is one job, so two job files never share one."""
    sys.stderr.write(
        f"BLOCKED: an agent for this job is already launched ({key[:160]}, started {int((time.time() - started) / 60)} min ago). One agent per job: "
        "read its status first (task_status, its latest runs); a turn that ended or 'waiting_for_children' means it is still alive. "
        "Continue it with a message instead of starting another. Only when its task is terminal and you have read its result, "
        f"release the job with `agent-job done {shlex.quote(key[:200])}`, then launch.\n")
    refused()
this_job = json.load(open(job_file)) if os.path.exists(job_file) else {}
same = [this_job] if time.time() - this_job.get('started', 0) < agent_jobs.OPEN else [c for c in calls_out if c['key'] == key]
if same: one_per_job(same[0]['started'])
for j in registered + calls_out if req.task.strip() else ():
    if same and j.get('key') == key: continue  # this job's own record, refused above
    if (other := j.get('brief', '').strip()) and (other in req.task.strip() or req.task.strip() in other) and (j in calls_out or not agent_jobs.finished(j)):
        sys.stderr.write(
            f"BLOCKED: this task contains, or is contained in, an open job's task ({j['key'][:160]}, started {int((time.time() - j['started']) / 60)} min ago), "
            "so it is the same work under another title, and an agent already on the job gets a message, not a twin (mergeworthy:delegate step 1). An agent of a fan-out names its part in its task "
            "(its slice, subsystem, frames or topic). A new round on the same task releases the earlier job first, once its agent "
            f"is done and you have read its result: `agent-job done {shlex.quote(j['key'][:200])}`.\n")
        refused()
# At most 3 agents at a time per session (delegate step 1), or the number the user gave, quoted in the task's scope.md (the work folder
# of the session's cwd, else the one the briefs it launches are in): a job is open until released or its agent finished, and a launch let through
# counts until its call registers or returns, so launches in one message see each other; a memory refresh doesn't count (`capped`)
def users_words(quote):
    """Whether a prompt the user typed in this session (its transcript) holds quote verbatim: a tool result, hook message or
    assistant turn doesn't count."""
    try:
        for l in open(req.transcript or '', errors='replace'):
            try: o = json.loads(l)
            except ValueError: continue
            if isinstance(o, dict) and memory_file.prompt(o) and any(quote in t for t in memory_file.texts(o)): return True
    except OSError: pass
    return False
if capped:
    # session, then refresh, then finished: a refresh never counts, so its transcript isn't searched
    live = [j for j in registered if j.get('session') == req.session and not is_refresh(j) and not agent_jobs.finished(j)] \
        + [c for c in calls_out if c.get('session') == req.session and not c['refresh']]
    folders = {f for t in L.files + L.refs if (f := task_of(t))}
    scope = os.path.join(task_of(req.cwd or '/') or (folders.pop() if len(folders) == 1 else '<your work folder>'), 'scope.md')
    raised = re.search(r'^Agents: ([1-9]\d*) \(user \d{4}-\d{2}-\d{2}: "(.+)"\)$', open(scope, errors='replace').read() if os.path.isfile(scope) else '', re.M)
    limit = int(raised[1]) if raised and len(live) >= 3 and users_words(raised[2]) else 3  # a transcript is read only at the cap
    if len(live) >= limit:
        sys.stderr.write(f"BLOCKED: this session already has {len(live)} agents open, and the limit is {limit} at a time (mergeworthy:delegate step 1):\n"
                         + '\n'.join(f"{j['key'][:160]} (started {int((time.time() - j['started']) / 60)} min ago)" for j in live)
                         + "\nContinue one with a message, or wait for one to finish, read its result and release it with `agent-job done <key>`. "
                         f"A higher limit the user gave for this task goes in {scope} as a line `Agents: <N> (user <YYYY-MM-DD>: \"<their words>\")`, quoting the user's own words from this session.\n")
        refused()
admit()
if not blocked:
    os.makedirs(agent_jobs.LAUNCHED, exist_ok=True); json.dump({'launched': time.time(), 'key': key, 'task': req.task, 'role': req.role, 'worktrees': L.worktrees, 'tool_use_id': req.tool_use_id,
                                                           'transcript': req.transcript, 'session': req.session, 'refresh': bool(k.refresh), 'memory': k.refresh,
                                                           **({'approach': list(approach[:2])} if approach else {}),
                                                           **({'heads': round_heads()[1]} if k.review and not k.post_review else {})}, open(pre, 'w'))
sys.exit(2 if blocked else 0)
