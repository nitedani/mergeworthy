import { createHash } from 'node:crypto'
import { readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { parseArgs } from 'node:util'
import { isValidReason } from './gates.mjs'
import { cwdRepo, ghPaged, ghUser, hasBadge, parseRef, threadUrl } from './github.mjs'
import { lint, printFindings } from './lint.mjs'

const BYPASS_FLAG = 'I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE'

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
  const thread = namedThread(ghArgs, ctx)
  const post = { draft, thread, kind: values.kind ?? inferredKind(ghWords(ghArgs)), repo: repoOf(ghArgs) ?? cwdRepo(ctx, ctx.cwd), login: ghUser(ctx)?.login }
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
    problem: ({ draft, repo, kind, login }, ctx) => {
      const findings = lint(readFileSync(draft, 'utf8'), { repo, kind, login })
      printFindings(ctx, findings)
      return findings.some((f) => f.level === 'error') && 'the draft has lint errors (above)'
    },
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

function namedThread(ghArgs, ctx) {
  const [group, action, target] = ghWords(ghArgs)
  if (['pr', 'issue'].includes(group) && action === 'comment' && target) {
    if (/^\d+$/.test(target)) {
      const repo = repoOf(ghArgs) ?? cwdRepo(ctx, ctx.cwd)
      return repo && parseRef(`${repo}#${target}`)
    }
    return parseRef(target)
  }
  const api = ghArgs.map((a) => /^\/?repos\/([^/]+)\/([^/]+)\/issues\/(\d+)\/comments$/.exec(a)).find(Boolean)
  return api && { owner: api[1], repo: api[2], number: Number(api[3]) }
}

function inferredKind([group, action]) {
  if (group === 'pr' && (action === 'create' || action === 'edit')) return 'pr'
  if (group === 'issue' && action === 'create') return 'issue'
  return 'reply'
}

function ghWords(ghArgs) {
  return ghArgs.filter((a, i) => !['-R', '--repo'].includes(ghArgs[i - 1]) && !['-R', '--repo'].includes(a))
}

function repoOf(ghArgs) {
  const flag = ghArgs.findIndex((a) => a === '-R' || a === '--repo')
  if (flag >= 0) return ghArgs[flag + 1]
  for (const arg of ghArgs) {
    const repo = /^--repo=(.+)$|github\.com\/([^/]+\/[^/]+)\/|^\/?repos\/([^/]+\/[^/]+)\//.exec(arg)
    if (repo) return repo[1] ?? repo[2] ?? repo[3]
  }
  return null
}

function refuse(ctx, stops, reason, argv) {
  for (const stop of stops) ctx.err(`mw post stopped (${stop.name}): ${stop.problem}`)
  if (reason !== undefined) ctx.err('The bypass reason is missing or shorter than 3 words.')
  ctx.err(`To post anyway, with your real reason: mw post --${BYPASS_FLAG} "<why this is right here>" ${argv.join(' ')}`)
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
