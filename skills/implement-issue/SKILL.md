---
name: implement-issue
description: "Implementing an issue or opening a PR: already fixed?, reproduce, approach rating, build and gate, browser evidence, review round, refactor pass, PR body."
---

# Implementing a change

From an issue or a problem to one merge-ready PR. The tiers come from `core` (1.0 Triage):
- **Tier S** (one bounded fix) follows this skill as written.
- **Tier ≥ M** runs it once per PR, and replaces the single rounds of steps 6 and 7 with `converge`'s loops. `guardian` (landing) says what feeds `pr-steps`.

**The repo's `AGENTS.md` / `CLAUDE.md` governs how the code is written.** Everything else particular to a repo lives in its **project file**: the base branch, gates, existing guarantees, security surfaces, tracker, labels, and how to run the app. The project file is `.claude/skills/implement-issue/references/project.md`, else `.claude/implement-issue.md`.

**If the repo has no project file, derive one** under the headings of the project template at the end of this skill:
- the base branch from `gh repo view --json defaultBranchRef`;
- the gates from the CI config and package scripts;
- how to run the app from the README.

Write it to `.claude/implement-issue.md`, tell the user it is a draft, and use it.

**A repo's own `.claude/skills/implement-issue/SKILL.md` wins over this skill.** Read it on `origin/<base>` first. The exceptions are where `core`, `github-threads` or `merging` say otherwise: usage limits (1.1.13), found defects (1.1.7), and process staying out of the thread.

**Work in a worktree off `<base>`**, the base branch the project file names: `git fetch origin && git worktree add -b <branch> <artifact root>/<branch> origin/<base>`. In CI (e.g. `$GITHUB_ACTIONS` is `true`), read the project file's CI section first, if it has one.

**Check you can finish before you start**, both halves up front:
- **Browser control**: a [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) or anything that opens a page and screenshots it. Try it; nothing in a shell can test it. Configure the MCP with `--isolated` (e.g. `npx -y chrome-devtools-mcp@latest --headless --isolated`), so parallel sessions don't share one profile. Isolated profiles are temporary: set the cookies and storage the test needs in the page.
- **The rest of the machine**: `gh` and its login, and whatever the app needs (containers, the hostname, the secrets, the data). The project file's preflight checks all of it in one pass and prints every failure together.

**Install whatever doesn't need root** (a browser, the MCP server, the stack, the data; the project file has the commands). For anything that needs root, stop: the first thing in your reply is the exact steps, in order, with the commands to run.

**Everything this skill posts passes the posting gate** (1.6): issue comments, the PR body, inline comments, filed issues.

### 1. Check it is not already fixed

Two minutes, before a stack, before reading code.

```bash
git log --oneline origin/<base> -- <the files this would touch>
gh issue view <N> --json assignees,comments        # someone already on it?
gh pr list --state all --search "<keyword>"        # an open or merged PR
```

