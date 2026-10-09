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

### `thread-context` (enforces 1.6 and writing step 0)

`thread-context <owner/repo#N> [--depth 2] [--max 30] [--out <file>]` writes the record a reply is drafted from (default `./thread-context.md`). Run it into the draft folder, and hand it to the drafter and the reviewer, never read it into the main session.
- It fetches the thread's body, issue comments, PR review comments and review bodies, each with author, time and permalink, and every thread they reference (`owner/repo#N`, bare `#N`, github.com URLs), breadth-first to `--depth`, at most `--max` threads, skipping bots. Threads are cached by `updated_at` under `~/.cache/mergeworthy/threads/`.
- The file holds a header (root, `latest-human-comment`, threads included), a **Decisions and positions** ledger (one line per human comment, not the agent's, with agreement, rejection, proposal or decision language: date, author, tags, quote, permalink), the root's full transcript, then the linked transcripts (first post and last 30 comments). The agent's posts (the `claude.png` badge) are marked `AGENT` and kept out of the ledger.
- `--latest <repo#N>` prints the latest human comment; `--verify <file> [--target <repo#N>] [--parent <file>]` is what the gate and the guard run.

### `gate-pass` (enforces 1.6)

`gate-pass <abs>/drafts/x.md <review output> [post-lint flags]` records that a draft passed the gate.
- It re-runs `post-lint` with the flags the draft last passed with (stored in `<draft>.lint`).
- It checks that the review's final message is exactly `CLEAN`.
- It records the pass as the draft's sha256 in `<draft>.gate`.
- A `reply`, `inline` or `proposal` draft needs `thread-context.md` in its folder, newer than its `.parent.md`, recording a latest human comment (`thread-context --verify`).
- A draft that promises work ("I'll", "follow-up PR") first needs a `PROMISED … (<draft name>)` line in `proposals-open.md`.

### `review-context`

`review-context <base-ref> [--max-refs N]` prints, for the symbols a diff changes, who calls them, what they call and which names the diff removes. Run it inside the repo at the head under review and paste its output into the reviewer's prompt; it costs no model tokens.
- For each changed function, method, class, arrow function, exported const, interface or type it lists the callers grouped by file (test files tagged `[test]`, capped at `--max-refs`, default 15) and the in-repo functions it calls.
- For each top-level name the diff removes it lists the remaining `git grep` hits at HEAD (dangling callers) under `### removed: name`.
- It loads the repo's TypeScript, falling back to mergeworthy's own when the repo's has no compiler API (TypeScript 7). It builds one language service per tsconfig, freeing each after use; a small diff on vike takes about 3 s.
- It never blocks a review: the analysis runs in a child with a 3 GB heap cap and a 60 s limit (`--timeout SECONDS`); on a failure, crash or timeout it prints `review-context: failed (<reason>); no context` and exits 0. Output is capped at about 400 lines.

### `loc-breakdown`

`loc-breakdown <base>..<head> <map file> [--repo-dir DIR]` prints a markdown table of the lines each feature changed (`pull-request`, the PR body). The map has lines `<feature>\t<path>[:<start>-<end>]`: a head range for added lines, `<path>:base:<start>-<end>` for removed lines, a bare path for the whole file.
- Docs (one row, one number), Tests, Lockfile and Generated are separate rows and not features; docs, tests and lockfiles are recognized by path, and the map can assign any path to those names.
- It exits 1 and lists the lines when a changed line is in no entry or in two, so the totals equal `git diff --numstat`. `post-lint` doesn't count the table in a PR's word budget.

### The finality trigger (`pre-bash-guard`, `post-bash-register`)

`post-bash-register` counts each posted `--kind proposal` draft per thread in `~/.claude/proposal-rounds.txt`. Before the third proposal, refresh the thread map with its invariants (`finality`, When to run it) and update the thread's WIP comment from it (`github-threads`).

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
    - `### DEPENDENT of merged …`: a PR listed in `waiting-on.txt` merged;
    - `### FOLLOW-UP`: for 60 days after one of your watched PRs merges, a commit by someone else (not a merge) that changes lines the PR changed, or renames or removes its files, and another person's PR that references it, each once. The watcher checks hourly and records the PR's lines at the merge; a commit counts within 3 lines of them. Read each as `core` 1.3 says (Learning from follow-ups).
- **`/agent` commands.** Your comment starting with `/agent` on a thread no live watch dir lists is found in the recent issue and review comments of every repo a live watch dir lists (the comments feeds are live; the search index and your events feed lag by many minutes, so a search of your comments only backs it up), since you and the agent post as one account. It goes once to one dir's `events.log` as `### AGENT COMMAND`, and the thread joins that dir's `threads.txt`: to the dir named by `/agent <folder name>`, else to the dir listing a thread this one links to or is linked from (most matches; a tie goes to the `--main` dir), else to the `--main` dir as `### UNROUTED /agent`.
- **Retiring.** It retires itself, service, launchd agent and cron lines included, once every thread is merged or closed and `repos.txt` is empty.
- **State.** State lives in `gh-watch-state.json`, so restarts lose nothing.

## Hooks

### `pre-bash-guard.py` (enforces 1.6, 1.7, 1.8)

It blocks:
- a `gh` post or edit whose body isn't a gated draft, or changed since its gate (use absolute draft paths);
- opening an issue or PR in a repo no running watcher covers;
- the same gated draft posted twice as new;
- a post or edit on a thread (comment, review, PR or issue body edit, comment PATCH) whose draft folder has no `thread-context.md` for that thread recording its current latest human comment, or older than the draft's parent; the message gives the `thread-context` command. `--kind tracker` drafts and new issues and PRs are exempt;
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

It blocks ending a turn when:
- it ends with "want me to / should I / your call…" and no `GENUINE-FORK:` line;
- you posted on GitHub and no live Monitor watches a watcher's `events.log` (a `claude -p` run's caller watches);
- a watch dir it worked in owes a reply.

It skips its watcher checks while the user's last message says "pause". Each turn's first stop also gets a check-in: work to start, or anything waiting?

### `session-start` (enforces the always-on rules)

It puts the always-on rules into context and writes `settings.env`. It also points `~/.mergeworthy/current` at the installed version, the stable path watchers use.

**`pre-agent-dedupe`** registers launches that ran (its PostToolUse half) by ticket and blocks duplicate jobs (`delegating` 1.10). A `clientRequestId` may retry within ten minutes; later reuse is blocked. Read a terminal task’s result, then release it with `agent-job done <ticket>` (`delegating` 1.10).
