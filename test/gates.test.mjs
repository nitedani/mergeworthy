import assert from 'node:assert/strict'
import { mkdirSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { test } from 'node:test'
import { agentGates, bashGates, recordAgent } from '../lib/gates.mjs'
import { readState, writeState } from '../lib/state.mjs'
import { DAY, MINUTE } from '../lib/time.mjs'
import { execResponses, fakeCtx, gateNames, ghResponses, NOW } from './helpers.mjs'

const BYPASS = '\n# --I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE: the user asked for exactly this'
const SHORT_BYPASS = '\n# --I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE: asked'
const HEAD = 'a'.repeat(40)
const OLD_HEAD = 'b'.repeat(40)
const BASE = 'c'.repeat(40)
const PR = 'https://github.com/o/r/pull/5'

const worktreeAt = (gitDir) => () => fakeCtx({ exec: execResponses({ 'rev-parse --path-format=absolute': `${gitDir}\n/work/.git\n` }) })
const mainWorktree = worktreeAt('/work/.git')
const linkedWorktree = worktreeAt('/work/.git/worktrees/x')
const prWithSteps = (steps) => {
  const ctx = fakeCtx({
    gh: ghResponses({ 'pr view': JSON.stringify({ headRefOid: HEAD, url: PR }) }),
    exec: execResponses({
      'symbolic-ref refs/remotes/origin/HEAD': 'refs/remotes/origin/main\n',
      'merge-base': `${BASE}\n`,
      [`diff ${BASE} ${OLD_HEAD}`]: '+old line\n',
      [`diff ${BASE} ${HEAD}`]: '+old line\n+new line\n-gone line\n',
    }),
  })
  mkdirSync(ctx.home, { recursive: true })
  writeFileSync(join(ctx.home, 'steps.jsonl'), steps.map(([step, head]) => JSON.stringify({ step, head, pr: PR }) + '\n').join(''))
  return ctx
}
const checkoutAt = () => fakeCtx({ exec: execResponses({ 'rev-parse HEAD': `${HEAD}\n`, 'rev-parse --abbrev-ref HEAD': 'fix-x\n' }) })
const pushOf = (authorEmail, config = { 'config user.email': 'me@work.example\n' }) =>
  fakeCtx({
    gh: ghResponses({ 'api user': '123\nbot\n' }),
    exec: execResponses({ ...config, '--format=%H %ae': `${HEAD} ${authorEmail}\n${OLD_HEAD} 123+bot@users.noreply.github.com\n` }),
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
      'gh api repos/o/r/issues/5/comments -F body=@reply.md',
      'gh pr close 5 --comment "Replaced by #6"',
      'gh issue close 5 -c "Fixed in #6"',
      "gh api repos/o/r/pulls/5/reviews -f event=COMMENT -f 'comments[][path]=src/a.js' -F 'comments[][line]=3' -f 'comments[][body]=This drops the cache key.'",
      'gh api repos/o/r/pulls/5 -X PATCH -f title="Fix the router"',
      'gh api repos/o/r/issues -f title=Bug',
      'gh api repos/o/r/releases -f tag_name=v1 -f name=v1',
    ],
    silent: [
      'gh pr close 5',
      'gh api repos/o/r/issues/5/labels -f labels[]=bug',
      'gh api repos/o/r/pulls/5/requested_reviewers -f reviewers[]=x',
      'gh api repos/o/r/issues/5 -X PATCH -f state=closed',
      'gh api repos/o/r/pulls/5/reviews -f event=APPROVE',
      'gh api repos/o/r/issues/comments/1/reactions -f content=eyes',
      'gh pr edit 5 --add-label bug --add-reviewer x',
      'gh api repos/o/r/issues/5/comments',
      `gh api graphql -f query='{ viewer { login } }'`,
      `gh api graphql -f query='mutation { addReaction(input: {subjectId: "x", content: EYES}) { clientMutationId } }'`,
      'gh pr view 5',
      'mw post b.md -- gh pr comment 5 --body-file b.md',
    ],
  },
  ready: {
    fires: [['gh pr ready 5', () => prWithSteps([])], ['gh pr ready 5 --undo=false', () => prWithSteps([])], ['mw post b.md -- gh pr create --title "Fix it" --body-file b.md', checkoutAt], ['mw post b.md -- gh pr create --draft=false --title "Fix it" --body-file b.md', checkoutAt]],
    silent: [
      ['gh pr ready 5', () => prWithSteps([['gates', HEAD], ['verify', HEAD], ['quality', HEAD], ['review', HEAD]])],
      ['gh pr ready 5 --undo', () => prWithSteps([])],
      ['gh pr create --draft --title t', () => prWithSteps([])],
      ['mw post b.md -- gh pr create --draft --title t --body-file b.md', checkoutAt],
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
      ['git push origin main', () => pushOf('maintainer@example.com')],
      ['git push origin --delete x', () => pushOf('me@work.example')],
      ['git push origin --tags', () => pushOf('me@work.example')],
      ['git push origin main', () => fakeCtx({ exec: pushOf('me@work.example').exec })],
      ['git push origin main', () => pushOf('me@work.example', {})],
      ['git push origin main', () => pushOf('123+bot@users.noreply.github.com', { 'config user.email': '123+bot@users.noreply.github.com\n' })],
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
    test(`${gate} fires on: ${command}`, () => assert.deepEqual(gateNames(command, { ctx: makeCtx() }), [gate]))
  }
  for (const [command, makeCtx] of cases(silent)) {
    test(`${gate} stays silent on: ${command}`, () => assert.ok(!gateNames(command, { ctx: makeCtx() }).includes(gate)))
  }
}

test('a block gate ignores the bypass', () => {
  assert.deepEqual(gateNames('pkill node' + BYPASS), ['kill-by-pattern'])
  assert.deepEqual(gateNames('git push -f' + BYPASS), ['force-push'])
})

for (const [gate, command, makeCtx] of [
  ['post', 'gh pr comment 5 --body hi', fakeCtx],
  ['ready', 'gh pr ready 5', () => prWithSteps([])],
  ['shared-git', 'git checkout main', mainWorktree],
  ['identity', 'git push origin main', () => pushOf('me@work.example')],
  ['foreground-wait', 'sleep 60', fakeCtx],
]) {
  test(`${gate} is bypassed by a reason of 3+ words`, () => assert.deepEqual(gateNames(command + BYPASS, { ctx: makeCtx() }), []))
  test(`${gate} is not bypassed by a shorter reason`, () => {
    const [finding] = bashGates({ command: command + SHORT_BYPASS, cwd: '/work' }, makeCtx())
    assert.equal(finding.gate, gate)
    assert.match(finding.message, /no reason of at least 3 words/)
  })
}

test('a warn message ends with the exact bypass line', () => {
  const [finding] = bashGates({ command: 'sleep 60', cwd: '/work' }, fakeCtx())
  assert.match(finding.message, /^mergeworthy stopped this command \(its foreground-wait check\): /)
  assert.match(finding.message, /\n# --I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE: <why this is right here>$/)
})

test('a block message says there is no bypass', () => {
  const [finding] = bashGates({ command: 'pkill x', cwd: '/work' }, fakeCtx())
  assert.match(finding.message, /^mergeworthy blocked this command \(its kill-by-pattern check\), and this check has no bypass: .*ps -o pid,ppid,cmd -p <pid>/)
})

test('a post message names the API path of a gh api call and the flag that reads the draft', () => {
  const [finding] = bashGates({ command: 'gh api -X PATCH repos/o/r/issues/comments/1 -f body=x', cwd: '/work' }, fakeCtx())
  assert.match(finding.message, /^mergeworthy stopped this command \(its post check\): `gh api repos\/o\/r\/issues\/comments\/1` posts to GitHub directly/)
  assert.match(finding.message, /`mw post <draft> -- <this gh command with -F body=@<draft>>`/)
})

const postAdvice = (command) => bashGates({ command, cwd: '/work' }, fakeCtx()).find((f) => f.gate === 'post').message.split('\n')[1]

for (const [command, advice] of [
  ['gh pr close --comment "superseded by #6" 5', '`mw post <draft> -- gh pr comment 5 --body-file <draft>`, which runs both checks first. Then close without --comment.'],
  ['gh pr close 5 -R vikejs/vike --comment "Replaced by #6"', '`mw post <draft> -- gh pr comment 5 -R vikejs/vike --body-file <draft>`, which runs both checks first. Then close without --comment.'],
  ['gh release create v1 --notes x', '`mw post <draft> -- <this gh command with --notes-file <draft>>`, which runs both checks first.'],
  ['gh gist create notes.md', '`mw post <draft> -- <this gh command>`, with the draft among the files it uploads, which runs both checks first.'],
  ['gh pr edit 5 --title "New title"', "mw post can't read a title from a draft file. Get the new title reviewed, then run this command again with the bypass line below."],
  ['gh api repos/o/r/pulls/5 -X PATCH -f title="Fix the router"', "mw post can't read a title from a draft file. Get the new title reviewed, then run this command again with the bypass line below."],
  ['gh pr edit 5 --title t --body-file b.md', '`mw post <draft> -- <this gh command with --body-file <draft>>`, which runs both checks first.'],
]) {
  test(`a post message gives advice that works for: ${command}`, () => assert.ok(postAdvice(command).endsWith(advice), postAdvice(command)))
}

test('a post message for a closing comment says to post it first, then close', () => {
  const [finding] = bashGates({ command: 'gh pr close 5 --comment "Replaced by #6"', cwd: '/work' }, fakeCtx())
  assert.match(finding.message, /`gh pr close` posts to GitHub directly/)
  assert.match(finding.message, /`mw post <draft> -- gh pr comment 5 --body-file <draft>`, which runs both checks first\. Then close without --comment\./)
})

test('ready lists the steps recorded on an older head, with lines changed since', () => {
  const [finding] = bashGates({ command: 'gh pr ready 5', cwd: '/work' }, prWithSteps([['gates', OLD_HEAD], ['verify', HEAD]]))
  assert.match(finding.message, /has no record of these required steps: gates, quality, review/)
  assert.match(finding.message, /gates was done only on an older commit, bbbbbbb, and 2 lines of the PR's changes differ since then/)
})

test('ready checks the checkout head for gh pr create without --draft', () => {
  const [finding] = bashGates({ command: 'gh pr create --title t --body-file b.md', cwd: '/work' }, checkoutAt()).filter((f) => f.gate === 'ready')
  assert.match(finding.message, /`gh pr create` makes fix-x ready for review, but its latest commit, aaaaaaa, has no record of these required steps: gates, verify, quality, review/)
})

test('foreground-wait stays silent when the command runs in the background', () => {
  assert.deepEqual(gateNames('sleep 60', { runInBackground: true }), [])
})

const SESSION = 'session-a'
const agentNames = (input, ctx, session = SESSION) => agentGates({ input, session }, ctx).map((f) => f.gate)
const withState = (files, overrides) => {
  const ctx = fakeCtx(overrides)
  for (const [name, value] of Object.entries(files)) writeState(ctx, name, value)
  return ctx
}
const firstUsed = (minutes) => () => withState({ 'request-ids.json': { 'req-1': NOW - minutes * MINUTE } })
const started = (ms, tool = 'Agent') => () => withState({ 'agents.json': { [`${SESSION}/review pr 5`]: { at: NOW - ms, tool } } })
const claude = (pid, rssKiB = 2 ** 20) => ({ pid, comm: 'claude', ageSec: 3700, cpuPct: 12, rssKiB })
const lowMemory = () => fakeCtx({ meminfo: () => ({ availableKiB: 2 * 2 ** 20 }), procs: () => [claude(11), claude(22, 3 * 2 ** 20), { pid: 33, comm: 'bash', rssKiB: 9e9 }] })
const claudes = (count) => () => fakeCtx({ procs: () => Array.from({ length: count }, (_, i) => claude(i + 1)) })

const AGENT_CASES = {
  'reused-request-id': {
    fires: [
      { when: 'on an id first used 11 minutes ago', input: { clientRequestId: 'req-1' }, ctx: firstUsed(11) },
      { when: 'on a reused id even with a bypass line', input: { clientRequestId: 'req-1', task: 'x' + BYPASS }, ctx: firstUsed(11) },
    ],
    silent: [
      { when: 'on a retry within 10 minutes', input: { clientRequestId: 'req-1' }, ctx: firstUsed(5) },
      { when: 'on a new id', input: { clientRequestId: 'req-2' }, ctx: firstUsed(11) },
    ],
  },
  'agent-dedupe': {
    fires: [{ when: 'on a title registered 30 minutes ago', input: { description: ' Review PR 5 ' }, ctx: started(30 * MINUTE) }],
    silent: [
      { when: 'on a title registered over 24 hours ago', input: { description: 'Review PR 5' }, ctx: started(DAY + 60 * MINUTE) },
      { when: 'on a different title', input: { title: 'review pr 6' }, ctx: started(30 * MINUTE) },
    ],
  },
  'agent-load': {
    fires: [
      { when: 'when free memory is under the floor', input: {}, ctx: lowMemory },
      { when: 'at the agent cap', input: {}, ctx: claudes(8) },
    ],
    silent: [
      { when: 'under both limits', input: {}, ctx: claudes(1) },
      { when: 'when config.json lowers the floor', input: {}, ctx: () => withState({ 'config.json': { minFreeGiB: 1 } }, { meminfo: () => ({ availableKiB: 2 * 2 ** 20 }) }) },
    ],
  },
}

for (const [gate, { fires, silent }] of Object.entries(AGENT_CASES)) {
  for (const { when, input, ctx } of fires) test(`${gate} fires ${when}`, () => assert.deepEqual(agentNames(input, ctx()), [gate]))
  for (const { when, input, ctx } of silent) test(`${gate} stays silent ${when}`, () => assert.deepEqual(agentNames(input, ctx()), []))
}

for (const { gate, input, ctx } of [
  { gate: 'agent-dedupe', input: { description: 'Review PR 5' }, ctx: started(30 * MINUTE) },
  { gate: 'agent-load', input: {}, ctx: lowMemory },
]) {
  test(`${gate} is bypassed by a reason of 3+ words in the prompt`, () => assert.deepEqual(agentNames({ ...input, prompt: 'go' + BYPASS }, ctx()), []))
  test(`${gate} is not bypassed by a shorter reason in the task`, () => {
    const [finding] = agentGates({ input: { ...input, task: 'go' + SHORT_BYPASS }, session: SESSION }, ctx())
    assert.equal(finding.gate, gate)
    assert.match(finding.message, /no reason of at least 3 words/)
  })
}

test('an agent-dedupe message says how long ago the agent started and where the bypass goes', () => {
  const [finding] = agentGates({ input: { description: 'Review PR 5' }, session: SESSION }, started(30 * MINUTE)())
  assert.match(finding.message, /started in this session 30 min ago/)
  assert.match(finding.message, /add this line to the agent prompt/)
})

test('an agent-load message gives the numbers and the largest agents', () => {
  const [finding] = agentGates({ input: {} }, lowMemory())
  assert.match(finding.message, /2\.0 GiB of memory is free .* 2 claude\/codex processes/)
  assert.match(finding.message, /The largest: pid 22 \(claude, 1h 1m, 12% cpu, 3\.0 GiB\); pid 11/)
})

for (const [tool, advice] of [
  ['Agent', 'Continue that agent instead, with SendMessage. A new review round gets its own title, like "… round 2". If the old agent died'],
  ['Task', 'Continue that agent instead, with SendMessage.'],
  ['mcp__t3-code__delegate_task', 'Check that task instead, with `task_status` on the taskId its `delegate_task` call returned. A new review round is a new `delegate_task` call with a new title, like "… round 2". If the old agent died'],
]) {
  test(`an agent-dedupe message says how to continue an agent that ${tool} started`, () => {
    const [finding] = agentGates({ input: { description: 'Review PR 5' }, session: SESSION }, started(30 * MINUTE, tool)())
    assert.ok(finding.message.includes(advice), finding.message)
    assert.doesNotMatch(finding.message, /t3_thread_send/)
  })
}

test('agent-dedupe stays silent on a title that another session started', () => {
  assert.deepEqual(agentNames({ description: 'Review PR 5' }, started(30 * MINUTE)(), 'session-b'), [])
})

test('recordAgent registers the title under the session and keeps the first sighting of a request id', () => {
  const ctx = withState({ 'request-ids.json': { 'req-1': NOW - MINUTE, stale: NOW - 8 * DAY } })
  recordAgent({ toolName: 'mcp__t3__delegate_task', input: { title: 'Fix X', clientRequestId: 'req-1' }, session: SESSION }, ctx)
  assert.deepEqual(readState(ctx, 'agents.json'), { 'session-a/fix x': { at: NOW, tool: 'mcp__t3__delegate_task' } })
  assert.deepEqual(readState(ctx, 'request-ids.json'), { 'req-1': NOW - MINUTE })
})
