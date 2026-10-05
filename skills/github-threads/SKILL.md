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
- **A `/ai` comment is the user typing in this chat.** Start the work at once, in parallel with what's running rather than queued behind it. Follow the skill the comment calls for (`implement-issue` for "fix it" or "open a PR"), and tell the user in chat.

Each comment you answer goes through these steps:

1. **Within 10 seconds:** 👀 reaction. The watcher does this.
2. **Within about a minute:** a short reply through the fast gate (1.6). Before acting on any comment, check that its reason fits the line it's anchored to; if the reason fits another line better, ask before changing anything.
   - **An instruction** ("Let's…", "Remove…", "Merge origin/main") or a suggestion block: do it, then reply "Done in <sha>."
   - **A question or soft suggestion** ("Overkill?", "How about…?", "why…?", "I think we can…") gets an answer, never a code change until they answer it. "How about X?" or "Is X possible?" starts with yes or no and the one real obstacle. When their idea is simpler than yours, recommend their idea. If the answer needs work, say what you're checking ("Measuring the calls"); never agree with a premise or promise a change you haven't measured.
   - **A short acknowledgement** ("OK", "Good!", 👍) is not the end of the thread: read the whole thread to find what the acknowledgement answers. It answers your last open proposal or question in that thread. If that thread has none, it answers your latest open proposal or question elsewhere in the same PR, posted just before the acknowledgement. That proposal is now an instruction. If the acknowledgement could answer two, do both if they don't conflict; otherwise ask which in one line. Only an acknowledgement of a finished change needs nothing but a 👍.
   - **A 👍 or 👎 reaction** from the user or a maintainer on one of your comments is feedback on that comment. For 👍, note what they liked and reinforce the rule that produced it; on a proposal, the 👍 is also the approval. For 👎, work out why and fix the rule behind it (1.1.12). Then, if the thread is still on that point, post a new reply with the fix that @-mentions them. If the thread has moved on, edit the 👎'd comment to add how you'll do better. Leave the 👎 either way.
   - **A maintainer's commits pushed to your PR** (the watcher's `### MAINTAINER COMMITS`): fetch, fast-forward, and run the gates on the head. Then review each commit in one table, `| Commit | What it does, and the idea behind it | Rating |`, rated N/10:
     - the middle column says in one short sentence what the commit does;
     - a rating below 10 carries its reason in a few words next to it (`8/10 (invalid keys untested now)`);
     - an emoji only where it's funny (`5/10 🎀 (nothing reads the narrower type)`);
     - 10/10 only when nothing could be better;
     - findings come with the exact fix; where the change is big, apply `review`'s reviewer charter and `refactor`'s prompt to it;
     - never just "looks good", and don't push onto the branch while they're committing unless asked.
   - **"I don't understand this"** on a docs or code-comment line reports a bug in that text. Push clearer wording and reply "Done in <sha>: <new sentence>"; ask "OK?" only if the meaning changes.
3. **Then think, as a mini debate.** Instructions and acknowledgements skip this step. Agreeing is a conclusion, never the default.
   - **The whole picture first:** what does the maintainer want overall? Trace the actual flow in code (caller → callee, which object each side sees, in each environment). Check that every path to the same thing behaves consistently, and name any gap you find with `file:line` and the next check.
   - **Then one fresh-context agent argues it divergently,** with that evidence, what `main` does, and a measurement where one is possible. Is "over-engineering" the right call, or is there a small, cleaner fix?
   - **The agent first only generates, no judging:** the strongest case for the maintainer's view and the strongest case against. Each case comes from at least three frames, past the obvious first answers. Frames include the user who hits it, the maintainer who keeps the code, and the smallest diff. Others are the version with no new code, and the design from scratch.
   - **Only then does the agent judge:** it scores both sides, names each side's weakest point and the traps (hidden cost, a fix for a case nobody hits), and recommends.
   - **You decide.** Rate the agent's recommendation as in `implement-issue` step 3 (open `implement-issue` for the rating steps), and decide.
   - **Before answering "keep",** build the simpler version (theirs, or the simplest row of your own comparison) and name what breaks in it. If nothing breaks, recommend the simpler version.
   - **The reply reads as one person thinking:** your view, the reason, and in a sentence why the other side lost. Where the question is about code behavior, show your view as code at both ends (caller and callee). Never a bare yes, and plain even when it disagrees.
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
- **`replies-owed.md`:** every comment you answer (above). Cleared by replacing its line with `done: <reply URL> <what changed>`.
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
   - Before the first sentence, write the one line the reader needs: the verdict or the ask. Then list what the reader already has (their words, the thread) and the new things you'll tell them, at most four; the rest goes in a linked document or nowhere.
   - Write from that list, by the Writing rules below.
   - Read the draft as a scanner would, only the first words of each line and the bold text: the point and the ask must come through. Then read every sentence once: none you'd have to read twice, no "it" with two meanings.
