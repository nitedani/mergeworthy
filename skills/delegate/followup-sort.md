# Follow-up sort brief (a MAINTAINER REVIEW from the watcher)

Standards: `~/.mergeworthy/current/skills/code/SKILL.md`. Include `delegate/agent.md`.

A maintainer's review names what our checks let through. The session that received it fills this once per review (`rules` step 6).

```
Our open PR: <PR URL> at <head SHA>, in <worktree>. The review: <review URL>; its defects: <each one's quoted words>. A rename: <PR URL>#rename-<time> is the review URL, both titles the defect. Read them against git diff <base>...<head SHA>.
The project file: <project file path>.

Sort each defect once:
- MISS: a miss our checks should have caught (a bug, a sibling case, a gap a gate could find). Find the agent whose turn should have caught it in its own transcript (a Claude Code `.jsonl` under `~/.claude/projects/`, a T3 thread, a Codex log; grep for its brief or output path), quote that turn with its line, and say why it didn't: no rule told it, it skipped one, its probe was wrong, or it judged the case out of scope. Name the mergeworthy step that failed.
- TASTE: the project's taste (naming, structure, comment density, what the maintainer cuts or adds). Write the one project-file line it teaches, for Conventions, Maintainer preferences or Recurring misses, with the link.
- WORKED: a maintainer praised or adopted something of ours. The one line for `## What worked`, with the link.
- DIRECTION: the maintainer chose differently, no fault in ours. The reason in a line.
Confirm the review's words say the change your line describes.

Write <work folder>/followup-<id>.md (<id>: from #pullrequestreview-<id>, or rename-<time>).
Final message: one line per defect, `<review URL> MISS|TASTE|WORKED|DIRECTION <the line or reason>`.
```
