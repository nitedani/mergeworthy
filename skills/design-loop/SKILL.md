---
name: design-loop
description: "Designing an API, protocol or module, or restructuring code: the design loop, prototypes, walkthroughs, deep modules (1.4.1), design it twice."
---

## 1.4 Design loop (Tier ≥ M, any API or protocol)

The design loop takes a new API or protocol from candidates to a shape the maintainer has agreed to, before any PR converges.

- **Design the end state first, then plan the way there.** The cleanest end state from first principles wins; effort, release count and diff size belong to the plan that builds it, and 1.1.15 judges findings, never a design's shape. Judge a design on its correctness, its invariants and how simple the final shape is. The work to get there (releases, migrations, how many PRs) is planning, never an argument for a weaker shape, and "later" or "until someone needs it" is not a design decision. Do the work the design needs now, and defer nothing that the design depends on.

0. **Prototype on existing extension points first.** Before any new core API, prototype the solution that uses only existing extension points (e.g. an existing middleware, render hook or plugin hook). That prototype is the first candidate; a core change needs a named requirement the prototype fails.
1. **Draft `decisions/<name>.md`:** the invariant table (1.1.2), and the candidates rated as in `pull-request` step 3 (open `pull-request` for the rating steps). Rank the candidates by interface size. Recommend the smallest that keeps every invariant; recommend a larger one only with the requirement the smaller one fails, shown as code.
2. **Prototype** to prove the invariants end to end: a real browser, request counts, timing, byte comparisons, dev, prod and static hosting.
3. **Adversarial review** of the prototype (`review`: open it for who reviews): how does the prototype fail? When two review rounds each find a new case breaking the same rule, stop patching cases. Restate the cases as one rule, walk every setup through that rule yourself, then ask again.
4. **Propose to maintainers** only when no invariant is broken, as a **walkthrough**:
   1. the one new concept, in one sentence;
   2. what the user or extension writes, as code;
   3. what happens on each path a user can take;
   4. why this format, each alternative shown the same way (as `writing` says, as code), and the recommended one's downsides against `main`, found by arguing against it before posting;
   5. numbered questions.

   The walkthrough holds nothing that changes existing behavior the feature doesn't strictly need. Every term is explained in plain words.
5. **Post the walkthrough** as soon as the prototype holds the invariants.
   - **Before the maintainer OKs the shape,** one pass: `converge`'s loops (open `converge` to work a PR to its final state) run only on a shape the maintainer has OK'd (the user's own repos: `converge`).
   - **After a PR opens,** each commit answers a user or maintainer request, a red CI, a found bug, or a mergeworthy rule.


### 1.4.1 Codebase design: deep modules

**Aim for deep modules wherever code is written, designed or restructured,** from its first line, not only when a guardian reviews it. That covers the design loop, `pull-request` steps 3 and 4, the finality pass and `refactor`. A deep module has a lot of behaviour behind a small interface, sits at a clean seam, and is testable through that interface.

**Use these terms exactly,** in code reviews and PR text too; don't substitute component, service, API or boundary:

- **Module**: anything with an interface and an implementation, at any scale (a function, a class, a package, a slice across tiers).
- **Interface**: everything a caller must know to use the module correctly: the types, and also invariants, ordering, error modes, required configuration and performance characteristics. Not only a TypeScript `interface` or a class's public methods.
- **Implementation**: the code inside a module.
- **Depth**: leverage at the interface, the behaviour a caller or test can exercise per unit of interface it has to learn. Deep: a lot behind a small interface. Shallow: an interface nearly as complex as what it hides (a pass-through). Not a ratio of lines, which would reward padding.
- **Seam** (Feathers): where behaviour can change without editing in that place; where a module's interface lives. Where to put a seam is a decision of its own, apart from what goes behind it. Not "boundary".
- **Adapter**: a concrete thing that satisfies an interface at a seam; a role, not a size.
- **Leverage** (what callers get) and **locality** (what maintainers get: a change, a bug, a fix in one place).

Principles:
- **Depth belongs to the interface.** A deep module may be built from small parts with internal seams that its own tests use; those seams are not part of its interface.
- **The deletion test:** imagine deleting the module. If complexity vanishes, the module was a pass-through; if complexity reappears across its callers, the module earns its keep.
- **The interface is the test surface:** callers and tests cross the same seam. Needing to test past the interface means the module has the wrong shape.
- **One adapter is a hypothetical seam, two are a real one:** don't add a seam until something varies across it.
- **Shaping an interface,** ask: fewer methods? simpler parameters? more hidden inside?
- **For testability:**
  - accept dependencies rather than create them (`processOrder(order, gateway)`, not a `new StripeGateway()` inside);
  - return results rather than produce side effects (`calculateDiscount(cart): Discount`, not `applyDiscount(cart): void`);
  - a small surface means fewer tests and simpler setup.

**Deepening a cluster of shallow modules:** classify each dependency first, since its category decides how the deep module is tested at its seam.
- **In-process** (pure computation, in-memory state): merge the modules and test through the new interface; no adapter.
- **Local-substitutable** (a local stand-in exists, e.g. PGLite for Postgres, an in-memory filesystem): test with the stand-in in the suite; the seam stays internal.
- **Remote but owned** (your own services over a network): a port at the seam. The deep module owns the logic; the transport is an injected adapter (in-memory in tests, HTTP or a queue in production).
- **True external** (a third party you don't control): an injected port, a mock adapter in tests.

**Tests after deepening:**
- **Internal seams stay internal.** A deep module may keep internal seams for its own tests; don't expose them through its interface because tests use them.
- **Replace, don't layer.** Once tests at the deepened interface exist, delete the old tests on the shallow parts.
- **Assert outcomes through the interface,** so the tests survive internal refactors. A test that changes with the implementation tests past the interface.

**Design it twice:** your first interface is unlikely to be the best. The three designs are the candidates of 1.4 step 1.
1. **Frame the problem for the user:** the constraints any interface must meet, the dependencies and their categories, and a rough code sketch that makes the constraints concrete. The sketch is not a proposal.
2. **Have one fresh-context agent design it three times** (1.1.14). The agent writes all three before comparing any. Each design works under a different one of these constraints, and none reuses another's entry points:
   - minimize the interface (1–3 entry points);
   - maximize flexibility; or, where dependencies cross a seam, ports and adapters in its place;
   - make the most common caller trivial.
3. **Each design returns:** the interface (types, invariants, ordering, error modes), a usage example, what hides behind the seam, its dependency strategy and adapters, and where its leverage is high or thin.
4. **Compare and recommend.** Compare the designs on depth, locality and seam placement. Recommend one (or a hybrid) and say why: a strong read, not a menu.
