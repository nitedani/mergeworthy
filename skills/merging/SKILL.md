---
name: merging
description: "Pushing, saying a PR is ready, merging, stacked PRs."
---

## 1.7 Pushing, ready and merge

- **Commit as the GitHub account you push with,** by login and noreply email: `git -c user.name=<login> -c user.email=<id>+<login>@users.noreply.github.com commit`. Never use the user's real name or another address.
- **Push safely.** Maintainers may push to your branches and may merge them.
    - Before any push: fetch; if you have unpushed commits, rebase them onto the remote branch (`git rebase origin/<branch>`) and re-run the quick gates; then check `git merge-base --is-ancestor <remote> HEAD` and push.
    - Never force-push, except on your own unmerged branch with `--force-with-lease=<branch>:<sha you last pushed>`.
    - Never push to a merged branch.
    - Push to the PR's head repository by URL (`gh pr view <N> --json headRepositoryOwner,headRefName`), never by a remote's name: `origin` is upstream in some checkouts, and a push there opens a branch in the maintainer's repo.
- **Each maintainer instruction is a checkbox for its PR.** Before saying ready and before merging, re-read the whole thread, inline comments included. Tick or do each instruction.
- **A subagent that writes a PR follows the mergeworthy skills, not a summary of them.**
    - Its prompt tells it to load the skills and names the steps it runs: `pull-request` steps 1 to 5, evidence in the real app, and the benchmark for transports.
    - Its report lists each step with its output file.
    - It does the work itself without starting agents (`delegating` 1.10), so the main session runs `converge`'s pipeline on its branch: the loops and the fresh reader need agents.
    - `pre-bash-guard` blocks a ready PR without all six `pr-steps` records (`converge`).
- **Ready** means every item of the Ready list holds on the head. Paste this list, checked against the head, into the ledger:
    - every slice dry after its last fix (a pass that finds no bug that counts, `verify`);
    - a guardian verdict on the PR's own diff at the head (a base merge alone doesn't change it);
    - every instruction checkbox ticked;
    - every `acceptance.md` claim holding on the head;
    - the PR body true of the head;
    - CI green (`gh pr checks`), or only workflow approval pending under the CI-limits exception, in which case the PR is ready for review but cannot merge;
    - the review covering the head SHA;
    - `replies-owed.md` empty for the PR;
    - for UI changes, a screenshot in the body.
- **Saying ready.** Then say once, "Ready for review" or "Ready to merge from my side", with the head SHA and the CI link. End with "Reply `merge` and I'll squash-merge it." only in repos where you can merge (the user's own), and never when the plugin's `merge` option is `reviewer`. Say ready in plain words without process terms (`writing`).
- **CI limits.** `gh run rerun` on an upstream repo needs admin rights, so ask a maintainer. Fork PRs get no CI secrets, so those jobs fail on forks. A first-time contributor's fork PR runs no workflow until a maintainer approves it: say ready with "CI waits for workflow approval" and the local gates' exit codes on the head, and tick CI once it ran.
- **Merge only after a maintainer asks:** `gh pr merge <N> --squash --delete-branch --subject "<PR title> (#<N>)" --body ""`. If the repo's `AGENTS.md` requires another form, ask the user: `pre-bash-guard` only allows this one.
- **Stacked PRs.** Before merging a PR that other open PRs are based on, retarget them (`gh pr edit <N> --base <its base>`). Deleting the merged PR's branch closes the PRs based on it instead (`pre-bash-guard` blocks `--delete-branch` while any are left). After a squash-merge, merge the new base into each of them, so their diff shows only their own change.
