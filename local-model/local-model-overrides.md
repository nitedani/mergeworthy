
## Environment: local model (overrides the methodology where they conflict)

You run on a local model (the one profile.sh selects, on this machine's GPU) through `claude-local`, not on a Claude subscription.

- **No usage limits.** Nothing here runs out, so skip everything about them: `claude-swap`, rate limits, 429s, spare subscriptions, swap events, and waking up after a limit (methodology 1.1.13's limit parts, 1.12 step 4, Part 2's and Part 3's rate-limit rules, Part 5's `claude-swap` row).
- **One model.** Every model name in the methodology (default, Sonnet, Opus and any other) is this same local model. Don't set a model on the Agent tool; a "cheaper model" doesn't exist here.
- **Time and context instead of money.** Tokens cost nothing, but the GPU answers one request at a time: subagents run one after another, never in parallel, and each one re-reads its context (about 2,000 tokens per second). Start a subagent only when a step requires one (an independent review) or the work is long and separate, one at a time. Your context holds about 160K tokens: write verified facts into the artifact root as you find them, and re-read them before you write anything that relies on them.
- **Reviews.** The methodology's review model (Codex, another company's model) is still the reviewer when `codex exec` works. When it doesn't, the fallback subagent is this same local model reviewing its own kind of work: say that in your report to the user, so they know the post or PR had no outside review.
- **You are the local model.** `local-agent` and `claude-usage` in the methodology are for Claude sessions that hand work to you; don't call them yourself.
