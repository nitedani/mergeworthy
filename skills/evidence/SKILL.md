---
name: evidence
description: "Showing a behavior to a reader who wasn't there: controlling a browser, reproducing it as a person would, a screenshot, a video or the request and response, and uploading it."
---

# Evidence

How to let a newcomer see a behavior for themselves, in a PR, an issue or a comment that reproduces a bug.

## Steps

1. **Set up browser control** for UI work or anything you check at runtime. Register the Chrome DevTools MCP server with Claude Code, with `--isolated`: `claude mcp add chrome-devtools -- npx -y chrome-devtools-mcp@latest --headless --isolated`. With `--isolated`, each session gets its own browser profile, so sessions running in parallel don't share cookies or storage.
   Done: it opened a page and took a screenshot.
2. **Reproduce it as a person would:** real clicks, keys and touches in the running app. Start where a newcomer starts: a fresh login as the kind of user who meets the behavior, on the default view. Scripted events, emulated hover and comparing computed styles don't count. Compare the age of the data with the date of the fix: rows written before a fix can still make the bug look alive. When the browser must reach a server, run the server under `mw netns --publish <port> -- <cmd>`, which gives it a private network and prints the URL to open.
   Done: the steps, from a clean start, reach the behavior.
3. **Capture what shows it:**
   - a screenshot of the screen where a user meets it;
   - a video of the whole flow from a clean start, when reaching it takes more than one action, because still images hide layout shifts, stale content that flashes, and controls that become usable late;
   - the request and response, or the command and its output, when nothing on screen shows it.

   Say anything you changed on the page to get the shot. Hide secrets. Show a fix to a settings form by showing the thing it configures behaving differently on screen. Take a measurement through the exact path the user runs: the same client, API and settings. A change to a CI workflow counts only once a real run on the branch shows it.
   Done: the capture is in the work folder, with a one-line caption saying what to look at and what it proves.
4. **Upload it** with the post, through `mw post` (`mergeworthy:posting`), which checks the post before it runs the `gh` command: `gh pr edit <N> --body-file body.md --attach '/abs/path/01-name.png#alt'`. `gh issue create` and comments take `--attach` too. Refer to each file in the body by the exact path you pass. A video goes in as `![](<path>.mp4)`, alone in its paragraph. If your `gh` has no `--attach`, update `gh`. If you can't, ask the user to upload the file in GitHub's editor, and link it.
   Done: `gh pr view <N> --json body` (or `gh issue view`) shows no local path left.

## The screenshot reviewer

Before anyone sees new UI, a fresh Opus agent gets the whole-page screenshots, the references you studied in `mergeworthy:task` step 3, and one question: "List what draws the eye first, what's noise, and what looks unfinished." You, the main session, decide on each point it lists.
