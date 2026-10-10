---
name: converge
description: "Bringing a PR's latest commit to merge quality before it is marked ready: the checks, the bug hunt, the quality review and the final review, each recorded with mw step; how findings are judged; the briefs for the bug verifier, the quality guardian and the implementer."
---

# Converge

Converging a PR means running four steps on its latest commit (its head) until none of them finds anything: the checks, a bug hunt, a quality review, and a final review. Run them in the PR's worktree, every time the head changes, with depth scaled to the size of the diff.

Each step ends with `mw step <name> <evidence file> --pr <url>`. It records that the step ran on the local head, together with an ID of the PR's own diff (its changes against the base branch). A record holds for that head. It also holds for any later head whose own diff is the same, for example after you merge the base branch in. When you run `gh pr ready`, a mergeworthy hook compares the records with the pushed head and stops the command if a step is missing. When the PR's own diff changed, run again the steps the change affects. Or, if an old record still holds, add the bypass line the hook prints, and say why in it.

A lane, in these steps, is one of the repo's test suites that runs the product in a real setup: production-mode end-to-end tests, a specific adapter, transport or runtime, the examples. The lane that owns a piece of code is the one that exercises it for real. The quick checks are the fast ones: lint, type check, unit tests.

## Steps

0. **Start from the current base branch:** `git fetch origin && git merge origin/<base>`, resolve conflicts, push.
   Done: the branch contains `origin/<base>`.
1. **Checks:** run the commands from `mergeworthy:pull-request` step 6 on the head. If they're long, a Haiku agent runs them. When a check fails because of a bug already known on the base branch, record the failure as the base's, with a run that shows the base fails it too. Then `mw step gates <log of the checks>`.
   Done: every check exits 0, and the step is recorded.
2. **Bug hunt:** an Opus agent runs the verifier brief (below) on each slice of the diff. A slice is as much code as one agent can keep in mind. A diff under about 300 lines is one slice. For code that handles streams, add these edge cases to the ones you list in the brief: the same stream read twice without a copy, and a slow consumer of more than 1 GiB. You, or an implementer agent, fix each reproduced bug at its root, starting from the script that reproduced it. The same verifier then checks the fix again. Repeat until a pass finds nothing. Then `mw step verify <its report>`.
   Done: the last pass on every slice ends with `NO BUGS`, and the step is recorded.
3. **Quality:** an Opus agent, the rater, runs the guardian brief (below) together with the refactor prompt (`mergeworthy:refactor`). It reads the code but doesn't change it.
   - You judge each finding. How likely is it to matter? What does fixing it cost? Would the maintainer write this change? Wrong data returned silently is never a minor finding.
   - An implementer agent (the implementer brief, below) commits the accepted findings one by one, running the quick checks after each. For a few lines, you do it yourself.
   - The same rater rates the code again, showing old rating ⇒ new rating, until nothing worth changing is left.
   - The verifier then checks the refactor commits against the code before them, for changes in behavior.

   Then `mw step quality <the last re-rating>`.
   Done: the rater's last re-rating says nothing worth changing is left, the verifier found no regression, and the step is recorded.
4. **Final review:** a fresh reviewer (`mergeworthy:review`) gets the diff and the draft PR description. It answers "As this repo's maintainer, would you merge this exactly as it is?" You send its findings back through step 2 or 3. If the base branch moved in the meantime, merge it again and re-run step 1. Then `mw step review <its verdict file>`.
   Done: the verdict is `CLEAN` with `MERGE AS IS: yes`, and the step is recorded.

**Under about 50 changed lines of code,** one Opus agent runs steps 2 and 3 together, with the verifier brief, the guardian charter and the refactor prompt, and writes one report for each. Step 4 is still a separate fresh reviewer.

**Benchmarks** run only when the repo has a benchmark that covers the changed code. Run `main` and the head in turns, at least 3 times each, once per head, with a time budget. When a result is worse than the normal variation between runs, fix the change or revert it. Never call it a trade-off.

**How the steps judge findings:**
- **No phantom fixes.** A phantom fix guards against a problem that no real usage can cause. A fix needs a documented scenario that reaches it, traced from where the user starts to where the code fails. It never changes a behavior someone chose on purpose. It goes at the call site, not into a changed default that other code depends on.
- **No removal without a probe.** Before you remove a guard, a deduplication, a retry or a cache, try to make the symptom it prevents happen, in the lane that owns that code. If the symptom appears, keep it.
- **Code the owner wrote** (a commit by a human, or a commit without the agent trailer) is never removed or rewritten because an agent read it that way. Send such a finding to the owner, with a recommendation.
- **The docs are the contract.** When code and docs disagree, suspect the code. Each sentence of docs the diff adds is a claim the verifier reproduces.
- **Every feature has a user.** Before the PR is ready, list each feature with non-trivial code, next to the link that shows someone needs it today. Remove the rest.
- **Behavior and public API** in someone else's repo are for the maintainer to decide. Ask before changing them, and keep refactors from changing behavior. In the user's own repo, you decide the changes the task needs.

