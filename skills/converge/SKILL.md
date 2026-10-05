---
name: converge
description: "Converging a PR before it is ready, in every tier: the pipeline (finality, Loop A, Loop B, the fresh reader, gates) and the agents that run it, authority, the phantom and removal gates, stacked PRs, gates and evidence, PR bodies."
---

# Converge

Converging a pull request means working it to a final state: no reviewer, agent or verifier finds anything worth changing, and every claim in the PR is backed by evidence you observed. The same holds for a stack of PRs.

- **When:** every PR, in every tier. The tier changes the records (`core` 1.2), not the loops: on a small fix each loop usually ends after its first dry pass.
- **New API or protocol:** the pipeline runs on it only once the maintainer has OK'd its shape (`design-loop`, 1.4 step 5). In the user's own repos, post the walkthrough and continue on your recommendation; a reply from the user re-opens the shape (1.1.3).
- **Your role:** you are the orchestrator, and the only writer of the PR branches' git history. Subagents work read-only or in their own worktrees; you review what they produce and land it.

### The pipeline

In the order it runs. Converged means every step's done condition holds on the final head.

1. **Finality,** where the area has drifted through many patches: open `finality` when the work reshapes existing code, or when a small change can't be made cleanly because of past patches. Its Phases A and B are the analysis while planning (`implement-issue` step 3), and its Phase C is the build itself.
2. **Loop A, bug verification.** One agent runs the verifier brief (`verify`) on the diff. Fix what it reproduces, then continue the same agent with the commits. Done when every slice has a dry pass after its last fix: a pass that finds no bug that counts.
3. **Loop B, review and quality.** Once Loop A is dry, one agent runs, in one prompt and each into its own output file, the reviewer charter (`review`), then the guardian brief, which carries the refactor prompt (`guardian`, `refactor`). Reviewing first fills the context it rates with. Land its findings commit by commit with the gates after each, then continue the same agent with the commits. A bug its review finds is fixed, and Loop A re-verifies that slice. Done when it finds nothing behavior-preserving worth its price, said as an honest-positive verdict ("nothing worth changing"), and its ratings are high and justified. Keep its last re-rating's output file; step 6 records it.
4. **Loop A again, on Loop B's commits.** They re-open the slices they touch, so continue the Loop A agent with them: it compares the pre-refactor tree with the head (`verify`, after the refactors). Done when those slices are dry again.
5. **The fresh reader,** one cold read of the final head, after you merge the base into the branch (1.7) so it reads what will merge: the verifier brief, the reviewer charter, and the posting gate's review (1.6 step 3) of the PR body draft, its claims and screenshots checked against the head. Where finality ran, it also runs the guardian brief, which gives Owner-Safe closure its fresh guardian evidence; in that report only DELETE-NOW, FIX, FILL or DELETE-CAREFULLY items worth their price are findings, and OWNER-DECISION rows go on the owner's list. Pick it in `review`'s order: another company's model first. The loop agents have lived inside the fixes and are judging their own suggestions, so an agent that hasn't seen them catches what that familiarity hides. Its findings go back to step 2 or 3; if the head then changed only by those fixes, continue the same fresh reader, otherwise start a new one. Its `CLEAN` is the PR body's posting-gate review (1.6), and step 6 records it.
6. **Gates, body and closure.** Every gate and product lane is green on each PR's final head, CI is green, and the PR bodies are true to the final head. Where finality ran, its Owner-Safe closure comes last, with the review and guardian evidence attached. Last, on the final head, run `pr-steps review <fresh reader's output>` and `pr-steps refactor <Loop B's last re-rating>`; a head that changes after that (a CI fix, a base merge) needs both again.

Owner decisions don't block convergence, and neither do changes to code the owner wrote. They go on the owner's list with a recommendation: the PR body's notes table for an external maintainer, the decisions in your report (1.11) for the user.

### Running the agents

