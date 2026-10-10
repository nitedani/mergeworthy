---
name: finality
description: "The finality pass, for code that drifted through many patches, a design thread that drifted over many rounds, being stuck with every option costing something ruled out, or a request for the ideal design: map the code, imagine the design fresh, hunt guards nothing needs, refactor to the new design, and check everything agrees."
---

# Finality

The finality pass brings code that has drifted through many patches, or a design discussion that has drifted, to a final state that won't need a rewrite. You map all of the code, imagine the design fresh from the problem itself, remove what crept in, and turn the rest into commits that keep behavior the same. The prompt below gives the details of each phase. You are the author and the orchestrator: you start the agents and hand them their inputs.

## Steps

1. **Decide that it applies.** Run it on your own, without being asked, when:
   - the work reshapes existing code rather than changing what it does;
   - a change can't be made cleanly because the area has taken too many patches;
   - every option costs something the user ruled out, or two fixes in one area didn't hold;
   - someone asks for the ideal design ("in a perfect world", "the pinnacle");
   - a design discussion has gone through three or more rounds without settling.

   Done: `task.md` names the reason it applies.
2. **Phase A, map the code:** start the mapper agents on Opus. They only read code. Each builds a map of its part of the system: every file and function, what it does, what it depends on, and where patches piled up. Use one mapper when all the parts fit in one context, otherwise one per part, in parallel. Each agent's brief, here and in Phase B, names the absolute path of the `code` standard (`mergeworthy:code`) next to the prompt, as what good code looks like.
   Done: each part's map is in the work folder, ending with its list of core concepts.
3. **Phase B, imagine the design fresh:** write the problem as its users would state it, with no trace of the current solution, and pick the points of view to look at it from. Then start 3 separate design agents that can't see each other's work. After them, start one agent that compares all their designs against the map and derives the best design. All run on Opus, and none of them is the author.
   Done: the best design, how it differs from the current code, and a ranked plan of refactors are in the work folder.
4. **Phase B½, hunt fixes for problems that can't happen** (a half step between designing and refactoring): the prompt's queries over the map find suspects, such as guards nothing can reach and the same failure handled in two layers. You, the author, add counters to the suspects (a temporary line that counts how often a branch runs), run the test suites, and remove what turns out unneeded, in the removal order the prompt gives.
   Done: each suspect is either kept, with the counter that shows it runs, or removed, with the test of the layer that really handles it passing.
5. **Phase C, refactor to the design:** you carry out the plan as commits that don't change behavior, with the checks passing after each.
   Done: the commits are landed, and the short design doc is in the work folder (or posted, where the repo keeps no design docs).
6. **Check that everything agrees,** last, with the reviewer's and the guardian's evidence attached (`mergeworthy:converge`). The prompt's last list ("Owner-Safe closure reconciliation": the checks that let the code's owner trust the result without redoing it) says what must agree.
   Done: every item in that list holds.

## The prompt

The prompt's words stay exactly as written, so here is what some of them mean. "The session's model tier" is Opus, as steps 2 and 3 say. Its Phase C, "CONVERGE", is this skill's step 5, not the `mergeworthy:converge` skill. "Mutations" are the probes in `mergeworthy:code`, Tests: break a production line and see a test fail. "Reference captures" are the screenshots of the reference you compare against (`mergeworthy:evidence`).

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
