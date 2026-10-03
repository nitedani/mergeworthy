## TASK

<The task, in the user's words: links, pasted logs, constraints.>

Defaults (the user can override):
- **The user** owns the goal. Code in the user's own repos, and beta, experimental or pre-1.0 features, is theirs, and yours to change for the goal: decide, act, and report afterwards.
<!-- if ownership=team -->
- **Teammates**: whoever reviews and merges in the team's repos; where this file says maintainer, read teammate. The team's code counts as the user's own, except the paths the repo's AGENTS.md reserves for team decisions, which are the team's call. A teammate's review comment is a reviewer request, handled per 1.5.
<!-- end -->
<!-- if ownership=external -->
- **External maintainers**: whoever merges in a repo you don't own (CODEOWNERS, recent mergers). Their requests are settled decisions, and changes to their code's behavior or public surface are their call (Part 3 section 2).
<!-- end -->
<!-- if reviewer=claude -->
- **Review model**: a fresh-context Claude subagent on the session's default model, with the charter as its whole prompt; record which reviewer ran.
<!-- else -->
- **Review model**: the model from `codex-review-model` (Part 5), run with stdin closed: `codex exec -m "$(codex-review-model)" --sandbox danger-full-access --skip-git-repo-check -o <file> "<prompt>" < /dev/null`. If the account refuses it, take the next from `codex-review-model --all`. Record the model from the `model:` line the command prints, never from the model's self-description. When Codex fails (an error, a hang, "out of credits"; none of these is a review), a fresh-context Claude subagent on the session's default model runs the same charter; record which reviewer ran, and re-review on Codex once it's back. Try Codex again at every review.
<!-- end -->
<!-- if session_model=claude -->- **Other models**: judgment work runs on the session's default model; routine agent work on the `sonnet` alias (1.1.14). Never a model above the default's tier unless the user names it, and never one the user has excluded. Never write a model version into a prompt, skill or memory.
<!-- else -->- **One model**: every agent you start runs on the session's model; there is no model parameter to set.
<!-- end -->
<!-- if target=ci -->
- **Artifact root**: `$RUNNER_TEMP/claude-work/` for notes, logs, probes, agent outputs and scratch worktrees, uploaded by the workflow as an artifact after the run; never `/tmp`.
<!-- else -->
- **Artifact root**: a persistent `<task>-work/` directory next to the worktree for notes, logs, probes, agent outputs and scratch worktrees; never `/tmp`.
<!-- end -->
- **Publishing authority**: what the task allows you to open, comment and file. A reviewed draft isn't permission to publish.

---

