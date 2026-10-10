const API_VALUED = new Set(['-X', '--method', '-f', '-F', '--field', '--raw-field', '--input', '-H', '--header', '-q', '--jq', '-t', '--template', '--cache', '-p', '--preview', '--hostname'])
const API_FIELDS = new Set(['-f', '-F', '--field', '--raw-field'])
const VALUE_FLAGS = new Set([
  ...['-b', '--body', '-F', '--body-file', '--notes-file', '-c', '--comment', '-t', '--title', '-n', '--notes', '-r', '--reason', '--reviewer', '--remove', '-a', '--assignee', '--add'],
  ...['-l', '--label', '-m', '--milestone', '-p', '--project', '-B', '--base', '-H', '--head', '-T', '--template', '--desc', '--filename', '--duplicate-of', '--parent', '--type'],
  ...['--add-assignee', '--remove-assignee', '--add-label', '--remove-label', '--add-project', '--remove-project', '--add-reviewer', '--remove-reviewer'],
  ...['--add-blocked-by', '--remove-blocked-by', '--add-blocking', '--remove-blocking', '--add-sub-issue', '--remove-sub-issue', '--blocked-by', '--blocking'],
  ...['--recover', '--attach', '--tag', '--target', '--discussion-category', '--notes-start-tag'],
])
const EDIT_BODY = /^(--body|-b|--body-file|-F)(=|$)/
const EDIT_TITLE = /^(--title|-t)(=|$)/
const CLOSE_COMMENT = /^(--comment|-c)(=|$)/
const BODY_FILE = { fileFlags: ['--body-file', '-F'], draftArgs: '--body-file <draft>' }
const NOTES_FILE = { fileFlags: ['--notes-file', '-F'], draftArgs: '--notes-file <draft>' }
const GIST_FILE = { fileFlags: null, draftArgs: '<draft> as a file argument' }
// Each gh command that can post text: the flags that read its text from a file (null: the file is a positional argument), the arguments that make it read a draft (null: it can't), the flags without which it posts nothing, and for edits, the flag a draft can replace.
const POSTING = {
  'pr comment': BODY_FILE,
  'pr create': BODY_FILE,
  'pr review': BODY_FILE,
  'pr edit': { ...BODY_FILE, postsWith: [EDIT_BODY, EDIT_TITLE], draftReplaces: EDIT_BODY },
  'pr close': { fileFlags: [], draftArgs: null, postsWith: [CLOSE_COMMENT] },
  'issue comment': BODY_FILE,
  'issue create': BODY_FILE,
  'issue edit': { ...BODY_FILE, postsWith: [EDIT_BODY, EDIT_TITLE], draftReplaces: EDIT_BODY },
  'issue close': { fileFlags: [], draftArgs: null, postsWith: [CLOSE_COMMENT] },
  'release create': NOTES_FILE,
  'release edit': NOTES_FILE,
  'gist create': GIST_FILE,
  'gist edit': GIST_FILE,
}
const POSTING_PATH = /(^|\/)(issues|pulls|comments|reviews|replies|releases)(\/|\?|$)/
const BODY_FIELD = /^body=|\[body\]=/
const TITLE_FIELD = /^(?:title|name)=/
const POSTING_MUTATION = /\bmutation\b[\s\S]*\b(add|update|create|submit)\w*(Comment|Review|Issue|PullRequest)/

export function ghCommand(args) {
  const words = []
  let repo = null
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '-R' || args[i] === '--repo') repo = args[++i]
    else if (args[i].startsWith('--repo=')) repo = args[i].slice(7)
    else words.push(args[i])
  }
  const [group, action, ...rest] = words
  return { group, action, args: rest, repo, target: positionals(rest)[0] ?? null, api: group === 'api' ? apiRequest(words.slice(1)) : null }
}

export function ghName(gh) {
  return gh.api ? `gh api ${gh.api.path}` : `gh ${gh.group} ${gh.action}`
}

export function postsToGitHub(gh) {
  if (gh.api) return apiPosts(gh.api)
  const posting = POSTING[`${gh.group} ${gh.action}`]
  return Boolean(posting) && (!posting.postsWith || gh.args.some((a) => posting.postsWith.some((flag) => flag.test(a))))
}

export function draftArgs(gh) {
  if (gh.api) return gh.api.path === 'graphql' || sendsBody(gh.api) ? '-F body=@<draft>' : null
  const posting = POSTING[`${gh.group} ${gh.action}`]
  if (posting?.draftReplaces && !gh.args.some((a) => posting.draftReplaces.test(a))) return null
  return posting?.draftArgs ?? null
}

export function textFiles(gh) {
  if (gh.api) return [gh.api.input, ...gh.api.fields.map((f) => /^body=@(.+)/.exec(f)?.[1])].filter(Boolean)
  const posting = POSTING[`${gh.group} ${gh.action}`]
  if (!posting) return []
  return posting.fileFlags ? flagValues(gh.args, posting.fileFlags) : positionals(gh.args)
}

function apiPosts({ method, path, fields, input }) {
  if (path === 'graphql') return fields.some((f) => POSTING_MUTATION.test(f))
  return ['POST', 'PATCH', 'PUT'].includes(method) && POSTING_PATH.test(path ?? '') && (sendsBody({ fields, input }) || fields.some((f) => TITLE_FIELD.test(f)))
}

function sendsBody({ fields, input }) {
  return input !== null || fields.some((f) => BODY_FIELD.test(f))
}

function positionals(args) {
  return args.filter((a, i) => !a.startsWith('-') && !VALUE_FLAGS.has(args[i - 1]))
}

function flagValues(args, flags) {
  return args.flatMap((a, i) => {
    if (flags.includes(a)) return args[i + 1] === undefined ? [] : [args[i + 1]]
    const inline = flags.find((flag) => flag.startsWith('--') && a.startsWith(`${flag}=`))
    return inline ? [a.slice(inline.length + 1)] : []
  })
}

function apiRequest(args) {
  let method = null
  let path = null
  let input = null
  const fields = []
  for (let i = 0; i < args.length; i++) {
    const [flag, inline] = splitFlag(args[i])
    if (!API_VALUED.has(flag)) {
      if (!flag.startsWith('-')) path ??= args[i]
      continue
    }
    const value = inline ?? args[++i] ?? ''
    if (flag === '-X' || flag === '--method') method = value.toUpperCase()
    if (flag === '--input') input = value
    if (API_FIELDS.has(flag)) fields.push(value)
  }
  return { method: method ?? (fields.length || input !== null ? 'POST' : 'GET'), path, fields, input }
}

function splitFlag(arg) {
  if (arg.startsWith('--') && arg.includes('=')) return [arg.slice(0, arg.indexOf('=')), arg.slice(arg.indexOf('=') + 1)]
  if (/^-[A-Za-z]./.test(arg) && API_VALUED.has(arg.slice(0, 2))) return [arg.slice(0, 2), arg.slice(2)]
  return [arg, undefined]
}
