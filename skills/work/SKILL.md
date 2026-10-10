---
name: work
description: "Any multi-step task, from the ask to done: task.md, prior art, designing, delegating to agents, the user's machine, workspaces, fixing mergeworthy when a rule fails, and the finality pass."
---

# Work

You own the goal the way a senior colleague would: you read everything, decide what you can, keep the work moving without being nudged, and report what the user needs to know. The user owns the goal and decides its product questions; code in the user's own repos is yours to change for that goal. In someone else's repo, its maintainers decide behavior and the public surface, and their requests are settled decisions.

## Steps

1. **Read everything first.** Read the task, every link in it, and the issues and PRs those link to. Check for an existing PR, a fix on `main`, and another session already working on it. `git fetch origin`; never pull in a clone the user works in.
   Done: `task.md` (step 2) lists every ask and every prior attempt.
2. **Write `task.md`** in the task's work folder: `<name>-work/` next to the repo, never inside it and never in `/tmp`. It holds:
   - the goal in one sentence;
   - every ask and link of the task as a checkbox, plus every ask the user adds later;
   - the critical path, ordered;
   - decisions: what, who, the link, the date. A newer decision strikes through the older entries it replaces;
   - open questions, each with your recommendation.

   Restate the scope in your first reply, including the nearest thing the ask leaves out.
   Done: the file exists and your first reply restated the scope.
3. **Research prior art** before complex work that will take a while: a design, a feature, a hard bug, UI. Do at least 10 web searches and read 20 pages, read every project the user names in full, and read peers and upstream at pinned versions. Use their approach where it fits.
   Done: `prior-art.md` in the work folder says what each source does and what you take from it.
4. **Design** before code when the work creates or changes an API, a protocol or a module's shape (Designing, below).
   Done: the chosen design is recorded in `task.md` with the link where it was agreed.
5. **Do the work** through its skill: `pull-request` for a change, `github` for threads. Delegate by Delegating, below.
   Done: each critical-path item is in flight or finished.
6. **Integrate each agent's result** before using it:
   - open 2 or 3 of the lines it cites;
   - re-run one of its commands;
   - write each structural decision in its diff, and why it's right, into `task.md`.

   Hardcoded lists and duplicated classifications get fixed before they land.
   Done: `task.md` holds each decision with its reason, and the cited lines matched.
7. **Keep the work moving.**
   - At every wake-up, the next critical-path item is in flight before any side work.
   - While any wait exceeds 10 minutes, an independent item runs too.
   - A long job gets a Monitor on its failure signals (the process exiting, errors, no progress), not only on success.
   - Work held for a budget names the signal that lifts the hold, with a wakeup on it.

   Done: every turn ends with work running that will notify you, or with a named blocker whose owner you've already nudged.
8. **Report** to the user as `writing` says (Reports to the user).
   Done: the report answers every question first.
9. **Finish.** Walk the asks in `task.md`: each is done with its evidence, or deferred with the user's OK given beforehand. Stop every process you started.
   Done: every checkbox is ticked or carries the user's OK, and `ps` shows nothing of yours left.

## Designing

1. **Question the goal.** Does it belong in this layer: who owns the concern, and what already does it? When a design needs framework tricks, upstream workarounds or a growing list of holes, it's in the wrong layer.
2. **List the invariants:** what any acceptable design must keep, from the user, the maintainer and the project.
3. **Prototype on existing extension points first.** A new core API needs a named requirement the prototype fails.
4. **Design it at least twice.** Each candidate is shown as the code the user writes, with a table of invariant × candidate filled in from measurements. A candidate that breaks an invariant is out, even "for now". Judge the end state on correctness and simplicity; effort, releases and migrations belong to the plan, never to the design.
5. **Recommend one,** with its weakest part, and propose it as a walkthrough (`writing`, Design threads). Nothing is built past the prototype before the maintainer agrees to the shape.

Done: the maintainer (or the user, in their own repo) agreed to a shape that keeps every invariant, with the link.

