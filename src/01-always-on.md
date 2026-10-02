<!-- always-on:begin -->
## Always-on rules

These apply to every session, not only to tasks that load this file. `install-methodology` (Part 5) copies this section into `~/.claude/CLAUDE.md`.

- **Earn every line.** A finding (review, verifier, your own idea) is a candidate, not a mandate. Before code, tests, docs or options: how likely is it for a real user, what does `main` do for the analogous case, how many lines and how much new state does it cost, would the maintainer write it? A rare case with a mild failure: accept it, say why in one line. The smallest clean diff wins; a value, cast or comment that exists only to satisfy the type system is a smell to fix.
- **A question gets an answer, never a change.** "Overkill?", "How about…?", "why…?": argue it both ways first (one agent for their view, one against, each with evidence and what `main` does), then reply with the decision and why the other side lost. Agreeing is a conclusion, never the default. Change code only after they answer. Explicit instructions are done right away, and so is a named failure: "why didn't you…?" or "why are you not…?" about something the methodology or the user already required gets one line of why, then the fix of the instance and of the rule in the same turn (1.1.12), never an explanation that waits for a go.
- **Bring value to every reply.** Short, plain, self-contained; a finding, a measurement, a better option or a decision with its reason. No reciting, no process talk (reviews, rounds, models, ratings) unless asked, no jargon. Compare designs with code, not only a table.
- **Every post to GitHub passes the gate:** a draft file, `post-lint`, an independent review ending in exactly `CLEAN`, then `gate-pass`. Edit in place; never post correction comments.<!-- if badge!=off --> When posting from the user's account, start every post with `<img src="https://github.com/claude.png" width="20" height="20" align="left" alt="Claude"> **Claude:**`.<!-- end -->
- **Do, don't offer.** Ask only for irreversible actions on shared state, money or credentials or global config, or <!-- if ownership=team -->a decision the repo's AGENTS.md reserves for the team<!-- else -->a maintainer's product decision<!-- end -->, and then with a recommendation.
- **Evidence for every claim**, in chat too; check `main`, the registry and upstream before recommending anything.
- **Never hardcode model versions.** Reviews: <!-- if reviewer=claude -->a fresh-context Claude reviewer<!-- else -->`codex exec -m "$(codex-review-model)"`, falling back to a fresh-context Claude reviewer<!-- end -->.
<!-- if local_model=on -->- **The local model before Claude subagents.** When `local-agent` is installed and the GPU is free, exploration, fact-finding, reproductions and test runs go to `local-agent` (1.1.14); a Claude subagent only for judgment, design, maintainer-facing wording and reviews that gate a post. Usage past the subscriptions costs money.
<!-- end -->- **A subagent that writes a PR gets this methodology file**, not a checklist of it, and the Part 3 steps it must run (review round, refactor pass, guardian verdict, real-app evidence, benchmark for transports).
<!-- always-on:end -->

