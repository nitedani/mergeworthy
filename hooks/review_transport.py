"""How a review round reaches its reviewer: a launch (Agent, Task, delegate_task, t3_thread_launch) is a round by its name; a send
(T3's t3_thread_send, Claude Code's SendMessage) is one only as a round `<loop>-r<N>` that continues the reviewer it is sent to
(loops.continues, delegate §Continue), its message the task and its round name the title; any other send is no launch. A shell
reviewer (`codex exec`, its `resume`, `claude -p`) is a round by its prompt file's name, `<loop>-r<N>.md`."""
import os, re
import loops, t3_tasks


def as_launch(tool, ti):
    """(the tool input as the launch it is, whether it was sent to a running reviewer); None for a send that is no review round."""
    tool = str(tool or '')
    if tool.endswith('t3_thread_send'):
        name, seat = str(ti.get('clientRequestId') or ''), str(ti.get('threadId') or '')
    elif tool == 'SendMessage':
        name, seat = str(ti.get('summary') or ''), str(ti.get('to') or '')
    else:
        return ti, False
    m = loops.round_of(name)
    if not seat or not (m and loops.continues(m[1], int(m[2]), seat)):
        return None
    return {'task': str(ti.get('message') or ''), 'title': name, 'role': 'review', 'clientRequestId': name, 'threadId': seat}, True


def round_name(ti):
    """The name a launch gives its round: T3's clientRequestId, else the Agent tool's description."""
    return str(ti.get('clientRequestId') or ti.get('description') or '')


def thread(ti, response):
    """The reviewer a round ran in, which a later round is sent to: the one it was sent to, T3's childThreadId, or Claude Code's agentId."""
    return ti.get('threadId') or (t3_tasks.result(response) or {}).get('childThreadId') \
        or (response.get('agentId') if isinstance(response, dict) else None)


def shell_round(command):
    """(the round `<loop>-r<N>` a shell reviewer's command names by its prompt file, that file's text), else None."""
    for f in re.findall(r'(?<![\w.~/-])(~?/[^\s`\'"()<>$]+\.md)\b', command):
        if (m := loops.round_of(os.path.basename(f)[:-3])) and os.path.isfile(p := os.path.expanduser(f)):
            return m, open(p, errors='replace').read()
    return None
