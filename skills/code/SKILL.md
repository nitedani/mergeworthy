---
name: code
description: "The standard for code: what good code, tests, code comments and module designs look like. Read it before you write any of them; an agent gets its path in its brief; every checker of code uses it as its checklist. The repo's own ways, writing it, deep modules, the twelve lenses, mechanisms and who decides, edge cases and related cases, tests, comments, the self-check, and the refactor prompt."
---

# Code

This file says what good code looks like. Quality is made while writing, so you read this file before you write code, tests, a code comment or a module design, and you write to it from the first line. The checks that come later use this same file as their checklist: the bug hunt, the quality review and the final review in `mergeworthy:converge`, and any review from `mergeworthy:review`. When the writing met this file, they find nothing.

When you hand the writing or the checking of code to an agent, its brief names this file by its absolute path, because the agent may not have this plugin's skills loaded (`mergeworthy:delegating`, step 2). The Skill tool's message that loads this skill shows its base directory, and the file is `SKILL.md` in it. A checker's finding names the section of this file it breaks. A real finding that no line here covers gets that line added here, never to a checker's brief (`mergeworthy:task`, When a rule fails).

A lane, in this file, is one of the repo's test suites that runs the product in a real setup: production-mode end-to-end tests, a specific adapter, transport or runtime, the examples. The lane that owns a piece of code is the one that exercises it for real.

## Steps

1. **Learn the repo's own ways first.** The repo's `AGENTS.md` / `CLAUDE.md`, your notes on the project in `~/.mergeworthy/projects/<owner>/<repo>.md`, and three files next to the change show how code is written there. In a PR, `mergeworthy:pull-request` step 4 writes these conventions into `task.md`. An agent gets them in its brief.
   Done: you can name the conventions this code must follow: typing patterns, naming, JSDoc tags, test helpers, how many comments.
2. **Write to the sections below:** Writing it, Deep modules, Mechanisms and who decides, Edges and related cases, Tests, and Comments. Read the lenses before you start too, because they are what the quality review will look for.
   Done: every section holds for the code as you wrote it.
3. **Check your own diff** as The self-check (below) says, and fix what it finds before you call the code done or hand it back.
   Done: the self-check finds nothing worth changing. An agent's final message says what its self-check found and what it changed.

## Writing it

- **Fix at the root, and never make anything worse.** If something works on `main` and fails on your branch, that is a regression for you to fix, not a limitation to mention.
- **Make the smallest diff that finishes the job:** every call site, every translation. A new dependency joins an open PR only after the maintainer agrees.
- **A silent fallback, a retry or reload loop, parsing something twice, or a second code path for old runtimes** needs the user's OK, plus a written reason why fixing the root cause is impossible. Errors from misuse stay visible. Code that is unreleased or before 1.0 gets no compatibility layer for old versions. Check with `npm view <pkg> versions`, which lists the published versions.
- **Check every new public name with one line:** the name, then what it does in every case. Add an option only for a named user scenario that nothing else serves.
- **Before changing a mechanism** (a hook, a scheduler, a lifecycle), write down how it starts and what running and finished look like. Before removing or moving code, list what depends on it, and run `git log -S <name>` to find the commits that added or removed that name. After a rename, search the repo and the open PRs for the old name.
- **Build the whole interaction,** not only the path where everything goes right.
- **Make it elegant:** the simplest shape that is obviously right. Each file reads from top to bottom, with each caller above the functions it calls, and one level of abstraction per function. Prefer modules that hide a lot behind a small interface (Deep modules, below). No special cases. No wrappers or tiny functions that add nothing. Where logic is really a lookup, write it as a table of data. Write to the standard of the refactor prompt (the last section of this file) from the first line, so that its rating finds nothing.

## Deep modules

A module (a function, a class, a package, a part of a system) is deep when a lot of behavior sits behind a small interface. The interface is everything a caller must know to use it: its types, the rules it relies on, the order of calls, how it fails, and its configuration.
- **The deletion test:** imagine deleting the module. If the complexity disappears with it, the module only passed calls through. If the complexity comes back in every caller, the module earns its place.
- **Test through the interface.** If a test has to reach past the interface, the module has the wrong shape. When you make a module deeper, test each of its dependencies according to what it is: code in the same process, a local stand-in for a service, your own remote service, or a true third-party service. Tests written against the new interface replace the old tests of the shallow parts.
- **Add a seam (a point where one implementation can be swapped for another) only for variation that exists today,** or for a named dependency that is known to change. Never add one for a second user who might come one day.
- **Take dependencies as arguments rather than creating them inside, and return results rather than causing side effects.**

## The lenses

The quality review in `mergeworthy:converge` step 3 looks at the code through each of these lenses, on every pass. Write with them in mind, so it finds nothing.

1. **Bloat:** dead code; API surface nobody uses yet; two pieces of code for the same purpose; defensive branches for states that can't happen (turn them into assertions); custom test scripts (delete them).
2. **Code quality:** rate every file, function and piece of logic, and tick off the coverage list (the refactor prompt, the last section of this file).
3. **Other ways to solve it:** list every flow, rate each from 0 to 10 on how good its solution is, and sketch better alternatives for low scores.
4. **File placement:** each file sits where the repo's existing structure would put it.
5. **The mechanism census.** For every mechanism that corrects or guards against something (a retry, a guard, a deduplication, a fallback), write down:
   - where it came from, from `git blame` (one added during a round of fixes is presumed to be accumulated clutter);
   - the user-visible scenario it serves, or NO NAMED SCENARIO;
   - one sentence on the promise it enforces;
   - the evidence for that promise in the docs or types;
   - an honest, weaker alternative;
   - a verdict: GENUINE, OVERBUILT or SUSPECTED-PHANTOM (guarding against something no real usage causes), with the lines removing it would save.

   Before deleting one, run the probe (Mechanisms and who decides, below).
