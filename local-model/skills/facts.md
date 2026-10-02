---
mode: facts
use: Answer a question from the code, e.g. "every caller of X and when it runs".
requires: Goal
---
## Instructions
Answer the Goal with facts from the code and commands only. Every claim carries its source: `path:line`, or the command you ran and its exit code. Before saying something is unused or only used once, find every caller.

## Ticket
- Goal: the question, as one observable answer.
- Facts: what you verified, each with its source.
- To check: your hypotheses, as questions.
- Scope: the paths and commands it may use.
