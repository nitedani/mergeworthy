---
name: open-issue
description: "Opening an issue: already filed?, reproduced first, one finding a newcomer can find, How to reproduce, a screenshot or a video of the flow, decision issues, the gate."
---

# Opening an issue

One finding that a newcomer can find, reproduce and judge without asking you. When a defect becomes an issue is 1.1.7's call; a change to what a legitimate user sees or can do becomes a decision issue (1.1.9); an umbrella (`Tracking: <goal>`) follows 1.2, Tier L.

1. **Already filed or fixed?** `gh issue list --state all --search "<keyword>"` and `git log --oneline origin/<base> -- <the files>`. An existing issue gets your finding as a comment, not a twin; a fix already on `<base>` gets no issue.
2. **Reproduce it on today's `<base>`** per `evidence`, from a clean start. Trace both ends: where it starts in the code, and where a user meets it. What you can't reproduce isn't filed.
3. **Write the body** by `mergeworthy:writing` (its budget and issue form):

   ```markdown
   <What breaks and where, in a user's words, one or two sentences of fact.>

   ### How to reproduce

   1. <the role or login, the page's URL>
   2. <each action, as a person does it>
   3. <what you see, and what you expected>

   ![](/abs/path/flow.mp4)
   ```

   - **The evidence, per `evidence`:** a screenshot when one screen shows it, a video of the whole flow when reaching it takes more than one action, the request and the response when no screen does.
   - **A decision issue** adds `### Options`: what a user sees under each, then your recommendation and its reason. It keeps How to reproduce and the evidence, because the reader decides on a behavior they must see.
4. **Post it through the gate** (1.6, `post-lint --kind issue`), with a watcher covering the repo (1.5). Say it's filed only once the evidence shows in the posted body.
