---
name: design
description: "Designing an API, a protocol or a module, or restructuring code: question the goal, invariants, prototype on existing extension points, design it more than once, a walkthrough; deep modules."
---

# Design

A design is agreed before it is built: the cleanest end state that keeps every invariant, shown as the code its user writes, and chosen with the maintainer. Effort, releases and migrations belong to the plan, never to the design.

## Steps

1. **Question the goal.** Does it belong in this layer: who owns the concern, and what already does it? When a design needs framework tricks, upstream workarounds or a growing list of holes, it's in the wrong layer.
   Done: `task.md` says which layer owns the concern, and why.
2. **List the invariants:** what any acceptable design must keep, from the user, the maintainer and the project. A limit on what users can do needs the maintainer's OK, and a mistake the user can avoid gets a warning, not a limit.
   Done: `task.md` lists the invariants, each with its source.
3. **Prototype on existing extension points first.** A new core API needs a named requirement the prototype fails. When two review rounds each find a new case breaking the same rule, stop patching cases: restate them as one rule and walk every setup through it.
   Done: the prototype runs, or `task.md` names the requirement it fails.
4. **Design it at least twice.** Have one fresh Opus agent write three designs before comparing any: the smallest interface (one to three entry points), the most flexible one, and the one that makes the most common caller trivial. Each is shown as the code the user writes, with a table of invariant × candidate filled in from measurements. A candidate that breaks an invariant is out, even "for now".
   Done: the table is in the work folder, every cell measured.
5. **Recommend the smallest interface that keeps every invariant,** a larger one only with the requirement the smaller one fails, shown as code. Name its weakest part, and propose it as a walkthrough (`writing`, Design threads), posted by `posting`. Nothing is built past the prototype before the maintainer agrees to the shape.
   Done: the maintainer (or the user, in their own repo) agreed to a shape that keeps every invariant, with the link in `task.md`.

## Deep modules

A module (a function, class, package or slice) is deep when a lot of behavior sits behind a small interface. The interface is everything a caller must know: types, invariants, ordering, error modes, configuration.
- **The deletion test:** if deleting a module makes complexity vanish, it was a pass-through; if complexity reappears across its callers, it earns its keep.
- **The interface is the test surface:** testing past it means the module has the wrong shape. When deepening, each dependency's kind (in-process, a local stand-in, your own remote service, a true external) decides how its seam is tested, and the tests at the new interface replace the old ones on the shallow parts.
- **Add a seam only for present variation** or a named unstable dependency; never for a hypothetical second consumer.
- **Accept dependencies rather than create them, and return results rather than produce side effects.**
