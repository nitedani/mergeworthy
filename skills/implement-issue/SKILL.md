---
name: implement-issue
description: "Implementing an issue or opening a PR: already fixed?, reproduce, approach rating, build and gate, browser evidence, review round, refactor pass, PR body."
---

# Implementing a change

From an issue or a problem to one merge-ready PR. Tier S follows it as written; Tier ≥ M runs it once per PR, with `convergence`'s loops in place of steps 6 and 7's single rounds (`convergence` §7 says what feeds `pr-steps`).

The repo's `AGENTS.md` / `CLAUDE.md` governs how the code is written. Everything particular to a repo (base branch, gates, existing guarantees, security surfaces, tracker, labels, how to run the app) lives in its **project file**: `.claude/skills/implement-issue/references/project.md`, else `.claude/implement-issue.md`. If the repo has none, derive it (base branch from `gh repo view --json defaultBranchRef`, gates from CI config and package scripts, how to run the app from the README) under the headings of the project template at the end of this skill, write it to `.claude/implement-issue.md`, tell the user it is a draft, and use it. If the repo has `.claude/skills/implement-issue/SKILL.md`, read it on `origin/<base>` first: where it differs from this skill, it wins, except where `core`, `github-threads` or `merging` say otherwise (usage limits per 1.1.13, found defects per 1.1.7, process stays out of the thread).

`<base>` below is the base branch it names. Work in a worktree off it: `git fetch origin && git worktree add -b <branch> <artifact root>/<branch> origin/<base>`. In CI (e.g. `$GITHUB_ACTIONS` is `true`) read the project file's CI section first, if it has one.

**Check you can finish before you start**, both halves up front:
- **Browser control**: a [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) or anything that opens a page and screenshots it. Try it; nothing in a shell can test it. Configure the MCP with `--isolated` (e.g. `npx -y chrome-devtools-mcp@latest --headless --isolated`) so parallel sessions don't share one profile; isolated profiles are temporary, so set the cookies and storage the test needs in the page.
- **The rest of the machine**: `gh` and its login, and whatever the app needs (containers, the hostname, the secrets, the data). The project file's preflight checks all of it in one pass and prints every failure together.

Install whatever doesn't need root (a browser, the MCP server, the stack, the data; the project file has the commands). For the rest, stop: the first thing in your reply is the exact steps, in order, with the commands to run.

Everything this skill posts (issue comments, the PR body, inline comments, filed issues) passes the posting gate (1.6).

### 1. Check it is not already fixed

Two minutes, before a stack, before reading code.

```bash
git log --oneline origin/<base> -- <the files this would touch>
gh issue view <N> --json assignees,comments        # someone already on it?
gh pr list --state all --search "<keyword>"        # an open or merged PR
```

