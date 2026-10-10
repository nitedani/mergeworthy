import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { test } from 'node:test'
import { agentGates, bashGates, recordAgent } from '../lib/gates.mjs'
import { readState, writeState } from '../lib/state.mjs'
import { execResponses, fakeCtx, ghResponses, NOW } from './helpers.mjs'

const BYPASS = '\n# --I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE: the user asked for exactly this'
const SHORT_BYPASS = '\n# --I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE: asked'
const HEAD = 'a'.repeat(40)
const OLD_HEAD = 'b'.repeat(40)
const PR = 'https://github.com/o/r/pull/5'

const firing = (command, ctx = fakeCtx(), options = {}) => bashGates({ command, cwd: '/work', ...options }, ctx).map((f) => f.gate)

const mainWorktree = () => fakeCtx({ exec: execResponses({ 'rev-parse --path-format=absolute': '/work/.git\n/work/.git\n' }) })
const linkedWorktree = () => fakeCtx({ exec: execResponses({ 'rev-parse --path-format=absolute': '/work/.git/worktrees/x\n/work/.git\n' }) })
const prWithSteps = (steps) => {
  const ctx = fakeCtx({
    gh: ghResponses({ 'pr view': JSON.stringify({ headRefOid: HEAD, url: PR }) }),
    exec: execResponses({ 'diff --shortstat': ' 2 files changed, 10 insertions(+), 2 deletions(-)\n' }),
  })
  mkdirSync(ctx.home, { recursive: true })
  writeFileSync(join(ctx.home, 'steps.jsonl'), steps.map(([step, head]) => JSON.stringify({ step, head, pr: PR }) + '\n').join(''))
  return ctx
}
const pushOf = (authorEmail) =>
  fakeCtx({
    gh: ghResponses({ 'api user': '123\nbot\n' }),
    exec: execResponses({ 'log --format': `${HEAD} ${authorEmail}\n${OLD_HEAD} 123+bot@users.noreply.github.com\n` }),
  })

const CASES = {
  'kill-by-pattern': {
    fires: ['pkill -f vite', 'killall node', 'sudo pkill x', 'kill $(pgrep -f vite)', 'kill -9 `pgrep x`', 'pgrep -f vite | xargs kill', 'pgrep x | grep -v y | xargs -r kill -9', 'kill -1', 'kill -9 -1', 'kill 0'],
    silent: ['kill 12345', 'kill -9 4242', 'kill -1 4242', 'pgrep -f vite', 'echo pkill', 'cat <<EOF\npkill node\nEOF'],
  },
  'force-push': {
    fires: ['git push -f', 'git push --force origin main', 'git push -fu origin x', 'git push origin +main', 'git -C /x push --force'],
    silent: ['git push origin main', 'git push -u origin x', 'git push --force-with-lease', 'git push --force --force-with-lease=main:abc'],
  },
  post: {
    fires: [
      'gh pr comment 5 --body hi',
      'gh pr review 5 --approve',
      'gh issue comment 5 -b x',
      'gh -R o/r issue create --title t',
      'gh pr edit 5 --body-file notes.md',
      'gh issue edit 5 -t "new title"',
      'gh release create v1',
      'gh gist edit 1',
      'gh api repos/o/r/issues/5/comments -f body=x',
      'gh api -X PATCH repos/o/r/issues/comments/1 -f body=x',
      'gh api --method=POST repos/o/r/pulls/5/reviews --input review.json',
      `gh api graphql -f query='mutation { addComment(input: {subjectId: "x", body: "y"}) { clientMutationId } }'`,
    ],
    silent: [
      'gh api repos/o/r/issues/comments/1/reactions -f content=eyes',
      'gh pr edit 5 --add-label bug --add-reviewer x',
      'gh api repos/o/r/issues/5/comments',
      `gh api graphql -f query='{ viewer { login } }'`,
      `gh api graphql -f query='mutation { addReaction(input: {subjectId: "x", content: EYES}) { clientMutationId } }'`,
      'gh pr view 5',
    ],
  },
  ready: {
    fires: [['gh pr ready 5', () => prWithSteps([])]],
    silent: [
      ['gh pr ready 5', () => prWithSteps([['gates', HEAD], ['verify', HEAD], ['quality', HEAD], ['review', HEAD]])],
      ['gh pr ready 5 --undo', () => prWithSteps([])],
      ['gh pr create --draft --title t', () => prWithSteps([])],
      ['gh pr ready 5', () => fakeCtx()],
    ],
  },
  'shared-git': {
    fires: [...['git checkout main', 'git checkout -- f', 'git switch -c x', 'git reset --hard', 'git clean -fd', 'git restore f', 'git restore --staged --worktree f'].map((c) => [c, mainWorktree]), ['git stash', linkedWorktree], ['git stash pop', linkedWorktree]],
    silent: [...['git checkout -p', 'git reset --soft HEAD~1', 'git clean -n', 'git restore --staged f', 'git stash list', 'git stash show -p'].map((c) => [c, mainWorktree]), ['git checkout main', linkedWorktree]],
  },
  identity: {
    fires: [['git push origin main', () => pushOf('me@work.example')]],
    silent: [
      ['git push origin main', () => pushOf('123+bot@users.noreply.github.com')],
      ['git push origin --delete x', () => pushOf('me@work.example')],
      ['git push origin --tags', () => pushOf('me@work.example')],
      ['git push origin main', () => fakeCtx({ exec: pushOf('me@work.example').exec })],
    ],
  },
  'foreground-wait': {
    fires: ['sleep 30', 'sleep 1m', 'timeout 2h sleep 0.5h', 'while true; do sleep 1; done', 'until curl -s x; do sleep 2; done'],
    silent: ['sleep 29', 'sleep 60 &', 'for i in 1 2; do sleep 1; done', 'sleep $DELAY'],
  },
}

