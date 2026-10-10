import assert from 'node:assert/strict'
import { appendFileSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { test } from 'node:test'
import { fakeGh, run, tempDir } from './helpers.mjs'

const BADGE = '<img src="https://github.com/claude.png" width="20" height="20" alt="Claude">'
const DRAFT = `${BADGE}\n\nFixed in the latest commit, with a test.\n`
const REASON = 'the maintainer asked for this exact text'

function setup({ comments = [], text = DRAFT } = {}) {
  const home = tempDir()
  const draft = join(home, 'reply.md')
  writeFileSync(draft, text)
  writeFileSync(join(home, 'gh-user.json'), JSON.stringify({ id: 1, login: 'bot' }))
  const gh = fakeGh([['issues/5/comments', JSON.stringify([comments])]])
  const mw = (...args) => run('bin/mw', args, { env: { ...gh.env, MW_HOME: home } })
  return {
    draft,
    mw,
    post: (flags = [], ghArgs = ['pr', 'comment', '5', '-R', 'o/r', '--body-file', draft]) => mw('post', ...flags, draft, '--', 'gh', ...ghArgs),
    posts: () => gh.calls().filter((args) => args[0] !== 'api'),
  }
}

test('mw verdict records the sha256 of the draft', () => {
  const { draft, mw } = setup()
  assert.equal(mw('verdict', draft, 'CLEAN', '--by', 'codex').code, 0)
  const verdict = JSON.parse(readFileSync(`${draft}.verdict.json`, 'utf8'))
  assert.deepEqual([verdict.verdict, verdict.by, verdict.sha256.length], ['CLEAN', 'codex', 64])
})

test('mw post stops with exit 3 when the draft has no verdict', () => {
  const { post, posts } = setup()
  const r = post()
  assert.equal(r.code, 3)
  assert.match(r.stderr, /no review verdict/)
  assert.match(r.stderr, /--I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE "<why this is right here>"/)
  assert.deepEqual(posts(), [])
})

test('mw post stops when the draft changed since its review', () => {
  const { draft, mw, post, posts } = setup()
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  appendFileSync(draft, 'One more line.\n')
  const r = post()
  assert.equal(r.code, 3)
  assert.match(r.stderr, /changed since its review/)
  assert.deepEqual(posts(), [])
})

test('mw post runs the gh command when the verdict is CLEAN and current', () => {
  const { draft, mw, post, posts } = setup()
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  const r = post()
  assert.equal(r.code, 0)
  assert.deepEqual(posts(), [['pr', 'comment', '5', '-R', 'o/r', '--body-file', draft]])
  assert.match(r.stdout, /posted\. Not watching this thread yet\? mw watch https:\/\/github\.com\/o\/r\/issues\/5/)
})

test('mw post with a bypass reason runs gh and says what it bypassed', () => {
  for (const flags of [['--I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE', REASON], [`--I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE=${REASON}`]]) {
    const { post, posts } = setup()
    const r = post(flags)
    assert.equal(r.code, 0)
    assert.match(r.stderr, new RegExp(`bypassed \\(verdict\\): ${REASON}`))
    assert.equal(posts().length, 1)
  }
})

test('mw post rejects a bypass reason under 3 words', () => {
  const { post, posts } = setup()
  const r = post(['--I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE', 'because'])
  assert.equal(r.code, 3)
  assert.match(r.stderr, /reason is missing or shorter than 3 words/)
  assert.deepEqual(posts(), [])
})

test('mw post exits 2 when the gh command does not post the draft', () => {
  const { post, posts } = setup()
  const r = post([], ['pr', 'comment', '5', '-R', 'o/r', '--body', 'other text'])
  assert.equal(r.code, 2)
  assert.match(r.stderr, /the gh command must post this draft/)
  assert.deepEqual(posts(), [])
})

test('mw post stops on a lint error', () => {
  const { draft, mw, post } = setup({ text: `${BADGE}\n\nFixed — with a test.\n` })
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  const r = post()
  assert.equal(r.code, 3)
  assert.match(r.stdout, /error: 3: em dash/)
})

test('mw post stops a third comment in a row', () => {
  const ours = { user: { login: 'bot' }, body: `${BADGE}\n\nearlier` }
  const { draft, mw, post } = setup({ comments: [{ user: { login: 'carol' }, body: 'q' }, ours, ours] })
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  const r = post()
  assert.equal(r.code, 3)
  assert.match(r.stderr, /third comment in a row; edit your last one instead/)
})

test('mw post infers the lint kind from the gh command, and --kind overrides it', () => {
  const { draft, mw, post } = setup({ text: `${BADGE}\n\n${'word '.repeat(450)}\n` })
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  assert.doesNotMatch(post([], ['pr', 'create', '-R', 'o/r', '--body-file', draft]).stdout, /posts usually need/)
  assert.match(post([], ['issue', 'create', '-R', 'o/r', '--body-file', draft]).stdout, /issue posts usually need/)
  assert.match(post().stdout, /reply posts usually need/)
  assert.match(post(['--kind', 'design']).stdout, /design posts usually need/)
})

test('mw post --kind umbrella exempts the draft from the badge', () => {
  const { draft, mw, post } = setup({ text: 'Tracking the fix across packages.\n' })
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  assert.equal(post().code, 3)
  assert.equal(post(['--kind', 'umbrella']).code, 0)
})
