---
name: past-failures
description: "When a rule failed or the user names a failure: the table of past failures and the rule that covers each."
---

# Failures that already happened

Each failure below happened, most more than once. When a rule fails or the user names a failure, find its row. A new failure gets a new row and a fixed rule (1.1.12).

| What happened | Rule |
|---|---|
| Replies posted unreviewed; correction comments stacked on top; one draft posted twice. | 1.6, `pre-bash-guard` |
| Maintainer comments unanswered for hours: watcher gaps, unregistered PRs, a watch expired during a usage limit, 👀 then silence, an issue opened by a "Tier 0" audit and never watched. Asked "why didn't you?", the agent explained and waited for a go. | 1.5 watcher, 1.1.13, always-on (named failure), `gh-watch-start`, `pre-bash-guard`, `stop-lint` |
| "Good!" read as closing an old point, and left unanswered. | 1.5 acknowledgements, `proposals-open.md` |
| Stale tracker lines and Decisions comment, hours and many merges behind. | 1.2 |
| Red CI noticed by the user. | the watcher's `### CI` events |
| An LGTM'd item still "waiting"; a superseded statement cited. | 1.1.9 |
| Maintainer instructions ignored ("remove the test right before merging"). | 1.7 checkboxes, 1.7 Ready list |
| Review, guardian and refactor briefs pasted from copies saved hours earlier, as separate agents, without the verifier; a review passed on the author's evidence without a run. | `delegating` (pasted from the installed skill), `converge` (the pipeline) |
| A subagent started six agents of its own, then ended its turn while they ran; its report never came. | `delegating` (what the agent must not do) |
| Behavior verdicts taken without a run: a reviewer called a case correct by reasoning; a bot then called the same case a bug, and its "fix" went in within seconds, against the reviewer's verdict; a probe later showed the reviewer was right. A Tier S review round ran without the verifier's bug hunt. | `review` (behavior is settled by a run), `converge` (the pipeline) |
| "Ready" on green CI alone, or without review, refactor or guardian verdict; a subagent ran a hand-written checklist. | 1.7 Ready list, `pr-steps` |
| "Stacked on #N" without `gh stack`. | 1.6 links, `post-lint` |
| "Should I…? / your call" on our own recommendation. | 1.1.3, `stop-lint` |
| A modal question answered by accident. | 1.1.3 |
| User questions absorbed into work and never answered. | 1.1.4 |
| Claims from memory, false "can't"s, a reversed close-the-PR advice. | 1.1.5 |
| Workarounds shipped as fixes; defects documented as caveats. | 1.1.6, `converge` (phantom and removal gates) |
| Upstream PR for a problem our own hook choice caused. | 1.1.6 |
| A design that sent the payload three times "for now". | 1.1.2 |
| Hooks named against their behavior; options nobody asked for. | 1.1.10 |
| A proposal that pulled in unrelated behavior, with unexplained shorthand. | 1.4 walkthrough |
| A design comparison sent as a table; the user needed code. | 1.6 comparisons, 1.4 |
| Side-PR review rounds while the critical-path feature stayed a prototype. | 1.1.1 |
| "Separate PR" meaning "later"; a 5-minute item deferred twice; a promised PR never opened. | 1.1.7, 1.5 `PROMISED`, `gate-pass` |
| Parts of the task and of an accepted design silently dropped. | 1.1.8 |
| Throughput losses and reconnects called trade-offs. | 1.1.11 benchmark |
| A regression for users of an existing feature called "limitation: experimental". | 1.1.11 |
| UI bugs found by the user; UI "verified" by computed styles and scripted events. | `implement-issue` (UI and runtime work) |
| A transport fix opened with Node-script evidence only. | `implement-issue` (UI and runtime work) |
| A release unlike the maintainer's past releases. | 1.3 precedent |
| Docs in the agent's voice; repeated "I don't understand"; a coined term. | 1.3, 1.5 |
| Jargon, AI phrasing, out-of-context replies; replies that only complied or restated. | 1.6 writing, `post-lint` |
| A reply showed a hole was class-wide (a query-parser default) but recommended only the PR's narrow fix; the user had to propose the global one, and 👎'd it. | 1.5 step 3 (question behind the literal one) |
| A reply claim no longer true after a revert. | 1.6 step 4 |
| Soft suggestions answered "Done"; the wrong paragraph removed. | 1.5 step 2, `post-lint` |
| Choices handed back that we could settle. | 1.6, `post-lint` |
| A design credited to the maintainer who couldn't recall it. | 1.6 credit |
| Review reports and raw rater output posted on PRs. | 1.6 process invisible, `post-lint` |
| Over-engineering the maintainer cut (long collision checks, a tiny cache, rare-case docs, lookup tests); the maintainer cut most submitted test lines. | 1.1.15, 1.1.16 |
| A 100-line feature with no user. | 1.1.16 feature list |
| Five new core hooks where an existing extension point sufficed. | 1.4 step 0 |
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
| Held new work while the budget was red, with nothing watching the budget; it turned green and the session spent hours only re-arming the GitHub watcher until the user asked why it stopped. | 1.1.13 (a budget hold has a Monitor on the signal that lifts it) |