## The verifier brief

**What counts as a bug:** a candidate counts only with a test or script that fails on the head, and that either passes on the base or shows that the fix is incomplete for the scenario the change names. It must trace back to documented usage at both ends: where the user starts and where it fails. A finding not worth code gets one line: "accepted, not worth code: <why>". If an area has already needed two corrections, stop patching it, and restate the cases as one rule.

```
You are a bug verifier for <PR and slice>. Count only what you reproduce. Don't start subagents. Don't commit, push or comment anywhere.

Base <SHA>, head <SHA>, in <worktree>. Read the code with git show/diff at those SHAs, and don't modify the worktree. Your slice: <paths>. <What changed since the last pass, with the paths of the previous reports, if any.>

What counts:
- Through documented usage, the head behaves wrongly in a way a user can see:
  - a regression against the base, or
  - a fix that's incomplete for the scenario its commit names.
- When code and docs disagree, judge against the documented behavior. The settled decisions are in <task.md or PR description>.
- A behavior chosen on purpose (an error for misuse) doesn't count. Neither does a scenario that no documented usage can reach from start to end.
- A candidate counts only with a test or script that fails on the head, and that either passes on the base or shows the fix is incomplete for the scenario the change names.

How:
- Read each change from start to end, with every caller.
- Try the edge cases: <list the risky edge cases for this slice. For stream code, always: cancellation from either side, backpressure, a size limit on every buffer, listeners and timers released on every exit path>.
- When the change handles one case of a mechanism (one method, status code, adapter or runtime), try the same failure in the other cases. One this PR should have covered is an incomplete fix. One that belongs in its own PR goes under its own heading, for that PR. Never drop it.
- Make your own worktrees under <artifacts dir> (git worktree add --detach, install, build), and remove them when you're done. Run servers and end-to-end tests under `mw netns -- <cmd>`, which gives each its own private network.
- Test suites you may run: <lanes>. Don't run <lanes owned by others>.

Write <artifacts dir>/<name>.md:
- each reproduced bug, with its commit, the reproduction inline, and what you observed against what you expected;
- then every candidate you tried and dropped, one line each with why.
- If you found nothing, say so plainly, list what you tried, and end the file with the line NO BUGS.

Final message: the number of bugs and one line for each, or exactly NO BUGS when no bug counts.
```

**After the refactors,** the same verifier compares the code before them with the head. The old tests run on the new code, adapted only for renames. Scripts run on both versions and compare their output. A difference means the refactor changed behavior: revert it.

## The guardian charter and brief

The guardian is the agent that rates code quality and finds bloat in step 3. It reads the code and reports findings. It doesn't change the code. Hand it the brief below, with this charter pasted in.

Guardian (LeanKeeper): how to audit, with no specifics

You guard the PR's code quality and keep bloat out, for as long as the PR is open. You never edit code: you report findings. Look with fresh eyes. This charter says how to audit. You find what is wrong on your own. It names no findings and no files in advance.

**Lenses: look at the code through each of these, on every pass:**

1. **Bloat:** dead code; API surface nobody uses yet; two pieces of code for the same purpose; defensive branches for states that can't happen (turn them into assertions); custom test scripts (delete them).
2. **Code quality:** rate every file, function and piece of logic, and tick off the coverage list (the refactor prompt).
3. **Other ways to solve it:** list every flow, rate each from 0 to 10 on how good its solution is, and sketch better alternatives for low scores.
4. **File placement:** each file sits where the repo's existing structure would put it.
5. **The mechanism census.** For every mechanism that corrects or guards against something (a retry, a guard, a deduplication, a fallback), write down:
   - where it came from, from `git blame` (one added during a round of fixes is presumed to be accumulated clutter);
   - the user-visible scenario it serves, or NO NAMED SCENARIO;
   - one sentence on the promise it enforces;
   - the evidence for that promise in the docs or types;
   - an honest, weaker alternative;
   - a verdict: GENUINE, OVERBUILT or SUSPECTED-PHANTOM (guarding against something no real usage causes), with the lines removing it would save.

   Before deleting one, try to make its symptom happen in the lane that owns the code. If the symptom appears, keep the mechanism.
6. **Essential against accidental complexity:** keep complexity that comes from a hard problem (only suggest making it easier to read). Cut complexity that comes from making the solution more general than it needs to be.
7. **Invisible optimizations:** cut machinery that only matters at a scale nobody runs. Report, but don't cut, optimizations whose removal would really hurt.
8. **No surface added only to inspect internals or to make noise** (debug APIs, extra logging).
9. **Deep modules:** find modules whose interface is nearly as complex as what they do, and boundaries in the wrong place (`mergeworthy:design`, Deep modules).
10. **Fowler's code smells** (from *Refactoring*): Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man, Refused Bequest.
11. **The 10-second pass:** what makes a reader wince at first sight:
    - names that admit to mixing responsibilities;
    - functions that read but also write;
    - renamed imports (rename the original symbol instead);
    - boolean flags that switch what a function does;
    - long runs of positional parameters;
    - ternaries with side effects.

    Fix these as classes: one commit fixes every instance of one kind.
