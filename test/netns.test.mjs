import assert from 'node:assert/strict'
import { spawn, spawnSync } from 'node:child_process'
import { once } from 'node:events'
import { join } from 'node:path'
import { test } from 'node:test'
import { ROOT, run } from './helpers.mjs'

const works = (cmd, args) => spawnSync(cmd, args).status === 0
const skip = works('slirp4netns', ['--version']) && works('unshare', ['-rn', 'true']) ? false : 'slirp4netns or unprivileged unshare is unavailable'
const READ_ONLY_PROC_SYS = ['unshare', '-rmpf', '--kill-child', '--mount-proc', 'sh', '-c', 'mount --bind /proc/sys /proc/sys && mount -o remount,bind,ro /proc/sys && exec "$@"', '_']
const skipReadOnly = skip || (works(READ_ONLY_PROC_SYS[0], [...READ_ONLY_PROC_SYS.slice(1), 'true']) ? false : 'unshare cannot make /proc/sys read-only here')
const server = (host) => `require('http').createServer((req, res) => { res.end('inside'); process.exit(0) }).listen(8080, '${host}', () => console.log('listening'))`

test('mw netns exits with the command status', { skip }, () => {
  assert.equal(run('bin/mw', ['netns', '--', 'sh', '-c', 'exit 3']).code, 3)
})

for (const host of ['0.0.0.0', '127.0.0.1']) {
  test(`mw netns --publish forwards a host port to a server inside that listens on ${host}`, { skip, timeout: 30_000 }, async () => {
    const { answer, note } = await publish(host)
    assert.equal(answer, 'inside')
    assert.match(note, /^for a server inside that listens on localhost, 127\.0\.0\.1 or all interfaces\./)
  })
}

test('mw netns --publish still reaches a server on 0.0.0.0 where /proc/sys is read-only, and says the server must listen there', { skip: skipReadOnly, timeout: 30_000 }, async () => {
  const { answer, note } = await publish('0.0.0.0', READ_ONLY_PROC_SYS)
  assert.equal(answer, 'inside')
  assert.match(note, /^for a server inside that listens on 0\.0\.0\.0 \(for Vite: --host 0\.0\.0\.0\)\./)
})

async function publish(host, wrapper = []) {
  const [cmd, ...args] = [...wrapper, process.execPath, join(ROOT, 'bin/mw'), 'netns', '--publish', '8080', '--', process.execPath, '-e', server(host)]
  const mw = spawn(cmd, args)
  try {
    const [published] = await Promise.all([lineMatching(mw.stderr, /published 8080 at (http:\/\/127\.0\.0\.1:\d+), (.*)\n/), lineMatching(mw.stdout, /listening/)])
    const answer = await (await fetch(published[1], { signal: AbortSignal.timeout(5000) })).text()
    assert.deepEqual(await once(mw, 'exit'), [0, null])
    return { answer, note: published[2] }
  } finally {
    if (mw.exitCode === null) mw.kill(wrapper.length ? 'SIGKILL' : 'SIGTERM')
  }
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
