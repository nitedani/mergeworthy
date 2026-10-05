# Evidence in the real app

- Use a browser you control (a DevTools MCP started with `--isolated`, so parallel sessions don't share a profile). If you have none, stop and say what is missing.
- Capture "before" by reverting only your own files, letting the app reload, then restoring them; leave `git status` clean.
- Use the app as a user would for five minutes around your change, not only along the path you fixed.
- Check each touched page at widths 360, 768, 1280 and 1920, in light and dark, in hover, focus and open states, and on a cold first load; any console error fails.
- Drive it with a real mouse, keyboard and touch, look at a screenshot after each action, and record anything that moves.
- Show a runtime fix (a stream, a cancel, a cache) through a real browser, the base branch against your head, with the server's logs.
- Show a change that isn't visual through what is: the payload the service received, the request that was refused.
