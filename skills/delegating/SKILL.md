---
name: delegating
description: "Writing skills, rules or prompts, and starting, briefing or integrating subagents."
---

## 1.9 Writing rules, prompts and docs

These rules hold when you edit a skill, prompt, rules file or AGENTS.md. Rules for user-facing docs are in `core` 1.3 (docs, style): open `core` before writing docs in a repo.
- **Exactly the requested operation.** Make exactly the requested operation on exactly the named text. Anything extra gets one line in your reply, not an edit. Text the user supplied verbatim stays verbatim.
- **The minimal delta,** usually one sentence, placed at the step where it bites.
    - No rationale, no incident stories, nothing a competent model does anyway.
    - Repo facts go only in the project file.
    - Grep first and change the text that already covers it, never add beside it; merge any overlap you find. Keep the word count flat or lower; the repo's word-budget test fails when the skills grow, and raising its budget needs the reason nothing existing could carry the change.
    - Prefer a mechanism to a sentence.
- **A mechanism ships whole, the first time.** It starts, restarts after a crash and a reboot, retires when its job is done, and runs one instance per job. Before calling it done, test it by killing it and finishing its job.
- **State the behavior you want** ("write one-line comments"), not only the one you don't. Keep a "never" for hard guardrails, and pair it with what to do instead.
- **No self-assessed opt-outs** ("skip on small fixes"). A missing precondition is a hard stop.
- **A cold read after any cut.** A fresh-context agent reads the file cold and lists every sentence it can't act on. Fix those sentences.
- **Commit and push every change** to a mergeworthy skill or mechanism, to its repo, in the same step. Update each installed agent through its installation mechanism and verify the installed version before claiming the rule is fixed there (README, Install). Never edit an installed or running copy.

## 1.10 Integrating agents' work

- **Understand a subagent's diff before landing it.** Write down each structural decision in it and why it's right. Hardcoded lists and duplicated classifications get fixed before pushing.
- **The orchestrator never blocks.** Start agents and long commands in the background and keep working; their completion notification wakes you. A foreground wait loop stalls every other thread and reply (`pre-bash-guard` blocks one).
- **One agent per job, enforced by `pre-agent-dedupe`.** An agent is alive until its task is terminal: a turn that ended, `waiting_for_children`, or a cancel that finds "no interruptible run" all mean it will wake again when its background commands end. Continue a stuck agent with a message instead of starting another; when two run one job, keep the one with the most progress. After reading a finished agent's result, release its job with `agent-job done <ticket>`.
- **Every background job has a liveness check** (output size or log mtime). Check it at 2 minutes and at every wakeup; five minutes without output means investigate now. Never report "dispatched" or "armed" as progress.
- **Relay every agent report.** When an agent reports, relay the result to the user and act on it; the user never sees the agent's report.
- **Taking over another session's work starts with its state,** re-checked on the current head. Re-run each claim in the open PR's body (checks, e2e, screenshots), and list each owed reply. That state is the first answer to "done?", and the work continues from what failed.

### Choosing the model

- **Fan-out** (parallel agents, one per angle: designs, finality branches, mappers, probe cases, reproductions) and checklist checks: the smallest tier with an effort setting, at high effort. Go wider, not bigger.
- **Routine work** (tests, gates, log mining, mechanical edits): a smaller tier.
- **Judgment** (merging fan-out findings, design calls, Loop B, ratings, the fresh reader, gates on design answers and PR bodies): the session's default model, never above unless the user names one.

### Briefing an agent

- **The brief** has five parts:
    - `Goal`: one observable outcome.
    - `Facts`: only what you verified, each with its source.
    - `To check`: your guesses, as questions.
    - `Scope`: the paths and commands it may use.
    - `Acceptance`: the commands or observations that define done.

  Never put in your opinion, the answer you expect, or earlier agents' conclusions: a guess goes under `To check`. The one exception is a previous round's report, given to an agent that re-rates it.
- **An agent ends its turn only with its result.** A turn ended while its own install or test still runs never reports back, and a process it finds later is its own leftover: it checks with `ps` and kills it by PID, never waits on it. Long installs skip postinstall downloads (`--ignore-scripts`) when the browsers or binaries are already cached.
- **A brief from a skill** has its `<...>` placeholders filled with the specifics, and points the agent at pinned SHAs, never a moving branch.
- **A charter or prompt from a skill is pasted from the installed skill** each time you write the brief (in Claude Code, `~/.mergeworthy/current/skills/`). A copy saved earlier in your work folder drifts from it.
- **What the agent returns:** the result with evidence (`path:line`, or the command and its exit code), and a `not_checked` list. An unchecked item or a deviation is yours to decide; never send the same brief again.
- **What the agent must not do:**
    - widen the brief;
    - pick a different approach than the plan (it stops and reports why the plan is wrong instead);
    - call something unused before finding every caller (`grep -rn`) and reading the comment above it;
    - say a step ran when it couldn't (it stops and says what blocked it).
    - start agents of its own (it does the work itself).
- **One run is one agent with one prompt.** Group roles reading one artifact in one loop, in order, each writing its own output file. Split only for context limits or independence: authors never review themselves, and fresh readers haven't seen the fixes. Later work on the same thing (confirming fixes, re-rating) continues that agent: in Claude Code, `SendMessage` to its agent id; for Codex, `codex exec resume -c sandbox_mode=danger-full-access <session id> "<what changed>"` (the id `codex exec` printed, never `--last`; resume has no `--sandbox` flag). A new agent re-reads everything.
- **Before using its result,** open two or three of its cited `path:line`s, re-run one command, or diff the result against your plan.
- **A long job gets a time budget in its brief, and an early check.** Read its first output within half an hour. Confirm the numbers can be used (a benchmark alone on the machine, warmed up, comparing like with like) before it runs the rest. Past its budget, stop it or extend it deliberately.
- Have a PR implementer run the full assigned skills and return each step’s evidence (`merging` 1.7).
