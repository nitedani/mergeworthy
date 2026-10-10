import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { createHash } from 'node:crypto'

// sha256 of the prompt in mergeworthy main's skills/refactor/SKILL.md, from "Refactor this PR:" to its last line
const MAIN_PROMPT_SHA256 = 'e3b5de6cc3b62759da488494b326094a924d3548ba814ed8d140326c3eb469a9'

test('the refactor prompt is byte for byte the one on main', () => {
  const skill = readFileSync(new URL('../skills/code/SKILL.md', import.meta.url), 'utf8')
  const start = skill.indexOf('Refactor this PR:')
  const last = '  rating with link to commit(s).'
  const end = skill.indexOf(last, start) + last.length
  assert.ok(start >= 0 && end > start, 'prompt not found')
  assert.equal(createHash('sha256').update(skill.slice(start, end)).digest('hex'), MAIN_PROMPT_SHA256)
})
