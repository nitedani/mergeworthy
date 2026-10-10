---
name: delegating
description: "Starting, briefing, continuing or integrating a subagent: which model, the five-part brief, one agent per job, never waiting in the foreground, checking and relaying its result."
---

# Delegating

You decide and brief; an agent does the work you hand it. Do small edits yourself; brief an agent for big or parallel work, and for every independent check.

## Steps

1. **Choose the model by role.** Opus at high effort for everything that writes or judges: code, tests, docs, posts, reviews, designs, root causes, verification. Haiku at high effort only for mechanical work whose output doesn't ship: running gates or tests, a reproduction from a recipe, log mining. A Haiku result that fails your spot-check is redone on Opus. Never Sonnet.
   Done: `task.md` names the agent's role and its model.
2. **Write the brief** in five parts:
   - **Goal:** one observable outcome.
   - **Facts:** only what you verified, each with its source.
   - **To check:** your guesses, as questions. Never your expected answer or an earlier agent's conclusion.
   - **Scope:** the paths and commands it may use, plus the machine's limits: ports it must not touch, servers only under `mw netns`, killing only the PIDs it started, in scripts it writes too, and no agents of its own.
   - **Acceptance:** the commands or observations that define done, plus a final message of at most 15 lines (the result with `path:line` or command evidence, and a `not_checked` list), with the rest in a file.

   A charter or prompt from a skill is pasted from the installed skill, never from a saved copy.
   Done: the brief has all five parts, the machine's limits included.
3. **Check `mw load`,** then launch in the background. Never wait in the foreground: the agent's completion wakes you. One agent per job: a follow-up on the same work continues that agent (SendMessage in Claude Code, `t3_thread_send` with mode `queue` in T3 Code). In T3 Code, a review round is a new launch with its own title that carries the prior findings (`review`, step 4).
   Done: the agent runs in the background, `mw load` showed room for it, and nothing waits on it in the foreground.
4. **Check its first output early.** At 2 minutes, and at every wakeup, confirm it is making progress; five minutes with no output means investigate. A long job gets a time budget in its brief.
   Done: its first output exists, or you found out why not.
5. **Integrate and relay its result** (`task`, step 6). The user never sees the agent's report, so relay what matters and act on it.
   Done: the result is checked against its citations, relayed to the user, and acted on.

An agent never widens its brief, never picks another approach than the plan (it stops and says why the plan is wrong), never calls code unused before finding every caller, and never says a step ran when it couldn't.
