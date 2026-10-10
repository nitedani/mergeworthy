import { spawn } from 'node:child_process'
import { mkdtempSync, rmSync } from 'node:fs'
import { writeFile } from 'node:fs/promises'
import { createConnection, createServer } from 'node:net'
import { constants, tmpdir } from 'node:os'
import { join } from 'node:path'
import { parseArgs } from 'node:util'

const NAMESPACE_INIT = 'read _ < "$1"; ip link set lo up; echo 1 > /proc/sys/net/ipv4/conf/all/route_localnet; shift; exec "$@"'
const REQUIRED = [
  ['slirp4netns', 'slirp4netns is not installed; run the server on a free port of your own on the host instead'],
  ['unshare', 'unshare is not installed'],
]

export async function netnsCommand(argv, ctx) {
  const split = argv.indexOf('--')
  const command = argv.slice(split + 1)
  const { values } = parseArgs({ args: argv.slice(0, Math.max(split, 0)), options: { publish: { type: 'string' } } })
  const ports = values.publish?.split(',').map(Number) ?? []
  if (split < 0 || !command.length || !ports.every((port) => Number.isInteger(port) && port > 0)) return 2
  const missing = REQUIRED.find(([bin]) => ctx.exec('sh', ['-c', 'command -v "$1"', '_', bin]).code !== 0)
  if (missing) {
    ctx.err(`mw netns: ${missing[1]}`)
    return 127
  }
  const dir = mkdtempSync(join(tmpdir(), 'mw-netns-'))
  try {
    return await runInNamespace(ctx, dir, command, ports)
  } finally {
    rmSync(dir, { recursive: true, force: true })
  }
}

async function runInNamespace(ctx, dir, command, ports) {
  const fifo = join(dir, 'go')
  const apiSocket = join(dir, 'api.sock')
  if (ctx.exec('mkfifo', [fifo]).code !== 0) throw new Error(`mkfifo ${fifo} failed`)
  const namespace = spawn('unshare', ['-rn', '--fork', 'sh', '-c', NAMESPACE_INIT, '_', fifo, ...command], { stdio: 'inherit' })
  const exited = new Promise((resolve) => namespace.on('exit', (code, signal) => resolve(code ?? 128 + constants.signals[signal])))
  const child = await childPid(ctx, namespace.pid)
  if (!child) {
    namespace.kill('SIGKILL')
    throw new Error("the private network namespace didn't start")
  }
  const slirp = spawn('slirp4netns', ['--configure', '--mtu=65520', '--disable-host-loopback', '--ready-fd=3', '--api-socket', apiSocket, String(child), 'tap0'], {
    stdio: ['ignore', 'ignore', 'pipe', 'pipe'],
  })
  try {
    await slirpReady(slirp)
    for (const port of ports) {
      const hostPort = await freePort()
      await slirpRequest(apiSocket, { execute: 'add_hostfwd', arguments: { proto: 'tcp', host_addr: '127.0.0.1', host_port: hostPort, guest_addr: '127.0.0.1', guest_port: port } })
      ctx.err(`published ${port} at http://127.0.0.1:${hostPort}, for a server inside that listens on localhost, 127.0.0.1 or all interfaces. One that listens only on ::1 can't be reached; start it with --host 127.0.0.1`)
    }
    await writeFile(fifo, 'go\n')
    for (const signal of ['SIGINT', 'SIGTERM']) process.on(signal, () => process.kill(child, signal))
    return await exited
  } catch (error) {
    process.kill(child, 'SIGKILL')
    await exited
    throw error
  } finally {
    slirp.kill()
  }
}

async function childPid(ctx, parent) {
  for (let attempt = 0; attempt < 100; attempt++) {
    const pid = Number(ctx.exec('ps', ['-o', 'pid=', '--ppid', String(parent)]).stdout.trim().split('\n')[0])
    if (pid) return pid
    await ctx.sleep(50)
  }
  return null
}

function slirpReady(slirp) {
  let log = ''
  slirp.stdio[2].on('data', (chunk) => (log += chunk))
  return new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error(`slirp4netns didn't come up: ${log.trim()}`)), 10_000)
    slirp.stdio[3].once('data', () => {
      clearTimeout(timer)
      resolve()
    })
    slirp.once('exit', () => {
      clearTimeout(timer)
      reject(new Error(`slirp4netns exited: ${log.trim()}`))
    })
  })
}

function freePort() {
  return new Promise((resolve, reject) => {
    const server = createServer().listen(0, '127.0.0.1', () => {
      const { port } = server.address()
      server.close(() => resolve(port))
    })
    server.on('error', reject)
  })
}

function slirpRequest(socket, request) {
  return new Promise((resolve, reject) => {
    let reply = ''
    const connection = createConnection(socket, () => connection.end(JSON.stringify(request)))
    connection.on('data', (chunk) => (reply += chunk))
    connection.on('error', reject)
    connection.on('end', () => {
      const { error } = JSON.parse(reply)
      if (error) reject(new Error(`slirp4netns ${request.execute}: ${JSON.stringify(error)}`))
      else resolve()
    })
  })
}
