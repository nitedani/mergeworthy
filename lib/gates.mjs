import { realpathSync } from 'node:fs'
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

export function bashGates({ command, cwd, runInBackground }, ctx) {
  const { commands, comments } = parse(command, cwd)
  return evaluate(BASH_GATES, { commands, runInBackground }, ctx, { bypass: findBypass(comments.join('\n')), place: 'command', prefix: '# ' })
}

export function agentGates({ input }, ctx) {
  const text = [input.prompt, input.task, input.description].filter(Boolean).join('\n')
  return evaluate(AGENT_GATES, { input }, ctx, { bypass: findBypass(text), place: 'prompt', prefix: '' })
}

function findBypass(text) {
  const reasons = [...text.matchAll(new RegExp(`${BYPASS_TOKEN}(?=[:\\s]|$)[: \\t]*([^\\n]*)`, 'g'))].map((m) => m[1])
  if (!reasons.length) return 'none'
  return reasons.some(isValidReason) ? 'valid' : 'short'
}

export function isValidReason(reason) {
  return (reason ?? '').split(/\s+/).filter(Boolean).length >= 3
}

function evaluate(gates, input, ctx, how) {
  return gates.flatMap((gate) => {
    if (gate.kind === 'warn' && how.bypass === 'valid') return []
    const finding = gate.fires(input, ctx)
    return finding ? [{ gate: gate.name, kind: gate.kind, message: message(gate, finding, how) }] : []
  })
}

function message(gate, { why, instead }, { bypass, place, prefix }) {
  if (gate.kind === 'block') return `mergeworthy ${gate.name} (blocked, no bypass): ${why}. ${instead}.`
  return [
    `mergeworthy ${gate.name}: ${why}`,
    instead,
    ...(bypass === 'short' ? ['Your bypass line is missing its reason: give at least 3 words.'] : []),
    `To go ahead anyway, add this line to the ${place}, with your real reason:`,
    `${prefix}${BYPASS_TOKEN}: <why this is right here>`,
  ].join('\n')
}

