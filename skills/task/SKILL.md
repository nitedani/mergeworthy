---
name: task
description: "When the user gives a task or writes /ai or /agent on GitHub: size it, record every ask, find what exists, plan the critical path."
---

## When

The user gives you a task, writes `/ai` or `/agent` on a GitHub thread, or you resume a session whose `scope.md` still has unchecked boxes.

## Steps

1. Read the task and every link in it, recursively: issues, PRs, review comments, CI. Pull the default branch.
2. Make the artifact root `<task>-work/` next to the repo, never in `/tmp`, for notes, logs, drafts and scratch worktrees.
3. Write `scope.md`: every ask as a checkbox, then the critical path, the ordered list of what blocks the goal.
4. Size the task and state the size in your first report:
   - **Answer:** nothing to change.
   - **Fix:** one bounded change in one repo.
   - **Feature:** a new capability, a changed contract, or several changes.
   - **Program:** several repos or several decision makers.
5. Find what exists before building: open PRs and issues on the topic, other sessions' work, and how the maintainers shipped the same kind of change in their last five merged PRs.
6. Note who decides each part (**Owners decide**).
7. Keep `ledger.md` (one line per event: what, which head, the result) for a feature or a program, and `decisions.md` (decision, who, when, link, what it beat) when people decide things.
8. Open one umbrella issue for a program, listing every PR with its state, and update it in the same step as every event.

## Done when

`scope.md` holds every ask and the critical path, and your first report states the size.

## Never

- Start side work while the next critical-path item isn't moving.
- Ask something the user already answered.

## Enforced by

Nothing: this is judgment.

## Next

`mergeworthy:design` for a new API or a restructure, `mergeworthy:change` for code, `mergeworthy:turn-end` for an answer.
