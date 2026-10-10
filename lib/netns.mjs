import { spawn } from 'node:child_process'
import { mkdtempSync, rmSync } from 'node:fs'
import { createConnection, createServer } from 'node:net'
import { constants, tmpdir } from 'node:os'
import { join } from 'node:path'
import { parseArgs } from 'node:util'

// Runs inside the namespace. Over fd 3 it tells mw its pid and whether connections forwarded to 127.0.0.1 can arrive, then waits for mw to connect the network before it becomes the command.
const NAMESPACE_INIT = `
if { echo 1 > /proc/sys/net/ipv4/conf/all/route_localnet; } 2>/dev/null; then loopback=yes; else loopback=no; fi
echo "$$ $loopback" >&3
read go <&3 || exit 1
exec 3>&-
ip link set lo up
exec "$@"
`
const REACHES_LOOPBACK = "for a server inside that listens on localhost, 127.0.0.1 or all interfaces. One that listens only on ::1 can't be reached; start it with --host 127.0.0.1"
const REACHES_ALL_INTERFACES = "for a server inside that listens on 0.0.0.0 (for Vite: --host 0.0.0.0). This machine doesn't let mw netns forward to 127.0.0.1 inside, so a server that listens only on localhost can't be reached"
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
  const apiSocket = join(dir, 'api.sock')
  const namespace = spawn('unshare', ['-rn', '--fork', 'sh', '-c', NAMESPACE_INIT, '_', ...command], { stdio: ['inherit', 'inherit', 'inherit', 'pipe'] })
  const exited = new Promise((resolve) => namespace.on('exit', (code, signal) => resolve(code ?? 128 + constants.signals[signal])))
  const control = namespace.stdio[3]
  const [pid, loopback] = ((await firstLine(control)) ?? '').split(' ')
  const child = Number(pid)
  const toLoopback = loopback === 'yes'
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
      await slirpRequest(apiSocket, { execute: 'add_hostfwd', arguments: { proto: 'tcp', host_addr: '127.0.0.1', host_port: hostPort, ...(toLoopback && { guest_addr: '127.0.0.1' }), guest_port: port } })
      ctx.err(`published ${port} at http://127.0.0.1:${hostPort}, ${toLoopback ? REACHES_LOOPBACK : REACHES_ALL_INTERFACES}`)
    }
    control.end('go\n')
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

function firstLine(stream) {
  return new Promise((resolve) => {
    let text = ''
    stream.on('data', (chunk) => {
      text += chunk
      if (text.includes('\n')) resolve(text.slice(0, text.indexOf('\n')))
    })
    stream.on('close', () => resolve(null))
  })
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
