# How the skills connect

Generated from the skills by `docs/build-graphs.py`; edit the skills, then run it. One graph per entry point in `always-on.md`: each section of the skill is a box, its numbered steps run top to bottom, and a dashed arrow marks where a step hands over to another skill.

## Which skill hands over to which

| Skill | Hands over to |
|---|---|
| `converge` | `finality`, `pull-request`, `verify`, `review`, `guardian`, `refactor`, `merging`, `github-threads`, `writing` |
| `core` | `open-issue`, `evidence`, `delegating`, `merging`, `github-threads`, `design-loop`, `converge`, `pull-request` |
| `delegating` | nothing |
| `design-loop` | `pull-request`, `core`, `review`, `writing`, `converge` |
| `evidence` | nothing |
| `finality` | nothing |
| `github-threads` | `converge`, `review`, `refactor`, `core`, `pull-request`, `writing`, `finality` |
| `guardian` | `delegating`, `converge`, `design-loop` |
| `mechanisms` | nothing |
| `merging` | nothing |
| `open-issue` | `evidence`, `writing`, `github-threads` |
| `past-failures` | nothing |
| `pull-request` | `evidence`, `finality`, `core`, `guardian`, `design-loop`, `converge`, `open-issue`, `writing` |
| `refactor` | nothing |
| `review` | `delegating`, `guardian`, `refactor`, `github-threads`, `core`, `converge` |
| `verify` | `core`, `converge` |
| `writing` | nothing |

## Any multi-step or GitHub task, first

Opens `mergeworthy:core` (the task, triage 1.0, principles 1.1, tracking 1.2, discovery 1.3 (docs, style), safety 1.8, pre-flight 1.12).

```mermaid
flowchart TB
  start(["Any multi-step or GitHub<br/>task, first"])
  subgraph g0["1.1 Principles"]
    s0["17 rules: Critical path first, Invariants first, Do…"]
  end
  s0 -.-> r1[["open-issue"]]
  s0 -.-> r2[["evidence"]]
  s0 -.-> r3[["design-loop"]]
  s0 -.-> r4[["converge"]]
  s0 -.-> r5[["pull-request"]]
  s0 -.-> r6[["delegating"]]
  s0 -.-> r7[["merging"]]
  s0 -.-> r8[["github-threads"]]
  subgraph g1["1.12 Pre-flight"]
    s1["1. Write scope.md"]
    s2["2. Write the critical path"]
    s1 --> s2
    s3["3. Before you open an issue<br/>or PR"]
    s2 --> s3
    s4["4. Confirm browser control"]
    s3 --> s4
    s5["5. Note the precedents and<br/>style"]
    s4 --> s5
  end
  s3 -.-> r9[["github-threads"]]
  start --> g0
  g0 ~~~ g1
```

## Writing anything a person reads: a comment, reply or edit, a PR or issue body, a design answer, a report to the user

Opens `mergeworthy:writing` (every writing rule 1.11: voice, model replies, budgets, the badge).

```mermaid
flowchart TB
  start(["Writing anything a<br/>person reads: a comment,<br/>reply or edit, a PR or<br/>issue …"])
  subgraph g0["Draft by talking"]
    s0["1. Before writing"]
    s1["2. Read it out loud as them"]
    s0 --> s1
    s2["3. A passage that can't be<br/>fixed sentence by …"]
    s1 --> s2
    s3["4. A design reply to a<br/>maintainer"]
    s2 --> s3
  end
  start --> g0
```

## Designing an API, protocol or module, or restructuring code

Opens `mergeworthy:design-loop` (1.4).

```mermaid
flowchart TB
  start(["Designing an API,<br/>protocol or module, or<br/>restructuring code"])
  subgraph g0["1.4 Design loop"]
    s0["0. Prototype on existing<br/>extension points first"]
    s1["1. Draft<br/>decisions/‹name›.md"]
    s0 --> s1
    s2["2. Prototype"]
    s1 --> s2
    s3["3. Adversarial review"]
    s2 --> s3
    s4["4. Propose to maintainers"]
    s3 --> s4
    s5["5. Post the walkthrough"]
    s4 --> s5
  end
  s1 -.-> r1[["pull-request"]]
  s1 -.-> r2[["core"]]
  s3 -.-> r3[["review"]]
  s4 -.-> r4[["writing"]]
  s5 -.-> r5[["converge"]]
  subgraph g1["1.4.1 Codebase design"]
    s6["1. Frame the problem for<br/>the user"]
    s7["2. Have one fresh-context<br/>agent design it three<br/>times"]
    s6 --> s7
    s8["3. Each design returns"]
    s7 --> s8
    s9["4. Compare and recommend"]
    s8 --> s9
  end
  s7 -.-> r6[["core"]]
  start --> g0
  g0 ~~~ g1
```

