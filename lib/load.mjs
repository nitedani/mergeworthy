import { availableParallelism, loadavg } from 'node:os'

const GROUPS = {
  claude: ['claude'],
  codex: ['codex'],
  chrome: ['chrome', 'chromium', 'headless_shell'],
}

export function loadCommand(argv, ctx) {
  const mem = ctx.meminfo()
  const procs = ctx.procs()
  ctx.out(`MemAvailable: ${gib(mem.availableKiB)} GiB of ${gib(mem.totalKiB)} GiB`)
  ctx.out(`loadavg: ${loadavg().map((n) => n.toFixed(2)).join(' ')} on ${availableParallelism()} cores`)
  for (const [group, comms] of Object.entries(GROUPS)) {
    const members = procs.filter((p) => comms.includes(p.comm))
    ctx.out(`${group}: ${members.length} processes, ${gib(members.reduce((sum, p) => sum + p.rssKiB, 0))} GiB of memory in use (RSS)`)
  }
  return 0
}

export function agentProcesses(procs) {
  return procs.filter((p) => [...GROUPS.claude, ...GROUPS.codex].includes(p.comm))
}

export function describeProcess(p) {
  return `pid ${p.pid} (${p.comm}, ${age(p.ageSec)}, ${Math.round(p.cpuPct)}% cpu, ${gib(p.rssKiB)} GiB)`
}

export function gib(kib) {
  return (kib / 2 ** 20).toFixed(1)
}

function age(sec) {
  const h = Math.floor(sec / 3600)
  const m = Math.floor((sec % 3600) / 60)
  return h ? `${h}h ${m}m` : `${m}m`
}