2. **Run `post-lint`** with the draft's `--kind` (and `--repo`). It must pass; `gate-pass` re-runs it with the same flags.
3. **Run the review** (`review`: open it for who reviews) with a prompt file. The review should come back quickly with nothing. A finding means step 1 missed something: fix the draft, and add one line to the ledger saying what the writing missed, so the writing improves and the gate stays quiet. The review checks facts and noise, never wording:
   - **Claims:** every claim against the code (`file:line` or a command and its output), the thread and the evidence.
   - **Noise:**
     - every con or risk names who hits it today (a caller, repo or user), or is cut;
     - every sentence the reader could delete is cut;
     - every question is answered;
     - every absolute word ("every", "unchanged", "always", "only") quotes what proves it, or is cut;
     - maintainer requests are followed, and links are correct.
   - **A cold read:** "you have not seen this thread; list every term or sentence you can't understand", and "say in one line what the reader is asked to decide". If the reviewer can't say, or names two decisions, that's a finding; so is any pronoun with two possible meanings.
   - **Reader load:** does someone who reads only the first words of each line and the bold text get the point and the ask? Is there a sentence they must read twice, or a term they haven't seen? Must they hold more than about four things at once? Does any sentence lack its subject, or read as a fragment squeezed under the budget? Does it sound like a colleague, answering them in kind?
   - **The result:** capture only the reviewer's final message (`drafts/<name>.review.out`). Fix every finding and re-review until that message is exactly `CLEAN`. Never paste the reviewer's rewritten wording; write the fix in your own plain words.