6. **Essential against accidental complexity:** keep complexity that comes from a hard problem (only suggest making it easier to read). Cut complexity that comes from making the solution more general than it needs to be.
7. **Invisible optimizations:** cut machinery that only matters at a scale nobody runs. Report, but don't cut, optimizations whose removal would really hurt.
8. **No surface added only to inspect internals or to make noise** (debug APIs, extra logging).
9. **Deep modules:** find modules whose interface is nearly as complex as what they do, and boundaries in the wrong place (Deep modules, above).
10. **Fowler's code smells** (from *Refactoring*): Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man, Refused Bequest.
11. **The 10-second pass:** what makes a reader wince at first sight:
    - names that admit to mixing responsibilities;
    - functions that read but also write;
    - renamed imports (rename the original symbol instead);
    - boolean flags that switch what a function does;
    - long runs of positional parameters;
    - ternaries with side effects.

    Fix these as classes: one commit fixes every instance of one kind.
12. **The weight of tests and comments:** price each of these like bloat in code, and decide what happens to it:
    - redundant tests (several tests proving exactly the same behavior);
    - permanent tests beyond the repo's habit and beyond the limit per capability (Tests, below);
    - test harnesses and scaffolding that should have been throwaway probes;
    - comments that narrate, justify or record history, and walls of JSDoc.

    Never remove a test that checks a documented contract holds, or a regression test for a named counterexample.

## Mechanisms and who decides

- **No phantom fixes.** A phantom fix guards against a problem that no real usage can cause. Every mechanism you add (a guard, a retry, a fallback) needs a documented scenario that reaches it, traced from where the user starts to where the code fails. "It could break" is not a scenario. With no scenario, delete the mechanism. A fix never changes a behavior someone chose on purpose. It goes at the call site, not into a changed default that other code depends on.
- **No removal without a probe.** A probe is a run that could fail. Before you remove a guard, a deduplication, a retry or a cache, try to make the symptom it prevents happen, in the lane that owns that code. If the symptom appears, keep it.
- **Code the owner wrote** is never removed or rewritten because an agent read it that way. Code the owner wrote is a commit by a human, or a commit without the trailer line that the environment adds to an agent's commits. Send such a finding to the owner, with a recommendation. In the user's own repo, the user is the owner, so the finding goes to them and they decide.
- **The docs are the contract.** When code and docs disagree, suspect the code. Each sentence of docs the diff adds is a claim that the bug hunt (`mergeworthy:converge`, step 2) reproduces.
- **Every feature has a user.** Before the PR is ready, list each feature with non-trivial code, next to the link that shows someone needs it today. Remove the rest.
- **Behavior and public API** in someone else's repo are for the maintainer to decide. Ask before changing them, and keep refactors from changing behavior. In the user's own repo, you decide the changes the task needs.
- **Wrong data returned silently is never a minor finding.**

## Edges and related cases

- **Read each change from start to end, with every caller.**
- **Try the risky edge cases** of the code you write or check. For code that handles streams, always try these: cancellation from either side, backpressure, a size limit on every buffer, listeners and timers released on every exit path, the same stream read twice without a copy, and a slow consumer of more than 1 GiB.
- **Try the related cases.** When the change handles one case of a mechanism (one method, status code, adapter or runtime), try the same failure in the other cases. `mergeworthy:pull-request` step 3 says where each related case goes. Never drop one.

## Tests

- **Tests follow the repo's habit.** Where the maintainer keeps regression tests, keep them. Where they remove tests that only proved a PR worked, remove yours in a final commit once the PR is approved.
- **Add at most one permanent end-to-end assertion per new capability.**
- **Tests wait for events, never for a fixed time.** Expected values come from outside the code under test.
- **A test proves something only when it fails without the change.** Revert the fix, see the test fail, then restore the fix.
- **When you remove, merge or move a test or a guard,** break the production line it protects, and check that a remaining test fails. Record this probe.

## Comments

None by default. A comment is one literally true line about a constraint the code can't show. Never history or comparison with old code ("now", "no longer", "instead of", "previously"), never a restatement of the code, never a link to source, never a JSDoc wall. Names follow their siblings. `mw diff-lint` (run in `mergeworthy:pull-request` step 6) warns about added comments longer than one line and comments about history.

## The self-check

Run it on your own diff before you call the code done or hand it back. It is the pass the quality review will make, so what it finds now, the review won't.
1. Look at every file and function you changed through each lens above.
2. Rate your diff with the refactor prompt below, as the rater in the quality review would.
3. Check the diff against Mechanisms and who decides, Edges and related cases, and Tests: each mechanism you added has its scenario, each related case was tried, and each new test fails without the change.
4. Ask yourself, as this repo's maintainer: would you merge this exactly as it is?

Fix what you find, then run the self-check again on what changed.

## The refactor prompt

The prompt below sets the bar every diff is written to from its first line. Before a PR is ready, a rater, an agent that isn't the author, runs it on the whole diff and only reads the code (`mergeworthy:converge`, step 3).

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
