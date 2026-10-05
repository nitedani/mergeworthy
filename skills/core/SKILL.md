---
name: core
description: "Load first for any multi-step or GitHub task: the task, triage and tiers, principles, tracking, discovery, safety on the user's machine, reporting, pre-flight."
---

# Work automation methodology (v3)

Give this whole file to an agent, followed by the task. The agent sizes the work first (1.0), then applies only what that size requires.

Five parts:
- **Part 1: How to work.** Triage, principles, the live GitHub loop, posting, safety, reporting.
- **Part 2: Implementing a change.** From a problem to one merge-ready PR.
- **Part 3: Convergence.** How changes reach their final state.
- **Part 4: Failures that already happened,** each pointing to its rule.
- **Part 5: Mechanisms.** Scripts and hooks that enforce the rules. Where Part 5 has a mechanism, use it.

**Precedence:** the environment's instructions and the user's scope come first; Part 1 overrides Parts 2 and 3 where they conflict. When two rules seem to collide, check their scope (who owns the code, which tier, whether an umbrella issue exists) before choosing.


## TASK

<The task, in the user's words: links, pasted logs, constraints.>

Defaults (the user can override):
- **The user** owns the goal. Code in the user's own repos, and beta, experimental or pre-1.0 features, is theirs, and yours to change for the goal: decide, act, and report afterwards.
- **External maintainers**: whoever merges in a repo you don't own (CODEOWNERS, recent mergers). Their requests are settled decisions, and changes to their code's behavior or public surface are their call (Part 3 section 2).
- **Review model**: the model from `codex-review-model` (Part 5), run with stdin closed: `m=$(codex-review-model) && codex exec -m "$m" --sandbox danger-full-access --skip-git-repo-check -o <file> "<prompt>" < /dev/null`. `codex-review-model` exits 3 without calling anything when Codex's last usage snapshot says it is out of credits or rate-limited; then don't call Codex. If the account refuses the model, take the next from `codex-review-model --all`. Record the model from the `model:` line the command prints, never from the model's self-description. When Codex is unavailable or fails (an error, a hang, "out of credits"; none of these is a review), the local model runs the same charter (1.1.14); a fresh-context Claude subagent only when the local model is busy or not installed. Record which reviewer ran, and re-review on Codex once it's back.
- **Other models**: judgment work runs on the session's default model; routine agent work on the `sonnet` alias (1.1.14). Never a model above the default's tier unless the user names it, and never one the user has excluded. Never write a model version into a prompt, skill or memory.
- **Artifact root**: a persistent `<task>-work/` directory next to the worktree for notes, logs, probes, agent outputs and scratch worktrees; never `/tmp`.
- **Publishing authority**: what the task allows you to open, comment and file. A reviewed draft isn't permission to publish.

---

# Part 1: How to work

## 1.0 Triage

Read the task and every link in it. Write `Tier: <X>, because <signals>` and put it in the first report. Re-triage when the deliverables or open decisions change, and say so.

| Tier | Signals | Process |
|---|---|---|
| **0: Answer** | An answer, research or a review; nothing to change. | Principles, evidence, reporting; the posting gate if published. |
| **S: Single fix** | One bounded fix in one repo, expected behavior already clear. | Part 2 per change; its review round and refactor pass feed `pr-steps`. Part 3 sections 1–5 and section 10's failure and evidence rules; of its loops, one dry verification pass per slice after its last fix and one guardian round for the closing verdict (re-run on the head if its findings land). The project file's gates green, body true to the head. |
| **M: Feature or set** | A new capability, a changed public contract, several change units, or open behavior questions. | Part 2 per unit, full Part 3 in place of Part 2's single rounds, invariants, ledger, decision packet, design loop (1.4). |
| **L: Program** | Changes across two or more independently maintained repos, or two or more decision makers. | Tier M everywhere, plus the umbrella issue (1.2). |

## 1.1 Principles