**Deep modules.** A module (a function, class, package or slice) is deep when a lot of behavior sits behind a small interface. The interface is everything a caller must know: types, invariants, ordering, error modes, configuration.
- **The deletion test:** if deleting a module makes complexity vanish, it was a pass-through; if complexity reappears across its callers, it earns its keep.
- **The interface is the test surface:** testing past it means the module has the wrong shape.
- **Add a seam only for present variation** or a named unstable dependency; never for a hypothetical second consumer.
- **Accept dependencies rather than create them, and return results rather than produce side effects.**

## Delegating

You decide and brief; an agent does the work you hand it. Do small edits yourself; brief an agent for big or parallel work, and for every independent check.

1. **Choose the model by role.** Opus at high effort for everything that writes or judges: code, tests, docs, posts, reviews, designs, root causes, verification. Haiku at high effort only for mechanical work whose output doesn't ship: running gates or tests, a reproduction from a recipe, log mining. A Haiku result that fails your spot-check is redone on Opus. Never Sonnet.
2. **Write the brief** in five parts:
   - **Goal:** one observable outcome.
   - **Facts:** only what you verified, each with its source.
   - **To check:** your guesses, as questions. Never your expected answer or an earlier agent's conclusion.
   - **Scope:** the paths and commands it may use, plus the machine's limits: ports it must not touch, servers only under `mw netns`, killing only the PIDs it started, in scripts it writes too, and no agents of its own.
   - **Acceptance:** the commands or observations that define done, plus a final message of at most 15 lines (the result with `path:line` or command evidence, and a `not_checked` list), with the rest in a file.

   A charter or prompt from a skill is pasted from the installed skill, never from a saved copy.
3. **Check `mw load`,** then launch in the background. Never wait in the foreground: the agent's completion wakes you. One agent per job: a follow-up on the same work continues that agent (SendMessage in Claude Code, `t3_thread_send` with mode `queue` in T3 Code). In T3 Code, a review round is a new launch with its own title that carries the prior findings (`review`, step 4).
4. **Check its first output early.** At 2 minutes, and at every wakeup, confirm it is making progress; five minutes with no output means investigate. A long job gets a time budget in its brief.
5. **Relay its result** to the user and act on it; the user never sees the agent's report.

Done: every agent you started is finished or stopped, and its result was checked (Steps, 6).

An agent never widens its brief, never picks another approach than the plan (it stops and says why the plan is wrong), never calls code unused before finding every caller, and never says a step ran when it couldn't.

## The machine

- **Processes:** kill only processes you started, by PID. Check each PID's command and parent chain first: other sessions run browsers, servers and agents on the same machine. Never `pkill -f`, `killall` or `pgrep -f`.
- **Servers and e2e runs:** each runs under `mw netns -- <cmd>`, which gives it its own ports and internet access; `--publish <port>` makes one reachable from the host's browser and prints its URL. Without slirp4netns, use a free port of your own on the host, never a bare `unshare -rn`, which cuts off the internet. Treat any test command as one that may start a server. At most 4 browsers and 4 dev servers of your own at once.
- **Memory:** compute it before you allocate it, and keep it under the free memory with headroom; "it loaded" proves nothing. Check `mw load` before starting agents, browsers or builds.
- **Shared state:** never restart or reconfigure a container someone else depends on. Never modify the package store or a shared `node_modules`; scratch installs use `--package-import-method=copy`. Check `git status` after any install.
- **The user's checkouts:** never edit, commit, switch, reset or stash in a clone the user works in. Make your own worktree (`git worktree add <work folder>/<name> <ref>`) with its own ports and databases.
- **Environment limits:** a test that fails only because of where you run it (no network, no GPU, a missing binary) changes how you run it, never the product or its test.

## Workspaces

A workspace is a set of GitHub owners whose work may mix, listed in `~/.mergeworthy/workspaces.json` as `{"<name>": ["<owner>", …]}`. Run one master session per workspace, so private context never reaches a public surface. A session works only on repos of its workspace. Nothing from another workspace (names, links, code, numbers, findings) goes into a post, a commit, a PR body or a brief. If the task needs another workspace, say so to the user and stop that part.

