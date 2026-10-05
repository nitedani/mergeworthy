#!/usr/bin/env node
// npx mergeworthy [install|uninstall] [--yes] [--agents claude,codex,other] [--source <owner/repo or path>]
// Installs mergeworthy into the coding agents on this machine through each agent's own plugin system, so updates come
// from that system: Claude Code (skills, hooks, commands, options; auto-update on), Codex (skills, and the always-on
// rules in ~/.codex/AGENTS.md), and any other agent through skills.sh (skills only).
import * as p from '@clack/prompts'
import { execFileSync, spawnSync } from 'node:child_process'
import fs from 'node:fs'
import os from 'node:os'
import path from 'node:path'

const NAME = 'mergeworthy'
const ID = `${NAME}@${NAME}`
const args = process.argv.slice(2)
const flag = (f) => args.includes(f)
const SOURCE = (args.includes('--source') && args[args.indexOf('--source') + 1]) || 'nitedani/mergeworthy'
const YES = flag('--yes') || flag('-y')
const HOME = os.homedir()
const CLAUDE_DIR = process.env.CLAUDE_CONFIG_DIR || path.join(HOME, '.claude')
const CODEX_DIR = process.env.CODEX_HOME || path.join(HOME, '.codex')
const SETTINGS = path.join(CLAUDE_DIR, 'settings.json')
const BEGIN = `<!-- ${NAME}:begin (written by npx ${NAME}; re-run it to update) -->`
const END = `<!-- ${NAME}:end -->`

const has = (cmd) => spawnSync('sh', ['-c', `command -v ${cmd}`]).status === 0
const run = (cmd, argv, opts = {}) => {
  const r = spawnSync(cmd, argv, { encoding: 'utf8', ...opts })
  if (r.status !== 0) throw new Error(`${cmd} ${argv.join(' ')} failed:\n${r.stderr || r.stdout || ''}`)
  return r.stdout
}
const readJson = (f, d) => (fs.existsSync(f) ? JSON.parse(fs.readFileSync(f, 'utf8')) : d)
const writeJson = (f, v) => fs.writeFileSync(f, JSON.stringify(v, null, 2) + '\n')
const bail = (v) => {
  if (p.isCancel(v)) { p.cancel('Nothing changed.'); process.exit(0) }
  return v
}

// The options declared in .claude-plugin/plugin.json, with their choices and defaults
const OPTIONS = {
  badge: { label: 'Agent badge on posts', choices: ['on', 'off', 'auto'] },
  merge: { label: 'Who merges', choices: ['on-request-squash', 'reviewer'] },
  watcher: { label: 'GitHub watcher', choices: ['on', 'off'] },
  local_model: { label: 'Local model for routine work', choices: ['off', 'on'] },
}

// ---------- Claude Code ----------
function claudeInstalled() {
  try { return JSON.parse(run('claude', ['plugin', 'list', '--json'])).find((x) => x.id === ID) } catch { return undefined }
}
function installClaude(values) {
  const known = readJson(path.join(CLAUDE_DIR, 'plugins', 'known_marketplaces.json'), {})
  if (!known[NAME]) run('claude', ['plugin', 'marketplace', 'add', SOURCE])
  // Auto-update is off by default for marketplaces other than Anthropic's; it's a setting on the marketplace entry
  const s = readJson(SETTINGS, {})
  if (s.extraKnownMarketplaces?.[NAME] && s.extraKnownMarketplaces[NAME].autoUpdate !== true) {
    s.extraKnownMarketplaces[NAME].autoUpdate = true
    writeJson(SETTINGS, s)
  }
  if (claudeInstalled()) run('claude', ['plugin', 'configure', ID, '--values-stdin'], { input: JSON.stringify(values) })
  else run('claude', ['plugin', 'install', ID, ...Object.entries(values).flatMap(([k, v]) => ['--config', `${k}=${v}`])])
  // The stable path watchers and cron use; the session-start hook keeps it current after this
  const installed = claudeInstalled()
  if (installed?.installPath) {
    fs.mkdirSync(path.join(HOME, '.mergeworthy'), { recursive: true })
    fs.rmSync(path.join(HOME, '.mergeworthy', 'current'), { force: true })
    fs.symlinkSync(installed.installPath, path.join(HOME, '.mergeworthy', 'current'))
  }
}
function uninstallClaude() {
  if (claudeInstalled()) run('claude', ['plugin', 'uninstall', ID])
  try { run('claude', ['plugin', 'marketplace', 'remove', NAME]) } catch {}
  fs.rmSync(path.join(HOME, '.mergeworthy'), { recursive: true, force: true })
}

