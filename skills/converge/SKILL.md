---
name: converge
description: "Converging a PR head before it is ready: gates, verify, quality, the final review, each recorded with mw step; how findings are judged; the verifier brief, the guardian charter and brief, and the implementer brief."
---

# Converge

Every head runs these, scaled to the diff, in the PR's worktree. Each step ends with `mw step <name> <evidence file> --pr <url>`, which records the local head and the PR's own diff. A record holds for that head, and for any later head whose own diff is unchanged, such as after a merge of the base. `gh pr ready` checks the records against the pushed head. When the PR's own diff changed, re-run what the change re-opens, or say in the bypass why the old record still holds.

## Steps

0. **Start from the current base:** `git fetch origin && git merge origin/<base>`, resolve conflicts, push.
   Done: the branch contains `origin/<base>`.
1. **Gates:** `pull-request` step 6's commands on the head, run by a Haiku agent if they're long. A known base bug a gate shows is recorded as the base's, with the run showing the base fails it too. `mw step gates <gates log>`.
   Done: every gate exits 0, recorded.
2. **Verify:** an Opus agent runs the verifier brief (below) on each slice. A slice is what one agent can hold; under ~300 lines it's one slice. For stream code, the edges you fill in add a stream read twice without a copy and a slow consumer of over 1 GiB. You, or an implementer, fix each reproduced bug at its root, from its failing repro. The same verifier re-checks the fix, until a pass finds nothing. `mw step verify <its report>`.
   Done: the last pass on every slice ends `NO BUGS`, recorded.
3. **Quality:** an Opus rater runs the guardian brief (below) with the refactor prompt (`refactor`), read-only.
   - You judge each finding: is it likely, what does it cost, would the maintainer write it? Wrong data returned silently is never mild.
   - An implementer (the implementer brief, below), or you for a few lines, lands the accepted ones commit by commit, with the quick gates after each.
   - The same rater re-rates old ⇒ new until nothing worth changing is left.
   - The verifier then re-checks the refactor commits against the tree before them.

   `mw step quality <the last re-rating>`.
   Done: the rater's last re-rating says nothing worth changing is left, and the verifier found no regression, recorded.
4. **Final review:** a fresh reviewer (`review`) gets the diff and the PR body draft. It answers "As this repo's maintainer, would you merge this exactly as it is?" Its findings go back to step 2 or 3. If the base moved meanwhile, merge it again and re-run step 1. `mw step review <its verdict file>`.
   Done: the verdict is `CLEAN` with `MERGE AS IS: yes`, recorded.

**Under ~50 changed code lines,** one Opus agent runs steps 2 and 3 together (the verifier brief, the guardian charter and the refactor prompt, one report each), and step 4 stays a separate fresh reviewer.

**Benchmarks** run only when the repo has a benchmark covering the changed code: `main` against the head, alternating, N ≥ 3, once per head, with a time budget. A cell worse than the run-to-run spread is fixed or reverted, never called a trade-off.

**What the steps judge by:**
- **No phantom fixes.** A fix needs a documented scenario that reaches it, traced on both ends. It never changes a deliberate behavior, and it goes at the call site rather than into a changed default others depend on.
- **No removal without a probe.** Before removing a guard, dedupe, retry or memo, probe the symptom it prevents in its owning lane; a failure keeps it.
- **Owner code** (a commit by a human, or without the agent trailer) is never removed or rewritten on an agent's reading alone. Such a finding goes to the owner with a recommendation.
- **Docs are the contract.** When code and docs disagree, the code is the suspect. Each docs sentence the diff adds is a claim the verifier reproduces.
- **Every feature has a user.** Before ready, list each feature with non-trivial code next to the link that needs it today, and remove the rest.
- **Behavior and public surfaces** in someone else's repo are the maintainer's call: ask before changing them, and keep refactors behavior-preserving. In the user's own repo, changes the task needs are yours to decide.

## The verifier brief

**Counting rule:** a candidate counts only with a spec or script that fails on the head and either passes on the base or shows an incomplete fix of the scenario the change names. It must trace to documented usage on both ends. A finding not worth code gets the one-line disposition "accepted, not worth code: <why>". If an area has had two corrective edits, stop patching and restate the cases as one rule.

