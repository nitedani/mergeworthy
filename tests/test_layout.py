#!/usr/bin/env python3
"""The plugin's layout holds together. Run: python3 tests/test_layout.py (exit 0 = all pass).
- every skills/<name>/SKILL.md has YAML frontmatter whose name is its folder and whose description is set
- every skill another file names (`mergeworthy:<skill>`) exists
- every script hooks/hooks.json runs exists and is executable or a .py file
- `claude plugin validate .` passes, when claude is installed"""
import glob, json, os, re, shutil, subprocess, sys
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
os.chdir(ROOT)
fails = []
skills = sorted(os.path.basename(os.path.dirname(p)) for p in glob.glob('skills/*/SKILL.md'))
for name in skills:
    m = re.match(r'---\nname: (.+)\ndescription: (".+")\n---\n', open(f'skills/{name}/SKILL.md').read())
    if not m: fails.append(f'skills/{name}/SKILL.md: frontmatter is not `name` then a quoted `description`'); continue
    if m.group(1) != name: fails.append(f'skills/{name}/SKILL.md: name {m.group(1)!r} is not its folder')
    if not json.loads(m.group(2)).strip(): fails.append(f'skills/{name}/SKILL.md: empty description')
for p in glob.glob('skills/*/SKILL.md') + ['always-on.md'] + glob.glob('hooks/*') + glob.glob('bin/*'):
    for ref in set(re.findall(r'`mergeworthy:([a-z-]+)`', open(p, errors='replace').read())):
        if ref not in skills: fails.append(f'{p}: names `mergeworthy:{ref}`, which is not a skill')
for e in json.load(open('hooks/hooks.json'))['hooks'].values():
    for h in (h for m in e for h in m['hooks']):
        script = re.search(r'\}"?/([\w./-]+)', h['command']).group(1)
        if not os.path.isfile(script): fails.append(f'hooks.json runs {script}, which does not exist')
        elif not script.endswith('.py') and not os.access(script, os.X_OK): fails.append(f'{script} is not executable')
if shutil.which('node') and subprocess.run(['node', '--check', 'cli/index.mjs']).returncode != 0:
    fails.append('cli/index.mjs does not parse')
if shutil.which('claude'):
    r = subprocess.run(['claude', 'plugin', 'validate', '.'], capture_output=True, text=True)
    if r.returncode != 0: fails.append('claude plugin validate failed:\n' + r.stdout + r.stderr)
for f in fails: print('FAIL', f)
print(f'{len(skills)} skills, {len(fails)} failures')
sys.exit(1 if fails else 0)
