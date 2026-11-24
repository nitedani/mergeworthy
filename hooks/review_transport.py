"""How a review round reaches its reviewer, for pre-agent-dedupe: a launch (Agent, Task, delegate_task, t3_thread_launch) is a round
by its name; a t3_thread_send is one only as a later round `<loop>-r<N>` sent to a thread an earlier round of that loop ran in
(delegate §Continue), its message the task and its round name the title; any other send is no launch."""
import loops, t3_tasks


def as_launch(tool, ti):
    """(the tool input as the launch it is, whether it was sent to a running reviewer); None for a send that is no review round."""
    if not str(tool or '').endswith('t3_thread_send'):
        return ti, False
    cid, thread = str(ti.get('clientRequestId') or ''), str(ti.get('threadId') or '')
    m = loops.round_of(cid)
    if thread not in (loops.threads(m[1]) if m and int(m[2]) >= 2 else []):
        return None
    return {'task': str(ti.get('message') or ''), 'title': cid, 'role': 'review', 'clientRequestId': cid, 'threadId': thread}, True


def round_name(ti):
    """The name a launch gives its round: T3's clientRequestId, else the Agent tool's description."""
    return str(ti.get('clientRequestId') or ti.get('description') or '')


def thread(ti, response):
    """The T3 thread a round ran in: the one it was sent to, or the childThreadId T3's result names; None on Claude Code."""
    return ti.get('threadId') or (t3_tasks.result(response) or {}).get('childThreadId')
