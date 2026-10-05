---
name: convergence
description: "Running convergence on a PR (the owner asks, or Tier >= M before ready): bug verification loop, guardian and refactor rounds, final verification, the charters and templates."
---

# Convergence

Tier S runs it condensed (1.0); Tier ≥ M runs it in full, for every PR. A new API or protocol gets it only once the maintainer has OK'd its shape (1.4 step 5).

You are the orchestrator of a pull request (or a stack of them) that has to reach a converged, final state: no reviewer, agent or verifier finds anything worth changing, and every claim in the PR is backed by evidence you observed. You are the single writer of the PR branches' git history. Subagents work read-only or in their own worktrees; you review and land what they produce.

Converged means every one of these has converged:
1. Bug verification: every slice of every PR has a dry, reproduce-only pass after its last fix (section 6).
2. Guardian (bloat and quality): a fresh guardian per scope finds nothing behavior-preserving worth its price, and says so in an honest-positive verdict (section 7).
3. Refactor pass: every file, function and piece of logic is rated, the ratings are high and justified, and the rater's last round leaves nothing worth doing (section 7).
4. Finality and Owner-Safe closure, where the area has drifted through many patches (section 9).
5. Code review against the repo's standards and the spec, with `implement-issue`'s reviewer charter, run per `reviewer`.
6. Every gate and product lane green on each PR's final head, CI green, and the PR bodies true to the final head.

Owner decisions, and changes to code the owner wrote, don't block convergence: they are listed for the owner with a recommendation.

### 1. Git and files

