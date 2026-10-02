## 1.0 Triage

Read the task and every link in it. Write `Tier: <X>, because <signals>` and put it in the first report. Re-triage when the deliverables or open decisions change, and say so.

| Tier | Signals | Process |
|---|---|---|
| **0: Answer** | An answer, research or a review; nothing to change. | Principles, evidence, reporting; the posting gate if published. |
| **S: Single fix** | One bounded fix in one repo, expected behavior already clear. | Part 2 per change; its review round and refactor pass feed `pr-steps`. Part 3 sections 1–5 and section 10's failure and evidence rules; of its loops, one dry verification pass per slice after its last fix and one guardian round for the closing verdict (re-run on the head if its findings land). The project file's gates green, body true to the head. |
| **M: Feature or set** | A new capability, a changed public contract, several change units, or open behavior questions. | Part 2 per unit, full Part 3 in place of Part 2's single rounds, invariants, ledger, decision packet, design loop (1.4). |
| **L: Program** | Changes across two or more independently maintained repos<!-- if ownership=external -->, or two or more decision makers<!-- end -->. | Tier M everywhere, plus the umbrella issue (1.2). |

