#!/usr/bin/env python3
"""Tests for build.sh and filter.py. Run: python3 test_build.py (exit 0 = all pass).
Builds in ./build-check/ (never /tmp): a copy of the sources, so dist/ is only compared, never written."""
import importlib.util, os, re, shutil, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
spec = importlib.util.spec_from_file_location('filter', os.path.join(ROOT, 'claude', 'tools', 'filter.py'))
flt = importlib.util.module_from_spec(spec); spec.loader.exec_module(flt)
DEFAULTS = {k: v[0] for k, v in flt.SCHEMA.items()}
fails = []

def expect(name, ok):
    if not ok: fails.append(name)

def render(text, **kw):
    try:
        return flt.render(text, {**DEFAULTS, **kw})
    except SystemExit as e:
        return f'ERROR {e}'

# the filter: inline and whole-line blocks, else, negation, and every malformed marker
expect('inline', render('a<!-- if target=ci -->C<!-- else -->L<!-- end -->b') == 'aLb')
expect('inline ci', render('a<!-- if target=ci -->C<!-- else -->L<!-- end -->b', target='ci') == 'aCb')
expect('whole lines', render('x\n<!-- if watcher=on -->\nW\n<!-- end -->\ny\n', watcher='off') == 'x\ny\n')
expect('negation', render('<!-- if badge!=off -->B<!-- end -->', badge='auto') == 'B')
for bad in ('<!-- if nope=x -->a<!-- end -->', '<!-- if target=nope -->a<!-- end -->', '<!-- if target=ci -->a',
            'a<!-- end -->', '<!-- if target=ci -->a<!-- else -->b<!-- else -->c<!-- end -->'):
    expect(f'rejects {bad!r}', render(bad).startswith('ERROR'))

# every marker in methodology/ parses, with known keys and values (each file balanced on its own)
for d, _, files in os.walk(os.path.join(ROOT, 'methodology')):
    for f in files:
        out = render(open(os.path.join(d, f)).read())
        expect(f'{f}: {out}', not out.startswith('ERROR'))

# every profile sets known keys to known values
for f in os.listdir(os.path.join(ROOT, 'profiles')):
    for k, v in re.findall(r'^(\w+)=(\S+)', open(os.path.join(ROOT, 'profiles', f)).read(), re.M):
        expect(f'profiles/{f}: {k}={v}', v in flt.SCHEMA.get(k, ()))

# the committed dist/ files are what build.sh makes; the no-profile build differs from them at most in the settings header
B = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'build-check')
shutil.rmtree(B, ignore_errors=True)
for x in ('methodology', 'claude', 'profiles'): shutil.copytree(os.path.join(ROOT, x), os.path.join(B, x))
shutil.copy2(os.path.join(ROOT, 'build.sh'), B)
r = subprocess.run(['./build.sh', '--all'], cwd=B, capture_output=True, text=True)
expect(f'build.sh --all: {r.stderr}', r.returncode == 0)
body = lambda p: re.sub(r'\A<!-- settings: .* -->\n', '', open(p).read()) if os.path.exists(p) else None
for name in ('prompt', 'ci', 'local'):
    built, committed = (os.path.join(b, 'dist', f'methodology-{name}.md') for b in (B, ROOT))
    if name == 'prompt':
        expect('no-profile build equals dist/methodology-prompt.md, header aside', body(built) == body(committed))
    else:
        expect(f'dist/methodology-{name}.md is current', open(built).read() == open(committed).read())
shutil.rmtree(B)

for f in fails: print('FAIL', f)
print(f'{len(fails)} failures')
sys.exit(1 if fails else 0)
