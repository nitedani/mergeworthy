---
name: mechanisms
description: "Using or fixing the mechanisms that enforce the rules: the watcher, the hooks, gate-pass, post-lint, pr-steps."
---

# Mechanisms

These scripts enforce the rules that failed as text alone.

- **Where they live.** The scripts ship in the mergeworthy plugin: its `bin/` is on the Bash `PATH`, and its `hooks/hooks.json` is active while the plugin is enabled. They update with the plugin.
- **Changing them.** Edit and propagate from the source repo, leaving installed copies untouched (`delegating` 1.9).
- **Options.** The plugin's options are `badge`, `merge` and `watcher` (`/plugin` → mergeworthy → Configure options). They reach the scripts through `~/.mergeworthy/settings.env`, rewritten at every session start. An environment variable `MERGEWORTHY_<KEY>` wins over the option.

## Commands

### `gh-watch-start` (enforces 1.5)

`gh-watch-start [--main] <dir> [owner/repo [N]]…` is the one way to start watching; running it again is harmless.
- **What it adds.** It adds `owner/repo N` to `<dir>/threads.txt`. A bare `owner/repo` goes to `repos.txt`, which covers a repo before an issue exists; delete that line once the thread exists, or the watcher never retires.
- **`--main`:** this dir gets the user's `/ai` calls on threads no watcher watches. The default is the first live dir.
- **The supervisor.** It starts the daemon under a supervisor: the systemd user service `gh-watch@<dir>` on Linux, a launchd agent on macOS, else a detached daemon that cron revives.
- **Maintainers.** `GH_WATCH_EYES` names the maintainers whose commits and 👍/👎 are reported; without it, `<dir>/eyes`, else your own login.
- **One watcher per thread.** It refuses a thread another live watch dir already watches.
- **The Monitor.** Arm the printed Monitor so the session wakes and answers events (`github-threads` 1.5).

### `post-lint` (enforces 1.6 and writing 1.11)

`post-lint drafts/x.md --kind reply|pr|issue|inline|tracker|proposal [--repo o/r]` checks a draft before it is posted.
- **A reply** reads its parent comment from `drafts/x.parent.md`. Use `--parent none` when it answers nobody.
- **`tracker`** checks the umbrella issue's format: a `Title: Tracking: …` line, `##` sections of checkboxes, no table, the Decisions comment linked, a ticked item's end state, and the Decisions comment's sections. Leave tracker posts badge-free (`writing`).
- **The checks**, each where it applies to the kind:
  - **Writing:** banned phrases; sentences over 40 words or averaging over 25, and more than 30% bold (not for `pr`); internal labels like W2; a bold label followed by a fragment; em dashes.
  - **References:** "stacked on"; bare `#N`.
  - **Content:** budgets; unclassified notes; process in the thread; questions without a recommendation; a bare "Done" to a question (`reply`, `inline`); deferrals in the notes table.
  - **Safety and form:** secrets; a missing badge, unless the `badge` option says otherwise (not for `tracker`).

### `gate-pass` (enforces 1.6)

`gate-pass <abs>/drafts/x.md <review output> [post-lint flags]` records that a draft passed the gate.
- It re-runs `post-lint` with the flags the draft last passed with (stored in `<draft>.lint`).
- It checks that the review's final message is exactly `CLEAN`.
- It records the pass as the draft's sha256 in `<draft>.gate`.
- A draft that promises work ("I'll", "follow-up PR") first needs a `PROMISED … (<draft name>)` line in `proposals-open.md`.

### The finality trigger (`pre-bash-guard`, `post-bash-register`)

`post-bash-register` counts each posted `--kind proposal` draft per thread in `~/.claude/proposal-rounds.txt`. Before the third proposal, refresh the thread map with its invariants (`finality`, When to run it).

### `pr-steps` (enforces 1.7)

