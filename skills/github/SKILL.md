---
name: github
description: "Any GitHub thread you're in, and everything you post: the live loop (mw watch, whose comments, how each kind is answered, /agent), the umbrella issue, waiting and nudging, thread rules, the posting steps, and opening an issue."
---

# GitHub

A maintainer's comment is handled like the user typing in this chat: first, with full effort. Every post brings something the reader didn't have, and nothing they already have. You carry the load: what can be decided or measured, you do, and you ask only what is truly theirs.

## Steps

The live loop, from your first post until every thread you're in is merged or closed:

1. **Watch every thread you're in.** Run `mw watch <url> …` with `run_in_background` and the longest timeout. It exits when events arrive (comments, reviews, inline comments, red CI, merge, close, conflict) and prints the command to re-arm it. A session that handles `/agent` comments for its workspace adds `--commands --workspace <name>`.
   Done: a watch is running with every open thread you're in.
2. **On each event, decide whether it's yours,** and re-arm the watch in the same step.
   - **On a thread you opened:** every human comment and every review bot's inline finding.
   - **On a thread you only posted in:** a maintainer's comment or the user's.
   - **Anywhere in your workspace:** the user's `/agent <instruction>`, which is the user typing in this chat: start it now, in parallel with what's running.
   - **The user's own comments** in a watched thread are instructions too: answer them in the session, not in the thread.

   React 👀 to each comment that's yours when you start on it (reviews can't take reactions).
   Done: every event is handled or marked not yours, and the watch is re-armed.
3. **Answer by kind** (How each comment is answered, below). If the answer needs more than about an hour of work, post a holding reply first that carries what you found so far and when the answer comes.
   Done: the reply is posted (Posting, below), as a new comment, because edits don't notify.
4. **Record it in the same step.** A decision goes into `task.md` with its permalink; a change to the agreed or open list goes into the umbrella issue's body.
   Done: `task.md` and the umbrella body are true of the thread.
5. **Red CI on your PR is the maintainer's first question.** Fix it. When the red isn't the PR's doing (a secret forks don't get, a flaky job), say so on the PR at once, with the evidence.
   Done: CI is green, or the PR carries a comment explaining the red.
6. **Drive the goal at every wakeup.** Name the critical path's next item and move it. A dependency that lands (a merge or release you wait on) is handled like a maintainer comment: apply what waited on it and post the progress on the dependent PR.
   Done: the wakeup moved an item, not only confirmed that nothing waits on you.

## How each comment is answered

- **An instruction** ("Let's…", "Remove…") or a suggestion block: do it, then reply "Done in <sha>".
- **A critical question about your own work** ("Is it all DRY?", "Is this tested?", "Why this comment?") is a request: fix it, push, and reply with what was missing and the commit. Ask first only when the fix would change behavior or scope.
- **A question about a decision** ("Why X?", "How about Y?", "Overkill?") gets an answer, not a code change that reverses the decision before they answer. "Why X?" gets the reason, and if X now looks wrong, say so with your recommendation. "How about Y?" starts with yes or no and the one real obstacle. When their idea is simpler than yours, recommend theirs.
- **A design question:** think before replying.
  1. Trace the actual flow in code, every path to the same thing. Done: you can name the gap with `file:line`.
  2. Have one fresh Opus agent argue both sides from at least three frames (the user who hits it, the maintainer who keeps it, the smallest diff, no new code, the design from scratch), then score them. Done: its recommendation is written down.
  3. Decide. Before answering "keep", build the simpler version and name what breaks in it; if nothing breaks, recommend the simpler one. Done: your position, with the evidence for it.

  "First principles" or "perfect world" means the ideal design; leave out migration, release and option-visibility costs until asked. A thread that drifted through three or more rounds gets the finality pass first (`work`).
- **A short acknowledgement** ("OK", 👍) answers your last open proposal or question in that thread, or your latest one just before it in the same PR. That proposal is now an instruction.
- **A 👍 or 👎 on your comment** is feedback on that comment. For a 👎, find out why and fix the rule behind it (`work`, When a rule fails).
- **Commits a maintainer pushed to your PR:** fetch and run the gates. Then review each commit in one table, `| Commit | What it does, and the idea behind it | Rating |`: a rating below 10 carries its reason, and findings come with the exact fix. Don't push while they're committing.
- **"I don't understand this"** on a docs or comment line reports a bug in that text. Push clearer wording and reply "Done in <sha>: <new sentence>".
- **A bot's finding** is a reviewer's finding: run its case first, then reply with the fix's commit or the output that declines it.

## The umbrella issue

Any goal that needs two or more PRs or issues gets one umbrella issue, `Tracking: <goal>`. Use the issue the user names, or turn the program's own issue into it; open a new one only when neither exists.

1. **Body:** one sentence on what it tracks and what has to land. Then:
   - `## TODO`: each PR and issue as a checkbox, `- [x] owner/repo#N (merged): <what a user hit on main>`, and work with no PR yet, with what it waits on;
   - `## Agreed`: each point with the permalink where it was agreed;
   - `## Open`: each item with who it waits on and your recommendation.

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

## Posting

Everything that reaches GitHub goes through these steps: comments, replies, inline comments, reviews, PR and issue bodies, edits of any of them, and gists. Reactions don't.

1. **Read the whole thread** from its first comment, the threads it links and your own earlier replies: `mw thread <ref>`. For a long thread, an Opus drafter reads it and drafts from your brief (the question, your position and reasons), and returns the draft plus every conflict with a past decision, each with its permalink.
   Done: you know every question still open and every decision already made in the thread.
2. **Draft it by `writing`** into a file in the task's work folder (`drafts/<name>.md`), never straight into a command.
   Done: the draft file exists.
3. **Lint it:** `mw lint <draft> --repo <owner/repo> --kind <reply|design|pr|issue>`. Fix every error.
   Done: `mw lint` exits 0.
4. **Review it** (`review`, with the posting checks). Fix the draft and re-review until the reviewer's verdict is `CLEAN`.
   Done: `<draft>.verdict.json` says `CLEAN` for the current text.
5. **Re-check every claim against the current head** right before posting: `git fetch`, and confirm every referenced commit is pushed.
   Done: every claim and link holds on the head.
6. **Post it:** `mw post <draft> -- gh <command with --body-file <draft>>`, or `-F body=@<draft>` for API posts. A one-line acknowledgement or "Done in <sha>" may bypass the review with the reason in the flag.
   Done: `mw post` printed the URL, and the thread is in your watch.

## Opening an issue

1. **Should it be a PR instead?** Find the fix first; an obvious fix for a defect you hit is a PR, upstream included. File an issue only when you can't find a fix, or when the fix needs the owner's product decision.
   Done: you know why it's an issue and not a PR.
2. **Already filed or fixed?** Run `gh issue list --state all --search "<keyword>"` and `git log --oneline origin/<base> -- <files>`. An existing issue gets your finding as a comment, not a twin.
   Done: no twin, and no fix on the base.
3. **Reproduce it on today's base** from a clean start, as a user meets it. What you can't reproduce isn't filed.
   Done: a screenshot, video, or request and response that shows it.
4. **Write the body** by `writing` (Forms), with `### How to reproduce` and the evidence. A decision issue adds `### Options`, showing what a user sees under each option, plus your recommendation.
   Done: a newcomer could reproduce it from the body alone.
5. **Post it** (Posting, above) and add it to the watch.
   Done: the posted body shows its evidence.
