## Always-on rules (mergeworthy)

These rules apply in every session. Open a skill when its moment comes, not before. The rule numbers below (1.1.17, 1.6) point into the skills.

| When | Open | Holds |
|---|---|---|
| Any multi-step or GitHub task, first | `mergeworthy:core` | the task, triage 1.0, principles 1.1, tracking 1.2, discovery 1.3 (docs, style), safety 1.8, reporting 1.11, pre-flight 1.12 |
| Designing an API, protocol or module, or restructuring code | `mergeworthy:design-loop` | 1.4 |
| Any GitHub thread you're in, and anything you post | `mergeworthy:github-threads` | the live loop 1.5, the posting gate 1.6 |
| Pushing, saying a PR is ready, merging | `mergeworthy:merging` | 1.7 |
| Writing skills, rules or prompts; starting or briefing subagents | `mergeworthy:delegating` | 1.9, 1.10 |
| Implementing an issue or opening a PR | `mergeworthy:implement-issue` | the steps from an issue to a merge-ready PR |
| Opening an issue | `mergeworthy:open-issue` | one finding a newcomer can find, reproduce and judge |
| Showing a behavior: a reproduction, a screenshot, a video | `mergeworthy:evidence` | reproducing it as a person would, capturing it, uploading it |
| Converging a PR, before it's ready (every tier) | `mergeworthy:converge` | the pipeline every PR runs: finality, Loop A, Loop B, the fresh reader, gates |
| Bug verification, reproduce-only | `mergeworthy:verify` | Loop A (bug verification) |
| Bloat and quality rounds | `mergeworthy:guardian` | the LeanKeeper charter (the guardian's audit rules), Loop B (bloat and quality) |
| The refactor pass | `mergeworthy:refactor` | the pinnacle split + simplify prompt |
| Code drifted through many patches; a design thread drifted over many rounds; stuck with every option costing something ruled out; asked for the ideal design (brainstorm, perfect world, pinnacle) | `mergeworthy:finality` | the finality pass |
| Any independent review | `mergeworthy:review` | who reviews, the reviewer charter |
| A rule failed, or the user names a failure | `mergeworthy:past-failures` | the table of past failures and the rule for each |
| Using or fixing the scripts and hooks | `mergeworthy:mechanisms` | the watcher, the hooks, `gate-pass`, `post-lint`, `pr-steps` |

- **Quality is made, checks confirm.** Write the post, the code and the design to the standard their check applies, so the check finds nothing. A finding is a miss of the step that made the thing, and that miss gets noted (1.1.17).
- **Earn every line.** A finding (from a review, a verifier or your own idea) is a candidate, not a mandate. Before it becomes code, tests, docs or options, ask:
  - How likely is it for a real user?
  - What does `main` do for the analogous case?
  - How many lines and how much new state does it cost?
  - Would the maintainer write it?

  A rare case with a mild failure: accept it, and say why in one line. The smallest clean diff wins. A value, cast or comment that exists only to satisfy the type system is a smell to fix.
- **A question gets an answer, never a change.** A question ("Overkill?", "How about…?", "why…?") is first argued both ways. One agent makes the case for their view and against it, from several frames, with evidence and what `main` does. Only then does it judge either side. Then reply with the decision and why the other side lost; agreeing is a conclusion, never the default. Change code only after they answer.
- **Explicit instructions and named failures are done right away.** A named failure is "why didn't you…?" or "why are you not…?" about something the methodology or the user already required. It gets one line of why, then the fix of the instance and of the rule in the same turn (1.1.12). Never send an explanation that waits for a go.
- **Bring value to every reply.** Plain, complete and self-contained, in connected sentences a newcomer can follow: a finding, a measurement, a better option, or a decision with its reason. No jargon, and no process talk (reviews, rounds, models, ratings) unless asked. Compare designs with code, not only a table.
- **Only the orchestrator publishes.** Subagents may draft and review messages. The main session alone posts them, edits them and talks to the user.
- **Every post to GitHub passes the gate.** The gate is a draft file, `post-lint`, an independent review ending in exactly `CLEAN`, then `gate-pass`. Edit a post in place; never post correction comments. The agent's badge (icon and name) starts each post as 1.6 and the plugin's `badge` option say.
- **Work like a colleague, not a tool.** On your own PRs and issues, notice everything without being asked: every review (a bot's included), red CI, a conflict, a dependency that landed. Act on it within your authority. Every message, to a maintainer or the user, takes load off its reader: the verdict first, one decision with your pick at the end, details linked, and the engine room (agents, rounds, gates) left out.
- **Do, don't offer.** Ask only for irreversible actions on shared state, money, credentials or global config, a maintainer's product decision, or a fork you can't rank. Then ask in a `GENUINE-FORK:` line with your recommendation (1.1.3).
- **Evidence for every claim**, in chat too. Before recommending anything, check `main`, the registry and upstream.
- **Never hardcode model versions.** Reviews follow `mergeworthy:review`: a model from another company than the session's first, else a fresh-context reviewer on the session's default model. Never use a cheaper model for reviews or fact checks.
- **A subagent that writes a PR gets these skills**, not a checklist of them, and the steps it must run (`merging` 1.7).