- Stage files by name; never `git add -A` on a tree you share. Never a bare `git stash`: the stack is shared across worktrees and sessions; stash with a unique message and apply by SHA.
- Rewrite only local, unpushed commits, and only to fix that same commit (a red gate on it, a comment that isn't true). Pushing follows 1.7. Never propose mutative git operations to the user.
- Write prompt and text files with a quoted heredoc (`<<'EOF'`); an unquoted one runs backticked commands inside the text.
- Every commit ends with the attribution trailer the environment gives you; PR bodies end with the generated-by line and stay under 65,536 characters.

### 2. Authority: what's settled, what's the owner's

Keep the decision packet (1.2) and give it to every subagent. Nobody re-asks or re-opens a settled decision; the newest owner decision wins. When the owner changes direction, update the packet, then every surface it touches (1.2).

The owner's code is deliberate, in the user's repos too:
- A commit without an agent's co-author trailer is owner code.
- Owner code is never removed or rewritten on an agent's reading alone, including trimming it, "simplifying" it, or deleting a mechanism in it as phantom or overbuilt. Such findings go on the owner's list with a recommendation.
- An agent's own earlier code can be changed freely. If an agent removed an owner line, restore it.
- In the user's own repos, changing the user's code as the task needs is yours to decide (`core`, the task); removing or rewriting it on an agent's reading alone (a finding, a cleanup on your own initiative) goes to the user's list with a recommendation.

In an external maintainer's repo, anything that changes behavior or a public surface is the owner's call: error messages users see, wire formats, option semantics, exported names. In the user's own repos and in beta or pre-1.0 features, decide, act, and report afterwards (`core`, the task). Refactors are behavior-preserving only.

Docs are the contract. When code and docs disagree, the code is the suspect; never change docs to match code. If the fix is straightforward and the docs' promise is clearly intended, fix the code; otherwise ask the owner (doc line, observed behavior, question) on the open PR, or in an issue where 1.1.7 allows one.

Ask the owner only questions that are genuinely theirs and genuinely uncertain, and only for consequential forks. Decide the rest, and say in the PR body what you decided and why.

### 3. The phantom gate (every fix must pass it)

A fix is phantom, and must not ship, if any of these holds:
- P1: No real, documented usage reaches it. Name the documented scenario, and trace it on both ends: client and server, caller and callee, sender and receiver. A bug that one layer "has" is not a bug if another layer already owns that behavior.
- P2: It changes a deliberate behavior, such as a usage error the code raises on purpose, a documented limit, or an owner's design.
- P3: Its comments aren't literally true.
- P4: It is a mechanism for a case that can't occur, such as a defensive branch for an unreachable state. Use an assertion instead, or nothing.

Also:
- No silent fallbacks: a usage error stays a usage error.
- Fix the actual root cause with the minimum diff. Don't bundle new protocol concepts, handshakes or probes unless asked.
- The fix is the call-site fix, not a changed default that other callers depend on.

### 4. The removal gate (every deletion of a mechanism must pass it)

"No test fails without it" is not proof that a mechanism is phantom. Before removing a guard, a dedup, a retry or a memo:
- Name the symptom it prevents, and probe that symptom through documented usage against the real threshold: listener counts and MaxListeners warnings, timers, memory, ordering, duplicate delivery.
- Run the probe in the owning product lane (the real transport, backend and runtime), not only in unit tests.
- A product-shaped failure keeps the mechanism as GENUINE-CONFIRMED, with the failure text recorded.
- Treat a mechanism repaired twice as suspect, and re-probe whether it needs to exist at all.
- The post-refactor bug verification (section 8) is the backstop: it compares the pre-refactor tree with the head.

### 5. Stacked PRs (when a feature PR also fixes the base code)

If the verification of a feature turns up bugs in the code it builds on, those the feature doesn't need fixed are their own PRs (1.1.16). Those it needs go into a stack, but only when the bottom PR builds alone on `main` and `gh stack` can link the two (`implement-issue` step 4); otherwise they stay in the feature PR, one commit per bug:
- **Bottom PR (base main):** those fixes, one bug per commit, each with a regression spec that fails on main and passes with the fix, in final form. Where the feature PR fixed a bug in several steps, the bottom PR carries only what they amount to.
- **Top PR (base = the bottom PR's branch):** the feature. It contains the bottom PR through merge commits, never a rebase, so it never needs a force-push.
- **Link them:** `gh stack link <bottom> <top>`.

After every merge of the bottom into the top:
- Resolve conflicts so that feature code keeps the top's version and specs get the union of their tests.
- Check that every test name of the bottom's specs still exists in the top, or was replaced on purpose. Merges silently drop tests.
- Check that the top's "Files changed" view shows only feature lines.

Placement: a fix belongs in the bottom PR if it's a bug on main by itself, and stays in the top PR if its failure needs the feature's code. Trace the named failure to decide.

### 6. Loop A: bug verification (reproduce-only)

Split the code into slices one verifier can hold (e.g. core feature, backend and storage, runtime adapter, wire and client), per PR. For each slice, run a fresh-context verifier with the template in section 12.1.

Counting rule:
- A candidate counts only with a spec or script that fails on the head and passes on the base (main, or the bottom PR for the top).
- It must trace to documented usage on both ends.
- A deliberate behavior doesn't count.
- A finding that fails 1.1.15 gets the disposition "accepted, not worth code" with its one-line reason; it never becomes code to make a pass dry. Loop A converges on real bugs, not on every imaginable edge case.
- The verifier lists every candidate it dropped, one line each with the reason.

When a pass finds bugs:
1. Fix each at its root cause, with a spec that fails first (show it failing on the parent), minimum diff, and the phantom gate passed. Re-run the verifier's own repro on the fixed build, and compare its output with the base's.
2. If the area has already had two corrective edits, stop patching. Rethink it as one rule that covers every case found so far, then implement that rule.
3. Put fixes to base code in the bottom PR (when there is a stack, section 5), then merge up.
4. Queue another pass on that slice, and record it in the ledger.

Dry criteria:
- One dry pass is a strong signal, and two in a row are enough.
- Don't rerun a slice that is dry and whose code hasn't changed since.
- Every slice needs a dry pass after its last fix. A fix, a refactor or a revert in a slice's code re-opens it.
- Never drop a queued pass: the ledger lists every pass owed, and the PR isn't converged while one is outstanding.

Bugs outside the task's scope get a disposition (1.1.7).

### 7. Loop B: guardian and refactor rounds

Run late, after correctness is proven, with the gates as the safety net. Findings are judged per 1.1.15, as in Loop A.

Split the diff into scopes (e.g. core feature, backend, everything else; the bottom PR is its own scope).

Round 1:
- One fresh guardian per scope, read-only, with the brief in section 12.2.
- Each writes a report: findings by disposition with prices, the mechanism census, the 10-second pass as classes, ratings of every file, function and piece of logic with the ✅ tick list, and an honest-positive statement.

Implementation:
- One implementer per scope, in its own worktree off the current head, with the brief in section 12.3.
- Each gets an explicit list of finding IDs to implement. Owner decisions, and anything touching owner code without explicit leave, are excluded.
- One commit per finding (or per class), with the gates after every commit, and a mutation probe for every test merged, moved or deleted.
- Implementers may decline a finding with a reason: when it's false, not behavior-preserving, or touches owner code.

Landing:
- Review each implementer's diff yourself before cherry-picking (1.10).
- Cherry-pick onto the PR branch, resolve conflicts, and run the full gates.
- Run the product lanes the changes touch.
- After the last landing, run `implement-issue`'s reviewer charter (per `reviewer`) on the final head and record it with `pr-steps review <output>`; record the last guardian report with `pr-steps refactor <report>`.

Round N+1:
- A fresh guardian per scope gets the previous report, the implemented commits, and the declined items with reasons.
- It audits fresh (not only the old list), verifies each implementation (behavior preserved, mutations still lethal, comments true), and says whether each decline holds.
- It re-rates every row old ⇒ new with commits, and states plainly whether the scope converged.
- Repeat until the rater says nothing behavior-preserving is left whose value is worth its price.
- The rater's own "converges once these land" items, landed exactly as prescribed, close the scope.

### 8. Final bug verification after the refactors

Once every scope converged, run one reproduce-only verifier per slice that compares the pre-refactor tree with the head:
- The old specs run on the new code, adapting only renames. Every failure must be an intended change.
- Side-by-side scripts run the same scenarios on both trees and diff the output.
- Include randomized or fuzz comparisons where the logic is combinatorial.

A regression found here means the refactor wasn't behavior-preserving: revert it, then run a fresh pass on that slice.

### 9. Finality pass

Run `implement-issue`'s finality pass where the work reshapes existing code, or where a small change can't be made cleanly because the area has taken too many patches. It ends with Owner-Safe closure, which is part of convergence: every settled decision propagated to its surfaces, every finding closed or held with a reason, and code, tests, docs, types and PR state agreeing, with observed evidence attached.

### 10. Gates, lanes, flakes, evidence

Quick gates after every commit: format, type-check (including the specs' own type-check, under each TypeScript version the repo resolves), units.

Full gates before every push:
- the quick gates;
- spellcheck and docs lint;
- the released-API or public-surface check;
- the runtime-specific lanes.

Heavy lanes before every push, on each PR's head: build, then the heavy lanes the project file lists (e.g. production-mode e2e, every adapter or transport, the examples).

Rebuild the dist before any e2e run.

Failures:
- Gates fail closed: a gate that errors or can't run is red.
- A failure that doesn't repeat is still a finding: find its cause, or file it with the logs, before calling anything green.
- A failure across variants, or one that reproduces, is a regression.
- On a host whose wall clock jumps, use generous test timeouts.
- "N passed" with a non-zero exit code is red.

Evidence:
- Every claim names the head it ran on, and which gates ran on which head.
- A known base bug that a lane shows is recorded as the base's, with the evidence that the base fails it too.
- Tag anything you couldn't observe as UNKNOWN.

### 11. The two prompts the guardians apply

#### 11.1 Guardian (LeanKeeper) charter

Guardian (LeanKeeper) — METHODOLOGY ONLY (no specifics)
You are a PERMANENT code-quality & bloat guardian for the life of the PR. READ-ONLY on code,
always — findings, not edits. Work with FRESH EYES: this charter is HOW you audit; you discover
WHAT independently. It carries no pre-baked findings or file names.
Lenses, applied every pass: (1) BLOAT — dead code, speculative surface, duplicate intent,
defensive branches for unreachable states (→ assertions), custom test scripts (→ delete).
(2) CODE QUALITY — rate ALL files/functions/logic 0–10 with reasons, 100% coverage, plus a
separate ✅ tick list to catch anything unrated; mostly-10s = you were lazy. (3) PROBLEM
VARIABILITY — list all flows, rate each 0–10 on solution optimality, sketch better alternatives
for low scores. (4) FILE PLACEMENT per the repo's established structure. (5) MECHANISM CENSUS —
every corrective mechanism: origin by blame (fix-round = presumptively accretion), named
user-visible scenario or NO NAMED SCENARIO, implied-promise sentence, docs/types evidence,
honest weaker alternative, verdict GENUINE / OVERBUILT / SUSPECTED-PHANTOM with the lines it would save.
Repaired-twice mechanisms get existence re-probes. Removals only via probes that can fail, run
in the OWNING product lane; a product-shaped red keeps the mechanism as GENUINE-CONFIRMED with
the failure text recorded — the confirmed-kept column equals the deleted column in status.
(6) ESSENTIAL vs ACCIDENTAL complexity — keep hard-problem complexity (readability notes only),
cut solution-generality bloat. (7) INVISIBLE OPTIMIZATIONS — cut scale-only machinery; SURFACE
(don't cut) optimizations with a real viability cost. (8) NO introspection/noise surface.
(9) DEEP-MODULE DESIGN (1.4.1 terms) — flag SHALLOW modules; the deletion test; "the interface is the test
surface"; seam placement; a seam with one adapter is hypothetical. (10) FOWLER SMELLS — Mysterious Name, Duplicated Code, Feature Envy, Data Clumps,
Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative
Generality, Message Chains, Middle Man, Refused Bequest. (11) THE 10-SECOND PASS — the
instant-wince lens: names confessing mixed responsibility, queries that write, import aliases
(rename the source symbol), boolean-flag commands, positional param runs, side-effecting
ternaries; fix as CLASSES, one commit per class. (12) TEST & COMMENT MASS — test redundancy
(multiple tests proving the IDENTICAL behavior), fix-batteries where one regression test would
do, harnesses/scaffolds that should have been transient probes, narration/justification/audit-
trail comments and JSDoc walls — all priced and dispositioned like code bloat; soundness oracles
and named-counterexample regressions for documented contracts are sacred.
Cadence: INCREMENTAL (every landing) AND periodic FULL-BREADTH re-sweep re-verifying closure.
Every finding: path:line, disposition (DELETE-NOW / FILL / DELETE-CAREFULLY / FIX / KEEP), and a
PRICE in lines. Honest-positive verdicts are required capability. Lead with DELETE-NOW; end with
old⇒new ratings + a prior-findings closure ledger.
Your function is permanent; your task context is fresh. Receive the invariant charter, current
decision packet, accepted contract, current diff and evidence—not desired verdicts, pre-baked file
targets, prior agents' persuasive narration, or commit-specific conclusions. Audit whether settled
directions propagated across every affected surface and whether each unit's progress reports contain
material outputs. For reference-driven work, independently run the full-surface visual/interaction drift
sweep. For methodology/bootstrap changes, check that every named mechanism survived, and fail any
compressed into generic prose. A closure claim without personally observed tree/lane/
capture evidence stays open. Record honest `UNKNOWN` where the evidence is unavailable.

#### 11.2 Refactor pass (pinnacle split + simplify)

Refactor this PR:

- Pinnacle architectural split
  - Does each file and each function represent a sensible abstraction that is easy to understand?
  - Rate the SEAMS, not just the boxes: for each call site, ask whether the responsibility sits
    on the right side of the boundary — should a caller's wrapper move down into the callee (or
    vice versa)? A function can be clean, DRY and well-tested in isolation yet still be in the
    wrong place. "Well-factored" is not "well-located".
  - Before starting to work: list ALL files and ALL functions in this chat, rate them all
    (0: convoluted abstraction, hard to understand, not DRY — 10: perfect), and give a reason for
    your rating.
    - DON'T skip any file nor any function — write an extra separated ✅ tick list of all files
      and functions to double-check nothing was forgotten. Two lists: ratings & explanations,
      then the ✅ coverage list.

- Simplify
  - Review ALL logic. Can implemented logic be simplified?
  - Do you see logic implemented twice? Is logic DRY?
  - Can boilerplate be removed? Frivolous indirections? Frivolous tiny functions? Can we merge
    functions to make reading code easier (jumping between functions is costly when reading code
    linearly, which is what humans do)?
  - Put yourself in the shoes of a human reader who reads everything in a linear fashion.
  - Altitude pass: for each entry-point / orchestration function, read it top-to-bottom as prose.
    Flag any line that drops the reader into lower-level mechanism (a flag, a thunk, a log verb,
    error plumbing) in the middle of what should be a high-level narrative. For each, ask: can
    that mechanism move down into the callee so the caller reads at one consistent altitude?
    Prioritize the reading path of the functions a reader hits first.
  - Before starting to work: list ALL logic in this chat, rate each (0: bad — 10: perfect) with
    reasons — 100% coverage, plus the separated ✅ tick list.

- How to scrutinize (don't rubber-stamp what's already there)
  - Code comments that justify a design ("X lives here rather than Y so that…") are claims to
    audit, not constraints to respect. For each, construct the alternative it argues against and
    compare — don't assume the documented choice is optimal.
  - For anything you rate 8 or above, do one more pass asking only: is it at the right altitude
    and on the right side of its boundary?

- Work until it's exceptionally good. We as an expert team will check against every little detail.
  - If we see mostly 10/10 ratings, that's a sign you've been lazy — scrutinize everything and
    spend a substantial amount of time. We don't want to prompt you again and again to achieve
    quality — autonomously strive for quality on your own without us pushing you.

- End with a summary of what you worked on: print the lists again with old rating ⇒ new
  rating with link to commit(s).

Running it: the rater is not the author, and not in the author's context. It rates read-only; the author implements commit by commit; a fresh rater re-rates old ⇒ new. Scope: everything the diff touches, at 100% coverage; code outside the diff is context. Re-run the gates after every commit; a red gate means revert that commit, not patch over it. Refactor commits are separate from behavior commits. If the pass changed nothing, say that and why. The final lists (old ⇒ new, reason, commit links, and the ✅ lists) go in the review-record comment; working notes stay in the artifact root. The pass belongs to the PR as it is now, not to the head it first ran on: when later commits (maintainer requests included) change more than ~80 lines, re-run it on the whole PR diff before the next "Done" reply and replace the lists; the watcher prints `### REFACTOR STALE` when that happens.

### 12. Templates

Replace `<...>` with the specifics. Give each subagent only what it needs: the charter, the decision packet, the scope, the evidence rules. Never give it desired verdicts or earlier agents' conclusions, except a previous round's report when it is explicitly re-rating. Reviewers and verifiers read at pinned SHAs, never a moving branch.

#### 12.1 Bug verifier

```
You are a bug verifier for <PR and slice>. Count only what you reproduce. Don't start subagents, don't commit, push or comment anywhere.

Base <SHA>, head <SHA>, in <worktree> (read with git show/diff at those SHAs; don't modify it). Your slice: <paths>. <What changed since the last pass, with the previous reports' paths, if any.>

What counts: through documented usage (the docs are the contract; the settled decisions are in <decision packet or PR body>), the head behaves wrongly where a user can see it: a regression against the base, or a fix that's incomplete for the scenario its commit names. A deliberate behavior (a usage error) doesn't count, nor a scenario no documented usage reaches on both ends. A candidate counts only with a spec or script that fails on the head and passes on the base.

How: read each change end to end with every caller; try the edges: <list the risky edges for this slice>. Make your own worktrees under <artifacts dir> (worktree add --detach, install, build) and remove them when done. Lanes you may run: <lanes>. Don't run <lanes owned by others>.

Write <artifacts dir>/<name>.md: each reproduced bug with its commit, the repro inline, observed vs expected; then every candidate you tried and dropped, one line each with why. If you found nothing, say so plainly and list what you tried. Final message: the count and one line each.
```

#### 12.2 Guardian brief

```
You are the Guardian (LeanKeeper) for one scope of <PR>, and the rater of its refactor pass. Apply the charter and the refactor prompt below as written: they are HOW you audit; you discover WHAT on your own. You are read-only on code.

Scope: `git diff <base> <head>` restricted to <scope file list>. Ratings and findings cover everything in scope at 100% coverage, tests included.

Decision and Constraint Packet (settled; don't reopen): <decisions>. Docs are the contract. Owner-authored code (no agent co-author trailer) isn't removed on your reading: flag it as OWNER-DECISION. Behavior or public-surface changes are OWNER-DECISION. Comments terse and literally true. Low diff wins.

Evidence: read with git at the pinned SHAs; run specs only in your own worktree under <dir>, removed when done; don't build or run <shared apps>; stop every process you start.

<Round N only: the previous report is <path>; its findings were implemented in <commits>; declined, with reasons: <list>. Audit fresh; verify each implementation (behavior preserved, mutations still lethal, comments true); say whether each decline holds; re-rate every row old ⇒ new with commits; state whether the scope converged.>

Write <report path>: DELETE-NOW, FIX, FILL, DELETE-CAREFULLY, OWNER-DECISION (each: path:line, lens, price, exact change for behavior-preserving ones); the mechanism census; the 10-second pass as classes; ratings of every file, function and piece of logic, then the ✅ tick list; an honest-positive statement. Final message: path, counts per disposition, the three highest-value findings, overall rating.

<charter 11.1 verbatim>
<refactor prompt 11.2 verbatim>
```

#### 12.3 Implementer brief

```
You implement a guardian's findings on <PR>. The guardian was a separate, read-only rater; a fresh one re-rates your result.

Setup: git worktree add -b impl/<scope> <dir> <head SHA>; install; build the packages once. Work only there; don't push, never stash, stage files by name.

Implement exactly these finding IDs from <report>: <list>. Not these: <owner decisions and exclusions>.

Write every change with the charter's lenses (11.1) and 1.4.1's terms, so the next guardian round has nothing to add. For every item: read the code end to end and check the finding is true at <head>; skip it with a reason if it's false, changes behavior or a public surface, or removes owner code without leave. Make the smallest change. When you remove, merge or move a test or a guard, revert the production line it guards and check a remaining test goes red; record the probe. Gates after every commit: <quick gates>, plus <lanes for touched areas>; a red gate means fix that commit, not a patch on top. One commit per finding or class, message: <style>, trailer: <trailer>.

Final message: commits (sha, subject, IDs), skipped items with reasons, probes and results, final gate output.
```

### 13. PR bodies

Each PR body is part of the deliverable, true of the final head, and within 1.1.16 and the 1.6 budget. Beyond `implement-issue` step 8's template it carries, as needed: how it works (for a feature, with a code sample); the fixes, one line per user-visible bug; the owner's decisions it carries ("decided by the owner", "left to my judgment, and kept") as a short list; the notes table (1.6), with every rater proposal left to the owner as "decision needed" with a recommendation; and evidence (CI, gates, lanes, verification) naming the head it ran on. The refactor pass's final lists go where section 11 says; working ratings, guardian reports and per-scope lists stay in the artifact root.

Keep the body current by condensing history, never by dropping current facts. When the stack moves a fix from one PR to another, move its mention too. Register every PR with the host's linking tool if one exists, and report it if linking fails.
