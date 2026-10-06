---
name: mechanisms
description: "Using or fixing the mechanisms that enforce the rules: the watcher, the hooks, gate-pass, post-lint, pr-steps."
---

# Mechanisms

These scripts enforce the rules that failed as text alone.

- **Where they live.** The scripts ship in the mergeworthy plugin: its `bin/` is on the Bash `PATH`, and its `hooks/hooks.json` is active while the plugin is enabled. They update with the plugin.
- **Changing them.** Change them in the mergeworthy repo, then commit and push (1.9). Never edit an installed copy.
- **Options.** The plugin's options are `badge`, `merge` and `watcher` (`/plugin` → mergeworthy → Configure options). They reach the scripts through `~/.mergeworthy/settings.env`, rewritten at every session start. An environment variable `MERGEWORTHY_<KEY>` wins over the option.

## Commands

### `gh-watch-start` (enforces 1.5)

`gh-watch-start [--main] <dir> [owner/repo [N]]…` is the one way to start watching; running it again is harmless.
- **What it adds.** It adds `owner/repo N` to `<dir>/threads.txt`. A bare `owner/repo` goes to `repos.txt`, which covers a repo before an issue exists.
- **`--main`:** this dir gets the user's `/ai` calls on threads no watcher watches. The default is the first live dir.
- **The supervisor.** It starts the daemon under a supervisor: the systemd user service `gh-watch@<dir>` on Linux, a launchd agent on macOS, else a detached daemon that cron revives.
- **Maintainers.** `GH_WATCH_EYES` names the maintainers whose commits and 👍/👎 are reported; without it, `<dir>/eyes`, else your own login.
- **One watcher per thread.** It refuses a thread another live watch dir already watches.
- **The Monitor.** It prints the Monitor to arm in the session. The session is what answers events, and nothing else wakes it.

### `post-lint` (enforces 1.6)

`post-lint drafts/x.md --kind reply|pr|issue|inline|tracker|proposal [--repo o/r]` checks a draft before it is posted.
- **A reply** reads its parent comment from `drafts/x.parent.md`. Use `--parent none` when it answers nobody.
- **`tracker`** checks the umbrella issue's format: a `Title: Tracking: …` line, `##` sections of checkboxes, no table, the Decisions comment linked, a ticked item's end state, and the Decisions comment's sections. A tracker post needs no badge.
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

### `pr-steps` (enforces 1.7)

`pr-steps review <reviewer output>` and `pr-steps refactor <rating output>` record, on the final head, that the step ran.
- `gh pr create` (unless `--draft`) and `gh pr ready` are blocked until HEAD has a `review` and a `refactor` record.

## The watcher daemon: `watcher/gh-watch.py` (enforces 1.5)

The daemon reports to `<dir>/events.log` and adds 👀 within about 10 seconds. It never starts an agent.
- **Comments.** It reports exactly the comments 1.5 says you answer, and records each in `replies-owed.md`.
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
- a third comment while your last two on that thread have no reply and the last is under 3 hours old (1.6);
- `gh pr merge` without `--squash --subject "<title> (#N)" --body ""`, and with `merge=reviewer`, every merge;
- `--delete-branch` while PRs are based on the branch;
- a `git commit` whose author isn't the pushing GitHub account (1.7);
- `pkill -f` and `killall`;
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
