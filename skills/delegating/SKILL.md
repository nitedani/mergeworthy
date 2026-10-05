---
name: delegating
description: "Writing rules, prompts or docs, and starting, briefing or integrating subagents."
---

## 1.9 Writing rules, prompts and docs

When editing a skill, prompt, rules file or AGENTS.md:
- Make exactly the requested operation on exactly the named text; anything extra gets one line in your reply, not an edit. Text the user supplied verbatim stays verbatim.
- Add the minimal delta, usually one sentence, placed at the step where it bites. No rationale, no incident stories, nothing a competent model does anyway. Repo facts go only in the project file. Grep first and edit the existing line instead of adding another. Prefer a mechanism to a sentence.
- A mechanism ships whole, the first time: it starts, restarts after a crash and a reboot, retires when its job is done, runs one instance per job, and works on every OS the methodology runs on (Linux, macOS; a fallback elsewhere). Test it by killing it, rebooting its supervisor and finishing its job, before calling it done.
- State the behavior you want ("write one-line comments"), not only the one you don't; keep a "never" for hard guardrails, and pair it with what to do instead.
- No self-assessed opt-outs ("skip on small fixes"). A missing precondition is a hard stop.
- After any cut, a fresh-context agent reads the file cold and lists every sentence it can't act on. Fix those. Every change to a mergeworthy skill or mechanism is committed and pushed to its repo in the same step (the plugin's auto-update brings it to every machine); never edit an installed or running copy.

## 1.10 Integrating agents' work

- Before landing a subagent's diff, write down each structural decision in it and why it's right. Hardcoded lists and duplicated classifications get fixed before pushing.
- Every background job has a liveness check (output size or log mtime), checked at 2 minutes and at every wakeup. Five minutes without output means investigate now. Never report "dispatched" or "armed" as progress.
- When an agent reports, relay the result to the user and act on it; its report isn't shown to them.
- Taking over another session's work starts with its state, re-checked on the current head: each claim in the open PR's body (checks, e2e, screenshots) re-run, each owed reply listed. That state is the first answer to "done?", and the work continues from what failed.

### Briefing an agent

- **The brief**: `Goal` (one observable outcome), `Facts` (only what you verified, each with its source), `To check` (your guesses, as questions), `Scope` (paths and commands it may use), `Acceptance` (the commands or observations that define done). Never your opinion or the answer you expect: a guess goes under `To check`.
- **What it returns**: the result with evidence (`path:line`, or the command and its exit code), and a `not_checked` list. An unchecked item or a deviation is yours to decide; never send the same brief again.
- **What it must not do**: widen the brief, pick a different approach than the plan (it stops and reports why the plan is wrong instead), call something unused before finding every caller (`grep -rn`) and reading the comment above it, or say a step ran when it couldn't (it stops and says what blocked it).
- **Before using its result**: open two or three of its cited `path:line`s, re-run one command, or diff it against your plan.
- **A long job gets a time budget in its brief and an early check**: read its first output within half an hour and confirm the numbers can be used (a benchmark alone on the machine, warmed up, comparing like with like) before it runs the rest; past its budget, stop it or extend it deliberately.
