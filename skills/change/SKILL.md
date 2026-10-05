---
name: change
description: "When you are about to write code for an issue or a task: check it isn't fixed, reproduce it, find an approach that rates high, build the smallest diff, show it working."
---

## When

You are about to make the first edit for an issue or a scope item.

## Steps

1. Check it isn't already fixed: `git log` on the files involved, open and merged PRs, and who is assigned. Confirm a hit in today's code before stopping on it.
2. Read the repo's `AGENTS.md` or `CLAUDE.md` on the base branch, and work in your own worktree: `git worktree add -b <branch> <artifact root>/<branch> origin/<base>`.
3. Reproduce the problem with one command that fails on the symptom (a test, a request, a browser script), and keep it red while you cut it down. For a cause that isn't obvious, write three to five candidate causes, each with what it predicts, before testing any.
4. Rate two or three approaches, including not building it, from 0 to 10 on how sure you are each is the obviously right one; stop and say why if none rates above 6.
5. Build the smallest diff that finishes the job, everywhere it applies: every call site, every locale. Add at most one regression test, in an existing suite, with its expected value taken from outside the code.
6. Run the repo's gates; the exit code is the verdict, not your reading of the output.
7. Show it working in the real app, per [evidence.md](evidence.md), and capture the before and after.
8. Stop every server, browser and process you started, by its PID.

## Done when

The gates pass, the before and after are captured, and nothing you started is still running.

## Never

- Claim it works from a unit test alone when the change is visible to a user.
- Use a port or a browser profile another run holds.
- Touch the user's own checkouts: read other branches with `git worktree add --detach`.

## Enforced by

`pre-bash-guard` (blocks `pkill -f`, `killall`, a bare `git stash`, and a force-push without `--force-with-lease=<branch>:<sha>`).

## Next

`mergeworthy:pr`.