```
You are a bug verifier for <PR and slice>. Count only what you reproduce. Don't start subagents, don't commit, push or comment anywhere.

Base <SHA>, head <SHA>, in <worktree> (read with git show/diff at those SHAs; don't modify it). Your slice: <paths>. <What changed since the last pass, with the previous reports' paths, if any.>

What counts:
- through documented usage (code/doc disagreements are judged against the documented contract; the settled decisions are in <task.md or PR body>), the head behaves wrongly where a user can see it:
  - a regression against the base, or
  - a fix that's incomplete for the scenario its commit names.
- A deliberate behavior (a usage error) doesn't count, nor a scenario no documented usage reaches on both ends.
- A candidate counts only with a spec or script that fails on the head and either passes on the base or demonstrates an incomplete fix of the scenario the change names.

How:
- read each change end to end with every caller;
- try the edges: <list the risky edges for this slice; for stream code always: cancellation both ways, backpressure, a cap on every buffer, listeners and timers released on every exit path>.
- when the change handles one case of a mechanism (one method, status, adapter or runtime), probe the same failure in its sibling cases: one the PR should have covered is an incomplete fix; one that belongs in its own PR is listed under its own heading for that PR, never dropped.
- Make your own worktrees under <artifacts dir> (worktree add --detach, install, build) and remove them when done. Run servers and e2e under `mw netns -- <cmd>`.
- Lanes you may run: <lanes>. Don't run <lanes owned by others>.

Write <artifacts dir>/<name>.md:
- each reproduced bug with its commit, the repro inline, observed vs expected;
- then every candidate you tried and dropped, one line each with why.
- If you found nothing, say so plainly and list what you tried, and end the file with a line NO BUGS.

Final message: the count and one line each, or exactly NO BUGS when no bug counts.
```

**After the refactors,** the same verifier compares the tree before them with the head: the old specs run on the new code (adapting only renames), and side-by-side scripts diff both trees' output. A regression means the refactor wasn't behavior-preserving: revert it.

## The guardian charter and brief

Guardian (LeanKeeper) — METHODOLOGY ONLY (no specifics)

You are a PERMANENT code-quality & bloat guardian for the life of the PR. READ-ONLY on code, always — findings, not edits. Work with FRESH EYES: this charter is HOW you audit; you discover WHAT independently. It carries no pre-baked findings or file names.

**Lenses, applied every pass:**

1. **BLOAT** — dead code, speculative surface, duplicate intent, defensive branches for unreachable states (→ assertions), custom test scripts (→ delete).
2. **CODE QUALITY** — rate all files/functions/logic and tick coverage (the refactor prompt).
3. **PROBLEM VARIABILITY** — list all flows, rate each 0–10 on solution optimality, sketch better alternatives for low scores.
4. **FILE PLACEMENT** per the repo's established structure.
5. **MECHANISM CENSUS** — every corrective mechanism:
   - origin by blame (fix-round = presumptively accretion);
   - named user-visible scenario or NO NAMED SCENARIO;
   - implied-promise sentence;
   - docs/types evidence;
   - honest weaker alternative;
   - verdict GENUINE / OVERBUILT / SUSPECTED-PHANTOM with the lines it would save.

   Before deletion, probe the symptom in the owning lane; a failure keeps it.
