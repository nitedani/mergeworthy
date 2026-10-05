---
name: post
description: "When you are about to write anything to GitHub: draft it, check it, gate it, post it."
---

## When

You are about to write a comment, a reply, an inline comment, a PR or issue body, or an edit of one. Reactions are exempt.

## Steps

1. Start the watcher before opening an issue or a PR in a repo: `gh-watch-start <artifact root> <owner/repo>`, then arm the Monitor it prints and re-arm it whenever it expires.
2. Write the draft to `<artifact root>/drafts/<name>.md` following [writing.md](writing.md), and the comment it answers to `<name>.parent.md`.
3. Run `post-lint drafts/<name>.md --kind reply|pr|issue|inline` until it passes.
4. Have a fresh reader check the draft (`mergeworthy:ready`, Who reads): every claim against the code and the thread, every rule in [writing.md](writing.md), and a cold read listing what it can't understand. Fix and re-check until its final message is exactly `CLEAN`.
5. Re-read every claim against the current head after `git fetch`, and check every commit you cite is pushed.
6. Run `gate-pass <abs path>/drafts/<name>.md <review output>`, then post with `--body-file` or `gh api … -F body=@<file>`.

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
