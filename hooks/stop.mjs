import { createReadStream } from 'node:fs'
import { createInterface } from 'node:readline'
import { runHook } from '../lib/hooks.mjs'

const STOP_REASON = "Before you stop, mergeworthy asks: is there work the goal is waiting on that you can start now, or a GitHub reply, a failing CI check or a finished agent's result waiting for you? If so, do it now. If not, stop again; this check asks only once."

runHook(async (input) => {
  if (input.stop_hook_active || (await isDelegatedChild(input.transcript_path))) return null
  return JSON.stringify({ decision: 'block', reason: STOP_REASON })
})

async function isDelegatedChild(transcriptPath) {
  const prompt = await firstUserMessage(transcriptPath, 30).catch(() => null)
  const text = typeof prompt === 'string' ? prompt : (prompt ?? []).map((part) => part.text ?? '').join('')
  return text.startsWith('Act as the ') && text.includes('sub-agent for this task')
}

async function firstUserMessage(path, maxLines) {
  const stream = createReadStream(path)
  try {
    let count = 0
    for await (const line of createInterface({ input: stream })) {
      if (line.includes('"type":"user"')) return JSON.parse(line).message?.content
      if (++count === maxLines) return null
    }
    return null
  } finally {
    stream.destroy()
  }
}
