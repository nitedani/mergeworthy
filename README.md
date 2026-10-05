# mergeworthy

A working method for an AI coding agent on GitHub: it acts as your second brain across your tasks and the threads it opens, gates every post through an independent review before it goes out, and converges each PR through bug verification, guardian, refactor and finality passes until nothing worth changing is left. Hooks enforce the parts that text alone didn't.

## Install

```sh
npx mergeworthy
```

It finds the coding agents on this machine, asks which to install into and how to set the options, and installs through each agent's own plugin system:

| Agent | Gets | Updates |
|---|---|---|
| Claude Code | the skills, the hooks, the `bin/` commands and the always-on rules | automatically |
| Codex | the skills, and the always-on rules in `~/.codex/AGENTS.md` | re-run `npx mergeworthy` |
| Others, through [skills.sh](https://skills.sh) | the skills | `npx skills update` |

Run it again to change the options or add an agent; `npx mergeworthy uninstall` removes it.

## Options

| Option | Values (default first) | What changes |
|---|---|---|
| `badge` | `on`, `off`, `auto` | The agent's icon and label at the start of every post; `auto`: only when posting from a human account. |
| `merge` | `on-request-squash`, `reviewer` | `reviewer`: the agent never merges. |
| `watcher` | `on`, `off` | `off`: no GitHub watcher. |

## How it reads

This is the work automation methodology (v3), split into skills along its own parts and sections, with the text and prompts as they were. `always-on.md` is in every session: the always-on rules, and an index of which skill to open when and which rule numbers it holds. Rule numbers (1.6, Part 3) work across skills.

| Skill | v3 |
|---|---|
| `core` | the task, Part 1: 1.0 triage, 1.1 principles, 1.2 tracking, 1.3 discovery, 1.8 safety, 1.11 reporting, 1.12 pre-flight |
| `design-loop` | 1.4 |
| `github-threads` | 1.5 the live GitHub loop, 1.6 the posting gate |
| `merging` | 1.7 |
| `delegating` | 1.9, 1.10 |
| `implement-issue` | Part 2 |
| `converge` | Part 3 |
| `verify`, `guardian`, `refactor`, `finality`, `review` | Part 3's passes and their prompts, Part 2's finality pass and reviewer charter |
| `past-failures` | Part 4 |
| `mechanisms` | Part 5 (the code itself lives in `hooks/`, `bin/` and `watcher/`) |

## How the passes connect

`docs/execution-graph.md` is the decision record (invariants, candidates, why two readers per PR), and `docs/graphs/` has one graph per entry point: the entry router, the Tier S and Tier M PR pipelines, the Tier L program, a comment, the other watcher events, and the posting gate (`.mmd` sources, rendered `.png`).

## Layout

```
always-on.md        the always-on rules and the index, in every session
skills/<name>/      one skill per part or pass of the methodology
hooks/              hooks.json and the scripts it runs
bin/                commands on the Bash PATH: gate-pass, post-lint, pr-steps, gh-watch-start
watcher/            the GitHub watcher daemon gh-watch-start runs
cli/                the npx mergeworthy installer
docs/               the execution graph and its rendered graphs
.claude-plugin/     the plugin manifest (options) and its marketplace
```

## Changing it

Edit here, commit and push; installed copies update through the plugin. To try a change first: `claude --plugin-dir .`.