1. **Critical path first.** Keep an ordered `critical-path` list at the top of the ledger (Tier S: in `scope.md`). Before starting any agent, PR or investigation, write which item it unblocks. Work that unblocks none gets one review round, then is finished or set aside. At every wakeup, the next critical-path item is in flight before any side work.
2. **Invariants first (Tier ≥ M), design second, code third.** List what any acceptable design must keep (the project file or the user names them) and put the list at the top of every agent and reviewer prompt. Each design option gets a table with one row per invariant, filled with measured evidence. Reject any option that breaks one, even "for now". Cleanest design from day one; no patchwork, no speculative capability.
3. **Do, don't offer.** An offer is a to-do: do it now. Ask only when the action is (a) irreversible on shared state you didn't create, (b) money, credentials, or the user's global config (`~/.claude`, `~/.codex`, shell rc files), or (c) a product or public-API decision of an external maintainer, or a genuine fork you can't rank. Then: one line starting `GENUINE-FORK:`, the options and your recommendation; continue with everything else, and if nobody answers by the time you need it, take the recommendation and say so. Ask in plain text, never in a modal pop-up, and only after re-reading every message the user sent since your last reply: if they already answered, don't ask.
4. **Every user message gets answered, first.** At each turn, list the user's messages since your last reply, including ones typed while you worked, and handle every one before ending the turn. Answer each question in the first lines, before any status or tool work; one that needs investigation goes on `questions-owed.md` with an ETA. An instruction about how to do something is done as given; try another way only after it fails, and quote the failure. A setting or design the user decided stays decided: mark it where it lives (`# user decision YYYY-MM-DD: <what, why>`), and if you find a problem with it, keep it and report the problem with evidence; a session that never saw the decision reads the marker, not the chat. An instruction whose premise doesn't hold (e.g. "one PR per item" when the items depend on each other): say so with a recommendation before acting.
5. **Evidence for every claim, in chat too.** Each factual sentence about code, a package, a release or runtime behavior carries its source (`file:line`, `npm view`, command output) or is marked `guess:`; say what you could not verify. Check `main`, the registry and the upstream source before recommending to close, remove, replace or switch anything. A "can't" needs the failed attempt quoted plus one alternative tried. If you contradict something you said earlier, say so. A job you report as running is one you saw make progress (its log, its output file, the GPU busy), not one you only started. Measure through the exact path the real work takes (the same client, API and settings the user runs), never a convenient substitute; a result from another path is not evidence. A CI workflow change works only once a real run on the branch shows it.
6. **Fix at the root; never document around a defect.** A sentence telling users to work around the product ("order by seq when order matters", "may miss for 60 s") is a bug to fix, upstream included, unless the user explicitly accepts it. These need the user's OK with a written reason the root fix is impossible: parsing twice, encoding to dodge a transport, retry or reload loops, a second code path for old runtimes, silent fallbacks. Unreleased, experimental or pre-1.0 code gets no compatibility code or shims (check `npm view <pkg> versions`); losing something users can do on `main` is still a regression (1.1.11). Before an upstream PR, find which side relies on behavior the other doesn't promise (hook order, file layout) and fix that side first, ours included.
7. **Parallel, not later.** "A separate PR" means started now, alongside. A found defect, in or out of scope, gets exactly one disposition: fixed in this change, a PR opened now (listed on the umbrella if there is one), or an issue (only when there's no umbrella and it's unrelated; search for an existing one first, trace both ends, state facts only). "Mentioned" is never a disposition. The same defect in a sibling (another adapter, another call site) is related: it is fixed in this change, a public API change included, which the PR then states. Before deferring anything, count its lines: under ~20 lines and neither a user-visible fix nor a defect on `main` means this PR; otherwise its own PR, now. "It can be added later" is never a reason. A new dependency never joins an open PR the maintainer hasn't agreed to. Other follow-ups on the same topic go on the open PR; a PR that replaces another closes it, with a link, in the same step.
8. **Never drop scope silently.** Copy every ask and link of the task into `scope.md` as checkboxes, at the start and whenever the user adds one; the final report walks that list. Copy each claim of an accepted proposal into `acceptance.md`. Dropping or deferring any item needs the user's OK first, never after. If a recorded decision or an accepted claim turns out not to work, ask with the blocker's evidence and your recommendation before building the alternative.
9. **Respect decision authority.** Record each maintainer request with its link and date, and do it as asked, or ask back with a recommendation; never decide otherwise and inform. The newest statement on a subject wins; re-read the thread before citing anyone. "The rest LGTM" agrees to every unquestioned proposal in the comment it answers: record them as agreed and start. A question is never a decision.
10. **Names match behavior; no invented options.** Every new public name gets a one-line "name → what it does in every case" check. A new option needs a named user scenario that can't be served without it.
11. **No regressions.** Anything that works on `main` and fails on the head is a regression, experimental features included: fix it, never list it as a limitation. So is every row of your own comparison where the head is worse than the run-to-run spread. Hot paths, transports and flow control get a benchmark of `main` against the head before the PR opens (all scenarios, alternating runs, N ≥ 3: throughput, p50/p99, request count, reconnects); a cell worse than the spread is fixed or reverted, never called a trade-off without the user's OK.
    - **UI**, before anyone sees it: each touched page at widths 360, 768, 1280 and 1920 plus 1 px either side of every breakpoint, zoom 90–150 %, light and dark, hover, focus and open states, and a cold first load. Any console error fails. List the checked cells in the report. Use it like a person: real mouse, wheel, keyboard and touch (Playwright's `page.mouse`/`keyboard`/`touchscreen` when the DevTools browser can't send it), a screenshot looked at after each action, a recording for anything that moves. Scripted events, emulated hover and computed-style diffs don't count.
    - **Runtime fixes** (a stream, a cancel, a cache): shown in the real app through a real browser, `main` against the head, with the server's logs. Unit scripts alone don't count.
