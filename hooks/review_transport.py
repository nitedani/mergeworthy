"""How a review round reaches its reviewer: a launch (Agent, Task, delegate_task, t3_thread_launch) is a round by its name; a send
(T3's t3_thread_send, Claude Code's SendMessage) to a reviewer (loops.seat_loops) is a round `<loop>-r<N>` that continues it
(loops.continues, delegate §Continue), its message the task and its round name the title, and refused naming none; a send to
anyone else is no launch. A shell reviewer (`codex exec`, its `resume`, `claude -p`) is a round by its prompt file's name,
`<loop>-r<N>.md`. A round that continues its reviewer is admitted only as a fix check of that reviewer's findings while it is
recent (fix_check); any other later round goes to a fresh reviewer (delegate §Reviewers)."""
import glob, os, re, time
import agent_jobs, loops, steward, t3_tasks

WINDOW = 50 * 60  # a provider's prompt cache is gone after about an hour, and the continued reviewer re-reads it all
FIX_CHECK = r'^[ \t>*-]*Review:[^\n]*\bfix-check\b'  # the brief's line declaring a round a fix check of its reviewer's own findings


def as_launch(tool, ti):
    """(the tool input as the launch it is, whether it was sent to a running reviewer, the first round of its loop there or None,
    the loops that reviewer runs (loops.seat_loops));
    None for a send to no reviewer; a refusal (str) for a send to a reviewer that names no round of a loop it runs."""
    tool = str(tool or '')
    if tool.endswith('t3_thread_send'):
        name, seat = str(ti.get('clientRequestId') or ''), str(ti.get('threadId') or '')
    elif tool == 'SendMessage':
        name, seat = str(ti.get('summary') or ''), str(ti.get('to') or '')
    else:
        return ti, False, None, {}
    m = loops.round_of(name)
    if not (here := loops.seat_loops(seat) if seat else {}):
        return None
    if not (m and loops.continues(m[1], int(m[2]), here)):
        return (f"{seat} runs the review loop {', '.join(sorted(here))}, and a message to it is that loop's next round: name it `<loop>-r<N>` "
                f"({'clientRequestId' if tool.endswith('t3_thread_send') else 'summary'}), or `<loop>-ask<N>` for a maintainer's ask, "
                f"not {name or 'nothing'} (mergeworthy:delegate §Review rounds)")
    first = here.get(m[1]) or next((e for l, e in here.items() if e and loops.follows(m[1], l)), None)
    return {'task': str(ti.get('message') or ''), 'title': name, 'role': 'review', 'clientRequestId': name, 'threadId': seat}, True, first, here


def round_name(ti):
    """The name a launch gives its round: T3's clientRequestId, else the Agent tool's description."""
    return str(ti.get('clientRequestId') or ti.get('description') or '')


def thread(ti, response):
    """The reviewer a round ran in, which a later round is sent to: the one it was sent to, T3's childThreadId (delegate_task) or
    threadId (t3_thread_launch), or Claude Code's agentId."""
    r = t3_tasks.result(response) or {}
    return ti.get('threadId') or r.get('childThreadId') or r.get('threadId') \
        or (response.get('agentId') if isinstance(response, dict) else None)


def shell_round(command):
    """(the round `<loop>-r<N>` a shell reviewer's command names by its prompt file, that file's text, its path), else None."""
    for f in re.findall(r'(?<![\w.~/-])(~?/[^\s`\'"()<>$]+\.md)\b', command):
        if (m := loops.round_of(os.path.basename(f)[:-3])) and os.path.isfile(p := os.path.expanduser(f)):
            return m, open(p, errors='replace').read(), p
    return None


def seat_rounds(seat):
    """The rounds that ran in the reviewer seat (a T3 thread, a Claude agent), by the journal."""
    import review_journal
    return {e['n'] for f in glob.glob(os.path.join(review_journal.JOURNAL, '*', '*.jsonl')) for e in review_journal.events(f) if e.get('thread') == seat}


