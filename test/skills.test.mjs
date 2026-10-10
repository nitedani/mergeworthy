import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, readdirSync } from 'node:fs'

const skillsDir = new URL('../skills/', import.meta.url)
const skills = readdirSync(skillsDir)

test('the twelve skills exist', () => {
  assert.deepEqual(skills.sort(), ['code', 'converge', 'delegating', 'design', 'evidence', 'finality', 'github', 'posting', 'pull-request', 'review', 'task', 'writing'])
})

for (const name of skills) {
  test(`${name}: frontmatter names it, and every numbered step says when it's done`, () => {
    const text = readFileSync(new URL(`${name}/SKILL.md`, skillsDir), 'utf8')
    const front = text.match(/^---\nname: (.+)\ndescription: "(.+)"\n---\n/)
    assert.ok(front, 'frontmatter with name and a quoted description')
    assert.equal(front[1], name)
    const steps = text.split('\n## Steps\n')[1]
    assert.ok(steps, 'a "## Steps" section')
    const items = steps.split('\n## ')[0].split(/\n(?=\d+\. )/).filter(s => /^\d+\. /.test(s))
    assert.ok(items.length >= 3, 'at least three numbered steps')
    for (const item of items) assert.match(item, /\bDone:/, `step without "Done:": ${item.slice(0, 60)}`)
  })
}

test('the always-on text routes to every skill', () => {
  const text = readFileSync(new URL('../always-on.md', import.meta.url), 'utf8')
  for (const name of skills) assert.ok(text.includes(`mergeworthy:${name}`), name)
})
