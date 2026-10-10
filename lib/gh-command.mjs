const API_VALUED = new Set(['-X', '--method', '-f', '-F', '--field', '--raw-field', '--input', '-H', '--header', '-q', '--jq', '-t', '--template', '--cache', '-p', '--preview', '--hostname'])
const API_BODY = new Set(['-f', '-F', '--field', '--raw-field', '--input'])

export function ghCommand(args) {
  const words = []
  let repo = null
  for (let i = 0; i < args.length; i++) {
    if (args[i] === '-R' || args[i] === '--repo') repo = args[++i]
    else if (args[i].startsWith('--repo=')) repo = args[i].slice(7)
    else words.push(args[i])
  }
  return { group: words[0], action: words[1], args: words.slice(2), repo }
}

export function apiRequest(args) {
  let method = null
  let path = null
  const fields = []
  for (let i = 0; i < args.length; i++) {
    const [flag, inline] = splitFlag(args[i])
    if (!API_VALUED.has(flag)) {
      if (!flag.startsWith('-')) path ??= args[i]
      continue
    }
    const value = inline ?? args[++i] ?? ''
    if (flag === '-X' || flag === '--method') method = value.toUpperCase()
    if (API_BODY.has(flag)) fields.push(value)
  }
  return { method: method ?? (fields.length ? 'POST' : 'GET'), path, fields }
}

function splitFlag(arg) {
  if (arg.startsWith('--') && arg.includes('=')) return [arg.slice(0, arg.indexOf('=')), arg.slice(arg.indexOf('=') + 1)]
  if (/^-[A-Za-z]./.test(arg) && API_VALUED.has(arg.slice(0, 2))) return [arg.slice(0, 2), arg.slice(2)]
  return [arg, undefined]
}
