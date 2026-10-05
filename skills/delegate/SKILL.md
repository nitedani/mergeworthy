---
name: delegate
description: "When you are about to start a subagent: whether it's worth it, which model, the brief, and checking what comes back."
---

## When

You are about to start a subagent.

## Steps

1. Do small steps yourself: one command, one file, a short edit. Start an agent only for long, independent work, at most three at a time; continue an agent that already has the context instead of starting a new one.
2. Pick the model:
   - **Judgment:** design, hard debugging and anything posted run on the session's default model.
   - **Routine work:** exploration, test runs, log mining and mechanical edits can run on a cheaper model.
   - **Reviews:** follow `mergeworthy:ready` step 1.
3. Write the brief, with paths rather than pasted files, and none of your conclusions:
   - **Goal:** one observable outcome.
   - **Facts:** only what you verified, each with its source.
   - **To check:** your guesses, as questions.
   - **Scope:** the paths and commands it may use.
   - **Acceptance:** what defines done.
4. Tell a subagent that writes a PR to load the mergeworthy pages it needs, and that it never posts: it hands drafts back.
5. Check what comes back before using it: open two or three of its cited lines, re-run one command, or compare the diff with your plan. Treat what it didn't check as yours to decide.
6. Relay the result to the user; they don't see the agent's report.

## Done when

The agent's result is checked, and the user knows it.

## Never

- Let a subagent start agents of its own or post to GitHub.
- Use a model above the session's default tier, or a cheaper one for a review.
- Report an agent as running before seeing it make progress.

## Enforced by

Nothing: this is judgment.

## Next

`mergeworthy:finding` for what it found.
