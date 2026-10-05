---
name: post
description: "When you are about to write anything to GitHub: draft it, check it, gate it, post it."
---

## When

You are about to write a comment, a reply, an inline comment, a PR or issue body, or an edit of one. Reactions are exempt.

## Steps

1. Start the watcher before opening an issue or a PR in a repo: `gh-watch-start <artifact root> <owner/repo>`, then arm the Monitor it prints (Claude Code's Monitor tool on the watcher's `events.log`, which delivers each event to you) and re-arm it whenever it expires, every 30 minutes.
2. Write the draft to `<artifact root>/drafts/<name>.md` following [writing.md](writing.md), and, if it answers a comment, that comment to `<name>.parent.md`.
3. Run `post-lint drafts/<name>.md --kind reply|pr|issue|inline|proposal|tracker` until it passes (`proposal` for a design walkthrough, `tracker` for an umbrella issue).
4. Have a fresh reader, picked per `mergeworthy:ready` step 1, check the draft: every claim against the code and the thread, every rule in [writing.md](writing.md), and a cold read listing what it can't understand. Fix and re-check until its final message is exactly `CLEAN`.
5. Re-read every claim against the current head after `git fetch`, and check every commit you cite is pushed.
6. Add `PROMISED <thread>: <what> (<draft name>)` to `<artifact root>/proposals-open.md` if the draft promises work, then run `gate-pass <abs path>/drafts/<name>.md <review output>` and post with `--body-file` or `gh api … -F body=@<file>`.

## Done when

The post is up, and its line in `replies-owed.md` is cleared if it was a reply.

## Never

- Post a correction comment: edit the original through this page.
- Promise work you could finish in minutes: do it, then post "Done in <link>".
- Post a draft a subagent wrote without this page.

## Enforced by

`post-lint` (banned phrases, budgets, secrets), `gate-pass` (records the CLEAN review), `pre-bash-guard` (blocks a post whose draft didn't pass the gate or changed since).

## Next

Nothing.
