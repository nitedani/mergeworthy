---
name: delegating
description: "Writing rules, prompts or docs, and starting, briefing or integrating subagents and the local model."
---

## 1.9 Writing rules, prompts and docs

When editing a skill, prompt, rules file or AGENTS.md:
- Make exactly the requested operation on exactly the named text; anything extra gets one line in your reply, not an edit. Text the user supplied verbatim stays verbatim.
- Add the minimal delta, usually one sentence, placed at the step where it bites. No rationale, no incident stories, nothing a competent model does anyway. Repo facts go only in the project file. Grep first and edit the existing line instead of adding another. Prefer a mechanism to a sentence.
- A mechanism ships whole, the first time: it starts, restarts after a crash and a reboot, retires when its job is done, runs one instance per job, and works on every OS the methodology runs on (Linux, macOS; a fallback elsewhere). Test it by killing it, rebooting its supervisor and finishing its job, before calling it done.
- State the behavior you want ("write one-line comments"), not only the one you don't; keep a "never" for hard guardrails, and pair it with what to do instead.
- No self-assessed opt-outs ("skip on small fixes"). A missing precondition is a hard stop.
- After any cut, a fresh-context agent reads the file cold and lists every sentence it can't act on. Fix those. Every change to the methodology or a mechanism is committed and pushed to its repo in the same step, then installed (`install-methodology`); never edit an installed or running copy.

## 1.10 Integrating agents' work

- Before landing a subagent's diff, write down each structural decision in it and why it's right. Hardcoded lists and duplicated classifications get fixed before pushing.
- Every background job has a liveness check (output size or log mtime), checked at 2 minutes and at every wakeup. Five minutes without output means investigate now. Never report "dispatched" or "armed" as progress.
- When an agent reports, relay the result to the user and act on it; its report isn't shown to them.
- Taking over another session's work starts with its state, re-checked on the current head: each claim in the open PR's body (checks, e2e, screenshots) re-run, each owed reply listed. That state is the first answer to "done?", and the work continues from what failed.
