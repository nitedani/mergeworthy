import { basename, resolve } from 'node:path'
import { apiRequest, ghCommand } from './gh-command.mjs'
import { git } from './git.mjs'
import { ghUser, noreplyEmail } from './github.mjs'
import { agentProcesses, describeProcess, gib } from './load.mjs'
import { parse } from './shell.mjs'
import { prune, readState, writeState } from './state.mjs'
import { checkoutHead, checkSteps, describeStep, prHead } from './steps.mjs'
import { DAY, MINUTE, seconds } from './time.mjs'

export const BYPASS_TOKEN = '--I_UNDERSTAND_IMPLICATIONS_AND_BYPASS_GATE'
const BYPASS_IN_COMMAND = { target: 'command', place: 'command', prefix: '# ' }
const BYPASS_IN_PROMPT = { target: 'agent launch', place: 'agent prompt', prefix: '' }

export function bashGates({ command, cwd, runInBackground }, ctx) {
  const { commands, comments } = parse(command, cwd)
  return evaluate(BASH_GATES, { commands, runInBackground }, ctx, findBypass(comments.join('\n')), BYPASS_IN_COMMAND)
}

export function agentGates({ input }, ctx) {
  const text = [input.prompt, input.task, input.description].filter(Boolean).join('\n')
  return evaluate(AGENT_GATES, { input }, ctx, findBypass(text), BYPASS_IN_PROMPT)
}

function findBypass(text) {
  const reasons = [...text.matchAll(new RegExp(`${BYPASS_TOKEN}(?=[:\\s]|$)[: \\t]*([^\\n]*)`, 'g'))].map((m) => m[1])
  if (!reasons.length) return 'none'
  return reasons.some(isValidReason) ? 'valid' : 'short'
}

export function isValidReason(reason) {
  return (reason ?? '').split(/\s+/).filter(Boolean).length >= 3
}

function evaluate(gates, input, ctx, bypass, bypassLine) {
  return gates.flatMap((gate) => {
    if (gate.kind === 'warn' && bypass === 'valid') return []
    const finding = gate.fires(input, ctx)
    return finding ? [{ gate: gate.name, kind: gate.kind, message: message(gate, finding, bypass, bypassLine) }] : []
  })
}

function message(gate, { why, instead }, bypass, { target, place, prefix }) {
  if (gate.kind === 'block') return `mergeworthy blocked this ${target} (its ${gate.name} check), and this check has no bypass: ${why}. ${instead}.`
  return [
    `mergeworthy stopped this ${target} (its ${gate.name} check): ${why}.`,
    `${instead}.`,
    ...(bypass === 'short' ? ['Your bypass line has no reason of at least 3 words, so it does not count yet.'] : []),
    `This check is a warning you may bypass. To go ahead anyway, add this line to the ${place} with your real reason, which the user will see there:`,
    `${prefix}${BYPASS_TOKEN}: <why this is right here>`,
  ].join('\n')
}

const BASH_GATES = [
  {
    name: 'kill-by-pattern',
    kind: 'block',
    fires: ({ commands }) =>
      commands.some((cmd) => killsByPattern(cmd, commands)) && {
        why: 'killing processes by name or pattern also kills the processes of other sessions and programs on this machine',
        instead: 'Kill only the processes you started, by PID. Check each one first with `ps -o pid,ppid,cmd -p <pid>`',
      },
  },
  {
    name: 'force-push',
    kind: 'block',
    fires: ({ commands }) =>
      commands.some((cmd) => forcePushes(gitCommand(cmd))) && {
        why: 'a plain force push overwrites any commits that others pushed to the branch since you last fetched',
        instead: 'Push with `--force-with-lease` instead, which refuses when the remote branch has commits you have not fetched',
      },
  },
  {
    name: 'post',
    kind: 'warn',
    fires: ({ commands }) => {
      const gh = commands.map(ghInvocation).find((call) => !call?.throughMwPost && postsToGitHub(call))
      return gh && {
        why: `\`${describeGh(gh)}\` posts to GitHub directly, so the text skips the two checks every post needs: \`mw lint\` and a reviewer's CLEAN verdict`,
        instead: postAdvice(gh),
      }
    },
  },
  {
    name: 'ready',
    kind: 'warn',
    fires: ({ commands }, ctx) => commands.map((cmd) => missingSteps(ghInvocation(cmd), ctx)).find(Boolean),
  },
  {
    name: 'shared-git',
    kind: 'warn',
    fires: ({ commands }, ctx) => commands.map((cmd) => sharedGitChange(gitCommand(cmd), ctx)).find(Boolean),
  },
  {
    name: 'identity',
    kind: 'warn',
    fires: ({ commands }, ctx) => commands.map((cmd) => foreignAuthors(gitCommand(cmd), ctx)).find(Boolean),
  },
  {
    name: 'foreground-wait',
    kind: 'warn',
    fires: ({ commands, runInBackground }) => {
      const sleep = !runInBackground && commands.find((cmd) => program(cmd) === 'sleep' && !cmd.background && (cmd.inWhile || sleepSeconds(cmd.argv) >= 30))
      return sleep && {
        why: sleep.inWhile ? 'a while/until loop with `sleep` waits in the foreground, and the session can do nothing else until it ends' : `\`${sleep.argv.join(' ')}\` waits in the foreground, and the session can do nothing else until it ends`,
        instead: "Run it with the Bash tool's `run_in_background` option, or wait for the event with the Monitor tool",
      }
    },
  },
]

