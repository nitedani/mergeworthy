export const TEST_FILE = /(^|\/)(test|tests|__tests__|spec|e2e)\/|\.(test|spec)\./

export function git(ctx, cwd, args) {
  if (!cwd) return null
  const r = ctx.exec('git', ['-C', cwd, ...args])
  return r.code === 0 ? r.stdout.trim() : null
}

export function diffBase(ctx, base) {
  const found = base ?? mergeBase(ctx, ctx.cwd, 'HEAD')
  if (!found) throw new Error('no base given, and HEAD has no merge-base with origin/HEAD')
  return found
}

export function mergeBase(ctx, cwd, rev) {
  const remoteHead = git(ctx, cwd, ['symbolic-ref', 'refs/remotes/origin/HEAD'])
  return remoteHead && git(ctx, cwd, ['merge-base', rev, remoteHead.replace('refs/remotes/', '')])
}
