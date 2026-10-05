---
name: pr
description: "When you are about to open a PR: the shape that gets merged, the body, and the records the ready check needs."
---

## When

You are about to run `gh pr create`.

## Steps

1. Look at the maintainer's recent merged PRs: what they keep, what they cut, how they title and describe them.
2. Keep it to one purpose and small. Each user-visible fix is its own PR; internal cleanups go together in one.
3. Remove every feature in the diff that no current need asks for, and every comment, guard or test the repo's habits wouldn't keep.
4. Ask the questions `mergeworthy:ready` lists for the task's size, `review` last so it sees the final head; record them with `pr-steps read <read output>` and `pr-steps review <review output>`.
5. Write the body through `mergeworthy:post`:
   - **First sentence:** the problem a user hits on today's base branch.
   - **Link:** `Closes #N` only if the change fixes what the issue reports; otherwise `Refs #N`.
   - **What you should see:** a numbered sequence of screenshots or a recording, captured per `mergeworthy:change` step 7, that opens on the defect and closes on the fix, one line each on what it proves.
   - **Notes:** the notes table, if there are any.
6. Add an inline review comment only where a reviewer must judge something the diff can't show.
7. Open it ready, not as a draft.

## Done when

The PR is open, its body is true of the head, and it is in the watcher's `threads.txt`.

## Never

- Add an option or a feature nobody asked for.
- List a follow-up instead of opening it now.
- Let the body go stale: re-check it after every push.

## Enforced by

`pr-steps` (blocks `gh pr create` and `gh pr ready` without the read and review records), `post-bash-register` (puts the new PR on the watcher's list).

## Next

`mergeworthy:ready` before calling it ready.
