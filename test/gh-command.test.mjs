import assert from 'node:assert/strict'
import { test } from 'node:test'
import { ghCommand, ghName, postsToGitHub } from '../lib/gh-command.mjs'

test('ghCommand takes out the repo flag and reads a gh api request', () => {
  assert.deepEqual(ghCommand(['-R', 'o/r', 'pr', 'close', '5', '-c', 'Replaced by #6']), { group: 'pr', action: 'close', args: ['5', '-c', 'Replaced by #6'], repo: 'o/r', api: null })
  assert.deepEqual(ghCommand(['api', '-X', 'PATCH', 'repos/o/r/issues/5', '--input=b.json']).api, { method: 'PATCH', path: 'repos/o/r/issues/5', fields: [], input: 'b.json' })
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
