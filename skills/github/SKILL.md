---
name: github
description: "Any GitHub thread you're in: mw watch, whose comments are yours, how each kind is answered, /agent, the umbrella issue, waiting and nudging, and the thread rules."
---

# GitHub

A maintainer's comment is handled like the user typing in this chat: first, with full effort. Every post brings something the reader didn't have, and nothing they already have. You carry the load: what can be decided or measured, you do, and you ask only what is truly theirs.

## Steps

The live loop, from your first post until every thread you're in is merged or closed:

1. **Watch every thread you're in.** Run `mw watch <url> …` with `run_in_background` and the longest timeout. It exits when events arrive (comments, reviews, inline comments, a 👍 or 👎 on your comment, someone else's push to your PR, red CI, merge, close, conflict) and prints the command to re-arm it. The session that handles `/agent` comments for its workspace adds `--commands --workspace <name>`: a key of `~/.mergeworthy/workspaces.json`, or a single GitHub owner when the file doesn't list it.
   Done: a watch is running with every open thread you're in.
2. **On each event, decide whether it's yours,** and re-arm the watch in the same step.
   - **On a thread you opened:** every human comment and every review bot's inline finding.
   - **On a thread you only posted in:** a maintainer's comment or the user's.
   - **Anywhere in your workspace:** the user's `/agent <instruction>`, which is the user typing in this chat: start it now, in parallel with what's running.
   - **The user's own comments** in a watched thread are instructions too: answer them in the session, not in the thread.

   React 👀 to each comment that's yours when you start on it: `gh api repos/<o>/<r>/issues/comments/<id>/reactions -f content=eyes`, or `pulls/comments/<id>/reactions` for an inline comment. Reviews can't take reactions.
   Done: every event is handled, or listed in `task.md` as not yours with why, and the watch is re-armed.
3. **Answer by kind** (How each comment is answered, below). If the answer needs more than about an hour of work, post a holding reply first that carries what you found so far and when the answer comes.
   Done: the answer is posted (`posting`) as a new comment, because edits don't notify. After a holding reply, the answer is that new comment; anything more before someone replies edits it.
4. **Record it in the same step.** A decision goes into `task.md` with its permalink; a change to the agreed or open list goes into the umbrella issue's body.
   Done: `task.md` and the umbrella body are true of the thread.
5. **Red CI on your PR is the maintainer's first question.** Fix it. When the red isn't the PR's doing (a secret forks don't get, a flaky job), say so on the PR at once, with the evidence.
   Done: CI is green, or the PR carries a comment explaining the red.
6. **Drive the goal at every wakeup.** Name the critical path's next item and move it. A dependency that lands (a merge or release you wait on) is handled like a maintainer comment: apply what waited on it and post the progress on the dependent PR.
   Done: the wakeup moved an item, not only confirmed that nothing waits on you.

## How each comment is answered

- **An instruction** ("Let's…", "Remove…") or a suggestion block: do it, then reply "Done in <sha>". Once you've said yes to a request ("Yes, I'm splitting it"), do exactly that; if the work leads elsewhere, say so in the thread before you deviate.
- **A critical question about your own work** ("Is it all DRY?", "Is this tested?", "Why this comment?") is a request: fix it, push, and reply with what was missing and the commit. Ask first only when the fix would change behavior or scope.
- **A question about a decision** ("Why X?", "How about Y?", "Overkill?") gets an answer, not a code change that reverses the decision before they answer. "Why X?" gets the reason, and if X now looks wrong, say so with your recommendation. "How about Y?" starts with yes or no and the one real obstacle. When their idea is simpler than yours, recommend theirs.
- **A design question:** think before replying.
  1. Trace the actual flow in code, every path to the same thing. Done: the gap is written in `task.md` with its `file:line`.
  2. Have one fresh Opus agent argue both sides from at least three frames (the user who hits it, the maintainer who keeps it, the smallest diff, no new code, the design from scratch), then score them. Done: its report is in the work folder.
  3. Decide. Before answering "keep", build the simpler version and name what breaks in it; if nothing breaks, recommend the simpler one. Done: your position and its evidence are in `task.md`.

  "First principles" or "perfect world" means the ideal design; leave out migration, release and option-visibility costs until asked. A thread that drifted through three or more rounds gets the finality pass first (`finality`).
- **A short acknowledgement** ("OK", 👍) answers your last open proposal or question in that thread, or your latest one just before it in the same PR. That proposal is now an instruction.
- **A 👍 or 👎 on your comment** is feedback on that comment. For a 👎, find out why and fix the rule behind it (`task`, When a rule fails).
- **Commits a maintainer pushed to your PR** (a `PUSH` event): fetch, fast-forward, and run the gates. Then review each commit in one table, `| Commit | What it does, and the idea behind it | Rating |`: a rating below 10 carries its reason, and findings come with the exact fix. Don't push while they're committing.
- **"I don't understand this"** on a docs or comment line reports a bug in that text. Push clearer wording and reply "Done in <sha>: <new sentence>".
- **A bot's finding** is a reviewer's finding: run its case first, then reply with the fix's commit or the output that declines it.

## The umbrella issue

Any goal that needs two or more PRs or issues gets one umbrella issue, `Tracking: <goal>`. Use the issue the user names, or turn the program's own issue into it; open a new one only when neither exists.

1. **Body:** `# 🚧 WIP`, then *This issue is edited upon updates.*, then:
   - `## TLDR`: two or three sentences, the goal and where it stands;
   - `## Scope`: what's in and what's out;
   - `## State`: three or four high-level bullets;
   - `## TODO`: each PR and issue as a checkbox, `- [x] owner/repo#N (merged): <what a user hit on main>`, and work with no PR yet, with what it waits on;
   - `## Agreed`: each point with the permalink where it was agreed;
   - `## Open`: each item with who it waits on and your recommendation;
   - `## Next steps`: your recommended order.

   Done: every line has a source link.
2. **Edit it in place** in the same step as every event: a PR merges, a decision lands, an item opens. A new decision strikes through, with its link, the older entries it replaces.
   Done: the body is true of every linked thread.
3. **Replies never repeat its lists.** When one changed, say so in one line with a link ("I updated the [tracking issue](link)").
   Done: no reply restates the agreed or open list.

## Waiting and nudging

- **No @-mention** unless you're blocked on that person now, and never while they're mid-review or after they said they're busy. Then it's one mention with the decisions you need, each with your recommendation (`mw lint` stops other mentions).
- **No release requests** unless the downstream work is ready to use the release now and the user agreed.
- **Open quick-win PRs without asking:** a small fix for a bug that already breaks today and is independent of the open discussion.
- **Harness changes** are shown to a maintainer only when they ask, in one place.

## Thread rules

- **One reply per person.** Several comments from one person get one reply. Corrections are edits of your earlier post.
- **At most two of your comments in a row.** A third edits your last one (`mw post` stops it).
- **Post in the thread where the person wrote.** Read the repo's `AGENTS.md` / `CLAUDE.md` on the target branch before a commit, merge or PR there.
- **Evidence carries no secret:** write `<REDACTED>` for every token, cookie, auth header and key.
- **Only the main session posts.** Agents hand it drafts.
