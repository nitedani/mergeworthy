---
name: pull-request
description: "Any change that lands in a PR, from an issue or not: already fixed?, reproduce, root cause and siblings, the house style, building, seeing it in the app, converging every head, ready, merging, stacks. Holds the verifier brief, the guardian charter, the implementer brief and the refactor prompt."
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
2. **Reproduce it on `main`** as a user meets it (Evidence, below): in the running app for UI, with the request and response for a backend, otherwise with one fast command that goes red on the symptom. For a feature, capture the current state.
   Done: a command, screenshot or video in the work folder that shows the symptom on `main`.
3. **Find the root cause and every sibling case.** Check the same failure in the mechanism's other cases: each adapter, method, status, runtime.
   - A sibling that fails the same way in the same files is part of this fix.
   - A sibling elsewhere with a clear fix gets its own PR, opened now.
   - A sibling whose fix needs the owner's decision gets an issue (`github`, Opening an issue).

   Generate two or three approaches, "not building it" included, before choosing. When the fix belongs upstream, fix it there first.
   Done: `task.md` names the cause, the layer that owns it, and each sibling with its disposition.
4. **Read the house before writing:**
   - three files next to the change;
   - the maintainer's last merged PRs (what they keep and what they cut);
   - the project notes;
   - `mw followups <owner/repo>`, the commits maintainers made after our merged PRs. Add what they teach to the project notes, one line each, with the link.

   Grep for what already does the work: reuse it, and a fix it needs to be reused is part of this PR.
   Done: `task.md` lists the conventions this diff must follow (typing patterns, naming, JSDoc tags, test helpers, comment density).
5. **Write it** in a worktree off the target repo's base, never a fork's (`git worktree add -b <branch> <work folder>/<branch> origin/<base>`):
   - The smallest diff that finishes the job: every call site, every locale.
   - Build the whole interaction, not only the happy path.
   - Elegant: the simplest shape that is obviously right. Each file reads top to bottom, caller above callee, one level of abstraction per function. Deep modules, no special cases, no frivolous wrappers or tiny functions, data where the logic is a table. Write it to the refactor prompt's standard (Appendix D) from the first line, so its pass finds nothing.
   - Comments per `writing`: none by default.
   - Tests follow the repo's habit: where the maintainer keeps regression tests, keep them; where they remove PR-proving tests, remove them in a final commit once approved. At most one permanent e2e assertion per new capability. Tests wait on events, never on sleeps or timeouts. Expected values come from outside the implementation.
   - Docs are written per `writing`, Docs.

   Done: reading your own diff with the refactor prompt finds nothing worth changing, and it follows every convention from step 4.
6. **Run the gates:** every check the repo's CI workflows run, read from the workflow files, plus `mw diff-lint`. Run servers and e2e under `mw netns`. The exit code is the verdict. A failure that doesn't repeat is still a finding.
   Done: every gate exits 0, and each `mw diff-lint` warning is fixed or answered in one line in the gates log.
7. **See it work as a user meets it** (Evidence, below):
   - capture "before" by reverting only your files (`git checkout origin/<base> -- <files>`, then `git checkout HEAD -- <files>`);
   - use it as a person would for five minutes, around the change and not only the fixed path. A server the browser must reach runs under `mw netns --publish <port> -- <cmd>`, which prints the host URL;
   - for UI, check each touched page at phone, tablet and desktop widths, light and dark, with hover, focus and open states, and compare it against the references from `work` step 3. Any console error fails. Show the whole page at the real viewport with real data, or a video when it takes more than one click;
   - for a backend, show the request and response, `main` against the head.

   Done: the before and after evidence is in the work folder, and anything else you tripped over has a PR or an issue.
8. **Open a draft PR** with the first push: `gh pr create --draft` through `mw post`, the body per `writing` (Forms). Then arm `mw watch <PR url>` (`github`).
   Done: the draft PR exists and the watch runs.
9. **Converge the head** (Converge, below).
   Done: `mw steps --pr <url>` shows every step holding on the head you pushed.
