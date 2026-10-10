import { closeSync, openSync, readFileSync, readSync } from 'node:fs'
import { realCtx } from './ctx.mjs'

const STOP_REASON = "Before you stop: is there critical-path work you can start now, or a reply, red CI or a finished agent's result waiting on you? Then do it now. Otherwise stop."

export function runHook(decide) {
  try {
    const output = decide(JSON.parse(readFileSync(0, 'utf8')), realCtx())
    if (output) process.stdout.write(output + '\n')
  } catch {}
}

export function denial(findings) {
  if (!findings.length) return null
  return JSON.stringify({
    hookSpecificOutput: {
      hookEventName: 'PreToolUse',
      permissionDecision: 'deny',
      permissionDecisionReason: findings.map((f) => f.message).join('\n\n'),
    },
  })
}

export function stopDecision(input) {
  if (input.stop_hook_active || isDelegatedChild(input.transcript_path)) return null
  return JSON.stringify({ decision: 'block', reason: STOP_REASON })
}

function isDelegatedChild(transcriptPath) {
  const first = firstLines(transcriptPath, 30).find((line) => line.includes('"type":"user"'))
  const content = first && JSON.parse(first).message?.content
  const text = typeof content === 'string' ? content : (content ?? []).map((part) => part.text ?? '').join('')
  return text.startsWith('Act as the ') && text.includes('sub-agent for this task')
}

function firstLines(path, count) {
  const fd = openSync(path, 'r')
  const buffer = Buffer.alloc(4 << 20)
  const bytes = readSync(fd, buffer, 0, buffer.length, 0)
  closeSync(fd)
  return buffer.toString('utf8', 0, bytes).split('\n').slice(0, count).filter(Boolean)
}
