import { parseArgs } from 'node:util'
import { ghJson, ghPaged, ghUser } from './github.mjs'
import { DAY } from './time.mjs'

export function followupsCommand(argv, ctx) {
  const { positionals, values } = parseArgs({ args: argv, allowPositionals: true, options: { days: { type: 'string', default: '14' } } })
  const repo = positionals[0]
  if (!/^[^/\s]+\/[^/\s]+$/.test(repo ?? '')) return 2
  const login = ghUser(ctx)?.login
  if (!login) throw new Error('gh api user failed; is gh logged in?')
  const since = new Date(ctx.now() - Number(values.days) * DAY).toISOString().slice(0, 10)
  const prs = ghJson(ctx, ['search', 'prs', '--author', login, '--repo', repo, '--merged', '--merged-at', `>=${since}`, '--json', 'number,title,url,closedAt'])
  for (const pr of prs) {
    ctx.out(`#${pr.number} ${pr.title}`)
    for (const { commit, files } of followupCommits(ctx, repo, pr, login)) {
      ctx.out(`  ${commit.sha.slice(0, 7)} ${commit.author?.login ?? commit.commit.author.name} ${commit.commit.author.date} ${commit.commit.message.split('\n')[0]} (${files.join(', ')})`)
    }
  }
  return 0
}

function followupCommits(ctx, repo, pr, login) {
  const bySha = new Map()
  for (const { filename } of ghPaged(ctx, `repos/${repo}/pulls/${pr.number}/files`)) {
    const commits = ghJson(ctx, ['api', `repos/${repo}/commits?path=${encodeURIComponent(filename)}&since=${pr.closedAt}`])
    for (const commit of commits.filter((c) => c.author?.login !== login)) {
      if (!bySha.has(commit.sha)) bySha.set(commit.sha, { commit, files: [] })
      bySha.get(commit.sha).files.push(filename)
    }
  }
  return [...bySha.values()]
}