4. **Right before posting, re-read every claim against the current head** (`git fetch` first; read a PR's state before describing it). Every referenced commit is pushed (`git ls-remote`). Run `gate-pass <abs path>/drafts/<name>.md <review output>` and post with `--body-file` on that absolute path (`gh api … -F body=@<file>` for API posts).
5. **Post in the thread where the person wrote.** Log it.

**Fast gate** (the 1-minute reply in 1.5). It is only for a reply of a few claims: an acknowledgment, a "Done in <sha>", what you're checking. It runs the same steps, with the reviewer asked only about those claims. The reviewer still has to answer exactly `CLEAN`.

### Writing

**Every post brings the reader something they didn't have** (every report too, 1.11): a finding, a measurement, a better option, a risk, or a decision with its reason. If it wouldn't, think more first. Engage as a peer: agree or disagree, and say why.

- **Take load off the reader.** A post exists to leave the maintainer with less to hold in their head, not more.
  - The first line is the verdict or the ask.
  - One decision per comment, with your pick, answerable in a word.
  - A concrete example in their words, not a case matrix; an edge case only when it would change their decision.
  - Long material (a spec, a report, every case) goes in a linked document (a gist). The comment carries the two sentences that matter and the decision; never a spec inline.
  - When you change your mind, say so in one line ("I was wrong about X: Y").
- **Write like a colleague talking.** Full sentences with a subject, and your own voice: "I agree, it's the wrong word", not "The wrong word." Answer their tone in kind: a question gets an answer, a fair point gets "you're right", and real work they did for you (a repro, a fix, a long explanation) gets a thank-you; an approval or a review gets none (below). Keep them engaged: open with what's new for them, and answer a comment of several points the way they wrote it, quoting each point (`> their words`) above your answer. "Done in <sha>.", bold lead-ins and table cells stay short. When a post runs over its budget, cut a point or link it; never cut the grammar.
- **Write for how people read.** Readers scan: they read the first words of each line and what's bold, and they hold about four things at once.
  - The answer or the ask comes first, in the post and in each paragraph; the rest can be cut at any point and the point survives.
  - Each sentence starts from what the reader already has (their words, your previous sentence) and ends on the new point.
  - The people and things act: "Vike warns", not "a warning is issued". Their words, not yours; a term they haven't seen is explained where it first appears. A word that ranks difficulty ("fundamental", "impossible") says what it's hard for.
  - Sentences of 15 to 20 words, none over 30; paragraphs of at most three sentences; at most about four items to hold at once, grouped or linked beyond that.
  - Hierarchy carries the structure: a bullet per parallel item with its point in a bold lead-in, prose for reasoning, one level of nesting, headings only for a long post. Bold marks the lead-ins and the decision, nothing else; a table only for a real comparison of a few columns.
- **At most two comments in a row.** The second is only the 1.5 result after its holding reply, a wait ping, a dependency's progress or a 👎 fix; anything else edits your last comment. `pre-bash-guard` blocks a third within 3 hours of your last; after that, the third may be the wait ping.
- **Evidence carries no secret.** In logs, requests, payloads and screenshots, write `<REDACTED>` in place of every token, cookie, auth header and key. Quote only the lines that show the point (`post-lint` fails on common token shapes).
- **Self-contained** for anyone who finds the thread later. A comparison of designs or behavior shows each option as code: what the user or extension writes, and what changes as a short ```diff block (removed lines `-`, added `+`, so GitHub shows them red and green). A table may summarize the options; it never replaces the code.
- **Short, plain words,** one idea per sentence. Name the thing again instead of "it", "them" or "this" whenever two things could be meant ("Vike can't tell these two apps apart, so Vike warns", not "so it warns"). No jargon, abstractions or AI phrasing ("in this run", "doesn't establish", "worth noting", "happy to", "let me know"), and never solicit ("pushback welcome").
- **Say only what they don't know yet.** Don't recite their comment or your earlier replies, don't thank them for an approval, and don't promise how you'll behave next time. When answering several questions, quote each in one line. If all there is to say is "done", say "Done in <sha>".
- **One reply per person, edits for corrections.** Several comments from one person get one reply. Never post a comment that corrects or adds to your own earlier one: edit it in place, through the gate.
- **Keep the process invisible.** Reviewers, models, gates, rounds, working ratings and pass reports stay in the artifact root (`ledger.md`). The thread gets the result, with evidence only where a reader needs it to judge.
- **Decide what you can decide or measure.** A question carries your recommendation and its reason; a change you'd recommend within scope is made, not listed.
- **Credit** a design or statement to someone only with a link to where they said it.
- **Links** to another repo use `owner/repo#N`. Write "depends on #N", never "stacked on", unless `gh stack` links them.
- **The badge.** Unless the plugin's `badge` option says otherwise (`auto`: only from a human account), start with the icon of the agent that did the work and its name as the label (e.g. `<img src="https://github.com/claude.png" width="20" height="20" align="left" alt="Claude"> **Claude:**`, or `**Agent:**` for any agent).
- **Budgets:**
  - reply ≤ 80 words;
  - a design answer or walkthrough ≤ 250 words, code included; one decision per comment, its recommendation and code first;
  - PR body about 150 words plus evidence, up to 250 when it lists decisions for the maintainer;
  - issue: one finding, ≤ 400 characters plus a screenshot;
  - inline review comments ≤ 2 sentences, only where the reader must judge.

  Tables, code and collapsed sections count toward every budget except a PR body's, where tables, code, images and links don't count. Moving prose into a table to fit is the loophole the budget exists to close.
- **Notes for a maintainer go in one table:** `| Note | Kind | Blocks merge | Next |`.
  - Kind is bug, limitation, not a regression, or decision needed. Next is fixed in <sha>, PR <url>, or nothing, because Y.
  - A follow-up is opened before the post, never listed as "recommend" or "follow-up"; in the user's own repos, just do it.
  - A note that blocks the goal and can be fixed anywhere, upstream included, is fixed instead of listed.
