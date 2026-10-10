import { bashGates } from '../lib/gates.mjs'
import { denial, runHook } from '../lib/hooks.mjs'

runHook((input, ctx) => {
  const { command, run_in_background } = input.tool_input
  return denial(bashGates({ command, cwd: input.cwd, runInBackground: run_in_background }, ctx))
})
