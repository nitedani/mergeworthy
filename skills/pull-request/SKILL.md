---
name: pull-request
description: "Any change that goes into a PR, from an issue or not: is it already fixed?, reproduce it, the root cause and related cases, the repo's style, building it, seeing it work, marking it ready, merging, pushing, and stacked PRs."
---

# Pull request

A change becomes a small PR that its maintainer merges as it is, without asking for anything. Write it in the repo's own style from the first line. Small fixes with one cause, a regression test where the repo keeps them, and a before/after table get merged without discussion. Steps 3–7 are where the quality is made. The converge steps afterwards (step 9) only confirm it. How code is written in the repo is set by its `AGENTS.md` / `CLAUDE.md`, and by your notes on the project in `~/.mergeworthy/projects/<owner>/<repo>.md` (its checks, its conventions, what maintainers changed after earlier PRs).

## Steps

1. **Check it isn't already fixed.**
   - `git log --oneline origin/<base> -- <files>`
   - `gh pr list --state all --search "<keyword>"`
   - the issue's comments and assignees.

   A hit isn't proof: confirm the behavior in today's code.
   Done: no fix on `main` and no open PR. If one exists, you posted a comment with the commit and the `file:line`, and you stop.
2. **Reproduce it on `main`** as a user meets it (`mergeworthy:evidence`). For UI, in the running app. For a backend, with the request and response. Otherwise, with one fast command that fails because of the symptom. For a feature, capture how things are now. Claim the issue (`gh issue edit <N> --add-assignee @me`, where you have triage rights), and comment the reproduction on it. If it doesn't reproduce, comment what you tried.
   Done: a command, screenshot or video in the work folder shows the symptom on `main`.
3. **Find the root cause, and every related case.** Check whether the same failure happens in the other cases of the same mechanism: each adapter, method, status code, runtime.
   - A related case that fails the same way in the same files is part of this fix.
   - A related case elsewhere with a clear fix gets its own PR, opened now.
   - A related case whose fix needs the owner's decision gets an issue (`mergeworthy:posting`, Opening an issue).

   Come up with two or three approaches, including not building it at all. Rate each from 0 to 10, as the code's owner would for all its users. If none reaches 7, don't build any: comment what you tried, and ask the product question hidden in the issue. Before a PR to an upstream project, find which side relies on behavior that the other side doesn't promise, and fix that side first, even when it's our code. A security fix or bug fix closes only the hole. A change to what a legitimate user sees or can do gets its own issue that asks for a decision, with options.
   Done: `task.md` names the cause, the layer of the code responsible for it, each related case and what happens to it, and each approach with its rating and the one chosen. Or, when none reaches 7, the link to the comment that asks the product question.
4. **Learn the repo's ways before writing:**
   - read three files next to the change;
   - read the maintainer's last merged PRs: what they keep and what they cut;
   - read the project notes: the repo's checks, what already guarantees things (validators, types that rule out invalid values, authorization layers), and the parts that matter for security. If a section is missing, write it once from CI, the README and the code;
   - run `mw followups <owner/repo>`. It lists the commits other people made, after the merge, to the files of your PRs merged in the last 14 days. Add what each teaches to the project notes, one line each, with the link. If a follow-up shows a mistake your steps should have caught, fix the mergeworthy rule instead (`mergeworthy:task`, When a rule fails).

   Search the code for something that already does the work, and search other PRs, open and merged, for a check that already exists. Reuse it. If it needs a fix before you can reuse it, that fix is part of this PR.
   Done: `task.md` lists the conventions this diff must follow (typing patterns, naming, JSDoc tags, test helpers, how many comments).
5. **Write it** in a worktree based on the target repo's base branch, never a fork's: `git worktree add -b <branch> <work folder>/<branch> origin/<base>`.
   - Make the smallest diff that finishes the job: every call site, every translation. A new dependency joins an open PR only after the maintainer agrees.
   - A silent fallback, a retry or reload loop, parsing something twice, or a second code path for old runtimes needs the user's OK, plus a written reason why fixing the root cause is impossible. Errors from misuse stay visible. Code that is unreleased or before 1.0 gets no compatibility layer for old versions (check with `npm view <pkg> versions`).
   - Check every new public name with one line: the name, then what it does in every case. Add an option only for a named user scenario that nothing else serves.
   - Before changing a mechanism (a hook, a scheduler, a lifecycle), write down how it starts and what running and finished look like. Before removing or moving code, list what depends on it, and run `git log -S <name>`. After a rename, search the repo and the open PRs for the old name.
   - Build the whole interaction, not only the path where everything goes right.
   - Make it elegant: the simplest shape that is obviously right. Each file reads from top to bottom, with each caller above the functions it calls, and one level of abstraction per function. Prefer modules that hide a lot behind a small interface (`mergeworthy:design`, Deep modules). No special cases. No wrappers or tiny functions that add nothing. Where logic is really a lookup, write it as a table of data. Write to the standard of the refactor prompt (`mergeworthy:refactor`) from the first line, so its review finds nothing.
   - Code comments follow `mergeworthy:writing`: none by default.
   - Tests follow the repo's habit. Where the maintainer keeps regression tests, keep them. Where they remove tests that only proved a PR worked, remove yours in a final commit once the PR is approved. Add at most one permanent end-to-end assertion per new capability. Tests wait for events, never for a fixed time. Expected values come from outside the code under test.
   - Docs follow `mergeworthy:writing`, Docs.

   Done: reading your own diff with the refactor prompt finds nothing worth changing, and the diff follows every convention from step 4.
