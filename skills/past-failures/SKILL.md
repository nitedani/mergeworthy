---
name: past-failures
description: "When a rule failed or the user names a failure: the table of past failures and the rule that covers each."
---

# Failures that already happened

Each failure below happened, most more than once. When a rule fails or the user names a failure, find its row. A new failure goes in an existing row when one covers its rule; otherwise a new row of at most one line. Either way the rule is fixed (1.1.12).

| What happened | Rule |
|---|---|
| Replies posted unreviewed; correction comments stacked on top; one draft posted twice. | 1.6, `pre-bash-guard` |
| Maintainer comments unanswered for hours (watcher gaps, an expired watch, 👀 then silence); asked why, the agent explained and waited for a go. | 1.5 watcher, 1.1.13, always-on (named failure), `gh-watch-start`, `pre-bash-guard`, `stop-lint` |
| "Good!" read as closing an old point, and left unanswered. | 1.5 acknowledgements, `proposals-open.md` |
| Stale tracker lines and Decisions comment, hours and many merges behind. | 1.2 |
| Red CI noticed by the user. | the watcher's `### CI` events |
| An LGTM'd item still "waiting"; a superseded statement cited. | 1.1.9 |
| Maintainer instructions ignored ("remove the test right before merging"). | 1.7 checkboxes, 1.7 Ready list |
| Briefs pasted from stale copies; a review passed on the author's evidence without a run. | `delegating`, `converge` |
| A subagent started six agents of its own, then ended its turn while they ran; its report never came. | `delegating` (what the agent must not do) |
| Behavior verdicts taken by reasoning, without a run; a bot's opposite "fix" went in within seconds, and a probe showed the reviewer was right. | `review` (behavior is settled by a run), `converge` |
| "Ready" without review, refactor or guardian verdict; fixes pushed to ready PRs unreviewed, a CI result recorded as their review. | always-on 1–3, `pr-steps`, `pre-bash-guard` |
| "Stacked on #N" without `gh stack`. | `writing` links, `post-lint` |
| "Should I…? / your call" on our own recommendation. | 1.1.3, `stop-lint` |
| A modal question answered by accident. | 1.1.3 |
| User questions absorbed into work and never answered. | 1.1.4 |
| Claims from memory, false "can't"s, a reversed close-the-PR advice. | 1.1.5 |
| Workarounds shipped as fixes; defects documented as caveats. | 1.1.6, `converge` (phantom and removal gates) |
| Upstream PR for a problem our own hook choice caused. | 1.1.6 |
| A design that sent the payload three times "for now". | 1.1.2 |
| Hooks named against their behavior; options nobody asked for. | 1.1.10 |
| A proposal that pulled in unrelated behavior, with unexplained shorthand. | 1.4 walkthrough |
| A design comparison sent as a table; the user needed code. | `writing`, 1.4 |
| Side-PR review rounds while the critical-path feature stayed a prototype. | 1.1.1 |
| "Separate PR" meaning "later"; a 5-minute item deferred twice; a promised PR never opened. | 1.1.7, 1.5 `PROMISED`, `gate-pass` |
| Parts of the task and of an accepted design silently dropped. | 1.1.8 |
| Throughput losses called trade-offs; a `read(n)` that grew the buffer until 20 GB stalled passed 200 MB probes. | 1.1.11 |
| A regression for users of an existing feature called "limitation: experimental". | 1.1.11 |
| UI bugs found by the user; UI "verified" by computed styles and scripted events. | `evidence` (reproduce it as a person would) |
| A transport fix opened with Node-script evidence only. | `evidence` (reproduce it as a person would) |
| A release unlike the maintainer's past releases. | 1.3 precedent |
| Docs in the agent's voice; repeated "I don't understand"; a coined term. | 1.3, 1.5 |
| Jargon, AI phrasing, out-of-context replies; replies that only complied or restated. | `writing`, `post-lint` |
| Class-wide bugs got narrow fixes: a query-parser default; a router that didn't decode paths, fixed by an opt-in option rated for Vike from an anchored brief. | 1.5 step 3, `pull-request` step 3 |
| A reply claim no longer true after a revert. | 1.6 step 4 |
| Soft suggestions answered "Done"; the wrong paragraph removed. | 1.5 step 2, `post-lint` |
| Choices handed back that we could settle. | 1.6, `post-lint` |
| A design credited to the maintainer who couldn't recall it. | `writing` credit |
| Review reports and raw rater output posted on PRs. | `writing` process invisible, `post-lint` |
| Over-engineering the maintainer cut (long collision checks, a tiny cache, rare-case docs, lookup tests); the maintainer cut most submitted test lines. | 1.1.15, 1.1.16 |
| A 100-line feature with no user. | 1.1.16 feature list |
| Five new core hooks where an existing extension point sufficed; a diff viewer the named project already had, rewritten; a "reference" project imported. | 1.4 step 0, 1.3, 1.1.8 |
| Instruction files bloated with rationale and opt-outs. | 1.9 |
| A lesson from one repo repeated in another. | 1.1.12 |
| Work stopped at every rate limit; hundreds of headless browsers; a preview left running for hours. | 1.1.13, 1.8 |
| Shared pnpm store modified, logs overwritten, backups lost in `/tmp`, a colleague's commits force-pushed over. | 1.8, 1.2, `core` (artifact root), 1.7 |
| A model above the default's tier used for subagents; global config edited instead of the skill. | `core` (models), 1.1.3 |
| A subagent's design merged without understanding it. | 1.10 |
| Squash merges carrying full PR history. | 1.7, `pre-bash-guard` |
| `ps \| awk '/<port>/'` matched and killed another session's server. | 1.8 |
| Posting with inline bodies; `gh run rerun` on upstream (needs admin: ask a maintainer); fork PRs lack CI secrets, so those jobs fail. | 1.6 step 4, 1.7 CI |
| The watcher started a headless agent per event instead of waking the session that owned the thread; the user saw 👀 and no answer. | 1.5 (the session is the agent, woken by its Monitor), `stop-lint` |
| The agent watched and answered every thread in the scope repos, not only threads it opened or posted in and the user's `/ai` calls. | 1.5 (which comments you answer), the watcher (`watcher/gh-watch.py`), `post-bash-register` |
| Held work while the budget was red with nothing watching it, then only re-armed the watcher. | 1.1.13 (a hold has a Monitor on what lifts it) |
| A type check a sibling PR's validators already covered; the owner called it bloat. | 1.1.16 |
| Two decision issues were filed with text and code references only; the owner couldn't see where in the app the problem was. | `open-issue`, with `evidence` shared by `pull-request`; `post-lint --kind issue` fails without `### How to reproduce` and its evidence. |
| A security fix also changed a legitimate user's flow, which needed the business's decision first. | 1.1.9 and the project file: a fix closes only the hole; a behavior change gets its own issue with options. |
| Branches were pushed and worked on for hours with no PR; GitHub showed them as "no pull request yet", and merged PRs' branches were left behind. | `pull-request` (draft PR with the first push), 1.7 (`--delete-branch` at merge). |
| A symptom behind several clicks got stills; the owner wanted a video. | `evidence`, `post-lint --kind issue` |
| A tool result saying the user doesn't want the action, with no user message after it, was a harness cancellation; the session went idle. | 1.1.13 (a cancellation with no user message after it is re-run) |
| A benchmark regression sent as a GENUINE-FORK, then kept by default. | 1.1.3 (no default on a regression), 1.1.11 |
| Stuck on a fix whose every option regressed, the agent asked the user to pick instead of running the finality pass; the user had to name it. | finality (when to run it), 1.1.3 |
| Phase B branches were about to get the code map and angles phrased in the current design's terms, anchoring them on what exists; the user named it. | finality (Phase B: the clean problem) |
| A decision issue recommended the smallest change over the option users want. | `mergeworthy:writing`, How a good colleague writes (recommendations) |
| Agents taken for dead when their turn ended, retried and killed; the orchestrator blocked on wait loops. | 1.10, `pre-agent-dedupe`, `agent-job`, `pre-bash-guard` |
| Design-thread replies chased the latest comment, flipped without evidence, argued from execution cost and left invariants open (the user's too). | `writing` (Design threads), `github-threads` 1.5 step 3, `finality`, `design-loop` (end state first) |
| Replies read like reports: label lines ("Two decisions:"), options described in words instead of code, a bug backlog sent as "holes". | `writing` (draft by talking; the reply that carries the load) |