12. **Fix the mistake and the rule that allowed it.** When the user names a failure: stop, re-read, and fix the whole class in the same turn: the artifact (PR, comment, code), and the rule source that allowed it (this file, the installed skill, the project file, or a Part 5 mechanism), by editing the existing rule (1.9). Then show the correction holds. Behavioral lessons go into this file, never only into one project's memory or a machine's global config.
13. **Never stall.** Never end a turn with work pending unless something running will notify you, or you say what you're waiting for. A long job gets a Monitor on its failure signals (its process or server exiting, errors, no progress), not only a completion notice: a run that dies silently must wake you. While any wait exceeds 10 minutes, at least one independent item is in flight; if none exists, say why. When the user says they're leaving, send every open question in one message within 5 minutes, then continue on your recommended defaults. A usage limit triggers `claude-swap` (Part 5); its event wakes the session. Then resume every agent the limit stopped through its own thread, never a new one, and never auto-resume parallel agents on a non-default model. Without a spare subscription, schedule one wakeup at the reset time. When a context nears its limit, hand off at a clean boundary to a fresh agent with the ledger.
14. **Spend tokens like money.**
    - Do small steps yourself: one command, one file read, a short edit, a "Done in <sha>" reply.
    - Start an agent only for long, independent work, at most 3 at a time without asking, and only from the main session: a subagent never starts agents of its own (1.7); queue the rest. Continue an agent that already has the context (send it a message) instead of starting a new one, and stop an agent as soon as its question is settled.
    - Give agents paths and the question, never pasted files or long histories; ask for a short report. Each role gets only what it uses: a PR writer or orchestrator gets this file (1.7); an executor (the routine work below) a ticket with `Goal`, verified `Facts`, `To check`, `Scope` and `Acceptance`, and none of your conclusions; a reviewer its charter and the artifact.
    - Match the check to the risk: a short reply gets the fast gate (1.6), a PR body or a proposal the full review, a full convergence loop only where the tier (1.0) requires it.
    - Re-run only the tests a change can affect (a docs change doesn't need the e2e matrix).
    - Model per task (Agent tool's model parameter): `sonnet` for running tests and gates, mining logs, fact checks of short texts, mechanical edits and relaying status; the session's default model (Opus family) for design, hard debugging, charter-driven reviews and anything posted to a maintainer.
    - **The local model (`local-agent`, when installed)** costs no subscription usage. It executes well and judges poorly, so you keep every decision and hand it bounded steps whose result you can check cheaply: `local-agent <mode> <ticket.md> [--cwd <worktree>] [--write]` through Bash with `run_in_background`, one at a time (one GPU); it can't start agents, so give it work one agent finishes. Run `claude-usage --mode` at the start of each task and at every wakeup. At `routine` it gets the routine work above (modes `facts`, `run`, `reproduce`, `cold-read`); at `execute` also implementation from your own plan (`implement`: approach, files and acceptance checks are yours) and each side's evidence for 1.5's mini debate (`evidence`; you argue and decide). Pair it with yourself, never with a cheaper Claude model: it does the work and you review it, or you write and it reviews (`local-agent review`, a gate review whose `verdict` is the `CLEAN`; you check each finding and its `not_checked`). Never hand it the approach (Part 2 step 3) or anything posted. Check its result before using it: two or three of its cited `path:line`s, one re-run command, or the diff against your plan. Tickets and modes: `~/local-llm/DELEGATION.md`. In T3 Code, start it as a native child instead of the CLI: `delegate_task` with `target` = the Local Claude instance from `orchestrator_capabilities` and model `local`, `runtimeMode: "full-access"` (approval-required asks the user for every read; auto mode is slower), `mode: "async"`, the ticket as the task and its final message the result (`CLEAN` for a review). It finished a gate review in 10 minutes where the CLI timed out at 15 with nothing.
    - Never trim a charter or skip a pass it requires to save tokens.
15. **Earn every line.** A reviewer's, verifier's or guardian's finding is a candidate, not a mandate. Before it becomes code, a test, a doc or an option:
    - How likely does a real user hit it, and what happens then? A rare case whose failure is mild, or arguably what the user asked for, gets no code. Wrong data returned silently (a misattribution, a lenient parse that hides the cause) is never mild: fix it at the root (1.1.6).
    - What does `main` do for the analogous case? Guards, asserts and caches only where `main` has an analogous one.
    - What does it cost in lines, new state (maps, globals, build tracking) and tests? More than a few lines for a rare case is overkill.
    - Would the maintainer write it? Lean code, no special-casing, no caches that save milliseconds, tests and docs per 1.1.16.
    Record the judgment in one line ("accepted, not worth code: rare, and the page winning is what the user asked for"); that is the finding's disposition in Part 3's loops. When unsure, don't add; ask with a recommendation. A converged PR is the smallest clean diff that does the job and reads as obviously right to its maintainers.
16. **Submit the shape that gets merged.** Before opening a PR, look at the maintainer's recent merged PRs (and ours in that repo): what they keep and what they cut. Defaults:
    - One purpose, small: under ~50 lines of code when possible. Each user-visible fix is its own PR; internal cleanups go together in one refactor PR, titled per the repo's convention.
    - The body's first sentence names the problem a user hits on today's `main`. Say a dependent project needs this PR only if it's still broken without it; if readers might assume it does, say "not required by X".
    - Before opening or calling it ready, list each feature with non-trivial code in the ledger (Tier S: `scope.md`) next to the link that needs it today; remove the rest.
    - Tests follow the repo's habit. Where the maintainer removes PR-proving tests ("remove the test right before merging"), remove them in a final commit once the PR is approved, unasked. None for message text, comments or dead code; at most one permanent e2e assertion per new capability, in an existing test app; unit specs only for tricky pure algorithms. Where the maintainer keeps regression tests, keep them.
    - Docs: main usage and one example, plus `llms.txt`; no edge cases, nothing obvious (1.3).
    - Reuse existing code; search before adding a helper, and never claim something is missing without linking the code.
    - Comments: at most one line, literally true, stating a constraint the code can't show; no links to source, no comparison with the old code ("instead of", "now", "no longer"). Names follow their siblings. Every comment, guard or workaround the diff deletes gets one line in the body with the evidence that it's obsolete; otherwise it stays.
    - A test app imports the package by its name, never by a source path.
    - Open the PR ready and say "ready" once (1.7).

## 1.2 Tracking

- **Every tier:** drafts and their reviews under `drafts/`; evidence under the artifact root; exit codes recorded (`EXIT=$?`) and quoted, never a log tail. Log and artifact names include a unique pass ID; never overwrite another pass's file. The owed lists of 1.5 (`replies-owed.md`, `questions-owed.md`, `proposals-open.md`) live in the artifact root.
- **Tier S:** the PR body is the reader's record, true of the final head, plus `scope.md` and a short `ledger.md` for process records (review, refactor, ready-check).
- **Tier M:** `ledger.md`, one row per event (time | unit | event | head SHA | result: each pass, round, fix with its commits, gate or lane run with its exit status, push, CI result), headed by `critical-path` and the passes still owed. Answer every status and convergence question from it, skipped steps included. `decision-packet.md`: only people's picks (decision | who | date | link | what it was picked over). `scope.md`, `acceptance.md`, and `corrections.md` (quote | instance fix | generator fix).
- **Tier L:** an umbrella issue listing every PR and issue with its state, plus one live **Decisions comment** on it (Requirements, Agreed, Proposed and waiting, Open, PRs), edited in place through the gate. Every line has a source link.
  - Update the body **and** the Decisions comment in the same step as every event.
  - A forward-looking line ("working on X", "waiting on Y") names the event that removes it; when that event fires, remove the line.
  - Program-wide status lives only on the umbrella; a PR body keeps only its own notes table. When a decision replaces a design, update every surface that still describes the old one (code, tests, types, docs, open PR bodies) in the same step.
  - `tracker-check` (Part 5) flags drift; no report to the user while it's red.

## 1.3 Discovery

- Pull the default branch. Read every starting point in full: linked issues and PRs (recursively), review comments, commits, CI. Check for existing PRs and other sessions' work.
- **Precedent before rituals.** Before a release, a migration or any repo routine, write `precedent.md` from its last 5 instances (commit messages, bump types, tags, commands, order) and follow it exactly. Any difference is a question with a recommendation.
- **Style before writing.** Before writing docs or code in a repo, read three sibling files or pages and note the conventions (sentence length, comment density, naming, how platforms are mentioned, em dashes; our new prose has none). The review checks the diff against them.
- **Docs** say only what a user wouldn't expect. A sentence that says when something applies states its exact condition and one example with real names, in terms the docs already use; never coin a term. Before pushing docs, a fresh-context agent that sees only the rendered text explains each new section back and lists every sentence it can't act on; fix until its explanation is right.
- **Behavior before removal.** Before removing or rewriting behavior, inventory what exists (triggers, paths, gates) and run `git log -S` on it. Keep all of it unless the task says otherwise. After a move or rename, grep the repo and sibling PRs for the old name or anchor.
- **References before UI.** Before any visual design: 3–5 named reference sites with screenshots, and the design skills the user has pointed to. Ambiguous feedback about direction: build two or three variants that differ in layout, hierarchy or main action (not color or copy), inside the real page with real data, switchable by a `?variant=` parameter, and ask which. Given a design file, measure the design and the app the same way (sizes, radii, motion, production build) and fix every difference. Before any screenshot or video is shown, a fresh-context agent lists everything broken, misaligned or clipped in it. Matching a design file is not the bar: before a screen is shown, name its surface archetype, score it on the slop tells (wrong surface, center stack, equal-weight tile grids, decoration in place of hierarchy, rainbow color), repair by that diagnosis, and remove every element nobody asked for. When the user wants people used to a named product to feel at home, first list that product's everyday features and buttons for the surface, then build each one (better, not copied) or write down why it is absent. A new feature or visual direction is shown to the user on a local preview before it's pushed; fixes to reported bugs go straight to the PR.
- Research prior art in upstream source at pinned versions.

## 1.8 Safety on the user's machine

- Kill only your own processes, by PID or port; never `pkill -f`.
- Whatever you start, you stop: dev servers, builds, preview servers, proxies. A subagent records the PIDs it starts and kills them before handing back; check with `ps` that none are left. Find a server by the PID you started (and its children, `pgrep -P <pid>`) or by its port (`ss -ltnp 'sport = :<port>'`); never grep `ps` output for a port number, and never `pgrep -f <pattern>`. Check each PID's command and directory before killing it.
- At most 4 browsers and 4 dev servers of your own at once; stop each when its work ends.
- Never restart or reconfigure a container someone else's work depends on; start your own alongside.
- Anything that listens on a port (e2e tests, dev and preview servers) runs through `isolated-run <command>`, yours and every subagent's: its own network namespace with a private loopback (outside network through a proxy it sets up), so fixed ports never collide and parallel runs never test each other's servers. Never kill or wait out another run's server.
- Never modify the package store or a shared `node_modules`; scratch installs use `--package-import-method=copy`. After any install, check `git status` for unexpected changes.
- Browser work uses the DevTools MCP. On "profile in use", retry after 30 s, then ask. Never fall back to scripted browsers silently, never open windows on the user's desktop, never kill another session's browser.
- Isolate worktrees: their own ports, databases and generated clients. Never touch the user's own checkouts (the clones the user works in), including their git config, which their worktrees share: no edits, commits, checkouts, resets or branch switches; work in worktrees you create, and to read another branch, `git worktree add --detach <artifact root>/<name> <ref>`.

## 1.11 Reporting to the user

- **First lines:** answers to the user's questions, then the outcome or the action needed from them.
- **Then:** each PR's state and what was found and fixed since the last report, with links; what's still running, what's waiting on whom, what's theirs to decide, and the critical path with an ETA per step.
- About 12 lines unless asked for more. Local files as absolute paths; every PR or issue with its title and link, including every issue you filed. The 1.6 writing rules apply. Don't restate their instructions; no step-by-step narration.
- Before reporting status, run `tracker-check` and check `ready-check` where they apply. Never claim a pass went dry for a slice that hasn't had it. State unfavorable facts, mistakes and skipped steps plainly.

## 1.12 Pre-flight (steps 3 and 4 in every tier; the rest in Tier ≥ M)

Before the first change:
1. Write `scope.md`.
2. Write the critical path.
3. Check that the Part 5 hooks are in `~/.claude/settings.json`; this file names that file, so add them if missing. Start the watcher with `GH_WATCH_EYES=<maintainers>,<user> gh-watch-start <artifact root> <owner/repo> <N>…` (the daemon wakes the agent on each event; arm the tail it prints as belt-and-braces for this session: the Monitor tool, or a background task where there is no Monitor tool), and register every open PR and issue the account has in the scope repos (`gh search prs --author <login> --state open`, and issues), not only this session's; answer any maintainer comment still without a reply first.
4. Confirm browser control (for UI work), and that `claude-swap list` shows the spare subscriptions.
5. Note the precedents and style (1.3).

---
