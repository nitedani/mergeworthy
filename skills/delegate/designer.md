# Designer brief (design it twice; approach candidates)

Standards: `~/.mergeworthy/current/skills/code/SKILL.md` §Deep modules. Include `delegate/agent.md`.

One fresh-context agent per provider writes all its designs or candidates before comparing any (`design` step 4, `pull-request` step 5).

```
The problem, for its users: <the constraints any interface must meet, the dependencies and their categories (code §Deep modules), a rough code sketch that makes the constraints concrete; the sketch is not a proposal>.
The invariants: <design/<name>.invariants.md's path; approach candidates: the behavior to keep, with sources>. The project file: <project file path>. Read the code at <SHA> in <worktree>.

<Design it twice:> write three designs, each under a different constraint, none reusing another's entry points:
- minimize the interface (1–3 entry points);
- maximize flexibility; or, where dependencies cross a seam, ports and adapters in its place;
- make the most common caller trivial.
<Approach candidates:> <each principle or doc a maintainer cited, quoted, or none>. Two or three, before rating any: the direct fix, "not building it", and one dropping its load-bearing assumption.

Each candidate returns: the interface (types, invariants, ordering, error modes; unchanged: the current behavior), a usage example, what hides behind the seam, its dependency strategy and adapters, where its leverage is high or thin, and a row per invariant with measured evidence or a pending check (an option that breaks one is rejected, even "for now").
Then compare on depth, locality and seam placement, rank by interface size, and recommend one (or a hybrid): the smallest that keeps every invariant, a larger one only with the requirement the smaller fails, shown as code.

Write <work folder>/design/<name>.<provider>.<design or approach>.md.
Final message: the recommendation and its rating 0–10.
```
