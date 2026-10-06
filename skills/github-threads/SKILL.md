---
name: github-threads
description: "Any GitHub thread you're in: the live loop (watcher, 👀, replies, which threads are yours) and the posting gate every post, edit and PR body passes."
---

## 1.5 The live GitHub loop (every tier, from your first post until every thread you're in is merged or closed)

**A maintainer's comment is handled like the user typing in this chat:** highest priority, full effort.

**Red CI on your PR is the maintainer's first question.** Fix it. When the red isn't the PR's doing (a secret forks don't get, a flaky job), say so on the PR right away. One comment gives the cause and the evidence: the workflow line, or the same failure on another PR or `main`. Explaining it only in chat leaves the PR looking broken.

**Which comments you answer.** Answer these, and nothing else:
- **On a thread you opened:** everything a person would answer on their own PR. That is every human's comment (maintainer, contributor, the user) and every inline finding of a review bot (CodeRabbit and the like; a bot's summary comments ask nothing).
- **A bot's finding is a reviewer's finding:** run its case first (`review`), then reply with the fix's commit or the output that declines it.
- **On a thread you only posted in:** a maintainer's comment (write access to the repo) or the user's.
- **On any other thread:** the user's comment, when it contains `/ai` or `/agent`.
- **What the watcher does with them:** it reports exactly these comments and adds 👀 to each (GitHub has no reactions on reviews). It records each comment and review in `replies-owed.md`.
- **A `/ai` comment is the user typing in this chat.** Start the work at once, in parallel with what's running rather than queued behind it. Follow the skill the comment calls for (`pull-request` for "fix it" or "open a PR"), and tell the user in chat.

Each comment you answer goes through these steps:

1. **Within 10 seconds:** 👀 reaction. The watcher does this.
2. **The answer, or a holding reply.** Answer through the gate (1.6). Only when the answer needs long work (more than about 15 minutes) post a holding reply first, through the fast gate, and make it carry something: what you've found so far, and when the answer comes. Before acting on any comment, check that its reason fits the line it's anchored to; if the reason fits another line better, ask before changing anything.
   - **An instruction** ("Let's…", "Remove…", "Merge origin/main") or a suggestion block: do it, then reply "Done in <sha>."
   - **A question or soft suggestion** ("Overkill?", "How about…?", "why…?", "I think we can…") gets an answer, never a code change until they answer it. "How about X?" or "Is X possible?" starts with yes or no and the one real obstacle. When their idea is simpler than yours, recommend their idea. If the answer needs work, say what you're checking ("Measuring the calls"); never agree with a premise or promise a change you haven't measured. Hold any loop finding on the questioned lines until they answer.
   - **A short acknowledgement** ("OK", "Good!", 👍) is not the end of the thread: read the whole thread to find what the acknowledgement answers. It answers your last open proposal or question in that thread. If that thread has none, it answers your latest open proposal or question elsewhere in the same PR, posted just before the acknowledgement. That proposal is now an instruction. If the acknowledgement could answer two, do both if they don't conflict; otherwise ask which in one line. Only an acknowledgement of a finished change needs nothing but a 👍.
   - **A 👍 or 👎 reaction** from the user or a maintainer on one of your comments is feedback on that comment. For 👍, note what they liked and reinforce the rule that produced it; on a proposal, the 👍 is also the approval. For 👎, work out why and fix the rule behind it (1.1.12). Then, if the thread is still on that point, post a new reply with the fix that @-mentions them. If the thread has moved on, edit the 👎'd comment to add how you'll do better. Leave the 👎 either way.
   - **A maintainer's commits pushed to your PR** (the watcher's `### MAINTAINER COMMITS`): fetch, fast-forward, and run the gates on the head. Then review each commit in one table, `| Commit | What it does, and the idea behind it | Rating |`, rated N/10:
     - the middle column says in one short sentence what the commit does;
     - a rating below 10 carries its reason in a few words next to it (`8/10 (invalid keys untested now)`);
     - 10/10 only when nothing could be better;
     - findings come with the exact fix; where the change is big, send the commits to the PR's Loop B agent (`converge`) and use its review and re-rating; with no loop running, apply `review`'s reviewer charter and `refactor`'s prompt to it;
     - never just "looks good", and don't push onto the branch while they're committing unless asked.
   - **"I don't understand this"** on a docs or code-comment line reports a bug in that text. Push clearer wording and reply "Done in <sha>: <new sentence>"; ask "OK?" only if the meaning changes.
