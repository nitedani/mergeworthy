## 1.12 Pre-flight (steps 3 and 4 in every tier; the rest in Tier ≥ M)

<!-- if target=ci -->
At the start of every run, in every tier: read the whole thread since the bot's last comment (comments, review comments, reviews, pushes) and the bot's earlier tracking comment, and rebuild `scope.md` from them. Keep the scope, the ledger and the owed lists (1.5) in this run's tracking comment (the one the action posts and updates), updated as they change, through the gate as a tracker post (`post-lint --kind tracker`); its last edit is the run's final comment.

<!-- end -->
Before the first change:
1. Write `scope.md`.
2. Write the critical path.
3. Check that the Part 5 hooks are in `~/.claude/settings.json`; this file names that file, so add them if missing. <!-- if watcher=on -->Start the watcher with `GH_WATCH_EYES=<maintainers>,<user> gh-watch-start <artifact root> <owner/repo> <N>…`, arm the tail it prints (the Monitor tool, or a background task where there is no Monitor tool), and register every open PR and issue the account has in the scope repos (`gh search prs --author <login> --state open`, and issues), not only this session's; answer<!-- else -->Answer<!-- end --> any maintainer comment still without a reply first.
4. Confirm browser control (for UI work)<!-- if target=local --><!-- if session_model=claude -->, and that `claude-swap list` shows the spare subscriptions<!-- end --><!-- end -->.
5. Note the precedents and style (1.3).

---
