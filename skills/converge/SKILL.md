---
name: converge
description: "Converging a PR (Tier S condensed, Tier >= M in full before ready, or the owner asks): what converged means, the order of the passes, authority, the phantom and removal gates, stacked PRs, gates and evidence, PR bodies."
---

# Converge

Converging a pull request means working it to a final state: no reviewer, agent or verifier finds anything worth changing, and every claim in the PR is backed by evidence you observed. The same holds for a stack of PRs.

- **When:** Tier ≥ M runs it in full, for every PR. Tier S runs it condensed. (`core` 1.0)
- **New API or protocol:** converge runs on it only once the maintainer has OK'd its shape (`design-loop`, 1.4 step 5).
- **Your role:** you are the orchestrator, and the only writer of the PR branches' git history. Subagents work read-only or in their own worktrees; you review what they produce and land it.

Converged means every one of these has converged:
1. **Bug verification (Loop A).** Loop A is the reproduce-only bug hunt in `verify`; open `verify` to run it. Every slice of every PR has a dry pass after its last fix: a reproduce-only pass that finds no bug that counts.
2. **Guardian (Loop B, bloat and quality).** Loop B is the guardian rounds in `guardian`; open `guardian` to run them. The reader's guardian verdict for each scope finds nothing behavior-preserving worth its price. It says so in an honest-positive verdict: a plain "nothing worth changing", given as a real result. The fresh reader's Bloat lens on the final head is clean too.
3. **Refactor pass.** Every file, function and piece of logic is rated, the ratings are high and justified, and the rater's last round leaves nothing worth doing. Open `refactor` for the prompt and how to run it.
4. **Finality and Owner-Safe closure,** where the area has drifted through many patches. Open `finality` when the work reshapes existing code, or when a small change can't be made cleanly because of past patches.
5. **Code review** against the repo's standards and the spec: the fresh reader on the final head (who reads, below).
6. **Gates and body.** Every gate and product lane is green on each PR's final head, CI is green, and the PR bodies are true to the final head.

Owner decisions don't block convergence, and neither do changes to code the owner wrote. They go on the owner's list with a recommendation.

### Who reads: two agents per PR

Every pass above runs in one of two readers. Each reader covers one slice set: the slices that fit one context. Under about 1500 diff lines, one of each reader is enough; in a stack, each PR gets its own pair. The briefs and charters run as written, each into its own output file.

- **The reader** is a Claude agent, because it judges. One run, in this order, since rating code that a bug fix will change is waste. Each brief lives in the skill named next to it; open that skill when you write the reader's prompt:
  1. the verifier brief (`verify`);
  2. the reviewer charter with all three lenses (`review`);
  3. the guardian charter and the refactor prompt (`guardian`, `refactor`).
- **What the reader reads.** It reads the head's code in full. A finality `map.md` is a navigation index only.
- **After fixes,** send the reader the new commits (`delegating`, one run). The reader re-verifies the touched slices until dry, then re-rates old ⇒ new after the refactor commits. A regression means revert that commit and verify that slice fresh.
- **A new reader** starts, with the last report, when the reader's context passes about half the window or the decision packet changes.
- **The fresh reader of the final head** is picked in `review`'s order, Codex first. One run: the verifier brief on the final head, the reviewer charter, and the PR body's claims and screenshots. That run is also the PR body's posting-gate review (1.6).
- **The fresh reader's findings** go back to the fixes. If the head then changed only by those fixes, the same fresh reader confirms them (`delegating`, one run); otherwise start a new fresh reader.
- **Execution is yours, not the readers'.** Repro loops, tests and benchmarks with a time budget run in the main session, on the model your environment names for it, else the `sonnet` alias (1.1.14). Judgment stays with the readers.

**Briefing a subagent.** Replace `<...>` in its brief with the specifics. Give each subagent only what it needs: the charter, the decision packet, the scope and the evidence rules.
- Never give it the verdict you want, or earlier agents' conclusions. The one exception is a previous round's report, when the subagent is explicitly re-rating.
- Reviewers and verifiers read at pinned SHAs, never a moving branch.

### Git and files

- **Staging:** stage files by name; never `git add -A` on a tree you share.
- **Stash:** never a bare `git stash`, because the stash stack is shared across worktrees and sessions. Stash with a unique message and apply by SHA.
- **Rewriting history:** rewrite only local, unpushed commits, and only to fix that same commit (a red gate on it, a comment that isn't true). Pushing follows 1.7 (`merging`). Never propose mutative git operations to the user.
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
- **The user's own repos:** changing the user's code as the task needs is yours to decide (`core`, the task). Removing or rewriting it on an agent's reading alone (a finding, a cleanup on your own initiative) goes on the user's list with a recommendation.

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

- **Quick gates, after every commit:** format, type-check and units. The type-check includes the specs' own type-check, under each TypeScript version the repo resolves.
- **Full gates, before every push:** the quick gates; spellcheck and docs lint; the released-API or public-surface check; the runtime-specific lanes.
- **Heavy lanes, before every push,** on each PR's head: build, then the heavy lanes the project file lists (e.g. production-mode e2e, every adapter or transport, the examples).
- **Dist:** rebuild the dist before any e2e run.

Failures:
- **Gates fail closed:** a gate that errors or can't run is red.
- **A failure that doesn't repeat is still a finding.** Find its cause, or file it with the logs, before calling anything green.
- **A regression** is a failure across variants, or one that reproduces.
- **Clock jumps:** on a host whose wall clock jumps, use generous test timeouts.
- **Exit codes:** "N passed" with a non-zero exit code is red.

Evidence:
- **Name the head.** Every claim names the head it ran on, and which gates ran on which head.
- **Base bugs:** a known base bug that a lane shows is recorded as the base's, with the evidence that the base fails it too.
- **UNKNOWN:** tag anything you couldn't observe as UNKNOWN.

### PR bodies

Each PR body is part of the deliverable. It is true of the final head, and within 1.1.16 and the 1.6 budget.

Beyond `implement-issue` step 8's template, a PR body carries, as needed:
- **How it works:** for a feature, with a code sample.
- **The fixes:** one line per user-visible bug.
- **The owner's decisions** it carries, as a short list ("decided by the owner", "left to my judgment, and kept").
- **The notes table (1.6):** every rater proposal left to the owner is a "decision needed" row with a recommendation.
- **Evidence** (CI, gates, lanes, verification), naming the head it ran on.

**What stays out.** The refactor pass's final lists go where `refactor` says. Working ratings, guardian reports and per-scope lists stay in the artifact root.

**Keeping it current.** Condense history; never drop current facts. When the stack moves a fix from one PR to another, move the fix's mention too. Register every PR with the host's linking tool if one exists, and report it if linking fails.
