# Monitor fix notes (2026-10-04)

Task: fix the 30-min "wakes for nothing" loop in the watcher's belt-and-braces tail.

## Problem (measured in t3code-cc1ce9af session)
- Harness re-invokes the session whenever a background task hits its timeout.
- Documented pattern: arm `tail -n 0 -F events.log | grep ...` as a background task, timeout 1800s -> wakes every 30 min, empty when quiet.
- While a live tail exists, the daemon suppresses its own wake (`session_watching()` in gh-watch.py:83-95, used in wake_agent:104).
- Daemon wake path proven end-to-end: watch-204/wake.log shows a woken `claude -p` agent caught up, edited the posted reply in place through the gate (dropped false "zero runtime deps"; src/package.json has 16), advanced events.cursor, cleared replies-owed.md.
- Stop hook (stop-lint.py:58-67) accepts ANY live `tail` process on the dir's events.log as the armed monitor.

## Design decision
1. Daemon wake becomes the ONLY event handler: wake_agent no longer suppressed by a live tail. One woken agent per dir (wake.pid), serializes itself; prompt already skips events before events.cursor.
2. Tail becomes persistent + detached (nohup, `>> <dir>/tail-events.log`, never expires, no harness notification) -> no periodic wakes. Still satisfies the Stop hook (/proc scan) and archives events.
3. Live session acting on a thread: first check (a) events.cursor — if past an event, it is handled, skip; (b) wake.pid — if a woken agent is running for the dir, the event is being handled, don't race it.
4. gh-watch-start prints the persistent-arm one-liner (nohup, idempotent via a `tail.pid` pidfile guard); drops "re-arm on every expiry".
5. Text updates: part5-mechanisms.md (gh-watch row + stop-hook row + gh-watch-start row), part1/05-the-live-github-loop.md (1.5 paragraph), local-model/prompts/claude-local-overrides.md (No-Monitor-tool line).
6. build.sh --all, install-methodology (local profile), commit only my files (leave other session's 01-always-on.md WIP + untracked test files out), re-arm watch-204 with the new persistent tail (kill old harness tails by PID), verify.

## Files to change
- claude/watcher/gh-watch.py (wake_agent, drop session_watching)
- claude/watcher/gh-watch-start (printed arm command)
- methodology/part5-mechanisms.md, methodology/part1/05-the-live-github-loop.md
- local-model/prompts/claude-local-overrides.md

## Facts (verified, with source)
- The arm one-liner works as printed, run via `bash -c` (the Bash tool's runner): first run starts exactly one chain (nohup execs sh, PID 1671733, child `tail` 1671735); second run prints "tail already running" — idempotent via the pidfile guard. /tmp/tailtest, 2026-10-05.
- The chain archives: appending `### TEST EVENT line to capture` to events.log landed in tail-events.log within 2 s. A plain text line was also captured — expected: the filter's `^[^ =]` exists to catch event body lines (gh-watch.py:336 emits multi-line comment bodies `### …\n{body}\n`) and Python traceback lines; indented lines are dropped (archive, not a full log).
- `pgrep -x tail` guard was wrong: ps showed 4 unrelated `tail` processes from other watchers — it would false-positive and skip arming. Replaced with the pidfile guard: `if [ -s $dir/tail.pid ] && kill -0 $(cat $dir/tail.pid) 2>/dev/null; then echo tail already running; else nohup … & echo $! > $dir/tail.pid; fi` (gh-watch-start:47).
- Stale pidfile is self-healing: if the process dies, `kill -0` fails and the next arm restarts the chain.
- Test chain cleaned up by killing its own PID only (1671733); the other four tail procs (1495790, 1496085, 1509679, 1671720) belong to other watchers and were left alone.
- stop-lint.py:58-67 `armed_tail()` scans /proc for live `tail` processes on a registered dir's events.log — the persistent nohup tail satisfies it without expiring.
