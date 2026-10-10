---
name: design
description: "Designing an API, a protocol or a module, or restructuring code: question the goal, list what every design must keep, prototype on what the code already lets you extend, design it more than once, propose it as a walkthrough; deep modules."
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
4. **Design it at least twice.** Have one fresh Opus agent write three designs before comparing any:
   - the smallest interface (one to three entry points);
   - the most flexible one;
   - the one that makes the most common caller's code trivial.

   Each is shown as the code the user writes, with a table that has one row per invariant and one column per design, each cell filled in from a measurement. A design that breaks an invariant is out, even "for now".
   Done: the table is in the work folder, and every cell was measured.
5. **Recommend the smallest interface that keeps every invariant.** Recommend a larger one only with the requirement the smaller one fails, shown as code. Name its weakest part. Propose it as a walkthrough (`mergeworthy:writing`, Design threads: what the user writes, what happens on each path, why this shape, then numbered questions), and post it as `mergeworthy:posting` says. Build nothing beyond the prototype until the maintainer agrees to the shape.
   Done: the maintainer (or the user, in their own repo) agreed to a shape that keeps every invariant, and the link is in `task.md`.

## Deep modules

A module (a function, a class, a package, a part of a system) is deep when a lot of behavior sits behind a small interface. The interface is everything a caller must know to use it: its types, the rules it relies on, the order of calls, how it fails, and its configuration.
- **The deletion test:** imagine deleting the module. If the complexity disappears with it, the module only passed calls through. If the complexity comes back in every caller, the module earns its place.
- **Test through the interface.** If a test has to reach past the interface, the module has the wrong shape. When you make a module deeper, test each of its dependencies according to what it is: code in the same process, a local stand-in for a service, your own remote service, or a true third-party service. Tests written against the new interface replace the old tests of the shallow parts.
- **Add a seam (a point where one implementation can be swapped for another) only for variation that exists today,** or for a named dependency that is known to change. Never add one for a second user who might come one day.
- **Take dependencies as arguments rather than creating them inside, and return results rather than causing side effects.**