for (const [gate, { fires, silent }] of Object.entries(CASES)) {
  const cases = (list) => list.map((c) => (Array.isArray(c) ? c : [c, fakeCtx]))
  for (const [command, makeCtx] of cases(fires)) {
    test(`${gate} fires on: ${command}`, () => assert.deepEqual(firing(command, makeCtx()), [gate]))
  }
  for (const [command, makeCtx] of cases(silent)) {
    test(`${gate} stays silent on: ${command}`, () => assert.ok(!firing(command, makeCtx()).includes(gate)))
  }
}

test('a block gate ignores the bypass', () => {
  assert.deepEqual(firing('pkill node' + BYPASS), ['kill-by-pattern'])
  assert.deepEqual(firing('git push -f' + BYPASS), ['force-push'])
})

for (const [gate, command, makeCtx] of [
  ['post', 'gh pr comment 5 --body hi', fakeCtx],
  ['ready', 'gh pr ready 5', () => prWithSteps([])],
  ['shared-git', 'git checkout main', mainWorktree],
  ['identity', 'git push origin main', () => pushOf('me@work.example')],
  ['foreground-wait', 'sleep 60', fakeCtx],
]) {
  test(`${gate} is bypassed by a reason of 3+ words`, () => assert.deepEqual(firing(command + BYPASS, makeCtx()), []))
  test(`${gate} is not bypassed by a shorter reason`, () => {
    const [finding] = bashGates({ command: command + SHORT_BYPASS, cwd: '/work' }, makeCtx())
    assert.equal(finding.gate, gate)
    assert.match(finding.message, /missing its reason/)
  })
}

