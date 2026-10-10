import { createHash } from 'node:crypto'
import { readFileSync, writeFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { parseArgs } from 'node:util'
import { BYPASS_TOKEN, isValidReason } from './gates.mjs'
import { ghCommand, textFiles } from './gh-command.mjs'
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
  ctx.out(`Recorded the ${verdict} verdict for ${draft}, with the sha256 hash of its text (${record.sha256.slice(0, 12)}…). mw post accepts a CLEAN verdict only while the draft is unchanged`)
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
  const gh = ghCommand(ghArgs)
  if (!textFiles(gh).some((file) => resolve(ctx.cwd, file) === draft)) {
    ctx.err('mw post: the gh command after -- must read its text from this draft file, so that the reviewed text is what gets posted. Pass it with --body-file <draft> (--notes-file <draft> for a release, or as a file argument for a gist), or with -F body=@<draft> or --input <draft> for gh api')
    return 2
  }
  const repo = gh.repo ?? urlRepo(ghArgs) ?? cwdRepo(ctx, ctx.cwd)
  const thread = namedThread(gh, repo)
  const login = ghUser(ctx)?.login
  const findings = lint(readFileSync(draft, 'utf8'), { repo, kind: values.kind ?? inferredKind(gh), login })
  printFindings(ctx, findings)
  const post = { draft, thread, findings, login }
  const stops = POST_CHECKS.map((check) => ({ name: check.name, problem: check.problem(post, ctx) })).filter((stop) => stop.problem)
  const reason = values[BYPASS_FLAG]
  if (stops.length && !isValidReason(reason)) return refuse(ctx, stops, reason, argv)
  if (stops.length) ctx.err(`mw post: posting despite the failed checks (${stops.map((stop) => stop.name).join(', ')}), with this bypass reason: ${reason}`)
  const code = ctx.gh(ghArgs, { inherit: true }).code
  if (code === 0) ctx.out(`Posted. If you are not watching this thread for replies yet, run: mw watch ${thread ? threadUrl(thread) : '<url>'}`)
  return code
}

const POST_CHECKS = [
  {
    name: 'lint',
    problem: ({ findings }) => findings.some((f) => f.level === 'error') && 'the draft has mw lint errors, listed above',
  },
  {
    name: 'verdict',
    problem: ({ draft }) => {
      const verdict = readVerdict(draft)
      if (!verdict) return `the draft has no review verdict yet. A reviewer other than its writer reads it and, when it is ready, runs \`mw verdict ${draft} CLEAN --by <who>\``
      if (verdict.verdict !== 'CLEAN') return `the reviewer's verdict is ${verdict.verdict}. Fix what they found, then get a new review`
      return verdict.sha256 !== sha256(draft) && 'the draft changed after its review, so it needs a new review'
    },
  },
  {
    name: 'thread',
    problem: ({ thread, login }, ctx) => {
      if (!thread) return null
      const { comments, error } = readComments(ctx, thread)
      if (error) return `couldn't read the thread's comments, so mw post can't tell whether this would be your third comment in a row (${error}). Check that gh works with \`gh auth status\`, then run this again`
      const newest = comments.slice(-2)
      const ours = newest.length === 2 && newest.every((c) => c.user?.login === login && hasBadge(c.body))
      return ours && 'this would be your third comment in a row on this thread, after two of yours. Edit your last comment instead'
    },
  },
]

function readComments(ctx, { owner, repo, number }) {
  try {
    return { comments: ghPaged(ctx, `repos/${owner}/${repo}/issues/${number}/comments`) }
  } catch (error) {
    return { error: error.message }
  }
}

function namedThread({ group, action, target, api }, repo) {
  if (['pr', 'issue'].includes(group) && action === 'comment' && target) return /^\d+$/.test(target) ? repo && parseRef(`${repo}#${target}`) : parseRef(target)
  const path = /^\/?repos\/([^/]+)\/([^/]+)\/issues\/(\d+)\/comments$/.exec(api?.path ?? '')
  return path && { owner: path[1], repo: path[2], number: Number(path[3]) }
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
  for (const stop of stops) ctx.err(`mw post did not post (its ${stop.name} check): ${stop.problem}`)
  if (reason !== undefined) ctx.err('Your bypass reason is missing or shorter than 3 words, so it does not count.')
  ctx.err(`These checks are warnings you may bypass. To post anyway, run this with your real reason, which the user will see in the command: mw post --${BYPASS_FLAG} "<why this is right here>" ${withoutBypass(argv).map(shellQuote).join(' ')}`)
  return 3
}

function withoutBypass(argv) {
  const split = argv.indexOf('--')
  const own = argv.slice(0, split).filter((arg, i, args) => !arg.startsWith(`--${BYPASS_FLAG}`) && args[i - 1] !== `--${BYPASS_FLAG}`)
  return [...own, ...argv.slice(split)]
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
