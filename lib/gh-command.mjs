const REPO_FLAGS = ['-R', '--repo']
const API_VALUE_FLAGS = ['-X', '--method', '-f', '--raw-field', '-F', '--field', '--input', '-H', '--header', '-q', '--jq', '-t', '--template', '--cache', '-p', '--preview', '--hostname']
const BODY_FLAGS = ['-b', '--body', '-F', '--body-file']
const TITLE_FLAGS = ['-t', '--title']
const POSTING_PATH = /(^|\/)(issues|pulls|comments|reviews|replies|releases)(\/|\?|$)/
const BODY_FIELD = /^body=|\[body\]=/
const TITLE_FIELD = /^(?:title|name)=/
const POSTING_MUTATION = /\bmutation\b[\s\S]*\b(add|update|create|submit)\w*(Comment|Review|Issue|PullRequest)/

const withDraft = (args) => `Save the text in a draft file, get it reviewed, and post it with \`mw post <draft> -- <this gh command with ${args}>\`, which runs both checks first`
const TITLE_ADVICE = "mw post can't read a title from a draft file. Get the new title reviewed, then run this command again with the bypass line below"
const BODY = { reads: 'flag', fileFlags: ['-F', '--body-file'], advice: () => withDraft('--body-file <draft>') }
const NOTES = { reads: 'flag', fileFlags: ['-F', '--notes-file'], advice: () => withDraft('--notes-file <draft>') }
const GIST = { reads: 'file argument', advice: () => 'Save the text in a draft file, get it reviewed, and post it with `mw post <draft> -- <this gh command>`, with the draft among the files it uploads, which runs both checks first' }
const EDIT = { ...BODY, postsWith: [...BODY_FLAGS, ...TITLE_FLAGS], advice: (gh) => (BODY_FLAGS.some((flag) => gh.flags[flag]) ? withDraft('--body-file <draft>') : TITLE_ADVICE) }
const CLOSE = {
  reads: 'nothing',
  postsWith: ['-c', '--comment'],
  advice: (gh) =>
    `Save the comment in a draft file, get it reviewed, and post it with \`mw post <draft> -- gh ${gh.group} comment ${gh.target ?? '<number>'}${gh.repo ? ` -R ${gh.repo}` : ''} --body-file <draft>\`, which runs both checks first. Then close without --comment`,
}
const API = { reads: 'body field', valueFlags: API_VALUE_FLAGS, advice: (gh) => (gh.api.path === 'graphql' || sendsBody(gh.api) ? withDraft('-F body=@<draft>') : TITLE_ADVICE) }

// Each gh command that can post text. valueFlags are the flags that take a value, from the command's --help; postsWith, when given, are the flags without which it posts nothing.
const POSTING = {
  'pr comment': { ...BODY, valueFlags: ['--attach', ...BODY_FLAGS] },
  'pr create': { ...BODY, valueFlags: ['-a', '--assignee', '--attach', '-B', '--base', ...BODY_FLAGS, '-H', '--head', '-l', '--label', '-m', '--milestone', '-p', '--project', '--recover', '-r', '--reviewer', '-T', '--template', ...TITLE_FLAGS] },
  'pr review': { ...BODY, valueFlags: BODY_FLAGS },
  'pr edit': {
    ...EDIT,
    valueFlags: ['--add-assignee', '--add-label', '--add-project', '--add-reviewer', '--attach', '-B', '--base', ...BODY_FLAGS, '-m', '--milestone', '--remove-assignee', '--remove-label', '--remove-project', '--remove-reviewer', ...TITLE_FLAGS],
  },
  'pr close': { ...CLOSE, valueFlags: ['-c', '--comment'] },
  'issue comment': { ...BODY, valueFlags: ['--attach', ...BODY_FLAGS] },
  'issue create': {
    ...BODY,
    valueFlags: ['-a', '--assignee', '--attach', '--blocked-by', '--blocking', ...BODY_FLAGS, '-l', '--label', '-m', '--milestone', '--parent', '-p', '--project', '--recover', '-T', '--template', ...TITLE_FLAGS, '--type'],
  },
  'issue edit': {
    ...EDIT,
    valueFlags: [
      ...['--add-assignee', '--add-blocked-by', '--add-blocking', '--add-label', '--add-project', '--add-sub-issue', '--attach', ...BODY_FLAGS, '-m', '--milestone', '--parent'],
      ...['--remove-assignee', '--remove-blocked-by', '--remove-blocking', '--remove-label', '--remove-project', '--remove-sub-issue', ...TITLE_FLAGS, '--type'],
    ],
  },
  'issue close': { ...CLOSE, valueFlags: ['-c', '--comment', '--duplicate-of', '-r', '--reason'] },
  'release create': { ...NOTES, valueFlags: ['--discussion-category', '-n', '--notes', '-F', '--notes-file', '--notes-start-tag', '--target', ...TITLE_FLAGS] },
  'release edit': { ...NOTES, valueFlags: ['--discussion-category', '-n', '--notes', '-F', '--notes-file', '--tag', '--target', ...TITLE_FLAGS] },
  'gist create': { ...GIST, valueFlags: ['-d', '--desc', '-f', '--filename'] },
  'gist edit': { ...GIST, valueFlags: ['-a', '--add', '-d', '--desc', '-f', '--filename', '-r', '--remove'] },
}
const TEXT_FILES = {
  flag: (gh, row) => row.fileFlags.flatMap((flag) => gh.flags[flag] ?? []),
  'file argument': (gh) => gh.positionals,
  'body field': (gh) => gh.api.fileFields.map((f) => /^body=@(.+)/.exec(f)?.[1]).filter(Boolean),
  nothing: () => [],
}

