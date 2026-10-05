# mergeworthy

How an AI coding agent works on GitHub so that its replies and PRs are worth merging: sizing the work, evidence for every claim, an independent review before anything is posted, answering maintainers within minutes, and converging each PR until no reviewer finds anything worth changing. Hooks and scripts enforce the rules that text alone didn't.

## Install

```sh
npx mergeworthy
```

It finds the coding agents on this machine, asks which to install into and how to set the options below, and installs through each agent's own plugin system:

| Agent | Gets | Updates |
|---|---|---|
| Claude Code | the skills, the hooks, the commands (on the Bash `PATH`) and the always-on rules | automatically (auto-update is turned on) |
| Codex | the skills, and the always-on rules in `~/.codex/AGENTS.md` | re-run `npx mergeworthy` |
| Others, through [skills.sh](https://skills.sh) | the skills | `npx skills update` |

Run it again to change the options or add an agent; `npx mergeworthy uninstall` removes it. It also replaces an older `install-methodology` setup, moving running watchers over.

Without the installer, in Claude Code: `/plugin install mergeworthy --marketplace nitedani/mergeworthy`, then turn on auto-update under `/plugin` → Marketplaces.

## Options

Set by the installer, or later under `/plugin` → mergeworthy → Configure options (Claude Code only; the other agents don't run the scripts they control).

| Option | Values (default first) | What changes |
|---|---|---|
| `badge` | `on`, `off`, `auto` | The agent's icon and label at the start of every post; `auto`: only when posting from a human account. |
| `merge` | `on-request-squash`, `review` | `review`: the agent never merges; the guard blocks `gh pr merge`. |
| `watcher` | `on`, `off` | `off`: no GitHub watcher; owed replies are checked at each start. |
| `local_model` | `off`, `on` | `on`: exploration and gate reviews go to a local model (`local-model/`) while it's available. |

## Layout

```
skills/<name>/SKILL.md   the methodology: core (load first), github-threads, merging, design-loop, delegating,
                         implement-issue, converge and its passes (verify, guardian, refactor, finality, review),
                         past-failures, mechanisms
always-on.md             the rules every session gets (the session-start hook prints it)
hooks/                   hooks.json and the scripts it runs
bin/                     commands, on the Bash PATH while the plugin is enabled
watcher/                 the GitHub watcher daemon gh-watch-start runs
local-model/             Claude Code on a local model (claude-local, the llama.cpp server, usage); install.sh
cli/                     the npx mergeworthy installer
.claude-plugin/          the plugin manifest (options) and the marketplace that lists it
```

## Changing it

Edit the skill or script here, commit and push. Installed copies update through the plugin; never edit them. To try a change before pushing: `claude --plugin-dir .`.
