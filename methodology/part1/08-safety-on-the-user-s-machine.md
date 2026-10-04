## 1.8 Safety on the user's machine

- Kill only your own processes, by PID or port; never `pkill -f`.
- Whatever you start, you stop: dev servers, builds, preview servers, proxies. A subagent records the PIDs it starts and kills them before handing back; check with `ps` that none are left. Find a server by the PID you started (and its children, `pgrep -P <pid>`) or by its port (`ss -ltnp 'sport = :<port>'`); never grep `ps` output for a port number, and never `pgrep -f <pattern>`. Check each PID's command and directory before killing it.
- At most 4 browsers and 4 dev servers of your own at once; stop each when its work ends.
- Never restart or reconfigure a container someone else's work depends on; start your own alongside.
- Anything that listens on a port (e2e tests, dev and preview servers) runs through `isolated-run <command>`, yours and every subagent's: its own network namespace, so fixed ports never collide and parallel runs never test each other's servers. Install dependencies outside it (no network inside). Never kill or wait out another run's server.
- Never modify the package store or a shared `node_modules`; scratch installs use `--package-import-method=copy`. After any install, check `git status` for unexpected changes.
- Browser work uses the DevTools MCP. On "profile in use", retry after 30 s, then ask. Never fall back to scripted browsers silently, never open windows on the user's desktop, never kill another session's browser.
- Isolate worktrees: their own ports, databases and generated clients. <!-- if target=ci -->Work in the checkout the workflow made, on its branch; to read another branch, `git worktree add --detach <artifact root>/<name> <ref>`.<!-- else -->Never touch the user's own checkouts (the clones the user works in), including their git config, which their worktrees share: no edits, commits, checkouts, resets or branch switches; work in worktrees you create, and to read another branch, `git worktree add --detach <artifact root>/<name> <ref>`.<!-- end -->

