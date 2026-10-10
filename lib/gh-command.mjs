const API_VALUED = new Set(['-X', '--method', '-f', '-F', '--field', '--raw-field', '--input', '-H', '--header', '-q', '--jq', '-t', '--template', '--cache', '-p', '--preview', '--hostname'])
const API_FIELDS = new Set(['-f', '-F', '--field', '--raw-field'])
const FILE_FIELDS = new Set(['-F', '--field'])
const EDIT_BODY = /^(--body|-b|--body-file|-F)(=|$)/
const EDIT_TITLE = /^(--title|-t)(=|$)/
const CLOSE_COMMENT = /^(--comment|-c)(=|$)/
const BODY_FILE = { fileFlags: ['--body-file', '-F'], draftArgs: '--body-file <draft>' }
const NOTES_FILE = { fileFlags: ['--notes-file', '-F'], draftArgs: '--notes-file <draft>' }
const GIST_FILE = { fileFlags: null, draftArgs: '<draft> as a file argument' }
// Each gh command that can post text: the flags that read its text from a file (null: the file is a positional argument), the arguments that make it read a draft (null: it can't), the flags without which it posts nothing, for edits the flag a draft can replace, and the flags that take a value, from the command's --help.
const POSTING = {
  'pr comment': { ...BODY_FILE, valueFlags: ['--attach', '-b', '--body', '-F', '--body-file'] },
  'pr create': { ...BODY_FILE, valueFlags: ['-a', '--assignee', '--attach', '-B', '--base', '-b', '--body', '-F', '--body-file', '-H', '--head', '-l', '--label', '-m', '--milestone', '-p', '--project', '--recover', '-r', '--reviewer', '-T', '--template', '-t', '--title'] },
  'pr review': { ...BODY_FILE, valueFlags: ['-b', '--body', '-F', '--body-file'] },
  'pr edit': {
    ...BODY_FILE,
    postsWith: [EDIT_BODY, EDIT_TITLE],
    draftReplaces: EDIT_BODY,
    valueFlags: ['--add-assignee', '--add-label', '--add-project', '--add-reviewer', '--attach', '-B', '--base', '-b', '--body', '-F', '--body-file', '-m', '--milestone', '--remove-assignee', '--remove-label', '--remove-project', '--remove-reviewer', '-t', '--title'],
  },
  'pr close': { fileFlags: [], draftArgs: null, postsWith: [CLOSE_COMMENT], valueFlags: ['-c', '--comment'] },
  'issue comment': { ...BODY_FILE, valueFlags: ['--attach', '-b', '--body', '-F', '--body-file'] },
  'issue create': {
    ...BODY_FILE,
    valueFlags: ['-a', '--assignee', '--attach', '--blocked-by', '--blocking', '-b', '--body', '-F', '--body-file', '-l', '--label', '-m', '--milestone', '--parent', '-p', '--project', '--recover', '-T', '--template', '-t', '--title', '--type'],
  },
  'issue edit': {
    ...BODY_FILE,
    postsWith: [EDIT_BODY, EDIT_TITLE],
    draftReplaces: EDIT_BODY,
    valueFlags: [
      ...['--add-assignee', '--add-blocked-by', '--add-blocking', '--add-label', '--add-project', '--add-sub-issue', '--attach', '-b', '--body', '-F', '--body-file', '-m', '--milestone', '--parent'],
      ...['--remove-assignee', '--remove-blocked-by', '--remove-blocking', '--remove-label', '--remove-project', '--remove-sub-issue', '-t', '--title', '--type'],
    ],
  },
  'issue close': { fileFlags: [], draftArgs: null, postsWith: [CLOSE_COMMENT], valueFlags: ['-c', '--comment', '--duplicate-of', '-r', '--reason'] },
  'release create': { ...NOTES_FILE, valueFlags: ['--discussion-category', '-n', '--notes', '-F', '--notes-file', '--notes-start-tag', '--target', '-t', '--title'] },
  'release edit': { ...NOTES_FILE, valueFlags: ['--discussion-category', '-n', '--notes', '-F', '--notes-file', '--tag', '--target', '-t', '--title'] },
  'gist create': { ...GIST_FILE, valueFlags: ['-d', '--desc', '-f', '--filename'] },
  'gist edit': { ...GIST_FILE, valueFlags: ['-a', '--add', '-d', '--desc', '-f', '--filename', '-r', '--remove'] },
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
  return { group, action, args: rest, repo, target: positionals(rest, POSTING[`${group} ${action}`]?.valueFlags ?? [])[0] ?? null, api: group === 'api' ? apiRequest(words.slice(1)) : null }
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
  if (gh.api) return gh.api.fileFields.map((f) => /^body=@(.+)/.exec(f)?.[1]).filter(Boolean)
  const posting = POSTING[`${gh.group} ${gh.action}`]
  if (!posting) return []
  return posting.fileFlags ? flagValues(gh.args, posting.fileFlags) : positionals(gh.args, posting.valueFlags)
}

function apiPosts({ method, path, fields, input }) {
  if (path === 'graphql') return fields.some((f) => POSTING_MUTATION.test(f))
  return ['POST', 'PATCH', 'PUT'].includes(method) && POSTING_PATH.test(path ?? '') && (sendsBody({ fields, input }) || fields.some((f) => TITLE_FIELD.test(f)))
}

function sendsBody({ fields, input }) {
  return input !== null || fields.some((f) => BODY_FIELD.test(f))
}

function positionals(args, valueFlags) {
  return args.filter((a, i) => !a.startsWith('-') && !valueFlags.includes(args[i - 1]))
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
  const fileFields = []
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
    if (FILE_FIELDS.has(flag)) fileFields.push(value)
  }
  return { method: method ?? (fields.length || input !== null ? 'POST' : 'GET'), path, fields, fileFields, input }
}

function splitFlag(arg) {
  if (arg.startsWith('--') && arg.includes('=')) return [arg.slice(0, arg.indexOf('=')), arg.slice(arg.indexOf('=') + 1)]
  if (/^-[A-Za-z]./.test(arg) && API_VALUED.has(arg.slice(0, 2))) return [arg.slice(0, 2), arg.slice(2)]
  return [arg, undefined]
}