If the tracker was migrated, commits cite the old number, which the issue body names (the project file has this repo's form). Then ask what already owns this: a framework, validation layer or type boundary may guarantee the thing you are about to guard.

**A hit is not proof.** Read the commit and confirm the behavior is in today's code. If it is already fixed, comment on the issue with the commit and the current `file:line`, recommend closing, and stop. Otherwise claim the issue before you start: `gh issue edit <N> --add-assignee @me`.

### 2. Prove the problem exists

Reproduce it in the running app (step 5 starts one), then comment the reproduction on the issue with screenshots: what you did, what you saw.

```bash
gh issue comment <N> --body-file repro.md --attach '/abs/path/repro.png#alt text'
```

**Check the age of the data.** Dev data is often a restored snapshot. If it predates a fix that step 1 turned up, rows written the old way still make the bug look alive: compare the age of the data with the date of the fix. If you cannot reproduce the problem, comment what you tried and what happened, and stop.

**When the cause isn't obvious at a first look, build a red loop before a theory:**
- **One command that goes red on the reported symptom**, written before reading code for a theory: a failing test, a curl, a script that drives the browser.
- **Fast and repeatable.** It gives the same result every run. For a flaky bug, loop the trigger and add load until it fails often enough to work with.
- **Minimize.** Cut inputs, steps and config one at a time while it stays red.
- **Bisect.** If it worked at an earlier commit or version, `git bisect run` it.
- **Hypotheses before probes.** With the loop red, write three to five possible causes, each with what it predicts ("if X, changing Y makes it pass"), before testing any.
- **One change per probe.** Each probe tests one prediction and changes one thing.
- **Tag temporary logs** with one unique prefix (`[DBG-a4f2]`), so one grep removes them before the commit.

For a feature, capture the current state as the before shot and settle what "done" means. For a restructure, capture what the code does now: the behavior you must preserve.

### 3. Find an approach that rates high, or stop

List the distinct problems the change must solve. Then rate each candidate approach 0–10 on how confident you are that it is the obviously right approach (not on implementation quality):
- **Generate two or three before rating any**, and include *not building it*; for a guard, not building it often wins.
- **Leave the frame.** Invert it (how would you guarantee this bug?), or delete what everyone treats as immovable.
- **Shared assumptions count once.** Candidates resting on the same unspoken assumption count as one.

**6 or below is not ready to build.**
- If the work adds a surface, rate the **contract** (the surface, its invariants, its counterexamples) before writing a line.
- If the work reshapes existing code, run Phases A and B of the finality pass (open `finality`: it maps the code and derives the shape it should have), and rate that shape.

**If nothing rates high, abort.** Comment what you tried and why each falls short, then stop. An open product question hiding in the issue is asked before building.

### 4. Build and gate

**The smallest diff that finishes the job:** schema, API, every call site, every locale.
- **The gates are in the project file.** The exit code is the verdict, not your reading of the output.
- **At most one regression test**, in an existing suite. Its expected value comes from outside the code: a literal, the issue, a worked example. Never recompute it the way the code computes it, and never take a snapshot of the code's own output.

**Write it with the guardian's lenses from the first line.** Before writing, open `guardian` for its charter and `design-loop` for 1.4.1. The code has deep modules, no speculative surface, no defensive branch for an unreachable state, and no duplicate intent. Its comments are terse and literally true, and its names don't confess mixed responsibility. Before the review round, read your own diff through those lenses and fix what they catch.

The guardian checks; it isn't where the code gets its shape. A guardian round that finds design work means this step was skipped.

**Build the whole interaction, not the happy path.** Someone will finish the task, change their mind, go back, reload, mistype, use the keyboard, leave halfway. Anything that would make them wonder what happened is a defect, whether or not the ticket mentioned it.

**Converging a subsystem** is built as the finality pass's Phase C: behavior-preserving commits, with the gates after each.

**Independent user-visible fixes are separate PRs** (1.1.16). A larger change whose pieces depend on each other becomes a stack of small PRs only when both hold:
- the bottom PR builds and makes sense alone on `main`;
- `gh stack` can link them (`converge` (stacked PRs)).

Otherwise it is one PR with a commit per item.

### 5. See it in the browser

The project file's preflight starts what is missing, isolated from everyone else's.

**Capture "before" by reverting only your own files** (`git checkout origin/<base> -- <files>`), letting HMR reload, then restoring them (`git checkout HEAD -- <files>`). Leave `git status` clean; never amend or force-push to fake it.

**Then use it as a user for five minutes.** Look at the screen around your change, not the path you fixed. If the screen renders by role, walk it as each role. Fix what your change caused; anything else you trip over gets a disposition (1.1.7).

**An issue you file holds one finding:** what breaks, where, and how to see it.
- Attach the screenshot of the screen the finding sits behind (or a recording when reaching it takes clicks) with `--attach`.
- Leave out how you came across it and what the team already knows.
- `raw.githubusercontent.com` links 404 for a private repo.

Tear the stack down when you finish, including when you abort.

#### UI work

- **References before UI.** Before any visual design, collect 3–5 named reference sites with screenshots, and the design skills the user has pointed to.
- **Ambiguous feedback about direction gets variants.** Build two or three variants that differ in layout, hierarchy or main action (not color or copy). Put them inside the real page with real data, switchable by a `?variant=` parameter, and ask which.
- **A design file is measured, not eyeballed.** Measure the design and the app the same way (sizes, radii, motion, production build), and fix every difference.
- **A fresh eye before any screenshot or video is shown.** A fresh-context agent (the review round's reviewer, when one runs) lists everything broken, misaligned or clipped in it.
- **Matching a design file is not the bar.** Before a screen is shown:
  - name its surface archetype (the kind of screen it is, e.g. a dashboard, a form, a settings page, a landing page);
  - score it on the slop tells (the marks of generic, generated-looking UI): wrong surface, center stack, equal-weight tile grids, decoration in place of hierarchy, rainbow color;
  - repair by that diagnosis;
  - remove every element nobody asked for.
- **"Feel at home" means the familiar features are there.** When the user wants people used to a named product to feel at home, first list that product's everyday features and buttons for the surface. Then build each one (better, not copied), or write down why it is absent.
- **New directions are previewed locally.** A new feature or visual direction is shown to the user on a local preview before it's pushed; fixes to reported bugs go straight to the PR.

**Before anyone sees a UI change**, check each touched page across this matrix, and list the checked cells in the report:
- widths 360, 768, 1280 and 1920, plus 1 px either side of every breakpoint;
- zoom 90–150 %;
- light and dark;
- hover, focus and open states;
- a cold first load.

Any console error fails.

**Use it like a person.**
- Use a real mouse, wheel, keyboard and touch (Playwright's `page.mouse`/`keyboard`/`touchscreen` when the DevTools browser can't send it).
- Look at a screenshot after each action, and record anything that moves.
- Scripted events, emulated hover and computed-style diffs don't count.

**Runtime fixes** (a stream, a cancel, a cache) are shown in the real app through a real browser, `main` against the head, with the server's logs. Unit scripts alone don't count.

### 6. Review round

The review round runs in the reader. The reader is one agent, in one run, on the diff (open `converge`, who reads, for how the reader and the fresh reader are set up). The reader runs these in order, each into its own output file. Each brief lives in the skill named next to it; open that skill when you write the reader's prompt:
- the verifier brief (`verify`);
- the reviewer charter (`review`);
- the guardian verdict (`guardian`) and the refactor ratings (`refactor`).

The context the reader filled reviewing is the context it rates with.

### 7. Refactor pass

- **Fix the real defects.** Send the reader the commits; it re-verifies until dry.
- **Implement the ratings commit by commit**, with the gates after each (in a guardian round, `guardian`'s implementer does). The reader re-rates old ⇒ new; record it with `pr-steps refactor`.
- **Last, the fresh reader reads the final head and the PR body** (`converge`, who reads). Its `CLEAN` is both the body's posting-gate review and the `pr-steps review` record on that head.

### 8. The PR

```markdown
<Two or three plain sentences: what was wrong, what changed.>

Closes #N

### What you should see

**1.** <what to look at and what it proves>

![alt](/abs/path/01-name.png)
```

`Closes #N` only if the change fixes what the issue reported; otherwise `Refs #N`, leave it open, and comment your findings there.

**Write it to be scanned.**
- **The first sentence says what was wrong** in a user's words, not the mechanism.
- **Plain sentences that say why, not only what**; one line per caption. The implementation belongs in the diff.
- **Evidence in a skimmable shape:** a two-column before/after beats a transcript.
- **At most one closing caveat**, last, for the reviewer's decision. When a revert wouldn't undo the merge (a stored or wire format, a migration, a published name), that is the caveat.

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

**`gh` uploads attachments and rewrites matching local paths.** Reference each file by the exact path you pass to `--attach`, then confirm with `gh pr view <N> --json body` that no local path survived.

**Video works the same**, with an `.mp4` from whatever records your browser. Put it in the body as `![](<path>)`, alone in its paragraph, and GitHub renders a player.

**If the repo labels PRs by review effort** (`gh label list | grep effort/`, or the project file), apply the label that rates the reviewer's work, not yours. Don't copy the issue's label.
- `quick-win`: read it.
- `easy`: one behavior, settled by the screenshots.
- `medium`: check the walkthrough against the diff.
- `hard`: a shared contract, or correctness needing a run.

#### Inline comments

**Only where a careful reviewer would want to form their own opinion:**
- a judgment call that could have gone the other way (say what the other way was);
- something the diff cannot show;
- a risk you are handing over.

Not what the code does. No comments at all is the normal outcome for a small fix. Lines must fall inside the diff.

One gated draft per comment (`post-lint --kind inline`):

```bash
gh api repos/<owner>/<repo>/pulls/<N>/comments -F body=@<abs>/drafts/<name>.md -f commit_id=<head sha> -f path=<path> -F line=42 -f side=RIGHT
```

**Every sentence in the body is a claim.** "Unchanged", "every call site", "all locales" need a diff behind them, and a later push can turn a caption into a lie: re-check the body after every push.

## Reference: project template

Everything this skill needs to know about one repo; the method itself stays here. Default branch: `<base>`. Keep each section to what an agent would otherwise get wrong, and delete a section that has nothing to say.

- **Gates:** the commands that must exit 0 before a PR (typecheck, lint/format check, unit tests), where to run them (host, container) and how long they take. Locales, if any: which ones and where their files live.
- **What already guarantees things:** validation layers, generated type shields, authorizers, schema constraints, each with its file and function.
- **Security surfaces:** what is publicly reachable, how auth is checked per call, rate limiting, where admin actions and secrets live, and which changes are a team decision.
- **Issue tracker:** anything that makes `git log --grep <issue>` miss (a migrated tracker, different numbering in commits).
- **PR conventions:** labels (e.g. `effort/*`), title format, required reviewers, changeset or changelog expectations.
- **Feature-scale precedent:** how bigger changes have landed before, with an example.
- **Running the app:** *Preflight*: one command that checks everything the app needs and prints every failure together, plus install commands for what doesn't need root. *Start*: an isolated copy that disturbs nobody, and how to tell it is ready (the HTTP status, not just the exit code). *Drive it*: URLs, test accounts, seed data, how to reach the screen an issue is about. *Stop*: how to tear it all down, including after an abort.
