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
time (one GPU). It works offline in a sandbox, read-only unless `--write`, and even then only in `<dir>` (use a worktree
you created for it). It returns one JSON result: claims with `path:line` sources, commands with exit codes, and a
`not_checked` list. Modes:
- `facts`: answer a question from the code ("every caller of X and when it runs").
- `evidence`: the strongest evidence-backed case for one `## Position` (one side of 1.5's mini debate; each side gets
  the same neutral ticket, never the other side's argument). You argue and decide.
- `reproduce`: follow a report exactly and show whether it happens; no fixing.
- `run`: run gates, tests, benchmarks or re-runs of failures on `main` vs head, and table the results.
- `implement` (`--write`): execute **your `## Plan`**, a few key points in order (which function, what rule, what not to
  touch), commit, and run the `## Acceptance` checks. It reports deviations instead of choosing another approach.
- `review` (`## File` = the draft): check every claim, example and diff in it against the code; `verdict` is `CLEAN`
  only with no findings. Copy that verdict to the review output for `gate-pass`.
- `cold-read`: a newcomer's read of a doc or rules file (1.3, 1.9): every sentence it can't act on. A weaker model as the
  reader is a stricter test.

**The ticket** (markdown, `## ` headings): `Goal` (one observable outcome), `Facts` (verified, each with its source),
`To check` (hypotheses, as questions), `Scope` (paths, commands), `Acceptance` (commands or observations that define
done), plus `Plan` / `Position` / `File` per mode. Facts never carry your opinion or the answer you expect: the tool
refuses "I think", "probably", "the fix is"…, so a guess goes under `To check`. Paths, not pasted content.

**Check before you use it.** Open two or three of the cited `path:line`s, re-run one command, review an `implement`
diff against your plan. A `not_checked` item or a deviation is an answer: decide it yourself; don't retry the same ticket.