3. **Then think, as a mini debate.** Instructions and acknowledgements skip this step. Agreeing is a conclusion, never the default.
   - **The whole picture first:** what does the maintainer want overall? Trace the actual flow in code (caller → callee, which object each side sees, in each environment). Check that every path to the same thing behaves consistently, and name any gap you find with `file:line` and the next check.
   - **Then one fresh-context agent argues it divergently,** with that evidence, what `main` does, and a measurement where one is possible. Is "over-engineering" the right call, or is there a small, cleaner fix?
   - **The agent first only generates, no judging:** the strongest case for the maintainer's view and the strongest case against. Each case comes from at least three frames, past the obvious first answers. Frames include the user who hits it, the maintainer who keeps the code, and the smallest diff. Others are the version with no new code, and the design from scratch.
   - **Only then does the agent judge:** it scores both sides, names each side's weakest point and the traps (hidden cost, a fix for a case nobody hits), and recommends.
   - **You decide.** Rate the agent's recommendation as in `pull-request` step 3 (open `pull-request` for the rating steps), and decide.
   - **Before answering "keep",** build the simpler version (theirs, or the simplest row of your own comparison) and name what breaks in it. If nothing breaks, recommend the simpler version.
   - **The reply reads as one person thinking:** your view, the reason, and in a sentence why the other side lost. Where the question is about code behavior, show your view as code at both ends (caller and callee). Never a bare yes, and plain even when it disagrees.
   - **Head the thread to a converged design, through the other side, not around them, and carry its load.** Keep a map of the whole thread in the artifact root: the linked threads and PRs, every invariant agreed (with the link) or open, and where it is heading. The thread has converged when every invariant is agreed. Each design reply moves the open ones by number: decide what evidence or a measurement settles and state it as the plan you'll follow unless they object, and ask only what is truly theirs to decide, each a question a yes or no answers. A decision blocks only the part it decides: start everything else now, and say in the reply what is already moving, so progress never waits on a reply. Then come back when it's sorted, not with progress. When the design has drifted over several rounds, run the finality pass first (`finality`, when to run it), then restate the design as those invariants.
     - Hold your own position: say where you disagree, what each option costs and which part of the design is weakest, also when it is the part the other side likes. Ask the question that would settle each disagreement.
     - Change position only on new evidence (a probe, a case, a cost you had missed), and name it; the other side's preference is a reason to look again, not a reason to flip.
   - **Answer the question behind the literal one.** Your answer may show the defect is a class (a default, a parser, a shared helper). Then recommend the class-wide fix with its evidence, not only the instance the PR fixes. When they question an example or post their own code, say why not that simpler version. When a measurement rejects their suggestion, offer a measured way to reach its goal. "First principles" or "perfect world" means the ideal design, regardless of the open PR.
4. **Then reply** with the result as a new comment, because edits don't notify. Beyond this result (and the wait ping below), a question gets no further comments from you; later changes to your reply are edits.
5. **Book-keeping, in the same step:** decision packet, umbrella body, Decisions comment, ledger.

### The watcher and the owed lists

**Start the watcher before your first post on any thread.** The watcher is a daemon that records GitHub events for you; a Monitor in your session wakes you when it records one. Unless the plugin's `watcher` option is `off`:
- **Start:** before you open an issue or PR in any tier (an audit report included), run `gh-watch-start <artifact root> <owner/repo>`. The artifact root you pass becomes the watch dir: the folder holding the watcher's files.
- **Maintainers:** set `GH_WATCH_EYES=<login>,<login>` to the PR's maintainers before `gh-watch-start`. The watcher reports commits and 👍/👎 only from those logins, and the default is your own.
- **Arm the Monitor** the command prints, with the longest timeout (`timeout_ms` 1800000, 30 minutes).
- **Retire the repo line:** once the issue or PR exists (the hook adds it to `threads.txt`), delete the bare `owner/repo` line from `repos.txt`, or the watcher never retires.
- **Every thread joins the watch list** in the same step you open or post in it. The hooks add it once a watcher runs. The posting guard refuses to open an issue or PR in a repo no running watcher covers.

