import assert from 'node:assert/strict'
import { homedir } from 'node:os'
import { test } from 'node:test'
import { parse } from '../lib/shell.mjs'

const commandsOf = (command) => parse(command, '/work').commands
const argvs = (command) => commandsOf(command).map((cmd) => cmd.argv)

test('splits on every separator, in order', () => {
  assert.deepEqual(argvs('a 1; b && c || d | e & f\ng'), [['a', '1'], ['b'], ['c'], ['d'], ['e'], ['f'], ['g']])
})

test('removes quotes and escapes, joining line continuations', () => {
  assert.deepEqual(argvs(`echo 'a;b' "c \\"d\\" $X" e\\ f \\\n g`), [['echo', 'a;b', 'c "d" $X', 'e f', 'g']])
})

test('records which command a pipe feeds', () => {
  const [pgrep, grep, xargs] = commandsOf('pgrep node | grep -v x | xargs kill')
  assert.equal(pgrep.pipeTo, 1)
  assert.equal(grep.pipeTo, 2)
  assert.equal(xargs.pipeTo, undefined)
})

test('collects comments apart from commands', () => {
  const { commands, comments } = parse('echo hi # a note\n# another', '/work')
  assert.deepEqual(commands.map((c) => c.argv), [['echo', 'hi']])
  assert.deepEqual(comments, ['# a note', '# another'])
})

test('treats a heredoc body as data', () => {
  for (const [opener, end] of [['<<EOF', 'EOF'], ["<<'EOF'", 'EOF'], ['<<"EOF"', 'EOF'], ['<<-EOF', '\tEOF']]) {
    assert.deepEqual(argvs(`cat ${opener} > notes.txt\npkill node\n${end}\necho done`), [['cat'], ['echo', 'done']])
  }
})

test('parses $(…) and backticks as commands and keeps them as words', () => {
  assert.deepEqual(argvs('kill $(pgrep -f "a b") `pgrep x`'), [['pgrep', '-f', 'a b'], ['pgrep', 'x'], ['kill', '$(pgrep -f "a b")', '`pgrep x`']])
})

test('parses bash -c and sh -c scripts recursively', () => {
  assert.deepEqual(argvs(`bash -lc 'git push -f; echo ok'`).slice(1), [['git', 'push', '-f'], ['echo', 'ok']])
  assert.deepEqual(argvs(`sh -c "pkill x"`).slice(1), [['pkill', 'x']])
})

test('moves leading assignments into env and unwraps prefixes', () => {
  const [cmd] = commandsOf('FOO=1 sudo -u me env BAR=2 nohup timeout 5m nice -n 5 git push')
  assert.deepEqual(cmd.argv, ['git', 'push'])
  assert.deepEqual(cmd.env, { FOO: '1', BAR: '2' })
})

test('keeps command -v as a query', () => {
  assert.deepEqual(argvs('command -v pkill'), [['command', '-v', 'pkill']])
})

test('a cd sets the cwd of the commands after it', () => {
  const cwds = commandsOf('git status; cd sub && git status; cd /abs; cd ~; cd $DIR; git status').map((c) => c.cwd)
  assert.deepEqual(cwds, ['/work', '/work', '/work/sub', '/work/sub', '/abs', homedir(), null])
})

test('drops redirections from argv', () => {
  assert.deepEqual(argvs('git log > out.txt 2>&1 < in.txt'), [['git', 'log']])
})

test('marks commands inside while and until loops', () => {
  const loops = commandsOf('while true; do sleep 5; done; until x; do y; done; sleep 1').map((c) => [c.argv[0], c.inWhile])
  assert.deepEqual(loops, [['true', true], ['sleep', true], ['x', true], ['y', true], ['sleep', false]])
})

test('marks background commands', () => {
  assert.deepEqual(commandsOf('sleep 60 & echo').map((c) => c.background), [true, false])
})
