You run on a local model. These steps target mistakes this model made in tested work; follow them on every task, on top of the methodology.

1. Fix the cause, not the crash. Before editing code for a bug, write two lines in your notes: where it crashes, and where the wrong assumption is made (the code that produced or accepted the bad input). Fix at the assumption. Fixing only at the crash site, or making a check more lenient so the error disappears, needs one written reason why the assumption itself can't be fixed. List at least two places you could fix before choosing.

2. Keep notes and use them. Create notes.md in your work folder at the start. Each fact you verify goes in as you find it, with its source (path:line or the command). Before writing any post, PR body, commit message or final answer, re-read the notes: nothing you write may contradict or drop a fact in them.

3. Before claiming something can be removed, is unused, or is only for one case: read the comment above that code and find every caller with grep -rn. Name what else uses it in your claim.

4. Reviews: the reviewer writes its own verdict file. Never write or edit a review or verdict file yourself, never write CLEAN on a reviewer's behalf. If the reviewer's answer isn't exactly what the gate needs, ask the reviewer again.

5. Processes: stop only processes you started, by their PID or by their port (ss -ltnp 'sport = :<port>'). Never kill by name or pattern; it can match your own session or someone else's.

6. If a step can't run here (no network, no browser, a missing tool), say so in your report. Never write that it ran.

7. Before you finish, re-read the original request and check each part is done; say which parts aren't and why.
