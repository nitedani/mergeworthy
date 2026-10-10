import { execFileSync, spawnSync } from 'node:child_process'
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join, resolve } from 'node:path'
import { after } from 'node:test'

export const ROOT = new URL('..', import.meta.url).pathname
export const NOW = Date.parse('2026-10-10T12:00:00Z')
const GIT_ENV = { ...process.env, GIT_CONFIG_GLOBAL: '/dev/null', GIT_CONFIG_NOSYSTEM: '1', GIT_AUTHOR_NAME: 'Me', GIT_AUTHOR_EMAIL: 'me@work.example', GIT_COMMITTER_NAME: 'Me', GIT_COMMITTER_EMAIL: 'me@work.example' }

export function tempDir() {
  const dir = mkdtempSync(join(tmpdir(), 'mw-test-'))
  after(() => rmSync(dir, { recursive: true, force: true }))
  return dir
}

export function fakeCtx(overrides = {}) {
  const ctx = {
    home: tempDir(),
    cwd: '/work',
    now: () => NOW,
    exec: () => ({ code: 1, stdout: '', stderr: 'not faked' }),
    gh: () => ({ code: 1, stdout: '', stderr: 'not faked' }),
    meminfo: () => ({ availableKiB: 16 * 2 ** 20, totalKiB: 32 * 2 ** 20 }),
    procs: () => [],
    sleep: async () => {},
    output: [],
    errors: [],
    out: (line) => ctx.output.push(line),
    err: (line) => ctx.errors.push(line),
    ...overrides,
  }
  return ctx
}

export function execResponses(table) {
  return (cmd, args) => respond(table, [cmd, ...args])
}

export function ghResponses(table) {
  return (args) => respond(table, args)
}

function respond(table, argv) {
  const key = Object.keys(table).find((pattern) => argv.join(' ').includes(pattern))
  return key === undefined ? { code: 1, stdout: '', stderr: 'no fake response' } : { code: 0, stdout: table[key], stderr: '' }
}

export function fakeGh(responses) {
  const dir = tempDir()
  writeFileSync(join(dir, 'responses.json'), JSON.stringify(responses))
  writeFileSync(join(dir, 'calls.jsonl'), '')
  return {
    env: { MW_GH: join(ROOT, 'test/fake-gh'), FAKE_GH_DIR: dir },
    calls: () => readFileSync(join(dir, 'calls.jsonl'), 'utf8').split('\n').filter(Boolean).map((line) => JSON.parse(line)),
  }
}

export function run(file, args, { env = {}, cwd = ROOT, input = '' } = {}) {
  const r = spawnSync(process.execPath, [resolve(ROOT, file), ...args], { cwd, input, encoding: 'utf8', env: { ...process.env, MW_HOME: tempDir(), ...env } })
  return { code: r.status, stdout: r.stdout, stderr: r.stderr }
}

export function sh(cwd, script) {
  return execFileSync('sh', ['-c', script], { cwd, env: GIT_ENV, encoding: 'utf8', stdio: ['ignore', 'pipe', 'pipe'] }).trim()
}
