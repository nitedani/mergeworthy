# Writing for GitHub

- Bring the reader something new: a finding, a measurement, a better option, or a decision with its reason.
- Say only what they don't know yet. Don't recite their comment or your earlier one.
- Use short, plain words. No jargon, no hedging, no "happy to", "let me know" or "worth noting".
- Make it self-contained for someone who finds the thread later.
- Compare designs as code: what the user writes, and a `diff` of what changes. A table may summarize; it never replaces the code.
- Give every question you ask your recommendation and its reason.
- Make a change you'd recommend within scope; don't list it.
- Put notes for a maintainer in one table: `| Note | Kind | Blocks merge | Next |`, where Kind is bug, limitation, not a regression, or decision needed.
- Keep the process out of the thread: no reviewers, models, rounds or ratings.
- Stay within budget: a reply ≤ 80 words, a PR body about 150 words plus evidence, an issue one finding in ≤ 400 characters plus a screenshot, an inline comment ≤ 2 sentences.
- Start with the agent's icon and an `**Agent:**` label when posting from the user's account (the `badge` option).
- Write `owner/repo#N` for another repo, and "depends on #N" unless `gh stack` links the PRs.
- Write `<REDACTED>` for every token, cookie and key in logs and screenshots.