The watcher runs independently of any session and only records events (and adds 👀); you answer them, woken by the Monitor.
- **Re-arm at once:** when the Monitor expires, its notice wakes you; re-arm it immediately.
- **No polling, no hand-off:** never poll GitHub in a loop in the conversation, and never hand events to a separate agent.
- **Unwatched `/ai` calls:** the user's `/ai` calls on threads nobody watches go to one watch dir (`gh-watch-start --main`, else the first live one).
- **After a gap:** after any resume, or any time the Monitor wasn't armed, read `events.log` past the last event you handled before anything else. That event's line number is kept in `events.cursor` in the watch dir; update it as you handle events.

**Each owed list is cleared only by the thing named:**
- **`replies-owed.md`:** every comment you answer (above). Cleared by replacing its line with `done: <reply URL> <what changed>`; a holding reply turns it into `holding: <reply URL> <ETA as an ISO time>` until then. While an agent drafts the answer, `drafting: <comment URL> <ETA>` keeps the stop hook from asking for it before then, so you never wait for the draft in the foreground.
- **`proposals-open.md`:** every "OK?" you ask, and every promise you post ("I'll…") as `PROMISED <thread>: <what> (<draft file name>)`, which `gate-pass` checks. Each new maintainer comment is checked against this list first. Cleared by the commit or link that delivers it. Do work you can finish in minutes before posting, so the post says "Done in <link>", never "fixing it now".
- **`waiting-on.txt`,** next to the watcher's `threads.txt`: each thing a PR of yours waits on (`<owner/repo#N> -> <dependent>: <what to do>`), also in that PR's notes table. The watcher prints `DEPENDENT of merged …` when a PR it watches merges. Check releases and unwatched PRs yourself at every wakeup.
- **A dependency that lands** (a merge or release you depend on) is handled like a maintainer comment: in the same step, apply what waited on it and post the progress on the dependent PR.
- **A pending task whose condition is met is done now.**

**After a burst of maintainer comments,** check the PR: no comment is the last word without a change, an answer or a reaction.

**The wait ping.** Post one when a proposal or question has waited 3 hours or more and the wait isn't obvious to them (buried in a thread, several open at once):
- one @-mention on that PR with the decisions you need, each with your recommendation and link;
- once per thread per wait, never while they're mid-review.

**Repo rules:** before a commit, merge or PR in a repo, read its CLAUDE.md / AGENTS.md on the target branch and follow it.

## 1.6 Posting gate (every tier, no exceptions)

**Everything that reaches an external service passes this gate,** with no lighter category: comments, review replies, inline comments, PR and issue bodies, filed issues, and edits of any of these. Reactions are exempt. Subagents never post; they hand you drafts.

1. **Write it the way it should end up;** the gate checks, it doesn't edit. Write in `drafts/<name>.md` (never straight into a `gh` command), with the comment it answers in `drafts/<name>.parent.md`.
   - Before the first sentence, write the one line the reader needs (the verdict or the ask), and what they already said or guessed.
   - Write it as `writing.md` says (and by the Thread rules below).
   - Read the draft top to bottom as a newcomer to the thread would: every term named where it first appears, every link between two sentences written out, nothing you'd have to read twice.
2. **Run `post-lint`** with the draft's `--kind` (and `--repo`). It must pass; `gate-pass` re-runs it with the same flags.
3. **Run the review** (`review`: open it for who reviews) with a prompt file. The review should come back quickly with nothing. A finding means step 1 missed something: fix the draft, and add one line to the ledger saying what the writing missed, so the writing improves and the gate stays quiet. The review checks facts and noise, never wording:
   - **Claims:** every claim against the code (`file:line` or a command and its output), the thread and the evidence.
   - **Noise:**
     - every con or risk names who hits it today (a caller, repo or user), or is cut;
     - every sentence that adds nothing is cut, but a sentence that links two points ("because", "so", "but") stays;
     - every question is answered;
     - every absolute word ("every", "unchanged", "always", "only") quotes what proves it, or is cut;
     - maintainer requests are followed, and links are correct.
   - **Convergence** (design threads): the reply states its author's own position and the design's weakest part; a change of position names the new evidence; every open invariant is either a stated default or a question that only the other side can answer, and the questions are as few as that allows.
   - **Voice:** does it read as the owner talking to a colleague (`voice.md`, `writing.md`)? A finding here means the draft wasn't written that way: rewrite it from what you'd say out loud, never patch the wording.
   - **A cold read:** "you have not seen this thread; list every term or sentence you can't understand", and "say in one line what the reader is asked to decide". If the reviewer can't say, or names two decisions, that's a finding; so is any pronoun with two possible meanings.
   - **Reader load:** can a newcomer who reads it top to bottom follow it? Is there a term or label they haven't seen, a sentence they must read twice, or a bold label or fragment standing in for a sentence? Does it sound like the owner (`voice.md`) talking to a colleague, answering them in kind?
   - **The result:** capture only the reviewer's final message (`drafts/<name>.review.out`). Fix every finding and re-review until that message is exactly `CLEAN`. Never paste the reviewer's rewritten wording; write the fix in your own plain words.
