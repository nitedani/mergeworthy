---
name: converge
description: "Converging a PR (the owner asks, or Tier >= M before ready): what converged means, the order of the passes, authority, the phantom and removal gates, stacked PRs, gates and evidence, PR bodies."
---

# Converge

Tier S runs it condensed (1.0); Tier ≥ M runs it in full, for every PR. A new API or protocol gets it only once the maintainer has OK'd its shape (1.4 step 5).

You are the orchestrator of a pull request (or a stack of them) that has to reach a converged, final state: no reviewer, agent or verifier finds anything worth changing, and every claim in the PR is backed by evidence you observed. You are the single writer of the PR branches' git history. Subagents work read-only or in their own worktrees; you review and land what they produce.

Converged means every one of these has converged:
1. Bug verification: every slice of every PR has a dry, reproduce-only pass after its last fix (`verify`).
2. Guardian (bloat and quality): a fresh guardian per scope finds nothing behavior-preserving worth its price, and says so in an honest-positive verdict (`guardian`).
3. Refactor pass: every file, function and piece of logic is rated, the ratings are high and justified, and the rater's last round leaves nothing worth doing (`refactor`).
4. Finality and Owner-Safe closure, where the area has drifted through many patches (`finality`).
5. Code review against the repo's standards and the spec, with `review`'s PR review round on the final head.
6. Every gate and product lane green on each PR's final head, CI green, and the PR bodies true to the final head.

Owner decisions, and changes to code the owner wrote, don't block convergence: they are listed for the owner with a recommendation.

### Git and files

- Stage files by name; never `git add -A` on a tree you share. Never a bare `git stash`: the stack is shared across worktrees and sessions; stash with a unique message and apply by SHA.
- Rewrite only local, unpushed commits, and only to fix that same commit (a red gate on it, a comment that isn't true). Pushing follows 1.7. Never propose mutative git operations to the user.
- Write prompt and text files with a quoted heredoc (`<<'EOF'`); an unquoted one runs backticked commands inside the text.
- Every commit ends with the attribution trailer the environment gives you; PR bodies end with the generated-by line and stay under 65,536 characters.

### Authority: what's settled, what's the owner's

Keep the decision packet (1.2) and give it to every subagent. Nobody re-asks or re-opens a settled decision; the newest owner decision wins. When the owner changes direction, update the packet, then every surface it touches (1.2).

The owner's code is deliberate, in the user's repos too:
- A commit without an agent's co-author trailer is owner code.
- Owner code is never removed or rewritten on an agent's reading alone, including trimming it, "simplifying" it, or deleting a mechanism in it as phantom or overbuilt. Such findings go on the owner's list with a recommendation.
- An agent's own earlier code can be changed freely. If an agent removed an owner line, restore it.
- In the user's own repos, changing the user's code as the task needs is yours to decide (`core`, the task); removing or rewriting it on an agent's reading alone (a finding, a cleanup on your own initiative) goes to the user's list with a recommendation.

In an external maintainer's repo, anything that changes behavior or a public surface is the owner's call: error messages users see, wire formats, option semantics, exported names. In the user's own repos and in beta or pre-1.0 features, decide, act, and report afterwards (`core`, the task). Refactors are behavior-preserving only.

Docs are the contract. When code and docs disagree, the code is the suspect; never change docs to match code. If the fix is straightforward and the docs' promise is clearly intended, fix the code; otherwise ask the owner (doc line, observed behavior, question) on the open PR, or in an issue where 1.1.7 allows one.

Ask the owner only questions that are genuinely theirs and genuinely uncertain, and only for consequential forks. Decide the rest, and say in the PR body what you decided and why.

### The phantom gate (every fix must pass it)

A fix is phantom, and must not ship, if any of these holds:
- P1: No real, documented usage reaches it. Name the documented scenario, and trace it on both ends: client and server, caller and callee, sender and receiver. A bug that one layer "has" is not a bug if another layer already owns that behavior.
- P2: It changes a deliberate behavior, such as a usage error the code raises on purpose, a documented limit, or an owner's design.
- P3: Its comments aren't literally true.
- P4: It is a mechanism for a case that can't occur, such as a defensive branch for an unreachable state. Use an assertion instead, or nothing.

Also:
- No silent fallbacks: a usage error stays a usage error.
- Fix the actual root cause with the minimum diff. Don't bundle new protocol concepts, handshakes or probes unless asked.
- The fix is the call-site fix, not a changed default that other callers depend on.

### The removal gate (every deletion of a mechanism must pass it)

"No test fails without it" is not proof that a mechanism is phantom. Before removing a guard, a dedup, a retry or a memo:
- Name the symptom it prevents, and probe that symptom through documented usage against the real threshold: listener counts and MaxListeners warnings, timers, memory, ordering, duplicate delivery.
- Run the probe in the owning product lane (the real transport, backend and runtime), not only in unit tests.
- A product-shaped failure keeps the mechanism as GENUINE-CONFIRMED, with the failure text recorded.
- Treat a mechanism repaired twice as suspect, and re-probe whether it needs to exist at all.
- The final bug verification after the refactors (`verify`) is the backstop: it compares the pre-refactor tree with the head.

### Stacked PRs (when a feature PR also fixes the base code)

If the verification of a feature turns up bugs in the code it builds on, those the feature doesn't need fixed are their own PRs (1.1.16). Those it needs go into a stack, but only when the bottom PR builds alone on `main` and `gh stack` can link the two (`implement-issue` step 4); otherwise they stay in the feature PR, one commit per bug:
- **Bottom PR (base main):** those fixes, one bug per commit, each with a regression spec that fails on main and passes with the fix, in final form. Where the feature PR fixed a bug in several steps, the bottom PR carries only what they amount to.
- **Top PR (base = the bottom PR's branch):** the feature. It contains the bottom PR through merge commits, never a rebase, so it never needs a force-push.
- **Link them:** `gh stack link <bottom> <top>`.

After every merge of the bottom into the top:
- Resolve conflicts so that feature code keeps the top's version and specs get the union of their tests.
- Check that every test name of the bottom's specs still exists in the top, or was replaced on purpose. Merges silently drop tests.
- Check that the top's "Files changed" view shows only feature lines.

Placement: a fix belongs in the bottom PR if it's a bug on main by itself, and stays in the top PR if its failure needs the feature's code. Trace the named failure to decide.

### Gates, lanes, flakes, evidence

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

## Subagent briefs

Replace `<...>` with the specifics. Give each subagent only what it needs: the charter, the decision packet, the scope, the evidence rules. Never give it desired verdicts or earlier agents' conclusions, except a previous round's report when it is explicitly re-rating. Reviewers and verifiers read at pinned SHAs, never a moving branch.

### PR bodies

Each PR body is part of the deliverable, true of the final head, and within 1.1.16 and the 1.6 budget. Beyond `implement-issue` step 8's template it carries, as needed: how it works (for a feature, with a code sample); the fixes, one line per user-visible bug; the owner's decisions it carries ("decided by the owner", "left to my judgment, and kept") as a short list; the notes table (1.6), with every rater proposal left to the owner as "decision needed" with a recommendation; and evidence (CI, gates, lanes, verification) naming the head it ran on. The refactor pass's final lists go where `refactor` says; working ratings, guardian reports and per-scope lists stay in the artifact root.

Keep the body current by condensing history, never by dropping current facts. When the stack moves a fix from one PR to another, move its mention too. Register every PR with the host's linking tool if one exists, and report it if linking fails.
