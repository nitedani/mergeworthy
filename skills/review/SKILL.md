---
name: review
description: "Any independent review: who reviews (Codex, else a fresh Claude), the CLEAN verdict, and the PR review round with its reviewer charter."
---

# Review

Every independent review uses this order: the posting gate (1.6), `review`'s PR review round and refactor pass, and `converge`'s passes.

1. **Codex**, another company's model:
   ```bash
   codex exec --sandbox danger-full-access --skip-git-repo-check -o <out> "$(cat <prompt file>)" < /dev/null
   ```
   It runs the model configured in `~/.codex/config.toml`. If it fails (out of credits, a rate limit, an error), go to step 2; that failure takes seconds.
2. **A fresh-context Claude subagent** on the session's default model, the same prompt. Never a cheaper model. When your environment's own instructions name a reviewer to use first (a local model on this machine), it goes before this step.

An error, a hang or "out of credits" is not a review. Record which reviewer ran; on Tier ≥ M work, re-review on Codex once it's back.

**The prompt** is a file: the charter (the gate's checks in 1.6, `review`'s reviewer charter, `guardian`'s charter or `refactor`'s prompt), the artifact's paths at pinned SHAs, and one sentence on what it claims to do. Never your conclusions or the verdict you want. Its final message is exactly `CLEAN`, or the findings.

**Its result** is candidates (1.1.15): check each finding against the code before acting, fix the real ones in your own words, and decline the rest with a one-line reason. Never write `CLEAN` yourself.

## The PR review round: correctness, security, bloat

The reviewer (`review`) reviews the diff with the reviewer charter at the end of this skill. Write the charter to `<artifact root>/review-<pass id>.md` and append: the diff command against `git merge-base HEAD origin/<base>`, the issue link (Tier ≥ M: also `acceptance.md`), and one sentence on what the change claims to do. It says UNKNOWN for anything it could not observe; paste your gate commands, exit codes and output where it can't run them. If no reviewer at all is available, review it yourself with the charter.

One round: fix real defects, decline the rest with a line of reasoning (1.1.15), no second round. Record who reviewed (or that it was a self-review) and what they found, including nothing, in the ledger (1.2), and run `pr-steps review <output>`.

## Reviewer charter

Hand this to the reviewer (`implement-issue` step 6): not the author, not in the author's context.

---

You are reviewing a change you did not write. Read the touched files in full, not just the hunks. Code outside the diff is context, not your subject. Run the gates yourself rather than trusting the report.

Tag every material claim OBSERVED (path:line, or command + exit code + output), INFERRED (say the premises), or UNKNOWN (say what is missing). Only OBSERVED closes anything. "Unchanged", "every call site" and "every locale" are claims that need a diff behind them — re-open the file rather than writing from memory.

Three lenses, one pass:

**Correctness.** Revert the fix and confirm the failure returns, then restore. A check that also passes without the change proves nothing. Look for the behaviour the issue actually reported, not the behaviour the diff implements. List each asked-for behavior that is missing or only partly there, quoting the line that asks for it.

**Security.** You know what to look for; this repo's surfaces are in the project file. The part you cannot infer from a diff: a change to what the API returns, or to what a filter matches, breaks consumers silently and is a team decision, not a reviewer's.

**Bloat**, deletions first. For every mechanism added, name the user-visible scenario it serves — "it could break" is not one; no scenario, delete it. Comments and tests are priced like code.

**Delete by probe, not by opinion.** Before calling something removable, run a check that *could* fail. If it goes red, the thing is load-bearing — say so and record the failure. Confirming a mechanism earns its place is as good a result as deleting one.

Do not ask for a guarantee to be strengthened in order to close a finding. A round that finds nothing is a real result: say what you searched and failed to find. If you confirm nearly every suspicion you started with, you were building a case, not reviewing.

Output: a verdict — PASS / CHANGES-REQUESTED / FAIL — then findings as `path:line — what breaks — what to do instead`, most severe first, then what you searched and did not find. No style preferences.
