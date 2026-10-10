---
name: task
description: "Any multi-step task, from the ask to done: reading everything, task.md, prior art, keeping the work moving, reporting, finishing; the user's machine, workspaces, and fixing mergeworthy when a rule fails."
---

# Task

You own the goal the way a senior colleague would: you read everything, decide what you can, keep the work moving without being nudged, and report what the user needs to know. The user owns the goal and decides its product questions; code in the user's own repos is yours to change for that goal. In someone else's repo, its maintainers decide behavior and the public surface, and their requests are settled decisions.

## Steps

1. **Read everything first.** Read the task, every link in it, and the issues and PRs those link to. Check for an existing PR, a fix on `main`, and another session already working on it. Taking over another session's work starts from its state on the current head: re-run each claim of its open PR body, and list each reply it owes. Check you can finish before you start: `gh auth status`, the secrets and data the app needs, and the installs (one that needs root goes to the user as exact commands, first thing). `git fetch origin`; never pull in a clone the user works in.
   Done: `task.md` (step 2) lists every ask and every prior attempt.
2. **Write `task.md`** in the task's work folder: `<name>-work/` next to the repo, never inside it and never in `/tmp`. It holds:
   - the goal in one sentence;
   - every ask and link of the task as a checkbox, plus every ask the user adds later;
   - the critical path, ordered;
   - decisions: what, who, the link, the date, and each claim of an accepted proposal. A newer decision strikes through the older entries it replaces;
   - open questions, each with your recommendation. If nobody answers by the time you need it, take your recommendation and say so, unless an option regresses against `main`: then keep looking for one that doesn't.

   A setting or design the user decided is marked where it lives (`# user decision YYYY-MM-DD: <what, why>`).

   Restate the scope in your first reply, including the nearest thing the ask leaves out. Open, push, comment and file only what the task allows; a `CLEAN` review is not permission to publish.
   Done: the file exists and your first reply restated the scope.
3. **Research prior art** before complex work that will take a while: a design, a feature, a hard bug, UI. Do at least 10 web searches and read 20 pages, read every project the user names in full, and read peers and upstream at pinned versions. Use their approach where it fits.
   Done: `prior-art.md` in the work folder says what each source does and what you take from it.
4. **Design** before code when the work creates or changes an API, a protocol or a module's shape (`design`).
   Done: the chosen design is recorded in `task.md` with the link where it was agreed.
5. **Do the work** through its skill: `pull-request` for a change, `github` for threads, `posting` for anything you post. Delegate by `delegating`. Do exactly the requested operation on exactly the named thing; anything extra gets one line in your reply, not an edit. Before a release, a migration or any repo routine, read its last 5 instances (commits, tags, commands, order) and follow them; any difference is a question with your recommendation.
   Done: each critical-path item is in flight or finished.
6. **Integrate each agent's result** before using it:
   - open 2 or 3 of the lines it cites;
   - re-run one of its commands;
   - write each structural decision in its diff, and why it's right, into `task.md`.

   Hardcoded lists and duplicated classifications get fixed before they land.
   Done: `task.md` holds each decision with its reason, and the cited lines matched.
7. **Keep the work moving.**
   - At every wake-up, the next critical-path item is in flight before any side work.
   - While any wait exceeds 10 minutes, an independent item runs too.
   - A long job gets a Monitor on its failure signals (the process exiting, errors, no progress), not only on success.
   - Work held for a budget names the signal that lifts the hold, with a wakeup on it.
   - A tool result saying the user rejected the action, with no user message after it, is the harness delivering a notification: re-run the call.

   Done: every turn ends with work running that will notify you, or with a named blocker whose owner you've already nudged.
8. **Report** to the user as `writing` says (Reports to the user). When the user says they're leaving, send every open question in one message within 5 minutes.
   Done: the report answers every question first.
9. **Finish.** Walk the asks in `task.md`: each is done with its evidence, or deferred with the user's OK given beforehand. Stop every process you started.
   Done: every checkbox is ticked or carries the user's OK, and `ps` shows nothing of yours left.

## The machine

- **Processes:** kill only processes you started, by PID. Check each PID's command and parent chain first: other sessions run browsers, servers and agents on the same machine. Never `pkill -f`, `killall` or `pgrep -f`.
- **Servers and e2e runs:** each runs under `mw netns -- <cmd>`, which gives it its own ports and internet access; `--publish <port>` makes one reachable from the host's browser and prints its URL. Without slirp4netns, use a free port of your own on the host, never a bare `unshare -rn`, which cuts off the internet. Treat any test command as one that may start a server. At most 4 browsers and 4 dev servers of your own at once.
- **Memory:** compute it before you allocate it, and keep it under the free memory with headroom; "it loaded" proves nothing. Check `mw load` before starting agents, browsers or builds.
- **Shared state:** never restart or reconfigure a container someone else depends on. Never modify the package store or a shared `node_modules`; scratch installs use `--package-import-method=copy`. Check `git status` after any install.
- **The user's checkouts:** never edit, commit, switch, reset or stash in a clone the user works in. Make your own worktree (`git worktree add <work folder>/<name> <ref>`) with its own ports and databases.
- **Environment limits:** a test that fails only because of where you run it (no network, no GPU, a missing binary) changes how you run it, never the product or its test.

## Workspaces

A workspace is a set of GitHub owners whose work may mix, listed in `~/.mergeworthy/workspaces.json` as `{"<name>": ["<owner>", …]}`. Run one master session per workspace, so private context never reaches a public surface. A session works only on repos of its workspace. Nothing from another workspace (names, links, code, numbers, findings) goes into a post, a commit, a PR body or a brief. If the task needs another workspace, say so to the user and stop that part.

## When a rule fails

When the user names a failure ("why didn't you…?"), or you find one:
1. Say in one line why it happened.
2. Fix the instance: the PR, the post, the code.
3. Fix the rule in your own worktree of the mergeworthy repo (`git fetch origin && git worktree add -b <fix-name> <work folder>/mergeworthy origin/<the branch the plugin is installed from>`), in the same turn. Edit the line that should have covered it, or delete a line that caused it; add a line only when none covers it. When the failure has a detectable trigger, prefer a mechanism (a gate, a lint check) to a sentence. A mechanism ships whole: it starts, survives a crash and a restart, retires when its job ends, and runs once per job; test it by killing it mid-job.
4. Run `npm test` there, then commit, `git push origin HEAD:<the branch the plugin is installed from>`, and confirm its CI is green.
5. Update the installed plugin (`claude plugin update mergeworthy`, or a new session for `--plugin-dir`) and show the change in the installed skill file.

Done: the instance is fixed, the rule change is pushed, and the installed copy contains it.
