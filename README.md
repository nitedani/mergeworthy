# mergeworthy

A Claude Code plugin that makes an AI agent work through GitHub like a colleague: PRs a maintainer merges as they are, every thread answered, every post reviewed before it goes out.

- `always-on.md` is injected into every session; it routes to twelve skills, each opened only when its step needs it: `task`, `delegating`, `design`, `finality`, `pull-request`, `converge`, `refactor`, `evidence`, `github`, `posting`, `writing`, `review`.
- Hooks stop a few commands. Three are blocked outright: killing by pattern, force-pushing without a lease, and reusing a T3 request id. The rest stop once and print how to go ahead with a stated reason.
- `mw` (on PATH inside Claude Code) holds the tools: `mw help`.

Try it: `claude --plugin-dir /path/to/mergeworthy`. Tests: `npm test` (Node ≥ 20, no dependencies).
