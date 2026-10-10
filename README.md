# mergeworthy

A Claude Code plugin that makes an AI agent work through GitHub like a colleague: PRs a maintainer merges as they are, every thread answered, every post reviewed before it goes out.

- `always-on.md` is added to every session. It tells the agent which of the twelve skills to open for the work at hand, and the agent opens each one only when it needs it: `task`, `delegating`, `design`, `finality`, `pull-request`, `converge`, `evidence`, `github`, `posting`, `review`, and the two standards `code` and `writing`, which say what good code and good prose look like.
- Hooks check some commands before they run. Three are always refused: killing processes by name or pattern, force-pushing without `--force-with-lease`, and reusing a T3 Code task's `clientRequestId` for a new task. The other checks stop a command once and print the line to add, with a reason, to run it anyway.
- `mw` is a command-line tool that is on the PATH inside Claude Code. It watches threads, checks and posts drafts, and records review steps. `mw help` lists its commands.

Try it: `claude --plugin-dir /path/to/mergeworthy`. Tests: `npm test` (Node ≥ 20, no dependencies).
