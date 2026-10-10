import { homedir } from 'node:os'
import { basename, resolve } from 'node:path'

const SEPARATORS = new Set([';', '&&', '||', '|', '|&', '&', '\n', '(', ')', ';;'])
const OPERATOR = /(?:&&|\|\||;;|\|&|&>>|&>|[;&|()]|\d*(?:<<<|<<-|<<|<>|<&|>&|>>|>\||<|>))/y
const ASSIGNMENT = /^[A-Za-z_][A-Za-z0-9_]*=/
const WRAPPERS = {
  sudo: { valued: ['-u', '-g', '-U', '-C', '-D', '-h', '-p', '-r', '-t', '-T'] },
  env: { valued: ['-u', '-C', '-S'], assignments: true },
  command: {},
  nohup: {},
  time: {},
  exec: { valued: ['-a'] },
  timeout: { valued: ['-s', '-k'], positional: 1 },
  nice: { valued: ['-n'] },
}
const SHELLS = new Set(['bash', 'sh', 'zsh', 'dash'])

export function parse(command, cwd) {
  const parsed = { commands: [], comments: [] }
  parseInto(command, cwd, false, parsed)
  return parsed
}

function parseInto(src, cwd, outerWhile, parsed) {
  const level = { parsed, cwd, outerWhile, loops: [], pipeFrom: null }
  let tokens = []
  for (const token of lex(src, parsed.comments)) {
    if (token.type !== 'op') tokens.push(token)
    else if (SEPARATORS.has(token.value)) {
      finish(level, tokens, token.value)
      tokens = []
    }
  }
  finish(level, tokens, '\n')
}

function finish(level, tokens, separator) {
  const words = dropRedirects(tokens)
  for (const word of words) for (const inner of word.subs) parseInto(inner, level.cwd, inWhile(level), level.parsed)
  const argv = stripReserved(words, level)
  if (!argv) return
  while (argv.length && ASSIGNMENT.test(argv[0])) argv.shift()
  const unwrapped = unwrap(argv)
  if (!unwrapped.length) return
  const cmd = {
    argv: unwrapped,
    cwd: level.cwd,
    background: separator === '&',
    inWhile: inWhile(level),
  }
  if (level.pipeFrom) level.pipeFrom.pipeTo = level.parsed.commands.length
  level.pipeFrom = separator === '|' || separator === '|&' ? cmd : null
  level.parsed.commands.push(cmd)
  if (basename(unwrapped[0]) === 'cd') level.cwd = cdTarget(unwrapped, level.cwd)
  const script = shellScript(unwrapped)
  if (script !== undefined) parseInto(script, cmd.cwd, cmd.inWhile, level.parsed)
}

function dropRedirects(tokens) {
  const words = []
  for (let i = 0; i < tokens.length; i++) {
    if (tokens[i].type === 'redirect') i++
    else words.push(tokens[i])
  }
  return words
}

function inWhile(level) {
  return level.outerWhile || level.loops.includes('while')
}

function stripReserved(words, level) {
  let i = 0
  while (i < words.length && words[i].plain) {
    const w = words[i].value
    if (w === 'while' || w === 'until') level.loops.push('while')
    else if (w === 'done') level.loops.pop()
    else if (w === 'for' || w === 'select') {
      level.loops.push('for')
      return null
    } else if (w === 'case' || w === 'function') return null
    else if (!['if', 'then', 'else', 'elif', 'do', 'fi', 'esac', '!', '{', '}'].includes(w)) break
    i++
  }
  const argv = words.slice(i).map((w) => w.value)
  return argv.length ? argv : null
}

function unwrap(argv) {
  for (;;) {
    const name = basename(argv[0] ?? '')
    const wrapper = WRAPPERS[name]
    if (!wrapper || (name === 'command' && argv.some((a) => a === '-v' || a === '-V'))) return argv
    let i = 1
    while (i < argv.length && argv[i].startsWith('-') && argv[i] !== '-') {
      if (argv[i] === '--') {
        i++
        break
      }
      i += wrapper.valued?.includes(argv[i]) ? 2 : 1
    }
    if (wrapper.assignments) while (i < argv.length && ASSIGNMENT.test(argv[i])) i++
    argv = argv.slice(i + (wrapper.positional ?? 0))
  }
}

