---
name: turn-end
description: "When you are about to end a turn or report to the user: answer first, report what changed, and leave nothing silently pending."
---

## When

You are about to end a turn or report to the user.

## Steps

1. List every message the user sent since your last reply, and answer each in your first lines.
2. Give the outcome, or the action you need from them, next.
3. Report each PR and issue with its title, link and state; what was found and fixed since the last report; what is still running and what it waits on.
4. Keep it near 12 lines, with local files as absolute paths, and state mistakes and skipped steps plainly.
5. Ask only per **Do, don't offer**, as one line starting `GENUINE-FORK:` with your recommendation, and keep working on everything else.
6. End the turn only when everything pending will wake you: a job you are waiting on has a background notification, and a watched thread has a live Monitor.

## Done when

Every user message has its answer, and nothing pending can finish without waking you.

## Never

- End with an offer or "should I…?".
- Narrate your steps or restate the user's instructions.
- Call something done that you didn't verify.

## Enforced by

`stop-lint` (blocks a turn that ends with an offer, after a post without a live Monitor, or while a reply is owed).

## Next

Nothing.