## Any GitHub thread you're in, and anything you post

Opens `mergeworthy:github-threads` (the live loop 1.5, the posting gate 1.6).

```mermaid
flowchart TB
  start(["Any GitHub thread you're<br/>in, and anything you<br/>post"])
  subgraph g0["1.5 The live GitHub loop"]
    s0["1. Within 10 seconds"]
    s1["2. The answer"]
    s0 --> s1
    s2["3. Then think"]
    s1 --> s2
    s3["4. Then reply"]
    s2 --> s3
    s4["5. Book-keeping"]
    s3 --> s4
  end
  s1 -.-> r1[["converge"]]
  s1 -.-> r2[["review"]]
  s1 -.-> r3[["refactor"]]
  s1 -.-> r4[["core"]]
  s2 -.-> r5[["pull-request"]]
  s2 -.-> r6[["writing"]]
  s2 -.-> r7[["finality"]]
  subgraph g1["1.6 Posting gate"]
    s5["1. Write it the way it<br/>should end up"]
    s6["2. Run post-lint"]
    s5 --> s6
    s7["3. Run the review"]
    s6 --> s7
    s8["4. Right before posting"]
    s7 --> s8
    s9["5. Post in the thread where<br/>the person wrote"]
    s8 --> s9
  end
  s5 -.-> r8[["writing"]]
  s7 -.-> r9[["review"]]
  s7 -.-> r10[["writing"]]
  start --> g0
  g0 ~~~ g1
```

## Pushing, saying a PR is ready, merging

Opens `mergeworthy:merging` (1.7).

```mermaid
flowchart TB
  start(["Pushing, saying a PR is<br/>ready, merging"])
  subgraph g0["1.7 Pushing"]
    s0["1.7 Pushing"]
  end
  start --> g0
```

## Writing skills, rules or prompts; starting or briefing subagents; taking over another session's work

Opens `mergeworthy:delegating` (1.9, 1.10).

```mermaid
flowchart TB
  start(["Writing skills, rules or<br/>prompts; starting or<br/>briefing subagents;<br/>taking over another<br/>session's work"])
  subgraph g0["1.9 Writing rules"]
    s0["1.9 Writing rules"]
  end
  subgraph g1["1.10 Integrating agents'<br/>work"]
    s1["1.10 Integrating agents'<br/>work"]
  end
  subgraph g2["Briefing an agent"]
    s2["Briefing an agent"]
  end
  start --> g0
  g0 ~~~ g1
  g1 ~~~ g2
```

## Any change that lands in a PR: writing it, committing it, pushing it to an open PR

Opens `mergeworthy:pull-request` (the steps to a merge-ready PR).

```mermaid
flowchart TB
  start(["Any change that lands in<br/>a PR: writing it,<br/>committing it, pushing<br/>it to …"])
  subgraph g0["pull-request"]
    s0["1. Check it is not already<br/>fixed"]
    s1["2. Prove the problem exists"]
    s0 --> s1
    s2["3. Find an approach that<br/>rates high"]
    s1 --> s2
    s3["4. Build and gate"]
    s2 --> s3
    s4["5. See it in the browser"]
    s3 --> s4
    s5["6. Converge"]
    s4 --> s5
    s6["7. The PR"]
    s5 --> s6
  end
  s1 -.-> r1[["evidence"]]
  s2 -.-> r2[["finality"]]
  s2 -.-> r3[["core"]]
  s3 -.-> r4[["guardian"]]
  s3 -.-> r5[["design-loop"]]
  s3 -.-> r6[["converge"]]
  s3 -.-> r7[["core"]]
  s4 -.-> r8[["open-issue"]]
  s4 -.-> r9[["evidence"]]
  s4 -.-> r10[["core"]]
  s5 -.-> r11[["converge"]]
  s6 -.-> r12[["writing"]]
  s6 -.-> r13[["evidence"]]
  s6 -.-> r14[["core"]]
  start --> g0
```

