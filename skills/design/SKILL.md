---
name: design
description: "Designing an API, a protocol or a module, or restructuring code: question the goal, list what every design must keep, prototype on what the code already lets you extend, design it more than once, propose it as a walkthrough."
---

# Design

A design is agreed with the maintainer before anyone builds it. It is the cleanest end state that keeps every invariant: everything any acceptable design must keep true. It is shown as the code its user will write. How much work it takes, which release it goes in and how users migrate to it belong to the plan for getting there, never to the design itself.

## Steps

1. **Question the goal.** Does it belong in this layer of the code? Find out which part of the system is responsible for the concern, and what already handles it. When a design needs framework tricks, workarounds for upstream code, or a growing list of cases it doesn't cover, it's in the wrong layer.
   Done: `task.md` says which layer is responsible for the concern, and why.
2. **List the invariants:** what any acceptable design must keep, from the user, the maintainer and the project. A design that limits what users can do needs the maintainer's OK. When users can avoid a mistake on their own, warn them about it instead of limiting them.
   Done: `task.md` lists the invariants, each with its source.
3. **Prototype on what the code already lets you extend** (plugins, hooks, options, existing APIs) before you add anything new. A new core API is only justified by a named requirement that the prototype can't meet. When two review rounds each find a new case that breaks the same rule, stop patching cases. Restate them as one rule, and check every supported setup against it.
   Done: the prototype runs, or `task.md` names the requirement it can't meet.
4. **Design it at least twice.**
   - **First, collect ideas from 3 Haiku agents** running in parallel (`mergeworthy:delegating`, step 1), each from one point of view: the user who calls it, the maintainer who keeps it, and a design from scratch, as if no code existed yet. Each proposes up to 3 designs, as the code its user would write, and checks each premise in the code at the pinned commit. Check each claim they make in the code yourself, and drop every design whose claims fail.
   - **Then have one fresh Opus agent write three designs** before comparing any. Its brief lists the designs that survived as questions under To check. One agent writes all three here, so the designs answer each other. Finality uses three separate agents on purpose, to get designs that can't influence each other. Its brief names the absolute path of the `code` standard (`mergeworthy:code`), whose Deep modules section and lenses each design is held to:
   - the smallest interface (one to three entry points);
   - the most flexible one;
   - the one that makes the most common caller's code trivial.

   Each is shown as the code the user writes, with a table that has one row per invariant and one column per design, each cell filled in from a measurement: a run of the prototype, a count of entry points, or user code that compiles against the sketch. A design that breaks an invariant is out, even "for now".
   Done: the work folder has the Haiku designs, each marked kept or dropped with the reason, and the table, with every cell measured.
5. **Recommend the smallest interface that keeps every invariant.** Recommend a larger one only with the requirement the smaller one fails, shown as code. Name its weakest part. Propose it as a walkthrough (`mergeworthy:writing`, Design threads: what the user writes, what happens on each path, why this shape, then numbered questions), and post it as `mergeworthy:posting` says. Build nothing beyond the prototype until the maintainer agrees to the shape.
   Done: the maintainer (or the user, in their own repo) agreed to a shape that keeps every invariant, and the link is in `task.md`.

