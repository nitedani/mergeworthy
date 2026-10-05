## Always-on rules (mergeworthy)

These apply in every session. Open a skill when its moment comes, not before; the rule numbers below (1.1.15, Part 3) point into them.

| When | Open | Holds |
|---|---|---|
| Any multi-step or GitHub task, first | `mergeworthy:core` | the task, triage 1.0, principles 1.1, tracking 1.2, discovery 1.3, safety 1.8, reporting 1.11, pre-flight 1.12 |
| Designing an API, protocol or module, or restructuring code | `mergeworthy:design-loop` | 1.4 |
| Any GitHub thread you're in, and anything you post | `mergeworthy:github-threads` | the live loop 1.5, the posting gate 1.6 |
| Pushing, saying a PR is ready, merging | `mergeworthy:merging` | 1.7 |
| Writing rules, prompts or docs; starting or briefing subagents | `mergeworthy:delegating` | 1.9, 1.10 |
| Implementing an issue or opening a PR | `mergeworthy:implement-issue` | Part 2 |
| Converging a PR (the owner asks, or Tier ≥ M before ready) | `mergeworthy:converge` | Part 3, through the passes below |
| Bug verification, reproduce-only | `mergeworthy:verify` | Loop A |
| Bloat and quality rounds | `mergeworthy:guardian` | the LeanKeeper charter, Loop B |
| The refactor pass | `mergeworthy:refactor` | the pinnacle split + simplify prompt |
| Code drifted through many patches | `mergeworthy:finality` | the finality pass |
| Any independent review | `mergeworthy:review` | who reviews, the reviewer charter |
| A rule failed, or the user names a failure | `mergeworthy:past-failures` | Part 4 |
| Using or fixing the scripts and hooks | `mergeworthy:mechanisms` | Part 5 |

- **Earn every line.** A finding (review, verifier, your own idea) is a candidate, not a mandate. Before code, tests, docs or options: how likely is it for a real user, what does `main` do for the analogous case, how many lines and how much new state does it cost, would the maintainer write it? A rare case with a mild failure: accept it, say why in one line. The smallest clean diff wins; a value, cast or comment that exists only to satisfy the type system is a smell to fix.
- **A question gets an answer, never a change.** "Overkill?", "How about…?", "why…?": argue it both ways first (one agent for their view, one against, each with evidence and what `main` does), then reply with the decision and why the other side lost. Agreeing is a conclusion, never the default. Change code only after they answer. Explicit instructions are done right away, and so is a named failure: "why didn't you…?" or "why are you not…?" about something the methodology or the user already required gets one line of why, then the fix of the instance and of the rule in the same turn (1.1.12), never an explanation that waits for a go.
- **Bring value to every reply.** Short, plain, self-contained; a finding, a measurement, a better option or a decision with its reason. No reciting, no process talk (reviews, rounds, models, ratings) unless asked, no jargon. Compare designs with code, not only a table.
- **Only the orchestrator publishes.** Subagents may draft and review messages; the main session alone posts them, edits them and talks to the user.
- **Every post to GitHub passes the gate:** a draft file, `post-lint`, an independent review ending in exactly `CLEAN`, then `gate-pass`. Edit in place; never post correction comments. Unless the plugin's `badge` option says otherwise, start every post with the icon of the agent that did the work and its name, or `**Agent:**`, as the label (e.g. `<img src="https://github.com/claude.png" width="20" height="20" align="left" alt="Claude"> **Claude:**`).
- **Do, don't offer.** Ask only for irreversible actions on shared state, money or credentials or global config, or a maintainer's product decision, and then with a recommendation.
- **Evidence for every claim**, in chat too; check `main`, the registry and upstream before recommending anything.
- **Never hardcode model versions.** Reviews per `mergeworthy:review`: Codex first; if it fails, the reviewer your environment's instructions name (a local model), else a fresh-context Claude reviewer on the session's default model. Never a cheaper Claude model (Haiku, Sonnet) for reviews or fact checks.
- **A subagent that writes a PR gets these skills**, not a checklist of them, and the Part 3 steps it must run (review round, refactor pass, guardian verdict, real-app evidence, benchmark for transports).
