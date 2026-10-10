import { mkdirSync, readFileSync, renameSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'

export function readState(ctx, name, fallback) {
  try {
    return JSON.parse(readFileSync(join(ctx.home, name), 'utf8'))
  } catch {
    return fallback
  }
}

export function writeState(ctx, name, value) {
  const file = join(ctx.home, name)
  mkdirSync(dirname(file), { recursive: true })
  const tmp = `${file}.${process.pid}.tmp`
  writeFileSync(tmp, JSON.stringify(value, null, 2) + '\n')
  renameSync(tmp, file)
}

export function prune(map, now, maxAgeMs, at = (v) => v) {
  return Object.fromEntries(Object.entries(map).filter(([, v]) => now - at(v) < maxAgeMs))
}
