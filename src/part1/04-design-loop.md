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

