"""How a review round reaches its reviewer: a launch (Agent, Task, delegate_task, t3_thread_launch) is a round by its name; a send
(T3's t3_thread_send, Claude Code's SendMessage) to a reviewer (loops.seat_loops) is a round `<loop>-r<N>` that continues it
(loops.continues, delegate §Continue), its message the task and its round name the title, and refused naming none; a send to
anyone else is no launch. A shell
reviewer (`codex exec`, its `resume`, `claude -p`) is a round by its prompt file's name, `<loop>-r<N>.md`."""
import os, re
import loops, t3_tasks


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
    first = here.get(m[1]) or next((e for l, e in here.items() if e and l.startswith(m[1].rsplit('-', 1)[0])), None)
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
    """(the round `<loop>-r<N>` a shell reviewer's command names by its prompt file, that file's text), else None."""
    for f in re.findall(r'(?<![\w.~/-])(~?/[^\s`\'"()<>$]+\.md)\b', command):
        if (m := loops.round_of(os.path.basename(f)[:-3])) and os.path.isfile(p := os.path.expanduser(f)):
            return m, open(p, errors='replace').read()
    return None
