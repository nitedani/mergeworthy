---
name: delegating
description: "Starting, instructing, continuing or checking a subagent: which model, the five-part brief, one agent per job, never waiting in the foreground, checking and passing on its result."
---

# Delegating

You are the main session: you make the decisions and write each agent's instructions, called its brief. The agent does the work you hand it. Do small edits yourself. Hand big work or parallel work to an agent, and every independent check too.

## Steps

1. **Choose the model by role.** Opus at high effort for everything that writes or judges: code, tests, docs, posts, reviews, designs, root causes, verification. Haiku at high effort only for mechanical work whose output doesn't ship: running gates or tests, a reproduction from a recipe, log mining. A Haiku result that fails your spot-check is redone on Opus. Never Sonnet.
   Done: `task.md` names the agent's role and its model.
2. **Write the brief** in five parts:
   - **Goal:** one outcome you can observe.
   - **Facts:** only what you verified, each with its source. Point to code at a specific commit SHA, never at a branch, which can move.
   - **To check:** your guesses, written as questions. Never your expected answer, and never an earlier agent's conclusion.
   - **Scope:** the paths and commands the agent may use, plus the limits of the shared machine. Name the ports it must not touch. It runs servers only under `mw netns` (its own private network). It kills only the PIDs it started, in scripts it writes too. It starts no agents of its own.
   - **Acceptance:** the commands or observations that show the work is done. Also ask for a final message of at most 15 lines: the result, with `path:line` or command evidence, and a `not_checked` list of what it couldn't check. Everything else goes in a file. The agent ends its turn only with that message, never while an install, test or server it started is still running.

   When a skill gives you a fixed text to hand an agent (a reviewer's instructions, a prompt), copy it from the installed skill each time, never from a copy you saved earlier. Keep model versions out of prompts, skills and briefs. Only the first line of a GitHub post names them (`mergeworthy:writing`, Forms).
   Done: the brief has all five parts, including the machine's limits.
3. **Run `mw load`** to see free memory, then start the agent in the background. Never wait for it in the foreground: you're notified when it finishes. Give each job to one agent only. An agent counts as alive until its task has finished, failed or been cancelled. So when its turn ended or its log went quiet, send it a message, and never start a second agent on the same job. Follow-up work on the same thing goes to the same agent: in Claude Code with SendMessage, in T3 Code with `t3_thread_send` in mode `queue`. In T3 Code, each review round is the exception: it is a new task with its own title, and its prompt carries the earlier findings (`mergeworthy:review`, step 4).
   Done: the agent runs in the background, `mw load` showed room for it, and nothing waits on it in the foreground.
4. **Check its first output early.** At 2 minutes, and every time you wake up, confirm it is making progress. If it has produced no output for five minutes, find out why. Give a long job a time budget in its brief.
   Done: its first output exists, or you found out why not.
5. **Check its result and pass it on.** Check it as `mergeworthy:task` step 6 says. The user never sees the agent's report, so tell them what matters in it, and act on it.
   Done: you checked the result against the lines it cites, told the user, and acted on it.

An agent never goes beyond its brief. It never takes a different approach than the plan: if the plan is wrong, it stops and says why. It never calls code unused until it has found every caller. It never says a step ran when it couldn't run it.
