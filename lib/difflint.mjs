import { diffBase, git, TEST_FILE } from './git.mjs'

const COMMENT_SYNTAX = [
  { files: /\.(sh|bash|py|rb|ya?ml)$/, comment: /^\s*#(?!!)/ },
  { files: /\.([cm]?[jt]sx?|vue|svelte|go|rs|java|kt|swift|scala|c|cc|cpp|h|hpp|cs|php|css|scss)$/, comment: /^\s*(\/\/|\/\*|\*\/|\*( |$))/ },
]
const HISTORY = /no longer|instead of|previously|used to|anymore|formerly|was changed|we now|now (we|it|this)/i
const TEST_WAIT = /setTimeout\(|sleep\(|waitForTimeout\(|time\.sleep\(|Promise\.race\(/

const RULES = [
  {
    message: 'a comment of 2+ lines; keep at most one line, for a constraint the code cannot show',
    find: (lines) => {
      const comments = lines.filter(isComment)
      return comments.filter((l, i) => !follows(l, comments[i - 1]) && follows(comments[i + 1], l))
    },
  },
  {
    message: 'a comment about history; say what the code does now, or nothing',
    find: (lines) => lines.filter((l) => isComment(l) && HISTORY.test(l.text)),
  },
  {
    message: 'a timed wait in a test; wait on the event instead',
    find: (lines) => lines.filter((l) => TEST_FILE.test(l.file) && TEST_WAIT.test(l.text)),
  },
]

export function diffLintCommand(argv, ctx) {
  const diff = git(ctx, ctx.cwd, ['diff', '-U0', `${diffBase(ctx, argv[0])}...HEAD`])
  if (diff === null) throw new Error('git diff failed')
  for (const w of diffLint(diff)) ctx.out(`warning: ${w.file}:${w.line}: ${w.message}`)
  return 0
}

export function diffLint(diff) {
  const lines = addedLines(diff)
  return RULES.flatMap((rule) => rule.find(lines).map((l) => ({ file: l.file, line: l.line, message: rule.message })))
}

function addedLines(diff) {
  const lines = []
  let file = null
  let next = 0
  for (const row of diff.split('\n')) {
    if (row.startsWith('+++ ')) file = row.startsWith('+++ b/') ? row.slice(6) : null
    else if (row.startsWith('@@')) next = Number(/\+(\d+)/.exec(row)[1])
    else if (row.startsWith('+') && file) lines.push({ file, line: next++, text: row.slice(1) })
  }
  return lines
}

function isComment(line) {
  return Boolean(COMMENT_SYNTAX.find((syntax) => syntax.files.test(line.file))?.comment.test(line.text))
}

function follows(line, previous) {
  return Boolean(line && previous && line.file === previous.file && line.line === previous.line + 1)
}
