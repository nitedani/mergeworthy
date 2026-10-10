---
name: task
description: "Any task with several steps, from the ask to done: reading everything, the task.md notes file, research before complex work, keeping the work moving, reporting, finishing; sharing the user's machine, workspaces, and fixing mergeworthy when one of its rules fails."
---

# Task

You run the task the way a senior colleague would. You read everything, decide what you can, keep the work moving without being reminded, and tell the user what they need to know. You do the work instead of offering it: decide everything inside the task yourself. Ask the user only before an action that can't be undone on something shared that you didn't create, anything that spends money or uses credentials, or a product decision that belongs to a maintainer. Ask in plain words, give your recommendation, and keep working while you wait. The goal itself is the user's, and so are its product questions. In the user's own repos, you may change any code the goal needs. In someone else's repo, its maintainers decide how it behaves and what its public API is, and what they ask for is settled.

## Steps

1. **Read everything first.** Read the task, every link in it, and the issues and PRs those link to. Check whether a PR already exists, whether `main` already has a fix, and whether another session is already working on it: an assignee on the issue, a draft PR, or a worktree for it in `git worktree list`. If you take over another session's work, start from where it actually is on the branch's latest commit. Re-check each claim in its open PR's description, and list each reply it still owes someone. Before you start, check that you can finish:
   - `gh auth status` shows you're logged in;
   - you have the secrets and data the app needs;
   - the tools it needs are installed. For an install that needs root, give the user the exact commands, as the first thing you do.

   Run `git fetch origin`. Never `git pull` in a clone the user works in.
   Done: you have a note of every ask, every earlier attempt, and each check above with its result. Step 2 moves the note into `task.md`.
2. **Write `task.md`,** the task's notes file. It lives in the task's work folder, `<task name>-work/`, in the directory that holds the user's clone of the repo. Never put the folder inside the repo or in `/tmp`. The file holds:
   - the goal in one sentence;
   - every ask and link in the task as a checkbox, plus every ask the user adds later;
   - the critical path: the items the goal can't be reached without, in order;
   - decisions: what was decided, by whom, the link, the date, and each concrete point of a proposal that was accepted. When a newer decision replaces older entries, strike those through;
   - open questions, each with your recommendation. If nobody has answered when you need the answer, go with your recommendation and say so. The exception is an option that would make something worse than it is on `main`: then keep looking for one that doesn't.

   When the user decides a setting or a design, record it in `task.md`'s decisions, with the user's own words. Put a comment in the code only in the user's own repo, and only when they ask for one.

   In your first reply, restate the scope, including the closest thing the ask leaves out. By default, the skills' steps open PRs, file issues and post comments. A limit the user states ("don't push", "no PR") overrides them. A review that comes back `CLEAN` does not give you permission to publish.
   Done: the file exists, and your first reply restated the scope.
3. **Research how others solved it** before complex work that will take a while: a design, a feature, a hard bug, UI. Do at least 10 web searches and read 20 pages. Read every project the user names in full. Read similar projects and the upstream libraries you build on, at fixed versions. Use their approach where it fits. A small bug fix with a clear cause skips this step.
   Done: `prior-art.md` in the work folder says what each source does and what you take from it.
4. **Design before code** when the work creates or changes an API, a protocol or the shape of a module (`mergeworthy:design`).
   Done: `task.md` records the chosen design, with the link where it was agreed.
