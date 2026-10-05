---
name: finality
description: "The finality pass, for code that has drifted through many patches: map, imagine, hunt phantom fixes, converge, and Owner-Safe closure."
---

# Finality pass

**When to run it.** The work reshapes existing code rather than changing what it does, or a change you meant to make small cannot be made cleanly because the area has taken too many patches.

**Who runs it.** Phases A and B are analysis by the reviewer (`review`) or a fresh-context subagent, never the author's context; the prompt's "strongest-model agent" is one of these, never above the default tier (`core`, the task). Phase C is the author implementing commit by commit, with the gates green underneath.

**"Bring me the decision"** in Phase C: in an external maintainer's code, stop and ask the person who owns it; in the user's own repos and beta features, decide, act, and report (`core`, the task). Convergence itself is behavior-preserving.

"Fan out parallel mapper agents" means one subagent per subsystem (at most 3 at once, 1.1.14). The graph is working material; the short design doc at the end is the deliverable.

Run the prompt as written:

```
Run a FINALITY PASS on <FEATURE / PATHS>. The feature evolved through many design changes —
added-to, patched, revised — which is exactly how code reaches the state where the next person
wants to rewrite it from scratch. I want the opposite outcome: converge it NOW to the final
state that will need no rewrite. That cannot be done by lazily shuffling code around. Do it in
three phases:

PHASE A — MAP. Build a knowledge graph of the ENTIRE feature, line by line. It is tedious work;
do it anyway. Fan out parallel mapper agents over the subsystems, one shared node schema. For
EVERY file: its role and why it is a separate file. For EVERY function/class/constant (internal
ones too): purpose (what it decides, not its name paraphrased); inputs/outputs; state it
reads/writes; invariants it relies on and maintains; call/data edges by module path (cross-
subsystem edges especially); failure behavior; cognitive-complexity flags (deep nesting, mode
flags, implicit protocols, state machines spread across functions); and ACCRETION SCARS with
line refs — vestigial parameters, generality nothing uses, shapes visibly patched across design
revisions, concepts duplicated across files, names that no longer match behavior, comments
contradicting code, seams that exist only for history. Each mapper ends with: the subsystem's
true concept list (the few ideas everything else elaborates), hidden couplings, its heaviest
cognitive-load points ranked, and rewrite-from-scratch observations. Mappers are read-only;
graphs are artifacts.

PHASE B — IMAGINE. Give the assembled graph to ONE strongest-model agent (one at a time, always
on the hardest task) and have it derive the PINNACLE design — the shape this feature would have
if designed today, from scratch, knowing everything the graph knows, with NO obligation to the
current file layout. Design pressures: (1) every module must be able to STATE the reason for its
complexity ("essential because <specific reality>") or be collapsed — complexity that cannot
name its reason is accidental; (2) terminology is part of the design — one small documented
vocabulary, functions readable by a maintainer who has not built this domain; (3) separate the
STABLE CORE from the BRITTLE EDGES — quarantine anything depending on third-party internals or
version pins behind a small named interface so the core survives churn and a future second
consumer could plug in (build the boundary, NOT the second consumer); (4) no speculative fixes,
and specifically NO PHANTOM HOLES FROM PARTIAL READS — a hole claim is only valid AGAINST THE
WHOLE GRAPH: the finder must name the layer that SHOULD own the behavior, look up in the full
map whether any layer DOES own it, and only an empty search is a hole. A hole that survives must
also have a plausible trigger; otherwise it is a documented accepted contract; (5) keep
cognitive complexity low; (6) every corrective mechanism in the graph passes the PROMISE test —
name the promise it enforces and whether anyone deliberately chose it; mechanisms whose promise
lives only in themselves and their tests are accretion candidates for the plan.
Output: the pinnacle architecture, the diff between it and the tree, and a ranked convergence
plan of behavior-preserving refactors.

PHASE B½ — HUNT CREPT-IN PHANTOM FIXES. Past phantom holes may already be IN the code, and they
are hard to see because a crept-in phantom fix looks identical to legitimate defense-in-depth —
the difference is a fact about the REST of the system. Run these graph queries: (1) RESPONSIBILITY
COLLISIONS — for each failure mode (reconnect/retry/dedupe/timeout/ordering/cleanup), list every
node claiming to handle it; >1 claimant across layers = suspect set, and the phantom is usually
the wrong-altitude one; (2) UNREACHABLE GUARDS — instrument suspect defensive branches with
counters and run the full suite + e2e through REAL entry points; a counter stuck at zero is the
signature (unit tests poking the branch directly don't count — that's the test MAINTAINING the
phantom); (3) ALIBI COMMENTS — "in case X…" where the graph shows another layer's contract
forbids or owns X; (4) STACKED IDEMPOTENCY — retry over retry, dedupe over dedupe, recovery
duplicating the caller's recovery; (5) PROVENANCE — fixes that landed without a failing repro,
and fixes born in audit rounds whose promise no one ratified.
REMOVAL ORDER (the danger is a phantom MASKING a real upstream gap): first prove ownership at
the owning layer with a test THERE; only then delete the duplicate; prove the deletion by the
owner's test staying green AND the deleted guard's zero reachability count — AND the owning
product lane green (units are not a verdict). If the counter fires, it was not phantom — you
found a real upstream gap or genuine shared responsibility; move it to the owner deliberately,
never keep both.

PHASE C — CONVERGE. Execute the convergence plan: separate revert-ready commits, behavior
preserved (every moved mechanism's tests move with it; transient probes re-run and lethal in
the new home — a refactor voids prior probe results for moved code), adversarially gated before
push. Where the pinnacle differs from the tree in ways that change behavior or public surface,
STOP and bring me the decision — convergence is refactoring, not redesign-by-stealth. Finish by
distilling the graph into a short design doc a maintainer can read in one sitting: the concept
list, the stable/brittle boundary, the glossary, how it all fits together.
Then run Owner-Safe closure reconciliation: prove every SETTLED decision propagated to its named
surfaces; every unit/finding is closed or held with a reason; code/tests/docs/types/UI/PR state agree;
reviewer and fresh Guardian evidence is attached; CI, owning lanes, mutations, reference captures,
and clean-tree scope are observed. Finality is not complete while any of those joins disagrees.
```
