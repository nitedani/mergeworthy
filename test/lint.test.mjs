import assert from 'node:assert/strict'
import { test } from 'node:test'
import { lint } from '../lib/lint.mjs'
import { BADGE } from './helpers.mjs'

const OTHER_REPO = { repo: 'vikejs/vike', login: 'bot' }
const withBadge = (text) => `${BADGE}\n\n${text}\n`
const checks = (text, options = OTHER_REPO) => lint(text, options).map((f) => f.check)

const CASES = {
  badge: {
    fires: ['Fixed in abc.\n', `\nFixed.\n${BADGE}\n`],
    silent: [withBadge('Fixed.'), `\n\n<img src="https://github.com/openai.png" width="20">\nFixed.`],
  },
  'process-words': {
    fires: [withBadge('The guardian found nothing.'), withBadge('Loop A passed.'), withBadge('Per the Fresh Reader, fine.')],
    silent: [withBadge('The loop and the guard are fine.'), withBadge('Run `mergeworthy` here.'), withBadge('> the harness said so')],
  },
  attribution: {
    fires: [withBadge('As agreed, I moved it.'), withBadge('You suggested a flag.'), withBadge('@carol decided to drop it.'), withBadge('Carol asked for this.')],
    silent: [withBadge('As agreed in https://github.com/o/r/issues/1#issuecomment-9, I moved it.'), withBadge('It was decided long ago.'), withBadge('> you suggested a flag'), withBadge('The compiler said x.')],
  },
  mention: {
    fires: [withBadge('Thanks @carol.'), withBadge('(@carol) can you look?')],
    silent: [withBadge('Mail me@work.example.'), withBadge('Use `@carol`.'), withBadge('> @carol wrote this')],
  },
  'em-dash': {
    fires: [withBadge('Fixed — with a test.')],
    silent: [withBadge('Fixed, with a test.'), withBadge('```\na — b\n```')],
  },
  secret: {
    fires: [withBadge('`ghp_' + 'a'.repeat(36) + '`'), withBadge('AKIA' + 'A'.repeat(16)), withBadge('-----BEGIN RSA PRIVATE KEY-----'), withBadge('Bearer ' + 'x'.repeat(30))],
    silent: [withBadge('ghp_short'), withBadge('sk-short')],
  },
  cant: {
    fires: [withBadge("That can't work here.")],
    silent: [withBadge("That can't work: `x()` throws."), withBadge("That can't work, see https://example.com/x."), withBadge('That works.')],
  },
}

for (const [check, { fires, silent }] of Object.entries(CASES)) {
  for (const text of fires) test(`${check} fires on: ${JSON.stringify(text)}`, () => assert.ok(checks(text).includes(check)))
  for (const text of silent) test(`${check} stays silent on: ${JSON.stringify(text)}`, () => assert.ok(!checks(text).includes(check)))
}

test('the badge check skips umbrella bodies', () => {
  assert.deepEqual(checks('Tracking the fix.\n', { ...OTHER_REPO, kind: 'umbrella' }), [])
})

test('process words are fine in the user’s own repos', () => {
  assert.deepEqual(checks(withBadge('The guardian found nothing.'), { repo: 'bot/tools', login: 'bot' }), [])
})

test('length warns past the norm for the kind, and only with a kind', () => {
  const long = withBadge('word '.repeat(250))
  assert.deepEqual(lint(long, { ...OTHER_REPO, kind: 'reply' }).map((f) => [f.check, f.level]), [['length', 'warning']])
  assert.deepEqual(checks(withBadge('word '.repeat(150)), { ...OTHER_REPO, kind: 'reply' }), [])
  assert.deepEqual(checks(long), [])
})

test('a design answer gets its length per quoted question', () => {
  const answer = withBadge(['> Why X?', 'word '.repeat(140), '> And Y?', 'word '.repeat(140)].join('\n\n'))
  assert.deepEqual(checks(answer, { ...OTHER_REPO, kind: 'design' }), [])
  assert.deepEqual(checks(withBadge('word '.repeat(280)), { ...OTHER_REPO, kind: 'design' }), ['length'])
})

test('findings carry their level and line', () => {
  assert.deepEqual(lint(withBadge('Thanks @carol.'), OTHER_REPO), [{ check: 'mention', level: 'error', line: 3, message: '@carol pings them; write the name without @ unless you are blocked on them' }])
})
