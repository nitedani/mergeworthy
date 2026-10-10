import assert from 'node:assert/strict'
import { writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { test } from 'node:test'
import { realCtx } from '../lib/ctx.mjs'
import { bashGates } from '../lib/gates.mjs'
import { stepCommand, stepsCommand } from '../lib/steps.mjs'
import { fakeCtx, gateNames, ghResponses, sh, tempDir } from './helpers.mjs'

const { exec } = realCtx()
const NOREPLY = '7+bot@users.noreply.github.com'
const MAINTAINER = 'maintainer@example.com'
const AS_MAINTAINER = `GIT_AUTHOR_EMAIL=${MAINTAINER} GIT_COMMITTER_EMAIL=${MAINTAINER}`
const asBot = () => fakeCtx({ exec, gh: ghResponses({ 'api user': '7\nbot\n' }) })

function clonedRepo() {
  const root = tempDir()
  sh(root, 'git init -q -b main upstream && cd upstream && echo one > a.txt && git add . && git commit -qm one && cd .. && git clone -q upstream work')
  return { upstream: join(root, 'upstream'), work: join(root, 'work'), root }
}

test('shared-git fires in a main worktree and stays silent in a linked one', () => {
  const { work, root } = clonedRepo()
  sh(work, `git worktree add -q ${root}/linked -b side`)
  const inDir = (cwd) => ({ cwd, ctx: fakeCtx({ exec }) })
  assert.deepEqual(gateNames('git checkout -b other', inDir(work)), ['shared-git'])
  assert.deepEqual(gateNames('git checkout -b other', inDir(join(root, 'linked'))), [])
  assert.deepEqual(gateNames(`git -C ${root}/linked reset --hard`, inDir(work)), [])
})

test('identity stays silent on a maintainer commit we rebased', () => {
  const { work } = clonedRepo()
  sh(work, `git config user.email me@work.example && echo two >> a.txt && GIT_AUTHOR_EMAIL=${MAINTAINER} git commit -qam two`)
  assert.deepEqual(gateNames('git push origin main', { cwd: work, ctx: asBot() }), [])
})

test("identity fires on our commit with the machine's identity, and its rewrite skips the maintainer's", () => {
  const { work } = clonedRepo()
  sh(work, `git config user.email me@work.example && echo ours >> a.txt && git commit -qam ours && echo theirs >> a.txt && GIT_AUTHOR_EMAIL=${MAINTAINER} git commit -qam theirs`)
  const [finding] = bashGates({ command: 'git push origin main', cwd: work }, asBot())
  assert.equal(finding.gate, 'identity')
  assert.match(finding.message, /1 commit\(s\) you are pushing have me@work\.example as author/)
  sh(work, `unset GIT_AUTHOR_NAME GIT_AUTHOR_EMAIL GIT_COMMITTER_NAME GIT_COMMITTER_EMAIL; ${/`(git -c user\.name=bot .*)`/.exec(finding.message)[1]}`)
  assert.equal(sh(work, 'git log -2 --format=%ae'), `${MAINTAINER}\n${NOREPLY}`)
})

test('identity stays silent on a maintainer commit the fork branch already has, fetched and pushed by URL', () => {
  const { work, root } = clonedRepo()
  sh(root, 'git clone -q --bare upstream fork.git')
  sh(work, `git config user.email me@work.example && git checkout -qb fix && echo fix >> a.txt && GIT_AUTHOR_EMAIL=${NOREPLY} git commit -qam fix && git push -q ../fork.git HEAD:fix`)
  sh(root, `git clone -q -b fix fork.git maintainer && cd maintainer && echo polish >> a.txt && ${AS_MAINTAINER} git commit -qam polish && git push -q origin fix`)
  sh(work, `git fetch -q ../fork.git fix && git rebase -q FETCH_HEAD && echo more >> a.txt && GIT_AUTHOR_EMAIL=${NOREPLY} git commit -qam more`)
  assert.deepEqual(gateNames('git push ../fork.git HEAD:fix', { cwd: work, ctx: asBot() }), [])
})

test('identity stays silent when the commits use the noreply address', () => {
  const { work } = clonedRepo()
  sh(work, `echo two >> a.txt && GIT_AUTHOR_EMAIL=${NOREPLY} git commit -qam two`)
  assert.deepEqual(gateNames('git push origin main', { cwd: work, ctx: asBot() }), [])
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
  assert.deepEqual(statusOf(ctx), [`gates: ✓ done on ${head.slice(0, 7)}`, 'verify: missing', 'quality: missing', 'review: missing'])
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
  assert.match(statusOf(ctx)[0], /^gates: ✓ done on /)
})

test("a maintainer's commits on a recorded commit carry its record", () => {
  const { ctx, work } = recordedBranch()
  sh(work, 'printf "x\\n" >> a.txt && git commit -qam "maintainer tweak"')
  assert.match(statusOf(ctx)[0], /^gates: ✓ done on /)
})

test('a step on an older diff shows the lines changed in the PR since', () => {
  const { ctx, work } = recordedBranch()
  const recorded = sh(work, 'git rev-parse HEAD')
  sh(work, 'printf "x\\ny\\n" >> a.txt && git commit -qam more -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"')
  assert.equal(statusOf(ctx)[0], `gates: done only on an older commit, ${recorded.slice(0, 7)}, and 2 lines of the PR's changes differ since then`)
})
