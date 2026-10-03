# Work methodology

How the agent works: triage, principles, the live GitHub loop, the posting gate, safety, the implement-issue skill, the Convergence Protocol, past failures, and the scripts and hooks that enforce the rules.

## Layout

| Path | What's in it |
| --- | --- |
| `SETUP.md` | Prompts to install, update or uninstall it with an agent |
| `methodology/` | The text, one file per section (`ORDER` lists Part 1's files); `01-always-on.md` goes into `~/.claude/CLAUDE.md` |
| `profiles/` | `defaults.env` (every setting, its default and its values) and one file per profile |
| `build.sh` | Builds `dist/methodology-<profiles>.md`: the text with the settings applied, plus every script it installs |
| `dist/` | The built files an agent is given. Don't edit them: edit `methodology/` and run `./build.sh --all` |
| `claude/hooks/` | Claude Code hooks: the posting and safety guard (Bash), the local-model guard (Agent), the thread register, the Stop check |
| `claude/bin/` | Commands: `gate-pass`, `post-lint`, `pr-steps`, `install-methodology`, `methodology-update`, `uninstall-methodology`, `claude-swap`, `codex-review-model`, `tracker-check` |
| `claude/watcher/` | The GitHub watcher (`gh-watch-start`, `gh-watch.py`, its daemon) |
| `claude/tools/` | `filter.py`, which applies the settings markers for `build.sh` |
| `local-model/` | Claude Code on a local model, and `local-agent` with one skill per task mode; see `local-model/README.md` |
| `tests/` | `python3 tests/test_build.py`; `python3 tests/test_post_lint.py`; `bash tests/run-guard-cases.sh claude/hooks/pre-bash-guard.py` |

Everything under `claude/` installs flat into `~/.claude/mechanisms/` (commands linked into `~/.local/bin`).

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
| `session_model` | `claude`, `local` | The model the session itself runs on. `local`: the subscription rules (usage limits, model tiers, `claude-swap`) drop out and the "you are the local model" rules take their place. |

Profiles:
- The defaults: an open-source repo where an external maintainer decides (`external`, `remove-before-merge`, `on-request-squash`).
- `ci`: GitHub Actions (`target=ci`, `watcher=off`, `reviewer=claude`, `badge=auto`).
- `local`: the pseudo-profile — no env file; a session that runs on the local model itself (`session_model=local`). It combines with others (`team local`).
- Your own: a `profiles/<name>.env` that sets only what differs, e.g. a team repo where teammates review and merge (`ownership=team`, `tests=keep`, `merge=reviewer`, `pr_open=draft`).

## Build

```sh
./build.sh                  # dist/methodology-prompt.md (defaults)
./build.sh ci               # dist/methodology-ci.md
./build.sh local            # dist/methodology-local.md (a session that runs on the local model)
./build.sh team ci          # profiles apply in order, later ones winning
./build.sh --all            # the defaults, ci and local
```

Each built file starts with its settings header, e.g. `<!-- settings: target=ci ownership=team … -->`.

## Use

See [SETUP.md](SETUP.md): one prompt each to install, update or uninstall it with an agent. Installed sessions update themselves from this repo once a day.

By hand: `./build.sh [profile…]`, then `mechanisms/install-methodology dist/<built file>`; `methodology-update`; `uninstall-methodology`.
