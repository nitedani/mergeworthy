---
name: post
description: "Everything that reaches GitHub or another external service (a comment, reply, inline comment, PR or issue body, an edit of any): draft, lint, review until gate-pass passes, re-check, post."
---

# Post

Everything that reaches an external service passes these steps: comments, review replies, inline comments, PR and issue bodies, filed issues, and edits of any of these. Reactions are exempt. A reviewed draft isn't permission to publish: the task says what you may open, comment and file. Called by a step of another skill; when done, return to it.

## Steps

1. **Draft** in `<work folder>/drafts/<thread>/<name>.md` (never straight into a `gh` command), with the comment it answers in `<name>.parent.md`. On a thread: build the thread record in the same folder and brief a drafter; you read only its draft and its list of conflicts with past decisions. A PR or issue body: from its template (`pull-request §Body`, `open-issue` step 3). Whoever drafts runs `writing §Self-check` before the review.
   Run: `thread-context <owner/repo#N> --out <work folder>/drafts/<thread>/thread-context.md` · Open: `delegate/drafter.md`; `writing` · Record: thread-context.md · Hook: gate-pass and pre-bash-guard (no record, or one without the thread's latest human comment)
2. **Lint until it passes.** gate-pass re-runs its flags. Editing another's issue/PR: `--edit-of <owner/repo#N>`.
   Run: `post-lint <draft> --kind <kind> [--repo <owner/repo>] [--draft]` (§Kinds)
3. **Review.** An independent reviewer with the post-review brief. Rule on each finding in the ledger, rewriting each passage you keep in your own words, never patching the reviewer's; lint again (step 2). Another round (`delegate §Review rounds`) runs only while gate-pass fails on the draft, as round 2 after a verdict not clean: pre-agent-dedupe refuses an agent's round otherwise, and a shell reviewer's is yours to hold back. It ends at a final message exactly `CLEAN`, or a ledger closing it (gate-pass `--ledger <path>`, default `<name>.ledger.md` beside the draft) on the draft its last round read. **The fast form,** for a later round, "Done in <sha>", a holding reply with findings, a draft PR's first body (`pull-request` step 7) or a typo or sha edit: the same, the reviewer asked only about those claims, the last round's open findings and, after a refactor ask, the result table. **A status post** (a reply saying only what you are doing and by an absolute time in UTC; post-lint rejects anything to check) skips the review: lint it with `--kind status`, add its `PROMISED` line (step 4), badge only its drafter, give gate-pass `none` as the review output.
   Open: `delegate §Reviewers`; `delegate/post-review.md` · Record: `<name>.review.out` (the last verdict; the ledger keeps earlier findings); the launch writes the draft's sha256 to `<name>.review.out.launch` · Hook: gate-pass
4. **Right before posting:** re-read every claim against the current head and a PR's state. Every commit the draft names exists in the repository its claim or link names; your own PR's commits, in its head repository. A draft PR's first body, before the PR exists: the repository you push to. A promise ("I'll…", "follow-up PR") first gets its `PROMISED` line in `proposals-open.md` (`task §Files`).
   Run: `git fetch`; `gh api repos/<owner>/<repo>/commits/<sha>` succeeds for each (a PR's head: `gh pr view <N> --json headRepositoryOwner,headRepository`); `gate-pass <abs draft> <abs review output>` · Record: `<name>.md.gate` · Hook: gate-pass, pre-bash-guard
5. **Post in the thread where the person wrote,** from the file, then clear its owed line as `done: <post URL> <what changed>`.
   Run: `--body-file <abs draft>` (API: `-F body=@<abs draft>`) · Open: §Thread rules · Record: the gate file, the owed line · Hook: pre-bash-guard (twice, a third comment, changed after the gate), stop-lint

### Kinds

`post-lint --kind`: `reply` (a thread comment; `--parent none` when it answers nobody), `status` (a reply, step 3), `proposal` (a reply proposing a design or asking agreement to one; counted per thread), `pr` (a PR body; `--draft` for a draft's), `issue`, `plan` (a design plan the user asked to post as an issue; at most 2500 words), `inline` (a diff-line review comment), `tracker` (the umbrella issue and Decisions comment; no badge).

### Thread rules

- **At most two comments in a row.** The second is only the answer after its holding reply or status post, a wait ping, a dependency's progress, a 👎 fix, or the review of commits a maintainer pushed after your last comment. Anything else edits your last comment; a would-be third is an edit with an @-mention.
- **One reply per person, edits for corrections.** Several comments from one person get one reply.
- **Evidence carries no secret.** In logs, requests, payloads and screenshots, write `<REDACTED>` for every token, cookie, auth header and key, and quote only the lines that show the point.
- **A maintainer who asks to see how you change this methodology:** write the installed mergeworthy commit (`git -C ~/.mergeworthy/current rev-parse HEAD`) to `~/.mergeworthy/harness-shown/<owner>`; gate-pass then appends to each `reply` or `proposal` a link comparing the commit it names with the installed one.
