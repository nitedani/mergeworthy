import assert from 'node:assert/strict'
import { test } from 'node:test'
import { parseRef } from '../lib/github.mjs'
import { writeState } from '../lib/state.mjs'
import { diffPoll, watchCommand } from '../lib/watch.mjs'
import { BADGE, fakeCtx, NOW } from './helpers.mjs'

const LOGIN = 'bot'
const PR_URL = 'https://github.com/o/r/pull/5'
const REFS = [parseRef('o/r#5')]
const BEFORE = '2026-10-10T10:00:00Z'
const AFTER = '2026-10-10T11:00:00Z'

const comment = (author, at, body, reactions = []) => ({ author: { login: author }, createdAt: at, url: `${PR_URL}#issuecomment-${author}`, body, reactions: { nodes: reactions } })
const reaction = (login, content, at = AFTER) => ({ content, createdAt: at, user: { login } })
const check = (name, conclusion) => ({ __typename: 'CheckRun', name, conclusion, detailsUrl: `https://ci/${name}` })
const pr = ({ comments = [], checks = [], head = 'a'.repeat(40), pusher = LOGIN, ...fields } = {}) => ({
  url: PR_URL,
  state: 'OPEN',
  mergeable: 'MERGEABLE',
  headRefOid: head,
  comments: { nodes: [comment('alice', BEFORE, 'first'), ...comments] },
  reviews: { nodes: [] },
  reviewThreads: { nodes: [] },
  commits: { nodes: [{ commit: { messageHeadline: 'Fix the thing', author: { name: pusher, user: { login: pusher } }, statusCheckRollup: { contexts: { nodes: checks } } } }] },
  ...fields,
})
const data = (node, extra = {}) => ({ viewer: { login: LOGIN }, t0: { issueOrPullRequest: node }, ...extra })
const baseline = (node) => diffPoll({ threads: {} }, data(node), REFS, BEFORE).next
const events = (before, after) => diffPoll(baseline(before), data(after), REFS, AFTER).events

test('the first poll of a thread is its baseline, with no events', () => {
  const { events, next } = diffPoll({ threads: {} }, data(pr({ checks: [check('ci', 'FAILURE')] })), REFS, AFTER)
  assert.deepEqual(events, [])
  assert.deepEqual(next.threads['o/r#5'], { since: '2026-10-10T10:00:00.000Z', conflict: false, failing: ['ci'], state: 'OPEN', head: 'a'.repeat(40) })
})

test('a new comment by someone else is a COMMENT event', () => {
  assert.deepEqual(events(pr(), pr({ comments: [comment('carol', AFTER, 'Could you\nrebase?')] })), [`COMMENT ${PR_URL}#issuecomment-carol carol: Could you rebase?`])
})

test('our own badge-first comment is not an event', () => {
  assert.deepEqual(events(pr(), pr({ comments: [comment(LOGIN, AFTER, `${BADGE}\n\nDone in abc`)] })), [])
})

test("the user's unbadged comment is an event marked (you)", () => {
  assert.deepEqual(events(pr(), pr({ comments: [comment(LOGIN, AFTER, 'please also fix y')] })), [`COMMENT ${PR_URL}#issuecomment-bot bot (you): please also fix y`])
})

test('reviews and inline review comments are events', () => {
  const after = pr({
    reviews: { nodes: [{ author: { login: 'carol' }, createdAt: BEFORE, submittedAt: AFTER, url: `${PR_URL}#review-1`, body: 'nits', state: 'CHANGES_REQUESTED' }] },
    reviewThreads: { nodes: [{ comments: { nodes: [{ author: { login: 'carol' }, createdAt: AFTER, url: `${PR_URL}#r1`, body: 'rename', path: 'a.js' }] } }] },
  })
  assert.deepEqual(events(pr(), after), [`REVIEW ${PR_URL}#review-1 carol: CHANGES_REQUESTED: nits`, `INLINE ${PR_URL}#r1 carol: a.js: rename`])
})

test('a newly failing check is a CI event, once', () => {
  const failing = pr({ checks: [check('ci', 'FAILURE'), check('lint', 'SUCCESS')] })
  assert.deepEqual(events(pr(), failing), ['CI https://ci/ci ci: FAILURE'])
  assert.deepEqual(events(failing, failing), [])
})

test('merging and closing are events', () => {
  assert.deepEqual(events(pr(), pr({ state: 'MERGED', mergedAt: AFTER })), [`MERGED ${PR_URL} -: merged at ${AFTER}`])
  assert.deepEqual(events(pr(), pr({ state: 'CLOSED', closedAt: AFTER })), [`CLOSED ${PR_URL} -: closed at ${AFTER}`])
})

test('becoming CONFLICTING is an event', () => {
  assert.deepEqual(events(pr(), pr({ mergeable: 'CONFLICTING' })), [`CONFLICT ${PR_URL} -: mergeable is CONFLICTING`])
  assert.deepEqual(events(pr({ mergeable: 'CONFLICTING' }), pr({ mergeable: 'UNKNOWN' })), [])
})

test("a push by someone else to the PR's branch is a PUSH event", () => {
  assert.deepEqual(events(pr(), pr({ head: 'b'.repeat(40), pusher: 'maintainer' })), [`PUSH ${PR_URL} maintainer: bbbbbbb Fix the thing`])
})

test('our own push and an unchanged head are not events', () => {
  assert.deepEqual(events(pr(), pr({ head: 'b'.repeat(40) })), [])
  assert.deepEqual(events(pr({ pusher: 'maintainer' }), pr({ pusher: 'maintainer' })), [])
})

test('a head seen for the first time is a baseline', () => {
  const state = baseline(pr())
  delete state.threads['o/r#5'].head
  assert.deepEqual(diffPoll(state, data(pr({ head: 'b'.repeat(40), pusher: 'maintainer' })), REFS, AFTER).events, [])
})

