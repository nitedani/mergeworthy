---
name: past-failures
description: "When a rule failed or the user names a failure: the table of past failures and the rule that covers each."
---

# Failures that already happened

Each happened, most more than once. When a rule fails or the user names a failure, find its row; a new failure gets a row and a fixed rule (1.1.12).

| What happened | Rule |
|---|---|
| Replies posted unreviewed; correction comments stacked on top; one draft posted twice. | 1.6, `pre-bash-guard` |
| Maintainer comments unanswered for hours: watcher gaps, unregistered PRs, a watch expired during a usage limit, 👀 then silence, an issue opened by a "Tier 0" audit and never watched. Asked "why didn't you?", the agent explained and waited for a go. | 1.5 watcher, 1.1.13, always-on (named failure), `gh-watch-start`, `pre-bash-guard`, `stop-lint` |
| "Good!" read as closing an old point, left 45 minutes. | 1.5 acknowledgements, `proposals-open.md` |
| Stale tracker lines and Decisions comment, hours and many merges behind. | 1.2 |
| Red CI noticed by the user. | `gh-watch` CI events |
| An LGTM'd item still "waiting"; a superseded statement cited. | 1.1.9 |
| Maintainer instructions ignored ("remove the test right before merging", twice). | 1.7 checkboxes, `ready-check` |
| "Ready" on green CI alone, or without review, refactor or guardian verdict; a subagent ran a hand-written checklist. | 1.7, `ready-check`, `pr-steps` |
| "Stacked on #N" without `gh stack`. | 1.6 links, `post-lint` |
| "Should I…? / your call" on our own recommendation, about 25 times. | 1.1.3, `stop-lint` |
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
| UI bugs found by the user; UI "verified" by computed styles and scripted events. | `implement-issue` (UI work) |
| A transport fix opened with Node-script evidence only. | `implement-issue` (UI work: runtime fixes) |
| A release unlike the maintainer's past releases. | 1.3 precedent |
| Docs in the agent's voice; eight rounds of "I don't understand"; a coined term. | 1.3, 1.5 |
| Jargon, AI phrasing, out-of-context replies; replies that only complied or restated. | 1.6 writing, `post-lint` |
| A reply showed a hole was class-wide (a query-parser default) but recommended only the PR's narrow fix; the user had to propose the global one, and 👎'd it. | 1.5 step 3 (question behind the literal one) |
| A reply claim no longer true after a revert. | 1.6 step 4 |
| Soft suggestions answered "Done"; the wrong paragraph removed. | 1.5 step 2, `post-lint` |
| Choices handed back that we could settle. | 1.6, `post-lint` |
| A design credited to the maintainer who couldn't recall it. | 1.6 credit |
| Review reports and raw rater output posted on PRs. | 1.6 process invisible, `post-lint` |
| "They look good" as a review of the maintainer's commits. | 1.5 step 2 (maintainer commits) |
| Over-engineering the maintainer cut (long collision checks, a tiny cache, rare-case docs, lookup tests); the maintainer cut most submitted test lines. | 1.1.15, 1.1.16 |
| A 100-line feature with no user. | 1.1.16 feature list |
| Five new core hooks where an existing extension point sufficed. | 1.4 step 0 |
| Instruction files bloated with rationale and opt-outs. | 1.9 |
| A lesson from one repo repeated in another. | 1.1.12 |
| Work stopped at every rate limit; 170 headless browsers; a preview left running 4.5 hours. | 1.1.13, 1.8 |
| Shared pnpm store modified, logs overwritten, backups lost in `/tmp`, a colleague's commits force-pushed over. | 1.8, 1.2, `core` (artifact root), 1.7 |
| A model above the default's tier used for subagents; global config edited instead of the skill. | `core` (models), 1.1.3 |
| A subagent's design merged without understanding it. | 1.10 |
| Squash merges carrying full PR history. | 1.7, `pre-bash-guard` |
| `ps \| awk '/<port>/'` matched and killed another session's server. | 1.8 |
| Posting with inline bodies; `gh run rerun` on upstream (needs admin: ask a maintainer); fork PRs lack CI secrets, so those jobs fail. | 1.6 step 4, 1.7 CI |
| The watcher started a separate headless agent per event; it ran without context or permissions, the user saw 👀 and no answer, and the session that owned the thread never heard of it. | 1.5 (the session is the agent, woken by its Monitor), `stop-lint` |
| The agent was told to register every open PR and issue in the scope repos and answer every maintainer comment, and every thread it commented on joined its watch list; the user wants answers only on threads the agent opened or posted in, and to their own `/ai` calls. | 1.5 (which comments you answer), `gh-watch`, `post-bash-register` |
| The user (also the repo's maintainer, posting from the agent's own account) asked questions and gave instructions on the agent's PRs without `/ai`; the watcher skipped them, so no 👀 and no answer for hours. The user's comment on a thread the agent opened or posted in is for the agent. | 1.5 (which comments you answer), `gh-watch` |
| A resumed session ran an 11-PR audit with two decision makers as single PRs: no tier was recorded, so it skipped the umbrella issue and its Decisions comment until the user pointed it out. | 1.0 (the Tier line, read on every resume), 1.2 Tier L |
| The umbrella issue kept the full audit report as its body with a PR table on top; the user wants the tracking shape of nitedani/vike-react-rsc#9 (checkbox line per PR with its state and what users hit, a Decisions comment with sources). | 1.2 Tier L |
| A second discovery round got its own section in the tracking body; the user wants new problems in the existing list, PRs linked there ("after 10 rounds the body is 10 km long"). | 1.2 Tier L |
| Design replies of 480 to 640 words came back as "I don't understand" or were read only superficially; one recommendation in about 50 words with "OK?" got "OK" within a minute (vikejs/vike#3550, #3407, #3500). | 1.6 budgets (a design answer ≤ 250 words, one decision per comment), `post-lint --kind proposal` |
| The maintainer found the simpler design four times on one PR (vikejs/vike#3550: "100x cleaner … Why aren't you recommending this approach?"), including a row of the agent's own options table; the PR took 153 commits. | 1.4 step 1 (smallest interface that keeps the invariants), 1.5 step 3 (build the simpler version before "keep") |
| Four recommendations were withdrawn after one maintainer question ("any downsides compared to what we do today?"), one after its LGTM. | 1.4 walkthrough item 4 (downsides against `main`) |
| A subagent ran a benchmark for 10 hours; half of it was runs that couldn't be used (two benchmarks at once skewed the CPU), found only when the user asked whether 10 hours was normal. | 1.10 (a time budget and an early check) |
| "Docker Desktop is the one thing blocking": the check was hours old and Docker was running. | 1.1.5 (re-check a blocker before reporting it) |
| A spec took eleven review rounds, each finding a new case of the same rule (when `renderPage()` runs `+middleware`); restating it as one rule ended the churn. | 1.4 step 3 |
| With the local model moved out of the plugin, nothing told sessions to use it: about 20 Claude reviewer subagents ran while `claude-usage` said `execute`. | the environment's own instructions (agent-tools' session-start hook and agent guard) |
