import assert from 'node:assert/strict'
import { test } from 'node:test'
import { lint } from '../lib/lint.mjs'
import { BADGE, umbrella, UMBRELLA_HEADINGS, withHeader } from './helpers.mjs'

const OTHER_REPO = { repo: 'vikejs/vike', login: 'bot' }
const checks = (text, options = OTHER_REPO) => lint(text, options).map((f) => f.check)

const CASES = {
  header: {
    fires: [
      'Fixed in abc.\n',
      `\nFixed.\n${BADGE}\n`,
      `${BADGE}\n\nFixed.\n`,
      `${BADGE}\n*Opus 5.5 wrote this.*\n`,
      `${BADGE} *Claude wrote this.*\n`,
      `${BADGE} *Opus 5.5 ${'word '.repeat(30)}*\n`,
      `${BADGE} *Opus 5.5 fixed it in a1b2c3d.*\n`,
    ],
    silent: [
      withHeader('Fixed.'),
      `\n\n<img src="https://github.com/openai.png" width="20"><img src="https://github.com/claude.png" width="20"> _GPT-5 and Opus 5.5 wrote this._\nFixed.`,
      `${BADGE} *Opus 5.5 wrote this, see https://github.com/o/r/commit/a1b2c3d4e5 and comment 6097556038.*\n`,
    ],
  },
  'process-words': {
    fires: [
      withHeader('The guardian found nothing.'),
      withHeader('Loop A passed.'),
      withHeader('Per the Fresh Reader, fine.'),
      withHeader('Two fresh reads found nothing.'),
      withHeader('Bug verification passed.'),
      withHeader('After three review rounds.'),
    ],
    silent: [
      withHeader('The loop and the guard are fine.'),
      withHeader('Run `mergeworthy` here.'),
      withHeader('> the harness said so'),
      `${BADGE} *Opus 5.5 wrote this through the mergeworthy harness.*\n\nFixed.\n`,
    ],
  },
  attribution: {
    fires: [withHeader('As agreed, I moved it.'), withHeader('You suggested a flag.'), withHeader('@carol decided to drop it.'), withHeader('Carol asked for this.')],
    silent: [withHeader('As agreed in https://github.com/o/r/issues/1#issuecomment-9, I moved it.'), withHeader('It was decided long ago.'), withHeader('> you suggested a flag'), withHeader('The compiler said x.')],
  },
  mention: {
    fires: [withHeader('Thanks @carol.'), withHeader('(@carol) can you look?')],
    silent: [withHeader('Mail me@work.example.'), withHeader('Use `@carol`.'), withHeader('> @carol wrote this')],
  },
  'em-dash': {
    fires: [withHeader('Fixed — with a test.')],
    silent: [withHeader('Fixed, with a test.'), withHeader('```\na — b\n```')],
  },
  secret: {
    fires: [withHeader('`ghp_' + 'a'.repeat(36) + '`'), withHeader('AKIA' + 'A'.repeat(16)), withHeader('-----BEGIN RSA PRIVATE KEY-----'), withHeader('Bearer ' + 'x'.repeat(30))],
    silent: [withHeader('ghp_short'), withHeader('sk-short')],
  },
  promise: {
    fires: [
      withHeader("I'll post the numbers tonight."),
      withHeader('The numbers come within the hour.'),
      withHeader('I’ll follow up tomorrow.'),
      withHeader("I'll come back to this."),
      withHeader('Review it once it is merged.'),
      withHeader("Once they're pushed, the PRs are ready."),
    ],
    silent: [withHeader('Here are the numbers.'), withHeader("I'll leave that call to you."), withHeader("> I'll post it later"), withHeader('Merged once, reverted twice.')],
  },
  cant: {
    fires: [withHeader("That can't work here.")],
    silent: [withHeader("That can't work: `x()` throws."), withHeader("That can't work, see https://example.com/x."), withHeader('That works.')],
  },
}

for (const [check, { fires, silent }] of Object.entries(CASES)) {
  for (const text of fires) test(`${check} fires on: ${JSON.stringify(text)}`, () => assert.ok(checks(text).includes(check)))
  for (const text of silent) test(`${check} stays silent on: ${JSON.stringify(text)}`, () => assert.ok(!checks(text).includes(check)))
}

const umbrellaChecks = (text) => lint(text, { ...OTHER_REPO, kind: 'umbrella' }).map((f) => [f.check, f.level])

test('an umbrella needs no header, and passes with every heading in order', () => {
  assert.deepEqual(umbrellaChecks(umbrella()), [])
})