const BASH_GATES = [
  {
    name: 'kill-by-pattern',
    kind: 'block',
    fires: ({ commands }) =>
      commands.some((cmd) => killsByPattern(cmd, commands)) && {
        why: "killing by name or pattern also hits other sessions' processes",
        instead: 'Kill the PIDs you started, by PID; check each with `ps -o pid,ppid,cmd -p <pid>` first',
      },
  },
  {
    name: 'force-push',
    kind: 'block',
    fires: ({ commands }) =>
      commands.some((cmd) => forcePushes(gitCommand(cmd))) && {
        why: 'a force push without a lease overwrites commits others pushed',
        instead: 'Push with `--force-with-lease` instead',
      },
  },
  {
    name: 'post',
    kind: 'warn',
    fires: ({ commands }) => {
      const gh = commands.map(ghInvocation).find(postsToGitHub)
      return gh && {
        why: `\`gh ${gh.group} ${gh.action}\` posts to GitHub directly, so the draft gets no lint and no review verdict.`,
        instead: 'Post through `mw post <draft> -- <this gh command with --body-file <draft>>`, which lints the draft and checks its review verdict.',
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
        why: sleep.inWhile ? 'a while/until loop with `sleep` polls in the foreground and blocks the session.' : `\`${sleep.argv.join(' ')}\` blocks the session in the foreground.`,
        instead: 'Run it with `run_in_background`, or use Monitor for repeated events.',
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
const BODY_FLAG = /^(--body|-b|--body-file|-F|--title|-t)(=|$)/
const POSTING_PATH = /(^|\/)(issues|pulls|comments|reviews|replies|releases)(\/|\?|$)/
const POSTING_MUTATION = /\bmutation\b[\s\S]*\b(add|update|create|submit)\w*(Comment|Review|Issue|PullRequest)/

function postsToGitHub(gh) {
  if (!gh) return false
  if (POSTING_ACTIONS[gh.group]?.includes(gh.action)) return true
  if (gh.action === 'edit' && (gh.group === 'pr' || gh.group === 'issue')) return gh.args.some((a) => BODY_FLAG.test(a))
  if (gh.group !== 'api') return false
  const { method, path, fields } = apiRequest([gh.action, ...gh.args])
  if (path === 'graphql') return fields.some((f) => POSTING_MUTATION.test(f))
  return ['POST', 'PATCH', 'PUT'].includes(method) && POSTING_PATH.test(path ?? '') && !/\/reactions(\/|\?|$)/.test(path)
}

function ghInvocation(cmd) {
  return program(cmd) === 'gh' ? { ...ghCommand(cmd.argv.slice(1)), cwd: cmd.cwd } : null
}

function missingSteps(gh, ctx) {
  const target = readyTarget(gh, ctx)
  if (!target?.head) return null
  const pending = checkSteps(ctx, gh.cwd, target).filter((s) => s.state !== 'done')
  if (!pending.length) return null
  const older = pending.filter((s) => s.state === 'older').map((s) => ` ${s.step} is recorded on an ${describeStep(s, target.head)}.`)
  return {
    why: `${target.head.slice(0, 7)} of ${target.pr ?? target.branch} has no ${pending.map((s) => s.step).join(', ')} step on this head.${older.join('')}`,
    instead: `Run each missing step on this head and record it with \`mw step <step> <evidence>${target.pr ? ` --pr ${target.pr}` : ''}\`.`,
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
      why: `\`${['git stash', ...call.args].join(' ')}\` uses the stash, which every worktree of this repo shares.`,
      instead: 'Commit the work in progress on a branch instead.',
    }
  }
  if (!DISCARDS[call?.sub]?.(call.args) || !call.dir || !isMainWorktree(ctx, call.dir)) return null
  return {
    why: `\`git ${call.sub} ${call.args.join(' ')}\` changes the files of ${call.dir}, a main worktree someone may be working in.`,
    instead: 'Make a worktree instead: `git worktree add <work dir>/<name> <ref>`.',
  }
}

function isMainWorktree(ctx, dir) {
  const dirs = git(ctx, dir, ['rev-parse', '--path-format=absolute', '--git-dir', '--git-common-dir'])
  if (!dirs) return false
  const [gitDir, commonDir] = dirs.split('\n').map(realpath)
  return gitDir === commonDir
}

function realpath(path) {
  try {
    return realpathSync(path)
  } catch {
    return path
  }
}

const PUSH_VALUED = new Set(['-o', '--push-option', '--repo', '--receive-pack', '--exec'])

function foreignAuthors(call, ctx) {
  const refs = call?.sub === 'push' && call.dir && pushedRefs(call.args)
  if (!refs?.length) return null
  const user = ghUser(ctx)
  if (!user) return null
  const expected = noreplyEmail(user)
  const log = git(ctx, call.dir, ['log', '--format=%H %ae', ...refs, '--not', '--remotes']) ?? ''
  const foreign = log.split('\n').filter(Boolean).map((line) => line.split(' ')).filter(([, email]) => email !== expected)
  if (!foreign.length) return null
  const emails = [...new Set(foreign.map(([, email]) => email))].join(', ')
  return {
    why: `${foreign.length} commit(s) to push are authored by ${emails}, not ${expected}, the GitHub account's noreply address.`,
    instead: `Rewrite them with that identity: \`git -c user.name=${user.login} -c user.email=${expected} rebase --exec 'git commit --amend --no-edit --reset-author' ${foreign.at(-1)[0].slice(0, 7)}~1\`.`,
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
        why: `clientRequestId '${input.clientRequestId}' was first used ${minutesSince(ctx, firstSeen)} min ago, and T3 Code answers a reused id with that old task's result`,
        instead: 'Give this task a new clientRequestId; reuse one only to retry the same request',
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
        why: `an agent titled '${key}' started ${minutesSince(ctx, started)} min ago.`,
        instead: 'Continue it (SendMessage to it, or `t3_thread_send` to its thread) instead of starting another; a new review round gets its own title ("… round 2"); if it died, relaunch it with the bypass line in the prompt.',
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
        why: `${gib(availableKiB)} GiB of memory is available (the floor is ${minFreeGiB}) and ${agents.length} claude/codex processes run (the cap is ${maxAgents}).`,
        instead: `Stop agents whose work is done, by PID after checking each with \`ps -o pid,ppid,cmd -p <pid>\`. The largest: ${agents.slice(0, 5).map(describeProcess).join('; ')}.`,
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
