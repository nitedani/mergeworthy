## 1.9 Writing rules, prompts and docs

When editing a skill, prompt, rules file or AGENTS.md:
- Make exactly the requested operation on exactly the named text; anything extra gets one line in your reply, not an edit. Text the user supplied verbatim stays verbatim.
- Add the minimal delta, usually one sentence, placed at the step where it bites. No rationale, no incident stories, nothing a competent model does anyway. Repo facts go only in the project file. Grep first and edit the existing line instead of adding another. Prefer a mechanism to a sentence.
- State the behavior you want ("write one-line comments"), not only the one you don't; keep a "never" for hard guardrails, and pair it with what to do instead.
- No self-assessed opt-outs ("skip on small fixes"). A missing precondition is a hard stop.
- After any cut, a fresh-context agent reads the file cold and lists every sentence it can't act on. Fix those. Every change to the methodology or a mechanism is committed and pushed to its repo in the same step, then installed (`install-methodology`); never edit an installed or running copy.