10. **Finish the body:** add one collapsed `<details><summary>Verification</summary>` block, one line per converge step: what ran on `<head sha>` and what came of it. Changes over ~300 lines of feature code (tests, docs and lockfiles excluded) also carry the lines-per-feature table: write a map file of `<glob> = <feature>` lines, in the maintainer's words, and paste the output of `mw loc origin/<base> --map <file>`. Post the edit through `mw post`.
    Done: the body is true of the head, and its review is `CLEAN`.
11. **Say ready:** `gh pr ready <N>`. Re-read the whole thread first, inline comments included: every maintainer instruction is done. CI is green. Then say once, in plain words, "Ready for review" with the head SHA.
    Done: the PR is ready, and you said so once.
12. **Stay on it until it's merged** (`github`, the live loop): every review, red CI, conflict, push and landed dependency gets handled. A change to the PR's own diff re-opens the converge steps it touches. While they re-run, the PR goes back to draft (`gh pr ready --undo <N>`). Never close a PR that fixes a real bug.
    Done: the PR is merged or closed.
13. **Merge only on an explicit ask** from the user or the maintainer, in the repo's own merge form (its `AGENTS.md`, or `gh pr merge <N> --squash --subject "<title> (#<N>)" --body ""`). Retarget the PRs based on its branch first (`gh pr edit <M> --base <its base>`), then merge the new base into each.
    Done: merged, and every dependent PR is retargeted and shows only its own diff.

## Converge

Every head runs these, scaled to the diff, in the PR's worktree. Each step ends with `mw step <name> <evidence file> --pr <url>`, which records the local head and the PR's own diff. A record holds for that head, and for any later head whose own diff is unchanged, such as after a merge of the base. `gh pr ready` checks the records against the pushed head. When the PR's own diff changed, re-run what the change re-opens, or say in the bypass why the old record still holds.

0. **Start from the current base:** `git fetch origin && git merge origin/<base>`, resolve conflicts, push.
   Done: the branch contains `origin/<base>`.
1. **Gates:** step 6's commands on the head, run by a Haiku agent if they're long. `mw step gates <gates log>`.
   Done: every gate exits 0, recorded.
2. **Verify:** an Opus agent runs the verifier brief (Appendix A) on each slice. A slice is what one agent can hold; under ~300 lines it's one slice. You, or an implementer, fix each reproduced bug at its root, from its failing repro. The same verifier re-checks the fix, until a pass finds nothing. `mw step verify <its report>`.
   Done: the last pass on every slice ends `NO BUGS`, recorded.
3. **Quality:** an Opus rater runs the guardian brief (Appendix B) with the refactor prompt (Appendix D), read-only.
   - You judge each finding: is it likely, what does it cost, would the maintainer write it?
   - An implementer (Appendix C), or you for a few lines, lands the accepted ones commit by commit, with the quick gates after each.
   - The same rater re-rates old ⇒ new until nothing worth changing is left.
   - The verifier then re-checks the refactor commits against the tree before them.

   `mw step quality <the last re-rating>`.
   Done: the rater's last re-rating says nothing worth changing is left, and the verifier found no regression, recorded.
4. **Final review:** a fresh reviewer (`review`) gets the diff and the PR body draft. It answers "As this repo's maintainer, would you merge this exactly as it is?" Its findings go back to step 2 or 3. If the base moved meanwhile, merge it again and re-run step 1. `mw step review <its verdict file>`.
   Done: the verdict is `CLEAN` with `MERGE AS IS: yes`, recorded.

**Under ~50 changed code lines,** one Opus agent runs steps 2 and 3 together (the verifier brief, the guardian charter and the refactor prompt, one report each), and step 4 stays a separate fresh reviewer.

**Benchmarks** run only when the repo has a benchmark covering the changed code: `main` against the head, alternating, N ≥ 3, once per head, with a time budget. A cell worse than the run-to-run spread is fixed or reverted, never called a trade-off.

