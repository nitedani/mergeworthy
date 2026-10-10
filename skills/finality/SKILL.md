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
2. **Phase A, map the code:** start the mapper agents on Opus. They only read code. Each builds a map of its part of the system: every file and function, what it does, what it depends on, and where patches piled up. Use one mapper when all the parts fit in one context, otherwise one per part, in parallel.
   Done: each part's map is in the work folder, ending with its list of core concepts.
3. **Phase B, imagine the design fresh:** write the problem as its users would state it, with no trace of the current solution, and pick the points of view to look at it from. Then start 3 separate design agents that can't see each other's work. After them, start one agent that compares all their designs against the map and derives the best design. All run on Opus, and none of them is the author.
   Done: the best design, how it differs from the current code, and a ranked plan of refactors are in the work folder.
4. **Phase B½, hunt fixes for problems that can't happen:** the prompt's queries over the map find suspects, such as guards nothing can reach and the same failure handled in two layers. You, the author, add counters to the suspects, run the test suites, and remove what turns out unneeded, in the removal order the prompt gives.
   Done: each suspect is either kept, with the counter that shows it runs, or removed, with the test of the layer that really handles it passing.
5. **Phase C, refactor to the design:** you carry out the plan as commits that don't change behavior, with the checks passing after each.
   Done: the commits are landed, and the short design doc is in the work folder (or posted, where the repo keeps no design docs).
6. **Check that everything agrees,** last, with the reviewer's and the guardian's evidence attached (`mergeworthy:converge`). The prompt's last list ("Owner-Safe closure") says what must agree.
   Done: every item in that list holds.

## The prompt

