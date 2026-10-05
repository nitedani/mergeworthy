---
name: implement-issue
description: "Implementing an issue or opening a PR: already fixed?, reproduce, approach rating, build and gate, browser evidence, converging it, the PR body."
---

# Implementing a change

From an issue or a problem to one merge-ready PR: steps 1 to 5 build the change, step 6 converges it with `converge`'s pipeline, and step 7 is the PR. Open it as a draft (`gh pr create --draft`) once step 5 holds, with step 7's body through the fast gate, so CI runs while it converges; the fresh reader's `CLEAN` gates the final body. A Tier ≥ M change (`core` 1.0) runs this once per PR.

**The repo's `AGENTS.md` / `CLAUDE.md` governs how the code is written;** everything else particular to the repo is in its project file (`core` 1.3).

**A repo's own `.claude/skills/implement-issue/SKILL.md` wins over this skill.** Read it on `origin/<base>` first. The exceptions are where `core`, `github-threads` or `merging` say otherwise: usage limits (1.1.13), found defects (1.1.7), and process staying out of the thread.

**Work in a worktree off `<base>`**, the base branch the project file names: `git fetch origin && git worktree add -b <branch> <artifact root>/<branch> origin/<base>`. In CI (e.g. `$GITHUB_ACTIONS` is `true`), read the project file's CI section first, if it has one.

**Check you can finish before you start**, both halves up front:
- **Browser control** (UI or runtime work): a [Chrome DevTools MCP](https://github.com/ChromeDevTools/chrome-devtools-mcp) or anything that opens a page and screenshots it. Try it; nothing in a shell can test it. Configure the MCP with `--isolated` (e.g. `npx -y chrome-devtools-mcp@latest --headless --isolated`), so parallel sessions don't share one profile. Isolated profiles are temporary: set the cookies and storage the test needs in the page.
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

**A hit is not proof.** Read the commit and confirm the behavior is in today's code. If it is already fixed, comment on the issue with the commit and the current `file:line`, recommend closing, and stop. Otherwise claim the issue before you start: `gh issue edit <N> --add-assignee @me` where you have triage rights; otherwise the repro comment (step 2) is the claim.

### 2. Prove the problem exists

Reproduce it in the running app (step 5 starts one), or for a non-UI fix with the command a user runs, then comment the reproduction on the issue with screenshots: what you did, what you saw.

```bash
gh issue comment <N> --body-file repro.md --attach '/abs/path/repro.png#alt text'
```

**Check the age of the data.** Dev data is often a restored snapshot. If it predates a fix that step 1 turned up, rows written the old way still make the bug look alive: compare the age of the data with the date of the fix. If you cannot reproduce the problem, comment what you tried and what happened, and stop.

**When the cause isn't obvious, build a red loop before a theory:** one fast, repeatable command that goes red on the reported symptom (a failing test, a curl, a script that drives the browser), then probe one change at a time.

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

Tear the stack down when you finish, including when you abort.

#### UI and runtime work

- **Show it in the real app, used like a person:** real mouse, keyboard and touch, a screenshot after each action. Scripted events, emulated hover and computed-style diffs don't count. A runtime fix (a stream, a cancel, a cache) is shown through a real browser, `main` against the head, with the server's logs.
- **Before anyone sees a UI change,** check each touched page at a phone, a tablet and a desktop width, in light and dark, with its hover, focus and open states. Any console error fails.

### 6. Converge

Run `converge`'s pipeline on the diff (open `converge`): Loop A until dry, Loop B until it leaves nothing worth doing, Loop A again on Loop B's commits, then the fresh reader on the final head. Before the fresh reader, update the PR body draft per step 7 (`drafts/pr-body.md`) and pass `post-lint --kind pr`, since the fresh reader reviews it. The pipeline's last step records `pr-steps review` and `pr-steps refactor` on the final head.

### 7. The PR

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
gh pr create --draft --base <base> ...   # + labels per the project file, where you can label
gh pr ready <N>                         # once the pipeline's records are on the final head
gh pr edit <N> --body-file body.md --attach '/abs/path/01-name.png#alt text'
```

**`gh` uploads attachments and rewrites matching local paths.** Reference each file by the exact path you pass to `--attach`, then confirm with `gh pr view <N> --json body` that no local path survived.

**Video works the same**, with an `.mp4` from whatever records your browser. Put it in the body as `![](<path>)`, alone in its paragraph, and GitHub renders a player.

**Labels and conventions** follow the project file.

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