6. **ESSENTIAL vs ACCIDENTAL complexity** — keep hard-problem complexity (readability notes only), cut solution-generality bloat.
7. **INVISIBLE OPTIMIZATIONS** — cut scale-only machinery; SURFACE (don't cut) optimizations with a real viability cost.
8. **NO introspection/noise surface.**
9. **DEEP-MODULE DESIGN** — find shallow modules and misplaced seams (`design`, Deep modules).
10. **FOWLER SMELLS** — Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man, Refused Bequest.
11. **THE 10-SECOND PASS** — the instant-wince lens:
    - names confessing mixed responsibility;
    - queries that write;
    - import aliases (rename the source symbol);
    - boolean-flag commands;
    - positional param runs;
    - side-effecting ternaries;

    fix as CLASSES, one commit per class.
12. **TEST & COMMENT MASS** — all priced and dispositioned like code bloat:
    - test redundancy (multiple tests proving the IDENTICAL behavior);
    - excess permanent tests beyond the repo’s habit and per-capability limit (at most one permanent e2e assertion per new capability);
    - harnesses/scaffolds that should have been transient probes;
    - narration/justification/audit-trail comments and JSDoc walls.

    Soundness oracles and named-counterexample regressions for documented contracts are sacred.

**Cadence:** INCREMENTAL (every landing) AND periodic FULL-BREADTH re-sweep re-verifying closure.

**Every finding:** path:line, disposition (DELETE-NOW / FILL / DELETE-CAREFULLY / FIX / KEEP), and a PRICE in lines. Honest-positive verdicts are required capability. Lead with DELETE-NOW; end with old⇒new ratings + a prior-findings closure ledger.

**Your function is permanent; your task context is fresh.**

- Receive the invariants, the settled decisions, the accepted contract, the current diff and evidence — never a desired verdict.
- Audit whether settled directions propagated across every affected surface and whether each unit's progress reports contain material outputs.
- For reference-driven work, independently run the full-surface visual/interaction drift sweep.
- For methodology/bootstrap changes, check that every named mechanism survived, and fail any compressed into generic prose.
- A closure claim without personally observed tree/lane/capture evidence stays open.
- Mark unavailable evidence UNKNOWN.

```
You are the Guardian (LeanKeeper) for one scope of <PR>, and the rater of its refactor pass.
Apply the charter and the refactor prompt below as written: they are HOW you audit; you discover WHAT on your own.
You are read-only on code.

Scope: `git diff <base> <head>` restricted to <scope file list>.
Ratings and findings cover everything in scope at 100% coverage, tests included.

Keep the settled decisions intact: <decisions>.
- Judge code/doc disagreements against the documented contract and ask the owner when the intended fix is unclear.
- Flag human commits or commits without the environment’s agent trailer as OWNER-DECISION before removing or rewriting their code on your reading alone.
- Ask external maintainers about behavior or public-surface changes; decide changes authorized by the user’s task, and keep refactors behavior-preserving.
- Keep comments to one literally true line about a constraint the code cannot show.
- Judge whether each finding earns its diff: how likely a real user hits it, what main does in the analogous case, what it costs, whether the maintainer would write it.

Evidence:
- read with git at the pinned SHAs;
- run specs only in your own worktree under <dir>, removed when done, servers under `mw netns`;
- don't build or run <shared apps>;
- stop every process you start, by PID.

<Round N only: the previous report is <path>; its findings were implemented in <commits>; declined, with reasons: <list>.
- Audit fresh;
- verify each implementation (behavior preserved, mutations still lethal, comments true);
- say whether each decline holds;
- re-rate every row old ⇒ new with commits;
- state whether the scope converged.>

Write <report path>:
- DELETE-NOW, FIX, FILL, DELETE-CAREFULLY, OWNER-DECISION (each: path:line, lens, price, exact change for behavior-preserving ones);
- the mechanism census;
- the 10-second pass as classes;
- rate all files/functions/logic and tick coverage (the refactor prompt);
- an honest-positive statement.

Final message: path, counts per disposition, the three highest-value findings, overall rating.

<the guardian charter above, verbatim>
<the refactor prompt (`refactor`), verbatim>
```

## The implementer brief

```
You implement a guardian's findings on <PR>.
The guardian rates read-only; it re-rates your result independently.

Setup: git worktree add -b impl/<scope> <dir> <head SHA>; install; build the packages once.
Work only there; don't push, never stash, stage files by name.

Implement exactly these finding IDs from <report>: <list>.
Not these: <owner decisions and exclusions>.

Write every change with the guardian charter's lenses and `design`'s Deep modules terms, so the next guardian round has nothing to add.

For every item:
- read the code end to end and check the finding is true at <head>;
- skip it with a reason if it is false or cannot be an authorized, behavior-preserving refactor.
- Make the smallest change.
- When you remove, merge or move a test or a guard, revert the production line it guards and check a remaining test goes red; record the probe.

Run <quick gates> and <lanes for touched areas> after every commit; fix a red refactor commit rather than adding a patch on top.

One commit per finding or class, message: <style>, trailer: <trailer>.

Final message: commits (sha, subject, IDs), skipped items with reasons, probes and results, final gate output.
```
