import { parseArgs } from 'node:util'
import { hasBadge, parseRef } from './github.mjs'
import { shellQuote } from './shell.mjs'
import { readState, writeState } from './state.mjs'
import { seconds } from './time.mjs'

const FAILED = new Set(['FAILURE', 'TIMED_OUT', 'STARTUP_FAILURE', 'ERROR'])
const THUMBS = { THUMBS_UP: '👍', THUMBS_DOWN: '👎' }

export async function watchCommand(argv, ctx) {
  const { positionals, values } = parseArgs({
    args: argv,
    allowPositionals: true,
    options: {
      commands: { type: 'boolean' },
      workspace: { type: 'string' },
      interval: { type: 'string', default: '60' },
      max: { type: 'string', default: '110m' },
      once: { type: 'boolean' },
    },
  })
  const refs = positionals.map(parseRef)
  const [intervalMs, maxMs] = [values.interval, values.max].map((duration) => seconds(duration) * 1000)
  if (values.commands && !values.workspace) {
    ctx.err('mw watch: --commands needs --workspace <name>')
    return 2
  }
  const owners = values.commands && (readState(ctx, 'workspaces.json', {})[values.workspace] ?? [values.workspace])
  if (!refs.length || refs.includes(null) || Number.isNaN(intervalMs + maxMs)) return 2
  const rearm = `mw watch ${argv.map(shellQuote).join(' ')}`
  return pollUntilEvents(ctx, { refs, owners, intervalMs, deadline: ctx.now() + maxMs, once: values.once, rearm })
}

async function pollUntilEvents(ctx, { refs, owners, intervalMs, deadline, once, rearm }) {
  const file = `watch/${process.env.CLAUDE_CODE_SESSION_ID || 'default'}.json`
  let errors = 0
  let lastError = ''
  for (let poll = 0; ; poll++) {
    const state = readState(ctx, file, { threads: {} })
    const now = new Date(ctx.now()).toISOString()
    const agentSearch = owners && poll % 3 === 0 && { owners, since: state.agentSince ?? now }
    const r = ctx.gh(['api', 'graphql', '-f', `query=${pollQuery(refs, agentSearch)}`])
    if (r.code === 0) {
      errors = 0
      const { events, next } = diffPoll(state, JSON.parse(r.stdout).data, refs, now)
      writeState(ctx, file, next)
      if (events.length) {
        for (const event of events) ctx.out(event)
        ctx.out(`re-arm: ${rearm}`)
        return 0
      }
    } else {
      errors++
      lastError = (r.stderr || r.stdout).trim().split('\n')[0] || `gh api graphql exited with code ${r.code} and printed nothing`
    }
    if (errors >= 5 || once || ctx.now() >= deadline) {
      ctx.out(errors ? `ERROR ${lastError}` : `no events; re-arm: ${rearm}`)
      return errors ? 1 : 0
    }
    await ctx.sleep(intervalMs)
  }
}

function pollQuery(refs, agentSearch) {
  const threads = refs.map(
    (ref, i) => `t${i}: repository(owner: ${JSON.stringify(ref.owner)}, name: ${JSON.stringify(ref.repo)}) { issueOrPullRequest(number: ${ref.number}) { ...thread } }`,
  )
  const search = agentSearch
    ? [`agent: search(type: ISSUE, first: 30, query: ${JSON.stringify(agentQuery(agentSearch))}) { nodes { ... on Issue { comments(last: 30) { ...comments } } ... on PullRequest { comments(last: 30) { ...comments } } } }`]
    : []
  return `query { viewer { login } ${[...threads, ...search].join(' ')} }
fragment comments on IssueCommentConnection { nodes { author { login } createdAt url body reactions(last: 10) { nodes { content createdAt user { login } } } } }
fragment thread on IssueOrPullRequest {
  ... on Issue { url state closedAt comments(last: 30) { ...comments } }
  ... on PullRequest {
    url state closedAt mergedAt mergeable headRefOid comments(last: 30) { ...comments }
    reviews(last: 20) { nodes { author { login } createdAt submittedAt url body state } }
    reviewThreads(last: 30) { nodes { comments(last: 10) { nodes { author { login } createdAt url body path } } } }
    commits(last: 1) { nodes { commit { messageHeadline author { name user { login } } statusCheckRollup { contexts(last: 100) { nodes {
      __typename ... on CheckRun { name conclusion detailsUrl } ... on StatusContext { context state targetUrl }
    } } } } } }
  }
}`
}

function agentQuery({ owners, since }) {
  return `commenter:@me "/agent" updated:>=${since.replace(/\.\d+Z$/, 'Z')} ${owners.map((owner) => `user:${owner}`).join(' ')}`
}

