import { readFileSync } from 'node:fs'
import { parseArgs } from 'node:util'
import { BADGE, ghUser } from './github.mjs'

export const LENGTH_NORMS = { reply: 200, design: 150, issue: 260 }

export function lintCommand(argv, ctx) {
  const { positionals, values } = parseArgs({ args: argv, allowPositionals: true, options: { repo: { type: 'string' }, kind: { type: 'string' } } })
  if (!positionals[0]) return 2
  const findings = lint(readFileSync(positionals[0], 'utf8'), { ...values, login: ghUser(ctx)?.login })
  printFindings(ctx, findings)
  return findings.some((f) => f.level === 'error') ? 1 : 0
}

export function printFindings(ctx, findings) {
  for (const f of findings) ctx.out(`${f.level}: ${f.line}: ${f.message}`)
}

export function lint(text, { repo, kind, login } = {}) {
  const doc = analyze(text)
  return CHECKS.filter((check) => !check.applies || check.applies({ repo, kind, login }))
    .flatMap((check) => check.find(doc, { kind }).map((f) => ({ check: check.name, level: check.level, ...f })))
    .sort((a, b) => a.line - b.line)
}

const PROCESS_WORDS = /\b(mergeworthy|harness|loop a|loop b|guardian|pr-steps|gate-pass|post-lint|fresh reader)\b/gi
const ATTRIBUTION = /(?:\b(?:[Yy]ou|[Hh]e|[Ss]he|[Tt]hey|[Ww]e)|@[\w-]+|\b(?!(?:It|This|That|What|Which|Who|There)\b)[A-Z][\w-]+)\s+(?:agreed|decided|suggested|proposed|asked for|said)\b|\b[Aa]s (?:agreed|discussed|decided)\b/g
const COMMENT_LINK = /#issuecomment-|#discussion_r|#pullrequestreview-/
const MENTION = /(?<![\w.@/`-])@[A-Za-z0-9][A-Za-z0-9-]*/g
const SECRET = /(?:ghp_|gho_|ghs_|ghu_|github_pat_)\w{20,}|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[abp]-|Bearer [A-Za-z0-9._-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----/g
const CODE_OR_LINK = /`|https?:\/\/|\]\(/
const CANT = /can't|can’t|cannot|impossible|no way to|isn't possible|isn’t possible/gi

const CHECKS = [
  {
    name: 'badge',
    level: 'error',
    applies: ({ kind }) => kind !== 'umbrella',
    find: (doc) => {
      const index = doc.lines.findIndex((line) => line.trim())
      return BADGE.test(doc.lines[index] ?? '') ? [] : [{ line: index + 1 || 1, message: 'the first line must be the agent badge, <img src="https://github.com/claude.png" ...>' }]
    },
  },
  {
    name: 'process-words',
    level: 'error',
    applies: ({ repo, login }) => !(login && repo?.split('/')[0].toLowerCase() === login.toLowerCase()),
    find: (doc) => matchLines(doc.prose, PROCESS_WORDS, (m) => `process word '${m}' in a repo the user doesn't own`),
  },
  {
    name: 'attribution',
    level: 'error',
    find: (doc) =>
      doc.paragraphs
        .filter((p) => !COMMENT_LINK.test(p.raw))
        .flatMap((p) => matchLines(p.prose, ATTRIBUTION, (m) => `'${m}' attributes a decision without a link to the comment`, p.line)),
  },
  { name: 'mention', level: 'error', find: (doc) => matchLines(doc.prose, MENTION, (m) => `${m} pings them; write the name without @ unless you are blocked on them`) },
  { name: 'em-dash', level: 'error', find: (doc) => matchLines(doc.prose, /—/g, () => 'em dash; use a comma, colon, period or parentheses') },
  { name: 'secret', level: 'error', find: (doc) => matchLines(doc.lines, SECRET, () => 'this looks like a secret token') },
  {
    name: 'cant',
    level: 'warning',
    find: (doc) =>
      doc.paragraphs
        .filter((p) => !CODE_OR_LINK.test(p.raw))
        .flatMap((p) => matchLines(p.prose, CANT, (m) => `'${m}' without code or a link that shows it`, p.line)),
  },
  {
    name: 'length',
    level: 'warning',
    applies: ({ kind }) => kind in LENGTH_NORMS,
    find: (doc, { kind }) => {
      const words = doc.prose.join(' ').replace(/<[^>]*>/g, ' ').split(/\s+/).filter((w) => /\w/.test(w)).length
      const limit = LENGTH_NORMS[kind] * (kind === 'design' ? Math.max(1, doc.quotes) : 1)
      return words > limit ? [{ line: 1, message: `${words} words, more than the ${limit} ${kind} posts usually need: say what the length is for (several quoted questions, code, a walkthrough)` }] : []
    },
  },
]

function analyze(text) {
  const lines = text.split('\n')
  let fenced = false
  const prose = lines.map((line) => {
    if (/^\s*(```|~~~)/.test(line)) {
      fenced = !fenced
      return ''
    }
    return fenced || /^\s*>/.test(line) ? '' : line.replace(/`[^`]*`/g, ' ')
  })
  const blocks = paragraphs(lines, prose)
  return { lines, prose, paragraphs: blocks, quotes: blocks.filter((p) => /^\s*>/.test(p.raw)).length }
}

function paragraphs(lines, prose) {
  const list = []
  lines.forEach((line, i) => {
    if (!line.trim()) return
    if (i === 0 || !lines[i - 1].trim()) list.push({ line: i + 1, raw: '', prose: [] })
    list.at(-1).raw += line + '\n'
    list.at(-1).prose.push(prose[i])
  })
  return list
}

function matchLines(lines, pattern, message, firstLine = 1) {
  return lines.flatMap((line, i) => [...line.matchAll(pattern)].map((m) => ({ line: firstLine + i, message: message(m[0]) })))
}
