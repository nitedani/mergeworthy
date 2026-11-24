#!/usr/bin/env python3
"""Use the same shell policy from the provider's native PreToolUse hook."""

import json
import os
from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parent.parent


def start(provider):
    rules = (ROOT / 'always-on.md').read_text()
    rules = rules.replace('with the Skill tool', 'from the installed plugin')
    home = Path.home()
    shared = home / '.mergeworthy'
    shared.mkdir(exist_ok=True)
    current = shared / 'current'
    try:
        current.symlink_to(ROOT, target_is_directory=True)
    except FileExistsError:
        pass
    (home / '.claude').mkdir(exist_ok=True)
    bins = home / '.local' / 'bin'
    bins.mkdir(parents=True, exist_ok=True)
    for tool in (ROOT / 'bin').iterdir():
        if not tool.is_file() or not os.access(tool, os.X_OK):
            continue
        try:
            shared_tool = current / 'bin' / tool.name
            (bins / tool.name).symlink_to(shared_tool if shared_tool.is_file() else tool)
        except FileExistsError:
            pass
    if provider == 'antigravity':
        return {'injectSteps': [{'systemMessage': {'systemMessage': rules}}]}
    return {'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': rules}}


def check(provider, event):
    if provider == 'antigravity':
        args = event['toolCall']['args']
        event = {
            'session_id': event['conversationId'],
            'transcript_path': event.get('transcriptPath'),
            'cwd': args['Cwd'],
            'tool_input': {'command': args['CommandLine']},
        }
    if not isinstance(event['tool_input']['command'], str) or not os.path.isabs(event['cwd']):
        raise ValueError('shell hook requires a command and an absolute working directory')
    event['tool_name'] = 'Bash'
    event['hook_event_name'] = 'PreToolUse'
    event['mergeworthy_provider'] = provider
    limit = min(float(os.environ.get('MERGEWORTHY_HOOK_SECONDS', 540)), 540)
    result = subprocess.run(
        [sys.executable, ROOT / 'hooks' / 'pre-bash-guard.py'],
        input=json.dumps(event), text=True, capture_output=True, timeout=limit,
    )
    if result.returncode == 0:
        return ''
    if result.returncode == 2 and result.stderr.strip():
        return result.stderr.strip()
    return f'Mergeworthy shell check exited {result.returncode} without a verdict.'


def main():
    provider, action = sys.argv[1:]
    if provider not in ('antigravity', 'codex') or action not in ('start', 'guard'):
        sys.exit('Usage: provider-hook.py (antigravity|codex) (start|guard)')
    if action == 'start':
        print(json.dumps(start(provider)))
        return
    try:
        reason = check(provider, json.load(sys.stdin))
    except (KeyError, TypeError, ValueError, OSError, subprocess.TimeoutExpired):
        reason = 'Mergeworthy could not check this command. Retry once and report the failure if it persists.'
    if provider == 'antigravity':
        print(json.dumps({'decision': 'deny', 'reason': reason} if reason else {'decision': 'allow'}))
    elif reason:
        print(json.dumps({'hookSpecificOutput': {
            'hookEventName': 'PreToolUse', 'permissionDecision': 'deny', 'permissionDecisionReason': reason,
        }}))


if __name__ == '__main__':
    main()
