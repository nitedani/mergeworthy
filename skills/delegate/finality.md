# Finality prompt (map, imagine, hunt, converge, close)

Standards: `~/.mergeworthy/current/skills/code/SKILL.md` §Deep modules, §Phantom gate, §Removal gate. Include `delegate/agent.md`.

The user's prompt, verbatim; `finality`'s steps say which part each agent gets. Its words:
- **The orchestrator** is the main session: it starts every agent the prompt names (the mappers, the 3 branch agents, one per provider, the converging agent); each agent does its share itself, without starting agents.
- **§A, the shared node schema** is the per-function field list under PHASE A.
- **§B** is PHASE B; **§B½** is PHASE B½; Phase C is the implementer's (`delegate/implementer.md`).
- **§Closure** is the Owner-Safe closure paragraph at the end. *Every SETTLED decision propagated to its named surfaces*: every decision in `<work folder>/decisions/*.md` reached every place that describes it (code, tests, types, docs, PR bodies). *Owning lanes, mutations, reference captures, clean-tree scope*: the lanes that own the changed code (`code §Gates`), mutation probes (`code §Tests`), before/after screenshots, and a `git status` with only in-scope changes, each observed on the head.
- Where PHASE C cites the old core skill's task and authority rules, read `code §Owner code and authority`.
- *Fresh Guardian evidence* is Loop B's latest shape report (`converge` step 2).
- The design doc it ends with is posted through `post` (a gist counts) unless the repo keeps design docs.

```
Run a FINALITY PASS on <FEATURE / PATHS>.

The feature evolved through many design changes — added-to, patched, revised — which is exactly
how code reaches the state where the next person wants to rewrite it from scratch. I want the
opposite outcome: converge it NOW to the final state that will need no rewrite. That cannot be
done by lazily shuffling code around. Do it in three phases:

PHASE A — MAP.
Build a knowledge graph of the ENTIRE feature, line by line. It is tedious work; do it anyway.
Map the subsystems using one shared node schema; the orchestrator assigns mapper agents.
Subsystem: <name and paths>
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
Diverge first, then converge; mixing them kills the ideas, because the critic strangles the generator.
DIVERGE: write the problem clean, as its users would state it: what
must happen, what it may never cost, and the facts of the outside world it lives in (platform
APIs, runtimes, networks). No current design, no file or function names, no project terms, no
hint of how it is solved today: those anchor the branches on what exists. Pick 6 to 9 distinct frames:
1 or 2 drawn from that clean problem itself (the ways it fails, the people it serves, a field that
solved its like), never from the current solution, each with a vantage prompt you write; the rest
from the table below, mostly tagged code or design and at least 1 tagged wild (a row with both
tags counts for both). The orchestrator starts 3 branch agents in parallel, each given as design input only the
clean problem, the names and vantage prompts of 2 or 3 of those frames (no frame given twice) and
this instruction, verbatim:
"You are in DIVERGENT mode: a generator, not a critic. For each frame, under its name, design as its persona:
first the 3 obvious designs a senior engineer would give in thirty seconds from its vantage,
marked obvious, then 6 more past them, each changing an assumption, a responsibility or a
mechanism of those first 3, into the awkward middle nobody walks into. Each design is one or two sentences
and a one-line rationale. Do not evaluate, rank or hedge."
No branch sees another's output: branches that see each other anchor each other, and the run
collapses into one wider thought. Breadth means different underlying assumptions; ten variations
of one design are decoration.
| Frame | Vantage prompt | Tags |
|---|---|---|
| hardware engineer | You think in latency, memory layout and physical limits. Re-ask this as a firmware problem: what do the bus, the cache and the timing budget say? | code, wild |
| regulator | You audit systems for compliance and failure modes. What must be provable, traceable or refusable here? | design |
| 10-year-old | You have never seen software. Describe naive, unencumbered approaches; ignore convention. | wild |
| attacker | You are out to break it. Find how your obvious designs are exploited, fail or are sabotaged, then invert each attack into a design. | code, design |
| biology | Transplant a mechanism from biology (immune systems, plasticity, cell signaling, evolution) and force-fit it onto this problem. | wild |
| logistics | Take queues, batching, just-in-time, hub-and-spoke, returns and last-mile, and apply them literally. | code, design |
| game designer | What are the loops, rewards, friction, save states and skips? Treat the user as a player. | design |
| markets | Treat it as a market: buyers, sellers, market-makers. What would an auction or a clearing house be here? | design, wild |
| inversion | Ask how to guarantee the goal fails, then negate each answer back. | code, design |
| $0, one hour | No money, no team, one hour: the crudest version that still does the load-bearing thing. | code |
| infinite budget, ten years | Unlimited compute and engineers for a decade: the maximalist version. | design, wild |
| no load-bearing assumption | Name what your obvious designs take as fixed and the clean problem doesn't require (the framework, the store, request-response). It is gone: what is possible now? | code, design, wild |
| speedrunner | Find the glitches, skips and out-of-bounds tricks: the abusive but legal path to what the users want. | code, wild |
| ant colony | No planner: many simple agents, local rules, trails. How does it solve itself? | code, wild |
| 3am on-call | You are paged at 3am when this breaks. What design never pages you? | code, design |
(The frames and this phase's method are adapted from github.com/UditAkhourii/adhd, Copyright (c) 2026 ADHD contributors, under the MIT license in `delegate/adhd-LICENSE.txt`.)
CONVERGE: only now does the graph come in: the orchestrator gives the clean problem, the
assembled graph AND every branch’s lists, labeled by frame, to ONE converging agent. It clusters every design by its underlying
angle, not its wording ("remove the server", "cache-shaped", "batch window"); the obvious
designs are its baseline. A design that breaks what the clean problem says must happen or may never cost is out,
with its one-line reason. It ranks every other design on merit only (correctness, cost on the fast
path, behavior at the edges, simplicity; novelty earns nothing) and flags each trap with its
one-line reason (a hidden cost, a false economy, won't scale, premature abstraction). It
deepens the best 3 that aren't traps (fewer when fewer remain): how each works in 4 to 8 sentences, its load-bearing risk,
the first concrete step, and 3 to 5 child designs (variations, hybrids, what it unlocks), judged and ranked like the rest. A
non-obvious design wins only by beating the best obvious one; it commits to one, never "here
are the options". When no design remains, it names the limits that rule them all out instead of a pinnacle, and the orchestrator brings them to the user. From that it derives the PINNACLE design — the shape this feature would have if
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
changes and decide changes authorized by the user’s task (`core`, The task and 1.1.9).
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