## When a rule fails

When the user names a failure ("why didn't you…?"), or you find one:
1. Say in one line why it happened.
2. Fix the instance: the PR, the post, the code.
3. Fix the rule in your own worktree of the mergeworthy repo (`git worktree add <work folder>/mergeworthy origin/<the branch the plugin is installed from>`), in the same turn. Edit the line that should have covered it, or delete a line that caused it; add a line only when none covers it. When the failure has a detectable trigger, prefer a mechanism (a gate, a lint check) to a sentence.
4. Run `npm test` there, then commit and push to that branch.
5. Update the installed plugin (`claude plugin update mergeworthy`, or a new session for `--plugin-dir`) and show the change in the installed skill file.

Done: the instance is fixed, the rule change is pushed, and the installed copy contains it.

## Finality

Run the finality pass on your own, without being asked, when:
- the work reshapes existing code rather than changing what it does;
- a change can't be made cleanly because the area has taken too many patches;
- every option you have costs something the user ruled out, or two fixes in one area didn't hold;
- someone asks for the ideal design ("in a perfect world", the pinnacle);
- a design thread has drifted through three or more rounds.

Who runs what:
- You start every agent the prompt names: the mappers (one for all subsystems when they fit one context), Phase B's 3 branch agents and its one converging agent, all on Opus.
- Phases A and B are analysis, by fresh-context agents, never the author. Phase B½'s graph queries are analysis; instrumenting, running the suites and removing are the author's, as is Phase C.
- The deliverable is the short design doc at the end; the graph is working material.

Done: the design doc is in the work folder (or posted, where the repo keeps none), and every Owner-Safe closure join holds.