// ---------- The install this replaced (install-methodology): hooks in settings.json, a CLAUDE.md block, copies ----------
const MECH = path.join(CLAUDE_DIR, 'mechanisms')
const CURRENT = path.join(HOME, '.mergeworthy', 'current')
function oldInstallFound() {
  const hooks = JSON.stringify(readJson(SETTINGS, {}).hooks || {})
  return hooks.includes('.claude/mechanisms/') || readText(path.join(CLAUDE_DIR, 'CLAUDE.md')).includes('<!-- methodology:begin')
}
function readText(f) { return fs.existsSync(f) ? fs.readFileSync(f, 'utf8') : '' }
function removeOldInstall() {
  const s = readJson(SETTINGS, {})
  for (const [event, entries] of Object.entries(s.hooks || {})) {
    s.hooks[event] = entries.filter((e) => !e.hooks.some((h) => /\.claude\/mechanisms\//.test(h.command)))
    // claude-swap moved into the plugin's bin/: point the usage-limit hook at the stable path
    for (const e of s.hooks[event]) for (const h of e.hooks) h.command = h.command.replace(/^~\/\.local\/bin\/claude-swap\b/, '~/.mergeworthy/current/bin/claude-swap')
    if (!s.hooks[event].length) delete s.hooks[event]
  }
  writeJson(SETTINGS, s)
  const md = path.join(CLAUDE_DIR, 'CLAUDE.md')
  fs.writeFileSync(md, readText(md).replace(/\n*<!-- methodology:begin[\s\S]*?<!-- methodology:end -->\n?/, '\n'))
  const skills = path.join(CLAUDE_DIR, 'skills')
  for (const d of fs.existsSync(skills) ? fs.readdirSync(skills) : []) if (d.startsWith('methodology-')) fs.rmSync(path.join(skills, d), { recursive: true })
  // Sessions started before this keep their hooks and PATH from the old install (hooks are read at session start):
  // the old files become links to the new version, so those sessions keep working, on the new code
  const NEW = { 'post-lint.py': 'bin/post-lint', 'tracker-check.sh': 'bin/tracker-check' }
  for (const f of fs.existsSync(MECH) ? fs.readdirSync(MECH) : []) {
    const rel = NEW[f] || (fs.existsSync(path.join(CURRENT, 'hooks', f)) ? `hooks/${f}` : fs.existsSync(path.join(CURRENT, 'bin', f)) ? `bin/${f}` : null)
    if (!rel) continue
    fs.rmSync(path.join(MECH, f), { force: true })
    fs.symlinkSync(path.join(CURRENT, rel), path.join(MECH, f))
  }
  // Running watchers link their scripts from the old copies: point them at the stable path, then stop the daemon by its
  // PID so its supervisor (systemd, launchd, cron) restarts it on the new code. Stopped watchers stay stopped.
  const alive = (pid) => { try { process.kill(pid, 0); return true } catch { return false } }
  const dirs = readText(path.join(CLAUDE_DIR, 'gh-watch-dirs.txt')).split('\n')
    .filter((d) => d && alive(Number(readText(path.join(d, 'gh-watch.pid')).trim()) || -1))
  for (const d of dirs) {
    for (const f of ['gh-watch.py', 'gh-watch-daemon.sh']) {
      const l = path.join(d, f)
      try { if (fs.readlinkSync(l).startsWith(MECH)) { fs.rmSync(l); fs.symlinkSync(path.join(CURRENT, 'bin', f), l) } } catch {}
    }
    for (const f of ['agent', 'wake.pid', 'wake.launch']) fs.rmSync(path.join(d, f), { force: true })
    process.kill(Number(readText(path.join(d, 'gh-watch.pid')).trim()), 'SIGTERM')
  }
  return dirs.length
}

// ---------- Codex ----------
function codexHasPlugin() {
  try { return run('codex', ['plugin', 'list']).split('\n').some((l) => l.startsWith(`${ID} `) && !l.includes('not installed')) } catch { return false }
}
function writeAgentsBlock(text) {
  const f = path.join(CODEX_DIR, 'AGENTS.md')
  let old = readText(f)
  const a = old.indexOf(BEGIN), b = old.indexOf(END)
  if (a >= 0 && b > a) old = old.slice(0, a) + old.slice(b + END.length).replace(/^\n/, '')
  fs.writeFileSync(f, text ? `${old.trimEnd()}${old.trim() ? '\n\n' : ''}${BEGIN}\n${text.trim()}\n${END}\n` : old)
}
function installCodex() {
  fs.mkdirSync(CODEX_DIR, { recursive: true })
  try { run('codex', ['plugin', 'marketplace', 'add', SOURCE]) } catch (e) { if (!/already/i.test(String(e))) throw e }
  try { run('codex', ['plugin', 'marketplace', 'upgrade', NAME]) } catch {}
  if (!codexHasPlugin()) run('codex', ['plugin', 'add', ID])
  // Codex doesn't run plugin hooks, so the always-on rules go into its AGENTS.md
  const root = run('codex', ['plugin', 'marketplace', 'list']).split('\n').find((l) => l.includes(NAME))?.match(/(\/\S+)/)?.[1]
  const text = root && readText(path.join(root, 'always-on.md'))
  if (text) writeAgentsBlock(text)
}
function uninstallCodex() {
  try { run('codex', ['plugin', 'remove', ID]) } catch {}
  try { run('codex', ['plugin', 'marketplace', 'remove', NAME]) } catch {}
  writeAgentsBlock('')
}

// ---------- Other agents (skills.sh) ----------
const skillsSh = (verb) => spawnSync('npx', ['-y', 'skills', verb, ...(verb === 'add' ? [SOURCE] : [NAME]), '-g'], { stdio: 'inherit' })

// ---------- main ----------
async function main() {
  const uninstall = args[0] === 'uninstall'
  p.intro(uninstall ? `Uninstall ${NAME}` : NAME)
  const agents = [
    has('claude') && { value: 'claude', label: 'Claude Code', hint: 'skills, hooks, commands, options; updates itself' },
    has('codex') && { value: 'codex', label: 'Codex', hint: 'skills and the always-on rules; re-run to update' },
    { value: 'other', label: 'Other agents (skills.sh)', hint: 'skills only; you pick the agents next' },
  ].filter(Boolean)
  const only = args.includes('--agents') ? args[args.indexOf('--agents') + 1].split(',') : null
  const targets = only ? only : YES ? agents.filter((a) => a.value !== 'other').map((a) => a.value)
    : bail(await p.multiselect({ message: uninstall ? 'Remove it from' : 'Install it into', options: agents, initialValues: agents.filter((a) => a.value !== 'other').map((a) => a.value), required: true }))

  if (uninstall) {
    const s = p.spinner()
    if (targets.includes('claude')) { s.start('Claude Code'); uninstallClaude(); s.stop('Removed from Claude Code') }
    if (targets.includes('codex')) { s.start('Codex'); uninstallCodex(); s.stop('Removed from Codex') }
    if (targets.includes('other')) skillsSh('remove')
    p.outro('Done. Watch folders and drafts are left as they are.')
    return
  }

  let values
  if (targets.includes('claude')) {
    const current = readJson(SETTINGS, {}).pluginConfigs?.[ID]?.options || {}
    values = {}
    for (const [key, o] of Object.entries(OPTIONS)) {
      const initial = current[key] || o.choices[0]
      values[key] = YES ? initial : bail(await p.select({ message: o.label, options: o.choices.map((c) => ({ value: c, label: c })), initialValue: initial }))
    }
  }
  const migrate = targets.includes('claude') && oldInstallFound() &&
    (YES || bail(await p.confirm({ message: 'An older install (install-methodology) is here: replace it? Its hooks, CLAUDE.md block and copies go; watchers are moved over.' })))

  const s = p.spinner()
  if (targets.includes('claude')) {
    s.start('Claude Code'); installClaude(values); s.stop('Claude Code: installed, auto-update on')
    if (migrate) { s.start('Older install'); const n = removeOldInstall(); s.stop(`Older install removed; ${n} watcher(s) moved over`) }
  }
  if (targets.includes('codex')) { s.start('Codex'); installCodex(); s.stop('Codex: installed, always-on rules in ~/.codex/AGENTS.md') }
  if (targets.includes('other')) skillsSh('add')
  p.outro('Done. New sessions load it; run this again to change the options or add an agent.')
}

main().catch((e) => { p.cancel(String(e.message || e)); process.exit(1) })
