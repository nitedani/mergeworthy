import { agentGates } from '../lib/gates.mjs'
import { denial, runHook } from '../lib/hooks.mjs'

runHook((input, ctx) => denial(agentGates({ toolName: input.tool_name, input: input.tool_input }, ctx)))
