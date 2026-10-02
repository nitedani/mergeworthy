---
mode: implement
use: Execute your plan: a few key points in order, commit, and run the acceptance checks. Needs --write, in a worktree you created for it.
requires: Goal, Plan, Acceptance
write: true
---
## Instructions
Implement the Plan, step by step, then commit on the current branch and run every Acceptance check. The approach is the Plan's: if a step turns out wrong or impossible, stop and report it in deviations instead of choosing another approach.

## Ticket
- Goal: the observable outcome.
- Plan: your key points, in order (which function, what rule, what not to touch).
- Acceptance: the commands that define done.
- Facts, Scope: as for facts.