export function diffPoll(state, data, refs, now) {
  const login = data.viewer.login
  const threads = {}
  const events = []
  refs.forEach((ref, i) => {
    const node = data[`t${i}`].issueOrPullRequest
    const key = `${ref.owner}/${ref.repo}#${ref.number}`
    const diff = diffThread(state.threads[key], node, login, now)
    threads[key] = diff.next
    events.push(...diff.events)
  })
  const agent = diffAgentCommands(state.agentSince, data.agent, login, now)
  return { events: [...events, ...agent.events], next: { threads: { ...state.threads, ...threads }, agentSince: agent.since } }
}

function diffThread(prev, node, login, now) {
  const items = threadItems(node, login)
  const failing = failingChecks(node)
  const headCommit = node.commits?.nodes[0]?.commit
  const conflict = node.mergeable === 'UNKNOWN' ? (prev?.conflict ?? false) : node.mergeable === 'CONFLICTING'
  const times = items.map((item) => item.at)
  const since = latest(prev ? [prev.since, ...times] : times.length ? times : [now])
  const next = { since, conflict, failing: failing.map((c) => c.name), state: node.state, head: node.headRefOid ?? null }
  if (!prev) return { events: [], next }
  const othersHead = prev.head && next.head !== prev.head && headCommit.author.user?.login !== login
  const events = [
    ...items
      .filter((item) => Date.parse(item.at) > Date.parse(prev.since) && !item.mine)
      .map((item) => eventLine(item.kind, item.url, item.author === login ? `${item.author} (you)` : item.author, item.text)),
    ...failing.filter((c) => !prev.failing.includes(c.name)).map((c) => eventLine('CI', c.url ?? node.url, c.name, c.result)),
    ...(othersHead ? [eventLine('PUSH', node.url, headCommit.author.user?.login ?? headCommit.author.name, `${next.head.slice(0, 7)} ${headCommit.messageHeadline}`)] : []),
    ...(node.state !== prev.state && node.state !== 'OPEN' ? [eventLine(node.state, node.url, '-', `${node.state.toLowerCase()} at ${node.mergedAt ?? node.closedAt}`)] : []),
    ...(conflict && !prev.conflict ? [eventLine('CONFLICT', node.url, '-', 'mergeable is CONFLICTING')] : []),
  ]
  return { events, next }
}

function threadItems(node, login) {
  const comments = node.comments.nodes
  const reviews = node.reviews?.nodes ?? []
  const inline = (node.reviewThreads?.nodes ?? []).flatMap((thread) => thread.comments.nodes)
  const reactions = comments
    .filter((c) => isOurs(c, login))
    .flatMap((c) =>
      c.reactions.nodes
        .filter((r) => r.content in THUMBS)
        .map((r) => ({ kind: 'REACTION', url: c.url, author: r.user?.login ?? 'ghost', at: r.createdAt, text: THUMBS[r.content], mine: r.user?.login === login })),
    )
  return [
    ...comments.map((c) => item({ kind: 'COMMENT', node: c, at: c.createdAt, text: c.body }, login)),
    ...reviews.map((r) => item({ kind: 'REVIEW', node: r, at: r.submittedAt ?? r.createdAt, text: [r.state, r.body].filter(Boolean).join(': ') }, login)),
    ...inline.map((c) => item({ kind: 'INLINE', node: c, at: c.createdAt, text: `${c.path}: ${c.body}` }, login)),
    ...reactions,
  ]
}

function item({ kind, node, at, text }, login) {
  return { kind, url: node.url, author: node.author?.login ?? 'ghost', at, text, mine: isOurs(node, login) }
}

function isOurs(node, login) {
  return node.author?.login === login && hasBadge(node.body)
}

function failingChecks(node) {
  const contexts = node.commits?.nodes[0]?.commit.statusCheckRollup?.contexts.nodes ?? []
  return contexts
    .map((c) => (c.__typename === 'CheckRun' ? { name: c.name, result: c.conclusion, url: c.detailsUrl } : { name: c.context, result: c.state, url: c.targetUrl }))
    .filter((c) => FAILED.has(c.result))
}

function diffAgentCommands(since, search, login, now) {
  if (!search) return { events: [], since }
  const from = since ?? now
  const commands = search.nodes
    .flatMap((issue) => issue.comments?.nodes ?? [])
    .filter((c) => c.author?.login === login && c.body.startsWith('/agent') && Date.parse(c.createdAt) > Date.parse(from))
  return {
    events: commands.map((c) => eventLine('AGENT', c.url, login, c.body)),
    since: latest([from, ...commands.map((c) => c.createdAt)]),
  }
}

function eventLine(kind, url, author, text) {
  return `${kind} ${url} ${author}: ${String(text ?? '').replace(/\s+/g, ' ').trim().slice(0, 160)}`
}

function latest(times) {
  return new Date(Math.max(...times.map(Date.parse))).toISOString()
}