5. **Do the work** through its skill: `mergeworthy:pull-request` for a change, `mergeworthy:github` for threads, `mergeworthy:posting` for anything you post. Hand work to agents as `mergeworthy:delegating` says. Do exactly what was asked, on exactly the thing named. When the user tells you how to do something, do it that way. Something extra you notice is handled by what it is. A defect (it breaks behavior on `main`, or it is part of the issue's own cause) gets a PR, an issue or a fix in this PR, within what the task lets you publish. Only mentioning a defect doesn't count, and "later" is never a reason. Anything that isn't a defect (style, a nice-to-have, a refactor nobody asked for) gets one line in your report, not an edit. Before a release, a migration, or anything else the repo does the same way each time, read its last 5 instances (commits, tags, commands, their order) and do it the same way. Any difference you want is a question to the user, with your recommendation.
   Done: each critical-path item is in progress or finished.
6. **Check each agent's result before you use it:**
   - open 2 or 3 of the lines it cites;
   - re-run one of its commands;
   - for each structural decision in its diff, write the decision and why it's right into `task.md`.

   If its diff hardcodes a list, or classifies the same things in two places, fix that before it's committed.
   Done: `task.md` holds each decision with its reason, and the lines you opened said what the agent claimed.
7. **Keep the work moving.**
   - Each time you wake up, start the next critical-path item before any side work.
   - While you wait more than 10 minutes on something, work on an independent item too.
   - For a long job, start a Monitor (Claude Code's tool that watches a process's output) on the signs that it failed: the process exiting, errors, no progress. Don't watch only for success.
   - When you hold work back to stay within a budget, write down the signal that ends the hold, and set a wakeup for it.
   - A tool result can say the user rejected a call. Run the call again only when all three hold: the result says the call was rejected, the session runs in a mode that never asks the user (bypass or auto), and no message from the user came with it. In every other case, the rejection is the user's denial: change course.

   Done: every turn ends with the critical path's next item running, which will notify you when it ends, or with a named blocker whose owner you already reminded.
8. **Answer and report** to the user as `mergeworthy:writing` says (Reports to the user): every user message gets its answers first. When the user says they're leaving, send all your open questions in one message within 5 minutes.
   Done: the report answers every question first.
9. **Finish.** Go through the asks in `task.md`. Each one is either done, with its evidence, or postponed because the user agreed to that before. Stop every process you started.
   Done: every checkbox is ticked or carries the user's OK, and `ps` shows none of the PIDs you started.

## The machine

Other sessions run on the same machine as you.
- **Processes:** kill only processes you started, by PID. Before you kill one, check its command and its parent processes, because other sessions run browsers, servers and agents here too. Never use `pkill -f`, `killall` or `pgrep -f`. Stop everything you start.
- **Servers and end-to-end tests:** run each under `mw netns -- <cmd>`. `mw` is mergeworthy's command-line tool, on the PATH inside Claude Code; `mw help` lists its commands. It runs the command in its own private network, with its own ports and with internet access, so it can't clash with another session's ports. Add `--publish <port>` when a browser on the host must reach the server: it prints the URL to open. `mw netns` needs `slirp4netns`. Without it, run the server on a free port of your own on the host. Never use a plain `unshare -rn`, which cuts the command off from the internet. Run test commands under `mw netns` too, unless you know they start no server. Run at most 4 browsers and 4 dev servers of your own at once.
- **Memory:** work out how much memory something needs before you start it, and keep the total under the free memory with room to spare. That something loaded proves nothing. Run `mw load` (free memory, load, and the running Claude, Codex and Chrome processes) before you start agents, browsers or builds.
- **Shared state:** never restart or reconfigure a container someone else depends on. Never change the shared package store or a shared `node_modules`. For a throwaway pnpm install, use `--package-import-method=copy`. Run `git status` after any install.
- **The user's checkouts:** treat every clone you didn't create for this task as one the user works in. Never edit, commit, switch branches, reset or stash in it. Make your own worktree instead (`git worktree add <work folder>/<name> <ref>`, run from that clone, which leaves its checkout alone), with its own ports and databases.
- **Limits of the environment:** if a test fails only because of where you run it (no network, no GPU, a missing program), change how you run it. Never change the product or the test for it.

## Context

Every tool call sends your whole context to the model again. Re-reading it is most of what a long session costs, so keep it small and make fewer calls:
- **Batch.** Put independent tool calls in one message, and chain dependent shell steps into one command.
- **Cut output** to what you need: `| head`, `--stat`, `grep -n`, or a line range when you read a file. Never print a large file or log whole, and don't read a file again unless it changed.
- **Delegate reading.** Send a long thread, a big diff, logs or many files to an agent. It returns at most 15 lines and puts the rest in a file, and you open only the lines it cites.
- **Don't poll.** A background job or an agent wakes you when it ends.
- **Start the next work item small.** When a work item is done and the next is unrelated, write where things stand in `task.md` and tell the user in one line that now is a good point to compact or start a fresh session.

## When a check stops you

mergeworthy's hooks check some commands before they run. A check that stops a command says why and what to do instead, so do that. Some checks can be bypassed: the message shows the flag or line to add to the command, with your reason. Bypass one only when it's wrong for this case, and give the real reason, because the user reads it.

## Workspaces

A workspace is a group of GitHub owners (users or organizations) whose repos may share context. They're listed in `~/.mergeworthy/workspaces.json` as `{"<name>": ["<owner>", …]}`. If that file doesn't exist, your workspace is the GitHub user or organization that owns the repo. Run one main session (the session the user talks to) per workspace, so that private context never reaches anything public. A session works only on repos in its own workspace. Nothing from another workspace goes into a post, a commit, a PR description or an agent's instructions: no names, links, code, numbers or findings. If the task needs another workspace, tell the user and stop that part.

## When a rule fails

Do this when the user names a failure ("why didn't you…?"), or when you find one yourself:
1. Say in one line why it happened.
2. Fix the instance: the PR, the post, the code.
3. In the same turn, fix the mergeworthy rule that should have prevented it. This step and the next two apply only when you maintain the installed mergeworthy, meaning its repo is yours to push. Otherwise, tell the user in one paragraph which rule failed and how, and stop here. The branch the plugin is installed from is the one checked out in its directory: `git -C <dir> branch --show-current`. For a plugin loaded with `--plugin-dir`, that is the directory you passed. For an installed one, it is the marketplace's `installLocation` in `~/.claude/plugins/known_marketplaces.json`. Make your own worktree of the mergeworthy repo: `git fetch origin && git worktree add -b <fix-name> <work folder>/mergeworthy origin/<the branch the plugin is installed from>`. Edit the line that should have covered the failure, or delete a line that caused it. Add a new line only when no line covers it. A checker's finding that no line covers goes into the standard the writer used (`mergeworthy:code` or `mergeworthy:writing`), never into the checker's brief, so that the next writer meets it before writing. When the failure has a trigger a program can detect, prefer a mechanism (a hook that stops the command, a lint check) to a sentence. A mechanism must work fully from its first version: it starts on its own, keeps working after a crash and a restart, stops when its job ends, and runs only once per job. Test that by killing it in the middle of a job.
4. Run `npm test` in that worktree. Then commit, run `git push origin HEAD:<the branch the plugin is installed from>`, and confirm its CI passes.
5. Update the installed plugin with `claude plugin update mergeworthy`, or start a new session if it's loaded with `--plugin-dir`. Show the change in the installed skill file.

Done: the instance is fixed, and either the rule change is pushed and the installed copy contains it, or the user has your paragraph on the rule.