function program(cmd) {
  return basename(cmd.argv[0])
}

function killsByPattern(cmd, commands) {
  switch (program(cmd)) {
    case 'pkill':
    case 'killall':
      return true
    case 'kill':
      return cmd.argv.some((w) => /(\$\(|`)\s*pgrep\b/.test(w)) || killTargets(cmd.argv.slice(1)).some((t) => t === '-1' || t === '0')
    case 'pgrep':
      return pipeline(cmd, commands).some((next) => program(next) === 'xargs' && next.argv.some((w) => basename(w) === 'kill'))
    default:
      return false
  }
}

function killTargets(args) {
  if (args.length === 1) return args
  const signalWords = args[0] === '-s' || args[0] === '-n' ? 2 : args[0]?.startsWith('-') ? 1 : 0
  return args.slice(signalWords)
}

function pipeline(cmd, commands) {
  const next = commands[cmd.pipeTo]
  return next ? [next, ...pipeline(next, commands)] : []
}

function gitCommand(cmd) {
  if (program(cmd) !== 'git') return null
  let dir = cmd.cwd
  let i = 1
  for (; i < cmd.argv.length && cmd.argv[i].startsWith('-'); i++) {
    if (cmd.argv[i] === '-C') dir = resolveDir(dir, cmd.argv[++i])
    else if (cmd.argv[i] === '-c') i++
  }
  return { dir, sub: cmd.argv[i], args: cmd.argv.slice(i + 1) }
}

function resolveDir(base, dir) {
  if (/[$`~]/.test(dir)) return null
  return dir.startsWith('/') ? dir : base && resolve(base, dir)
}

function forcePushes(call) {
  if (call?.sub !== 'push' || call.args.some((a) => a.startsWith('--force-with-lease'))) return false
  return call.args.some((a) => a === '--force' || /^-[a-zA-Z]*f[a-zA-Z]*$/.test(a) || a.startsWith('+'))
}

const POSTING_ACTIONS = { pr: ['comment', 'create', 'review'], issue: ['comment', 'create'], release: ['create', 'edit'], gist: ['create', 'edit'] }
const TEXT_FLAGS = { edit: /^(--body|-b|--body-file|-F|--title|-t)(=|$)/, close: /^(--comment|-c)(=|$)/ }
const POSTING_PATH = /(^|\/)(issues|pulls|comments|reviews|replies|releases)(\/|\?|$)/
const POSTING_MUTATION = /\bmutation\b[\s\S]*\b(add|update|create|submit)\w*(Comment|Review|Issue|PullRequest)/

function postsToGitHub(gh) {
  if (!gh) return false
  if (POSTING_ACTIONS[gh.group]?.includes(gh.action)) return true
  if ((gh.group === 'pr' || gh.group === 'issue') && TEXT_FLAGS[gh.action]) return gh.args.some((a) => TEXT_FLAGS[gh.action].test(a))
  if (gh.group !== 'api') return false
  const { method, path, fields, input } = apiRequest([gh.action, ...gh.args])
  if (path === 'graphql') return fields.some((f) => POSTING_MUTATION.test(f))
  return ['POST', 'PATCH', 'PUT'].includes(method) && POSTING_PATH.test(path ?? '') && (input !== null || fields.some((f) => f.startsWith('body=')))
}

function describeGh(gh) {
  return gh.group === 'api' ? `gh api ${apiRequest([gh.action, ...gh.args]).path}` : `gh ${gh.group} ${gh.action}`
}

function postAdvice(gh) {
  if (gh.action === 'close') {
    return `Save the comment in a draft file, get it reviewed, and post it with \`mw post <draft> -- gh ${gh.group} comment ${gh.args.find((a) => !a.startsWith('-')) ?? '<number>'} --body-file <draft>\`, which runs both checks first. Then close without --comment`
  }
  return `Save the text in a draft file, get it reviewed, and post it with \`mw post <draft> -- <this gh command with ${gh.group === 'api' ? '-F body=@<draft>' : '--body-file <draft>'}>\`, which runs both checks first`
}

function ghInvocation(cmd) {
  const argv = program(cmd) === 'gh' ? cmd.argv.slice(1) : postedGhArgs(cmd)
  return argv && { ...ghCommand(argv), cwd: cmd.cwd, throughMwPost: program(cmd) === 'mw' }
}

function postedGhArgs(cmd) {
  const split = cmd.argv.indexOf('--')
  return program(cmd) === 'mw' && cmd.argv[1] === 'post' && cmd.argv[split + 1] === 'gh' ? cmd.argv.slice(split + 2) : null
}

function missingSteps(gh, ctx) {
  const target = readyTarget(gh, ctx)
  if (!target?.head) return null
  const pending = checkSteps(ctx, gh.cwd, target).filter((s) => s.state !== 'done')
  if (!pending.length) return null
  const older = pending.filter((s) => s.state === 'older').map((s) => `${s.step} was ${describeStep(s, target.head)}`)
  return {
    why: [
      `\`gh pr ${gh.action}\` makes ${target.pr ?? target.branch} ready for review, but its latest commit, ${target.head.slice(0, 7)}, has no record of these required steps: ${pending.map((s) => s.step).join(', ')}`,
      ...older,
    ].join('. '),
    instead: `Run each missing step on commit ${target.head.slice(0, 7)}, then record it with \`mw step <step> <evidence file>${target.pr ? ` --pr ${target.pr}` : ''}\` (the converge skill says what each step is)`,
  }
}

function readyTarget(gh, ctx) {
  if (gh?.group !== 'pr') return null
  if (gh.action === 'ready' && !gh.args.includes('--undo')) {
    try {
      return prHead(ctx, gh.args.find((a) => !a.startsWith('-')), { repo: gh.repo, cwd: gh.cwd })
    } catch {
      return null
    }
  }
  if (gh.action !== 'create' || gh.args.some((a) => a === '--draft' || a === '-d')) return null
  return checkoutHead(ctx, gh.cwd)
}

const DISCARDS = {
  checkout: (args) => !args.some((a) => a === '-p' || a === '--patch'),
  switch: () => true,
  reset: (args) => args.includes('--hard'),
  clean: (args) => args.some((a) => a === '--force' || /^-[a-zA-Z]*f/.test(a)),
  restore: (args) => !args.some((a) => a === '--staged' || a === '-S') || args.some((a) => a === '--worktree' || a === '-W'),
}
const STASH_WRITES = [undefined, 'push', 'pop', 'apply', 'drop', 'clear', 'save']

function sharedGitChange(call, ctx) {
  if (call?.sub === 'stash' && STASH_WRITES.includes(call.args.find((a) => !a.startsWith('-')))) {
    return {
      why: `\`${['git stash', ...call.args].join(' ')}\` changes the stash, which every worktree of this repo shares, so it can take or drop work that another session saved there`,
      instead: 'Commit the work in progress on a branch instead',
    }
  }
  if (!DISCARDS[call?.sub]?.(call.args) || !call.dir || !isMainWorktree(ctx, call.dir)) return null
  return {
    why: `\`git ${call.sub} ${call.args.join(' ')}\` changes or discards files in ${call.dir}, the repo's main checkout, where the user or another session may be working`,
    instead: 'Work in a worktree of your own instead: `git worktree add <new dir> <branch or commit>`',
  }
}

function isMainWorktree(ctx, dir) {
  const dirs = git(ctx, dir, ['rev-parse', '--path-format=absolute', '--git-dir', '--git-common-dir'])
  if (!dirs) return false
  const [gitDir, commonDir] = dirs.split('\n')
  return gitDir === commonDir
}

const PUSH_VALUED = new Set(['-o', '--push-option', '--repo', '--receive-pack', '--exec'])

function foreignAuthors(call, ctx) {
  const refs = call?.sub === 'push' && call.dir && pushedRefs(call.args)
  const user = refs?.length && ghUser(ctx)
  const machineEmail = user && git(ctx, call.dir, ['config', 'user.email'])
  const expected = user && noreplyEmail(user)
  if (!machineEmail || machineEmail === expected) return null
  const log = git(ctx, call.dir, ['log', '--format=%H %ae', ...refs, '--not', '--remotes']) ?? ''
  const wrong = log
    .split('\n')
    .map((line) => line.split(' '))
    .filter(([, author]) => author === machineEmail)
    .map(([sha]) => sha)
  if (!wrong.length) return null
  return {
    why: `${wrong.length} commit(s) you are pushing have ${machineEmail} as author, which is this machine's git email, instead of ${expected}, the private noreply email of the GitHub account gh is logged in as`,
    instead: `Rewrite the author of only those commits, then push again: \`git -c user.name=${user.login} -c user.email=${expected} rebase --exec 'test "$(git log -1 --format=%ae)" != "${machineEmail}" || git commit --amend --no-edit --reset-author' ${wrong.at(-1).slice(0, 7)}~1\``,
  }
}

function pushedRefs(args) {
  if (args.includes('--delete') || args.includes('-d')) return null
  const positional = args.filter((a, i) => !a.startsWith('-') && !PUSH_VALUED.has(args[i - 1]))
  const refspecs = positional.slice(1).map((r) => r.replace(/^\+/, ''))
  if (refspecs[0] === 'tag' || (refspecs.length && refspecs.every((r) => r.startsWith('refs/tags/')))) return null
  if (!refspecs.length) return args.includes('--tags') ? null : ['HEAD']
  return refspecs.map((r) => r.split(':')[0]).filter(Boolean)
}

function sleepSeconds(argv) {
  return argv.slice(1).reduce((sum, duration) => sum + seconds(duration), 0)
}

const AGENT_GATES = [
  {
    name: 'reused-request-id',
    kind: 'block',
    fires: ({ input }, ctx) => {
      const firstSeen = input.clientRequestId && readState(ctx, 'request-ids.json', {})[input.clientRequestId]
      return firstSeen && ctx.now() - firstSeen > 10 * MINUTE && {
        why: `the clientRequestId '${input.clientRequestId}' was first used ${minutesSince(ctx, firstSeen)} min ago. T3 Code answers a reused id with the old task's result instead of starting this one`,
        instead: 'Give this task a new clientRequestId. Reuse an id only to retry the same request',
      }
    },
  },
  {
    name: 'agent-dedupe',
    kind: 'warn',
    fires: ({ input }, ctx) => {
      const key = agentKey(input)
      const started = key && readState(ctx, 'agents.json', {})[key]?.at
      return started && ctx.now() - started < DAY && {
        why: `an agent with the same title or description, '${key}', started ${minutesSince(ctx, started)} min ago, so this one would likely repeat its work`,
        instead: 'Continue that agent instead: SendMessage to it, or `t3_thread_send` to its thread. A new review round gets its own title, like "… round 2". If the old agent died, start this one again with the bypass line below',
      }
    },
  },
  {
    name: 'agent-load',
    kind: 'warn',
    fires: (_, ctx) => {
      const { minFreeGiB = 4, maxAgents = 8 } = readState(ctx, 'config.json', {})
      const { availableKiB } = ctx.meminfo()
      const agents = agentProcesses(ctx.procs()).sort((a, b) => b.rssKiB - a.rssKiB)
      return (availableKiB < minFreeGiB * 2 ** 20 || agents.length >= maxAgents) && {
        why: `the machine has reached one of its limits for agents: ${gib(availableKiB)} GiB of memory is free (the minimum is ${minFreeGiB} GiB) and ${agents.length} claude/codex processes are running (the maximum is ${maxAgents}). Both limits are set in config.json in the mergeworthy home directory, ~/.mergeworthy by default`,
        instead: `Stop agents whose work is done: check each with \`ps -o pid,ppid,cmd -p <pid>\`, then kill it by PID. The largest: ${agents.slice(0, 5).map(describeProcess).join('; ')}`,
      }
    },
  },
]

export function recordAgent({ toolName, input }, ctx) {
  const now = ctx.now()
  const key = agentKey(input)
  const agents = prune(readState(ctx, 'agents.json', {}), now, 7 * DAY, (entry) => entry.at)
  if (key) agents[key] = { at: now, tool: toolName }
  writeState(ctx, 'agents.json', agents)
  if (!input.clientRequestId) return
  const ids = prune(readState(ctx, 'request-ids.json', {}), now, 7 * DAY)
  ids[input.clientRequestId] ??= now
  writeState(ctx, 'request-ids.json', ids)
}

function agentKey(input) {
  return (input.title || input.description || '').trim().toLowerCase()
}

function minutesSince(ctx, at) {
  return Math.round((ctx.now() - at) / MINUTE)
}
