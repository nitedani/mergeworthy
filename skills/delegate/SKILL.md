---
name: delegate
description: "Starting, continuing or checking a subagent, writing a brief, and integrating its result: one agent per job, model class and effort, the brief from a template, its result. Holds the brief templates in delegate/."
---

# Delegate

Each role's brief is a template in `~/.mergeworthy/current/skills/delegate/`, with `agent.md` included in every one.

## Steps

1. **One job, one agent.** An agent on the job gets a message, not a twin (§Continue). At most 3 agents at once, implementers included, or the number the user allowed at once for this task, first written in its work folder's scope.md: `Agents: <N> (user <YYYY-MM-DD>: "<their words>")`. Exempt: agents a step runs together, each brief holding `Fan-out: finality step 2`, `Fan-out: converge §Running the agents` or §Model class's per-provider line; they still count against an agent without it. Start a browser-heavy agent only while the 1-minute load (`uptime`) is below `nproc`. Stop an agent once its question is settled.
   Hook: pre-agent-dedupe
2. **Model class and effort.**
   Open: §Model class; reviews: §Reviewers; the project file's `## Agents` section overrides
3. **The brief.** Paste the role's template from the installed copy each time and fill every `<…>`: the pinned current head (never a moving branch), the project file's path, the standards by path, `agent.md`, the critical-path item it unblocks, and a time budget for a long job.
   Open: `delegate/<role>.md`; §Brief · Record: the brief file · Hook: pre-agent-dedupe (pins, `Fan-out:`, the project file, its repo study within 30 days for authors and fresh readers, `Topic:`)
