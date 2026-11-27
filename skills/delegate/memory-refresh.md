# Memory-refresh brief (noting what new session-log lines hold for memory.md)

`memory.md` holds what the built-in compaction summary loses: the user's rulings in force, what is ruled out and why, what was superseded, what is still intended, and the last 24 hours of what happened and why. *The read-through notes* (`memory-notes.txt`, named in the brief) are your whole output: `memory-prep` merges them into `memory.md`.
## 1. Read the input in chunks

The input is entries `[<log timestamp> ROLE] text`, oldest first: USER is the user (the project owner), ASSISTANT the main session. Its last line is `[<log timestamp> END]`.

Read it with the Read tool, 200 lines at a time (`offset`, `limit`; halve `limit` if Read says the chunk is too large). After each chunk, before reading the next, append (Bash `>>`) to the read-through notes:

```
read-through: <the timestamp of the last entry header in this chunk>
- <section>: <item>
```

Each item names its date and time and, when the user said it, quotes the user's words. A chunk with nothing worth keeping gets only its `read-through` line. Read every line; don't skim or sample.

## 2. Classify each item

- **Rulings in force:** how the user wants the work done, and decisions the user made. `- Rulings in force: **No cron** (2026-10-12 09:14Z). Recurring work runs in the watcher: "never use cron".`
- **Ruled out:** an approach, tool or path rejected or failed, and why. `- Ruled out: **Codex for implementation** (2026-10-11 18:02Z). Codex only reviews; its patches needed rewriting.`
- **Superseded:** `old → new`, and why it changed, naming the old plan so nobody resumes it. `- Superseded: **Day files → one memory.md** (2026-10-12 21:00Z). Day files duplicated the compaction summary.`
- **Still intended:** what is meant to happen and hasn't, and what it waits on. `- Still intended: **Release the RSC extension** (2026-10-12 15:30Z). Waits on the upstream fix being published.`
- **Recent:** what happened and why. `- Recent: 2026-10-12 16:40Z: the review found the stream closing early; the fix moved to the server.`

Leave out commit SHAs, branch heads and PR states except to say what was superseded (git and GitHub record those), the task in flight (the compaction summary keeps it), and step-by-step narration. Take facts only from the input; mark an ambiguous item as such.

## 3. Tag what a note replaces

- A Standing note is one line, `- <section>: **<lead>** (<date time>). <one sentence>.`, ending with the user's words quoted or a link when there is one; a Recent note is `- Recent: <date time>: <item>`.
- Before noting a Standing item, Grep the brief's memory files for its subject. When an item there is the ruling or plan the note replaces, reuse its lead (the merge then replaces that item) or end the note with `[replaces <its lead>]`: the old item goes under Superseded. When the note finishes intended work, end it with `[done <its lead>]`. Otherwise both items stay.
- Never Read or write `memory.md`, only Grep it: the merge keeps Standing newest first and Recent to 24 hours, and moves old items to `memory-archive-<month>.md`.
- If you stop before the `END` line, the notes are honestly behind at their last `read-through`, and the next run's input starts after it.
