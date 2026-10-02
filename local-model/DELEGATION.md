## Delegating to the local model (`local-agent`)

This machine runs a local model (the one profile.sh selects) that costs no subscription usage. It executes well and judges
poorly: given a clear plan it implements and verifies correctly; left to choose, it can fix a symptom instead of the
cause or draw a confident wrong conclusion. So **Claude owns every decision; the local model does bounded steps whose
result Claude can check cheaply.** Work with it like a senior with a junior: a precise ticket in, a result to review out,
no pairing.

**When.** Only bounded work: Claude can define it precisely, and the local model finishes it in minutes (limit 15 by
default). Not for what Claude does in about a minute itself (writing the ticket and checking the result would cost
more), not for open-ended work, and never for: the approach (Part 2 step 3), anything posted or pushed, maintainer-facing wording. It pairs with Claude:
it works and Claude reviews, or Claude writes and it reviews (`review` mode: the gate review of a draft, `verdict` CLEAN or
FINDINGS; Claude checks every finding). Never a cheaper Claude model in its place.

**How.** `local-agent <mode> <ticket.md> [--cwd <dir>] [--write]`, through Bash with `run_in_background`; one runs at a
time (one GPU). It works in a sandbox with network access (docs, registries, upstream source) but no credentials, read-only unless `--write`, and even then only in `<dir>` (use a worktree
you created for it). It returns one JSON result: claims with `path:line` sources, commands with exit codes, and a
`not_checked` list. Each mode is a skill in `skills/<mode>.md`: what it's for, the agent's instructions, and the ticket
sections it needs (`local-agent` refuses a ticket without them):

| Mode | For |
| --- | --- |
| [`facts`](skills/facts.md) | A question answered from the code |
| [`evidence`](skills/evidence.md) | One side of the mini debate |
| [`reproduce`](skills/reproduce.md) | A report followed exactly, no fixing |
| [`run`](skills/run.md) | Gates, tests, benchmarks, re-runs, tabled |
| [`implement`](skills/implement.md) | Your plan executed and committed (`--write`) |
| [`review`](skills/review.md) | The gate review of a draft; its verdict is the `CLEAN` |
| [`cold-read`](skills/cold-read.md) | A newcomer's read of a doc |

**The ticket** (markdown, `## ` headings): `Goal` (one observable outcome), `Facts` (verified, each with its source),
`To check` (hypotheses, as questions), `Scope` (paths, commands), `Acceptance` (commands or observations that define
done), plus `Plan` / `Position` / `File` per mode. Facts never carry your opinion or the answer you expect: the tool
refuses "I think", "probably", "the fix is"…, so a guess goes under `To check`. Paths, not pasted content.

**Check before you use it.** Open two or three of the cited `path:line`s, re-run one command, review an `implement`
diff against your plan. A `not_checked` item or a deviation is an answer: decide it yourself; don't retry the same ticket.
