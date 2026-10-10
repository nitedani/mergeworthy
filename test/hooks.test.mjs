import assert from 'node:assert/strict'
import { readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { test } from 'node:test'
import { ROOT, run, tempDir } from './helpers.mjs'

const hook = (name, input, env) => run(`hooks/${name}.mjs`, [], { input: typeof input === 'string' ? input : JSON.stringify(input), env })
const denial = (stdout) => JSON.parse(stdout).hookSpecificOutput

test('pre-bash denies a gated command with the gate message', () => {
  const r = hook('pre-bash', { tool_name: 'Bash', tool_input: { command: 'pkill -f vite' }, cwd: '/tmp' })
  assert.equal(r.code, 0)
  assert.deepEqual(Object.keys(denial(r.stdout)), ['hookEventName', 'permissionDecision', 'permissionDecisionReason'])
  assert.equal(denial(r.stdout).permissionDecision, 'deny')
  assert.match(denial(r.stdout).permissionDecisionReason, /^mergeworthy blocked this command \(its kill-by-pattern check\), and this check has no bypass/)
})

test('pre-bash is silent on an ungated command', () => {
  assert.deepEqual(hook('pre-bash', { tool_name: 'Bash', tool_input: { command: 'ls -la' }, cwd: '/tmp' }), { code: 0, stdout: '', stderr: '' })
})

test('pre-agent denies a duplicate launch that post-agent registered in the same session', () => {
  const home = tempDir()
  writeFileSync(join(home, 'config.json'), JSON.stringify({ minFreeGiB: 0, maxAgents: 1e9 }))
  const launch = { session_id: 'session-a', tool_name: 'Agent', tool_input: { description: 'Review PR 5', prompt: 'review it' } }
  assert.equal(hook('post-agent', launch, { MW_HOME: home }).stdout, '')
  assert.match(denial(hook('pre-agent', launch, { MW_HOME: home }).stdout).permissionDecisionReason, /^mergeworthy stopped this agent launch \(its agent-dedupe check\): an agent with the same title or description, 'review pr 5'/)
  assert.equal(hook('pre-agent', { ...launch, session_id: 'session-b' }, { MW_HOME: home }).stdout, '')
})

test('stop blocks once, then allows the stop', () => {
  const transcript = join(tempDir(), 't.jsonl')
  writeFileSync(transcript, JSON.stringify({ type: 'user', message: { role: 'user', content: 'Fix the bug' } }) + '\n')
  assert.match(JSON.parse(hook('stop', { stop_hook_active: false, transcript_path: transcript }).stdout).reason, /^Before you stop, mergeworthy asks: /)
  assert.equal(JSON.parse(hook('stop', { transcript_path: transcript }).stdout).decision, 'block')
  assert.equal(hook('stop', { stop_hook_active: true, transcript_path: transcript }).stdout, '')
})

test('stop blocks when the transcript is missing or unreadable', () => {
  for (const transcript_path of [undefined, join(tempDir(), 'gone.jsonl'), tempDir()]) {
    const input = { stop_hook_active: false, transcript_path }
    assert.equal(JSON.parse(hook('stop', input).stdout).decision, 'block')
  }
})

test('stop allows a T3 delegated child to stop', () => {
  const transcript = join(tempDir(), 't.jsonl')
  const prompt = { type: 'user', message: { role: 'user', content: 'Act as the implementation sub-agent for this task.\n\nGoal: x' } }
  writeFileSync(transcript, [{ type: 'queue-operation' }, prompt].map((entry) => JSON.stringify(entry)).join('\n') + '\n')
  assert.equal(hook('stop', { stop_hook_active: false, transcript_path: transcript }).stdout, '')
})

test('session-start prints the framing line, a blank line and always-on.md', () => {
  const { stdout } = hook('session-start', {})
  assert.match(stdout, /^IMPORTANT: These are the user's instructions for every session .* open the skill that row names with the Skill tool\.\n\n/)
  assert.ok(stdout.endsWith(`\n\n${readFileSync(join(ROOT, 'always-on.md'), 'utf8')}\n`))
})

for (const name of ['pre-bash', 'pre-agent', 'post-agent', 'stop', 'session-start']) {
  test(`${name} fails open on garbage stdin`, () => assert.deepEqual(hook(name, 'not json {'), { code: 0, stdout: '', stderr: '' }))
}
