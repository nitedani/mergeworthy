---
name: github
description: "Any GitHub thread you're in: watching threads with mw watch, which comments you answer, how each kind is answered, /agent comments, the tracking issue, waiting and reminding, and the thread rules."
---

# GitHub

Handle a maintainer's comment the way you handle the user typing in this chat: first, and with full effort. Every post brings the reader something they didn't have, and nothing they already have. You carry the load: what can be decided or measured, you decide or measure, and you ask only what truly belongs to them.

You post from the user's GitHub account. Your posts start with an agent icon on the first line (`mergeworthy:writing`, Forms), and that is how `mw` tells your comments apart from the user's own.

## Steps

From your first post until every thread you're in is merged or closed, repeat these steps:

1. **Watch every thread you're in.** Run `mw watch <url> …` with every open issue and PR you're in, using `run_in_background` and the longest timeout. It checks the threads on GitHub every minute. It exits as soon as something happens, or after about two hours with nothing new. Either way it prints what happened and the exact command to start it again. These count as events:
   - a comment, a review, or an inline comment on the code;
   - a 👍 or 👎 on one of your comments;
   - someone else pushing to your PR;
   - a failing CI check;
   - a merge, a close, or a merge conflict.

   Restarting the watch with the printed command is called re-arming it. After a session resumes, or after its context is compacted, re-arm the watch before anything else, and handle what it reports.

   The user can also give you work from GitHub. A comment they write that starts with `/agent`, on any issue or PR in their repos, is an instruction to you, as if they typed it in this chat. Only one session picks these comments up for a given workspace (a group of repos that may share context, `mergeworthy:task`, Workspaces), so that two sessions never do the same instruction. If this session is that one, add `--commands --workspace <name>` to the `mw watch` command. `<name>` is one of the groups listed in `~/.mergeworthy/workspaces.json`, or, if that file doesn't list it, the GitHub user or organization that owns the repos.
   Done: a watch is running with every open thread you're in.
2. **On each event, decide whether it's yours to answer,** and re-arm the watch in the same step. These are yours:
   - **On a thread you opened:** every comment from a person, and every inline finding from a review bot.
   - **On a thread where you only posted:** a comment from a maintainer or from the user.
   - **Anywhere in your workspace:** the user's `/agent <instruction>` comment. Treat it as the user typing in this chat: start on it now, alongside what's already running.
   - **The user's own comments** in a watched thread (from their account, without the agent icon) are instructions to you too. Answer them here in the session, not in the thread.

   When you start on a comment that's yours, react to it with 👀: `gh api repos/<o>/<r>/issues/comments/<id>/reactions -f content=eyes`, or `pulls/comments/<id>/reactions` for an inline comment. Reviews can't take reactions.
   Done: every event is handled, or listed in `task.md` as not yours with the reason, and the watch is re-armed.
3. **Answer each comment by its kind** (How each comment is answered, below). If the answer needs more than about an hour of work, first post a holding reply: what you found so far, and when the full answer will come. Do work you can finish in minutes before you reply, so the reply can say "Done in <sha>". When you promise something in a post, keep the promise in `task.md` until the commit or link that delivers it exists. After a burst of comments, check that every comment got a change, an answer or a reaction from you.
   Done: the answer is posted (`mergeworthy:posting`) as a new comment, because edits don't send notifications. After a holding reply, the full answer is that new comment. If you have more to add before anyone replies, edit it into that comment.
4. **Record it in the same step.** Write a decision into `task.md` with its permalink. When the list of agreed or open points changes, update the tracking issue's description (The tracking issue, below). When a decision replaces a design, update everything that still describes the old one in the same step: code, tests, types, docs, and the descriptions of open PRs.
   Done: `task.md` and the tracking issue match what the thread says.