4. **Right before posting, re-read every claim against the current head** (`git fetch` first; read a PR's state before describing it). Every referenced commit is pushed (`git ls-remote`). Run `gate-pass <abs path>/drafts/<name>.md <review output>` and post with `--body-file` on that absolute path (`gh api … -F body=@<file>` for API posts).
5. **Post in the thread where the person wrote.** Log it.

**Fast gate,** for a reply of a few claims: a "Done in <sha>", or the holding reply of 1.5 with what you found so far. It runs the same steps, with the reviewer asked only about those claims. The reviewer still has to answer exactly `CLEAN`.

### Thread rules

**How to write** a post (voice, drafting by talking, what reads as machine-written, the reply that carries the load) is in `writing.md` next to this skill, with `~/.mergeworthy/voice.md` (else `voice.md` here): read both before drafting any post. The rules below are about the thread, not the prose.

- **At most two comments in a row.** The second is only the 1.5 result after its holding reply, a wait ping, a dependency's progress, a 👎 fix, or the review of commits a maintainer pushed after your last comment; anything else edits your last comment. `pre-bash-guard` blocks a third within 3 hours of your last; after that, the third may be the wait ping.
- **Evidence carries no secret.** In logs, requests, payloads and screenshots, write `<REDACTED>` in place of every token, cookie, auth header and key. Quote only the lines that show the point (`post-lint` fails on common token shapes).
- **One reply per person, edits for corrections.** Several comments from one person get one reply. Never post a comment that corrects or adds to your own earlier one: edit it in place, through the gate.
- **Keep the process invisible.** Reviewers, models, gates, rounds, working ratings and pass reports stay in the artifact root (`ledger.md`). The thread gets the result, with evidence only where a reader needs it to judge.
- **Decide what you can decide or measure.** A question carries your recommendation and its reason; recommend the option that is best for the people who use it, and state the cost of each option beside it. Never pick an option because it is the smallest change when another serves users better; a change you'd recommend within scope is made, not listed. Never solicit ("pushback welcome"), and don't promise how you'll behave next time.
- **Credit** a design or statement to someone only with a link to where they said it.
- **Links** to another repo use `owner/repo#N`. Write "depends on #N", never "stacked on", unless `gh stack` links them.
- **The badge.** Unless the plugin's `badge` option says otherwise (`auto`: only from a human account), start with the icon of the agent that did the work and its name as the label (e.g. `<img src="https://github.com/claude.png" width="20" height="20" align="left" alt="Claude"> **Claude:**`, or `**Agent:**` for any agent).
- **Budgets:**
  - reply ≤ 80 words;
  - a design answer or walkthrough ≤ 400 words, code included; one decision per comment, with your pick;
  - a reply or design answer gets 60 more words for each question beyond the first in the comment it answers (quoted lines don't count);
  - PR body about 150 words plus evidence, up to 250 when it lists decisions for the maintainer;
  - issue (`open-issue`): ≤ 400 characters besides `### How to reproduce` and its evidence; a decision issue ≤ 400 words;
  - inline review comments ≤ 2 sentences, only where the reader must judge.

  Tables, code and collapsed sections count toward every budget except a PR body's, where tables, code, images and links don't count. Moving prose into a table to fit is the loophole the budget exists to close.
- **Notes for a maintainer go in one table:** `| Note | Kind | Blocks merge | Next |`.
  - Kind is bug, limitation, not a regression, or decision needed. Next is fixed in <sha>, PR <url>, or nothing, because Y.
  - A follow-up is opened before the post, never listed as "recommend" or "follow-up"; in the user's own repos, just do it.
  - A note that blocks the goal and can be fixed anywhere, upstream included, is fixed instead of listed.
