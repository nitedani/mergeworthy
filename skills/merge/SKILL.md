---
name: merge
description: "When a maintainer asks you to merge, or you are about to push to a shared branch: push safely, merge in the repo's format, and move what depends on it."
---

## When

A maintainer asks you to merge, or you are about to push to a branch others may have pushed to.

## Steps

1. Push safely: fetch, fast-forward onto other people's commits, confirm `git merge-base --is-ancestor <remote> HEAD`, then push. Force-push only your own unmerged branch, with `--force-with-lease=<branch>:<sha you last pushed>`.
2. Commit as the account you push with, using its noreply address.
3. Merge only after a maintainer asks, and only if the plugin's `merge` option is `on-request-squash`. Re-read the repo's `AGENTS.md` on the target branch right before merging.
4. Squash-merge in the repo's format, by default `gh pr merge <N> --squash --subject "<title> (#<N>)" --body ""`.
5. Retarget every open PR based on this one to its base before merging (`gh pr edit <N> --base <base>`), then merge the new base into each of them after.
6. Apply in the same step what waited on this merge (`waiting-on.txt`), and update the umbrella issue if there is one.

## Done when

The PR is merged, nothing that depended on it is closed or stale, and the umbrella issue shows the new state.

## Never

- Merge without being asked.
- Delete a branch other open PRs are based on.
- Push to a merged branch.

## Enforced by

`pre-bash-guard` (blocks a merge in any other format, every merge when the `merge` option is `reviewer`, `--delete-branch` while PRs are based on it, and a force-push without `--force-with-lease=<branch>:<sha>`).

## Next

`mergeworthy:github-event` for what the merge unblocks.