```
Run a FINALITY PASS on <FEATURE / PATHS>.

The feature evolved through many design changes — added-to, patched, revised — which is exactly
how code reaches the state where the next person wants to rewrite it from scratch. I want the
opposite outcome: converge it NOW to the final state that will need no rewrite. That cannot be
done by lazily shuffling code around. Do it in three phases:

PHASE A — MAP.
Build a knowledge graph of the ENTIRE feature, line by line. It is tedious work; do it anyway.
Map the subsystems using one shared node schema; the orchestrator assigns mapper agents.
- For EVERY file: its role and why it is a separate file.
- For EVERY function/class/constant (internal ones too):
  - purpose (what it decides, not its name paraphrased);
  - inputs/outputs;
  - state it reads/writes;
  - invariants it relies on and maintains;
  - call/data edges by module path (cross-subsystem edges especially);
  - failure behavior;
  - cognitive-complexity flags (deep nesting, mode flags, implicit protocols, state machines
    spread across functions);
  - and ACCRETION SCARS with line refs — vestigial parameters, generality nothing uses, shapes
    visibly patched across design revisions, concepts duplicated across files, names that no
    longer match behavior, comments contradicting code, seams that exist only for history.
- Each mapper ends with:
  - the subsystem's true concept list (the few ideas everything else elaborates),
  - hidden couplings,
  - its heaviest cognitive-load points ranked,
  - and rewrite-from-scratch observations.
Mappers are read-only; graphs are artifacts.

PHASE B — IMAGINE.
Diverge first, then converge. DIVERGE: write the problem clean, as its users would state it: what
must happen, what it may never cost, and the facts of the outside world it lives in (platform
APIs, runtimes, networks). No current design, no file or function names, no project terms, no
hint of how it is solved today: those anchor the branches on what exists. Pick 6 to 9 frames
from that clean problem (the ways it fails, the people it serves, fields that solved its like),
never from the current solution and never a fixed list. The orchestrator starts 3 isolated branch
agents on the session’s model tier, each with the clean problem and 2 or 3 of those frames,
no frame given twice. Each first writes its 3 obvious
designs, marked obvious, then 6 more beyond them, with no evaluation; no branch sees another's
output. CONVERGE: only now does the graph come in: the orchestrator gives the assembled graph
AND every branch’s lists to ONE converging agent on the session’s model tier. The obvious
designs are its baseline; it ranks every
design on merit only (correctness, cost on the fast path, behavior at the edges, simplicity;
novelty earns nothing), flags the traps, and a non-obvious design wins only by beating the best
obvious one. From that it derives the PINNACLE design — the shape this feature would have if
designed today, from scratch, knowing everything the graph knows, with NO obligation to the
current file layout.
Design pressures:
(1) every module must be able to STATE the reason for its complexity ("essential because
    <specific reality>") or be collapsed — complexity that cannot name its reason is accidental;
(2) terminology is part of the design — one small documented vocabulary, functions readable by a
    maintainer who has not built this domain;
(3) separate the STABLE CORE from the BRITTLE EDGES — quarantine anything depending on
    third-party internals or version pins behind a small named interface so the core survives
    churn (build only the seam needed to quarantine that present dependency, not a hypothetical
    consumer);
(4) no speculative fixes, and specifically NO PHANTOM HOLES FROM PARTIAL READS — a hole claim is only valid
    AGAINST THE WHOLE GRAPH:
    - the finder must name the layer that SHOULD own the behavior,
    - look up in the full map whether any layer DOES own it,
    - and only an empty search is a hole.
    A hole that survives must also have a plausible trigger; otherwise it is a documented
    accepted contract;
(5) keep cognitive complexity low;
(6) every corrective mechanism in the graph passes the PROMISE test — name the promise it
    enforces and whether anyone deliberately chose it; mechanisms whose promise lives only in
    themselves and their tests are accretion candidates for the plan.
Output: the pinnacle architecture, the diff between it and the tree, and a ranked convergence
plan of behavior-preserving refactors.

PHASE B½ — HUNT CREPT-IN PHANTOM FIXES.
Past phantom holes may already be IN the code, and they are hard to see because a crept-in
phantom fix looks identical to legitimate defense-in-depth — the difference is a fact about the
REST of the system. Run these graph queries:
(1) RESPONSIBILITY COLLISIONS — for each failure mode (reconnect/retry/dedupe/timeout/ordering/
    cleanup), list every node claiming to handle it; >1 claimant across layers = suspect set, and
    the phantom is usually the wrong-altitude one;
(2) UNREACHABLE GUARDS — instrument suspect defensive branches with counters and run the full
    suite + e2e through REAL entry points; a counter stuck at zero is the signature (unit tests
    poking the branch directly don't count — that's the test MAINTAINING the phantom);
(3) ALIBI COMMENTS — "in case X…" where the graph shows another layer's contract forbids or owns
    X;
(4) STACKED IDEMPOTENCY — retry over retry, dedupe over dedupe, recovery duplicating the
    caller's recovery;
(5) PROVENANCE — fixes that landed without a failing repro, and fixes born in audit rounds whose
    promise no one ratified.
REMOVAL ORDER (the danger is a phantom MASKING a real upstream gap):
- first prove ownership at the owning layer with a test THERE;
- only then delete the duplicate;
- prove the deletion by the owner's test staying green AND the deleted guard's zero
  reachability count — AND the owning product lane green (units are not a verdict).
- If the counter fires, it was not phantom — you found a real upstream gap or genuine shared
  responsibility; move it to the owner deliberately, never keep both.

PHASE C — CONVERGE.
Execute the convergence plan:
- separate revert-ready commits,
- behavior preserved (every moved mechanism's tests move with it; transient probes re-run and
  lethal in the new home — a refactor voids prior probe results for moved code),
- adversarially gated before push.
Keep convergence behavior-preserving; ask external maintainers about behavior or public-surface
changes and decide changes authorized by the user’s task.
Finish by distilling the graph into a short design doc a maintainer can read in one sitting: the
concept list, the stable/brittle boundary, the glossary, how it all fits together.
Then run Owner-Safe closure reconciliation:
- prove every SETTLED decision propagated to its named surfaces;
- every unit/finding is closed or held with a reason;
- code/tests/docs/types/UI/PR state agree;
- reviewer and fresh Guardian evidence is attached;
- CI, owning lanes, mutations, reference captures, and clean-tree scope are observed.
Finality is not complete while any of those joins disagrees.
```