test('an umbrella missing a heading fails', () => {
  assert.deepEqual(umbrellaChecks(umbrella(UMBRELLA_HEADINGS.filter((h) => h !== '## Scope'))), [['umbrella-headings', 'error']])
})

test('an umbrella with headings out of order fails', () => {
  const swapped = ['# 🚧 WIP', '## TLDR', '## Scope', '## TODO', '## State', '## Agreed', '## Open', '## Next steps']
  assert.deepEqual(umbrellaChecks(umbrella(swapped)), [['umbrella-headings', 'error']])
})

test('a State bullet over 25 words warns, and 25 words pass', () => {
  assert.deepEqual(umbrellaChecks(umbrella(UMBRELLA_HEADINGS, `- ${'word '.repeat(26)}`)), [['umbrella-state', 'warning']])
  assert.deepEqual(umbrellaChecks(umbrella(UMBRELLA_HEADINGS, `- ${'word '.repeat(25)}`)), [])
})

const details = (summary) => `<details>\n<summary>${summary}</summary>\n\nRan it.\n</details>`
const prChecks = (text) => lint(text, { ...OTHER_REPO, kind: 'pr' }).map((f) => f.check)

test('a PR body may have one <details> block, summarized Verification', () => {
  assert.deepEqual(prChecks(withHeader(`Fix.\n\n${details('Verification')}`)), [])
  assert.deepEqual(prChecks(withHeader('Fix.')), [])
  assert.deepEqual(prChecks(withHeader('Fix.\n\n```html\n<details><summary>Example</summary></details>\n```')), [])
})

test('a PR body fails with a second <details> block or another summary', () => {
  assert.deepEqual(prChecks(withHeader(`Fix.\n\n${details('Verification')}\n\n${details('Process')}`)), ['pr-details'])
  assert.deepEqual(prChecks(withHeader(`Fix.\n\n${details('How I tested')}`)), ['pr-details'])
})

test('pr-details checks only PR bodies', () => {
  assert.deepEqual(lint(withHeader(details('How I tested')), { ...OTHER_REPO, kind: 'reply' }), [])
})

const issueChecks = (text) => lint(text, { ...OTHER_REPO, kind: 'issue' }).map((f) => f.check)

test('an issue needs a How to reproduce section, decision issues too', () => {
  assert.deepEqual(issueChecks(withHeader('It breaks.')), ['issue-reproduce'])
  assert.deepEqual(issueChecks(withHeader('### Options\n\n- Keep it.\n- Drop it.')), ['issue-reproduce'])
  assert.deepEqual(issueChecks(withHeader('```\n### How to reproduce\n```')), ['issue-reproduce'])
})

test('an issue with a How to reproduce section passes, and other kinds need none', () => {
  assert.deepEqual(issueChecks(withHeader('It breaks.\n\n### How to reproduce\n\n1. Run `vike dev`.')), [])
  assert.deepEqual(lint(withHeader('It breaks.'), { ...OTHER_REPO, kind: 'reply' }), [])
})

test('process words are fine in the user’s own repos', () => {
  assert.deepEqual(checks(withHeader('The guardian found nothing.'), { repo: 'bot/tools', login: 'bot' }), [])
})

test('length warns past the norm for the kind, and only with a kind', () => {
  const long = withHeader('word '.repeat(250))
  assert.deepEqual(lint(long, { ...OTHER_REPO, kind: 'reply' }).map((f) => [f.check, f.level]), [['length', 'warning']])
  assert.deepEqual(checks(withHeader('word '.repeat(150)), { ...OTHER_REPO, kind: 'reply' }), [])
  assert.deepEqual(checks(long), [])
})

test('a design answer gets its length per quoted question', () => {
  const answer = withHeader(['> Why X?', 'word '.repeat(140), '> And Y?', 'word '.repeat(140)].join('\n\n'))
  assert.deepEqual(checks(answer, { ...OTHER_REPO, kind: 'design' }), [])
  assert.deepEqual(checks(withHeader('word '.repeat(280)), { ...OTHER_REPO, kind: 'design' }), ['length'])
})

test('each failing rule of the header gets its own message', () => {
  const messages = lint(`${BADGE} *Claude fixed it in a1b2c3d.*\n`, OTHER_REPO).map((f) => f.message)
  assert.deepEqual(messages, ["the header's note must name the model with its version, like Opus 5.5 or GPT-5", "the header's note names a commit; leave commits to the body"])
})

test('findings carry their level and line', () => {
  assert.deepEqual(lint(withHeader('Thanks @carol.'), OTHER_REPO), [{ check: 'mention', level: 'error', line: 3, message: '@carol pings them; write the name without @ unless you are blocked on them' }])
})
