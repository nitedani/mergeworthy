
## Environment: local model (the methodology is already built for it)

The methodology you got is its `local` build profile (`session_model=local`): the subscription rules are out of it, and its "You are the local model" rules are yours. What it can't know about this environment:

- **Time and context instead of money.** Tokens cost nothing, but the GPU answers one request at a time: subagents run one after another, never in parallel, and each one re-reads its context (about 2,000 tokens per second). Start a subagent only when a step requires one (an independent review) or the work is long and separate, one at a time. Your context holds about 160K tokens: write verified facts into the artifact root as you find them, and re-read them before you write anything that relies on them.
- **No Monitor tool.** A local claude has no Monitor tool: where the methodology arms the Monitor on a watcher's `events.log`, run the printed tail as a background task (timeout 1800), handle its output when notified, and re-arm on every expiry — the Stop hook accepts the live `tail` process as the armed monitor.
- **Reviews.** The methodology's review model (Codex, another company's model) is still the reviewer when `codex exec` works. When it doesn't, the fallback subagent is this same local model reviewing its own kind of work: say that in your report to the user, so they know the post or PR had no outside review.
- **Web search.** The built-in `WebSearch` needs Anthropic's servers and returns nothing here. Search with `web_search` (it lists results), then read a page with `WebFetch`. Numbers and specs you state come from a page you read, with its URL; if you couldn't find a source, say so and give the number as an estimate.
