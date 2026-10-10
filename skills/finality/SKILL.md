---
name: finality
description: "The finality pass, for code that drifted through many patches, a design thread that drifted over many rounds, being stuck with every option costing something ruled out, or a request for the ideal design: map, imagine, hunt phantom fixes, converge, and Owner-Safe closure."
---

# Finality

Converge drifted code, or a drifted design, to the final state that will need no rewrite: map all of it, imagine it fresh from the clean problem, remove what crept in, and land the rest as behavior-preserving commits.

## Steps

1. **Decide it applies.** Run it on your own, without being asked, when the work reshapes existing code rather than changing what it does; when a change can't be made cleanly because the area has taken too many patches; when every option costs something the user ruled out, or two fixes in one area didn't hold; when someone asks for the ideal design ("in a perfect world", the pinnacle); or when a design thread has drifted through three or more rounds.
   Done: `task.md` names the trigger.
2. **Phase A, map:** start the mappers, read-only, on Opus (one for all subsystems when they fit one context, otherwise one per subsystem in parallel).
   Done: each subsystem's graph is in the work folder, ending with its concept list.
3. **Phase B, imagine:** write the clean problem and its frames, then start the 3 isolated branch agents and, after them, the one converging agent, all on Opus and never the author.
   Done: the pinnacle design, its diff to the tree and the ranked convergence plan are in the work folder.
4. **Phase B½, hunt phantom fixes:** the graph queries are analysis; the author instruments, runs the suites and removes, in the prompt's removal order.
   Done: each suspect is kept with its counter's evidence, or removed with the owner's test green.
5. **Phase C, converge:** the author lands the plan as behavior-preserving commits, the gates green under each.
   Done: the commits are landed, and the short design doc is in the work folder (or posted, where the repo keeps no design docs).
6. **Owner-Safe closure,** last, with the reviewer's and the guardian's evidence attached.
   Done: every closure join in the prompt holds.

## The prompt

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
