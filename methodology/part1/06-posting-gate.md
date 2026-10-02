## 1.6 Posting gate (every tier, no exceptions)

It covers everything that reaches an external service, with no lighter category: comments, review replies, inline comments, PR and issue bodies, filed issues, and edits of any of these. Reactions are exempt. Implementer subagents never post; they hand you drafts.

1. Write the draft to `drafts/<name>.md` (never straight into a `gh` command), and the comment it answers to `drafts/<name>.parent.md`.
2. Run `post-lint` (Part 5). It must pass.
3. Run the review model with a prompt file. It checks facts and noise, never wording: every claim against the code (`file:line` or a command and its output), the thread and the evidence; every con or risk names who hits it today (a caller, repo or user), or is cut; every sentence the reader could delete; every question answered; every absolute word ("every", "unchanged", "always", "only") quoting what proves it, or cut; maintainer requests followed; links correct. It also reads cold: "you have not seen this thread; list every term or sentence you can't understand". Capture only its final message (<!-- if reviewer=claude -->saved as `drafts/<name>.review.out`<!-- else -->`-o drafts/<name>.review.out`<!-- end -->). Fix every finding and re-review until that message is exactly `CLEAN`. Never paste the reviewer's rewritten wording; write the fix in your own plain words.
4. Right before posting, re-read every claim against the current head (`git fetch` first; read a PR's state before describing it). Every referenced commit is pushed (`git ls-remote`). Run `gate-pass <abs path>/drafts/<name>.md <review output>` and post with `--body-file` on that absolute path (`gh api … -F body=@<file>` for API posts).
5. Post in the thread where the person wrote. Log it.

**Fast gate** (the 1-minute reply in 1.5), only for a reply of a few claims (an acknowledgment, a "Done in <sha>", what you're checking): the same steps, with the review model asked only about those claims. It still has to answer exactly `CLEAN`; never write `CLEAN` yourself.

**Reviewing a maintainer's commits** (when asked): fetch and fast-forward, then build, lint, format-check and test the head. Reply once per push with a table, one row per commit: what it does, the idea behind it, whether that idea holds, and a rating out of 10 with its reason. Findings come with the exact fix. Where the change is big enough, apply the reviewer charter (Part 2) and the refactor prompt (Part 3 section 11.2) to it. Never just "looks good". Don't push onto the branch while the maintainer is committing unless asked.

**Writing.** Every post (and every report, 1.11) brings the reader something they didn't have: a finding, a measurement, a better option, a risk, or a decision with its reason; if it wouldn't, think more first. Engage as a peer: agree or disagree, and say why.
- Self-contained for anyone who finds the thread later. A comparison of designs or behavior shows each option as code: what the user or extension writes, and what changes as a short ```diff block (removed lines `-`, added `+`, so GitHub shows them red and green). A table may summarize them; it never replaces the code.
- Short, plain words. No jargon, abstractions or AI phrasing ("in this run", "doesn't establish", "worth noting", "happy to", "let me know"), and never solicit ("pushback welcome").
<!-- if post_lang=thread -->
- Answer an issue in the language it is written in; PRs, their comments and commits are in English.
<!-- end -->
- Say only what they don't know yet. Don't recite their comment or your earlier replies, don't thank them for an approval, and don't promise how you'll behave next time. When answering several questions, quote each in one line. If all there is to say is "done", say "Done in <sha>".
- Several comments from one person get one reply. Never post a comment that corrects or adds to your own earlier one: edit it in place, through the gate. (The 1.5 result, wait-ping and dependency-progress comments are new comments.)
- Keep the process invisible: reviewers, models, gates, rounds, working ratings and pass reports stay in the artifact root<!-- if review_trace=comment -->, except the review record: one comment per PR (`post-lint --kind review-record`), edited in place as rounds land<!-- end --><!-- if target=ci -->; the ledger in the tracking comment (1.12) sits in a collapsed `<details>` block<!-- end -->. The thread gets the result, with evidence only where a reader needs it to judge.
- Decide what you can decide or measure. A question carries your recommendation and its reason; a change you'd recommend within scope is made, not listed.
- Credit a design or statement to someone only with a link to where they said it.
- Links to another repo use `owner/repo#N`. Write "depends on #N", never "stacked on", unless `gh stack` links them.
<!-- if badge!=off -->
- When posting from the user's account, start with the Claude badge `<img src="https://github.com/claude.png" width="20" height="20" align="left" alt="Claude"> **Claude:**`.
<!-- end -->
- Budgets: reply ≤ 80 words; PR body about 150 words plus evidence, up to 250 when it lists decisions for the maintainer; issue: one finding, ≤ 400 characters plus a screenshot; inline review comments ≤ 2 sentences, only where the reader must judge. Tables, code and images don't count.
- Notes for a maintainer go in one table: `| Note | Kind | Blocks merge | Next |`. Kind is bug, limitation, not a regression, or decision needed; Next is fixed in <sha>, PR <url>, or nothing, because Y. A follow-up is opened before the post, never listed as "recommend" or "follow-up"; in the user's own repos, just do it. A note that blocks the goal and can be fixed anywhere, upstream included, is fixed instead of listed.

