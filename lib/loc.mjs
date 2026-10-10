import { readFileSync } from 'node:fs'
import { parseArgs } from 'node:util'
import { diffBase, git, TEST_FILE } from './git.mjs'

const LOCKFILE = /(^|\/)(package-lock\.json|pnpm-lock\.yaml|yarn\.lock|[^/]*\.lock)$/
const DOCS = /\.mdx?$|(^|\/)docs\//

export function locCommand(argv, ctx) {
  const { positionals, values } = parseArgs({ args: argv, allowPositionals: true, options: { map: { type: 'string' } } })
  const numstat = git(ctx, ctx.cwd, ['diff', '--numstat', `${diffBase(ctx, positionals[0])}...HEAD`])
  if (numstat === null) throw new Error('git diff failed')
  ctx.out(locTable(numstat, values.map ? parseMap(readFileSync(values.map, 'utf8')) : []))
  return 0
}

export function locTable(numstat, map) {
  const features = new Map()
  const tests = { added: 0, deleted: 0 }
  const docs = { added: 0, deleted: 0, files: 0 }
  for (const change of parseNumstat(numstat).filter((c) => !LOCKFILE.test(c.path))) {
    const row = TEST_FILE.test(change.path) ? tests : DOCS.test(change.path) ? docs : featureRow(features, map, change.path)
    row.added += change.added
    row.deleted += change.deleted
    if (row === docs) docs.files++
  }
  return [
    '| Feature | + | − |',
    '|---|---|---|',
    ...[...features].map(([name, row]) => `| ${name} | ${row.added} | ${row.deleted} |`),
    `| Tests | ${tests.added} | ${tests.deleted} |`,
    `| Docs (${docs.files} files) | ${docs.added} | ${docs.deleted} |`,
  ].join('\n')
}

function featureRow(features, map, path) {
  const name = map.find((entry) => entry.pattern.test(path))?.feature ?? '(unmapped)'
  if (!features.has(name)) features.set(name, { added: 0, deleted: 0 })
  return features.get(name)
}

function parseNumstat(numstat) {
  return numstat
    .split('\n')
    .filter(Boolean)
    .map((row) => {
      const [added, deleted, path] = row.split('\t')
      return { added: Number(added) || 0, deleted: Number(deleted) || 0, path: path.replace(/\{[^{}]* => ([^{}]*)\}/, '$1').replace(/^.* => /, '').replace('//', '/') }
    })
}

export function parseMap(text) {
  return text
    .split('\n')
    .map((line) => /^\s*([^#=\s][^=]*?)\s*=\s*(.+?)\s*$/.exec(line))
    .filter(Boolean)
    .map(([, glob, feature]) => ({ pattern: globPattern(glob), feature }))
}

function globPattern(glob) {
  const wildcards = { '**/': '(?:.*/)?', '**': '.*', '*': '[^/]*', '?': '[^/]' }
  const source = glob.replace(/[.+^${}()|[\]\\]/g, '\\$&').replace(/\*\*\/|\*\*|\*|\?/g, (w) => wildcards[w])
  return new RegExp(`^${source}$`)
}
