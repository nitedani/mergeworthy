---
name: design
description: "When you are about to choose an API, a protocol, a module boundary or a restructure: invariants first, design it twice, prototype, then propose."
---

## When

You are about to add or change a public surface, a protocol or a module boundary, or to restructure code; or a maintainer asks "how about X?" about a design.

## Steps

1. List the invariants any acceptable design must keep, and put them at the top of every agent and reviewer brief.
2. Prototype the solution that uses only existing extension points first; a change to the core needs a named requirement that prototype fails.
3. Design it twice: give three fresh agents the same problem, each under a different constraint (the smallest interface, the most common caller made trivial, ports and adapters where dependencies cross a seam). Compare them in a table with one row per invariant, filled with measured evidence, and reject any design that breaks one.
4. Prototype the chosen design end to end, in the real runtime, and have a fresh reader attack it: how does it fail?
5. Propose it to the owner as a walkthrough:
   - **The concept:** the one new idea, in one sentence.
   - **The code:** what the user or extension writes.
   - **The paths:** what happens on each path a user can take.
   - **The alternatives:** each shown the same way, with why it lost.
   - **The questions:** numbered, each with your recommendation.
6. Build only the shape the owner accepted; use [deep-modules.md](deep-modules.md) for the code's shape.

## Done when

The owner accepted the walkthrough, and the invariant table shows no broken row.

## Never

- Break an invariant "for now".
- Pull behavior the feature doesn't strictly need into the proposal.
- Send a design comparison as a table only: show the code.

## Enforced by

Nothing: this is judgment.

## Next

`mergeworthy:post` for the walkthrough, then `mergeworthy:change`.
