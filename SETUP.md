# Setup

Give one of these prompts to a Claude Code session on the machine. Each is complete on its own.

## Install

```text
Install the work methodology from https://github.com/nitedani/work-methodology on this machine:
1. Clone it to ~/work-methodology (or `git -C ~/work-methodology pull --ff-only` if it's already there).
2. Ask me which settings differ from the defaults: read profiles/defaults.env and the settings table in README.md, show
   them as a short list with the default first, and take my answers. If they match an existing profile in profiles/, use
   it; otherwise write profiles/local.env with only the changed keys (it stays untracked).
3. Run ./build.sh with those profiles (none for the defaults), then
   python3 mechanisms/install-methodology dist/<the built file>.
4. Optional parts, each only if I say yes:
   - GitHub watcher: nothing to install; `gh-watch-start` starts it on first use.
   - claude-swap: for each extra Claude subscription, `/login` to it, then `claude-swap save <name>`.
   - Local model (needs an NVIDIA GPU with 16 GB): follow local-model/README.md, then run local-model/install.sh.
5. Check it: ~/.claude/settings.json has the hooks, ~/.claude/CLAUDE.md has the methodology block, and
   `methodology-update` runs without an error. Report what you installed and what you skipped.
```

## Update

```text
Run `methodology-update` and report the commits it pulled (`git -C <repo> log --oneline <before>..<after>`). It
rebuilds with the same settings and reinstalls. Sessions also update themselves once a day at start (the SessionStart
hook); this is the manual way.
```

## Uninstall

```text
Run `uninstall-methodology`. Then tell me what it removed and what it kept: the repo clone, my artifacts,
~/.claude/gated-posts.txt, ~/.claude/pr-steps/ and the local model's files (~/local-llm, ~/local-llm-eval). Ask before
deleting any of those.
```