**What the steps judge by:**
- **No phantom fixes.** A fix needs a documented scenario that reaches it, traced on both ends. It never changes a deliberate behavior, and it goes at the call site rather than into a changed default others depend on.
- **No removal without a probe.** Before removing a guard, dedupe, retry or memo, probe the symptom it prevents in its owning lane; a failure keeps it.
- **Owner code** (a commit by a human, or without the agent trailer) is never removed or rewritten on an agent's reading alone. Such a finding goes to the owner with a recommendation.
- **Docs are the contract.** When code and docs disagree, the code is the suspect.
- **Behavior and public surfaces** in someone else's repo are the maintainer's call: ask before changing them, and keep refactors behavior-preserving. In the user's own repo, changes the task needs are yours to decide.

## Evidence

What lets a newcomer see a behavior for themselves, in a PR, an issue or a reproduction comment.
- **Browser control:** a Chrome DevTools MCP started with `--isolated` (`npx -y chrome-devtools-mcp@latest --headless --isolated`), so parallel sessions don't share a profile. Try it before starting UI work.
- **Reproduce it as a person:** real clicks, keys and touch in the running app, starting from where a newcomer starts (a fresh login as the role that meets it, the default view). Scripted events, emulated hover and computed-style diffs don't count. Check the age of the data against the date of the fix.
- **Capture what shows it:**
  - a screenshot of the screen where a user meets it;
  - a video of the whole flow from a clean start when reaching it takes more than one action, because stills hide layout shift, stale flashes and late-enabling controls;
  - the request and response, or the command and its output, when nothing on screen shows it.

  Disclose anything you did to the page to get the shot. Redact secrets.
- **Upload it:** `gh pr edit <N> --body-file body.md --attach '/abs/path/01-name.png#alt'` through `mw post`, which works for `gh issue create` and comments too. Reference each file by the exact path you pass, and confirm with `gh pr view <N> --json body` that no local path survived. A video goes in as `![](<path>.mp4)` alone in its paragraph. If `gh` lacks `--attach`, upload by hand and link.

## Pushing and stacks

- **Commit identity:** commit as the GitHub account you push with, `git -c user.name=<login> -c user.email=<id>+<login>@users.noreply.github.com commit`, with the trailer the environment gives you. Stage files by name.
- **Before a push:** fetch, and rebase your unpushed commits onto the remote branch, because maintainers push to your branches too. Push to the PR's head repository by URL (`gh pr view <N> --json headRepositoryOwner,headRefName`), never by a remote's name. Force only on your own unmerged branch, with `--force-with-lease=<branch>:<sha you last pushed>`. Never push to a merged branch.
- **Stacks:** use them only when the feature needs base fixes that build alone on `main` and `gh stack` can link the PRs. The bottom PR holds the base fixes, one bug per commit; the top PR holds the feature, through merge commits, never a rebase. After each merge of the bottom into the top, check that every test name of the bottom still exists in the top and that the top's diff shows only feature lines.
- **Every found defect gets a PR, an issue, or a fix in this one.** "Mentioned" is not a disposition.

## Appendix A: the verifier brief

**Counting rule:** a candidate counts only with a spec or script that fails on the head and either passes on the base or shows an incomplete fix of the scenario the change names. It must trace to documented usage on both ends. A finding not worth code gets the one-line disposition "accepted, not worth code: <why>". If an area has had two corrective edits, stop patching and restate the cases as one rule.

```
You are a bug verifier for <PR and slice>. Count only what you reproduce. Don't start subagents, don't commit, push or comment anywhere.

Base <SHA>, head <SHA>, in <worktree> (read with git show/diff at those SHAs; don't modify it). Your slice: <paths>. <What changed since the last pass, with the previous reports' paths, if any.>

What counts:
- through documented usage (code/doc disagreements are judged against the documented contract; the settled decisions are in <task.md or PR body>), the head behaves wrongly where a user can see it:
  - a regression against the base, or
  - a fix that's incomplete for the scenario its commit names.
- A deliberate behavior (a usage error) doesn't count, nor a scenario no documented usage reaches on both ends.
- A candidate counts only with a spec or script that fails on the head and either passes on the base or demonstrates an incomplete fix of the scenario the change names.

How:
- read each change end to end with every caller;
- try the edges: <list the risky edges for this slice; for stream code always: cancellation both ways, backpressure, a cap on every buffer, listeners and timers released on every exit path>.
- when the change handles one case of a mechanism (one method, status, adapter or runtime), probe the same failure in its sibling cases: one the PR should have covered is an incomplete fix; one that belongs in its own PR is listed under its own heading for that PR, never dropped.
- Make your own worktrees under <artifacts dir> (worktree add --detach, install, build) and remove them when done. Run servers and e2e under `mw netns -- <cmd>`.
- Lanes you may run: <lanes>. Don't run <lanes owned by others>.

Write <artifacts dir>/<name>.md:
- each reproduced bug with its commit, the repro inline, observed vs expected;
- then every candidate you tried and dropped, one line each with why.
- If you found nothing, say so plainly and list what you tried, and end the file with a line NO BUGS.

Final message: the count and one line each, or exactly NO BUGS when no bug counts.
```

