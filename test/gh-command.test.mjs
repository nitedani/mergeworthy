import assert from 'node:assert/strict'
import { test } from 'node:test'
import { ghCommand, ghName, postsToGitHub, textFiles } from '../lib/gh-command.mjs'

test('ghCommand takes out the repo flag and reads a gh api request', () => {
  assert.deepEqual(ghCommand(['-R', 'o/r', 'pr', 'close', '5', '-c', 'Replaced by #6']), { group: 'pr', action: 'close', args: ['5', '-c', 'Replaced by #6'], repo: 'o/r', target: '5', api: null })
  assert.deepEqual(ghCommand(['api', '-X', 'PATCH', 'repos/o/r/issues/5', '--input=b.json']).api, { method: 'PATCH', path: 'repos/o/r/issues/5', fields: [], fileFields: [], input: 'b.json' })
  assert.equal(ghCommand(['api', 'repos/o/r/issues/5/comments', '-fbody=x']).api.method, 'POST')
})

test('ghName names a gh api call by its path and any other gh call by its group and action', () => {
  assert.equal(ghName(ghCommand(['api', '--method=POST', 'repos/o/r/pulls/5/reviews', '--input', 'r.json'])), 'gh api repos/o/r/pulls/5/reviews')
  assert.equal(ghName(ghCommand(['issue', 'close', '5'])), 'gh issue close')
})

test('postsToGitHub counts a REST write as a post only when it sends a body', () => {
  assert.equal(postsToGitHub(ghCommand(['api', 'repos/o/r/issues/5/comments', '-F', 'body=@reply.md'])), true)
  assert.equal(postsToGitHub(ghCommand(['api', 'repos/o/r/issues/5', '-X', 'PATCH', '-f', 'state=closed'])), false)
})

test('ghCommand finds the target after flag values, wherever -R is', () => {
  assert.equal(ghCommand(['pr', 'close', '--comment', 'superseded by #6', '5']).target, '5')
  assert.equal(ghCommand(['pr', 'close', '-c', '7', '-R', 'o/r', 'https://github.com/o/r/pull/5']).target, 'https://github.com/o/r/pull/5')
  assert.equal(ghCommand(['pr', 'close', '-d', '5']).target, '5')
  assert.equal(ghCommand(['pr', 'ready']).target, null)
  assert.equal(ghCommand(['pr', 'review', '-r', '5', '-b', 'Fix the key']).target, '5')
})

test('textFiles gives the files a command reads its text from, by the flag its command uses', () => {
  assert.deepEqual(textFiles(ghCommand(['pr', 'comment', '5', '--body-file', 'a.md'])), ['a.md'])
  assert.deepEqual(textFiles(ghCommand(['issue', 'create', '--title', 't', '--body-file=a.md'])), ['a.md'])
  assert.deepEqual(textFiles(ghCommand(['release', 'create', 'v1', '-F', 'notes.md'])), ['notes.md'])
  assert.deepEqual(textFiles(ghCommand(['gist', 'create', '-d', 'desc', '-p', 'a.md'])), ['a.md'])
  assert.deepEqual(textFiles(ghCommand(['api', 'repos/o/r/issues/5/comments', '-F', 'body=@a.md'])), ['a.md'])
  assert.deepEqual(textFiles(ghCommand(['pr', 'comment', '5', '--title', 'a.md'])), [])
})