export function ghCommand(args) {
  const { positionals: [group, ...afterGroup] } = scan(args, REPO_FLAGS)
  const isApi = group === 'api'
  const action = isApi ? null : afterGroup[0]
  const { positionals, flags } = scan(args, [...REPO_FLAGS, ...(rowOf(group, action)?.valueFlags ?? [])])
  const rest = positionals.slice(isApi ? 1 : 2)
  const repo = REPO_FLAGS.map((flag) => flags[flag]?.at(-1)).find(Boolean) ?? null
  return { group, action, positionals: rest, flags, repo, target: isApi ? null : (rest[0] ?? null), api: isApi ? apiRequest(rest, flags) : null }
}

export function ghName(gh) {
  return gh.api ? `gh api ${gh.api.path}` : `gh ${gh.group} ${gh.action}`
}

export function postsToGitHub(gh) {
  if (gh.api) return apiPosts(gh.api)
  const row = rowOf(gh.group, gh.action)
  return Boolean(row) && (!row.postsWith || row.postsWith.some((flag) => gh.flags[flag]))
}

/** A boolean flag counts as set unless it says `=false`, as gh reads it. */
export function isSet(gh, flag) {
  return gh.flags[flag]?.some((value) => value !== 'false') ?? false
}

export function postAdvice(gh) {
  return rowOf(gh.group, gh.action).advice(gh)
}

export function textFiles(gh) {
  const row = rowOf(gh.group, gh.action)
  return row ? TEXT_FILES[row.reads](gh, row) : []
}

function rowOf(group, action) {
  return group === 'api' ? API : POSTING[`${group} ${action}`]
}

function scan(args, valueFlags) {
  const positionals = []
  const flags = {}
  for (let i = 0; i < args.length; i++) {
    const arg = args[i]
    if (!arg.startsWith('-') || arg === '-') {
      positionals.push(arg)
      continue
    }
    const [name, value] = splitFlag(arg, valueFlags) ?? [arg, valueFlags.includes(arg) ? args[++i] : true]
    if (value !== undefined) (flags[name] ??= []).push(value)
  }
  return { positionals, flags }
}

function splitFlag(arg, valueFlags) {
  if (arg.startsWith('--') && arg.includes('=')) return [arg.slice(0, arg.indexOf('=')), arg.slice(arg.indexOf('=') + 1)]
  if (!arg.startsWith('--') && arg.length > 2 && valueFlags.includes(arg.slice(0, 2))) return [arg.slice(0, 2), arg.slice(2)]
  return null
}

function apiRequest([path = null], flags) {
  const values = (...names) => names.flatMap((name) => flags[name] ?? [])
  const fileFields = values('-F', '--field')
  const fields = [...values('-f', '--raw-field'), ...fileFields]
  const input = values('--input').at(-1) ?? null
  const method = values('-X', '--method').at(-1)?.toUpperCase()
  return { method: method ?? (fields.length || input !== null ? 'POST' : 'GET'), path, fields, fileFields, input }
}

function apiPosts({ method, path, fields, input }) {
  if (path === 'graphql') return fields.some((f) => POSTING_MUTATION.test(f))
  return ['POST', 'PATCH', 'PUT'].includes(method) && POSTING_PATH.test(path ?? '') && (sendsBody({ fields, input }) || fields.some((f) => TITLE_FIELD.test(f)))
}

function sendsBody({ fields, input }) {
  return input !== null || fields.some((f) => BODY_FIELD.test(f))
}
