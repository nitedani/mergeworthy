import { recordAgent } from '../lib/gates.mjs'
import { runHook } from '../lib/hooks.mjs'

runHook((input, ctx) => recordAgent({ toolName: input.tool_name, input: input.tool_input }, ctx))
