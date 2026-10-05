<p align="center"><img src="docs/icon.svg" width="96" height="96" alt="mergeworthy"></p>

# mergeworthy

Work with an AI coding agent through GitHub, the way you work with a coworker. You give it an issue or a request, then review its PR and answer its questions on the thread. You don't prompt it step by step or babysit a chat.

- **It ships merge-ready PRs.** Before you see a PR, the agent has hunted for bugs, reviewed the change and simplified it. A UI or runtime change is also checked in the real app.
- **It keeps its threads moving.** It watches its PRs and issues, and answers every review comment, bot finding and red CI run. When a PR it depends on lands, it updates its own.
- **It writes for busy reviewers.** A post leads with what the agent needs from you, gives one decision with its pick, and links the long material. An independent review checks every post before it goes out.
- **It asks only what isn't its to decide.** That means irreversible actions on shared state, money, credentials or your global config, a maintainer's product decision, and a fork it can't rank. Everything else it decides, does and reports.
- **Hooks hold the line.** Hooks block an unreviewed post, a PR marked ready without its review, and a third comment in a row within three hours.

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

## What's inside

`always-on.md` is loaded in every session: the rules that always apply, and when to open each skill.

| Skill | What it covers |
|---|---|
| `core` | triage, principles, tracking, discovery, safety, reporting |
| `implement-issue` | from an issue to a merge-ready PR |
| `github-threads` | watching threads, answering, and the review every post passes; `voice.md` is how posts sound (yours wins from `~/.mergeworthy/voice.md`) |
| `merging` | pushing, ready, merge |
| `design-loop` | designing an API, protocol or module |
| `converge` | the passes a PR runs until nothing worth changing is left |
| `verify`, `review`, `refactor`, `guardian`, `finality` | the passes: bug hunt, review, refactor, bloat and quality, rework of drifted code |
| `delegating` | briefing subagents and checking their work |
| `past-failures` | failures that happened, and the rule that now covers each |
| `mechanisms` | the watcher, hooks and commands that enforce the rules |

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