5. **Treat failing CI on your PR as the maintainer's first question.** Fix it. When your PR didn't cause the failure (a secret that PRs from forks don't get, a flaky job), say so on the PR right away, with the evidence. Rerunning a job in an upstream repo needs admin rights. A first-time contributor's PR from a fork waits for a maintainer to approve its workflow runs.
   Done: CI passes, or the PR has a comment explaining the failure.
6. **Move the goal forward each time you wake up.** Name the next item on the critical path (the items the goal can't be reached without) and move it. Also check the releases and PRs you wait on that aren't in your watch. When something you wait on lands (a merge or a release), handle it like a maintainer's comment: apply the work that waited on it, and post the progress on the PR that depends on it.
   Done: the wakeup moved an item forward, not only confirmed that nothing waits on you.

## How each comment is answered

- **An instruction** ("Let's…", "Remove…") or a suggested change: do it, then reply "Done in <sha>". Once you've agreed to a request ("Yes, I'm splitting it"), do exactly that. If the work leads elsewhere, say so in the thread before you change course.
- **A critical question about your own work** ("Is it all DRY?", "Is this tested?", "Why this comment?") is a request. Fix it, push, and reply with what was missing and the commit. Ask first only when the fix would change behavior or scope.
- **A question about a decision** ("Why X?", "How about Y?", "Overkill?") gets an answer. Don't reverse the decision in code before they answer. Until then, also don't change those lines for a finding from your own reviews (`mergeworthy:converge`). Never agree with a premise you haven't measured. "Why X?" gets the reason, and if X now looks wrong, say so with your recommendation. "How about Y?" starts with yes or no and the one real obstacle. When their idea is simpler than yours, recommend theirs.
- **A design question:** think before you reply.
  1. Trace the actual flow in the code, every path that reaches the same thing. Done: `task.md` describes the gap with its `file:line`.
  2. Have one fresh Opus agent argue both sides from at least three points of view, then score them. Points of view to pick from: the user who runs into it, the maintainer who keeps it, the smallest diff, no new code, the design from scratch. Done: its report is in the work folder.
  3. Decide. Before you answer "keep it as it is", build the simpler version and name what breaks in it. If nothing breaks, recommend the simpler one. When your answer shows the defect is a whole class (a default, a parser, a shared helper), recommend the fix for the whole class with its evidence, not only for this instance. Done: your position and its evidence are in `task.md`.

  "First principles" or "perfect world" asks for the ideal design: leave out the costs of migration, releases and which options users see, until they ask. If the thread has gone through three or more rounds without settling, run the finality pass first (`mergeworthy:finality`).
- **A short acknowledgement** ("OK", 👍) answers your last open proposal or question in that thread. If there is none, it answers your latest one just before it in the same PR. That proposal is now an instruction. "The rest LGTM" agrees to every proposal in that comment it doesn't question: record each one and start.
- **A 👍 on a proposal** approves it, as an instruction. Any other 👍 or 👎 on your comment is feedback on that comment. For a 👎, find out why, and fix the rule that led to it (`mergeworthy:task`, When a rule fails).
- **Commits a maintainer pushed to your PR** (a `PUSH` event from `mw watch`): fetch, fast-forward, and run the repo's checks. Then review the commits in one table, `| Commit | What it does, and the idea behind it | Rating |`. A rating below 10 comes with its reason, and each finding with the exact fix. Don't push while they're still committing.
- **"I don't understand this"** on a line of docs or a code comment reports a bug in that text. Push clearer wording and reply "Done in <sha>: <new sentence>".
- **An inline comment:** before acting on it, check that its reason fits the line it's attached to. If it fits another line better, ask which one they meant.
- **A bot's finding** counts the same as a reviewer's. Run its case first, then reply with the commit that fixes it, or with the output that shows it doesn't apply.

## The tracking issue

A goal that needs two or more PRs or issues gets one tracking issue, titled `Tracking: <goal>`. Use the issue the user names, or turn the project's existing issue for the goal into it. Open a new one only when neither exists. When the goal's design is discussed in a maintainer's issue, don't open a new one. Instead, post a comment in that issue starting with `# 🚧 WIP` (the WIP comment), and keep editing it. It plays the role of the tracking issue.

1. **Its description:** `# 🚧 WIP`, then the line *This issue is edited upon updates.* (or *comment* instead of *issue*, for a WIP comment), then these sections:
   - `## TLDR`: two or three sentences, the goal and where it stands;
   - `## Scope`: what's in and what's out;
   - `## State`: three or four high-level bullets;
   - `## TODO`: each PR and issue as a checkbox, like `- [x] owner/repo#N (merged): <what a user ran into on main>`, plus work that has no PR yet, with what it waits on;
   - `## Agreed`: each point, with the permalink where it was agreed;
   - `## Open`: each item, with who it waits on and your recommendation;
   - `## Next steps`: the order you recommend.

   `mw lint <draft> --kind umbrella` checks these headings and their order.
   Done: every line has a link to its source.
2. **Edit it in place** in the same step as each event: a PR merges, a decision is made, a new item comes up. When a new decision replaces older entries, strike them through, with the link to the new decision. A line about the future names the event that will remove it.
   Done: the description matches every linked thread.
3. **Replies never repeat its lists.** When one changed, say so in one line with a link ("I updated the [tracking issue](link)").
   Done: no reply restates the agreed or open list.

## Waiting and reminding

- **Remind people once per wait,** after about 3 hours of silence on your last comment, and only when the wait blocks your next step right now. Otherwise write in `task.md` what will end the wait. Never @-mention someone in the middle of their review, or after they said they're busy. The reminder is one @-mention with the decisions you need, each with your recommendation. `mw lint` reports every @-mention as an error, so post this one with `mw post`'s bypass flag, and give the reminder as the reason (`mergeworthy:posting`, step 6).
- **Don't ask for a release** unless the work that needs it is ready to use it now, and the user agreed.
- **Open small PRs without asking** when they fix a bug that already breaks things today and don't depend on the open discussion.
- **Changes to mergeworthy itself** (its skills, hooks and tools) are shown to a maintainer only when they ask, and in one place.

## Thread rules

- **One reply per person.** Several comments from one person get one reply. To correct something you posted, edit that post.
- **At most two of your comments in a row.** Instead of a third, edit your last one. `mw post` refuses a third.
- **Reply in the thread where the person wrote.** Before you commit, merge or open a PR in a repo, read its `AGENTS.md` / `CLAUDE.md` on the target branch.
- **Evidence never contains a secret:** write `<REDACTED>` for every token, cookie, auth header and key.
- **Only the main session posts.** Agents hand it drafts.
