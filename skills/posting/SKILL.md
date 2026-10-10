---
name: posting
description: "Everything you post or edit on GitHub: the posting steps (draft, lint, review, mw post), the required forms (the first line, PR and issue descriptions, inline comments, images), and opening an issue."
---

# Posting

Everything you send to GitHub goes through these steps: comments, replies, inline comments, reviews, PR and issue descriptions, edits of any of them, and gists. Reactions don't.

## Steps

1. **Read the whole thread,** from its first comment, plus the threads it links to and your own earlier replies. `mw thread <url or owner/repo#N>` prints all of it as markdown, with a permalink for each comment. For a long thread, hand the reading and drafting to an Opus agent. Its brief gives the question, your position and your reasons. It returns the draft, plus every place where the draft conflicts with a past decision, each with its permalink.
   Done: the notes with the draft list every question still open and every decision already made, each with its permalink.
2. **Write the draft as `mergeworthy:writing` says** (its steps 1–3), into a file in the task's work folder (`drafts/<name>.md`). Never write it straight into a command.
   Done: the draft file exists.
3. **Lint it:** `mw lint <draft> --repo <owner/repo> --kind <kind>`. The kind is `reply`, `design` (an answer in a design discussion), `pr`, `issue`, or `umbrella` (the description of a tracking issue or WIP comment, `mergeworthy:github`). The linter checks the first line, @-mentions, em dashes, secrets, words about our internal process in other people's repos, credit given without a link, and the sections each kind needs. Fix every error. The exception is an error that is wrong for this post: the one @-mention in a reminder, or words about our process in a thread where the maintainer asked to see how we change mergeworthy. Keep that one. Step 6 posts it with the bypass flag, and the reason names it.
   Done: `mw lint` exits 0, or the bypass reason for step 6 names each remaining error.
4. **Get it reviewed** (`mergeworthy:review`, with its Posting checks). Fix the draft as `mergeworthy:writing` step 4 says, and send it for review again, until the reviewer records the verdict `CLEAN`.
   Done: `<draft>.verdict.json`, which the reviewer writes with `mw verdict`, says `CLEAN` for the current text.
5. **Re-check every claim against the latest commit** right before posting. Run `git fetch`, and confirm every commit you refer to is pushed.
   Done: every claim and link holds on the latest commit.
6. **Post it with `mw post`.** It lints the draft again, checks that the reviewer's `CLEAN` verdict is for this exact text, and refuses a third comment of yours in a row. Then it runs the `gh` command you give it after `--`:
   - `mw post --kind <kind> <draft> -- gh <command with --body-file <draft>>`;
   - for a post through the API, use `-F body=@<draft>` instead of `--body-file`;
   - an inline review comment is one draft per comment: `mw post <draft> -- gh api repos/<o>/<r>/pulls/<N>/comments -F body=@<draft> -f commit_id=<head sha> -f path=<path> -F line=<n> -f side=RIGHT`.

   When one of these checks is wrong for this post, add `--I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE "<reason>"` anywhere before the `--`. This is the bypass flag. The reason is at least three words, and the user reads it. A reply that only acknowledges, or only says "Done in <sha>", may skip the review, with that reason in the bypass flag.
   Done: `mw post` printed the URL, and the thread is in your watch (`mergeworthy:github`, step 1).

## Forms

- **The first line.** A post's first line holds the icon of every agent that worked on it, reviewers included: Claude `<img src="https://github.com/claude.png" width="20" height="20" alt="Claude">`, Codex `<img src="https://github.com/openai.png" width="20" height="20" alt="Codex">`. On the same line, one short sentence in italics says which model did what, with its version (*<model and version> wrote this; <model and version> reviewed it.*). When the post belongs to a goal with a tracking issue or a WIP comment (`mergeworthy:github`, The tracking issue), the sentence ends with a link to it. Then a line break, with no label. Only the tracking issue's own description has no such line. When this form changes, edit the description of every open PR you own to match.
- **A PR description:**
  - Write it to be scanned. The first paragraph says what was wrong, in a user's words, and what this PR changes. Status (draft, what it depends on) comes after.
  - Show the evidence in a shape that's quick to skim: a before/after table, a permalink to the line at fault, screenshots with one line each saying what to look at.
  - For a feature, explain how it works with a code sample.
  - Put notes for the maintainer in one table, `| Note | Kind | Blocks merge | Next |`. Every comment, guard or workaround the diff deletes gets a row there, with the evidence that it's no longer needed. Without that evidence, keep it.
  - Write `Closes #N` only when the change fixes what the issue reported. Otherwise write `Refs #N`, and post your findings as a comment on the issue.
  - Say that another project needs this PR only if that project is still broken without it. When reverting the PR wouldn't undo what merging it did, say so as the last sentence of the text.
  - End with one collapsed Verification block (`mergeworthy:pull-request`, step 10).
- **An issue description:** one finding, without the story of how you came across it. The title is the symptom as a user meets it. Then `### How to reproduce` with numbered steps, then the evidence, and the `file:line` last, for whoever fixes it.
- **An inline review comment:** only where a reviewer must make a judgment (a choice that could have gone the other way, something the diff can't show, a risk you hand over). At most two sentences. For a small fix, the normal outcome is no inline comment at all.
- **An image or video:** one line saying what to look at and what it proves, plus the setup (the page, a filter) when the default view doesn't show it. A PR's images open on the defect and end on the fix. Between them, they show what the change could have broken and didn't.
- **A review of someone else's PR** posts its findings, and never approves unless the user asked you to.

## Opening an issue

1. **Should it be a PR instead?** Look for the fix first. When you hit a defect and the fix is obvious, open a PR, upstream too. File an issue only when you can't find a fix, or when the fix needs the owner's product decision.
   Done: `task.md` says why it's an issue and not a PR.
2. **Is it already filed or fixed?** Run `gh issue list --state all --search "<keyword>"` and `git log --oneline origin/<base> -- <files>`. If an issue already exists, add your finding to it as a comment instead of opening a duplicate.
   Done: no duplicate, and no fix on the base branch.
3. **Reproduce it on today's base branch** from a clean start, as a user meets it. Don't file what you can't reproduce.
   Done: a screenshot, a video, or a request and response that shows it.
4. **Write the description** as `mergeworthy:writing` and Forms (above) say, with `### How to reproduce` and the evidence. An issue that asks for a decision adds `### Options`, showing what a user sees under each option, plus your recommendation.
   Done: a newcomer could reproduce it from the description alone.
5. **Post it** (Steps, above) and add it to your watch.
   Done: the posted description shows its evidence.
