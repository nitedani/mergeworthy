## 1.4 Design loop (Tier ≥ M, any API or protocol)

0. Before any new core API, prototype the solution that uses only existing extension points (e.g. an existing middleware, render hook or plugin hook). It is the first candidate; a core change needs a named requirement it fails.
1. Draft `decisions/<name>.md`: the invariant table (1.1.2), and the candidates rated per Part 2 step 3.
2. **Prototype** to prove the invariants end to end: a real browser, request counts, timing, byte comparisons, dev, prod and static hosting.
3. **Adversarial review** of the prototype with the review model: how does it fail?
4. Propose to maintainers only when no invariant is broken, as a **walkthrough**:
   1. the one new concept, in one sentence;
   2. what the user or extension writes, as code;
   3. what happens on each path a user can take;
   4. why this format, each alternative shown the same way (1.6 comparisons);
   5. numbered questions.

   Nothing that changes existing behavior the feature doesn't strictly need. Every term explained in plain words.
5. Post the walkthrough as soon as the prototype holds the invariants. Part 3's loops run only on a shape the maintainer has OK'd; until then, one pass. After a PR opens, each commit answers a user or maintainer request, a red CI, a found bug, or a rule in this file.


### 1.4.1 Codebase design: deep modules

Wherever code is written, designed or restructured (from its first line, not only when a guardian reviews it: the design loop, Part 2 steps 3 and 4, the finality pass, Part 3's refactor pass), aim for deep modules: a lot of behaviour behind a small interface, placed at a clean seam, testable through that interface. Use these terms exactly, in code reviews and PR text too; don't substitute component, service, API or boundary:

- **Module**: anything with an interface and an implementation, at any scale (a function, a class, a package, a slice across tiers).
- **Interface**: everything a caller must know to use the module correctly: the types, and also invariants, ordering, error modes, required configuration and performance characteristics. Not only a TypeScript `interface` or a class's public methods.
- **Implementation**: the code inside a module.
- **Depth**: leverage at the interface, the behaviour a caller or test can exercise per unit of interface it has to learn. Deep: a lot behind a small interface. Shallow: an interface nearly as complex as what it hides (a pass-through). Not a ratio of lines, which would reward padding.
- **Seam** (Feathers): where behaviour can change without editing in that place; where a module's interface lives. Where to put it is a decision of its own, apart from what goes behind it. Not "boundary".
- **Adapter**: a concrete thing that satisfies an interface at a seam; a role, not a size.
- **Leverage** (what callers get) and **locality** (what maintainers get: a change, a bug, a fix in one place).

Principles:
- Depth belongs to the interface. A deep module may be built from small parts with internal seams that its own tests use; they're not part of its interface.
- **The deletion test**: imagine deleting the module. If complexity vanishes, it was a pass-through; if it reappears across its callers, it earns its keep.
- **The interface is the test surface**: callers and tests cross the same seam. Needing to test past the interface means the module has the wrong shape.
- **One adapter is a hypothetical seam, two are a real one**: don't add a seam until something varies across it.
- When shaping an interface, ask: fewer methods? simpler parameters? more hidden inside?
- For testability: accept dependencies rather than create them (`processOrder(order, gateway)`, not a `new StripeGateway()` inside); return results rather than produce side effects (`calculateDiscount(cart): Discount`, not `applyDiscount(cart): void`); a small surface means fewer tests and simpler setup.

**Design it twice**: for a new interface, have parallel fresh-context agents design it in radically different ways, then compare the candidates on depth, locality and seam placement (the candidates of step 1).
