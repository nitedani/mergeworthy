# Part 4: Failures that already happened

Each happened, most more than once. Read them before starting.

| What happened | Rule |
|---|---|
| Replies posted unreviewed; correction comments stacked on top; one draft posted twice. | 1.6, `pre-bash-guard` |
<!-- if watcher=on -->
| Maintainer comments unanswered for hours: watcher gaps, unregistered PRs, a watch expired during a usage limit, 👀 then silence, an issue opened by a "Tier 0" audit and never watched. Asked "why didn't you?", the agent explained and waited for a go. | 1.5 watcher, 1.1.13, always-on (named failure), `gh-watch-start`, `pre-bash-guard`, `stop-lint` |
| A headless agent the watcher launched picked up the owner's comment and drafted a reply while the live session didn't know. | 1.5 watcher (it launches no agent; the live session handles every event) |
<!-- end -->
| "Good!" read as closing an old point, left 45 minutes. | 1.5 acknowledgements, `proposals-open.md` |
| Stale tracker lines and Decisions comment, hours and many merges behind. | 1.2, `tracker-check` |
<!-- if watcher=on -->
| Red CI noticed by the user. | `gh-watch` CI events |
<!-- end -->
| An LGTM'd item still "waiting"; a superseded statement cited. | 1.1.9 |
| Maintainer instructions ignored<!-- if tests=remove-before-merge --> ("remove the test right before merging", twice)<!-- end -->. | 1.7 checkboxes, `ready-check` |
| "Ready" on green CI alone, or without review, refactor or guardian verdict; a subagent ran a hand-written checklist. | 1.7, `ready-check`, `pr-steps` |
| "Stacked on #N" without `gh stack`. | 1.6 links, `post-lint` |
| "Should I…? / your call" on our own recommendation, about 25 times. | 1.1.3, `stop-lint` |
| A modal question answered by accident. | 1.1.3 |
| User questions absorbed into work and never answered. | 1.1.4 |
| Claims from memory, false "can't"s, a reversed close-the-PR advice. | 1.1.5 |
| Workarounds shipped as fixes; defects documented as caveats. | 1.1.6, Part 3 sections 3–4 |
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
| UI bugs found by the user; UI "verified" by computed styles and scripted events. | 1.1.11 UI |
| A transport fix opened with Node-script evidence only. | 1.1.11 runtime fixes |
| A release unlike the maintainer's past releases. | 1.3 precedent |
| Docs in the agent's voice; eight rounds of "I don't understand"; a coined term. | 1.3, 1.5 |
| Jargon, AI phrasing, out-of-context replies; replies that only complied or restated. | 1.6 writing, `post-lint` |
| A reply showed a hole was class-wide (a query-parser default) but recommended only the PR's narrow fix; the user had to propose the global one, and 👎'd it. | 1.5 step 3 (question behind the literal one) |
| A reply claim no longer true after a revert. | 1.6 step 4 |
| Soft suggestions answered "Done"; the wrong paragraph removed. | 1.5 step 2, `post-lint` |
| Choices handed back that we could settle. | 1.6, `post-lint` |
| A design credited to the maintainer who couldn't recall it. | 1.6 credit |
| Review reports and raw rater output posted on PRs. | 1.6 process invisible, `post-lint` |
| "They look good" as a review of the maintainer's commits. | 1.6 reviewing commits |
| Over-engineering the maintainer cut (long collision checks, a tiny cache, rare-case docs, lookup tests)<!-- if ownership=external -->; the maintainer cut most submitted test lines<!-- end -->. | 1.1.15, 1.1.16 |
| A 100-line feature with no user. | 1.1.16 feature list |
| Five new core hooks where an existing extension point sufficed. | 1.4 step 0 |
| Instruction files bloated with rationale and opt-outs. | 1.9 |
| A lesson from one repo repeated in another. | 1.1.12 |
| <!-- if target=local -->Work stopped at every rate limit; <!-- end -->170 headless browsers; a preview left running 4.5 hours. | 1.1.13, 1.8 |
| Shared pnpm store modified, logs overwritten, backups lost in `/tmp`, a colleague's commits force-pushed over. | 1.8, 1.2, TASK, 1.7 |
| A model above the default's tier used for subagents; global config edited instead of the skill. | TASK, 1.1.3 |
| A subagent's design merged without understanding it. | 1.10 |
| Squash merges carrying full PR history. | 1.7, `pre-bash-guard` |
| `ps \| awk '/<port>/'` matched and killed another session's server. | 1.8 |
| Posting with inline bodies; `gh run rerun` on upstream (needs admin: ask a maintainer); fork PRs lack CI secrets, so those jobs fail. | 1.6 step 4, 1.7 CI |

---