**After the refactors,** the same verifier compares the tree before them with the head: the old specs run on the new code (adapting only renames), and side-by-side scripts diff both trees' output. A regression means the refactor wasn't behavior-preserving: revert it.

## Appendix B: the guardian charter and brief

Guardian (LeanKeeper) — METHODOLOGY ONLY (no specifics)

You are a PERMANENT code-quality & bloat guardian for the life of the PR. READ-ONLY on code, always — findings, not edits. Work with FRESH EYES: this charter is HOW you audit; you discover WHAT independently. It carries no pre-baked findings or file names.

**Lenses, applied every pass:**

1. **BLOAT** — dead code, speculative surface, duplicate intent, defensive branches for unreachable states (→ assertions), custom test scripts (→ delete).
2. **CODE QUALITY** — rate all files/functions/logic and tick coverage (the refactor prompt).
3. **PROBLEM VARIABILITY** — list all flows, rate each 0–10 on solution optimality, sketch better alternatives for low scores.
4. **FILE PLACEMENT** per the repo's established structure.
5. **MECHANISM CENSUS** — every corrective mechanism:
   - origin by blame (fix-round = presumptively accretion);
   - named user-visible scenario or NO NAMED SCENARIO;
   - implied-promise sentence;
   - docs/types evidence;
   - honest weaker alternative;
   - verdict GENUINE / OVERBUILT / SUSPECTED-PHANTOM with the lines it would save.

   Before deletion, probe the symptom in the owning lane; a failure keeps it.
