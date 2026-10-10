---
name: pull-request
description: "Any change that lands in a PR, from an issue or not: already fixed?, reproduce, root cause and siblings, the house style, building, seeing it work, ready, merging, pushing and stacks."
---

# Pull request

A change becomes a small PR that its maintainer merges as it is, without asking for anything. Write it in the house style from the first line. Small fixes with one cause, a regression test where the repo keeps them, and a before/after table merge without a word. Quality is made in steps 3–7; the converge steps confirm it. The repo's `AGENTS.md` / `CLAUDE.md` and the project notes in `~/.mergeworthy/projects/<owner>/<repo>.md` govern how the code is written there.

## Steps

1. **Check it isn't already fixed.**
   - `git log --oneline origin/<base> -- <files>`
   - `gh pr list --state all --search "<keyword>"`
   - the issue's comments and assignees.

   A hit isn't proof: confirm the behavior in today's code.
   Done: no fix on `main` and no open PR; or, if one exists, a comment with the commit and `file:line`, and you stop.
2. **Reproduce it on `main`** as a user meets it (`evidence`): in the running app for UI, with the request and response for a backend, otherwise with one fast command that goes red on the symptom. For a feature, capture the current state. Claim the issue (`gh issue edit <N> --add-assignee @me` where you have triage rights) and comment the reproduction on it, or what you tried when it doesn't reproduce.
   Done: a command, screenshot or video in the work folder that shows the symptom on `main`.
3. **Find the root cause and every sibling case.** Check the same failure in the mechanism's other cases: each adapter, method, status, runtime.
   - A sibling that fails the same way in the same files is part of this fix.
   - A sibling elsewhere with a clear fix gets its own PR, opened now.
   - A sibling whose fix needs the owner's decision gets an issue (`posting`, Opening an issue).

   Generate two or three approaches, "not building it" included, and rate each 0–10 as the code's owner for all its users; if none reaches 7, don't build: comment what you tried, and ask the product question hiding in the issue. Before an upstream PR, find which side relies on behavior the other side doesn't promise, and fix that side first, ours included. A security or bug fix closes only the hole; a change to what a legitimate user sees or can do gets its own decision issue with options.
   Done: `task.md` names the cause, the layer that owns it, each sibling with its disposition, and each approach with its rating and the one chosen; or, when none reaches 7, the link to the comment that asks the product question.
4. **Read the house before writing:**
   - three files next to the change;
   - the maintainer's last merged PRs (what they keep and what they cut);
   - the project notes: the repo's gates, what already guarantees things (validators, type shields, authorizers) and its security surfaces. Write a missing section once from CI, the README and the code;
   - `mw followups <owner/repo>`, the commits maintainers made after our merged PRs. Add what they teach to the project notes, one line each, with the link. A follow-up that shows a miss your steps should have caught fixes the mergeworthy rule instead (`task`, When a rule fails).

   Grep for what already does the work, and search sibling PRs, open and merged, for a check that already exists: reuse it, and a fix it needs to be reused is part of this PR.
   Done: `task.md` lists the conventions this diff must follow (typing patterns, naming, JSDoc tags, test helpers, comment density).
5. **Write it** in a worktree off the target repo's base, never a fork's (`git worktree add -b <branch> <work folder>/<branch> origin/<base>`):
   - The smallest diff that finishes the job: every call site, every locale. A new dependency joins an open PR only after the maintainer agrees.
   - A silent fallback, a retry or reload loop, parsing twice or a second path for old runtimes needs the user's OK and a written reason the root fix is impossible; usage errors stay visible. Unreleased or pre-1.0 code gets no compatibility shims (`npm view <pkg> versions`).
   - Check every new public name with one line, name → what it does in every case, and add an option only for a named user scenario nothing else serves.
   - Before changing a mechanism (a hook, a scheduler, a lifecycle), write how it starts and what running and finished look like; before removing or moving code, list what depends on it and run `git log -S <name>`; after a rename, grep the repo and open PRs for the old name.
   - Build the whole interaction, not only the happy path.
   - Elegant: the simplest shape that is obviously right. Each file reads top to bottom, caller above callee, one level of abstraction per function. Deep modules, no special cases, no frivolous wrappers or tiny functions, data where the logic is a table. Write it to the refactor prompt's standard (`refactor`) from the first line, so its pass finds nothing.
   - Comments per `writing`: none by default.
   - Tests follow the repo's habit: where the maintainer keeps regression tests, keep them; where they remove PR-proving tests, remove them in a final commit once approved. At most one permanent e2e assertion per new capability. Tests wait on events, never on sleeps or timeouts. Expected values come from outside the implementation.
   - Docs are written per `writing`, Docs.

   Done: reading your own diff with the refactor prompt finds nothing worth changing, and it follows every convention from step 4.
