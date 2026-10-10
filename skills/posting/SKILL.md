---
name: posting
description: "Everything you post or edit on GitHub: the posting steps, the forms (the header, PR and issue bodies, inline comments, images), and opening an issue."
---

# Posting

Everything that reaches GitHub goes through these steps: comments, replies, inline comments, reviews, PR and issue bodies, edits of any of them, and gists. Reactions don't.

## Steps

1. **Read the whole thread** from its first comment, the threads it links and your own earlier replies: `mw thread <ref>`. For a long thread, an Opus drafter reads it and drafts from your brief (the question, your position and reasons), and returns the draft plus every conflict with a past decision, each with its permalink.
   Done: the draft's notes list every question still open and every decision already made, each with its permalink.
2. **Draft it by `writing`** into a file in the task's work folder (`drafts/<name>.md`), never straight into a command.
   Done: the draft file exists.
3. **Lint it:** `mw lint <draft> --repo <owner/repo> --kind <reply|design|pr|issue|umbrella>`. Fix every error.
   Done: `mw lint` exits 0.
4. **Review it** (`review`, with the posting checks). Fix the draft and re-review until the reviewer's verdict is `CLEAN`.
   Done: `<draft>.verdict.json` says `CLEAN` for the current text.
5. **Re-check every claim against the current head** right before posting: `git fetch`, and confirm every referenced commit is pushed.
   Done: every claim and link holds on the head.
6. **Post it:** `mw post --kind <kind> <draft> -- gh <command with --body-file <draft>>`, or `-F body=@<draft>` for API posts. An inline review comment is one draft per comment: `mw post <draft> -- gh api repos/<o>/<r>/pulls/<N>/comments -F body=@<draft> -f commit_id=<head sha> -f path=<path> -F line=<n> -f side=RIGHT`. A reply whose only content is an acknowledgement, or "Done in <sha>" with nothing else, may skip the review, with that reason in the bypass flag.
   Done: `mw post` printed the URL, and the thread is in your watch.

## Forms

- **The header.** A post's first line is the icon of every agent that worked on it, reviewers too: Claude `<img src="https://github.com/claude.png" width="20" height="20" alt="Claude">`, Codex `<img src="https://github.com/openai.png" width="20" height="20" alt="Codex">`. On the same line, in italics, one short sentence says which model did what, with its version (*<model and version> wrote this; <model and version> reviewed it.*), and ends with a link to the umbrella issue or WIP comment of the goal the post belongs to, when there is one. Then a line break, no label. Only the umbrella's own body goes without. When the header form changes, edit every open PR body you own to it.
- **A PR body:**
  - It is written to be scanned. The first paragraph says what was wrong, in a user's words, and what this PR changes; status (draft, dependencies) comes after.
  - Evidence comes in a skimmable shape: a before/after table, a permalink to the line at fault, screenshots with one line each on what to look at.
  - A feature explains how it works with a code sample.
  - A note for the maintainer goes in one table, `| Note | Kind | Blocks merge | Next |`. Every comment, guard or workaround the diff deletes gets a row there with the evidence that it's obsolete; otherwise it stays.
  - `Closes #N` only when the change fixes what the issue reported; otherwise `Refs #N`, with your findings commented on the issue.
  - Say a dependent project needs this PR only if it is still broken without it. When a revert wouldn't undo the merge, that caveat ends the prose.
  - One collapsed Verification block comes last (`pull-request`, step 10).
- **An issue body:** one finding, without how you came across it. The title is the symptom as a user meets it. `### How to reproduce` with numbered steps, then the evidence; `file:line` last, for whoever fixes it.
- **An inline review comment:** only where a reviewer must judge (a call that could have gone the other way, something the diff can't show, a risk you hand over), at most two sentences. No comment at all is the normal outcome for a small fix.
- **An image or video:** one line on what to look at and what it proves, and the setup (page, filter) when the default view doesn't show it. A PR's images open on the defect, close on the fix, and between them show what the change could have broken and didn't.
- **A review of someone else's PR** posts its findings and never approves unless the user asked.

## Opening an issue

1. **Should it be a PR instead?** Find the fix first; an obvious fix for a defect you hit is a PR, upstream included. File an issue only when you can't find a fix, or when the fix needs the owner's product decision.
   Done: `task.md` says why it's an issue and not a PR.
2. **Already filed or fixed?** Run `gh issue list --state all --search "<keyword>"` and `git log --oneline origin/<base> -- <files>`. An existing issue gets your finding as a comment, not a twin.
   Done: no twin, and no fix on the base.
3. **Reproduce it on today's base** from a clean start, as a user meets it. What you can't reproduce isn't filed.
   Done: a screenshot, video, or request and response that shows it.
4. **Write the body** by `writing` and `posting` (Forms), with `### How to reproduce` and the evidence. A decision issue adds `### Options`, showing what a user sees under each option, plus your recommendation.
   Done: a newcomer could reproduce it from the body alone.
5. **Post it** (Steps, above) and add it to the watch.
   Done: the posted body shows its evidence.
