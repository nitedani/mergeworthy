# Work automation methodology (v3)

Give this whole file to an agent, followed by the task. The agent sizes the work first (1.0), then applies only what that size requires.

Five parts:
- **Part 1: How to work.** Triage, principles, the live GitHub loop, posting, safety, reporting.
- **Part 2: Implementing a change.** From a problem to one merge-ready PR.
- **Part 3: Convergence.** How changes reach their final state.
- **Part 4: Failures that already happened,** each pointing to its rule.
- **Part 5: Mechanisms.** Scripts and hooks that enforce the rules. Where Part 5 has a mechanism, use it.

**Precedence:** the environment's instructions and the user's scope come first; Part 1 overrides Parts 2 and 3 where they conflict. When two rules seem to collide, check their scope (who owns the code, which tier, whether an umbrella issue exists) before choosing.

