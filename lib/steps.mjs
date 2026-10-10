import { appendFileSync, mkdirSync, readFileSync, statSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { parseArgs } from 'node:util'
import { git, mergeBase } from './git.mjs'
import { ghJson, parseRef } from './github.mjs'

export const REQUIRED_STEPS = ['gates', 'verify', 'quality', 'review']

export function stepCommand(argv, ctx) {
  const { positionals, values } = parseArgs({ args: argv, allowPositionals: true, options: { pr: { type: 'string' } } })
  const [step, evidence] = positionals
  if (!REQUIRED_STEPS.includes(step) || !evidence) return 2
  const file = resolve(ctx.cwd, evidence)
  if (!nonEmpty(file)) {
    ctx.err(`mw step: the evidence file ${file} is missing or empty`)
    return 1
  }
  const { head, branch } = checkoutHead(ctx, ctx.cwd)
  if (!head) {
    ctx.err(`mw step: ${ctx.cwd} is not a git checkout`)
    return 1
  }
  appendStep(ctx, {
    step,
    head,
    diffId: diffId(ctx, ctx.cwd, head),
    pr: values.pr ?? null,
    branch,
    evidence: file,
    at: new Date(ctx.now()).toISOString(),
  })
  ctx.out(`recorded ${step} on ${head.slice(0, 7)}`)
  return 0
}

export function stepsCommand(argv, ctx) {
  const { values } = parseArgs({ args: argv, options: { pr: { type: 'string' } } })
  const target = values.pr ? prHead(ctx, values.pr) : checkoutHead(ctx, ctx.cwd)
  if (!target.head) {
    ctx.err('mw steps: could not find the head commit')
    return 1
  }
  for (const s of checkSteps(ctx, ctx.cwd, target)) ctx.out(`${s.step}: ${describeStep(s, target.head)}`)
  return 0
}

export function prHead(ctx, pr, { repo, cwd } = {}) {
  const view = ghJson(ctx, ['pr', 'view', ...(pr ? [pr] : []), ...(repo ? ['-R', repo] : []), '--json', 'headRefOid,headRefName,url'], { cwd })
  return { head: view.headRefOid, pr: view.url, branch: view.headRefName }
}

export function checkoutHead(ctx, cwd) {
  return { head: git(ctx, cwd, ['rev-parse', 'HEAD']), pr: null, branch: git(ctx, cwd, ['rev-parse', '--abbrev-ref', 'HEAD']) }
}

export function checkSteps(ctx, cwd, target) {
  const records = readSteps(ctx)
  const current = git(ctx, cwd, ['rev-parse', 'HEAD']) === target.head ? diffId(ctx, cwd, target.head) : null
  return REQUIRED_STEPS.map((step) => {
    const mine = records.filter((r) => r.step === step)
    if (mine.some((r) => r.head === target.head || (current && r.diffId === current))) return { step, state: 'done' }
    const older = mine.filter((r) => (target.pr && samePr(r.pr, target.pr)) || (target.branch && r.branch === target.branch)).at(-1)
    return older ? { step, state: 'older', head: older.head, lines: linesSince(ctx, cwd, older.head, target.head) } : { step, state: 'missing' }
  })
}

export function describeStep(s, head) {
  if (s.state === 'done') return `✓ on ${head.slice(0, 7)}`
  if (s.state === 'missing') return 'missing'
  return `older head ${s.head.slice(0, 7)}${s.lines === null ? '' : ` (+${s.lines} lines since)`}`
}

function nonEmpty(file) {
  try {
    return statSync(file).size > 0
  } catch {
    return false
  }
}

function diffId(ctx, cwd, head) {
  const base = mergeBase(ctx, cwd, head)
  if (!base) return null
  const r = ctx.exec('sh', ['-c', 'git diff "$1" "$2" | git patch-id --stable', '_', base, head], { cwd })
  return (r.code === 0 && r.stdout.split(' ')[0]) || null
}

function readSteps(ctx) {
  try {
    return readFileSync(join(ctx.home, 'steps.jsonl'), 'utf8')
      .split('\n')
      .filter(Boolean)
      .map((line) => JSON.parse(line))
  } catch {
    return []
  }
}

function appendStep(ctx, record) {
  mkdirSync(ctx.home, { recursive: true })
  appendFileSync(join(ctx.home, 'steps.jsonl'), JSON.stringify(record) + '\n')
}

function samePr(a, b) {
  const [x, y] = [a, b].map((url) => url && parseRef(url))
  return Boolean(x && y && `${x.owner}/${x.repo}#${x.number}`.toLowerCase() === `${y.owner}/${y.repo}#${y.number}`.toLowerCase())
}

function linesSince(ctx, cwd, old, head) {
  const [before, after] = [old, head].map((rev) => changedLines(ctx, cwd, rev))
  return before && after ? symmetricDifference(before, after) : null
}

function changedLines(ctx, cwd, rev) {
  const base = mergeBase(ctx, cwd, rev)
  const diff = base && git(ctx, cwd, ['diff', base, rev])
  return typeof diff === 'string' ? diff.split('\n').filter((line) => /^[+-](?![+-]{2} )/.test(line)) : null
}

function symmetricDifference(before, after) {
  const counts = new Map()
  for (const line of before) counts.set(line, (counts.get(line) ?? 0) + 1)
  for (const line of after) counts.set(line, (counts.get(line) ?? 0) - 1)
  return [...counts.values()].reduce((sum, n) => sum + Math.abs(n), 0)
}