4. **Launch in the background;** its completion wakes you.
   Run: T3 Code: `delegate_task` with a unique `clientRequestId`; else the Agent tool · Record: the job pre-agent-dedupe registers · Hook: pre-bash-guard (wait loops), pre-agent-dedupe (a review's company)
5. **Liveness** at 2 minutes and at every wakeup (its output size or log time); five minutes without output: look now. A long job's first output is read within half an hour; confirm its numbers can be used (a benchmark alone on the machine, warmed up, comparing like with like) before it runs the rest; past its budget, stop it or extend it deliberately.
   Run: T3 Code: `task_status`; else its output and log · Hook: stop-lint
6. **Its result** (T3's notice, or the watcher's `### AGENT DONE <ticket>`). Read the final message; open two or three cited `path:line`s or re-run one command, and diff the result against your plan. A diff: write down each structural decision in it and why it's right before landing it; hardcoded lists and duplicated classifications get fixed before pushing. Then release the job.
   Run: `agent-job done <its key>` · Hook: stop-lint, the watcher
7. **Relay the result to the user and act on it;** an unchecked item, a deviation and each finding (by `code §Earn every line`) are yours to decide; never send the same brief again. If it fails your check or comes back blocked, redo it on your model class (reviews: §Reviewers) with what failed.
   Open: `writing §Reports to the user`

### Brief

- **Five parts:** `Goal` (one observable outcome); `Facts` (only what you verified, each with its source); `To check` (your guesses, as questions); `Scope` (the paths and commands it may use, the semantic code-search MCP's name when your session has one, and `agent.md §Machine`, in every brief and every follow-up round); `Acceptance` (the commands or observations that define done).
- **In T3 Code,** `delegate_task`'s `role` is `implementation`, `research`, `design`, `test` or `review`. Research outside §Model class's per-provider seats adds `Topic: <key words>` and a `Checked: <file>` line per work-folder file already read: pre-agent-dedupe blocks one already written up in an unchecked file.
- **Never put in** your opinion, the answer you expect, or earlier agents' conclusions: a guess goes under `To check`. The exception: a report handed to an agent that re-rates it. A maintainer's ask goes in quoted whole: an either/or stays an either/or; the implementer reads the code each option touches and recommends one, saying why, and the main session decides before it lands.
- **Give paths and the question,** never pasted files or long histories.
- **One run is one agent with one prompt.** Group roles reading one artifact in one loop, in order, each writing its own file. Split only for context limits or independence: authors never review themselves, and fresh readers haven't seen the fixes.

### Continue

Later work on the same thing continues that agent, a review round only as a fix check (§Review rounds).
- **Claude Code:** `SendMessage` to its agent id; a `claude -p` reviewer launched with `--session-id <uuid>`: `claude -p --resume <uuid>`.
- **T3 Code:** `t3_thread_send` to its `childThreadId`, mode `queue`, asking for its result in a file a background wait watches; a review's fix check or reverify, which the host sends as a new `delegate_task`: its seat's company, the earlier report and what changed, and `Continues: <its seat loop>`.
- **Codex in a shell:** `codex exec resume -c sandbox_mode=danger-full-access <session id> "<what changed>"` (the id `codex exec` printed).
- **An agent is alive until its transcript and processes are quiet,** whatever T3 shows: a turn that ended, `waiting_for_children`, or a cancel that finds "no interruptible run" mean it wakes when its background commands end, and `t3_queue_promote_to_steer` can revive a run T3 calls `interrupted` or `cancelled`. Continue a stuck agent with a message; a replacement goes in a fresh worktree. When two agents run one job, keep the one with the most progress.

### Model class

The classes are model families, never versions: the largest is the newest Fable Claude Code offers, else the strongest; the strongest, the newest Opus; the smallest with an effort setting, the newest Haiku; missing: tell the user. The main session plans, briefs, decides, spot-checks results and approves every word to a maintainer. Never a model the user excluded, an effort above xhigh, nor a model version in a prompt, skill or memory.
- **Choosing among options** (`pull-request` step 5's rating, `finality` step 3's converging agent): the largest; **root causes and authors** (code, docs, PR bodies, replies, designs): the strongest (delegated if the main session isn't); both at high effort. **Audits and exploration:** the strongest at medium (independent checks: §Reviewers).
- **The smallest class with an effort setting, at high effort,** only for work where nothing it writes ships: running gates, tests and a reproduction from a recipe, log mining, data processing and bookkeeping.
- **One per provider:** `finality` step 3's branch agents, `design` steps 3–4's debaters and designers, `pull-request` step 5's candidates. One job per driver kind (`claudeAgent`, `codex`, `antigravity`; in T3, `target.providerInstanceId` from `orchestrator_capabilities`; outside T3, those the host starts); a provider that can't run: its finality branch goes to one that can, Claude first, keeping its `branch<N>`; other seats go without; your report names it; none can: stop, report it. Each call: role `research`, the provider and its `<kind>` in its title and `clientRequestId`, a `task` naming the provider, its part and its absolute output `<name>.<provider>.<kind>.md`; its brief: `Fan-out: <skill> step <N>`, the shared starting evidence (a finality branch: PHASE B's inputs only). Claude: smallest class for branches, else strongest; Codex: its default model; Antigravity: Gemini Neon (its default); no model override for either; high effort where offered. Antigravity never implements.

### Reviewers

Every independent check picks its reviewer in this order, trying the first each time: an earlier "unavailable" note (memory, a post's badge) is no check:
- **First, a model from another company than the main session's:** its default model, at the effort chosen per call (high; medium for a verifier or a few-sentence reply). In T3 Code, a round is a `delegate_task`, role `review`, the reviewer's `providerInstanceId` and effort from `orchestrator_capabilities`:
   ```json
   {"task": "Follow <prompt file>; output to <out>", "role": "review", "target": {"providerInstanceId": "<id>", "options": {"<its effort option>": "<effort>"}}, "clientRequestId": "<loop>-r<N>"}
   ```
   Elsewhere, a Codex reviewer: `codex exec -c model_reasoning_effort=<effort> --sandbox danger-full-access --skip-git-repo-check -o <out> "$(cat <prompt file>)" < /dev/null`; a Claude reviewer: `claude -p --session-id <uuid> --effort <effort> --permission-mode bypassPermissions < <prompt file> > <out>`.
- **Else, a fresh agent of the strongest class,** with the same prompt, effort and task line `Fallback: <failed seat tag> failed: <why>`, when the first fails (spent credits, rate limits, errors, no report in time). A report, even partial, is no failure.
- **Round 1 of a code loop** (each Loop A slice, Loop B, a small review, the fresh reader, its only round) runs two seats at once, each its own loop `<loop>-<seat>-r1` (`Fan-out: converge §Running the agents`, `Seats: <both tags>`, as `Seats: codex, neon`): the first above, Codex, and a third company's (Gemini Neon, the default model of a signed-in Antigravity instance; else your scope.md line `Reviewer: <providerInstanceId or CLI>`), else a fresh agent of the strongest class; the fresh read's: Codex and Neon, else its fallbacks. Rule on both.

The prompt is a file with the template filled. Never write `CLEAN` yourself. Record which reviewer ran (Tier M: a `ledger.md` row).

### Review rounds

Every review loop:
- **Severity:** the ledger keeps the reviewer's label (`agent.md`); your re-rating, with its reason, goes in the outcome, a finding you rate a nit `declined: nit, <why>`; nits get no code.
- **Rounds per head** for code and docs (a post's end once gate-pass passes: `post` step 3). Round 1 hunts every finding. A later round, the seat's next of four, is a fresh reviewer of its company hunting what changed since and what the reports left unchecked, given those commits, its ledger and the other seat's declined and listed rows, none raised again, never the reports, its template's slot bounding every check (a combined Loop B prompt's too); or, active within 50 minutes, that reviewer's fix check of its own findings by ledger id (`Review: <step> [<part>] fix-check`, §Continue), whose brief holds, in place of the template's checks, those ids, their fixes and the checks proving them. Rounds go on while the last brought a blocker or should you fixed, ending at the first bringing only nits or declined findings, or at round 4, whose fixes get only the gates; a round 4 bringing a fix means `finality`. Then open findings are `listed:`; work goes on. Before the next round, cut what fixes added beyond need.
- **A head past 80 of the PR's own changed lines** since a round's pinned head (`converge §Batching`'s exclusions, base merges too) starts the count again; round numbers go on.
- **Names:** round `<loop>-r<N>` (T3's `clientRequestId`, Agent's `description`, `SendMessage`'s `summary`, a prompt file) of loop `<step-or-slice>-<seat>` (its company, `codex`; a second on one company `claude2`), `<slice>-reverify`, `<slice>-recheck` and `<slice-or-step>-fresh`, on the seat reverify would pick, within its four, or `<loop>-ask<N>` (a maintainer's ask). A new agent replacing a seat past its context declares `Continues: <seat loop>` and gets that loop's last report and ledger.
- **Ledger:** each seat's `<work folder>/drafts/<review>.ledger.md` (a post's: beside it, both seats' rows), one line per finding: `<id> <label> <outcome>`, the id `R<round>.<n>` (a post's second seat: `<seat>:R<round>.<n>`) and the seat's label, the outcome `fixed in <sha>` (on HEAD; a post: `fixed in r<N>`, the confirming round; elsewhere a draft finding: `fixed in <draft, ledger-relative>` once gate-pass passed it), `declined: <why>`, `listed: <where>` or, mid-round, `disputed: <evidence>`, each row ending `seen by: <seat tags>`. `Round: <N>`: the last completed round. A last round not clean: `pr-steps <step> <file> --ledger <it>` or `gate-pass … --ledger <it>`: an open or listed blocker keeps the PR in draft.
- **Stuck:** a blocker you decline stays `declined: <your evidence>` and goes to the user, both sides in 2–3 lines. Rule on evidence, never to end the loop.
- **While a round runs,** leave what it reads unchanged.