6. **Run the checks:** every check the repo's CI runs, read from its workflow files, plus `mw diff-lint`. `mw diff-lint` warns about added comments longer than one line, comments about history, and timed waits added to tests. Run servers and end-to-end tests under `mw netns` (a private network, `mergeworthy:task`, The machine). A check passes only when it exits 0. A check that errors or can't run counts as failed. A failure that doesn't happen again is still a finding.
   Done: every check exits 0, and each `mw diff-lint` warning is fixed or answered in one line in the log of the checks you ran.
7. **See it work as a user meets it** (`mergeworthy:evidence`):
   - capture "before" by reverting only your files (`git checkout origin/<base> -- <files>`, then `git checkout HEAD -- <files>` to get them back);
   - use it as a person would for five minutes, around the change and not only along the fixed path. When the browser must reach a server, run it under `mw netns --publish <port> -- <cmd>`, which prints the URL to open;
   - for UI, check each changed page at phone, tablet and desktop widths, in light and dark mode, with hover, focus and open states. Compare it with the other projects you studied (`mergeworthy:task` step 3). Any error in the browser console is a failure. Show the whole page at the real screen size with real data, or a video when it takes more than one click. Before anyone sees new UI, a fresh reviewer (never you) judges the whole-page screenshot for hierarchy and clutter. For a change in how pages load, record from the navigation until the page is settled, and count every element that pops in late and every layout shift;
   - for a backend, show the request and response, on `main` and on your branch.

   Done: the before and after evidence is in the work folder. Anything else you ran into has a PR or an issue.
8. **Open a draft PR** with the first push: `gh pr create --draft`, run through `mw post` (`mergeworthy:posting`), with the description as `mergeworthy:posting` (Forms) says. Then add the PR to your `mw watch` (`mergeworthy:github`). If the PR replaces another, close that one, with a link, in the same step.
   Done: the draft PR exists, and the watch is running.
9. **Converge the latest commit** (`mergeworthy:converge`). Converging means running the checks, a bug hunt, a quality review and a final review on the PR's latest commit. Each of these steps is recorded with `mw step`.
   Done: `mw steps --pr <url>` shows every step recorded for the commit you pushed.
10. **Finish the description:** add one collapsed `<details><summary>Verification</summary>` block, with one line per converge step: what ran on `<head sha>` and what came of it. When the change has more than about 300 lines of feature code (not counting tests, docs and lockfiles), add the table of lines per feature. To make it, write a map file of `<glob> = <feature>` lines, naming features in the maintainer's words, and paste the output of `mw loc origin/<base> --map <file>`. Post the edit through `mw post`.
    Done: the description is true of the latest commit, and its review is `CLEAN`.
11. **Mark it ready:** `gh pr ready <N>`. mergeworthy's hook stops this command when a converge step isn't recorded for the latest commit. First, re-read the whole thread, inline comments included. Every maintainer instruction is done, and each point of an accepted proposal in `task.md` holds on the latest commit. CI passes. Then say once, in plain words, "Ready for review", with the commit SHA.
    Done: the PR is marked ready, and you said so once.
12. **Stay on it until it's merged** (`mergeworthy:github`). Handle every review, failing CI run, merge conflict, push by someone else, and dependency that lands. When the PR's own diff changes, run again the converge steps that the change affects. While they run, turn the PR back into a draft (`gh pr ready --undo <N>`). Never close a PR that fixes a real bug.
    Done: the PR is merged or closed.
13. **Merge only when the user or the maintainer explicitly asks,** in the repo's own way of merging (its `AGENTS.md`, or `gh pr merge <N> --squash --delete-branch --subject "<title> (#<N>)" --body ""`). First change the base of every PR built on this one's branch to this PR's base (`gh pr edit <M> --base <its base>`). After the merge, merge the new base into each of them.
    Done: merged, and every dependent PR targets the new base and shows only its own diff.

## Pushing and stacked PRs

- **Commit identity:** commit as the GitHub account you push with: `git -c user.name=<login> -c user.email=<id>+<login>@users.noreply.github.com commit`, with the trailer the environment gives you. Stage files by name.
- **Before a push:** fetch, and rebase your unpushed commits onto the remote branch, because maintainers push to your branches too. Push to the PR's head repository by URL (find it with `gh pr view <N> --json headRepositoryOwner,headRefName`), never by a remote's name. Force-push only to your own unmerged branch, and only with `--force-with-lease=<branch>:<sha you last pushed>`. Never push to a branch that's already merged.
- **Stacked PRs** (a PR whose base is another PR's branch): use them only when the feature needs fixes to the base that build on their own on `main`, and the `gh stack` extension can link the PRs. The bottom PR holds the base fixes, one bug per commit. The top PR holds the feature, and takes the bottom's changes through merge commits, never a rebase. After each merge of the bottom into the top, check that every test name from the bottom still exists in the top, and that the top's diff shows only feature lines.
- **Every defect you find gets a PR, an issue, or a fix in this PR.** Only mentioning it doesn't count. An item under about 20 lines that users can't see and that isn't a defect on `main` goes into this PR. "Later" is never a reason.
