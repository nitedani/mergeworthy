---
name: refactor
description: "The refactor pass on a PR's diff: the pinnacle-split-and-simplify prompt, who rates, how it's implemented and recorded, and when it goes stale."
---

# Refactor pass

Run it after `review`'s PR review round, on the diff you just wrote, with correctness proven and the gates green. The reviewer (`review`) rates it with the prompt below; with no reviewer available, run it yourself in two separate passes (rate, then edit) and record that. Mostly 10s means it was lazy. Then `pr-steps refactor <output>`. Refactor commits change the head: before ready, re-run `review`'s charter on the final head to confirm (fix real defects it finds and confirm again) and record it with `pr-steps review` (1.7).

## The prompt

Refactor this PR:

- Pinnacle architectural split
  - Does each file and each function represent a sensible abstraction that is easy to understand?
  - Rate the SEAMS, not just the boxes: for each call site, ask whether the responsibility sits
    on the right side of the boundary — should a caller's wrapper move down into the callee (or
    vice versa)? A function can be clean, DRY and well-tested in isolation yet still be in the
    wrong place. "Well-factored" is not "well-located".
  - Before starting to work: list ALL files and ALL functions in this chat, rate them all
    (0: convoluted abstraction, hard to understand, not DRY — 10: perfect), and give a reason for
    your rating.
    - DON'T skip any file nor any function — write an extra separated ✅ tick list of all files
      and functions to double-check nothing was forgotten. Two lists: ratings & explanations,
      then the ✅ coverage list.

- Simplify
  - Review ALL logic. Can implemented logic be simplified?
  - Do you see logic implemented twice? Is logic DRY?
  - Can boilerplate be removed? Frivolous indirections? Frivolous tiny functions? Can we merge
    functions to make reading code easier (jumping between functions is costly when reading code
    linearly, which is what humans do)?
  - Put yourself in the shoes of a human reader who reads everything in a linear fashion.
  - Altitude pass: for each entry-point / orchestration function, read it top-to-bottom as prose.
    Flag any line that drops the reader into lower-level mechanism (a flag, a thunk, a log verb,
    error plumbing) in the middle of what should be a high-level narrative. For each, ask: can
    that mechanism move down into the callee so the caller reads at one consistent altitude?
    Prioritize the reading path of the functions a reader hits first.
  - Before starting to work: list ALL logic in this chat, rate each (0: bad — 10: perfect) with
    reasons — 100% coverage, plus the separated ✅ tick list.

- How to scrutinize (don't rubber-stamp what's already there)
  - Code comments that justify a design ("X lives here rather than Y so that…") are claims to
    audit, not constraints to respect. For each, construct the alternative it argues against and
    compare — don't assume the documented choice is optimal.
  - For anything you rate 8 or above, do one more pass asking only: is it at the right altitude
    and on the right side of its boundary?

- Work until it's exceptionally good. We as an expert team will check against every little detail.
  - If we see mostly 10/10 ratings, that's a sign you've been lazy — scrutinize everything and
    spend a substantial amount of time. We don't want to prompt you again and again to achieve
    quality — autonomously strive for quality on your own without us pushing you.

- End with a summary of what you worked on: print the lists again with old rating ⇒ new
  rating with link to commit(s).

## Running it

The rater is not the author, and not in the author's context. It rates read-only; the author implements commit by commit; a fresh rater re-rates old ⇒ new. Scope: everything the diff touches, at 100% coverage; code outside the diff is context. Re-run the gates after every commit; a red gate means revert that commit, not patch over it. Refactor commits are separate from behavior commits. If the pass changed nothing, say that and why. The final lists (old ⇒ new, reason, commit links, and the ✅ lists) go in the review-record comment; working notes stay in the artifact root. The pass belongs to the PR as it is now, not to the head it first ran on: when later commits (maintainer requests included) change more than ~80 lines, re-run it on the whole PR diff before the next "Done" reply and replace the lists; the watcher prints `### REFACTOR STALE` when that happens.
