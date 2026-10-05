---
name: merging
description: "Pushing, saying a PR is ready, merging, stacked PRs."
---

## 1.7 Pushing, ready and merge

- Commit as the GitHub account you push with, by login and noreply email (`git -c user.name=<login> -c user.email=<id>+<login>@users.noreply.github.com commit`), never the user's real name or another address. Maintainers may push to your branches and may merge. Before any push: fetch, fast-forward onto their commits, check `git merge-base --is-ancestor <remote> HEAD`, then push. Never force-push, except on your own unmerged branch with `--force-with-lease=<branch>:<sha you last pushed>`; never push to a merged branch.
- Each maintainer instruction is a checkbox for its PR. Before saying ready and before merging, re-read the whole thread, inline comments included, and tick or do each one.
- **A subagent that writes a PR follows the mergeworthy skills, not a summary of them.** Its prompt tells it to load them and names the steps it runs (`review`'s PR review round per `review`, the refactor pass, `guardian`'s verdict, evidence in the real app, the benchmark for transports); its report lists each step with its output file. It starts no agents of its own: a step that needs one (a fallback reviewer, mappers) goes back in its report, and the main session runs it. The `pr-steps` hook blocks a ready PR without the review and refactor records.
- **Ready** means every item below holds (`ready-check`): every slice dry after its last fix, a guardian verdict covering the head, every instruction box ticked, every `acceptance.md` claim holding on the head, the body true of the head, CI green, the review covering the head SHA, `replies-owed.md` empty for the PR, and a screenshot in the body for UI changes. Then say once, "Ready for review" or "Ready to merge from my side", with the head SHA and the CI link, and end with "Reply `merge` and I'll squash-merge it." The checklist output stays in the ledger; "converged" and "dry" never appear in the thread.
- CI: `gh run rerun` on an upstream repo needs admin rights, so ask a maintainer; fork PRs get no CI secrets (e.g. a Vercel token), so those jobs fail on forks.
- Merge only after a maintainer asks: `gh pr merge <N> --squash --subject "<PR title> (#<N>)" --body ""`, unless the repo's `AGENTS.md`, re-read right before merging, says otherwise.
- Before merging a PR that other open PRs are based on, retarget them (`gh pr edit <N> --base <its base>`): deleting its branch closes them instead (`pre-bash-guard` blocks `--delete-branch` while any are left). After a squash-merge, merge the new base into each of them, so their diff shows only their own change.
