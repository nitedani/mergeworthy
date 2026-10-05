# Execution graph: decision record

## Invariants (what any pipeline must keep from v3)
| # | Invariant | Why |
|---|---|---|
| I1 | Every bug v3 catches is still caught: reproduce-only, fail-on-head pass-on-base, a dry pass after the last fix in each slice | Loop A is the correctness backstop |
| I2 | The author never reviews itself | the reviewer charter's first line |
| I3 | At least one read of the final head by an agent that wasn't anchored by earlier rounds | a continued reader confirms its own findings and misses what it missed the first time |
| I4 | Refactors are behavior-preserving, checked against the pre-refactor tree | verify's final verification |
| I5 | Owner code and owner decisions gates unchanged | converge authority |
| I6 | pr-steps review + refactor on the final head | pre-bash-guard |
| I7 | The verbatim prompts (refactor, guardian charter, finality, reviewer charter) unchanged | user requirement |
| I8 | Context limits: split by slices when the material doesn't fit one context | quality falls when a context overflows |

## Candidates (rated 0-10: how sure it is the obviously right shape)
- C0, today (v3 + today's folds): verifier per slice per round, guardian per scope per round, implementer per scope, final verifier, reviewer, rater. Holds I1-I8; 6 to 30 agents per Tier M PR. **5**: the cost is the problem the user raised.
- C1 (adopted after the adversarial review): one continued reader A1 (verify -> review -> guardian + refactor ratings) and one fresh reader F on the final head, plus D (divergent) only for a design or a maintainer question and X (mapper) only for reshaping. 2 agents per Tier S or M PR under ~1500 diff lines (F is also the PR body's posting-gate review); one A1 and one F per context-sized slice set above that, and per PR in a stack. **8** after the changes below.
- C2, C1 without F. Breaks I3. **4**.
- C3, the main session reads everything itself. Breaks I2. **2**.

## Decisions inside C1, after the adversarial review (adversarial.md)
- **A1, the continued reader** (Claude: it judges). In one run: the verifier brief (Loop A), the reviewer charter verbatim (all three lenses, Bloat included), the guardian charter and the refactor prompt (Loop B). Correctness before structure: rating code a bug fix will change is waste. It reads the head's code in full; `map.md` from a finality pass is a navigation index only. It continues across rounds (sent the new commits) while its context stays under about half the window and the decision packet hasn't changed; otherwise a fresh A1 gets the last report.
- **Rounds:** bugs are fixed and A1 re-verifies only the touched slices until dry (a slice with no bug is dry at once). Then refactor findings land, one commit each; a regression means revert that commit, then a fresh verification of that slice (verify). A1 re-rates old -> new.
- **F, the fresh reader on the final head** (Codex first, per `review`): in one run, the verifier brief on the final head, the reviewer charter verbatim, and the PR body's claims and screenshots. It is the PR body's posting-gate review, so Tier S gets it at no extra agent. F's findings go back through the fix loop; F continues only when the head changed by exactly its own findings' fixes, else a fresh F.
- **Finality** is not folded into the readers: Phases A and B run before code exists (when reshaping), by X; Phase B and a half (the phantom-fix hunt) by X continued; C by the author; D (Owner-Safe closure) is the main session's checklist.
- **Design:** D (one divergent agent) writes three designs before comparing; the adversarial read of the prototype is `review` (Codex, else a fresh Claude), never D.
- **Maintainer question:** D argues both sides from several frames, then judges.
- **Local model (max 2):** the main session's repro loops, test and benchmark runs (exit codes from the script, not the model's reading), and gate reviews of posts per the machine's own rule, each finding checked by the main session; never A1's or F's judgment.
- **Open:** the token cost of C0 against C1 on one real Tier M PR is not measured yet; agent count is not the cost. Measure it on the next Tier M PR and record it here.