```
Run a FINALITY PASS on <FEATURE / PATHS>.

The feature evolved through many design changes. It was added to, patched and revised, which is
exactly how code reaches the state where the next person wants to rewrite it from scratch. I want
the opposite: bring it NOW to the final state that will need no rewrite. That can't be done by
lazily moving code around. Do it in three phases:

PHASE A — MAP.
Build a map (a knowledge graph) of the ENTIRE feature, line by line. It is tedious work; do it
anyway. Map each part of the system using one shared format for the entries. The orchestrator
assigns the mapper agents.
- For EVERY file: its role, and why it is a separate file.
- For EVERY function, class and constant (internal ones too):
  - its purpose (what it decides, not its name reworded);
  - inputs and outputs;
  - the state it reads and writes;
  - the invariants it relies on and keeps;
  - which modules it calls or passes data to, by path (especially across parts of the system);
  - how it fails;
  - what makes it hard to follow (deep nesting, flags that switch modes, rules no code states,
    state machines spread over several functions);
  - and ACCRETION SCARS, with line references: signs that patches piled up. Parameters nothing
    uses any more, generality nothing uses, shapes visibly patched across design changes,
    concepts duplicated across files, names that no longer match the behavior, comments that
    contradict the code, boundaries that exist only for historical reasons.
- Each mapper ends with:
  - the part's real concept list (the few ideas everything else builds on),
  - hidden dependencies between parts,
  - the places hardest to understand, ranked,
  - and what it would do differently if rewriting from scratch.
Mappers only read code. Their maps are files.

PHASE B — IMAGINE.
First go wide, then narrow down. GO WIDE: write the problem clean, as its users would state it:
what must happen, what it must never cost, and the facts of the outside world it lives in
(platform APIs, runtimes, networks). Leave out the current design, file and function names,
project terms, and any hint of how it's solved today: those would pull the designers toward what
exists. Pick 6 to 9 points of view (frames) from that clean problem (the ways it fails, the
people it serves, fields that solved similar problems). Never take them from the current
solution, and never use a fixed list. The orchestrator starts 3 separate design agents on the
session's model tier, each with the clean problem and 2 or 3 of the frames, no frame given twice.
Each first writes its 3 obvious designs, marked obvious, then 6 more beyond them, with no
evaluation. No design agent sees another's output. NARROW DOWN: only now does the map come in.
The orchestrator gives the assembled map AND every design agent's lists to ONE converging agent
on the session's model tier. The obvious designs are its baseline. It ranks every design on merit
only (correctness, cost on the common path, behavior at the edges, simplicity; novelty earns
nothing) and flags the traps. A non-obvious design wins only by beating the best obvious one.
From that it derives the PINNACLE design: the shape this feature would have if designed today,
from scratch, knowing everything the map knows, with NO obligation to the current file layout.
What the design must meet:
(1) every module must be able to STATE the reason for its complexity ("essential because
    <specific fact of the problem>") or be collapsed. Complexity that can't name its reason is
    accidental;
(2) the words are part of the design: one small, documented vocabulary, and functions a
    maintainer who didn't build this can read;
(3) separate the STABLE CORE from the BRITTLE EDGES. Anything that depends on another project's
    internals or on pinned versions goes behind a small, named interface, so the core survives
    their changes. Build only the boundary this present dependency needs, not one for a
    hypothetical future user;
(4) no speculative fixes, and in particular NO PHANTOM HOLES FROM PARTIAL READS. A claim that the
    code fails to handle something (a hole) is only valid when checked AGAINST THE WHOLE MAP:
    - whoever claims it must name the layer that SHOULD handle the behavior,
    - look up in the full map whether any layer DOES handle it,
    - and only an empty search is a hole.
    A hole that survives must also have a plausible trigger. Otherwise it is an accepted,
    documented limit;
(5) keep the code easy to follow;
(6) every mechanism in the map that corrects or guards against something passes the PROMISE
    test: name the promise it enforces, and whether anyone chose that promise on purpose.
    Mechanisms whose promise exists only in themselves and their own tests are candidates for
    removal in the plan.
Output: the pinnacle design, how it differs from the current code, and a ranked plan of
refactors that don't change behavior.

PHASE B½ — HUNT PHANTOM FIXES THAT CREPT IN.
Fixes for holes that never existed (phantom fixes) may already be IN the code. They are hard to
see, because a phantom fix looks just like legitimate extra safety. The difference is a fact
about the REST of the system. Run these queries on the map:
(1) RESPONSIBILITY COLLISIONS: for each kind of failure (reconnect, retry, deduplication,
    timeout, ordering, cleanup), list every place that claims to handle it. More than one, in
    different layers, makes them suspects, and the phantom is usually the one in the wrong layer;
(2) UNREACHABLE GUARDS: add counters to the suspect defensive branches and run the full test
    suite and the end-to-end tests through the REAL entry points. A counter that stays at zero
    is the sign. Unit tests that call the branch directly don't count: they are the test that
    keeps the phantom alive;
(3) ALIBI COMMENTS: "in case X…", where the map shows that another layer's contract forbids X
    or already handles it;
(4) STACKED SAFETY: a retry around a retry, deduplication on top of deduplication, recovery
    that repeats the caller's recovery;
(5) ORIGIN: fixes that landed without a test that failed first, and fixes added during review
    rounds whose promise nobody agreed to.
REMOVAL ORDER (the danger is a phantom fix HIDING a real gap in the layer above):
- first prove, with a test in the layer that should handle the failure, that it does;
- only then delete the duplicate;
- prove the deletion: that layer's test still passes, AND the deleted guard's counter stayed at
  zero, AND the test suite that runs the product for real in that area passes (unit tests alone
  don't settle it).
- If the counter goes above zero, it was not a phantom: you found a real gap upstream, or a
  responsibility both layers really share. Move it on purpose to the layer that should own it.
  Never keep both.

PHASE C — CONVERGE.
Carry out the plan:
- separate commits, each easy to revert,
- behavior unchanged (every moved mechanism's tests move with it; throwaway probes are re-run in
  the new place and still fail when the code is broken; a refactor makes earlier probe results
  void for the code it moved),
- reviewed adversarially before pushing.
Keep this phase free of behavior changes. Ask external maintainers about changes to behavior or
public API, and decide the changes the user's task asks for.
Finish by turning the map into a short design doc a maintainer can read in one sitting: the
concept list, the boundary between the stable core and the brittle edges, the glossary, and how
it all fits together.
Then run the Owner-Safe closure check:
- prove every SETTLED decision reached every place it names;
- every unit of work and every finding is closed, or held with a reason;
- code, tests, docs, types, UI and the PR's state agree;
- the reviewer's and a fresh Guardian's evidence is attached;
- CI, the product test suites for the touched areas, the mutation probes, the reference
  screenshots, and a check that the tree holds only in-scope changes were all seen to pass.
Finality isn't complete while any of these disagree.
```
