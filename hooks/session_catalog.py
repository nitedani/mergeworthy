#!/usr/bin/env python3
"""The skill catalog a session loaded, recorded in ~/.mergeworthy/sessions/<session id> as `<version folder> graph|v1 <source>
<UTC time>`: pre-skill-gate and pr-steps read it. Records older than 30 days go. Run by session-start, with Claude Code's
SessionStart input on stdin and the session's plugin folder in $CLAUDE_PLUGIN_ROOT; hooks/agy.py calls record."""
import json, os, select, sys, time


def path(session_id):
    """Where session session_id's record is."""
    return os.path.join(os.path.expanduser('~/.mergeworthy/sessions'), os.path.basename(session_id))


def record(session_id, root, source):
    """Records the catalog in plugin folder root as the one session session_id loaded, at source (startup, resume, compact)."""
    catalog = 'graph' if os.path.isfile(os.path.join(root, 'skills', 'task', 'SKILL.md')) else 'v1'
    line = ' '.join([os.path.basename(os.path.realpath(root)), catalog, source or '-', time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())])
    sd = os.path.expanduser('~/.mergeworthy/sessions'); os.makedirs(sd, exist_ok=True)
    for f in os.listdir(sd):
        try:
            if os.path.getmtime(os.path.join(sd, f)) < time.time() - 30 * 86400: os.remove(os.path.join(sd, f))
        except FileNotFoundError: pass  # another session's start took it
    open(path(session_id), 'w').write(line + '\n')


if __name__ == '__main__':
    d = json.loads(sys.stdin.read() or '{}') if select.select([sys.stdin], [], [], 1)[0] else {}
    if d.get('session_id') and os.environ.get('CLAUDE_PLUGIN_ROOT'):
        record(d['session_id'], os.environ['CLAUDE_PLUGIN_ROOT'], d.get('source'))