- **One agent per loop, for the loop's whole life.** After every fix, continue that agent (`delegating`, one run) instead of starting a new one, so it re-checks only what changed. The loops get separate agents because their work fills different contexts: Loop A runs repros, Loop B reads and rates code. On a small diff (a Tier S fix, under about 300 lines) both fit one context, so one agent runs Loop A, then Loop B. The fresh reader is always separate, because not having seen the fixes is its point.
- **Who lands Loop B's findings:** you, commit by commit. For a long list, one implementer agent in its own worktree does it with `guardian`'s implementer brief, and you review its diff before landing (1.10).
- **Slices.** A diff too big for one agent's context (roughly over 1500 lines) is split into slices that each fit (`verify`; the guardian brief calls them scopes), with their own loop agents; in a stack, each PR has its own.
- **What they read.** The head's code in full, at pinned SHAs. A finality graph (Phase A) is only a navigation index.
- **A new loop agent** starts, given the last report, when its context passes about half the window. A changed decision packet is sent to the running agent, with what it re-opens.
- **Commits others push** (a maintainer's) re-open the slices they touch, like your own fixes: send them to the running loop agents. They are owner code (Authority, below).
- **Execution is yours.** Repro loops, tests and benchmarks with a time budget run in the main session or a `sonnet` subagent (1.1.14); judgment stays with the loop agents.

### Git and files

- **Staging:** stage files by name; never `git add -A` on a tree you share.
- **Stash:** never a bare `git stash`, because the stash stack is shared across worktrees and sessions. Stash with a unique message and apply by SHA.
- **Rewriting history:** rewrite only local, unpushed commits, and only to fix that same commit (a red gate on it, a comment that isn't true) or to replay them onto commits others pushed. Pushing follows 1.7 (`merging`). Never propose mutative git operations to the user.
- **Prompt and text files:** write them with a quoted heredoc (`<<'EOF'`). An unquoted heredoc runs the backticked commands inside the text.
- **Trailers:** every commit ends with the attribution trailer the environment gives you. PR bodies end with the generated-by line and stay under 65,536 characters.

### Authority: what's settled, what's the owner's

The decision packet (1.2) is the list of people's picks. Keep it current and give it to every subagent.
- Nobody re-asks or re-opens a settled decision; the newest owner decision wins.
- When the owner changes direction, update the packet, then every surface the change touches (1.2).

**The owner's code is deliberate,** in the user's repos too:
- **Owner code:** a commit without an agent's co-author trailer.
- **Never on an agent's reading alone:** owner code is never removed or rewritten on an agent's reading alone. That includes trimming it, "simplifying" it, or deleting a mechanism in it as phantom or overbuilt. Such findings go on the owner's list with a recommendation.
- **Agent code:** an agent's own earlier code can be changed freely. If an agent removed an owner line, restore that line.
- **The user's own repos:** changing the user's code as the task needs is yours to decide (`core`, the task). Removing or rewriting it on an agent's reading alone (a finding, a cleanup on your own initiative) goes on the user's list with a recommendation. A removal that passed the removal gate (a probe that could fail, run in the owning lane, stayed green) is not a reading alone: make it, and report it with the probe.

**Behavior and public surfaces.** In an external maintainer's repo, anything that changes behavior or a public surface is the owner's call: error messages users see, wire formats, option semantics, exported names. In the user's own repos and in beta or pre-1.0 features, decide, act, and report afterwards (`core`, the task). Refactors are behavior-preserving only.

**Docs are the contract.** When code and docs disagree, the code is the suspect; never change docs to match code.
- If the fix is straightforward and the docs' promise is clearly intended, fix the code.
- Otherwise ask the owner on the open PR, or in an issue where 1.1.7 allows one: the doc line, the observed behavior, the question.

**Ask the owner little.** Ask only questions that are genuinely the owner's, genuinely uncertain, and about consequential forks. Decide the rest, and say in the PR body what you decided and why.

### The phantom gate (every fix must pass it)

A phantom fix must not ship. A fix is phantom if any of these holds:
- **No real, documented usage reaches it.** Name the documented scenario, and trace it on both ends: client and server, caller and callee, sender and receiver. A bug that one layer "has" is not a bug if another layer already owns that behavior.
- **It changes a deliberate behavior,** such as a usage error the code raises on purpose, a documented limit, or an owner's design.
- **Its comments aren't literally true.**
- **It is a mechanism for a case that can't occur,** such as a defensive branch for an unreachable state. Use an assertion instead, or nothing.

Every fix also follows these:
- **No silent fallbacks:** a usage error stays a usage error.
- **Root cause, minimum diff.** Fix the actual root cause with the smallest diff. Don't bundle new protocol concepts, handshakes or probes unless asked.
- **Call site, not default.** The fix goes at the call site, not into a changed default that other callers depend on.

### The removal gate (every deletion of a mechanism must pass it)

"No test fails without it" doesn't prove a mechanism is phantom. Before removing a guard, a dedup, a retry or a memo:
- **Probe the symptom.** Name the symptom the mechanism prevents. Probe that symptom through documented usage against the real threshold: listener counts and MaxListeners warnings, timers, memory, ordering, duplicate delivery.
- **In the owning lane.** Run the probe in the product lane that owns the mechanism (the real transport, backend and runtime), not only in unit tests.
- **A product-shaped failure keeps it.** The mechanism stays, recorded as GENUINE-CONFIRMED (the guardian charter's mark for a mechanism a probe proved necessary) with the failure text.
- **Repaired twice is suspect.** Re-probe whether a mechanism repaired twice needs to exist at all.
- **The backstop:** the final bug verification after the refactors (`verify`) compares the pre-refactor tree with the head.

### Stacked PRs (when a feature PR also fixes the base code)

Verifying a feature can turn up bugs in the code the feature builds on.
- **Bugs the feature doesn't need fixed** become their own PRs (1.1.16).
- **Bugs the feature needs fixed** go into a stack, but only when the bottom PR builds alone on `main` and `gh stack` can link the two (`implement-issue` step 4).
- **Otherwise** they stay in the feature PR, one commit per bug.
- **Finality's refactor commits of base code** go in the bottom PR, before its fixes, when the fixes need the new shape; otherwise they're one refactor PR of their own (1.1.16) that the bottom PR depends on.

A stack has two PRs:
- **Bottom PR (base main):** those fixes, one bug per commit, each with a regression spec that fails on main and passes with the fix, in final form. Where the feature PR fixed a bug in several steps, the bottom PR carries only what those steps amount to.
- **Top PR (base = the bottom PR's branch):** the feature. The top PR contains the bottom PR through merge commits, never a rebase, so it never needs a force-push.
- **Link them:** `gh stack link <bottom> <top>`.

After every merge of the bottom into the top:
- **Conflicts:** feature code keeps the top's version; specs get the union of their tests.
- **Tests:** check that every test name of the bottom's specs still exists in the top, or was replaced on purpose. Merges silently drop tests.
- **Diff:** check that the top's "Files changed" view shows only feature lines.

**Placement.** A fix belongs in the bottom PR if it's a bug on main by itself. It stays in the top PR if its failure needs the feature's code. Trace the named failure to decide.

### Gates, lanes, flakes, evidence

- **Quick gates, after every commit:** format, type-check and units.
- **Full gates, before every push:** the quick gates; spellcheck and docs lint; the released-API or public-surface check; the runtime-specific lanes.
- **Heavy lanes, before every push,** on each PR's head: build, then the heavy lanes the project file lists (e.g. production-mode e2e, every adapter or transport, the examples).

Failures:
- **Gates fail closed:** a gate that errors or can't run is red.
- **A failure that doesn't repeat is still a finding.** Find its cause, or file it with the logs, before calling anything green.
- **A regression** is a failure across variants, or one that reproduces.
- **Exit codes:** "N passed" with a non-zero exit code is red.

Evidence:
- **Name the head.** Every claim names the head it ran on, and which gates ran on which head.
- **Base bugs:** a known base bug that a lane shows is recorded as the base's, with the evidence that the base fails it too.
- **UNKNOWN:** tag anything you couldn't observe as UNKNOWN.

### PR bodies

Each PR body is part of the deliverable. It is true of the final head, and within 1.1.16 and the 1.6 budget.

Beyond `implement-issue` step 7's template, a PR body carries, as needed:
- **How it works:** for a feature, with a code sample.
- **The fixes:** one line per user-visible bug.
- **The owner's decisions** it carries, as a short list ("decided by the owner", "left to my judgment, and kept").
- **The notes table (1.6):** every rater proposal left to the owner is a "decision needed" row with a recommendation.
- **Evidence** (CI, gates, lanes, verification), naming the head it ran on.

**What stays out.** The refactor pass's final lists go where `refactor` says. Working ratings, guardian reports and per-scope lists stay in the artifact root.

**Keeping it current.** Condense history; never drop current facts. When the stack moves a fix from one PR to another, move the fix's mention too. Register every PR with the host's linking tool if one exists, and report it if linking fails.
