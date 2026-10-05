# How the skills connect

Generated from the skills by `docs/build-graphs.py`; edit the skills, then run it. One graph per entry point in `always-on.md`: each section of the skill is a box, its numbered steps run top to bottom, and a dashed arrow marks where a step hands over to another skill.

## Which skill hands over to which

| Skill | Hands over to |
|---|---|
| `converge` | `finality`, `implement-issue`, `verify`, `guardian`, `refactor` |
| `core` | `implement-issue`, `delegating`, `merging`, `github-threads`, `converge` |
| `delegating` | nothing |
| `design-loop` | `implement-issue`, `core`, `review`, `github-threads`, `converge` |
| `finality` | nothing |
| `github-threads` | `review`, `refactor`, `core`, `implement-issue` |
| `guardian` | `delegating`, `review`, `design-loop` |
| `implement-issue` | `finality`, `guardian`, `design-loop`, `converge`, `core`, `verify`, `review`, `refactor` |
| `mechanisms` | nothing |
| `merging` | nothing |
| `past-failures` | nothing |
| `refactor` | nothing |
| `review` | `delegating`, `guardian`, `refactor`, `github-threads`, `core`, `converge` |
| `verify` | `converge`, `core` |

## Any multi-step or GitHub task, first

Opens `mergeworthy:core` (the task, triage 1.0, principles 1.1, tracking 1.2, discovery 1.3 (docs, style), safety 1.8, reporting 1.11, pre-flight 1.12).

```mermaid
flowchart TB
  start(["Any multi-step or GitHub<br/>task, first"])
  subgraph g0["1.1 Principles"]
    s0["17 rules: Critical path first, Invariants first, Do…"]
  end
  s0 -.-> r1[["implement-issue"]]
  s0 -.-> r2[["converge"]]
  s0 -.-> r3[["delegating"]]
  s0 -.-> r4[["merging"]]
  s0 -.-> r5[["github-threads"]]
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
  s3 -.-> r6[["github-threads"]]
  start --> g0
  g0 ~~~ g1
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
  s1 -.-> r1[["implement-issue"]]
  s1 -.-> r2[["core"]]
  s3 -.-> r3[["review"]]
  s4 -.-> r4[["github-threads"]]
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
    s1["2. Within about a minute"]
    s0 --> s1
    s2["3. Then think"]
    s1 --> s2
    s3["4. Then reply"]
    s2 --> s3
    s4["5. Book-keeping"]
    s3 --> s4
  end
  s1 -.-> r1[["review"]]
  s1 -.-> r2[["refactor"]]
  s1 -.-> r3[["core"]]
  s2 -.-> r4[["implement-issue"]]
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
  s7 -.-> r5[["review"]]
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

## Writing skills, rules or prompts; starting or briefing subagents

Opens `mergeworthy:delegating` (1.9, 1.10).

```mermaid
flowchart TB
  start(["Writing skills, rules or<br/>prompts; starting or<br/>briefing subagents"])
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

## Implementing an issue or opening a PR

Opens `mergeworthy:implement-issue` (the steps from an issue to a merge-ready PR).

```mermaid
flowchart TB
  start(["Implementing an issue or<br/>opening a PR"])
  subgraph g0["implement-issue"]
    s0["1. Check it is not already<br/>fixed"]
    s1["2. Prove the problem exists"]
    s0 --> s1
    s2["3. Find an approach that<br/>rates high"]
    s1 --> s2
    s3["4. Build and gate"]
    s2 --> s3
    s4["5. See it in the browser"]
    s3 --> s4
    s5["6. Review round"]
    s4 --> s5
    s6["7. Refactor pass"]
    s5 --> s6
    s7["8. The PR"]
    s6 --> s7
  end
  s2 -.-> r1[["finality"]]
  s3 -.-> r2[["guardian"]]
  s3 -.-> r3[["design-loop"]]
  s3 -.-> r4[["converge"]]
  s3 -.-> r5[["core"]]
  s4 -.-> r6[["core"]]
  s5 -.-> r7[["converge"]]
  s5 -.-> r8[["verify"]]
  s5 -.-> r9[["review"]]
  s5 -.-> r10[["guardian"]]
  s5 -.-> r11[["refactor"]]
  s6 -.-> r12[["guardian"]]
  s6 -.-> r13[["converge"]]
  start --> g0
```

## Converging a PR (Tier S condensed, Tier ≥ M in full before ready, or the owner asks)

Opens `mergeworthy:converge` (what converged means, through the passes below).

```mermaid
flowchart TB
  start(["Converging a PR (Tier S<br/>condensed, Tier ≥ M in<br/>full before ready, or …"])
  subgraph g0["converge"]
    s0["1. Finality"]
    s1["2. Bug verification"]
    s0 --> s1
    s2["3. Code review"]
    s1 --> s2
    s3["4. Guardian"]
    s2 --> s3
    s4["5. Refactor pass"]
    s3 --> s4
    s5["6. Gates"]
    s4 --> s5
  end
  s0 -.-> r1[["finality"]]
  s0 -.-> r2[["implement-issue"]]
  s1 -.-> r3[["verify"]]
  s3 -.-> r4[["guardian"]]
  s4 -.-> r5[["refactor"]]
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
  s0 -.-> r1[["converge"]]
  s2 -.-> r2[["converge"]]
  s3 -.-> r3[["core"]]
  start --> g0
```

## Bloat and quality rounds

Opens `mergeworthy:guardian` (the LeanKeeper charter (the guardian's audit rules), Loop B (bloat and quality)).

```mermaid
flowchart TB
  start(["Bloat and quality rounds"])
  subgraph g0["guardian"]
    s0["1. Review each<br/>implementer's diff<br/>yourself before<br/>cherry-picking"]
    s1["2. Cherry-pick onto the PR<br/>branch"]
    s0 --> s1
    s2["3. Run the product lanes<br/>the changes touch"]
    s1 --> s2
    s3["4. After the last landing"]
    s2 --> s3
  end
  s0 -.-> r1[["delegating"]]
  s3 -.-> r2[["review"]]
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

## Code drifted through many patches

Opens `mergeworthy:finality` (the finality pass).

```mermaid
flowchart TB
  start(["Code drifted through<br/>many patches"])
  start --> g0
```

## Any independent review

Opens `mergeworthy:review` (who reviews, the reviewer charter).

```mermaid
flowchart TB
  start(["Any independent review"])
  subgraph g0["review"]
    s0["1. Codex"]
    s1["2. A fresh-context Claude<br/>subagent"]
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
  subgraph g4["pr-steps"]
    s4["pr-steps"]
  end
  subgraph g5["The watcher daemon"]
    s5["The watcher daemon"]
  end
  subgraph g6["Hooks"]
    s6["Hooks"]
  end
  subgraph g7["pre-bash-guard.py"]
    s7["pre-bash-guard.py"]
  end
  subgraph g8["post-bash-register.py"]
    s8["post-bash-register.py"]
  end
  subgraph g9["stop-lint.py"]
    s9["stop-lint.py"]
  end
  subgraph g10["session-start"]
    s10["session-start"]
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
```
