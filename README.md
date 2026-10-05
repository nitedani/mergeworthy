# mergeworthy

A working method for an AI coding agent on GitHub: it acts as your second brain across your tasks and the threads it opens, checks every post with a fresh reader before it goes out, and converges each PR until no reader finds anything worth changing. Hooks enforce the parts that text alone didn't.

## Install

```sh
npx mergeworthy
```

It finds the coding agents on this machine, asks which to install into and how to set the options, and installs through each agent's own plugin system:

| Agent | Gets | Updates |
|---|---|---|
| Claude Code | the pages, the hooks, the commands and the always-on rules | automatically |
| Codex | the pages, and the always-on rules in `~/.codex/AGENTS.md` | re-run `npx mergeworthy` |
| Others, through [skills.sh](https://skills.sh) | the pages | `npx skills update` |

Run it again to change the options or add an agent; `npx mergeworthy uninstall` removes it.

## Options

| Option | Values (default first) | What changes |
|---|---|---|
| `badge` | `on`, `off`, `auto` | The agent's icon and label at the start of every post; `auto`: only when posting from a human account. |
| `merge` | `on-request-squash`, `reviewer` | `reviewer`: the agent never merges. |
| `watcher` | `on`, `off` | `off`: no GitHub watcher. |

## How it reads

`always-on.md` is in every session: the principles, and an index of which page to open when. Each page in `skills/` covers one moment (a task arrived, about to post, about to call a PR ready…) and is opened only when that moment comes.

## Layout

```
always-on.md        principles and the index, in every session
skills/<page>/      one page per moment: SKILL.md, plus the reference files it links
hooks/              hooks.json and the scripts it runs
bin/                commands on the Bash PATH: gate-pass, post-lint, pr-steps, gh-watch-start
watcher/            the GitHub watcher daemon gh-watch-start runs
cli/                the npx mergeworthy installer
.claude-plugin/     the plugin manifest (options) and its marketplace
```

## Writing a page

Every `SKILL.md` has the same shape, under 450 words:

```markdown
---
name: <page>
description: "When <moment>: <what the page gives>."
---

## When
One sentence.

## Steps
1. Imperative verb first, one or two sentences.
2. A step that branches by case uses one nested list:
   - **Case:** action.

## Done when
One sentence.

## Never
- Imperative, at most four.

## Enforced by
`mechanism` (what it blocks), or "Nothing: this is judgment."

## Next
`mergeworthy:<page>` and when, or "Nothing."
```

Principles are written in bold exactly as named in `always-on.md`, pages as `mergeworthy:<page>`, files and commands in backticks. Examples are generic; nothing names a particular project.

## Changing it

Edit here, commit and push; installed copies update through the plugin. To try a change first: `claude --plugin-dir .`.