If the tracker was migrated, commits cite the old number, which the issue body names (the project file has this repo's form). Then ask what already owns this: a framework, validation layer or type boundary may guarantee the thing you are about to guard.

A hit is not proof: read the commit and confirm the behavior is in today's code. If it is already fixed, comment on the issue with the commit and current `file:line`, recommend closing, and stop. Otherwise claim it before you start: `gh issue edit <N> --add-assignee @me`.

### 2. Prove the problem exists

Reproduce it in the running app (step 5 starts one), then comment the reproduction on the issue with screenshots: what you did, what you saw.

```bash
gh issue comment <N> --body-file repro.md --attach '/abs/path/repro.png#alt text'
```

Dev data is often a restored snapshot: if it predates a fix that step 1 turned up, rows written the old way still make the bug look alive. Compare the age of the data with the date of the fix. If you cannot reproduce it, comment what you tried and what happened, and stop.

When the cause isn't obvious at a first look, write one command that goes red on the reported symptom before reading code for a theory: a failing test, a curl, a script that drives the browser. Make it fast and give the same result every run; for a flaky bug, loop the trigger and add load until it fails often enough to work with. Cut inputs, steps and config one at a time while it stays red. If it worked at an earlier commit or version, `git bisect run` it. With the loop red, write three to five possible causes, each with what it predicts ("if X, changing Y makes it pass"), before testing any. Each probe tests one prediction and changes one thing. Temporary logs share one unique prefix (`[DBG-a4f2]`) so one grep removes them before the commit.

For a feature, capture the current state as the before shot and settle what "done" means. For a restructure, capture what the code does now: the behavior you must preserve.

### 3. Find an approach that rates high, or stop

List the distinct problems the change must solve. Rate each candidate 0–10 on how confident you are that it is the obviously right approach (not on implementation quality). Generate two or three before rating any, and include *not building it*; for a guard it often wins. To leave the frame, invert it (how would you guarantee this bug?) or delete what everyone treats as immovable. Candidates resting on the same unspoken assumption count as one.

**6 or below is not ready to build.** If the work adds a surface, rate the **contract** (the surface, its invariants, its counterexamples) before writing a line. If it reshapes existing code, run Phases A and B of the finality pass (below) and rate the shape they derive.

If nothing rates high, abort: comment what you tried and why each falls short, then stop. An open product question hiding in the issue is asked before building.

### 4. Build and gate

The smallest diff that finishes the job: schema, API, every call site, every locale. The gates are in the project file; the exit code is the verdict, not your reading of the output. At most one regression test, in an existing suite. Its expected value comes from outside the code: a literal, the issue, a worked example; never recomputed the way the code computes it, and never a snapshot taken from the code's own output.

Write it with the guardian's lenses from the first line (`convergence` §11.1, and 1.4.1): deep modules, no speculative surface or defensive branch for an unreachable state, no duplicate intent, terse comments that are literally true, names that don't confess mixed responsibility. Before the review round, read your own diff through those lenses and fix what they catch. The guardian checks; it isn't where the code gets its shape, so a guardian round that finds design work means this step was skipped.

**Build the whole interaction, not the happy path.** Someone will finish the task, change their mind, go back, reload, mistype, use the keyboard, leave halfway. Anything that would make them wonder what happened is a defect, whether or not the ticket mentioned it.

Converging a subsystem is built as the finality pass's Phase C: behavior-preserving commits, gates after each.

Independent user-visible fixes are separate PRs (1.1.16). A larger change whose pieces depend on each other becomes a stack of small PRs only when the bottom PR builds and makes sense alone on `main` and `gh stack` can link them (`convergence` §5); otherwise one PR with a commit per item.

### 5. See it in the browser

The project file's preflight starts what is missing, isolated from everyone else's.

Capture "before" by reverting only your own files (`git checkout origin/<base> -- <files>`), letting HMR reload, then restoring (`git checkout HEAD -- <files>`). Leave `git status` clean; never amend or force-push to fake it.

**Then use it as a user for five minutes.** Look at the screen around your change, not the path you fixed. If the screen renders by role, walk it as each role. Fix what your change caused; anything else you trip over gets a disposition (1.1.7).

An issue you file holds one finding: what breaks, where, and how to see it, with the screenshot of the screen it sits behind (or a recording when reaching it takes clicks), attached with `--attach`. Leave out how you came across it and what the team already knows. `raw.githubusercontent.com` links 404 for a private repo.

Tear the stack down when you finish, including when you abort.

#### UI work

**References before UI.** Before any visual design: 3–5 named reference sites with screenshots, and the design skills the user has pointed to. Ambiguous feedback about direction: build two or three variants that differ in layout, hierarchy or main action (not color or copy), inside the real page with real data, switchable by a `?variant=` parameter, and ask which. Given a design file, measure the design and the app the same way (sizes, radii, motion, production build) and fix every difference. Before any screenshot or video is shown, a fresh-context agent lists everything broken, misaligned or clipped in it. Matching a design file is not the bar: before a screen is shown, name its surface archetype, score it on the slop tells (wrong surface, center stack, equal-weight tile grids, decoration in place of hierarchy, rainbow color), repair by that diagnosis, and remove every element nobody asked for. When the user wants people used to a named product to feel at home, first list that product's everyday features and buttons for the surface, then build each one (better, not copied) or write down why it is absent. A new feature or visual direction is shown to the user on a local preview before it's pushed; fixes to reported bugs go straight to the PR.

**Before anyone sees a UI change:** each touched page at widths 360, 768, 1280 and 1920 plus 1 px either side of every breakpoint, zoom 90–150 %, light and dark, hover, focus and open states, and a cold first load. Any console error fails. List the checked cells in the report. Use it like a person: real mouse, wheel, keyboard and touch (Playwright's `page.mouse`/`keyboard`/`touchscreen` when the DevTools browser can't send it), a screenshot looked at after each action, a recording for anything that moves. Scripted events, emulated hover and computed-style diffs don't count.

**Runtime fixes** (a stream, a cancel, a cache) are shown in the real app through a real browser, `main` against the head, with the server's logs. Unit scripts alone don't count.

### 6. One review round: correctness, security, bloat

The reviewer (`reviewer`) reviews the diff with the reviewer charter at the end of this skill. Write the charter to `<artifact root>/review.md` and append: the diff command against `git merge-base HEAD origin/<base>`, the issue link (Tier ≥ M: also `acceptance.md`), and one sentence on what the change claims to do. It says UNKNOWN for anything it could not observe; paste your gate commands, exit codes and output where it can't run them. If no reviewer at all is available, review it yourself with the charter.

One round: fix real defects, decline the rest with a line of reasoning (1.1.15), no second round. Record who reviewed (or that it was a self-review) and what they found, including nothing, in the ledger and the PR's review-record comment (1.6), and run `pr-steps review <output>`.

### 7. Refactor pass

After the review round, with correctness proven and gates green: the reviewer (`reviewer`) rates **the diff you just wrote** with the refactor prompt (`convergence` §11.2), read-only; you implement commit by commit; it re-rates old ⇒ new. With no reviewer available, run it yourself in two separate passes (rate, then edit) and record that. Mostly-10s means it was lazy. Then `pr-steps refactor <output>`, and put the final lists in the PR (`convergence` §11.2). Re-run it whenever the watcher prints `### REFACTOR STALE` for your PR. Refactor commits change the head: before ready, re-run the charter review on the final head (to confirm, not as a new round: fix real defects it finds and confirm again) and record it with `pr-steps review` on that head (1.7).

### 8. The PR

```markdown
<Two or three plain sentences: what was wrong, what changed.>

Closes #N

### What you should see

**1.** <what to look at and what it proves>

![alt](/abs/path/01-name.png)
```

`Closes #N` only if the change fixes what the issue reported; otherwise `Refs #N`, leave it open, and comment your findings there.

**Write it to be scanned.** The first sentence says what was wrong in a user's words, not the mechanism. One idea per sentence, one line per caption. The implementation belongs in the diff. Evidence in a skimmable shape: a two-column before/after beats a transcript. At most one closing caveat, last, for the reviewer's decision. When a revert wouldn't undo the merge (a stored or wire format, a migration, a published name), that is the caveat.

#### The walkthrough

The images are the review: a sequence, not a before/after pair.
- **Open on the defect, close on the fix**, in the real app with real data, and in between show what your change could have broken and did not.
- **Show it where a user meets it, not where you edited it.** A fix to a form is not proven until the thing it configures is on screen behaving differently.
- **If the change is about what happens when you do something, record it.** Stills hide layout shift, a flash of stale data, a step that runs twice, a control that enables late. Stills alone are for what is static: formatting, labels, a column's contents.
- **One line per image**: what to look at, what it proves. Name the setup (page, date, filter) when the default view does not show it. Crop so the changed pixels are findable.
- **Disclose anything you did to the page** to get the shot, and whether it reproduces on `<base>`.
- **When the change is not visual**, show the evidence that is: the payload the service received, the request that was rejected. Label it, keep it in sequence.

#### Publishing

```bash
gh pr create --base <base> ...        # + --label effort/<level> if the repo uses them
gh pr edit <N> --body-file body.md --attach '/abs/path/01-name.png#alt text'
```

`gh` uploads attachments and rewrites matching local paths: reference each file by the exact path you pass to `--attach`, then confirm with `gh pr view <N> --json body` that none survived. Video works the same: in T3 Code, `preview_open` with `open:false` → `preview_recording_start` → drive → `preview_recording_stop` returns an `.mp4`; put it in the body as `![](<path>)` alone in its paragraph and GitHub renders a player.

**If the repo labels PRs by review effort** (`gh label list | grep effort/`, or the project file), apply the one that rates the reviewer's work, not yours: `quick-win` (read it), `easy` (one behavior, settled by the screenshots), `medium` (check the walkthrough against the diff), `hard` (a shared contract, or correctness needing a run). Don't copy the issue's label.

#### Inline comments

Only where a careful reviewer would want to form their own opinion: a judgment call that could have gone the other way (say what the other way was), something the diff cannot show, or a risk you are handing over. Not what the code does. No comments at all is the normal outcome for a small fix. Lines must fall inside the diff.

```bash
gh api repos/<owner>/<repo>/pulls/<N>/reviews --method POST --input review.json
## {"commit_id": "<head sha>", "event": "COMMENT",
##  "comments": [{"path": "...", "line": 42, "side": "RIGHT", "body": "..."}]}
```

**Every sentence in the body is a claim.** "Unchanged", "every call site", "all locales" need a diff behind them, and a later push can turn a caption into a lie: re-check the body after every push.

## Reference: finality pass

**When to run it.** The work reshapes existing code rather than changing what it does, or a change you meant to make small cannot be made cleanly because the area has taken too many patches.

**Who runs it.** Phases A and B are analysis by the reviewer (`reviewer`) or a fresh-context subagent, never the author's context; the prompt's "strongest-model agent" is one of these, never above the default tier (`core`, the task). Phase C is the author implementing commit by commit, with the gates green underneath.

**"Bring me the decision"** in Phase C: in an external maintainer's code, stop and ask the person who owns it; in the user's own repos and beta features, decide, act, and report (`core`, the task). Convergence itself is behavior-preserving.

"Fan out parallel mapper agents" means one subagent per subsystem (at most 3 at once, 1.1.14). The graph is working material; the short design doc at the end is the deliverable.

Run the prompt as written:

```
Run a FINALITY PASS on <FEATURE / PATHS>. The feature evolved through many design changes —
added-to, patched, revised — which is exactly how code reaches the state where the next person
wants to rewrite it from scratch. I want the opposite outcome: converge it NOW to the final
state that will need no rewrite. That cannot be done by lazily shuffling code around. Do it in
three phases:

PHASE A — MAP. Build a knowledge graph of the ENTIRE feature, line by line. It is tedious work;
do it anyway. Fan out parallel mapper agents over the subsystems, one shared node schema. For
EVERY file: its role and why it is a separate file. For EVERY function/class/constant (internal
ones too): purpose (what it decides, not its name paraphrased); inputs/outputs; state it
reads/writes; invariants it relies on and maintains; call/data edges by module path (cross-
subsystem edges especially); failure behavior; cognitive-complexity flags (deep nesting, mode
flags, implicit protocols, state machines spread across functions); and ACCRETION SCARS with
line refs — vestigial parameters, generality nothing uses, shapes visibly patched across design
revisions, concepts duplicated across files, names that no longer match behavior, comments
contradicting code, seams that exist only for history. Each mapper ends with: the subsystem's
true concept list (the few ideas everything else elaborates), hidden couplings, its heaviest
cognitive-load points ranked, and rewrite-from-scratch observations. Mappers are read-only;
graphs are artifacts.

PHASE B — IMAGINE. Give the assembled graph to ONE strongest-model agent (one at a time, always
on the hardest task) and have it derive the PINNACLE design — the shape this feature would have
if designed today, from scratch, knowing everything the graph knows, with NO obligation to the
current file layout. Design pressures: (1) every module must be able to STATE the reason for its
complexity ("essential because <specific reality>") or be collapsed — complexity that cannot
name its reason is accidental; (2) terminology is part of the design — one small documented
vocabulary, functions readable by a maintainer who has not built this domain; (3) separate the
STABLE CORE from the BRITTLE EDGES — quarantine anything depending on third-party internals or
version pins behind a small named interface so the core survives churn and a future second
consumer could plug in (build the boundary, NOT the second consumer); (4) no speculative fixes,
and specifically NO PHANTOM HOLES FROM PARTIAL READS — a hole claim is only valid AGAINST THE
WHOLE GRAPH: the finder must name the layer that SHOULD own the behavior, look up in the full
map whether any layer DOES own it, and only an empty search is a hole. A hole that survives must
also have a plausible trigger; otherwise it is a documented accepted contract; (5) keep
cognitive complexity low; (6) every corrective mechanism in the graph passes the PROMISE test —
name the promise it enforces and whether anyone deliberately chose it; mechanisms whose promise
lives only in themselves and their tests are accretion candidates for the plan.
Output: the pinnacle architecture, the diff between it and the tree, and a ranked convergence
plan of behavior-preserving refactors.

PHASE B½ — HUNT CREPT-IN PHANTOM FIXES. Past phantom holes may already be IN the code, and they
are hard to see because a crept-in phantom fix looks identical to legitimate defense-in-depth —
the difference is a fact about the REST of the system. Run these graph queries: (1) RESPONSIBILITY
COLLISIONS — for each failure mode (reconnect/retry/dedupe/timeout/ordering/cleanup), list every
node claiming to handle it; >1 claimant across layers = suspect set, and the phantom is usually
the wrong-altitude one; (2) UNREACHABLE GUARDS — instrument suspect defensive branches with
counters and run the full suite + e2e through REAL entry points; a counter stuck at zero is the
signature (unit tests poking the branch directly don't count — that's the test MAINTAINING the
phantom); (3) ALIBI COMMENTS — "in case X…" where the graph shows another layer's contract
forbids or owns X; (4) STACKED IDEMPOTENCY — retry over retry, dedupe over dedupe, recovery
duplicating the caller's recovery; (5) PROVENANCE — fixes that landed without a failing repro,
and fixes born in audit rounds whose promise no one ratified.
REMOVAL ORDER (the danger is a phantom MASKING a real upstream gap): first prove ownership at
the owning layer with a test THERE; only then delete the duplicate; prove the deletion by the
owner's test staying green AND the deleted guard's zero reachability count — AND the owning
product lane green (units are not a verdict). If the counter fires, it was not phantom — you
found a real upstream gap or genuine shared responsibility; move it to the owner deliberately,
never keep both.

PHASE C — CONVERGE. Execute the convergence plan: separate revert-ready commits, behavior
preserved (every moved mechanism's tests move with it; transient probes re-run and lethal in
the new home — a refactor voids prior probe results for moved code), adversarially gated before
push. Where the pinnacle differs from the tree in ways that change behavior or public surface,
STOP and bring me the decision — convergence is refactoring, not redesign-by-stealth. Finish by
distilling the graph into a short design doc a maintainer can read in one sitting: the concept
list, the stable/brittle boundary, the glossary, how it all fits together.
Then run Owner-Safe closure reconciliation: prove every SETTLED decision propagated to its named
surfaces; every unit/finding is closed or held with a reason; code/tests/docs/types/UI/PR state agree;
reviewer and fresh Guardian evidence is attached; CI, owning lanes, mutations, reference captures,
and clean-tree scope are observed. Finality is not complete while any of those joins disagrees.
```

## Reference: reviewer charter

Hand this to the reviewer (step 6): not the author, not in the author's context.

---

You are reviewing a change you did not write. Read the touched files in full, not just the hunks. Code outside the diff is context, not your subject. Run the gates yourself rather than trusting the report.

Tag every material claim OBSERVED (path:line, or command + exit code + output), INFERRED (say the premises), or UNKNOWN (say what is missing). Only OBSERVED closes anything. "Unchanged", "every call site" and "every locale" are claims that need a diff behind them — re-open the file rather than writing from memory.

Three lenses, one pass:

**Correctness.** Revert the fix and confirm the failure returns, then restore. A check that also passes without the change proves nothing. Look for the behaviour the issue actually reported, not the behaviour the diff implements. List each asked-for behavior that is missing or only partly there, quoting the line that asks for it.

**Security.** You know what to look for; this repo's surfaces are in the project file. The part you cannot infer from a diff: a change to what the API returns, or to what a filter matches, breaks consumers silently and is a team decision, not a reviewer's.

**Bloat**, deletions first. For every mechanism added, name the user-visible scenario it serves — "it could break" is not one; no scenario, delete it. Comments and tests are priced like code.

**Delete by probe, not by opinion.** Before calling something removable, run a check that *could* fail. If it goes red, the thing is load-bearing — say so and record the failure. Confirming a mechanism earns its place is as good a result as deleting one.

Do not ask for a guarantee to be strengthened in order to close a finding. A round that finds nothing is a real result: say what you searched and failed to find. If you confirm nearly every suspicion you started with, you were building a case, not reviewing.

Output: a verdict — PASS / CHANGES-REQUESTED / FAIL — then findings as `path:line — what breaks — what to do instead`, most severe first, then what you searched and did not find. No style preferences.

## Reference: project template

Everything this skill needs to know about one repo; the method itself stays here. Default branch: `<base>`. Keep each section to what an agent would otherwise get wrong; delete a section that has nothing to say.

- **Gates:** the commands that must exit 0 before a PR (typecheck, lint/format check, unit tests), where to run them (host, container) and how long they take. Locales, if any: which ones and where their files live.
- **What already guarantees things:** validation layers, generated type shields, authorizers, schema constraints, each with its file and function.
- **Security surfaces:** what is publicly reachable, how auth is checked per call, rate limiting, where admin actions and secrets live, and which changes are a team decision.
- **Issue tracker:** anything that makes `git log --grep <issue>` miss (a migrated tracker, different numbering in commits).
- **PR conventions:** labels (e.g. `effort/*`), title format, required reviewers, changeset or changelog expectations.
- **Feature-scale precedent:** how bigger changes have landed before, with an example.
- **Running the app:** *Preflight*: one command that checks everything the app needs and prints every failure together, plus install commands for what doesn't need root. *Start*: an isolated copy that disturbs nobody, and how to tell it is ready (the HTTP status, not just the exit code). *Drive it*: URLs, test accounts, seed data, how to reach the screen an issue is about. *Stop*: how to tear it all down, including after an abort.