6. **Run the gates:** every check the repo's CI workflows run, read from the workflow files, plus `mw diff-lint`. Run servers and e2e under `mw netns`. The exit code is the verdict, and a gate that errors or can't run is red. A failure that doesn't repeat is still a finding.
   Done: every gate exits 0, and each `mw diff-lint` warning is fixed or answered in one line in the gates log.
7. **See it work as a user meets it** (`evidence`):
   - capture "before" by reverting only your files (`git checkout origin/<base> -- <files>`, then `git checkout HEAD -- <files>`);
   - use it as a person would for five minutes, around the change and not only the fixed path. A server the browser must reach runs under `mw netns --publish <port> -- <cmd>`, which prints the host URL;
   - for UI, check each touched page at phone, tablet and desktop widths, light and dark, with hover, focus and open states, and compare it against the references from `task` step 3. Any console error fails. Show the whole page at the real viewport with real data, or a video when it takes more than one click. Before anyone sees new UI, a fresh reviewer, never you, judges the whole-page screenshot for hierarchy and noise; for a change in how pages load, record from navigation to settled and count every pop-in and shift;
   - for a backend, show the request and response, `main` against the head.

   Done: the before and after evidence is in the work folder, and anything else you tripped over has a PR or an issue.
8. **Open a draft PR** with the first push: `gh pr create --draft` through `mw post`, the body per `posting` (Forms). Then arm `mw watch <PR url>` (`github`). A PR that replaces another closes it, with a link, in the same step.
   Done: the draft PR exists and the watch runs.
9. **Converge the head** (`converge`).
   Done: `mw steps --pr <url>` shows every step holding on the head you pushed.
10. **Finish the body:** add one collapsed `<details><summary>Verification</summary>` block, one line per converge step: what ran on `<head sha>` and what came of it. Changes over ~300 lines of feature code (tests, docs and lockfiles excluded) also carry the lines-per-feature table: write a map file of `<glob> = <feature>` lines, in the maintainer's words, and paste the output of `mw loc origin/<base> --map <file>`. Post the edit through `mw post`.
    Done: the body is true of the head, and its review is `CLEAN`.
11. **Say ready:** `gh pr ready <N>`. Re-read the whole thread first, inline comments included: every maintainer instruction is done, and each claim of an accepted proposal in `task.md` holds on the head. CI is green. Then say once, in plain words, "Ready for review" with the head SHA.
    Done: the PR is ready, and you said so once.
12. **Stay on it until it's merged** (`github`, the live loop): every review, red CI, conflict, push and landed dependency gets handled. A change to the PR's own diff re-opens the converge steps it touches. While they re-run, the PR goes back to draft (`gh pr ready --undo <N>`). Never close a PR that fixes a real bug.
    Done: the PR is merged or closed.
13. **Merge only on an explicit ask** from the user or the maintainer, in the repo's own merge form (its `AGENTS.md`, or `gh pr merge <N> --squash --delete-branch --subject "<title> (#<N>)" --body ""`). Retarget the PRs based on its branch first (`gh pr edit <M> --base <its base>`), then merge the new base into each.
    Done: merged, and every dependent PR is retargeted and shows only its own diff.

## Pushing and stacks

- **Commit identity:** commit as the GitHub account you push with, `git -c user.name=<login> -c user.email=<id>+<login>@users.noreply.github.com commit`, with the trailer the environment gives you. Stage files by name.
- **Before a push:** fetch, and rebase your unpushed commits onto the remote branch, because maintainers push to your branches too. Push to the PR's head repository by URL (`gh pr view <N> --json headRepositoryOwner,headRefName`), never by a remote's name. Force only on your own unmerged branch, with `--force-with-lease=<branch>:<sha you last pushed>`. Never push to a merged branch.
- **Stacks:** use them only when the feature needs base fixes that build alone on `main` and `gh stack` can link the PRs. The bottom PR holds the base fixes, one bug per commit; the top PR holds the feature, through merge commits, never a rebase. After each merge of the bottom into the top, check that every test name of the bottom still exists in the top and that the top's diff shows only feature lines.
- **Every found defect gets a PR, an issue, or a fix in this one.** "Mentioned" is not a disposition. An item under ~20 lines that is neither user-visible nor a defect on `main` goes in this PR, and "later" is never a reason.
