---
name: refactor
description: "The refactor pass on a diff: a prompt that rates how the code is split into files and functions and how it can be simplified, and the standard code is written to from its first line."
---

# Refactor

The prompt below sets the bar every diff is written to from its first line, and the diff is rated against it before the PR is ready. A rater, an agent that isn't the author, runs it and only reads the code. The author commits fixes for its findings. The same rater then rates again, until nothing worth changing is left.

## Steps

1. **Rate, without changing code:** a rater who isn't the author runs the prompt below on the whole diff, covering every file and function in it. Code outside the diff is context.
   Done: its ratings and its ✅ coverage lists are in the work folder.
2. **Commit fixes for the findings,** one at a time. Keep refactor commits separate from commits that change behavior. Run the quick checks (lint, type check, unit tests) after each commit. If a check fails, fix that commit, never with a patch on top.
   Done: one commit per finding, or per class of findings (all instances of one kind), and a reason for each finding skipped.
3. **Rate again:** the same rater rates every row again, showing old rating ⇒ new rating, with the commits. A pass that changed nothing says so, and why.
   Done: the new ratings list every row old ⇒ new, and say nothing worth changing is left.
4. **Keep it current:** once the lines added plus the lines deleted since the last full rating exceed about 80, tests and lockfiles included, run it again on the whole diff before the next "ready". Give that run a new name in the work folder, so it doesn't overwrite the last one.
   Done: the latest full rating is less than about 80 changed lines old.

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
  - Do you see logic implemented twice, in the diff or anywhere in the codebase? For each constant,
    literal or import the new code uses, grep the repo for its other uses: an existing function that
    already does this work is a reuse finding.
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
