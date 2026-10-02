## 1.10 Integrating agents' work

- Before landing a subagent's diff, write down each structural decision in it and why it's right. Hardcoded lists and duplicated classifications get fixed before pushing.
- Every background job has a liveness check (output size or log mtime), checked at 2 minutes and at every wakeup. Five minutes without output means investigate now. Never report "dispatched" or "armed" as progress.
- When an agent reports, relay the result to the user and act on it; its report isn't shown to them.

