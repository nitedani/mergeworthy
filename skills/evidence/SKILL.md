---
name: evidence
description: "Showing a behavior to a reader who wasn't there: browser control, reproducing it as a person would, a screenshot, a video or the request and response, and uploading it."
---

# Evidence

What lets a newcomer see a behavior for themselves, in a PR, an issue or a reproduction comment.

## Steps

1. **Set up browser control** for UI or runtime work: a Chrome DevTools MCP started with `--isolated` (`npx -y chrome-devtools-mcp@latest --headless --isolated`), so parallel sessions don't share a profile.
   Done: it opened a page and took a screenshot.
2. **Reproduce it as a person:** real clicks, keys and touch in the running app, starting where a newcomer starts (a fresh login as the role that meets it, the default view). Scripted events, emulated hover and computed-style diffs don't count. Check the age of the data against the date of the fix. A server the browser must reach runs under `mw netns --publish <port> -- <cmd>`.
   Done: the steps, from a clean start, reach the behavior.
3. **Capture what shows it:** a screenshot of the screen where a user meets it; a video of the whole flow from a clean start when reaching it takes more than one action, because stills hide layout shift, stale flashes and late-enabling controls; the request and response, or the command and its output, when nothing on screen shows it. Disclose anything you did to the page to get the shot. Redact secrets. A fix to a form is shown by the thing it configures behaving differently on screen. A measurement goes through the exact path the user runs (the same client, API and settings), and a CI workflow change counts only once a real run on the branch shows it.
   Done: the capture is in the work folder, with a one-line caption of what to look at and what it proves.
4. **Upload it:** `gh pr edit <N> --body-file body.md --attach '/abs/path/01-name.png#alt'` through `mw post`; `gh issue create` and comments take `--attach` too. Reference each file by the exact path you pass. A video goes in as `![](<path>.mp4)` alone in its paragraph. If `gh` lacks `--attach`, upload by hand and link.
   Done: `gh pr view <N> --json body` (or `gh issue view`) shows no local path left.
