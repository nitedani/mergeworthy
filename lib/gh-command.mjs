const API_VALUED = new Set(['-X', '--method', '-f', '-F', '--field', '--raw-field', '--input', '-H', '--header', '-q', '--jq', '-t', '--template', '--cache', '-p', '--preview', '--hostname'])
const API_FIELDS = new Set(['-f', '-F', '--field', '--raw-field'])
const POSTING_ACTIONS = { pr: ['comment', 'create', 'review'], issue: ['comment', 'create'], release: ['create', 'edit'], gist: ['create', 'edit'] }
const TEXT_FLAGS = { edit: /^(--body|-b|--body-file|-F|--title|-t)(=|$)/, close: /^(--comment|-c)(=|$)/ }
const POSTING_PATH = /(^|\/)(issues|pulls|comments|reviews|replies|releases)(\/|\?|$)/
const TEXT_FIELD = /^(?:body|title|name)=|\[body\]=/
const POSTING_MUTATION = /\bmutation\b[\s\S]*\b(add|update|create|submit)\w*(Comment|Review|Issue|PullRequest)/

export function ghCommand(args) {
  const words = []
  let repo = null
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '-R' || args[i] === '--repo') repo = args[++i]
    else if (args[i].startsWith('--repo=')) repo = args[i].slice(7)
    else words.push(args[i])
  }
  return { group: words[0], action: words[1], args: words.slice(2), repo, api: words[0] === 'api' ? apiRequest(words.slice(1)) : null }
}

export function ghName(gh) {
  return gh.api ? `gh api ${gh.api.path}` : `gh ${gh.group} ${gh.action}`
}

export function postsToGitHub(gh) {
  if (POSTING_ACTIONS[gh.group]?.includes(gh.action)) return true
  if ((gh.group === 'pr' || gh.group === 'issue') && TEXT_FLAGS[gh.action]) return gh.args.some((a) => TEXT_FLAGS[gh.action].test(a))
  if (!gh.api) return false
  const { method, path, fields, input } = gh.api
  if (path === 'graphql') return fields.some((f) => POSTING_MUTATION.test(f))
  return ['POST', 'PATCH', 'PUT'].includes(method) && POSTING_PATH.test(path ?? '') && (input !== null || fields.some((f) => TEXT_FIELD.test(f)))
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