test('a warn message ends with the exact bypass line', () => {
  const [finding] = bashGates({ command: 'sleep 60', cwd: '/work' }, fakeCtx())
  assert.match(finding.message, /^mergeworthy foreground-wait: /)
  assert.match(finding.message, /\n# --I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE: <why this is right here>$/)
})

test('a block message says there is no bypass', () => {
  const [finding] = bashGates({ command: 'pkill x', cwd: '/work' }, fakeCtx())
  assert.match(finding.message, /^mergeworthy kill-by-pattern \(blocked, no bypass\): .*ps -o pid,ppid,cmd -p <pid>/)
})

test('ready lists the steps recorded on an older head, with lines changed since', () => {
  const [finding] = bashGates({ command: 'gh pr ready 5', cwd: '/work' }, prWithSteps([['gates', OLD_HEAD], ['verify', HEAD]]))
  assert.match(finding.message, /has no gates, quality, review step on this head/)
  assert.match(finding.message, /gates is recorded on an older head bbbbbbb \(\+12 lines since\)/)
})

test('ready checks the checkout head for gh pr create without --draft', () => {
  const ctx = fakeCtx({ exec: execResponses({ 'rev-parse HEAD': `${HEAD}\n`, 'rev-parse --abbrev-ref HEAD': 'fix-x\n' }) })
  const [finding] = bashGates({ command: 'gh pr create --title t --body-file b.md', cwd: '/work' }, ctx).filter((f) => f.gate === 'ready')
  assert.match(finding.message, /aaaaaaa of fix-x has no gates, verify, quality, review step/)
})

test('foreground-wait stays silent when the command runs in the background', () => {
  assert.deepEqual(firing('sleep 60', fakeCtx(), { runInBackground: true }), [])
})

const agentFiring = (input, ctx) => agentGates({ input }, ctx).map((f) => f.gate)
const withState = (files, overrides) => {
  const ctx = fakeCtx(overrides)
  for (const [name, value] of Object.entries(files)) writeState(ctx, name, value)
  return ctx
}
const MIN = 60_000

test('reused-request-id blocks an id first seen over 10 minutes ago, bypass or not', () => {
  const ctx = withState({ 'request-ids.json': { 'req-1': NOW - 11 * MIN } })
  assert.deepEqual(agentFiring({ clientRequestId: 'req-1', task: 'x' + BYPASS }, ctx), ['reused-request-id'])
})

test('reused-request-id allows a retry within 10 minutes and a new id', () => {
  const ctx = withState({ 'request-ids.json': { 'req-1': NOW - 5 * MIN } })
  assert.deepEqual(agentFiring({ clientRequestId: 'req-1' }, ctx), [])
  assert.deepEqual(agentFiring({ clientRequestId: 'req-2' }, ctx), [])
})

test('agent-dedupe fires on a title registered under 24 hours ago', () => {
  const ctx = withState({ 'agents.json': { 'review pr 5': { at: NOW - 30 * MIN, tool: 'Agent' } } })
  const [finding] = agentGates({ input: { description: ' Review PR 5 ' } }, ctx)
  assert.equal(finding.gate, 'agent-dedupe')
  assert.match(finding.message, /started 30 min ago/)
  assert.match(finding.message, /add this line to the prompt/)
})

test('agent-dedupe stays silent on an older or different title', () => {
  const ctx = withState({ 'agents.json': { 'review pr 5': { at: NOW - 25 * 60 * MIN } } })
  assert.deepEqual(agentFiring({ description: 'Review PR 5' }, ctx), [])
  assert.deepEqual(agentFiring({ title: 'review pr 6' }, ctx), [])
})

test('agent-dedupe is bypassed only by a reason of 3+ words in the prompt', () => {
  const ctx = withState({ 'agents.json': { 'review pr 5': { at: NOW - 30 * MIN } } })
  assert.deepEqual(agentFiring({ description: 'Review PR 5', prompt: 'go' + BYPASS }, ctx), [])
  assert.deepEqual(agentFiring({ description: 'Review PR 5', prompt: 'go' + SHORT_BYPASS }, ctx), ['agent-dedupe'])
})

const claude = (pid, rssKiB = 2 ** 20) => ({ pid, comm: 'claude', ageSec: 3700, cpuPct: 12, rssKiB })

test('agent-load fires when free memory is under the floor, naming the largest agents', () => {
  const ctx = fakeCtx({ meminfo: () => ({ availableKiB: 2 * 2 ** 20 }), procs: () => [claude(11), claude(22, 3 * 2 ** 20), { pid: 33, comm: 'bash', rssKiB: 9e9 }] })
  const [finding] = agentGates({ input: {} }, ctx)
  assert.equal(finding.gate, 'agent-load')
  assert.match(finding.message, /2\.0 GiB of memory is available .* 2 claude\/codex processes/)
  assert.match(finding.message, /The largest: pid 22 \(claude, 1h 1m, 12% cpu, 3\.0 GiB\); pid 11/)
})

test('agent-load fires at the agent cap', () => {
  const ctx = fakeCtx({ procs: () => Array.from({ length: 8 }, (_, i) => claude(i + 1)) })
  assert.deepEqual(agentFiring({}, ctx), ['agent-load'])
})

test('agent-load stays silent under the limits and honors config.json', () => {
  assert.deepEqual(agentFiring({}, fakeCtx({ procs: () => [claude(1)] })), [])
  const ctx = withState({ 'config.json': { minFreeGiB: 1 } }, { meminfo: () => ({ availableKiB: 2 * 2 ** 20 }) })
  assert.deepEqual(agentFiring({}, ctx), [])
})

test('recordAgent registers the title and keeps the first sighting of a request id', () => {
  const ctx = withState({ 'request-ids.json': { 'req-1': NOW - MIN, stale: NOW - 8 * 24 * 60 * MIN } })
  recordAgent({ toolName: 'mcp__t3__delegate_task', input: { title: 'Fix X', clientRequestId: 'req-1' } }, ctx)
  assert.deepEqual(readState(ctx, 'agents.json'), { 'fix x': { at: NOW, tool: 'mcp__t3__delegate_task' } })
  assert.deepEqual(readState(ctx, 'request-ids.json'), { 'req-1': NOW - MIN })
})