## Opening an issue

Opens `mergeworthy:open-issue` (one finding a newcomer can find, reproduce and judge).

```mermaid
flowchart TB
  start(["Opening an issue"])
  subgraph g0["open-issue"]
    s0["1. Already filed or fixed?"]
    s1["2. Reproduce it on today's<br/>‹base›"]
    s0 --> s1
    s2["3. Write the body"]
    s1 --> s2
    s3["4. Post it through the gate"]
    s2 --> s3
  end
  s1 -.-> r1[["evidence"]]
  s2 -.-> r2[["writing"]]
  s2 -.-> r3[["evidence"]]
  s3 -.-> r4[["github-threads"]]
  start --> g0
```

## Showing a behavior: a reproduction, a screenshot, a video

Opens `mergeworthy:evidence` (reproducing it as a person would, capturing it, uploading it).

```mermaid
flowchart TB
  start(["Showing a behavior: a<br/>reproduction, a<br/>screenshot, a video"])
  subgraph g0["Reproduce it as a person<br/>would"]
    s0["Reproduce it as a person<br/>would"]
  end
  subgraph g1["Capture it"]
    s1["Capture it"]
  end
  subgraph g2["Upload it"]
    s2["Upload it"]
  end
  start --> g0
  g0 ~~~ g1
  g1 ~~~ g2
```

## Converging a PR, before it's ready (every tier)

Opens `mergeworthy:converge` (the pipeline every PR runs: finality, Loop A, Loop B, the fresh reader, gates).

```mermaid
flowchart TB
  start(["Converging a PR, before<br/>it's ready (every tier)"])
  subgraph g0["The pipeline"]
    s0["1. Finality"]
    s1["2. Loop A"]
    s0 --> s1
    s2["3. Loop B"]
    s1 --> s2
    s3["4. Loop A again"]
    s2 --> s3
    s4["5. The fresh reader"]
    s3 --> s4
    s5["6. Gates"]
    s4 --> s5
  end
  s0 -.-> r1[["finality"]]
  s0 -.-> r2[["pull-request"]]
  s1 -.-> r3[["verify"]]
  s2 -.-> r4[["review"]]
  s2 -.-> r5[["guardian"]]
  s2 -.-> r6[["refactor"]]
  s3 -.-> r7[["verify"]]
  s4 -.-> r8[["review"]]
  s4 -.-> r9[["merging"]]
  s4 -.-> r10[["github-threads"]]
  s5 -.-> r11[["writing"]]
  start --> g0
```

## Bug verification, reproduce-only

Opens `mergeworthy:verify` (Loop A (bug verification)).

```mermaid
flowchart TB
  start(["Bug verification,<br/>reproduce-only"])
  subgraph g0["verify"]
    s0["1. Fix each bug at its root<br/>cause"]
    s1["2. If the area has already<br/>had two corrective …"]
    s0 --> s1
    s2["3. Put fixes to base code<br/>in the bottom …"]
    s1 --> s2
    s3["4. Queue another pass on<br/>that slice"]
    s2 --> s3
  end
  s0 -.-> r1[["core"]]
  s0 -.-> r2[["converge"]]
  s2 -.-> r3[["converge"]]
  s3 -.-> r4[["core"]]
  start --> g0
```

## Bloat and quality rounds

Opens `mergeworthy:guardian` (the guardian charter, Loop B (bloat and quality)).

```mermaid
flowchart TB
  start(["Bloat and quality rounds"])
  subgraph g0["guardian"]
    s0["1. Review each<br/>implementer's diff<br/>yourself before<br/>cherry-picking"]
    s1["2. Cherry-pick onto the PR<br/>branch"]
    s0 --> s1
    s2["3. Run the product lanes<br/>the changes touch"]
    s1 --> s2
    s3["4. Continue the Loop A<br/>agent with the landed …"]
    s2 --> s3
  end
  s0 -.-> r1[["delegating"]]
  s3 -.-> r2[["converge"]]
  s3 -.-> r3[["delegating"]]
  subgraph g1["Guardian"]
    s4["12 rules: BLOAT, CODE QUALITY, PROBLEM VARIABILITY…"]
  end
  s4 -.-> r4[["design-loop"]]
  start --> g0
  g0 ~~~ g1
```

