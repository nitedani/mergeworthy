import assert from 'node:assert/strict'
import { test } from 'node:test'
import { diffLint, locTable, parseMap } from '../lib/diff.mjs'

const patch = (file, start, lines) => `diff --git a/${file} b/${file}\n--- a/${file}\n+++ b/${file}\n@@ -0,0 +${start},${lines.length} @@\n${lines.map((l) => '+' + l).join('\n')}\n`
const warnings = (diff) => diffLint(diff).map((w) => `${w.file}:${w.line}: ${w.message.split(';')[0]}`)

test('diff-lint warns once per added comment block of 2+ lines', () => {
  assert.deepEqual(warnings(patch('src/a.ts', 10, ['// one', '// two', 'code()', '// alone'])), ['src/a.ts:10: an added code comment of 2+ lines'])
  assert.deepEqual(warnings(patch('run.sh', 1, ['#!/bin/sh', '# setup'])), [])
})

test('diff-lint warns on comments about history', () => {
  assert.deepEqual(warnings(patch('lib/x.py', 3, ['# we now cache this'])), ['lib/x.py:3: an added code comment about history (what changed or used to be)'])
  assert.deepEqual(warnings(patch('README.md', 3, ['This no longer applies.'])), [])
})

test('diff-lint warns on timed waits added in tests only', () => {
  assert.deepEqual(warnings(patch('test/a.test.mjs', 5, ['await sleep(100)'])), ['test/a.test.mjs:5: a test that waits a fixed time (setTimeout, sleep, …)'])
  assert.deepEqual(warnings(patch('src/retry.mjs', 5, ['setTimeout(retry, 100)'])), [])
})

test('loc splits lines into mapped features, tests and docs, skipping lockfiles', () => {
  const numstat = ['10\t2\tsrc/router/a.ts', '5\t0\tsrc/other.ts', '7\t1\ttest/a.test.ts', '3\t3\tdocs/guide.md', '4\t0\tREADME.md', '900\t0\tpnpm-lock.yaml', '1\t1\tsrc/{old => router}/b.ts'].join('\n')
  assert.equal(
    locTable(numstat, parseMap('# features\nsrc/router/** = Routing\n')),
    ['| Feature | + | − |', '|---|---|---|', '| Routing | 11 | 3 |', '| (unmapped) | 5 | 0 |', '| Tests | 7 | 1 |', '| Docs (2 files) | 7 | 3 |'].join('\n'),
  )
})

test('loc map globs: * stays in one directory, ? matches one character', () => {
  const [star, mark] = parseMap('src/*.ts = Top\nsrc/?.js = One')
  assert.deepEqual([star.pattern.test('src/a.ts'), star.pattern.test('src/x/a.ts')], [true, false])
  assert.deepEqual([mark.pattern.test('src/a.js'), mark.pattern.test('src/ab.js')], [true, false])
})
