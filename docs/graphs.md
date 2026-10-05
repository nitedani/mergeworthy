# How the skills connect

Generated from the skills by `docs/build-graphs.py`; edit the skills, then run it. One graph per entry point in `always-on.md`: each section of the skill is a box, its numbered steps run top to bottom, and a dashed arrow marks where a step hands over to another skill.

## Which skill hands over to which

| Skill | Hands over to |
|---|---|
| `converge` | `verify`, `guardian`, `refactor`, `finality` |
| `core` | `implement-issue`, `delegating`, `merging`, `github-threads`, `converge` |
| `delegating` | nothing |
| `design-loop` | `implement-issue`, `core`, `review`, `github-threads`, `converge` |
| `finality` | nothing |
| `github-threads` | `review`, `refactor`, `core`, `implement-issue`, `mechanisms` |
| `guardian` | `design-loop` |
| `implement-issue` | `finality`, `guardian`, `converge`, `design-loop`, `core` |
| `mechanisms` | nothing |
| `merging` | nothing |
| `past-failures` | nothing |
| `refactor` | nothing |
| `review` | `guardian`, `refactor`, `github-threads`, `core` |
| `verify` | `converge`, `core` |

## Any multi-step or GitHub task, first

Opens `mergeworthy:core` (the task, triage 1.0, principles 1.1, tracking 1.2, discovery 1.3, safety 1.8, reporting 1.11, pre-flight 1.12).

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
    s0["0. Before any new core API"]
    s1["1. Draft<br/>decisions/‹name›.md"]
    s0 --> s1
    s2["2. Prototype"]
    s1 --> s2
    s3["3. Adversarial review"]
    s2 --> s3
    s4["4. Propose to maintainers<br/>only when no invariant<br/>is …"]
    s3 --> s4
    s5["5. Post the walkthrough as<br/>soon as the prototype …"]
    s4 --> s5
  end
  s1 -.-> r1[["implement-issue"]]
  s1 -.-> r2[["core"]]
  s3 -.-> r3[["review"]]
  s4 -.-> r4[["github-threads"]]
  s5 -.-> r5[["converge"]]
  start --> g0
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
  s4 -.-> r5[["mechanisms"]]
  subgraph g1["1.6 Posting gate"]
    s5["1. Write it the way it<br/>should end up"]
    s6["2. Run post-lint with the<br/>draft's --kind"]
    s5 --> s6
    s7["3. Run the review"]
    s6 --> s7
    s8["4. Right before posting"]
    s7 --> s8
    s9["5. Post in the thread where<br/>the person wrote"]
    s8 --> s9
  end
  s7 -.-> r6[["review"]]
  s9 -.-> r7[["core"]]
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

## Writing rules, prompts or docs; starting or briefing subagents

Opens `mergeworthy:delegating` (1.9, 1.10).

```mermaid
flowchart TB
  start(["Writing rules, prompts<br/>or docs; starting or<br/>briefing subagents"])
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

Opens `mergeworthy:implement-issue` (Part 2).

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
  s3 -.-> r3[["converge"]]
  s3 -.-> r4[["design-loop"]]
  s3 -.-> r5[["core"]]
  s4 -.-> r6[["core"]]
  s5 -.-> r7[["converge"]]
  s6 -.-> r8[["converge"]]
  start --> g0
```

## Converging a PR (the owner asks, or Tier ≥ M before ready)

Opens `mergeworthy:converge` (Part 3, through the passes below).

```mermaid
flowchart TB
  start(["Converging a PR (the<br/>owner asks, or Tier ≥ M<br/>before ready)"])
  subgraph g0["converge"]
    s0["1. Bug verification"]
    s1["2. Guardian"]
    s0 --> s1
    s2["3. Refactor pass"]
    s1 --> s2
    s3["4. Finality and Owner-Safe<br/>closure"]
    s2 --> s3
    s4["5. Code review against the<br/>repo's standards and the<br/>…"]
    s3 --> s4
    s5["6. Every gate and product<br/>lane green on each …"]
    s4 --> s5
  end
  s0 -.-> r1[["verify"]]
  s1 -.-> r2[["guardian"]]
  s2 -.-> r3[["refactor"]]
  s3 -.-> r4[["finality"]]
  start --> g0
```

## Bug verification, reproduce-only

Opens `mergeworthy:verify` (Loop A).

```mermaid
flowchart TB
  start(["Bug verification,<br/>reproduce-only"])
  subgraph g0["verify"]
    s0["1. Fix each at its root<br/>cause"]
    s1["2. If the area has already<br/>had two corrective …"]
    s0 --> s1
    s2["3. Put fixes to base code<br/>in the bottom …"]
    s1 --> s2
    s3["4. Queue another pass on<br/>that slice"]
    s2 --> s3
  end
  s2 -.-> r1[["converge"]]
  s3 -.-> r2[["core"]]
  start --> g0
```

## Bloat and quality rounds

Opens `mergeworthy:guardian` (the LeanKeeper charter, Loop B).

```mermaid
flowchart TB
  start(["Bloat and quality rounds"])
  subgraph g0["The twelve lenses"]
    s0["12 rules: Bloat, Code quality, Problem variability…"]
  end
  s0 -.-> r1[["design-loop"]]
  start --> g0
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
  s1 -.-> r1[["guardian"]]
  s1 -.-> r2[["refactor"]]
  s1 -.-> r3[["github-threads"]]
  s1 -.-> r4[["core"]]
  start --> g0
```

## A rule failed, or the user names a failure

Opens `mergeworthy:past-failures` (Part 4).

```mermaid
flowchart TB
  start(["A rule failed, or the<br/>user names a failure"])
  start --> g0
```

## Using or fixing the scripts and hooks

Opens `mergeworthy:mechanisms` (Part 5).

```mermaid
flowchart TB
  start(["Using or fixing the<br/>scripts and hooks"])
  start --> g0
```