`pr-steps <step> <output>` checks and records one `converge` step on HEAD, one file per step:
- `verify`: trailing `DRY`.
- `reverify`: trailing `DRY`, or `NO LOOP B COMMITS` when none landed (`converge`, step 3).
- `loopb`: captured final message `CLEAN` (`review`).
- `fresh`: `MERGE AS IS: yes` and trailing `CLEAN`; keep the posting verdict in a separate file (`converge`, step 4).
- `refactor`: ✅ list and ratings, or `carries the pass of <sha>` with ≤ 80 changed lines.
- `gates`: `<command> -> exit 0` lines.
- `gh pr create` (unless `--draft`), `gh pr ready` and a push to a ready PR are blocked until HEAD has all six.

## The watcher daemon: `watcher/gh-watch.py` (enforces 1.5)

The daemon reports to `<dir>/events.log` and never starts an agent.
- **Comments.** Answer reported comments from the owed list; reactions follow the detection schedule (`github-threads` 1.5).
- **Thread events.** On watched threads it reports pushes, merges and closes (`### PR CHANGED`), CI results (`### CI`), and 👍/👎 on the agent's comments (`### THUMBS UP` / `### THUMBS DOWN`).
- **Other events:**
    - `### ACK`: an acknowledgement that answers your last open proposal;
    - `### MAINTAINER COMMITS`: commits a maintainer pushed to your PR;
    - `### TRACKER STALE`: a PR merged or closed, and the umbrella issue named in `<dir>/umbrella.txt` doesn't show it ticked with that state;
    - `### REFACTOR STALE`: a PR's code changed by more than ~80 lines since its last `pr-steps refactor`;
    - `### DEPENDENT of merged …`: a PR listed in `waiting-on.txt` merged.
- **Retiring.** It retires itself, service, launchd agent and cron lines included, once every thread is merged or closed and `repos.txt` is empty.
- **State.** State lives in `gh-watch-state.json`, so restarts lose nothing.

## Hooks

### `pre-bash-guard.py` (enforces 1.6, 1.7, 1.8)

It blocks:
- a `gh` post or edit whose body isn't a gated draft, or changed since its gate (use absolute draft paths);
- opening an issue or PR in a repo no running watcher covers;
- the same gated draft posted twice as new;
- a third comment on a thread (1.6 states the condition);
- `gh pr merge` without `--squash --subject "<title> (#N)" --body ""`, and with `merge=reviewer`, every merge;
- `--delete-branch` while PRs are based on the branch;
- a `git commit` whose author isn't the pushing GitHub account (1.7);
- `pkill -f` and `killall`;
- `kill` of a running agent's process (a `claude … stream-json` session): stop an agent through its task, after reading its status;
- a foreground wait loop (`until`/`while` with `sleep`); run it with `run_in_background` or rely on the completion notification;
- a bare `git stash`;
- a force-push without a pinned lease.

### `post-bash-register.py` (enforces 1.5)

It adds a thread you just posted in (a new issue or PR, a comment, a review) to the watch list. A read that only prints URLs adds nothing.

### `stop-lint.py` (enforces 1.1.3, 1.5)

It blocks ending a turn in three cases:
- the turn ends with "want me to / should I / your call…" and has no `GENUINE-FORK:` line;
- you posted on GitHub and no live Monitor in the session watches a watcher's `events.log` (a `claude -p` run is exempt: its caller watches);
- a watch dir the session worked in has a reply owed.

It skips its watcher checks while the user's last message contains "pause".

### `session-start` (enforces the always-on rules)

It puts the always-on rules into context and writes `settings.env`. It also points `~/.mergeworthy/current` at the installed version, the stable path watchers use.

**`pre-agent-dedupe`** registers launches by ticket and blocks duplicate jobs (`delegating` 1.10). A `clientRequestId` may retry within ten minutes; later reuse is blocked. Read a terminal task’s result, then release it with `agent-job done <ticket>` (`delegating` 1.10).
