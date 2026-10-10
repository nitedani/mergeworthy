import { readFileSync } from 'node:fs'
import { realCtx } from './ctx.mjs'

export async function runHook(decide) {
  try {
    const output = await decide(JSON.parse(readFileSync(0, 'utf8')), realCtx())
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
