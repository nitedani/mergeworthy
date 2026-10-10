import assert from 'node:assert/strict'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { test } from 'node:test'
import { realCtx } from '../lib/ctx.mjs'
import { bashGates } from '../lib/gates.mjs'
import { stepCommand, stepsCommand } from '../lib/steps.mjs'
import { fakeCtx, ghResponses, sh, tempDir } from './helpers.mjs'

const { exec } = realCtx()

function clonedRepo() {
  const root = tempDir()
  sh(root, 'git init -q -b main upstream && cd upstream && echo one > a.txt && git add . && git commit -qm one && cd .. && git clone -q upstream work')
  return { upstream: join(root, 'upstream'), work: join(root, 'work'), root }
}

const gates = (command, cwd, ctx = fakeCtx({ exec })) => bashGates({ command, cwd }, ctx).map((f) => f.gate)

test('shared-git fires in a main worktree and stays silent in a linked one', () => {
  const { work, root } = clonedRepo()
  sh(work, `git worktree add -q ${root}/linked -b side`)
  assert.deepEqual(gates('git checkout -b other', work), ['shared-git'])
  assert.deepEqual(gates('git checkout -b other', join(root, 'linked')), [])
  assert.deepEqual(gates(`git -C ${root}/linked reset --hard`, work), [])
})

test('identity fires on a push of commits not authored by the gh user', () => {
  const { work } = clonedRepo()
  sh(work, 'echo two >> a.txt && git commit -qam two')
  const ctx = fakeCtx({ exec, gh: ghResponses({ 'api user': '7\nbot\n' }) })
  const [finding] = bashGates({ command: 'git push origin main', cwd: work }, ctx)
  assert.equal(finding.gate, 'identity')
  assert.match(finding.message, /authored by me@work\.example, not 7\+bot@users\.noreply\.github\.com/)
})

test('identity stays silent when the commits use the noreply address', () => {
  const { work } = clonedRepo()
  sh(work, 'echo two >> a.txt && GIT_AUTHOR_EMAIL=7+bot@users.noreply.github.com git commit -qam two')
  assert.deepEqual(gates('git push origin main', work, fakeCtx({ exec, gh: ghResponses({ 'api user': '7\nbot\n' }) })), [])
})

function recordedBranch() {
  const repo = clonedRepo()
  sh(repo.work, 'git checkout -qb fix && echo fix >> a.txt && git commit -qam fix')
  const ctx = fakeCtx({ exec, cwd: repo.work })
  const evidence = join(repo.root, 'gates.log')
  writeFileSync(evidence, 'all green\n')
  assert.equal(stepCommand(['gates', evidence, '--pr', 'https://github.com/o/r/pull/5'], ctx), 0)
  return { ...repo, ctx }
}

const statusOf = (ctx) => {
  ctx.output.length = 0
  stepsCommand([], ctx)
  return ctx.output
}

test('mw step records the local head, its diff id and the PR label', () => {
  const { ctx, work } = recordedBranch()
  const head = sh(work, 'git rev-parse HEAD')
  assert.deepEqual(statusOf(ctx), [`gates: ✓ on ${head.slice(0, 7)}`, 'verify: missing', 'quality: missing', 'review: missing'])
})

test('mw step refuses a missing or empty evidence file', () => {
  const ctx = fakeCtx({ exec, cwd: clonedRepo().work })
  assert.equal(stepCommand(['gates', 'nothing.log'], ctx), 1)
  assert.match(ctx.errors[0], /missing or empty/)
})

test('a step survives a merge that only brings in the base branch', () => {
  const { ctx, upstream, work } = recordedBranch()
  sh(upstream, 'echo base > b.txt && git add . && git commit -qm base')
  sh(work, 'git fetch -q && git merge -q --no-edit origin/main')
  assert.match(statusOf(ctx)[0], /^gates: ✓ on /)
})

test('a step on an older diff shows the lines changed in the PR since', () => {
  const { ctx, work } = recordedBranch()
  const recorded = sh(work, 'git rev-parse HEAD')
  sh(work, 'printf "x\\ny\\n" >> a.txt && git commit -qam more')
  assert.equal(statusOf(ctx)[0], `gates: older head ${recorded.slice(0, 7)} (+2 lines since)`)
})
