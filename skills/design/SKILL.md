---
name: design
description: "A design question, designing an API, protocol or module, restructuring code, or your own proposal: question the goal, prototype on extension points, debate, design it twice, prove it, propose, converge."
---

# Design

Takes a design to a shape the maintainer agreed to, before any PR converges. Entered from `task` step 9, `reply` step 5 or `pull-request` step 5.

## Steps

1. **Question the goal.** Does it belong in this layer: who owns the concern, what already does it? When it needs framework tricks, upstream fixes or a growing list of holes, stop and ask again: wrong layer. Design the end state first: judge a design on its correctness, its invariants and how simple its final shape is; effort, releases, migrations and PR count belong to the plan, never an argument for a weaker shape. "Later" is not a design decision: do now what the design depends on. Trace the actual flow in code (caller → callee, which object each side sees, in each environment; `delegate/agent.md` §Code search); check every path to the same thing behaves consistently, and name a gap with `file:line`.
2. **Prototype on existing extension points first** (an existing middleware, render hook or plugin hook), in a scratch folder outside any checkout; none exists: say so. That prototype is the first candidate; a core change needs a named requirement the prototype fails.
3. **Debate.** One fresh agent per provider (`delegate §Model class`) argues it divergently. You rate each recommendation (`pull-request §Rating`) and decide. Before keeping the shape, you collect the distinct simpler versions and one `test` agent builds them in a scratch folder outside any checkout and writes what breaks in `<work folder>/design/<name>.simpler.md`; recommend the simplest that breaks nothing.
   Open: `delegate/debater.md` (its file ends `SIMPLER:`) · Record: debaters' `<work folder>/design/<name>.<provider>.debate.md`; yours, `<work folder>/design/<name>.debate.md`, `<name>` being the decision's name
4. **Design it twice** (Tier M or L, or a new interface). First the invariants, in `<work folder>/design/<name>.invariants.md`: what any acceptable design must keep, named by the project file or the user, one row each, with its evidence or pending check. Then one agent per provider writes three designs; you rank all by interface size and recommend the smallest that keeps every invariant. The invariant list heads every later agent's and reviewer's brief.
   Open: `delegate/designer.md`; `code §Deep modules` · Record: designers' `<work folder>/design/<name>.<provider>.design.md`; your ranking, `<work folder>/design/<name>.ranking.md`
5. **Prototype to prove the invariants end to end,** in a copy outside any checkout (`git archive`): a real browser for UI, request counts, timing, bytes, in each supported mode (dev, prod, static), each result into the ranking. A failing design: prove the next; none left: `finality` steps 2–3, its pinnacle proved next.
6. **Adversarial review of the prototype:** how does it fail? When two rounds each find a new case breaking the same rule, stop patching cases: restate them as one rule, walk every setup through it yourself, then ask again.
   Open: `delegate §Reviewers`; `delegate/reviewer.md` · Record: `<work folder>/design/<name>.review.md`
7. **Keep the thread map:** `<work folder>/maps/<owner>-<repo>-<N>.md` (no thread: `<name>.md`), your own file: linked threads and PRs, every invariant agreed (with its permalink, or the user's dated words) or open, and where it is heading. A decision blocks only the part it decides: start everything else now. When `finality` step 1 applies: its steps 2–3 first, a changed pinnacle back to step 5. **The WIP update:** post the WIP comment before a thread's third proposal, then edit it from the map when a section changes.
   Open: §WIP comment; `finality` · Record: the map · Hook: pre-bash-guard (a third proposal on a thread waits for a map newer than the last one)
8. **Propose** only when no invariant is broken: the walkthrough (`writing §Design threads`), each question with your pick; no thread: the user's own repo, to the user in chat; another's, to its maintainer on the existing issue or one `open-issue` opens.
   Open: `writing §Design threads`; on a thread, `post` with `--kind proposal` · Record: a thread's gate file · Hook: post-bash-register counts proposals per thread
9. **Converge:** agreement before product code. In the user's own repos, continue on your recommendation after step 8 (a reply from the user re-opens it). Then write the decision: `Source:` (the OK's permalink, the user's dated words, or `own repo, unanswered`), the shape, its invariants. Then: called by `pull-request` step 5, return it there; else a PR task starts `pull-request` at step 1, a design-only one ends here. After a PR opens, each commit answers a request, a red CI, a found bug, or a mergeworthy rule.
   Record: `<work folder>/decisions/<name>.md`, written here only · Hook: pre-design-gate (Tier M/L: no code before it)

### WIP comment

One comment per thread, posted and edited through `post` (`--kind reply`): `# 🚧 WIP`, then *This comment is edited upon updates.*, then `## TLDR` (the goal and where it stands), `## Scope` (in and out), `## State` (where each part stands), `## TODO` (the open work and who it waits on), `## Agreed` (each agreed point with the permalink where it was agreed), `## Open` (the open items and invariants, each with who it waits on), and `## Next steps` (your recommended order). The reply: `writing §Design threads`.
