import { createHash } from 'node:crypto'
import { readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { parseArgs } from 'node:util'
import { BYPASS_TOKEN, isValidReason } from './gates.mjs'
import { ghCommand } from './gh-command.mjs'
import { cwdRepo, ghPaged, ghUser, hasBadge, parseRef, threadUrl } from './github.mjs'
import { lint, printFindings } from './lint.mjs'
import { shellQuote } from './shell.mjs'

const BYPASS_FLAG = BYPASS_TOKEN.slice(2)

export function verdictCommand(argv, ctx) {
  const { positionals, values } = parseArgs({ args: argv, allowPositionals: true, options: { by: { type: 'string' } } })
  const [draft, verdict] = positionals
  if (!draft || !['CLEAN', 'CHANGES'].includes(verdict) || !values.by) return 2
  const record = { sha256: sha256(draft), verdict, by: values.by, at: new Date(ctx.now()).toISOString() }
  writeFileSync(`${draft}.verdict.json`, JSON.stringify(record, null, 2) + '\n')
  ctx.out(`${verdict} recorded for ${draft} (${record.sha256.slice(0, 12)})`)
  return 0
}

export function postCommand(argv, ctx) {
  const split = argv.indexOf('--')
  if (split < 0 || argv[split + 1] !== 'gh') return 2
  const ghArgs = argv.slice(split + 2)
  const { positionals, values } = parseArgs({
    args: argv.slice(0, split),
    allowPositionals: true,
    options: { [BYPASS_FLAG]: { type: 'string' }, kind: { type: 'string' } },
  })
  const draft = positionals[0] && resolve(ctx.cwd, positionals[0])
  if (!draft) return 2
  if (!postsDraft(ghArgs, draft, ctx.cwd)) {
    ctx.err('mw post: the gh command must post this draft (--body-file <draft>, -F body=@<draft> or --input <draft>)')
    return 2
  }
  const gh = ghCommand(ghArgs)
  const repo = gh.repo ?? urlRepo(ghArgs) ?? cwdRepo(ctx, ctx.cwd)
  const thread = namedThread(gh, ghArgs, repo)
  const login = ghUser(ctx)?.login
  const findings = lint(readFileSync(draft, 'utf8'), { repo, kind: values.kind ?? inferredKind(gh), login })
  printFindings(ctx, findings)
  const post = { draft, thread, findings, login }
  const stops = POST_CHECKS.map((check) => ({ name: check.name, problem: check.problem(post, ctx) })).filter((stop) => stop.problem)
  const reason = values[BYPASS_FLAG]
  if (stops.length && !isValidReason(reason)) return refuse(ctx, stops, reason, argv)
  if (stops.length) ctx.err(`bypassed (${stops.map((stop) => stop.name).join(', ')}): ${reason}`)
  const code = ctx.gh(ghArgs, { inherit: true }).code
  if (code === 0) ctx.out(`posted. Not watching this thread yet? mw watch ${thread ? threadUrl(thread) : '<url>'}`)
  return code
}

const POST_CHECKS = [
  {
    name: 'lint',
    problem: ({ findings }) => findings.some((f) => f.level === 'error') && 'the draft has lint errors (above)',
  },
  {
    name: 'verdict',
    problem: ({ draft }) => {
      const verdict = readVerdict(draft)
      if (!verdict) return `no review verdict: the reviewer runs \`mw verdict ${draft} CLEAN --by <who>\``
      if (verdict.verdict !== 'CLEAN') return `the review verdict is ${verdict.verdict}`
      return verdict.sha256 !== sha256(draft) && 'the draft changed since its review'
    },
  },
  {
    name: 'thread',
    problem: ({ thread, login }, ctx) => {
      const newest = thread && ghPaged(ctx, `repos/${thread.owner}/${thread.repo}/issues/${thread.number}/comments`).slice(-2)
      const ours = newest?.length === 2 && newest.every((c) => c.user?.login === login && hasBadge(c.body))
      return ours && 'third comment in a row; edit your last one instead'
    },
  },
]

function postsDraft(ghArgs, draft, cwd) {
  return ghArgs.some((arg) => resolve(cwd, arg.replace(/^(body=@|--body-file=|--input=)/, '')) === draft)
}

function namedThread(gh, ghArgs, repo) {
  const target = gh.args[0]
  if (['pr', 'issue'].includes(gh.group) && gh.action === 'comment' && target) return /^\d+$/.test(target) ? repo && parseRef(`${repo}#${target}`) : parseRef(target)
  const api = ghArgs.map((a) => /^\/?repos\/([^/]+)\/([^/]+)\/issues\/(\d+)\/comments$/.exec(a)).find(Boolean)
  return api && { owner: api[1], repo: api[2], number: Number(api[3]) }
}

function inferredKind({ group, action }) {
  if (group === 'pr' && (action === 'create' || action === 'edit')) return 'pr'
  if (group === 'issue' && action === 'create') return 'issue'
  return 'reply'
}

function urlRepo(ghArgs) {
  const match = ghArgs.map((a) => /github\.com\/([^/]+\/[^/]+)\/|^\/?repos\/([^/]+\/[^/]+)\//.exec(a)).find(Boolean)
  return match ? (match[1] ?? match[2]) : null
}

function refuse(ctx, stops, reason, argv) {
  for (const stop of stops) ctx.err(`mw post stopped (${stop.name}): ${stop.problem}`)
  if (reason !== undefined) ctx.err('The bypass reason is missing or shorter than 3 words.')
  ctx.err(`To post anyway, with your real reason: mw post --${BYPASS_FLAG} "<why this is right here>" ${argv.map(shellQuote).join(' ')}`)
  return 3
}

function readVerdict(draft) {
  try {
    return JSON.parse(readFileSync(`${draft}.verdict.json`, 'utf8'))
  } catch {
    return null
  }
}

function sha256(file) {
  return createHash('sha256').update(readFileSync(file)).digest('hex')
}
