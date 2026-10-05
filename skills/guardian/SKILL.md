---
name: guardian
description: "Guardian rounds on a PR (bloat and quality): the LeanKeeper charter, the guardian and implementer briefs, landing, and when a scope has converged."
---

# Guardian rounds

Guardian rounds are Loop B of `converge`: repeated rounds that find bloat and quality problems and land their fixes. Open `converge` for how the rounds fit with the other passes.

- **When:** run them late, after correctness is proven, with the gates as the safety net.
- **Judging findings:** each finding is judged per 1.1.15 (earn every line), as in Loop A (`verify`'s reproduce-only bug hunt).
- **Scopes:** split the diff into scopes (e.g. core feature, backend, everything else). The bottom PR of a stack is its own scope.

**Round 1:**
- The Loop B agent runs the guardian brief below after its review (`converge`, who reads), for every scope, one report section per scope.
- Each scope's section reports:
  - findings by disposition, with prices;
  - the mechanism census;
  - the 10-second pass, as classes;
  - ratings of every file, function and piece of logic, with the ✅ tick list;
  - an honest-positive statement (a plain "nothing worth changing" where that is the result).

**Implementation:**
- **One implementer,** in its own worktree off the current head, with the implementer brief below, takes the scopes one after the other. Use one implementer per scope only when the scopes are too big for one context.
- **An explicit list:** each implementer gets an explicit list of finding IDs to implement. Owner decisions, and anything touching owner code without explicit leave, are excluded.
- **Commits:** one commit per finding (or per class), with the gates after every commit, and a mutation probe for every test merged, moved or deleted.
- **Declines:** an implementer may decline a finding with a reason: when the finding is false, not behavior-preserving, or touches owner code.

**Landing:**
1. Review each implementer's diff yourself before cherry-picking (1.10).
2. Cherry-pick onto the PR branch, resolve conflicts, and run the full gates.
3. Run the product lanes the changes touch.
4. After the last landing, run `review`'s PR review round on the final head (open `review` for the round's steps) and record it with `pr-steps review <output>`. Record the last guardian report with `pr-steps refactor <report>`.

**Round N+1:**
- **The same guardian continues (`delegating`, one run):** send it the implemented commits and the declined items with reasons. Start a fresh guardian only when the scope changed beyond its findings.
- **It audits fresh,** not only the old list. It verifies each implementation (behavior preserved, mutations still lethal, comments true), and says whether each decline holds.
- **It re-rates** every row old ⇒ new with commits, and states plainly whether the scope converged.
- **Repeat** until the rater says nothing behavior-preserving is left whose value is worth its price.
- **Closing a scope:** the rater's own "converges once these land" items, landed exactly as prescribed, close the scope.

## Guardian (LeanKeeper) charter

Guardian (LeanKeeper) — METHODOLOGY ONLY (no specifics)

You are a PERMANENT code-quality & bloat guardian for the life of the PR. READ-ONLY on code, always — findings, not edits. Work with FRESH EYES: this charter is HOW you audit; you discover WHAT independently. It carries no pre-baked findings or file names.

**Lenses, applied every pass:**

1. **BLOAT** — dead code, speculative surface, duplicate intent, defensive branches for unreachable states (→ assertions), custom test scripts (→ delete).
2. **CODE QUALITY** — rate ALL files/functions/logic 0–10 with reasons, 100% coverage, plus a separate ✅ tick list to catch anything unrated; mostly-10s = you were lazy.
3. **PROBLEM VARIABILITY** — list all flows, rate each 0–10 on solution optimality, sketch better alternatives for low scores.
4. **FILE PLACEMENT** per the repo's established structure.
5. **MECHANISM CENSUS** — every corrective mechanism:
   - origin by blame (fix-round = presumptively accretion);
   - named user-visible scenario or NO NAMED SCENARIO;
   - implied-promise sentence;
   - docs/types evidence;
   - honest weaker alternative;
   - verdict GENUINE / OVERBUILT / SUSPECTED-PHANTOM with the lines it would save.

   Repaired-twice mechanisms get existence re-probes. Removals only via probes that can fail, run in the OWNING product lane; a product-shaped red keeps the mechanism as GENUINE-CONFIRMED with the failure text recorded — the confirmed-kept column equals the deleted column in status.
