---
name: delegating
description: "Starting, instructing, continuing or checking a subagent: which model, the six-part brief with the standard's path, one agent per job, continuing an agent or starting a new one, never waiting in the foreground, checking and passing on its result."
---

# Delegating

You are the main session: you make the decisions and write each agent's instructions, called its brief. The agent does the work you hand it. Do small edits, of a few lines, yourself. Hand bigger work or parallel work to an agent, and every independent check too.

## Steps

1. **Choose the model by what the agent does.**
   - **Opus at high effort** writes and judges: code, tests, docs, posts, reviews other than the independent one, which goes to Codex first (`mergeworthy:review`, step 1), designs, root causes, verification, and every decision.
   - **Haiku at high effort** does three kinds of work:
     - work a mechanical check decides: running tests or CI checks, a reproduction from a recipe, log mining;
     - applying code that Opus already wrote, line for line;
     - generating ideas in parallel: several agents, each from a different angle, propose options for you to decide between. Its brief says how to check a premise: read code only as it is at the pinned commit (`git show <sha>:<path>`, `git grep <symbol> <sha>`). When the brief or an earlier note names a commit, treat it as history: confirm in the pinned commit that the code it describes still exists.
   - **Every Haiku claim is a lead, not a fact.** Check it in the code yourself before you act on it or put it to the user. Redo on Opus any Haiku result that fails a check.
   - **Generate ideas on Opus instead** when a wrong decision is expensive and no later step tests the ideas, for example options that go from the agents straight to a maintainer. When an Opus agent measures each idea next, as in `mergeworthy:design` step 4, the ideas stay on Haiku.
   - **Never Sonnet.**
   - **A repo's project notes can require Opus for every agent** (the `## Agents` section of `~/.mergeworthy/projects/<owner>/<repo>.md`). Follow them there.

   Done: `task.md` names each agent's role and its model.
2. **Write the brief** in six parts:
   - **Goal:** one outcome you can observe.
   - **Facts:** only what you verified, each with its source. Point to code at a specific commit SHA, never at a branch, which can move.
   - **To check:** your guesses, written as questions. Never your expected answer, and never an earlier agent's conclusion.
   - **Scope:** the paths and commands the agent may use, plus the limits of the shared machine. Name the ports it must not touch. It runs servers only under `mw netns` (its own private network). It kills only the PIDs it started, in scripts it writes too. It starts no agents of its own.
   - **Standard:** the absolute path of the standard for each thing the agent writes or judges: the plugin's `skills/code/SKILL.md` for code, tests, code comments or a module design, and `skills/writing/SKILL.md` for anything a person reads. The Skill tool's message that loads a skill shows its base directory. Name the file by path, because the agent may not have this plugin's skills loaded. The agent reads the standard before it starts, and its final message says what its self-check against the standard found.
   - **Acceptance:** the commands or observations that show the work is done. Also ask for a final message of at most 15 lines: the result, with `path:line` or command evidence, and a `not_checked` list of what it couldn't check. Everything else goes in a file. The agent ends its turn only with that message, never while an install, test or server it started is still running.

   When a skill gives you a fixed text to hand an agent (a reviewer's instructions, a prompt), copy it from the installed skill each time, never from a copy you saved earlier. Keep model versions out of prompts, skills and briefs. Only the first line of a GitHub post names them (`mergeworthy:writing`, Forms).
   Done: the brief has all six parts, including the machine's limits and a standard's path for everything it asks the agent to write or judge.
3. **Run `mw load`** to see free memory, then start the agent in the background. Never wait for it in the foreground: you're notified when it finishes. Give each job to one agent only. An agent counts as alive until its task has finished, failed or been cancelled. So when its turn ended or its log went quiet, send it a message, and never start a second agent on the same job.
   Done: the agent runs in the background, `mw load` showed room for it, and nothing waits on it in the foreground.
4. **Continue the agent, or start a new one, for follow-up work** such as fixing what a check found, confirming fixes, or the next part of the same job. Every call an agent makes re-reads its whole context. That re-read is cheap while the agent was active in the last hour, and costs 25 to 40 times as much after that, as does a new agent reading the same files.
   - **Continue the agent** when the follow-up needs most of what it has already read. It keeps what it learned, and it doesn't read the files again. In Claude Code, use SendMessage. In T3 Code (an app that runs Claude Code and Codex sessions side by side), use its `t3_thread_send` tool in mode `queue`.
   - **Start a new agent** when the work must not see what the agent saw: a review, a fresh reader, or a check of the agent's own work. In T3 Code, each review round is a new task with its own title, and its prompt carries the earlier findings (`mergeworthy:review`, step 4).
   - **Start a new agent** also when the follow-up needs only a small part of what the agent read, for example 2 files of a whole module. This matters most when the agent has been idle for over an hour. Its brief points to the old agent's report file and the files it needs.

   Done: `task.md` says, for each follow-up, which agent got it and why.
5. **Check its first output early.** At 2 minutes, and every time you wake up, confirm it is making progress. If it has produced no output for five minutes, find out why. Give a long job a time budget in its brief.
   Done: its first output exists, or you found out why not.
6. **Check its result and pass it on.** Check it as `mergeworthy:task` step 6 says. The user never sees the agent's report, so tell them what matters in it, and act on it.
   Done: you checked the result against the lines it cites, told the user, and acted on it.

An agent never goes beyond its brief. It never takes a different approach than the plan: if the plan is wrong, it stops and says why. It never calls code unused until it has found every caller. It never says a step ran when it couldn't run it.
