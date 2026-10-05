---
name: ready
description: "When you are about to call a PR ready, or the user asks to converge it: ask fresh readers the questions in order until every answer is nothing worth changing."
---

## When

You are about to say a PR is ready, the user asks to converge a PR, or `mergeworthy:post` or `mergeworthy:pr` needs a fresh reader.

## Steps

1. Pick who reads, in this order (Who reads):
   - **Codex:** `codex exec --sandbox danger-full-access --skip-git-repo-check -o <out> "$(cat <brief>)" < /dev/null`, with the model configured in `~/.codex/config.toml`. If it fails, which takes seconds when it's out of credits, go on.
   - **The local model:** when the `local_model` option is on and the GPU is free, a T3 Code `delegate_task` child on the Local Claude provider, model `local`, `runtimeMode: "full-access"`.
   - **A fresh Claude subagent:** on the session's default model, never a cheaper one.
2. Write each brief from [questions.md](questions.md): the artifact at pinned SHAs, the decisions, exactly one question, and that question's evidence rule. Never your conclusions.
3. Ask the questions in order; the task's size decides which run:
   - **Fix:** bug, read, review, claims.
   - **Feature or program:** bug, shape (only where the code drifted through many patches), earn, read, preserved, review, claims.
4. Weigh every answer through `mergeworthy:finding`, and land each real one as its own commit.
5. Re-ask only what a commit could have changed: a behavior commit re-opens bug for its area; a structural commit re-opens earn, read and preserved for its area; any commit re-opens review and claims.
6. Check, before saying ready: every maintainer instruction in the thread is done, every `scope.md` box is ticked, CI is green, and `replies-owed.md` owes nothing for the PR.
7. Say it once on the PR: "Ready for review" with the head SHA and the CI link.

## Done when

Every question that applies answered "nothing worth changing" on the final head.

## Never

- Call a PR ready on green CI alone.
- Let the author's own context answer a question.
- Post the readers' reports on the PR: they stay in the artifact root.

## Enforced by

`pr-steps` (blocks `gh pr ready` without the review and refactor records on the head).

## Next

`mergeworthy:merge` when a maintainer asks.