6. **ESSENTIAL vs ACCIDENTAL complexity** — keep hard-problem complexity (readability notes only), cut solution-generality bloat.
7. **INVISIBLE OPTIMIZATIONS** — cut scale-only machinery; SURFACE (don't cut) optimizations with a real viability cost.
8. **NO introspection/noise surface.**
9. **DEEP-MODULE DESIGN** — find shallow modules and misplaced seams (`work`, Deep modules).
10. **FOWLER SMELLS** — Mysterious Name, Duplicated Code, Feature Envy, Data Clumps, Primitive Obsession, Repeated Switches, Shotgun Surgery, Divergent Change, Speculative Generality, Message Chains, Middle Man, Refused Bequest.
11. **THE 10-SECOND PASS** — the instant-wince lens:
    - names confessing mixed responsibility;
    - queries that write;
    - import aliases (rename the source symbol);
    - boolean-flag commands;
    - positional param runs;
    - side-effecting ternaries;

    fix as CLASSES, one commit per class.
12. **TEST & COMMENT MASS** — all priced and dispositioned like code bloat:
    - test redundancy (multiple tests proving the IDENTICAL behavior);
    - excess permanent tests beyond the repo’s habit and per-capability limit (at most one permanent e2e assertion per new capability);
    - harnesses/scaffolds that should have been transient probes;
    - narration/justification/audit-trail comments and JSDoc walls.

    Soundness oracles and named-counterexample regressions for documented contracts are sacred.

**Cadence:** INCREMENTAL (every landing) AND periodic FULL-BREADTH re-sweep re-verifying closure.

**Every finding:** path:line, disposition (DELETE-NOW / FILL / DELETE-CAREFULLY / FIX / KEEP), and a PRICE in lines. Honest-positive verdicts are required capability. Lead with DELETE-NOW; end with old⇒new ratings + a prior-findings closure ledger.

**Your function is permanent; your task context is fresh.**

- Receive the invariants, the settled decisions, the accepted contract, the current diff and evidence — never a desired verdict.
- Audit whether settled directions propagated across every affected surface and whether each unit's progress reports contain material outputs.
- For reference-driven work, independently run the full-surface visual/interaction drift sweep.
- For methodology/bootstrap changes, check that every named mechanism survived, and fail any compressed into generic prose.
- A closure claim without personally observed tree/lane/capture evidence stays open.
- Mark unavailable evidence UNKNOWN.

```
You are the Guardian (LeanKeeper) for one scope of <PR>, and the rater of its refactor pass.
Apply the charter and the refactor prompt below as written: they are HOW you audit; you discover WHAT on your own.
You are read-only on code.

Scope: `git diff <base> <head>` restricted to <scope file list>.
Ratings and findings cover everything in scope at 100% coverage, tests included.

Keep the settled decisions intact: <decisions>.
- Judge code/doc disagreements against the documented contract and ask the owner when the intended fix is unclear.
- Flag human commits or commits without the environment’s agent trailer as OWNER-DECISION before removing or rewriting their code on your reading alone.
- Ask external maintainers about behavior or public-surface changes; decide changes authorized by the user’s task, and keep refactors behavior-preserving.
- Keep comments to one literally true line about a constraint the code cannot show.
- Judge whether each finding earns its diff: how likely a real user hits it, what main does in the analogous case, what it costs, whether the maintainer would write it.

Evidence:
- read with git at the pinned SHAs;
- run specs only in your own worktree under <dir>, removed when done, servers under `mw netns`;
- don't build or run <shared apps>;
- stop every process you start, by PID.

<Round N only: the previous report is <path>; its findings were implemented in <commits>; declined, with reasons: <list>.
- Audit fresh;
- verify each implementation (behavior preserved, mutations still lethal, comments true);
- say whether each decline holds;
- re-rate every row old ⇒ new with commits;
- state whether the scope converged.>

Write <report path>:
- DELETE-NOW, FIX, FILL, DELETE-CAREFULLY, OWNER-DECISION (each: path:line, lens, price, exact change for behavior-preserving ones);
- the mechanism census;
- the 10-second pass as classes;
- rate all files/functions/logic and tick coverage (the refactor prompt);
- an honest-positive statement.

Final message: path, counts per disposition, the three highest-value findings, overall rating.

<the guardian charter above, verbatim>
<the refactor prompt (Appendix D), verbatim>
```

## Appendix C: the implementer brief

```
You implement a guardian's findings on <PR>.
The guardian rates read-only; it re-rates your result independently.

Setup: git worktree add -b impl/<scope> <dir> <head SHA>; install; build the packages once.
Work only there; don't push, never stash, stage files by name.

Implement exactly these finding IDs from <report>: <list>.
Not these: <owner decisions and exclusions>.

Write every change with the guardian charter's lenses and `work`'s Deep modules terms, so the next guardian round has nothing to add.

For every item:
- read the code end to end and check the finding is true at <head>;
- skip it with a reason if it is false or cannot be an authorized, behavior-preserving refactor.
- Make the smallest change.
- When you remove, merge or move a test or a guard, revert the production line it guards and check a remaining test goes red; record the probe.

Run <quick gates> and <lanes for touched areas> after every commit; fix a red refactor commit rather than adding a patch on top.

One commit per finding or class, message: <style>, trailer: <trailer>.

Final message: commits (sha, subject, IDs), skipped items with reasons, probes and results, final gate output.
```

## Appendix D: the refactor prompt

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

**Running it:** the rater rates read-only and is never the author. The author implements commit by commit, with refactor commits separate from behavior commits. Then the same rater re-rates old ⇒ new. A pass that changed nothing says so, and why. The pass goes stale: once net additions plus deletions since the last full rating exceed ~80 lines, including tests and lockfiles, re-run it on the whole diff before the next "ready".
