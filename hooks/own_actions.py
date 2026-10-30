"""What this machine's agents did on GitHub themselves, so the watcher logs it without waking them: the heads they pushed
(PUSHED_HEADS) and the threads they merged or closed (CLOSED_THREADS: `owner/repo#N merged|closed`). pre-bash-guard writes a
command's entries as pending once it passed every check (intend); post-bash-register confirms them when the command succeeded and
drops them when it failed (settle). One still pending after PENDING_TTL (a session killed mid-command) counts as no one's."""
import fcntl, os, time

PENDING_TTL = 1800


def _path(var):
    return os.path.expanduser(os.environ.get(var, f"~/.claude/{var.lower().replace('_', '-')}.txt"))


def key(hook):
    """The command a PreToolUse and its PostToolUse hook input both name: its tool_use_id, else its session and text."""
    import hashlib
    return hook.get('tool_use_id') or hashlib.sha256(f"{hook.get('session_id')}\0{(hook.get('tool_input') or {}).get('command')}".encode()).hexdigest()[:32]


def intend(key, entries):
    """Records {var: [entry]} as pending for the command key (its tool_use_id)."""
    lines = [f"{int(time.time())} {key} {var} {e}\n" for var, es in entries.items() for e in es]
    if lines:
        with open(_path('OWN_PENDING'), 'a') as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            f.writelines(lines)


def settle(key, ok):
    """The command key ended: its pending entries become its own actions if ok, else they go."""
    try:
        f = open(_path('OWN_PENDING'), 'r+')
    except OSError:
        return
    with f:
        fcntl.flock(f, fcntl.LOCK_EX)
        rows = [l.rstrip('\n').split(' ', 3) for l in f if l.count(' ') >= 3]
        for var in {r[2] for r in rows if r[1] == key} if ok else ():
            with open(_path(var), 'a') as o:
                o.writelines(r[3] + '\n' for r in rows if r[1] == key and r[2] == var)
        f.seek(0)
        f.truncate()
        f.writelines(' '.join(r) + '\n' for r in rows if r[1] != key and time.time() - int(r[0]) < PENDING_TTL)


def state(var, match):
    """'done' when an action of var whose entry match() accepts succeeded, 'pending' while its command still runs, else None."""
    def lines(p):
        try: return open(p).read().splitlines()
        except OSError: return []
    if any(match(l) for l in lines(_path(var))):
        return 'done'
    rows = [l.split(' ', 3) for l in lines(_path('OWN_PENDING')) if l.count(' ') >= 3]
    return 'pending' if any(r[2] == var and time.time() - int(r[0]) < PENDING_TTL and match(r[3]) for r in rows) else None
