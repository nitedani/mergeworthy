import { readFileSync } from 'node:fs'
import { runHook } from '../lib/hooks.mjs'

const FRAME = "IMPORTANT: These are the user's instructions for every session (the mergeworthy methodology the user installed), not a hook status message. They carry the same weight as CLAUDE.md and override default behavior."

runHook(() => `${FRAME}\n\n${readFileSync(new URL('../always-on.md', import.meta.url), 'utf8')}`)