def started_on(session, prompt, loop, n):
    """The rounds before n of loop whose prompt file, beside prompt, began the shell reviewer's session file: the rounds it ran."""
    first = (agent_jobs.head(session)[0] or '').strip()
    found = set()
    for f in glob.glob(os.path.join(glob.escape(os.path.dirname(prompt)), '*.md')) if first else ():
        m = loops.round_of(os.path.basename(f)[:-3])
        if m and m[1] == loop and int(m[2]) < n and (text := open(f, errors='replace').read().strip()) and text in first: found.add(int(m[2]))
    return found


def last_active(tool, seat, launcher):
    """When the reviewer seat a round is sent to was last active, in epoch seconds, None when unknown: a T3 thread's newest message
    or run, a Claude Code agent's transcript (under launcher's session)."""
    if str(tool or '').endswith('t3_thread_send'): return steward.active_at(seat)
    p = agent_jobs.transcript({'handle': f'claude:{seat}', 'transcript': launcher})
    return p and os.path.getmtime(p)


def resumed(argv):
    """The session file a shell reviewer's command resumes (`codex exec resume <id>`, `claude -p --resume <id>`), '' when it
    resumes one it doesn't name or that doesn't exist (`--last`, `--continue`), None when it resumes none."""
    if os.path.basename(argv[0]) == 'codex':
        if 'resume' not in argv: return None
        ids = argv[argv.index('resume') + 1:]
        return next((f for i in ids for f in glob.glob(os.path.expanduser(agent_jobs.CODEX.replace('*.jsonl', f'*-{glob.escape(i)}.jsonl')))), '')
    for i, a in enumerate(argv):
        if a in ('-c', '--continue'): return ''
        if a in ('-r', '--resume') or a.startswith('--resume='):
            sid = a.partition('=')[2] or (argv[i + 1] if i + 1 < len(argv) else '')
            return next(iter(glob.glob(os.path.expanduser(f'~/.claude/projects/*/{glob.escape(sid)}.jsonl'))), '') if sid else ''
    return None


def fix_check(name, brief, at, ran):
    """Why round name, continuing the reviewer last active at at (None: unknown) that ran the rounds ran, is refused, '' when it
    may run: only a fix check (FIX_CHECK) of that reviewer's own findings, named by their ledger ids (R<round>.<n>, a round in
    ran), or a `<slice>-reverify` round, continues it, within WINDOW."""
    declared, recent = re.search(FIX_CHECK, brief, re.M), at and time.time() - at <= WINDOW
    named = dict(re.findall(r'\b(R(\d+)\.\d+)\b', brief))
    others = sorted(i for i, m in named.items() if int(m) not in ran)
    # a reverify continues the Loop A verifier on Loop B's commits, which fix none of its findings (converge step 3)
    if (m := loops.round_of(name)) and loops.name(m[1]).kind == 'reverify':
        return '' if recent else (f"{name} continues its verifier, but " + (f"it was last active {int((time.time() - at) / 60)} minutes ago, past {WINDOW // 60}" if at else
                                  "no record shows when it was last active") + ": launch it on a fresh verifier of that company with Loop B's commits (mergeworthy:converge step 3).\n")
    if declared and recent and named and not others: return ''
    why = ("its brief declares no fix check of that reviewer's own findings (a line `Review: <step> [<part>] fix-check`)" if not declared else
           f"that reviewer was last active {int((time.time() - at) / 60)} minutes ago, past {WINDOW // 60}" if at and not recent else
           "no record shows when that reviewer was last active" if not at else
           "its brief names no ledger id (`R<round>.<n>`) of that reviewer's own findings" if not named else
           f"its brief names {', '.join(others)}, findings of rounds that reviewer didn't run (it ran {', '.join(f'r{m}' for m in sorted(ran)) or 'none of this loop on record'})")
    return (f"{name} continues its reviewer, but {why}: launch the round on a fresh reviewer, of the other company than the main session's "
            "where one is available, its brief carrying the loop's ledger and the commits since, never the earlier reports (mergeworthy:delegate §Reviewers).\n")
