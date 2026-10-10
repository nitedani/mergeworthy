import { spawnSync } from 'node:child_process'
import { readFileSync, readdirSync } from 'node:fs'
import { homedir } from 'node:os'
import { join } from 'node:path'

const CLOCK_TICKS = 100
const PAGE_KIB = 4

export function realCtx() {
  return {
    home: process.env.MW_HOME || join(homedir(), '.mergeworthy'),
    cwd: process.cwd(),
    now: () => Date.now(),
    exec,
    gh: (args, opts = {}) => exec(process.env.MW_GH || 'gh', args, opts),
    meminfo,
    procs,
    sleep: (ms) => new Promise((resolve) => setTimeout(resolve, ms)),
    out: (line) => process.stdout.write(line + '\n'),
    err: (line) => process.stderr.write(line + '\n'),
  }
}

function exec(cmd, args, { cwd, inherit } = {}) {
  const r = spawnSync(cmd, args, { cwd, encoding: 'utf8', maxBuffer: 256 << 20, stdio: inherit ? 'inherit' : 'pipe' })
  return { code: r.error ? 127 : r.status ?? 128, stdout: r.stdout || '', stderr: r.stderr || (r.error?.message ?? '') }
}

function meminfo() {
  const text = readFileSync('/proc/meminfo', 'utf8')
  const kib = (key) => Number(text.match(new RegExp(`^${key}:\\s+(\\d+)`, 'm'))?.[1] ?? NaN)
  return { availableKiB: kib('MemAvailable'), totalKiB: kib('MemTotal') }
}

function procs() {
  const uptime = Number(readFileSync('/proc/uptime', 'utf8').split(' ')[0])
  return readdirSync('/proc')
    .filter((entry) => /^\d+$/.test(entry))
    .flatMap((pid) => {
      try {
        return [procStat(pid, uptime)]
      } catch {
        return []
      }
    })
}

function procStat(pid, uptime) {
  const stat = readFileSync(`/proc/${pid}/stat`, 'utf8')
  const fields = stat.slice(stat.lastIndexOf(')') + 2).split(' ')
  const [utime, stime, startTicks, rssPages] = [11, 12, 19, 21].map((i) => Number(fields[i]))
  const ageSec = Math.max(uptime - startTicks / CLOCK_TICKS, 0)
  return {
    pid: Number(pid),
    comm: stat.slice(stat.indexOf('(') + 1, stat.lastIndexOf(')')),
    ageSec,
    cpuPct: ageSec ? (100 * (utime + stime)) / CLOCK_TICKS / ageSec : 0,
    rssKiB: rssPages * PAGE_KIB,
  }
}
