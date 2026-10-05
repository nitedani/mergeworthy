---
name: github-event
description: "When the watcher reports a GitHub event: decide whether it's yours and answer it the right way, within minutes."
---

## When

Your Monitor delivers a line from `<artifact root>/events.log`, where the watcher records events: a maintainer's comment on a thread you opened or posted in, the user's `/ai` or `/agent` comment, pushed commits, red CI, or a merge you were waiting on.

## Steps

1. Check it is yours: a maintainer's comment on a thread you opened or posted in, or the user's comment with `/ai` or `/agent`. The watcher reports only these; ignore anything else.
2. Reply within a minute through `mergeworthy:post` (its short-reply check): "Done in <sha>" for a finished instruction, or what you are checking.
3. Act on it by kind:
   - **Instruction or suggestion block:** do it (a merge through `mergeworthy:merge`), then reply "Done in <sha>"; if its reason fits a different line than the one it is anchored to, ask first.
   - **Question or soft suggestion:** follow **A question gets an answer, never a change**: trace the code path, have two fresh agents argue each side from the same neutral brief, decide, and answer with code where it is about code.
   - **"OK", "good" or 👍:** treat your last open proposal in that thread as accepted, and do it.
   - **👎 on your comment:** fix the rule behind it (`mergeworthy:failure`), then reply with the fix.
   - **Commits pushed to your PR:** fetch, run the gates, and rate each commit in one table: what it does, the idea, a rating out of 10 with the reason.
   - **Red CI on your PR:** fix it, or explain on the PR with evidence why it isn't the PR's doing.
   - **A merge you were waiting on (a line `<owner/repo#N> -> <dependent>: <what to do>` in `waiting-on.txt`):** apply what waited on it, and post the progress on the dependent PR.
4. Clear the line in `replies-owed.md` (the watcher's list of replies you owe) with `done: <reply URL> <what changed>`, and advance `events.cursor` (how far into `events.log` you have handled) past it.

## Done when

`replies-owed.md` owes nothing for this event, and your reply is a new comment, since edits don't notify.

## Never

- Leave a 👀 without an answer.
- Poll GitHub in a loop, or hand events to a separate agent.
- Correct your own comment with a new one: edit it.

## Enforced by

`gh-watch-start` (the watcher records events and owed replies), `stop-lint` (no turn ends while a reply is owed, or without a live Monitor after a post).

## Next

`mergeworthy:post` for every reply.
