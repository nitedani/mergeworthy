---
name: finality
description: "The finality pass, for code that has drifted through many patches, a design thread that has drifted over many rounds, being stuck with every option costing something ruled out, or a request for the ideal design: map, imagine, hunt phantom fixes, converge, close."
---

# Finality

Converges code or a design to the final state that will need no rewrite. The prompt is `delegate/finality.md`'s, filled; each step gives one agent its part. Called by `converge` step 0, `design` steps 5 and 7 (steps 2–3; Phase C after `design` step 9, in `pull-request` step 6) and `pull-request` steps 5–6; when done, return to the calling step.

## Steps

1. **When:** run it unasked when the work reshapes existing code rather than changing what it does, or a change meant to be small can't be made cleanly because the area has taken too many patches; when you're stuck (every option costs something the user ruled out, or two fixes in the same area haven't held), before bringing options to the user; when someone asks for the ideal design (brainstorming, "in a perfect world", the pinnacle); when a design thread has drifted (three or more rounds of proposals, or replies answering only the latest idea), before the next reply.
2. **Phase A, map:** one mapper for all subsystems when they fit one context, else one per subsystem in parallel, each brief naming its own on a line `Subsystem: <name and paths>`; fresh-context agents (role `research`, `Fan-out: finality step 2`), never the author's.
   Open: `delegate/finality.md` (PHASE A) · Record: `<work folder>/finality/<name>-map-<subsystem>.md` each
3. **Phase B, imagine.** You write the clean problem and its 6–9 frames first (PHASE B); 3 branch agents in parallel, `branch1`–`branch3` (`delegate §Model class`); then one converging agent with the graph and every branch's lists. You rate the pinnacle and decide.
   Open: `delegate/finality.md` (PHASE B) · Record: branches' `<work folder>/finality/<name>.<provider>.branch<N>.md`; `<work folder>/finality/<name>-pinnacle.md` with a line `Pinnacle: <the design>` and a line `Plan:`, then one numbered line per step · Run (on a branch): `pr-steps finality <that file>` · Hook: pre-bash-guard (a code file's 6th change since review waits for it)
4. **Phase B½, hunt phantom fixes:** the graph queries by Phase B's converging agent; instrumenting guards, running the full suite and e2e, and the removals by the implementer.
   Open: `delegate/finality.md` (PHASE B½); `code §Removal gate` · Record: `<work folder>/finality/<name>-phantoms.md`: suspects, counters, removals
5. **Phase C, converge:** behavior-preserving, revert-ready commits through an implementer, gates after each.
   Open: `delegate/implementer.md` · Record: commits
6. **The deliverable is the short design doc**, posted through `post` (a gist counts) unless the repo keeps design docs; in a design thread, then `design` step 7's WIP update.
   Open: `post` · Record: the doc's link or repo path
7. **Owner-Safe closure,** last in `converge` step 5: it needs the reviewer's and the shape pass's evidence.
   Open: `delegate/finality.md` (the closure paragraph and its header's glossary) · Record: `<work folder>/finality/<name>-closure.md`
