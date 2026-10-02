# Work methodology

How the agent works: triage, principles, the live GitHub loop, the posting gate, safety, the implement-issue skill, the Convergence Protocol, past failures, and the scripts and hooks that enforce the rules.

## Layout

- `src/`: the methodology text, one file per section. `src/ORDER` lists Part 1's files in order.
  - `00-intro.md`, `01-always-on.md` (copied into `~/.claude/CLAUDE.md` by `install-methodology`), `02-task.md`
  - `part1/`: How to work, one file per section (1.0–1.12)
  - `part2-implement-issue.md`, `part3-convergence.md`, `part4-failures.md`, `part5-mechanisms.md`
- `mechanisms/`: the scripts and hooks (watcher, post-lint, gate-pass, pre-bash guard, stop lint, pr-steps, claude-swap, codex-review-model, install-methodology).
- `profiles/`: `defaults.env` (every setting, its default and its values) and one file per profile.
- `local-model/`: tooling to run Claude Code on a local model and hand it bounded tasks (`claude-local`, `local-agent`, `claude-usage`, the sandbox, server scripts, prompts; `eval/` is a test harness). See `local-model/README.md`; `local-model/install.sh` installs it into `~/local-llm` and `~/local-llm-eval`.
- `filter.py`: resolves the settings markers in `src/`; `build.sh` runs it.
- `tests/`: `python3 tests/test_build.py`; `python3 tests/test_post_lint.py`; `cd tests && bash run-guard-cases.sh ../mechanisms/pre-bash-guard.py`.
- `dist/`: the built files an agent is given. Don't edit them; edit `src/` and run `./build.sh --all`.

## Settings

One source, several variants. Text that differs per setting sits between markers at the place it applies: `<!-- if KEY=VALUE -->…<!-- else -->…<!-- end -->` (`KEY!=VALUE` negates; `else` is optional). With no profile, every setting has its default, which is the local setup for contributing to repos you don't own.

| Setting | Values (default first) | What changes |
|---|---|---|
| `target` | `local`, `ci` | `ci`: a claude-code-action run per `@claude` comment. The run rebuilds its scope from the thread and keeps scope, ledger and owed lists in its tracking comment; artifacts go to `$RUNNER_TEMP/claude-work`; it works on the checkout's branch; a `GENUINE-FORK` takes the recommendation and is listed in the final comment; no `claude-swap`. |
| `ownership` | `external`, `team`, `own` | `team`: our code, teammates review; ask only for paths the repo's `AGENTS.md` reserves for team decisions. `own`: the user's repo, no external maintainer. |
| `tests` | `remove-before-merge`, `keep` | Whether PR-proving tests are removed once the PR is approved. |
| `merge` | `on-request-squash`, `reviewer` | `reviewer`: never merge or offer to; `pre-bash-guard` blocks `gh pr merge`. |
| `pr_open` | `ready`, `draft` | `draft`: open with `--draft`, mark ready when the Ready list holds. |
| `review_trace` | `hidden`, `comment` | `comment`: the review record goes in one PR comment (`post-lint --kind review-record`). |
| `badge` | `on`, `off`, `auto` | The Claude badge on posts; `auto` requires it only when `gh api user` is a human account. |
| `post_lang` | `en`, `thread` | `thread`: answer an issue in its language; PRs in English. |
| `reviewer` | `codex-then-claude`, `claude` | `claude`: a fresh-context Claude subagent reviews; no Codex. |
| `watcher` | `on`, `off` | `off`: no `gh-watch`, heartbeat or Monitor; owed lists are checked at each start. |
| `commit_identity` | `noreply`, `git-config` | `git-config`: commit with the checkout's git identity. |
| `local_model` | `on`, `off` | Whether 1.1.14's local-agent delegation is included. |

Profiles:
- The defaults: an open-source repo where an external maintainer decides (`external`, `remove-before-merge`, `on-request-squash`).
- `ci`: GitHub Actions (`target=ci`, `watcher=off`, `reviewer=claude`, `badge=auto`).
- Your own: a `profiles/<name>.env` that sets only what differs, e.g. a team repo where teammates review and merge (`ownership=team`, `tests=keep`, `merge=reviewer`, `pr_open=draft`).

## Build

```sh
./build.sh                  # dist/methodology-prompt.md (defaults)
./build.sh ci               # dist/methodology-ci.md
./build.sh team ci          # profiles apply in order, later ones winning
./build.sh --all            # the defaults and ci
```

Each built file starts with its settings header, e.g. `<!-- settings: target=ci ownership=team … -->`.

## Use

See [SETUP.md](SETUP.md): one prompt each to install, update or uninstall it with an agent. Installed sessions update themselves from this repo once a day.

By hand: `./build.sh [profile…]`, then `mechanisms/install-methodology dist/<built file>`; `methodology-update`; `uninstall-methodology`.
