---
name: failure
description: "When the user names a mistake or a rule visibly failed: fix the instance now, and fix the page or mechanism that let it happen."
---

## When

The user names a mistake ("why didn't you…?"), gives a 👎, or a rule visibly failed.

## Steps

1. Say in one line why it happened.
2. Fix the instance now: the post, the PR, the code.
3. Find the page whose moment failed, and fix it: a missing or wrong step, or one line in its Never section.
4. Add or extend a mechanism (a hook or a check in a script) instead, when the page's Never section would grow past four lines, or when the same failure happened twice.
5. Commit and push the fix to the mergeworthy repo in the same step; never edit an installed copy.
6. Show that the correction holds.

## Done when

The instance is fixed, the page or mechanism is fixed and pushed, and you showed it holds.

## Never

- Explain the failure and wait for a go before fixing it.
- Put the lesson only in one project's memory or one machine's config.

## Enforced by

Nothing: this is judgment.

## Next

Back to the page you came from.
