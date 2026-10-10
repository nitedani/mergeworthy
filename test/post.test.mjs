import assert from 'node:assert/strict'
import { appendFileSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { test } from 'node:test'
import { parse } from '../lib/shell.mjs'
import { fakeGh, run, tempDir, umbrella, withHeader } from './helpers.mjs'

const DRAFT = withHeader('Fixed in the latest commit, with a test.')
const REASON = 'the maintainer asked for this exact text'
const OURS = { user: { login: 'bot' }, body: withHeader('earlier') }

function setup({ comments = [], text = DRAFT, commentsFail = false } = {}) {
  const home = tempDir()
  const draft = join(home, 'reply.md')
  writeFileSync(draft, text)
  writeFileSync(join(home, 'gh-user.json'), JSON.stringify({ id: 1, login: 'bot' }))
  const gh = fakeGh([['issues/5/comments', commentsFail ? '' : JSON.stringify([comments]), commentsFail ? 1 : 0]])
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

test('mw post prints a bypass command that keeps a multi-word title as one argument', () => {
  const { draft, post } = setup()
  const r = post([], ['pr', 'create', '-R', 'o/r', '--title', 'Fix the parser bug', '--body-file', draft])
  assert.equal(r.code, 3)
  assert.match(r.stderr, /-- gh pr create -R o\/r --title 'Fix the parser bug' --body-file /)
})

test('mw post stops when the draft changed since its review', () => {
  const { draft, mw, post, posts } = setup()
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  appendFileSync(draft, 'One more line.\n')
  const r = post()
  assert.equal(r.code, 3)
  assert.match(r.stderr, /changed after its review/)
  assert.deepEqual(posts(), [])
})

test('mw post runs the gh command when the verdict is CLEAN and current', () => {
  const { draft, mw, post, posts } = setup()
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  const r = post()
  assert.equal(r.code, 0)
  assert.deepEqual(posts(), [['pr', 'comment', '5', '-R', 'o/r', '--body-file', draft]])
  assert.match(r.stdout, /Posted\. If you are not watching this thread for replies yet, run: mw watch https:\/\/github\.com\/o\/r\/issues\/5/)
})

test('mw post with a bypass reason runs gh and says what it bypassed', () => {
  for (const flags of [['--I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE', REASON], [`--I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE=${REASON}`]]) {
    const { post, posts } = setup()
    const r = post(flags)
    assert.equal(r.code, 0)
    assert.match(r.stderr, new RegExp(`posting despite the failed checks \\(verdict\\), with this bypass reason: ${REASON}`))
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

test('mw post prints a retry command without the old bypass, which posts once the reason is filled in', () => {
  for (const flags of [['--I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE', 'because'], ['--I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE=because']]) {
    const { mw, post, posts } = setup()
    const printed = /in the command: mw (post .*)$/m.exec(post(flags).stderr)[1]
    assert.equal(printed.match(/--I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE/g).length, 1)
    const retry = parse(printed.replace('<why this is right here>', REASON)).commands[0].argv
    assert.equal(mw(...retry).code, 0)
    assert.equal(posts().length, 1)
  }
})

test('mw post exits 2 when the gh command does not post the draft', () => {
  const { post, posts } = setup()
  const r = post([], ['pr', 'comment', '5', '-R', 'o/r', '--body', 'other text'])
  assert.equal(r.code, 2)
  assert.match(r.stderr, /the gh command after -- must read its text from this draft file/)
  assert.deepEqual(posts(), [])
})

test('mw post reads a release draft from --notes-file and a gist draft from a file argument, but not from --title', () => {
  const { draft, mw, post, posts } = setup()
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  assert.equal(post([], ['release', 'create', 'v1', '-R', 'o/r', '--notes-file', draft]).code, 0)
  assert.equal(post([], ['gist', 'create', draft]).code, 0)
  assert.equal(post([], ['pr', 'edit', '5', '-R', 'o/r', '--title', draft]).code, 2)
  assert.deepEqual(posts().map((args) => args.slice(0, 2).join(' ')).filter((command) => command !== 'repo view'), ['release create', 'gist create'])
})

test('mw post refuses gh api forms that send the draft path or the raw file instead of its text', () => {
  const { draft, mw, post, posts } = setup()
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  for (const form of [['-f', `body=@${draft}`], ['--raw-field', `body=@${draft}`], ['--input', draft]]) {
    const r = post([], ['api', 'repos/o/r/issues/5/comments', ...form])
    assert.equal(r.code, 2)
    assert.match(r.stderr, /or with -F body=@<draft> for gh api'?$/m)
  }
  assert.deepEqual(posts(), [])
})

test('mw post stops on a lint error', () => {
  const { draft, mw, post } = setup({ text: withHeader('Fixed — with a test.') })
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  const r = post()
  assert.equal(r.code, 3)
  assert.match(r.stdout, /error: line 3: em dash/)
})

test('mw post stops a third comment in a row', () => {
  const { draft, mw, post } = setup({ comments: [{ user: { login: 'carol' }, body: 'q' }, OURS, OURS] })
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  const r = post()
  assert.equal(r.code, 3)
  assert.match(r.stderr, /third comment in a row on this thread, after two of yours\. Edit your last comment instead/)
})

test('mw post stops when it cannot read the thread, and the bypass posts anyway', () => {
  const { draft, mw, post, posts } = setup({ commentsFail: true })
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  const r = post()
  assert.equal(r.code, 3)
  assert.match(r.stderr, /its thread check\): couldn't read the thread's comments, so mw post can't tell whether this would be your third comment in a row \(gh api repos\/o\/r\/issues\/5\/comments --paginate failed/)
  assert.deepEqual(posts(), [])
  assert.equal(post(['--I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE', REASON]).code, 0)
  assert.equal(posts().length, 1)
})

test('mw post stops a third comment in a row posted through gh api', () => {
  const { draft, mw, post } = setup({ comments: [OURS, OURS] })
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  const r = post([], ['api', 'repos/o/r/issues/5/comments', '-F', `body=@${draft}`])
  assert.equal(r.code, 3)
  assert.match(r.stderr, /third comment in a row/)
})

test('mw post lints with the repo named in a gh api path', () => {
  const { draft, mw, post } = setup({ text: withHeader('The guardian found nothing.') })
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  const r = post([], ['api', 'repos/bot/tools/issues/5/comments', '-F', `body=@${draft}`])
  assert.equal(r.code, 0)
  assert.doesNotMatch(r.stdout, /a process word/)
})

test('mw post infers the lint kind from the gh command, and --kind overrides it', () => {
  const { draft, mw, post } = setup({ text: withHeader('word '.repeat(450)) })
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  assert.doesNotMatch(post([], ['pr', 'create', '-R', 'o/r', '--body-file', draft]).stdout, /posts usually need/)
  assert.match(post([], ['issue', 'create', '-R', 'o/r', '--body-file', draft]).stdout, /issue posts usually need/)
  assert.match(post().stdout, /reply posts usually need/)
  assert.match(post(['--kind', 'design']).stdout, /design posts usually need/)
})

test('mw post stops an issue without a How to reproduce section', () => {
  const { draft, mw, post } = setup({ text: withHeader('It breaks.') })
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  const r = post([], ['issue', 'create', '-R', 'o/r', '--title', 'It breaks', '--body-file', draft])
  assert.equal(r.code, 3)
  assert.match(r.stdout, /### How to reproduce/)
})

test('mw post --kind umbrella exempts the draft from the header', () => {
  const { draft, mw, post } = setup({ text: umbrella() })
  mw('verdict', draft, 'CLEAN', '--by', 'codex')
  assert.equal(post().code, 3)
  assert.equal(post(['--kind', 'umbrella']).code, 0)
})
