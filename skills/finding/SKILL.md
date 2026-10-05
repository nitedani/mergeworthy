---
name: finding
description: "When a reviewer, CI or your own idea suggests a change: decide whether it earns code, and how to fix or remove things safely."
---

## When

A reader, a verifier, CI or your own idea produces a candidate change.

## Steps

1. Treat it as a candidate, per **Earn every line**: how often does a real user hit it, how bad is it then, what does the existing code do in the same case, and what does it cost in lines, state and tests?
2. Check the fix is real before writing it:
   - **Reachable:** a documented use reaches it, traced on both ends (caller and callee, client and server).
   - **Not deliberate:** it doesn't change a behavior someone chose on purpose.
   - **True:** its comments are literally true.
   - **Possible:** it guards a state that can happen; an impossible state gets an assertion or nothing.
3. Before removing a guard, a retry or a cache, run a probe that could fail, through real use; a failure keeps it, with the failure recorded.
4. Leave code someone else wrote unchanged on your reading alone: list the finding for its owner with a recommendation.
5. Rethink an area that has already taken two corrective edits as one rule that covers every case so far, and implement that rule.
6. Write the finding's disposition in one line in `ledger.md`: fixed in <sha>, or accepted with the reason.

## Done when

Every finding has a one-line disposition.

## Never

- Add code because a reviewer said so, without weighing it.
- Call a mechanism dead because no test fails without it.

## Enforced by

Nothing: this is judgment.

## Next

Back to the page you came from.