function cdTarget(argv, cwd) {
  const dir = argv.slice(1).find((a) => !/^-[LPe@]+$/.test(a))
  if (dir === undefined || dir === '~') return homedir()
  if (dir === '-' || /[$`]/.test(dir)) return null
  if (dir.startsWith('~/')) return resolve(homedir(), dir.slice(2))
  if (dir.startsWith('/')) return resolve(dir)
  return cwd ? resolve(cwd, dir) : null
}

function shellScript(argv) {
  if (!SHELLS.has(basename(argv[0]))) return undefined
  let i = 1
  let hasC = false
  while (i < argv.length && /^[-+]/.test(argv[i])) {
    if (argv[i] === '-o' || argv[i] === '+o') i++
    else if (/^-[a-zA-Z]*c[a-zA-Z]*$/.test(argv[i])) hasC = true
    i++
  }
  return hasC ? argv[i] : undefined
}

function lex(src, comments) {
  const tokens = []
  const heredocs = []
  let i = 0
  while (i < src.length) {
    const c = src[i]
    if (c === '\\' && src[i + 1] === '\n') i += 2
    else if (c === ' ' || c === '\t' || c === '\r') i++
    else if (c === '\n') {
      tokens.push({ type: 'op', value: '\n' })
      i = skipHeredocs(src, i + 1, heredocs)
    } else if (c === '#') {
      const end = lineEnd(src, i)
      comments.push(src.slice(i, end))
      i = end
    } else if ((c === '<' || c === '>') && src[i + 1] === '(') {
      const close = matchParen(src, i + 2)
      tokens.push({ type: 'word', value: src.slice(i, close + 1), plain: false, subs: [src.slice(i + 2, close)] })
      i = close + 1
    } else {
      OPERATOR.lastIndex = i
      const op = OPERATOR.exec(src)?.[0]
      if (op && /[<>]/.test(op)) {
        tokens.push({ type: 'redirect', value: op })
        i += op.length
        if (op.endsWith('<<') || op.endsWith('<<-')) {
          while (src[i] === ' ' || src[i] === '\t') i++
          const word = readWord(src, i)
          tokens.push(word)
          heredocs.push({ delimiter: word.value, strip: op.endsWith('-') })
          i = word.end
        }
      } else if (op) {
        tokens.push({ type: 'op', value: op })
        i += op.length
      } else {
        const word = readWord(src, i)
        tokens.push(word)
        i = word.end
      }
    }
  }
  return tokens
}

function skipHeredocs(src, i, heredocs) {
  for (const { delimiter, strip } of heredocs.splice(0)) {
    while (i < src.length) {
      const end = lineEnd(src, i)
      const line = src.slice(i, end)
      i = end + 1
      if ((strip ? line.replace(/^\t+/, '') : line) === delimiter) break
    }
  }
  return Math.min(i, src.length)
}

function lineEnd(src, i) {
  const end = src.indexOf('\n', i)
  return end === -1 ? src.length : end
}

function readWord(src, start) {
  let value = ''
  let plain = true
  const subs = []
  let i = start
  while (i < src.length && !' \t\r\n;&|<>()'.includes(src[i])) {
    plain &&= !`'"\\$\``.includes(src[i])
    const [text, next] = readPiece(src, i, subs)
    value += text
    i = next
  }
  return { type: 'word', value, plain, subs, end: Math.min(i, src.length) }
}

function readPiece(src, i, subs) {
  const c = src[i]
  if (c === "'") {
    const end = src.indexOf("'", i + 1)
    return end === -1 ? [src.slice(i + 1), src.length] : [src.slice(i + 1, end), end + 1]
  }
  if (c === '$' && src[i + 1] === "'") return readAnsi(src, i + 2)
  if (c === '"') return readDouble(src, i + 1, subs)
  if (c === '\\') return [src[i + 1] === '\n' ? '' : (src[i + 1] ?? ''), i + 2]
  if (c === '$' || c === '`') {
    const next = readExpansion(src, i, subs)
    return [src.slice(i, next), next]
  }
  return [c, i + 1]
}

function readDouble(src, i, subs) {
  let text = ''
  while (i < src.length && src[i] !== '"') {
    if (src[i] === '\\' && '$`"\\\n'.includes(src[i + 1])) {
      if (src[i + 1] !== '\n') text += src[i + 1]
      i += 2
    } else if (src[i] === '$' || src[i] === '`') {
      const next = readExpansion(src, i, subs)
      text += src.slice(i, next)
      i = next
    } else text += src[i++]
  }
  return [text, i + 1]
}

function readAnsi(src, i) {
  let text = ''
  while (i < src.length && src[i] !== "'") {
    if (src[i] === '\\') {
      text += src[i + 1] === 'n' ? '\n' : src[i + 1] === 't' ? '\t' : (src[i + 1] ?? '')
      i += 2
    } else text += src[i++]
  }
  return [text, i + 1]
}

function readExpansion(src, i, subs) {
  if (src[i] === '`') {
    let j = i + 1
    while (j < src.length && src[j] !== '`') j += src[j] === '\\' ? 2 : 1
    subs.push(src.slice(i + 1, j).replace(/\\([`\\$])/g, '$1'))
    return j + 1
  }
  if (src.startsWith('$((', i)) return matchParen(src, i + 3, 2) + 1
  if (src[i + 1] === '(') {
    const close = matchParen(src, i + 2)
    subs.push(src.slice(i + 2, close))
    return close + 1
  }
  if (src[i + 1] === '{') {
    const close = src.indexOf('}', i + 2)
    return close === -1 ? src.length : close + 1
  }
  return i + 1
}

function matchParen(src, i, depth = 1) {
  while (i < src.length) {
    const c = src[i]
    if (c === '\\') i += 2
    else if (c === "'") {
      const end = src.indexOf("'", i + 1)
      i = end === -1 ? src.length : end + 1
    } else if (c === '"') i = readDouble(src, i + 1, [])[1]
    else {
      if (c === '(') depth++
      else if (c === ')' && --depth === 0) return i
      i++
    }
  }
  return src.length
}