## The refactor pass

Opens `mergeworthy:refactor` (the pinnacle split + simplify prompt).

```mermaid
flowchart TB
  start(["The refactor pass"])
  subgraph g0["The prompt"]
    s0["The prompt"]
  end
  subgraph g1["Running it"]
    s1["Running it"]
  end
  start --> g0
  g0 ~~~ g1
```

## Code drifted through many patches; a design thread drifted over many rounds; stuck with every option costing something ruled out; asked for the ideal design (brainstorm, perfect world, pinnacle)

Opens `mergeworthy:finality` (the finality pass).

```mermaid
flowchart TB
  start(["Code drifted through<br/>many patches; a design<br/>thread drifted over many<br/>rounds; stuck with …"])
  start --> g0
```

## Any independent review

Opens `mergeworthy:review` (who reviews, the reviewer charter).

```mermaid
flowchart TB
  start(["Any independent review"])
  subgraph g0["review"]
    s0["1. A model from another<br/>company than the<br/>session's"]
    s1["2. A fresh-context subagent<br/>on the session's default<br/>model"]
    s0 --> s1
  end
  s1 -.-> r1[["delegating"]]
  s1 -.-> r2[["guardian"]]
  s1 -.-> r3[["refactor"]]
  s1 -.-> r4[["github-threads"]]
  s1 -.-> r5[["core"]]
  subgraph g1["The PR review round"]
    s2["1. Write the charter to<br/>‹artifact<br/>root›/review-‹pass<br/>id›.md"]
    s3["2. Append the diff command<br/>against git merge-base<br/>HEAD …"]
    s2 --> s3
    s4["3. Where the reviewer can't<br/>run your gates"]
    s3 --> s4
    s5["4. If no reviewer at all is<br/>available"]
    s4 --> s5
  end
  s3 -.-> r6[["core"]]
  s5 -.-> r7[["converge"]]
  s5 -.-> r8[["core"]]
  start --> g0
  g0 ~~~ g1
```

## A rule failed, or the user names a failure

Opens `mergeworthy:past-failures` (the table of past failures and the rule for each).

```mermaid
flowchart TB
  start(["A rule failed, or the<br/>user names a failure"])
  start --> g0
```

## Using or fixing the scripts and hooks

Opens `mergeworthy:mechanisms` (the watcher, the hooks, `gate-pass`, `post-lint`, `pr-steps`).

```mermaid
flowchart TB
  start(["Using or fixing the<br/>scripts and hooks"])
  subgraph g0["Commands"]
    s0["Commands"]
  end
  subgraph g1["gh-watch-start"]
    s1["gh-watch-start"]
  end
  subgraph g2["post-lint"]
    s2["post-lint"]
  end
  subgraph g3["gate-pass"]
    s3["gate-pass"]
  end
  subgraph g4["The finality trigger"]
    s4["The finality trigger"]
  end
  subgraph g5["pr-steps"]
    s5["pr-steps"]
  end
  subgraph g6["The watcher daemon"]
    s6["The watcher daemon"]
  end
  subgraph g7["Hooks"]
    s7["Hooks"]
  end
  subgraph g8["pre-bash-guard.py"]
    s8["pre-bash-guard.py"]
  end
  subgraph g9["post-bash-register.py"]
    s9["post-bash-register.py"]
  end
  subgraph g10["stop-lint.py"]
    s10["stop-lint.py"]
  end
  subgraph g11["session-start"]
    s11["session-start"]
  end
  start --> g0
  g0 ~~~ g1
  g1 ~~~ g2
  g2 ~~~ g3
  g3 ~~~ g4
  g4 ~~~ g5
  g5 ~~~ g6
  g6 ~~~ g7
  g7 ~~~ g8
  g8 ~~~ g9
  g9 ~~~ g10
  g10 ~~~ g11
```
