import { readState, writeState } from './state.mjs'

export const BADGE = /<img src="https:\/\/github\.com\/(?:claude|openai)\.png"/

export function hasBadge(body) {
  const first = (body ?? '').split('\n').find((line) => line.trim())
  return BADGE.test(first ?? '')
}

export function parseRef(ref) {
  const url = /github\.com\/([^/\s]+)\/([^/\s]+)\/(issues|pull)\/(\d+)/.exec(ref)
  if (url) return { owner: url[1], repo: url[2], number: Number(url[4]) }
  const short = /^([^/\s]+)\/([^#\s]+)#(\d+)$/.exec(ref)
  if (short) return { owner: short[1], repo: short[2], number: Number(short[3]) }
  return null
}

export function threadUrl({ owner, repo, number }) {
  return `https://github.com/${owner}/${repo}/issues/${number}`
}

export function ghJson(ctx, args, options) {
  const r = ctx.gh(args, options)
  if (r.code !== 0) throw new Error(`gh ${args.slice(0, 3).join(' ')} failed: ${(r.stderr || r.stdout).trim().slice(0, 300)}`)
  return JSON.parse(r.stdout)
}

export function ghPaged(ctx, path) {
  return ghJson(ctx, ['api', path, '--paginate', '--slurp']).flat()
}

export function ghUser(ctx) {
  const cached = readState(ctx, 'gh-user.json', null)
  if (cached?.login) return cached
  const r = ctx.gh(['api', 'user', '--jq', '.id,.login'])
  const [id, login] = r.stdout.trim().split('\n')
  if (r.code !== 0 || !id || !login) return null
  const user = { id: Number(id), login }
  writeState(ctx, 'gh-user.json', user)
  return user
}

export function noreplyEmail(user) {
  return `${user.id}+${user.login}@users.noreply.github.com`
}

export function cwdRepo(ctx, cwd) {
  const r = ctx.gh(['repo', 'view', '--json', 'nameWithOwner', '--jq', '.nameWithOwner'], { cwd })
  return (r.code === 0 && r.stdout.trim()) || null
}
