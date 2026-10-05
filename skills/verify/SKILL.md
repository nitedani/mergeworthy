---
name: verify
description: "Bug verification of a PR (reproduce-only): slicing, the verifier brief, the counting and dry rules, and the final verification after refactors."
---

# Bug verification

Split the code into slices one verifier can hold (e.g. core feature, backend and storage, runtime adapter, wire and client), per PR. For each slice, run a fresh-context verifier with the verifier brief below.

Counting rule:
- A candidate counts only with a spec or script that fails on the head and passes on the base (main, or the bottom PR for the top).
- It must trace to documented usage on both ends.
- A deliberate behavior doesn't count.
- A finding that fails 1.1.15 gets the disposition "accepted, not worth code" with its one-line reason; it never becomes code to make a pass dry. Loop A converges on real bugs, not on every imaginable edge case.
- The verifier lists every candidate it dropped, one line each with the reason.

When a pass finds bugs:
1. Fix each at its root cause, with a spec that fails first (show it failing on the parent), minimum diff, and the phantom gate passed. Re-run the verifier's own repro on the fixed build, and compare its output with the base's.
2. If the area has already had two corrective edits, stop patching. Rethink it as one rule that covers every case found so far, then implement that rule.
3. Put fixes to base code in the bottom PR (when there is a stack, `converge`), then merge up.
4. Queue another pass on that slice, and record it in the ledger.

Dry criteria:
- One dry pass is a strong signal, and two in a row are enough.
- Don't rerun a slice that is dry and whose code hasn't changed since.
- Every slice needs a dry pass after its last fix. A fix, a refactor or a revert in a slice's code re-opens it.
- Never drop a queued pass: the ledger lists every pass owed, and the PR isn't converged while one is outstanding.

Bugs outside the task's scope get a disposition (1.1.7).

### Final bug verification after the refactors

Once every scope converged, run one reproduce-only verifier per slice that compares the pre-refactor tree with the head:
- The old specs run on the new code, adapting only renames. Every failure must be an intended change.
- Side-by-side scripts run the same scenarios on both trees and diff the output.
- Include randomized or fuzz comparisons where the logic is combinatorial.

A regression found here means the refactor wasn't behavior-preserving: revert it, then run a fresh pass on that slice.

## Verifier brief

```
You are a bug verifier for <PR and slice>. Count only what you reproduce. Don't start subagents, don't commit, push or comment anywhere.

Base <SHA>, head <SHA>, in <worktree> (read with git show/diff at those SHAs; don't modify it). Your slice: <paths>. <What changed since the last pass, with the previous reports' paths, if any.>

What counts: through documented usage (the docs are the contract; the settled decisions are in <decision packet or PR body>), the head behaves wrongly where a user can see it: a regression against the base, or a fix that's incomplete for the scenario its commit names. A deliberate behavior (a usage error) doesn't count, nor a scenario no documented usage reaches on both ends. A candidate counts only with a spec or script that fails on the head and passes on the base.

How: read each change end to end with every caller; try the edges: <list the risky edges for this slice>. Make your own worktrees under <artifacts dir> (worktree add --detach, install, build) and remove them when done. Lanes you may run: <lanes>. Don't run <lanes owned by others>.

Write <artifacts dir>/<name>.md: each reproduced bug with its commit, the repro inline, observed vs expected; then every candidate you tried and dropped, one line each with why. If you found nothing, say so plainly and list what you tried. Final message: the count and one line each.
```
