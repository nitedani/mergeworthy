import assert from 'node:assert/strict'
import { spawn, spawnSync } from 'node:child_process'
import { once } from 'node:events'
import { join } from 'node:path'
import { test } from 'node:test'
import { ROOT, run } from './helpers.mjs'

const works = (cmd, args) => spawnSync(cmd, args).status === 0
const skip = works('slirp4netns', ['--version']) && works('unshare', ['-rn', 'true']) ? false : 'slirp4netns or unprivileged unshare is unavailable'
const server = (host) => `require('http').createServer((req, res) => { res.end('inside'); process.exit(0) }).listen(8080, '${host}', () => console.log('listening'))`

test('mw netns exits with the command status', { skip }, () => {
  assert.equal(run('bin/mw', ['netns', '--', 'sh', '-c', 'exit 3']).code, 3)
})

for (const host of ['0.0.0.0', '127.0.0.1']) {
  test(`mw netns --publish forwards a host port to a server inside that listens on ${host}`, { skip, timeout: 30_000 }, async () => {
    const mw = spawn(process.execPath, [join(ROOT, 'bin/mw'), 'netns', '--publish', '8080', '--', process.execPath, '-e', server(host)])
    try {
      const [published] = await Promise.all([lineMatching(mw.stderr, /published 8080 at (http:\/\/127\.0\.0\.1:\d+)/), lineMatching(mw.stdout, /listening/)])
      assert.equal(await (await fetch(published[1])).text(), 'inside')
      assert.deepEqual(await once(mw, 'exit'), [0, null])
    } finally {
      if (mw.exitCode === null) mw.kill()
    }
  })
}

function lineMatching(stream, pattern) {
  return new Promise((resolve) => {
    let text = ''
    stream.on('data', (chunk) => {
      text += chunk
      const match = pattern.exec(text)
      if (match) resolve(match)
    })
  })
}
