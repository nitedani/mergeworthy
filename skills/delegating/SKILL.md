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
    - Grep first, and edit the existing line instead of adding another.
    - Prefer a mechanism to a sentence.
- **A mechanism ships whole, the first time.** It starts, restarts after a crash and a reboot, retires when its job is done, and runs one instance per job. It works on every OS the methodology runs on (Linux, macOS; a fallback elsewhere). Before calling it done, test it by killing it, rebooting its supervisor and finishing its job.
- **State the behavior you want** ("write one-line comments"), not only the one you don't. Keep a "never" for hard guardrails, and pair it with what to do instead.
- **No self-assessed opt-outs** ("skip on small fixes"). A missing precondition is a hard stop.
- **A cold read after any cut.** A fresh-context agent reads the file cold and lists every sentence it can't act on. Fix those sentences.
- **Commit and push every change** to a mergeworthy skill or mechanism, to its repo, in the same step. The plugin's auto-update brings the change to every machine. Never edit an installed or running copy.

## 1.10 Integrating agents' work

- **Understand a subagent's diff before landing it.** Write down each structural decision in it and why it's right. Hardcoded lists and duplicated classifications get fixed before pushing.
- **Every background job has a liveness check** (output size or log mtime). Check it at 2 minutes and at every wakeup; five minutes without output means investigate now. Never report "dispatched" or "armed" as progress.
- **Relay every agent report.** When an agent reports, relay the result to the user and act on it; the user never sees the agent's report.
- **Taking over another session's work starts with its state,** re-checked on the current head. Re-run each claim in the open PR's body (checks, e2e, screenshots), and list each owed reply. That state is the first answer to "done?", and the work continues from what failed.

### Briefing an agent

- **The brief** has five parts:
    - `Goal`: one observable outcome.
    - `Facts`: only what you verified, each with its source.
    - `To check`: your guesses, as questions.
    - `Scope`: the paths and commands it may use.
    - `Acceptance`: the commands or observations that define done.

  Never put in your opinion or the answer you expect: a guess goes under `To check`.
- **What the agent returns:** the result with evidence (`path:line`, or the command and its exit code), and a `not_checked` list. An unchecked item or a deviation is yours to decide; never send the same brief again.
- **What the agent must not do:**
    - widen the brief;
    - pick a different approach than the plan (it stops and reports why the plan is wrong instead);
    - call something unused before finding every caller (`grep -rn`) and reading the comment above it;
    - say a step ran when it couldn't (it stops and says what blocked it).
    - start agents of its own (it does the work itself), or end its turn while work it started is still running.
- **Before using its result,** open two or three of its cited `path:line`s, re-run one command, or diff the result against your plan.
- **A long job gets a time budget in its brief, and an early check.** Read its first output within half an hour. Confirm the numbers can be used (a benchmark alone on the machine, warmed up, comparing like with like) before it runs the rest. Past its budget, stop it or extend it deliberately.
- **A subagent that writes a PR** follows the mergeworthy skills, not a summary of them: open `merging` (1.7) for what its prompt must name and what its report lists.
