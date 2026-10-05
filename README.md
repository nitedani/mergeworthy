# mergeworthy

A working method for an AI coding agent on GitHub. The agent acts as your second brain across your tasks and the threads it opens. It gates every post through an independent review before the post goes out. It converges each PR through bug verification, guardian, refactor and finality passes until nothing worth changing is left. Hooks enforce the parts that text alone didn't.

## Install

```sh
npx mergeworthy
```

The installer finds the coding agents on this machine and asks which to install into and how to set the options. It installs through each agent's own plugin system:

| Agent | Gets | Updates |
|---|---|---|
| Claude Code | the skills, the hooks, the `bin/` commands and the always-on rules | automatically |
| Codex | the skills, and the always-on rules in `~/.codex/AGENTS.md` | re-run `npx mergeworthy` |
| Others, through [skills.sh](https://skills.sh) | the skills | `npx skills update` |

Run `npx mergeworthy` again to change the options or add an agent; `npx mergeworthy uninstall` removes mergeworthy.

## Options

| Option | Values (default first) | What changes |
|---|---|---|
| `badge` | `on`, `off`, `auto` | The agent's icon and label at the start of every post; `auto`: only when posting from a human account. |
| `merge` | `on-request-squash`, `reviewer` | `reviewer`: the agent never merges. |
| `watcher` | `on`, `off` | `off`: no GitHub watcher. |

## How it reads

This is the work automation methodology, split into skills along its own parts and sections. The split keeps the methodology's substance, and its prompts and charters word for word. `always-on.md` is loaded in every session: it holds the always-on rules and an index of which skill to open when, and which rule numbers each skill holds. Rule numbers (1.6, 1.1.15) work across skills.

| Skill | Holds |
|---|---|
| `core` | the task, 1.0 triage, 1.1 principles, 1.2 tracking, 1.3 discovery, 1.8 safety, 1.11 reporting, 1.12 pre-flight |
| `design-loop` | 1.4 the design loop |
| `github-threads` | 1.5 the live GitHub loop, 1.6 the posting gate |
| `merging` | 1.7 pushing, ready and merge |
| `delegating` | 1.9 writing rules and prompts, 1.10 integrating agents' work |
| `implement-issue` | the steps from an issue to a merge-ready PR |
| `converge` | what a converged PR is, and the order of the passes |
| `verify`, `guardian`, `refactor`, `finality`, `review` | the passes and their prompts: bug verification, bloat and quality, the refactor pass, the finality pass, the reviewer charter |
| `past-failures` | the table of past failures and the rule that covers each |
| `mechanisms` | the scripts and hooks that enforce the rules (the code itself lives in `hooks/`, `bin/` and `watcher/`) |

## How the skills connect

`docs/graphs.md` has one graph per entry point of `always-on.md`, generated from the skills by `docs/build-graphs.py`. In each graph, each section is a box, its numbered steps run top to bottom, and a dashed arrow marks where a step hands over to another skill. After editing a skill, run `python3 docs/build-graphs.py`; CI fails while the graphs don't match the skills.

## Layout

```
always-on.md        the always-on rules and the index, in every session
skills/<name>/      one skill per part or pass of the methodology
hooks/              hooks.json and the scripts it runs
bin/                commands on the Bash PATH: gate-pass, post-lint, pr-steps, gh-watch-start
watcher/            the GitHub watcher daemon gh-watch-start runs
cli/                the npx mergeworthy installer
docs/               graphs.md (generated from the skills) and build-graphs.py
.claude-plugin/     the plugin manifest (options) and its marketplace
```

## Changing it

Edit here, commit and push; installed copies update through the plugin. To try a change before pushing, run `claude --plugin-dir .`.