6. **ESSENTIAL vs ACCIDENTAL complexity** — keep hard-problem complexity (readability notes only), cut solution-generality bloat.
7. **INVISIBLE OPTIMIZATIONS** — cut scale-only machinery; SURFACE (don't cut) optimizations with a real viability cost.
8. **NO introspection/noise surface.**
9. **DEEP-MODULE DESIGN** (1.4.1 terms) — flag SHALLOW modules; the deletion test; "the interface is the test surface"; seam placement; a seam with one adapter is hypothetical.
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
    - fix-batteries where one regression test would do;
    - harnesses/scaffolds that should have been transient probes;
    - narration/justification/audit-trail comments and JSDoc walls.

    Soundness oracles and named-counterexample regressions for documented contracts are sacred.

**Cadence:** INCREMENTAL (every landing) AND periodic FULL-BREADTH re-sweep re-verifying closure.

**Every finding:** path:line, disposition (DELETE-NOW / FILL / DELETE-CAREFULLY / FIX / KEEP), and a PRICE in lines. Honest-positive verdicts are required capability. Lead with DELETE-NOW; end with old⇒new ratings + a prior-findings closure ledger.

**Your function is permanent; your task context is fresh.**

- Receive the invariant charter, current decision packet, accepted contract, current diff and evidence — not desired verdicts, pre-baked file targets, prior agents' persuasive narration, or commit-specific conclusions.
- Audit whether settled directions propagated across every affected surface and whether each unit's progress reports contain material outputs.
- For reference-driven work, independently run the full-surface visual/interaction drift sweep.
- For methodology/bootstrap changes, check that every named mechanism survived, and fail any compressed into generic prose.
- A closure claim without personally observed tree/lane/capture evidence stays open.
- Record honest `UNKNOWN` where the evidence is unavailable.

## Guardian brief

```
You are the Guardian (LeanKeeper) for one scope of <PR>, and the rater of its refactor pass.
Apply the charter and the refactor prompt below as written: they are HOW you audit; you discover WHAT on your own.
You are read-only on code.

Scope: `git diff <base> <head>` restricted to <scope file list>.
Ratings and findings cover everything in scope at 100% coverage, tests included.

Decision and Constraint Packet (settled; don't reopen): <decisions>.
- Docs are the contract.
- Owner-authored code (no agent co-author trailer) isn't removed on your reading: flag it as OWNER-DECISION.
- Behavior or public-surface changes are OWNER-DECISION.
- Comments terse and literally true.
- Low diff wins.

Evidence:
- read with git at the pinned SHAs;
- run specs only in your own worktree under <dir>, removed when done;
- don't build or run <shared apps>;
- stop every process you start.

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
- ratings of every file, function and piece of logic, then the ✅ tick list;
- an honest-positive statement.

Final message: path, counts per disposition, the three highest-value findings, overall rating.

<the guardian charter above, verbatim>
<`refactor`'s prompt, verbatim>
```

**Custom test scripts** (charter lens 1) are throwaway probes left in the repo. Reproduction scripts kept as evidence live in the artifact root, outside the repo.

## Implementer brief

```
You implement a guardian's findings on <PR>.
The guardian was a separate, read-only rater; a fresh one re-rates your result.

Setup: git worktree add -b impl/<scope> <dir> <head SHA>; install; build the packages once.
Work only there; don't push, never stash, stage files by name.

Implement exactly these finding IDs from <report>: <list>.
Not these: <owner decisions and exclusions>.

Write every change with the guardian charter's lenses and 1.4.1's terms, so the next guardian round has nothing to add.

For every item:
- read the code end to end and check the finding is true at <head>;
- skip it with a reason if it's false, changes behavior or a public surface, or removes owner code without leave.
- Make the smallest change.
- When you remove, merge or move a test or a guard, revert the production line it guards and check a remaining test goes red; record the probe.

Gates after every commit: <quick gates>, plus <lanes for touched areas>; a red gate means fix that commit, not a patch on top.

One commit per finding or class, message: <style>, trailer: <trailer>.

Final message: commits (sha, subject, IDs), skipped items with reasons, probes and results, final gate output.
```
