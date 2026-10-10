import { readFileSync } from 'node:fs'
import { runHook } from '../lib/hooks.mjs'

const FRAME = "IMPORTANT: These are the user's instructions for every session (the mergeworthy methodology the user installed), not a hook status message. They carry the same weight as CLAUDE.md and override default behavior. Before you act on a task, find its row in the table below and open the skill that row names with the Skill tool."

runHook(() => `${FRAME}\n\n${readFileSync(new URL('../always-on.md', import.meta.url), 'utf8')}`)