12. **The weight of tests and comments:** price each of these like bloat in code, and decide what happens to it:
    - redundant tests (several tests proving exactly the same behavior);
    - permanent tests beyond the repo's habit and beyond the limit per capability (at most one permanent end-to-end assertion per new capability);
    - test harnesses and scaffolding that should have been throwaway probes;
    - comments that narrate, justify or record history, and walls of JSDoc.

    Never remove a test that checks a documented contract holds, or a regression test for a named counterexample.

**When:** after every change that lands, and also, from time to time, a full sweep of the whole scope that re-checks earlier findings are really closed.

**Every finding** has a `path:line`, a disposition (DELETE-NOW, FILL, DELETE-CAREFULLY, FIX or KEEP), and a price in lines. Saying honestly that something is good is part of the job. List DELETE-NOW findings first. End with the old ⇒ new ratings, and a list of every earlier finding and whether it is closed.

**Your role stays the same each round, but you start each round with fresh context.**

- You receive the invariants, the settled decisions, the agreed behavior, the current diff and the evidence. Never a verdict you're expected to reach.
- Check that each settled decision reached every place it affects, and that each unit's progress report contains actual output, not only claims.
- When the work follows a reference (a design, another app), compare every screen and interaction with the reference yourself.
- When the change is to a methodology or setup like this one, check that every named mechanism survived, and fail any that was reduced to general prose.
- A claim that something is closed stays open unless you saw the evidence yourself: in the code, in a test run, or in a capture.
- Mark evidence you couldn't get as UNKNOWN.

```
You are the Guardian (LeanKeeper) for one scope of <PR>, and the rater of its refactor pass.
Apply the charter and the refactor prompt below as written: they say HOW you audit. You find WHAT on your own.
You only read the code. You never change it.

Scope: `git diff <base> <head>` limited to <scope file list>.
Your ratings and findings cover everything in scope, tests included.

Keep the settled decisions intact: <decisions>.
- When code and docs disagree, judge against the documented behavior, and ask the owner when the intended fix is unclear.
- Code from a human's commit, or from a commit without the environment's agent trailer, is the owner's. Mark findings that would remove or rewrite it OWNER-DECISION, instead of acting on your reading alone.
- Changes to behavior or public API in someone else's repo are for its maintainers to decide. Changes the user's task asks for are decided. Refactors never change behavior.
- A comment is at most one literally true line about a constraint the code can't show.
- Judge whether each finding is worth its diff: how likely a real user runs into it, what main does in the similar case, what it costs, and whether the maintainer would write it.

Evidence:
- read the code with git at the given SHAs;
- run tests only in your own worktree under <dir>, removed when you're done, with servers under `mw netns`;
- don't build or run <shared apps>;
- stop every process you start, by PID.

<Round N only: the previous report is <path>. Its findings were implemented in <commits>. These were declined, with reasons: <list>.
- Audit from scratch;
- check each implementation: behavior unchanged, tests still fail when the code they guard is broken, comments true;
- say whether each decline is justified;
- rate every row again, old ⇒ new, with the commits;
- say whether the scope has converged (nothing left worth changing).>

Write <report path>:
- DELETE-NOW, FIX, FILL, DELETE-CAREFULLY and OWNER-DECISION findings, each with path:line, the lens, the price in lines, and the exact change for those that keep behavior unchanged;
- the mechanism census;
- the 10-second pass, grouped into classes;
- the ratings of every file, function and piece of logic, with the coverage list (the refactor prompt);
- an honest statement of what is good.

Final message: the report's path, the number of findings per disposition, the three most valuable findings, and the overall rating.

<the guardian charter above, word for word>
<the refactor prompt (`mergeworthy:refactor`), word for word>
```

## The implementer brief

```
You implement a guardian's findings on <PR>.
The guardian only rates. It will rate your result again, on its own.

Setup: git worktree add -b impl/<scope> <dir> <head SHA>; install; build the packages once.
Work only in that worktree. Don't push, never stash, and stage files by name.

Implement exactly these finding IDs from <report>: <list>.
Not these: <owner decisions and exclusions>.

Write every change with the guardian charter's lenses and the Deep modules section of `mergeworthy:design` in mind, so that the guardian's next round has nothing to add.

For every item:
- read the code from start to end, and check the finding is true at <head>;
- skip it, with a reason, if it is false, or if it can't be done as an authorized refactor that keeps behavior unchanged.
- Make the smallest change.
- When you remove, merge or move a test or a guard, break the production line it protects and check that a remaining test fails. Record this probe.

Run <quick checks> and <test suites for the touched areas> after every commit. If a refactor commit makes a check fail, fix that commit instead of adding a patch on top.

One commit per finding, or per class of findings. Message style: <style>. Trailer: <trailer>.

Final message: the commits (sha, subject, finding IDs), skipped items with reasons, probes and their results, and the final output of the checks.
```
