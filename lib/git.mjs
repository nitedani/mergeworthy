export function git(ctx, cwd, args) {
  if (!cwd) return null
  const r = ctx.exec('git', ['-C', cwd, ...args])
  return r.code === 0 ? r.stdout.trim() : null
}

export function diffBase(ctx, base) {
  const found = base ?? mergeBase(ctx, ctx.cwd, 'HEAD')
  if (!found) throw new Error('no base branch or commit was given, and none was found: origin/HEAD is not set, or HEAD shares no history with it. Pass the base as the first argument, like main')
  return found
}

export function mergeBase(ctx, cwd, rev) {
  const remoteHead = git(ctx, cwd, ['symbolic-ref', 'refs/remotes/origin/HEAD'])
  return remoteHead && git(ctx, cwd, ['merge-base', rev, remoteHead.replace('refs/remotes/', '')])
}
