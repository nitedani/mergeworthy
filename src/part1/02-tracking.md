## 1.2 Tracking

- **Every tier:** drafts and their reviews under `drafts/`; evidence under the artifact root; exit codes recorded (`EXIT=$?`) and quoted, never a log tail. Log and artifact names include a unique pass ID; never overwrite another pass's file. The owed lists of 1.5 (`replies-owed.md`, `questions-owed.md`, `proposals-open.md`) live in the <!-- if target=ci -->tracking comment (1.12)<!-- else -->artifact root<!-- end -->.
- **Tier S:** the PR body is the reader's record, true of the final head, plus `scope.md` and a short `ledger.md` for process records (review, refactor, ready-check).
- **Tier M:** `ledger.md`, one row per event (time | unit | event | head SHA | result: each pass, round, fix with its commits, gate or lane run with its exit status, push, CI result), headed by `critical-path` and the passes still owed. Answer every status and convergence question from it, skipped steps included. `decision-packet.md`: only people's picks (decision | who | date | link | what it was picked over). `scope.md`, `acceptance.md`, and `corrections.md` (quote | instance fix | generator fix).
- **Tier L:** an umbrella issue listing every PR and issue with its state, plus one live **Decisions comment** on it (Requirements, Agreed, Proposed and waiting, Open, PRs), edited in place through the gate. Every line has a source link.
  - Update the body **and** the Decisions comment in the same step as every event.
  - A forward-looking line ("working on X", "waiting on Y") names the event that removes it; when that event fires, remove the line.
  - Program-wide status lives only on the umbrella; a PR body keeps only its own notes table. When a decision replaces a design, update every surface that still describes the old one (code, tests, types, docs, open PR bodies) in the same step.
  - `tracker-check` (Part 5) flags drift; no report to the user while it's red.

