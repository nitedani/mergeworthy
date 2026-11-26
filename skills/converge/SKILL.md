---
name: converge
description: "Converging a PR's head before it is ready, in every tier: the design agreed, Loop A, Loop B, Loop A again, the fresh reader, gates and the evidence blocks; batching, running the agents, stacked PRs."
---

# Converge

Working a PR's head to a final state: every review loop ends clean, or its last round's ledger closes what is left (`delegate §Review rounds`), and every claim in the PR is backed by evidence you observed. Called by `pull-request` step 9; when done, return there. Each step ends with its `pr-steps` record, which pre-bash-guard requires before the PR leaves draft or a ready PR gets a push (`merging` step 1). Subagents work read-only or in their own worktrees; only you write the PR branch's history.

## Steps

0. **The shape is agreed and the area is clean.** A new API, protocol or behavior is built only once the maintainer OK'd its shape (`design` step 9); in the user's own repos, once the walkthrough is posted. Code being reshaped, or a change that can't be made cleanly because of past patches: `finality`. Size the batch first (§Batching).
   Open: §Batching; `finality` · Hook: pre-bash-guard
1. **Loop A: does it break anything?** Two seats per slice (`delegate §Reviewers`). You decide each reproduced bug's root-cause fix; an implementer lands it. Under each `## Dropped` or `## Untested claims` line, you write `RULED: <candidate>: <ruling>` (a claim's: the text before ` — `): a bug to fix, or your evidence it isn't. A bug outside the functions this change edits: its `task §Dispositions`, never re-opening this one. Done when every seat's last file is recorded, ending `NO BUGS` or with its `--ledger`.
   Open: `delegate/verifier.md`; `delegate/implementer.md` · Run: `pr-steps verify <its file>` · Hook: pre-bash-guard
2. **Loop B: is it good code?** After Loop A, its two seats, each one prompt writing one file per brief: first the reviewer brief, then the shape pass. You decide which findings land (`code §Earn every line`); an implementer lands them commit by commit, gates after each; each seat's next round follows `delegate §Review rounds`. A bug its review finds gets its `task §Dispositions`; once one is fixed, Loop A re-checks that slice (`<slice>-recheck`). Done when each seat's last shape report is recorded, ending `CLEAN` or with its `--ledger`.
   Open: `delegate/reviewer.md`, `delegate/shape.md`, `delegate/implementer.md` · Run: `pr-steps shape <its shape report>` · Hook: pre-bash-guard
3. **Loop A again, on Loop B's commits.** Per slice Loop B's commits touch, one Loop A seat's fix check (`<slice>-reverify`): the one whose findings were fixed, else (both or neither) the first company's; with none, you record a file saying `NO LOOP B COMMITS`.
   Open: `delegate/verifier.md` §After refactors · Run: `pr-steps reverify <its file> [--ledger <its ledger>]` · Hook: pre-bash-guard