test('a thumbs reaction by someone else on our comment is a REACTION event', () => {
  const ours = (reactions) => pr({ comments: [comment(LOGIN, BEFORE, `${BADGE}\n\nProposal`, reactions)] })
  assert.deepEqual(events(ours([]), ours([reaction('carol', 'THUMBS_UP'), reaction('dave', 'THUMBS_DOWN')])), [
    `REACTION ${PR_URL}#issuecomment-bot carol: 👍`,
    `REACTION ${PR_URL}#issuecomment-bot dave: 👎`,
  ])
})

test('other reactions, our own, old ones and those on others’ comments are not events', () => {
  const ours = (reactions) => pr({ comments: [comment(LOGIN, BEFORE, `${BADGE}\n\nProposal`, reactions)] })
  assert.deepEqual(events(ours([]), ours([reaction('carol', 'HEART'), reaction(LOGIN, 'THUMBS_UP'), reaction('dave', 'THUMBS_UP', '2026-10-10T09:00:00Z')])), [])
  const theirs = pr({ comments: [comment('carol', BEFORE, 'idea', [reaction('dave', 'THUMBS_UP')])] })
  assert.deepEqual(events(pr(), theirs), [])
})

test("an /agent comment by the user after since is an AGENT event", () => {
  const state = { ...baseline(pr()), agentSince: BEFORE }
  const agent = { nodes: [{ comments: { nodes: [comment(LOGIN, AFTER, '/agent fix the flaky test'), comment(LOGIN, AFTER, 'not a command'), comment('carol', AFTER, '/agent x')] } }] }
  assert.deepEqual(diffPoll(state, data(pr(), { agent }), REFS, AFTER).events, [`AGENT ${PR_URL}#issuecomment-bot bot: /agent fix the flaky test`])
})

const pollsOf = (responses, overrides = {}) => {
  let now = NOW
  const calls = []
  const ctx = fakeCtx({
    now: () => now,
    sleep: async (ms) => (now += ms),
    gh: (args) => {
      calls.push(args)
      const response = responses[Math.min(calls.length, responses.length) - 1]
      return 'error' in response ? { code: 1, stdout: '', stderr: response.error } : { code: 0, stdout: JSON.stringify({ data: response }), stderr: '' }
    },
    ...overrides,
  })
  return { ctx, calls }
}
const threeThreads = (node) => ({ viewer: { login: LOGIN }, t0: { issueOrPullRequest: node }, t1: { issueOrPullRequest: node }, t2: { issueOrPullRequest: node } })
const URLS = ['o/r#5', 'o/r#6', 'https://github.com/o/s/issues/7']

test('mw watch makes one GraphQL request per poll for any number of threads', async () => {
  const { ctx, calls } = pollsOf([threeThreads(pr())])
  assert.equal(await watchCommand([...URLS, '--max', '5m'], ctx), 0)
  assert.equal(calls.length, 6)
  assert.ok(calls.every((args) => args[0] === 'api' && args[1] === 'graphql'))
  assert.match(calls[0][3], /t0: repository.*t1: repository.*t2: repository/s)
  assert.deepEqual(ctx.output, [`no events; re-arm: mw watch ${URLS.join(' ')} --max 5m`])
})

test('mw watch --commands searches every 3rd poll inside the same request', async () => {
  const { ctx, calls } = pollsOf([threeThreads(pr())])
  writeState(ctx, 'workspaces.json', { oss: ['o', 'p'] })
  await watchCommand([...URLS, '--commands', '--workspace', 'oss', '--max', '5m'], ctx)
  assert.equal(calls.length, 6)
  assert.deepEqual(calls.map((args) => args[3].includes('agent: search')), [true, false, false, true, false, false])
  assert.match(calls[0][3], /commenter:@me \\"\/agent\\" updated:>=\S+ user:o user:p/)
})

test('mw watch --commands without a workspaces.json entry searches the owner the workspace is named after', async () => {
  const { ctx, calls } = pollsOf([threeThreads(pr())])
  assert.equal(await watchCommand([...URLS, '--commands', '--workspace', 'o', '--once'], ctx), 0)
  assert.match(calls[0][3], /updated:>=\S+ user:o"\)/)
})

test('mw watch exits on the first poll with events and prints the re-arm command', async () => {
  const { ctx, calls } = pollsOf([data(pr()), data(pr({ comments: [comment('carol', AFTER, 'ping')] }))])
  assert.equal(await watchCommand(['o/r#5'], ctx), 0)
  assert.equal(calls.length, 2)
  assert.deepEqual(ctx.output, [`COMMENT ${PR_URL}#issuecomment-carol carol: ping`, 're-arm: mw watch o/r#5'])
})

test('mw watch exits 1 after 5 API errors in a row', async () => {
  const { ctx, calls } = pollsOf([{ error: 'HTTP 502' }])
  assert.equal(await watchCommand(['o/r#5'], ctx), 1)
  assert.equal(calls.length, 5)
  assert.deepEqual(ctx.output, ['ERROR HTTP 502'])
})

test('mw watch --once reports a failed poll as an error, not a quiet thread', async () => {
  const { ctx } = pollsOf([{ error: 'HTTP 502' }])
  assert.equal(await watchCommand(['o/r#5', '--once'], ctx), 1)
  assert.deepEqual(ctx.output, ['ERROR HTTP 502'])
})

test('mw watch names the failure when gh fails without printing anything', async () => {
  const { ctx } = pollsOf([{ error: '' }])
  assert.equal(await watchCommand(['o/r#5', '--once'], ctx), 1)
  assert.deepEqual(ctx.output, ['ERROR gh api graphql exited with code 1 and printed nothing'])
})
