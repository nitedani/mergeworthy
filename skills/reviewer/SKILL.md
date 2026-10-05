---
name: reviewer
description: "Running an independent review (a post's gate, a PR's review round, a convergence pass): who reviews, how to run it, and the CLEAN verdict."
---

# Reviewer

Every independent review uses this order: the posting gate (1.6), `implement-issue`'s review round and refactor pass, and `convergence`'s passes.

1. **Codex**, another company's model:
   ```bash
   m=$(codex-review-model) && codex exec -m "$m" --sandbox danger-full-access --skip-git-repo-check -o <out> "$(cat <prompt file>)" < /dev/null
   ```
   `codex-review-model` prints Codex's current top model, never a hardcoded one. It exits 3 without calling anything while Codex's last usage snapshot says it is out of credits or rate-limited: then skip to step 2. If the account refuses the model, take the next from `codex-review-model --all`. Record the model from the `model:` line the command prints.
2. **The local model**, when it is on and the GPU is free: a T3 Code `delegate_task` child on the Local Claude instance (`orchestrator_capabilities`), model `local`, `runtimeMode: "full-access"`, `mode: "async"`, the same prompt.
3. **A fresh-context Claude subagent** on the session's default model, the same prompt. Never a cheaper model.

An error, a hang or "out of credits" is not a review. Record which reviewer ran; on Tier ≥ M work, re-review on Codex once it's back. When the session itself runs on the local model, a step-2 or step-3 review is the same model reviewing its own kind of work: say in the report that there was no outside review.

**The prompt** is a file: the charter (the gate's checks in 1.6, `implement-issue`'s reviewer charter, `convergence`'s guardian or refactor prompt), the artifact's paths at pinned SHAs, and one sentence on what it claims to do. Never your conclusions or the verdict you want. Its final message is exactly `CLEAN`, or the findings.

**Its result** is candidates (1.1.15): check each finding against the code before acting, fix the real ones in your own words, and decline the rest with a one-line reason. Never write `CLEAN` yourself.
