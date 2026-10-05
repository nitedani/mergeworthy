---
name: review
description: "Any independent review: who reviews (Codex, else a fresh Claude), the CLEAN verdict, and the PR review round with its reviewer charter."
---

# Review

**Every independent review picks its reviewer in this order.** That covers the posting gate (1.6), the PR review round below, `refactor`'s refactor pass, and `converge`'s passes.

1. **Codex**, another company's model:
   ```bash
   codex exec --sandbox danger-full-access --skip-git-repo-check -o <out> "$(cat <prompt file>)" < /dev/null
   ```
   Codex runs the model configured in `~/.codex/config.toml`. If Codex fails (out of credits, a rate limit, an error), go to the next reviewer; that failure takes seconds.
2. **The reviewer your environment's instructions name**, if they name one (a local model on this machine).
3. **A fresh-context Claude subagent** on the session's default model, with the same prompt. Never a cheaper model.

After the review:
- **Confirm fixes with the same reviewer.** After you fix its findings, continue that reviewer and send it what changed. Start a fresh reviewer only when the artifact changed beyond those findings, or for the final read of a long artifact.
- **A failure is not a review.** An error, a hang or "out of credits" counts as no review.
- **Record which reviewer ran.** On Tier ≥ M work, re-review on Codex once Codex is back.

**The prompt is a file.** It holds the charter (the gate's checks in 1.6, the reviewer charter below, `guardian`'s charter or `refactor`'s prompt), the artifact's paths at pinned SHAs, and one sentence on what the artifact claims to do. It never holds your conclusions or the verdict you want.

**The reviewer's final message is exactly `CLEAN`, or the findings.** One run may follow several briefs that have their own output (the reviewer charter's verdict, the verifier's count). Then each brief writes to its own output file, and the final message is exactly `CLEAN` only when none of them has a finding.

**The result is candidates** (1.1.15). Check each finding against the code before acting. Fix the real ones in your own words, and decline the rest with a one-line reason. Never write `CLEAN` yourself.

## The PR review round: correctness, security, bloat

A reviewer, picked in the order above, reviews the diff with the reviewer charter at the end of this skill.

1. Write the charter to `<artifact root>/review-<pass id>.md`. Name an output file in it for the full verdict and findings; the final message is only `CLEAN` or the findings.
2. Append the diff command against `git merge-base HEAD origin/<base>`, the issue link (Tier ≥ M: also `acceptance.md`), and one sentence on what the change claims to do.
3. Where the reviewer can't run your gates, paste the gate commands, exit codes and output; it says UNKNOWN for anything it could not observe.
4. If no reviewer at all is available, review the diff yourself with the charter.

In a PR's pipeline, this round runs inside two agents that `converge` defines under "who reads". The reader runs it once on the diff, together with the other passes. The fresh reader runs it again on the final head.

**One round.** Fix real defects, and decline the rest with a line of reasoning (1.1.15). The same reviewer then confirms the fixes (above), with no fresh audit. Record who reviewed (or that it was a self-review) and what they found, including nothing, in the ledger (1.2). Then run `pr-steps review <output>`.

## Reviewer charter

Hand this to the reviewer (`implement-issue` step 6): not the author, not in the author's context.

---

You are reviewing a change you did not write.
- Read the touched files in full, not just the hunks.
- Code outside the diff is context, not your subject.
- Run the gates yourself rather than trusting the report.

Tag every material claim:
- OBSERVED (path:line, or command + exit code + output),
- INFERRED (say the premises), or
- UNKNOWN (say what is missing).

Only OBSERVED closes anything. "Unchanged", "every call site" and "every locale" are claims that need a diff behind them — re-open the file rather than writing from memory.

Three lenses, one pass:

**Correctness.**
- Revert the fix and confirm the failure returns, then restore. A check that also passes without the change proves nothing.
- Look for the behaviour the issue actually reported, not the behaviour the diff implements.
- List each asked-for behavior that is missing or only partly there, quoting the line that asks for it.

**Security.**
- You know what to look for; this repo's surfaces are in the project file.
- The part you cannot infer from a diff: a change to what the API returns, or to what a filter matches, breaks consumers silently and is a team decision, not a reviewer's.

**Bloat**, deletions first.
- For every mechanism added, name the user-visible scenario it serves — "it could break" is not one; no scenario, delete it.
- Comments and tests are priced like code.

**Delete by probe, not by opinion.**
- Before calling something removable, run a check that *could* fail.
- If it goes red, the thing is load-bearing — say so and record the failure.
- Confirming a mechanism earns its place is as good a result as deleting one.

Do not ask for a guarantee to be strengthened in order to close a finding. A round that finds nothing is a real result: say what you searched and failed to find. If you confirm nearly every suspicion you started with, you were building a case, not reviewing.

Output:
- a verdict — PASS / CHANGES-REQUESTED / FAIL —
- then findings as `path:line — what breaks — what to do instead`, most severe first,
- then what you searched and did not find.

No style preferences.

Your final message is exactly `CLEAN` when the verdict is PASS with no findings, else the findings.