4. **The fresh reader, with the maintainer's eyes.** Merge `origin/<base>` into the branch, resolve, rerun the gates; write `drafts/<pr>/pr-body.md` by `pull-request §Body` (finished in `pull-request` step 10) and pass `post-lint --kind pr`. Then its two seats at once (`delegate §Reviewers`). A behavior finding goes back to its slice's Loop A, a code one to Loop B (`<slice-or-step>-fresh`), and you apply its "New to the study" and "Stale in the project file" lines to the project file and the study in the same step (`rules` step 6's TASTE, with its sweep of our open PRs). Done when each seat's report names the maintainer and says `MERGE AS IS: yes`, or at its `--ledger` record once those loops closed each finding and `post` step 3 each body finding on `pr-body.md`.
   Open: `delegate/fresh-reader.md` · Run: `git fetch origin && git merge origin/<base>`; `pr-steps fresh <work folder>/drafts/fresh-<seat>.report.md` per seat; the first seat's body verdict, `<work folder>/drafts/<pr>/pr-body.review.out` (its task: `output to <the report> and <it>`), and the second's `pr-body-<seat>.review.out` are the body loop's round 1 · Hook: pre-bash-guard
5. **Gates and body.** A smallest-class agent runs every gate CI runs, and the heavy lanes, on the final head. CI green, or only workflow approval pending (`merging §CI limits`). The body's evidence blocks (§Evidence blocks), then gate-pass on the final body; where it fails, the body loop's next round, `post` step 3's fast form. Where `finality` ran, its closure (`finality` step 7) comes last. Optional owner recommendations don't block; approval the entry conditions require does.
   Open: `code §Gates`; §Evidence blocks; `post` step 3 · Run: `pr-steps gates <the log>` · Hook: pre-bash-guard

### Small fix

A change of at most 60 lines outside tests, docs (any `.md`), lockfiles and build output, with a test the base fails and the head passes (a repo keeping none: a reproduction; docs or whole-line comments alone: a commit's `Cold-read: <rules step 4's report>` trailer), replaces steps 1–4 with one two-seat review (`delegate §Reviewers`): `delegate/small-review.md` on the pushed head, recorded by `pr-steps small <each report>`; then step 5. Each blocker or should: your ruling and `delegate §Review rounds`; each `## Outside this change` line: its `task §Dispositions`.

### Batching

- **Batch:** let the work land (every commit a review round or a maintainer's ask produces), each pushed when `merging` step 1 allows, then converge the whole PR once before `ready`.
- **Carry the pass:** a change to the PR's own diff of 80 lines or fewer, only in test paths, `.md` files and build output, gets the quick gates and lanes it touches; its loop records say `carries the pass of <sha>`, with no new loops or reader. After a maintainer asks for one, the shape pass runs and records instead, on the unchanged head too. Anything else gets the loops on the PR diff from its merge-base, then one fresh read.
- **The shape pass goes stale** past 80 changed lines since its last full pass (tests, lockfiles and build output excluded; the watcher's `### SHAPE STALE`): a fresh agent runs it on the whole diff before the next "Done" reply.

### Running the agents

- **Loop A and Loop B get separate agents,** except a Tier S PR under ~300 lines, where each seat runs both.
- **A long list of Loop B findings** goes to one implementer in its own worktree, slice by slice. Review its diff and cherry-pick it onto the PR branch.
- **Slices:** a diff over about 1500 lines is split (`delegate/verifier.md` §Slices); each slice, a file several use in each, gets its own seats; Loop B's cover the whole PR (step 2).
- **What they read:** the head's code in full at the brief's pinned SHAs; a later round, its slot's scope. A finality graph is only an index.
- **A seat past about 100k context tokens** (its harness's count) goes to a new agent of its company, same loop and rounds, given the last report and ledger. A changed decision in `decisions/*.md` goes to the running agent.
- **A maintainer's commits are owner code** (`code §Owner code and authority`).

### Stacked PRs

When a feature PR also fixes the base code it builds on:
- **Bugs the feature doesn't need fixed** get their `task §Dispositions`: a PR of their own only where it allows one.
- **Bugs the feature needs fixed** go into a stack, only when the bottom PR builds alone on `main` and `gh stack` can link the two; otherwise they stay in the feature PR, one commit per bug.
- **Finality's reshaping commits of base code** go in the bottom PR, before its fixes, when the fixes need the new shape; otherwise they're one refactoring PR of their own that the bottom PR depends on.
- **Bottom PR (base `main`):** the fixes, one bug per commit, each proven by a repro that fails on `main` (kept as a test only per `code §Tests`). Where the feature fixed a bug in several steps, the bottom PR carries only what they amount to. A fix belongs here if it's a bug on `main` by itself; it stays in the top PR if its failure needs the feature's code.
- **Top PR (base: the bottom PR's branch):** the feature, containing the bottom through merge commits, never a rebase. Link them: `gh stack link <bottom> <top>`.
- **After every merge of the bottom into the top:** feature code keeps the top's version, specs get the union of their tests; check every test name of the bottom's specs still exists in the top (merges silently drop tests); check the top's "Files changed" shows only feature lines. When the stack moves a fix, move its mention in the bodies too.

### Evidence blocks

Just enough to prove each step ran: one collapsed block per step above, plus an Approach block (the candidates and ratings, linking a gist of `approach.md`), its runs newest first, each naming its head. In a PR body, each `<summary>` starts with a title whose block post-lint neither counts nor lints: Approach, Loop A, Loop B, Refactor pass, Fresh read or Gates (in a repo with a `Language:` line, that language's, in `hooks/post_words.py`). Each says plainly what ran and what came of it, names a finding that changed the PR or says nothing was worth changing, and links the full output in a readable gist: how many passes ran and what each found, then the commits, what stays below the bar and why, then one line per item, grouped by area. Claim only what ran on that head.
