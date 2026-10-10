import { ghJson, ghPaged, hasBadge, parseRef } from './github.mjs'

export function threadCommand(argv, ctx) {
  const ref = parseRef(argv[0] ?? '')
  if (!ref) return 2
  ctx.out(renderThread(fetchThread(ctx, ref)))
  return 0
}

function fetchThread(ctx, { owner, repo, number }) {
  const base = `repos/${owner}/${repo}`
  const issue = ghJson(ctx, ['api', `${base}/issues/${number}`])
  const comments = ghPaged(ctx, `${base}/issues/${number}/comments`).map((c) => entry({ user: c.user, at: c.created_at, url: c.html_url, body: c.body }))
  const reviews = issue.pull_request
    ? ghPaged(ctx, `${base}/pulls/${number}/reviews`)
        .filter((r) => r.body || r.state !== 'COMMENTED')
        .map((r) => entry({ user: r.user, at: r.submitted_at, url: r.html_url, body: r.body, label: `review ${r.state}` }))
    : []
  const inline = issue.pull_request
    ? ghPaged(ctx, `${base}/pulls/${number}/comments`).map((c) => entry({ user: c.user, at: c.created_at, url: c.html_url, body: c.body, label: `${c.path}:${c.line ?? c.original_line}` }))
    : []
  const references = ghPaged(ctx, `${base}/issues/${number}/timeline`)
    .filter((event) => event.event === 'cross-referenced' && event.source?.issue)
    .map((event) => event.source.issue)
  return { issue, entries: [...comments, ...reviews, ...inline].sort((a, b) => Date.parse(a.at) - Date.parse(b.at)), references }
}

function entry({ user, at, url, body, label }) {
  return { login: user?.login ?? 'ghost', at, url, body: body ?? '', label }
}

function renderThread({ issue, entries, references }) {
  return [
    `# ${issue.title}`,
    `${issue.pull_request ? 'PR' : 'Issue'} · ${issue.state} · by ${issue.user?.login} · ${issue.html_url}`,
    '',
    issue.body ?? '',
    ...entries.flatMap((e) => ['', `### ${e.login} · ${e.at} · ${e.url}${e.label ? ` · ${e.label}` : ''}${hasBadge(e.body) ? ' (agent)' : ''}`, '', e.body]),
    ...(references.length ? ['', '## Cross-references', '', ...references.map((r) => `- ${r.html_url} (${r.state}): ${r.title}`)] : []),
  ].join('\n')
}
